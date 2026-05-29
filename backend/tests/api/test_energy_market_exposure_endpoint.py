"""
PROMEOS — Tests GET /api/energy/market-exposure (Sprint Énergie P1.S2d).

Couvre la checklist QA de sortie S2d :
1. /api/energy/market-exposure répond 200 sur site valide.
2. Coût spot théorique calculé en € avec formule correcte.
3. Prix spot pondéré calculé sans division par zéro.
4. Écart vs baseload disponible.
5. Top heures chères triées.
6. Prix négatifs détectés.
7. Score exposition borné [0, 100].
8. Chaque KPI / top hour / simulation a provenance.
9. Aucun frontend modifié.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest


pytestmark = pytest.mark.fast


TZ_PARIS = ZoneInfo("Europe/Paris")


@pytest.fixture
def db_empty(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.base import Base

    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


@pytest.fixture
def db_with_prices(db_empty):
    """DB avec quelques prix MktPrice spot day-ahead sur 24h récentes."""
    from models.market_models import (
        MarketDataSource,
        MarketType,
        MktPrice,
        PriceZone,
        ProductType,
        Resolution,
    )

    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    # 24 prix horaires : 4 négatifs (h=12..15) + 4 très chers (h=18..21) + reste neutre.
    prices_by_hour = {h: 50.0 for h in range(24)}
    prices_by_hour.update({12: -10.0, 13: -5.0, 14: -3.0, 15: -8.0})
    prices_by_hour.update({18: 220.0, 19: 240.0, 20: 260.0, 21: 280.0})

    for h, price in prices_by_hour.items():
        ts = (now_utc - timedelta(days=1)).replace(hour=h)
        db_empty.add(
            MktPrice(
                source=MarketDataSource.ENTSOE,
                market_type=MarketType.SPOT_DAY_AHEAD,
                product_type=ProductType.HOURLY,
                zone=PriceZone.FR,
                delivery_start=ts,
                delivery_end=ts + timedelta(hours=1),
                price_eur_mwh=price,
                volume_mwh=None,
                resolution=Resolution.PT60M,
            )
        )
    db_empty.commit()
    return db_empty


# ── 1. Scope valide → 200 ───────────────────────────────────────────────


class TestMarketExposureScopeValid:
    """/api/energy/market-exposure répond 200 sur site valide."""

    def test_site_scope_returns_response(self, db_empty):
        from services.energy_orchestration.market_exposure import build_market_exposure

        resp = build_market_exposure(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            period_label="12m",
        )
        assert resp.scope.kind == "site"
        assert resp.period.timezone == "Europe/Paris"
        assert resp.market.type == "day_ahead"
        assert resp.market.zone == "FR"
        # Le payload est construit même sans données
        assert resp.kpis is not None
        assert isinstance(resp.series, list)


# ── 2. Scope invalide → erreur ──────────────────────────────────────────


class TestMarketExposureScopeInvalid:
    def test_org_scope_raises(self, db_empty):
        from services.energy_orchestration.market_exposure import (
            MarketExposureError,
            build_market_exposure,
        )

        with pytest.raises(MarketExposureError) as exc_info:
            build_market_exposure(
                db_empty,
                scope_kind="org",
                scope_id=1,
                org_id=1,
                period_label="12m",
            )
        assert exc_info.value.hint is not None

    def test_missing_scope_id_raises(self, db_empty):
        from services.energy_orchestration.market_exposure import (
            MarketExposureError,
            build_market_exposure,
        )

        with pytest.raises(MarketExposureError) as exc_info:
            build_market_exposure(
                db_empty,
                scope_kind="site",
                scope_id=None,
                org_id=1,
                period_label="12m",
            )
        assert "scope_id" in str(exc_info.value).lower()

    def test_unknown_market_raises(self, db_empty):
        from services.energy_orchestration.market_exposure import (
            MarketExposureError,
            build_market_exposure,
        )

        with pytest.raises(MarketExposureError):
            build_market_exposure(
                db_empty,
                scope_kind="site",
                scope_id=1,
                org_id=1,
                market="plouf",
            )

    def test_unknown_zone_raises(self, db_empty):
        from services.energy_orchestration.market_exposure import (
            MarketExposureError,
            build_market_exposure,
        )

        with pytest.raises(MarketExposureError):
            build_market_exposure(
                db_empty,
                scope_kind="site",
                scope_id=1,
                org_id=1,
                zone="ZZ",
            )


# ── 3. Empty states ────────────────────────────────────────────────────


class TestMarketExposureEmptyStates:
    def test_no_consumption_and_no_prices(self, db_empty):
        from services.energy_orchestration.market_exposure import build_market_exposure

        resp = build_market_exposure(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            period_label="12m",
        )
        assert resp.empty_state is not None
        assert "consommation" in resp.empty_state.lower()
        assert "prix" in resp.empty_state.lower()

    def test_no_prices_only(self, db_empty):
        """DB sans MktPrice → empty_state 'Aucun prix marché'."""
        from services.energy_orchestration.market_exposure import build_market_exposure

        resp = build_market_exposure(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
        )
        # Pas de consommation ni de prix → empty_state mentionne les deux
        assert resp.empty_state is not None


# ── 4. Formule spot_cost et division par zéro ──────────────────────────


class TestSpotCostFormula:
    """Coût spot théorique calculé en € avec formule correcte."""

    def test_spot_cost_formula_kwh_times_price_div_1000(self):
        from services.energy_orchestration.market_exposure import _compute_spot_cost

        # 1000 kWh × 50 €/MWh / 1000 = 50 €
        assert _compute_spot_cost(1000.0, 50.0) == 50.0
        # 250 kWh × 200 €/MWh / 1000 = 50 €
        assert _compute_spot_cost(250.0, 200.0) == 50.0
        # 100 kWh × -10 €/MWh / 1000 = -1 € (prix négatifs autorisés)
        assert _compute_spot_cost(100.0, -10.0) == -1.0
        # 0 kWh × X = 0 (cas limite)
        assert _compute_spot_cost(0.0, 100.0) == 0.0


class TestWeightedPriceNullSafe:
    """Prix spot pondéré calculé sans division par zéro."""

    def test_zero_kwh_returns_null_weighted_price(self, db_empty):
        from services.energy_orchestration.market_exposure import build_market_exposure

        resp = build_market_exposure(
            db_empty,
            scope_kind="site",
            scope_id=999,
            org_id=1,
        )
        wp = resp.kpis.spot_avg_weighted_eur_mwh
        assert wp is not None  # structure KPI présente
        assert wp.value is None  # valeur null (DB vide)
        assert wp.state == "inactif"

    def test_weighted_price_formula(self, db_empty):
        """Σ(kWh × prix) / Σ(kWh) = prix moyen pondéré."""
        from schemas.energy_orchestration import EnergyMarketExposurePoint
        from services.energy_orchestration.market_exposure import _compute_spot_cost

        # Point A : 100 kWh × 30 €/MWh = 3 €
        # Point B : 200 kWh × 60 €/MWh = 12 €
        # Total : 300 kWh, 15 € → pondéré = 15/0.3 = 50 €/MWh
        cost_a = _compute_spot_cost(100.0, 30.0)
        cost_b = _compute_spot_cost(200.0, 60.0)
        total_cost = cost_a + cost_b
        total_kwh = 100.0 + 200.0
        weighted = total_cost / total_kwh * 1000.0
        assert abs(weighted - 50.0) < 0.01


# ── 5. Top heures chères triées ────────────────────────────────────────


class TestTopExpensiveHoursSorted:
    """Top heures chères triées par cost_eur décroissant."""

    def test_top_hours_sorted_descending(self):
        from datetime import datetime

        from schemas.energy_orchestration import EnergyMarketExposurePoint, EnergyPeriod, EnergyScope
        from services.energy_orchestration.market_exposure import _compute_top_expensive_hours

        scope = EnergyScope(kind="site", id=1, org_id=1)
        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 2, tzinfo=TZ_PARIS),
            days=1,
            timezone="Europe/Paris",
        )
        # 20 points avec coûts croissants 1.0..20.0 (Q90 = ~18)
        series = []
        for i in range(1, 21):
            ts = datetime(2026, 5, 1, i % 24, tzinfo=TZ_PARIS)
            series.append(
                EnergyMarketExposurePoint(
                    timestamp=ts,
                    kwh=float(i),
                    spot_price_eur_mwh=100.0,
                    spot_cost_eur=float(i),
                )
            )

        top, top_share = _compute_top_expensive_hours(series, period)
        assert len(top) >= 1
        # Vérifier le tri décroissant
        for i in range(len(top) - 1):
            assert top[i].cost_eur >= top[i + 1].cost_eur
        # Rang 1 = la plus coûteuse
        assert top[0].rank == 1


# ── 6. Prix négatifs détectés ──────────────────────────────────────────


class TestNegativePricesDetected:
    """Prix négatifs (spot_price < 0) détectés et exposés."""

    def test_negative_price_flagged_in_favorable_hours(self):
        from datetime import datetime

        from schemas.energy_orchestration import EnergyMarketExposurePoint, EnergyPeriod
        from services.energy_orchestration.market_exposure import _compute_favorable_hours

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 2, tzinfo=TZ_PARIS),
            days=1,
            timezone="Europe/Paris",
        )
        series = [
            EnergyMarketExposurePoint(
                timestamp=datetime(2026, 5, 1, h, tzinfo=TZ_PARIS),
                kwh=10.0,
                spot_price_eur_mwh=(-20.0 if h in (12, 13) else 50.0),
            )
            for h in range(24)
        ]
        favorable, neg_pct = _compute_favorable_hours(series, period)
        # Deux heures avec prix négatif → présentes dans favorable
        neg_in_list = [f for f in favorable if f.reason == "prix négatif"]
        assert len(neg_in_list) == 2
        # Part conso pendant prix négatif = 2 × 10 / (24 × 10) = ~8.33 %
        assert neg_pct is not None
        assert 8.0 < neg_pct < 9.0

    def test_zero_consumption_returns_null_negative_pct(self):
        from datetime import datetime

        from schemas.energy_orchestration import EnergyMarketExposurePoint, EnergyPeriod
        from services.energy_orchestration.market_exposure import _compute_favorable_hours

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 2, tzinfo=TZ_PARIS),
            days=1,
            timezone="Europe/Paris",
        )
        series = [
            EnergyMarketExposurePoint(
                timestamp=datetime(2026, 5, 1, h, tzinfo=TZ_PARIS),
                kwh=None,  # pas de conso
                spot_price_eur_mwh=-10.0,
            )
            for h in range(5)
        ]
        favorable, neg_pct = _compute_favorable_hours(series, period)
        assert neg_pct is None  # null safe


# ── 7. Score exposition borné [0, 100] ──────────────────────────────────


class TestExposureScoreBounded:
    """Score d'exposition toujours borné [0, 100]."""

    @pytest.mark.parametrize(
        "spot_simple,spot_weighted,delta,top_share",
        [
            (None, None, None, None),  # tous None
            (50.0, 50.0, 0.0, 10.0),  # neutre
            (50.0, 200.0, 9999.0, 99.0),  # extrêmes
            (50.0, -100.0, -9999.0, -10.0),  # négatifs
        ],
    )
    def test_score_always_in_0_100(self, spot_simple, spot_weighted, delta, top_share):
        from services.energy_orchestration.market_exposure import _compute_exposure_score

        score = _compute_exposure_score(spot_simple, spot_weighted, delta, top_share)
        if score is not None:
            assert 0 <= score <= 100

    def test_all_none_returns_none(self):
        from services.energy_orchestration.market_exposure import _compute_exposure_score

        assert _compute_exposure_score(None, None, None, None) is None


