"""
PROMEOS - Package Routes
"""
from .sites import router as sites_router
from .compteurs import router as compteurs_router
from .consommations import router as consommations_router
from .alertes import router as alertes_router
from .cockpit import router as cockpit_router

__all__ = [
    "sites_router",
    "compteurs_router",
    "consommations_router",
    "alertes_router",
    "cockpit_router",
]
