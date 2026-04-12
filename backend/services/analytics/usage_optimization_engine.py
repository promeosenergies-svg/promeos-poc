"""
Etage 3 — Plan d'optimisation par usage avec ROI chiffre.

Croise :
- Decomposition CDC (etage 1 : disaggregate_site)
- Anomalies detectees (etage 2 : detect_usage_anomalies)
- Referentiel actions par usage (catalogue ci-dessous)

Pour produire un plan d'action ROI chiffre :
  usage X anomalie -> action concrete + gain kWh/EUR + investissement + payback

Sources gains :
- ADEME fiches CEE : gains % par action (10-30% selon action)
- IFPEB/ACTEE : couts d'investissement par m2/kW
- CEREN : intensite moyenne par usage (kWh/m2)
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

PRIX_MOY_EUR_KWH = 0.18
# Facteur d'utilisation moyen pour estimer la puissance installee depuis kWh/an
# P_installee = kWh_an / (8760 * facteur_utilisation)
# 0.25 = typique tertiaire (20-30% selon ADEME CEREN)
FACTEUR_UTILISATION_INVEST = 0.25


@dataclass
class OptimizationAction:
    """Une action d'optimisation chiffree sur un usage."""

    usage_code: str
    usage_label: str
    action_code: str
    action_title: str
    action_detail: str
    gain_kwh_an: float
    gain_eur_an: float
    investment_eur: float
    payback_months: int
    priority: int  # 1=quick win, 2=moyen terme, 3=structurant
    complexity: str  # simple | moderate | complex
    anomaly_source: Optional[str] = None  # type anomalie ayant declenche l'action


@dataclass
class OptimizationPlan:
    site_id: int
    site_nom: str
    archetype_code: str
    n_actions: int
    total_gain_eur_an: float
    total_investment_eur: float
    avg_payback_months: float
    actions: list[OptimizationAction]
    period_start: str
    period_end: str
    method: str = "usage_anomaly_x_catalog"


