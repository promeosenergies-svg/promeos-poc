"""
PROMEOS - Schemas Pydantic pour le referentiel Sirene et l'onboarding from-sirene.
"""

import re
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ======================================================================
# Schemas de reponse — Recherche Sirene
# ======================================================================


class SireneUniteLegaleOut(BaseModel):
    model_config = {"from_attributes": True}
    siren: str
    denomination: Optional[str] = None
    sigle: Optional[str] = None
    nom_unite_legale: Optional[str] = None
    prenom1: Optional[str] = None
    categorie_juridique: Optional[str] = None
    activite_principale: Optional[str] = None
    activite_principale_naf25: Optional[str] = None
    etat_administratif: str = "A"
    statut_diffusion: str = "O"
    categorie_entreprise: Optional[str] = None
    tranche_effectifs: Optional[str] = None
    date_creation: Optional[str] = None
    nic_siege: Optional[str] = None
    economie_sociale_solidaire: Optional[str] = None
    societe_mission: Optional[str] = None


class SireneEtablissementOut(BaseModel):
    model_config = {"from_attributes": True}
    siret: str
    siren: str
    nic: str
    enseigne: Optional[str] = None
    denomination_usuelle: Optional[str] = None
    activite_principale: Optional[str] = None
    activite_principale_naf25: Optional[str] = None
    etat_administratif: str = "A"
    statut_diffusion: str = "O"
    etablissement_siege: Optional[bool] = False
    numero_voie: Optional[str] = None
    type_voie: Optional[str] = None
    libelle_voie: Optional[str] = None
    complement_adresse: Optional[str] = None
    code_postal: Optional[str] = None
    libelle_commune: Optional[str] = None
    code_commune: Optional[str] = None
    tranche_effectifs: Optional[str] = None
    date_creation: Optional[str] = None

    @property
    def adresse_complete(self) -> str:
        parts = [self.numero_voie, self.type_voie, self.libelle_voie]
        rue = " ".join(p for p in parts if p)
        return f"{rue}, {self.code_postal} {self.libelle_commune}".strip(", ")


class SireneSearchResult(BaseModel):
    query: str
    total: int
    results: List[SireneUniteLegaleOut]


class SireneEtablissementListResult(BaseModel):
    siren: str
    total: int
    etablissements: List[SireneEtablissementOut]


# ======================================================================
# Schemas de requete — Onboarding from-sirene
# ======================================================================


class OnboardingFromSireneRequest(BaseModel):
    siren: str = Field(..., min_length=9, max_length=9)
    etablissement_sirets: List[str] = Field(..., min_length=1, max_length=50)
    org_nom_override: Optional[str] = Field(None, max_length=200)
    type_client: Optional[str] = Field(None, pattern="^(retail|tertiaire|industrie|collectivite)$")

    @field_validator("siren")
    @classmethod
    def validate_siren(cls, v):
        v = re.sub(r"[\s\-]", "", v)
        if not v.isdigit() or len(v) != 9:
            raise ValueError("SIREN doit contenir exactement 9 chiffres")
        return v

    @field_validator("etablissement_sirets")
    @classmethod
    def validate_sirets(cls, v):
        cleaned = []
        for s in v:
            s = re.sub(r"[\s\-]", "", s)
            if not s.isdigit() or len(s) != 14:
                raise ValueError(f"SIRET invalide: {s} (14 chiffres attendus)")
            cleaned.append(s)
        return cleaned


class OnboardingFromSireneWarning(BaseModel):
    type: str  # "siren_exists", "siret_exists", "nom_similaire"
    message: str
    existing_id: Optional[int] = None


class SiteCreatedOut(BaseModel):
    id: int
    siret: str
    nom: str
    code_postal: Optional[str] = None
    ville: Optional[str] = None


class LeadScoreOut(BaseModel):
    siren: str
    segment: str  # TPE / PME / ETI / GE
    estimated_mrr_eur: int
    estimated_arr_eur: int
    priority: str  # A / B / C
    n_etablissements_actifs: int
    naf_value_tier: str  # high / medium / low / unknown
    drivers: List[str]


class OnboardingFromSireneResponse(BaseModel):
    organisation_id: int
    entite_juridique_id: int
    portefeuille_id: int
    sites: List[SiteCreatedOut]
    warnings: List[OnboardingFromSireneWarning]
    trace_id: str
    lead_score: Optional[LeadScoreOut] = None


# ======================================================================
# Schemas admin — Import
# ======================================================================


class SireneImportRequest(BaseModel):
    ul_path: Optional[str] = Field(None, description="Chemin vers stockUniteLegale CSV (relatif a SIRENE_DATA_DIR)")
    etab_path: Optional[str] = Field(None, description="Chemin vers stockEtablissement CSV")
    doublons_path: Optional[str] = Field(None, description="Chemin vers stockDoublons CSV")
    snapshot_date: Optional[str] = Field(None, description="Date snapshot YYYY-MM-DD")

    @field_validator("ul_path", "etab_path", "doublons_path")
    @classmethod
    def validate_no_traversal(cls, v):
        if v is not None:
            normalized = v.replace("\\", "/")
            if ".." in normalized or normalized.startswith("/") or ":" in normalized:
                raise ValueError(
                    "Chemin invalide: traversee de repertoire interdite. Utilisez un chemin relatif a SIRENE_DATA_DIR."
                )
        return v


class SireneSyncRunOut(BaseModel):
    id: int
    sync_type: str
    source_file: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None
    lines_read: int = 0
    lines_inserted: int = 0
    lines_updated: int = 0
    lines_rejected: int = 0
    status: str
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None
