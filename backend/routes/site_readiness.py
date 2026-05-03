"""Site readiness routes — Sprint C-2 Phase 1.4.

Endpoint `/api/v1/sites/{site_id}/production-ready-status` (org-scopé).
Cohérence URL avec endpoint cascade Phase 6 Sprint C-1
(`/api/v1/sites/{site_id}/cascade-impact`).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth


router = APIRouter(prefix="/api/v1", tags=["site-readiness"])


@router.get("/sites/{site_id}/production-ready-status")
def get_site_production_ready_status(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Vérifie si un site est prêt pour production (7 checks matrice v1 §9.2).

    Source : matrice v1 §9.2 + doctrine PROMEOS Sol §9.

    7 checks :
    1. Hiérarchie complète Org → EJ → Portefeuille → Site
    2. Champs P0 site complets (8 champs : nom, adresse, code_postal, ville,
       tertiaire_area_m2, altitude_m, operat_sous_categorie_id, ...)
    3. Au moins 1 bâtiment avec surface > 0 + Site.operat_sous_categorie_id déclarée
    4. Au moins 1 compteur déclaré
    5. Au moins 1 contrat actif lié à un DeliveryPoint du site
    6. Compliance score calculable (V2 wrapper Phase 5 — NON_APPLICABLE accepté)
    7. Cabs 2030 calculable SI DT assujetti (sinon non requis = passe par défaut)

    Org-scopé : le site doit appartenir à l'org de l'utilisateur authentifié.

    Erreurs :
    - 404 : site introuvable ou hors périmètre de l'organisation
    """
    from models import EntiteJuridique, Portefeuille, Site, not_deleted
    from services.scope_utils import resolve_org_id
    from services.site_readiness_service import is_site_production_ready

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
            detail={
                "error": "SITE_INTROUVABLE",
                "message": "Site introuvable ou hors périmètre de l'organisation",
            },
        )

    result = is_site_production_ready(db, site_id)
    return result.to_dict()
