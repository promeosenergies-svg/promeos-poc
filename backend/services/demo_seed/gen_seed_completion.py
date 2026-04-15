"""
PROMEOS — Seed Completion for HELIOS demo (Phase 1.2-1.9).
Fills gaps identified by Phase 0 audit without modifying existing generators.

Usage: called from orchestrator after all existing generators.
"""

import hashlib
import json
import logging
import random
import uuid
from datetime import datetime, timedelta, date, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

HELIOS_CITIES = ["paris", "lyon", "marseille", "nice", "toulouse"]


def _build_site_map(sites: list) -> dict:
    """Map lowercase city keyword → Site object for HELIOS sites."""
    result = {}
    for s in sites:
        nom_lower = s.nom.lower()
        for city in HELIOS_CITIES:
            if city in nom_lower:
                result[city] = s
                break
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1.2 — APER: augmenter parking/roof au-dessus des seuils réglementaires
# Seuils APER: parking ≥ 1500 m², toit ≥ 500 m²
# ──────────────────────────────────────────────────────────────────────────────

APER_OVERRIDES = {
    "paris": {"parking_area_m2": 2200, "roof_area_m2": 900},
    "lyon": {"parking_area_m2": 500, "roof_area_m2": 350},  # sous seuils → pas assujetti
    "toulouse": {"parking_area_m2": 3500, "roof_area_m2": 3200},  # entrepôt → gros parking + toiture
    "nice": {"parking_area_m2": 1800, "roof_area_m2": 1600},  # hôtel → parking client + toit plat
    "marseille": {"parking_area_m2": 2000, "roof_area_m2": 1400},  # école → parking + préau
}


def seed_aper_fields(db: Session, sites: list) -> int:
    """Met à jour parking_area_m2 et roof_area_m2 pour déclencher APER."""
    from models.site import Site

    updated = 0
    for site in sites:
        nom_lower = site.nom.lower()
        for city, vals in APER_OVERRIDES.items():
            if city in nom_lower:
                changed = False
                if (site.parking_area_m2 or 0) < vals["parking_area_m2"]:
                    site.parking_area_m2 = vals["parking_area_m2"]
                    changed = True
                if (site.roof_area_m2 or 0) < vals["roof_area_m2"]:
                    site.roof_area_m2 = vals["roof_area_m2"]
                    changed = True
                if changed:
                    updated += 1
                break
    db.flush()
    return updated


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1.4 — DataPoints RTE CO2 + PVGIS
# ──────────────────────────────────────────────────────────────────────────────

# Intensité carbone moyenne France métropolitaine (gCO2/kWh) par mois
# Source: RTE éCO2mix 2024-2025 — hiver plus carboné (appels centrales gaz)
CO2_INTENSITY_BY_MONTH = {
    1: 62,
    2: 58,
    3: 48,
    4: 38,
    5: 35,
    6: 42,
    7: 45,
    8: 43,
    9: 40,
    10: 44,
    11: 55,
    12: 65,
}

PVGIS_ESTIMATES = [
    {"city": "paris", "lat": 48.86, "lon": 2.35, "irradiance_kwh_m2": 1150, "efficiency": 0.165},
    {"city": "lyon", "lat": 45.76, "lon": 4.83, "irradiance_kwh_m2": 1300, "efficiency": 0.165},
    {"city": "marseille", "lat": 43.30, "lon": 5.37, "irradiance_kwh_m2": 1600, "efficiency": 0.165},
    {"city": "nice", "lat": 43.71, "lon": 7.26, "irradiance_kwh_m2": 1550, "efficiency": 0.165},
    {"city": "toulouse", "lat": 43.60, "lon": 1.44, "irradiance_kwh_m2": 1400, "efficiency": 0.165},
]


