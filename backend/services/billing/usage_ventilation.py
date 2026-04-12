"""
Ventilation d'un shadow bill par usage (clés de répartition par archétype).

Permet de répondre à : "sur ma facture de 3200 EUR HT, combien est imputable
a la CVC, l'ECS, l'IRVE, l'eclairage, le froid, etc. ?"

Limite : les usages ne sont PAS mesures individuellement. La ventilation est
une estimation basee sur un profil de repartition par archetype canonique.

Sources de calibration :
- ADEME CEREN repartition usages tertiaire 2024
- CRE deliberation 2026-33 (HC solaires 11h-14h, ECS IRVE BATTERIES)
- CEREN Sectoriel Tertiaire 2023 (% par poste usage)
"""

from typing import Optional

# Profil de repartition par archetype : {usage_code: (share_hp, share_hc)}
# share_hp + share_hc = proportion de la conso totale du site sur cet usage
# Le ratio share_hp/(share_hp+share_hc) indique la modulation HP/HC de cet usage.
#
# Exemple BUREAU_STANDARD : CVC_HVAC = (0.35, 0.05) -> 40% conso totale, dont 87% HP, 13% HC
USAGE_REPARTITION_BY_ARCHETYPE: dict[str, dict[str, tuple[float, float]]] = {
    "BUREAU_STANDARD": {
        "CVC_HVAC": (0.35, 0.05),
        "ECLAIRAGE": (0.18, 0.02),
        "ECS": (0.05, 0.05),
        "IRVE": (0.08, 0.07),
        "AUTRES": (0.12, 0.03),
    },
    "HOTEL_HEBERGEMENT": {
        "CVC_HVAC": (0.30, 0.10),
        "ECS": (0.08, 0.12),
        "FROID_COMMERCIAL": (0.10, 0.05),
        "ECLAIRAGE": (0.10, 0.05),
        "IRVE": (0.05, 0.05),
    },
    "ENSEIGNEMENT": {
        "CVC_HVAC": (0.45, 0.05),
        "ECLAIRAGE": (0.18, 0.02),
        "ECS": (0.10, 0.08),
        "AUTRES": (0.10, 0.02),
    },
    "ENSEIGNEMENT_SUP": {
        "CVC_HVAC": (0.35, 0.05),
        "DATA_CENTER": (0.10, 0.10),
        "ECLAIRAGE": (0.18, 0.02),
        "ECS": (0.08, 0.05),
        "IRVE": (0.04, 0.03),
    },
    "SANTE": {
        "CVC_HVAC": (0.30, 0.15),
        "ECS": (0.15, 0.10),
        "ECLAIRAGE": (0.12, 0.05),
        "AUTRES": (0.10, 0.03),
    },
    "LOGISTIQUE_SEC": {
        "ECLAIRAGE": (0.25, 0.05),
        "CVC_HVAC": (0.20, 0.05),
        "AIR_COMPRIME": (0.18, 0.07),
        "IRVE": (0.08, 0.12),
    },
    "LOGISTIQUE_FRIGO": {
        "FROID_INDUSTRIEL": (0.40, 0.20),
        "CHAINES_FRIGO": (0.12, 0.08),
        "ECLAIRAGE": (0.08, 0.02),
        "CVC_HVAC": (0.06, 0.04),
    },
    "COMMERCE_ALIMENTAIRE": {
        "FROID_COMMERCIAL": (0.35, 0.15),
        "CVC_HVAC": (0.15, 0.05),
        "ECLAIRAGE": (0.18, 0.02),
        "IRVE": (0.05, 0.05),
    },
    "RESTAURANT": {
        "FROID_COMMERCIAL": (0.25, 0.15),
        "ECS": (0.15, 0.10),
        "CVC_HVAC": (0.15, 0.10),
        "ECLAIRAGE": (0.07, 0.03),
    },
    "INDUSTRIE_LEGERE": {
        "PROCESS_BATCH": (0.30, 0.10),
        "AIR_COMPRIME": (0.15, 0.05),
        "POMPES": (0.12, 0.03),
        "CVC_HVAC": (0.15, 0.05),
        "ECLAIRAGE": (0.04, 0.01),
    },
    "INDUSTRIE_LOURDE": {
        "PROCESS_CONTINU": (0.40, 0.20),
        "CVC_HVAC": (0.10, 0.05),
        "POMPES": (0.10, 0.05),
        "AIR_COMPRIME": (0.05, 0.05),
    },
    "DATA_CENTER": {
        "DATA_CENTER": (0.55, 0.30),
        "CVC_HVAC": (0.08, 0.07),
    },
    "SPORT_LOISIR": {
        "ECS": (0.25, 0.15),
        "CVC_HVAC": (0.20, 0.05),
        "POMPES": (0.15, 0.05),
        "ECLAIRAGE": (0.10, 0.05),
    },
    "COLLECTIVITE": {
        "CVC_HVAC": (0.40, 0.05),
        "ECLAIRAGE": (0.18, 0.02),
        "ECS": (0.08, 0.05),
        "IRVE": (0.15, 0.07),
    },
    "COPROPRIETE": {
        "CVC_HVAC": (0.35, 0.20),
        "ECS": (0.10, 0.15),
        "ECLAIRAGE": (0.10, 0.05),
        "IRVE": (0.02, 0.03),
    },
    "DEFAULT": {
        "CVC_HVAC": (0.35, 0.10),
        "ECLAIRAGE": (0.15, 0.05),
        "ECS": (0.10, 0.10),
        "AUTRES": (0.10, 0.05),
    },
}


