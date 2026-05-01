"""Typology resolver scope-dynamique (org/site/portfolio).

Sprint Refonte Narrative dynamique — Phase 1.2 (2026-05-01).

Résout la typologie organisationnelle PROMEOS Sol2 selon le scope d'une
narrative :

- **scope site** (`{"site_id": X}`) : typologie du site spécifique. Permet
  drill-down (ex: depuis vue HELIOS, cliquer sur Hôtel Nice → narrative
  COMMERCE adaptée hôtellerie).
- **scope org** (`{"org_id": Y}`) : typologie dominante de l'org calculée
  selon **Option A** (Amine 2026-05-01) — pondération par surface,
  **UNKNOWN exclu du calcul**.
- **scope portfolio** (`{"portfolio_id": Z}`) : idem org mais filtré
  portefeuille.

## Option A — règle de calcul typologie dominante org

Décision Amine 2026-05-01 (cadrage Phase 1.2) :

> Pour le typology_resolver scope-dynamique : appliquer Option A pour le
> calcul de typologie dominante org. UNKNOWN exclu du calcul. Si la part
> UNKNOWN dépasse 30 % de la surface, ajouter un log warning visible.
> Documenter dans le code que c'est intentionnel et que la couverture
> sera étendue en V2 (PME tertiaire + Industrie).

**Implication runtime HELIOS** :

| Site | Surface | NAF | Typologie |
|---|---:|---|---|
| Siège Paris | 3 500 m² | 6820B | GRAND_GROUPE |
| Bureau Lyon | 1 200 m² | 6820B | GRAND_GROUPE |
| Entrepôt Toulouse | 6 000 m² | 5210B | **UNKNOWN** (entreposage 52 hors MVP) |
| Hôtel Nice | 4 000 m² | 5510Z | COMMERCE |
| École Marseille | 2 800 m² | 8520Z | ERP |
| **Total** | **17 500 m²** | | |

UNKNOWN = 6 000 m² / 17 500 m² = **34,3 %** → WARNING log.

Calcul dominant en excluant UNKNOWN (surface utile 11 500 m²) :
- GRAND_GROUPE : 4 700 / 11 500 = **41 %** ← dominant
- COMMERCE : 4 000 / 11 500 = 35 %
- ERP : 2 800 / 11 500 = 24 %

→ HELIOS scope org → **GRAND_GROUPE**.

## V2 (Sprint Q3 2026)

Ajout des typologies PME_TERTIAIRE et INDUSTRIE :
- Préfixes 49-53 (transport/entreposage) → PME_TERTIAIRE ou INDUSTRIE
- Préfixes 10-33 (industrie manufacturière) → INDUSTRIE
- Réduction attendue de la part UNKNOWN < 5 % en moyenne portefeuille

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 1.2.
"""

from __future__ import annotations

import logging
from typing import Optional, TypedDict

from sqlalchemy.orm import Session

from doctrine.naf_to_typology import OrganizationTypology, resolve_typology
from models import EntiteJuridique, Portefeuille, Site, not_deleted

_logger = logging.getLogger("promeos.narrative.typology_resolver")

# Seuil au-delà duquel on émet un warning sur la couverture UNKNOWN.
# Valeur tranchée Amine 2026-05-01 (Phase 1.2 cadrage) : 30 %.
# À monitorer en prod : si on observe ce warning fréquemment, c'est le
# signal qu'il faut prioriser V2 (PME tertiaire + Industrie).
UNKNOWN_SURFACE_WARNING_THRESHOLD_PCT = 30.0


class NarrativeScope(TypedDict, total=False):
    """Scope canonique d'une narrative.

    Au moins une clé doit être présente : `site_id`, `org_id` ou
    `portfolio_id`. Si plusieurs sont présentes, l'ordre de priorité est
    `site_id > portfolio_id > org_id` (du plus spécifique au plus large).
    """

    site_id: int
    org_id: int
    portfolio_id: int


def _typology_dominant_for_sites(
    sites: list[Site],
    scope_label: str = "scope",
) -> OrganizationTypology:
    """Calcule la typologie dominante d'un ensemble de sites — Option A.

    Règle Option A (Amine 2026-05-01) :
    1. Calculer la surface par typologie.
    2. **Exclure UNKNOWN** du calcul.
    3. Retourner la typologie avec la plus grande surface (hors UNKNOWN).
    4. Si UNKNOWN > 30 % de la surface totale → log warning.
    5. Si après exclusion il ne reste rien (100 % UNKNOWN) → retourner UNKNOWN.

    Args:
        sites: liste de Site (déjà filtrés `deleted_at IS NULL`).
        scope_label: label utilisé dans les logs (`"org_id=1"`, etc.).

    Returns:
        OrganizationTypology dominante (hors UNKNOWN si possible).
    """
    if not sites:
        return OrganizationTypology.UNKNOWN

    surface_by_typology: dict[OrganizationTypology, float] = {}
    total_surface = 0.0
    for site in sites:
        typology = resolve_typology(site.naf_code)
        surface = float(site.surface_m2 or 0.0)
        surface_by_typology[typology] = surface_by_typology.get(typology, 0.0) + surface
        total_surface += surface

    # Si surface totale = 0 (sites sans surface_m2 renseigné), pas de calcul
    # pondéré possible — fallback compte simple.
    if total_surface <= 0:
        # Compte par occurrence, exclut UNKNOWN
        counts = {}
        for site in sites:
            typo = resolve_typology(site.naf_code)
            if typo != OrganizationTypology.UNKNOWN:
                counts[typo] = counts.get(typo, 0) + 1
        if not counts:
            return OrganizationTypology.UNKNOWN
        return max(counts, key=counts.get)

    # Warning si UNKNOWN > seuil — signal pour prioriser V2.
    unknown_surface = surface_by_typology.get(OrganizationTypology.UNKNOWN, 0.0)
    unknown_pct = (unknown_surface / total_surface) * 100
    if unknown_pct > UNKNOWN_SURFACE_WARNING_THRESHOLD_PCT:
        _logger.warning(
            "[%s] couverture typologie UNKNOWN = %.1f %% surface (>%.0f %% seuil). "
            "Sites NAF non mappés : %s. Couverture étendue prévue V2 (PME tertiaire + Industrie).",
            scope_label,
            unknown_pct,
            UNKNOWN_SURFACE_WARNING_THRESHOLD_PCT,
            [s.nom for s in sites if resolve_typology(s.naf_code) == OrganizationTypology.UNKNOWN][
                :5
            ],  # limit 5 noms pour log lisibilité
        )

    # Option A : calcul dominant EXCLUANT UNKNOWN
    surface_excl_unknown = {
        typo: surf for typo, surf in surface_by_typology.items() if typo != OrganizationTypology.UNKNOWN
    }
    if not surface_excl_unknown:
        # 100 % UNKNOWN — aucune typologie valide à retourner
        return OrganizationTypology.UNKNOWN

    return max(surface_excl_unknown, key=surface_excl_unknown.get)