def seed_datapoints(db: Session, sites: list) -> int:
    from models.datapoint import DataPoint
    from models.enums import SourceType

    now = datetime.now(timezone.utc)
    created = 0

    # 12 mois CO2 intensity (idempotent per source)
    co2_exists = db.query(DataPoint).filter(DataPoint.source_name == "rte_eco2mix").count() > 0
    if not co2_exists:
        for month_offset in range(12):
            dt = now - timedelta(days=30 * month_offset)
            ts_start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ts_end = (ts_start + timedelta(days=32)).replace(day=1)
            month = ts_start.month
            co2 = CO2_INTENSITY_BY_MONTH.get(month, 50)

            db.add(
                DataPoint(
                    object_type="grid",
                    object_id=0,
                    metric="co2_intensity_g_kwh",
                    ts_start=ts_start,
                    ts_end=ts_end,
                    value=float(co2),
                    unit="gCO2/kWh",
                    source_type=SourceType.API,
                    source_name="rte_eco2mix",
                    quality_score=0.95,
                    coverage_ratio=1.0,
                    retrieved_at=now,
                    source_ref="https://www.rte-france.com/eco2mix",
                )
            )
            created += 1

    # PVGIS par site (independent idempotence)
    pvgis_exists = db.query(DataPoint).filter(DataPoint.source_name == "pvgis_eu").count() > 0
    if not pvgis_exists:
        site_map = _build_site_map(sites)

        for pv in PVGIS_ESTIMATES:
            site = site_map.get(pv["city"])
            if not site:
                continue
            roof_m2 = site.roof_area_m2 or 500
            kwh_year = round(roof_m2 * pv["irradiance_kwh_m2"] * pv["efficiency"])

            db.add(
                DataPoint(
                    object_type="site",
                    object_id=site.id,
                    metric="pv_prod_estimate_kwh_year",
                    ts_start=now.replace(month=1, day=1),
                    ts_end=now.replace(month=12, day=31),
                    value=float(kwh_year),
                    unit="kWh/year",
                    source_type=SourceType.API,
                    source_name="pvgis_eu",
                    quality_score=0.85,
                    coverage_ratio=1.0,
                    retrieved_at=now,
                    source_ref=json.dumps(
                        {
                            "lat": pv["lat"],
                            "lon": pv["lon"],
                            "roof_area_m2": roof_m2,
                            "irradiance_kwh_m2": pv["irradiance_kwh_m2"],
                        }
                    ),
                )
            )
            created += 1

    db.flush()
    return created


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1.5 — RegSourceEvents (veille réglementaire)
# ──────────────────────────────────────────────────────────────────────────────

REG_EVENTS_DATA = [
    {
        "source_name": "cre",
        "title": "TURPE 7 — Nouveaux tarifs d'acheminement en vigueur",
        "snippet": "Délibération CRE n°2025-78 : grilles TURPE 7 applicables au 1er août 2025. Hausse moyenne +3,4% HTA, +5,2% BT>36kVA.",
        "tags": "turpe,reseau,tarif",
        "published_at": datetime(2025, 8, 1),
    },
    {
        "source_name": "legifrance",
        "title": "Décret BACS — Seuil 290 kW applicable",
        "snippet": "Décret n°2020-887 modifié : systèmes CVC > 290 kW doivent être équipés d'un BACS classe B. Seuil 70 kW au 01/01/2027.",
        "tags": "bacs,cvc,conformite",
        "published_at": datetime(2025, 1, 1),
    },
    {
        "source_name": "legifrance",
        "title": "Loi APER — Obligations solaires parkings et toitures",
        "snippet": "Loi n°2023-175 art. 40-42 : parkings ≥ 1500 m² couverture PV obligatoire (50%). Toitures neuves ≥ 500 m² : étude faisabilité.",
        "tags": "aper,solaire,parking,toiture",
        "published_at": datetime(2025, 3, 14),
    },
    {
        "source_name": "cre",
        "title": "Post-ARENH — VNU (Versement Nucléaire Universel) en vigueur",
        "snippet": "Fin ARENH 31/12/2025. Loi n°2023-491 : VNU = 1/3 volume nucléaire à prix CRE. Obligation fournisseurs alternatifs.",
        "tags": "vnu,arenh,nucleaire,fournisseur",
        "published_at": datetime(2026, 1, 1),
    },
    {
        "source_name": "legifrance",
        "title": "Audit énergétique — Deadline 11 octobre 2026",
        "snippet": "Loi 2025-391 art. 3 : entreprises > 2,75 GWh audit tous les 4 ans. > 23,6 GWh : ISO 50001. Échéance : 11/10/2026.",
        "tags": "audit,sme,iso50001",
        "published_at": datetime(2025, 4, 30),
    },
    {
        "source_name": "cre",
        "title": "HC Méridiennes 11h-14h — Nouveau calendrier heures creuses",
        "snippet": "Délib. CRE 2026-33 : nouvelles souscriptions C5 incluent HC 11h-14h (solaires) en plus des plages nocturnes classiques.",
        "tags": "hc,meridiennes,tarif,turpe",
        "published_at": datetime(2026, 2, 4),
    },
]


