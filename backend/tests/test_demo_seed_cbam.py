"""Tests seed CBAM fields (P3 wedge) + migration + wiring cost_simulator."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import EntiteJuridique, Organisation, Portefeuille, Site
from models.base import Base
from models.enums import TypeSite
from models.market_models import (
    MarketDataSource,
    MarketType,
    MktPrice,
    PriceZone,
    ProductType,
    Resolution,
)
from services.demo_seed.gen_cbam_fields import CBAM_PROFILES_BY_ARCHETYPE, seed_cbam_fields
from services.purchase.cost_simulator_2026 import simulate_annual_cost_2026


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_site(db, archetype: str, nom: str = "Test Site") -> Site:
    import uuid

    siren = uuid.uuid4().hex[:9].upper()
    org = Organisation(nom=f"Org {siren}", type_client="industrie", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren=siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        nom=nom,
        type=TypeSite.COMMERCE,
        portefeuille_id=pf.id,
        annual_kwh_total=500_000,
        archetype_code=archetype,
    )
    db.add(site)
    db.flush()
    return site


def test_seed_cbam_populise_site_industrie_legere(db_session):
    """Un site INDUSTRIE_LEGERE sans CBAM → seedé avec acier+alu."""
    site = _make_site(db_session, archetype="INDUSTRIE_LEGERE")
    assert site.cbam_imports_tonnes is None

    stats = seed_cbam_fields(db_session, [site])
    assert stats["updated"] == 1
    assert site.cbam_imports_tonnes == CBAM_PROFILES_BY_ARCHETYPE["INDUSTRIE_LEGERE"]


def test_seed_cbam_idempotent_skip_si_deja_renseigne(db_session):
    """Un site avec cbam_imports_tonnes déjà rempli → skip (pas d'écrasement)."""
    site = _make_site(db_session, archetype="INDUSTRIE_LEGERE")
    # Valeur custom pré-existante (simule saisie utilisateur)
    site.cbam_imports_tonnes = {"acier": 999.0}
    db_session.flush()

    stats = seed_cbam_fields(db_session, [site])
    assert stats["updated"] == 0
    assert stats["skipped_existing"] == 1
    # La valeur custom est préservée
    assert site.cbam_imports_tonnes == {"acier": 999.0}


def test_seed_cbam_skip_archetype_sans_profil(db_session):
    """Site BUREAU_STANDARD → pas de profil CBAM (tertiaire n'importe pas)."""
    site = _make_site(db_session, archetype="BUREAU_STANDARD")
    stats = seed_cbam_fields(db_session, [site])
    assert stats["updated"] == 0
    assert stats["skipped_no_profile"] == 1
    assert site.cbam_imports_tonnes is None


def test_cost_simulator_lit_cbam_imports_tonnes_depuis_colonne(db_session):
    """Après migration, `site.cbam_imports_tonnes` est une vraie colonne lue par le simulator."""
    site = _make_site(db_session, archetype="INDUSTRIE_LEGERE")
    # Seed à la volée
    stats = seed_cbam_fields(db_session, [site])
    assert stats["updated"] == 1

    # Seed forward 2026
    db_session.add(
        MktPrice(
            source=MarketDataSource.MANUAL,
            market_type=MarketType.FORWARD_YEAR,
            product_type=ProductType.BASELOAD,
            zone=PriceZone.FR,
            delivery_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            delivery_end=datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            price_eur_mwh=62.0,
            resolution=Resolution.P1Y,
            fetched_at=datetime.now(timezone.utc),
        )
    )
    db_session.flush()

    result = simulate_annual_cost_2026(site, db_session, year=2026)
    # INDUSTRIE_LEGERE seedé : acier 50t + alu 8t
    # = (50 × 2.0 + 8 × 16.5) × 75.36 = (100 + 132) × 75.36 = 17 483.52 €
    expected = (50.0 * 2.0 + 8.0 * 16.5) * 75.36
    assert result["composantes"]["cbam_scope"] == pytest.approx(expected, rel=1e-3)
    assert result["hypotheses"]["cbam_applicable"] is True
    assert len(result["hypotheses"]["cbam_breakdown"]) == 2
