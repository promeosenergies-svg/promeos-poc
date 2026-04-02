"""
Moteur d'éligibilité NEBCO (Notification d'Échanges de Blocs de Consommation).
Remplace NEBEF depuis 01/09/2025.

Différences majeures vs NEBEF :
1. 3 types de modulation : EFFACEMENT / ANTICIPATION / REPORT
2. Discipline de décalage : vol_hausse ≤ vol_baisse sur 7j (télérelevé) / 2j (profilé)
3. Versement fournisseur NET = (vol_baisse − vol_hausse) × barème
4. Seuil : 100 kW PAR PAS DE CONTRÔLE (réglementaire)

Sources : RM-5-NEBCO-V01, Code énergie L271-1, CRE délib. 31/07/2025.
"""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from models.power import NebcoModulationType, NebcoEligibilityStatus
from services.power.power_profile_service import get_power_profile, get_active_contract

SEUIL_NEBCO_KW = 100.0
SEUIL_PANELS_SITES = 500
RATIO_DECALAGE_TELERELEVE_JOURS = 7
RATIO_DECALAGE_PROFILE_JOURS = 2
TOLERANCE_BILAN_MENSUEL = 0.05
REVENU_CENTRAL = 140.0
REVENU_MIN = 80.0
REVENU_MAX = 200.0

CVC_PILOTABLE_PCT = {
    "BUREAU_STANDARD": {"baisse": 0.35, "hausse": 0.20},
    "HOTEL_HEBERGEMENT": {"baisse": 0.40, "hausse": 0.25},
    "ENSEIGNEMENT": {"baisse": 0.30, "hausse": 0.15},
    "LOGISTIQUE_SEC": {"baisse": 0.20, "hausse": 0.35},
    "COMMERCE_ALIMENTAIRE": {"baisse": 0.55, "hausse": 0.40},
    "DEFAULT": {"baisse": 0.25, "hausse": 0.15},
}

COMPTEURS_TELERELEVE = {"PME-PMI", "ICE", "SAPHIR", "CVE", "CJE", "CVEM1", "CVEM2", "CVEM3"}


