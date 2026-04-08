"""
PROMEOS Connectors — Enedis Data Connect OAuth2 (PKCE)

Client complet pour l'API Enedis Data Connect v5.
OAuth2 Authorization Code + PKCE (S256).
Rate limit: 10 req/s via simple time.sleep.
"""

import hashlib
import logging
import os
import secrets
import time
import base64
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional

import httpx
from sqlalchemy.orm import Session

from .base import Connector
from .enedis_dataconnect_errors import (
    EnedisDataConnectError,
    ConsentExpiredError,
    ConsentRevokedError,
    PrmNotFoundError,
    TokenInvalidError,
    RateLimitError,
    EnedisApiError,
)

logger = logging.getLogger("promeos.connectors.enedis_dataconnect")

# Base URLs par environnement
_BASE_URLS = {
    "sandbox": "https://gw.hml.api.enedis.fr",
    "production": "https://gw.prd.api.enedis.fr",
}

# Rate limiter simple (timestamp du dernier appel)
_last_request_time: float = 0.0
_MIN_INTERVAL = 0.1  # 10 req/s


def _rate_limit():
    """Attend si nécessaire pour respecter 10 req/s."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def _generate_code_verifier() -> str:
    """Génère un code_verifier PKCE (43-128 caractères URL-safe)."""
    return secrets.token_urlsafe(64)[:96]


def _generate_code_challenge(code_verifier: str) -> str:
    """Génère le code_challenge S256 à partir du code_verifier."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class EnedisDataConnectConnector(Connector):
    """Client OAuth2 Enedis Data Connect v5 avec PKCE."""

    name = "enedis_dataconnect"
    description = "Enedis Data Connect OAuth — consommation Linky"
    requires_auth = True
    env_vars = ["ENEDIS_CLIENT_ID", "ENEDIS_CLIENT_SECRET"]

    def __init__(self):
        env = os.environ.get("ENEDIS_ENV", "sandbox")
        self.base_url = _BASE_URLS.get(env, _BASE_URLS["sandbox"])
        self.client_id = os.environ.get("ENEDIS_CLIENT_ID", "")
        self.client_secret = os.environ.get("ENEDIS_CLIENT_SECRET", "")
        self.timeout = 30.0

    # --- OAuth2 ---

    def get_authorization_url(self, prm: str, redirect_uri: str, state: str | None = None) -> dict:
        """Construit l'URL d'autorisation OAuth2 avec PKCE (S256).

        Retourne: {auth_url, state, code_verifier}
        """
        if not self.client_id:
            raise EnedisDataConnectError("ENEDIS_CLIENT_ID non configuré")

        code_verifier = _generate_code_verifier()
        code_challenge = _generate_code_challenge(code_verifier)
        state = state or secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "duration": "P3Y",  # consentement 3 ans
        }
        # Enedis attend le PRM dans le scope
        if prm:
            params["scope"] = f"openid {prm}"

        auth_url = f"{self.base_url}/dataconnect/v1/oauth2/authorize?" + "&".join(f"{k}={v}" for k, v in params.items())

        return {
            "auth_url": auth_url,
            "state": state,
            "code_verifier": code_verifier,
        }

    def exchange_code(self, code: str, code_verifier: str, redirect_uri: str, db: Session) -> dict:
        """Échange le code d'autorisation contre un token. Stocke en DB.

        Retourne: {access_token, prm, expires_at}
        """
        _rate_limit()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code_verifier": code_verifier,
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/oauth2/v3/token", data=data)

        if resp.status_code != 200:
            raise EnedisApiError(resp.status_code, resp.text)

        token_data = resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 12600)  # ~3.5h par défaut
        scope = token_data.get("scope", "")

        # Extraire le PRM du scope (format: "openid 12345678901234")
        prm = ""
        for part in scope.split():
            if part.isdigit() and len(part) == 14:
                prm = part
                break

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Stocker le token
        self._store_token(
            db=db,
            prm=prm or "__client__",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scope=scope,
        )

        return {
            "access_token": access_token,
            "prm": prm,
            "expires_at": expires_at.isoformat(),
        }

    def _store_token(
        self,
        db: Session,
        prm: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime,
        scope: str = "",
        consent_expiry: date | None = None,
    ):
        """INSERT OR UPDATE le token en DB."""
        from models.connector_token import ConnectorToken

        existing = db.query(ConnectorToken).filter_by(connector_name=self.name, prm=prm).first()

        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token or existing.refresh_token
            existing.expires_at = expires_at
            existing.scope = scope
            existing.consent_status = "active"
            if consent_expiry:
                existing.consent_expiry = consent_expiry
        else:
            token = ConnectorToken(
                connector_name=self.name,
                prm=prm,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                scope=scope,
                consent_status="active",
                consent_expiry=consent_expiry,
            )
            db.add(token)

        db.commit()

    def _get_valid_token(self, prm: str, db: Session) -> str:
        """Récupère un token valide pour le PRM, refresh si proche de l'expiration.

        Retourne: access_token (string)
        Raises: TokenInvalidError si pas de token, ConsentExpiredError si expiré.
        """
        from models.connector_token import ConnectorToken

        token_row = db.query(ConnectorToken).filter_by(connector_name=self.name, prm=prm).first()
        if not token_row:
            raise TokenInvalidError(f"Aucun token pour le PRM {prm}")

        # Vérifier consentement
        if token_row.consent_status == "revoked":
            raise ConsentRevokedError(prm)
        if token_row.consent_expiry and token_row.consent_expiry < date.today():
            token_row.consent_status = "expired"
            db.commit()
            raise ConsentExpiredError(prm)

        now = datetime.now(timezone.utc)
        # Rafraîchir si expire dans moins de 5 minutes
        if token_row.expires_at.replace(tzinfo=timezone.utc) < now + timedelta(minutes=5):
            if token_row.refresh_token:
                self._refresh_token(token_row, db)
            else:
                raise TokenInvalidError("Token expiré et pas de refresh_token")

        return token_row.access_token

    def _refresh_token(self, token_row, db: Session):
        """Rafraîchit le token via le grant refresh_token."""
        _rate_limit()
        data = {
            "grant_type": "refresh_token",
            "refresh_token": token_row.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/oauth2/v3/token", data=data)

        if resp.status_code != 200:
            logger.warning("Refresh token failed (%d): %s", resp.status_code, resp.text[:200])
            raise TokenInvalidError("Refresh token invalide")

        token_data = resp.json()
        token_row.access_token = token_data["access_token"]
        if "refresh_token" in token_data:
            token_row.refresh_token = token_data["refresh_token"]
        expires_in = token_data.get("expires_in", 12600)
        token_row.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        db.commit()
        logger.info("Token refreshed pour PRM %s", token_row.prm)

    @staticmethod
    def _extract_interval_readings(data: dict) -> list:
        """Extrait la liste interval_reading depuis la réponse Enedis."""
        return data.get("meter_reading", {}).get("interval_reading", [])

    # --- API calls ---

    def _api_get(self, path: str, params: dict, token: str, retries: int = 2) -> dict:
        """GET sur l'API Enedis avec gestion des erreurs et retry 429."""
        _rate_limit()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        for attempt in range(retries + 1):
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}{path}", params=params, headers=headers)

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2))
                if attempt < retries:
                    logger.warning("Rate limit 429, retry dans %ds (attempt %d)", retry_after, attempt + 1)
                    time.sleep(retry_after)
                    continue
                raise RateLimitError(retry_after)

            # Erreurs Enedis spécifiques
            body = resp.text
            if "ADAM-ERR0025" in body:
                raise ConsentExpiredError(params.get("usage_point_id", "?"))
            if "ADAM-ERR0069" in body:
                raise PrmNotFoundError(params.get("usage_point_id", "?"))
            if "ADAM-ERR0031" in body:
                raise TokenInvalidError()

            raise EnedisApiError(resp.status_code, body)

        # Ne devrait pas arriver
        raise EnedisApiError(0, "Max retries exceeded")

    def fetch_daily_consumption(self, prm: str, start: date, end: date, db: Session) -> List[dict]:
        """GET /metering_data_dc/v5/daily_consumption

        Retourne: [{date, value_wh}]
        """
        token = self._get_valid_token(prm, db)
        data = self._api_get(
            "/metering_data_dc/v5/daily_consumption",
            params={
                "usage_point_id": prm,
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            token=token,
        )

        return [
            {"date": r.get("date"), "value_wh": int(r.get("value", 0))} for r in self._extract_interval_readings(data)
        ]

    def fetch_load_curve(self, prm: str, start: date, end: date, db: Session) -> List[dict]:
        """GET /metering_data_clc/v5/consumption_load_curve

        Pagination par fenêtres de 7 jours (limite API Enedis).
        Retourne: [{date, value_w}]
        """
        token = self._get_valid_token(prm, db)
        results = []
        chunk_start = start

        while chunk_start < end:
            chunk_end = min(chunk_start + timedelta(days=7), end)
            data = self._api_get(
                "/metering_data_clc/v5/consumption_load_curve",
                params={
                    "usage_point_id": prm,
                    "start": chunk_start.isoformat(),
                    "end": chunk_end.isoformat(),
                },
                token=token,
            )

            results.extend(
                {"date": r.get("date"), "value_w": int(r.get("value", 0))}
                for r in self._extract_interval_readings(data)
            )

            chunk_start = chunk_end

        return results

    def check_consent(self, prm: str, db: Session) -> dict:
        """GET /customers_upc/v5/usage_points/contracts — vérifie le consentement.

        Retourne: {prm, consent_status, consent_expiry}
        """
        token = self._get_valid_token(prm, db)
        try:
            data = self._api_get(
                "/customers_upc/v5/usage_points/contracts",
                params={"usage_point_id": prm},
                token=token,
            )
            # Si la requête passe, le consentement est actif
            from models.connector_token import ConnectorToken

            token_row = db.query(ConnectorToken).filter_by(connector_name=self.name, prm=prm).first()
            if token_row:
                token_row.consent_status = "active"
                db.commit()

            return {
                "prm": prm,
                "consent_status": "active",
                "consent_expiry": token_row.consent_expiry.isoformat()
                if token_row and token_row.consent_expiry
                else None,
                "contracts": data,
            }
        except ConsentExpiredError:
            return {"prm": prm, "consent_status": "expired", "consent_expiry": None}
        except ConsentRevokedError:
            return {"prm": prm, "consent_status": "revoked", "consent_expiry": None}

    # --- Connector interface ---

    def test_connection(self) -> dict:
        if not self.client_id:
            return {
                "status": "pending",
                "message": "Identifiants OAuth non configurés — définir ENEDIS_CLIENT_ID/SECRET",
                "doc": "https://data-connect.enedis.fr/",
            }
        return {"status": "ok", "message": f"Client ID present, env={os.environ.get('ENEDIS_ENV', 'sandbox')}"}

    def sync(self, db: Session, object_type: str = "", object_id: int = 0, date_from=None, date_to=None):
        """Sync via Data Connect — nécessite un PRM avec token actif."""
        # object_id = meter_id, on cherche le PRM
        from models.energy_models import Meter

        meter = db.query(Meter).filter_by(id=object_id).first()
        if not meter:
            return []

        prm = meter.meter_id
        start = date_from or (date.today() - timedelta(days=30))
        end = date_to or date.today()

        if isinstance(start, datetime):
            start = start.date()
        if isinstance(end, datetime):
            end = end.date()

        daily = self.fetch_daily_consumption(prm, start, end, db)
        return daily
