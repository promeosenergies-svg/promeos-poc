"""
PROMEOS — Endpoint GET /api/regulatory/rates (Sprint C-3 Phase 3.3).

Expose le SoT `backend/config/sources_reglementaires.yaml` au frontend
via API publique (sources réglementaires = données publiques française =
accessibles à tous, pas d'org-scoping requis).

Migre `frontend/src/domain/regulatory_rates.js` (hardcoded 184L) vers
fetch hook `useRegulatoryRates` (Phase 3.3 FE).

Cohérent avec endpoint /api/config/emission-factors existant (config_emission_factors.py).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from config.regulatory_sources_loader import (
    get_term,
    get_terms_by_domain,
    list_all_domains,
    load_regulatory_sources,
)


router = APIRouter(prefix="/api/regulatory", tags=["Regulatory"])

# Phase L33.2 audit fix P0 SECURITY (Reviewer #3 META-AUDIT L33.0) — Statuts
# correspondant à de la doctrine PROMEOS interne NON OPPOSABLE LÉGALEMENT.
# Ces termes (BILL_ANOMALY_*, READINESS_WEIGHT_*, FLEX_HEURISTIC, etc.) ne
# doivent JAMAIS être exposés via l'endpoint public — ce sont les heuristiques
# qui constituent le différenciateur compétitif PROMEOS Sol §15.
# Un concurrent (Deepki/Metron) pourrait reverse-engineer la doctrine.
_INTERNAL_PROMEOS_STATUSES = frozenset({"internal_doctrine", "internal_heuristic", "internal_fallback"})


def _filter_public_terms(terms: dict) -> dict:
    """Phase L33.2 — Filtre les termes publics (status verified/pending/observatory).

    Exclut les termes status: internal_* qui exposeraient la doctrine PROMEOS
    interne (heuristiques détecteur factures R19→R31, pondérations scoring).

    Convention : status absent = équivalent verified implicite (cf. header YAML
    sources_reglementaires.yaml). Ces termes sont donc inclus dans le filtrage
    public (cohérent avec SG_REG_YAML_07-12).
    """
    return {term_id: term for term_id, term in terms.items() if term.get("status") not in _INTERNAL_PROMEOS_STATUSES}


@router.get("/rates")
def get_regulatory_rates(
    domain: Optional[str] = Query(
        None,
        description="Filtre par domaine (co2, tarifs, accises, tva, dt, bacs, aper, audit_sme, operat).",
    ),
    term_id: Optional[str] = Query(
        None,
        description="Filtre par term_id spécifique (ex: CO2_FACTOR_ELEC_KGCO2_PER_KWH).",
    ),
) -> dict:
    """Récupère les sources réglementaires PROMEOS depuis le SoT YAML versionné git.

    Modes (mutuellement exclusifs en pratique) :
    - **Sans paramètre** : retourne tout le YAML (version + last_updated + 68 termes).
    - **`?domain=co2`** : retourne uniquement les termes du domaine.
    - **`?term_id=...`** : retourne 1 seul terme.

    Endpoint public (pas d'org-scoping) : sources réglementaires françaises
    accessibles à tous. Cohérent avec /api/config/emission-factors.

    Source : backend/config/sources_reglementaires.yaml (Sprint C-3 Phase 3.2).

    Réponse selon mode :
    - sans filtre : `{ version, last_updated, sprint_origin, terms: {...} }`
    - domain : `{ domain, terms: {...} }`
    - term_id : `{ term_id, term: {...} }`
    """
    # Mode 1 : term_id spécifique → 1 seul term
    if term_id:
        try:
            term = get_term(term_id)
            # Phase L33.2 — refus 404 si term internal_doctrine (fuite doctrine PROMEOS)
            if term.get("status") in _INTERNAL_PROMEOS_STATUSES:
                raise HTTPException(
                    status_code=404,
                    detail=f"Term {term_id!r} introuvable ou non public.",
                )
            return {"term_id": term_id, "term": term}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Mode 2 : filtre par domaine → tous les termes du domaine (filtrés public)
    if domain:
        terms = get_terms_by_domain(domain)
        if not terms:
            valid_domains = list_all_domains()
            raise HTTPException(
                status_code=404,
                detail=(f"Domaine inconnu ou vide : {domain!r}. Domaines disponibles : {valid_domains}"),
            )
        # Phase L33.2 audit fix P0 SECURITY — filtre internal_doctrine
        public_terms = _filter_public_terms(terms)
        return {"domain": domain, "terms": public_terms}

    # Mode 3 : sans filtre → tout le YAML (filtré public)
    # Phase L33.2 audit fix P0 SECURITY — exclusion termes internal_doctrine/heuristic/fallback.
    # CRITICAL : copie superficielle obligatoire pour éviter de muter le cache lru_cache
    # partagé par list_all_domains() / get_terms_by_domain() / get_term().
    cached_yaml = load_regulatory_sources()
    return {**cached_yaml, "terms": _filter_public_terms(cached_yaml.get("terms", {}))}


@router.get("/domains")
def get_regulatory_domains() -> dict:
    """Liste tous les domaines disponibles dans le SoT (utile UI de filtre)."""
    return {"domains": list_all_domains()}
