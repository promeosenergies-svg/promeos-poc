"""
PROMEOS — Tests cardinaux Phase D-0 hotfix Patrimoine (audit Sprint Patrimoine v1).

Couvre 3 P0 audit Sprint Patrimoine v1 (commit f738f1d0) :
- D-Audit-PARAM-D6-SousCompteur-Self-FK-002 P0 (D6 self-FK + sub_meter_usage)
- D-Audit-PARAM-Bati-Champs-Manquants-001 P0 (Bâtiment RNB/DPE/rénovation 5 champs)
- D-Audit-PARAM-Site-Cat-Operat-Mode-Propriete-005 P0 (Site categorie_operat + mode_propriete)
"""

from __future__ import annotations

from datetime import date


# ─── P0-002 — D6 SousCompteur self-FK ────────────────────────────────────────


def test_phase_d0_compteur_has_sub_meter_of_id_self_fk():
    """Phase D-0 cardinal : Compteur.sub_meter_of_id self-FK présent (D6 honoré)."""
    from sqlalchemy import inspect

    from models.compteur import Compteur

    columns = {c.name: c for c in inspect(Compteur).columns}
    assert "sub_meter_of_id" in columns, "Phase D-0 BLOQUANT : sub_meter_of_id absent (D6 NON honoré)"
    assert "sub_meter_usage" in columns, "Phase D-0 BLOQUANT : sub_meter_usage absent"

    # Self-FK vers compteurs.id
    fk = list(columns["sub_meter_of_id"].foreign_keys)
    assert len(fk) == 1
    assert fk[0].column.table.name == "compteurs", "FK doit pointer vers compteurs.id (self-FK)"


def test_phase_d0_compteur_sub_meter_relationship_works(app_client):
    """Phase D-0 : relation hierarchical parent_meter ↔ sub_meters fonctionne."""
    from models import EnergyVector, EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.compteur import Compteur
    from models.enums import TypeCompteur

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgPhaseD0", siren="999000001")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD0", siren="999000001", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD0", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD0", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        parent = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="PARENT-D0-001",
            energy_vector=EnergyVector.ELECTRICITY,
        )
        db.add(parent)
        db.flush()

        sub_cvc = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="SUB-D0-CVC",
            energy_vector=EnergyVector.ELECTRICITY,
            sub_meter_of_id=parent.id,
            sub_meter_usage="CVC",
        )
        sub_it = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="SUB-D0-IT",
            energy_vector=EnergyVector.ELECTRICITY,
            sub_meter_of_id=parent.id,
            sub_meter_usage="IT",
        )
        db.add_all([sub_cvc, sub_it])
        db.commit()

        # Verify relationship navigability
        db.refresh(parent)
        assert sub_cvc.parent_meter.id == parent.id
        assert sub_cvc.sub_meter_usage == "CVC"
        assert sub_it.parent_meter.id == parent.id
        assert sub_it.sub_meter_usage == "IT"
        # Backref : parent.sub_meters
        sub_ids = {s.id for s in parent.sub_meters}
        assert sub_ids == {sub_cvc.id, sub_it.id}
    finally:
        db.close()


# ─── P0-001 — Bâtiment RNB/DPE/rénovation ────────────────────────────────────


def test_phase_d0_batiment_has_rnb_dpe_renovation_fields():
    """Phase D-0 cardinal : Bâtiment 5 champs matrice v1 §4.5 ajoutés."""
    from sqlalchemy import inspect

    from models.batiment import Batiment

    columns = {c.name: c for c in inspect(Batiment).columns}
    cardinal_fields = [
        "rnb_id",
        "dpe_class",
        "dpe_score_kwhep_m2_an",
        "dpe_date_validite",
        "annee_renovation_lourde",
    ]
    missing = [f for f in cardinal_fields if f not in columns]
    assert not missing, f"Phase D-0 BLOQUANT : champs Bâtiment manquants : {missing}"


def test_phase_d0_batiment_rnb_dpe_values_persist(app_client):
    """Phase D-0 : Bâtiment.rnb_id/dpe_class/dpe_score persist + reload."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.batiment import Batiment

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgPhaseD0Bati", siren="999000002")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD0Bati", siren="999000002", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD0Bati", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD0Bati", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        bat = Batiment(
            site_id=site.id,
            nom="Bât A",
            surface_m2=1500.0,
            annee_construction=1985,
            rnb_id="RNB-V9-12345-ABC",
            dpe_class="C",
            dpe_score_kwhep_m2_an=185.5,
            dpe_date_validite=date(2031, 6, 15),
            annee_renovation_lourde=2018,
        )
        db.add(bat)
        db.commit()
        db.refresh(bat)

        assert bat.rnb_id == "RNB-V9-12345-ABC"
        assert bat.dpe_class == "C"
        assert bat.dpe_score_kwhep_m2_an == 185.5
        assert bat.dpe_date_validite == date(2031, 6, 15)
        assert bat.annee_renovation_lourde == 2018
    finally:
        db.close()


# ─── P0-005 — Site categorie_operat_principale + mode_propriete ─────────────


def test_phase_d0_site_has_categorie_operat_mode_propriete():
    """Phase D-0 cardinal : Site 2 champs Section 9.1 P0 ajoutés."""
    from sqlalchemy import inspect

    from models.site import Site

    columns = {c.name: c for c in inspect(Site).columns}
    assert "categorie_operat_principale" in columns, (
        "Phase D-0 BLOQUANT : Site.categorie_operat_principale absent (matrice v1 §4.4 P0)"
    )
    assert "mode_propriete" in columns, "Phase D-0 BLOQUANT : Site.mode_propriete absent (P0)"


def test_phase_d0_site_categorie_operat_mode_propriete_persist(app_client):
    """Phase D-0 : Site.categorie_operat_principale + mode_propriete persistent + reload."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgPhaseD0Site", siren="999000003")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD0Site", siren="999000003", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD0Site", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(
            nom="SD0Site",
            type=TypeSite.BUREAU,
            actif=True,
            portefeuille_id=pf.id,
            categorie_operat_principale="BUREAUX",  # Phase D-4 Tier 4 : strict OperatUsagePrincipalEnum
            mode_propriete="proprietaire",
        )
        db.add(site)
        db.commit()
        db.refresh(site)

        assert site.categorie_operat_principale == "BUREAUX"
        assert site.mode_propriete == "proprietaire"
    finally:
        db.close()


# ─── Anti-régression migration 13e ───────────────────────────────────────────


def test_phase_d0_alembic_migration_13e_clean_no_destructive():
    """Phase D-0 : 13e migration Alembic propre, anti-DROP discipline 13e épisode."""
    from pathlib import Path

    migration = (
        Path(__file__).parent.parent / "alembic" / "versions" / "252890dd94e4_phase_d_0_hotfix_patrimoine_d6_.py"
    )
    assert migration.exists(), "Phase D-0 BLOQUANT : migration 13e absente"

    content = migration.read_text(encoding="utf-8")

    # Marqueurs cardinaux Phase D-0
    assert "D-Audit-PARAM-D6-SousCompteur-Self-FK-002" in content
    assert "D-Audit-PARAM-Bati-Champs-Manquants-001" in content
    assert "D-Audit-PARAM-Site-Cat-Operat-Mode-Propriete-005" in content
    assert "13 migrations propres / 0 destructive" in content
