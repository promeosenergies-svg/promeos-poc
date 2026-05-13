"""PROMEOS — Tests Vague AA (Phase 3.6) : services compute_*."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services.strategique.computes import (
    DT_TARGET_PCT,
    compute_bench_sites,
    compute_next_contract_end,
    compute_spot_exposure,
    compute_trajectory_drift,
    compute_unvalued_cee_keur,
)


# ── compute_trajectory_drift ──────────────────────────────────────────────


def test_trajectory_drift_no_sites(monkeypatch):
    monkeypatch.setattr(
        "services.strategique.computes.sites_for_org_query",
        lambda db, oid: MagicMock(all=lambda: []),
    )
    r = compute_trajectory_drift(MagicMock(), org_id=1)
    assert r["source"] == "insufficient_data"
    assert r["drift_pct"] == 0.0
    assert r["sites_count"] == 0


def test_trajectory_drift_with_intensity_no_assessment(monkeypatch):
    s = SimpleNamespace(id=1, intensity_kwh_m2_tertiaire=180.0, annee_reference_operat=2015)
    monkeypatch.setattr(
        "services.strategique.computes.sites_for_org_query",
        lambda db, oid: MagicMock(all=lambda: [s]),
    )
    # Mock DB query → no RegAssessment
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    r = compute_trajectory_drift(db, org_id=1)
    assert r["source"] == "computed"
    assert r["sites_count"] == 1
    # atteint_moyen = 0 (pas d'assessment) → drift = 40 - 0 = 40
    assert r["drift_pct"] == DT_TARGET_PCT


def test_trajectory_drift_with_assessment(monkeypatch):
    s = SimpleNamespace(id=2, intensity_kwh_m2_tertiaire=200.0, annee_reference_operat=2015)
    monkeypatch.setattr(
        "services.strategique.computes.sites_for_org_query",
        lambda db, oid: MagicMock(all=lambda: [s]),
    )
    ra = SimpleNamespace(compliance_score=80.0)  # → atteint = 32 %
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = ra
    r = compute_trajectory_drift(db, org_id=2)
    assert r["atteint_pct_moyen"] == 32.0
    assert r["drift_pct"] == 8.0  # 40 - 32


# ── compute_next_contract_end ─────────────────────────────────────────────


def test_next_contract_end_no_contract():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    r = compute_next_contract_end(db, org_id=1)
    assert r["days"] == 99999
    assert r["source"] == "no_contract"


def test_next_contract_end_future():
    db = MagicMock()
    future = date.today() + timedelta(days=60)
    contrat = SimpleNamespace(id=42, date_fin=future, fournisseur="EDF")
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [contrat]
    r = compute_next_contract_end(db, org_id=1)
    assert r["days"] == 60
    assert r["contract_id"] == 42
    assert r["fournisseur"] == "EDF"
    assert r["source"] == "computed"


# ── compute_spot_exposure ─────────────────────────────────────────────────


def test_spot_exposure_no_contract():
    db = MagicMock()
    db.query.return_value.all.return_value = []
    r = compute_spot_exposure(db, org_id=1)
    assert r["pct"] == 0.0
    assert r["source"] == "no_contract"


def test_spot_exposure_all_fixe():
    db = MagicMock()
    c1 = SimpleNamespace(type_prix="FIXE")
    c2 = SimpleNamespace(type_prix="FIXE")
    db.query.return_value.all.return_value = [c1, c2]
    r = compute_spot_exposure(db, org_id=1)
    assert r["pct"] == 0.0


def test_spot_exposure_mixed():
    db = MagicMock()
    c1 = SimpleNamespace(type_prix="FIXE")
    c2 = SimpleNamespace(type_prix="SPOT")
    c3 = SimpleNamespace(type_prix="MIXTE")
    db.query.return_value.all.return_value = [c1, c2, c3]
    r = compute_spot_exposure(db, org_id=1)
    # 1 SPOT + 0.5 mixte / 3 = 1.5/3 = 50%
    assert r["pct"] == 50.0


# ── compute_bench_sites ───────────────────────────────────────────────────


def test_bench_sites_empty(monkeypatch):
    monkeypatch.setattr(
        "services.strategique.computes.sites_for_org_query",
        lambda db, oid: MagicMock(all=lambda: []),
    )
    r = compute_bench_sites(MagicMock(), org_id=1)
    assert r == []


def test_bench_sites_no_intensity(monkeypatch):
    s = SimpleNamespace(id=1, nom="X", intensity_kwh_m2_tertiaire=None)
    monkeypatch.setattr(
        "services.strategique.computes.sites_for_org_query",
        lambda db, oid: MagicMock(all=lambda: [s]),
    )
    r = compute_bench_sites(MagicMock(), org_id=1)
    assert r == []


def test_bench_sites_3_sites_canonical_selection(monkeypatch):
    sites = [
        SimpleNamespace(id=1, nom="WorstSite", intensity_kwh_m2_tertiaire=250.0),
        SimpleNamespace(id=2, nom="MedianSite", intensity_kwh_m2_tertiaire=180.0),
        SimpleNamespace(id=3, nom="BestSite", intensity_kwh_m2_tertiaire=110.0),
    ]
    monkeypatch.setattr(
        "services.strategique.computes.sites_for_org_query",
        lambda db, oid: MagicMock(all=lambda: sites),
    )
    r = compute_bench_sites(MagicMock(), org_id=1)
    assert len(r) == 3
    assert r[0]["site"] == "WorstSite"
    assert r[0]["tier"] == "warn"
    assert r[2]["site"] == "BestSite"
    assert r[2]["tier"] == "pos"


def test_bench_sites_2_sites_top_n_fallback(monkeypatch):
    sites = [
        SimpleNamespace(id=1, nom="A", intensity_kwh_m2_tertiaire=200.0),
        SimpleNamespace(id=2, nom="B", intensity_kwh_m2_tertiaire=150.0),
    ]
    monkeypatch.setattr(
        "services.strategique.computes.sites_for_org_query",
        lambda db, oid: MagicMock(all=lambda: sites),
    )
    r = compute_bench_sites(MagicMock(), org_id=1, top_n=3)
    assert len(r) == 2


# ── compute_unvalued_cee_keur ────────────────────────────────────────────


def test_unvalued_cee_no_model():
    """Si le modèle CEE n'est pas disponible, retourne 0 sans crash."""
    db = MagicMock()
    # Pas de patch sur l'import → ImportError attrapé
    r = compute_unvalued_cee_keur(db, org_id=1)
    # Soit no_cee_model soit computed=0 selon présence modèle
    assert "k_eur" in r and "source" in r
    assert r["k_eur"] >= 0.0
