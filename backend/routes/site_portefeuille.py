"""Site portefeuille transfer routes — Sprint C-2 Phase 2.

Endpoint `PATCH /api/v1/sites/{site_id}/portefeuille` (org-scopé).

Transfère un site vers un autre portefeuille de la MÊME EJ. Audit log automatique
via audit_log_service. Cross-EJ transfer rejected (422).

Cohérence URL avec Phase 6 cascade-impact + Phase 1.4 production-ready-status.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth


router = APIRouter(prefix="/api/v1", tags=["site-portefeuille-transfer"])


class PortefeuilleTransferRequest(BaseModel):
    """Body PATCH /api/v1/sites/{id}/portefeuille."""

    new_portefeuille_id: int = Field(..., description="ID du portefeuille cible (même EJ)")
    raison: Optional[str] = Field(None, max_length=500, description="Raison de la bascule (libre)")


def _serialize_history_entry(entry) -> dict[str, Any]:
    """Sérialise une SitePortefeuilleHistory en dict JSON-safe."""

    def _iso(dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None

    return {
        "id": entry.id,
        "site_id": entry.site_id,
        "portefeuille_id": entry.portefeuille_id,
        "valid_from": _iso(entry.valid_from),
        "valid_to": _iso(entry.valid_to),
        "transferred_by_user_id": entry.transferred_by_user_id,
        "raison": entry.raison,
        "metadata_json": entry.metadata_json,
    }


@router.patch("/sites/{site_id}/portefeuille")
def transfer_site_portefeuille(
    site_id: int,
    body: PortefeuilleTransferRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Bascule un site vers un nouveau portefeuille de la MÊME EJ.

    Audit log automatique via audit_log_service.log_patrimoine_change.

    Org-scoping P0 :
    - Site doit appartenir à l'org de l'utilisateur authentifié
    - Portefeuille cible doit appartenir à la même org

    Erreurs :
    - 404 SITE_INTROUVABLE : site introuvable ou hors org
    - 404 PORTEFEUILLE_INTROUVABLE : portefeuille cible introuvable ou hors org
    - 422 CROSS_EJ_TRANSFER_FORBIDDEN : tentative bascule cross-EJ
    """
    from models import EntiteJuridique, Portefeuille, Site, not_deleted
    from services.scope_utils import resolve_org_id
    from services.site_portefeuille_service import (
        CrossEjTransferError,
        PortefeuilleNotFoundError,
        SiteNotFoundError,
        transfer_site_to_portefeuille,
    )

    org_id = resolve_org_id(request, auth, db)

    # Org-scoping site source
    site = (
        db.query(Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(
            Site.id == site_id,
            EntiteJuridique.organisation_id == org_id,
            not_deleted(Site),
        )
        .first()
    )
    if not site:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "SITE_INTROUVABLE",
                "message": "Site introuvable ou hors périmètre de l'organisation",
            },
        )

    # ⚠️ Org-scoping portefeuille cible (P0 sécurité — pas de leak vers autre org)
    new_portef = (
        db.query(Portefeuille)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(
            Portefeuille.id == body.new_portefeuille_id,
            EntiteJuridique.organisation_id == org_id,
        )
        .first()
    )
    if not new_portef:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "PORTEFEUILLE_INTROUVABLE",
                "message": "Portefeuille cible introuvable ou hors périmètre de l'organisation",
            },
        )

    correlation_id = request.headers.get("X-Correlation-ID")
    user_id = getattr(auth, "user_id", None) if auth else None

    try:
        history_entry = transfer_site_to_portefeuille(
            db,
            site_id=site_id,
            new_portefeuille_id=body.new_portefeuille_id,
            user_id=user_id,
            org_id=org_id,
            correlation_id=correlation_id,
            raison=body.raison,
        )
    except CrossEjTransferError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "CROSS_EJ_TRANSFER_FORBIDDEN", "message": str(e)},
        )
    except (SiteNotFoundError, PortefeuilleNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    db.commit()
    db.refresh(history_entry)
    return _serialize_history_entry(history_entry)


@router.get("/sites/{site_id}/portefeuille-history")
def get_site_portefeuille_history(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Retourne l'historique complet des bascules portefeuille pour un site.

    Org-scopé. Trié par valid_from desc (plus récent en premier).
    """
    from models import EntiteJuridique, Portefeuille, Site, not_deleted
    from services.scope_utils import resolve_org_id
    from services.site_portefeuille_service import get_site_history

    org_id = resolve_org_id(request, auth, db)

    site = (
        db.query(Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(
            Site.id == site_id,
            EntiteJuridique.organisation_id == org_id,
            not_deleted(Site),
        )
        .first()
    )
    if not site:
        raise HTTPException(
            status_code=404,
            detail={"error": "SITE_INTROUVABLE", "message": "Site introuvable ou hors périmètre"},
        )

    history = get_site_history(db, site_id)
    return [_serialize_history_entry(e) for e in history]
