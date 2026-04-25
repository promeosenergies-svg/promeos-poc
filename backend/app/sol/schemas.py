"""
PROMEOS Sol — Schemas Pydantic pour /api/sol/proposal.

Structure d'un plan d'action prescriptif retourné par Sol :
- Headline : 1 phrase qui synthétise (chiffrage en hero)
- 3 actions max, sévérité-triées, chacune avec impact €/an + ROI + délai + path
- Sources tracées pour confiance utilisateur
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


SeverityT = Literal["critical", "high", "warn", "info"]
ImpactKindT = Literal["gain", "saving", "compliance_unlock", "risk_avoided"]
DelayT = Literal["aujourd'hui", "cette semaine", "ce mois", "ce trimestre"]
ConfidenceT = Literal["low", "medium", "high"]
SourceModuleT = Literal[
    "conformite",
    "billing",
    "actions",
    "achat-energie",
    "patrimoine",
    "flex",
]


class SolAction(BaseModel):
    """Une action prescriptive chiffrée proposée par Sol."""

    id: str = Field(..., description="Identifiant stable de l'action")
    title: str = Field(..., description="Phrase d'action courte (≤ 80 chars)")
    description: str = Field(
        ..., description="Justification en 1-2 phrases incluant le pourquoi"
    )
    severity: SeverityT
    impact_eur_per_year: int = Field(
        ..., description="Gain potentiel ou perte évitée en €/an"
    )
    impact_kind: ImpactKindT = Field(
        ..., description="Nature de l'impact : gain pur, économie, déblocage conformité, risque évité"
    )
    roi_months: Optional[int] = Field(
        None, description="Période retour sur investissement en mois (None si pas d'investissement)"
    )
    delay: DelayT = Field(..., description="Échéance d'action recommandée")
    source_module: SourceModuleT = Field(
        ..., description="Module produit qui détecte/exécute l'action"
    )
    action_path: str = Field(..., description="Route frontend pour exécuter (ex /conformite)")
    confidence: ConfidenceT = Field(..., description="Confiance Sol dans le chiffrage")


class SolProposal(BaseModel):
    """Plan d'action complet retourné par Sol pour le hero."""

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    org_id: int
    org_name: Optional[str] = None
    scope_label: str = Field(
        "votre patrimoine",
        description="Label scope appliqué (org / portefeuille / site)",
    )
    headline: str = Field(
        ..., description="1 phrase prescriptive avec chiffrage agrégé pour le hero"
    )
    headline_severity: SeverityT
    actions: List[SolAction] = Field(
        default_factory=list, description="Top 3 actions priorisées sévérité+impact"
    )
    total_impact_eur_per_year: int = Field(
        0, description="Somme des impact_eur_per_year des actions retenues"
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Modules sources contributifs (pour traçabilité utilisateur)",
    )


class PeerComparison(BaseModel):
    """Comparaison tarifaire org vs pairs sectoriels.

    Wedge anti-fournisseur PROMEOS « tout sauf la fourniture » : on prouve
    au client qu'il surpaye en €/kWh par rapport au benchmark de son
    archétype NAF.
    """

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    org_id: int
    archetype: str = Field(
        ..., description="Archétype NAF dominant du patrimoine (ex 'bureau')"
    )
    archetype_label: str = Field(
        ..., description="Label lisible (ex 'Bureau tertiaire')"
    )
    my_avg_kwh_price_eur: Optional[float] = Field(
        None, description="Prix moyen €/kWh du patrimoine (facture / conso)"
    )
    peer_avg_kwh_price_eur: float = Field(
        ..., description="Prix moyen €/kWh des pairs OID/CEREN même archétype"
    )
    spread_pct: Optional[float] = Field(
        None, description="(my - peer) / peer × 100 — positif = surpaye"
    )
    annual_overpayment_eur: Optional[int] = Field(
        None, description="Surpaiement annuel estimé si spread > 0"
    )
    sites_count_in_scope: int = 0
    confidence: ConfidenceT = "medium"
    peer_source: str = Field(
        "OID/CEREN benchmarks B2B 2026",
        description="Source du benchmark pair (traçabilité)",
    )
    interpretation: str = Field(
        ..., description="Phrase d'interprétation prête à afficher en wow-card"
    )
