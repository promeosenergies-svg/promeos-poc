"""
PROMEOS — Sprint C-3 Phase 3.4 : Tests endpoint GET /api/portfolio/intensity.

Vérifie l'agrégat intensité patrimoine (Σ kWh / Σ surface) org-scopé.

Dette clôturée : D-Phase4-3-Portfolio-Intensity-Backend-001 (Sprint C-3).

Périmètre :
- Sans filtre : agrégation tous portefeuilles de l'organisation
- Avec portefeuille_id : 1 portefeuille spécifique + vérification ownership
- Cas vides + cas partiels (sites avec/sans données)
- Cohérence mathématique : ratio des SOMMES (pas moyenne arithmétique des ratios)
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


# ─── Service unit (formule correcte) ─────────────────────────────────────────


def test_compute_portfolio_intensity_uses_ratio_of_sums_not_mean_of_ratios():
    """Formule canonique : Σ(kWh) / Σ(m²) ≠ Σ(kWh/m²) / N.

    Démonstration mathématique :
      site A : 100 kWh / 1 m²   → intensity_A = 100
      site B : 1 kWh / 100 m²   → intensity_B = 0.01
      Moyenne arithmétique = 50.005 (FAUX, pondère pareil les 2 sites)
      Σ/Σ = 101 / 101 = 1.0     (CORRECT, pondéré par surface)
    """
    from unittest.mock import MagicMock
    from services.portfolio_intensity_service import compute_portfolio_intensity

    # Setup : 2 sites avec annual_kwh + surface_m2 contrastés
    site_a = MagicMock(annual_kwh_total=100.0, surface_m2=1.0, tertiaire_area_m2=None)
    site_b = MagicMock(annual_kwh_total=1.0, surface_m2=100.0, tertiaire_area_m2=None)

    db = MagicMock()
    # Mock chain query.join.join.filter.filter.all() → [site_a, site_b]
    db.query.return_value.join.return_value.join.return_value.filter.return_value.filter.return_value.all.return_value = [
        site_a,
        site_b,
    ]

    result = compute_portfolio_intensity(db, organisation_id=1)

    # Σ kWh = 101, Σ surface = 101 → 1.0 (pas 50.005 qui serait la moyenne arithmétique)
    assert result["intensity_kwh_m2_total"] == 1.0
    assert result["sum_annual_kwh"] == 101.0
    assert result["sum_surface_m2"] == 101.0
    assert result["sites_count"] == 2
    assert result["sites_with_data_count"] == 2


def test_compute_portfolio_intensity_no_sites_returns_null_intensity():
    """Org sans sites → intensity=None (pas crash, pas 0)."""
    from unittest.mock import MagicMock
    from services.portfolio_intensity_service import compute_portfolio_intensity

    db = MagicMock()
    db.query.return_value.join.return_value.join.return_value.filter.return_value.filter.return_value.all.return_value = []

    result = compute_portfolio_intensity(db, organisation_id=1)

    assert result["intensity_kwh_m2_total"] is None
    assert result["intensity_kwh_m2_tertiaire"] is None
    assert result["sites_count"] == 0
    assert result["sites_with_data_count"] == 0
    assert result["sum_annual_kwh"] is None


def test_compute_portfolio_intensity_partial_data_handled():
    """Sites mix : certains avec données, d'autres sans → comptage correct."""
    from unittest.mock import MagicMock
    from services.portfolio_intensity_service import compute_portfolio_intensity

    site_complete = MagicMock(annual_kwh_total=10000, surface_m2=100, tertiaire_area_m2=80)
    site_no_kwh = MagicMock(annual_kwh_total=None, surface_m2=200, tertiaire_area_m2=None)
    site_no_surface = MagicMock(annual_kwh_total=5000, surface_m2=None, tertiaire_area_m2=None)
    site_zero_kwh = MagicMock(annual_kwh_total=0, surface_m2=50, tertiaire_area_m2=None)

    db = MagicMock()
    db.query.return_value.join.return_value.join.return_value.filter.return_value.filter.return_value.all.return_value = [
        site_complete,
        site_no_kwh,
        site_no_surface,
        site_zero_kwh,
    ]

    result = compute_portfolio_intensity(db, organisation_id=1)

    assert result["sites_count"] == 4
    # Seul site_complete a kWh > 0 ET surface > 0
    assert result["sites_with_data_count"] == 1
    # Σ kWh effectifs : 10000 (complete) + 5000 (no_surface, kWh seul) = 15000
    assert result["sum_annual_kwh"] == 15000
    # Σ surface effective : 100 (complete) + 200 (no_kwh, surface seule) + 50 (zero_kwh, surface) = 350
    assert result["sum_surface_m2"] == 350
    # intensity_total = 15000 / 350 ≈ 42.86
    assert result["intensity_kwh_m2_total"] == pytest.approx(42.86, abs=0.01)


