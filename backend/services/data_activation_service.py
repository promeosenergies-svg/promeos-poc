"""
PROMEOS — Data Activation service (migration JS → Python).

Phase 1.4.e du sprint refonte cockpit dual sol2 (29/04/2026). Migration de
`frontend/src/models/dataActivationModel.js` (144 lignes) vers backend
Python pour respecter la règle d'or CLAUDE.md #1 : zero business logic
in frontend.

NOTE — migration progressive (stratégie « SoT d'abord ») :
    Le fichier JS frontend/src/models/dataActivationModel.js reste
    temporairement en place comme couche de compatibilité legacy. Les 3
    pages importeuses (useDataReadiness, ActivationPage.jsx,
    DataActivationPanel.jsx) seront migrées pour consommer l'endpoint
    /api/cockpit/data_activation en Phase 1.4.e.bis.

Cohérence cross-service :
    ACTIVATION_THRESHOLD = 3 est la même constante que celle exposée par
    `services/lever_engine_service.py` (Phase 1.4.c). Les 2 services
    réfèrent à la même règle métier : si activated_count < 3, le levier
    "data_activation" devient prioritaire (cf. lever_engine V37).

Exports :
    ACTIVATION_DIMENSIONS — liste ordonnée des 5 clés canoniques
    ACTIVATION_THRESHOLD = 3 — seuil levier (cohérent lever_engine_service)
    ActivationDimension dataclass
    ActivationResult dataclass
    build_activation_checklist(kpis, billing_summary, purchase_signals) → ActivationResult
    compute_activated_count(kpis, billing_summary, purchase_signals) → int

Compatibilité : accepte clés camelCase legacy (nonConformes, aRisque,
couvertureDonnees) en plus des clés snake_case.
"""

from dataclasses import dataclass, field
from typing import Optional


ACTIVATION_DIMENSIONS = [
    "patrimoine",
    "conformite",
    "consommation",
    "facturation",
    "achat",
]

# Seuil canonique cohérent avec services/lever_engine_service.py (Phase 1.4.c)
ACTIVATION_THRESHOLD = 3


@dataclass
class ActivationDimension:
    """Brique d'activation (une des 5 dimensions canoniques)."""

    key: str
    label: str
    description: str
    available: bool
    coverage: int  # 0-100
    detail: Optional[str]
    cta_path: str
    cta_label: str

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "available": self.available,
            "coverage": self.coverage,
            "detail": self.detail,
            "cta_path": self.cta_path,
            "cta_label": self.cta_label,
        }


@dataclass
class ActivationResult:
    """Résultat de build_activation_checklist : 5 dimensions + agrégats."""

    dimensions: list[ActivationDimension] = field(default_factory=list)
    activated_count: int = 0
    total_dimensions: int = 5
    overall_coverage: int = 0  # moyenne 0-100
    next_action: Optional[ActivationDimension] = None

    def to_dict(self) -> dict:
        return {
            "dimensions": [d.to_dict() for d in self.dimensions],
            "activated_count": self.activated_count,
            "total_dimensions": self.total_dimensions,
            "overall_coverage": self.overall_coverage,
            "next_action": self.next_action.to_dict() if self.next_action else None,
        }


def _is_purchase_available(purchase_signals: Optional[dict]) -> bool:
    """Détection présence signals achat (pattern aligné lever_engine_service)."""
    if not purchase_signals or not isinstance(purchase_signals, dict):
        return False
    total_contracts = purchase_signals.get("totalContracts", purchase_signals.get("total_contracts", 0)) or 0
    return total_contracts > 0


