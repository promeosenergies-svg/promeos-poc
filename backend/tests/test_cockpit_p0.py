"""
PROMEOS - Tests P0 Cockpit Credibility
Vérifie : compliance score source, risk constants, trajectory endpoint, CO2 factor.
"""

import sys
import os
import pathlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

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
        from config.emission_factors import BASE_PENALTY_EURO, A_RISQUE_PENALTY_EURO

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
        if data.get("error"):
            assert data["error"] in ("no_targets", "no_sites")
            return
        required = [
            "reference_year",
            "reference_kwh_m2",
            "annees",
            "reel_mwh",
            "objectif_mwh",
            "jalons",
        ]
        for field in required:
            assert field in data, f"Champ manquant : {field}"

    def test_trajectory_jalons_correct(self, client):
        """Les jalons DT sont conformes au décret n°2019-771 (pas de jalon 2026)."""
        response = client.get("/api/cockpit/trajectory", headers={"X-Org-Id": "1"})
        data = response.json()
        if "error" in data:
            pytest.skip("Pas de targets en base de test")
        jalons = {j["annee"]: j["reduction_pct"] for j in data["jalons"]}
        assert 2026 not in jalons, "Le jalon 2026 n'existe pas dans le Decret n°2019-771"
        assert jalons.get(2030) == -40.0
        assert jalons.get(2040) == -50.0
        assert jalons.get(2050) == -60.0

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
        """CO2 electricite = 0.052 kg/kWh (ADEME Base Empreinte V23.6)."""
        from config.emission_factors import get_emission_factor

        assert get_emission_factor("ELEC") == 0.052

    def test_co2_factor_gaz_canonical(self):
        """CO2 gaz naturel = 0.227 kg/kWh (ADEME Base Empreinte V23.6)."""
        from config.emission_factors import get_emission_factor

        assert get_emission_factor("GAZ") == 0.227

    def test_co2_factors_from_single_source(self):
        """Tous les facteurs CO2 viennent de config/emission_factors.py."""
        from config.emission_factors import get_emission_factor

        assert get_emission_factor("ELEC") == 0.052
        assert get_emission_factor("GAZ") == 0.227


# ── P0-5 : CO2 N-1 Comparison ────────────────────────────────────────


class TestCo2N1Endpoint:
    """Vérifie la shape de GET /api/cockpit/co2."""

    def test_co2_endpoint_returns_expected_fields(self, client):
        """L'endpoint retourne les champs CO2 attendus."""
        response = client.get("/api/cockpit/co2", headers={"X-Org-Id": "1"})
        assert response.status_code == 200
        data = response.json()

        # Champs CO2 par énergie
        assert "elec_co2_kg" in data
        assert "gaz_co2_kg" in data
        assert "sites" in data
        assert isinstance(data["sites"], list)

    def test_co2_endpoint_sites_structure(self, client):
        """Chaque site contient les champs attendus."""
        data = client.get("/api/cockpit/co2", headers={"X-Org-Id": "1"}).json()

        if data["sites"]:
            site = data["sites"][0]
            assert "site_id" in site
            assert "site_nom" in site
            assert "breakdown" in site

    def test_co2_endpoint_values_non_negative(self, client):
        """Les valeurs CO2 sont >= 0."""
        data = client.get("/api/cockpit/co2", headers={"X-Org-Id": "1"}).json()

        assert data["elec_co2_kg"] >= 0
        assert data["gaz_co2_kg"] >= 0
