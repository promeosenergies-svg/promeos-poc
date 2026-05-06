"""
PROMEOS — Tests Site.s_ce_m2 Phase 7.1 Sprint C-7 (clôture D-Phase4-2-Operat-Surfaces-3-Distinct).

Couverture cardinal :
- Site CRUD avec s_ce_m2 (default NULL, set valeur, sérialisation)
- 3 surfaces distinctes preuve séparation (SDP / tertiaire / S_CE)
- Validation Float optionnel (pas de default imposé MVP)
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
    """In-memory SQLite avec schema déployé."""
    from models import Base

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_site(db, **kwargs):
    """Helper : Org → EJ → PF → Site avec kwargs Site optionnels."""
    from models import (
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )

    org = Organisation(nom="OrgPhase71", siren="800000001")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom="EJPhase71", siren="800000001", organisation_id=org.id)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom="PFPhase71", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    site = Site(
        nom="SitePhase71",
        type=TypeSite.BUREAU,
        actif=True,
        portefeuille_id=pf.id,
        **kwargs,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def test_site_s_ce_m2_default_null(db_session):
    """Phase 7.1 : par défaut s_ce_m2 = None (champ optionnel)."""
    site = _seed_site(db_session)
    assert site.s_ce_m2 is None


def test_site_s_ce_m2_set_positive_value(db_session):
    """Phase 7.1 : s_ce_m2 set valeur positive persiste correctement."""
    site = _seed_site(db_session, s_ce_m2=1250.50)

    db_session.refresh(site)
    assert site.s_ce_m2 == 1250.50


def test_site_3_surfaces_distinct_independent(db_session):
    """Phase 7.1 CARDINAL : 3 surfaces distinctes Site (SDP / tertiaire / S_CE) indépendantes.

    Cohérent doctrine clôture D-Phase4-2-Operat-Surfaces-3-Distinct-001 :
    - surface_m2 = SDP (Surface De Plancher) — Code construction art. R111-22
    - tertiaire_area_m2 = surface tertiaire assujettie OPERAT (sous-périmètre SDP)
    - s_ce_m2 = Surface CE OPERAT — Arrêté 10/04/2020 art. 2-j (inclut parking intérieur + locaux techniques)

    S_CE est typiquement > SDP (intègre stationnement intérieur + locaux techniques).
    """
    site = _seed_site(
        db_session,
        surface_m2=1000.0,  # SDP
        tertiaire_area_m2=900.0,  # sous-périmètre tertiaire OPERAT
        s_ce_m2=1150.0,  # > SDP : ajoute parking intérieur (+150 m²)
    )

    db_session.refresh(site)
    # 3 surfaces distinctes, valeurs différentes confirmées
    assert site.surface_m2 == 1000.0
    assert site.tertiaire_area_m2 == 900.0
    assert site.s_ce_m2 == 1150.0
    # Vérifier ordre cardinal : tertiaire ≤ SDP < S_CE (cas typique)
    assert site.tertiaire_area_m2 <= site.surface_m2 < site.s_ce_m2


def test_site_s_ce_m2_can_equal_surface_m2(db_session):
    """Phase 7.1 : S_CE peut être égal à SDP si pas de parking intérieur ni locaux techniques."""
    site = _seed_site(
        db_session,
        surface_m2=500.0,
        s_ce_m2=500.0,  # Cas dégénéré : SDP = S_CE
    )

    db_session.refresh(site)
    assert site.s_ce_m2 == site.surface_m2 == 500.0


def test_site_s_ce_m2_precision_decimal(db_session):
    """Phase 7.1 : s_ce_m2 supporte décimales (Float Numeric)."""
    site = _seed_site(db_session, s_ce_m2=1234.56)

    db_session.refresh(site)
    assert site.s_ce_m2 == 1234.56


def test_site_s_ce_m2_optional_no_default_imposed(db_session):
    """Phase 7.1 : nullable=True, pas de default — peut rester None pour sites legacy."""
    from models import Site

    site = _seed_site(db_session)  # pas de s_ce_m2 fourni
    assert site.s_ce_m2 is None

    # Update explicite à NULL OK
    site.s_ce_m2 = None
    db_session.commit()
    db_session.refresh(site)
    assert site.s_ce_m2 is None


def test_site_s_ce_m2_can_be_set_post_creation(db_session):
    """Phase 7.1 : champ peut être ajouté post-création (migration progressive sites legacy)."""
    site = _seed_site(db_session, surface_m2=2000.0, tertiaire_area_m2=1800.0)
    assert site.s_ce_m2 is None  # initialement NULL

    # Ajout S_CE post-création (cas migration progressive)
    site.s_ce_m2 = 2300.0  # SDP 2000 + parking intérieur 300
    db_session.commit()
    db_session.refresh(site)
    assert site.s_ce_m2 == 2300.0