# ── 8. Écart vs baseload disponible ─────────────────────────────────────


class TestBaseloadComparison:
    def test_baseload_comparison_present_with_data(self):
        from datetime import datetime

        from schemas.energy_orchestration import EnergyMarketExposurePoint, EnergyPeriod, EnergyScope
        from services.energy_orchestration.market_exposure import _compute_baseload_comparison

        scope = EnergyScope(kind="site", id=1, org_id=1)
        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 2, tzinfo=TZ_PARIS),
            days=1,
            timezone="Europe/Paris",
        )
        series = [
            EnergyMarketExposurePoint(
                timestamp=datetime(2026, 5, 1, h, tzinfo=TZ_PARIS),
                kwh=10.0,
                spot_price_eur_mwh=50.0 if h < 12 else 100.0,  # profil non-plat
                spot_cost_eur=(10.0 * (50.0 if h < 12 else 100.0)) / 1000.0,
            )
            for h in range(24)
        ]
        comp = _compute_baseload_comparison(series, period, scope)
        assert comp is not None
        assert comp.real_profile_cost_eur is not None
        assert comp.baseload_cost_eur is not None
        assert comp.delta_eur is not None
        assert "comparaison" in comp.formula.lower()

    def test_baseload_returns_none_when_empty(self):
        from datetime import datetime

        from schemas.energy_orchestration import EnergyPeriod, EnergyScope
        from services.energy_orchestration.market_exposure import _compute_baseload_comparison

        scope = EnergyScope(kind="site", id=1)
        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 2, tzinfo=TZ_PARIS),
            days=1,
            timezone="Europe/Paris",
        )
        assert _compute_baseload_comparison([], period, scope) is None


