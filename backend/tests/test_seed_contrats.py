"""
PROMEOS — Tests seed contrats cadre V2 (generate_cadre_contracts).
Idempotence + 4 cadres HELIOS + annexes + volumes.
Phase 6 CONTRATS-V2 QA.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    BillingEnergyType,
    ContractStatus,
)
from models.contract_v2_models import (
    ContratCadre,
    ContractAnnexe,
    ContractPricing,
    VolumeCommitment,
)
from services.demo_seed.gen_billing import generate_cadre_contracts


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def db():
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
def helios_setup(db):
    """Simulate HELIOS org with 5 sites (minimum for all 4 cadres)."""
    from models.enums import TypeSite

    org = Organisation(nom="HELIOS", siren="123456789", actif=True)
    db.add(org)
    db.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="HELIOS SAS", siren="987654321")
    db.add(ej)
    db.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="Portefeuille HELIOS")
    db.add(pf)
    db.flush()

    site_names = ["Paris Bureaux", "Lyon Bureaux", "Toulouse Entrepot", "Nice Hotel", "Marseille Ecole"]
    sites = []
    for name in site_names:
        s = Site(portefeuille_id=pf.id, nom=name, type=TypeSite.BUREAU, actif=True)
        db.add(s)
        db.flush()
        sites.append(s)

    db.commit()
    return {"org": org, "ej": ej, "sites": sites}


@pytest.fixture
def small_setup(db):
    """Org with only 2 sites (below threshold for full cadre generation)."""
    from models.enums import TypeSite

    org = Organisation(nom="SmallOrg", siren="222333444", actif=True)
    db.add(org)
    db.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="SmallEJ", siren="444333222")
    db.add(ej)
    db.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF-Small")
    db.add(pf)
    db.flush()

    sites = []
    for name in ["Site A", "Site B"]:
        s = Site(portefeuille_id=pf.id, nom=name, type=TypeSite.BUREAU, actif=True)
        db.add(s)
        db.flush()
        sites.append(s)

    db.commit()
    return {"org": org, "ej": ej, "sites": sites}


# ============================================================
# Idempotence
# ============================================================


class TestIdempotence:
    def test_double_run_no_duplicates(self, db, helios_setup):
        """Running generate_cadre_contracts twice → same number of cadres, no duplicates."""
        org = helios_setup["org"]
        sites = helios_setup["sites"]

        result1 = generate_cadre_contracts(db, org, sites)
        db.commit()
        count_after_first = db.query(ContratCadre).count()

        result2 = generate_cadre_contracts(db, org, sites)
        db.commit()
        count_after_second = db.query(ContratCadre).count()

        assert count_after_first == count_after_second
        assert result2["cadres"] == 0  # No new cadres on second run

    def test_idempotency_guard_checks_ref_fournisseur(self, db, helios_setup):
        """Each cadre is guarded by reference_fournisseur uniqueness."""
        org = helios_setup["org"]
        sites = helios_setup["sites"]

        generate_cadre_contracts(db, org, sites)
        db.commit()

        refs = [c.reference_fournisseur for c in db.query(ContratCadre).all()]
        assert len(refs) == len(set(refs))  # All unique


# ============================================================
# 4 cadres HELIOS
# ============================================================


class TestHeliosCadres:
    def test_creates_4_cadres_with_5_sites(self, db, helios_setup):
        """5 sites → 4 cadres created (EDF, ENGIE, TotalEnergies, Ekwateur)."""
        org = helios_setup["org"]
        sites = helios_setup["sites"]

        result = generate_cadre_contracts(db, org, sites)
        db.commit()

        assert result["cadres"] == 4
        cadres = db.query(ContratCadre).all()
        assert len(cadres) == 4

    def test_cadre1_edf_fixe_elec(self, db, helios_setup):
        """Cadre 1: EDF Entreprises — FIXE elec — 2 annexes (Paris + Lyon)."""
        generate_cadre_contracts(db, helios_setup["org"], helios_setup["sites"])
        db.commit()

        cadre = db.query(ContratCadre).filter(ContratCadre.reference_fournisseur == "EDF-CADRE-2024-001").first()
        assert cadre is not None
        assert cadre.fournisseur == "EDF Entreprises"
        assert cadre.energie == BillingEnergyType.ELEC
        assert cadre.prix_hp_eur_kwh == 0.1580
        assert cadre.prix_hc_eur_kwh == 0.1180
        assert cadre.poids_hp == 62.0
        assert cadre.poids_hc == 38.0
        assert cadre.cee_inclus is True

        annexes = db.query(ContractAnnexe).filter(ContractAnnexe.cadre_id == cadre.id).all()
        assert len(annexes) == 2

    def test_cadre2_engie_indexe_gaz(self, db, helios_setup):
        """Cadre 2: ENGIE Pro — INDEXE PEG gaz — 1 annexe (Toulouse)."""
        generate_cadre_contracts(db, helios_setup["org"], helios_setup["sites"])
        db.commit()

        cadre = db.query(ContratCadre).filter(ContratCadre.reference_fournisseur == "ENGIE-GP-2025-042").first()
        assert cadre is not None
        assert cadre.fournisseur == "ENGIE Pro"
        assert cadre.energie == BillingEnergyType.GAZ
        assert cadre.indexation_reference == "PEG_DA"
        assert cadre.indexation_spread_eur_mwh == 3.0

        annexes = db.query(ContractAnnexe).filter(ContractAnnexe.cadre_id == cadre.id).all()
        assert len(annexes) == 1

    def test_cadre3_total_fixe_vert(self, db, helios_setup):
        """Cadre 3: TotalEnergies — FIXE elec vert — 2 annexes (Nice + Marseille)."""
        generate_cadre_contracts(db, helios_setup["org"], helios_setup["sites"])
        db.commit()

        cadre = db.query(ContratCadre).filter(ContratCadre.reference_fournisseur == "TE-B2B-2025-087").first()
        assert cadre is not None
        assert cadre.fournisseur == "TotalEnergies"
        assert cadre.is_green is True
        assert cadre.green_percentage == 100.0

        annexes = db.query(ContractAnnexe).filter(ContractAnnexe.cadre_id == cadre.id).all()
        assert len(annexes) == 2

    def test_cadre4_ekwateur_spot(self, db, helios_setup):
        """Cadre 4: Ekwateur — SPOT EPEX elec — 1 annexe (Nice)."""
        generate_cadre_contracts(db, helios_setup["org"], helios_setup["sites"])
        db.commit()

        cadre = db.query(ContratCadre).filter(ContratCadre.reference_fournisseur == "EKW-SPOT-2025-019").first()
        assert cadre is not None
        assert cadre.fournisseur == "Ekwateur"
        assert cadre.indexation_reference == "EPEX_SPOT_FR"
        assert cadre.indexation_spread_eur_mwh == 5.0
        assert cadre.prix_plafond_eur_mwh == 200.0
        assert cadre.prix_plancher_eur_mwh == 60.0

        annexes = db.query(ContractAnnexe).filter(ContractAnnexe.cadre_id == cadre.id).all()
        assert len(annexes) == 1


# ============================================================
# Volume commitments
# ============================================================


class TestVolumeCommitments:
    def test_annexes_have_volumes(self, db, helios_setup):
        """All annexes have a VolumeCommitment attached."""
        generate_cadre_contracts(db, helios_setup["org"], helios_setup["sites"])
        db.commit()

        annexes = db.query(ContractAnnexe).all()
        for a in annexes:
            vc = db.query(VolumeCommitment).filter(VolumeCommitment.annexe_id == a.id).first()
            assert vc is not None, f"Annexe {a.annexe_ref} missing VolumeCommitment"
            assert vc.annual_kwh > 0

    def test_edf_lyon_override_pricing(self, db, helios_setup):
        """Annexe Lyon (EDF) has price override + ContractPricing line."""
        generate_cadre_contracts(db, helios_setup["org"], helios_setup["sites"])
        db.commit()

        lyon_annexe = db.query(ContractAnnexe).filter(ContractAnnexe.annexe_ref == "ANX-EDF-Lyon-002").first()
        assert lyon_annexe is not None
        assert lyon_annexe.has_price_override is True

        pricing = db.query(ContractPricing).filter(ContractPricing.annexe_id == lyon_annexe.id).all()
        assert len(pricing) >= 1
        assert pricing[0].unit_price_eur_kwh == 0.1380


# ============================================================
# Edge: insufficient sites
# ============================================================


class TestEdgeCases:
    def test_less_than_3_sites_returns_zero(self, db, small_setup):
        """With < 3 sites, generate_cadre_contracts returns 0 cadres."""
        result = generate_cadre_contracts(db, small_setup["org"], small_setup["sites"])
        assert result["cadres"] == 0
        assert result["annexes"] == 0
        assert db.query(ContratCadre).count() == 0
