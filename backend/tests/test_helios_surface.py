"""
PROMEOS — Source-guard Phase 1.5 : surface HELIOS = 17 500 m² (Q4 audit Vue Exécutive).

Verrouille que :
  1. La migration `correct_helios_surface_phase1_5` redistribue correctement
     les batiments des 5 sites HELIOS pour atteindre 17 500 m² total.
  2. L'endpoint `/api/cockpit/_facts.scope.surface_total_m2` retourne bien 17 500
     en scope HELIOS — KPI kWh/m²/an cohérent pour Phase 2.

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.5 (décision Q4).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import Site
from sqlalchemy import func

from models.batiment import Batiment

HEADERS = {"X-Org-Id": "1"}

HELIOS_SITES = [
    "Siège HELIOS Paris",
    "Bureau Régional Lyon",
    "Entrepôt HELIOS Toulouse",
    "Hôtel HELIOS Nice",
    "École Jules Ferry Marseille",
]


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Source-guard DB invariant ───────────────────────────────────────────


class TestHeliosSurfaceDb:
    def test_helios_surface_total_17500_m2(self, db):
        """SUM(surface_m2) sur les 5 sites HELIOS canoniques = 17 500 m²."""
        total = (
            db.query(func.coalesce(func.sum(Batiment.surface_m2), 0))
            .join(Site, Site.id == Batiment.site_id)
            .filter(Site.nom.in_(HELIOS_SITES))
            .scalar()
        )
        # Tolérance 0.5 m² pour arrondi flottant (round(target/N, 1))
        assert abs(total - 17500) <= 0.5, (
            f"Total HELIOS surface = {total:.1f} m² (cible 17 500). "
            "Lancer `python -m migrations.correct_helios_surface_phase1_5`."
        )

    def test_helios_per_site_canonical_surfaces(self, db):
        """Chaque site HELIOS a la surface canonique de la spec packs.py."""
        targets = {
            "Siège HELIOS Paris": 3500,
            "Bureau Régional Lyon": 1200,
            "Entrepôt HELIOS Toulouse": 6000,
            "Hôtel HELIOS Nice": 4000,
            "École Jules Ferry Marseille": 2800,
        }
        for site_name, target_m2 in targets.items():
            site = db.query(Site).filter(Site.nom == site_name).first()
            if site is None:
                pytest.skip(f"Site {site_name} absent — seed HELIOS requis")
            actual = (
                db.query(func.coalesce(func.sum(Batiment.surface_m2), 0)).filter(Batiment.site_id == site.id).scalar()
            )
            assert abs(actual - target_m2) <= 0.5, f"Site '{site_name}' surface = {actual:.1f} m² (cible {target_m2})"


# ── Source-guard endpoint /api/cockpit/_facts ──────────────────────────


class TestHeliosSurfaceEndpoint:
    def test_facts_scope_surface_total_m2(self, client):
        """L'endpoint /api/cockpit/_facts expose surface_total_m2 = 17 500."""
        response = client.get("/api/cockpit/_facts", headers=HEADERS)
        assert response.status_code == 200, response.text
        body = response.json()
        scope = body.get("scope", {})
        surface = scope.get("surface_total_m2")
        assert surface is not None, "scope.surface_total_m2 absent du payload _facts"
        # Tolérance 0.5 m² flottant (round)
        assert abs(surface - 17500) <= 0.5, (
            f"surface_total_m2 = {surface} (cible 17 500). Migration correct_helios_surface_phase1_5 à exécuter ?"
        )
