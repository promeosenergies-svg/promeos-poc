"""
PROMEOS - Package Routes
"""
from .sites import router as sites_router
from .compteurs import router as compteurs_router
from .consommations import router as consommations_router
from .alertes import router as alertes_router
from .cockpit import router as cockpit_router
from .compliance import router as compliance_router
from .demo import router as demo_router
from .guidance import router as guidance_router
from .regops import router as regops_router
from .connectors_route import router as connectors_router
from .watchers_route import router as watchers_router
from .ai_route import router as ai_router
from .kb_usages import router as kb_usages_router
from .energy import router as energy_router
from .monitoring import router as monitoring_router
from .onboarding import router as onboarding_router
from .import_sites import router as import_router
from .dashboard_2min import router as dashboard_2min_router
from .segmentation import router as segmentation_router
from .consumption_diagnostic import router as consumption_diag_router
from .site_config import router as site_config_router
from .billing import router as billing_router
from .purchase import router as purchase_router
from .actions import router as actions_router
from .reports import router as reports_router
from .notifications import router as notifications_router
from .auth import router as auth_router
from .admin_users import router as admin_users_router
from .patrimoine import router as patrimoine_router
from .intake import router as intake_router
from .bacs import router as bacs_router
from .ems import router as ems_router
from .dev_tools import router as dev_tools_router
from .flex import router as flex_router
from .tertiaire import router as tertiaire_router
from .portfolio import router as portfolio_router
from .consumption_context import router as consumption_context_router

__all__ = [
    "sites_router",
    "compteurs_router",
    "consommations_router",
    "alertes_router",
    "cockpit_router",
    "compliance_router",
    "demo_router",
    "guidance_router",
    "regops_router",
    "connectors_router",
    "watchers_router",
    "ai_router",
    "kb_usages_router",
    "energy_router",
    "monitoring_router",
    "onboarding_router",
    "import_router",
    "dashboard_2min_router",
    "segmentation_router",
    "consumption_diag_router",
    "site_config_router",
    "billing_router",
    "purchase_router",
    "actions_router",
    "reports_router",
    "notifications_router",
    "auth_router",
    "admin_users_router",
    "patrimoine_router",
    "intake_router",
    "bacs_router",
    "ems_router",
    "dev_tools_router",
    "flex_router",
    "tertiaire_router",
    "portfolio_router",
    "consumption_context_router",
]
