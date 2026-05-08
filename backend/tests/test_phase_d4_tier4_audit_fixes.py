"""
PROMEOS — Tests cardinaux Phase D-4 Tier 4 (3 P0 + 4 P1 fixes audit code-reviewer cumul).

Couvre :
- P0-1 cascade BACS active déclenchée create_batiment + endpoints PATCH/DELETE
- P0-2 duplication Enum accise CIBS — helper accise_category_elec_to_categorie + commentaires
- P0-3 IDOR flag explicite tête patrimoine_crud
- P1 Site.categorie_operat_principale validator strict
- P1 email_contact named export EMAIL_RFC5322_PATTERN

Audit cardinal : audit code-reviewer cumul Phase D-4 (Pilier 6 ADR-016 7e cycle).
"""

from __future__ import annotations

import pytest


# ─── P0-1 Cascade BACS active sur create_batiment ─────────────────────────


def test_phase_d4_t4_p01_cascade_bacs_create_batiment(app_client):
    """P0-1 : POST /api/patrimoine/crud/batiments déclenche cascade BACS active.

    Crée un Batiment cvc_power_kw=80 (>70 kW seuil BACS) → site.bacs_assujetti=True automatique.
    """
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite

    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T4-P01", siren="999D40001")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4T4-P01", siren="999D40001", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD4T4-P01", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD4T4-P01", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.commit()
        db.refresh(site)

        # Initial : aucun bâtiment → bacs_assujetti=None
        assert site.bacs_assujetti is None

        # POST batiment 80 kW via API
        response = client.post(
            "/api/patrimoine/crud/batiments",
            json={
                "site_id": site.id,
                "nom": "Bât principal",
                "surface_m2": 2000.0,
                "cvc_power_kw": 80.0,
            },
        )
        assert response.status_code == 201, response.json()

        # Cascade BACS active : Site doit être recalculé
        db.expire(site)
        db.refresh(site)
        assert site.bacs_puissance_cvc_totale_kw == 80.0
        assert site.bacs_assujetti is True
    finally:
        db.close()


def test_phase_d4_t4_p01_cascade_bacs_patch_batiment(app_client):
    """P0-1 : PATCH /batiments/{id} déclenche cascade BACS si cvc_power_kw modifié."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.batiment import Batiment

    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD4T4-P01b", siren="999D40002")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD4T4-P01b", siren="999D40002", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD4T4-P01b", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD4T4-P01b", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()
        b = Batiment(site_id=site.id, nom="B1", surface_m2=1000.0, cvc_power_kw=50.0)
        db.add(b)
        db.commit()

        # PATCH cvc 50→100 kW
        response = client.patch(
            f"/api/patrimoine/crud/batiments/{b.id}",
            json={"cvc_power_kw": 100.0},
        )
        assert response.status_code == 200, response.json()

        db.expire(site)
        db.refresh(site)
        assert site.bacs_puissance_cvc_totale_kw == 100.0
        assert site.bacs_assujetti is True
    finally:
        db.close()


# ─── P0-2 Duplication Enum accise CIBS — helper mapping ───────────────────


def test_phase_d4_t4_p02_accise_helper_mapping():
    """P0-2 : helper accise_category_elec_to_categorie Vague 1 → D-4."""
    from models.enums import (
        AcciseCategorieElec,
        AcciseCategoryElec,
        accise_category_elec_to_categorie,
    )

    # Mapping cardinal
    assert accise_category_elec_to_categorie(AcciseCategoryElec.HOUSEHOLD) == AcciseCategorieElec.MENAGES_ASSIMILES
    assert accise_category_elec_to_categorie(AcciseCategoryElec.SME) == AcciseCategorieElec.PME
    assert accise_category_elec_to_categorie(AcciseCategoryElec.HIGH_POWER) == AcciseCategorieElec.HAUTE_PUISSANCE
    assert accise_category_elec_to_categorie(AcciseCategoryElec.REDUCED) == AcciseCategorieElec.PME
    assert accise_category_elec_to_categorie(AcciseCategoryElec.EXEMPT) == AcciseCategorieElec.MENAGES_ASSIMILES


def test_phase_d4_t4_p02_accise_docstring_documente_dualite():
    """P0-2 : docstring AcciseCategoryElec mentionne explicitement coexistence Phase D-4."""
    from models.enums import AcciseCategoryElec

    docstring = AcciseCategoryElec.__doc__ or ""
    assert "AcciseCategorieElec" in docstring
    assert "COEXISTE" in docstring
    assert "Phase E unification" in docstring


# ─── P0-3 IDOR flag explicite ─────────────────────────────────────────────


def test_phase_d4_t4_p03_idor_dette_flag_documente():
    """P0-3 : commentaire tête patrimoine_crud.py documente DETTE IDOR cardinale."""
    from pathlib import Path

    crud_path = Path(__file__).resolve().parent.parent / "routes" / "patrimoine_crud.py"
    src = crud_path.read_text(encoding="utf-8")
    assert "DETTE IDOR CARDINALE" in src
    assert "Sprint dédié 'IDOR Patrimoine CRUD'" in src
    assert "DEMO_MODE" in src  # mitigation explicite


# ─── P1 Site.categorie_operat_principale validator strict ─────────────────


def test_phase_d4_t4_p1_site_categorie_operat_principale_strict():
    """P1 audit : Site.categorie_operat_principale strict OperatUsagePrincipalEnum."""
    from models.enums import TypeSite
    from models.site import Site

    s = Site(nom="X", type=TypeSite.BUREAU)
    for val in ("BUREAUX", "COMMERCES", "MIXTE"):
        s.categorie_operat_principale = val

    with pytest.raises(ValueError, match="categorie_operat_principale"):
        s.categorie_operat_principale = "Bureaux"  # lowercase rejet
    with pytest.raises(ValueError, match="categorie_operat_principale"):
        s.categorie_operat_principale = "AUTRES"  # non canonique


# ─── P1 email_contact named export ────────────────────────────────────────


def test_phase_d4_t4_p1_email_pattern_named_export():
    """P1 audit : EMAIL_RFC5322_PATTERN named export pii_sanitizer SoT (anti-couplage index)."""
    from services.security import pii_sanitizer

    assert hasattr(pii_sanitizer, "EMAIL_RFC5322_PATTERN")
    assert hasattr(pii_sanitizer, "IBAN_FR_PATTERN")
    assert hasattr(pii_sanitizer, "PHONE_FR_INTL_PATTERN")
    assert hasattr(pii_sanitizer, "SIRET_PRM_PCE_PATTERN")
    assert hasattr(pii_sanitizer, "SIREN_PATTERN")

    # EMAIL_RFC5322_PATTERN doit matcher l'index 1 du tuple PII_VALUE_PATTERNS (rétro-compat)
    assert pii_sanitizer.EMAIL_RFC5322_PATTERN is pii_sanitizer.PII_VALUE_PATTERNS[1]
