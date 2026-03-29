"""
Source Guard — Aucun module hors allowlist ne doit querier directement
func.sum(MeterReading.value_kwh) ou func.sum(EnergyInvoice.energy_kwh)
pour afficher un KPI de consommation.

Tous doivent passer par consumption_unified_service.get_consumption_summary().
"""

import os
import re

import pytest

pytestmark = pytest.mark.fast

# Fichiers autorises a faire des queries directes sur MeterReading/EnergyInvoice
# (services analytiques qui ont besoin de donnees per-reading, pas de totaux KPI)
ALLOWED_FILES = {
    "consumption_unified_service.py",  # Le service unifie lui-meme
    "timeseries_service.py",  # Charts time-series (granularite per-reading)
    "meter_unified_service.py",  # Reconciliation sous-compteurs
    "usage_service.py",  # Analyse HP/HC, heatmaps (per-reading)
    "consumption_context_service.py",  # Profils de charge, baseload (per-reading)
    "consumption_diagnostic.py",  # Detection anomalies (per-reading)
    "copilot_engine.py",  # Rules engine (monthly grouping, percentiles)
    "billing_service.py",  # Shadow billing per-invoice
    "demo_seed.py",  # Seed data
    "billing_seed.py",  # Seed data
    "seed_data.py",  # Seed data
    "helios_seed.py",  # Seed data
}

# Patterns qui indiquent un acces direct pour un total kWh
FORBIDDEN_PATTERNS = [
    r"func\.sum\(.*MeterReading\.value_kwh",
    r"func\.sum\(.*MeterReading\.hp_kwh",
    r"func\.sum\(.*MeterReading\.hc_kwh",
    r"func\.sum\(.*EnergyInvoice\.energy_kwh",
]


def test_no_direct_consumption_queries():
    """Aucun module hors allowlist ne fait de sum(MeterReading.value_kwh)."""
    violations = []

    backend_dir = os.path.join(os.path.dirname(__file__), "..")
    for root, dirs, files in os.walk(backend_dir):
        # Skip __pycache__ and tests
        if "__pycache__" in root or os.sep + "tests" + os.sep in root + os.sep:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            if f in ALLOWED_FILES:
                continue

            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    content = fh.read()
            except (UnicodeDecodeError, PermissionError):
                continue

            for pattern in FORBIDDEN_PATTERNS:
                matches = re.findall(pattern, content)
                if matches:
                    violations.append(f"{f}: pattern={pattern} ({len(matches)} occurrences)")

    assert violations == [], (
        "Les fichiers suivants querient directement les donnees conso "
        "(doivent utiliser consumption_unified_service.py) :\n" + "\n".join(f"  - {v}" for v in violations)
    )
