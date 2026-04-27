"""Vérifie l'intégrité du registre KPI."""
import pytest

from doctrine.kpi_registry import KPI_REGISTRY, get_kpi


def test_registry_not_empty():
    assert len(KPI_REGISTRY) >= 7, "Au moins les 7 KPIs prioritaires cockpit (§8.2)"


def test_each_kpi_has_full_fiche():
    for kpi_id, kpi in KPI_REGISTRY.items():
        assert kpi.kpi_id == kpi_id
        assert kpi.label, f"{kpi_id}: label manquant"
        assert kpi.unit, f"{kpi_id}: unit manquante"
        assert kpi.formula, f"{kpi_id}: formula manquante"
        assert kpi.source, f"{kpi_id}: source manquante"
        assert kpi.scope, f"{kpi_id}: scope vide"
        assert kpi.period, f"{kpi_id}: period vide"
        assert kpi.freshness in {"realtime", "daily", "monthly", "on_import"}
        assert kpi.confidence_rule, f"{kpi_id}: confidence_rule manquante"
        assert kpi.owner, f"{kpi_id}: owner manquant"
        assert kpi.used_in, f"{kpi_id}: used_in vide"


def test_get_kpi_raises_on_unknown():
    with pytest.raises(KeyError, match="non enregistré"):
        get_kpi("kpi_inexistant_xyz")
