"""
PROMEOS — Demo Manifest Endpoint Tests
GET /api/demo/manifest: source de verite org/portfolios/sites/compteurs.

Tests the manifest logic directly (without importing routes module which
has heavy transitive deps like bcrypt).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, EntiteJuridique, Portefeuille, Compteur
from services.demo_state import DemoState


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def reset_demo_state():
    """Reset DemoState between tests."""
    DemoState.clear_demo_org()
    yield
    DemoState.clear_demo_org()


def _seed(db, pack="helios", size="S"):
    """Run SeedOrchestrator and return result."""
    from services.demo_seed import SeedOrchestrator
    orch = SeedOrchestrator(db)
    return orch.seed(pack=pack, size=size, rng_seed=42, days=30)


def _get_manifest(db):
    """Replicate GET /api/demo/manifest logic (avoids importing routes module)."""
    ctx = DemoState.get_demo_context()
    org_id = ctx.get("org_id")

    if not org_id:
        raise HTTPException(status_code=404, detail="No demo seeded")

    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found in DB")

    entites = db.query(EntiteJuridique).filter(
        EntiteJuridique.organisation_id == org.id
    ).all()

    portefeuilles = []
    total_sites = 0
    total_compteurs = 0
    all_site_ids = []

    for ej in entites:
        for p in db.query(Portefeuille).filter(
            Portefeuille.entite_juridique_id == ej.id
        ).all():
            sites = db.query(Site).filter(Site.portefeuille_id == p.id).all()
            compteurs_count = (
                db.query(Compteur).filter(Compteur.site_id.in_([s.id for s in sites])).count()
                if sites else 0
            )
            total_sites += len(sites)
            total_compteurs += compteurs_count
            site_ids = [s.id for s in sites]
            all_site_ids.extend(site_ids)
            portefeuilles.append({
                "id": p.id,
                "nom": p.nom,
                "entite_juridique_id": ej.id,
                "sites_count": len(sites),
                "site_ids": site_ids,
            })

    return {
        "org_id": org.id,
        "org_nom": org.nom,
        "pack": ctx.get("pack"),
        "size": ctx.get("size"),
        "portefeuilles": portefeuilles,
        "total_sites": total_sites,
        "total_compteurs": total_compteurs,
        "all_site_ids": all_site_ids,
    }


class TestManifestNoSeed:
    def test_manifest_no_seed_returns_404(self, db_session):
        """Without seed, manifest returns 404."""
        with pytest.raises(HTTPException) as exc_info:
            _get_manifest(db_session)
        assert exc_info.value.status_code == 404
        assert "No demo seeded" in str(exc_info.value.detail)


class TestManifestAfterSeed:
    def test_manifest_returns_structure(self, db_session):
        """After seed, manifest has all expected keys."""
        _seed(db_session, "helios", "S")
        manifest = _get_manifest(db_session)

        assert "org_id" in manifest
        assert "org_nom" in manifest
        assert "pack" in manifest
        assert "size" in manifest
        assert "portefeuilles" in manifest
        assert "total_sites" in manifest
        assert "total_compteurs" in manifest
        assert "all_site_ids" in manifest
        assert manifest["org_nom"] == "Groupe HELIOS"
        assert manifest["pack"] == "helios"
        assert manifest["size"] == "S"

    def test_manifest_site_count_matches_pack(self, db_session):
        """Helios S = 5 sites. Manifest count must match DB count."""
        _seed(db_session, "helios", "S")
        manifest = _get_manifest(db_session)

        assert manifest["total_sites"] == 5
        # Cross-check with DB
        db_count = db_session.query(Site).count()
        assert manifest["total_sites"] == db_count
        # all_site_ids length must match
        assert len(manifest["all_site_ids"]) == 5

    def test_manifest_portefeuilles_sum(self, db_session):
        """Sum of sites_count across portefeuilles == total_sites."""
        _seed(db_session, "helios", "S")
        manifest = _get_manifest(db_session)

        pf_sum = sum(p["sites_count"] for p in manifest["portefeuilles"])
        assert pf_sum == manifest["total_sites"]

    def test_manifest_compteurs_count(self, db_session):
        """Manifest total_compteurs matches DB count."""
        _seed(db_session, "helios", "S")
        manifest = _get_manifest(db_session)

        db_count = db_session.query(Compteur).count()
        assert manifest["total_compteurs"] == db_count
        assert manifest["total_compteurs"] > 0


class TestSeedIdempotent:
    def test_seed_twice_same_result(self, db_session):
        """Seeding twice with reset produces identical manifest."""
        from services.demo_seed import SeedOrchestrator

        # First seed
        _seed(db_session, "casino", "S")
        m1 = _get_manifest(db_session)

        # Reset + re-seed (idempotent)
        orch = SeedOrchestrator(db_session)
        orch.reset(mode="hard")
        _seed(db_session, "casino", "S")
        m2 = _get_manifest(db_session)

        assert m2["total_sites"] == m1["total_sites"]
        assert m2["total_compteurs"] == m1["total_compteurs"]
        assert m2["pack"] == m1["pack"]
        assert len(m2["portefeuilles"]) == len(m1["portefeuilles"])
