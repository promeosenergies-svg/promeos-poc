"""Phase 3.2 — Source-guards trigger prioritizer (Option 4.C primary + secondary).

Vérifie :
1. Multiple triggers → primary = priorité 1 (DT_TRAJECTORY_DRIFT)
2. Max 2 triggers tissés (primary + secondary), jamais 3+
3. COMPLIANCE_THRESHOLD_CROSSED jamais primary pour COMMERCE (masqué)
4. Aucun event → primary = None (silence narratif, pas d'erreur)

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 3.2.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from doctrine.naf_to_typology import OrganizationTypology
from doctrine.triggers import TriggerType
from services.event_bus.types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventSource,
    SolEventCard,
)
from services.narrative.trigger_prioritizer import prioritize_triggers


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_event(event_type: str, severity: str = "warning", title: str = "test") -> SolEventCard:
    """Construit un SolEventCard minimal pour les tests."""
    return SolEventCard(
        id=f"{event_type}:test",
        event_type=event_type,  # type: ignore
        severity=severity,  # type: ignore
        title=title,
        narrative=f"Test narrative pour {event_type}",
        impact=EventImpact(value=1000.0, unit="€", period="week"),
        source=EventSource(
            system="RegOps",  # type: ignore
            last_updated_at=datetime.now(timezone.utc),
            confidence="high",  # type: ignore
        ),
        action=EventAction(label="Voir détail", route="/test"),
        linked_assets=EventLinkedAssets(org_id=1),
    )


# ─── Tests prioritizer — primary selection ──────────────────────────────────


class TestPrioritizerPrimarySelection:
    """Source-guards : primary = trigger de plus haute priorité."""

    def test_prioritizer_returns_top_priority(self):
        """Multiple triggers → primary = priorité 1 (DT_TRAJECTORY_DRIFT)."""
        events = [
            _make_event("contract_renewal"),  # PURCHASE_WINDOW_OPEN prio 5
            _make_event("consumption_drift"),  # DT_TRAJECTORY_DRIFT prio 1
            _make_event("compliance_deadline"),  # AUDIT_DEADLINE_IMMINENT prio 4
        ]
        result = prioritize_triggers(events, OrganizationTypology.GRAND_GROUPE)
        assert result["primary"] == TriggerType.DT_TRAJECTORY_DRIFT, (
            f"Primary doit être DT_TRAJECTORY_DRIFT (prio 1), trouvé : {result['primary']}"
        )
        assert result["primary_event"].event_type == "consumption_drift"

    def test_prioritizer_secondary_is_priority_2(self):
        """Avec 3 triggers (prio 1, 4, 5), secondary = priorité 4."""
        events = [
            _make_event("contract_renewal"),  # prio 5
            _make_event("consumption_drift"),  # prio 1
            _make_event("compliance_deadline"),  # prio 4
        ]
        result = prioritize_triggers(events, OrganizationTypology.GRAND_GROUPE)
        assert result["secondary"] == TriggerType.AUDIT_DEADLINE_IMMINENT, (
            f"Secondary doit être AUDIT_DEADLINE_IMMINENT (prio 4 après prio 1), trouvé : {result['secondary']}"
        )


class TestPrioritizerMaxTwoInBody:
    """Source-guard cardinal : Option 4.C — jamais 3+ triggers tissés en body."""

    def test_prioritizer_max_2_in_body(self):
        """Quel que soit le nombre d'events, primary + secondary uniquement (max 2)."""
        # 5 triggers distincts
        events = [
            _make_event("consumption_drift"),  # DT_TRAJECTORY_DRIFT prio 1
            _make_event("billing_anomaly"),  # MAJOR_ANOMALY prio 2
            _make_event("compliance_deadline"),  # AUDIT_DEADLINE_IMMINENT prio 4
            _make_event("contract_renewal"),  # PURCHASE_WINDOW_OPEN prio 5
            _make_event("market_window"),  # PURCHASE_WINDOW_OPEN prio 5 (dédup)
        ]
        result = prioritize_triggers(events, OrganizationTypology.GRAND_GROUPE)
        # Primary + secondary garantis non-None ; mais on ne tisse en body
        # que ces 2-là ; les autres sont dans all_active_triggers pour
        # la pile <SolEventStream>.
        assert result["primary"] is not None
        assert result["secondary"] is not None
        # On vérifie qu'il y a bien plus que 2 triggers actifs détectés mais
        # que le contrat primary/secondary respecte max 2.
        assert len(result["all_active_triggers"]) >= 3, (
            "Test setup : on doit avoir 3+ triggers actifs pour valider le contrat max 2"
        )
        # primary + secondary = 2 places exposées en body, jamais plus
        body_slots = [r for r in (result["primary"], result["secondary"]) if r is not None]
        assert len(body_slots) <= 2, f"Body ne doit avoir que 2 slots max, trouvé {len(body_slots)}"

    def test_prioritizer_dedup_same_trigger(self):
        """Plusieurs events mappant sur le même trigger → 1 seule occurrence."""
        events = [
            _make_event("billing_anomaly", title="Anomalie A"),  # MAJOR_ANOMALY
            _make_event("action_overdue", title="Action B"),  # MAJOR_ANOMALY (dédup)
            _make_event("billing_anomaly", title="Anomalie C"),  # MAJOR_ANOMALY (dédup)
        ]
        result = prioritize_triggers(events, OrganizationTypology.GRAND_GROUPE)
        assert result["primary"] == TriggerType.MAJOR_ANOMALY
        assert result["secondary"] is None  # Pas de second trigger distinct
        assert result["all_active_triggers"] == [TriggerType.MAJOR_ANOMALY]


