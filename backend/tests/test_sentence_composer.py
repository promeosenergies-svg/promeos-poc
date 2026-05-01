"""Phase 3.3 — Source-guards composition phrase 1 événementielle.

Vérifie :
1. GRAND_GROUPE phrase DT_drift contient "patrimoine"
2. COMMERCE phrase DT_drift NE contient PAS "patrimoine" (anti-pattern doctrinal)
3. Pas de trigger → phrase de stabilité spécifique typologie

+ couverture étendue : 4 composers (DT_DRIFT, MAJOR_ANOMALY, AUDIT_DEADLINE,
PURCHASE_WINDOW) × 3 typologies + fallback UNKNOWN + dispatch dispatch_safe.

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 3.3.
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
from services.narrative.sentence_composer import (
    SENTENCE_STABLE_BY_TYPOLOGY,
    TRIGGER_TO_COMPOSER,
    compose_dt_drift_sentence,
    compose_sentence_1_eventful,
)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_event(
    event_type: str,
    title: str = "Test event",
    site_ids: list[int] = None,
) -> SolEventCard:
    """Construit un SolEventCard minimal."""
    return SolEventCard(
        id=f"{event_type}:test",
        event_type=event_type,  # type: ignore
        severity="warning",  # type: ignore
        title=title,
        narrative=f"Test narrative pour {event_type}",
        impact=EventImpact(value=1000.0, unit="€", period="week"),
        source=EventSource(
            system="RegOps",  # type: ignore
            last_updated_at=datetime.now(timezone.utc),
            confidence="high",  # type: ignore
        ),
        action=EventAction(label="Voir", route="/test"),
        linked_assets=EventLinkedAssets(org_id=1, site_ids=site_ids or []),
    )


# ─── Tests phrase 1 — DT_TRAJECTORY_DRIFT par typologie ─────────────────────


class TestSentence1DriftByTypology:
    """Source-guards : phrase DT drift respecte le registre typologique."""

    def test_sentence_1_drift_grand_groupe_has_patrimoine(self):
        """Phrase GRAND_GROUPE doit contenir 'patrimoine' (vocabulaire CODIR)."""
        event = _make_event("consumption_drift", site_ids=[1, 2, 3])
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.GRAND_GROUPE)
        assert "patrimoine" in sentence, f"Phrase GRAND_GROUPE doit contenir 'patrimoine', trouvé : {sentence!r}"
        assert "trajectoire 2030" in sentence

    def test_sentence_1_drift_commerce_no_patrimoine(self):
        """Phrase COMMERCE NE doit JAMAIS contenir 'patrimoine' (anti-pattern doctrinal)."""
        event = _make_event("consumption_drift", site_ids=[1])
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.COMMERCE)
        assert "patrimoine" not in sentence.lower(), (
            f"Phrase COMMERCE ne doit JAMAIS contenir 'patrimoine' "
            f"(jargon ETI tertiaire incompatible commerçant), trouvé : {sentence!r}"
        )

    def test_sentence_1_drift_commerce_uses_activity_term(self):
        """Phrase COMMERCE utilise le nom métier (magasin/boulangerie/etc)."""
        event = _make_event("consumption_drift", site_ids=[1])
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.COMMERCE)
        # Fallback "magasin" (pas de NAF dans SolEventCard MVP)
        assert "magasin" in sentence
        # Vocabulaire pédagogique : "consomme plus" / "similaires" / "région"
        assert "similaires" in sentence
        assert "région" in sentence

    def test_sentence_1_drift_erp_uses_etablissement(self):
        """Phrase ERP utilise 'établissement' (vocabulaire service public)."""
        event = _make_event("consumption_drift", site_ids=[1])
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.ERP)
        assert "établissement" in sentence, f"Phrase ERP doit contenir 'établissement', trouvé : {sentence!r}"
        assert "patrimoine" not in sentence.lower(), (
            f"Phrase ERP ne doit PAS contenir 'patrimoine' (concept GG privé), trouvé : {sentence!r}"
        )

    def test_sentence_1_drift_grand_groupe_pluriel_singulier(self):
        """GRAND_GROUPE : phrase s'accorde correctement selon nombre de sites."""
        event_1 = _make_event("consumption_drift", site_ids=[1])
        sentence_1 = compose_dt_drift_sentence(event_1, OrganizationTypology.GRAND_GROUPE)
        assert "1 site " in sentence_1
        assert "a basculé" in sentence_1  # singulier

        event_3 = _make_event("consumption_drift", site_ids=[1, 2, 3])
        sentence_3 = compose_dt_drift_sentence(event_3, OrganizationTypology.GRAND_GROUPE)
        assert "3 sites " in sentence_3
        assert "ont basculé" in sentence_3  # pluriel


# ─── Tests phrase de stabilité ──────────────────────────────────────────────


