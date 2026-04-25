"""
PROMEOS Sol — Router /api/sol/proposal.

GET /api/sol/proposal
    Retourne le plan d'action prescriptif Sol pour le scope de l'utilisateur :
    headline 1 phrase chiffrée + 3 actions max (impact €/an, ROI, délai, source).

Scope :
    - auth.org_id en priorité (multi-tenant)
    - X-Org-Id header en fallback (DEMO_MODE)
    - Resolved via services.scope_utils.resolve_org_id (canonique)

Performance :
    - Une seule passe DB (sites scope + ActionPlanItem ouverts)
    - Pas de calcul métier inventé : lit ce que les moteurs amont ont produit
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id

from .schemas import PeerComparison, SolProposal
from .service import ProposalService


router = APIRouter(prefix="/api/sol", tags=["Sol"])


@router.get("/proposal", response_model=SolProposal)
def get_sol_proposal(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Plan d'action prescriptif Sol pour le scope courant.

    Retourne au maximum 3 actions chiffrées (€/an), triées par sévérité × impact
    descendant. Source canonique : ActionPlanItem ouverts + fallback sur
    Site.statut_decret_tertiaire pour assurer un payload non vide en démo.
    """

    effective_org_id = resolve_org_id(request, auth, db)
    site_ids = auth.site_ids if auth and auth.site_ids else None

    service = ProposalService(db)
    proposal = service.build_proposal(
        org_id=effective_org_id,
        site_ids=site_ids,
    )
    return proposal


@router.get("/peer-comparison", response_model=PeerComparison)
def get_peer_comparison(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Comparaison tarifaire org vs pairs sectoriels (€/kWh moyen).

    Wedge anti-fournisseur PROMEOS « tout sauf la fourniture » : prouve au
    client qu'il surpaye vs benchmark archétype NAF. Sources : OID/CEREN
    benchmarks B2B + Observatoire CRE T4. Aggregation factures sur scope.
    """

    effective_org_id = resolve_org_id(request, auth, db)
    site_ids = auth.site_ids if auth and auth.site_ids else None

    service = ProposalService(db)
    return service.build_peer_comparison(
        org_id=effective_org_id,
        site_ids=site_ids,
    )
