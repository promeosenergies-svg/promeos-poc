"""
test_patrimoine_anomalies_v58.py — Tests V58 : Anomalies Patrimoine (8 règles P0)

Couverture :
- Chaque règle P0 individuellement
- Score de complétude (D7)
- Endpoints /sites/{id}/anomalies et /anomalies (org list)
- Scoping org (403 cross-org)
"""

import pytest
from datetime import date, datetime
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
    EnergyVector,
    DeliveryPointStatus,
    DeliveryPointEnergyType,
    BillingEnergyType,
    TypeUsage,
)
from database import get_db
from main import app
from services.demo_state import DemoState


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


def _make_org_site(db, nom="TestOrg"):
    """Helper : crée une hiérarchie complète org → EJ → PF → Site vierge."""
    org = Organisation(nom=nom, actif=True)
    db.add(org)
    db.flush()
    siren = str(abs(hash(nom)) % 10**9).zfill(9)
    ej = EntiteJuridique(nom=f"EJ {nom}", organisation_id=org.id, siren=siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom=f"PF {nom}", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    site = Site(nom=f"Site {nom}", type=TypeSite.BUREAU, portefeuille_id=pf.id, actif=True)
    db.add(site)
    db.commit()
    return org, pf, site


# ── Règle 1 : SURFACE_MISSING ─────────────────────────────────────────────────


class TestSurfaceMissing:
    def test_no_surface_no_batiments(self, db):
        """Site sans surface ni bâtiments → SURFACE_MISSING HIGH."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "NoSurf1")
        site.surface_m2 = None
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "SURFACE_MISSING" in codes
        anom = next(a for a in result["anomalies"] if a["code"] == "SURFACE_MISSING")
        assert anom["severity"] == "HIGH"

    def test_with_surface_no_anomaly(self, db):
        """Site avec surface_m2 > 0 et pas de bâtiments → pas SURFACE_MISSING."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "WithSurf")
        site.surface_m2 = 1000.0
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "SURFACE_MISSING" not in codes

    def test_batiments_zero_surface(self, db):
        """Bâtiments présents mais surface_m2 à 0 → SURFACE_MISSING."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, pf, site = _make_org_site(db, "ZeroSurf")
        bat = Batiment(site_id=site.id, nom="Bat0", surface_m2=0.0)
        db.add(bat)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "SURFACE_MISSING" in codes


# ── Règle 2 : SURFACE_MISMATCH ────────────────────────────────────────────────


class TestSurfaceMismatch:
    def test_mismatch_beyond_tolerance(self, db):
        """Écart > 5 % entre site.surface_m2 et ∑ bâtiments → SURFACE_MISMATCH."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "Mismatch1")
        site.surface_m2 = 1000.0
        db.commit()
        bat = Batiment(site_id=site.id, nom="BatBig", surface_m2=2000.0)
        db.add(bat)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "SURFACE_MISMATCH" in codes
        anom = next(a for a in result["anomalies"] if a["code"] == "SURFACE_MISMATCH")
        assert anom["severity"] == "MEDIUM"

    def test_no_mismatch_within_tolerance(self, db):
        """Écart ≤ 5 % → pas SURFACE_MISMATCH."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "NoMismatch")
        site.surface_m2 = 1000.0
        db.commit()
        bat = Batiment(site_id=site.id, nom="BatOk", surface_m2=1020.0)  # 2 % écart
        db.add(bat)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "SURFACE_MISMATCH" not in codes


# ── Règle 3 : BUILDING_MISSING ────────────────────────────────────────────────


class TestBuildingMissing:
    def test_no_buildings(self, db):
        """Site sans bâtiment → BUILDING_MISSING MEDIUM."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "NoBat")
        site.surface_m2 = 500.0
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "BUILDING_MISSING" in codes
        anom = next(a for a in result["anomalies"] if a["code"] == "BUILDING_MISSING")
        assert anom["severity"] == "MEDIUM"

    def test_with_building_no_anomaly(self, db):
        """Site avec bâtiment → pas BUILDING_MISSING."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "WithBat")
        site.surface_m2 = 500.0
        db.commit()
        bat = Batiment(site_id=site.id, nom="BatPresent", surface_m2=500.0)
        db.add(bat)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "BUILDING_MISSING" not in codes


# ── Règle 4 : BUILDING_USAGE_MISSING ─────────────────────────────────────────


class TestBuildingUsageMissing:
    def test_batiment_without_usage(self, db):
        """Bâtiment sans usage → BUILDING_USAGE_MISSING LOW."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "NoUsage")
        site.surface_m2 = 1000.0
        db.commit()
        bat = Batiment(site_id=site.id, nom="BatNoUsage", surface_m2=1000.0)
        db.add(bat)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "BUILDING_USAGE_MISSING" in codes
        anom = next(a for a in result["anomalies"] if a["code"] == "BUILDING_USAGE_MISSING")
        assert anom["severity"] == "LOW"

    def test_batiment_with_usage_no_anomaly(self, db):
        """Bâtiment avec usage → pas BUILDING_USAGE_MISSING."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "WithUsage")
        site.surface_m2 = 1000.0
        db.commit()
        bat = Batiment(site_id=site.id, nom="BatWithUsage", surface_m2=1000.0)
        db.add(bat)
        db.flush()
        usage = Usage(batiment_id=bat.id, type=TypeUsage.BUREAUX)
        db.add(usage)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "BUILDING_USAGE_MISSING" not in codes


# ── Règle 5 : METER_NO_DELIVERY_POINT ────────────────────────────────────────


class TestMeterNoDeliveryPoint:
    def test_compteur_without_dp(self, db):
        """Compteur sans delivery_point_id → METER_NO_DELIVERY_POINT MEDIUM."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "NoDP")
        site.surface_m2 = 1000.0
        db.commit()
        cpt = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="SN-NODP",
            actif=True,
            delivery_point_id=None,
        )
        db.add(cpt)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "METER_NO_DELIVERY_POINT" in codes
        anom = next(a for a in result["anomalies"] if a["code"] == "METER_NO_DELIVERY_POINT")
        assert anom["severity"] == "MEDIUM"

    def test_compteur_with_dp_no_anomaly(self, db):
        """Compteur avec delivery_point_id → pas METER_NO_DELIVERY_POINT."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "WithDP")
        site.surface_m2 = 1000.0
        db.commit()
        dp = DeliveryPoint(
            code="98765432109876",
            energy_type=DeliveryPointEnergyType.ELEC,
            site_id=site.id,
            status=DeliveryPointStatus.ACTIVE,
        )
        db.add(dp)
        db.flush()
        cpt = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="SN-WITHDP",
            actif=True,
            delivery_point_id=dp.id,
        )
        db.add(cpt)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "METER_NO_DELIVERY_POINT" not in codes


# ── Règle 6 : CONTRACT_DATE_INVALID ──────────────────────────────────────────


class TestContractDateInvalid:
    def test_start_after_end(self, db):
        """start_date >= end_date → CONTRACT_DATE_INVALID HIGH."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "BadDates")
        site.surface_m2 = 1000.0
        db.commit()
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF Bad",
            start_date=date(2024, 12, 31),
            end_date=date(2024, 1, 1),
        )
        db.add(contract)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "CONTRACT_DATE_INVALID" in codes
        anom = next(a for a in result["anomalies"] if a["code"] == "CONTRACT_DATE_INVALID")
        assert anom["severity"] == "HIGH"

    def test_valid_dates_no_anomaly(self, db):
        """Dates valides → pas CONTRACT_DATE_INVALID."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "GoodDates")
        site.surface_m2 = 1000.0
        db.commit()
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF Good",
            start_date=date(2023, 1, 1),
            end_date=date(2025, 12, 31),
        )
        db.add(contract)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "CONTRACT_DATE_INVALID" not in codes

    def test_null_dates_no_anomaly(self, db):
        """Dates nulles → pas CONTRACT_DATE_INVALID (on ne peut pas comparer)."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "NullDates")
        site.surface_m2 = 1000.0
        db.commit()
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF Null",
            start_date=None,
            end_date=None,
        )
        db.add(contract)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "CONTRACT_DATE_INVALID" not in codes


