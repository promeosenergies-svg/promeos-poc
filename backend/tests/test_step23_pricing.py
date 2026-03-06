"""
Step 23 — Modèle pricing réaliste (forward + spread + cap)
Backend tests: purchase_pricing engine + market context endpoint.
"""

import pytest
from services.purchase_pricing import compute_strategy_price, get_market_context


# ── Fixtures ──

MARKET_CTX = {
    "spot_avg_30d_eur_mwh": 68.0,
    "spot_avg_12m_eur_mwh": 72.0,
    "spot_current_eur_mwh": 68.0,
    "volatility_12m_eur_mwh": 15.0,
    "trend_30d_vs_12m_pct": -5.6,
}


# ── A. compute_strategy_price — fixe ──

class TestFixeStrategy:
    def test_fixe_returns_all_fields(self):
        r = compute_strategy_price("fixe", MARKET_CTX)
        assert "price_eur_mwh" in r
        assert "price_eur_kwh" in r
        assert "risk_score" in r
        assert "p10_eur_mwh" in r
        assert "p90_eur_mwh" in r
        assert "breakdown" in r
        assert "methodology" in r

    def test_fixe_price_above_spot(self):
        r = compute_strategy_price("fixe", MARKET_CTX)
        assert r["price_eur_mwh"] > MARKET_CTX["spot_avg_30d_eur_mwh"]

    def test_fixe_p10_equals_p90(self):
        """Fixe = pas de bande de prix."""
        r = compute_strategy_price("fixe", MARKET_CTX)
        assert r["p10_eur_mwh"] == r["p90_eur_mwh"]

    def test_fixe_eur_kwh_conversion(self):
        r = compute_strategy_price("fixe", MARKET_CTX)
        assert abs(r["price_eur_kwh"] - r["price_eur_mwh"] / 1000) < 0.00001

    def test_fixe_breakdown_has_components(self):
        r = compute_strategy_price("fixe", MARKET_CTX)
        bd = r["breakdown"]
        assert "spot_base" in bd
        assert "terme_premium" in bd
        assert "supplier_margin" in bd


# ── B. compute_strategy_price — indexe ──

class TestIndexeStrategy:
    def test_indexe_has_spread(self):
        r = compute_strategy_price("indexe", MARKET_CTX)
        assert r["breakdown"]["spread"] > 0

    def test_indexe_has_cap(self):
        r = compute_strategy_price("indexe", MARKET_CTX)
        assert "cap_eur_mwh" in r["breakdown"]

    def test_indexe_p90_below_cap(self):
        r = compute_strategy_price("indexe", MARKET_CTX)
        assert r["p90_eur_mwh"] <= r["breakdown"]["cap_eur_mwh"]

    def test_indexe_risk_higher_than_fixe(self):
        fixe = compute_strategy_price("fixe", MARKET_CTX)
        indexe = compute_strategy_price("indexe", MARKET_CTX)
        assert indexe["risk_score"] > fixe["risk_score"]


# ── C. compute_strategy_price — spot ──

class TestSpotStrategy:
    def test_spot_includes_aggregator_fee(self):
        r = compute_strategy_price("spot", MARKET_CTX)
        assert r["breakdown"]["aggregator_fee"] > 0

    def test_spot_profile_factor_applied(self):
        r1 = compute_strategy_price("spot", MARKET_CTX, profile_factor=1.0)
        r2 = compute_strategy_price("spot", MARKET_CTX, profile_factor=1.2)
        assert r2["price_eur_mwh"] > r1["price_eur_mwh"]

    def test_spot_risk_highest(self):
        spot = compute_strategy_price("spot", MARKET_CTX)
        fixe = compute_strategy_price("fixe", MARKET_CTX)
        assert spot["risk_score"] > fixe["risk_score"]


# ── D. compute_strategy_price — reflex_solar ──

class TestReflexSolarStrategy:
    def test_reflex_solar_has_solar_discount(self):
        r = compute_strategy_price("reflex_solar", MARKET_CTX)
        assert r["breakdown"]["solar_discount_pct"] < 0

    def test_reflex_solar_has_blended_price(self):
        r = compute_strategy_price("reflex_solar", MARKET_CTX)
        assert "blended_price" in r["breakdown"]

    def test_reflex_solar_methodology_mentions_blocs(self):
        r = compute_strategy_price("reflex_solar", MARKET_CTX)
        assert "solaire" in r["methodology"].lower() or "bloc" in r["methodology"].lower()


# ── E. Unknown strategy ──

class TestUnknownStrategy:
    def test_unknown_returns_none(self):
        r = compute_strategy_price("unknown_strategy", MARKET_CTX)
        assert r is None


# ── F. Horizon months effect ──

class TestHorizonMonths:
    def test_fixe_longer_horizon_higher_price(self):
        r12 = compute_strategy_price("fixe", MARKET_CTX, horizon_months=12)
        r24 = compute_strategy_price("fixe", MARKET_CTX, horizon_months=24)
        assert r24["price_eur_mwh"] > r12["price_eur_mwh"]

    def test_fixe_terme_premium_capped(self):
        """Prime de terme plafonnée à 12%."""
        r = compute_strategy_price("fixe", MARKET_CTX, horizon_months=60)
        spot = MARKET_CTX["spot_avg_30d_eur_mwh"]
        max_forward = spot * (1 + 12 / 100)
        # price = forward + margin, forward <= spot * 1.12
        assert r["breakdown"]["terme_premium"] <= spot * 0.12 + 0.01


# ── G. get_market_context — source guard ──

class TestGetMarketContextSignature:
    def test_function_exists(self):
        assert callable(get_market_context)

    def test_accepts_db_and_energy_type(self):
        import inspect
        sig = inspect.signature(get_market_context)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "energy_type" in params