# Garde de coherence : la taxonomie doit couvrir les memes archetypes que le moteur flex.
# Evite les derives silencieuses quand un archetype est ajoute dans un module mais pas l'autre.
def _assert_archetype_coverage() -> None:
    from services.flex.flexibility_scoring_engine import ARCHETYPE_TO_USAGES as _canonical

    missing = set(_canonical.keys()) - set(USAGE_REPARTITION_BY_ARCHETYPE.keys())
    if missing:
        raise RuntimeError(f"usage_ventilation: archetypes manquants vs flex engine : {sorted(missing)}")


_assert_archetype_coverage()


USAGE_LABELS: dict[str, str] = {
    "CVC_HVAC": "Chauffage / Ventilation / Climatisation",
    "ECS": "Eau Chaude Sanitaire",
    "FROID_COMMERCIAL": "Froid commercial",
    "FROID_INDUSTRIEL": "Froid industriel",
    "AIR_COMPRIME": "Air comprime",
    "POMPES": "Pompes hydrauliques",
    "IRVE": "Recharge VE",
    "ECLAIRAGE": "Eclairage",
    "DATA_CENTER": "Salles informatiques",
    "PROCESS_BATCH": "Process batch",
    "CHAINES_FRIGO": "Chaines du froid",
    "AUTRES": "Autres usages",
}


def get_usage_repartition(archetype_code: str) -> dict[str, tuple[float, float]]:
    """Retourne le profil de repartition pour un archetype (fallback DEFAULT)."""
    return USAGE_REPARTITION_BY_ARCHETYPE.get(
        archetype_code,
        USAGE_REPARTITION_BY_ARCHETYPE["DEFAULT"],
    )


