"""
PROMEOS — Schemas Pydantic stricts pour les routes prioritaires Patrimoine.
Quick-create site, update site, creation contrat.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Quick-Create Site ──────────────────────────────────────────────────────


class QuickCreateSiteRequest(BaseModel):
    """Payload pour la creation rapide d'un site B2B France."""

    nom: str = Field(..., min_length=1, max_length=300, description="Nom du site")
    usage: str = Field("bureau", max_length=50, description="Usage (bureau, commerce, usine, etc.)")
    adresse: Optional[str] = Field(None, max_length=500)
    code_postal: Optional[str] = Field(None, max_length=10)
    ville: Optional[str] = Field(None, max_length=200)
    surface_m2: Optional[float] = Field(None, ge=0, le=1e7)
    siret: Optional[str] = Field(None, max_length=14)
    naf_code: Optional[str] = Field(None, max_length=10)
    skip_duplicate_check: bool = Field(False, description="Forcer la creation meme si doublon detecte")

    @field_validator("nom")
    @classmethod
    def nom_not_blank(cls, v):
        if not v.strip():
            raise ValueError("Le nom du site ne peut pas etre vide")
        return v.strip()

    @field_validator("code_postal")
    @classmethod
    def validate_code_postal(cls, v):
        if v is not None:
            v = v.strip()
            if v and (len(v) < 2 or len(v) > 10):
                raise ValueError("Code postal invalide")
        return v


class QuickCreateSiteResponse(BaseModel):
    """Reponse de la creation rapide d'un site."""

    status: str  # "created" | "duplicate_detected"
    site: Optional[Dict] = None
    building: Optional[Dict] = None
    auto_provisioned: Optional[Dict] = None
    auto_created: Optional[Dict] = None
    warnings: List[str] = []
    # Champs optionnels pour les doublons
    level: Optional[str] = None
    existing_site: Optional[Dict] = None
    message: Optional[str] = None


# ── Site Update ────────────────────────────────────────────────────────────


class SiteUpdateRequest(BaseModel):
    """Mise a jour partielle d'un site — tous les champs optionnels."""

    nom: Optional[str] = Field(None, min_length=1, max_length=300)
    surface_m2: Optional[float] = Field(None, ge=0, le=1e7)
    siret: Optional[str] = Field(None, max_length=14)
    adresse: Optional[str] = Field(None, max_length=500)
    code_postal: Optional[str] = Field(None, max_length=10)
    ville: Optional[str] = Field(None, max_length=200)
    region: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, max_length=50)
    naf_code: Optional[str] = Field(None, max_length=10)
    nombre_employes: Optional[int] = Field(None, ge=0, le=1_000_000)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    @field_validator("siret")
    @classmethod
    def validate_siret(cls, v):
        if v is not None:
            import re

            v = re.sub(r"[\s\-]", "", v)
            if v and (not v.isdigit() or len(v) != 14):
                raise ValueError("SIRET doit contenir exactement 14 chiffres")
        return v


# ── Contract Create ────────────────────────────────────────────────────────


class ContractCreateRequest(BaseModel):
    """Creation d'un contrat energie — champs stricts avec validation."""

    site_id: int = Field(..., gt=0, description="ID du site rattache")
    energy_type: str = Field("elec", description="Type energie: elec, gaz, eau, fioul, chaleur")
    supplier_name: str = Field(..., min_length=1, max_length=300, description="Nom du fournisseur")
    start_date: Optional[str] = Field(None, description="Date debut (ISO format YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Date fin (ISO format YYYY-MM-DD)")
    price_ref_eur_per_kwh: Optional[float] = Field(None, ge=0, le=10)
    fixed_fee_eur_per_month: Optional[float] = Field(None, ge=0, le=1e6)
    notice_period_days: int = Field(90, ge=0, le=365)
    auto_renew: bool = False
    # V96
    offer_indexation: Optional[str] = None
    price_granularity: Optional[str] = None
    renewal_alert_days: Optional[int] = Field(None, ge=0, le=365)
    contract_status: Optional[str] = None
    # V-registre
    reference_fournisseur: Optional[str] = Field(None, max_length=200)
    date_signature: Optional[str] = None
    conditions_particulieres: Optional[str] = Field(None, max_length=2000)
    document_url: Optional[str] = Field(None, max_length=500)
    delivery_point_ids: Optional[List[int]] = None

    @field_validator("start_date", "end_date", "date_signature")
    @classmethod
    def validate_date_format(cls, v):
        if v is not None:
            from datetime import date

            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValueError(f"Format de date invalide: {v}. Attendu: YYYY-MM-DD")
        return v

    @field_validator("energy_type")
    @classmethod
    def validate_energy_type(cls, v):
        allowed = {"elec", "gaz", "eau", "fioul", "chaleur", "froid", "vapeur", "bois"}
        if v.lower() not in allowed:
            raise ValueError(f"Type energie invalide: {v}. Valeurs autorisees: {', '.join(sorted(allowed))}")
        return v.lower()
