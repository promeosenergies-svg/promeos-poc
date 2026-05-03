"""
PROMEOS — Sprint C-1 Phase 3 : Tests Pydantic schemas Site avec 18 nouveaux champs.

Vérifie que SiteResponse / SiteCreate / SiteUpdate / SiteUpdateRequest acceptent
les 18 champs OPERAT/APER/EFA en Optional, valident les enums, sérialisent
correctement les types JSON dict / Date.
"""

from __future__ import annotations

import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── SiteCreate ─────────────────────────────────────────────────────────────


def test_site_create_accepts_all_18_optional_fields():
    """SiteCreate doit accepter les 18 champs Optional sans erreur."""
    from schemas.patrimoine_crud import SiteCreate

    payload = {
        "portefeuille_id": 1,
        "nom": "Site test",
        "type": "bureau",
        # Les 18 nouveaux champs OPERAT/APER/EFA
        "operat_zone_climatique": "H1a",
        "operat_palier_altitude": "alt_lt_400",
        "altitude_m": 100,
        "operat_sous_categorie_id": "BUREAU_STD_CLIMATISE",
        "operat_iiu_temporels": {"jours_par_an": 250},
        "operat_iiu_surfaciques": {"densite_employes": 0.1},
        "cabs_kwh_m2_an": 85.0,
        "crelat_kwh_m2_an": 70.0,
        "usage_principal": "BUREAUX",
        "efa_id": "EFA-TEST-001",
        "annee_reference_operat": 2020,
        "methode_modulation_dt": "COUT_DISPROPORTIONNE",
        "dossier_modulation_id": "MOD-2026-001",
        "aper_assujetti": True,
        "aper_categorie_taille": "SMALL",
        "aper_deadline": date(2028, 7, 1),
        "parking_solar_pct_engaged": 50.0,
        "aper_exemption_motif": None,
    }
    s = SiteCreate(**payload)
    assert s.cabs_kwh_m2_an == 85.0
    assert s.operat_iiu_temporels == {"jours_par_an": 250}


def test_site_create_rejects_invalid_zone():
    """SiteCreate rejette une zone climatique hors enum."""
    from pydantic import ValidationError
    from schemas.patrimoine_crud import SiteCreate

    with pytest.raises(ValidationError):
        SiteCreate(portefeuille_id=1, nom="X", type="bureau", operat_zone_climatique="ZZZ")


def test_site_create_rejects_invalid_palier():
    """SiteCreate rejette un palier altitude invalide."""
    from pydantic import ValidationError
    from schemas.patrimoine_crud import SiteCreate

    with pytest.raises(ValidationError):
        SiteCreate(portefeuille_id=1, nom="X", type="bureau", operat_palier_altitude="alt_unknown")


def test_site_create_rejects_negative_cabs():
    """SiteCreate rejette cabs_kwh_m2_an négatif (Field ge=0)."""
    from pydantic import ValidationError
    from schemas.patrimoine_crud import SiteCreate

    with pytest.raises(ValidationError):
        SiteCreate(portefeuille_id=1, nom="X", type="bureau", cabs_kwh_m2_an=-5.0)


def test_site_create_rejects_invalid_year():
    """SiteCreate rejette annee_reference_operat hors plage 2010-2022."""
    from pydantic import ValidationError
    from schemas.patrimoine_crud import SiteCreate

    with pytest.raises(ValidationError):
        SiteCreate(portefeuille_id=1, nom="X", type="bureau", annee_reference_operat=2009)
    with pytest.raises(ValidationError):
        SiteCreate(portefeuille_id=1, nom="X", type="bureau", annee_reference_operat=2025)


def test_site_create_back_compat_no_new_fields():
    """SiteCreate doit fonctionner SANS les nouveaux champs (rétro-compat)."""
    from schemas.patrimoine_crud import SiteCreate

    s = SiteCreate(portefeuille_id=1, nom="Site simple", type="bureau")
    assert s.operat_zone_climatique is None
    assert s.aper_assujetti is None
    assert s.cabs_kwh_m2_an is None


# ─── SiteUpdate ─────────────────────────────────────────────────────────────


def test_site_update_accepts_all_optional():
    """SiteUpdate accepte tous les nouveaux champs Optional."""
    from schemas.patrimoine_crud import SiteUpdate

    s = SiteUpdate(operat_zone_climatique="H3", aper_categorie_taille="LARGE")
    assert s.operat_zone_climatique.value == "H3"
    assert s.aper_categorie_taille.value == "LARGE"


# ─── SiteUpdateRequest ──────────────────────────────────────────────────────


def test_site_update_request_accepts_all_optional():
    """SiteUpdateRequest (autre PATCH endpoint) accepte les nouveaux champs."""
    from schemas.patrimoine_schemas import SiteUpdateRequest

    s = SiteUpdateRequest(
        operat_zone_climatique="H2a",
        altitude_m=350,
        cabs_kwh_m2_an=92.5,
    )
    assert s.altitude_m == 350


# ─── SiteResponse ───────────────────────────────────────────────────────────


def test_site_response_exposes_18_fields():
    """SiteResponse doit déclarer les 18 nouveaux champs (Optional, default None)."""
    from routes.schemas import SiteResponse

    expected_fields = {
        "operat_zone_climatique",
        "operat_palier_altitude",
        "altitude_m",
        "operat_sous_categorie_id",
        "operat_iiu_temporels",
        "operat_iiu_surfaciques",
        "cabs_kwh_m2_an",
        "crelat_kwh_m2_an",
        "usage_principal",
        "efa_id",
        "annee_reference_operat",
        "methode_modulation_dt",
        "dossier_modulation_id",
        "aper_assujetti",
        "aper_categorie_taille",
        "aper_deadline",
        "parking_solar_pct_engaged",
        "aper_exemption_motif",
    }
    actual = set(SiteResponse.model_fields.keys())
    missing = expected_fields - actual
    assert not missing, f"Champs manquants dans SiteResponse : {missing}"