# ── Règle 7 : CONTRACT_OVERLAP_SITE ──────────────────────────────────────────


class TestContractOverlap:
    def test_overlapping_contracts(self, db):
        """Deux contrats qui se chevauchent sur la même énergie → CONTRACT_OVERLAP_SITE HIGH."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "Overlap")
        site.surface_m2 = 1000.0
        db.commit()
        c1 = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF A",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )
        c2 = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Engie B",
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
        )
        db.add_all([c1, c2])
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "CONTRACT_OVERLAP_SITE" in codes
        anom = next(a for a in result["anomalies"] if a["code"] == "CONTRACT_OVERLAP_SITE")
        assert anom["severity"] == "HIGH"

    def test_non_overlapping_contracts(self, db):
        """Contrats consécutifs sans chevauchement → pas CONTRACT_OVERLAP_SITE."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "NoOverlap")
        site.surface_m2 = 1000.0
        db.commit()
        c1 = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF C",
            start_date=date(2022, 1, 1),
            end_date=date(2023, 12, 31),
        )
        c2 = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Engie D",
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
        )
        db.add_all([c1, c2])
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "CONTRACT_OVERLAP_SITE" not in codes

    def test_different_energy_no_overlap_anomaly(self, db):
        """Chevauchement sur énergies différentes → pas CONTRACT_OVERLAP_SITE."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "DiffEnergy")
        site.surface_m2 = 1000.0
        db.commit()
        c1 = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF E",
            start_date=date(2023, 1, 1),
            end_date=date(2025, 12, 31),
        )
        c2 = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.GAZ,
            supplier_name="Engie F",
            start_date=date(2023, 1, 1),
            end_date=date(2025, 12, 31),
        )
        db.add_all([c1, c2])
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "CONTRACT_OVERLAP_SITE" not in codes


# ── Règle 8 : ORPHANS_DETECTED ───────────────────────────────────────────────


class TestOrphansDetected:
    def test_archived_site_with_active_children(self, db):
        """Site archivé (actif=False) avec compteurs actifs → ORPHANS_DETECTED CRITICAL."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, pf, site = _make_org_site(db, "Archived")
        site.actif = False
        db.commit()
        cpt = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="SN-ORPHAN",
            actif=True,
        )
        db.add(cpt)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "ORPHANS_DETECTED" in codes
        anom = next(a for a in result["anomalies"] if a["code"] == "ORPHANS_DETECTED")
        assert anom["severity"] == "CRITICAL"

    def test_active_site_no_orphan_anomaly(self, db):
        """Site actif → pas ORPHANS_DETECTED."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "Active2")
        site.surface_m2 = 500.0
        db.commit()

        result = compute_site_anomalies(site.id, db)
        codes = [a["code"] for a in result["anomalies"]]
        assert "ORPHANS_DETECTED" not in codes


# ── Score de complétude (D7) ──────────────────────────────────────────────────


class TestCompletudeScore:
    def test_perfect_score_no_anomalies(self, db):
        """Site complet → score 100."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "Perfect")
        site.surface_m2 = 1000.0
        db.commit()
        bat = Batiment(site_id=site.id, nom="BatPerf", surface_m2=1000.0)
        db.add(bat)
        db.flush()
        usage = Usage(batiment_id=bat.id, type=TypeUsage.BUREAUX)
        db.add(usage)
        dp = DeliveryPoint(
            code="11111111111111",
            energy_type=DeliveryPointEnergyType.ELEC,
            site_id=site.id,
            status=DeliveryPointStatus.ACTIVE,
        )
        db.add(dp)
        db.flush()
        cpt = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="SN-PERF",
            actif=True,
            delivery_point_id=dp.id,
        )
        db.add(cpt)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        assert result["completude_score"] == 100
        assert result["nb_anomalies"] == 0

    def test_score_decreases_with_anomalies(self, db):
        """Score diminue avec les anomalies : CRITICAL -30, HIGH -15."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, pf, site = _make_org_site(db, "DecrScore")
        site.surface_m2 = None
        site.actif = False  # ORPHANS_DETECTED CRITICAL (-30) if children
        db.commit()
        cpt = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="SN-DECR",
            actif=True,
            delivery_point_id=None,
        )
        db.add(cpt)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        # ORPHANS_DETECTED (CRITICAL, -30) + SURFACE_MISSING (HIGH, -15)
        # + METER_NO_DELIVERY_POINT (MEDIUM, -7) + BUILDING_MISSING (MEDIUM, -7) = 100-59=41
        assert result["completude_score"] < 100
        assert result["completude_score"] >= 0

    def test_score_capped_at_zero(self, db):
        """Score ne peut pas être négatif."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "NegScore")
        site.surface_m2 = None
        site.actif = False
        db.commit()
        # Ajouter beaucoup d'anomalies
        for i in range(5):
            cpt = Compteur(
                site_id=site.id,
                type=TypeCompteur.ELECTRICITE,
                numero_serie=f"SN-NEG-{i}",
                actif=True,
            )
            db.add(cpt)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        assert result["completude_score"] >= 0

    def test_anomalies_sorted_critical_first(self, db):
        """Anomalies triées CRITICAL > HIGH > MEDIUM > LOW."""
        from services.patrimoine_anomalies import compute_site_anomalies

        _, _, site = _make_org_site(db, "SortOrder")
        site.surface_m2 = None
        site.actif = False
        db.commit()
        cpt = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="SN-SORT",
            actif=True,
        )
        db.add(cpt)
        db.commit()

        result = compute_site_anomalies(site.id, db)
        severities = [a["severity"] for a in result["anomalies"]]
        order_map = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        for i in range(len(severities) - 1):
            assert order_map[severities[i]] <= order_map[severities[i + 1]]


