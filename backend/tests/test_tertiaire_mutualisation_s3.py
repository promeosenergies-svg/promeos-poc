"""Sprint S3 (2026-05-28) — Tests garde-fous mutualisation Art. 14.

Couvre les 5 invariants juridiques cardinaux :
  I1 — création groupe + lifecycle status whitelist
  I2 — validation représentant légal obligatoire pour export
  I3 — 1 EFA active ⊆ 1 seul groupe actif
  I4 — redistribution unique par EFA donneuse / jalon
  I5 — refus si redistribution > surplus disponible

+ export Table 1B CSV (Chantier 3) :
  - refusé tant que tous les RL ne sont pas validés (I2)
  - réussi quand tous les RL sont validés

Fixture `db_session` locale (le conftest racine n'expose que `app_client`).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    GroupeStructures,
    GroupeStructuresMembre,
    MutualisationLedger,
    TertiaireEfa,
)


@pytest.fixture
def db_session() -> Session:
    """DB SQLite in-memory isolée par test (rollback implicite à la fin)."""
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


from services.tertiaire_groupe_structures_service import (
    MutualisationViolation,
    add_efa_to_groupe,
    archive_groupe,
    create_groupe,
    ensure_groupe_exportable,
    record_redistribution,
    remove_efa_from_groupe,
    set_groupe_status,
    set_representant_legal_status,
)


# ─── Fixtures locales ─────────────────────────────────────────────────────


@pytest.fixture
def org_efas(db_session: Session):
    """Crée 1 org + 2 EFA dans cette org pour les tests."""
    from models import Organisation, EntiteJuridique, Portefeuille, Site

    org = Organisation(nom="Org S3 Test", actif=True)
    db_session.add(org)
    db_session.flush()
    # `siren` est NOT NULL côté modèle Organisation/EntiteJuridique.
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ Test", siren="123456789")
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF Test")
    db_session.add(pf)
    db_session.flush()
    site = Site(portefeuille_id=pf.id, nom="Site Test", type="bureau", actif=True)
    db_session.add(site)
    db_session.flush()
    efa1 = TertiaireEfa(org_id=org.id, site_id=site.id, nom="EFA Alpha", reference_year=2020, reference_year_kwh=500000)
    efa2 = TertiaireEfa(org_id=org.id, site_id=site.id, nom="EFA Beta", reference_year=2020, reference_year_kwh=400000)
    db_session.add_all([efa1, efa2])
    db_session.flush()
    return org, efa1, efa2


# ─── I1 — Lifecycle + création ───────────────────────────────────────────


class TestI1GroupeLifecycle:
    def test_create_groupe_default_draft(self, db_session, org_efas):
        org, _, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="Test draft")
        assert g.status == "draft"
        assert g.organisation_id == org.id

    def test_create_groupe_nom_required(self, db_session, org_efas):
        org, _, _ = org_efas
        with pytest.raises(MutualisationViolation) as exc:
            create_groupe(db_session, organisation_id=org.id, nom="  ")
        assert exc.value.code == "GROUPE_NOM_REQUIS"

    def test_status_transition_valid(self, db_session, org_efas):
        org, _, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="T")
        set_groupe_status(db_session, g, "pending_validation")
        assert g.status == "pending_validation"

    def test_status_transition_invalid_refused(self, db_session, org_efas):
        org, _, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="T")
        with pytest.raises(MutualisationViolation) as exc:
            set_groupe_status(db_session, g, "merged_into_other")
        assert exc.value.code == "GROUPE_STATUS_INVALID"


# ─── I2 — Validation représentant légal ──────────────────────────────────


class TestI2ValidationRepresentantLegal:
    def test_membre_initial_pending(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="T")
        m = add_efa_to_groupe(db_session, g, e1.id)
        assert m.representant_legal_status == "pending"
        assert m.representant_legal_validated_at is None

    def test_validate_rl_sets_timestamp_and_validator(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="T")
        m = add_efa_to_groupe(db_session, g, e1.id)
        set_representant_legal_status(db_session, m, new_status="validated", validator_user_id="rl@helios-energie.fr")
        assert m.representant_legal_status == "validated"
        assert m.representant_legal_validated_at is not None
        assert m.validator_user_id == "rl@helios-energie.fr"

    def test_reject_rl_clears_timestamp(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="T")
        m = add_efa_to_groupe(db_session, g, e1.id)
        set_representant_legal_status(db_session, m, new_status="validated", validator_user_id="x")
        set_representant_legal_status(
            db_session, m, new_status="rejected", validator_user_id="y", validation_note="cf. mail"
        )
        assert m.representant_legal_status == "rejected"
        assert m.representant_legal_validated_at is None

    def test_regression_to_pending_refused(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="T")
        m = add_efa_to_groupe(db_session, g, e1.id)
        set_representant_legal_status(db_session, m, new_status="validated", validator_user_id="x")
        with pytest.raises(MutualisationViolation) as exc:
            set_representant_legal_status(db_session, m, new_status="pending", validator_user_id=None)
        assert exc.value.code == "RL_STATUS_REGRESSION_DENIED"

    def test_invalid_rl_status_refused(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="T")
        m = add_efa_to_groupe(db_session, g, e1.id)
        with pytest.raises(MutualisationViolation) as exc:
            set_representant_legal_status(db_session, m, new_status="maybe", validator_user_id="x")
        assert exc.value.code == "RL_STATUS_INVALID"


# ─── I3 — Unicité EFA / groupe (Art. 14 §1 al.3) ─────────────────────────


class TestI3UniciteEfa:
    def test_efa_can_be_added_to_one_group(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G1")
        m = add_efa_to_groupe(db_session, g, e1.id)
        assert m.efa_id == e1.id

    def test_efa_double_appartenance_refused(self, db_session, org_efas):
        org, e1, _ = org_efas
        g1 = create_groupe(db_session, organisation_id=org.id, nom="G1")
        add_efa_to_groupe(db_session, g1, e1.id)
        g2 = create_groupe(db_session, organisation_id=org.id, nom="G2")
        with pytest.raises(MutualisationViolation) as exc:
            add_efa_to_groupe(db_session, g2, e1.id)
        assert exc.value.code == "EFA_ALREADY_IN_ACTIVE_GROUP"

    def test_efa_can_be_moved_after_removal(self, db_session, org_efas):
        org, e1, _ = org_efas
        g1 = create_groupe(db_session, organisation_id=org.id, nom="G1")
        add_efa_to_groupe(db_session, g1, e1.id)
        remove_efa_from_groupe(db_session, g1, e1.id)
        # Maintenant on doit pouvoir l'ajouter à un autre groupe.
        g2 = create_groupe(db_session, organisation_id=org.id, nom="G2")
        m = add_efa_to_groupe(db_session, g2, e1.id)
        assert m.efa_id == e1.id

    def test_efa_can_be_moved_after_archive(self, db_session, org_efas):
        org, e1, _ = org_efas
        g1 = create_groupe(db_session, organisation_id=org.id, nom="G1")
        add_efa_to_groupe(db_session, g1, e1.id)
        archive_groupe(db_session, g1)
        # G1 archivé → libère l'EFA pour un autre groupe actif.
        g2 = create_groupe(db_session, organisation_id=org.id, nom="G2")
        m = add_efa_to_groupe(db_session, g2, e1.id)
        assert m.efa_id == e1.id

    def test_archived_group_cannot_receive_new_members(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="T")
        archive_groupe(db_session, g)
        with pytest.raises(MutualisationViolation) as exc:
            add_efa_to_groupe(db_session, g, e1.id)
        assert exc.value.code == "GROUPE_ARCHIVED"

    def test_efa_cross_org_refused(self, db_session, org_efas):
        # Second org + son EFA
        from models import Organisation, EntiteJuridique, Portefeuille, Site

        org2 = Organisation(nom="Org2", actif=True)
        db_session.add(org2)
        db_session.flush()
        ej2 = EntiteJuridique(organisation_id=org2.id, nom="EJ2", siren="987654321")
        db_session.add(ej2)
        db_session.flush()
        pf2 = Portefeuille(entite_juridique_id=ej2.id, nom="PF2")
        db_session.add(pf2)
        db_session.flush()
        s2 = Site(portefeuille_id=pf2.id, nom="S2", type="bureau", actif=True)
        db_session.add(s2)
        db_session.flush()
        e_org2 = TertiaireEfa(org_id=org2.id, site_id=s2.id, nom="EFA Org2")
        db_session.add(e_org2)
        db_session.flush()

        org, _, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        with pytest.raises(MutualisationViolation) as exc:
            add_efa_to_groupe(db_session, g, e_org2.id)
        assert exc.value.code == "EFA_CROSS_ORG"


# ─── I4 + I5 — Redistribution unique + plafond surplus ────────────────────


class TestI4I5Redistribution:
    def test_first_redistribution_recorded(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        add_efa_to_groupe(db_session, g, e1.id)
        entry = record_redistribution(
            db_session,
            g,
            donneuse_efa_id=e1.id,
            jalon_annee=2030,
            kwh_redistribues=10000,
            surplus_disponible_kwh=50000,
        )
        assert entry.kwh_redistribues == 10000

    def test_second_redistribution_same_jalon_refused(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        add_efa_to_groupe(db_session, g, e1.id)
        record_redistribution(
            db_session,
            g,
            donneuse_efa_id=e1.id,
            jalon_annee=2030,
            kwh_redistribues=10000,
            surplus_disponible_kwh=50000,
        )
        with pytest.raises(MutualisationViolation) as exc:
            record_redistribution(
                db_session,
                g,
                donneuse_efa_id=e1.id,
                jalon_annee=2030,
                kwh_redistribues=5000,
                surplus_disponible_kwh=50000,
            )
        assert exc.value.code == "REDISTRIBUTION_DEJA_EFFECTUEE"

    def test_redistribution_different_jalons_ok(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        add_efa_to_groupe(db_session, g, e1.id)
        record_redistribution(
            db_session,
            g,
            donneuse_efa_id=e1.id,
            jalon_annee=2030,
            kwh_redistribues=10000,
            surplus_disponible_kwh=50000,
        )
        # Jalon 2040 = nouveau cycle, autorisé.
        record_redistribution(
            db_session,
            g,
            donneuse_efa_id=e1.id,
            jalon_annee=2040,
            kwh_redistribues=15000,
            surplus_disponible_kwh=50000,
        )

    def test_redistribution_excede_surplus_refused(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        add_efa_to_groupe(db_session, g, e1.id)
        with pytest.raises(MutualisationViolation) as exc:
            record_redistribution(
                db_session,
                g,
                donneuse_efa_id=e1.id,
                jalon_annee=2030,
                kwh_redistribues=10000,
                surplus_disponible_kwh=5000,
            )
        assert exc.value.code == "REDISTRIBUTION_EXCEDE_SURPLUS"

    def test_redistribution_kwh_zero_refused(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        add_efa_to_groupe(db_session, g, e1.id)
        with pytest.raises(MutualisationViolation) as exc:
            record_redistribution(
                db_session,
                g,
                donneuse_efa_id=e1.id,
                jalon_annee=2030,
                kwh_redistribues=0,
                surplus_disponible_kwh=50000,
            )
        assert exc.value.code == "REDISTRIBUTION_KWH_NON_POSITIF"


# ─── Export Table 1B (Chantier 3 + I2) ────────────────────────────────────


class TestExportTable1B:
    def test_export_refused_when_group_empty(self, db_session, org_efas):
        org, _, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G vide")
        with pytest.raises(MutualisationViolation) as exc:
            ensure_groupe_exportable(g)
        assert exc.value.code == "GROUPE_EMPTY"

    def test_export_refused_when_rl_pending(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        add_efa_to_groupe(db_session, g, e1.id)
        with pytest.raises(MutualisationViolation) as exc:
            ensure_groupe_exportable(g)
        assert exc.value.code == "RL_VALIDATION_MISSING"

    def test_export_ok_when_all_rl_validated(self, db_session, org_efas):
        org, e1, e2 = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        m1 = add_efa_to_groupe(db_session, g, e1.id)
        m2 = add_efa_to_groupe(db_session, g, e2.id)
        set_representant_legal_status(db_session, m1, new_status="validated", validator_user_id="x")
        set_representant_legal_status(db_session, m2, new_status="validated", validator_user_id="y")
        # Pas d'exception levée.
        ensure_groupe_exportable(g)

    def test_export_refused_when_one_rl_rejected(self, db_session, org_efas):
        org, e1, e2 = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        m1 = add_efa_to_groupe(db_session, g, e1.id)
        m2 = add_efa_to_groupe(db_session, g, e2.id)
        set_representant_legal_status(db_session, m1, new_status="validated", validator_user_id="x")
        set_representant_legal_status(db_session, m2, new_status="rejected", validator_user_id="y")
        with pytest.raises(MutualisationViolation) as exc:
            ensure_groupe_exportable(g)
        assert exc.value.code == "RL_VALIDATION_MISSING"

    def test_export_refused_when_archived(self, db_session, org_efas):
        org, e1, _ = org_efas
        g = create_groupe(db_session, organisation_id=org.id, nom="G")
        m = add_efa_to_groupe(db_session, g, e1.id)
        set_representant_legal_status(db_session, m, new_status="validated", validator_user_id="x")
        archive_groupe(db_session, g)
        with pytest.raises(MutualisationViolation) as exc:
            ensure_groupe_exportable(g)
        assert exc.value.code == "GROUPE_ARCHIVED"
