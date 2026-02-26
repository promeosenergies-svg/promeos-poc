"""
PROMEOS — Achat Energie Seed WOW (Brique 3)
Multi-site datasets: 15 sites x 3 scenarios, happy + dirty modes.
"""
import uuid
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.orm import Session

from models import (
    Organisation, EntiteJuridique, Portefeuille, Site,
    EnergyContract, PurchaseAssumptionSet, PurchasePreference,
    PurchaseScenarioResult, PurchaseStrategy, PurchaseRecoStatus,
    BillingEnergyType, TypeSite,
)

# 15 realistic French B2B sites
_WOW_SITES = [
    {"nom": "Hypermarche Montreuil",  "type": TypeSite.COMMERCE,   "ville": "Montreuil",   "cp": "93100", "surface": 4500, "volume": 1_800_000, "profile": 1.30},
    {"nom": "Bureau Haussmann",       "type": TypeSite.BUREAU,     "ville": "Paris",        "cp": "75008", "surface": 1200, "volume": 350_000,   "profile": 1.10},
    {"nom": "Entrepot Rungis",        "type": TypeSite.ENTREPOT,   "ville": "Rungis",       "cp": "94150", "surface": 8000, "volume": 600_000,   "profile": 0.85},
    {"nom": "Usine Villepinte",       "type": TypeSite.USINE,      "ville": "Villepinte",   "cp": "93420", "surface": 12000,"volume": 2_500_000, "profile": 0.90},
    {"nom": "Bureau La Defense T1",   "type": TypeSite.BUREAU,     "ville": "Courbevoie",   "cp": "92400", "surface": 3000, "volume": 800_000,   "profile": 1.20},
    {"nom": "Magasin Lyon Confluence","type": TypeSite.MAGASIN,    "ville": "Lyon",         "cp": "69002", "surface": 2200, "volume": 900_000,   "profile": 1.15},
    {"nom": "Entrepot Marseille",     "type": TypeSite.ENTREPOT,   "ville": "Marseille",    "cp": "13015", "surface": 6500, "volume": 450_000,   "profile": 0.80},
    {"nom": "Bureau Nantes Ile",      "type": TypeSite.BUREAU,     "ville": "Nantes",       "cp": "44200", "surface": 900,  "volume": 250_000,   "profile": 1.05},
    {"nom": "Commerce Bordeaux",      "type": TypeSite.COMMERCE,   "ville": "Bordeaux",     "cp": "33000", "surface": 3500, "volume": 1_200_000, "profile": 1.25},
    {"nom": "Copropriete Toulouse",   "type": TypeSite.COPROPRIETE,"ville": "Toulouse",     "cp": "31000", "surface": 5000, "volume": 700_000,   "profile": 0.95},
    {"nom": "Logement Social Lille",  "type": TypeSite.LOGEMENT_SOCIAL, "ville": "Lille", "cp": "59000", "surface": 4000, "volume": 550_000, "profile": 0.90},
    {"nom": "Magasin Strasbourg",     "type": TypeSite.MAGASIN,    "ville": "Strasbourg",   "cp": "67000", "surface": 1800, "volume": 650_000,   "profile": 1.10},
    {"nom": "Bureau Sophia Antipolis","type": TypeSite.BUREAU,     "ville": "Sophia Antipolis","cp": "06560","surface": 1500,"volume": 400_000,  "profile": 1.00},
    {"nom": "Usine Grenoble",         "type": TypeSite.USINE,      "ville": "Grenoble",     "cp": "38000", "surface": 9000, "volume": 3_000_000, "profile": 0.85},
    {"nom": "Entrepot Rouen",         "type": TypeSite.ENTREPOT,   "ville": "Rouen",        "cp": "76000", "surface": 5500, "volume": 380_000,   "profile": 0.80},
]


def _create_wow_org(db: Session, org_name: str = "PROMEOS Demo Corp"):
    """Create org with 3 portfolios for WOW demo."""
    # Reuse existing org if possible
    existing = db.query(Organisation).filter(Organisation.nom == org_name).first()
    if existing:
        return existing

    org = Organisation(nom=org_name, type_client="bureau", actif=True)
    db.add(org)
    db.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom=f"{org_name} SAS", siren="987654321")
    db.add(ej)
    db.flush()

    for pf_name in ["Ile-de-France", "Province Nord", "Province Sud"]:
        pf = Portefeuille(entite_juridique_id=ej.id, nom=pf_name, description=f"Portefeuille {pf_name}")
        db.add(pf)

    db.flush()
    return org


