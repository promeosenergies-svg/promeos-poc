"""
PROMEOS — Tests cardinaux Phase D-4 Tier 2 (8 P1 doctrine + cascade BACS active ADR-D-04).

Couvre :
- 6 P1 EJ adresse + Audit SMÉ co-déclencheurs (P1-MATV1-011→016)
- 2 P1 Batiment usage_batiment + dpe_emissions (P1-MATV1-023/024)
- 2 P1 DeliveryPoint cdc_pas + pcs_kwh (P1-MATV1-028/033)
- 1 P1 ContractPricing indice_reference (P1-MATV1-038)
- 4 fixes audit code-reviewer milieu-étape (P1-A indice_reference 30, P1-C 4 constantes,
  P1-D commentaire SoT, P1-E cross-FK PARKING/TECHNIQUE)
- ADR-D-04 cascade BACS active : compute + recompute + soft-delete rebuild

Audit cardinal : docs/audits/AUDIT_ECARTS_MATRICE_V1_2026_05_07.md.
"""

from __future__ import annotations

import pytest


# ─── EJ 6 P1 doctrine ──────────────────────────────────────────────────────


def test_phase_d4_t2_ej_adresse_siege_persiste(app_client):
    """P1-MATV1-011→014 : EJ adresse + code_postal + commune + pays."""
    from models import EntiteJuridique, Organisation

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T2-001", siren="999900001")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(
            nom="EJD4T2-001",
            siren="999900001",
            organisation_id=org.id,
            adresse_siege="10 Rue de Paris",
            code_postal_siege="75001",
            commune_siege="Paris",
            pays="FR",
        )
        db.add(ej)
        db.commit()
        db.refresh(ej)
        assert ej.adresse_siege == "10 Rue de Paris"
        assert ej.code_postal_siege == "75001"
        assert ej.commune_siege == "Paris"
        assert ej.pays == "FR"
    finally:
        db.close()


def test_phase_d4_t2_ej_audit_sme_co_declencheurs(app_client):
    """P1-MATV1-015 + 016 : EJ effectif_etp + chiffre_affaires_eur (Audit SMÉ co-déclencheurs)."""
    from models import EntiteJuridique, Organisation

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T2-002", siren="999900002")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(
            nom="EJD4T2-002",
            siren="999900002",
            organisation_id=org.id,
            effectif_etp=320,
            chiffre_affaires_eur=85_000_000.0,  # > seuil PME
            consommation_annuelle_moyenne_3y_gwh=4.2,  # > 2.75 GWh seuil Audit SMÉ
        )
        db.add(ej)
        db.commit()
        db.refresh(ej)
        assert ej.effectif_etp == 320
        assert ej.chiffre_affaires_eur == 85_000_000.0
    finally:
        db.close()


# ─── Batiment 2 P1 doctrine ────────────────────────────────────────────────


def test_phase_d4_t2_batiment_usage_strict_enum():
    """P1-MATV1-023 : usage_batiment strict UsageBatimentEnum (11 valeurs)."""
    from models.batiment import Batiment

    b = Batiment(site_id=1, nom="Aile X", surface_m2=1500.0)
    for val in (
        "BUREAUX",
        "COMMERCES",
        "ENSEIGNEMENT",
        "HOTELLERIE",
        "RESTAURATION",
        "SANTE",
        "SPORT_LOISIRS",
        "LOGISTIQUE",
        "PARKING",
        "TECHNIQUE",
        "MIXTE",
    ):
        b.usage_batiment = val

    with pytest.raises(ValueError, match="usage_batiment"):
        b.usage_batiment = "WAREHOUSE"


