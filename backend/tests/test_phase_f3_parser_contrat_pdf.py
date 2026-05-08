"""
PROMEOS — Phase F3 (ADR-F-03) : tests cardinaux parser contrat PDF.

8 tests T-CONTRACT-01 → T-CONTRACT-08 :
- Extraction supplier_name + SIREN (T-CONTRACT-01)
- Date signature (T-CONTRACT-02)
- start_date + end_date (T-CONTRACT-03)
- price_ref EUR/kWh (T-CONTRACT-04)
- fixed_fee EUR/mois (T-CONTRACT-05)
- reference_fournisseur (T-CONTRACT-06)
- Bridge Fournisseur F1 — fournisseur_id résolu (T-CONTRACT-07)
- Confidence score (T-CONTRACT-08)
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Fournisseur, TypeFournitureEnum


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _seed_canoniques(db):
    db.add_all(
        [
            Fournisseur(nom="EDF", siren="552081317", type_fourniture=TypeFournitureEnum.MULTI),
            Fournisseur(nom="ENGIE", siren="542107651", type_fourniture=TypeFournitureEnum.MULTI),
        ]
    )
    db.commit()


SAMPLE_CONTRACT_TEXT = """
EDF Entreprises
SIRET: 55208131700123

CONTRAT DE FOURNITURE D'ÉLECTRICITÉ

Fournisseur : EDF
N° contrat : EDF-2026-ABC123
Référence : CONT-9876

Fait le 15/03/2026
Date de début : 01/04/2026
Date de fin : 31/03/2029

Prix de référence : 0,1542 EUR/kWh
Abonnement : 35,80 EUR/mois

Clauses particulières...
"""


# ─── T-CONTRACT-01 : supplier_name + SIREN ──────────────────────────────────


def test_t_contract_01_supplier_name_and_siren():
    """T-CONTRACT-01 : extraction supplier_name (header) + SIREN via SIRET."""
    from services.contract_pdf_parser import parse_contract_pdf_text

    result = parse_contract_pdf_text(SAMPLE_CONTRACT_TEXT)
    assert result.supplier_name is not None
    assert "EDF" in (result.supplier_name or "")
    assert result.siren_extracted == "552081317"


# ─── T-CONTRACT-02 : date_signature ─────────────────────────────────────────


def test_t_contract_02_date_signature():
    """T-CONTRACT-02 : extraction date signature DD/MM/YYYY."""
    from services.contract_pdf_parser import parse_contract_pdf_text

    result = parse_contract_pdf_text(SAMPLE_CONTRACT_TEXT)
    assert result.date_signature == date(2026, 3, 15)


# ─── T-CONTRACT-03 : start_date + end_date ──────────────────────────────────


def test_t_contract_03_start_end_date():
    """T-CONTRACT-03 : extraction période contractuelle."""
    from services.contract_pdf_parser import parse_contract_pdf_text

    result = parse_contract_pdf_text(SAMPLE_CONTRACT_TEXT)
    assert result.start_date == date(2026, 4, 1)
    assert result.end_date == date(2029, 3, 31)


# ─── T-CONTRACT-04 : price_ref EUR/kWh ──────────────────────────────────────


def test_t_contract_04_price_ref_eur_kwh():
    """T-CONTRACT-04 : extraction prix référence EUR/kWh."""
    from services.contract_pdf_parser import parse_contract_pdf_text

    result = parse_contract_pdf_text(SAMPLE_CONTRACT_TEXT)
    assert result.price_ref_eur_per_kwh is not None
    assert abs(result.price_ref_eur_per_kwh - 0.1542) < 1e-6


# ─── T-CONTRACT-05 : fixed_fee EUR/mois ─────────────────────────────────────


def test_t_contract_05_fixed_fee_eur_per_month():
    """T-CONTRACT-05 : extraction abonnement EUR/mois."""
    from services.contract_pdf_parser import parse_contract_pdf_text

    result = parse_contract_pdf_text(SAMPLE_CONTRACT_TEXT)
    assert result.fixed_fee_eur_per_month is not None
    assert abs(result.fixed_fee_eur_per_month - 35.80) < 1e-6


# ─── T-CONTRACT-06 : reference_fournisseur ──────────────────────────────────


def test_t_contract_06_reference_fournisseur():
    """T-CONTRACT-06 : extraction numéro contrat fournisseur."""
    from services.contract_pdf_parser import parse_contract_pdf_text

    result = parse_contract_pdf_text(SAMPLE_CONTRACT_TEXT)
    assert result.reference_fournisseur is not None
    assert "EDF-2026-ABC123" in result.reference_fournisseur


# ─── T-CONTRACT-07 : Bridge Fournisseur F1 ──────────────────────────────────


def test_t_contract_07_bridge_fournisseur_f1(db):
    """T-CONTRACT-07 : SIREN extrait → résolution Fournisseur canonique."""
    from services.contract_pdf_parser import parse_contract_pdf_text

    _seed_canoniques(db)
    result = parse_contract_pdf_text(SAMPLE_CONTRACT_TEXT, db=db)
    assert result.fournisseur_id is not None
    assert result.fournisseur_nom_canonique == "EDF"


# ─── T-CONTRACT-08 : Confidence score ───────────────────────────────────────


def test_t_contract_08_confidence_score():
    """T-CONTRACT-08 : confidence >= 0.5 si 4+ champs cardinaux extraits."""
    from services.contract_pdf_parser import parse_contract_pdf_text

    result = parse_contract_pdf_text(SAMPLE_CONTRACT_TEXT)
    # Sample contient supplier + siren + signature + start + end + price + fee + ref = 8/8
    assert result.confidence >= 0.5
    assert len(result.fields_extracted) >= 4


def test_t_contract_08bis_low_confidence_empty_pdf():
    """T-CONTRACT-08bis : PDF vide → confidence 0.0 + log warning sans crash."""
    from services.contract_pdf_parser import parse_contract_pdf_text

    result = parse_contract_pdf_text("Random text with no contract data")
    assert result.confidence < 0.3
    assert result.fields_extracted == []
