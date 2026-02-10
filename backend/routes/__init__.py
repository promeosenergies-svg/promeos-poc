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
]