def build_activation_checklist(
    kpis: Optional[dict] = None,
    billing_summary: Optional[dict] = None,
    purchase_signals: Optional[dict] = None,
) -> ActivationResult:
    """
    Construit la checklist d'activation des 5 dimensions canoniques.

    Args:
        kpis: dict KPI Cockpit (total, conformes, nonConformes/non_conformes,
              aRisque/a_risque, couvertureDonnees/couverture_donnees)
        billing_summary: dict avec total_invoices ou total_eur
        purchase_signals: dict normalisé via purchaseSignalsContract

    Returns:
        ActivationResult avec 5 ActivationDimension + agrégats.
    """
    k = kpis or {}
    bs = billing_summary or {}

    total = int(k.get("total", 0) or 0)
    conformes = int(k.get("conformes", 0) or 0)
    nc = int(k.get("nonConformes", k.get("non_conformes", 0)) or 0)
    ar = int(k.get("aRisque", k.get("a_risque", 0)) or 0)
    couverture = int(k.get("couvertureDonnees", k.get("couverture_donnees", 0)) or 0)

    conformes_sites = conformes + nc + ar
    has_billing = (bs.get("total_invoices") or bs.get("total_eur", 0) or 0) > 0
    has_purchase = _is_purchase_available(purchase_signals)

    total_contracts = (
        purchase_signals.get("totalContracts", purchase_signals.get("total_contracts", 0)) if purchase_signals else 0
    ) or 0
    coverage_contracts = (
        purchase_signals.get("coverageContractsPct", purchase_signals.get("coverage_contracts_pct", 0))
        if purchase_signals
        else 0
    ) or 0

    dimensions = [
        ActivationDimension(
            key="patrimoine",
            label="Patrimoine",
            description="Sites importés dans le référentiel",
            available=total > 0,
            coverage=100 if total > 0 else 0,
            detail=f"{total} site{'s' if total > 1 else ''}" if total > 0 else None,
            cta_path="/patrimoine",
            cta_label="Importer le patrimoine",
        ),
        ActivationDimension(
            key="conformite",
            label="Conformité réglementaire",
            description="Évaluation du statut conformité par site",
            available=conformes_sites > 0,
            coverage=round((conformes_sites / total) * 100) if total > 0 else 0,
            detail=f"{conformes_sites}/{total} évalués" if conformes_sites > 0 else None,
            cta_path="/conformite",
            cta_label="Évaluer la conformité",
        ),
        ActivationDimension(
            key="consommation",
            label="Données de consommation",
            description="Consommation énergétique par site (kWh/an)",
            available=couverture > 0,
            coverage=couverture,
            detail=f"{couverture}% des sites" if couverture > 0 else None,
            cta_path="/consommations/import",
            cta_label="Importer les consommations",
        ),
        ActivationDimension(
            key="facturation",
            label="Audit facturation",
            description="Factures analysées par le moteur d'audit",
            available=has_billing,
            coverage=100 if has_billing else 0,
            detail=f"{bs.get('total_invoices', '–')} factures" if has_billing else None,
            cta_path="/bill-intel",
            cta_label="Importer les factures",
        ),
        ActivationDimension(
            key="achat",
            label="Contrats énergie",
            description="Contrats de fourniture renseignés par site",
            available=has_purchase,
            coverage=int(coverage_contracts) if coverage_contracts else 0,
            detail=(f"{total_contracts} contrat{'s' if total_contracts > 1 else ''}" if has_purchase else None),
            cta_path="/achat-energie",
            cta_label="Renseigner les contrats",
        ),
    ]

    activated_count = sum(1 for d in dimensions if d.available)
    total_dimensions = len(dimensions)
    overall_coverage = round(sum(d.coverage for d in dimensions) / total_dimensions) if total_dimensions > 0 else 0
    next_action = next((d for d in dimensions if not d.available), None)

    return ActivationResult(
        dimensions=dimensions,
        activated_count=activated_count,
        total_dimensions=total_dimensions,
        overall_coverage=overall_coverage,
        next_action=next_action,
    )


def compute_activated_count(
    kpis: Optional[dict] = None,
    billing_summary: Optional[dict] = None,
    purchase_signals: Optional[dict] = None,
) -> int:
    """
    Compte rapide des briques actives (0-5) sans construire la checklist complète.

    Aligné avec le pattern V37 du JS — utilisé par lever_engine_service.py
    pour décider de l'activation du levier "data_activation".
    """
    k = kpis or {}
    bs = billing_summary or {}

    total = int(k.get("total", 0) or 0)
    conformes = int(k.get("conformes", 0) or 0)
    nc = int(k.get("nonConformes", k.get("non_conformes", 0)) or 0)
    ar = int(k.get("aRisque", k.get("a_risque", 0)) or 0)
    couverture = int(k.get("couvertureDonnees", k.get("couverture_donnees", 0)) or 0)

    flags = [
        total > 0,
        (conformes + nc + ar) > 0,
        couverture > 0,
        (bs.get("total_invoices") or bs.get("total_eur", 0) or 0) > 0,
        _is_purchase_available(purchase_signals),
    ]
    return sum(1 for f in flags if f)
