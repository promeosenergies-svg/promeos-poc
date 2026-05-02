"""PROMEOS — Navigation badges schema.

Compteurs agrégés exposés par GET /api/v1/navigation/badges pour le rail
+ panel frontend. Source de vérité unique des compteurs nav (remplace les
3 fetches dispersés Sidebar x2 + AppShell x1).

Doctrine §6.2 anti-pattern "menus muets" : pas de None/Optional, toujours
un nombre concret (0 si org sans data).
Doctrine §8.1 zéro business logic FE : le calcul est 100 % backend, le FE
ne fait qu'affichage.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class NavBadgesResponse(BaseModel):
    """Compteurs agrégés navigation rail/panel.

    Sémantique :
    - energy_alerts : MonitoringAlert ouvertes (status=OPEN, scope org).
    - compliance_alerts : notifications critical + warn (notification_service).
    - billing_anomalies : EnergyInvoice status=ANOMALY (non revues).
    - purchase_deadlines : EnergyContract end_date entre aujourd'hui et J+90
      (convention contract_expiration_alerts.py — alerte prod 90 j).
    - action_center : total issues du Centre d'action
      (action_center_service.get_action_center_issues).
    - conformite_*_progress : moyenne pondérée par Site.surface_m2 des
      scores par framework (compute_portfolio_compliance), fallback 1000 m².
      Mapping interne : tertiaire_operat → dt (doctrine §11.3).
    """

    energy_alerts: int = Field(ge=0, description="Alertes monitoring ouvertes")
    compliance_alerts: int = Field(ge=0, description="Notifications critical + warn (rail Conformité)")
    billing_anomalies: int = Field(ge=0, description="Factures en statut ANOMALY")
    purchase_deadlines: int = Field(ge=0, description="Échéances marché ≤ 90 j (contrats expirant)")
    action_center: int = Field(ge=0, description="Issues ouvertes du Centre d'action")
    conformite_dt_progress: float = Field(ge=0, le=100, description="Score Décret Tertiaire org-level (0-100)")
    conformite_bacs_progress: float = Field(ge=0, le=100, description="Score BACS org-level (0-100)")
    conformite_aper_progress: float = Field(ge=0, le=100, description="Score APER org-level (0-100)")
    computed_at: datetime = Field(description="Horodatage UTC du calcul")
    cache_ttl_seconds: int = Field(default=60, description="TTL cache FE conseillé")
