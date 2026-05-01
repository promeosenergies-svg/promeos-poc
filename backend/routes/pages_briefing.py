"""Pages briefing endpoint — récit éditorial Sol §5.

ADR-001 grammaire Sol industrialisée : un seul endpoint par page Sol.
MVP Sprint 1.1 : `cockpit_daily` uniquement. S1.2-S1.3 étendra aux autres.

Convention API Sol : retour `{ data, provenance }` standardisé via
`with_provenance()` (cf services/data_provenance/).

Doctrine §8.1 règle d'or : aucun calcul métier ici. Le router délègue
intégralement à `narrative_generator.generate_page_narrative()`.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from models import EntiteJuridique, Organisation, Portefeuille, Site, not_deleted
from services.data_provenance import with_provenance
from services.narrative import generate_page_narrative
from services.scope_utils import resolve_org_id

_logger = logging.getLogger("promeos.pages_briefing")

router = APIRouter(prefix="/api/pages", tags=["pages-briefing"])


# Liste des page_keys actuellement supportés. Étendre au fur et à mesure
# que les builders sont ajoutés dans `narrative_generator._BUILDERS`.
SUPPORTED_PAGE_KEYS = {
    "cockpit_daily",
    "cockpit_comex",
    "patrimoine",
    "conformite",
    "bill_intel",
    "achat_energie",
    "monitoring",
    "diagnostic",
    "anomalies",
    "flex",
}


@router.get("/{page_key}/briefing")
def get_page_briefing(
    page_key: str,
    request: Request,
    persona: str = "daily",
    archetype: Optional[str] = None,
    simulate_date: Optional[str] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Retourne le récit éditorial complet d'une page Sol.

    Args:
        page_key : identifiant page Sol canonique (cf SUPPORTED_PAGE_KEYS).
        persona  : "daily" (Marie 8h45) ou "comex" (Jean-Marc CFO).
        archetype: Sprint 3 chantier β — branchement multi-archetype.
        simulate_date: Phase 6 — date ISO 8601 (YYYY-MM-DD) pour simuler
            la narrative comme si on était à cette date. Override le
            `datetime.now()` interne du builder (kicker week_iso, deltas
            S-1, etc.). Si None, on utilise la date courante. Format
            invalide → 400.

    Response:
        { data: Narrative, provenance: { source, confidence, updated_at } }
    """
    if page_key not in SUPPORTED_PAGE_KEYS:
        raise HTTPException(
            status_code=404,
            detail=(
                f"page_key='{page_key}' non supporté. "
                f"Pages disponibles MVP Sprint 1.1 : {sorted(SUPPORTED_PAGE_KEYS)}. "
                f"Sprint 1.2+ étendra aux 9 autres pages Sol."
            ),
        )

    if persona not in ("daily", "comex"):
        raise HTTPException(
            status_code=400,
            detail=f"persona='{persona}' invalide. Valeurs : 'daily' (Marie) | 'comex' (Jean-Marc).",
        )

    # Phase 6 — Parse simulate_date si fourni (ISO 8601 strict).
    # Phase 7 correctif A audit P0 — bornes 1970 ≤ year ≤ now+1 an
    # (anti-DoS doux + anti-week_iso aberrant en démo).
    simulated_now = None
    if simulate_date:
        from datetime import datetime as _dt
        from datetime import timezone as _tz

        try:
            parsed = _dt.fromisoformat(simulate_date)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"simulate_date='{simulate_date}' invalide. "
                    f"Format attendu : ISO 8601 (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)."
                ),
            )
        # Normaliser en UTC-aware pour cohérence avec datetime.now(timezone.utc)
        simulated_now = parsed if parsed.tzinfo else parsed.replace(tzinfo=_tz.utc)
        # Borne anti-abus (Phase 7 correctif audit)
        _now_utc = _dt.now(_tz.utc)
        _max_year = _now_utc.year + 1
        if simulated_now.year < 1970 or simulated_now.year > _max_year:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"simulate_date={simulate_date} hors plage autorisée "
                    f"(année 1970 ≤ X ≤ {_max_year}). Évite les week_iso aberrants "
                    f"et les abus de cache."
                ),
            )

    effective_org_id = resolve_org_id(request, auth, db)
    org = db.query(Organisation).filter(Organisation.id == effective_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    # Sites du scope org pour densification narrative.
    # Note S1.5bis : trade-off assumé — `count()` léger ici + `.all()` dans
    # le builder via `_load_org_context()`. La factorisation `org_context=ctx`
    # paramétrable demanderait de refactorer les 5 signatures builders pour
    # un gain perf marginal (count est trivial). À reconsidérer S2 si la
    # liste de pages_briefing devient un hot-path.
    sites_count = (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == effective_org_id)
        .count()
    )

    # Phase 7 correctif C — extraire user info depuis auth context pour
    # mention persona italique. Fallback safe sur None si auth absente
    # (DEMO_MODE lenient) ou user sans prenom — la mention sera omise.
    user_first_name = None
    user_role = None
    if auth and hasattr(auth, "user") and auth.user:
        user_first_name = getattr(auth.user, "prenom", None) or None
    # Mapping persona param → PersonaRole MVP : comex→cfo, daily→energy_manager
    # (DG/asset_manager/owner_commerce/director_erp restent V2 ; le builder
    # tombera sur fallback générique si role inconnu).
    if persona == "comex":
        user_role = "cfo"
    elif persona == "daily":
        user_role = "energy_manager"

    narrative = generate_page_narrative(
        db=db,
        page_key=page_key,
        org_id=effective_org_id,
        org_name=org.nom or "",
        sites_count=sites_count,
        persona=persona,
        archetype=archetype,
        now=simulated_now,
        user_first_name=user_first_name,
        user_role=user_role,
    )

    payload = narrative.to_dict()
    # `provenance` déjà dans narrative.to_dict() — on extrait pour wrappage
    # standard `{ data, provenance }`. payload["provenance"] reste pour
    # rétro-compatibilité éventuelle.
    return with_provenance(payload=payload, provenance=narrative.provenance)
