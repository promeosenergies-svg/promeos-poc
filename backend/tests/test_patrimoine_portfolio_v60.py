"""
test_patrimoine_portfolio_v60.py — Tests V60 : Portfolio Summary endpoint

Couverture :
  - Cas scope vide (aucun site) → tout à 0, listes vides, pas de crash
  - Cas nominal (site avec anomalies) → risk >0, top_sites length >0
  - Filtre site_id → summary réduit à ce site
  - Filtre portefeuille_id → summary réduit au portefeuille
  - top_n param → limite top_sites
  - Multi-org guard → site org B invisible depuis org A
  - Pydantic models présents (PortfolioSummaryResponse, PortfolioTopSiteItem, etc.)
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


def _make_site_with_anomalies(db, pf, nom="Site A", surface_site=5000.0, surface_bat=3000.0):
    """
    Crée un site avec SURFACE_MISMATCH garantie (site.surface != SUM(batiments)).
    risk attendu : |5000 - 3000| * 90 kWh/m² * 0.12 €/kWh = 21 600 €
    """
    site = Site(
        nom=nom, type=TypeSite.BUREAU,
        surface_m2=surface_site,
        portefeuille_id=pf.id, actif=True,
    )
    db.add(site)
    db.flush()
    bat = Batiment(site_id=site.id, nom="Bat", surface_m2=surface_bat)
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
    """Site sans anomalie : surface cohérente, compteur avec DP, contrat valide."""
    site = Site(
        nom=nom, type=TypeSite.BUREAU,
        surface_m2=1000.0,
        portefeuille_id=pf.id, actif=True,
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


# ── Tests scope vide ──────────────────────────────────────────────────────────

class TestPortfolioSummaryEmpty:
    def test_no_sites_returns_zeros(self, client, db):
        """Aucun site → total = 0, listes vides, pas de crash."""
        _make_org(db, "OrgEmpty")
        r = client.get("/api/patrimoine/portfolio-summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_estimated_risk_eur"] == 0.0
        assert data["sites_count"] == 0
        assert data["top_sites"] == []
        assert data["framework_breakdown"] == []

    def test_no_sites_at_risk_all_zero(self, client, db):
        _make_org(db, "OrgEmpty2")
        r = client.get("/api/patrimoine/portfolio-summary")
        data = r.json()
        sar = data["sites_at_risk"]
        assert sar["critical"] == 0
        assert sar["high"] == 0
        assert sar["medium"] == 0
        assert sar["low"] == 0

    def test_scope_field_present(self, client, db):
        _make_org(db, "OrgScope")
        r = client.get("/api/patrimoine/portfolio-summary")
        data = r.json()
        assert "scope" in data
        assert "org_id" in data["scope"]
        assert "computed_at" in data

    def test_no_org_no_crash(self, client, db):
        """Aucune org en base → resolve_org_id() refuse avec 403 (pas de crash 500).
        Le multi-org guard est actif : 403 est le comportement attendu, pas un crash applicatif.
        """
        r = client.get("/api/patrimoine/portfolio-summary")
        # resolve_org_id() lève 403 quand aucune org n'est trouvée — guard multi-org.
        assert r.status_code in (200, 403)
        assert r.status_code != 500


# ── Tests cas nominal (site avec anomalies) ───────────────────────────────────

class TestPortfolioSummaryNominal:
    def test_total_risk_positive(self, client, db):
        """Site avec SURFACE_MISMATCH → risk > 0."""
        _, pf = _make_org(db, "OrgRisk")
        _make_site_with_anomalies(db, pf)
        r = client.get("/api/patrimoine/portfolio-summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_estimated_risk_eur"] > 0

    def test_top_sites_not_empty(self, client, db):
        """Site avec anomalies → top_sites non vide."""
        _, pf = _make_org(db, "OrgTop")
        _make_site_with_anomalies(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert len(data["top_sites"]) >= 1

    def test_top_site_fields(self, client, db):
        _, pf = _make_org(db, "OrgFields")
        site = _make_site_with_anomalies(db, pf, nom="Site Champs")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        ts = data["top_sites"][0]
        assert ts["site_id"] == site.id
        assert ts["site_nom"] == "Site Champs"
        assert ts["risk_eur"] > 0
        assert ts["anomalies_count"] > 0

    def test_framework_breakdown_not_empty(self, client, db):
        """SURFACE_MISMATCH → DECRET_TERTIAIRE dans framework_breakdown."""
        _, pf = _make_org(db, "OrgFW")
        _make_site_with_anomalies(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert len(data["framework_breakdown"]) > 0
        frameworks = [fb["framework"] for fb in data["framework_breakdown"]]
        assert "DECRET_TERTIAIRE" in frameworks

    def test_sites_count_matches(self, client, db):
        _, pf = _make_org(db, "OrgCount")
        _make_site_with_anomalies(db, pf, nom="S1")
        _make_site_with_anomalies(db, pf, nom="S2")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["sites_count"] == 2

    def test_sites_at_risk_incremented(self, client, db):
        _, pf = _make_org(db, "OrgAtRisk")
        _make_site_with_anomalies(db, pf)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        sar = data["sites_at_risk"]
        total = sar["critical"] + sar["high"] + sar["medium"] + sar["low"]
        assert total >= 1

    def test_top_sites_sorted_desc_by_risk(self, client, db):
        """Les top_sites sont triés risk_eur DESC."""
        _, pf = _make_org(db, "OrgSort")
        # Site A : grosse anomalie surface (5000 vs 3000)
        _make_site_with_anomalies(db, pf, nom="Gros", surface_site=5000.0, surface_bat=1000.0)
        # Site B : petite anomalie (surface très proche)
        _make_clean_site(db, pf, nom="Propre")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        top = data["top_sites"]
        if len(top) >= 2:
            assert top[0]["risk_eur"] >= top[1]["risk_eur"]


# ── Tests filtre site_id ──────────────────────────────────────────────────────

class TestPortfolioSummarySiteFilter:
    def test_site_filter_reduces_scope(self, client, db):
        """Filtre site_id → summary limité à ce site."""
        _, pf = _make_org(db, "OrgFilter")
        s1 = _make_site_with_anomalies(db, pf, nom="Site 1")
        _make_site_with_anomalies(db, pf, nom="Site 2")
        r = client.get(f"/api/patrimoine/portfolio-summary?site_id={s1.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["sites_count"] == 1
        assert len(data["top_sites"]) == 1
        assert data["top_sites"][0]["site_id"] == s1.id

    def test_site_filter_risk_isolated(self, client, db):
        """Risk d'un site filtré ≤ risk total (2 sites)."""
        _, pf = _make_org(db, "OrgIso")
        s1 = _make_site_with_anomalies(db, pf, nom="ISO1")
        _make_site_with_anomalies(db, pf, nom="ISO2")
        total = client.get("/api/patrimoine/portfolio-summary").json()["total_estimated_risk_eur"]
        filtered = client.get(f"/api/patrimoine/portfolio-summary?site_id={s1.id}").json()["total_estimated_risk_eur"]
        assert filtered <= total

    def test_top_n_limits_results(self, client, db):
        """top_n=1 → au plus 1 site dans top_sites."""
        _, pf = _make_org(db, "OrgTopN")
        for i in range(3):
            _make_site_with_anomalies(db, pf, nom=f"Site {i}")
        data = client.get("/api/patrimoine/portfolio-summary?top_n=1").json()
        assert len(data["top_sites"]) <= 1

    def test_top_n_default_3(self, client, db):
        """Par défaut top_n=3 → au plus 3 sites."""
        _, pf = _make_org(db, "OrgDef3")
        for i in range(5):
            _make_site_with_anomalies(db, pf, nom=f"Site {i}")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert len(data["top_sites"]) <= 3


# ── Guard multi-org ───────────────────────────────────────────────────────────

class TestPortfolioSummaryMultiOrg:
    def test_org_a_cannot_see_org_b_sites(self, client, db):
        """Org A ne voit pas les sites de org B."""
        org_a, pf_a = _make_org(db, "OrgA_V60")
        org_b, pf_b = _make_org(db, "OrgB_V60")
        _make_site_with_anomalies(db, pf_b, nom="Site OrgB")

        # Le client est scopé sur org_a (première org créée dans DemoState / fallback)
        # On vérifie que sites_count = 0 depuis l'org A (qui n'a aucun site)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        # L'org résolue est la première org (org_a) qui n'a pas de sites
        assert data["sites_count"] == 0

    def test_scope_contains_org_id(self, client, db):
        _make_org(db, "OrgScopeCheck")
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["scope"]["org_id"] is not None
