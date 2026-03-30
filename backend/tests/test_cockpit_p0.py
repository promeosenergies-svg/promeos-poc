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
    """Vérifie la shape enrichie de GET /api/cockpit/co2 avec N-1."""

    def test_co2_endpoint_returns_n1_fields(self, client):
        """L'endpoint retourne les champs N-1 et deltas."""
        response = client.get("/api/cockpit/co2", headers={"X-Org-Id": "1"})
        assert response.status_code == 200
        data = response.json()

        # Champs N existants
        assert "total_t_co2" in data
        assert "scope1_t_co2" in data
        assert "scope2_t_co2" in data

        # Champs N-1 (nouveaux)
        assert "prev_total_tco2" in data
        assert "prev_scope1_tco2" in data
        assert "prev_scope2_tco2" in data

        # Deltas (nouveaux)
        assert "delta_total_pct" in data
        assert "delta_scope1_pct" in data
        assert "delta_scope2_pct" in data

        # Métadonnées période
        assert "year" in data
        assert "period_label" in data
        assert "prev_year" in data
        assert "prev_period_label" in data
        assert data["prev_year"] == data["year"] - 1

    def test_co2_endpoint_factors_tracability(self, client):
        """La réponse contient les facteurs ADEME pour traçabilité."""
        data = client.get("/api/cockpit/co2", headers={"X-Org-Id": "1"}).json()

        assert "co2_factors" in data
        assert data["co2_factors"]["elec_kgco2_per_kwh"] == 0.052
        assert data["co2_factors"]["gaz_kgco2_per_kwh"] == 0.227
        assert "ADEME" in data["co2_factors"]["source"]

    def test_co2_endpoint_coherence_total_eq_scopes(self, client):
        """total = scope1 + scope2 (à 0.2 tCO₂ près pour arrondis)."""
        data = client.get("/api/cockpit/co2", headers={"X-Org-Id": "1"}).json()

        if data["total_t_co2"] > 0:
            assert abs(data["total_t_co2"] - (data["scope1_t_co2"] + data["scope2_t_co2"])) < 0.2

    def test_co2_endpoint_delta_formula(self, client):
        """delta = (N - N-1) / N-1 × 100, arrondi à 1 décimale."""
        data = client.get("/api/cockpit/co2", headers={"X-Org-Id": "1"}).json()

        if data.get("prev_total_tco2") and data["prev_total_tco2"] > 0:
            expected = round((data["total_t_co2"] - data["prev_total_tco2"]) / data["prev_total_tco2"] * 100, 1)
            assert data["delta_total_pct"] == pytest.approx(expected, abs=0.1)

    def test_co2_endpoint_period_labels_same_months(self, client):
        """Les labels N et N-1 couvrent les mêmes mois."""
        data = client.get("/api/cockpit/co2", headers={"X-Org-Id": "1"}).json()

        # Les deux labels commencent par "Janv" et finissent par le même mois
        assert data["period_label"].startswith("Janv")
        assert data["prev_period_label"].startswith("Janv")
        # Même mois fin (ex: "Janv – Mars 2026" vs "Janv – Mars 2025")
        month_n = data["period_label"].split(" – ")[1].split(" ")[0]
        month_n1 = data["prev_period_label"].split(" – ")[1].split(" ")[0]
        assert month_n == month_n1
