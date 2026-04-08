"""
PROMEOS Connectors — GRDF ADICT REST client

Client pour l'API GRDF ADICT (Accès aux Données Individuelles de Consommation Tertiaire).
Authentification: OAuth2 client_credentials.
"""

import logging
import os
import time
from datetime import datetime, date, timedelta, timezone
from typing import List

import httpx
from sqlalchemy.orm import Session

from .base import Connector
from .grdf_errors import GrdfAdictError, PceNotFoundError, PceNotAuthorizedError, GrdfApiError

logger = logging.getLogger("promeos.connectors.grdf_adict")

# Base URLs
_BASE_URLS = {
    "sandbox": "https://api.grdf.fr/adict/v2",
    "production": "https://api.grdf.fr/adict/v2",
}
_SSO_URL = "https://sofit-sso-oidc.grdf.fr/openam/oauth2/realms/externeGrdf/access_token"

# Rate limiter
_last_request_time: float = 0.0
_MIN_INTERVAL = 0.2  # 5 req/s


def _rate_limit():
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


class GrdfAdictConnector(Connector):
    """Client REST GRDF ADICT avec OAuth2 client_credentials."""

    name = "grdf_adict"
    description = "GRDF ADICT — consommation gaz (PCE)"
    requires_auth = True
    env_vars = ["GRDF_CLIENT_ID", "GRDF_CLIENT_SECRET"]

    def __init__(self):
        env = os.environ.get("GRDF_ENV", "sandbox")
        self.base_url = _BASE_URLS.get(env, _BASE_URLS["sandbox"])
        self.sso_url = os.environ.get("GRDF_SSO_URL", _SSO_URL)
        self.client_id = os.environ.get("GRDF_CLIENT_ID", "")
        self.client_secret = os.environ.get("GRDF_CLIENT_SECRET", "")
        self.timeout = 30.0

    # --- OAuth2 client_credentials ---

    def _get_client_token(self, db: Session) -> str:
        """Obtient un token client_credentials, le stocke en DB si possible.

        Retourne: access_token (string)
        """
        from models.connector_token import ConnectorToken

        # Chercher token existant et valide
        token_row = db.query(ConnectorToken).filter_by(connector_name=self.name, prm="__client__").first()

        now = datetime.now(timezone.utc)
        if token_row and token_row.expires_at.replace(tzinfo=timezone.utc) > now + timedelta(minutes=2):
            return token_row.access_token

        # Demander un nouveau token
        if not self.client_id:
            raise GrdfAdictError("GRDF_CLIENT_ID non configuré")

        _rate_limit()
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "/adict/v2",
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self.sso_url, data=data)

        if resp.status_code != 200:
            raise GrdfApiError(resp.status_code, resp.text)

        token_data = resp.json()
        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        expires_at = now + timedelta(seconds=expires_in)

        # Stocker
        if token_row:
            token_row.access_token = access_token
            token_row.expires_at = expires_at
        else:
            token_row = ConnectorToken(
                connector_name=self.name,
                prm="__client__",
                access_token=access_token,
                expires_at=expires_at,
                consent_status="active",
            )
            db.add(token_row)
        db.commit()

        return access_token

    # --- API calls ---

    def _api_get(self, path: str, token: str, params: dict | None = None) -> dict:
        """GET sur l'API GRDF avec gestion des erreurs."""
        _rate_limit()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}{path}", params=params, headers=headers)

        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            # Extraire PCE du path
            pce = path.split("/pce/")[-1].split("/")[0] if "/pce/" in path else "?"
            raise PceNotFoundError(pce)
        if resp.status_code == 403:
            pce = path.split("/pce/")[-1].split("/")[0] if "/pce/" in path else "?"
            raise PceNotAuthorizedError(pce)

        raise GrdfApiError(resp.status_code, resp.text)

    @staticmethod
    def _extract_consommations(data: dict | list) -> list:
        """Extrait la liste de consommations depuis la réponse GRDF (format variable)."""
        return data if isinstance(data, list) else data.get("consommations", [])

    @staticmethod
    def _normalize_conso_base(conso: dict) -> dict:
        """Normalise les champs communs d'une consommation GRDF."""
        return {
            "date_debut": conso.get("dateDebutConsommation") or conso.get("date_debut"),
            "date_fin": conso.get("dateFinConsommation") or conso.get("date_fin"),
            "energie_kwh": conso.get("energieConsommee") or conso.get("energie_kwh"),
        }

    def fetch_informative_consumption(self, pce: str, date_debut: date, date_fin: date, db: Session) -> List[dict]:
        """GET /pce/{pce}/donnees_consos_informatives

        Retourne: [{date_debut, date_fin, energie_kwh, volume_m3}]
        """
        token = self._get_client_token(db)
        data = self._api_get(
            f"/pce/{pce}/donnees_consos_informatives",
            token=token,
            params={
                "date_debut": date_debut.isoformat(),
                "date_fin": date_fin.isoformat(),
            },
        )

        return [
            {
                **self._normalize_conso_base(c),
                "volume_m3": c.get("volumeBrutConsomme") or c.get("volume_m3"),
            }
            for c in self._extract_consommations(data)
        ]

    def fetch_published_consumption(self, pce: str, db: Session) -> List[dict]:
        """GET /pce/{pce}/donnees_consos_publiees

        Retourne les consommations publiées (index relevés).
        """
        token = self._get_client_token(db)
        data = self._api_get(f"/pce/{pce}/donnees_consos_publiees", token=token)

        return [
            {
                **self._normalize_conso_base(c),
                "index_debut": c.get("indexDebut") or c.get("index_debut"),
                "index_fin": c.get("indexFin") or c.get("index_fin"),
            }
            for c in self._extract_consommations(data)
        ]

    # --- Connector interface ---

    def test_connection(self) -> dict:
        if not self.client_id:
            return {
                "status": "pending",
                "message": "Identifiants OAuth non configurés — définir GRDF_CLIENT_ID/SECRET",
                "doc": "https://sites.grdf.fr/web/portail-api-grdf-adict",
            }
        return {"status": "ok", "message": "Client ID present (non testé)"}

    def sync(self, db: Session, object_type: str = "", object_id: int = 0, date_from=None, date_to=None):
        """Sync via GRDF ADICT — nécessite un PCE autorisé."""
        from models.energy_models import Meter

        meter = db.query(Meter).filter_by(id=object_id).first()
        if not meter:
            return []

        pce = meter.meter_id
        start = date_from or (date.today() - timedelta(days=365))
        end = date_to or date.today()

        if isinstance(start, datetime):
            start = start.date()
        if isinstance(end, datetime):
            end = end.date()

        return self.fetch_informative_consumption(pce, start, end, db)
