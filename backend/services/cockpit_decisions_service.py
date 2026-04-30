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
    BACS_PENALTY_EUR,
    CO2_FACTOR_ELEC_KGCO2_PER_KWH,
    DT_PENALTY_AT_RISK_EUR,
    DT_PENALTY_EUR,
    OPERAT_PENALTY_EUR,
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

# Phase 16.C — mappings levier → catégorie + pénalité hissés au scope module
# (audit /simplify Phase 15) : auparavant `_LEVER_TO_CATEGORY` était local à
# `serialize_action_for_decision` et `_LEVER_TO_PENALTY` local à
# `_estimate_capex_payback`. Cohérent avec `_CAPEX_HEURISTIC_BY_LEVER` et
# `_DECISION_NARRATIVE_FALLBACK_BY_LEVER` qui sont déjà module-level → un seul
# endroit pour tester / étendre / documenter.
_LEVER_TO_CATEGORY = {
    "bacs": "Conformité",
    "audit_sme": "Conformité",
    "operat": "Conformité",
    "aper": "Conformité",
    "achat": "Achat énergie",
}

# Pénalité légale annuelle évitée par levier — utilisée pour calculer
# `payback_months_net_penalty` (Phase 15.D).  Constantes doctrine canoniques
# (cf doctrine/constants.py BACS_PENALTY_EUR, OPERAT_PENALTY_EUR…).
# - APER : sanction 20 €/m²/an parking, dépend surface — pas de constante
#   (à hisser quand SiteSurfaceParking sera exposé).
# - audit_sme : pas de pénalité directe ETI < 250 ETP.
_LEVER_TO_PENALTY_EUR_YEAR = {
    "bacs": float(BACS_PENALTY_EUR),
    "operat": float(OPERAT_PENALTY_EUR),
    "aper": 0.0,
    "audit_sme": 0.0,
}

# Phase 15.B (audit Phase 14 P1-A : "zero business logic in frontend").
# Avant : `frontend/src/pages/CockpitDecision.jsx::NarrativeFallback`
# dupliquait ce mapping côté FE. Désormais : SoT unique côté backend, exposé
# via `narrative_fallback` dans `serialize_action_for_decision`. Garde la
# grammaire §5 doctrine (énoncé descriptif court + chiffre sourcé).
_DECISION_NARRATIVE_FALLBACK_BY_LEVER = {
    "bacs": (
        "Site assujetti au Décret BACS — système de pilotage CVC obligatoire "
        "avant 2027. Impact technique (GTB classe A/B) + arbitrage CapEx vs "
        "pénalité 1 500 €/an évitée."
    ),
    "audit_sme": (
        "Audit énergétique réglementaire (Code Énergie L233-1) — réalisation "
        "par OPQIBI ou ISO 50001. Levier généralement à payback rapide "
        "(~12-18 mois)."
    ),
    "achat": (
        "Renouvellement contrat fourniture post-ARENH — fenêtre forward Y+1 "
        "ouverte. Arbitrage entre baseload, profilé peakload et fixation "
        "partielle."
    ),
    "aper": (
        "Solarisation parking obligatoire (Loi APER) — surface > 1 500 m² "
        "assujettie. Couverture mini 50 % d'ici juillet 2028, sanction "
        "20 €/m²/an si non engagée."
    ),
    "operat": (
        "Déclaration OPERAT annuelle obligatoire (Décret Tertiaire) — collecte "
        "conso + pièces justificatives. Sanction 1 500 € + name & shame ADEME."
    ),
}


def _fmt_eur_short(v: float) -> str:
    """Formatte un montant en € compact FR (ex 135 600 → '135,6 k€').

    Phase 16.bis.C (audit /simplify) : ajout du tier M€ pour aligner avec
    `frontend/src/utils/format.js::fmtEurShort` (qui gère déjà M€). Avant :
    1 500 000 → '1500,0 k€' (incohérent FE qui retournait '1,5 M€').
    Cross-référence SoT : si tu modifies ici, modifie aussi le FE.
    """
    if v is None:
        return "—"
    abs_v = abs(v)
    if abs_v >= 1_000_000:
        return f"{(v / 1_000_000):.1f} M€".replace(".", ",")
    if abs_v >= 1_000:
        return f"{(v / 1_000):.1f} k€".replace(".", ",")
    return f"{int(round(v))} €"