def check_nebco_eligibility(
    db: Session,
    meter_id: int,
    site_archetype: str = "DEFAULT",
    tarif_central: float = REVENU_CENTRAL,
    tarif_min: float = REVENU_MIN,
    tarif_max: float = REVENU_MAX,
    n_sites_portefeuille: int = 1,
) -> dict:
    """Évalue l'éligibilité NEBCO avec 3 types de modulation et discipline décalage."""
    date_fin = date.today()
    date_debut = date_fin - timedelta(days=365)

    profile = get_power_profile(db, meter_id, date_debut, date_fin)
    contract = get_active_contract(db, meter_id, date_fin)

    base = {
        "meter_id": meter_id,
        "source": "nebco_eligibility_engine",
        "computed_at": datetime.now().isoformat(),
    }

    if not profile.get("data_available"):
        return {
            **base,
            "eligible": False,
            "eligible_technique": False,
            "statut": NebcoEligibilityStatus.NON_ELIGIBLE.value,
            "raison": "Données insuffisantes",
            "confidence": 0,
        }

    P_max = profile["kpis"]["P_max_kw"]
    completude = profile["completude_pct"]
    type_compteur = contract.type_compteur if contract else None
    is_telereleve = type_compteur in COMPTEURS_TELERELEVE

    # No-go rules
    no_go = []
    if P_max < SEUIL_NEBCO_KW:
        no_go.append(
            {
                "code": "P_MAX_INSUFFISANT",
                "message": f"P_max = {P_max:.1f} kW < seuil NEBCO {SEUIL_NEBCO_KW} kW. "
                "Optimisation tarifaire uniquement disponible.",
                "bloquant": True,
            }
        )
    if not is_telereleve and type_compteur == "Linky" and n_sites_portefeuille < SEUIL_PANELS_SITES:
        no_go.append(
            {
                "code": "PANELS_PORTEFEUILLE_INSUFFISANT",
                "message": f"Méthode panels NEBCO requiert ≥ {SEUIL_PANELS_SITES} sites Linky. "
                f"Portefeuille actuel : {n_sites_portefeuille} sites.",
                "bloquant": True,
            }
        )

    checklist = [
        {
            "critere": f"P_max ≥ {SEUIL_NEBCO_KW} kW par pas de contrôle",
            "ok": P_max >= SEUIL_NEBCO_KW,
            "bloquant": True,
            "source": "RM-5-NEBCO-V01",
        },
        {
            "critere": "Compteur télérelevé ou Linky",
            "ok": is_telereleve or type_compteur == "Linky",
            "bloquant": True,
            "source": "RM-5-NEBCO-V01 §3",
        },
        {
            "critere": "Historique ≥ 12 mois (complétude > 50%)",
            "ok": completude >= 50.0,
            "bloquant": True,
            "source": "RM-5-NEBCO-V01",
        },
        {
            "critere": "Accord client + rattachement périmètre",
            "ok": None,
            "bloquant": True,
            "source": "Code énergie L271-1",
        },
        {"critere": "GTB/EMS commande J-1/intraday", "ok": None, "bloquant": True, "source": "RM-5-NEBCO-V01 §4"},
        {"critere": "Opérateur d'effacement agréé RTE", "ok": None, "bloquant": True, "source": "Code énergie L271-2"},
        {"critere": "Discipline de décalage applicable", "ok": True, "bloquant": False, "source": "RM-5-NEBCO-V01 §5"},
        {"critere": "Pas d'offre EIF conflictuelle", "ok": None, "bloquant": False, "source": "RM-5-NEBCO-V01 §6"},
        {"critere": "Capacité M&V et audit trail", "ok": None, "bloquant": False, "source": "Exigence opérationnelle"},
    ]

    eligible_technique = P_max >= SEUIL_NEBCO_KW and all(
        c["ok"] is True for c in checklist if c["bloquant"] and c["ok"] is not None
    )
    eligible = P_max >= SEUIL_NEBCO_KW and all(c["ok"] is True for c in checklist if c["bloquant"])

    statut = (
        NebcoEligibilityStatus.ELIGIBLE
        if eligible
        else NebcoEligibilityStatus.ELIGIBLE_TECHNIQUE
        if eligible_technique
        else NebcoEligibilityStatus.NON_ELIGIBLE
    ).value

    # Types de modulation NEBCO (3 vs 1 pour NEBEF)
    taux = CVC_PILOTABLE_PCT.get(site_archetype, CVC_PILOTABLE_PCT["DEFAULT"])
    P_effacable = round(P_max * taux["baisse"], 1)
    P_anticipable = round(P_max * taux["hausse"], 1)

    modulation_types = []
    if P_effacable > 0:
        modulation_types.append(
            {
                "type": NebcoModulationType.EFFACEMENT.value,
                "P_kw": P_effacable,
                "description": "Baisse de consommation — signal prix élevés/pointe",
            }
        )
    if P_anticipable > 0:
        modulation_types.append(
            {
                "type": NebcoModulationType.ANTICIPATION.value,
                "P_kw": P_anticipable,
                "description": "Hausse avant effacement — signal prix négatifs/bas",
            }
        )
        modulation_types.append(
            {
                "type": NebcoModulationType.REPORT.value,
                "P_kw": P_anticipable,
                "description": "Hausse après effacement — gestion rebond thermique",
            }
        )

    # Potentiel revenu
    potentiel = None
    if eligible_technique:
        rev_central = round(P_effacable * tarif_central)
        potentiel = {
            "P_effacable_kw": P_effacable,
            "P_anticipable_kw": P_anticipable,
            "P_pilotable_total_kw": round(P_effacable + P_anticipable, 1),
            "revenu_min_eur_an": round(P_effacable * tarif_min),
            "revenu_central_eur_an": rev_central,
            "revenu_max_eur_an": round(P_effacable * tarif_max),
            "calcul": {
                "formule": f"{P_effacable} kW × {tarif_central} €/kW/an = {rev_central} €/an",
                "source_tarif": "Données marché agrégateurs FR (fourchette 80–200 €/kW/an)",
                "note_versement": "Revenu BRUT — versement fournisseur net à déduire",
            },
        }

    # Justification
    if eligible and potentiel:
        justification = f"Éligible NEBCO — P_max {P_max:.1f} kW. Effaçable : {P_effacable} kW."
    elif eligible_technique:
        ko_manual = [c["critere"] for c in checklist if c["bloquant"] and c["ok"] is None]
        justification = f"Éligible techniquement — à valider : {', '.join(ko_manual[:2])}"
    else:
        ko = [c["critere"] for c in checklist if c["bloquant"] and c["ok"] is False]
        justification = f"Non éligible — {', '.join(ko[:2])}" if ko else "Non éligible"

    return {
        **base,
        "eligible": eligible,
        "eligible_technique": eligible_technique,
        "statut": statut,
        "P_max_kw": round(P_max, 1),
        "seuil_nebco_kw": SEUIL_NEBCO_KW,
        "type_compteur": type_compteur,
        "is_telereleve": is_telereleve,
        "checklist": checklist,
        "modulation_types": modulation_types,
        "discipline_decalage": {
            "regle": f"Volume hausse ≤ volume baisse sur {RATIO_DECALAGE_TELERELEVE_JOURS}j (télérelevé) "
            f"/ {RATIO_DECALAGE_PROFILE_JOURS}j (profilé)",
            "bilan_mensuel": f"BEner_M ≥ −{TOLERANCE_BILAN_MENSUEL * 100:.0f}% × VR_Baisse",
            "source": "RM-5-NEBCO-V01 §5",
        },
        "versement_fournisseur": {
            "principe": "Versement net = max(0, vol_baisse − vol_hausse) × barème régulé",
            "impact": "Les modulations à la hausse réduisent le versement net",
            "source": "Code énergie L271-3",
        },
        "no_go_rules": no_go,
        "potentiel": potentiel,
        "justification": justification,
        "promesse_tenable": (
            "PROMEOS identifie et quantifie la flexibilité exploitable (tarifaire + pointe) "
            "et fournit la preuve de l'impact. Pour les clients éligibles, PROMEOS prépare "
            "et supervise l'exécution NEBCO via un opérateur agréé, sans promettre un revenu garanti."
        ),
        "confidence": round(completude / 100, 2),
    }
