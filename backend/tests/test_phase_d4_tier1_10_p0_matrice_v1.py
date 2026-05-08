"""
PROMEOS — Tests cardinaux Phase D-4 Tier 1 (10 P0 cardinaux matrice v1).

Couvre les 10 P0 résiduels audit écarts matrice v1 (AUDIT_ECARTS_MATRICE_V1_2026_05_07.md) :

- P0-MATV1-001 : EJ.consommation_annuelle_moyenne_3y_gwh (déclencheur Audit SMÉ)
- P0-MATV1-002 + 003 : DP.accise_categorie_gaz/elec (CIBS L.312 — ADR-D-05)
- P0-MATV1-004 : Site.consentement_site_overrides JSON (cascade RGPD §6.1)
- P0-MATV1-005 : Site.bacs_assujetti + bacs_puissance_cvc_totale_kw (ADR-D-04)
- P0-MATV1-006 + 007 + 008 : DP gaz 5 colonnes matérialisées (ADR-D-02)
- P0-MATV1-009 : Batiment.categorie_operat_batiment (contrainte A9)
- P0-MATV1-010 : Compteur.batiment_id FK (ADR-D-03)

+ Tests cross-validators (P0-1 + P0-2 + P1-1 + P1-2 audit code-reviewer milieu-étape).
"""

from __future__ import annotations

import pytest


# ─── P0-MATV1-001 — EntiteJuridique.consommation_annuelle_moyenne_3y_gwh ───


def test_phase_d4_ej_consommation_3y_gwh_persiste(app_client):
    """P0-001 : `consommation_annuelle_moyenne_3y_gwh` Float persistable."""
    from models import EntiteJuridique, Organisation

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4P001", siren="999800001")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(
            nom="EJD4P001", siren="999800001", organisation_id=org.id, consommation_annuelle_moyenne_3y_gwh=3.5
        )
        db.add(ej)
        db.commit()
        db.refresh(ej)
        assert ej.consommation_annuelle_moyenne_3y_gwh == 3.5  # > seuil 2.75 GWh
    finally:
        db.close()


# ─── P0-MATV1-002 + 003 — Accise CIBS Enum strict ──────────────────────────


def test_phase_d4_accise_categorie_elec_strict():
    """P0-003 : accise_categorie_elec strict CIBS L.312-36/37 (3 valeurs)."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="14999800000001", site_id=1)
    dp.accise_categorie_elec = "MENAGES_ASSIMILES"
    dp.accise_categorie_elec = "PME"
    dp.accise_categorie_elec = "HAUTE_PUISSANCE"

    with pytest.raises(ValueError, match="accise_categorie_elec"):
        dp.accise_categorie_elec = "INDUSTRIEL"


def test_phase_d4_accise_categorie_gaz_strict():
    """P0-002 : accise_categorie_gaz strict CIBS L.312-24 (3 valeurs)."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="14999800000002", site_id=1)
    dp.accise_categorie_gaz = "NATUREL"
    dp.accise_categorie_gaz = "GPL"
    dp.accise_categorie_gaz = "GNL"

    with pytest.raises(ValueError, match="accise_categorie_gaz"):
        dp.accise_categorie_gaz = "BIOGAZ"


# ─── P0-MATV1-006 + 007 + 008 — DP gaz 5 colonnes Enum strict ─────────────


def test_phase_d4_pce_format_strict_3_canoniques():
    """P0-006 : pce_format strict + cross-validator P0-1 (code regex cohérent)."""
    from models.patrimoine import DeliveryPoint

    # 3 codes distincts pour 3 formats canoniques cohérents (cross-validator P0-1 actif)
    dp1 = DeliveryPoint(code="14999800000003", site_id=1)
    dp1.pce_format = "DISTRIBUTION_14"

    dp2 = DeliveryPoint(code="GI123456", site_id=1)
    dp2.pce_format = "DISTRIBUTION_GI"

    dp3 = DeliveryPoint(code="IR0011", site_id=1)
    dp3.pce_format = "TRANSPORT_PIR"

    # Rejet format invalide (validator strict canonique)
    dp4 = DeliveryPoint(code="14999800000004", site_id=1)
    with pytest.raises(ValueError, match="pce_format"):
        dp4.pce_format = "DISTRIBUTION_XYZ"


