"""
PROMEOS — Enedis Data Connect API routes (Sprint F Connectors)

Prefix: /api/dataconnect
OAuth2 flow, consent check, sync consumption.

Sprint C-7 Phase 7.8 — Fix IDOR critique (audit deep multi-agents Phase 7) :
ajout `resolve_org_id` + validation PRM ↔ org via JOIN Meter→Site→Portefeuille→EJ.
Anti-CWE-639 (IDOR) + CWE-862 (Missing Authorization).
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth

logger = logging.getLogger("promeos.routes.dataconnect")

router = APIRouter(prefix="/api/dataconnect", tags=["Enedis Data Connect"])

# In-memory PKCE state cache: state -> code_verifier (acceptable for POC)
_pending_auth: dict[str, str] = {}


def _assert_prm_belongs_to_org(db: Session, prm: str, org_id: int) -> None:
    """Sprint C-7 Phase 7.8 — Fix IDOR : valide PRM ↔ org via JOIN chain.

    JOIN Meter → Site → Portefeuille → EntiteJuridique.organisation_id.
    Si PRM existe mais hors-scope org → 403 (anti-énumération cross-tenant).
    Si PRM inexistant en DB → 404 (legitimate).

    Anti-CWE-639 (IDOR) cardinal pré-pilote.
    """
    from models import EntiteJuridique, Portefeuille, Site
    from models.energy_models import Meter

    meter = (
        db.query(Meter)
        .join(Site, Meter.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(
            Meter.meter_id == prm,
            EntiteJuridique.organisation_id == org_id,
        )
        .first()
    )
    if not meter:
        # 403 plutôt que 404 : anti-énumération PRM cross-tenant
        raise HTTPException(status_code=403, detail="PRM hors scope organisation")


# --- Schemas ---


class AuthorizeResponse(BaseModel):
    auth_url: str
    state: str


class CallbackResponse(BaseModel):
    access_token: str
    prm: str
    expires_at: str


class ConsentResponse(BaseModel):
    prm: str
    consent_status: str
    consent_expiry: Optional[str] = None
    contracts: Optional[dict] = None


class TokenInfo(BaseModel):
    id: int
    connector_name: str
    prm: str
    expires_at: str
    consent_status: str
    consent_expiry: Optional[str] = None


class SyncResponse(BaseModel):
    prm: str
    readings_count: int
    date_start: Optional[str] = None
    date_end: Optional[str] = None


# --- Endpoints ---


@router.get("/authorize", response_model=AuthorizeResponse)
def authorize(
    request: Request,
    prm: str = Query(..., min_length=14, max_length=14, description="PRM 14 chiffres"),
    redirect_uri: str = Query(..., description="URI de redirection OAuth2"),
    state: Optional[str] = Query(None, description="State parameter (auto-généré si absent)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Génère l'URL d'autorisation OAuth2 Enedis avec PKCE.

    Sprint C-7 Phase 7.8 — Fix IDOR : auth obligatoire (anti-DEMO_MODE bypass).
    Note : pas de validation PRM ↔ org ici car Meter potentiellement pas encore créé
    (onboarding initial). L'org_id est résolu pour audit trail.
    """
    from services.scope_utils import resolve_org_id

    resolve_org_id(request, auth, db)  # auth + org-scoping enforcement
    from connectors.enedis_dataconnect import EnedisDataConnectConnector
    from connectors.enedis_dataconnect_errors import EnedisDataConnectError

    try:
        connector = EnedisDataConnectConnector()
        result = connector.get_authorization_url(prm, redirect_uri, state)
        # Store code_verifier server-side, keyed by state
        _pending_auth[result["state"]] = result["code_verifier"]
        return AuthorizeResponse(auth_url=result["auth_url"], state=result["state"])
    except EnedisDataConnectError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/callback", response_model=CallbackResponse)
def callback(
    code: str = Query(..., description="Code d'autorisation OAuth2"),
    state: str = Query(..., description="State parameter"),
    prm: str = Query("", description="PRM (optionnel, extrait du scope)"),
    redirect_uri: str = Query(..., description="Même redirect_uri que pour /authorize"),
    db: Session = Depends(get_db),
):
    """Échange le code d'autorisation contre un token OAuth2."""
    from connectors.enedis_dataconnect import EnedisDataConnectConnector
    from connectors.enedis_dataconnect_errors import EnedisDataConnectError, EnedisApiError

    # Retrieve code_verifier from server-side state cache
    code_verifier = _pending_auth.pop(state, None)
    if not code_verifier:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    try:
        connector = EnedisDataConnectConnector()
        result = connector.exchange_code(code, code_verifier, redirect_uri, db)
        return CallbackResponse(**result)
    except EnedisApiError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except EnedisDataConnectError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/consent/{prm}", response_model=ConsentResponse)
