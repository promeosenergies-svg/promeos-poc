"""
PROMEOS — Tests chaine patrimoine → conformite.
Cascade archivage, propagation surface, recalcul BACS, orphelins.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, Batiment, TertiaireEfa
from models.bacs_models import BacsAsset, BacsCvcSystem
from models.tertiaire import TertiaireEfaBuilding
from models.enums import CvcSystemType, CvcArchitecture
from services.patrimoine_conformite_sync import (
    cascade_site_archive,
    flag_efa_desync_on_surface_change,
    detect_orphans,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def setup(db):
    org = Organisation(nom="O", type_client="tertiaire", actif=True, siren="123456789")
    db.add(org)
    db.flush()
    site = Site(nom="S", type="bureau", actif=True, surface_m2=1000)
    db.add(site)
    db.flush()
    bat = Batiment(site_id=site.id, nom="B", surface_m2=1000)
    db.add(bat)
    db.flush()
    efa = TertiaireEfa(org_id=org.id, site_id=site.id, nom="EFA Test")
    db.add(efa)
    db.flush()
    eb = TertiaireEfaBuilding(efa_id=efa.id, building_id=bat.id, surface_m2=1000, usage_label="Bureaux")
    db.add(eb)
    db.flush()
    asset = BacsAsset(site_id=site.id, is_tertiary_non_residential=True)
    db.add(asset)
    db.flush()
    return {"org": org, "site": site, "bat": bat, "efa": efa, "eb": eb, "asset": asset}


class TestCascadeArchive:
    def test_archive_site_cascades_efa(self, db, setup):
        site = setup["site"]
        efa = setup["efa"]
        site.soft_delete()
        result = cascade_site_archive(db, site.id)
        db.flush()
        db.refresh(efa)
        assert efa.is_deleted is True
        assert result["efa"] == 1

    def test_archive_site_cascades_bacs(self, db, setup):
        site = setup["site"]
        asset = setup["asset"]
        site.soft_delete()
        result = cascade_site_archive(db, site.id)
        db.flush()
        db.refresh(asset)
        assert asset.is_deleted is True
        assert result["bacs"] == 1

    def test_efa_not_visible_after_cascade(self, db, setup):
        site = setup["site"]
        site.soft_delete()
        cascade_site_archive(db, site.id)
        db.flush()
        from models import not_deleted

        active_efas = db.query(TertiaireEfa).filter(not_deleted(TertiaireEfa)).all()
        assert len(active_efas) == 0


class TestSurfaceSync:
    def test_surface_change_syncs_efa_building(self, db, setup):
        bat = setup["bat"]
        eb = setup["eb"]
        # Modifier surface batiment
        bat.surface_m2 = 1500
        db.flush()
        # Synchro
        synced = flag_efa_desync_on_surface_change(db, setup["site"].id)
        db.flush()
        db.refresh(eb)
        assert eb.surface_m2 == 1500
        assert synced == 1

    def test_no_sync_if_same_surface(self, db, setup):
        synced = flag_efa_desync_on_surface_change(db, setup["site"].id)
        assert synced == 0


class TestOrphanDetection:
    def test_detects_efa_orphan(self, db, setup):
        site = setup["site"]
        site.soft_delete()
        db.flush()
        # EFA non cascade (simulation sans la cascade)
        orphans = detect_orphans(db)
        assert len(orphans["efa_orphans"]) >= 1

    def test_detects_bacs_orphan(self, db, setup):
        site = setup["site"]
        site.soft_delete()
        db.flush()
        orphans = detect_orphans(db)
        assert len(orphans["bacs_orphans"]) >= 1

    def test_no_orphan_when_clean(self, db, setup):
        orphans = detect_orphans(db)
        assert len(orphans["efa_orphans"]) == 0
        assert len(orphans["bacs_orphans"]) == 0
