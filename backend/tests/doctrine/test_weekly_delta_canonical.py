"""
PROMEOS — Source-guard doctrinal : weekly_delta_struct canonique.

Phase 3.bis.b : verrouille le contrat single SoT de
`backend/doctrine/delta.py::weekly_delta_struct` — toute métrique push hebdo
Sol2 doit produire ce payload (6 champs canoniques + Literal direction).

Anti-régression : si une copie locale du helper réapparaît dans un service
(comme avant Phase 3.bis.b dans cockpit_facts_service.py), ce test alerte.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

load_dotenv()

import pytest

from doctrine.delta import (
    WeeklyDeltaDirection,
    WeeklyDeltaPayload,
    weekly_delta_struct,
)


# ── Contrat canonique TypedDict ──────────────────────────────────────


class TestWeeklyDeltaPayloadContract:
    def test_typeddict_6_canonical_fields(self):
        """WeeklyDeltaPayload TypedDict garantit 6 champs canoniques."""
        # __annotations__ expose les champs déclarés
        expected = {"current", "previous", "delta_absolute", "delta_pct", "direction", "unit"}
        actual = set(WeeklyDeltaPayload.__annotations__.keys())
        assert actual == expected

    def test_direction_literal_4_values(self):
        """WeeklyDeltaDirection Literal canonique = 4 valeurs."""
        # typing.get_args extrait les valeurs Literal
        from typing import get_args

        assert set(get_args(WeeklyDeltaDirection)) == {"up", "down", "stable", "unknown"}


# ── Comportement helper ──────────────────────────────────────────────


class TestWeeklyDeltaStruct:
    def test_current_none_returns_unknown(self):
        result = weekly_delta_struct(None, None, unit="€")
        assert result["direction"] == "unknown"
        assert result["delta_absolute"] is None

    def test_previous_none_returns_unknown_with_current(self):
        result = weekly_delta_struct(26200, None, unit="€")
        assert result["current"] == 26200
        assert result["previous"] is None
        assert result["direction"] == "unknown"

    def test_positive_delta_direction_up(self):
        result = weekly_delta_struct(30000, 26200, unit="€")
        assert result["direction"] == "up"
        assert result["delta_absolute"] == 3800

    def test_negative_delta_direction_down(self):
        result = weekly_delta_struct(20000, 26200, unit="€")
        assert result["direction"] == "down"
        assert result["delta_absolute"] == -6200

    def test_zero_delta_direction_stable(self):
        result = weekly_delta_struct(37, 37, unit="pts")
        assert result["direction"] == "stable"

    def test_division_by_zero_safe(self):
        """previous=0 → delta_pct=None (pas de ZeroDivisionError)."""
        result = weekly_delta_struct(10, 0, unit="MWh/an")
        assert result["delta_pct"] is None
        assert result["direction"] == "up"  # delta_abs > 0


# ── Anti-régression : pas de ré-implémentation ailleurs ───────────────


class TestNoLocalCopies:
    """Source-guard structurel : aucun service ne doit redéfinir ce helper."""

    SERVICES_DIR = Path(__file__).resolve().parent.parent.parent / "services"

    def test_no_local_def_in_services(self):
        """Aucun fichier services/*.py ne définit `def _weekly_delta_struct`."""
        offenders = []
        for path in self.SERVICES_DIR.rglob("*.py"):
            if "doctrine" in path.parts:
                continue
            src = path.read_text()
            # Tolère l'alias d'import (Phase 3.bis.b cockpit_facts_service.py)
            # Détecte uniquement les `def _weekly_delta_struct(` réelles
            if "def _weekly_delta_struct(" in src or "def weekly_delta_struct(" in src:
                offenders.append(str(path.relative_to(self.SERVICES_DIR)))
        assert not offenders, (
            f"Re-définition locale de weekly_delta_struct détectée dans : {offenders}. "
            "Importer depuis `doctrine.delta` à la place."
        )