def _narrative_fallback_for_lever(
    lever_key: str,
    action: ActionItem,
    capex_eur: Optional[float] = None,
    savings_eur_year: Optional[float] = None,
    penalty_eur_year: Optional[float] = None,
    payback_months: Optional[int] = None,
) -> Optional[str]:
    """Retourne un narrative cadre pour un levier connu, sinon None.

    Phase 16.B (audit Phase 15 P1) : interpole les chiffres réels du levier
    (CapEx + savings + pénalité évitée + payback) dans la narrative pour
    éviter le "démo scriptée" — 2 actions BACS sur 2 sites distincts ne
    portent plus la même phrase identique mot-à-mot.

    Phase 15.B : utilisé par `serialize_action_for_decision` pour pré-remplir
    le champ `narrative` quand `action.rationale` et `action.description` sont
    absents.
    """
    tpl = _DECISION_NARRATIVE_FALLBACK_BY_LEVER.get(lever_key)

    # Suffixe chiffré dynamique (Phase 16.B). Ajouté à la fin du template
    # cadre pour conserver la grammaire éditoriale §5 + ajouter du concret.
    extras = []
    if capex_eur and capex_eur > 0:
        extras.append(f"CapEx ~{_fmt_eur_short(capex_eur)}")
    if payback_months and payback_months > 0:
        if payback_months < 24:
            extras.append(f"payback ~{payback_months} mois")
        else:
            extras.append(f"payback ~{payback_months / 12:.1f} ans")
    if penalty_eur_year and penalty_eur_year > 0:
        extras.append(f"pénalité {_fmt_eur_short(penalty_eur_year)}/an évitée")

    if tpl:
        if extras:
            return f"{tpl} ({' · '.join(extras)})"
        return tpl

    # Fallback générique avec date d'échéance si dispo.
    if action.due_date:
        base = (
            "Action ouverte sur ce site, à arbitrer cette semaine selon "
            f"priorité métier et contraintes réglementaires. Échéance "
            f"{action.due_date.strftime('%d/%m/%Y')}."
        )
        if extras:
            base = base.rstrip(".") + f" ({' · '.join(extras)})."
        return base
    return None


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

    # Phase 16.C : `_LEVER_TO_CATEGORY` désormais hissé au scope module.
    # Étape 9 P0-D : exposer category_label depuis lever_key au lieu de
    # laisser le frontend deviner par parsing textuel (règle d'or zéro
    # business logic frontend).
    category_label = _LEVER_TO_CATEGORY.get(lever_key, "Investissement")

    # Phase 15.B + 16.B : narrative_fallback SoT backend, désormais chiffrée
    # avec CapEx + payback + pénalité évitée (interpolés depuis capex_estimation).
    # Le frontend ne duplique plus _NARRATIVE_TEMPLATE_BY_LEVER.
    narrative = action.rationale or action.description or ""
    if not narrative:
        narrative = (
            _narrative_fallback_for_lever(
                lever_key,
                action,
                capex_eur=capex_estimation.get("capex_eur"),
                savings_eur_year=capex_estimation.get("savings_eur_year"),
                penalty_eur_year=capex_estimation.get("penalty_avoided_eur_year"),
                payback_months=capex_estimation.get("payback_months_net_penalty")
                or capex_estimation.get("payback_months"),
            )
            or ""
        )

    return {
        "id": action.id,
        "title": title,
        "narrative": narrative,
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
        # Phase 15.D : payback CFO net pénalité évitée (champs additifs,
        # n'invalide pas payback_months brut conservé pour rétro-compat).
        "payback_months_net_penalty": capex_estimation.get("payback_months_net_penalty"),
        "penalty_avoided_eur_year": capex_estimation.get("penalty_avoided_eur_year"),
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

    # Phase 15.D (audit Phase 14 personas Jean-Marc CFO) : payback NET de la
    # pénalité réglementaire évitée. Pour les leviers de mise en conformité,
    # le ROI réel intègre la pénalité légale qui ne sera plus due une fois
    # l'action engagée. Le payback brut surestime le délai pour BACS/OPERAT/
    # APER/audit_sme. Calculé séparément pour préserver la transparence
    # (exposition simultanée brut + net pour audit terrain).
    # Phase 16.C/D : imports doctrine + mapping levier→pénalité hissés au
    # scope module (audit /simplify Phase 15 — anti-pattern lazy import résolu).
    penalty_avoided_eur_year = 0.0
    if action.severity and str(action.severity).lower() in ("critical", "high"):
        penalty = _LEVER_TO_PENALTY_EUR_YEAR.get(lever_key)
        if penalty is None and lever_key.startswith("other_"):
            # Fallback DT pour leviers compliance critiques non typés explicitement.
            penalty = (
                float(DT_PENALTY_EUR) if str(action.severity).lower() == "critical" else float(DT_PENALTY_AT_RISK_EUR)
            )
        if penalty:
            penalty_avoided_eur_year = penalty

    payback_months_net = None
    if capex_eur > 0 and savings_eur_year + penalty_avoided_eur_year > 0 and penalty_avoided_eur_year > 0:
        payback_months_net = round(capex_eur / (savings_eur_year + penalty_avoided_eur_year) * 12)

    return {
        "capex_eur": capex_eur if capex_eur > 0 else None,
        "savings_eur_year": savings_eur_year,
        "payback_months": payback_months,
        # Phase 15.D : payback NET = CapEx / (savings + pénalité évitée) × 12
        # — exposé séparément pour transparence Jean-Marc CFO.
        "payback_months_net_penalty": payback_months_net,
        "penalty_avoided_eur_year": (round(penalty_avoided_eur_year) if penalty_avoided_eur_year > 0 else None),
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

    # Phase 13.C (audit Antoine 80 sites) : fenêtre candidate proportionnelle
    # au nombre de sites. Si BACS domine (ex : 80 actions BACS × 5 sites les
    # plus critiques = 12), un fixed-12 ratait audit/achat/APER plus bas dans
    # le ranking. Désormais : N candidats = max(12, 3 × len(site_ids)) capé
    # à 80 — assez large pour 4 leviers distincts × top sites par sévérité,
    # tout en bornant la mémoire / temps de tri.
    candidate_window = min(max(12, 3 * len(site_ids)), 80)
    rows = (
        db.query(ActionItem)
        .filter(
            ActionItem.site_id.in_(site_ids),
            ActionItem.status.in_(["open", "in_progress"]),
        )
        .order_by(severity_rank.asc(), ActionItem.due_date.asc().nullslast())
        .limit(candidate_window)
        .all()
    )

    # Phase 14.D (audit Marie/Sophie 29/04) : dédup par lever_key GLOBAL.
    # Avant : dédup (site_id, lever) → si BACS dominait sur 5 sites, le Top 3
    # remontait 3× BACS sur 3 sites différents = "produit ne sait dire qu'une
    # chose" pour Marie/Sophie. Cassait la promesse "3 décisions à arbitrer"
    # de la maquette doctrine §11.3.
    # Après : un seul levier par Top 3 (BACS le plus critique + audit + achat
    # ou APER ou OPERAT). Si moins de 3 leviers distincts dans la fenêtre
    # candidate (ex 1 seul site, 1 seul levier), on complète avec d'autres
    # actions du même levier (fallback explicite).
    seen_levers: set[str] = set()
    deduped: list[ActionItem] = []
    fallback_pool: list[ActionItem] = []
    for action in rows:
        lever = _classify_lever(action)
        if lever in seen_levers:
            fallback_pool.append(action)
            continue
        seen_levers.add(lever)
        deduped.append(action)
        if len(deduped) >= 3:
            break

    # Fallback si < 3 leviers distincts disponibles : on ajoute des actions
    # du pool dédoublonné (même levier, sites différents) pour quand même
    # remplir le Top 3 plutôt que d'afficher 1 ou 2 cards.
    if len(deduped) < 3:
        seen_combos: set[tuple] = {(a.site_id or 0, _classify_lever(a)) for a in deduped}
        for action in fallback_pool:
            combo = (action.site_id or 0, _classify_lever(action))
            if combo in seen_combos:
                continue
            seen_combos.add(combo)
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