def test_phase_d4_t2_batiment_dpe_emissions_persistance(app_client):
    """P1-MATV1-024 : dpe_emissions_kgco2_m2 Float (DPE double étiquette)."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.batiment import Batiment

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T2-003", siren="999900003")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4T2-003", siren="999900003", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD4T2-003", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD4T2-003", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()
        b = Batiment(
            site_id=site.id,
            nom="Aile Z",
            surface_m2=2000.0,
            dpe_class="C",
            dpe_score_kwhep_m2_an=180.0,
            dpe_emissions_kgco2_m2=22.5,  # classe C kgCO2e
        )
        db.add(b)
        db.commit()
        db.refresh(b)
        assert b.dpe_emissions_kgco2_m2 == 22.5
    finally:
        db.close()


# ─── P1-E cross-FK PARKING/TECHNIQUE → categorie_operat_batiment NULL ──────


def test_phase_d4_t2_p1e_parking_technique_categorie_null():
    """P1-E audit : usage_batiment PARKING/TECHNIQUE → categorie_operat_batiment NULL."""
    from models.batiment import Batiment

    # Cas valide : usage_batiment hors OPERAT, categorie NULL
    b1 = Batiment(site_id=1, nom="P1", surface_m2=500.0)
    b1.usage_batiment = "PARKING"
    assert b1.categorie_operat_batiment is None

    # Cas invalide : usage_batiment PARKING + categorie défini → rejet
    b2 = Batiment(site_id=1, nom="P2", surface_m2=500.0)
    b2.usage_batiment = "PARKING"
    with pytest.raises(ValueError, match="P1-E.*hors périmètre OPERAT"):
        b2.categorie_operat_batiment = "BUREAUX"

    # Cas inverse : categorie défini puis usage_batiment PARKING → rejet
    b3 = Batiment(site_id=1, nom="P3", surface_m2=500.0)
    b3.categorie_operat_batiment = "BUREAUX"
    with pytest.raises(ValueError, match="P1-E.*hors OPERAT"):
        b3.usage_batiment = "TECHNIQUE"


# ─── DP 2 P1 doctrine — validators range bornes doctrine ──────────────────


def test_phase_d4_t2_dp_cdc_pas_temporel_range():
    """P1-MATV1-028 : cdc_pas_temporel_minutes range CDC_PAS_MIN/MAX (doctrine)."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="14999900000001", site_id=1)
    for val in (1, 10, 30, 60):
        dp.cdc_pas_temporel_minutes = val

    # Bornes hors range
    for invalid in (0, -10, 61, 120):
        with pytest.raises(ValueError, match="cdc_pas_temporel_minutes"):
            dp.cdc_pas_temporel_minutes = invalid


def test_phase_d4_t2_dp_pcs_kwh_par_nm3_range():
    """P1-MATV1-033 : pcs_kwh_par_nm3 range PCS_GAZ_MIN/MAX_KWH_NM3 (doctrine)."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="14999900000002", site_id=1)
    for val in (9.0, 10.5, 12.5, 13.0):
        dp.pcs_kwh_par_nm3 = val

    # Bornes hors range
    for invalid in (0.0, 5.0, 8.5, 13.5, 15.0):
        with pytest.raises(ValueError, match="pcs_kwh_par_nm3"):
            dp.pcs_kwh_par_nm3 = invalid


def test_phase_d4_t2_p1c_constantes_doctrine_exposees():
    """P1-C audit code-reviewer : 4 constantes range exposées doctrine.constants."""
    from doctrine.constants import (
        CDC_PAS_MAX_MINUTES,
        CDC_PAS_MIN_MINUTES,
        PCS_GAZ_MAX_KWH_NM3,
        PCS_GAZ_MIN_KWH_NM3,
    )

    assert CDC_PAS_MIN_MINUTES == 1
    assert CDC_PAS_MAX_MINUTES == 60
    assert PCS_GAZ_MIN_KWH_NM3 == 9.0
    assert PCS_GAZ_MAX_KWH_NM3 == 13.0


# ─── ContractPricing indice_reference Enum strict ─────────────────────────


def test_phase_d4_t2_indice_reference_strict_enum(app_client):
    """P1-MATV1-038 : indice_reference strict IndiceReferenceEnum (8 valeurs)."""
    from datetime import date
    from decimal import Decimal

    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.billing_models import BillingEnergyType, EnergyContract
    from models.contract_v2_models import ContractPricing

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T2-038", siren="999900038")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4T2-038", siren="999900038", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD4T2-038", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD4T2-038", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        contract = EnergyContract(site_id=site.id, energy_type=BillingEnergyType.ELEC, supplier_name="EDF")
        db.add(contract)
        db.flush()

        # Tous les 8 indices canoniques acceptés
        for indice in ("EEX_BASE", "EEX_PEAK", "PEG", "TTF", "SPOT_FR", "FORWARD_CAL", "FORWARD_TRIM", "FIXE"):
            pricing = ContractPricing(
                contract_id=contract.id,
                period_code=f"P{indice[:3]}",
                unit_price_eur_kwh=Decimal("0.100000"),
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
                indice_reference=indice,
            )
            db.add(pricing)
        db.commit()

        # Rejet indice invalide
        bad = ContractPricing(
            contract_id=contract.id,
            period_code="PXX",
            unit_price_eur_kwh=Decimal("0.100000"),
        )
        with pytest.raises(ValueError, match="indice_reference"):
            bad.indice_reference = "EUREX_BASE"
    finally:
        db.close()


# ─── ADR-D-04 cascade BACS active ──────────────────────────────────────────


def test_phase_d4_t2_cascade_bacs_compute_aggregate(app_client):
    """ADR-D-04 : compute_site_bacs_aggregate Σ Batiment.cvc_power_kw."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.batiment import Batiment
    from services.cascade_bacs_service import compute_site_bacs_aggregate

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T2-CASC", siren="999900100")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4T2-CASC", siren="999900100", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD4T2-CASC", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD4T2-CASC", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        # 2 bâtiments : 40 + 35 = 75 kW > seuil 70
        b1 = Batiment(site_id=site.id, nom="B1", surface_m2=1000.0, cvc_power_kw=40.0)
        b2 = Batiment(site_id=site.id, nom="B2", surface_m2=800.0, cvc_power_kw=35.0)
        db.add_all([b1, b2])
        db.commit()

        result = compute_site_bacs_aggregate(db, site.id)
        assert result["puissance_cvc_totale_kw"] == 75.0
        assert result["bacs_assujetti"] is True
        assert result["nb_batiments"] == 2
        assert result["threshold_kw"] == 70
    finally:
        db.close()


