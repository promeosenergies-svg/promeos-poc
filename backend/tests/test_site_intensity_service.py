"""
PROMEOS — Sprint C-2 Phase 4.2 : Tests site_intensity_service.

Vérifie les 2 calculs d'intensité (matrice v1 §4.4.F #56) :
- intensity_kwh_m2_total      = annual_kwh_total / surface_m2
- intensity_kwh_m2_tertiaire  = annual_kwh_total / tertiaire_area_m2

Garde-fous testés :
- Division par zéro safe (retourne None, pas NaN/Infinity)
- annual_kwh_total None / 0 → None pour les 2 intensités
- surface absente → None pour l'intensité correspondante seulement
- Persistance DB + reload (test 8)
"""

from __future__ import annotations

import math
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Test 1 : intensity_total calcul correct ────────────────────────────────


def test_intensity_total_calculation_correct():
    """Site avec annual_kwh=100000 et surface_m2=1000 → intensity_total=100.0."""
    from services.site_intensity_service import compute_site_intensities

    site = MagicMock()
    site.annual_kwh_total = 100_000
    site.surface_m2 = 1000
    site.tertiaire_area_m2 = 800

    result = compute_site_intensities(site)
    assert result["intensity_kwh_m2_total"] == 100.0


# ─── Test 2 : intensity_tertiaire calcul correct ────────────────────────────


def test_intensity_tertiaire_calculation_correct():
    """Site avec annual_kwh=100000 et tertiaire_area_m2=800 → intensity_tertiaire=125.0."""
    from services.site_intensity_service import compute_site_intensities

    site = MagicMock()
    site.annual_kwh_total = 100_000
    site.surface_m2 = 1000
    site.tertiaire_area_m2 = 800

    result = compute_site_intensities(site)
    assert result["intensity_kwh_m2_tertiaire"] == 125.0


# ─── Test 3 : annual_kwh=0 → 2 None ────────────────────────────────────────


def test_intensity_null_when_annual_kwh_zero():
    """Conso=0 → intensity_total=None ET intensity_tertiaire=None (pas de données)."""
    from services.site_intensity_service import compute_site_intensities

    site = MagicMock()
    site.annual_kwh_total = 0
    site.surface_m2 = 1000
    site.tertiaire_area_m2 = 800

    result = compute_site_intensities(site)
    assert result["intensity_kwh_m2_total"] is None
    assert result["intensity_kwh_m2_tertiaire"] is None


# ─── Test 4 : annual_kwh=None → 2 None ─────────────────────────────────────


def test_intensity_null_when_annual_kwh_none():
    """Conso=None → intensity_total=None ET intensity_tertiaire=None."""
    from services.site_intensity_service import compute_site_intensities

    site = MagicMock()
    site.annual_kwh_total = None
    site.surface_m2 = 1000
    site.tertiaire_area_m2 = 800

    result = compute_site_intensities(site)
    assert result["intensity_kwh_m2_total"] is None
    assert result["intensity_kwh_m2_tertiaire"] is None


# ─── Test 5 : surface_m2=0 → intensity_total=None mais tertiaire OK ────────


def test_intensity_total_null_when_surface_zero():
    """surface_m2=0 → intensity_total=None ; intensity_tertiaire indépendant et OK si tertiaire OK."""
    from services.site_intensity_service import compute_site_intensities

    site = MagicMock()
    site.annual_kwh_total = 100_000
    site.surface_m2 = 0
    site.tertiaire_area_m2 = 800

    result = compute_site_intensities(site)
    assert result["intensity_kwh_m2_total"] is None
    assert result["intensity_kwh_m2_tertiaire"] == 125.0


# ─── Test 6 : tertiaire_area_m2=None → intensity_tertiaire=None ────────────