def _create_wow_sites(db: Session, org: Organisation):
    """Create 15 WOW sites spread across 3 portfolios."""
    ej = db.query(EntiteJuridique).filter(EntiteJuridique.organisation_id == org.id).first()
    portefeuilles = db.query(Portefeuille).filter(Portefeuille.entite_juridique_id == ej.id).all()

    sites = []
    for i, spec in enumerate(_WOW_SITES):
        pf = portefeuilles[i % len(portefeuilles)]
        site = Site(
            nom=spec["nom"],
            type=spec["type"],
            adresse=f"{10 + i} rue du Commerce",
            code_postal=spec["cp"],
            ville=spec["ville"],
            surface_m2=spec["surface"],
            portefeuille_id=pf.id,
            actif=True,
        )
        db.add(site)
        sites.append((site, spec))

    db.flush()
    return sites


def _compute_scenario(ref_price, volume, profile_factor, strategy_specs):
    """Generate scenario results for a single site."""
    scenarios = []
    current_total = round(ref_price * volume, 2)

    for strategy, mult, risk, p10_mult, p90_mult, is_reco in strategy_specs:
        price = round(ref_price * mult, 4)
        total = round(price * volume, 2)
        savings = round((1 - total / current_total) * 100, 1) if current_total > 0 else 0
        scenarios.append({
            "strategy": strategy,
            "price": price,
            "total": total,
            "risk": risk,
            "savings": savings,
            "p10": round(total * p10_mult, 2),
            "p90": round(total * p90_mult, 2),
            "is_reco": is_reco,
        })
    return scenarios


def seed_wow_happy(db: Session) -> dict:
    """
    Seed 15 multi-site portfolio with clean, realistic data.
    All ELEC, varied volumes, nice scenario spread.
    """
    org = _create_wow_org(db, "PROMEOS WOW Demo")
    site_specs = _create_wow_sites(db, org)

    # Preference
    existing_pref = db.query(PurchasePreference).filter(PurchasePreference.org_id == org.id).first()
    if not existing_pref:
        db.add(PurchasePreference(org_id=org.id, risk_tolerance="medium", budget_priority=0.6, green_preference=True))
        db.flush()

    assumptions_created = 0
    scenarios_created = 0
    contracts_created = 0
    today = date.today()

    for site, spec in site_specs:
        # Assumption
        assumption = PurchaseAssumptionSet(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            volume_kwh_an=spec["volume"],
            profile_factor=spec["profile"],
            horizon_months=24,
        )
        db.add(assumption)
        db.flush()
        assumptions_created += 1

        # Reference price (varies by volume)
        if spec["volume"] > 1_500_000:
            ref_price = 0.16  # Large consumer = better tariff
        elif spec["volume"] > 500_000:
            ref_price = 0.18
        else:
            ref_price = 0.20  # Small = higher price

        # Scenario strategies: alternate recommendations
        reco_idx = assumptions_created % 3
        strategy_specs = [
            (PurchaseStrategy.FIXE,   1.05, 15, 1.0,  1.0,  reco_idx == 0),
            (PurchaseStrategy.INDEXE, 0.95, 45, 0.85, 1.20, reco_idx == 1),
            (PurchaseStrategy.SPOT,   0.88, 75, 0.70, 1.45, reco_idx == 2),
        ]

        run_id = str(uuid.uuid4())
        for s in _compute_scenario(ref_price, spec["volume"], spec["profile"], strategy_specs):
            db.add(PurchaseScenarioResult(
                assumption_set_id=assumption.id,
                run_id=run_id,
                strategy=s["strategy"],
                price_eur_per_kwh=s["price"],
                total_annual_eur=s["total"],
                risk_score=s["risk"],
                savings_vs_current_pct=s["savings"],
                p10_eur=s["p10"],
                p90_eur=s["p90"],
                is_recommended=s["is_reco"],
                reco_status=PurchaseRecoStatus.DRAFT,
                computed_at=datetime.now(timezone.utc),
            ))
            scenarios_created += 1

        # Contract — varied expiries
        days_offset = 30 + (assumptions_created * 25)  # 55..405 days
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name=["EDF Entreprises", "Engie Elec", "TotalEnergies", "Vattenfall", "Alpiq"][assumptions_created % 5],
            start_date=today - timedelta(days=335),
            end_date=today + timedelta(days=days_offset),
            price_ref_eur_per_kwh=ref_price,
            fixed_fee_eur_per_month=round(spec["surface"] * 0.008, 2),
            notice_period_days=60 if assumptions_created % 2 == 0 else 90,
            auto_renew=assumptions_created % 3 == 0,
        )
        db.add(contract)
        contracts_created += 1

    db.commit()

    return {
        "mode": "happy",
        "org_id": org.id,
        "org_nom": org.nom,
        "sites_created": len(site_specs),
        "assumptions_created": assumptions_created,
        "scenarios_created": scenarios_created,
        "contracts_created": contracts_created,
    }


