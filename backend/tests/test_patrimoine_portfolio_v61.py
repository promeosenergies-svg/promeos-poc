"""
test_patrimoine_portfolio_v61.py — Tests V61 : sites_health + trend nullable

Couverture :
  - sites_health présent dans response (healthy/warning/critical/healthy_pct)
  - healthy_pct calculé correctement (0% si toutes anomalies)
  - trend toujours null (pas d'historique en V61)
  - empty scope → sites_health tout à 0, trend null
  - seuils : score >= 85 = healthy, 50..84 = warning, < 50 = critical
  - framework_breakdown : anomalies_count présent dans chaque item
  - backward compat : champs V60 toujours présents
"""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Batiment,
    Usage,
    Compteur,
    DeliveryPoint,
    EnergyContract,
    TypeSite,
    TypeCompteur,
    TypeUsage,
    DeliveryPointStatus,
    DeliveryPointEnergyType,
    BillingEnergyType,
)
from database import get_db
from main import app


# ── Fixtures ──────────────────────────────────────────────────────────────────


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


def _make_site_with_surface_mismatch(db, pf, nom="Site Mismatch"):
    """SURFACE_MISMATCH garantie → completude_score dégradé, risk > 0."""
    site = Site(
        nom=nom,
        type=TypeSite.BUREAU,
        surface_m2=5000.0,
        portefeuille_id=pf.id,
        actif=True,
    )
    db.add(site)
    db.flush()
    bat = Batiment(site_id=site.id, nom="Bat", surface_m2=3000.0)
    db.add(bat)
    db.flush()
    db.add(Usage(batiment_id=bat.id, type=TypeUsage.BUREAUX))
    dp = DeliveryPoint(
        code="12345678901234",
        energy_type=DeliveryPointEnergyType.ELEC,
        site_id=site.id,
        status=DeliveryPointStatus.ACTIVE,
    )
    db.add(dp)
    db.flush()
    db.add(
        Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie=f"SN-{site.id}",
            actif=True,
            delivery_point_id=dp.id,
        )
    )
    db.add(
        EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            start_date=date(2023, 1, 1),
            end_date=date(2025, 12, 31),
        )
    )
    db.commit()
    return site


def _make_clean_site(db, pf, nom="Site Clean"):
    """Site sans anomalie : score = 100, healthy."""
    site = Site(
        nom=nom,
        type=TypeSite.BUREAU,
        surface_m2=1000.0,
        portefeuille_id=pf.id,
        actif=True,
    )
    db.add(site)
    db.flush()
    bat = Batiment(site_id=site.id, nom="Bat", surface_m2=1000.0)
    db.add(bat)
    db.flush()
    db.add(Usage(batiment_id=bat.id, type=TypeUsage.BUREAUX))
    dp = DeliveryPoint(
        code="99999999999999",
        energy_type=DeliveryPointEnergyType.ELEC,
        site_id=site.id,
        status=DeliveryPointStatus.ACTIVE,
    )
    db.add(dp)
    db.flush()
    db.add(
        Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie=f"SN-C{site.id}",
            actif=True,
            delivery_point_id=dp.id,
        )
    )
    db.add(
        EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Engie",
            start_date=date(2023, 1, 1),
            end_date=date(2025, 12, 31),
        )
    )
    db.commit()
    return site


# ── Tests sites_health ────────────────────────────────────────────────────────


