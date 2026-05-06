"""
PROMEOS — Tests cardinaux Sprint D1-B Validators cross-FK Top 20 contraintes matrice v1 §8.3.

Couvre :
- C50 : nom bâtiment unique par site
- C60 : PRM unique global (élec)
- C61-63 : categorie_turpe ⟺ domaine_tension
- C64 : code_fta cohérent préfixe segmentaire CRE + categorie_turpe
- C85 : PCE unique global (gaz)
- C89-90 : grd_code ⟺ energy_type (heuristique)
- C95 : atrd_option=T4 → cja_mwh_per_day requis
- C97 : atrd_option=T1-T3 profilé → gas_profile requis
- C108 : ContractPricing effective_to > effective_from

Source : CRE délibération 2025-78 (TURPE 7) + ATRD 7 GRDF.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError


# ─── C61-63 — categorie_turpe ⟺ domaine_tension ────────────────────────────


def test_c61_c5_bt_inf_36_ok():
    """C61 : C5 + BT≤36kVA → OK."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111101", site_id=1)
    dp.categorie_turpe = "C5"
    dp.domaine_tension = "BT≤36kVA"
    assert dp.categorie_turpe == "C5"


def test_c61_c5_hta_rejected():
    """C61 : C5 + HTA → ValueError."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111102", site_id=1)
    dp.categorie_turpe = "C5"
    with pytest.raises(ValueError, match="C61-63"):
        dp.domaine_tension = "HTA"


def test_c61_c4_bt_sup_36_ok():
    """C62 : C4 + BT>36kVA → OK."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111103", site_id=1)
    dp.categorie_turpe = "C4"
    dp.domaine_tension = "BT>36kVA"


def test_c61_c3_hta_ok():
    """C63 : C3 + HTA → OK."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111104", site_id=1)
    dp.categorie_turpe = "C3"
    dp.domaine_tension = "HTA"


def test_c61_c1_htb_ok():
    """C61 : C1 + HTB → OK (transport)."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111105", site_id=1)
    dp.categorie_turpe = "C1"
    dp.domaine_tension = "HTB"


def test_c61_unknown_categorie_rejected():
    """C61 : categorie_turpe=C99 inconnue → ValueError."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111106", site_id=1)
    dp.categorie_turpe = "C99"
    with pytest.raises(ValueError, match="C61-63"):
        dp.domaine_tension = "BT≤36kVA"


# ─── C64 — code_fta préfixe segmentaire ────────────────────────────────────


def test_c64_code_fta_bt_prefix_ok():
    """C64 : code_fta='BTINFCU4' (Enedis canonique) → OK."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111201", site_id=1)
    dp.code_fta = "BTINFCU4"


def test_c64_code_fta_hta_prefix_ok():
    """C64 : code_fta='HTACU5' canonique CRE → OK."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111202", site_id=1)
    dp.code_fta = "HTACU5"


def test_c64_code_fta_invalid_prefix_rejected():
    """C64 : code_fta='XXXX_INVALID' sans préfixe → ValueError."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111203", site_id=1)
    with pytest.raises(ValueError, match="C64"):
        dp.code_fta = "XXX_INVALID"


