"""
PROMEOS — Achat Energie Seed Demo
2 sites x 3 scenarios (fixe/indexe/spot) + preferences.
"""
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from models import (
    Site, EnergyContract,
    PurchaseAssumptionSet, PurchasePreference, PurchaseScenarioResult,
    PurchaseStrategy, PurchaseRecoStatus, BillingEnergyType,
)


def seed_purchase_demo(db: Session) -> dict:
    """
    Seed purchase scenarios for 2 sites.
    Returns summary.
    """
    sites = db.query(Site).limit(3).all()
    if len(sites) < 2:
        return {"error": "Need at least 2 sites to seed purchase demo"}

    site_a = sites[0]
    site_b = sites[1]

    # ── Preference (org-level) ──
    existing_pref = db.query(PurchasePreference).first()
    if not existing_pref:
        pref = PurchasePreference(
            org_id=1,
            risk_tolerance="medium",
            budget_priority=0.6,
            green_preference=False,
        )
        db.add(pref)
        db.flush()

    # ── Assumptions site A (elec, 600k kWh/an) ──
    assumptions_a = PurchaseAssumptionSet(
        site_id=site_a.id,
        energy_type=BillingEnergyType.ELEC,
        volume_kwh_an=600_000,
        profile_factor=1.25,
        horizon_months=24,
    )
    db.add(assumptions_a)
    db.flush()

    # ── Assumptions site B (elec, 300k kWh/an — Energy Gate: ELEC-only) ──
    assumptions_b = PurchaseAssumptionSet(
        site_id=site_b.id,
        energy_type=BillingEnergyType.ELEC,
        volume_kwh_an=300_000,
        profile_factor=0.85,
        horizon_months=24,
    )
    db.add(assumptions_b)
    db.flush()

    scenarios_created = 0

    # ── Site A scenarios (elec @ 0.18 ref) ──
    ref_a = 0.18
    for strategy, price_mult, risk, p10_mult, p90_mult, is_reco in [
        (PurchaseStrategy.FIXE,   1.05, 15, 1.0,  1.0,  False),
        (PurchaseStrategy.INDEXE, 0.95, 45, 0.85, 1.20, True),   # Recommended
        (PurchaseStrategy.SPOT,   0.88, 75, 0.70, 1.45, False),
    ]:
        price = round(ref_a * price_mult, 4)
        total = round(price * 600_000, 2)
        current_total = round(ref_a * 600_000, 2)
        savings = round((1 - total / current_total) * 100, 1)
        db.add(PurchaseScenarioResult(
            assumption_set_id=assumptions_a.id,
            strategy=strategy,
            price_eur_per_kwh=price,
            total_annual_eur=total,
            risk_score=risk,
            savings_vs_current_pct=savings,
            p10_eur=round(total * p10_mult, 2),
            p90_eur=round(total * p90_mult, 2),
            is_recommended=is_reco,
            reco_status=PurchaseRecoStatus.DRAFT,
            computed_at=datetime.utcnow(),
        ))
        scenarios_created += 1

    # ── Site B scenarios (elec @ 0.15 ref — smaller site, lower tariff) ──
    ref_b = 0.15
    for strategy, price_mult, risk, p10_mult, p90_mult, is_reco in [
        (PurchaseStrategy.FIXE,   1.05, 15, 1.0,  1.0,  True),   # Recommended (low risk)
        (PurchaseStrategy.INDEXE, 0.95, 45, 0.85, 1.20, False),
        (PurchaseStrategy.SPOT,   0.88, 75, 0.70, 1.45, False),
    ]:
        price = round(ref_b * price_mult, 4)
        total = round(price * 300_000, 2)
        current_total = round(ref_b * 300_000, 2)
        savings = round((1 - total / current_total) * 100, 1)
        db.add(PurchaseScenarioResult(
            assumption_set_id=assumptions_b.id,
            strategy=strategy,
            price_eur_per_kwh=price,
            total_annual_eur=total,
            risk_score=risk,
            savings_vs_current_pct=savings,
            p10_eur=round(total * p10_mult, 2),
            p90_eur=round(total * p90_mult, 2),
            is_recommended=is_reco,
            reco_status=PurchaseRecoStatus.DRAFT,
            computed_at=datetime.utcnow(),
        ))
        scenarios_created += 1

    db.commit()

    # ── V1.1: Seed contracts with notice_period_days + auto_renew ──
    today = date.today()
    contracts_created = 0

    # Contract 1: near expiry (~45 days), auto_renew=False
    contract_near = EnergyContract(
        site_id=site_a.id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF Entreprises",
        start_date=today - timedelta(days=335),
        end_date=today + timedelta(days=45),
        price_ref_eur_per_kwh=0.18,
        fixed_fee_eur_per_month=45.0,
        notice_period_days=60,
        auto_renew=False,
    )
    db.add(contract_near)
    contracts_created += 1

    # Contract 2: far expiry (~180 days), auto_renew=True
    contract_far = EnergyContract(
        site_id=site_b.id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="Engie Elec Pro",
        start_date=today - timedelta(days=185),
        end_date=today + timedelta(days=180),
        price_ref_eur_per_kwh=0.09,
        fixed_fee_eur_per_month=30.0,
        notice_period_days=90,
        auto_renew=True,
    )
    db.add(contract_far)
    contracts_created += 1

    db.commit()

    return {
        "sites_used": [site_a.id, site_b.id],
        "assumptions_created": 2,
        "preferences_created": 0 if existing_pref else 1,
        "scenarios_created": scenarios_created,
        "contracts_created": contracts_created,
    }