def test_phase_d4_type_reseau_strict():
    """P0-007 : type_reseau strict (DISTRIBUTION/TRANSPORT)."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="14999800000004", site_id=1)
    dp.type_reseau = "DISTRIBUTION"
    dp.type_reseau = "TRANSPORT"

    with pytest.raises(ValueError, match="type_reseau"):
        dp.type_reseau = "MIXED"


def test_phase_d4_referentiel_tarifaire_strict():
    """P0-007 : referentiel_tarifaire strict (ATRD/ATRT)."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="14999800000005", site_id=1)
    dp.referentiel_tarifaire = "ATRD"
    dp.referentiel_tarifaire = "ATRT"

    with pytest.raises(ValueError, match="referentiel_tarifaire"):
        dp.referentiel_tarifaire = "ATRX"


def test_phase_d4_mode_releve_gaz_strict():
    """P0-008 : mode_releve_gaz strict (MM/MJ/JJ/MH)."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="14999800000006", site_id=1)
    for val in ("MM", "MJ", "JJ", "MH"):
        dp.mode_releve_gaz = val

    with pytest.raises(ValueError, match="mode_releve_gaz"):
        dp.mode_releve_gaz = "XX"


# ─── P0-MATV1-009 — Batiment.categorie_operat_batiment Enum strict ────────


def test_phase_d4_batiment_categorie_operat_strict():
    """P0-009 + P0-2 audit code-reviewer : Enum strict OperatUsagePrincipalEnum (9 catégories)."""
    from models.batiment import Batiment

    b = Batiment(site_id=1, nom="Aile Test", surface_m2=1000.0)
    for val in (
        "BUREAUX",
        "COMMERCES",
        "ENSEIGNEMENT",
        "HOTELLERIE",
        "RESTAURATION",
        "SANTE",
        "SPORT_LOISIRS",
        "LOGISTIQUE",
        "MIXTE",
    ):
        b.categorie_operat_batiment = val

    with pytest.raises(ValueError, match="categorie_operat_batiment"):
        b.categorie_operat_batiment = "TOTO"


# ─── P0-MATV1-010 — Compteur.batiment_id FK ────────────────────────────────


def test_phase_d4_compteur_batiment_fk(app_client):
    """P0-010 : Compteur.batiment_id FK Batiment + ondelete=SET NULL (ADR-D-03)."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.batiment import Batiment
    from models.compteur import Compteur
    from models.enums import TypeCompteur

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4P010", siren="999800010")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4P010", siren="999800010", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD4P010", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD4P010", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()
        b = Batiment(site_id=site.id, nom="Aile Nord", surface_m2=2000.0)
        db.add(b)
        db.flush()

        c = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="D4-T1-COMP-001",
            actif=True,
            batiment_id=b.id,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        assert c.batiment_id == b.id
    finally:
        db.close()


# ─── P0-MATV1-004 + 005 — Site cascade RGPD + BACS ─────────────────────────