# Catalogue d'actions par (usage_code, anomaly_type)
# Chaque entree : gain_pct (% du kwh usage), investment_eur_per_kw, complexity
ACTION_CATALOG: dict[tuple[str, str], dict] = {
    ("CVC_HVAC", "CVC_NUIT_EXCESSIF"): {
        "action_code": "CVC_PROGRAMMATION_HORAIRE",
        "title": "Programmer arret CVC hors occupation",
        "detail": "Arreter la CVC 1h avant fermeture, redemarrer 30min avant ouverture (inertie thermique du batiment). Necessite une horloge ou un automate programmable sur la CVC.",
        "gain_pct": 0.20,
        "investment_per_kw": 50,  # EUR/kW installe
        "complexity": "simple",
        "priority": 1,
    },
    ("CVC_HVAC", "CVC_FAIBLE_CORRELATION_DJU"): {
        "action_code": "CVC_AUDIT_DIMENSIONNEMENT",
        "title": "Auditer le dimensionnement CVC",
        "detail": "Verifier les consignes de temperature, l'equilibrage du reseau, et le dimensionnement des equipements (PAC, chaudiere, CTA). Un surdimensionnement entraine des cycles courts et une surconsommation.",
        "gain_pct": 0.15,
        "investment_per_kw": 0,  # audit = temps, pas d'investissement materiel
        "complexity": "moderate",
        "priority": 2,
    },
    ("ECLAIRAGE", "ECLAIRAGE_NUIT"): {
        "action_code": "ECLAIRAGE_DETECTEURS_PRESENCE",
        "title": "Installer des detecteurs de presence",
        "detail": "Detecteurs de presence + horloge programmable dans les zones non occupees la nuit (couloirs, sanitaires, parkings). Gain immediat sans modification de l'installation electrique.",
        "gain_pct": 0.40,
        "investment_per_kw": 200,  # EUR/kW eclairage
        "complexity": "simple",
        "priority": 1,
    },
    ("ECS", "ECS_HP_AU_LIEU_HC"): {
        "action_code": "ECS_DECALAGE_HC",
        "title": "Decaler le ballon ECS en heures creuses",
        "detail": "Programmer le ballon ECS en heures creuses (22h-6h) ou en heures solaires 11h-14h (CRE delib. 2026-33). Contacteur HC ou horloge simple. Economie sur le delta prix HP/HC.",
        "gain_pct": 0.0,  # pas de gain kWh mais gain EUR (delta HP/HC)
        "investment_per_kw": 20,
        "complexity": "simple",
        "priority": 1,
        "gain_eur_override_per_kwh": 0.05,  # delta prix HP-HC ~0.05 EUR/kWh
    },
    ("CVC_HVAC", "SIMULTANEITE_CHAUD_FROID"): {
        "action_code": "CVC_BANDE_MORTE",
        "title": "Calibrer la bande morte chaud/froid",
        "detail": "Separer les consignes chauffage (ex: 20 degres C) et climatisation (ex: 24 degres C) "
        "avec une bande morte de 3-4 degres C pour eviter les conflits.",
        "gain_pct": 0.10,
        "investment_per_kw": 0,
        "complexity": "simple",
        "priority": 1,
    },
    ("GLOBAL", "DEPASSEMENT_PS_RISQUE"): {
        "action_code": "ECRETAGE_POINTE",
        "title": "Decaler les demarrages pour ecreter la pointe",
        "detail": "Programmer les demarrages d'equipements lourds (CVC, compresseurs) en cascade "
        "avec 5-10 min de decalage. Reduit le pic sans investissement.",
        "gain_pct": 0.0,
        "investment_per_kw": 0,
        "complexity": "simple",
        "priority": 1,
        "gain_eur_override_per_kwh": 0.01,
    },
    ("AIR_COMPRIME", "AIR_COMPRIME_FUITES"): {
        "action_code": "AIR_DETECTION_FUITES",
        "title": "Detecter et colmater les fuites d'air comprime",
        "detail": "Detection ultrasonore + reparation joints. 20-30% de la conso air comprime est due "
        "aux fuites (ADEME). CEE IND-UT-114 eligible.",
        "gain_pct": 0.25,
        "investment_per_kw": 20,
        "complexity": "simple",
        "priority": 1,
    },
    ("POMPES", "VENTILATION_24_7"): {
        "action_code": "VENTILATION_HYGROSTAT_CO",
        "title": "Installer detecteur CO + variateur ventilation parking",
        "detail": "Regulation sur demande (detection CO monoxyde) au lieu de fonctionnement 24/7. "
        "Reduction 65-75%. Payback 1-2 ans.",
        "gain_pct": 0.65,
        "investment_per_kw": 80,
        "complexity": "simple",
        "priority": 1,
    },
    ("FROID_COMMERCIAL", "FROID_SURCONSOMMATION"): {
        "action_code": "FROID_MAINTENANCE",
        "title": "Maintenance froid : condenseurs + joints + thermostat",
        "detail": "Nettoyage condenseurs (gain 10-15%), verification joints portes vitrines, "
        "calibrage thermostat. CEE BAT-EQ-130 eligible.",
        "gain_pct": 0.12,
        "investment_per_kw": 30,
        "complexity": "simple",
        "priority": 1,
    },
    ("FROID_INDUSTRIEL", "FROID_SURCONSOMMATION"): {
        "action_code": "FROID_INDUS_MAINTENANCE",
        "title": "Maintenance froid industriel + variateurs compresseurs",
        "detail": "Nettoyage evaporateurs, verification charge frigorique, variateurs sur compresseurs. "
        "CEE IND-UT-102 eligible. TRI 2-4 ans.",
        "gain_pct": 0.15,
        "investment_per_kw": 150,
        "complexity": "moderate",
        "priority": 2,
    },
    ("GLOBAL", "INTENSITE_ENERGETIQUE_ELEVEE"): {
        "action_code": "AUDIT_ENERGETIQUE_GLOBAL",
        "title": "Realiser un audit energetique",
        "detail": "Audit energetique reglementaire (Loi 2025-391) ou volontaire pour identifier les postes de surconsommation et etablir un plan d'actions prioritaires (quick wins + investissements structurants).",
        "gain_pct": 0.15,
        "investment_per_kw": 0,
        "complexity": "moderate",
        "priority": 2,
    },
    ("GLOBAL", "WEEKEND_EXCESSIF"): {
        "action_code": "GTC_PROGRAMMATION_WEEKEND",
        "title": "Couper les usages non essentiels le weekend",
        "detail": "Programmer l'arret automatique des usages non essentiels le weekend via la GTC/GTB : CVC, eclairage bureaux, bureautique. Conserver uniquement securite, froid (si alimentaire), et serveurs.",
        "gain_pct": 0.15,
        "investment_per_kw": 30,
        "complexity": "simple",
        "priority": 1,
    },
}

