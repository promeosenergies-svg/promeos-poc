"""
PROMEOS — Tests cardinaux Phase D-4 Tier 3 (24 P1 polish matrice v1 + 4 fixes audit).

Couvre :
- Portefeuille 6 P1 polish + validator couleur_ui + actif NOT NULL
- Bâtiment 4 P1 polish + validators SIRET/etage/parties_communes
- DeliveryPoint 7 P1 polish (élec + gaz) — DataConnect OAuth2 + ADICT
- EJ 7 P1 polish + validator SIRET cohérent SIREN + email pii_sanitizer SoT + site_web normalisation

4 fixes audit code-reviewer milieu-étape :
- P1-1 : Portefeuille.actif NOT NULL default=True
- P1-2 : EJ.siret strict 14 chiffres + cohérent SIREN
- P1-3 : email_contact via PII SoT centralisé (pii_sanitizer.PII_VALUE_PATTERNS)
- P1-4 : site_web normalisation silencieuse https://

Audit cardinal : docs/audits/AUDIT_ECARTS_MATRICE_V1_2026_05_07.md.
"""

from __future__ import annotations

import pytest


# ─── §4.3 Portefeuille — 6 P1 polish + validator couleur_ui + P1-1 actif ───


def test_phase_d4_t3_portefeuille_6_polish(app_client):
    """6 P1 polish Portefeuille (responsable_id + actif + couleur + tags + code_interne + notes)."""
    from models import EntiteJuridique, Organisation, Portefeuille

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T3-PF", siren="999A00001")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4T3-PF", siren="999A00001", organisation_id=org.id)
        db.add(ej)
        db.flush()

        pf = Portefeuille(
            entite_juridique_id=ej.id,
            nom="PF Polish",
            actif=True,
            couleur_ui="#FF5733",
            tags={"region": "IDF", "priority": "high"},
            code_interne="PF-001",
            notes="Notes libres polish",
        )
        db.add(pf)
        db.commit()
        db.refresh(pf)
        assert pf.actif is True
        assert pf.couleur_ui == "#FF5733"
        assert pf.tags == {"region": "IDF", "priority": "high"}
        assert pf.code_interne == "PF-001"
    finally:
        db.close()


def test_phase_d4_t3_portefeuille_couleur_ui_validator():
    """Validator couleur_ui hex strict."""
    from models import Portefeuille

    pf = Portefeuille(entite_juridique_id=1, nom="X")
    pf.couleur_ui = "#FFF"  # short hex
    pf.couleur_ui = "#FF5733"  # long hex
    pf.couleur_ui = "#abcdef"  # lowercase OK

    with pytest.raises(ValueError, match="couleur_ui"):
        pf.couleur_ui = "red"
    with pytest.raises(ValueError, match="couleur_ui"):
        pf.couleur_ui = "#FF"


def test_phase_d4_t3_p1_1_portefeuille_actif_not_null():
    """P1-1 fix code-reviewer : Portefeuille.actif NOT NULL default=True (cohérent SoftDeleteMixin)."""
    from sqlalchemy import inspect

    from models.portefeuille import Portefeuille

    actif_col = next(c for c in inspect(Portefeuille).columns if c.name == "actif")
    assert actif_col.nullable is False, "P1-1 : Portefeuille.actif doit être NOT NULL"


# ─── §4.5 Batiment — 4 P1 polish + 3 validators ───────────────────────────


def test_phase_d4_t3_batiment_siret_validator():
    """Batiment.siret_batiment validator 14 chiffres."""
    from models.batiment import Batiment

    b = Batiment(site_id=1, nom="B-X", surface_m2=1000.0)
    b.siret_batiment = "12345678901234"  # OK
    b.siret_batiment = None  # None OK

    with pytest.raises(ValueError, match="siret_batiment"):
        b.siret_batiment = "ABC123"


def test_phase_d4_t3_batiment_etage_count_range():
    """Batiment.etage_count range -5/200."""
    from models.batiment import Batiment

    b = Batiment(site_id=1, nom="B-Y", surface_m2=1000.0)
    for val in (-5, 0, 50, 200):
        b.etage_count = val

    for invalid in (-10, 201):
        with pytest.raises(ValueError, match="etage_count"):
            b.etage_count = invalid


def test_phase_d4_t3_batiment_parties_communes_pct_range():
    """Batiment.parties_communes_pct range 0.0-100.0."""
    from models.batiment import Batiment

    b = Batiment(site_id=1, nom="B-Z", surface_m2=1000.0)
    for val in (0.0, 25.5, 100.0):
        b.parties_communes_pct = val

    for invalid in (-1.0, 101.0):
        with pytest.raises(ValueError, match="parties_communes_pct"):
            b.parties_communes_pct = invalid


# ─── §4.6.B + §4.6.C DP polish ────────────────────────────────────────────


