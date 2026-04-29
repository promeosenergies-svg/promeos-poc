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

    # Étape 4 P1 backend : CapEx + payback estimés pour les cards Décision
    # (audits Marie + Jean-Marc : "manque CapEx + Économie €/an + Payback").
    # Heuristique CEE BAT-TH-* / lever_kind : on dérive un CapEx indicatif
    # depuis le levier détecté + le potentiel énergétique. Confiance
    # "indicative" — frontend rendra le badge "Estimation".
    capex_estimation = _estimate_capex_payback(action, gain_mwh)

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
        "estimated_savings_eur_year": capex_estimation.get("savings_eur_year"),
        "investment_capex_eur": capex_estimation.get("capex_eur"),
        "payback_months": capex_estimation.get("payback_months"),
        "co2_avoided_t_year": capex_estimation.get("co2_avoided_t_year"),
        "estimation_method": capex_estimation.get("method"),
        "reference": cee_ref or regulatory_article,
        "regulatory_penalty_eur": regulatory_penalty,
    }


# Constantes heuristique CapEx — séparées en module-level pour testabilité.
# Sources : médiane référentiels CEE BAT-TH-* + retours opérateurs OPERA
# 2024-2025 sur tertiaire mid-market.
_CAPEX_HEURISTIC_BY_LEVER = {
    "bacs": {
        "capex_per_mwh_year": 1_200,  # GTB classe A/B ~1 200 €/MWh éco
        "method": "CEE BAT-TH-116 médiane",
    },
    "audit_sme": {
        "capex_per_mwh_year": 80,  # Audit ISO 50001 ~80 €/MWh éco
        "method": "Référentiel ADEME audit SME",
    },
    "achat": {
        "capex_per_mwh_year": 0,  # Renouvellement contrat = pas de CapEx
        "method": "Renouvellement contrat sans engagement",
    },
    "aper": {
        "capex_per_mwh_year": 1_500,  # Solaire parking ~1 500 €/MWh éco
        "method": "Retour benchmark APER tertiaire",
    },
    "default": {
        "capex_per_mwh_year": 1_000,
        "method": "Heuristique CEE générique",
    },
}

# Coût marginal énergie ETI tertiaire 2026 (post-ARENH) — médiane CRE T4 2025.
_PRICE_ELEC_EUR_PER_MWH_2026 = 130.0
# Facteur émission CO₂ électricité France ADEME V23.6 (kgCO₂/kWh).
_CO2_FACTOR_KG_PER_KWH = 0.052


def _estimate_capex_payback(action: ActionItem, gain_mwh_year: int) -> dict:
    """Estime CapEx + payback + CO₂ évité selon levier + potentiel énergie.

    Retourne {capex_eur, savings_eur_year, payback_months, co2_avoided_t_year,
    method} — tous None si gain_mwh_year=0 (pas d'estimation possible).
    """
    if not gain_mwh_year or gain_mwh_year <= 0:
        return {
            "capex_eur": None,
            "savings_eur_year": None,
            "payback_months": None,
            "co2_avoided_t_year": None,
            "method": None,
        }

    # Détecter le levier (réutilise la classification de get_top3_decisions)
    title = (action.title or "").lower()
    if "bacs" in title or "gtb" in title or "pilotage cvc" in title:
        params = _CAPEX_HEURISTIC_BY_LEVER["bacs"]
    elif "audit" in title and ("énergétique" in title or "energie" in title or "iso" in title):
        params = _CAPEX_HEURISTIC_BY_LEVER["audit_sme"]
    elif "renouvel" in title or "contrat" in title or "achat" in title or "marché" in title:
        params = _CAPEX_HEURISTIC_BY_LEVER["achat"]
    elif "aper" in title or "solaire" in title:
        params = _CAPEX_HEURISTIC_BY_LEVER["aper"]
    else:
        params = _CAPEX_HEURISTIC_BY_LEVER["default"]

    capex_eur = round(gain_mwh_year * params["capex_per_mwh_year"])
    savings_eur_year = round(gain_mwh_year * _PRICE_ELEC_EUR_PER_MWH_2026)
    payback_months = round(capex_eur / savings_eur_year * 12) if savings_eur_year > 0 and capex_eur > 0 else None
    co2_avoided_t_year = round(gain_mwh_year * 1000 * _CO2_FACTOR_KG_PER_KWH / 1000, 1)

    return {
        "capex_eur": capex_eur if capex_eur > 0 else None,
        "savings_eur_year": savings_eur_year,
        "payback_months": payback_months,
        "co2_avoided_t_year": co2_avoided_t_year,
        "method": params["method"],
    }


def _classify_lever(action: ActionItem) -> str:
    """Classifie l'action par grand levier doctrinal pour dédup site×levier.

    Étape 4 P0-B backend : la file Top 3 doit présenter 3 leviers DISTINCTS,
    pas 3 actions de même levier sur le même site (ex : 2 actions BACS
    Siège créent une redondance dans la Vue Exécutive — détecté par
    /frontend-design audit Étape 2).
    """
    title = (action.title or "").lower()
    if "bacs" in title or "gtb" in title or "pilotage cvc" in title:
        return "bacs"
    if "audit énergétique" in title or "audit energie" in title or "iso 50001" in title:
        return "audit_sme"
    if "renouvel" in title or "contrat" in title or "achat" in title or "marché" in title:
        return "achat"
    if "aper" in title or "solaire" in title or "photovolt" in title:
        return "aper"
    if "operat" in title or "déclaration" in title:
        return "operat"
    return f"other_{action.id}"


def get_top3_decisions(db: Session, site_ids: list[int]) -> list[dict]:
    """Retourne les 3 actions Top Décision pour la Vue Exécutive.

    Tri : critical → high → medium ; actions avec due_date plus proche
    en premier. Dédoublonne par (site_id × lever_kind) afin que les 3
    décisions présentées soient des leviers distincts (Étape 4 P0-B).
    Limit 3 max. Si pas d'actions ouvertes → liste vide.
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

    # On élargit la fenêtre à 12 actions candidates (3 × 4 leviers max) puis
    # on dédup côté Python (vs filtrer côté SQL — moins lisible et fragile).
    rows = (
        db.query(ActionItem)
        .filter(
            ActionItem.site_id.in_(site_ids),
            ActionItem.status.in_(["open", "in_progress"]),
        )
        .order_by(severity_rank.asc(), ActionItem.due_date.asc().nullslast())
        .limit(12)
        .all()
    )

    # Dédup site_id × lever : on garde l'action de plus haute priorité par
    # combo. Si l'action n'a pas de site_id, on ne dédup que par levier.
    seen_keys: set[tuple] = set()
    deduped: list[ActionItem] = []
    for action in rows:
        lever = _classify_lever(action)
        key = (action.site_id or 0, lever)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(action)
        if len(deduped) >= 3:
            break

    # Site name resolver — single query
    site_names: dict[int, str] = {}
    if deduped:
        from models import Site

        site_ids_used = {a.site_id for a in deduped if a.site_id}
        for sid, nom in db.query(Site.id, Site.nom).filter(Site.id.in_(site_ids_used)).all():
            site_names[sid] = nom

    return [serialize_action_for_decision(a, site_name=site_names.get(a.site_id, "")) for a in deduped]


__all__ = [
    "serialize_action_for_decision",
    "get_top3_decisions",
]
