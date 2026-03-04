"""
PROMEOS - Tests Validation Format Industrielle
Covers: SIREN/SIRET Luhn, meter_id 14 digits, postal code, helper utils.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    StagingBatch,
    StagingSite,
    StagingCompteur,
    StagingStatus,
    ImportSourceType,
    QualityRuleSeverity,
)
from services.validation_helpers import (
    is_valid_siren,
    is_valid_siret,
    is_valid_meter_id,
    is_valid_postal_code,
    is_valid_date_str,
)
from services.quality_rules import (
    check_valid_siren,
    check_valid_siret,
    check_valid_meter_format,
    check_valid_postal_code,
    check_valid_dates,
)
from services.patrimoine_service import create_staging_batch, run_quality_gate


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def db_session():
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


def _create_org(db_session):
    org = Organisation(nom="Test Org", type_client="bureau", actif=True, siren="443061841")
    db_session.add(org)
    db_session.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="Test EJ", siren="443061841")
    db_session.add(ej)
    db_session.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF Test", description="Test")
    db_session.add(pf)
    db_session.flush()

    return org, ej, pf


def _create_batch(db_session, org_id):
    return create_staging_batch(
        db_session,
        org_id=org_id,
        user_id=None,
        source_type=ImportSourceType.CSV,
        mode="import",
    )


# ========================================
# Helper unit tests
# ========================================


class TestHelperSiren:
    def test_valid_siren(self):
        assert is_valid_siren("443061841") is True

    def test_invalid_siren_bad_luhn(self):
        assert is_valid_siren("123456789") is False

    def test_invalid_siren_too_short(self):
        assert is_valid_siren("12345") is False

    def test_invalid_siren_letters(self):
        assert is_valid_siren("ABCDEFGHI") is False

    def test_invalid_siren_empty(self):
        assert is_valid_siren("") is False
        assert is_valid_siren(None) is False


class TestHelperSiret:
    def test_valid_siret(self):
        # 44306184100005 passes Luhn on 14 digits
        assert is_valid_siret("44306184100005") is True

    def test_invalid_siret_bad_luhn(self):
        assert is_valid_siret("12345678901234") is False

    def test_invalid_siret_too_short(self):
        assert is_valid_siret("443061841") is False

    def test_invalid_siret_letters(self):
        assert is_valid_siret("ABCDEFGHIJKLMN") is False


class TestHelperMeter:
    def test_valid_meter_14_digits(self):
        assert is_valid_meter_id("12345678901234") is True

    def test_invalid_meter_too_short(self):
        assert is_valid_meter_id("1234567890") is False

    def test_invalid_meter_letters(self):
        assert is_valid_meter_id("ABCDEF78901234") is False

    def test_invalid_meter_empty(self):
        assert is_valid_meter_id("") is False


class TestHelperPostalCode:
    def test_valid_paris(self):
        assert is_valid_postal_code("75001") is True

    def test_valid_dom(self):
        assert is_valid_postal_code("97100") is True

    def test_invalid_dept_99(self):
        assert is_valid_postal_code("99001") is False

    def test_invalid_dept_00(self):
        assert is_valid_postal_code("00100") is False

    def test_invalid_too_short(self):
        assert is_valid_postal_code("7500") is False

    def test_invalid_letters(self):
        assert is_valid_postal_code("ABCDE") is False


class TestHelperDate:
    def test_valid_iso(self):
        assert is_valid_date_str("2024-01-15") is True

    def test_valid_french(self):
        assert is_valid_date_str("15/01/2024") is True

    def test_invalid_format(self):
        assert is_valid_date_str("01-15-2024") is False

    def test_invalid_month(self):
        assert is_valid_date_str("2024-13-01") is False


# ========================================
# Quality rule integration tests
# ========================================


class TestInvalidSirenBlocked:
    """Invalid SIREN in staging SIRET field produces BLOCKING finding."""

    def test_invalid_siren_blocked(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch = _create_batch(db_session, org.id)

        ss = StagingSite(
            batch_id=batch.id,
            row_number=2,
            nom="Site Bad SIREN",
            adresse="1 rue Test",
            code_postal="75001",
            ville="Paris",
            siret="12345678901234",  # SIREN part = 123456789 → invalid Luhn
        )
        db_session.add(ss)
        db_session.flush()

        findings = check_valid_siren(db_session, batch.id)

        assert len(findings) == 1
        f = findings[0]
        assert f["rule_id"] == "valid_siren_format"
        assert f["severity"] == QualityRuleSeverity.BLOCKING
        evidence = json.loads(f["evidence_json"])
        assert evidence["siren_extracted"] == "123456789"

    def test_valid_siren_passes(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch = _create_batch(db_session, org.id)

        ss = StagingSite(
            batch_id=batch.id,
            row_number=2,
            nom="Site Good SIREN",
            adresse="1 rue Test",
            code_postal="75001",
            ville="Paris",
            siret="44306184100005",  # SIREN part = 443061841 → valid Luhn
        )
        db_session.add(ss)
        db_session.flush()

        findings = check_valid_siren(db_session, batch.id)
        assert len(findings) == 0


class TestInvalidSiretBlocked:
    """Invalid SIRET produces BLOCKING finding."""

    def test_invalid_siret_blocked(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch = _create_batch(db_session, org.id)

        ss = StagingSite(
            batch_id=batch.id,
            row_number=2,
            nom="Site Bad SIRET",
            adresse="1 rue Test",
            code_postal="75001",
            ville="Paris",
            siret="12345678901234",  # Invalid Luhn on 14 digits
        )
        db_session.add(ss)
        db_session.flush()

        findings = check_valid_siret(db_session, batch.id)

        assert len(findings) == 1
        f = findings[0]
        assert f["rule_id"] == "valid_siret_format"
        assert f["severity"] == QualityRuleSeverity.BLOCKING


class TestInvalidMeterBlocked:
    """Invalid meter_id format produces BLOCKING finding."""

    def test_invalid_meter_blocked(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch = _create_batch(db_session, org.id)

        ss = StagingSite(
            batch_id=batch.id,
            row_number=2,
            nom="Site Test",
            adresse="1 rue Test",
            code_postal="75001",
            ville="Paris",
        )
        db_session.add(ss)
        db_session.flush()

        sc = StagingCompteur(
            batch_id=batch.id,
            staging_site_id=ss.id,
            row_number=2,
            numero_serie="S-001",
            meter_id="SHORT123",  # Not 14 digits
            type_compteur="electricite",
        )
        db_session.add(sc)
        db_session.flush()

        findings = check_valid_meter_format(db_session, batch.id)

        assert len(findings) == 1
        f = findings[0]
        assert f["rule_id"] == "valid_meter_format"
        assert f["severity"] == QualityRuleSeverity.BLOCKING
        evidence = json.loads(f["evidence_json"])
        assert evidence["value"] == "SHORT123"
        assert evidence["reason"] == "expected_14_digits"

    def test_valid_meter_passes(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch = _create_batch(db_session, org.id)

        ss = StagingSite(
            batch_id=batch.id,
            row_number=2,
            nom="Site Test",
            adresse="1 rue Test",
            code_postal="75001",
            ville="Paris",
        )
        db_session.add(ss)
        db_session.flush()

        sc = StagingCompteur(
            batch_id=batch.id,
            staging_site_id=ss.id,
            row_number=2,
            numero_serie="S-001",
            meter_id="12345678901234",  # Exactly 14 digits
            type_compteur="electricite",
        )
        db_session.add(sc)
        db_session.flush()

        findings = check_valid_meter_format(db_session, batch.id)
        assert len(findings) == 0


class TestInvalidPostalWarning:
    """Invalid postal code produces WARNING finding."""

    def test_invalid_postal_warning(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch = _create_batch(db_session, org.id)

        ss = StagingSite(
            batch_id=batch.id,
            row_number=2,
            nom="Site Bad CP",
            adresse="1 rue Test",
            code_postal="99001",
            ville="Paris",
        )
        db_session.add(ss)
        db_session.flush()

        findings = check_valid_postal_code(db_session, batch.id)

        assert len(findings) == 1
        f = findings[0]
        assert f["rule_id"] == "valid_postal_code"
        assert f["severity"] == QualityRuleSeverity.WARNING
        evidence = json.loads(f["evidence_json"])
        assert evidence["value"] == "99001"

    def test_valid_postal_passes(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch = _create_batch(db_session, org.id)

        ss = StagingSite(
            batch_id=batch.id,
            row_number=2,
            nom="Site Good CP",
            adresse="1 rue Test",
            code_postal="75001",
            ville="Paris",
        )
        db_session.add(ss)
        db_session.flush()

        findings = check_valid_postal_code(db_session, batch.id)
        assert len(findings) == 0


class TestValidDateRule:
    """Date rule returns empty (no string date fields in staging)."""

    def test_date_rule_returns_empty(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch = _create_batch(db_session, org.id)
        findings = check_valid_dates(db_session, batch.id)
        assert findings == []


class TestValidDataPasses:
    """All valid data produces zero format findings from new rules."""

    def test_valid_data_passes(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch = _create_batch(db_session, org.id)

        ss = StagingSite(
            batch_id=batch.id,
            row_number=2,
            nom="Site Parfait",
            adresse="10 avenue des Champs-Elysees",
            code_postal="75008",
            ville="Paris",
            siret="44306184100005",
        )
        db_session.add(ss)
        db_session.flush()

        sc = StagingCompteur(
            batch_id=batch.id,
            staging_site_id=ss.id,
            row_number=2,
            numero_serie="SERIE-VALID-001",
            meter_id="12345678901234",
            type_compteur="electricite",
        )
        db_session.add(sc)
        db_session.flush()

        # Check each format rule individually
        assert len(check_valid_siren(db_session, batch.id)) == 0
        assert len(check_valid_siret(db_session, batch.id)) == 0
        assert len(check_valid_meter_format(db_session, batch.id)) == 0
        assert len(check_valid_postal_code(db_session, batch.id)) == 0
        assert len(check_valid_dates(db_session, batch.id)) == 0

    def test_quality_gate_includes_format_rules(self, db_session):
        """Full quality gate run picks up format validation findings."""
        org, ej, pf = _create_org(db_session)
        batch = _create_batch(db_session, org.id)

        ss = StagingSite(
            batch_id=batch.id,
            row_number=2,
            nom="Site Mixed",
            adresse="1 rue Test",
            code_postal="99999",  # invalid
            ville="Paris",
            siret="ABCDEFGHIJKLMN",  # invalid
        )
        db_session.add(ss)
        db_session.flush()

        sc = StagingCompteur(
            batch_id=batch.id,
            staging_site_id=ss.id,
            row_number=2,
            numero_serie="S-MIX-001",
            meter_id="SHORT",  # invalid
            type_compteur="electricite",
        )
        db_session.add(sc)
        db_session.flush()

        results = run_quality_gate(db_session, batch.id)
        format_rules = {r["rule_id"] for r in results if r["rule_id"].startswith("valid_")}
        assert "valid_siren_format" in format_rules
        assert "valid_siret_format" in format_rules
        assert "valid_meter_format" in format_rules
        assert "valid_postal_code" in format_rules
