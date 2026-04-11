"""Non-regression tests for flex scoring bugs fixed on fix/flex-scoring-bugs.

Covers:
1. flex_assessment_service._asset_based_assessment — composite score formula
   (nebco_component + inventory_component), replacing broken kw/(kw+10) asymptote.
2. flex_nebco_service.compute_flex_nebco — returns flex_score from base_assessment
   correctly (was reading wrong key "flex_potential_score" and always returning 0).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base
from models.flex_models import FlexAsset
from services.flex_assessment_service import compute_flex_assessment


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


def _seed_site(db):
    """Seed the minimum org/entité/portefeuille/site graph FlexAsset needs."""
    from models import Organisation, EntiteJuridique, Portefeuille, Site

    org = Organisation(nom="Test Org")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom="Test EJ", organisation_id=org.id, siren="123456789")
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom="Test PF", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    site = Site(nom="Test Site", portefeuille_id=pf.id, type="bureau")
    db.add(site)
    db.flush()
    return site.id


def _add_asset(db, site_id, power_kw, controllable=True, confidence="high", asset_type="hvac"):
    asset = FlexAsset(
        site_id=site_id,
        asset_type=asset_type,
        label=f"Asset {power_kw}kW",
        power_kw=power_kw,
        is_controllable=controllable,
        confidence=confidence,
        status="active",
    )
    db.add(asset)
    db.flush()
    return asset


# ── Asset-based score formula ──────────────────────────────────────────────


def test_score_100kw_fully_controllable_verified_scores_100(db_session):
    """100 kW pilotable, 100% contrôlable, 100% vérifié → 100/100 (seuil NEBCO atteint)."""
    site_id = _seed_site(db_session)
    # hvac factor = 0.6, so 167 kW nameplate ≈ 100 kW pilotable
    _add_asset(db_session, site_id, power_kw=167, controllable=True, confidence="high")
    result = compute_flex_assessment(db_session, site_id)
    assert result["potential_kw"] >= 100
    assert result["flex_score"] == 100


def test_score_small_site_5kw_not_zero(db_session):
    """Petit site 5 kW flex, full controllable + verified → score > 50 (qualité inventaire)."""
    site_id = _seed_site(db_session)
    # 8.33 kW nameplate * 0.6 = 5 kW pilotable
    _add_asset(db_session, site_id, power_kw=8.33, controllable=True, confidence="high")
    result = compute_flex_assessment(db_session, site_id)
    # 5 kW → nebco_component = 2.5, inventory = 50 → 52 (rounded)
    assert 50 <= result["flex_score"] <= 55


def test_score_non_controllable_zero_pilotable_returns_zero(db_session):
    """Asset non contrôlable → 0 kW pilotable → score 0 (aucune valeur flex)."""
    site_id = _seed_site(db_session)
    _add_asset(db_session, site_id, power_kw=500, controllable=False, confidence="unverified")
    result = compute_flex_assessment(db_session, site_id)
    # 0 kW pilotable → nebco_component = 0, inventory: 0/1 + 0/1 = 0 → 0
    assert result["flex_score"] == 0


def test_score_mixed_assets_weighted_inventory(db_session):
    """Mix 2 assets : 1 contrôlable vérifié + 1 non. Vérifie la pondération inventaire."""
    site_id = _seed_site(db_session)
    _add_asset(db_session, site_id, power_kw=167, controllable=True, confidence="high")
    _add_asset(db_session, site_id, power_kw=100, controllable=False, confidence="low")
    result = compute_flex_assessment(db_session, site_id)
    # pilotable = 167*0.6 + 0 = 100 kW → nebco = 50
    # inventory: 1/2 controllable * 25 + 1/2 verified * 25 = 25
    # total = 75
    assert 70 <= result["flex_score"] <= 80


# ── NEBCO service score key propagation ──────────────────────────────────


def test_nebco_service_propagates_flex_score(db_session):
    """compute_flex_nebco doit retourner le flex_score de l'assessment (bug: lisait la mauvaise clé)."""
    from services.flex_nebco_service import compute_flex_nebco

    site_id = _seed_site(db_session)
    _add_asset(db_session, site_id, power_kw=167, controllable=True, confidence="high")

    result = compute_flex_nebco(db_session, site_id)
    # Before fix: always 0 because it read "flex_potential_score" (non-existent key).
    # After fix: reads "flex_score" correctly → should be 100 for this setup.
    assert result["flex_score"] == 100