def check_consent(
    prm: str,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Vérifie le statut du consentement pour un PRM.

    Sprint C-7 Phase 7.8 — Fix IDOR : validation PRM ↔ org stricte.
    """
    from services.scope_utils import resolve_org_id

    org_id = resolve_org_id(request, auth, db)
    _assert_prm_belongs_to_org(db, prm, org_id)
    from connectors.enedis_dataconnect import EnedisDataConnectConnector
    from connectors.enedis_dataconnect_errors import EnedisDataConnectError, TokenInvalidError

    try:
        connector = EnedisDataConnectConnector()
        result = connector.check_consent(prm, db)
        return ConsentResponse(**result)
    except TokenInvalidError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except EnedisDataConnectError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sync/{prm}", response_model=SyncResponse)
def sync_consumption(
    prm: str,
    request: Request,
    start: Optional[date] = Query(None, description="Date début (défaut: J-30)"),
    end: Optional[date] = Query(None, description="Date fin (défaut: aujourd'hui)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Récupère la consommation journalière et l'écrit en MeterReading.

    Sprint C-7 Phase 7.8 — Fix IDOR : validation PRM ↔ org stricte avant sync écriture.
    """
    from services.scope_utils import resolve_org_id

    org_id = resolve_org_id(request, auth, db)
    _assert_prm_belongs_to_org(db, prm, org_id)
    from connectors.enedis_dataconnect import EnedisDataConnectConnector
    from connectors.enedis_dataconnect_errors import EnedisDataConnectError, TokenInvalidError
    from models.energy_models import Meter, MeterReading, DataImportJob, FrequencyType, ImportStatus
    from sqlalchemy import insert

    start = start or (date.today() - timedelta(days=30))
    end = end or date.today()

    try:
        connector = EnedisDataConnectConnector()
        daily = connector.fetch_daily_consumption(prm, start, end, db)
    except TokenInvalidError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except EnedisDataConnectError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Trouver ou créer le Meter
    meter = db.query(Meter).filter(Meter.meter_id == prm).first()
    if not meter:
        raise HTTPException(status_code=404, detail=f"Aucun Meter pour PRM {prm}")

    # Créer un job d'import
    job = DataImportJob(
        job_type="dataconnect_sync",
        status=ImportStatus.PROCESSING,
        meter_id=meter.id,
        date_start=datetime.combine(start, datetime.min.time()),
        date_end=datetime.combine(end, datetime.min.time()),
        created_by="dataconnect",
    )
    db.add(job)
    db.flush()

    # Insérer les readings
    inserted = 0
    for day_data in daily:
        ts_str = day_data.get("date")
        if not ts_str:
            continue
        try:
            ts = datetime.strptime(ts_str[:10], "%Y-%m-%d")
            value_kwh = day_data["value_wh"] / 1000.0

            stmt = (
                insert(MeterReading)
                .prefix_with("OR IGNORE")
                .values(
                    meter_id=meter.id,
                    timestamp=ts,
                    frequency=FrequencyType.DAILY,
                    value_kwh=round(value_kwh, 3),
                    is_estimated=False,
                    quality_score=1.0,
                    import_job_id=job.id,
                    created_at=datetime.now(timezone.utc),
                )
            )
            db.execute(stmt)
            inserted += 1
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("Skip reading: %s", e)

    job.status = ImportStatus.COMPLETED
    job.rows_total = len(daily)
    job.rows_imported = inserted
    job.completed_at = datetime.now(timezone.utc)
    db.commit()

    return SyncResponse(
        prm=prm,
        readings_count=inserted,
        date_start=start.isoformat(),
        date_end=end.isoformat(),
    )


@router.get("/tokens", response_model=list[TokenInfo])
def list_tokens(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les tokens Data Connect stockés (filtrés org).

    Sprint C-7 Phase 7.8 — Fix IDOR cardinal : avant fix, GET /tokens retournait
    TOUS les tokens toutes orgs confondues (CWE-200 + CWE-639). Maintenant filtré
    via JOIN Meter→Site→Portefeuille→EJ.organisation_id == org_id.
    """
    from models import EntiteJuridique, Portefeuille, Site
    from models.connector_token import ConnectorToken
    from models.energy_models import Meter
    from services.scope_utils import resolve_org_id

    org_id = resolve_org_id(request, auth, db)

    # PRM autorisés pour l'org via JOIN chain
    org_prms = {
        m.meter_id
        for m in db.query(Meter)
        .join(Site, Meter.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    }

    tokens = (
        db.query(ConnectorToken)
        .filter(
            ConnectorToken.connector_name == "enedis_dataconnect",
            ConnectorToken.prm.in_(org_prms) if org_prms else False,
        )
        .order_by(ConnectorToken.prm)
        .all()
    )
    return [
        TokenInfo(
            id=t.id,
            connector_name=t.connector_name,
            prm=t.prm,
            expires_at=t.expires_at.isoformat() if t.expires_at else "",
            consent_status=t.consent_status or "unknown",
            consent_expiry=t.consent_expiry.isoformat() if t.consent_expiry else None,
        )
        for t in tokens
    ]


@router.delete("/tokens/{prm}")
def delete_token(
    prm: str,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Supprime un token Data Connect pour un PRM.

    Sprint C-7 Phase 7.8 — Fix IDOR : validation PRM ↔ org avant suppression
    (anti-DELETE cross-tenant CWE-639).
    """
    from models.connector_token import ConnectorToken
    from services.scope_utils import resolve_org_id

    org_id = resolve_org_id(request, auth, db)
    _assert_prm_belongs_to_org(db, prm, org_id)

    token = db.query(ConnectorToken).filter_by(connector_name="enedis_dataconnect", prm=prm).first()
    if not token:
        raise HTTPException(status_code=404, detail=f"Token non trouvé pour PRM {prm}")

    db.delete(token)
    db.commit()
    return {"deleted": True, "prm": prm}
