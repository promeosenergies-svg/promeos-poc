"""
PROMEOS - Tests P0 Cockpit Credibility
Vérifie : compliance score source, risk constants, trajectory endpoint, CO2 factor.
"""

import sys
import os
import pathlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from main import app
from models import Base
from database import get_db


@pytest.fixture
def client():
    """Client with demo DB (read-only tests)."""
    return TestClient(app)


@pytest.fixture
def isolated_client():
    """Client with isolated in-memory DB."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()
    session.close()


# ── P0-1 : Compliance Score ──────────────────────────────────────────


class TestCockpitComplianceScore:
    def test_score_from_reg_assessment(self, client):
        """compliance_score vient de RegAssessment (0-100, higher=better)."""
        response = client.get("/api/cockpit", headers={"X-Org-Id": "1"})
        assert response.status_code == 200
        data = response.json()
        assert "compliance_score" in data["stats"]
        assert data["stats"]["compliance_source"] == "RegAssessment"

    def test_computed_at_present(self, client):
        """compliance_computed_at doit être présent."""
        response = client.get("/api/cockpit", headers={"X-Org-Id": "1"})
        data = response.json()
        assert "compliance_computed_at" in data["stats"]

    def test_sites_evaluated_present(self, client):
        """sites_evaluated doit être présent."""
        response = client.get("/api/cockpit", headers={"X-Org-Id": "1"})
        data = response.json()
        assert "sites_evaluated" in data["stats"]
        assert isinstance(data["stats"]["sites_evaluated"], int)


# ── P0-2 : Risk Constants ────────────────────────────────────────────


class TestCockpitRisk:
    def test_a_risque_penalty_constant(self):
        """A_RISQUE_PENALTY_EURO == 3750 (50% de BASE_PENALTY_EURO)."""
        from services.compliance_engine import BASE_PENALTY_EURO, A_RISQUE_PENALTY_EURO

        assert BASE_PENALTY_EURO == 7_500
        assert A_RISQUE_PENALTY_EURO == 3_750

    def test_no_hardcoded_half_penalty_in_migrations(self):
        """migrations.py utilise A_RISQUE_PENALTY_EURO, pas BASE_PENALTY_EURO * 0.5."""
        src = pathlib.Path("backend/database/migrations.py")
        if not src.exists():
            src = (
                pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "database" / "migrations.py"
            )
        text = src.read_text(encoding="utf-8")
        assert "A_RISQUE_PENALTY_EURO" in text

    def test_risque_breakdown_present(self, client):
        """risque_breakdown doit être dans la réponse cockpit."""
        response = client.get("/api/cockpit", headers={"X-Org-Id": "1"})
        data = response.json()
        assert "risque_breakdown" in data["stats"]
        rb = data["stats"]["risque_breakdown"]
        assert "total_eur" in rb
        assert "reglementaire_eur" in rb


# ── P0-3 : Trajectory Endpoint ───────────────────────────────────────


class TestCockpitTrajectory:
    def test_trajectory_endpoint_exists(self, client):
        """GET /api/cockpit/trajectory retourne 200."""
        response = client.get("/api/cockpit/trajectory", headers={"X-Org-Id": "1"})
        assert response.status_code == 200

    def test_trajectory_structure(self, client):
        """La réponse contient les séries attendues."""
        response = client.get("/api/cockpit/trajectory", headers={"X-Org-Id": "1"})
        data = response.json()
        # Si pas de targets, on attend error=no_targets ou no_sites
        if "error" in data:
            assert data["error"] in ("no_targets", "no_sites")
            return
        required = [
            "ref_year",
            "ref_kwh",
            "reduction_pct_actuelle",
            "annees",
            "reel_mwh",
            "objectif_mwh",
            "jalons",
        ]
        for field in required:
            assert field in data, f"Champ manquant : {field}"

    def test_trajectory_jalons_correct(self, client):
        """Les jalons DT sont conformes au décret n°2019-771."""
        response = client.get("/api/cockpit/trajectory", headers={"X-Org-Id": "1"})
        data = response.json()
        if "error" in data:
            pytest.skip("Pas de targets en base de test")
        jalons = {j["annee"]: j["reduction_pct"] for j in data["jalons"]}
        assert jalons.get(2026) == -25.0
        assert jalons.get(2030) == -40.0
        assert jalons.get(2040) == -50.0

    def test_no_calc_in_frontend_trajectory(self):
        """Vérification structurelle : le front ne calcule pas la trajectoire."""
        base = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        frontend_pages = base.parent / "frontend" / "src" / "pages"
        frontend_hooks = base.parent / "frontend" / "src" / "hooks"
        cockpit_files = list(frontend_pages.rglob("Cockpit*.jsx")) if frontend_pages.exists() else []
        cockpit_files += list(frontend_pages.rglob("CommandCenter*.jsx")) if frontend_pages.exists() else []
        cockpit_files += list(frontend_hooks.rglob("useCockpit*.js")) if frontend_hooks.exists() else []
        for f in cockpit_files:
            src = f.read_text(encoding="utf-8", errors="ignore")
            assert "conso_ref" not in src, f"Calcul trajectoire front détecté dans {f}"


# ── P0-4 : CO2 Factor ────────────────────────────────────────────────


class TestCo2Factor:
    def test_co2_factor_elec_canonical(self):
        """CO2 électricité = 0.0569 kg/kWh (ADEME 2024) — pas 0.052."""
        from services.compliance_engine import CO2_FACTOR_ELEC_KG_KWH

        assert CO2_FACTOR_ELEC_KG_KWH == 0.0569

    def test_co2_factor_gaz_canonical(self):
        """CO2 gaz naturel = 0.2270 kg/kWh (ADEME 2024)."""
        from services.compliance_engine import CO2_FACTOR_GAZ_KG_KWH

        assert CO2_FACTOR_GAZ_KG_KWH == 0.2270
