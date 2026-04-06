"""
PROMEOS — Contract Risk Service (P1-A2)

Calcule le risque contrat en EUR pour le cockpit.
Trois composantes :
  1. Renewal risk : cout annuel des contrats expires ou dans le preavis
  2. Price gap risk : surcoût vs marche (contrat plus cher que spot)
  3. Volume penalty risk : penalites take-or-pay estimees

Tous les montants sont en EUR HT.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import EnergyContract, Site
from models.contract_v2_models import ContractAnnexe, VolumeCommitment
from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH, DEFAULT_PRICE_GAZ_EUR_KWH

_logger = logging.getLogger("promeos.contract_risk")


def compute_contract_risk_eur(
    db: Session,
    site_ids: list[int],
    market_spot_eur_kwh: Optional[float] = None,
) -> dict:
    """
    Compute contract risk in EUR for a set of sites.

    Parameters
    ----------
    db : Session
    site_ids : list of site IDs in scope
    market_spot_eur_kwh : optional override for current market price (EUR/kWh).
                          If None, fetched from mkt_prices or defaults.

    Returns
    -------
    dict with keys:
        renewal_risk_eur, price_gap_risk_eur, volume_penalty_risk_eur,
        total_eur, contracts_at_risk, details
    """
    if not site_ids:
        return _empty_result()

    today = date.today()

    # Fetch all contracts for scope
    contracts = db.query(EnergyContract).filter(EnergyContract.site_id.in_(site_ids)).all()

    if not contracts:
        return _empty_result()

    # Market reference price
    spot_eur_kwh = market_spot_eur_kwh or _get_spot_price(db)

    renewal_total = 0.0
    price_gap_total = 0.0
    contracts_at_risk_count = 0
    details = []

    for ct in contracts:
        ct_risk = _assess_single_contract(ct, today, spot_eur_kwh)
        renewal_total += ct_risk["renewal_risk_eur"]
        price_gap_total += ct_risk["price_gap_risk_eur"]
        if ct_risk["renewal_risk_eur"] > 0 or ct_risk["price_gap_risk_eur"] > 0:
            contracts_at_risk_count += 1
            details.append(ct_risk)

    # Volume penalty risk (from VolumeCommitment via ContractAnnexe)
    volume_penalty_total = _compute_volume_penalty_risk(db, site_ids)

    total = renewal_total + price_gap_total + volume_penalty_total

    return {
        "renewal_risk_eur": round(renewal_total, 2),
        "price_gap_risk_eur": round(price_gap_total, 2),
        "volume_penalty_risk_eur": round(volume_penalty_total, 2),
        "total_eur": round(total, 2),
        "contracts_at_risk": contracts_at_risk_count,
        "details": details,
    }


def _assess_single_contract(
    ct: EnergyContract,
    today: date,
    spot_eur_kwh: float,
) -> dict:
    """Assess renewal + price-gap risk for a single contract."""
    renewal_risk = 0.0
    price_gap_risk = 0.0

    # Annual consumption estimate (kWh)
    annual_kwh = ct.annual_consumption_kwh or 0
    if annual_kwh <= 0:
        # Fallback: site.annual_kwh_total via relationship
        site = ct.site
        if site:
            annual_kwh = getattr(site, "annual_kwh_total", 0) or 0

    # Contract price (EUR/kWh)
    contract_price = ct.price_ref_eur_per_kwh or ct.price_base_eur_kwh or 0

    # -- 1. Renewal risk --
    # Contracts expired or within notice period without auto-renew
    if ct.end_date:
        days_to_end = (ct.end_date - today).days
        notice_days = ct.notice_period_days or 90

        is_expired = days_to_end < 0
        is_past_notice = days_to_end >= 0 and days_to_end <= notice_days

        if is_expired or (is_past_notice and not ct.auto_renew):
            # Risk = estimated annual cost of renegotiating at market price
            # Use the higher of contract price and market price as potential cost
            renegotiation_price = max(contract_price, spot_eur_kwh)
            if annual_kwh > 0:
                renewal_risk = renegotiation_price * annual_kwh
            else:
                # Fallback: use fixed_fee if available
                monthly_fee = ct.fixed_fee_eur_per_month or 0
                renewal_risk = monthly_fee * 12

    # -- 2. Price gap risk --
    # When contract price > spot → we are overpaying (negative exposure)
    if contract_price > 0 and annual_kwh > 0 and ct.end_date and ct.end_date > today:
        gap_eur_kwh = contract_price - spot_eur_kwh
        if gap_eur_kwh > 0:
            # Remaining months on contract
            days_remaining = (ct.end_date - today).days
            remaining_fraction = min(days_remaining / 365.0, 1.0)
            price_gap_risk = gap_eur_kwh * annual_kwh * remaining_fraction

    return {
        "contract_id": ct.id,
        "site_id": ct.site_id,
        "supplier": ct.supplier_name,
        "end_date": ct.end_date.isoformat() if ct.end_date else None,
        "renewal_risk_eur": round(renewal_risk, 2),
        "price_gap_risk_eur": round(price_gap_risk, 2),
    }


def _compute_volume_penalty_risk(db: Session, site_ids: list[int]) -> float:
    """
    Estimate take-or-pay penalty exposure from VolumeCommitment records.
    Conservative: assume 15% deviation from committed volume.
    """
    commitments = (
        db.query(VolumeCommitment, ContractAnnexe)
        .join(ContractAnnexe, ContractAnnexe.id == VolumeCommitment.annexe_id)
        .filter(ContractAnnexe.site_id.in_(site_ids))
        .all()
    )

    total_penalty = 0.0
    deviation_pct = 15.0  # conservative assumption: 15% under-consumption

    for vc, annexe in commitments:
        if not vc.annual_kwh or vc.annual_kwh <= 0:
            continue

        tolerance_down = vc.tolerance_pct_down or 10.0
        penalty_rate = vc.penalty_eur_kwh_below or 0

        if penalty_rate <= 0:
            continue

        # If assumed deviation exceeds tolerance, penalty applies
        excess_deviation = deviation_pct - tolerance_down
        if excess_deviation > 0:
            penalized_kwh = vc.annual_kwh * (excess_deviation / 100.0)
            total_penalty += penalized_kwh * penalty_rate

    return total_penalty


def _get_spot_price(db: Session) -> float:
    """Get current spot price from mkt_prices, fallback to default."""
    try:
        from models.market_models import MktPrice, MarketType, PriceZone

        today = date.today()
        avg_30d = (
            db.query(func.avg(MktPrice.price_eur_mwh))
            .filter(
                MktPrice.zone == PriceZone.FR,
                MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
                MktPrice.delivery_start >= today - timedelta(days=30),
                MktPrice.delivery_start <= today,
            )
            .scalar()
        )
        if avg_30d and avg_30d > 0:
            return avg_30d / 1000.0  # Convert EUR/MWh → EUR/kWh
    except Exception:
        _logger.warning("Could not fetch spot price from mkt_prices, using default")

    return DEFAULT_PRICE_ELEC_EUR_KWH


def _empty_result() -> dict:
    return {
        "renewal_risk_eur": 0.0,
        "price_gap_risk_eur": 0.0,
        "volume_penalty_risk_eur": 0.0,
        "total_eur": 0.0,
        "contracts_at_risk": 0,
        "details": [],
    }
