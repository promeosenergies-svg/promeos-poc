"""
PROMEOS - Demo Seed: Purchase Scenarios Generator
Creates purchase assumption sets + scenario results for a few sites.
"""
import random
import uuid
from datetime import datetime

from models import (
    PurchaseAssumptionSet, PurchaseScenarioResult,
    BillingEnergyType, PurchaseStrategy, PurchaseRecoStatus,
)


def generate_purchase(db, sites: list, rng: random.Random) -> dict:
    """Generate purchase scenarios for ~30% of sites."""
    assumption_sets = 0
    scenarios = 0

    sample_size = max(2, len(sites) // 3)
    sampled = rng.sample(sites, min(sample_size, len(sites)))

    for site in sampled:
        annual_kwh = site.annual_kwh_total or rng.randint(200000, 2000000)
        profile_factor = round(rng.uniform(0.8, 1.4), 2)

        ass = PurchaseAssumptionSet(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            volume_kwh_an=annual_kwh,
            profile_factor=profile_factor,
            horizon_months=rng.choice([12, 24, 36]),
        )
        db.add(ass)
        db.flush()
        assumption_sets += 1

        run_id = str(uuid.uuid4())

        # 3 strategies per assumption set
        for strategy, price_mult, risk in [
            (PurchaseStrategy.FIXE, 1.0, 20),
            (PurchaseStrategy.INDEXE, 0.92, 55),
            (PurchaseStrategy.SPOT, 0.85, 80),
        ]:
            base_price = round(rng.uniform(0.12, 0.22) * price_mult, 4)
            total = round(annual_kwh * base_price, 2)
            is_reco = strategy == PurchaseStrategy.FIXE

            db.add(PurchaseScenarioResult(
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
            ))
            scenarios += 1

    db.flush()
    return {"assumption_sets": assumption_sets, "scenarios": scenarios}