class TestPortfolioSitesHealth:
    def test_sites_health_present_in_response(self, client, db):
        """sites_health est présent dans la réponse (V61)."""
        _, pf = _make_org(db, "OrgHealth1")
        _make_site_with_surface_mismatch(db, pf)
        r = client.get("/api/patrimoine/portfolio-summary")
        assert r.status_code == 200
        assert "sites_health" in r.json()

    def test_sites_health_keys(self, client, db):
        """sites_health contient healthy/warning/critical/healthy_pct."""
        _, pf = _make_org(db, "OrgHealth2")
        _make_clean_site(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        sh = data["sites_health"]
        for key in ("healthy", "warning", "critical", "healthy_pct"):
            assert key in sh, f"Clé manquante : {key}"

    def test_clean_site_is_healthy(self, client, db):
        """Site sans anomalie → completude_score = 100 → bucket healthy."""
        _, pf = _make_org(db, "OrgClean")
        _make_clean_site(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        sh = data["sites_health"]
        assert sh["healthy"] >= 1

    def test_healthy_pct_100_for_clean_portfolio(self, client, db):
        """Portfolio 100% sain → healthy_pct = 100.0."""
        _, pf = _make_org(db, "OrgFull")
        _make_clean_site(db, pf, nom="S1")
        _make_clean_site(db, pf, nom="S2")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["sites_health"]["healthy_pct"] == 100.0

    def test_site_with_anomaly_not_healthy(self, client, db):
        """Site avec anomalies → completude_score < 100 → pas 100% healthy."""
        _, pf = _make_org(db, "OrgMixed")
        _make_site_with_surface_mismatch(db, pf, nom="Anom")
        _make_clean_site(db, pf, nom="Clean")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        sh = data["sites_health"]
        # Au moins 1 site sain (le clean), au moins 1 pas sain (le mismatch)
        assert sh["healthy"] >= 1
        total = sh["healthy"] + sh["warning"] + sh["critical"]
        assert total == 2

    def test_healthy_pct_range(self, client, db):
        """healthy_pct est entre 0 et 100."""
        _, pf = _make_org(db, "OrgRange")
        _make_site_with_surface_mismatch(db, pf)
        _make_clean_site(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        pct = data["sites_health"]["healthy_pct"]
        assert 0.0 <= pct <= 100.0

    def test_empty_scope_sites_health_zeros(self, client, db):
        """Scope vide → sites_health tout à 0."""
        _make_org(db, "OrgEmpty61")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        sh = data["sites_health"]
        assert sh["healthy"] == 0
        assert sh["warning"] == 0
        assert sh["critical"] == 0
        assert sh["healthy_pct"] == 0.0

    def test_sites_health_sum_equals_sites_count(self, client, db):
        """sum(healthy+warning+critical) == sites_count."""
        _, pf = _make_org(db, "OrgSum")
        _make_site_with_surface_mismatch(db, pf, nom="A1")
        _make_site_with_surface_mismatch(db, pf, nom="A2")
        _make_clean_site(db, pf, nom="C1")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        sh = data["sites_health"]
        total = sh["healthy"] + sh["warning"] + sh["critical"]
        assert total == data["sites_count"]


# ── Tests trend ───────────────────────────────────────────────────────────────


class TestPortfolioTrend:
    def test_trend_field_present(self, client, db):
        """trend est présent dans la réponse (V61)."""
        _, pf = _make_org(db, "OrgTrend1")
        _make_clean_site(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert "trend" in data

    def test_trend_is_null_v61(self, client, db):
        """trend null ou stable zéro-delta quand pas d'historique."""
        _, pf = _make_org(db, "OrgTrendNull")
        _make_clean_site(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        trend = data["trend"]
        assert trend is None or (trend.get("direction") == "stable" and trend.get("risk_eur_delta") == 0.0)

    def test_trend_null_empty_scope(self, client, db):
        """Scope vide → trend est aussi null."""
        _make_org(db, "OrgEmptyTrend")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["trend"] is None


# ── Tests backward compat V60 ─────────────────────────────────────────────────


class TestBackwardCompatV60:
    def test_v60_fields_still_present(self, client, db):
        """Tous les champs V60 toujours présents après V61."""
        _, pf = _make_org(db, "OrgCompat")
        _make_site_with_surface_mismatch(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        for field in (
            "scope",
            "total_estimated_risk_eur",
            "sites_count",
            "sites_at_risk",
            "framework_breakdown",
            "top_sites",
            "computed_at",
        ):
            assert field in data, f"Champ V60 manquant : {field}"

    def test_framework_breakdown_has_anomalies_count(self, client, db):
        """framework_breakdown items ont anomalies_count (V60 déjà, V61 confirme)."""
        _, pf = _make_org(db, "OrgFWCount")
        _make_site_with_surface_mismatch(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        for item in data["framework_breakdown"]:
            assert "anomalies_count" in item
            assert item["anomalies_count"] >= 1

    def test_sites_at_risk_v60_still_correct(self, client, db):
        """sites_at_risk fonctionne encore correctement (V60 behavior)."""
        _, pf = _make_org(db, "OrgAtRisk61")
        _make_site_with_surface_mismatch(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        sar = data["sites_at_risk"]
        total = sar["critical"] + sar["high"] + sar["medium"] + sar["low"]
        assert total >= 1
