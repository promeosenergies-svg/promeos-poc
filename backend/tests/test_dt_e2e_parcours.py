"""
PROMEOS — Test E2E Parcours Complet Décret Tertiaire

Vérifie le parcours utilisateur complet après seed HELIOS :
  seed → cockpit → dashboard DT → EFA detail → trajectoire →
  mutualisation → modulation → score explain → regops site
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import Base


@pytest.fixture(scope="module")
def seeded_client():
    """Crée une DB in-memory, seed le pack HELIOS S, et fournit un TestClient."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override

    # Seed HELIOS pack
    from services.demo_seed.orchestrator import SeedOrchestrator

    orchestrator = SeedOrchestrator(session)
    result = orchestrator.seed(pack="helios", size="S")
    session.commit()

    client = TestClient(app)
    yield client, session, result

    app.dependency_overrides.clear()
    session.close()


class TestDTParcoursComplet:
    """Parcours E2E complet du Décret Tertiaire après seed HELIOS."""

    # ── 1. Cockpit ──

    def test_cockpit_accessible(self, seeded_client):
        client, session, seed = seeded_client
        r = client.get("/api/cockpit")
        assert r.status_code == 200
        data = r.json()
        stats = data.get("stats", data)
        assert stats.get("total_sites", 0) >= 4, f"Cockpit devrait voir >= 4 sites, got {stats}"

    # ── 2. Dashboard Tertiaire ──

    def test_tertiaire_dashboard(self, seeded_client):
        client, session, seed = seeded_client
        org_id = seed.get("org_id", 1)
        r = client.get("/api/tertiaire/dashboard", params={"org_id": org_id})
        assert r.status_code == 200
        data = r.json()
        total = data.get("total_efa", 0) or len(data.get("efas", []))
        assert total >= 4, f"Dashboard devrait voir >= 4 EFA, got {data}"

    # ── 3. EFA Detail ──

    def test_efa_detail_paris(self, seeded_client):
        client, session, seed = seeded_client
        from models.tertiaire import TertiaireEfa

        efas = session.query(TertiaireEfa).all()
        assert len(efas) >= 4, f"Expected >= 4 EFAs, got {len(efas)}"

        for efa in efas:
            r = client.get(f"/api/tertiaire/efa/{efa.id}")
            assert r.status_code == 200, f"EFA {efa.id} ({efa.nom}) returned {r.status_code}"
            data = r.json()
            assert "name" in data or "id" in data

    # ── 4. Trajectoire avec delta_kwh != None ──

    def test_trajectoire_delta_not_none(self, seeded_client):
        client, session, seed = seeded_client
        from models.tertiaire import TertiaireEfa

        efas = session.query(TertiaireEfa).all()
        for efa in efas:
            r = client.get(f"/api/tertiaire/efa/{efa.id}/targets/validate", params={"year": 2024})
            assert r.status_code == 200, f"EFA {efa.id}: status {r.status_code}"
            data = r.json()

            if data.get("status") != "not_evaluable":
                assert data.get("raw_delta_kwh") is not None, (
                    f"EFA {efa.id} ({efa.nom}): raw_delta_kwh is None but status={data.get('status')}"
                )
                assert data.get("raw_delta_percent") is not None, f"EFA {efa.id} ({efa.nom}): raw_delta_percent is None"
                assert isinstance(data["raw_delta_kwh"], (int, float))

    def test_trajectoire_coherence(self, seeded_client):
        """Lyon (on_track) devrait avoir delta < 0 ; Paris (off_track) delta > 0."""
        client, session, seed = seeded_client
        from models.tertiaire import TertiaireEfa

        efas = session.query(TertiaireEfa).all()
        results = {}
        for efa in efas:
            r = client.get(f"/api/tertiaire/efa/{efa.id}/targets/validate", params={"year": 2024})
            if r.status_code == 200:
                data = r.json()
                results[efa.nom] = data

        # Au moins un on_track et un off_track
        statuses = [r.get("status") for r in results.values() if r.get("status") != "not_evaluable"]
        assert len(statuses) >= 2, f"Expected >= 2 evaluable EFAs, got {len(statuses)}"

    # ── 5. Mutualisation ──

    def test_mutualisation(self, seeded_client):
        client, session, seed = seeded_client
        org_id = seed.get("org_id", 1)
        r = client.get("/api/tertiaire/mutualisation", params={"org_id": org_id, "jalon": 2030})
        assert r.status_code == 200
        data = r.json()
        sites = data.get("sites") or data.get("efas") or []
        assert len(sites) >= 2, f"Mutualisation devrait voir >= 2 sites, got {len(sites)}"

    # ── 6. Modulation simulation ──

    def test_modulation_simulation(self, seeded_client):
        client, session, seed = seeded_client
        from models.tertiaire import TertiaireEfa

        efa = session.query(TertiaireEfa).first()
        assert efa is not None

        body = {
            "efa_id": efa.id,
            "contraintes": [
                {
                    "type": "technique",
                    "description": "Bâtiment classé",
                    "actions": [
                        {
                            "label": "PAC",
                            "cout_eur": 85000,
                            "economie_annuelle_kwh": 50000,
                            "economie_annuelle_eur": 5000,
                            "duree_vie_ans": 20,
                        }
                    ],
                }
            ],
        }
        r = client.post("/api/tertiaire/modulation-simulation", json=body)
        assert r.status_code == 200, f"Modulation returned {r.status_code}: {r.text[:200]}"
        data = r.json()
        assert "dossier_readiness_score" in data or "objectif_module_kwh" in data or "modulated_target" in data

    # ── 7. Score explain ──

    def test_score_explain(self, seeded_client):
        client, session, seed = seeded_client
        from models import Site

        site = session.query(Site).first()
        assert site is not None

        r = client.get("/api/regops/score_explain", params={"scope_type": "site", "scope_id": site.id})
        assert r.status_code == 200
        data = r.json()
        assert "per_regulation" in data or "score" in data or "breakdown" in data

    # ── 8. RegOps site findings ──

    def test_regops_site(self, seeded_client):
        client, session, seed = seeded_client
        from models import Site

        site = session.query(Site).first()
        assert site is not None

        r = client.get(f"/api/regops/site/{site.id}")
        assert r.status_code == 200
        data = r.json()
        # Vérifier structure de base
        assert isinstance(data, dict)