def _sites_for_org(db: Session, org_id: int) -> list[Site]:
    """Récupère sites actifs d'une org via la chaîne portefeuille → EJ → org."""
    return (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    )


def _sites_for_portfolio(db: Session, portfolio_id: int) -> list[Site]:
    """Récupère sites actifs d'un portefeuille."""
    return not_deleted(db.query(Site), Site).filter(Site.portefeuille_id == portfolio_id).all()


def resolve_typology_for_scope(
    scope: NarrativeScope,
    db: Session,
    user_id: Optional[int] = None,
) -> OrganizationTypology:
    """Résout la typologie selon le scope demandé.

    Ordre de priorité :

    0. **User override** (Phase 1.4) — si `user_id` fourni et que
       `user_preferences.typology_override` est défini, on respecte la
       préférence utilisateur. Permet à un CFO de figer une typologie
       même si l'auto-détection NAF la classe autrement.
    1. `scope["site_id"]` → typologie du site (NAF du site directement).
    2. `scope["portfolio_id"]` → typologie dominante du portefeuille
       (Option A, exclusion UNKNOWN).
    3. `scope["org_id"]` → typologie dominante de l'org (Option A).

    Args:
        scope: dict avec au moins une des 3 clés. Si plusieurs présentes,
            la plus spécifique l'emporte (site > portfolio > org).
        db: session SQLAlchemy.
        user_id: id du user authentifié (optionnel). Si fourni, on
            consulte `user_preferences.typology_override` en priorité.
            En l'absence d'override, la résolution scope reprend la main.

    Returns:
        `OrganizationTypology`. Jamais d'exception ; UNKNOWN en fallback
        si scope invalide ou entité introuvable.

    Examples:
        >>> # Scope HELIOS org → GRAND_GROUPE (Option A, UNKNOWN exclu)
        >>> resolve_typology_for_scope({"org_id": 1}, db)
        <OrganizationTypology.GRAND_GROUPE: 'grand_groupe_tertiaire'>

        >>> # Scope Hôtel Nice site → COMMERCE (NAF 5510Z direct)
        >>> resolve_typology_for_scope({"site_id": 4}, db)
        <OrganizationTypology.COMMERCE: 'commerce'>

        >>> # User override → respecté quel que soit le scope
        >>> resolve_typology_for_scope({"org_id": 1}, db, user_id=42)
        <OrganizationTypology.COMMERCE: 'commerce'>  # si override = COMMERCE
    """
    # 0. Phase 1.4 — User typology_override (priorité absolue).
    # Import depuis services/ (pas routes/) — respect du layering :
    # services ne doivent jamais dépendre de routes.
    if user_id is not None:
        from services.user_preference_service import get_user_typology_override

        override = get_user_typology_override(db, user_id)
        if override is not None:
            _logger.debug(
                "resolve_typology_for_scope: user_id=%s override=%s (scope=%s ignoré)",
                user_id,
                override,
                scope,
            )
            return override

    # 1. site_id (le plus spécifique)
    site_id = scope.get("site_id")
    if site_id is not None:
        site = db.query(Site).filter(Site.id == site_id, Site.deleted_at.is_(None)).first()
        return resolve_typology(site.naf_code if site else None)

    # 2. portfolio_id
    portfolio_id = scope.get("portfolio_id")
    if portfolio_id is not None:
        sites = _sites_for_portfolio(db, portfolio_id)
        return _typology_dominant_for_sites(sites, scope_label=f"portfolio_id={portfolio_id}")

    # 3. org_id
    org_id = scope.get("org_id")
    if org_id is not None:
        sites = _sites_for_org(db, org_id)
        return _typology_dominant_for_sites(sites, scope_label=f"org_id={org_id}")

    # Aucune clé valide → UNKNOWN
    _logger.warning("resolve_typology_for_scope appelé sans site_id/portfolio_id/org_id : %s", scope)
    return OrganizationTypology.UNKNOWN


__all__ = [
    "NarrativeScope",
    "UNKNOWN_SURFACE_WARNING_THRESHOLD_PCT",
    "resolve_typology_for_scope",
]
