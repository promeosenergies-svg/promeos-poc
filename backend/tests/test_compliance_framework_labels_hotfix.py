"""
Hotfix 2026-05-24 — Labels FR canoniques des frameworks réglementaires.

Couvre :
1. `get_framework_label_fr()` retourne le label FR pour chaque framework
   V2 adaptatif (DT, BACS, APER, audit_sme, iso_50001, solar_toiture, beges).
2. Un framework inconnu retourne le code brut (PAS un label métier faux
   comme "APER" — c'était le bug pré-hotfix côté FE).
3. `FrameworkScore.to_dict()` enrichit chaque entrée breakdown avec `label_fr`.
4. `compute_portfolio_compliance()` retourne `breakdown_avg_labeled` (liste
   typée) en plus de `breakdown_avg` (dict legacy rétro-compat).
5. L'endpoint `/api/compliance/portfolio/score` expose `breakdown_avg_labeled`.
"""

from __future__ import annotations

import os
import sys
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402
from main import app  # noqa: E402
from models import Base, EntiteJuridique, Organisation, Portefeuille, Site, TypeSite  # noqa: E402
from services.compliance_score_service import (  # noqa: E402
    FRAMEWORK_LABELS_FR,
    FrameworkScore,
    compute_portfolio_compliance,
    get_framework_label_fr,
)


# ─── 1. get_framework_label_fr — exhaustivité + fallback ──────────────


class TestGetFrameworkLabelFr:
    """SoT backend des labels FR — pas de fallback métier faux."""

    def test_tertiaire_operat(self):
        assert get_framework_label_fr("tertiaire_operat") == "Décret Tertiaire"

    def test_bacs(self):
        assert get_framework_label_fr("bacs") == "BACS"

    def test_aper(self):
        assert get_framework_label_fr("aper") == "APER"

    def test_audit_sme(self):
        # Cœur du bug pré-hotfix : audit_sme s'affichait "APER" côté FE.
        assert get_framework_label_fr("audit_sme") == "Audit SMÉ"

    def test_iso_50001(self):
        assert get_framework_label_fr("iso_50001") == "ISO 50001"

    def test_solar_toiture(self):
        # 2e victime du bug pré-hotfix — étiqueté "APER" alors qu'il s'agit
        # de l'obligation de solarisation des toitures.
        assert get_framework_label_fr("solar_toiture") == "Solarisation toiture"

    def test_beges_futur(self):
        # BEGES n'est pas encore dans V2 mais doit être couvert pour éviter
        # une régression dès que l'évaluateur sera activé.
        assert get_framework_label_fr("beges") == "BEGES"

    def test_unknown_framework_returns_code(self):
        # Garde-fou cardinal : un framework inconnu NE DOIT JAMAIS retourner
        # un label métier existant (DT/BACS/APER). Il retourne le code brut.
        result = get_framework_label_fr("framework_inexistant_2030")
        assert result == "framework_inexistant_2030"
        assert result != "APER"  # exactement le bug pré-hotfix
        assert result != "BACS"
        assert result != "Décret Tertiaire"

    def test_dict_has_all_v2_frameworks(self):
        # Les 6 frameworks de _compute_v2_adaptive + BEGES (futur) = 7.
        expected = {
            "tertiaire_operat",
            "bacs",
            "aper",
            "audit_sme",
            "iso_50001",
            "solar_toiture",
            "beges",
        }
        assert expected.issubset(set(FRAMEWORK_LABELS_FR.keys()))


# ─── 2. FrameworkScore.to_dict() — label_fr injecté ──────────────────


class TestFrameworkScoreToDict:
    """Chaque entrée breakdown contient label_fr."""

    def test_breakdown_entries_have_label_fr(self):
        from services.compliance_score_service import ComplianceScoreResult

        result = ComplianceScoreResult(
            score=70.0,
            breakdown=[
                FrameworkScore(framework="audit_sme", score=0.0, weight=0.15, available=True, source="v2_adaptive"),
                FrameworkScore(
                    framework="solar_toiture", score=50.0, weight=0.10, available=True, source="v2_adaptive"
                ),
            ],
        )
        d = result.to_dict()
        labels = {e["framework"]: e["label_fr"] for e in d["breakdown"]}
        assert labels["audit_sme"] == "Audit SMÉ"
        assert labels["solar_toiture"] == "Solarisation toiture"

    def test_breakdown_preserves_score_and_weight(self):
        from services.compliance_score_service import ComplianceScoreResult

        result = ComplianceScoreResult(
            score=42.0,
            breakdown=[
                FrameworkScore(framework="iso_50001", score=33.3, weight=0.25, available=True, source="v2_adaptive"),
            ],
        )
        d = result.to_dict()
        entry = d["breakdown"][0]
        assert entry["framework"] == "iso_50001"
        assert entry["label_fr"] == "ISO 50001"
        assert entry["score"] == 33.3
        assert entry["weight"] == 0.25