def test_phase_d4_t2_cascade_bacs_recompute_below_threshold(app_client):
    """ADR-D-04 : recompute persiste bacs_assujetti=False si Σ < 70 kW."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.batiment import Batiment
    from services.cascade_bacs_service import recompute_site_bacs_aggregate

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T2-CASC2", siren="999900200")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4T2-CASC2", siren="999900200", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD4T2-CASC2", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD4T2-CASC2", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        # 1 bâtiment 50 kW < seuil 70 kW
        b = Batiment(site_id=site.id, nom="B-low", surface_m2=600.0, cvc_power_kw=50.0)
        db.add(b)
        db.commit()

        result = recompute_site_bacs_aggregate(db, site.id, commit=True)
        db.refresh(site)
        assert result["bacs_assujetti"] is False
        assert site.bacs_puissance_cvc_totale_kw == 50.0
        assert site.bacs_assujetti is False
    finally:
        db.close()


def test_phase_d4_t2_cascade_bacs_soft_delete_rebuild(app_client):
    """ADR-D-04 : recompute après soft-delete d'un Batiment exclut sa puissance.

    Cas cardinal : 2 bâtiments 40+40 kW (= 80 kW assujetti) → soft-delete 1 → 40 kW non assujetti.
    """
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.batiment import Batiment
    from services.cascade_bacs_service import recompute_site_bacs_aggregate

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T2-CASC3", siren="999900300")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4T2-CASC3", siren="999900300", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD4T2-CASC3", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD4T2-CASC3", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        b1 = Batiment(site_id=site.id, nom="B-keep", surface_m2=1000.0, cvc_power_kw=40.0)
        b2 = Batiment(site_id=site.id, nom="B-soft-del", surface_m2=1000.0, cvc_power_kw=40.0)
        db.add_all([b1, b2])
        db.commit()

        # Initial : 80 kW > 70 kW assujetti
        result_initial = recompute_site_bacs_aggregate(db, site.id, commit=True)
        assert result_initial["puissance_cvc_totale_kw"] == 80.0
        assert result_initial["bacs_assujetti"] is True

        # Soft-delete b2
        b2.soft_delete(by="admin", reason="decommissioned")
        db.commit()

        # Rebuild : 40 kW < 70 kW non assujetti
        result_after = recompute_site_bacs_aggregate(db, site.id, commit=True)
        assert result_after["puissance_cvc_totale_kw"] == 40.0
        assert result_after["bacs_assujetti"] is False
        assert result_after["nb_batiments"] == 1
    finally:
        db.close()


# ─── Migration Alembic 17e propre ──────────────────────────────────────────


def test_phase_d4_t2_alembic_17e_migration_clean():
    """Phase D-4 Tier 2 : 17e migration Alembic propre (anti-DROP discipline 17e épisode)."""
    from pathlib import Path

    migration = (
        Path(__file__).parent.parent
        / "alembic"
        / "versions"
        / "531b64deea87_phase_d_4_tier_2_8_p1_doctrine_cascade_.py"
    )
    assert migration.exists()
    content = migration.read_text(encoding="utf-8")
    assert "P1-MATV1-011" in content
    assert "P1-MATV1-038" in content
    assert "17 migrations propres / 0 destructive" in content
    assert "ADR-D-04 cascade BACS" in content
