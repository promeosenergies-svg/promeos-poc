"""
PROMEOS - Demo Mode State (in-memory singleton)
Single-user POC: one global demo_enabled flag + current seeded org metadata.

After each seed-pack, DemoState.set_demo_org() is called so all endpoints
can resolve the correct org without relying on Organisation.first().
State resets on server restart — intentional for a stateless POC.
"""

from typing import Optional


class DemoState:
    """Global demo mode state."""

    _enabled: bool = True  # Start in demo mode by default for POC

    # Set by orchestrator after each seed; used by status-pack + reset flows
    _current_org_id: Optional[int] = None
    _current_org_nom: Optional[str] = None
    _current_pack: Optional[str] = None
    _current_size: Optional[str] = None
    _current_sites_count: Optional[int] = None
    _current_default_site_id: Optional[int] = None
    _current_default_site_name: Optional[str] = None

    @classmethod
    def is_enabled(cls) -> bool:
        return cls._enabled

    @classmethod
    def enable(cls):
        cls._enabled = True

    @classmethod
    def disable(cls):
        cls._enabled = False

    @classmethod
    def status(cls) -> dict:
        return {
            "demo_enabled": cls._enabled,
            "mode": "demo" if cls._enabled else "production",
            "label": "Mode Démo actif" if cls._enabled else "Mode Production",
        }

    @classmethod
    def set_demo_org(
        cls,
        org_id: int,
        org_nom: str = None,
        pack: str = None,
        size: str = None,
        sites_count: int = None,
        default_site_id: int = None,
        default_site_name: str = None,
    ):
        """Called after each successful seed to register the active org."""
        cls._current_org_id = org_id
        cls._current_org_nom = org_nom
        cls._current_pack = pack
        cls._current_size = size
        cls._current_sites_count = sites_count
        cls._current_default_site_id = default_site_id
        cls._current_default_site_name = default_site_name

    @classmethod
    def clear_demo_org(cls):
        """Called after reset to remove org reference."""
        cls._current_org_id = None
        cls._current_org_nom = None
        cls._current_pack = None
        cls._current_size = None
        cls._current_sites_count = None
        cls._current_default_site_id = None
        cls._current_default_site_name = None

    @classmethod
    def get_demo_org_id(cls) -> Optional[int]:
        return cls._current_org_id

    @classmethod
    def get_demo_context(cls) -> dict:
        """Return the full demo context dict (all known after seed)."""
        return {
            "org_id": cls._current_org_id,
            "org_nom": cls._current_org_nom,
            "pack": cls._current_pack,
            "size": cls._current_size,
            "sites_count": cls._current_sites_count,
            "default_site_id": cls._current_default_site_id,
            "default_site_name": cls._current_default_site_name,
        }
