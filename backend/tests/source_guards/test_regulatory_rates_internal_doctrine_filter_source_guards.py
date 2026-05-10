"""
PROMEOS — Source-guards Phase L33.2 — filtre internal_doctrine sur /api/regulatory/rates.

Reviewer #3 META-AUDIT L33.0 (security-auditor PERSONA TRÈS SÉVÈRE) a identifié
un P0 sécurité : les endpoints regulatory exposaient sans filtre les ~40 clés
`status: internal_doctrine` (BILL_ANOMALY_* heuristiques R19→R31, READINESS_WEIGHT_*,
REGOPS_WEIGHT_*, FLEX_HEURISTIC, etc.) — fuite de la doctrine PROMEOS Sol §15
qu'un concurrent (Deepki/Metron) pourrait reverse-engineer.

Patterns vérifiés :
- SG_REG_RATES_PUBLIC_01 : /api/regulatory/rates sans filtre exclut tous les
  termes status: internal_doctrine|internal_heuristic|internal_fallback.
- SG_REG_RATES_PUBLIC_02 : /api/regulatory/rates?domain=bill_intelligence
  retourne 0 terme (toutes internal_doctrine — domain entièrement masqué public).
- SG_REG_RATES_PUBLIC_03 : /api/regulatory/rates?term_id=BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR
  retourne 404 (term internal_doctrine — refus exposition).
- SG_REG_RATES_PUBLIC_04 : /api/regulatory/rates?term_id=ACCISE_ELEC_T1_EUR_PER_MWH
  retourne 200 (term verified — exposition autorisée).
- SG_REG_RATES_PUBLIC_05 : cache lru_cache loader non muté (anti-régression bug
  Phase L33.2 où le filtre mutait le cache partagé).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from main import app

    return TestClient(app)


_INTERNAL_STATUSES = frozenset({"internal_doctrine", "internal_heuristic", "internal_fallback"})


# ─── SG_REG_RATES_PUBLIC_01 : exclusion globale internal_doctrine ───────────


def test_sg_reg_rates_public_01_no_internal_doctrine_in_full_response(client):
    """Phase L33.2 audit fix P0 SECURITY — /api/regulatory/rates sans filtre
    NE DOIT PAS exposer les termes status: internal_doctrine|heuristic|fallback.

    Sinon : fuite doctrine PROMEOS Sol §15 (BILL_ANOMALY heuristiques R19→R31)
    accessible publiquement aux concurrents (Deepki/Metron).
    """
    resp = client.get("/api/regulatory/rates")
    assert resp.status_code == 200
    data = resp.json()
    terms = data.get("terms", {})

    leaked = [term_id for term_id, term in terms.items() if term.get("status") in _INTERNAL_STATUSES]
    assert not leaked, (
        f"Fuite doctrine PROMEOS interne via /api/regulatory/rates : "
        f"{len(leaked)} termes internal_* exposés publiquement :\n  - " + "\n  - ".join(leaked[:10])
    )


# ─── SG_REG_RATES_PUBLIC_02 : domain=bill_intelligence masqué ───────────────


def test_sg_reg_rates_public_02_bill_intelligence_domain_empty_public(client):
    """Phase L33.2 — domain=bill_intelligence retourne 0 terme (toutes internal_doctrine)."""
    resp = client.get("/api/regulatory/rates", params={"domain": "bill_intelligence"})
    # 200 OK avec terms vide (filtre laisse passer le domain mais filtre les termes)
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "bill_intelligence"
    assert len(data["terms"]) == 0, (
        f"Fuite doctrine — domain=bill_intelligence devrait être 0 termes publics, "
        f"reçu {len(data['terms'])}: {list(data['terms'].keys())[:5]}"
    )


# ─── SG_REG_RATES_PUBLIC_03 : term_id internal_doctrine refusé ──────────────


def test_sg_reg_rates_public_03_internal_doctrine_term_404(client):
    """Phase L33.2 — term_id explicite avec status internal_doctrine retourne 404."""
    resp = client.get(
        "/api/regulatory/rates",
        params={"term_id": "BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR"},
    )
    assert resp.status_code == 404, (
        f"Fuite doctrine — BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR (internal_doctrine) "
        f"NE DOIT PAS être exposé via /api/regulatory/rates?term_id=... (statut {resp.status_code})"
    )


# ─── SG_REG_RATES_PUBLIC_04 : term_id verified autorisé ─────────────────────


def test_sg_reg_rates_public_04_verified_term_200(client):
    """Phase L33.2 — term_id status verified (ACCISE_ELEC_T1) retourne 200 (filtre n'over-bloque pas)."""
    resp = client.get(
        "/api/regulatory/rates",
        params={"term_id": "ACCISE_ELEC_T1_EUR_PER_MWH"},
    )
    assert resp.status_code == 200, (
        f"Régression filtre L33.2 — ACCISE_ELEC_T1_EUR_PER_MWH (verified) "
        f"DOIT être exposé via /api/regulatory/rates (reçu {resp.status_code})"
    )
    data = resp.json()
    assert data["term"]["value"] == 30.85


# ─── SG_REG_RATES_PUBLIC_05 : cache lru_cache non muté (anti-régression) ────


def test_sg_reg_rates_public_05_cache_not_mutated(client):
    """Phase L33.2 audit fix CRITICAL — anti-régression du bug initial où le filtre
    mutait le cache lru_cache partagé. Vérifie que list_all_domains() retourne
    toujours les 12 domaines complets après un appel à /api/regulatory/rates.
    """
    # Appel d'abord /api/regulatory/rates (qui filtre)
    client.get("/api/regulatory/rates")

    # Puis vérifier que le cache loader n'a pas été muté : les 12 domaines doivent rester
    from config.regulatory_sources_loader import list_all_domains

    domains = list_all_domains()
    expected_domains = {
        "co2",
        "tarifs",
        "accises",
        "tva",
        "dt",
        "bacs",
        "aper",
        "audit_sme",
        "operat",
        "regops",
        "readiness",
        "bill_intelligence",
    }
    assert set(domains) == expected_domains, (
        f"Cache lru_cache muté par le filtre Phase L33.2 — domains attendus "
        f"{sorted(expected_domains)}, reçus {sorted(domains)}"
    )
