"""
PROMEOS - Schémas Pydantic pour validation des données API
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models import TypeSite, TypeCompteur, SeveriteAlerte

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
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

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
    
    class Config:
        from_attributes = True

# ========================================
# SCHÉMAS CONSOMMATION
# ========================================

class ConsommationResponse(BaseModel):
    id: int
    compteur_id: int
    timestamp: datetime
    valeur: float
    cout_euro: Optional[float] = None
    
    class Config:
        from_attributes = True

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
    
    class Config:
        from_attributes = True

# ========================================
# SCHÉMAS DE RÉPONSE LISTE
# ========================================

class SiteListResponse(BaseModel):
    total: int
    sites: List[SiteResponse]

class AlerteListResponse(BaseModel):
    total: int
    alertes: List[AlerteResponse]