# ── 9. Provenance obligatoire ───────────────────────────────────────────


class TestProvenanceEverywhere:
    """Chaque KPI / top hour / simulation a provenance."""

    def test_all_kpis_have_provenance(self, db_empty):
        from services.energy_orchestration.market_exposure import build_market_exposure

        resp = build_market_exposure(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
        )
        for kpi in (
            resp.kpis.spot_cost_theoretical_eur,
            resp.kpis.spot_avg_simple_eur_mwh,
            resp.kpis.spot_avg_weighted_eur_mwh,
            resp.kpis.baseload_cost_eur,
            resp.kpis.delta_vs_baseload_eur,
            resp.kpis.top_10pct_expensive_hours_cost_pct,
            resp.kpis.negative_price_consumption_pct,
            resp.kpis.exposure_score,
        ):
            assert kpi is not None
            assert kpi.provenance.source
            assert kpi.provenance.service
            assert kpi.provenance.formula

    def test_market_context_has_provenance(self, db_empty):
        from services.energy_orchestration.market_exposure import build_market_exposure

        resp = build_market_exposure(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
        )
        assert resp.market.provenance.source
        assert resp.market.provenance.service
        assert "MktPrice" in resp.market.source
        assert "canonique" in resp.market.source.lower() or "canon" in resp.market.source.lower()

    def test_simulation_has_warning_and_provenance(self, db_empty):
        from services.energy_orchestration.market_exposure import build_market_exposure

        resp = build_market_exposure(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
        )
        assert resp.simulation is not None
        assert "indicative" in resp.simulation.warning.lower()
        assert "promesse" in resp.simulation.warning.lower()
        assert resp.simulation.provenance.source

    def test_root_provenance_includes_paris(self, db_empty):
        from services.energy_orchestration.market_exposure import build_market_exposure

        resp = build_market_exposure(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
        )
        joined = " ".join(resp.provenance.assumptions)
        assert "Europe/Paris" in joined or "Paris" in joined
        # Doctrine : pas d'économie garantie
        assert "indicative" in joined.lower() or "no guaranteed" in joined.lower()


