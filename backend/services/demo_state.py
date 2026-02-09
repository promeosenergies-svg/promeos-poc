"""
PROMEOS - Demo Mode State (in-memory singleton)
Single-user POC: one global demo_enabled flag.
"""


class DemoState:
    """Global demo mode state."""

    _enabled: bool = True  # Start in demo mode by default for POC

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
            "label": "Mode Demo actif" if cls._enabled else "Mode Production",
        }
