"""
PROMEOS — Schemas Pydantic pour CRUD Patrimoine (Step 19)
Organisation / EntiteJuridique / Portefeuille / Site
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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


# ── Bâtiment ────────────────────────────────────────────────────────────────


class BatimentCreate(BaseModel):
    site_id: int
    nom: str = Field(..., min_length=1, max_length=200)
    surface_m2: float = Field(..., ge=0)
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
