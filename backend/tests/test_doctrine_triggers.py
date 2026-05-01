"""Phase 3.1 — Source-guards 6 déclencheurs narratifs hiérarchisés.

Vérifie :
1. 6 triggers ont des priorités 1-6 distinctes (pas de doublon priorité)
2. Les 9 event_types canoniques sont mappés (ou explicitement None)
3. COMMERCE masque COMPLIANCE_THRESHOLD_CROSSED + EXPOSURE_VARIATION
4. ERP / GRAND_GROUPE n'ont aucun trigger masqué (audience experte)

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 3.1.
"""

from __future__ import annotations

import pytest

from doctrine.naf_to_typology import OrganizationTypology
from doctrine.triggers import (
    EVENT_TYPE_TO_TRIGGER,
    MASKED_TRIGGERS_BY_TYPOLOGY,
    TRIGGER_PRIORITY,
    TriggerType,
)


# ─── Source-guards priorités triggers ──────────────────────────────────────


class TestTriggerPriorities:
    """Source-guards : 6 triggers, priorités 1-6 distinctes."""

    def test_trigger_priorities_consistent(self):
        """Les 6 triggers ont des priorités 1-6 distinctes (pas de collision)."""
        priorities = list(TRIGGER_PRIORITY.values())
        assert len(priorities) == 6, f"6 triggers attendus, trouvé {len(priorities)}"
        assert sorted(priorities) == [1, 2, 3, 4, 5, 6], (
            f"Priorités doivent être 1-6 strictement, trouvé : {sorted(priorities)}"
        )

    def test_trigger_dt_drift_is_priority_1(self):
        """DT_TRAJECTORY_DRIFT = priorité 1 (déclencheur le plus urgent)."""
        assert TRIGGER_PRIORITY[TriggerType.DT_TRAJECTORY_DRIFT] == 1

    def test_all_trigger_types_have_priority(self):
        """Chaque membre TriggerType a une priorité définie."""
        for trigger in TriggerType:
            assert trigger in TRIGGER_PRIORITY, f"{trigger} sans priorité définie"


# ─── Source-guards mapping event_types → triggers ──────────────────────────


class TestEventTypeMapping:
    """Source-guards : 9 event_types canoniques mappés (ou explicitement None)."""

    def test_detector_mapping_complete(self):
        """Les 9 event_types canoniques sont tous présents dans le mapping."""
        canonical_event_types = {
            "consumption_drift",
            "billing_anomaly",
            "compliance_deadline",
            "contract_renewal",
            "market_window",
            "data_quality_issue",
            "flex_opportunity",
            "asset_registry_issue",
            "action_overdue",
        }
        mapped = set(EVENT_TYPE_TO_TRIGGER.keys())
        missing = canonical_event_types - mapped
        assert not missing, f"event_types non mappés : {missing}"

    def test_consumption_drift_maps_to_dt_trajectory(self):
        assert EVENT_TYPE_TO_TRIGGER["consumption_drift"] == TriggerType.DT_TRAJECTORY_DRIFT

    def test_data_quality_explicitly_masked(self):
        """data_quality_issue = None (masqué de la narrative, reste pile <SolEventStream>)."""
        assert EVENT_TYPE_TO_TRIGGER["data_quality_issue"] is None

    def test_flex_opportunity_explicitly_masked(self):
        """flex_opportunity = None (opportunité, pas déclencheur urgent narratif)."""
        assert EVENT_TYPE_TO_TRIGGER["flex_opportunity"] is None

    def test_asset_registry_explicitly_masked(self):
        """asset_registry_issue = None (technique, pas saillant CFO)."""
        assert EVENT_TYPE_TO_TRIGGER["asset_registry_issue"] is None


# ─── Source-guards triggers masqués par typologie ──────────────────────────


class TestMaskedTriggers:
    """Source-guards : triggers masqués par typologie (doctrine §11.3)."""

    def test_masked_triggers_commerce_includes_compliance_threshold(self):
        """COMMERCE masque COMPLIANCE_THRESHOLD_CROSSED (score abstrait pour commerçant)."""
        assert TriggerType.COMPLIANCE_THRESHOLD_CROSSED in MASKED_TRIGGERS_BY_TYPOLOGY[OrganizationTypology.COMMERCE]

    def test_masked_triggers_commerce_includes_exposure_variation(self):
        """COMMERCE masque EXPOSURE_VARIATION (jargon CFO incompatible commerçant)."""
        assert TriggerType.EXPOSURE_VARIATION in MASKED_TRIGGERS_BY_TYPOLOGY[OrganizationTypology.COMMERCE]

    def test_masked_triggers_erp_empty(self):
        """ERP : tous triggers actifs (directeur établissement = audience experte)."""
        assert MASKED_TRIGGERS_BY_TYPOLOGY[OrganizationTypology.ERP] == set()

    def test_masked_triggers_grand_groupe_empty(self):
        """GRAND_GROUPE : tous triggers actifs (CFO = audience experte)."""
        assert MASKED_TRIGGERS_BY_TYPOLOGY[OrganizationTypology.GRAND_GROUPE] == set()

    def test_all_typologies_have_masked_set_defined(self):
        """Les 4 typologies ont une entrée dans MASKED_TRIGGERS_BY_TYPOLOGY."""
        for typology in OrganizationTypology:
            assert typology in MASKED_TRIGGERS_BY_TYPOLOGY, f"{typology} sans masque défini — risque KeyError runtime"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