def seed_reg_source_events(db: Session) -> int:
    from models.reg_source_event import RegSourceEvent
    from models.enums import WatcherEventStatus

    created = 0
    for evt in REG_EVENTS_DATA:
        content_hash = hashlib.sha256(evt["title"].encode()).hexdigest()[:64]
        dedup_key = f"seed-helios:{content_hash[:32]}"

        existing = db.query(RegSourceEvent).filter_by(dedup_key=dedup_key).first()
        if existing:
            continue

        db.add(
            RegSourceEvent(
                source_name=evt["source_name"],
                title=evt["title"],
                snippet=evt["snippet"],
                tags=evt["tags"],
                published_at=evt["published_at"],
                retrieved_at=datetime.now(timezone.utc),
                content_hash=content_hash,
                dedup_key=dedup_key,
                status=WatcherEventStatus.NEW,
            )
        )
        created += 1

    db.flush()
    return created


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1.6 — Purchase assumptions pour les 3 sites manquants
# ──────────────────────────────────────────────────────────────────────────────


def seed_purchase_completion(db: Session, sites: list, rng: random.Random) -> dict:
    from models.purchase_models import PurchaseAssumptionSet, PurchaseScenarioResult
    from models.enums import BillingEnergyType, PurchaseStrategy, PurchaseRecoStatus

    created_ass = 0
    created_res = 0

    for site in sites:
        existing = db.query(PurchaseAssumptionSet).filter_by(site_id=site.id).first()
        if existing:
            continue

        annual_kwh = site.annual_kwh_total or (site.surface_m2 or 1000) * 170
        profile_factor = round(rng.uniform(0.85, 1.3), 2)

        ass = PurchaseAssumptionSet(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            volume_kwh_an=annual_kwh,
            profile_factor=profile_factor,
            horizon_months=rng.choice([12, 24, 36]),
        )
        db.add(ass)
        db.flush()
        created_ass += 1

        run_id = str(uuid.uuid4())
        for strategy, price_mult, risk in [
            (PurchaseStrategy.FIXE, 1.0, 20),
            (PurchaseStrategy.INDEXE, 0.92, 55),
            (PurchaseStrategy.SPOT, 0.85, 80),
        ]:
            base_price = round(rng.uniform(0.12, 0.22) * price_mult, 4)
            total = round(annual_kwh * base_price, 2)
            is_reco = strategy == PurchaseStrategy.FIXE

            db.add(
                PurchaseScenarioResult(
                    run_id=run_id,
                    assumption_set_id=ass.id,
                    strategy=strategy,
                    price_eur_per_kwh=base_price,
                    total_annual_eur=total,
                    risk_score=risk + rng.randint(-10, 10),
                    savings_vs_current_pct=round((1.0 - price_mult) * 100, 1),
                    p10_eur=round(total * 0.85, 2),
                    p90_eur=round(total * 1.20, 2),
                    is_recommended=is_reco,
                    reco_status=PurchaseRecoStatus.DRAFT,
                )
            )
            created_res += 1

    db.flush()
    return {"assumptions": created_ass, "results": created_res}


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1.7 — Actions extra (15 → 35+, 7 source_types)
# ──────────────────────────────────────────────────────────────────────────────