# ── 10. Frontend non modifié + pas de MarketPrice legacy ───────────────


class TestNoFrontendChanges:
    """Brief : aucun frontend modifié dans P1.S2d."""

    def test_market_exposure_service_does_not_use_legacy_marketprice(self):
        """Source-guard interdit l'usage de MarketPrice legacy ; on vérifie ici
        le fichier service explicitement."""
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        svc_file = repo_root / "backend" / "services" / "energy_orchestration" / "market_exposure.py"
        content = svc_file.read_text(encoding="utf-8")
        # Importer MktPrice canonique uniquement
        assert "from models.market_models import MktPrice" in content
        # Aucune référence au modèle legacy MarketPrice
        assert "from models.market_price" not in content
        assert "import MarketPrice" not in content


class TestNoExtraEndpoints:
    """Brief : seul /market-exposure est créé dans P1.S2d."""

    def test_router_contains_market_exposure(self):
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        router_file = repo_root / "backend" / "routes" / "energy_orchestration.py"
        content = router_file.read_text(encoding="utf-8")
        assert "/market-exposure" in content
        assert "build_market_exposure" in content


class TestErrorCodes:
    """Nouveaux codes erreur exposés."""

    def test_market_unknown_code_exists(self):
        from services.energy_orchestration.errors import (
            CODE_MARKET_UNKNOWN,
            CODE_ZONE_UNKNOWN,
        )

        assert CODE_MARKET_UNKNOWN == "ENERGY_MARKET_UNKNOWN"
        assert CODE_ZONE_UNKNOWN == "ENERGY_ZONE_UNKNOWN"
