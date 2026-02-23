"""
test_patrimoine_snapshot_v58.py -- Tests V58 : Snapshot canonique Patrimoine

Couverture : surface SoT D1, soft-delete filtering, scoping org, endpoints HTTP.
"""
import pytest
from datetime import date, datetime
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
from services.demo_state import DemoState


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


def _make_org(db, nom, siren=None):
    org = Organisation(nom=nom, actif=True)
    db.add(org)
    db.flush()
    s = siren or str(abs(hash(nom)) % 10**9).zfill(9)
    ej = EntiteJuridique(nom="EJ " + nom, organisation_id=org.id, siren=s)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom="PF " + nom, entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    return org, pf


def _make_full_site(db, pf, nom="Site", surface=5000.0):
    site = Site(nom=nom, type=TypeSite.BUREAU, surface_m2=surface,
                portefeuille_id=pf.id, actif=True)
    db.add(site)
    db.flush()
    bat_a = Batiment(site_id=site.id, nom="Bat A", surface_m2=3000.0)
    bat_b = Batiment(site_id=site.id, nom="Bat B", surface_m2=2000.0)
    db.add_all([bat_a, bat_b])
    db.flush()
    db.add(Usage(batiment_id=bat_a.id, type=TypeUsage.BUREAUX))
    dp = DeliveryPoint(code="12345678901234", energy_type=DeliveryPointEnergyType.ELEC,
                       site_id=site.id, status=DeliveryPointStatus.ACTIVE)
    db.add(dp)
    db.flush()
    db.add(Compteur(site_id=site.id, type=TypeCompteur.ELECTRICITE,
                    numero_serie="SN-001", actif=True, delivery_point_id=dp.id))
    db.add(EnergyContract(site_id=site.id, energy_type=BillingEnergyType.ELEC,
                          supplier_name="EDF", start_date=date(2023, 1, 1),
                          end_date=date(2025, 12, 31)))
    db.commit()
    return site, bat_a, bat_b, dp


class TestSnapshotService:
    def test_surface_sot_uses_batiments_sum(self, db):
        """D1: surface SoT = somme batiments quand batiments presents."""
        from services.patrimoine_snapshot import get_site_snapshot
        org, pf = _make_org(db, "OrgSoT")
        site, _, _, _ = _make_full_site(db, pf, surface=5000.0)
        snap = get_site_snapshot(site.id, org.id, db)
        assert snap is not None
        assert snap["surface_sot_m2"] == 5000.0  # Bat A(3000) + Bat B(2000)
        assert snap["surface_site_m2"] == 5000.0

    def test_surface_sot_fallback_no_batiments(self, db):
        """D1 fallback: pas de batiments -> SoT = site.surface_m2."""
        from services.patrimoine_snapshot import get_site_snapshot
        org, pf = _make_org(db, "OrgFallback")
        site = Site(nom="NoBat", type=TypeSite.BUREAU, surface_m2=999.0,
                    portefeuille_id=pf.id, actif=True)
        db.add(site)
        db.commit()
        snap = get_site_snapshot(site.id, org.id, db)
        assert snap["surface_sot_m2"] == 999.0
        assert snap["nb_batiments"] == 0

    def test_soft_deleted_batiment_excluded(self, db):
        """Batiment soft-deleted (deleted_at != None) exclu du snapshot."""
        from services.patrimoine_snapshot import get_site_snapshot
        org, pf = _make_org(db, "OrgDelBat")
        site, _, _, _ = _make_full_site(db, pf, surface=5000.0)
        bat_del = Batiment(site_id=site.id, nom="Bat Del", surface_m2=9999.0)
        bat_del.deleted_at = datetime.utcnow()
        db.add(bat_del)
        db.commit()
        snap = get_site_snapshot(site.id, org.id, db)
        assert "Bat Del" not in [b["nom"] for b in snap["batiments"]]
        assert snap["surface_sot_m2"] == 5000.0

    def test_inactive_compteur_excluded(self, db):
        """Compteur actif=False exclu du snapshot."""
        from services.patrimoine_snapshot import get_site_snapshot
        org, pf = _make_org(db, "OrgInactCpt")
        site, _, _, _ = _make_full_site(db, pf)
        db.add(Compteur(site_id=site.id, type=TypeCompteur.ELECTRICITE,
                        numero_serie="SN-INACTIF", actif=False))
        db.commit()
        snap = get_site_snapshot(site.id, org.id, db)
        assert "SN-INACTIF" not in [c["numero_serie"] for c in snap["compteurs"]]

    def test_snapshot_has_all_collections(self, db):
        """Snapshot expose batiments, compteurs, delivery_points, contracts."""
        from services.patrimoine_snapshot import get_site_snapshot
        org, pf = _make_org(db, "OrgAllColl")
        site, _, _, _ = _make_full_site(db, pf)
        snap = get_site_snapshot(site.id, org.id, db)
        for key in ("batiments", "compteurs", "delivery_points", "contracts"):
            assert key in snap
        assert snap["nb_batiments"] >= 2
        assert snap["nb_compteurs"] >= 1
        assert snap["nb_delivery_points"] >= 1
        assert snap["nb_contracts"] >= 1

    def test_snapshot_none_for_missing_site(self, db):
        """get_site_snapshot retourne None si le site n existe pas."""
        from services.patrimoine_snapshot import get_site_snapshot
        assert get_site_snapshot(99999, 1, db) is None

    def test_usages_included_in_batiment(self, db):
        """Les usages sont inclus dans les batiments du snapshot."""
        from services.patrimoine_snapshot import get_site_snapshot
        org, pf = _make_org(db, "OrgUsages")
        site, bat_a, _, _ = _make_full_site(db, pf)
        snap = get_site_snapshot(site.id, org.id, db)
        bat_data = next(b for b in snap["batiments"] if b["nom"] == "Bat A")
        assert len(bat_data["usages"]) >= 1

    def test_surface_sot_none_no_surface(self, db):
        """Ni site.surface_m2 ni batiments -> surface_sot_m2 = None."""
        from services.patrimoine_snapshot import get_site_snapshot
        org, pf = _make_org(db, "OrgNoSurf")
        site = Site(nom="NoSurf", type=TypeSite.BUREAU, surface_m2=None,
                    portefeuille_id=pf.id, actif=True)
        db.add(site)
        db.commit()
        snap = get_site_snapshot(site.id, org.id, db)
        assert snap["surface_sot_m2"] is None


