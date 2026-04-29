"""
PROMEOS — Tests Phase 1.1 : EurAmount typé + traçabilité (Décision A §0.D).

Source-guards :
  - test_eur_amount_typed : endpoint proof retourne contrat typé
  - test_eur_amount_traceability : DB insertion respecte CheckConstraint
  - test_no_modeled_eur_amount : seules 2 catégories canoniques

Couverture service :
  - build_regulatory() happy + erreurs (article vide, formula vide)
  - build_contractual() happy + 404 contract_id introuvable + formula vide
  - to_dict_with_proof() contrat de réponse complet
  - Endpoint /api/cockpit/eur_amount/{id}/proof 200 + 404
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from main import app
from models.billing_models import EnergyContract
from models.eur_amount import EurAmount, EurAmountCategory
from services.eur_amount_service import (
    build_contractual,
    build_regulatory,
    to_dict_with_proof,
)

HEADERS = {"X-Org-Id": "1"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture()
def db():
    """Session DB nettoyée des EurAmount créés pendant le test."""
    session = SessionLocal()
    created_ids: list[int] = []
    try:
        yield session, created_ids
    finally:
        for eur_id in created_ids:
            obj = session.query(EurAmount).filter(EurAmount.id == eur_id).first()
            if obj:
                session.delete(obj)
        session.commit()
        session.close()


# ── EurAmountCategory enum canonical ────────────────────────────────────────


class TestEurAmountCategory:
    def test_only_two_canonical_categories(self):
        """Doctrine §0.D : seules 2 catégories autorisées (no modeled/estimated)."""
        values = {c.value for c in EurAmountCategory}
        assert values == {"calculated_regulatory", "calculated_contractual"}

    def test_no_modeled_or_estimated_keyword(self):
        """Anti-pattern : aucune catégorie ne mentionne modeled ou estimated."""
        for cat in EurAmountCategory:
            assert "modeled" not in cat.value
            assert "estimated" not in cat.value


# ── build_regulatory() ──────────────────────────────────────────────────────


class TestBuildRegulatory:
    def test_happy_path_persists(self, db):
        session, created_ids = db
        eur = build_regulatory(
            session,
            value_eur=7500.0,
            regulatory_article="Décret 2019-771 art. 9",
            formula_text="1 site non conforme × 7500 €",
        )
        session.commit()
        created_ids.append(eur.id)

        assert eur.id is not None
        assert eur.value_eur == 7500.0
        assert eur.category == EurAmountCategory.CALCULATED_REGULATORY
        assert eur.regulatory_article == "Décret 2019-771 art. 9"
        assert eur.contract_id is None
        assert "7500" in eur.formula_text

    def test_strips_whitespace(self, db):
        session, created_ids = db
        eur = build_regulatory(
            session,
            value_eur=1500.0,
            regulatory_article="  Décret 2020-887  ",
            formula_text="  1 site BACS × 1500 €  ",
        )
        session.commit()
        created_ids.append(eur.id)

        assert eur.regulatory_article == "Décret 2020-887"
        assert eur.formula_text == "1 site BACS × 1500 €"

    def test_raises_on_empty_article(self, db):
        session, _ = db
        with pytest.raises(ValueError, match="regulatory_article"):
            build_regulatory(session, value_eur=100.0, regulatory_article="", formula_text="x")

    def test_raises_on_whitespace_article(self, db):
        session, _ = db
        with pytest.raises(ValueError, match="regulatory_article"):
            build_regulatory(session, value_eur=100.0, regulatory_article="   ", formula_text="x")

    def test_raises_on_empty_formula(self, db):
        session, _ = db
        with pytest.raises(ValueError, match="formula_text"):
            build_regulatory(
                session,
                value_eur=100.0,
                regulatory_article="Décret 2019-771 art. 9",
                formula_text="",
            )


# ── build_contractual() ─────────────────────────────────────────────────────


class TestBuildContractual:
    def test_happy_path_with_existing_contract(self, db):
        session, created_ids = db
        contract = session.query(EnergyContract).first()
        if contract is None:
            pytest.skip("Aucun EnergyContract en DB — seed requis")

        eur = build_contractual(
            session,
            value_eur=3200.0,
            contract_id=contract.id,
            formula_text="12 mois × 266,67 €/mois",
        )
        session.commit()
        created_ids.append(eur.id)

        assert eur.id is not None
        assert eur.value_eur == 3200.0
        assert eur.category == EurAmountCategory.CALCULATED_CONTRACTUAL
        assert eur.regulatory_article is None
        assert eur.contract_id == contract.id
        assert "266,67" in eur.formula_text

    def test_raises_404_on_missing_contract(self, db):
        session, _ = db
        with pytest.raises(HTTPException) as exc:
            build_contractual(
                session,
                value_eur=100.0,
                contract_id=999_999_999,
                formula_text="dummy",
            )
        assert exc.value.status_code == 404
        assert "999999999" in exc.value.detail or "999_999_999" in exc.value.detail

    def test_raises_on_empty_formula(self, db):
        session, _ = db
        with pytest.raises(ValueError, match="formula_text"):
            build_contractual(session, value_eur=100.0, contract_id=1, formula_text="")


# ── to_dict_with_proof() ────────────────────────────────────────────────────


class TestToDictWithProof:
    def test_returns_all_canonical_fields(self, db):
        session, created_ids = db
        eur = build_regulatory(
            session,
            value_eur=7500.0,
            regulatory_article="Décret 2019-771 art. 9",
            formula_text="1 × 7500 €",
        )
        session.commit()
        created_ids.append(eur.id)

        d = to_dict_with_proof(eur)
        assert set(d.keys()) == {
            "id",
            "value_eur",
            "category",
            "regulatory_article",
            "contract_id",
            "formula_text",
            "computed_at",
            "proof_url",
        }
        assert d["category"] == "calculated_regulatory"
        assert d["proof_url"] == f"/api/cockpit/eur_amount/{eur.id}/proof"

    def test_computed_at_is_iso_string(self, db):
        session, created_ids = db
        eur = build_regulatory(session, value_eur=100.0, regulatory_article="X", formula_text="y")
        session.commit()
        created_ids.append(eur.id)

        d = to_dict_with_proof(eur)
        assert isinstance(d["computed_at"], str)
        assert "T" in d["computed_at"]  # ISO format datetime


# ── CheckConstraint DB enforcement ──────────────────────────────────────────


class TestCheckConstraint:
    def test_regulatory_without_article_raises_integrity(self, db):
        """Insertion directe (bypass service) doit lever IntegrityError."""
        session, _ = db
        bad = EurAmount(
            value_eur=100.0,
            category=EurAmountCategory.CALCULATED_REGULATORY,
            regulatory_article=None,
            contract_id=None,
            formula_text="invalid",
        )
        session.add(bad)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_contractual_without_contract_id_raises_integrity(self, db):
        session, _ = db
        bad = EurAmount(
            value_eur=100.0,
            category=EurAmountCategory.CALCULATED_CONTRACTUAL,
            regulatory_article=None,
            contract_id=None,
            formula_text="invalid",
        )
        session.add(bad)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


# ── Endpoint /api/cockpit/eur_amount/{id}/proof ────────────────────────────


class TestEurAmountProofEndpoint:
    def test_404_on_missing_id(self, client):
        response = client.get("/api/cockpit/eur_amount/999999999/proof", headers=HEADERS)
        assert response.status_code == 404

    def test_200_returns_proof(self, client, db):
        session, created_ids = db
        eur = build_regulatory(
            session,
            value_eur=7500.0,
            regulatory_article="Décret 2019-771 art. 9",
            formula_text="1 × 7500 €",
        )
        session.commit()
        created_ids.append(eur.id)

        response = client.get(f"/api/cockpit/eur_amount/{eur.id}/proof", headers=HEADERS)
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == eur.id
        assert body["value_eur"] == 7500.0
        assert body["category"] == "calculated_regulatory"
        assert body["regulatory_article"] == "Décret 2019-771 art. 9"
        assert body["proof_url"] == f"/api/cockpit/eur_amount/{eur.id}/proof"


# ── Source-guards prompt §2.B ───────────────────────────────────────────────


class TestSourceGuards:
    def test_eur_amount_typed_endpoint_contract(self, client, db):
        """Source-guard : endpoint proof expose category + traceability fields."""
        session, created_ids = db
        eur = build_regulatory(session, value_eur=100.0, regulatory_article="Decret X", formula_text="y")
        session.commit()
        created_ids.append(eur.id)

        response = client.get(f"/api/cockpit/eur_amount/{eur.id}/proof", headers=HEADERS)
        body = response.json()
        # Le contrat exige category + traceability + formula explicite
        assert "category" in body
        assert "regulatory_article" in body or "contract_id" in body
        assert "formula_text" in body

    def test_eur_amount_traceability_db_invariant(self, db):
        """Source-guard : tous les EurAmount en DB respectent la traçabilité."""
        session, _ = db
        all_eurs = session.query(EurAmount).all()
        for eur in all_eurs:
            if eur.category == EurAmountCategory.CALCULATED_REGULATORY:
                assert eur.regulatory_article is not None, f"EurAmount id={eur.id} regulatory sans article — viole §0.D"
            elif eur.category == EurAmountCategory.CALCULATED_CONTRACTUAL:
                assert eur.contract_id is not None, f"EurAmount id={eur.id} contractuel sans contract_id — viole §0.D"

    def test_no_modeled_eur_amount(self, db):
        """Source-guard : aucune entrée DB avec category hors enum canonique."""
        session, _ = db
        all_eurs = session.query(EurAmount).all()
        canonical = {c.value for c in EurAmountCategory}
        for eur in all_eurs:
            cat_value = eur.category.value if hasattr(eur.category, "value") else str(eur.category)
            assert cat_value in canonical, f"EurAmount id={eur.id} category={cat_value} hors-doctrine"

    def test_models_file_no_modeled_estimated_keyword(self):
        """Source-guard statique : le fichier modèle ne mentionne pas modeled/estimated."""
        model_path = Path(__file__).resolve().parent.parent / "models" / "eur_amount.py"
        src = model_path.read_text()
        # Tolérance dans les commentaires/docstrings (qui mentionnent l'interdiction)
        # mais pas dans le code Enum lui-même
        # Pattern : pas de "MODELED = " ni "ESTIMATED = " dans Enum
        assert "MODELED = " not in src
        assert "ESTIMATED = " not in src
