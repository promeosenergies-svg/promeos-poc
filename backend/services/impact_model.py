"""
PROMEOS -- Impact Model Service (Sprint V4.9)
Resolves electricity price and computes EUR impacts for monitoring KPIs.
Three modes: CONTRAT (contract price), TARIF (site tariff profile), DEMO (default 0.18).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.billing_models import EnergyContract
from models.enums import BillingEnergyType
from models.site_tariff_profile import SiteTariffProfile


DEFAULT_PRICE_EUR_KWH = 0.18
TURPE_PENALTY_EUR_KVA_MONTH = 15.48


@dataclass
class PriceInfo:
    price_eur_kwh: float
    mode: str  # "CONTRAT" | "TARIF" | "DEMO"
    source_label: str
    confidence: str  # "high" | "medium" | "low"


@dataclass
class ImpactResult:
    eur_year: float
    mode: str
    confidence: str
    price_eur_kwh: float
    assumptions: List[str] = field(default_factory=list)


def resolve_price(db: Session, site_id: int) -> PriceInfo:
    """
    Resolve electricity price for a site.
    Priority: active EnergyContract (ELEC) > SiteTariffProfile > default 0.18.
    """
    # 1. Active ELEC contract with price
    today = date.today()
    contract = (
        db.query(EnergyContract)
        .filter(
            EnergyContract.site_id == site_id,
            EnergyContract.energy_type == BillingEnergyType.ELEC,
            EnergyContract.price_ref_eur_per_kwh.isnot(None),
        )
        .order_by(
            # Prefer contracts covering today; use coalesce for SQLite compat
            func.coalesce(EnergyContract.end_date, "9999-12-31").desc(),
        )
        .first()
    )

    if contract and contract.price_ref_eur_per_kwh and contract.price_ref_eur_per_kwh > 0:
        label = f"{contract.supplier_name} ({contract.start_date} - {contract.end_date or 'en cours'})"
        return PriceInfo(
            price_eur_kwh=contract.price_ref_eur_per_kwh,
            mode="CONTRAT",
            source_label=label,
            confidence="high",
        )

    # 2. SiteTariffProfile
    tariff = db.query(SiteTariffProfile).filter_by(site_id=site_id).first()
    if tariff and tariff.price_ref_eur_per_kwh and tariff.price_ref_eur_per_kwh > 0:
        return PriceInfo(
            price_eur_kwh=tariff.price_ref_eur_per_kwh,
            mode="TARIF",
            source_label=f"Profil tarifaire site ({tariff.price_ref_eur_per_kwh} EUR/kWh)",
            confidence="medium",
        )

    # 3. Default
    return PriceInfo(
        price_eur_kwh=DEFAULT_PRICE_EUR_KWH,
        mode="DEMO",
        source_label=f"Tarif par defaut ({DEFAULT_PRICE_EUR_KWH} EUR/kWh)",
        confidence="low",
    )


def compute_off_hours_eur(
    off_hours_kwh: float,
    period_days: int,
    price_info: PriceInfo,
    reduction_pct: float = 0.5,
) -> ImpactResult:
    """
    Estimate annual EUR savings from reducing off-hours consumption.
    Annualizes observed kWh, applies reduction_pct, multiplies by price.
    """
    assumptions = []

    if period_days <= 0 or off_hours_kwh <= 0:
        assumptions.append("Pas de consommation hors horaires detectee")
        return ImpactResult(
            eur_year=0.0,
            mode=price_info.mode,
            confidence=price_info.confidence,
            price_eur_kwh=price_info.price_eur_kwh,
            assumptions=assumptions,
        )

    annualized_kwh = off_hours_kwh * (365.0 / period_days)
    reducible_kwh = annualized_kwh * reduction_pct
    eur_year = round(reducible_kwh * price_info.price_eur_kwh, 2)

    assumptions.append(f"Annualisation: {off_hours_kwh:.0f} kWh sur {period_days}j -> {annualized_kwh:.0f} kWh/an")
    assumptions.append(f"Reduction cible: {reduction_pct * 100:.0f}% -> {reducible_kwh:.0f} kWh economisables")
    assumptions.append(f"Prix: {price_info.price_eur_kwh} EUR/kWh (mode {price_info.mode})")

    return ImpactResult(
        eur_year=max(0.0, eur_year),
        mode=price_info.mode,
        confidence=price_info.confidence,
        price_eur_kwh=price_info.price_eur_kwh,
        assumptions=assumptions,
    )


def compute_power_overrun_eur(
    p95_kw: float,
    psub_kva: Optional[float],
    price_info: PriceInfo,
) -> ImpactResult:
    """
    Estimate annual penalty from exceeding subscribed power (TURPE).
    Excess = max(0, P95 - Psub) * 15.48 EUR/kVA/month * 12.
    """
    assumptions = []

    if psub_kva is None or psub_kva <= 0:
        assumptions.append("Puissance souscrite inconnue — calcul impossible")
        return ImpactResult(
            eur_year=0.0,
            mode=price_info.mode,
            confidence="low",
            price_eur_kwh=price_info.price_eur_kwh,
            assumptions=assumptions,
        )

    excess_kva = max(0.0, p95_kw - psub_kva)

    if excess_kva <= 0:
        assumptions.append(f"P95 ({p95_kw:.1f} kW) <= Psub ({psub_kva:.1f} kVA) — pas de depassement")
        return ImpactResult(
            eur_year=0.0,
            mode=price_info.mode,
            confidence=price_info.confidence,
            price_eur_kwh=price_info.price_eur_kwh,
            assumptions=assumptions,
        )

    eur_year = round(excess_kva * TURPE_PENALTY_EUR_KVA_MONTH * 12, 2)
    assumptions.append(f"Depassement: P95 ({p95_kw:.1f} kW) - Psub ({psub_kva:.1f} kVA) = {excess_kva:.1f} kVA")
    assumptions.append(
        f"Penalite TURPE: {TURPE_PENALTY_EUR_KVA_MONTH} EUR/kVA/mois x 12 = {TURPE_PENALTY_EUR_KVA_MONTH * 12:.2f} EUR/kVA/an"
    )
    assumptions.append(f"Prix electricite: {price_info.price_eur_kwh} EUR/kWh (mode {price_info.mode})")

    return ImpactResult(
        eur_year=max(0.0, eur_year),
        mode=price_info.mode,
        confidence=price_info.confidence,
        price_eur_kwh=price_info.price_eur_kwh,
        assumptions=assumptions,
    )
