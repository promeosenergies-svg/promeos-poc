"""
PROMEOS - Compliance Engine (LEGACY — wrapper de rétrocompatibilité)

⚠️  DÉPRÉCIÉ — Ce fichier re-exporte les fonctions migrées :
    - services/compliance_utils.py : fonctions utilitaires pures
    - services/compliance_readiness_service.py : V68 readiness gate + summaries
    - services/compliance_coordinator.py : recompute_site/portfolio/organisation
    - services/cee_service.py : CEE/M&V pipeline
"""

from config.emission_factors import get_emission_factor as _get_ef

# ── Re-exports depuis compliance_utils.py ──
from services.compliance_utils import (  # noqa: F401
    worst_status,
    _worst_from_statuts,
    average_avancement,
    compute_risque_financier,
    compute_action_recommandee,
    bacs_deadline_for_power,
    compute_bacs_statut,
    _ACTION_TEMPLATES,
    _STATUS_SEVERITY,
    BACS_DEADLINE_290,
    BACS_DEADLINE_70,
)

# ── Re-exports depuis compliance_readiness_service.py ──
from services.compliance_readiness_service import (  # noqa: F401
    compute_readiness,
    compute_applicability,
    compute_scores,
    compute_deadlines,
    compute_data_trust,
    compute_site_snapshot,
    compute_site_compliance_summary,
    compute_portfolio_compliance_summary,
)

# ── Re-exports depuis compliance_coordinator.py ──
from services.compliance_coordinator import (  # noqa: F401
    recompute_site,
    recompute_portfolio,
    recompute_organisation,
)

# ── Constantes re-exportées ──
from config.emission_factors import BASE_PENALTY_EURO, BACS_SEUIL_HAUT, BACS_SEUIL_BAS  # noqa: F401

CO2_FACTOR_ELEC_KG_KWH = _get_ef("ELEC")
CO2_FACTOR_GAZ_KG_KWH = _get_ef("GAZ")
A_RISQUE_PENALTY_RATIO = 0.5