def ventile_shadow_bill_by_usage(
    shadow_bill: dict,
    archetype_code: str,
    override_weights: Optional[dict[str, tuple[float, float]]] = None,
) -> dict:
    """
    Ventile un shadow bill total par usage en utilisant les cles de repartition
    de l'archetype (estimee, non mesuree).

    Args:
        shadow_bill: dict retourne par shadow_billing_v2, contient au minimum
            - "expected_fourniture_ht"
            - "expected_reseau_ht"
            - "expected_taxes_ht"
            - "expected_abo_ht"
            - "expected_tva"
            - "expected_ttc"
            - "kwh" (total consomme sur la periode)
        archetype_code: code canonique flex (ex BUREAU_STANDARD)
        override_weights: dict optionnel pour remplacer les poids par defaut
            (permet d'injecter des cles calibrees par l'utilisateur)

    Returns:
        {
            "archetype_code": str,
            "total_kwh": float,
            "by_usage": {
                "CVC_HVAC": {
                    "label": "Chauffage / Ventilation / Climatisation",
                    "kwh_total": 12500.0,
                    "kwh_hp": 11000.0,
                    "kwh_hc": 1500.0,
                    "share_total_pct": 40.0,
                    "fourniture_ht": 1300.0,
                    "reseau_ht": 400.0,
                    "taxes_ht": 180.0,
                    "abo_ht": 85.0,
                    "total_ht": 1965.0,
                    "tva": 393.0,
                    "ttc": 2358.0,
                },
                ...
            },
            "totals_check": {
                "sum_ttc_by_usage": 3200.0,
                "shadow_ttc": 3200.0,
                "residual_ttc": 0.0,
            },
            "method": "archetype_repartition",
            "confidence": "medium",
        }

    Note : les composantes HT sont ventilees proportionnellement a la conso kWh
    de chaque usage, sauf pour `expected_abo_ht` qui est partage uniformement
    (l'abonnement est lie au contrat, pas a l'usage). La TVA est recalculee
    sur le total HT par usage.
    """
    weights = override_weights or get_usage_repartition(archetype_code)

    total_kwh = float(shadow_bill.get("kwh", 0) or 0)
    fourniture_ht = float(shadow_bill.get("expected_fourniture_ht", 0) or 0)
    reseau_ht = float(shadow_bill.get("expected_reseau_ht", 0) or 0)
    taxes_ht = float(shadow_bill.get("expected_taxes_ht", 0) or 0)
    abo_ht = float(shadow_bill.get("expected_abo_ht", 0) or 0)
    expected_ttc = float(shadow_bill.get("expected_ttc", 0) or 0)

    # Normaliser les poids (au cas ou la somme ne fait pas 1.0)
    total_share = sum(hp + hc for hp, hc in weights.values())
    if total_share <= 0:
        return _empty_ventilation(archetype_code, total_kwh, expected_ttc)

    n_usages = max(len(weights), 1)
    abo_per_usage = abo_ht / n_usages  # abonnement partage uniformement

    by_usage: dict[str, dict] = {}
    sum_ttc = 0.0

    for usage_code, (share_hp, share_hc) in weights.items():
        share_total = share_hp + share_hc
        share_total_norm = share_total / total_share  # proportion effective

        kwh_total = round(total_kwh * share_total_norm, 1)
        kwh_hp = round(total_kwh * (share_hp / total_share), 1)
        kwh_hc = round(total_kwh * (share_hc / total_share), 1)

        # Ventilation proportionnelle de la fourniture, du reseau et des taxes
        fourniture = round(fourniture_ht * share_total_norm, 2)
        reseau = round(reseau_ht * share_total_norm, 2)
        taxes = round(taxes_ht * share_total_norm, 2)

        total_ht_usage = round(fourniture + reseau + taxes + abo_per_usage, 2)
        # TVA a 20% sur le total HT ventile (simplification : uniforme)
        tva_usage = round(total_ht_usage * 0.20, 2)
        ttc_usage = round(total_ht_usage + tva_usage, 2)

        by_usage[usage_code] = {
            "label": USAGE_LABELS.get(usage_code, usage_code),
            "kwh_total": kwh_total,
            "kwh_hp": kwh_hp,
            "kwh_hc": kwh_hc,
            "share_total_pct": round(share_total_norm * 100, 1),
            "fourniture_ht": fourniture,
            "reseau_ht": reseau,
            "taxes_ht": taxes,
            "abo_ht": round(abo_per_usage, 2),
            "total_ht": total_ht_usage,
            "tva": tva_usage,
            "ttc": ttc_usage,
        }
        sum_ttc += ttc_usage

    return {
        "archetype_code": archetype_code,
        "total_kwh": total_kwh,
        "by_usage": by_usage,
        "totals_check": {
            "sum_ttc_by_usage": round(sum_ttc, 2),
            "shadow_ttc": round(expected_ttc, 2),
            "residual_ttc": round(expected_ttc - sum_ttc, 2),
        },
        "method": "archetype_repartition",
        "confidence": "medium",
    }


def _empty_ventilation(archetype_code: str, total_kwh: float, expected_ttc: float) -> dict:
    return {
        "archetype_code": archetype_code,
        "total_kwh": total_kwh,
        "by_usage": {},
        "totals_check": {
            "sum_ttc_by_usage": 0.0,
            "shadow_ttc": round(expected_ttc, 2),
            "residual_ttc": round(expected_ttc, 2),
        },
        "method": "archetype_repartition",
        "confidence": "low",
    }
