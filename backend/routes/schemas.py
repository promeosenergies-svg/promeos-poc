"""
PROMEOS - Schémas Pydantic pour validation des données API
"""

from pydantic import BaseModel, ConfigDict, model_validator
from typing import Optional, List
from datetime import datetime, date
from models import (
    TypeSite,
    TypeCompteur,
    SeveriteAlerte,
    StatutConformite,
    TypeObligation,
    TypeEvidence,
    StatutEvidence,
)

# ========================================
# SCHÉMAS SITE
# ========================================


class SiteBase(BaseModel):
    nom: str
    type: TypeSite
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    region: Optional[str] = None
    surface_m2: Optional[float] = None
    nombre_employes: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    actif: bool = True


class SiteResponse(SiteBase):
    id: int
    portefeuille_id: Optional[int] = None
    statut_decret_tertiaire: Optional[StatutConformite] = None
    avancement_decret_pct: Optional[float] = None
    statut_bacs: Optional[StatutConformite] = None
    anomalie_facture: bool = False
    action_recommandee: Optional[str] = None
    risque_financier_euro: float = 0.0
    annual_kwh_total: Optional[float] = None
    conso_kwh_an: Optional[float] = None
    compliance_score_composite: Optional[float] = None
    geocoding_source: Optional[str] = None
    geocoding_score: Optional[float] = None
    geocoding_status: Optional[str] = None

    @model_validator(mode="after")
    def _fill_conso_kwh_an(self):
        if self.conso_kwh_an is None and self.annual_kwh_total is not None:
            self.conso_kwh_an = self.annual_kwh_total
        return self

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SiteStats(BaseModel):
    """Statistiques d'un site"""

    nb_compteurs: int
    nb_alertes_actives: int
    consommation_totale_mois: float
    cout_total_mois: float


# ========================================
# SCHÉMAS COMPTEUR
# ========================================


class CompteurBase(BaseModel):
    type: TypeCompteur
    numero_serie: str
    puissance_souscrite_kw: Optional[float] = None
    actif: bool = True


class CompteurResponse(CompteurBase):
    id: int
    site_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ========================================
# SCHÉMAS CONSOMMATION
# ========================================


class ConsommationResponse(BaseModel):
    id: int
    compteur_id: int
    timestamp: datetime
    valeur: float
    cout_euro: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# ========================================
# SCHÉMAS ALERTE
# ========================================


class AlerteBase(BaseModel):
    severite: SeveriteAlerte
    titre: str
    description: Optional[str] = None


class AlerteResponse(AlerteBase):
    id: int
    site_id: int
    timestamp: datetime
    resolue: bool
    date_resolution: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ========================================
# SCHÉMAS DE RÉPONSE LISTE
# ========================================


class SiteListResponse(BaseModel):
    total: int
    sites: List[SiteResponse]


class AlerteListResponse(BaseModel):
    total: int
    alertes: List[AlerteResponse]


# ========================================
# SCHÉMAS BATIMENT
# ========================================


class BatimentResponse(BaseModel):
    id: int
    site_id: int
    nom: str
    surface_m2: float
    annee_construction: Optional[int] = None
    cvc_power_kw: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ========================================
# SCHÉMAS OBLIGATION
# ========================================


class ObligationResponse(BaseModel):
    id: int
    site_id: int
    type: TypeObligation
    description: Optional[str] = None
    echeance: Optional[date] = None
    statut: StatutConformite
    avancement_pct: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ========================================
# SCHÉMAS EVIDENCE
# ========================================


class EvidenceResponse(BaseModel):
    id: int
    site_id: int
    type: TypeEvidence
    statut: StatutEvidence
    note: Optional[str] = None
    file_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ========================================
# SCHÉMA COMPLIANCE DÉTAILLÉ
# ========================================


class ComplianceExplanation(BaseModel):
    """Explication lisible d'un aspect conformité"""

    label: str
    statut: StatutConformite
    why: str


class SiteComplianceResponse(BaseModel):
    """Réponse détaillée conformité d'un site"""

    site: SiteResponse
    batiments: List[BatimentResponse]
    obligations: List[ObligationResponse]
    evidences: List[EvidenceResponse]
    explanations: List[ComplianceExplanation]
    actions: List[str]
