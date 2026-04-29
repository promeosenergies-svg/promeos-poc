"""PROMEOS — Cockpit Decisions service (Phase 2.3 Top 3 actions Décision).

Sérialise les actions ouvertes en payload Décision (vue exécutive) selon
contrat doctrine §0.D décision A : tout € exposé doit être traçable
réglementaire (article cité) ou contractuel. Sinon, conversion MWh/an.

Pour chaque action retournée par `/api/cockpit/decisions/top3` :
  - estimated_gain_mwh_year : conversion kWh via DEFAULT_PRICE_ELEC_EUR_KWH
  - reference : CEE BAT-TH-* extrait du title/rationale ou article réglementaire
  - regulatory_penalty_eur : EurAmount typé via build_regulatory si action de
    mise en conformité (source_type='compliance' + severity='critical')
  - title : passé à transform_acronym (Phase 1.8) — zéro acronyme brut

Source-guard : test_actions_decision_show_mwh_or_traced_eur (chaque action
expose soit MWh, soit € avec traceability fields, jamais ni l'un ni l'autre).

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §3.B Phase 2.3.
"""

from __future__ import annotations

import re
from typing import Optional

from sqlalchemy import case
from sqlalchemy.orm import Session

from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH
from doctrine.acronyms import transform_acronym
from doctrine.constants import DT_PENALTY_EUR
from models.action_item import ActionItem
from models.enums import ActionSourceType, Severity


# Constante article DT canonique — single SoT, partagée avec _build_regulatory.
DT_REGULATORY_ARTICLE = "Décret 2019-771 art. 9"

_CEE_PATTERN = re.compile(r"BAT-TH-\d+", re.IGNORECASE)


def _extract_cee_reference(text: Optional[str]) -> Optional[str]:
    """Détecte une référence CEE BAT-TH-NNN dans un texte libre."""
    if not text:
        return None
    match = _CEE_PATTERN.search(text)
    return match.group(0).upper() if match else None


def _enum_str(value) -> str:
    """Normalise un Enum SQLAlchemy ou str ORM en string lowercase.

    ActionItem.severity est `Column(String(20))` — déjà str au runtime.
    ActionItem.source_type est `Column(SAEnum(ActionSourceType))` — instance Enum.
    Cet helper unifie les 2 cas (extraction valid pour comparaison enum.value).
    """
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value).lower()
    return str(value).lower()


def _infer_regulatory_article(action: ActionItem) -> Optional[str]:
    """Détermine l'article réglementaire applicable selon source_type + sévérité.

    Phase 2.3 : règle simple — actions critiques de mise en conformité DT
    sont rattachées à Décret 2019-771 art. 9 (pénalité DT_PENALTY_EUR/site NC).
    Utilise les enums canoniques `ActionSourceType` + `Severity` (P1 audit).
    """
    if (
        _enum_str(action.source_type) == ActionSourceType.COMPLIANCE.value
        and _enum_str(action.severity) == Severity.CRITICAL.value
    ):
        return DT_REGULATORY_ARTICLE
    return None


def serialize_action_for_decision(action: ActionItem, site_name: str = "") -> dict:
    """Sérialise un ActionItem en payload Décision (vue exécutive).

    Doctrine §0.D A : si pas de regulatory_article ni contract_id, le
    montant € est exclu — seul le MWh/an est exposé. Si action de mise
    en conformité, on rattache l'EurAmount via build_regulatory avec
    article cité.

    Args:
        action: ActionItem ORM
        site_name: nom lisible du site (resolved par l'appelant)

    Returns:
        dict avec champs canoniques (cf prompt §3.B Phase 2.3)
    """
    raw_gain = action.estimated_gain_eur or 0
    gain_mwh = round(raw_gain / DEFAULT_PRICE_ELEC_EUR_KWH / 1000) if raw_gain > 0 else 0

    title = transform_acronym(action.title or "")
    cee_ref = _extract_cee_reference(action.title) or _extract_cee_reference(action.rationale)

    regulatory_article = _infer_regulatory_article(action)
    regulatory_penalty: Optional[dict] = None
    if regulatory_article == DT_REGULATORY_ARTICLE:
        # Read-only contract dict aligné Phase 1.1 EurAmount.to_dict_with_proof()
        # (mêmes clés id-less : value_eur, category, regulatory_article, formula_text).
        # Pas de persist DB sur GET (cohérent /simplify Phase 1 P1 EurAmount POST-on-GET).
        regulatory_penalty = {
            "value_eur": float(DT_PENALTY_EUR),
            "category": "calculated_regulatory",
            "regulatory_article": regulatory_article,
            "formula_text": f"{int(DT_PENALTY_EUR)} € pénalité légale annuelle/site",
        }

    return {
        "id": action.id,
        "title": title,
        "narrative": action.rationale or action.description or "",
        "site_id": action.site_id,
        "site": site_name,
        "echeance": action.due_date.isoformat() if action.due_date else None,
        "severity": _enum_str(action.severity),
        "priority": _enum_str(action.priority),
        "estimated_gain_mwh_year": gain_mwh,
        "reference": cee_ref or regulatory_article,
        "regulatory_penalty_eur": regulatory_penalty,
    }


def get_top3_decisions(db: Session, site_ids: list[int]) -> list[dict]:
    """Retourne les 3 actions Top Décision pour la Vue Exécutive.

    Tri : critical → high → medium ; actions avec due_date plus proche
    en premier. Limit 3 max. Si pas d'actions ouvertes → liste vide.
    """
    if not site_ids:
        return []

    # Tri severity SÉMANTIQUE (critical=0 → high=1 → medium=2 → low=3)
    # via SQL CASE — ActionItem.severity est Column(String(20)) donc le
    # tri natif `.desc()` est alphabétique (medium > low > high > critical),
    # ce qui inverse l'ordre attendu. Bug P0 /simplify audit fin Phase 2.
    severity_rank = case(
        {
            Severity.CRITICAL.value: 0,
            Severity.HIGH.value: 1,
            Severity.MEDIUM.value: 2,
            Severity.LOW.value: 3,
        },
        value=ActionItem.severity,
        else_=4,
    )

    rows = (
        db.query(ActionItem)
        .filter(
            ActionItem.site_id.in_(site_ids),
            ActionItem.status.in_(["open", "in_progress"]),
        )
        .order_by(severity_rank.asc(), ActionItem.due_date.asc().nullslast())
        .limit(3)
        .all()
    )

    # Site name resolver — single query
    site_names: dict[int, str] = {}
    if rows:
        from models import Site

        site_ids_used = {a.site_id for a in rows if a.site_id}
        for sid, nom in db.query(Site.id, Site.nom).filter(Site.id.in_(site_ids_used)).all():
            site_names[sid] = nom

    return [serialize_action_for_decision(a, site_name=site_names.get(a.site_id, "")) for a in rows]


__all__ = [
    "serialize_action_for_decision",
    "get_top3_decisions",
]
