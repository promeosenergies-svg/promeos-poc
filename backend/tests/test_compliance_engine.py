"""
PROMEOS - Tests for the Compliance Engine
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Base, Site, Obligation, Organisation, EntiteJuridique, Portefeuille,
    Evidence, StatutConformite, TypeObligation, TypeSite,
    TypeEvidence, StatutEvidence,
)
from services.compliance_engine import (
    worst_status,
    average_avancement,
    compute_risque_financier,
    compute_action_recommandee,
    compute_site_snapshot,
    compute_bacs_statut,
    bacs_deadline_for_power,
    recompute_site,
    recompute_portfolio,
    recompute_organisation,
    BASE_PENALTY_EURO,
    BACS_SEUIL_HAUT,
    BACS_SEUIL_BAS,
    BACS_DEADLINE_290,
    BACS_DEADLINE_70,
)


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def db_session():
    """In-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_obligation(
    site_id=1,
    ob_type=TypeObligation.DECRET_TERTIAIRE,
    statut=StatutConformite.CONFORME,
    avancement_pct=50.0,
    echeance=None,
):
    """Helper to create Obligation objects for pure function tests."""
    return Obligation(
        site_id=site_id,
        type=ob_type,
        statut=statut,
        avancement_pct=avancement_pct,
        echeance=echeance or date(2030, 12, 31),
    )


def _make_evidence(
    site_id=1,
    ev_type=TypeEvidence.AUDIT,
    statut=StatutEvidence.VALIDE,
):
    """Helper to create Evidence objects for pure function tests."""
    return Evidence(site_id=site_id, type=ev_type, statut=statut, note="test")


def _seed_hierarchy(db):
    """Create org -> entite -> portefeuille -> 2 sites -> obligations."""
    org = Organisation(nom="Test Org", type_client="retail", actif=True)
    db.add(org)
    db.commit()
    db.refresh(org)

    entite = EntiteJuridique(
        organisation_id=org.id, nom="Test SAS", siren="123456789"
    )
    db.add(entite)
    db.commit()
    db.refresh(entite)

    pf = Portefeuille(
        entite_juridique_id=entite.id, nom="PF Test", description="Test"
    )
    db.add(pf)
    db.commit()
    db.refresh(pf)

    site1 = Site(
        nom="Site A", type=TypeSite.MAGASIN, portefeuille_id=pf.id,
        surface_m2=2000, actif=True,
        statut_decret_tertiaire=StatutConformite.CONFORME,
        statut_bacs=StatutConformite.CONFORME,
    )
    site2 = Site(
        nom="Site B", type=TypeSite.BUREAU, portefeuille_id=pf.id,
        surface_m2=3000, actif=True,
        statut_decret_tertiaire=StatutConformite.CONFORME,
        statut_bacs=StatutConformite.CONFORME,
    )
    db.add_all([site1, site2])
    db.commit()
    db.refresh(site1)
    db.refresh(site2)

    # Site1: decret NON_CONFORME + bacs CONFORME
    ob1 = Obligation(
        site_id=site1.id, type=TypeObligation.DECRET_TERTIAIRE,
        statut=StatutConformite.NON_CONFORME, avancement_pct=30.0,
        echeance=date(2030, 12, 31),
    )
    ob2 = Obligation(
        site_id=site1.id, type=TypeObligation.BACS,
        statut=StatutConformite.CONFORME, avancement_pct=100.0,
        echeance=date(2025, 1, 1),
    )
    # Site2: decret CONFORME
    ob3 = Obligation(
        site_id=site2.id, type=TypeObligation.DECRET_TERTIAIRE,
        statut=StatutConformite.CONFORME, avancement_pct=90.0,
        echeance=date(2030, 12, 31),
    )
    db.add_all([ob1, ob2, ob3])

    # Site1: valid attestation BACS
    ev1 = Evidence(
        site_id=site1.id, type=TypeEvidence.ATTESTATION_BACS,
        statut=StatutEvidence.VALIDE, note="GTB OK",
    )
    db.add(ev1)
    db.commit()

    return org, entite, pf, site1, site2


# ========================================
# Tests: worst_status
# ========================================