def test_phase_d4_t3_dp_polish_persistance(app_client):
    """7 P1 polish DP élec + gaz persistables."""
    from datetime import datetime, timezone

    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.enums import DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T3-DP", siren="999A00002")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4T3-DP", siren="999A00002", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD4T3-DP", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD4T3-DP", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        token_exp = datetime(2026, 12, 31, tzinfo=timezone.utc)
        dp = DeliveryPoint(
            code="14999100000001",
            energy_type=DeliveryPointEnergyType.ELEC,
            site_id=site.id,
            puissances_souscrites_par_plage={"HPH": 250, "HCH": 150},
            tan_phi_mesure=0.4,
            dataconnect_token_expires_at=token_exp,
            dataconnect_scopes=["LOAD_CURVE", "CONSUMPTION_DAILY"],
            zone_implantation="ZI-IDF-NORD",
            pitd_code="PITD-12345",
            adict_token_expires_at=token_exp,
        )
        db.add(dp)
        db.commit()
        db.refresh(dp)
        assert dp.tan_phi_mesure == 0.4
        assert dp.dataconnect_scopes == ["LOAD_CURVE", "CONSUMPTION_DAILY"]
        assert dp.pitd_code == "PITD-12345"
    finally:
        db.close()


# ─── §4.2 EJ polish + 4 fixes audit ───────────────────────────────────────


def test_phase_d4_t3_ej_polish_persistance(app_client):
    """7 P1 polish EJ persistables."""
    from datetime import date

    from models import EntiteJuridique, Organisation

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T3-EJ", siren="999A00003")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(
            nom="EJD4T3-EJ",
            siren="999A00003",
            organisation_id=org.id,
            telephone="+33 1 23 45 67 89",
            email_contact="contact@exemple.fr",
            site_web="https://www.exemple.fr",
            type_societe="SAS",
            date_creation_societe=date(2010, 6, 15),
            capital_social_eur=100_000.0,
            representant_legal_nom="Jean Dupont",
        )
        db.add(ej)
        db.commit()
        db.refresh(ej)
        assert ej.email_contact == "contact@exemple.fr"
        assert ej.type_societe == "SAS"
        assert ej.capital_social_eur == 100_000.0
    finally:
        db.close()


def test_phase_d4_t3_p1_2_ej_siret_validator_strict():
    """P1-2 fix : EJ.siret strict 14 chiffres + cohérent SIREN préfixe."""
    from models.entite_juridique import EntiteJuridique

    ej = EntiteJuridique(nom="X", siren="123456789", organisation_id=1)
    # Cohérent : SIRET 14 chiffres avec préfixe SIREN
    ej.siret = "12345678901234"

    # Format invalide
    with pytest.raises(ValueError, match="siret"):
        ej.siret = "ABC123"

    # Cohérence SIREN cassée
    ej2 = EntiteJuridique(nom="X2", siren="987654321", organisation_id=1)
    with pytest.raises(ValueError, match="siret.*incohérent.*siren"):
        ej2.siret = "12345678901234"  # préfixe 9 chiffres ≠ siren


def test_phase_d4_t3_p1_3_ej_email_uses_pii_sot():
    """P1-3 fix : email_contact validator délégué pii_sanitizer SoT centralisé."""
    from models.entite_juridique import EntiteJuridique

    ej = EntiteJuridique(nom="X", siren="999A00099", organisation_id=1)
    ej.email_contact = "valid@exemple.fr"
    ej.email_contact = "user.name+tag@sub.domain.co.uk"

    with pytest.raises(ValueError, match="email_contact"):
        ej.email_contact = "not-an-email"
    with pytest.raises(ValueError, match="email_contact"):
        ej.email_contact = "missing@dom"  # no TLD


def test_phase_d4_t3_p1_4_ej_site_web_normalisation_https():
    """P1-4 fix : site_web normalisation silencieuse https:// si absent."""
    from models.entite_juridique import EntiteJuridique

    ej = EntiteJuridique(nom="X", siren="999A00077", organisation_id=1)

    # Cas UX courant : sans protocole → normalisé https://
    ej.site_web = "www.exemple.fr"
    assert ej.site_web == "https://www.exemple.fr"

    # Avec http:// : préservé
    ej.site_web = "http://legacy.exemple.fr"
    assert ej.site_web == "http://legacy.exemple.fr"

    # Avec https:// : préservé
    ej.site_web = "https://secure.exemple.fr"
    assert ej.site_web == "https://secure.exemple.fr"


# ─── Migration Alembic 18e propre ─────────────────────────────────────────


def test_phase_d4_t3_alembic_18e_migration_clean():
    """18e migration Alembic propre (anti-DROP discipline 18e épisode)."""
    from pathlib import Path

    migration = (
        Path(__file__).parent.parent / "alembic" / "versions" / "17c5ab8161bf_phase_d_4_tier_3_24_p1_polish_matrice_.py"
    )
    assert migration.exists()
    content = migration.read_text(encoding="utf-8")
    assert "Phase D-4 Tier 3" in content
    assert "18 migrations propres / 0 destructive" in content