def test_phase_d4_site_consentement_overrides_json(app_client):
    """P0-004 : Site.consentement_site_overrides JSON cascade RGPD §6.1."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4P004", siren="999800004")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4P004", siren="999800004", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD4P004", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(
            nom="SD4P004",
            type=TypeSite.BUREAU,
            actif=True,
            portefeuille_id=pf.id,
            consentement_site_overrides={"dataconnect": "accepte_local", "grdf": "herite_entite"},
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        assert site.consentement_site_overrides["dataconnect"] == "accepte_local"
    finally:
        db.close()


def test_phase_d4_site_bacs_persistance(app_client):
    """P0-005 : Site.bacs_assujetti + bacs_puissance_cvc_totale_kw persistables (ADR-D-04)."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4P005", siren="999800005")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4P005", siren="999800005", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD4P005", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(
            nom="SD4P005",
            type=TypeSite.BUREAU,
            actif=True,
            portefeuille_id=pf.id,
            bacs_assujetti=True,
            bacs_puissance_cvc_totale_kw=120.0,  # > 70 kW (BACS_THRESHOLD_KW_EXISTING)
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        assert site.bacs_assujetti is True
        assert site.bacs_puissance_cvc_totale_kw == 120.0
    finally:
        db.close()


# ─── Cross-validators audit code-reviewer milieu-étape ─────────────────────


def test_phase_d4_p0_1_cross_validator_pce_format_code():
    """P0-1 fix code-reviewer : pce_format ↔ code regex cohérence cross-FK."""
    from models.patrimoine import DeliveryPoint

    # Cohérent : DISTRIBUTION_14 + 14 chiffres
    dp1 = DeliveryPoint(code="14999000000001", site_id=1)
    dp1.pce_format = "DISTRIBUTION_14"

    # Cohérent : DISTRIBUTION_GI + GI\d{6}
    dp2 = DeliveryPoint(code="GI123456", site_id=1)
    dp2.pce_format = "DISTRIBUTION_GI"

    # Cohérent : TRANSPORT_PIR + IR\d{4}
    dp3 = DeliveryPoint(code="IR0011", site_id=1)
    dp3.pce_format = "TRANSPORT_PIR"

    # Incohérent : DISTRIBUTION_14 + GI\d{6}
    dp4 = DeliveryPoint(code="GI123456", site_id=1)
    with pytest.raises(ValueError, match="P0-1.*incohérent"):
        dp4.pce_format = "DISTRIBUTION_14"

    # Incohérent : TRANSPORT_PIR + 14 chiffres
    dp5 = DeliveryPoint(code="14999000000099", site_id=1)
    with pytest.raises(ValueError, match="P0-1.*incohérent"):
        dp5.pce_format = "TRANSPORT_PIR"


def test_phase_d4_p1_1_cross_validator_type_reseau_referentiel():
    """P1-1 fix code-reviewer : DISTRIBUTION → ATRD, TRANSPORT → ATRT (bijection)."""
    from models.patrimoine import DeliveryPoint

    # Cohérent
    dp1 = DeliveryPoint(code="14999000000010", site_id=1)
    dp1.type_reseau = "DISTRIBUTION"
    dp1.referentiel_tarifaire = "ATRD"

    dp2 = DeliveryPoint(code="IR0050", site_id=1)
    dp2.type_reseau = "TRANSPORT"
    dp2.referentiel_tarifaire = "ATRT"

    # Incohérent : DISTRIBUTION + ATRT
    dp3 = DeliveryPoint(code="14999000000020", site_id=1)
    dp3.referentiel_tarifaire = "ATRT"
    with pytest.raises(ValueError, match="P1-1.*incohérent"):
        dp3.type_reseau = "DISTRIBUTION"

    # Incohérent : TRANSPORT + ATRD
    dp4 = DeliveryPoint(code="IR0099", site_id=1)
    dp4.type_reseau = "TRANSPORT"
    with pytest.raises(ValueError, match="P1-1.*incohérent"):
        dp4.referentiel_tarifaire = "ATRD"


def test_phase_d4_p1_2_cross_validator_est_profile_atrd():
    """P1-2 fix code-reviewer : est_profile ↔ atrd_option (T1/T2/T3 = profilé)."""
    from models.enums import AtrdOption, DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    # Cohérent T2 + est_profile=True
    dp1 = DeliveryPoint(code="14999000000030", site_id=1, energy_type=DeliveryPointEnergyType.GAZ)
    dp1.gas_profile = "B1"  # cohérent C97 si T2
    dp1.atrd_option = AtrdOption.T2
    dp1.est_profile = True

    # Cohérent T4 + est_profile=False (CJA requise C95)
    dp2 = DeliveryPoint(code="14999000000031", site_id=1, energy_type=DeliveryPointEnergyType.GAZ)
    dp2.cja_mwh_per_day = 50.0
    dp2.atrd_option = AtrdOption.T4
    dp2.est_profile = False

    # Incohérent : T4 + est_profile=True
    dp3 = DeliveryPoint(code="14999000000032", site_id=1, energy_type=DeliveryPointEnergyType.GAZ)
    dp3.cja_mwh_per_day = 50.0
    dp3.atrd_option = AtrdOption.T4
    with pytest.raises(ValueError, match="P1-2.*incohérent"):
        dp3.est_profile = True


# ─── Audit doc + ADR livrés ────────────────────────────────────────────────


def test_phase_d4_audit_doc_livre():
    """Phase D-4 Tier 1 : audit + 4 ADR stubs livrés."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    audits = repo_root / "docs" / "audits"
    adr = repo_root / "docs" / "adr"

    assert (audits / "AUDIT_ECARTS_MATRICE_V1_2026_05_07.md").exists()
    assert (adr / "ADR-D-02-materialisation-vs-derivation-dp-gaz.md").exists()
    assert (adr / "ADR-D-03-compteur-batiment-fk-cascade.md").exists()
    assert (adr / "ADR-D-04-bacs-puissance-cvc-cascade.md").exists()
    assert (adr / "ADR-D-05-accise-cibs-enum-strict.md").exists()


def test_phase_d4_alembic_16e_migration_clean():
    """Phase D-4 Tier 1 : 16e migration Alembic propre (anti-DROP discipline 16e épisode)."""
    from pathlib import Path

    migration = (
        Path(__file__).parent.parent / "alembic" / "versions" / "7f318cc8fb86_phase_d_4_tier_1_10_p0_cardinaux_.py"
    )
    assert migration.exists()
    content = migration.read_text(encoding="utf-8")
    assert "P0-MATV1-001" in content
    assert "P0-MATV1-010" in content
    assert "16 migrations propres / 0 destructive" in content
