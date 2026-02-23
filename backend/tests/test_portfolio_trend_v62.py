"""
test_portfolio_trend_v62.py — Tests V62 : Portfolio Trend réel (in-memory cache)

Couverture :
  - trend None au 1er appel (pas de snapshot précédent)
  - trend non-None au 2ème appel (snapshot précédent disponible)
  - direction "stable" si delta_risk ≤ EPS (1.0 €)
  - direction "up" si risque augmente
  - direction "down" si risque diminue
  - risk_eur_delta et sites_count_delta corrects
  - vs_computed_at = computed_at du snapshot précédent
  - Filtre site_id → pas de mise en cache (trend=None même au 2ème appel)
  - Filtre portefeuille_id → pas de mise en cache
  - Multi-org : cache isolé par org_id (org A ne voit pas le snapshot de org B)
  - clear_snapshot isole correctement
  - clear_all vide tout le cache
  - Backward compat : champs V61 toujours présents quand trend non-None

Notes techniques :
  - Le cache est un module-level dict partagé entre tests → chaque test nettoie
    explicitement via clear_all() en setup (fixture autouse).
  - On simule "deux appels successifs" via deux appels HTTP via TestClient dans
    le même test, sans modifier la DB entre les deux.
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models import (
    Organisation, EntiteJuridique, Portefeuille, Site, Batiment, Usage,
    Compteur, DeliveryPoint, EnergyContract,
    TypeSite, TypeCompteur, TypeUsage,
    DeliveryPointStatus, DeliveryPointEnergyType, BillingEnergyType,
)
from database import get_db
from main import app
import services.patrimoine_portfolio_cache as _cache_mod


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_cache():
    """Nettoie le cache avant chaque test pour éviter les interférences."""
    _cache_mod.clear_all()
    yield
    _cache_mod.clear_all()


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_org(db, nom):
    org = Organisation(nom=nom, actif=True)
    db.add(org)
    db.flush()
    siren = str(abs(hash(nom)) % 10**9).zfill(9)
    ej = EntiteJuridique(nom="EJ " + nom, organisation_id=org.id, siren=siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom="PF " + nom, entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    return org, pf


def _make_site_with_mismatch(db, pf, nom="Site Mismatch"):
    site = Site(
        nom=nom, type=TypeSite.BUREAU,
        surface_m2=5000.0, portefeuille_id=pf.id, actif=True,
    )
    db.add(site)
    db.flush()
    bat = Batiment(site_id=site.id, nom="Bat", surface_m2=3000.0)
    db.add(bat)
    db.flush()
    db.add(Usage(batiment_id=bat.id, type=TypeUsage.BUREAUX))
    dp = DeliveryPoint(
        code="12345678901234", energy_type=DeliveryPointEnergyType.ELEC,
        site_id=site.id, status=DeliveryPointStatus.ACTIVE,
    )
    db.add(dp)
    db.flush()
    db.add(Compteur(
        site_id=site.id, type=TypeCompteur.ELECTRICITE,
        numero_serie=f"SN-{site.id}", actif=True, delivery_point_id=dp.id,
    ))
    db.add(EnergyContract(
        site_id=site.id, energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF",
        start_date=date(2023, 1, 1), end_date=date(2025, 12, 31),
    ))
    db.commit()
    return site


def _make_clean_site(db, pf, nom="Site Clean"):
    site = Site(
        nom=nom, type=TypeSite.BUREAU,
        surface_m2=1000.0, portefeuille_id=pf.id, actif=True,
    )
    db.add(site)
    db.flush()
    bat = Batiment(site_id=site.id, nom="Bat", surface_m2=1000.0)
    db.add(bat)
    db.flush()
    db.add(Usage(batiment_id=bat.id, type=TypeUsage.BUREAUX))
    dp = DeliveryPoint(
        code="99999999999999", energy_type=DeliveryPointEnergyType.ELEC,
        site_id=site.id, status=DeliveryPointStatus.ACTIVE,
    )
    db.add(dp)
    db.flush()
    db.add(Compteur(
        site_id=site.id, type=TypeCompteur.ELECTRICITE,
        numero_serie=f"SN-C{site.id}", actif=True, delivery_point_id=dp.id,
    ))
    db.add(EnergyContract(
        site_id=site.id, energy_type=BillingEnergyType.ELEC,
        supplier_name="Engie",
        start_date=date(2023, 1, 1), end_date=date(2025, 12, 31),
    ))
    db.commit()
    return site


# ── Tests cache unitaires ─────────────────────────────────────────────────────

class TestPortfolioCacheUnit:
    def test_get_none_when_empty(self):
        assert _cache_mod.get_prev_snapshot(999) is None

    def test_set_and_get(self):
        snap = {"computed_at": "2026-01-01T00:00:00Z", "total_estimated_risk_eur": 500.0, "sites_count": 3}
        _cache_mod.set_snapshot(1, snap)
        result = _cache_mod.get_prev_snapshot(1)
        assert result is not None
        assert result["total_estimated_risk_eur"] == 500.0
        assert result["sites_count"] == 3

    def test_set_ignores_extra_fields(self):
        snap = {"computed_at": "Z", "total_estimated_risk_eur": 100.0, "sites_count": 1, "extra": "ignored"}
        _cache_mod.set_snapshot(1, snap)
        result = _cache_mod.get_prev_snapshot(1)
        assert "extra" not in result

    def test_clear_snapshot_removes_org(self):
        _cache_mod.set_snapshot(1, {"computed_at": "Z", "total_estimated_risk_eur": 0.0, "sites_count": 0})
        _cache_mod.clear_snapshot(1)
        assert _cache_mod.get_prev_snapshot(1) is None

    def test_clear_snapshot_doesnt_affect_other_orgs(self):
        _cache_mod.set_snapshot(1, {"computed_at": "Z", "total_estimated_risk_eur": 0.0, "sites_count": 0})
        _cache_mod.set_snapshot(2, {"computed_at": "Z", "total_estimated_risk_eur": 0.0, "sites_count": 0})
        _cache_mod.clear_snapshot(1)
        assert _cache_mod.get_prev_snapshot(1) is None
        assert _cache_mod.get_prev_snapshot(2) is not None

    def test_clear_all(self):
        _cache_mod.set_snapshot(1, {"computed_at": "Z", "total_estimated_risk_eur": 0.0, "sites_count": 0})
        _cache_mod.set_snapshot(2, {"computed_at": "Z", "total_estimated_risk_eur": 0.0, "sites_count": 0})
        _cache_mod.clear_all()
        assert _cache_mod.get_prev_snapshot(1) is None
        assert _cache_mod.get_prev_snapshot(2) is None

    def test_set_none_org_id_ignored(self):
        _cache_mod.set_snapshot(None, {"computed_at": "Z", "total_estimated_risk_eur": 0.0, "sites_count": 0})
        assert _cache_mod.get_prev_snapshot(None) is None

    def test_overwrite_snapshot(self):
        _cache_mod.set_snapshot(1, {"computed_at": "A", "total_estimated_risk_eur": 100.0, "sites_count": 1})
        _cache_mod.set_snapshot(1, {"computed_at": "B", "total_estimated_risk_eur": 200.0, "sites_count": 2})
        result = _cache_mod.get_prev_snapshot(1)
        assert result["total_estimated_risk_eur"] == 200.0
        assert result["computed_at"] == "B"


# ── Tests trend endpoint (intégration) ───────────────────────────────────────

class TestPortfolioTrendV62:
    def test_trend_none_on_first_call(self, client, db):
        """Premier appel → pas de snapshot → trend est null."""
        _, pf = _make_org(db, "OrgTrendFirst")
        _make_site_with_mismatch(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert "trend" in data
        assert data["trend"] is None

    def test_trend_non_none_on_second_call(self, client, db):
        """Deuxième appel → snapshot disponible → trend non-null."""
        _, pf = _make_org(db, "OrgTrendSecond")
        _make_site_with_mismatch(db, pf)
        client.get("/api/patrimoine/portfolio-summary")   # 1er : peuple cache
        data = client.get("/api/patrimoine/portfolio-summary").json()  # 2ème
        assert data["trend"] is not None

    def test_trend_direction_stable_same_data(self, client, db):
        """Deux appels sans changement → delta ≈ 0 → direction stable."""
        _, pf = _make_org(db, "OrgStable")
        _make_site_with_mismatch(db, pf)
        client.get("/api/patrimoine/portfolio-summary")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["trend"] is not None
        assert data["trend"]["direction"] == "stable"

    def test_trend_risk_eur_delta_is_zero_for_same_data(self, client, db):
        """Deux appels identiques → risk_eur_delta = 0.0."""
        _, pf = _make_org(db, "OrgDelta0")
        _make_site_with_mismatch(db, pf)
        client.get("/api/patrimoine/portfolio-summary")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["trend"]["risk_eur_delta"] == 0.0

    def test_trend_sites_count_delta_zero_same_data(self, client, db):
        """Deux appels sans ajout/suppression de site → sites_count_delta = 0."""
        _, pf = _make_org(db, "OrgCountDelta")
        _make_site_with_mismatch(db, pf)
        client.get("/api/patrimoine/portfolio-summary")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["trend"]["sites_count_delta"] == 0

    def test_trend_direction_up_after_risk_increase(self, client, db):
        """Simuler une hausse de risque en injectant un snapshot artificiel avec risk plus bas."""
        _, pf = _make_org(db, "OrgUp")
        _make_site_with_mismatch(db, pf)
        # 1er appel → get current risk
        first = client.get("/api/patrimoine/portfolio-summary").json()
        current_risk = first["total_estimated_risk_eur"]
        org_id = first["scope"]["org_id"]
        # Forcer un snapshot précédent avec un risque inférieur (→ delta > EPS → "up")
        _cache_mod.set_snapshot(org_id, {
            "computed_at": "2026-01-01T00:00:00Z",
            "total_estimated_risk_eur": max(0.0, current_risk - 5000.0),
            "sites_count": 1,
        })
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["trend"] is not None
        assert data["trend"]["direction"] == "up"
        assert data["trend"]["risk_eur_delta"] > 0

    def test_trend_direction_down_after_risk_decrease(self, client, db):
        """Simuler une baisse de risque via snapshot artificiel plus élevé."""
        _, pf = _make_org(db, "OrgDown")
        _make_site_with_mismatch(db, pf)
        first = client.get("/api/patrimoine/portfolio-summary").json()
        current_risk = first["total_estimated_risk_eur"]
        org_id = first["scope"]["org_id"]
        # Forcer snapshot avec risque plus élevé (→ delta < -EPS → "down")
        _cache_mod.set_snapshot(org_id, {
            "computed_at": "2026-01-01T00:00:00Z",
            "total_estimated_risk_eur": current_risk + 5000.0,
            "sites_count": 1,
        })
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["trend"] is not None
        assert data["trend"]["direction"] == "down"
        assert data["trend"]["risk_eur_delta"] < 0

    def test_trend_vs_computed_at_matches_previous_snapshot(self, client, db):
        """vs_computed_at dans trend = computed_at du snapshot précédent."""
        _, pf = _make_org(db, "OrgVsAt")
        _make_site_with_mismatch(db, pf)
        first = client.get("/api/patrimoine/portfolio-summary").json()
        first_computed_at = first["computed_at"]
        org_id = first["scope"]["org_id"]
        # Le cache a été mis à jour avec first["computed_at"]
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["trend"]["vs_computed_at"] == first_computed_at

    def test_trend_fields_present(self, client, db):
        """Trend non-None → tous les champs attendus présents."""
        _, pf = _make_org(db, "OrgTrendFields")
        _make_site_with_mismatch(db, pf)
        client.get("/api/patrimoine/portfolio-summary")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        t = data["trend"]
        assert t is not None
        for field in ("risk_eur_delta", "sites_count_delta", "direction", "vs_computed_at"):
            assert field in t, f"Champ manquant dans trend : {field}"

    def test_trend_none_with_site_filter(self, client, db):
        """Filtre site_id → pas de mise en cache → trend toujours None."""
        _, pf = _make_org(db, "OrgSiteFilter")
        site = _make_site_with_mismatch(db, pf)
        url = f"/api/patrimoine/portfolio-summary?site_id={site.id}"
        client.get(url)           # 1er appel avec filtre
        data = client.get(url).json()   # 2ème
        assert data["trend"] is None

    def test_trend_none_with_portefeuille_filter(self, client, db):
        """Filtre portefeuille_id → pas de mise en cache → trend toujours None."""
        _, pf = _make_org(db, "OrgPfFilter")
        _make_site_with_mismatch(db, pf)
        url = f"/api/patrimoine/portfolio-summary?portefeuille_id={pf.id}"
        client.get(url)
        data = client.get(url).json()
        assert data["trend"] is None

    def test_trend_multi_org_isolation(self, db):
        """Org A et Org B ont des caches strictement isolés."""
        # Deux clients distincts avec des DB distinctes serait idéal mais impossible
        # avec StaticPool partagé. On teste l'isolation au niveau du module cache :
        org_a_id = 100
        org_b_id = 200
        _cache_mod.set_snapshot(org_a_id, {
            "computed_at": "2026-01-01T00:00:00Z",
            "total_estimated_risk_eur": 1000.0,
            "sites_count": 2,
        })
        assert _cache_mod.get_prev_snapshot(org_b_id) is None
        _cache_mod.clear_snapshot(org_a_id)
        # B non affecté (déjà None, stable)
        assert _cache_mod.get_prev_snapshot(org_b_id) is None

    def test_backward_compat_v61_fields_with_trend(self, client, db):
        """Champs V61 (sites_health) toujours présents quand trend est non-None."""
        _, pf = _make_org(db, "OrgCompatV61")
        _make_site_with_mismatch(db, pf)
        client.get("/api/patrimoine/portfolio-summary")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert "sites_health" in data
        sh = data["sites_health"]
        for key in ("healthy", "warning", "critical", "healthy_pct"):
            assert key in sh

    def test_trend_none_empty_scope_never_cached(self, client, db):
        """Scope vide → trend None, et le cache n'est pas pollué."""
        _make_org(db, "OrgEmptyTrend62")
        client.get("/api/patrimoine/portfolio-summary")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["trend"] is None