# ─── Tests prioritizer — masquage par typologie ─────────────────────────────


class TestPrioritizerCommerceMasks:
    """Source-guard : COMMERCE masque COMPLIANCE_THRESHOLD_CROSSED + EXPOSURE_VARIATION."""

    def test_prioritizer_masks_compliance_for_commerce(self):
        """COMMERCE : compliance_deadline reste actif mais score abstrait masqué.

        Note : `compliance_deadline` event_type → AUDIT_DEADLINE_IMMINENT trigger,
        non masqué pour COMMERCE. Seul COMPLIANCE_THRESHOLD_CROSSED (calculé via
        score, pas un event_type direct) est masqué — il ne peut jamais devenir
        primary via le prioritizer. Le test vérifie qu'aucun event entrant ne
        peut faire surgir un trigger masqué.
        """
        # On simule un trigger masqué qui aurait été produit (impossible en
        # pratique avec EVENT_TYPE_TO_TRIGGER, mais le filtre doit tenir).
        events = [
            _make_event("consumption_drift"),  # DT_TRAJECTORY_DRIFT (actif)
            _make_event("compliance_deadline"),  # AUDIT_DEADLINE_IMMINENT (actif)
        ]
        result = prioritize_triggers(events, OrganizationTypology.COMMERCE)
        active = result["all_active_triggers"]
        # Ces 2 triggers ne sont pas masqués pour COMMERCE
        assert TriggerType.DT_TRAJECTORY_DRIFT in active
        assert TriggerType.AUDIT_DEADLINE_IMMINENT in active
        # Vérifier qu'aucun trigger masqué ne s'est faufilé
        from doctrine.triggers import MASKED_TRIGGERS_BY_TYPOLOGY

        masked = MASKED_TRIGGERS_BY_TYPOLOGY[OrganizationTypology.COMMERCE]
        leak = set(active) & masked
        assert not leak, f"Triggers masqués COMMERCE leakés en body : {leak}"


# ─── Tests prioritizer — silence ────────────────────────────────────────────


class TestPrioritizerSilence:
    """Source-guards : silence quand pas de trigger actif."""

    def test_prioritizer_silence_when_no_trigger(self):
        """Liste d'events vide → primary = None (pas d'erreur)."""
        result = prioritize_triggers([], OrganizationTypology.GRAND_GROUPE)
        assert result["primary"] is None
        assert result["primary_event"] is None
        assert result["secondary"] is None
        assert result["secondary_event"] is None
        assert result["all_active_triggers"] == []

    def test_prioritizer_silence_when_only_masked_event_types(self):
        """Que des event_types masqués (data_quality / asset_registry / flex)
        → silence narratif (rien ne mérite de phrase, tout reste en pile)."""
        events = [
            _make_event("data_quality_issue"),
            _make_event("asset_registry_issue"),
            _make_event("flex_opportunity"),
        ]
        result = prioritize_triggers(events, OrganizationTypology.GRAND_GROUPE)
        assert result["primary"] is None
        assert result["all_active_triggers"] == []

    def test_prioritizer_silence_for_commerce_when_only_masked_typology_triggers(self):
        """COMMERCE : si tous events tombent sur triggers masqués typologie,
        primary = None (pas de fallback non-désirable)."""
        # COMPLIANCE_THRESHOLD_CROSSED + EXPOSURE_VARIATION sont masqués
        # mais ne sont pas mappés depuis un event_type — donc pas atteignables
        # via prioritizer. On simule un cas avec event_types masqués globaux.
        events = [_make_event("data_quality_issue")]
        result = prioritize_triggers(events, OrganizationTypology.COMMERCE)
        assert result["primary"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
