"""PROMEOS — Cockpit Decisions service (Phase 2.3 Top 3 actions Décision).

Sérialise les actions ouvertes en payload Décision (vue exécutive) selon
contrat doctrine §0.D décision A : tout € exposé doit être traçable
réglementaire (article cité) ou contractuel. Sinon, conversion MWh/an.

Pour chaque action retournée par `/api/cockpit/decisions/top3` :
  - estimated_gain_mwh_year : conversion via PRICE_ELEC_ETI_2026_EUR_PER_MWH
    (Phase 13.A P0-3 : prix unique SoT des 2 côtés, plus de double standard)
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

from doctrine.acronyms import transform_acronym
from doctrine.constants import (
    CO2_FACTOR_ELEC_KGCO2_PER_KWH,
    DT_PENALTY_EUR,
    PRICE_ELEC_ETI_2026_EUR_PER_MWH,
)
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


_DECISION_QUESTION_TEMPLATES = {
    "bacs": "Faut-il installer un système de pilotage CVC obligatoire (Décret BACS) ?",
    "audit_sme": "Quel prestataire retenir pour l'audit énergétique obligatoire ?",
    "achat": "Quelle stratégie de renouvellement post-ARENH retenir ?",
    "aper": "Faut-il engager le solaire parking obligatoire (loi APER) ?",
    "operat": "Faut-il finaliser la déclaration OPERAT annuelle ?",
}


def _question_title_for_lever(lever_key: str, site_name: str = "") -> str | None:
    """Étape 6.bis P1 : transforme un titre action en question décisionnelle.

    Audit Marie + /frontend-design : les titres prod ("Installer un système…")
    annonçaient une action au lieu de poser la question d'arbitrage. Cette
    transformation rend les cards conversation cadre↔outil (§5 grammaire).

    Returns:
        Titre interrogatif suffixé du nom du site, ou None si le levier n'a
        pas de template (caller utilisera le titre brut transformé).
    """
    template = _DECISION_QUESTION_TEMPLATES.get(lever_key)
    if not template:
        return None
    if site_name:
        # On retire le "?" final pour ajouter le site avant
        base = template.rstrip("? ").rstrip()
        return f"{base} — {site_name} ?"
    return template


def serialize_action_for_decision(action: ActionItem, site_name: str = "") -> dict:
    """Sérialise un ActionItem en payload Décision (vue exécutive).

    Doctrine §0.D A : si pas de regulatory_article ni contract_id, le
    montant € est exclu — seul le MWh/an est exposé. Si action de mise
    en conformité, on rattache l'EurAmount via build_regulatory avec
    article cité.

    Étape 6.bis P1 : titre transformé en question décisionnelle pour
    les leviers connus (BACS, audit SMÉ, achat, APER, OPERAT) — effet
    "conseiller" plutôt qu'"injonction" (audit Marie 8.2/10).

    Args:
        action: ActionItem ORM
        site_name: nom lisible du site (resolved par l'appelant)

    Returns:
        dict avec champs canoniques (cf prompt §3.B Phase 2.3)
    """
    # Phase 13.A P0-3 (audit véracité 5.5/10) : prix énergie unifié SoT.
    # Avant : `raw_gain / DEFAULT_PRICE_ELEC_EUR_KWH / 1000` utilisait
    # 68 €/MWh (EPEX baseline) pour convertir € → MWh, puis le calcul
    # `_estimate_capex_payback` ré-utilisait 130 €/MWh (post-ARENH ETI 2026)
    # pour reconvertir MWh → savings_eur_year, gonflant artificiellement
    # tous les CapEx/savings BACS par ×1,91. Désormais : prix unique
    # PRICE_ELEC_ETI_2026_EUR_PER_MWH des 2 côtés (cohérent).
    raw_gain = action.estimated_gain_eur or 0
    gain_mwh = round(raw_gain / PRICE_ELEC_ETI_2026_EUR_PER_MWH) if raw_gain > 0 else 0

    # Étape 6.bis : titre interrogatif si levier connu, sinon titre brut narrativisé.
    lever_key = _classify_lever(action)
    question_title = _question_title_for_lever(lever_key, site_name)
    title = question_title if question_title else transform_acronym(action.title or "")
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

    # Étape 9 P0-D : exposer category_label depuis lever_key au lieu de
    # laisser le frontend deviner par parsing textuel (audit /simplify P0
    # "tagLabel = decision.title.toLowerCase().includes('contrat')" violait
    # la règle d'or zéro business logic frontend).
    _LEVER_TO_CATEGORY = {
        "bacs": "Conformité",
        "audit_sme": "Conformité",
        "operat": "Conformité",
        "aper": "Conformité",
        "achat": "Achat énergie",
    }
    category_label = _LEVER_TO_CATEGORY.get(lever_key, "Investissement")

    return {
        "id": action.id,
        "title": title,
        "narrative": action.rationale or action.description or "",
        "site_id": action.site_id,
        "site": site_name,
        "echeance": action.due_date.isoformat() if action.due_date else None,
        "severity": _enum_str(action.severity),
        "priority": _enum_str(action.priority),
        "lever_key": lever_key,  # backend SoT pour mapping FE
        "category_label": category_label,
        "estimated_gain_mwh_year": gain_mwh,
        "estimated_savings_eur_year": capex_estimation.get("savings_eur_year"),
        "investment_capex_eur": capex_estimation.get("capex_eur"),
        "payback_months": capex_estimation.get("payback_months"),
        "co2_avoided_t_year": capex_estimation.get("co2_avoided_t_year"),
        "estimation_method": capex_estimation.get("method"),
        "reference": cee_ref or regulatory_article,
        "regulatory_penalty_eur": regulatory_penalty,
    }


# Heuristique CapEx € par MWh évité par type de levier — médiane référentiels
# CEE BAT-TH-* + retours opérateurs 2024-2025 sur tertiaire mid-market.
# Étape 6.bis : indexé par clé _classify_lever() pour DRY (audit /simplify P1
# divergence silencieuse possible — un levier classé `bacs` côté dedup mais
# `default` côté CapEx héritait des mauvaises constantes).
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
    "operat": {
        "capex_per_mwh_year": 50,  # Déclaration OPERAT ~50 €/MWh éco
        "method": "Référentiel ADEME OPERAT",
    },
    "default": {
        "capex_per_mwh_year": 1_000,
        "method": "Heuristique CEE générique",
    },
}


def _estimate_capex_payback(action: ActionItem, gain_mwh_year: int) -> dict:
    """Estime CapEx + payback + CO₂ évité selon levier + potentiel énergie.

    Étape 6.bis :
    - Réutilise `_classify_lever()` au lieu de dupliquer le parsing titre
      (audit /simplify P1 — divergence silencieuse possible).
    - Sources canoniques :
        - PRICE_ELEC_ETI_2026_EUR_PER_MWH (doctrine/constants.py SoT)
        - CO2_FACTOR_ELEC_KGCO2_PER_KWH (ADEME Base Empreinte V23.6)

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

    # _classify_lever() retourne `other_<id>` pour leviers non catégorisés
    # → fallback sur "default" du mapping CapEx.
    lever_key = _classify_lever(action)
    params = _CAPEX_HEURISTIC_BY_LEVER.get(lever_key, _CAPEX_HEURISTIC_BY_LEVER["default"])

    capex_eur = round(gain_mwh_year * params["capex_per_mwh_year"])
    savings_eur_year = round(gain_mwh_year * PRICE_ELEC_ETI_2026_EUR_PER_MWH)
    payback_months = round(capex_eur / savings_eur_year * 12) if savings_eur_year > 0 and capex_eur > 0 else None
    # Conversion : MWh × 1 000 (→ kWh) × kgCO₂/kWh / 1 000 (→ tCO₂)
    # = MWh × CO2_FACTOR (kg/kWh est numériquement = t/MWh, propriété SI).
    co2_avoided_t_year = round(gain_mwh_year * CO2_FACTOR_ELEC_KGCO2_PER_KWH, 1)

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