def test_compute_portfolio_intensity_total_vs_tertiaire_distinct():
    """intensity_total et intensity_tertiaire calculés sur 2 dénominateurs distincts."""
    from unittest.mock import MagicMock
    from services.portfolio_intensity_service import compute_portfolio_intensity

    site = MagicMock(annual_kwh_total=10000, surface_m2=100, tertiaire_area_m2=50)

    db = MagicMock()
    db.query.return_value.join.return_value.join.return_value.filter.return_value.filter.return_value.all.return_value = [
        site
    ]

    result = compute_portfolio_intensity(db, organisation_id=1)

    assert result["intensity_kwh_m2_total"] == 100.0  # 10000/100
    assert result["intensity_kwh_m2_tertiaire"] == 200.0  # 10000/50


# ─── Endpoint integration via TestClient ─────────────────────────────────────


def test_endpoint_no_filter_returns_org_aggregate():
    """GET /api/portfolio/intensity sans paramètre → agrégat org HELIOS."""
    resp = client.get("/api/portfolio/intensity")
    assert resp.status_code == 200, resp.text

    data = resp.json()
    # Schema obligatoire
    for key in [
        "intensity_kwh_m2_total",
        "intensity_kwh_m2_tertiaire",
        "sites_count",
        "sites_with_data_count",
        "sum_annual_kwh",
        "sum_surface_m2",
        "sum_tertiaire_area_m2",
        "scope",
    ]:
        assert key in data, f"Key manquante: {key}"

    # Sprint C-3 Phase 3.7d audit follow-up — PROMEOS-SEC-2026-042 (CWE-200) :
    # `organisation_id` retiré de la réponse publique (anti-amplification IDOR).
    # Seul `portefeuille_id` reste dans scope (déjà fourni par le client).
    assert "organisation_id" not in data["scope"]
    assert "portefeuille_id" in data["scope"]
    assert data["scope"]["portefeuille_id"] is None  # pas de filtre


def test_endpoint_with_portefeuille_filter():
    """Filtre sur 1 portefeuille existant → response valide."""
    from database import SessionLocal
    from models import Portefeuille

    db = SessionLocal()
    try:
        pf = db.query(Portefeuille).first()
        if not pf:
            pytest.skip("Aucun portefeuille seedé")
        pf_id = pf.id
    finally:
        db.close()

    resp = client.get("/api/portfolio/intensity", params={"portefeuille_id": pf_id})
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["scope"]["portefeuille_id"] == pf_id


def test_endpoint_other_org_portefeuille_returns_403_or_404():
    """Sécurité : portefeuille hors org → 403 (helper raise) ou 404 si inexistant."""
    resp = client.get("/api/portfolio/intensity", params={"portefeuille_id": 9_999_999})
    # _check_portfolio_belongs_to_org raise 404 si portefeuille inexistant
    assert resp.status_code in (403, 404)


def test_endpoint_response_schema_strict():
    """Anti-régression schema endpoint."""
    resp = client.get("/api/portfolio/intensity")
    assert resp.status_code == 200

    data = resp.json()
    # Types attendus
    assert isinstance(data["sites_count"], int)
    assert isinstance(data["sites_with_data_count"], int)
    assert data["sites_with_data_count"] <= data["sites_count"]


def test_endpoint_aggregation_correctness_demo_seed():
    """Sur seed HELIOS, intensity_kwh_m2_total = Σ kWh / Σ surface (cohérence)."""
    resp = client.get("/api/portfolio/intensity")
    assert resp.status_code == 200

    data = resp.json()
    if data["sum_annual_kwh"] and data["sum_surface_m2"]:
        expected = round(data["sum_annual_kwh"] / data["sum_surface_m2"], 2)
        assert data["intensity_kwh_m2_total"] == expected, (
            f"Cohérence cassée : {data['intensity_kwh_m2_total']} ≠ "
            f"{data['sum_annual_kwh']}/{data['sum_surface_m2']} = {expected}"
        )