class TestWorstStatus:
    def test_empty_list(self):
        assert worst_status([]) is None

    def test_all_conforme(self):
        obs = [
            _make_obligation(statut=StatutConformite.CONFORME),
            _make_obligation(statut=StatutConformite.CONFORME),
        ]
        assert worst_status(obs) == StatutConformite.CONFORME

    def test_mixed_conforme_and_a_risque(self):
        obs = [
            _make_obligation(statut=StatutConformite.CONFORME),
            _make_obligation(statut=StatutConformite.A_RISQUE),
        ]
        assert worst_status(obs) == StatutConformite.A_RISQUE

    def test_mixed_all_three(self):
        obs = [
            _make_obligation(statut=StatutConformite.CONFORME),
            _make_obligation(statut=StatutConformite.A_RISQUE),
            _make_obligation(statut=StatutConformite.NON_CONFORME),
        ]
        assert worst_status(obs) == StatutConformite.NON_CONFORME

    def test_single_non_conforme(self):
        obs = [_make_obligation(statut=StatutConformite.NON_CONFORME)]
        assert worst_status(obs) == StatutConformite.NON_CONFORME

    def test_derogation_less_severe_than_a_risque(self):
        obs = [
            _make_obligation(statut=StatutConformite.DEROGATION),
            _make_obligation(statut=StatutConformite.A_RISQUE),
        ]
        assert worst_status(obs) == StatutConformite.A_RISQUE

    def test_derogation_more_severe_than_conforme(self):
        obs = [
            _make_obligation(statut=StatutConformite.CONFORME),
            _make_obligation(statut=StatutConformite.DEROGATION),
        ]
        assert worst_status(obs) == StatutConformite.DEROGATION


# ========================================
# Tests: average_avancement
# ========================================

class TestAverageAvancement:
    def test_empty_list(self):
        assert average_avancement([]) == 0.0

    def test_single_value(self):
        obs = [_make_obligation(avancement_pct=75.0)]
        assert average_avancement(obs) == 75.0

    def test_multiple_values(self):
        obs = [
            _make_obligation(avancement_pct=50.0),
            _make_obligation(avancement_pct=100.0),
        ]
        assert average_avancement(obs) == 75.0

    def test_all_zero(self):
        obs = [
            _make_obligation(avancement_pct=0.0),
            _make_obligation(avancement_pct=0.0),
        ]
        assert average_avancement(obs) == 0.0


# ========================================
# Tests: compute_risque_financier
# ========================================

class TestComputeRisqueFinancier:
    def test_no_obligations(self):
        assert compute_risque_financier([]) == 0.0

    def test_all_conforme(self):
        obs = [_make_obligation(statut=StatutConformite.CONFORME)]
        assert compute_risque_financier(obs) == 0.0

    def test_one_non_conforme(self):
        obs = [_make_obligation(statut=StatutConformite.NON_CONFORME)]
        assert compute_risque_financier(obs) == BASE_PENALTY_EURO

    def test_two_non_conforme(self):
        obs = [
            _make_obligation(statut=StatutConformite.NON_CONFORME),
            _make_obligation(statut=StatutConformite.NON_CONFORME),
        ]
        assert compute_risque_financier(obs) == BASE_PENALTY_EURO * 2

    def test_a_risque_not_counted(self):
        obs = [_make_obligation(statut=StatutConformite.A_RISQUE)]
        assert compute_risque_financier(obs) == 0.0

    def test_mixed(self):
        obs = [
            _make_obligation(statut=StatutConformite.CONFORME),
            _make_obligation(statut=StatutConformite.A_RISQUE),
            _make_obligation(statut=StatutConformite.NON_CONFORME),
        ]
        assert compute_risque_financier(obs) == BASE_PENALTY_EURO

    def test_derogation_not_counted(self):
        obs = [_make_obligation(statut=StatutConformite.DEROGATION)]
        assert compute_risque_financier(obs) == 0.0


# ========================================
# Tests: compute_action_recommandee
# ========================================

class TestComputeActionRecommandee:
    def test_no_obligations(self):
        assert compute_action_recommandee([]) is None

    def test_all_conforme(self):
        obs = [_make_obligation(statut=StatutConformite.CONFORME)]
        assert compute_action_recommandee(obs) is None

    def test_bacs_non_conforme_highest_priority(self):
        obs = [
            _make_obligation(ob_type=TypeObligation.BACS, statut=StatutConformite.NON_CONFORME),
            _make_obligation(ob_type=TypeObligation.DECRET_TERTIAIRE, statut=StatutConformite.NON_CONFORME),
        ]
        result = compute_action_recommandee(obs)
        assert "BACS" in result

    def test_decret_non_conforme(self):
        obs = [
            _make_obligation(ob_type=TypeObligation.DECRET_TERTIAIRE, statut=StatutConformite.NON_CONFORME),
        ]
        result = compute_action_recommandee(obs)
        assert "decret tertiaire" in result.lower()

    def test_a_risque_fallback(self):
        obs = [
            _make_obligation(ob_type=TypeObligation.BACS, statut=StatutConformite.A_RISQUE),
        ]
        result = compute_action_recommandee(obs)
        assert result is not None
        assert "BACS" in result