class TestSnapshotEndpoint:
    def test_snapshot_happy_path(self, client, db):
        """GET /api/patrimoine/sites/{id}/snapshot -> 200."""
        DemoState.clear_demo_org()
        org, pf = _make_org(db, "OrgEndpt")
        site, _, _, _ = _make_full_site(db, pf)
        DemoState.set_demo_org(org.id)
        r = client.get(f"/api/patrimoine/sites/{site.id}/snapshot")
        assert r.status_code == 200
        data = r.json()
        assert data["site_id"] == site.id
        assert "surface_sot_m2" in data
        assert "batiments" in data
        assert "completude_score" not in data  # snapshot != anomalies
        assert data["nb_batiments"] >= 2

    def test_snapshot_no_org_returns_error(self, client):
        """Sans org -> 401/403/404."""
        DemoState.clear_demo_org()
        r = client.get("/api/patrimoine/sites/99999/snapshot")
        assert r.status_code in (401, 403, 404)

    def test_snapshot_computed_at_present(self, client, db):
        """Le champ computed_at est present."""
        DemoState.clear_demo_org()
        org, pf = _make_org(db, "OrgCmpAt")
        site, _, _, _ = _make_full_site(db, pf)
        DemoState.set_demo_org(org.id)
        r = client.get(f"/api/patrimoine/sites/{site.id}/snapshot")
        assert r.status_code == 200
        assert r.json()["computed_at"]

    def test_snapshot_org_scoping_403(self, client, db):
        """Site d une autre org -> 403."""
        DemoState.clear_demo_org()
        org1, pf1 = _make_org(db, "OrgSc1", siren="111111101")
        org2, pf2 = _make_org(db, "OrgSc2", siren="222222202")
        _make_full_site(db, pf1, nom="S1")
        site2 = Site(nom="S2", type=TypeSite.BUREAU, portefeuille_id=pf2.id, actif=True)
        db.add(site2)
        db.commit()
        DemoState.set_demo_org(org1.id)
        r = client.get(f"/api/patrimoine/sites/{site2.id}/snapshot")
        assert r.status_code == 403

    def test_snapshot_missing_site_404(self, client, db):
        """Site inexistant -> 404."""
        DemoState.clear_demo_org()
        org, _ = _make_org(db, "OrgMiss")
        DemoState.set_demo_org(org.id)
        r = client.get("/api/patrimoine/sites/99999/snapshot")
        assert r.status_code == 404
