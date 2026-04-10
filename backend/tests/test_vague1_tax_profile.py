"""
PROMEOS — Tests data model Vague 1 (TaxProfile + seed + enums).

Verrouille le comportement du nouveau modèle TaxProfile, du seed de
compatibilité, et des enums AcciseCategory* / NetworkCostModel.
"""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models.billing_models import EnergyContract
from models.enums import (
    AcciseCategoryElec,
    AcciseCategoryGaz,
    BillingEnergyType,
    DeliveryPointEnergyType,
    NetworkCostModel,
    TariffSegmentEnum,
)
from models.patrimoine import DeliveryPoint
from models.site import Site
from models.tax_profile import TaxProfile
from services.billing_engine.vague1_seed import (
    SeedSummary,
    _derive_grd_code,
    _derive_tax_profile_elec,
    seed_vague1,
)


# ── Enums ─────────────────────────────────────────────────────────────────


class TestEnums:
    def test_accise_elec_values(self):
        assert AcciseCategoryElec.HOUSEHOLD.value == "HOUSEHOLD"
        assert AcciseCategoryElec.SME.value == "SME"
        assert AcciseCategoryElec.HIGH_POWER.value == "HIGH_POWER"
        assert AcciseCategoryElec.REDUCED.value == "REDUCED"
        assert AcciseCategoryElec.EXEMPT.value == "EXEMPT"

    def test_accise_gaz_values(self):
        assert AcciseCategoryGaz.NORMAL.value == "NORMAL"
        assert AcciseCategoryGaz.REDUCED.value == "REDUCED"
        assert AcciseCategoryGaz.EXEMPT.value == "EXEMPT"

    def test_network_cost_model_values(self):
        assert NetworkCostModel.INCLUDED.value == "INCLUDED"
        assert NetworkCostModel.FULL_PASS_THROUGH.value == "FULL_PASS_THROUGH"
        assert NetworkCostModel.FLAT_UNIT_COST.value == "FLAT_UNIT_COST"
        assert NetworkCostModel.MARGINATED.value == "MARGINATED"


# ── Dérivation GRD / TaxProfile (pure, sans DB) ──────────────────────────


class TestDerivation:
    def test_derive_grd_elec(self):
        assert _derive_grd_code("elec") == "ENEDIS"
        assert _derive_grd_code("electricity") == "ENEDIS"
        assert _derive_grd_code("ELEC") == "ENEDIS"

    def test_derive_grd_gaz(self):
        assert _derive_grd_code("gaz") == "GRDF"
        assert _derive_grd_code("gas") == "GRDF"
        assert _derive_grd_code("GAZ") == "GRDF"

    def test_derive_grd_unknown(self):
        assert _derive_grd_code(None) is None
        assert _derive_grd_code("unknown") is None
        assert _derive_grd_code("") is None

    def test_derive_tax_profile_elec_segments(self):
        assert _derive_tax_profile_elec("C5_BT") == AcciseCategoryElec.HOUSEHOLD
        assert _derive_tax_profile_elec("C4_BT") == AcciseCategoryElec.SME
        assert _derive_tax_profile_elec("C3_HTA") == AcciseCategoryElec.HIGH_POWER

    def test_derive_tax_profile_elec_fallback(self):
        assert _derive_tax_profile_elec(None) == AcciseCategoryElec.HOUSEHOLD
        assert _derive_tax_profile_elec("UNKNOWN") == AcciseCategoryElec.HOUSEHOLD


# ── TaxProfile model (CRUD avec DB) ──────────────────────────────────────


@pytest.fixture
def db_session():
    """In-memory SQLite avec tous les models chargés."""
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


@pytest.fixture
def db_with_pdl(db_session: Session):
    """Fixture : crée un site + 1 PDL élec + 1 PDL gaz."""
    site = Site(nom="TestSite", type="bureau", surface_m2=1000)
    db_session.add(site)
    db_session.flush()

    pdl_elec = DeliveryPoint(
        code="30000000000001",
        energy_type=DeliveryPointEnergyType.ELEC,
        tariff_segment=TariffSegmentEnum.C4_BT,
        site_id=site.id,
        puissance_souscrite_kva=60.0,
    )
    pdl_gaz = DeliveryPoint(
        code="70000000000002",
        energy_type=DeliveryPointEnergyType.GAZ,
        site_id=site.id,
    )
    db_session.add_all([pdl_elec, pdl_gaz])
    db_session.commit()
    return db_session, site, pdl_elec, pdl_gaz