# ========================================
# Tests: bacs_deadline_for_power
# ========================================

class TestBacsDeadlineForPower:
    def test_above_290(self):
        assert bacs_deadline_for_power(350.0) == BACS_DEADLINE_290

    def test_above_70(self):
        assert bacs_deadline_for_power(150.0) == BACS_DEADLINE_70

    def test_below_70(self):
        assert bacs_deadline_for_power(50.0) is None

    def test_boundary_290(self):
        assert bacs_deadline_for_power(290.0) == BACS_DEADLINE_70  # =290 -> seuil bas (>70)
        assert bacs_deadline_for_power(290.1) == BACS_DEADLINE_290  # >290 -> seuil haut

    def test_boundary_70(self):
        assert bacs_deadline_for_power(70.0) is None  # not strictly >70
        assert bacs_deadline_for_power(70.1) == BACS_DEADLINE_70


# ========================================
# Tests: compute_bacs_statut
# ========================================

class TestComputeBacsStatut:
    def test_valid_attestation_gives_conforme(self):
        evs = [_make_evidence(ev_type=TypeEvidence.ATTESTATION_BACS, statut=StatutEvidence.VALIDE)]
        result = compute_bacs_statut(evs, date(2025, 1, 1), today=date(2026, 1, 1))
        assert result == StatutConformite.CONFORME

    def test_valid_derogation_takes_priority(self):
        evs = [
            _make_evidence(ev_type=TypeEvidence.ATTESTATION_BACS, statut=StatutEvidence.VALIDE),
            _make_evidence(ev_type=TypeEvidence.DEROGATION_BACS, statut=StatutEvidence.VALIDE),
        ]
        result = compute_bacs_statut(evs, date(2025, 1, 1), today=date(2026, 1, 1))
        assert result == StatutConformite.DEROGATION

    def test_no_evidence_deadline_passed_gives_non_conforme(self):
        result = compute_bacs_statut([], date(2025, 1, 1), today=date(2026, 6, 1))
        assert result == StatutConformite.NON_CONFORME

    def test_no_evidence_deadline_future_gives_a_risque(self):
        result = compute_bacs_statut([], date(2030, 1, 1), today=date(2026, 1, 1))
        assert result == StatutConformite.A_RISQUE

    def test_expired_attestation_not_counted(self):
        evs = [_make_evidence(ev_type=TypeEvidence.ATTESTATION_BACS, statut=StatutEvidence.EXPIRE)]
        result = compute_bacs_statut(evs, date(2025, 1, 1), today=date(2026, 1, 1))
        assert result == StatutConformite.NON_CONFORME

    def test_pending_derogation_not_counted(self):
        evs = [_make_evidence(ev_type=TypeEvidence.DEROGATION_BACS, statut=StatutEvidence.EN_ATTENTE)]
        result = compute_bacs_statut(evs, date(2025, 1, 1), today=date(2026, 1, 1))
        assert result == StatutConformite.NON_CONFORME

    def test_unrelated_evidence_ignored(self):
        evs = [_make_evidence(ev_type=TypeEvidence.AUDIT, statut=StatutEvidence.VALIDE)]
        result = compute_bacs_statut(evs, date(2025, 1, 1), today=date(2026, 1, 1))
        assert result == StatutConformite.NON_CONFORME


# ========================================
# Tests: compute_site_snapshot
# ========================================