def test_intensity_tertiaire_null_when_no_tertiaire():
    """tertiaire_area_m2=None → intensity_tertiaire=None ; intensity_total OK si surface_m2 OK."""
    from services.site_intensity_service import compute_site_intensities

    site = MagicMock()
    site.annual_kwh_total = 100_000
    site.surface_m2 = 1000
    site.tertiaire_area_m2 = None

    result = compute_site_intensities(site)
    assert result["intensity_kwh_m2_total"] == 100.0
    assert result["intensity_kwh_m2_tertiaire"] is None


# ─── Test 7 : pas de NaN ni Infinity même en cas tordu ─────────────────────


def test_intensity_no_nan_no_infinity():
    """Toutes les combinaisons surface=0/None ne doivent jamais produire NaN ni Infinity."""
    from services.site_intensity_service import _safe_intensity, compute_site_intensities

    # _safe_intensity directement
    cases = [
        (None, 1000),
        (100_000, None),
        (0, 1000),
        (100_000, 0),
        (-50, 1000),  # cas négatif (improbable mais doit être safe)
        (100_000, -50),
    ]
    for kwh, surface in cases:
        result = _safe_intensity(kwh, surface)
        assert result is None, f"Expected None for kwh={kwh}, surface={surface}, got {result}"

    # Via compute_site_intensities
    site = MagicMock()
    site.annual_kwh_total = 100_000
    site.surface_m2 = 0
    site.tertiaire_area_m2 = 0
    result = compute_site_intensities(site)
    for value in result.values():
        assert value is None or not (isinstance(value, float) and (math.isnan(value) or math.isinf(value)))


# ─── Test 8 : persist_site_intensities écrit + reload ───────────────────────


def test_persist_site_intensities_writes_to_db():
    """persist_site_intensities() flush les valeurs sur Site (lisibles via reload)."""
    from database import SessionLocal
    from models import Site, not_deleted
    from services.site_intensity_service import persist_site_intensities

    db = SessionLocal()
    snapshot = {}
    site_id = None
    try:
        site = db.query(Site).filter(not_deleted(Site)).first()
        if not site:
            pytest.skip("Aucun site HELIOS dans la DB")
        site_id = site.id

        # Snapshot avant pour restoration
        snapshot = {
            "annual_kwh_total": site.annual_kwh_total,
            "surface_m2": site.surface_m2,
            "tertiaire_area_m2": site.tertiaire_area_m2,
            "intensity_kwh_m2_total": site.intensity_kwh_m2_total,
            "intensity_kwh_m2_tertiaire": site.intensity_kwh_m2_tertiaire,
        }

        # Forcer des valeurs déterministes pour le test
        site.annual_kwh_total = 200_000
        site.surface_m2 = 2000
        site.tertiaire_area_m2 = 1600
        db.flush()

        result = persist_site_intensities(db, site)
        db.commit()

        # Reload depuis nouvelle session
        db2 = SessionLocal()
        try:
            reloaded = db2.query(Site).filter(Site.id == site_id).first()
            assert reloaded.intensity_kwh_m2_total == 100.0  # 200000 / 2000
            assert reloaded.intensity_kwh_m2_tertiaire == 125.0  # 200000 / 1600
            assert result["intensity_kwh_m2_total"] == 100.0
            assert result["intensity_kwh_m2_tertiaire"] == 125.0
        finally:
            db2.close()
    finally:
        # Restoration
        if site_id is not None and snapshot:
            try:
                site = db.query(Site).filter(Site.id == site_id).first()
                if site:
                    for field, value in snapshot.items():
                        setattr(site, field, value)
                    db.commit()
            except Exception:
                db.rollback()
        db.close()


# ─── Tests 9-11 : Cascade integration ───────────────────────────────────────


