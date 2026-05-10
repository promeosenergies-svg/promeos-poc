"""
PROMEOS — Sprint C-3 Phase 3.3 : Tests endpoint GET /api/regulatory/rates.

Vérifie que l'endpoint expose correctement le SoT YAML
`backend/config/sources_reglementaires.yaml` au frontend (~68 termes /
9 domaines), avec les 3 modes :
- sans filtre : tout le YAML
- ?domain=... : filtre par domaine
- ?term_id=... : 1 seul terme

Endpoint public (pas d'org-scoping) — sources réglementaires françaises
accessibles à tous (cohérent avec /api/config/emission-factors).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


# ─── Mode 1 : sans filtre — tout le YAML ─────────────────────────────────────


def test_get_regulatory_rates_no_filter_returns_200():
    resp = client.get("/api/regulatory/rates")
    assert resp.status_code == 200


def test_get_regulatory_rates_no_filter_returns_full_yaml_structure():
    """Sans filtre : retourne version + last_updated + sprint_origin + terms."""
    resp = client.get("/api/regulatory/rates")
    data = resp.json()

    assert "version" in data
    assert "last_updated" in data
    assert "sprint_origin" in data
    assert "terms" in data
    assert isinstance(data["terms"], dict)


def test_get_regulatory_rates_no_filter_returns_at_least_60_terms():
    """Volumétrie cible Sprint C-3 ≥ 60 termes."""
    resp = client.get("/api/regulatory/rates")
    data = resp.json()
    assert len(data["terms"]) >= 60


# ─── Mode 2 : filtre par domaine ─────────────────────────────────────────────


def test_get_regulatory_rates_filter_by_domain_co2_returns_3_terms():
    """Phase L33.2 — domain co2 contient 5 termes post-L31.3+L32 (3 CO2_FACTOR + 2 CBAM)."""
    resp = client.get("/api/regulatory/rates", params={"domain": "co2"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["domain"] == "co2"
    assert "terms" in data
    assert len(data["terms"]) >= 3
    assert "CO2_FACTOR_ELEC_KGCO2_PER_KWH" in data["terms"]


def test_get_regulatory_rates_filter_by_domain_dt():
    resp = client.get("/api/regulatory/rates", params={"domain": "dt"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["domain"] == "dt"
    # 14 termes dt (cf. Phase 3.2 audit volumétrie)
    assert len(data["terms"]) >= 10


def test_get_regulatory_rates_unknown_domain_returns_404():
    resp = client.get("/api/regulatory/rates", params={"domain": "inexistant_xyz"})
    assert resp.status_code == 404
    # Global error handler transforme HTTPException.detail → {code, message, hint, correlation_id}
    body = resp.json()
    assert "Domaine inconnu" in body.get("message", "")
    assert body.get("code") == "NOT_FOUND"


# ─── Mode 3 : filtre par term_id ─────────────────────────────────────────────


def test_get_regulatory_rates_filter_by_term_id_returns_single_term():
    resp = client.get("/api/regulatory/rates", params={"term_id": "CO2_FACTOR_ELEC_KGCO2_PER_KWH"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["term_id"] == "CO2_FACTOR_ELEC_KGCO2_PER_KWH"
    assert "term" in data
    assert data["term"]["value"] == 0.052
    assert data["term"]["unit"] == "kgCO2e/kWh"
    assert data["term"]["domain"] == "co2"
    assert "source" in data["term"]


def test_get_regulatory_rates_unknown_term_id_returns_404():
    resp = client.get("/api/regulatory/rates", params={"term_id": "UNKNOWN_TERM_XYZ"})
    assert resp.status_code == 404
    # Global error handler : detail → {code, message, hint, correlation_id}
    body = resp.json()
    assert "UNKNOWN_TERM_XYZ" in body.get("message", "")


# ─── Endpoint public (pas d'org-scoping) ────────────────────────────────────


def test_get_regulatory_rates_no_authentication_required():
    """Endpoint public : pas de header Authorization ni X-Org-Id requis."""
    resp = client.get("/api/regulatory/rates")
    # Pas de 401/403 attendu — accessible sans auth
    assert resp.status_code == 200


# ─── Schema strict des réponses ──────────────────────────────────────────────


def test_get_regulatory_rates_each_term_has_source_url_https():
    """Anti-régression schema : chaque term.source.url commence par https://."""
    resp = client.get("/api/regulatory/rates")
    data = resp.json()

    offenders = []
    for tid, term in data["terms"].items():
        url = term.get("source", {}).get("url", "")
        if not url.startswith("https://"):
            offenders.append(f"{tid}: {url!r}")
    assert not offenders, "URL non-https détectée:\n  - " + "\n  - ".join(offenders)


def test_get_regulatory_rates_each_term_has_required_keys():
    """Anti-régression schema : value, unit, domain, source, formula, notes obligatoires."""
    resp = client.get("/api/regulatory/rates")
    data = resp.json()

    required = {"value", "unit", "domain", "source", "formula", "notes"}
    offenders = []
    for tid, term in data["terms"].items():
        missing = required - set(term.keys())
        if missing:
            offenders.append(f"{tid}: missing {sorted(missing)}")
    assert not offenders, "Termes mal structurés:\n  - " + "\n  - ".join(offenders)


# ─── Endpoint /api/regulatory/domains ────────────────────────────────────────


def test_get_regulatory_domains_returns_distinct_set():
    """Phase 3.4d → Phase L31.3 : 12 domaines distincts post bill_intelligence ajouté."""
    resp = client.get("/api/regulatory/domains")
    assert resp.status_code == 200
    data = resp.json()

    assert "domains" in data
    expected = {
        "co2",
        "tarifs",
        "accises",
        "tva",
        "dt",
        "bacs",
        "aper",
        "audit_sme",
        "operat",
        # Phase 3.4d audit follow-up
        "regops",
        "readiness",
        # Phase L31.3 — Bill Intelligence anomalies (R19→R31, ~30 clés internal_doctrine)
        "bill_intelligence",
    }
    assert set(data["domains"]) == expected