EXTRA_ACTIONS = [
    # purchase (3)
    {
        "title": "Renouveler contrat Paris — échéance 3 mois",
        "source_type": "PURCHASE",
        "city": "paris",
        "status": "OPEN",
        "priority": 1,
        "severity": "high",
        "category": "finance",
        "gain": 12000,
    },
    {
        "title": "Simuler passage Tarif Heures Solaires — Lyon",
        "source_type": "PURCHASE",
        "city": "lyon",
        "status": "IN_PROGRESS",
        "priority": 2,
        "severity": "medium",
        "category": "finance",
        "gain": 4500,
    },
    {
        "title": "Optimiser profil achat Nice — arbitrage HP/HC",
        "source_type": "PURCHASE",
        "city": "nice",
        "status": "OPEN",
        "priority": 3,
        "severity": "medium",
        "category": "finance",
        "gain": 6000,
    },
    # manual (3)
    {
        "title": "Audit terrain site Lyon — contrôle GTB",
        "source_type": "MANUAL",
        "city": "lyon",
        "status": "DONE",
        "priority": 4,
        "severity": "low",
        "category": "maintenance",
    },
    {
        "title": "Mettre à jour fiche site Marseille (surface vérifiée)",
        "source_type": "MANUAL",
        "city": "marseille",
        "status": "DONE",
        "priority": 5,
        "severity": "low",
        "category": "maintenance",
    },
    {
        "title": "Former le responsable site Toulouse sur le tableau de bord",
        "source_type": "MANUAL",
        "city": "toulouse",
        "status": "IN_PROGRESS",
        "priority": 4,
        "severity": "low",
        "category": "maintenance",
    },
    # compliance extra (3)
    {
        "title": "Préparer dossier BACS inspection Nice",
        "source_type": "COMPLIANCE",
        "city": "nice",
        "status": "IN_PROGRESS",
        "priority": 1,
        "severity": "high",
        "category": "conformite",
        "gain": 0,
    },
    {
        "title": "Installer BACS classe B — Toulouse entrepôt",
        "source_type": "COMPLIANCE",
        "city": "toulouse",
        "status": "OPEN",
        "priority": 1,
        "severity": "high",
        "category": "conformite",
        "gain": 0,
    },
    {
        "title": "Étude faisabilité solaire parking Marseille (APER)",
        "source_type": "COMPLIANCE",
        "city": "marseille",
        "status": "IN_PROGRESS",
        "priority": 2,
        "severity": "medium",
        "category": "conformite",
    },
    # consumption extra (3)
    {
        "title": "Réduire baseload nuit Paris — ventilation 24/7 détectée",
        "source_type": "CONSUMPTION",
        "city": "paris",
        "status": "OPEN",
        "priority": 1,
        "severity": "high",
        "category": "energie",
        "gain": 8500,
    },
    {
        "title": "Anomalie weekend Marseille — école chauffée samedi",
        "source_type": "CONSUMPTION",
        "city": "marseille",
        "status": "IN_PROGRESS",
        "priority": 2,
        "severity": "medium",
        "category": "energie",
        "gain": 3200,
    },
    {
        "title": "Optimiser puissance souscrite Lyon (dépassements fréquents)",
        "source_type": "CONSUMPTION",
        "city": "lyon",
        "status": "OPEN",
        "priority": 2,
        "severity": "medium",
        "category": "energie",
        "gain": 5000,
    },
    # billing extra (3)
    {
        "title": "Contester surfacturation Nice mars 2025 (R1)",
        "source_type": "BILLING",
        "city": "nice",
        "status": "OPEN",
        "priority": 1,
        "severity": "high",
        "category": "finance",
        "gain": 3400,
    },
    {
        "title": "Vérifier composante réseau TURPE 7 Paris",
        "source_type": "BILLING",
        "city": "paris",
        "status": "DONE",
        "priority": 3,
        "severity": "medium",
        "category": "finance",
    },
    {
        "title": "Régulariser trou facturation Toulouse Q3",
        "source_type": "BILLING",
        "city": "toulouse",
        "status": "IN_PROGRESS",
        "priority": 2,
        "severity": "medium",
        "category": "finance",
    },
    # insight (KB reco) extra (2)
    {
        "title": "Appliquer reco archetype HOTEL : consignes CVC nuit",
        "source_type": "INSIGHT",
        "city": "nice",
        "status": "IN_PROGRESS",
        "priority": 2,
        "severity": "medium",
        "category": "energie",
        "gain": 7200,
    },
    {
        "title": "Planifier audit éclairage LED — Lyon bureaux",
        "source_type": "INSIGHT",
        "city": "lyon",
        "status": "OPEN",
        "priority": 3,
        "severity": "low",
        "category": "energie",
        "gain": 2800,
    },
    # cancelled (2)
    {
        "title": "PV toiture Lyon (abandonné — surface insuffisante)",
        "source_type": "COMPLIANCE",
        "city": "lyon",
        "status": "FALSE_POSITIVE",
        "priority": 5,
        "severity": "low",
        "category": "conformite",
    },
    {
        "title": "Étude délestage Marseille (non pertinent école)",
        "source_type": "INSIGHT",
        "city": "marseille",
        "status": "FALSE_POSITIVE",
        "priority": 5,
        "severity": "low",
        "category": "energie",
    },
    # copilot (1)
    {
        "title": "Copilot : planifier shift CVC vers heures creuses solaires",
        "source_type": "COPILOT",
        "city": "paris",
        "status": "OPEN",
        "priority": 2,
        "severity": "medium",
        "category": "energie",
        "gain": 4000,
    },
]