class TestTaxProfileModel:
    def test_create_elec_profile(self, db_with_pdl):
        db, _, pdl_elec, _ = db_with_pdl
        tp = TaxProfile(
            delivery_point_id=pdl_elec.id,
            accise_category_elec=AcciseCategoryElec.SME,
            regime_reduit=False,
        )
        db.add(tp)
        db.commit()
        assert tp.id is not None
        assert tp.accise_category_elec == AcciseCategoryElec.SME
        assert tp.accise_category_gaz is None

    def test_create_gaz_profile(self, db_with_pdl):
        db, _, _, pdl_gaz = db_with_pdl
        tp = TaxProfile(
            delivery_point_id=pdl_gaz.id,
            accise_category_gaz=AcciseCategoryGaz.NORMAL,
            regime_reduit=False,
        )
        db.add(tp)
        db.commit()
        assert tp.accise_category_gaz == AcciseCategoryGaz.NORMAL
        assert tp.accise_category_elec is None

    def test_create_reduced_regime_with_attestation(self, db_with_pdl):
        db, _, pdl_elec, _ = db_with_pdl
        tp = TaxProfile(
            delivery_point_id=pdl_elec.id,
            accise_category_elec=AcciseCategoryElec.REDUCED,
            regime_reduit=True,
            attestation_ref="ARRETE-2024-001",
            eligibility_code="CIBS_L266",
            valid_from=date(2024, 1, 1),
        )
        db.add(tp)
        db.commit()
        assert tp.regime_reduit is True
        assert tp.attestation_ref == "ARRETE-2024-001"
        assert tp.valid_from == date(2024, 1, 1)
        assert tp.valid_to is None

    def test_repr_contains_category(self, db_with_pdl):
        db, _, pdl_elec, _ = db_with_pdl
        tp = TaxProfile(
            delivery_point_id=pdl_elec.id,
            accise_category_elec=AcciseCategoryElec.HOUSEHOLD,
        )
        db.add(tp)
        db.commit()
        r = repr(tp)
        assert "TaxProfile" in r
        assert "HOUSEHOLD" in r


# ── Nouvelles colonnes sur modèles existants ────────────────────────────


class TestExistingModelColumns:
    def test_delivery_point_has_grd_code(self, db_with_pdl):
        db, _, pdl_elec, _ = db_with_pdl
        pdl_elec.grd_code = "ENEDIS"
        db.commit()
        assert pdl_elec.grd_code == "ENEDIS"

    def test_energy_contract_pass_through_defaults(self, db_with_pdl):
        db, site, _, _ = db_with_pdl
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
        )
        db.add(contract)
        db.commit()
        # DB defaults
        assert contract.cee_pass_through is False
        assert contract.accise_pass_through is True
        # network_cost_model nullable par défaut
        assert contract.network_cost_model is None

    def test_energy_contract_network_cost_model_assignment(self, db_with_pdl):
        db, site, _, _ = db_with_pdl
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Engie",
            network_cost_model=NetworkCostModel.FULL_PASS_THROUGH,
        )
        db.add(contract)
        db.commit()
        assert contract.network_cost_model == NetworkCostModel.FULL_PASS_THROUGH


# ── Seed de compatibilité ────────────────────────────────────────────────


class TestSeedVague1:
    def test_seed_derives_grd_code(self, db_with_pdl):
        db, _, pdl_elec, pdl_gaz = db_with_pdl
        # Reset grd_code pour forcer la dérivation
        pdl_elec.grd_code = None
        pdl_gaz.grd_code = None
        db.commit()

        summary = seed_vague1(db)

        db.refresh(pdl_elec)
        db.refresh(pdl_gaz)
        assert pdl_elec.grd_code == "ENEDIS"
        assert pdl_gaz.grd_code == "GRDF"
        assert summary.grd_codes_set >= 2

    def test_seed_creates_tax_profiles(self, db_with_pdl):
        db, _, pdl_elec, pdl_gaz = db_with_pdl
        # Nettoyer les profils existants pour les 2 PDLs
        db.query(TaxProfile).filter(TaxProfile.delivery_point_id.in_([pdl_elec.id, pdl_gaz.id])).delete(
            synchronize_session=False
        )
        db.commit()

        summary = seed_vague1(db)

        assert summary.tax_profiles_created >= 2

        tp_elec = db.query(TaxProfile).filter(TaxProfile.delivery_point_id == pdl_elec.id).first()
        tp_gaz = db.query(TaxProfile).filter(TaxProfile.delivery_point_id == pdl_gaz.id).first()
        assert tp_elec is not None
        assert tp_elec.accise_category_elec == AcciseCategoryElec.SME  # C4_BT
        assert tp_gaz is not None
        assert tp_gaz.accise_category_gaz == AcciseCategoryGaz.NORMAL

    def test_seed_idempotent(self, db_with_pdl):
        db, _, pdl_elec, pdl_gaz = db_with_pdl
        # 1er run
        summary1 = seed_vague1(db)
        # 2e run doit être no-op sur les profils déjà créés
        summary2 = seed_vague1(db)
        assert summary2.tax_profiles_created == 0
        assert summary2.grd_codes_set == 0
        # skipped_already_populated doit être non-nul
        assert summary2.skipped_already_populated > 0

    def test_seed_returns_summary_dataclass(self, db_with_pdl):
        db, _, _, _ = db_with_pdl
        summary = seed_vague1(db)
        assert isinstance(summary, SeedSummary)
        assert isinstance(summary.grd_codes_set, int)
        assert isinstance(summary.tax_profiles_created, int)
        assert isinstance(summary.errors, list)
