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

from sqlalchemy.orm import Session

from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH
from doctrine.acronyms import transform_acronym
from doctrine.constants import DT_PENALTY_EUR
from models.action_item import ActionItem


_CEE_PATTERN = re.compile(r"BAT-TH-\d+", re.IGNORECASE)


def _extract_cee_reference(text: Optional[str]) -> Optional[str]:
    """Détecte une référence CEE BAT-TH-NNN dans un texte libre."""
    if not text:
        return None
    match = _CEE_PATTERN.search(text)
    return match.group(0).upper() if match else None


def _infer_regulatory_article(action: ActionItem) -> Optional[str]:
    """Détermine l'article réglementaire applicable selon source_type + sévérité.

    Phase 2.3 : règle simple — actions critiques de mise en conformité DT
    sont rattachées à Décret 2019-771 art. 9 (pénalité 7 500 €/site NC).
    """
    source = (
        action.source_type.value if hasattr(action.source_type, "value") else str(action.source_type or "")
    ).lower()
    severity = (action.severity.value if hasattr(action.severity, "value") else str(action.severity or "")).lower()
    if source == "compliance" and severity == "critical":
        return "Décret 2019-771 art. 9"
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
    if regulatory_article == "Décret 2019-771 art. 9":
        # Mise en conformité DT : pénalité 7 500 €/site (Phase 1.1 EurAmount typé).
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
        "severity": action.severity.value if hasattr(action.severity, "value") else str(action.severity or ""),
        "priority": action.priority.value if hasattr(action.priority, "value") else str(action.priority or ""),
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

    rows = (
        db.query(ActionItem)
        .filter(
            ActionItem.site_id.in_(site_ids),
            ActionItem.status.in_(["open", "in_progress"]),
        )
        .order_by(
            ActionItem.severity.desc(),  # critical avant high (alphabétique inverse)
            ActionItem.due_date.asc().nullslast(),
        )
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