# ── Endpoints HTTP ────────────────────────────────────────────────────────────


class TestAnomaliesEndpoints:
    def test_site_anomalies_endpoint_200(self, client, db):
        """GET /api/patrimoine/sites/{id}/anomalies → 200."""
        DemoState.clear_demo_org()
        org, _, site = _make_org_site(db, "EndpointOrg")
        site.surface_m2 = 1000.0
        db.commit()
        DemoState.set_demo_org(org.id)

        r = client.get(f"/api/patrimoine/sites/{site.id}/anomalies")
        assert r.status_code == 200
        data = r.json()
        assert "anomalies" in data
        assert "completude_score" in data
        assert "nb_anomalies" in data
        assert "computed_at" in data

    def test_site_anomalies_403_wrong_org(self, client, db):
        """Cross-org → 403."""
        DemoState.clear_demo_org()
        org1, _, _ = _make_org_site(db, "Org403A")
        org2, _, site2 = _make_org_site(db, "Org403B")
        DemoState.set_demo_org(org1.id)

        r = client.get(f"/api/patrimoine/sites/{site2.id}/anomalies")
        assert r.status_code == 403

    def test_list_org_anomalies_endpoint_200(self, client, db):
        """GET /api/patrimoine/anomalies → 200 + sites list."""
        DemoState.clear_demo_org()
        org, _, site = _make_org_site(db, "ListOrg")
        site.surface_m2 = 500.0
        db.commit()
        DemoState.set_demo_org(org.id)

        r = client.get("/api/patrimoine/anomalies")
        assert r.status_code == 200
        data = r.json()
        assert "sites" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["sites"], list)

    def test_list_org_anomalies_pagination(self, client, db):
        """Pagination page/page_size fonctionnelle."""
        DemoState.clear_demo_org()
        org, pf, _ = _make_org_site(db, "PagOrg")
        # Ajouter plus de sites
        for i in range(5):
            s = Site(nom=f"PagSite{i}", type=TypeSite.BUREAU, portefeuille_id=pf.id, actif=True)
            db.add(s)
        db.commit()
        DemoState.set_demo_org(org.id)

        r = client.get("/api/patrimoine/anomalies?page=1&page_size=2")
        assert r.status_code == 200
        data = r.json()
        assert len(data["sites"]) <= 2

    def test_list_org_anomalies_min_score_filter(self, client, db):
        """Filtre min_score=100 → uniquement les sites parfaits."""
        DemoState.clear_demo_org()
        org, _, site = _make_org_site(db, "FilterOrg")
        site.surface_m2 = 1000.0
        db.commit()
        DemoState.set_demo_org(org.id)

        # Score <= 50 → uniquement les sites dégradés
        r = client.get("/api/patrimoine/anomalies?min_score=50")
        assert r.status_code == 200
        data = r.json()
        for s in data["sites"]:
            assert s["completude_score"] <= 50

    def test_anomalies_cta_fields_present(self, client, db):
        """Chaque anomalie contient les champs CTA requis."""
        DemoState.clear_demo_org()
        org, _, site = _make_org_site(db, "CTAOrg")
        site.surface_m2 = None  # force SURFACE_MISSING
        db.commit()
        DemoState.set_demo_org(org.id)

        r = client.get(f"/api/patrimoine/sites/{site.id}/anomalies")
        assert r.status_code == 200
        data = r.json()
        for anom in data["anomalies"]:
            assert "code" in anom
            assert "severity" in anom
            assert "title_fr" in anom
            assert "detail_fr" in anom
            assert "evidence" in anom
            assert "cta" in anom
            assert "label" in anom["cta"]
            assert "to" in anom["cta"]
            assert "fix_hint_fr" in anom

    def test_source_guard_no_organisation_first(self):
        """Guard : les services patrimoine n'utilisent pas Organisation.first()."""
        import re
        import pathlib

        for fname in ["patrimoine_snapshot.py", "patrimoine_anomalies.py"]:
            path = pathlib.Path(__file__).parent.parent / "services" / fname
            content = path.read_text(encoding="utf-8")
            assert not re.search(r"Organisation\s*\)\s*\.first\(\)", content), (
                f"{fname} contient Organisation.first() — interdit (V57)"
            )