# Actions generiques par usage (si pas d'anomalie specifique detectee)
GENERIC_ACTIONS: dict[str, dict] = {
    "CVC_HVAC": {
        "action_code": "CVC_OPTIMISATION_CONSIGNES",
        "title": "Optimiser les consignes de temperature",
        "detail": "Reduire la consigne de 1 degre C en hiver (chauffage 19 degres C au lieu de 20) = ~7% d'economie sur le poste CVC (ADEME). Verifier l'absence de consignes contradictoires (chaud+froid simultane).",
        "gain_pct": 0.07,
        "investment_per_kw": 0,
        "complexity": "simple",
        "priority": 1,
    },
    "ECLAIRAGE": {
        "action_code": "ECLAIRAGE_LED_RETROFIT",
        "title": "Remplacer l'eclairage par des LED",
        "detail": "Retrofit LED sur les luminaires existants : gain 40-60% sur le poste eclairage. Eligibilite CEE BAR-EQ-110 (prime 2-5 EUR/tube). TRI typique < 3 ans.",
        "gain_pct": 0.50,
        "investment_per_kw": 500,
        "complexity": "simple",
        "priority": 1,
    },
    "IRVE": {
        "action_code": "IRVE_PILOTAGE_INTELLIGENT",
        "title": "Installer un pilotage intelligent IRVE",
        "detail": "Pilotage OCPP pour decaler la charge en heures creuses ou heures solaires. Gain HP/HC + contribution NEBCO si agregation > 100 kW.",
        "gain_pct": 0.0,
        "investment_per_kw": 100,
        "complexity": "simple",
        "priority": 2,
        "gain_eur_override_per_kwh": 0.04,
    },
    "ECS": {
        "action_code": "ECS_PROGRAMMATION_HC",
        "title": "Programmer le ballon ECS en heures creuses",
        "detail": "Decaler la production ECS en heures creuses (22h-6h) ou heures solaires 11h-14h (CRE delib. 2026-33). Contacteur HC ou horloge simple. Gain sur le delta prix HP/HC.",
        "gain_pct": 0.0,
        "investment_per_kw": 20,
        "complexity": "simple",
        "priority": 1,
        "gain_eur_override_per_kwh": 0.05,
    },
    "FROID_COMMERCIAL": {
        "action_code": "FROID_MAINTENANCE_PREVENTIVE",
        "title": "Optimiser la maintenance du froid commercial",
        "detail": "Nettoyage condenseurs (gain 10-15%), verification joints de portes vitrines, consignes temperature (gain 3%/degre). CEE BAT-EQ-130 eligible.",
        "gain_pct": 0.12,
        "investment_per_kw": 30,
        "complexity": "simple",
        "priority": 1,
    },
    "FROID_INDUSTRIEL": {
        "action_code": "FROID_INDUS_VARIATEUR",
        "title": "Installer des variateurs sur les compresseurs froid",
        "detail": "Variateurs de vitesse sur compresseurs frigorifiques : gain 15-25% sur le poste froid. CEE IND-UT-102 eligible. TRI typique 2-4 ans.",
        "gain_pct": 0.20,
        "investment_per_kw": 150,
        "complexity": "moderate",
        "priority": 2,
    },
    "AIR_COMPRIME": {
        "action_code": "AIR_COMPRIME_FUITES",
        "title": "Detecter et reparer les fuites d'air comprime",
        "detail": "Les fuites representent 20-30% de la conso air comprime (ADEME). Detection ultrasonore + reparation : gain immediat, investissement faible. CEE IND-UT-114.",
        "gain_pct": 0.25,
        "investment_per_kw": 20,
        "complexity": "simple",
        "priority": 1,
    },
    "POMPES": {
        "action_code": "POMPES_VARIATEUR_VITESSE",
        "title": "Installer des variateurs de vitesse sur les pompes",
        "detail": "Variateurs de vitesse sur pompes de circulation : gain 20-40% (loi d'affinite P proportionnel a N^3). CEE IND-UT-102 eligible.",
        "gain_pct": 0.30,
        "investment_per_kw": 120,
        "complexity": "moderate",
        "priority": 2,
    },
    "DATA_CENTER": {
        "action_code": "DATA_CENTER_FREE_COOLING",
        "title": "Deployer le free-cooling sur les salles IT",
        "detail": "Free-cooling air exterieur quand T_ext < 18 degres C (300-400h/an en IDF). Gain 15-25% sur la climatisation IT. PUE cible < 1.4.",
        "gain_pct": 0.15,
        "investment_per_kw": 200,
        "complexity": "moderate",
        "priority": 2,
    },
}


