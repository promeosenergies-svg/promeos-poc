"""Cascade routes — Sprint C-1 Phase 6.

Endpoint preview pour cascade_recompute_service (dry-run uniquement).
Le wiring PATCH /api/sites/{id} → cascade_recompute_on_change(persist=True)
est reporté en Sprint C-2 (FE cleanup + temporalité).
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth


router = APIRouter(prefix="/api/v1", tags=["cascade-impact"])


# Champs Site supportés en cascade preview MVP Sprint C-1.
# Mapping field name → expected Python type pour coercion server-side.
_ALLOWED_FIELDS_TYPED: dict[str, type] = {
    "code_postal": str,
    "altitude_m": int,
    "tertiaire_area_m2": int,
    "parking_area_m2": int,
    "roof_area_m2": int,
    "operat_sous_categorie_id": str,
}


def _coerce_value(field_name: str, raw: str) -> Any:
    """Coerce string value selon type attendu pour le field."""
    expected = _ALLOWED_FIELDS_TYPED.get(field_name)
    if expected is None:
        return raw
    if raw in ("", "null", "None"):
        return None
    try:
        if expected is int:
            return int(raw)
        if expected is float:
            return float(raw)
        return str(raw)
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de convertir '{raw}' en {expected.__name__} pour {field_name}: {e}",
        )


@router.get("/sites/{site_id}/cascade-impact")
def preview_cascade_impact(
    site_id: int,
    request: Request,
    field: str = Query(..., description="Field à prévisualiser (ex: 'code_postal', 'altitude_m')"),
    new_value: str = Query(..., description="Nouvelle valeur en string (coerce server-side)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Preview cascade SANS écriture DB.

    Use case : tooltip UI affiche les recalculs cascadants si l'utilisateur
    valide la modification du champ (ex: "Si tu changes 75001 → 06000 :
    nouvelle zone H3, nouveau Cabs 90 kWh/m²/an, compliance score recalculé").

    Org-scopé : le site doit appartenir à l'org de l'utilisateur authentifié.
    Dry-run only : aucune écriture DB (le wiring PATCH /api/sites est Sprint C-2).

    Champs supportés MVP : code_postal, altitude_m, tertiaire_area_m2,
    parking_area_m2, roof_area_m2, operat_sous_categorie_id.

    Erreurs :
    - 400 : field hors whitelist ou coercion impossible
    - 404 : site introuvable ou hors org
    """
    if field not in _ALLOWED_FIELDS_TYPED:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "FIELD_NOT_SUPPORTED",
                "message": f"Field '{field}' non supporté pour cascade preview MVP",
                "supported_fields": list(_ALLOWED_FIELDS_TYPED.keys()),
            },
        )

    from models import EntiteJuridique, Portefeuille, Site, not_deleted
    from regops.services.cascade_recompute_service import cascade_impact_preview
    from services.scope_utils import resolve_org_id

    org_id = resolve_org_id(request, auth, db)

    # Org-scoping via Site → Portefeuille → EntiteJuridique → Organisation
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

    coerced_value = _coerce_value(field, new_value)
    field_full = f"Site.{field}"

    # Sprint C-2 Phase 1.3 : propager contexte audit (correlation_id/ip/user_agent)
    correlation_id = request.headers.get("X-Correlation-ID") if request else None
    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    user_id = getattr(auth, "user_id", None) if auth else None

    result = cascade_impact_preview(
        db,
        site,
        field_full,
        coerced_value,
        user_id=user_id,
        org_id=org_id,
        correlation_id=correlation_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return result.to_dict()
