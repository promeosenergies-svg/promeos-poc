"""
PROMEOS — Routes PATCH RGPD consentement Org/DP (Sprint C-7 Phase 7.3, ADR-019).

Endpoints dédiés cohérents doctrine "endpoints dédiés RGPD" + audit trail clair.
Préparation Phase 7.4 wiring AuditLog automatique RGPD_CONSENT_CHANGE.

Cohérent :
- Phase 5.3 RGPD ext (consentement_*_by + cgu_version cols)
- Phase 5.6 F1 PRAGMA enforcement runtime
- Phase 5.8 G1 cascade Org wiring (réutilisé via cascade_recompute_on_change)
- Phase 7.2 ADR-017 Option B org_id validation DB stricte
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from models import (
    DeliveryPoint,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    not_deleted,
)
from regops.services.cascade_recompute_service import cascade_recompute_on_change
from schemas.rgpd_consent import (
    DeliveryPointConsentementLocalPatch,
    OrganisationConsentementPatch,
)
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api", tags=["RGPD Consent"])

_logger = logging.getLogger("promeos.rgpd_consent")


@router.patch("/organisations/{org_id}/consentement")
def patch_organisation_consentement(
    org_id: int,
    payload: OrganisationConsentementPatch,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Sprint C-7 Phase 7.3 (ADR-019) — PATCH consentement Org RGPD complet.

    Cohérent ADR-007 (modèle Org/DP cardinal) + ADR-007 ext (audit trail _by + cgu_version) +
    ADR-017 Option B (org_id validation DB stricte) + Phase 5.8 G1 (cascade wiring runtime).

    Validation pydantic stricte : `cgu_version` requis si `consentement_*_global` set
    (CNIL article 7 — preuve d'origine forte).
    """
    # Org-scoping strict (cohérent Phase 7.2 ADR-017 Option B)
    resolved_org_id = resolve_org_id(request, auth, db)
    if resolved_org_id != org_id:
        raise HTTPException(status_code=403, detail="Forbidden — org_id mismatch (cross-tenant blocked)")

    org = db.query(Organisation).filter(Organisation.id == org_id, not_deleted(Organisation)).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation introuvable")

    now = datetime.now(timezone.utc)
    user_id = auth.user_id if auth and getattr(auth, "user_id", None) else None
    cgu_version = payload.cgu_version

    # Capture old values pour cascade audit
    old_values = {
        "consentement_dataconnect_global": org.consentement_dataconnect_global,
        "consentement_grdf_global": org.consentement_grdf_global,
    }

    # Mutations cardinales (audit trail Phase 5.3 fields _by + _at + _cgu_version)
    if payload.consentement_dataconnect_global is not None:
        org.consentement_dataconnect_global = payload.consentement_dataconnect_global
        org.consentement_dataconnect_at = now
        org.consentement_dataconnect_by = user_id
        org.consentement_dataconnect_cgu_version = cgu_version

    if payload.consentement_grdf_global is not None:
        org.consentement_grdf_global = payload.consentement_grdf_global
        org.consentement_grdf_at = now
        org.consentement_grdf_by = user_id
        org.consentement_grdf_cgu_version = cgu_version

    db.commit()
    db.refresh(org)

    # Cascade trigger runtime — réutilise pattern Phase 5.8 G1 (via cascade_recompute_on_change)
    cascade_results = []
    for cascade_field in ("consentement_dataconnect_global", "consentement_grdf_global"):
        new_val = getattr(payload, cascade_field, None)
        if new_val is not None:
            try:
                result = cascade_recompute_on_change(
                    db=db,
                    entity=org,
                    field_modified=f"Organisation.{cascade_field}",
                    old_value=old_values[cascade_field],
                    new_value=new_val,
                    persist=True,
                    user_id=user_id,
                    org_id=org_id,
                )
                cascade_results.append({"field": cascade_field, "actions": len(result.actions)})
            except Exception as exc:  # noqa: BLE001 — résilience cascade (pattern Phase 5.8 G1)
                _logger.error("Cascade Org consent failed: %s", type(exc).__name__)

    # Phase 7.4 préparation : wiring AuditLog log_consent_change automatique (event RGPD_CONSENT_CHANGE)

    return {
        "org_id": org_id,
        "consentement_dataconnect_global": org.consentement_dataconnect_global,
        "consentement_grdf_global": org.consentement_grdf_global,
        "cgu_version": cgu_version,
        "updated_at": now.isoformat(),
        "cascade": cascade_results,
    }


@router.patch("/delivery_points/{dp_id}/consentement-local")
def patch_delivery_point_consentement_local(
    dp_id: int,
    payload: DeliveryPointConsentementLocalPatch,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Sprint C-7 Phase 7.3 (ADR-019) — PATCH override local DP RGPD.

    Cohérent ADR-007 Option B archi-helios (Phase 4.5) : override local préservé,
    pas de propagation physique vers global Org. Helper `get_effective_consent`
    runtime calcule le consentement effectif (lecture seule).

    Org-scoping strict via JOIN chain DP → Site → Portefeuille → EntiteJuridique.organisation_id.
    """
    resolved_org_id = resolve_org_id(request, auth, db)

    # Vérifier que le DP appartient bien à l'org scope (anti-IDOR cross-tenant)
    dp = (
        db.query(DeliveryPoint)
        .join(Site, DeliveryPoint.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(
            DeliveryPoint.id == dp_id,
            EntiteJuridique.organisation_id == resolved_org_id,
            not_deleted(DeliveryPoint),
        )
        .first()
    )
    if not dp:
        raise HTTPException(
            status_code=404,
            detail="Delivery point introuvable ou hors scope organisation",
        )

    now = datetime.now(timezone.utc)
    user_id = auth.user_id if auth and getattr(auth, "user_id", None) else None
    cgu_version = payload.cgu_version

    if payload.consentement_dataconnect_local is not None:
        dp.consentement_dataconnect_local = payload.consentement_dataconnect_local
        dp.consentement_dataconnect_local_at = now
        dp.consentement_dataconnect_local_by = user_id
        dp.consentement_dataconnect_local_cgu_version = cgu_version

    if payload.consentement_grdf_local is not None:
        dp.consentement_grdf_local = payload.consentement_grdf_local
        dp.consentement_grdf_local_at = now
        dp.consentement_grdf_local_by = user_id
        dp.consentement_grdf_local_cgu_version = cgu_version

    db.commit()
    db.refresh(dp)

    # Phase 7.4 préparation : wiring AuditLog log_consent_change scope="local"

    return {
        "dp_id": dp_id,
        "consentement_dataconnect_local": dp.consentement_dataconnect_local,
        "consentement_grdf_local": dp.consentement_grdf_local,
        "cgu_version": cgu_version,
        "updated_at": now.isoformat(),
    }