def seed_wow_dirty(db: Session) -> dict:
    """
    Seed 15 multi-site portfolio with degraded/edge-case data.
    Missing volumes, extreme profiles, no contracts on some sites, very short expiries.
    """
    org = _create_wow_org(db, "PROMEOS WOW Dirty")
    site_specs = _create_wow_sites(db, org)

    # No preference set (forces default fallback in engine)

    assumptions_created = 0
    scenarios_created = 0
    contracts_created = 0
    today = date.today()

    for idx, (site, spec) in enumerate(site_specs):
        # Dirty patterns
        if idx == 0:
            volume = 0  # Zero volume
            profile = 1.0
        elif idx == 1:
            volume = 50  # Extremely small
            profile = 0.1  # Abnormal profile
        elif idx == 2:
            volume = 50_000_000  # Absurdly large
            profile = 3.0  # Extreme peak
        elif idx == 5:
            # Skip assumption entirely — site has no purchase data
            continue
        elif idx == 10:
            # Skip assumption — orphan site
            continue
        else:
            volume = spec["volume"]
            profile = spec["profile"]

        assumption = PurchaseAssumptionSet(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            volume_kwh_an=volume,
            profile_factor=profile,
            horizon_months=24 if idx % 4 != 3 else 12,  # Mix horizons
        )
        db.add(assumption)
        db.flush()
        assumptions_created += 1

        ref_price = 0.18

        # All recommend FIXE for dirty (conservative)
        strategy_specs = [
            (PurchaseStrategy.FIXE,   1.05, 15, 1.0,  1.0,  True),
            (PurchaseStrategy.INDEXE, 0.95, 45, 0.85, 1.20, False),
            (PurchaseStrategy.SPOT,   0.88, 75, 0.70, 1.45, False),
        ]

        run_id = str(uuid.uuid4())
        for s in _compute_scenario(ref_price, volume, profile, strategy_specs):
            db.add(PurchaseScenarioResult(
                assumption_set_id=assumption.id,
                run_id=run_id,
                strategy=s["strategy"],
                price_eur_per_kwh=s["price"],
                total_annual_eur=s["total"],
                risk_score=s["risk"],
                savings_vs_current_pct=s["savings"],
                p10_eur=s["p10"],
                p90_eur=s["p90"],
                is_recommended=s["is_reco"],
                reco_status=PurchaseRecoStatus.DRAFT,
                computed_at=datetime.now(timezone.utc),
            ))
            scenarios_created += 1

        # Contracts — some missing, some expired, some very short notice
        if idx in (3, 7, 12):
            # No contract — forces default price fallback
            pass
        elif idx == 4:
            # Already expired contract
            db.add(EnergyContract(
                site_id=site.id, energy_type=BillingEnergyType.ELEC,
                supplier_name="Ancien Fournisseur",
                start_date=today - timedelta(days=400),
                end_date=today - timedelta(days=5),
                price_ref_eur_per_kwh=0.22,
                notice_period_days=30,
            ))
            contracts_created += 1
        elif idx == 6:
            # Contract expiring in 10 days (urgent)
            db.add(EnergyContract(
                site_id=site.id, energy_type=BillingEnergyType.ELEC,
                supplier_name="EDF Urgence",
                start_date=today - timedelta(days=355),
                end_date=today + timedelta(days=10),
                price_ref_eur_per_kwh=0.19,
                notice_period_days=60,
                auto_renew=False,
            ))
            contracts_created += 1
        else:
            db.add(EnergyContract(
                site_id=site.id, energy_type=BillingEnergyType.ELEC,
                supplier_name=["EDF", "Engie", "Total"][idx % 3],
                start_date=today - timedelta(days=200),
                end_date=today + timedelta(days=60 + idx * 15),
                price_ref_eur_per_kwh=0.18,
                notice_period_days=90,
            ))
            contracts_created += 1

    db.commit()

    return {
        "mode": "dirty",
        "org_id": org.id,
        "org_nom": org.nom,
        "sites_created": len(site_specs),
        "assumptions_created": assumptions_created,
        "scenarios_created": scenarios_created,
        "contracts_created": contracts_created,
        "warnings": [
            "Site 1: volume=0 kWh/an",
            "Site 2: volume=50 kWh/an, profile=0.1 (anormal)",
            "Site 3: volume=50M kWh/an, profile=3.0 (extreme)",
            "Sites 6, 11: aucune hypothese (orphelins)",
            "Sites 4, 8, 13: aucun contrat (prix par defaut)",
            "Site 5: contrat expire",
            "Site 7: contrat expire dans 10 jours (urgent)",
        ],
    }