def test_c64_code_fta_categorie_inconsistency_rejected():
    """C64 : code_fta='HTACU5' + categorie_turpe='C5' → ValueError (BT/HTA mismatch)."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111204", site_id=1)
    dp.categorie_turpe = "C5"
    dp.domaine_tension = "BT≤36kVA"
    with pytest.raises(ValueError, match="C64"):
        dp.code_fta = "HTACU5"


# ─── C89-90 — grd_code ⟺ energy_type ────────────────────────────────────────


def test_c89_grd_enedis_elec_ok():
    """C89 : grd_code=ENEDIS + energy_type=ELEC → OK."""
    from models.enums import DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111301", site_id=1, energy_type=DeliveryPointEnergyType.ELEC)
    dp.grd_code = "ENEDIS"


def test_c89_grd_grdf_elec_rejected():
    """C90 : grd_code=GRDF + energy_type=ELEC → ValueError (gaz attendu)."""
    from models.enums import DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111302", site_id=1, energy_type=DeliveryPointEnergyType.ELEC)
    with pytest.raises(ValueError, match="C89-90"):
        dp.grd_code = "GRDF"


def test_c89_grd_eld_locale_tolere():
    """C89-90 : ELD locale (code inconnu) tolérée (any energy_type)."""
    from models.enums import DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111303", site_id=1, energy_type=DeliveryPointEnergyType.ELEC)
    dp.grd_code = "ELD_STRASBOURG"  # ELD locale → toléré


# ─── C95 + C97 — DP gaz ATRD/profil/CJA cohérence ──────────────────────────


def test_c95_t4_requires_cja():
    """C95 : atrd_option=T4 + cja=NULL → ValueError."""
    from models.enums import AtrdOption, DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111401", site_id=1, energy_type=DeliveryPointEnergyType.GAZ)
    with pytest.raises(ValueError, match="C95"):
        dp.atrd_option = AtrdOption.T4


def test_c95_t4_with_cja_ok():
    """C95 : atrd_option=T4 + cja défini → OK."""
    from models.enums import AtrdOption, DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111402", site_id=1, energy_type=DeliveryPointEnergyType.GAZ)
    dp.cja_mwh_per_day = 50.0
    dp.atrd_option = AtrdOption.T4


def test_c97_t2_requires_gas_profile():
    """C97 : atrd_option=T2 + gas_profile=NULL → ValueError."""
    from models.enums import AtrdOption, DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111403", site_id=1, energy_type=DeliveryPointEnergyType.GAZ)
    with pytest.raises(ValueError, match="C97"):
        dp.atrd_option = AtrdOption.T2


def test_c97_t2_with_profile_ok():
    """C97 : atrd_option=T2 + gas_profile=B1 → OK."""
    from models.enums import AtrdOption, DeliveryPointEnergyType, GasProfileGrdf
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111404", site_id=1, energy_type=DeliveryPointEnergyType.GAZ)
    dp.gas_profile = GasProfileGrdf.B1
    dp.atrd_option = AtrdOption.T2


def test_c95_c97_skipped_on_elec_dp():
    """C95+C97 ne s'appliquent PAS sur DP élec (energy_type=ELEC)."""
    from models.enums import DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="11111111111405", site_id=1, energy_type=DeliveryPointEnergyType.ELEC)
    # gas_profile/cja restent NULL — pas de validator gaz déclenché
    assert dp.gas_profile is None
    assert dp.cja_mwh_per_day is None


# ─── C50 — Bâtiment nom unique par site ────────────────────────────────────


def test_c50_batiment_nom_unique_per_site_integrity(app_client):
    """C50 : 2 bâtiments même nom même site → IntegrityError."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.batiment import Batiment

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD1B", siren="999300001")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD1B", siren="999300001", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD1B", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD1B", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        b1 = Batiment(site_id=site.id, nom="Aile Nord", surface_m2=1000.0)
        db.add(b1)
        db.commit()

        b2 = Batiment(site_id=site.id, nom="Aile Nord", surface_m2=500.0)
        db.add(b2)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_c50_batiment_nom_unique_per_site_different_sites_ok(app_client):
    """C50 : 2 bâtiments même nom mais sites différents → OK."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.batiment import Batiment

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD1B2", siren="999300002")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD1B2", siren="999300002", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD1B2", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        s1 = Site(nom="S1", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        s2 = Site(nom="S2", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add_all([s1, s2])
        db.flush()

        b1 = Batiment(site_id=s1.id, nom="Aile Nord", surface_m2=1000.0)
        b2 = Batiment(site_id=s2.id, nom="Aile Nord", surface_m2=500.0)
        db.add_all([b1, b2])
        db.commit()
        assert b1.id != b2.id
    finally:
        db.close()


# ─── C60 + C85 — DP code (PRM/PCE) unique global ───────────────────────────


