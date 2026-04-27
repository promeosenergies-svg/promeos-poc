"""Registre KPI PROMEOS Sol — fiche obligatoire par KPI (§8 Doctrine).

Tout KPI affiché dans le produit DOIT être enregistré ici.
Test associé : tests/doctrine/test_kpi_registry_format.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Unit = Literal["kWh", "MWh", "kW", "kVA", "€", "€/MWh", "€/kWh", "kgCO2e", "%", "days", "kWhEF/m²/an"]
Scope = Literal["site", "building", "meter", "portfolio", "organization"]
Period = Literal["day", "week", "month", "year", "rolling_12_months", "calendar_year", "contract_year"]
Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class KPIDefinition:
    kpi_id: str
    label: str
    unit: Unit
    formula: str
    source: str
    scope: list[Scope]
    period: list[Period]
    freshness: Literal["realtime", "daily", "monthly", "on_import"]
    confidence_rule: str
    owner: str
    used_in: list[str] = field(default_factory=list)


# ─── KPIs prioritaires cockpit (§8.2) ──────────────────────────────────────
KPI_REGISTRY: dict[str, KPIDefinition] = {
    "annual_consumption_mwh": KPIDefinition(
        kpi_id="annual_consumption_mwh",
        label="Consommation annuelle",
        unit="MWh",
        formula="sum(consumption_kwh) / 1000 sur période",
        source="consumption_unified_service (Enedis + GRDF + factures)",
        scope=["site", "portfolio", "organization"],
        period=["rolling_12_months", "calendar_year", "contract_year"],
        freshness="daily",
        confidence_rule="high si période complète et source primaire",
        owner="data_product",
        used_in=["cockpit", "portfolio", "site", "conformity", "bill_intelligence"],
    ),
    "energy_cost_eur": KPIDefinition(
        kpi_id="energy_cost_eur",
        label="Coût énergie",
        unit="€",
        formula="sum(invoice.total_ht) sur période OU consumption × prix_pondéré si pas de facture",
        source="invoices + tarifs_reglementaires.yaml",
        scope=["site", "portfolio", "organization"],
        period=["month", "year", "contract_year"],
        freshness="on_import",
        confidence_rule="high si factures complètes, medium si fallback prix",
        owner="bill_intelligence",
        used_in=["cockpit", "portfolio", "site", "bill_intelligence", "achat"],
    ),
    "compliance_score": KPIDefinition(
        kpi_id="compliance_score",
        label="Score conformité",
        unit="%",
        formula="weighted_sum(DT, BACS, APER, AUDIT) avec poids depuis REGOPS_WEIGHTS_*",
        source="regops/scoring.py — RegAssessment.compliance_score",
        scope=["organization", "site"],
        period=["calendar_year"],
        freshness="daily",
        confidence_rule="high si toutes obligations évaluées",
        owner="regops",
        used_in=["cockpit", "conformity"],
    ),
    "data_quality_score": KPIDefinition(
        kpi_id="data_quality_score",
        label="Qualité données",
        unit="%",
        formula="(meters_with_data_period_complete / total_meters) × completeness_rate",
        source="data_completeness_service",
        scope=["site", "portfolio", "organization"],
        period=["rolling_12_months"],
        freshness="daily",
        confidence_rule="auto",
        owner="data_product",
        used_in=["cockpit", "patrimoine", "ems"],
    ),
    "open_actions_count": KPIDefinition(
        kpi_id="open_actions_count",
        label="Actions ouvertes",
        unit="days",  # impropre mais on stocke le count comme int — voir validation
        formula="count(actions WHERE status IN ('open','in_progress'))",
        source="actions_service",
        scope=["site", "portfolio", "organization"],
        period=["day"],
        freshness="realtime",
        confidence_rule="high",
        owner="action_center",
        used_in=["cockpit", "centre_action"],
    ),
    "trajectory_dt_progress": KPIDefinition(
        kpi_id="trajectory_dt_progress",
        label="Trajectoire Décret Tertiaire",
        unit="%",
        formula="(consumption_ref - consumption_current) / (consumption_ref × |jalon|)",
        source="dt_progress_service",
        scope=["site", "portfolio", "organization"],
        period=["calendar_year"],
        freshness="daily",
        confidence_rule="high si ref_year=2020 et données complètes",
        owner="regops",
        used_in=["cockpit", "conformity", "executive"],
    ),
    "billing_anomalies_count": KPIDefinition(
        kpi_id="billing_anomalies_count",
        label="Anomalies facture",
        unit="days",  # idem, count int
        formula="count(billing_anomalies WHERE resolved=false)",
        source="bill_intelligence/anomaly_detector",
        scope=["site", "portfolio", "organization"],
        period=["rolling_12_months"],
        freshness="on_import",
        confidence_rule="high",
        owner="bill_intelligence",
        used_in=["cockpit", "bill_intelligence"],
    ),
}


def get_kpi(kpi_id: str) -> KPIDefinition:
    """Récupère une fiche KPI. Lève KeyError si non enregistrée (§8 doctrine)."""
    if kpi_id not in KPI_REGISTRY:
        raise KeyError(
            f"KPI '{kpi_id}' non enregistré dans le registry. "
            f"Doctrine §8 : tout KPI doit avoir une fiche. "
            f"Ajouter la définition dans backend/doctrine/kpi_registry.py."
        )
    return KPI_REGISTRY[kpi_id]