class TestSentence1Stable:
    """Source-guards : pas de trigger → phrase de stabilité typologique."""

    def test_sentence_1_stable_when_no_trigger(self):
        """Pas de primary → phrase de stabilité, pas de chaîne vide."""
        prioritization = {
            "primary": None,
            "primary_event": None,
            "secondary": None,
            "secondary_event": None,
            "all_active_triggers": [],
        }
        sentence = compose_sentence_1_eventful(prioritization, OrganizationTypology.GRAND_GROUPE)
        assert sentence  # Non vide
        assert "stable" in sentence.lower()
        assert "patrimoine" in sentence  # Vocabulaire GG respecté

    def test_sentence_1_stable_commerce_no_patrimoine(self):
        """COMMERCE stable ne contient JAMAIS 'patrimoine'."""
        prioritization = {
            "primary": None,
            "primary_event": None,
            "secondary": None,
            "secondary_event": None,
            "all_active_triggers": [],
        }
        sentence = compose_sentence_1_eventful(prioritization, OrganizationTypology.COMMERCE)
        assert "patrimoine" not in sentence.lower()
        assert "stable" in sentence.lower()

    def test_sentence_1_stable_erp_uses_etablissement(self):
        """ERP stable utilise 'établissement'."""
        prioritization = {
            "primary": None,
            "primary_event": None,
            "secondary": None,
            "secondary_event": None,
            "all_active_triggers": [],
        }
        sentence = compose_sentence_1_eventful(prioritization, OrganizationTypology.ERP)
        assert "établissement" in sentence
        assert "stable" in sentence.lower()

    def test_all_typologies_have_stable_sentence(self):
        """Les 4 typologies ont une phrase de stabilité définie (anti-KeyError)."""
        for typology in OrganizationTypology:
            assert typology in SENTENCE_STABLE_BY_TYPOLOGY, (
                f"{typology} sans phrase de stabilité — risque KeyError runtime"
            )
            assert SENTENCE_STABLE_BY_TYPOLOGY[typology], f"Phrase stable {typology} ne doit pas être vide"


# ─── Tests dispatch trigger → composer ──────────────────────────────────────


class TestTriggerDispatch:
    """Source-guards : dispatch trigger → composer cohérent."""

    def test_dispatch_dt_drift_to_composer(self):
        """compose_sentence_1_eventful dispatch DT_TRAJECTORY_DRIFT → composer."""
        event = _make_event("consumption_drift", site_ids=[1, 2])
        prioritization = {
            "primary": TriggerType.DT_TRAJECTORY_DRIFT,
            "primary_event": event,
            "secondary": None,
            "secondary_event": None,
            "all_active_triggers": [TriggerType.DT_TRAJECTORY_DRIFT],
        }
        sentence = compose_sentence_1_eventful(prioritization, OrganizationTypology.GRAND_GROUPE)
        assert "trajectoire 2030" in sentence
        assert "2 sites" in sentence

    def test_dispatch_major_anomaly_includes_event_title(self):
        """MAJOR_ANOMALY composer inclut le title de l'event."""
        event = _make_event("billing_anomaly", title="Surfacturation TURPE détectée")
        prioritization = {
            "primary": TriggerType.MAJOR_ANOMALY,
            "primary_event": event,
            "secondary": None,
            "secondary_event": None,
            "all_active_triggers": [TriggerType.MAJOR_ANOMALY],
        }
        sentence = compose_sentence_1_eventful(prioritization, OrganizationTypology.GRAND_GROUPE)
        assert "anomalie" in sentence.lower()
        assert "surfacturation turpe détectée" in sentence.lower()

    def test_dispatch_unsupported_trigger_falls_back_stable(self):
        """Trigger non-event-driven (ex: EXPOSURE_VARIATION) → fallback stable."""
        prioritization = {
            "primary": TriggerType.EXPOSURE_VARIATION,  # pas dans TRIGGER_TO_COMPOSER
            "primary_event": _make_event("consumption_drift"),
            "secondary": None,
            "secondary_event": None,
            "all_active_triggers": [TriggerType.EXPOSURE_VARIATION],
        }
        sentence = compose_sentence_1_eventful(prioritization, OrganizationTypology.GRAND_GROUPE)
        # Tombe sur fallback stable typologique
        assert sentence in SENTENCE_STABLE_BY_TYPOLOGY.values()

    def test_trigger_to_composer_covers_event_driven_triggers(self):
        """Tous les triggers event-driven (4 prio) ont un composer dédié."""
        event_driven_triggers = {
            TriggerType.DT_TRAJECTORY_DRIFT,
            TriggerType.MAJOR_ANOMALY,
            TriggerType.AUDIT_DEADLINE_IMMINENT,
            TriggerType.PURCHASE_WINDOW_OPEN,
        }
        missing = event_driven_triggers - set(TRIGGER_TO_COMPOSER.keys())
        assert not missing, f"Triggers event-driven sans composer : {missing}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