def seed_extra_actions(db: Session, org, sites: list, rng: random.Random) -> int:
    from models.action_item import ActionItem
    from models.enums import ActionSourceType, ActionStatus

    site_map = _build_site_map(sites)

    status_map = {
        "OPEN": ActionStatus.OPEN,
        "IN_PROGRESS": ActionStatus.IN_PROGRESS,
        "DONE": ActionStatus.DONE,
        "BLOCKED": ActionStatus.BLOCKED,
        "FALSE_POSITIVE": ActionStatus.FALSE_POSITIVE,
    }
    source_map = {
        "COMPLIANCE": ActionSourceType.COMPLIANCE,
        "CONSUMPTION": ActionSourceType.CONSUMPTION,
        "BILLING": ActionSourceType.BILLING,
        "PURCHASE": ActionSourceType.PURCHASE,
        "INSIGHT": ActionSourceType.INSIGHT,
        "MANUAL": ActionSourceType.MANUAL,
        "COPILOT": ActionSourceType.COPILOT,
    }

    created = 0
    now = datetime.now(timezone.utc)

    for i, act in enumerate(EXTRA_ACTIONS):
        idem_key = f"helios-completion:action:{i}"
        existing = db.query(ActionItem).filter_by(idempotency_key=idem_key).first()
        if existing:
            continue

        site = site_map.get(act["city"])
        db.add(
            ActionItem(
                org_id=org.id,
                site_id=site.id if site else None,
                source_type=source_map[act["source_type"]],
                source_id=f"seed-completion-{i}",
                source_key=f"completion:{act['source_type'].lower()}:{i}",
                idempotency_key=idem_key,
                title=act["title"],
                priority=act.get("priority", 3),
                severity=act.get("severity", "medium"),
                status=status_map[act["status"]],
                category=act.get("category"),
                estimated_gain_eur=act.get("gain"),
                due_date=date.today() + timedelta(days=rng.randint(14, 120)),
            )
        )
        created += 1

    db.flush()
    return created


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1.8 — Notifications extra (10 → 22+)
# ──────────────────────────────────────────────────────────────────────────────