def generate_optimization_plan(
    db: Session,
    site_id: int,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    disagg_result=None,
    anomalies_result=None,
) -> OptimizationPlan:
    """
    Genere un plan d'optimisation pour un site en croisant :
    1. La decomposition CDC par usage (etage 1)
    2. Les anomalies detectees (etage 2)
    3. Le catalogue d'actions (etage 3)

    Args:
        disagg_result: optionnel — reutilise une decomposition deja calculee.
        anomalies_result: optionnel — reutilise des anomalies deja detectees.
    """
    from services.analytics.usage_disaggregation import disaggregate_site
    from services.analytics.usage_anomaly_detector import detect_usage_anomalies
    from models.site import Site

    if date_fin is None:
        date_fin = date.today()
    if date_debut is None:
        date_debut = date_fin - timedelta(days=365)

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} non trouve")

    # Etage 1 : decomposition (reutilise si fourni)
    disagg = disagg_result or disaggregate_site(db, site_id, date_debut, date_fin)
    usage_by_code = {u.code: u for u in disagg.usages}

    # Etage 2 : anomalies (reutilise si fourni, sinon calcule avec disagg)
    anomalies = anomalies_result or detect_usage_anomalies(db, site_id, date_debut, date_fin, disagg_result=disagg)

    actions: list[OptimizationAction] = []

    # Actions basees sur les anomalies detectees
    for anom in anomalies.anomalies:
        key = (anom.usage_code, anom.anomaly_type)
        catalog_entry = ACTION_CATALOG.get(key)
        if not catalog_entry:
            continue

        usage = usage_by_code.get(anom.usage_code)
        usage_kwh = usage.kwh if usage else anom.gain_kwh_an

        gain_kwh = round(usage_kwh * catalog_entry["gain_pct"], 0) if catalog_entry["gain_pct"] > 0 else 0
        gain_eur_override = catalog_entry.get("gain_eur_override_per_kwh")
        if gain_eur_override and usage_kwh > 0:
            gain_eur = round(usage_kwh * gain_eur_override, 0)
        else:
            gain_eur = round(gain_kwh * PRIX_MOY_EUR_KWH, 0)

        investment = round(
            catalog_entry["investment_per_kw"] * (usage_kwh / (8760 * FACTEUR_UTILISATION_INVEST))
            if usage_kwh > 0
            else 0,
            0,
        )
        payback = int(investment / gain_eur * 12) if gain_eur > 0 else 999

        actions.append(
            OptimizationAction(
                usage_code=anom.usage_code,
                usage_label=anom.usage_label,
                action_code=catalog_entry["action_code"],
                action_title=catalog_entry["title"],
                action_detail=catalog_entry["detail"],
                gain_kwh_an=gain_kwh,
                gain_eur_an=gain_eur,
                investment_eur=investment,
                payback_months=min(payback, 999),
                priority=catalog_entry["priority"],
                complexity=catalog_entry["complexity"],
                anomaly_source=anom.anomaly_type,
            )
        )

    # Actions generiques sur les usages non couverts par une anomalie
    anomaly_usages = {a.usage_code for a in actions}
    for usage in disagg.usages:
        if usage.code in anomaly_usages or usage.code in ("AUTRES", "SECURITE_VEILLE"):
            continue
        generic = GENERIC_ACTIONS.get(usage.code)
        if not generic:
            continue

        gain_kwh = round(usage.kwh * generic["gain_pct"], 0) if generic["gain_pct"] > 0 else 0
        gain_eur_override = generic.get("gain_eur_override_per_kwh")
        if gain_eur_override and usage.kwh > 0:
            gain_eur = round(usage.kwh * gain_eur_override, 0)
        else:
            gain_eur = round(gain_kwh * PRIX_MOY_EUR_KWH, 0)

        investment = round(
            generic["investment_per_kw"] * (usage.kwh / (8760 * FACTEUR_UTILISATION_INVEST)) if usage.kwh > 0 else 0, 0
        )
        payback = int(investment / gain_eur * 12) if gain_eur > 0 else 999

        if gain_eur < 50:
            continue  # pas d'action si gain < 50 EUR/an

        actions.append(
            OptimizationAction(
                usage_code=usage.code,
                usage_label=usage.label,
                action_code=generic["action_code"],
                action_title=generic["title"],
                action_detail=generic["detail"],
                gain_kwh_an=gain_kwh,
                gain_eur_an=gain_eur,
                investment_eur=investment,
                payback_months=min(payback, 999),
                priority=generic["priority"],
                complexity=generic["complexity"],
                anomaly_source=None,
            )
        )

    # Trier par payback croissant (quick wins en premier)
    actions.sort(key=lambda a: (a.priority, a.payback_months))

    total_gain = sum(a.gain_eur_an for a in actions)
    total_invest = sum(a.investment_eur for a in actions)
    avg_payback = sum(a.payback_months for a in actions if a.payback_months < 999) / max(
        sum(1 for a in actions if a.payback_months < 999), 1
    )

    return OptimizationPlan(
        site_id=site_id,
        site_nom=site.nom,
        archetype_code=disagg.archetype_code,
        n_actions=len(actions),
        total_gain_eur_an=round(total_gain, 0),
        total_investment_eur=round(total_invest, 0),
        avg_payback_months=round(avg_payback, 1),
        actions=actions,
        period_start=date_debut.isoformat(),
        period_end=date_fin.isoformat(),
    )
