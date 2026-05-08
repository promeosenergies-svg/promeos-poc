"""
PROMEOS — Schemas Pydantic pour CRUD Patrimoine (Step 19)
Organisation / EntiteJuridique / Portefeuille / Site
"""

import re
from datetime import date
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from models.enums import (
    AperCategorieTailleEnum,
    AperExemptionMotifEnum,
    OperatModulationMotifEnum,
    OperatPalierAltitudeEnum,
    OperatUsagePrincipalEnum,
    OperatZoneClimatiqueEnum,
)


# ── Organisation ─────────────────────────────────────────────────────────────


class OrganisationCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=200)
    type_client: Optional[str] = Field(None, description="retail, tertiaire, industrie")
    siren: Optional[str] = Field(None, max_length=14)

    @field_validator("siren")
    @classmethod
    def validate_siren(cls, v):
        if v is not None:
            v = re.sub(r"[\s\-]", "", v)
            if not v.isdigit() or len(v) != 9:
                raise ValueError("SIREN doit contenir exactement 9 chiffres")
        return v


class OrganisationUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=200)
    type_client: Optional[str] = None
    siren: Optional[str] = None


# ── Entité Juridique ─────────────────────────────────────────────────────────


class EntiteJuridiqueCreate(BaseModel):
    organisation_id: int
    nom: str = Field(..., min_length=1, max_length=200)
    siren: str = Field(..., max_length=14)
    siret: Optional[str] = Field(None, max_length=20)
    naf_code: Optional[str] = Field(None, max_length=5)
    region_code: Optional[str] = Field(None, max_length=3)

    @field_validator("siren")
    @classmethod
    def validate_siren(cls, v):
        v = re.sub(r"[\s\-]", "", v)
        if not v.isdigit() or len(v) != 9:
            raise ValueError("SIREN doit contenir exactement 9 chiffres")
        return v

    @field_validator("siret")
    @classmethod
    def validate_siret(cls, v):
        if v is not None:
            v = re.sub(r"[\s\-]", "", v)
            if not v.isdigit() or len(v) != 14:
                raise ValueError("SIRET doit contenir exactement 14 chiffres")
        return v


class EntiteJuridiqueUpdate(BaseModel):
    nom: Optional[str] = None
    siret: Optional[str] = None
    naf_code: Optional[str] = None
    region_code: Optional[str] = None


# ── Portefeuille ─────────────────────────────────────────────────────────────


class PortefeuilleCreate(BaseModel):
    entite_juridique_id: int
    nom: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class PortefeuilleUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None


# ── Site ─────────────────────────────────────────────────────────────────────


class SiteCreate(BaseModel):
    portefeuille_id: int
    nom: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., description="bureau, entrepot, hotel, commerce, etc.")
    adresse: Optional[str] = None
    code_postal: Optional[str] = Field(None, max_length=10)
    ville: Optional[str] = None
    region: Optional[str] = None
    surface_m2: Optional[float] = Field(None, ge=0)
    tertiaire_area_m2: Optional[float] = Field(None, ge=0)
    siret: Optional[str] = Field(None, max_length=14)
    naf_code: Optional[str] = Field(None, max_length=5)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # ─── OPERAT/APER/EFA — Sprint C-1 Phase 3 — matrice v1 §4.4.C/D/G ───
    # Tous Optional à la création : remplis post-create par services Phase 4-6.
    operat_zone_climatique: Optional[OperatZoneClimatiqueEnum] = None
    operat_palier_altitude: Optional[OperatPalierAltitudeEnum] = None
    altitude_m: Optional[int] = None
    operat_sous_categorie_id: Optional[str] = Field(None, max_length=50)
    operat_iiu_temporels: Optional[Dict[str, Any]] = None
    operat_iiu_surfaciques: Optional[Dict[str, Any]] = None
    cabs_kwh_m2_an: Optional[float] = Field(None, ge=0)
    crelat_kwh_m2_an: Optional[float] = Field(None, ge=0)
    usage_principal: Optional[OperatUsagePrincipalEnum] = None
    efa_id: Optional[str] = Field(None, max_length=50)
    annee_reference_operat: Optional[int] = Field(None, ge=2010, le=2022)
    methode_modulation_dt: Optional[OperatModulationMotifEnum] = None
    dossier_modulation_id: Optional[str] = Field(None, max_length=50)
    aper_assujetti: Optional[bool] = None
    aper_categorie_taille: Optional[AperCategorieTailleEnum] = None
    aper_deadline: Optional[date] = None
    parking_solar_pct_engaged: Optional[float] = Field(None, ge=0, le=100)
    aper_exemption_motif: Optional[AperExemptionMotifEnum] = None


# ── Bâtiment ────────────────────────────────────────────────────────────────


class BatimentCreate(BaseModel):
    site_id: int
    nom: str = Field(..., min_length=1, max_length=200)
    surface_m2: float = Field(..., ge=0)
    annee_construction: Optional[int] = Field(None, ge=1800, le=2100)
    cvc_power_kw: Optional[float] = Field(None, ge=0)


class BatimentUpdate(BaseModel):
    """Phase D-4 Tier 4 P1 : endpoint PATCH Batiment — cycle de vie complet.

    Phase F P2 : extrait depuis routes/patrimoine_crud.py vers schemas/ (SoT canonique
    schémas Pydantic, anti-duplication code-reviewer Phase E P2).
    """

    nom: Optional[str] = Field(None, min_length=1, max_length=200)
    surface_m2: Optional[float] = Field(None, ge=0)
    annee_construction: Optional[int] = Field(None, ge=1800, le=2100)
    cvc_power_kw: Optional[float] = Field(None, ge=0)


class SiteUpdate(BaseModel):
    nom: Optional[str] = None
    type: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    region: Optional[str] = None
    surface_m2: Optional[float] = Field(None, ge=0)
    tertiaire_area_m2: Optional[float] = Field(None, ge=0)
    siret: Optional[str] = None
    naf_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # ─── OPERAT/APER/EFA — Sprint C-1 Phase 3 — matrice v1 §4.4.C/D/G ───
    operat_zone_climatique: Optional[OperatZoneClimatiqueEnum] = None
    operat_palier_altitude: Optional[OperatPalierAltitudeEnum] = None
    altitude_m: Optional[int] = None
    operat_sous_categorie_id: Optional[str] = Field(None, max_length=50)
    operat_iiu_temporels: Optional[Dict[str, Any]] = None
    operat_iiu_surfaciques: Optional[Dict[str, Any]] = None
    cabs_kwh_m2_an: Optional[float] = Field(None, ge=0)
    crelat_kwh_m2_an: Optional[float] = Field(None, ge=0)
    usage_principal: Optional[OperatUsagePrincipalEnum] = None
    efa_id: Optional[str] = Field(None, max_length=50)
    annee_reference_operat: Optional[int] = Field(None, ge=2010, le=2022)
    methode_modulation_dt: Optional[OperatModulationMotifEnum] = None
    dossier_modulation_id: Optional[str] = Field(None, max_length=50)
    aper_assujetti: Optional[bool] = None
    aper_categorie_taille: Optional[AperCategorieTailleEnum] = None
    aper_deadline: Optional[date] = None
    parking_solar_pct_engaged: Optional[float] = Field(None, ge=0, le=100)
    aper_exemption_motif: Optional[AperExemptionMotifEnum] = None