EXTRA_NOTIFICATIONS = [
    # billing (3)
    {
        "title": "Facture Nice mars 2025 : anomalie détectée (surcharge +23%)",
        "source_type": "BILLING",
        "severity": "CRITICAL",
        "city": "nice",
        "message": "Règle R1 déclenchée : montant facture dépasse +20% vs historique. Écart estimé : 3 400 €.",
        "deeplink": "/bill-intel?site_id={site_id}",
    },
    {
        "title": "Facture Toulouse Q3 manquante — trou de couverture",
        "source_type": "BILLING",
        "severity": "WARN",
        "city": "toulouse",
        "message": "Aucune facture reçue pour juillet-septembre 2025. Couverture : 75%.",
        "deeplink": "/billing?site_id={site_id}",
    },
    {
        "title": "Shadow billing Paris : écart réseau TURPE 7 détecté",
        "source_type": "BILLING",
        "severity": "WARN",
        "city": "paris",
        "message": "Reconstitution shadow billing : composante réseau +8% vs tarif TURPE 7 officiel.",
        "deeplink": "/bill-intel?site_id={site_id}",
    },
    # consumption (3)
    {
        "title": "Pic de consommation Paris nuit — baseload +35% vs référence",
        "source_type": "CONSUMPTION",
        "severity": "CRITICAL",
        "city": "paris",
        "message": "Baseload nocturne 22h-6h supérieur de 35% au profil archetype bureau. Ventilation en cause probable.",
        "deeplink": "/usages?site_id={site_id}",
    },
    {
        "title": "Anomalie weekend Marseille — chauffage actif samedi/dimanche",
        "source_type": "CONSUMPTION",
        "severity": "WARN",
        "city": "marseille",
        "message": "Consommation weekend 40% du jour ouvré. Horaires planifiés : lun-ven 7h30-17h30.",
        "deeplink": "/usages?site_id={site_id}",
    },
    {
        "title": "Lyon : consommation 15% sous cible mensuelle (objectif atteint)",
        "source_type": "CONSUMPTION",
        "severity": "INFO",
        "city": "lyon",
        "message": "Performance positive : consommation mars 2026 inférieure de 15% à la cible DT.",
        "deeplink": "/dt-progress?site_id={site_id}",
    },
    # compliance (3)
    {
        "title": "Deadline OPERAT 2026 : déclaration attendue avant 30/09",
        "source_type": "COMPLIANCE",
        "severity": "CRITICAL",
        "city": None,
        "message": "5 sites concernés. Statut actuel : 2 déclarés, 3 en attente. Sanction : 7 500 € / EFA non déclarée.",
        "deeplink": "/conformite",
    },
    {
        "title": "BACS Nice : inspection programmée dans 45 jours",
        "source_type": "COMPLIANCE",
        "severity": "WARN",
        "city": "nice",
        "message": "Inspection quinquennale BACS prévue le 15/05/2026. Dossier à préparer.",
        "deeplink": "/conformite?tab=bacs&site_id={site_id}",
    },
    {
        "title": "APER Toulouse : étude solaire parking à planifier",
        "source_type": "COMPLIANCE",
        "severity": "WARN",
        "city": "toulouse",
        "message": "Parking 3 500 m² assujetti APER. Échéance couverture PV : 01/07/2028.",
        "deeplink": "/conformite?tab=aper&site_id={site_id}",
    },
    # action_hub (3)
    {
        "title": "3 actions en retard — revue hebdomadaire recommandée",
        "source_type": "ACTION_HUB",
        "severity": "CRITICAL",
        "city": None,
        "message": "Actions #12, #15, #18 dépassent leur échéance. Impact cumulé estimé : 15 000 €/an.",
        "deeplink": "/actions?status=overdue",
    },
    {
        "title": "Action 'Renouveler contrat Paris' : échéance dans 30 jours",
        "source_type": "ACTION_HUB",
        "severity": "WARN",
        "city": "paris",
        "message": "Contrat EDF actuel expire le 30/04/2026. 3 scénarios calculés, en attente de décision.",
        "deeplink": "/achat-energie?site_id={site_id}",
    },
    {
        "title": "Plan d'action Q2 : 5 actions complétées sur 8",
        "source_type": "ACTION_HUB",
        "severity": "INFO",
        "city": None,
        "message": "Progression Q2 2026 : 62,5%. Gain réalisé cumulé : 22 000 €.",
        "deeplink": "/actions?period=q2",
    },
]


