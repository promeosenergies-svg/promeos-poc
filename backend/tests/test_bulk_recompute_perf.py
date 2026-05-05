"""
PROMEOS — Tests perf bulk recompute organisation (Sprint C-4 Phase 4.6).

Validation scalabilité PROMEOS avant pilote pré-prod via tests perf bulk
`recompute_organisation` (Sprint C-2 P5.2) + helpers cascade Phase 4.5.

Cibles perf :
- 50 sites < 2 sec (cible démo HELIOS étendu)
- 200 sites < 8 sec (cible portfolio mid-market)
- 500 sites < 25 sec (cible portfolio large)
- get_effective_consent x50 DPs < 500ms (helper Phase 4.5)
- cascade GRDF court-circuit ELD x500 DPs < 3 sec

⚠️ Tests marqués `@pytest.mark.perf` — exécution manuelle uniquement
(`venv/bin/python -m pytest -m perf`). Évite ralentissement CI standard.
Workflow CI dédié optionnel Sprint C-7+ (cf. note dans test).

Si cibles ratées : créer dette `D-Phase4-6-Bulk-Recompute-Perf-Optim-001` P1
Sprint C-7 polish (bulk SELECT N+1, lazy compliance, cache Redis).
"""

from __future__ import annotations

import os
import sys
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Fixtures bulk org (factory_boy bulk creation, in-memory test isolation) ──


@pytest.fixture
def db_session():
    """In-memory SQLite avec schema déployé pour tests perf."""
    from models import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _create_org_with_n_sites(db, n: int):
    """Crée une org avec N sites + 2 DPs/site (1 élec + 1 gaz GRDF) pour tests perf."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.patrimoine import DeliveryPoint, DeliveryPointEnergyType

    org = Organisation(nom=f"PerfTest_{n}_sites", siren="999999999")
    db.add(org)
    db.flush()

    ej = EntiteJuridique(nom=f"PerfEJ_{n}", siren="999999999", organisation_id=org.id)
    db.add(ej)
    db.flush()

    pf = Portefeuille(nom=f"PerfPF_{n}", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()

    for i in range(n):
        site = Site(
            nom=f"PerfSite_{i}",
            type=TypeSite.BUREAU,
            actif=True,
            portefeuille_id=pf.id,
            surface_m2=1000 + i,
            annual_kwh_total=100000 + i * 1000,
        )
        db.add(site)
        db.flush()

        # 1 DP élec ENEDIS + 1 DP gaz GRDF par site
        dp_elec = DeliveryPoint(
            code=f"{i:014d}"[:14],
            site_id=site.id,
            energy_type=DeliveryPointEnergyType.ELEC,
            grd_code="ENEDIS",
        )
        dp_gaz = DeliveryPoint(
            code=f"9{i:013d}"[:14],
            site_id=site.id,
            energy_type=DeliveryPointEnergyType.GAZ,
            grd_code="GRDF",
        )
        db.add_all([dp_elec, dp_gaz])

    db.commit()
    return org


@pytest.fixture
def org_with_50_sites(db_session):
    return _create_org_with_n_sites(db_session, 50)


@pytest.fixture
def org_with_200_sites(db_session):
    return _create_org_with_n_sites(db_session, 200)


@pytest.fixture
def org_with_500_sites(db_session):
    return _create_org_with_n_sites(db_session, 500)


# ─── 1. recompute_organisation perf (50/200/500 sites) ───────────────────────


@pytest.mark.perf
def test_recompute_organisation_50_sites_under_2sec(db_session, org_with_50_sites):
    """Cible : recompute 50 sites < 2 sec (démo HELIOS étendu)."""
    from services.compliance_coordinator import recompute_organisation

    start = time.time()
    result = recompute_organisation(db_session, org_with_50_sites.id)
    duration = time.time() - start

    assert result["sites_recomputed"] == 50
    assert duration < 2.0, f"50 sites recompute took {duration:.2f}s (cible <2s)"


@pytest.mark.perf
def test_recompute_organisation_200_sites_under_8sec(db_session, org_with_200_sites):
    """Cible : recompute 200 sites < 8 sec (portfolio mid-market)."""
    from services.compliance_coordinator import recompute_organisation

    start = time.time()
    result = recompute_organisation(db_session, org_with_200_sites.id)
    duration = time.time() - start

    assert result["sites_recomputed"] == 200
    assert duration < 8.0, f"200 sites recompute took {duration:.2f}s (cible <8s)"


@pytest.mark.perf
def test_recompute_organisation_500_sites_under_25sec(db_session, org_with_500_sites):
    """Cible : recompute 500 sites < 25 sec (portfolio large)."""
    from services.compliance_coordinator import recompute_organisation

    start = time.time()
    result = recompute_organisation(db_session, org_with_500_sites.id)
    duration = time.time() - start

    assert result["sites_recomputed"] == 500
    assert duration < 25.0, f"500 sites recompute took {duration:.2f}s (cible <25s)"


# ─── 2. Helpers Phase 4.5 (consent runtime) ──────────────────────────────────


@pytest.mark.perf
def test_get_effective_consent_50_dps_under_500ms(db_session, org_with_50_sites):
    """Cible : get_effective_consent sur 50 DPs élec < 500ms (helper Phase 4.5).

    Vérifie qu'aucune relation FK lazy load N+1 ne ralentit le helper.
    """
    from models.patrimoine import DeliveryPoint, DeliveryPointEnergyType
    from services.consent_service import get_effective_consent

    org_with_50_sites.consentement_dataconnect_global = True
    db_session.commit()

    dps_elec = (
        db_session.query(DeliveryPoint)
        .filter(DeliveryPoint.energy_type == DeliveryPointEnergyType.ELEC)
        .limit(50)
        .all()
    )
    assert len(dps_elec) == 50

    start = time.time()
    for dp in dps_elec:
        get_effective_consent(dp, "dataconnect")
    duration = time.time() - start

    assert duration < 0.5, f"get_effective_consent x50 took {duration:.3f}s (cible <500ms)"


@pytest.mark.perf
def test_cascade_grdf_court_circuit_500_dps_under_3sec(db_session, org_with_500_sites):
    """Cible : cascade GRDF court-circuit ELD sur 500 DPs gaz < 3 sec (Phase 4.5)."""
    from regops.services.cascade_recompute_service import _propagate_consentement_grdf

    org_with_500_sites.consentement_grdf_global = True
    db_session.commit()

    start = time.time()
    result = _propagate_consentement_grdf(org_with_500_sites, db_session)
    duration = time.time() - start

    assert "eligible=500" in result, f"500 DPs GRDF doivent être éligibles, got: {result}"
    assert duration < 3.0, f"Cascade GRDF 500 DPs took {duration:.2f}s (cible <3s)"
