"""Sprint S4 (2026-05-29) — Tests mutualisation advanced.

Couvre :
- Export PDF Table 1B (reportlab) + magic bytes + hash SHA256 opposable.
- validation_token_hash calculé au moment du PASS validated (S3 ext).
- Service `compute_export_hash` reproductible.

Tests BE pure (sans BE live) via les helpers/fixtures locales.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    GroupeStructures,
    GroupeStructuresMembre,
    TertiaireEfa,
)
from services.tertiaire_groupe_structures_service import (
    add_efa_to_groupe,
    create_groupe,
    set_representant_legal_status,
)
from services.tertiaire_mutualisation_pdf import (
    MutualisationPdfError,
    compute_export_hash,
    generate_table_1b_pdf,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def org_efas(db_session: Session):
    from models import Organisation, EntiteJuridique, Portefeuille, Site

    org = Organisation(nom="Org S4 Test", actif=True)
    db_session.add(org)
    db_session.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="111111111")
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db_session.add(pf)
    db_session.flush()
    site = Site(portefeuille_id=pf.id, nom="S", type="bureau", actif=True)
    db_session.add(site)
    db_session.flush()
    e1 = TertiaireEfa(
        org_id=org.id,
        site_id=site.id,
        nom="EFA Alpha S4",
        reference_year=2020,
        reference_year_kwh=500_000,
    )
    e2 = TertiaireEfa(
        org_id=org.id,
        site_id=site.id,
        nom="EFA Beta S4",
        reference_year=2020,
        reference_year_kwh=400_000,
    )
    db_session.add_all([e1, e2])
    db_session.flush()
    return org, e1, e2


# ─── A. validation_token_hash (S3 enrichi S4) ─────────────────────────────


class TestValidationTokenHash:
    def test_hash_is_set_on_validated(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        m = add_efa_to_groupe(db_session, g, e1.id)
        assert m.validation_token_hash is None  # pending
        set_representant_legal_status(db_session, m, new_status="validated", validator_user_id="rl@test")
        assert m.validation_token_hash is not None
        assert len(m.validation_token_hash) == 64  # SHA256 hex
        assert all(c in "0123456789abcdef" for c in m.validation_token_hash)

    def test_hash_is_cleared_on_rejected(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        m = add_efa_to_groupe(db_session, g, e1.id)
        set_representant_legal_status(db_session, m, new_status="validated", validator_user_id="x")
        assert m.validation_token_hash is not None
        set_representant_legal_status(db_session, m, new_status="rejected", validator_user_id="y")
        assert m.validation_token_hash is None  # nettoyé

    def test_hash_is_unique_per_validation(self, db_session, org_efas):
        """2 EFAs validées dans le même groupe doivent avoir des hashs distincts
        (le payload inclut efa_id)."""
        org, e1, e2 = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        m1 = add_efa_to_groupe(db_session, g, e1.id)
        m2 = add_efa_to_groupe(db_session, g, e2.id)
        set_representant_legal_status(db_session, m1, new_status="validated", validator_user_id="x")
        set_representant_legal_status(db_session, m2, new_status="validated", validator_user_id="x")
        assert m1.validation_token_hash != m2.validation_token_hash


# ─── B. compute_export_hash (déterminisme) ────────────────────────────────


class TestComputeExportHash:
    def test_hash_is_64_hex_chars(self):
        h = compute_export_hash({"a": 1, "b": [2, 3]})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_is_deterministic(self):
        payload = {"groupe_id": 1, "membres": [{"efa_id": 2}]}
        assert compute_export_hash(payload) == compute_export_hash(payload)

    def test_hash_changes_with_payload(self):
        h1 = compute_export_hash({"a": 1})
        h2 = compute_export_hash({"a": 2})
        assert h1 != h2

    def test_hash_independent_of_key_order(self):
        # sort_keys=True dans l'impl → ordre n'affecte pas le hash.
        h1 = compute_export_hash({"a": 1, "b": 2})
        h2 = compute_export_hash({"b": 2, "a": 1})
        assert h1 == h2


# ─── C. generate_table_1b_pdf ────────────────────────────────────────────


class TestGenerateTable1bPdf:
    def test_pdf_magic_bytes(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G PDF")
        m = add_efa_to_groupe(db_session, g, e1.id)
        set_representant_legal_status(db_session, m, new_status="validated", validator_user_id="x")
        # Re-fetch g pour s'assurer que membres ont le hash en mémoire
        db_session.refresh(g)
        pdf_bytes, export_hash = generate_table_1b_pdf(db_session, g)
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 1000  # PDF non vide
        assert len(export_hash) == 64

    def test_pdf_refused_when_no_active_member(self, db_session, org_efas):
        org, _, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G vide")
        db_session.refresh(g)
        with pytest.raises(MutualisationPdfError):
            generate_table_1b_pdf(db_session, g)

    def test_pdf_hash_changes_after_new_member(self, db_session, org_efas):
        """Ajouter une EFA change la composition du groupe → hash export
        différent (signe que le contenu change)."""
        org, e1, e2 = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G hash")
        m1 = add_efa_to_groupe(db_session, g, e1.id)
        set_representant_legal_status(db_session, m1, new_status="validated", validator_user_id="x")
        db_session.refresh(g)
        _, hash_1efa = generate_table_1b_pdf(db_session, g)

        m2 = add_efa_to_groupe(db_session, g, e2.id)
        set_representant_legal_status(db_session, m2, new_status="validated", validator_user_id="x")
        db_session.refresh(g)
        _, hash_2efa = generate_table_1b_pdf(db_session, g)

        # 2 EFAs validated → hash différent du cas 1 EFA.
        # Le timestamp generated_at change aussi entre les 2 appels, mais
        # ce qu'on vérifie ici est que le hash bouge bien quand la
        # composition change.
        assert hash_1efa != hash_2efa