def seed_extra_notifications(db: Session, org, sites: list) -> int:
    from models.notification import NotificationEvent
    from models.enums import NotificationSeverity, NotificationStatus, NotificationSourceType

    site_map = _build_site_map(sites)

    severity_map = {
        "INFO": NotificationSeverity.INFO,
        "WARN": NotificationSeverity.WARN,
        "CRITICAL": NotificationSeverity.CRITICAL,
    }
    source_map = {
        "BILLING": NotificationSourceType.BILLING,
        "CONSUMPTION": NotificationSourceType.CONSUMPTION,
        "COMPLIANCE": NotificationSourceType.COMPLIANCE,
        "ACTION_HUB": NotificationSourceType.ACTION_HUB,
        "PURCHASE": NotificationSourceType.PURCHASE,
    }

    created = 0
    now = datetime.now(timezone.utc)

    for i, notif in enumerate(EXTRA_NOTIFICATIONS):
        source_key = f"completion:{notif['source_type'].lower()}:{i}"
        existing = (
            db.query(NotificationEvent)
            .filter_by(
                org_id=org.id,
                source_type=source_map[notif["source_type"]],
                source_key=source_key,
            )
            .first()
        )
        if existing:
            continue

        site = site_map.get(notif["city"]) if notif["city"] else None
        deeplink = notif.get("deeplink", "")
        if site and "{site_id}" in deeplink:
            deeplink = deeplink.replace("{site_id}", str(site.id))

        db.add(
            NotificationEvent(
                org_id=org.id,
                site_id=site.id if site else None,
                source_type=source_map[notif["source_type"]],
                source_id=f"seed-completion-{i}",
                source_key=source_key,
                severity=severity_map[notif["severity"]],
                title=notif["title"],
                message=notif.get("message"),
                deeplink_path=deeplink,
                status=NotificationStatus.NEW,
                inputs_hash=hashlib.sha256(f"completion-notif-{i}".encode()).hexdigest()[:64],
            )
        )
        created += 1

    db.flush()
    return created


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1.9 — Evidence/Preuves extra (5 → 25+)
# ──────────────────────────────────────────────────────────────────────────────

EXTRA_EVIDENCES = [
    # DT (5)
    {"type": "DECLARATION", "statut": "VALIDE", "city": "paris", "note": "Déclaration OPERAT 2024 — Siège Paris"},
    {"type": "RAPPORT", "statut": "VALIDE", "city": "paris", "note": "Plan d'action DT 2025-2030 — Paris"},
    {"type": "FACTURE", "statut": "EN_ATTENTE", "city": "marseille", "note": "Extraction conso 2024 — Marseille"},
    {"type": "DECLARATION", "statut": "VALIDE", "city": "nice", "note": "Déclaration OPERAT 2024 — Nice"},
    {"type": "RAPPORT", "statut": "EN_ATTENTE", "city": "toulouse", "note": "Plan d'action DT — Toulouse"},
    # BACS (5)
    {"type": "ATTESTATION_BACS", "statut": "VALIDE", "city": "nice", "note": "Attestation BACS classe B — Nice hôtel"},
    {"type": "RAPPORT", "statut": "VALIDE", "city": "nice", "note": "Rapport inspection BACS 2025 — Nice"},
    {"type": "RAPPORT", "statut": "EN_ATTENTE", "city": "toulouse", "note": "Specs techniques BACS — Toulouse"},
    {
        "type": "DEROGATION_BACS",
        "statut": "VALIDE",
        "city": "lyon",
        "note": "Étude TRI exemption BACS — Lyon (TRI > 10 ans)",
    },
    {"type": "RAPPORT", "statut": "EN_ATTENTE", "city": "paris", "note": "Documentation paramétrage GTB — Paris"},
    # APER (4)
    {"type": "RAPPORT", "statut": "VALIDE", "city": "marseille", "note": "Étude PV toiture Marseille — 1200 m²"},
    {"type": "RAPPORT", "statut": "EN_ATTENTE", "city": "toulouse", "note": "Diagnostic toiture Toulouse — 3200 m²"},
    {"type": "RAPPORT", "statut": "VALIDE", "city": "nice", "note": "Étude PV parking Nice — 1800 m²"},
    {"type": "CERTIFICAT", "statut": "EN_ATTENTE", "city": "paris", "note": "Étude PV parking Paris — 2200 m²"},
    # Audit énergie (3)
    {"type": "AUDIT", "statut": "VALIDE", "city": "paris", "note": "Rapport audit énergétique 2024 — Groupe HELIOS"},
    {"type": "RAPPORT", "statut": "EN_ATTENTE", "city": "paris", "note": "Plan SMÉ ISO 50001 (draft)"},
    {"type": "AUDIT", "statut": "VALIDE", "city": "lyon", "note": "Rapport audit Lyon 2024"},
    # Billing (3)
    {"type": "FACTURE", "statut": "VALIDE", "city": "paris", "note": "Facture EDF vérifiée Q1 2025 — Paris"},
    {"type": "CERTIFICAT", "statut": "VALIDE", "city": "nice", "note": "Contrat ENGIE Pro 2025-2028 — Nice"},
    {"type": "RAPPORT", "statut": "VALIDE", "city": "toulouse", "note": "Rapport shadow billing Q4 2024 — Toulouse"},
]


