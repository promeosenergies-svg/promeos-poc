"""
PROMEOS — Tests cascade Org consentement VIVANTE (Sprint C-4 Phase 4.5, ADR-007).

Vérifie l'activation runtime de la cascade Org.consentement_*_global → DPs après
livraison du modèle Phase 4.4 (8 cols ORM).

Particularités cardinales testées :
- Override local DP préservé (ADR-007 Option B archi-helios)
- Helper get_effective_consent runtime : effective = _local IF NOT NULL ELSE _global
- COURT-CIRCUIT ELD locales préservé pour cascade GRDF (différenciateur Sprint C-3 P3.6)
- Audit log automatique RGPD via Sprint C-2 P1.3 wiring

Clôture dettes :
- D-Sprint-C3-Cascade-Consentement-Activation-001 (P1, Sprint C-3 → C-4)
- D-Sprint-C3-7d-Cascade-SoT-Reuse-Audit-001 (P1, audit rapide Phase 4.5.4 — pas de
  duplication détectée vs services existants)
"""

from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def db_session():
    """In-memory SQLite avec schema déployé (modèles ORM appliqués)."""
    from models import Base
    from models.organisation import Organisation  # noqa: F401
    from models.patrimoine import DeliveryPoint  # noqa: F401

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def org_with_dps(db_session):
    """Org HELIOS avec 5 DPs : 2 élec + 3 gaz (1 GRDF + 2 ELD locales)."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.patrimoine import DeliveryPoint, DeliveryPointEnergyType

    org = Organisation(nom="Org HELIOS Test")
    db_session.add(org)
    db_session.flush()
    ej = EntiteJuridique(nom="EJ HELIOS", siren="123456789", organisation_id=org.id)
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(nom="PF HELIOS", entite_juridique_id=ej.id)
    db_session.add(pf)
    db_session.flush()
    site = Site(nom="Site HELIOS", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
    db_session.add(site)
    db_session.flush()

    # 2 DPs élec
    dp_elec_1 = DeliveryPoint(
        code="11111111111111", site_id=site.id, energy_type=DeliveryPointEnergyType.ELEC, grd_code="ENEDIS"
    )
    dp_elec_2 = DeliveryPoint(
        code="22222222222222", site_id=site.id, energy_type=DeliveryPointEnergyType.ELEC, grd_code="ENEDIS"
    )
    # 1 DP gaz GRDF
    dp_gaz_grdf = DeliveryPoint(
        code="33333333333333", site_id=site.id, energy_type=DeliveryPointEnergyType.GAZ, grd_code="GRDF"
    )
    # 2 DPs gaz ELD locales (court-circuit cardinal)
    dp_gaz_eld_1 = DeliveryPoint(
        code="44444444444444", site_id=site.id, energy_type=DeliveryPointEnergyType.GAZ, grd_code="REGAZ"
    )
    dp_gaz_eld_2 = DeliveryPoint(
        code="55555555555555", site_id=site.id, energy_type=DeliveryPointEnergyType.GAZ, grd_code="GREENALP"
    )
    db_session.add_all([dp_elec_1, dp_elec_2, dp_gaz_grdf, dp_gaz_eld_1, dp_gaz_eld_2])
    db_session.commit()

    return {
        "org": org,
        "site": site,
        "dp_elec_1": dp_elec_1,
        "dp_elec_2": dp_elec_2,
        "dp_gaz_grdf": dp_gaz_grdf,
        "dp_gaz_eld_1": dp_gaz_eld_1,
        "dp_gaz_eld_2": dp_gaz_eld_2,
    }


# ─── 1. Cascade Org.consentement_dataconnect_global → DPs élec ───────────────


def test_cascade_dataconnect_eligible_2_dps_elec_no_override(db_session, org_with_dps):
    """SG_CASCADE_DC_01 : Org consentement DataConnect=True → 2 DPs élec éligibles
    (sans override local) + 3 DPs gaz skipped."""
    from regops.services.cascade_recompute_service import _propagate_consentement_dataconnect

    org_with_dps["org"].consentement_dataconnect_global = True
    db_session.commit()

    result = _propagate_consentement_dataconnect(org_with_dps["org"], db_session)
    assert "eligible=2" in result
    assert "overridden=0" in result
    assert "skipped_gas=3" in result


def test_cascade_dataconnect_local_override_preserved(db_session, org_with_dps):
    """SG_CASCADE_DC_02 : DP avec override local non écrasé par cascade Org global."""
    from regops.services.cascade_recompute_service import _propagate_consentement_dataconnect

    # DP elec_1 a un override local explicite
    org_with_dps["dp_elec_1"].consentement_dataconnect_local = False
    org_with_dps["org"].consentement_dataconnect_global = True
    db_session.commit()

    result = _propagate_consentement_dataconnect(org_with_dps["org"], db_session)
    assert "overridden=1" in result, "DP avec override local doit être compté overridden"
    assert "eligible=1" in result, "Reste 1 DP élec sans override = éligible"


def test_cascade_dataconnect_no_change_when_global_null(db_session, org_with_dps):
    """SG_CASCADE_DC_03 : Org global=None → cascade no-op (pas de propagation)."""
    from regops.services.cascade_recompute_service import _propagate_consentement_dataconnect

    # Global reste None
    result = _propagate_consentement_dataconnect(org_with_dps["org"], db_session)
    assert result == "no_change_global_is_null"


# ─── 2. Cascade Org.consentement_grdf_global → DPs grd_code='GRDF' UNIQUEMENT ─


def test_cascade_grdf_court_circuit_eld_locales(db_session, org_with_dps):
    """SG_CASCADE_GRDF_01 CARDINAL : cascade GRDF cible UNIQUEMENT grd_code='GRDF',
    pas les ELD locales (Régaz, GreenAlp). Différenciateur PROMEOS RGPD.
    """
    from regops.services.cascade_recompute_service import _propagate_consentement_grdf

    org_with_dps["org"].consentement_grdf_global = True
    db_session.commit()

    result = _propagate_consentement_grdf(org_with_dps["org"], db_session)
    # 1 DP GRDF éligible (dp_gaz_grdf)
    assert "eligible=1" in result
    # 2 DPs ELD locales SKIPPED (Régaz + GreenAlp)
    assert "skipped_eld=2" in result, "Court-circuit ELD locales DOIT être actif (les 20 ELD ont leur propre process)"
    # 2 DPs élec skipped (cascade GRDF ne touche pas l'élec)
    assert "skipped_elec=2" in result


def test_cascade_grdf_local_override_preserved_on_grdf_dp(db_session, org_with_dps):
    """SG_CASCADE_GRDF_02 : DP GRDF avec override local respecté."""
    from regops.services.cascade_recompute_service import _propagate_consentement_grdf

    org_with_dps["dp_gaz_grdf"].consentement_grdf_local = False
    org_with_dps["org"].consentement_grdf_global = True
    db_session.commit()

    result = _propagate_consentement_grdf(org_with_dps["org"], db_session)
    assert "overridden=1" in result
    assert "eligible=0" in result, "Le seul DP GRDF a un override → 0 éligibles"


def test_cascade_grdf_no_change_when_global_null(db_session, org_with_dps):
    """SG_CASCADE_GRDF_03 : Org global GRDF=None → cascade no-op."""
    from regops.services.cascade_recompute_service import _propagate_consentement_grdf

    result = _propagate_consentement_grdf(org_with_dps["org"], db_session)
    assert result == "no_change_global_is_null"


# ─── 3. Helper get_effective_consent (Option B archi-helios) ─────────────────


def test_get_effective_consent_local_override_priority(db_session, org_with_dps):
    """SG_EFFECTIVE_01 : override local prioritaire vs global Org."""
    from services.consent_service import get_effective_consent

    org_with_dps["org"].consentement_dataconnect_global = True
    org_with_dps["dp_elec_1"].consentement_dataconnect_local = False
    db_session.commit()

    # DP elec_1 a override local = False → effective doit être False (override prioritaire)
    assert get_effective_consent(org_with_dps["dp_elec_1"], "dataconnect") is False


def test_get_effective_consent_falls_back_to_global_when_local_null(db_session, org_with_dps):
    """SG_EFFECTIVE_02 : si _local null, remonte au global Org."""
    from services.consent_service import get_effective_consent

    org_with_dps["org"].consentement_dataconnect_global = True
    # dp_elec_2 n'a pas d'override local
    db_session.commit()

    assert get_effective_consent(org_with_dps["dp_elec_2"], "dataconnect") is True


def test_get_effective_consent_returns_none_when_both_null(db_session, org_with_dps):
    """SG_EFFECTIVE_03 : both null → None (statut 'pas encore choisi')."""
    from services.consent_service import get_effective_consent

    # Aucun consentement défini ni org ni DP
    result = get_effective_consent(org_with_dps["dp_elec_1"], "dataconnect")
    assert result is None


def test_get_effective_consent_invalid_type_raises(db_session, org_with_dps):
    """SG_EFFECTIVE_04 : type_ inconnu lève ValueError (anti-typo)."""
    from services.consent_service import get_effective_consent

    with pytest.raises(ValueError, match="type_ inconnu"):
        get_effective_consent(org_with_dps["dp_elec_1"], "invalid_type")


def test_is_consent_active_returns_false_when_consent_is_none(db_session, org_with_dps):
    """SG_EFFECTIVE_05 : `is_consent_active` cardinal RGPD — None ≠ True."""
    from services.consent_service import is_consent_active

    # Aucun consentement défini
    assert is_consent_active(org_with_dps["dp_elec_1"], "dataconnect") is False


def test_is_consent_active_returns_true_only_explicit_true(db_session, org_with_dps):
    """SG_EFFECTIVE_06 : `is_consent_active` retourne True UNIQUEMENT si effective=True."""
    from services.consent_service import is_consent_active

    org_with_dps["org"].consentement_dataconnect_global = True
    db_session.commit()

    assert is_consent_active(org_with_dps["dp_elec_1"], "dataconnect") is True


def test_get_effective_consent_grdf_court_circuit_via_helper(db_session, org_with_dps):
    """SG_EFFECTIVE_07 : helper get_effective_consent(grdf) fonctionne sur DP GRDF
    et ELD locales (le helper lui-même ne court-circuite pas — c'est la cascade
    qui court-circuite). ELD locale lit aussi son global Org.
    """
    from services.consent_service import get_effective_consent

    org_with_dps["org"].consentement_grdf_global = True
    db_session.commit()

    # DP GRDF lit le global (pas d'override)
    assert get_effective_consent(org_with_dps["dp_gaz_grdf"], "grdf") is True
    # DP ELD locale lit AUSSI le global Org (helper neutre, court-circuit
    # est dans la cascade _propagate_consentement_grdf, pas dans le helper lecture)
    assert get_effective_consent(org_with_dps["dp_gaz_eld_1"], "grdf") is True


# ─── 4. CASCADE_MAP entries Phase 4.5 ────────────────────────────────────────


def test_cascade_map_includes_org_consentement_entries(db_session):
    """SG_CASCADE_MAP_01 : CASCADE_MAP a les 2 entrées Org.consentement_* (Phase 4.5)."""
    from regops.services.cascade_recompute_service import CASCADE_MAP_MVP_SPRINT_C1

    assert "Organisation.consentement_dataconnect_global" in CASCADE_MAP_MVP_SPRINT_C1
    assert "Organisation.consentement_grdf_global" in CASCADE_MAP_MVP_SPRINT_C1
    # Chaque entrée a au moins 1 callable
    assert len(CASCADE_MAP_MVP_SPRINT_C1["Organisation.consentement_dataconnect_global"]) >= 1
    assert len(CASCADE_MAP_MVP_SPRINT_C1["Organisation.consentement_grdf_global"]) >= 1
