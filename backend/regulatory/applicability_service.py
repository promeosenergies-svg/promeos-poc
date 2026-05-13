"""PROMEOS — Service unique du moteur d'assujettissement v1.0.

Référence : `docs/adr/ADR-024-moteur-assujettissement.md` §2 + §6.

Expose deux fonctions cardinales :
    compute_applicability(db, org_id, site_ids=None)
        → dict[RuleCode → list[RuleApplicability]] couvrant les 5 règles v1.0
    compute_patrimoine_maturity(db, org_id)
        → float ∈ [0.0, 1.0] : ratio de champs critiques renseignés

Discipline d'import (décision Phase 0 Q2 Amine) :
    Le legacy `services.compliance_readiness_service.compute_applicability`
    (schema dict[str, dict]) NE doit PAS être consommé par ce service.
    La cohabitation se fait par chemin distinct.

Note : ce service est conçu pour scope multi-sites. Pour un site unique,
passer `site_ids=[id]`.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from regulatory.applicability_types import (
    ApplicabilityStatus,
    RuleApplicability,
    RuleCode,
)
from regulatory.rules_catalog import RULE_EVALUATORS


_logger = logging.getLogger(__name__)


# Champs critiques pris en compte pour le score `patrimoine_maturity`.
# Modifier ce set passe par ADR (le seuil DATA_INSUFFICIENT du mode dispatcher
# en dépend, cf. Vague B).
_SITE_CRITICAL_FIELDS: tuple[str, ...] = (
    "tertiaire_area_m2",
    "usage_principal",
    "parking_area_m2",
    "roof_area_m2",
)
_ORG_CRITICAL_FIELDS: tuple[str, ...] = (
    "effectif_total",
    "chiffre_affaires_eur",
)
_BATIMENT_CRITICAL_FIELDS: tuple[str, ...] = ("cvc_power_kw",)


def compute_applicability(
    db: Session,
    org_id: int,
    site_ids: list[int] | None = None,
) -> dict[RuleCode, list[RuleApplicability]]:
    """Évalue l'applicabilité des 5 règles v1.0 pour une organisation.

    Args:
        db: Session SQLAlchemy.
        org_id: identifiant de l'organisation cible.
        site_ids: filtre optionnel sur un sous-ensemble de sites de l'org.

    Returns:
        dict[RuleCode → list[RuleApplicability]].
        - Règles site-scoped (DT, BACS, APER) : une entrée par site.
        - Règles org-scoped (SMÉ, BEGES) : une entrée unique avec
          scope_id = org_id.
    """
    sites = _load_sites(db, org_id, site_ids)
    organisation = _load_organisation(db, org_id)
    audit_sme = _load_audit_sme(db, org_id)

    result: dict[RuleCode, list[RuleApplicability]] = {r: [] for r in RuleCode}

    # Fix code-reviewer P1-B 13/05/2026 : utilisation des singletons
    # RULE_EVALUATORS (SoT unique) au lieu d'instances locales (était 3
    # instanciations parasites par appel + double source de vérité).

    # ── Règles site-scoped ──────────────────────────────────────────────
    for site in sites:
        batiments = _load_batiments_for_site(db, site)
        result[RuleCode.DT].append(RULE_EVALUATORS[RuleCode.DT].evaluate(site))
        result[RuleCode.BACS].append(RULE_EVALUATORS[RuleCode.BACS].evaluate(site, batiments))
        result[RuleCode.APER].append(RULE_EVALUATORS[RuleCode.APER].evaluate(site))

    # ── Règles org-scoped ──────────────────────────────────────────────
    if organisation is not None:
        result[RuleCode.SME].append(RULE_EVALUATORS[RuleCode.SME].evaluate(organisation, audit_sme))
        result[RuleCode.BEGES].append(RULE_EVALUATORS[RuleCode.BEGES].evaluate(organisation))

    return result


def compute_patrimoine_maturity(db: Session, org_id: int) -> float:
    """Renvoie un score 0.0..1.0 = % de champs critiques renseignés.

    Champs critiques (poids égaux v1.0) :
        Organisation : effectif_total, chiffre_affaires_eur
        Site         : tertiaire_area_m2, usage_principal, parking_area_m2,
                       roof_area_m2
        Batiment     : cvc_power_kw

    Args:
        db: Session SQLAlchemy.
        org_id: identifiant de l'organisation cible.

    Returns:
        ratio ∈ [0.0, 1.0]. 0.0 si aucun champ ne peut être évalué.
    """
    sites = _load_sites(db, org_id, None)
    organisation = _load_organisation(db, org_id)

    fields_checked = 0
    fields_present = 0

    # ── Organisation ───────────────────────────────────────────────────
    if organisation is not None:
        for fname in _ORG_CRITICAL_FIELDS:
            fields_checked += 1
            if getattr(organisation, fname, None) is not None:
                fields_present += 1

    # ── Sites + Bâtiments ─────────────────────────────────────────────
    for site in sites:
        for fname in _SITE_CRITICAL_FIELDS:
            fields_checked += 1
            if getattr(site, fname, None) is not None:
                fields_present += 1
        for batiment in _load_batiments_for_site(db, site):
            for fname in _BATIMENT_CRITICAL_FIELDS:
                fields_checked += 1
                if getattr(batiment, fname, None) is not None:
                    fields_present += 1

    if fields_checked == 0:
        return 0.0
    return round(fields_present / fields_checked, 4)


def count_unknown_or_missing(
    applicability: dict[RuleCode, list[RuleApplicability]],
) -> tuple[int, int]:
    """Helper utilisé par le mode dispatcher (Vague B).

    Returns:
        (total_entries, unknown_or_missing_entries)
    """
    total = 0
    bad = 0
    for entries in applicability.values():
        for entry in entries:
            total += 1
            if entry.status in (
                ApplicabilityStatus.UNKNOWN,
                ApplicabilityStatus.DATA_MISSING,
            ):
                bad += 1
    return total, bad


# ── Chargement modèles (lecture seule, aucun side-effect) ─────────────


def _load_sites(db: Session, org_id: int, site_ids: list[int] | None) -> list[Any]:
    """Charge les sites de l'org via `sites_for_org_query` (helper canonique).

    Le helper applique le filtre cardinal `Site.is_demo == Organisation.is_demo`
    (Correctif F.4 ff2b3a4d) et joint Portefeuille → EntiteJuridique → Organisation.
    """
    try:
        from models.site import Site
        from services.scope_utils import sites_for_org_query
    except Exception as exc:  # pragma: no cover — defensive
        _logger.warning("Impossible d'importer sites_for_org_query: %s", exc)
        return []

    query = sites_for_org_query(db, org_id)
    if site_ids is not None:
        query = query.filter(Site.id.in_(site_ids))
    return list(query.all())


def _load_organisation(db: Session, org_id: int) -> Any:
    try:
        from models.organisation import Organisation
    except Exception as exc:  # pragma: no cover — defensive
        _logger.warning("Impossible d'importer models.Organisation: %s", exc)
        return None
    return db.query(Organisation).filter(Organisation.id == org_id).first()


def _load_audit_sme(db: Session, org_id: int) -> Any:
    """Charge le dernier AuditSME de l'org (pour critère conso SMÉ)."""
    try:
        from models.audit_sme import AuditSME
    except Exception as exc:  # pragma: no cover
        _logger.warning("Impossible d'importer models.AuditSME: %s", exc)
        return None
    return db.query(AuditSME).filter(AuditSME.organisation_id == org_id).order_by(AuditSME.id.desc()).first()


def _load_batiments_for_site(db: Session, site: Any) -> list[Any]:
    """Charge les bâtiments d'un site (via relation `site.batiments`)."""
    if hasattr(site, "batiments"):
        rel = site.batiments
        # SQLAlchemy peut renvoyer une AppenderQuery (lazy="dynamic") ou une list
        if hasattr(rel, "all"):
            return list(rel.all())
        return list(rel)
    return []