def seed_extra_evidences(db: Session, sites: list) -> int:
    from models.evidence import Evidence
    from models.enums import TypeEvidence, StatutEvidence

    site_map = _build_site_map(sites)

    type_map = {
        "AUDIT": TypeEvidence.AUDIT,
        "FACTURE": TypeEvidence.FACTURE,
        "CERTIFICAT": TypeEvidence.CERTIFICAT,
        "RAPPORT": TypeEvidence.RAPPORT,
        "PHOTO": TypeEvidence.PHOTO,
        "DECLARATION": TypeEvidence.DECLARATION,
        "ATTESTATION_BACS": TypeEvidence.ATTESTATION_BACS,
        "DEROGATION_BACS": TypeEvidence.DEROGATION_BACS,
    }
    statut_map = {
        "VALIDE": StatutEvidence.VALIDE,
        "EN_ATTENTE": StatutEvidence.EN_ATTENTE,
        "MANQUANT": StatutEvidence.MANQUANT,
        "EXPIRE": StatutEvidence.EXPIRE,
    }

    created = 0
    for i, ev in enumerate(EXTRA_EVIDENCES):
        site = site_map.get(ev["city"])
        if not site:
            continue

        # Idempotence: check by note (unique enough)
        existing = db.query(Evidence).filter_by(site_id=site.id, note=ev["note"]).first()
        if existing:
            continue

        db.add(
            Evidence(
                site_id=site.id,
                type=type_map[ev["type"]],
                statut=statut_map[ev["statut"]],
                note=ev["note"],
            )
        )
        created += 1

    db.flush()
    return created


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point — called from orchestrator
# ──────────────────────────────────────────────────────────────────────────────


def seed_completion(db: Session, org, sites: list, rng: random.Random) -> dict:
    """Run all Phase 1 completion steps. Returns stats dict.

    Each step is isolated: a failure in one does not abort the others.
    """
    stats = {}

    steps = [
        ("aper_updated", lambda: seed_aper_fields(db, sites)),
        ("datapoints_created", lambda: seed_datapoints(db, sites)),
        ("reg_events_created", lambda: seed_reg_source_events(db)),
        ("purchase", lambda: seed_purchase_completion(db, sites, rng)),
        ("actions_extra", lambda: seed_extra_actions(db, org, sites, rng)),
        ("notifications_extra", lambda: seed_extra_notifications(db, org, sites)),
        ("evidences_extra", lambda: seed_extra_evidences(db, sites)),
    ]

    for key, fn in steps:
        try:
            stats[key] = fn()
        except Exception as exc:
            logger.warning("seed_completion step '%s' failed (non-bloquant): %s", key, exc)
            stats[key] = {"error": str(exc)}

    logger.info(f"Seed completion: {stats}")
    return stats