def _create_partial_unique_dp_index(db):
    """Crée le partial unique index `uq_delivery_point_code_active` côté SQLite in-memory test.

    Pattern doctrinal cardinal : `database/migrations.py:_add_unique_delivery_point_code_index`
    + Alembic 15e — autorise réutilisation PRM/PCE post-soft-delete.
    Le SessionLocal in-memory test (cf. conftest `app_client`) ne déclenche PAS
    `init_db_with_migrations`, on doit créer le partial index explicitement.
    """
    from sqlalchemy import text

    db.execute(
        text(
            'CREATE UNIQUE INDEX IF NOT EXISTS "uq_delivery_point_code_active" '
            'ON "delivery_points" ("code") '
            'WHERE "code" IS NOT NULL AND "deleted_at" IS NULL'
        )
    )
    db.commit()


def test_c60_c85_dp_code_unique_active_partial(app_client):
    """C60+C85 : 2 DP actifs même code → IntegrityError (partial unique index)."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.enums import DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        _create_partial_unique_dp_index(db)
        org = Organisation(nom="OrgD1Bcode", siren="999300003")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD1Bcode", siren="999300003", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD1Bcode", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD1Bcode", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        dp1 = DeliveryPoint(code="14999000000001", site_id=site.id, energy_type=DeliveryPointEnergyType.ELEC)
        db.add(dp1)
        db.commit()

        dp2 = DeliveryPoint(code="14999000000001", site_id=site.id, energy_type=DeliveryPointEnergyType.ELEC)
        db.add(dp2)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_c60_c85_dp_code_reuse_after_soft_delete_ok(app_client):
    """C60+C85 : code réutilisable après soft-delete (PRM/PCE recyclé Enedis/GRDF)."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.enums import DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        _create_partial_unique_dp_index(db)
        org = Organisation(nom="OrgD1Brecyc", siren="999300006")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD1Brecyc", siren="999300006", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD1Brecyc", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD1Brecyc", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        dp1 = DeliveryPoint(code="14999000000099", site_id=site.id, energy_type=DeliveryPointEnergyType.ELEC)
        db.add(dp1)
        db.commit()

        dp1.soft_delete(by="admin", reason="decommissioned")
        db.commit()

        dp2 = DeliveryPoint(code="14999000000099", site_id=site.id, energy_type=DeliveryPointEnergyType.ELEC)
        db.add(dp2)
        db.commit()
        assert dp2.id != dp1.id
    finally:
        db.close()


# ─── C108 — ContractPricing effective_to > effective_from ──────────────────


def _seed_contract(db, siren_suffix: str):
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.billing_models import BillingEnergyType, EnergyContract

    org = Organisation(nom=f"OrgC108_{siren_suffix}", siren=f"99930{siren_suffix}")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom=f"EJC108_{siren_suffix}", siren=f"99930{siren_suffix}", organisation_id=org.id)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom=f"PFC108_{siren_suffix}", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    site = Site(nom=f"SC108_{siren_suffix}", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
    db.add(site)
    db.flush()

    contract = EnergyContract(
        site_id=site.id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF",
    )
    db.add(contract)
    db.flush()
    return contract


def test_c108_contract_pricing_dates_order_invalid_rejected(app_client):
    """C108 : effective_to <= effective_from → IntegrityError."""
    from datetime import date
    from decimal import Decimal

    from models.contract_v2_models import ContractPricing

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        contract = _seed_contract(db, "1004")
        pricing = ContractPricing(
            contract_id=contract.id,
            period_code="HP",
            unit_price_eur_kwh=Decimal("0.150000"),
            effective_from=date(2026, 1, 1),
            effective_to=date(2025, 12, 31),  # antérieur — invalide
        )
        db.add(pricing)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_c108_contract_pricing_dates_order_valid_ok(app_client):
    """C108 : effective_to > effective_from → OK."""
    from datetime import date
    from decimal import Decimal

    from models.contract_v2_models import ContractPricing

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        contract = _seed_contract(db, "1005")
        pricing = ContractPricing(
            contract_id=contract.id,
            period_code="HC",
            unit_price_eur_kwh=Decimal("0.090000"),
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        db.add(pricing)
        db.commit()
        assert pricing.id is not None
    finally:
        db.close()