class TestComputeSiteSnapshot:
    def test_no_obligations_defaults(self):
        snapshot = compute_site_snapshot([])
        assert snapshot["statut_decret_tertiaire"] == StatutConformite.A_RISQUE
        assert snapshot["avancement_decret_pct"] == 0.0
        assert snapshot["statut_bacs"] == StatutConformite.A_RISQUE
        assert snapshot["risque_financier_euro"] == 0.0
        assert snapshot["action_recommandee"] is None

    def test_all_conforme(self):
        obs = [
            _make_obligation(ob_type=TypeObligation.DECRET_TERTIAIRE,
                             statut=StatutConformite.CONFORME, avancement_pct=85.0),
            _make_obligation(ob_type=TypeObligation.BACS,
                             statut=StatutConformite.CONFORME, avancement_pct=100.0),
        ]
        snapshot = compute_site_snapshot(obs)
        assert snapshot["statut_decret_tertiaire"] == StatutConformite.CONFORME
        assert snapshot["statut_bacs"] == StatutConformite.CONFORME
        assert snapshot["risque_financier_euro"] == 0.0
        assert snapshot["action_recommandee"] is None

    def test_mixed_picks_worst(self):
        obs = [
            _make_obligation(ob_type=TypeObligation.DECRET_TERTIAIRE,
                             statut=StatutConformite.CONFORME, avancement_pct=80.0),
            _make_obligation(ob_type=TypeObligation.DECRET_TERTIAIRE,
                             statut=StatutConformite.NON_CONFORME, avancement_pct=20.0),
        ]
        snapshot = compute_site_snapshot(obs)
        assert snapshot["statut_decret_tertiaire"] == StatutConformite.NON_CONFORME
        assert snapshot["avancement_decret_pct"] == 50.0
        assert snapshot["risque_financier_euro"] == BASE_PENALTY_EURO

    def test_only_bacs(self):
        obs = [
            _make_obligation(ob_type=TypeObligation.BACS,
                             statut=StatutConformite.NON_CONFORME, avancement_pct=30.0),
        ]
        snapshot = compute_site_snapshot(obs)
        assert snapshot["statut_decret_tertiaire"] == StatutConformite.A_RISQUE
        assert snapshot["avancement_decret_pct"] == 0.0
        assert snapshot["statut_bacs"] == StatutConformite.NON_CONFORME
        assert snapshot["risque_financier_euro"] == BASE_PENALTY_EURO

    def test_bacs_recomputed_from_evidences(self):
        """When evidences passed, BACS statut is recomputed from them."""
        obs = [
            _make_obligation(ob_type=TypeObligation.BACS,
                             statut=StatutConformite.A_RISQUE, avancement_pct=50.0,
                             echeance=date(2025, 1, 1)),
        ]
        evs = [_make_evidence(ev_type=TypeEvidence.ATTESTATION_BACS, statut=StatutEvidence.VALIDE)]
        snapshot = compute_site_snapshot(obs, evidences=evs)
        assert snapshot["statut_bacs"] == StatutConformite.CONFORME

    def test_bacs_non_conforme_when_deadline_passed_no_evidence(self):
        obs = [
            _make_obligation(ob_type=TypeObligation.BACS,
                             statut=StatutConformite.A_RISQUE, avancement_pct=50.0,
                             echeance=date(2025, 1, 1)),
        ]
        snapshot = compute_site_snapshot(obs, evidences=[])
        assert snapshot["statut_bacs"] == StatutConformite.NON_CONFORME

    def test_without_evidences_keeps_original_statut(self):
        """When evidences=None (legacy), BACS statut stays as-is."""
        obs = [
            _make_obligation(ob_type=TypeObligation.BACS,
                             statut=StatutConformite.CONFORME, avancement_pct=100.0),
        ]
        snapshot = compute_site_snapshot(obs)  # no evidences
        assert snapshot["statut_bacs"] == StatutConformite.CONFORME


# ========================================
# Tests: Database persistence
# ========================================

class TestRecomputeSite:
    def test_updates_site(self, db_session):
        _, _, _, site1, _ = _seed_hierarchy(db_session)

        result = recompute_site(db_session, site1.id)

        assert result["statut_decret_tertiaire"] == StatutConformite.NON_CONFORME
        # Site1 has valid ATTESTATION_BACS + deadline 2025 passed -> CONFORME
        assert result["statut_bacs"] == StatutConformite.CONFORME
        assert result["avancement_decret_pct"] == 30.0

        db_session.refresh(site1)
        assert site1.statut_decret_tertiaire == StatutConformite.NON_CONFORME
        assert site1.statut_bacs == StatutConformite.CONFORME

    def test_nonexistent_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            recompute_site(db_session, site_id=9999)


class TestRecomputePortfolio:
    def test_recomputes_all_sites(self, db_session):
        _, _, pf, site1, site2 = _seed_hierarchy(db_session)

        result = recompute_portfolio(db_session, pf.id)

        assert result["sites_recomputed"] == 2

        db_session.refresh(site1)
        db_session.refresh(site2)
        assert site1.statut_decret_tertiaire == StatutConformite.NON_CONFORME
        assert site2.statut_decret_tertiaire == StatutConformite.CONFORME

    def test_nonexistent_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            recompute_portfolio(db_session, portefeuille_id=9999)


class TestRecomputeOrganisation:
    def test_traverses_hierarchy(self, db_session):
        org, _, _, site1, _ = _seed_hierarchy(db_session)

        result = recompute_organisation(db_session, org.id)

        assert result["sites_recomputed"] == 2
        assert result["organisation_nom"] == "Test Org"

        db_session.refresh(site1)
        assert site1.statut_decret_tertiaire == StatutConformite.NON_CONFORME

    def test_nonexistent_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            recompute_organisation(db_session, organisation_id=9999)