@pytest.fixture
def site_with_data():
    """Site HELIOS avec valeurs déterministes pour cascade tests, restauré en teardown."""
    from database import SessionLocal
    from models import Site, not_deleted

    db = SessionLocal()
    snapshot = {}
    site_id = None
    try:
        site = db.query(Site).filter(not_deleted(Site)).first()
        if not site:
            pytest.skip("Aucun site HELIOS dans la DB")
        site_id = site.id

        snapshot = {
            "annual_kwh_total": site.annual_kwh_total,
            "surface_m2": site.surface_m2,
            "tertiaire_area_m2": site.tertiaire_area_m2,
            "intensity_kwh_m2_total": site.intensity_kwh_m2_total,
            "intensity_kwh_m2_tertiaire": site.intensity_kwh_m2_tertiaire,
            "altitude_m": site.altitude_m,
            "operat_sous_categorie_id": site.operat_sous_categorie_id,
        }

        site.annual_kwh_total = 100_000
        site.surface_m2 = 1000
        site.tertiaire_area_m2 = 500
        if site.altitude_m is None:
            site.altitude_m = 35
        if not site.operat_sous_categorie_id:
            site.operat_sous_categorie_id = "Bureaux - Bureaux Standards (cloisonnés - attribués)"
        db.commit()

        yield site, db
    finally:
        if site_id is not None and snapshot:
            try:
                site = db.query(Site).filter(Site.id == site_id).first()
                if site:
                    for field, value in snapshot.items():
                        setattr(site, field, value)
                    db.commit()
            except Exception:
                db.rollback()
        db.close()


def test_cascade_annual_kwh_change_triggers_both_intensities(site_with_data):
    """Cascade `Site.annual_kwh_total` → recalcule intensity_total ET intensity_tertiaire."""
    from regops.services.cascade_recompute_service import cascade_recompute_on_change

    site, db = site_with_data

    # Modifier annual_kwh puis cascade
    site.annual_kwh_total = 250_000
    db.flush()

    result = cascade_recompute_on_change(
        db,
        site,
        "Site.annual_kwh_total",
        old_value=100_000,
        new_value=250_000,
        persist=True,
        org_id=999_200,
    )

    output_fields = {a.output_field for a in result.actions}
    assert "intensity_kwh_m2_total" in output_fields
    assert "intensity_kwh_m2_tertiaire" in output_fields

    # Persistance : 250000 / 1000 = 250.0 ; 250000 / 500 = 500.0
    db.refresh(site)
    assert site.intensity_kwh_m2_total == 250.0
    assert site.intensity_kwh_m2_tertiaire == 500.0


def test_cascade_surface_m2_change_triggers_intensity_total_only(site_with_data):
    """Cascade `Site.surface_m2` → recalcule UNIQUEMENT intensity_total (pas tertiaire)."""
    from regops.services.cascade_recompute_service import cascade_recompute_on_change

    site, db = site_with_data

    site.surface_m2 = 2000
    db.flush()

    result = cascade_recompute_on_change(
        db,
        site,
        "Site.surface_m2",
        old_value=1000,
        new_value=2000,
        persist=True,
        org_id=999_201,
    )

    output_fields = {a.output_field for a in result.actions}
    assert "intensity_kwh_m2_total" in output_fields
    assert "intensity_kwh_m2_tertiaire" not in output_fields

    # 100000 / 2000 = 50.0
    db.refresh(site)
    assert site.intensity_kwh_m2_total == 50.0


def test_cascade_tertiaire_area_change_triggers_intensity_tertiaire_and_compliance(site_with_data):
    """Cascade `Site.tertiaire_area_m2` → recalcule intensity_tertiaire + compliance_score (existant)."""
    from regops.services.cascade_recompute_service import cascade_recompute_on_change

    site, db = site_with_data

    site.tertiaire_area_m2 = 250
    db.flush()

    result = cascade_recompute_on_change(
        db,
        site,
        "Site.tertiaire_area_m2",
        old_value=500,
        new_value=250,
        persist=True,
        org_id=999_202,
    )

    output_fields = {a.output_field for a in result.actions}
    # Phase 4.2 : intensity_tertiaire ajoutée
    assert "intensity_kwh_m2_tertiaire" in output_fields
    # Phase 6 Sprint C-1 : compliance_score préservé (anti-régression)
    assert "compliance_score" in output_fields

    # 100000 / 250 = 400.0
    db.refresh(site)
    assert site.intensity_kwh_m2_tertiaire == 400.0
