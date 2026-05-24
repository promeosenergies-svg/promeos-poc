"""
PROMEOS — Bill Intelligence P1 C7 (2026-05-24) :
`billing_explainability.compute_contributors` doit produire des labels et
explications **énergie-aware** (élec = TURPE, gaz = ATRD+ATRT).

Bug racine signalé live par le user : une facture GAZ s'auditait avec
un label "Réseau (TURPE)" — doctrinalement impossible (TURPE = élec uniquement).

Cas couverts :
- Facture élec → label "Réseau (TURPE)" + accise "CSPE/TICFE"
- Facture gaz → label "Acheminement (ATRD + ATRT)" + accise "TICGN"
- energy_type absent (rétro-compat pre-P1) → défaut élec
- Energy_type case-insensitive (GAZ / gaz / Gas)
- Fourniture explication adaptée ("gaz" vs "énergie")
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.billing_explainability import (  # noqa: E402
    _LABELS_ELEC,
    _LABELS_GAZ,
    compute_contributors,
)


def _make_metrics(energy_type: str | None, *, delta_reseau: float = 100.0):
    """Helper : construit un dict metrics avec écart sur la composante réseau."""
    return {
        "energy_type": energy_type,
        "delta_ttc": delta_reseau + 50.0,  # cohérent
        "delta_fourniture": 30.0,
        "delta_reseau": delta_reseau,
        "delta_taxes": 20.0,
        "price_ref": 0.15,
    }


# ─── Élec : label "Réseau (TURPE)" + accise CSPE/TICFE ──────────────────


def test_elec_invoice_uses_turpe_label():
    """Facture élec → label 'Réseau (TURPE)' + accise 'CSPE/TICFE'."""
    metrics = _make_metrics("ELEC", delta_reseau=100.0)
    contributors = compute_contributors(metrics)
    # Trouver la composante "reseau"
    reseau = next(c for c in contributors if c["code"] == "reseau")
    assert reseau["label"] == "Réseau (TURPE)"
    assert reseau["explanation_fr"] == "Coût réseau supérieur au TURPE attendu"
    assert reseau["energy_type"] == "ELEC"

    taxes = next(c for c in contributors if c["code"] == "taxes")
    assert "CSPE" in taxes["label"] and "TICFE" in taxes["label"]
    assert "CSPE/TICFE" in taxes["explanation_fr"]


# ─── Gaz : label "Acheminement (ATRD + ATRT)" + accise TICGN ────────────


def test_gaz_invoice_uses_atrd_atrt_label():
    """Facture gaz → label 'Acheminement (ATRD + ATRT)' + accise 'TICGN' — JAMAIS TURPE."""
    metrics = _make_metrics("GAZ", delta_reseau=150.0)
    contributors = compute_contributors(metrics)

    reseau = next(c for c in contributors if c["code"] == "reseau")
    assert reseau["label"] == "Acheminement (ATRD + ATRT)"
    assert "ATRD" in reseau["explanation_fr"] and "ATRT" in reseau["explanation_fr"]
    assert "TURPE" not in reseau["explanation_fr"], (
        "BUG DOCTRINAL : TURPE ne doit jamais apparaître sur une facture gaz"
    )
    assert reseau["energy_type"] == "GAZ"

    taxes = next(c for c in contributors if c["code"] == "taxes")
    assert "TICGN" in taxes["label"]
    assert "TICGN" in taxes["explanation_fr"]
    assert "CSPE" not in taxes["explanation_fr"]


def test_gaz_lowercase_also_recognized():
    """Case-insensitive : 'gaz', 'Gas', 'GAZ_NATUREL' tous acceptés."""
    for v in ("gaz", "Gaz", "GAZ", "Gas", "gaz_naturel", "GAZ_NATUREL"):
        metrics = _make_metrics(v, delta_reseau=100.0)
        contributors = compute_contributors(metrics)
        reseau = next(c for c in contributors if c["code"] == "reseau")
        assert "ATRD" in reseau["label"], f"Échec pour energy_type={v!r}"
        assert "TURPE" not in reseau["label"], f"BUG : label TURPE pour energy_type={v!r}"


def test_gaz_fourniture_label_says_gaz():
    """Pour gaz, l'explication fourniture dit 'gaz' (pas 'énergie' générique)."""
    metrics = _make_metrics("GAZ", delta_reseau=50.0)
    contributors = compute_contributors(metrics)
    fourniture = next(c for c in contributors if c["code"] == "fourniture")
    assert fourniture["label"] == "Fourniture de gaz"
    assert "gaz" in fourniture["explanation_fr"].lower()


# ─── Énergie absente : défaut élec (rétro-compat) ──────────────────────


def test_missing_energy_type_defaults_to_elec():
    """`energy_type` absent → défaut élec (rétro-compat pré-P1)."""
    metrics = _make_metrics(None, delta_reseau=100.0)
    contributors = compute_contributors(metrics)
    reseau = next(c for c in contributors if c["code"] == "reseau")
    assert reseau["label"] == "Réseau (TURPE)"


# ─── Sanity : pas de breakdown si delta_ttc = 0 ────────────────────────


def test_zero_delta_returns_empty():
    """Pas de contributeurs si pas d'écart total."""
    metrics = {"energy_type": "GAZ", "delta_ttc": 0}
    assert compute_contributors(metrics) == []


# ─── Sanity : LABELS_ELEC et LABELS_GAZ sont disjoints ─────────────────


def test_labels_dicts_have_required_keys():
    """Les 2 mappings doivent avoir les 4 clés (fourniture/reseau/taxes/abonnement)."""
    expected_keys = {"fourniture", "reseau", "taxes", "abonnement"}
    assert set(_LABELS_ELEC.keys()) == expected_keys
    assert set(_LABELS_GAZ.keys()) == expected_keys
    # Les labels réseau doivent être différents (TURPE vs ATRD/ATRT)
    assert _LABELS_ELEC["reseau"] != _LABELS_GAZ["reseau"]
    assert "TURPE" in _LABELS_ELEC["reseau"]
    assert "ATRD" in _LABELS_GAZ["reseau"]
