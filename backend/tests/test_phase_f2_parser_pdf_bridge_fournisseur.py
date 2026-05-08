"""
PROMEOS — Phase F2 (ADR-F-02) : tests cardinaux bridge parser PDF ↔ Fournisseur Phase F1.

8 tests T-PARSE-01 → T-PARSE-08 :
- Extraction SIREN/SIRET regex (T-PARSE-01/02)
- Mapping supplier_name canoniques + variantes (T-PARSE-03/04)
- Fallback unmapped (T-PARSE-05)
- IDOR resolver canoniques + privés scope (T-PARSE-06)
- Wire raw_json idempotent (T-PARSE-07/08)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Fournisseur,
    Organisation,
    TypeFournitureEnum,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


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
    """Crée 3 fournisseurs canoniques pour tests."""
    db.add_all(
        [
            Fournisseur(nom="EDF", siren="552081317", type_fourniture=TypeFournitureEnum.MULTI),
            Fournisseur(nom="ENGIE", siren="542107651", type_fourniture=TypeFournitureEnum.MULTI),
            Fournisseur(nom="TOTALENERGIES", siren="542051180", type_fourniture=TypeFournitureEnum.MULTI),
        ]
    )
    db.commit()


# ─── T-PARSE-01 / 02 : Extraction SIREN/SIRET ───────────────────────────────


def test_t_parse_01_extraction_siren_label():
    """T-PARSE-01 : SIREN 9 chiffres avec label depuis texte PDF."""
    from app.bill_intelligence.parsers.pdf_parser import extract_siren_from_pdf_text

    text = "Engie SA\nSIREN 542107651\nFacture n°ABC123"
    assert extract_siren_from_pdf_text(text) == "542107651"


def test_t_parse_02_extraction_siret_to_siren():
    """T-PARSE-02 : SIRET 14 chiffres → SIREN[0:9] (priorité plus spécifique)."""
    from app.bill_intelligence.parsers.pdf_parser import extract_siren_from_pdf_text

    text = "EDF Entreprises\nSIRET: 55208131700123\nN° facture: 9876"
    assert extract_siren_from_pdf_text(text) == "552081317"


# ─── T-PARSE-03 / 04 : Mapping supplier_name ────────────────────────────────


def test_t_parse_03_mapping_supplier_name_canonique(db):
    """T-PARSE-03 : `EDF` → Fournisseur canonique EDF."""
    from services.fournisseur_resolver_service import resolve_fournisseur_from_supplier_name

    _seed_canoniques(db)
    f = resolve_fournisseur_from_supplier_name(db, "EDF")
    assert f is not None
    assert f.nom == "EDF"
    assert f.is_canonique() is True


def test_t_parse_04_mapping_supplier_name_variantes(db):
    """T-PARSE-04 : `E.D.F.` / `EDF Entreprises` / `edf` → même Fournisseur EDF."""
    from services.fournisseur_resolver_service import resolve_fournisseur_from_supplier_name

    _seed_canoniques(db)
    f1 = resolve_fournisseur_from_supplier_name(db, "EDF")
    f2 = resolve_fournisseur_from_supplier_name(db, "E.D.F.")
    f3 = resolve_fournisseur_from_supplier_name(db, "EDF Entreprises")
    f4 = resolve_fournisseur_from_supplier_name(db, "edf")  # casse insensible

    # Assertions intermédiaires (P2 fix code-reviewer Phase F2 — messages clairs)
    assert f1 is not None, "Variante 'EDF' doit matcher canonique"
    assert f2 is not None, "Variante 'E.D.F.' doit matcher canonique (normalize keep dots)"
    assert f3 is not None, "Variante 'EDF Entreprises' doit matcher canonique"
    assert f4 is not None, "Variante 'edf' (casse insensible) doit matcher canonique"
    assert f1.id == f2.id == f3.id == f4.id


def test_t_parse_04bis_normalize_supplier_name_unit():
    """T-PARSE-04bis : normalize_supplier_name unitaire (P2 fix transparency)."""
    from config.fournisseur_mappings import normalize_supplier_name

    assert normalize_supplier_name(None) == ""
    assert normalize_supplier_name("") == ""
    assert normalize_supplier_name("EDF") == "EDF"
    assert normalize_supplier_name("edf") == "EDF"
    assert normalize_supplier_name("  EDF  ") == "EDF"
    assert normalize_supplier_name("EDF  Entreprises") == "EDF ENTREPRISES"  # dedup spaces
    assert normalize_supplier_name("E.D.F.") == "E.D.F."  # ne supprime pas les points


# ─── T-PARSE-05 : Fallback unmapped ─────────────────────────────────────────


def test_t_parse_05_unmapped_supplier_returns_none(db):
    """T-PARSE-05 : Fournisseur inconnu (Eni, Vattenfall) → None sans crash."""
    from services.fournisseur_resolver_service import resolve_fournisseur_from_supplier_name

    _seed_canoniques(db)
    assert resolve_fournisseur_from_supplier_name(db, "Eni") is None
    assert resolve_fournisseur_from_supplier_name(db, "Vattenfall") is None
    assert resolve_fournisseur_from_supplier_name(db, "") is None
    assert resolve_fournisseur_from_supplier_name(db, None) is None


# ─── T-PARSE-06 : IDOR resolver canoniques + privés scope ───────────────────


def test_t_parse_06_idor_resolver_scope(db):
    """T-PARSE-06 : SIREN match canonique OU privé scope, pas privé autre tenant."""
    from services.fournisseur_resolver_service import resolve_fournisseur_from_siren

    org_a = Organisation(nom="Org Alpha", actif=True, siren="111111111")
    org_b = Organisation(nom="Org Bravo", actif=True, siren="222222222")
    db.add_all([org_a, org_b])
    db.flush()

    # 1 canonique partagé
    f_canon = Fournisseur(nom="EDF", siren="552081317", type_fourniture=TypeFournitureEnum.MULTI)
    # 1 privé Bravo (SIREN différent)
    f_prive_b = Fournisseur(
        organisation_id=org_b.id,
        nom="ELD Bravo",
        siren="999999999",
        type_fourniture=TypeFournitureEnum.GAZ,
    )
    db.add_all([f_canon, f_prive_b])
    db.commit()

    # Org A scope : voit canonique EDF, pas privé Bravo
    assert resolve_fournisseur_from_siren(db, "552081317", scope_org_id=org_a.id) is not None
    assert resolve_fournisseur_from_siren(db, "999999999", scope_org_id=org_a.id) is None

    # Org B scope : voit privé Bravo
    assert resolve_fournisseur_from_siren(db, "999999999", scope_org_id=org_b.id) is not None


# ─── T-PARSE-07 / 08 : Composite resolver from invoice ──────────────────────


def test_t_parse_07_composite_resolve_via_siren(db):
    """T-PARSE-07 : SIREN extrait du PDF → match déterministe canonique (haute confiance)."""
    from services.fournisseur_resolver_service import resolve_fournisseur_from_invoice

    _seed_canoniques(db)
    invoice_mock = MagicMock(supplier="UnknownLabel")
    pdf_text = "EDF Entreprises\nSIRET: 55208131700123\n..."

    f = resolve_fournisseur_from_invoice(db, invoice_mock, pdf_text=pdf_text)
    assert f is not None
    assert f.nom == "EDF"


def test_t_parse_08_composite_idempotent_same_pdf(db):
    """T-PARSE-08 : Re-résolution même PDF = même fournisseur_id (déterministe)."""
    from services.fournisseur_resolver_service import resolve_fournisseur_from_invoice

    _seed_canoniques(db)
    invoice_mock = MagicMock(supplier="EDF")
    pdf_text = "EDF Entreprises\nSIREN 552081317\n..."

    f1 = resolve_fournisseur_from_invoice(db, invoice_mock, pdf_text=pdf_text)
    f2 = resolve_fournisseur_from_invoice(db, invoice_mock, pdf_text=pdf_text)
    assert f1 is not None
    assert f1.id == f2.id


# ─── T-PARSE-09 (bonus) : Fallback supplier_name si SIREN non extrait ──────


def test_t_parse_09_composite_fallback_supplier_name(db):
    """T-PARSE-09 : SIREN absent du PDF → fallback supplier_name mapping."""
    from services.fournisseur_resolver_service import resolve_fournisseur_from_invoice

    _seed_canoniques(db)
    invoice_mock = MagicMock(supplier="ENGIE")
    pdf_text = "Engie SA\nFacture sans identifiants SIREN/SIRET\n..."

    f = resolve_fournisseur_from_invoice(db, invoice_mock, pdf_text=pdf_text)
    assert f is not None
    assert f.nom == "ENGIE"