# ─── 3. compute_portfolio_compliance + endpoint live ──────────────────


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_org_with_site(db):
    """Crée 1 org + 1 EJ + 1 PF + 1 site assujetti à 3 obligations
    (suffit pour avoir un breakdown non vide)."""
    org = Organisation(nom="Org Hotfix", siren="999999999", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="999999999")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site Hotfix",
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        actif=True,
        surface_m2=1500.0,  # > 1000 → DT assujetti
        aper_assujetti=True,
    )
    db.add(site)
    db.commit()
    return org, site


class TestPortfolioBreakdownLabeled:
    """compute_portfolio_compliance ajoute breakdown_avg_labeled."""

    def test_payload_contains_breakdown_avg_labeled(self, db):
        org, _ = _seed_org_with_site(db)
        result = compute_portfolio_compliance(db, org.id)
        # Le champ existe et est une liste
        assert "breakdown_avg_labeled" in result
        assert isinstance(result["breakdown_avg_labeled"], list)
        # Rétro-compat : l'ancien champ dict est conservé
        assert "breakdown_avg" in result
        assert isinstance(result["breakdown_avg"], dict)

    def test_each_labeled_entry_has_framework_label_fr_score(self, db):
        org, _ = _seed_org_with_site(db)
        result = compute_portfolio_compliance(db, org.id)
        for entry in result["breakdown_avg_labeled"]:
            assert "framework" in entry
            assert "label_fr" in entry
            assert "score" in entry
            # Le label n'est jamais vide
            assert entry["label_fr"] and isinstance(entry["label_fr"], str)
            # Le label correspond au mapping FRAMEWORK_LABELS_FR
            assert entry["label_fr"] == get_framework_label_fr(entry["framework"])

    def test_audit_sme_never_labeled_as_aper(self, db):
        # Régression cardinale : si un site assujetti à audit_sme est
        # présent, son label DOIT être "Audit SMÉ" — JAMAIS "APER".
        org, site = _seed_org_with_site(db)
        # Force audit_sme assujetti via models.audit_sme s'il existe
        # (sinon le test se contente de vérifier qu'AUCUNE entrée APER
        # n'apparaît pour un code non-aper).
        result = compute_portfolio_compliance(db, org.id)
        for entry in result["breakdown_avg_labeled"]:
            if entry["framework"] != "aper":
                assert entry["label_fr"] != "APER", f"Régression : framework={entry['framework']} étiqueté 'APER'"


class TestPortfolioScoreEndpoint:
    """GET /api/compliance/portfolio/score expose breakdown_avg_labeled."""

    def test_endpoint_returns_breakdown_avg_labeled(self, client, db):
        org, _ = _seed_org_with_site(db)
        r = client.get("/api/compliance/portfolio/score", headers={"X-Org-Id": str(org.id)})
        assert r.status_code == 200
        body = r.json()
        assert "breakdown_avg_labeled" in body
        assert isinstance(body["breakdown_avg_labeled"], list)
        # Chaque entrée a label_fr
        for entry in body["breakdown_avg_labeled"]:
            assert "label_fr" in entry
            assert entry["label_fr"]  # non vide

    def test_endpoint_aper_label_unique_when_only_aper(self, client, db):
        # Anti-régression visuelle : si UN seul framework APER existe, on
        # ne doit pas voir plusieurs labels "APER" (le bug FE pré-hotfix
        # affichait 3 lignes APER pour aper + audit_sme + solar_toiture).
        org, _ = _seed_org_with_site(db)
        r = client.get("/api/compliance/portfolio/score", headers={"X-Org-Id": str(org.id)})
        body = r.json()
        aper_labels = [e for e in body["breakdown_avg_labeled"] if e["label_fr"] == "APER"]
        # Au plus 1 entrée APER (puisque le mapping BE est 1:1 avec le code)
        assert len(aper_labels) <= 1
