"""
PROMEOS KPI Catalog — machine-readable canonical definitions.
Each KPI has: kpi_id, name, definition, formula, unit, period, scope, source, traceable.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KpiDefinition:
    kpi_id: str
    name: str
    definition: str
    formula: str
    unit: str
    period: str
    scope: str
    source: str
    traceable: bool = True
    notes: Optional[str] = None


KPI_CATALOG = [
    KpiDefinition(
        kpi_id="compliance_score_composite",
        name="Score de conformité composite",
        definition="Score unifié de conformité réglementaire par site",
        formula="(DT×0.45 + BACS×0.30 + APER×0.25) / poids_applicable − MIN(20, critiques×5)",
        unit="score 0-100",
        period="instantané",
        scope="site",
        source="services/compliance_score_service.py:143-265",
    ),
    KpiDefinition(
        kpi_id="risque_financier_euro",
        name="Risque financier estimé",
        definition="Estimation du risque financier lié aux non-conformités",
        formula="7500 × nb(NON_CONFORME) + 3750 × nb(A_RISQUE)",
        unit="EUR",
        period="instantané",
        scope="site, agrégé par SUM au niveau org",
        source="services/compliance_engine.py:93-97",
        notes="Estimation indicative, pas une pénalité réglementaire officielle",
    ),
    KpiDefinition(
        kpi_id="completeness_score",
        name="Score de complétude patrimoniale",
        definition="Pourcentage de champs patrimoniaux renseignés",
        formula="ROUND(filled_checks / 8 × 100)",
        unit="pourcentage 0-100",
        period="instantané",
        scope="site",
        source="routes/patrimoine/_helpers.py:357-400",
    ),
    KpiDefinition(
        kpi_id="portfolio_compliance",
        name="Score conformité portefeuille",
        definition="Moyenne pondérée par surface des scores site",
        formula="SUM(score_site × surface_site) / SUM(surface_site)",
        unit="score 0-100",
        period="instantané",
        scope="organisation",
        source="services/kpi_service.py:compute_portfolio_compliance",
    ),
    KpiDefinition(
        kpi_id="nb_contrats_actifs",
        name="Nombre de contrats actifs",
        definition="Contrats dont la date de fin est future ou absente",
        formula="COUNT(contracts WHERE end_date >= today OR end_date IS NULL)",
        unit="count",
        period="instantané",
        scope="organisation",
        source="routes/patrimoine/sites.py:patrimoine_kpis",
    ),
    KpiDefinition(
        kpi_id="nb_contrats_expiring_90j",
        name="Contrats expirant sous 90 jours",
        definition="Contrats dont la date de fin est dans les 90 prochains jours",
        formula="COUNT(contracts WHERE end_date BETWEEN today AND today+90)",
        unit="count",
        period="glissant 90 jours",
        scope="organisation",
        source="routes/patrimoine/sites.py:patrimoine_kpis",
    ),
    KpiDefinition(
        kpi_id="bacs_status",
        name="Statut BACS",
        definition="Statut de conformité GTB/GTC par site",
        formula="Evidence DEROGATION→DEROGATION, ATTESTATION→CONFORME, échéance dépassée→NON_CONFORME, sinon→A_RISQUE",
        unit="enum (CONFORME, A_RISQUE, NON_CONFORME, DEROGATION)",
        period="instantané",
        scope="site",
        source="services/compliance_engine.py:123-157",
    ),
]


def get_kpi(kpi_id: str) -> Optional[KpiDefinition]:
    return next((k for k in KPI_CATALOG if k.kpi_id == kpi_id), None)


def list_kpis() -> list:
    return [{"kpi_id": k.kpi_id, "name": k.name, "unit": k.unit, "traceable": k.traceable} for k in KPI_CATALOG]
