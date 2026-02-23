"""
PROMEOS — Patrimoine Impact Service (V59)

Enrichit les anomalies V58 avec :
  - regulatory_impact : {framework, risk_level, explanation_fr}
  - business_impact   : {type, estimated_risk_eur, confidence, explanation_fr}
  - priority_score    : int 0..100

Décisions V59 :
  - Option A : hypothèses simples configurables (PatrimoineAssumptions)
  - Zéro accès DB — calcul pure function sur les dicts anomalies + snapshot
  - Tri final par priority_score DESC (plus risqué en premier)
  - Backward-compatible : les champs ajoutés sont additifs

Formules priority_score :
  base   = sévérité  (CRITICAL=30, HIGH=25, MEDIUM=15, LOW=5)
  réglem = framework (DECRET_TERTIAIRE=20, FACTURATION=20, BACS=10, NONE=0)
  €      = bucket    (>50k=30, 10-50k=20, 1-10k=10, sinon=0)
  score  = clamp(0, 100, base + réglem + €)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.patrimoine_assumptions import PatrimoineAssumptions, DEFAULT_ASSUMPTIONS


# ── Mapping code → métadonnées d'impact ───────────────────────────────────────

_IMPACT_META: Dict[str, Dict[str, Any]] = {
    "SURFACE_MISSING": {
        "framework": "DECRET_TERTIAIRE",
        "risk_level": "HIGH",
        "explanation_fr": (
            "La surface SoT est inconnue. Le Décret Tertiaire impose la déclaration "
            "de la surface tertiaire soumise à obligation sur OPERAT. "
            "Sans surface, aucun calcul de consommation normalisée (kWh/m²/an) "
            "n'est possible — trajectoire de réduction bloquée."
        ),
        "business_type": "DATA_QUALITY",
        "confidence": 0.4,
    },
    "SURFACE_MISMATCH": {
        "framework": "DECRET_TERTIAIRE",
        "risk_level": "HIGH",
        "explanation_fr": (
            "L'écart de surface fausse les calculs de consommation normalisée "
            "(kWh/m²/an) déclarés sur OPERAT, entraînant un risque de non-conformité "
            "Décret Tertiaire (trajectoire -40 % en 2030)."
        ),
        "business_type": "REGULATORY_RISK",
        "confidence": 0.5,
    },
    "BUILDING_MISSING": {
        "framework": "DECRET_TERTIAIRE",
        "risk_level": "MEDIUM",
        "explanation_fr": (
            "Sans bâtiment défini, la surface réglementaire SoT ne peut être calculée. "
            "Cela bloque la déclaration OPERAT et l'évaluation BACS (R2-2)."
        ),
        "business_type": "DATA_QUALITY",
        "confidence": 0.4,
    },
    "BUILDING_USAGE_MISSING": {
        "framework": "DECRET_TERTIAIRE",
        "risk_level": "MEDIUM",
        "explanation_fr": (
            "L'usage du bâtiment est requis pour le calcul de la valeur de référence "
            "OPERAT (catégorie d'activité). Sans usage, la trajectoire "
            "-40 %/-50 %/-60 % ne peut être calculée."
        ),
        "business_type": "DATA_QUALITY",
        "confidence": 0.4,
    },
    "METER_NO_DELIVERY_POINT": {
        "framework": "FACTURATION",
        "risk_level": "HIGH",
        "explanation_fr": (
            "Un compteur sans point de livraison (PRM/PCE) empêche la réconciliation "
            "des factures énergie. Risque de double facturation ou de factures "
            "non imputables détectées tardivement."
        ),
        "business_type": "BILLING_RISK",
        "confidence": 0.4,
    },
    "CONTRACT_DATE_INVALID": {
        "framework": "FACTURATION",
        "risk_level": "MEDIUM",
        "explanation_fr": (
            "Des dates de contrat invalides (début ≥ fin) rendent impossible "
            "le calcul de la durée contractuelle et la détection de l'expiration "
            "imminente — risque de reconduction tacite non souhaitée."
        ),
        "business_type": "DATA_QUALITY",
        "confidence": 0.3,
    },
    "CONTRACT_OVERLAP_SITE": {
        "framework": "FACTURATION",
        "risk_level": "HIGH",
        "explanation_fr": (
            "Un chevauchement de contrats peut entraîner une double facturation "
            "ou un conflit de conditions tarifaires sur la même période — "
            "surcoût direct facturé par le fournisseur."
        ),
        "business_type": "BILLING_RISK",
        "confidence": 0.6,
    },
    "ORPHANS_DETECTED": {
        "framework": "NONE",
        "risk_level": "LOW",
        "explanation_fr": (
            "Des données orphelines (site archivé avec enfants actifs) "
            "faussent les agrégations de portefeuille et la facturation."
        ),
        "business_type": "DATA_QUALITY",
        "confidence": 0.2,
    },
}

# ── Priority score weights ─────────────────────────────────────────────────────

_SEV_BASE: Dict[str, int] = {
    "CRITICAL": 30,
    "HIGH":     25,
    "MEDIUM":   15,
    "LOW":       5,
}

_FRAMEWORK_WEIGHT: Dict[str, int] = {
    "DECRET_TERTIAIRE": 20,
    "FACTURATION":      20,
    "BACS":             10,
    "NONE":              0,
}


def _eur_bucket(eur: float) -> int:
    if eur > 50_000:
        return 30
    if eur > 10_000:
        return 20
    if eur > 1_000:
        return 10
    return 0


def compute_priority_score(anomaly: Dict[str, Any]) -> int:
    """
    Score 0..100 = sévérité + poids réglementaire + bucket € estimé.
    Clampé à [0, 100].
    """
    sev = anomaly.get("severity", "LOW")
    base = _SEV_BASE.get(sev, 5)

    reg_impact = anomaly.get("regulatory_impact") or {}
    framework = reg_impact.get("framework", "NONE") if isinstance(reg_impact, dict) else "NONE"
    reg = _FRAMEWORK_WEIGHT.get(framework, 0)

    biz_impact = anomaly.get("business_impact") or {}
    eur = float(biz_impact.get("estimated_risk_eur") or 0.0) if isinstance(biz_impact, dict) else 0.0
    eur_score = _eur_bucket(eur)

    return min(100, base + reg + eur_score)


# ── Calculateurs d'impact business par code ───────────────────────────────────

def _calc_surface_missing(
    anomaly: Dict[str, Any],
    snapshot: Dict[str, Any],
    a: PatrimoineAssumptions,
) -> Dict[str, Any]:
    """Risque = conso_fallback * prix_elec * 15% (data quality penalty)."""
    risk_eur = a.conso_fallback_kwh_an * a.prix_elec_eur_kwh * 0.15
    return {
        "type": "DATA_QUALITY",
        "estimated_risk_eur": round(risk_eur, 0),
        "confidence": 0.4,
        "explanation_fr": (
            f"Estimation : {a.conso_fallback_kwh_an:,.0f} kWh/an × "
            f"{a.prix_elec_eur_kwh:.4f} €/kWh × 15 % (pénalité data quality)."
        ),
    }


def _calc_surface_mismatch(
    anomaly: Dict[str, Any],
    snapshot: Dict[str, Any],
    a: PatrimoineAssumptions,
) -> Dict[str, Any]:
    """
    Risque = |écart_m²| × conso_kWh/m²/an × prix_elec × horizon_factor.
    Usage extrait du snapshot si disponible, sinon default.
    """
    evidence = anomaly.get("evidence") or {}
    surface_site = float(evidence.get("surface_site_m2") or 0)
    surface_bats = float(evidence.get("surface_batiments_sum_m2") or 0)
    surface_diff = abs(surface_site - surface_bats)

    # Usage principal depuis le snapshot (premier bâtiment)
    primary_usage: Optional[str] = None
    for bat in (snapshot or {}).get("batiments", []):
        usages = bat.get("usages") or []
        if usages:
            primary_usage = usages[0].get("type")
            break

    conso_m2 = a.conso_m2_for_usage(primary_usage)
    risk_eur = surface_diff * conso_m2 * a.prix_elec_eur_kwh * a.horizon_factor

    return {
        "type": "REGULATORY_RISK",
        "estimated_risk_eur": round(risk_eur, 0),
        "confidence": 0.5,
        "explanation_fr": (
            f"Écart : {surface_diff:.0f} m² × {conso_m2:.0f} kWh/m²/an × "
            f"{a.prix_elec_eur_kwh:.4f} €/kWh."
        ),
    }


def _calc_meter_no_dp(
    anomaly: Dict[str, Any],
    snapshot: Dict[str, Any],
    a: PatrimoineAssumptions,
) -> Dict[str, Any]:
    """Risque = conso_fallback * prix_elec * 20% (facture non réconciliée)."""
    risk_eur = a.conso_fallback_kwh_an * a.prix_elec_eur_kwh * 0.20
    return {
        "type": "BILLING_RISK",
        "estimated_risk_eur": round(risk_eur, 0),
        "confidence": 0.4,
        "explanation_fr": (
            f"20 % du coût annuel fallback ({a.conso_fallback_kwh_an:,.0f} kWh × "
            f"{a.prix_elec_eur_kwh:.4f} €/kWh) — risque de facturation non imputée."
        ),
    }


def _calc_contract_overlap(
    anomaly: Dict[str, Any],
    snapshot: Dict[str, Any],
    a: PatrimoineAssumptions,
) -> Dict[str, Any]:
    """
    Risque = conso_fallback * prix_elec * (overlap_days/365).
    En l'absence des dates d'overlap, estimation conservatrice sur 30j.
    """
    overlap_days = 30  # fallback conservateur
    risk_eur = a.conso_fallback_kwh_an * a.prix_elec_eur_kwh * (overlap_days / 365)
    return {
        "type": "BILLING_RISK",
        "estimated_risk_eur": round(risk_eur, 0),
        "confidence": 0.6,
        "explanation_fr": (
            f"~{overlap_days} j de chevauchement × "
            f"{a.conso_fallback_kwh_an:,.0f} kWh/an × "
            f"{a.prix_elec_eur_kwh:.4f} €/kWh."
        ),
    }


def _calc_zero(business_type: str, confidence: float) -> Dict[str, Any]:
    return {
        "type": business_type,
        "estimated_risk_eur": 0.0,
        "confidence": confidence,
        "explanation_fr": "Impact financier direct non quantifiable — anomalie de qualité de données.",
    }


# ── Dispatch table ────────────────────────────────────────────────────────────

_CALC_DISPATCH = {
    "SURFACE_MISSING":       _calc_surface_missing,
    "SURFACE_MISMATCH":      _calc_surface_mismatch,
    "METER_NO_DELIVERY_POINT": _calc_meter_no_dp,
    "CONTRACT_OVERLAP_SITE": _calc_contract_overlap,
}


def _compute_business_impact(
    anomaly: Dict[str, Any],
    snapshot: Dict[str, Any],
    a: PatrimoineAssumptions,
    meta: Dict[str, Any],
) -> Dict[str, Any]:
    code = anomaly.get("code", "")
    calc = _CALC_DISPATCH.get(code)
    if calc:
        return calc(anomaly, snapshot, a)
    return _calc_zero(
        business_type=meta.get("business_type", "DATA_QUALITY"),
        confidence=meta.get("confidence", 0.3),
    )


# ── Fonction principale ───────────────────────────────────────────────────────

def enrich_anomalies_with_impact(
    anomalies: List[Dict[str, Any]],
    snapshot: Optional[Dict[str, Any]] = None,
    assumptions: Optional[PatrimoineAssumptions] = None,
) -> List[Dict[str, Any]]:
    """
    Enrichit chaque anomalie V58 avec regulatory_impact, business_impact,
    priority_score. Trie par priority_score DESC.

    Args:
        anomalies : liste d'anomalies issues de compute_site_anomalies()
        snapshot  : dict snapshot (optionnel — améliore SURFACE_MISMATCH)
        assumptions : hypothèses de calcul (default = DEFAULT_ASSUMPTIONS)

    Returns:
        Liste enrichie, triée par priority_score DESC.
        Backward-compatible : si anomalies est vide, retourne vide.
    """
    if not anomalies:
        return anomalies

    if assumptions is None:
        assumptions = DEFAULT_ASSUMPTIONS
    if snapshot is None:
        snapshot = {}

    enriched: List[Dict[str, Any]] = []
    for anomaly in anomalies:
        code = anomaly.get("code", "")
        meta = _IMPACT_META.get(code, {})

        regulatory_impact = {
            "framework":      meta.get("framework", "NONE"),
            "risk_level":     meta.get("risk_level", anomaly.get("severity", "LOW")),
            "explanation_fr": meta.get("explanation_fr", ""),
        }
        business_impact = _compute_business_impact(anomaly, snapshot, assumptions, meta)

        enriched_anomaly = {
            **anomaly,
            "regulatory_impact": regulatory_impact,
            "business_impact":   business_impact,
        }
        # Priority score calculé après enrichissement (dépend des nouveaux champs)
        enriched_anomaly["priority_score"] = compute_priority_score(enriched_anomaly)
        enriched.append(enriched_anomaly)

    # Tri par priority_score DESC
    enriched.sort(key=lambda a: a["priority_score"], reverse=True)
    return enriched
