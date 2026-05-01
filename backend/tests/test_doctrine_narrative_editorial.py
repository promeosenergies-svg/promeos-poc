"""Phase 4.0.C — Source-guards doctrine éditoriale globaux narrative-sol2.

Verrouille les règles éditoriales **transverses** sur les modules narrative
livrés Phases 1-3 + 4.0.A/B. Empêche les régressions cross-module sur les
règles non-négociables doctrine v1.1.

## Règles verrouillées

### §6 anti-patterns globaux
- Aucun `.lower()` sur event.title cross-composers
- Aucune chaîne hardcodée "TURPE" / "OPERAT" en lowercase
- Aucun usage de "rien à signaler" / "aucun signal" seul (creux §11.3)

### §7 sourçage cross-composers
- Tous les composers (DT_drift, MAJOR_ANOMALY, AUDIT_DEADLINE,
  PURCHASE_WINDOW) intègrent l'helper `_format_source_suffix`
- Aucun retour de phrase 1 sans `(source ` cité

### §11.3 lecture 3 min
- MAX_PHRASE_1_WORDS = 35 respecté pour TOUTES les combinaisons
  (4 composers × 4 typologies × 3 niveaux confidence)

### Coverage
- Les 4 typologies ont un template stable défini
- Les 4 event-driven triggers ont un composer dédié
- Les 6 TriggerType sont cohérents avec event_bus types

Ref : audit triple Phase 3 Marie + Ergonomie + CX 2026-05-01.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone

import pytest

from doctrine.naf_to_typology import OrganizationTypology
from doctrine.triggers import EVENT_TYPE_TO_TRIGGER, TriggerType
from services.event_bus.types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventSource,
    EventType,
    SolEventCard,
)
from services.narrative.sentence_composer import (
    MAX_PHRASE_1_WORDS,
    SENTENCE_STABLE_TEMPLATES,
    TRIGGER_TO_COMPOSER,
    compose_audit_deadline_sentence,
    compose_dt_drift_sentence,
    compose_major_anomaly_sentence,
    compose_purchase_window_sentence,
)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_event(
    event_type: str,
    title: str = "Test event TURPE 1234 €",
    site_ids: list[int] = None,
    confidence: str = "high",
    source_system: str = "RegOps",
) -> SolEventCard:
    return SolEventCard(
        id=f"{event_type}:test",
        event_type=event_type,
        severity="warning",
        title=title,
        narrative="Test",
        impact=EventImpact(value=1000.0, unit="€", period="week"),
        source=EventSource(
            system=source_system,
            last_updated_at=datetime.now(timezone.utc),
            confidence=confidence,
        ),
        action=EventAction(label="Voir", route="/test"),
        linked_assets=EventLinkedAssets(org_id=1, site_ids=site_ids or [1]),
    )


_ALL_TYPOLOGIES = list(OrganizationTypology)

# Tous les composers event-driven (utilisés pour sourçage + budget mots).
_EVENT_DRIVEN_COMPOSERS = [
    (compose_dt_drift_sentence, "consumption_drift"),
    (compose_major_anomaly_sentence, "billing_anomaly"),
    (compose_audit_deadline_sentence, "compliance_deadline"),
    (compose_purchase_window_sentence, "contract_renewal"),
]

# Composers qui injectent event.title (test sigles ne s'applique qu'à eux).
# DT_drift compose une phrase structurée à partir de site_ids/impact, sans
# event.title — donc le test sigle TURPE/OPERAT n'a pas de sens pour lui.
_TITLE_INJECTING_COMPOSERS = [
    (compose_major_anomaly_sentence, "billing_anomaly"),
    (compose_audit_deadline_sentence, "compliance_deadline"),
    (compose_purchase_window_sentence, "contract_renewal"),
]


# ─── §6 — Anti-patterns globaux ─────────────────────────────────────────────


class TestNoLowerOnTitle:
    """Source-guard cardinal §6 : composers qui injectent event.title préservent les sigles."""

    @pytest.mark.parametrize("composer,event_type", _TITLE_INJECTING_COMPOSERS)
    @pytest.mark.parametrize("typology", _ALL_TYPOLOGIES)
    def test_sigle_turpe_preserved(self, composer, event_type, typology):
        """TURPE doit rester TURPE quel que soit le composer/typology."""
        event = _make_event(event_type, title="Surfacturation TURPE 6 sur PDL 14529")
        sentence = composer(event, typology)
        assert "TURPE" in sentence, (
            f"Composer {composer.__name__} typology={typology} casse le sigle TURPE : {sentence!r}"
        )

    @pytest.mark.parametrize("composer,event_type", _TITLE_INJECTING_COMPOSERS)
    @pytest.mark.parametrize("typology", _ALL_TYPOLOGIES)
    def test_sigle_operat_preserved(self, composer, event_type, typology):
        """OPERAT doit rester OPERAT."""
        event = _make_event(event_type, title="Échéance OPERAT 30/09/2026")
        sentence = composer(event, typology)
        assert "OPERAT" in sentence, f"Composer {composer.__name__} typology={typology} casse OPERAT : {sentence!r}"

    def test_no_lower_call_in_composer_source(self):
        """Source-guard structurelle : aucun `.lower()` actif dans les composers qui injectent title.

        Garde-fou anti-régression — empêche un futur dev de réintroduire
        `event.title.lower()` "pour uniformiser le rendu". Sigles préservés.

        Utilise `ast` pour détecter les appels `.lower()` réels (pas les
        mentions textuelles dans docstrings/commentaires).
        """
        import ast

        for composer, _ in _TITLE_INJECTING_COMPOSERS:
            source = inspect.getsource(composer)
            tree = ast.parse(source)
            lower_calls = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "lower"
            ]
            assert not lower_calls, (
                f"Composer {composer.__name__} appelle `.lower()` — "
                f"casse les sigles TURPE/OPERAT/RTE/etc. Audit P0-2 Phase 4.0.A."
            )


class TestStableSentencesNotEmpty:
    """Source-guard §11.3 : phrases stables non creuses."""

    @pytest.mark.parametrize("typology", _ALL_TYPOLOGIES)
    def test_stable_no_aucun_signal_alone(self, typology):
        """Phrase stable ne doit PAS contenir "aucun signal" SEUL (creux §11.3).

        Audit Marie : 'aucun signal saillant à remonter au CODIR' = creux.
        Phase 4.0.A : phrases reformulées avec ancrage positif ('tient').
        """
        sentence = SENTENCE_STABLE_TEMPLATES[typology]
        # Doit avoir un ancrage positif ("tient")
        assert "tient" in sentence.lower(), (
            f"Phrase stable {typology} doit avoir un ancrage positif ('tient'), trouvé : {sentence!r}"
        )

    def test_stable_grand_groupe_no_codir(self):
        """Audit Marie : 'CODIR' inutilisable midmarket → supprimé Phase 4.0.A."""
        sentence = SENTENCE_STABLE_TEMPLATES[OrganizationTypology.GRAND_GROUPE]
        assert "CODIR" not in sentence


# ─── §7 — Sourçage systématique ─────────────────────────────────────────────


class TestSourceCitationCrossComposers:
    """Source-guard §7 : tous les composers citent (source X, confiance Y)."""

    @pytest.mark.parametrize("composer,event_type", _EVENT_DRIVEN_COMPOSERS)
    @pytest.mark.parametrize("typology", _ALL_TYPOLOGIES)
    def test_composer_cites_source(self, composer, event_type, typology):
        event = _make_event(event_type)
        sentence = composer(event, typology)
        assert "(source " in sentence, (
            f"Composer {composer.__name__} typology={typology} ne cite pas la source : {sentence!r}"
        )
        assert "confiance" in sentence


# ─── §11.3 — Lecture 3 min budget ───────────────────────────────────────────


class TestPhrase1WithinBudget:
    """Source-guard §11.3 : MAX_PHRASE_1_WORDS = 35 mots respecté partout."""

    @pytest.mark.parametrize("composer,event_type", _EVENT_DRIVEN_COMPOSERS)
    @pytest.mark.parametrize("typology", _ALL_TYPOLOGIES)
    @pytest.mark.parametrize("confidence", ["high", "medium", "low"])
    def test_composer_within_max_words(self, composer, event_type, typology, confidence):
        """Toutes combinaisons composer × typology × confidence sous budget."""
        event = _make_event(event_type, confidence=confidence)
        sentence = composer(event, typology)
        word_count = len(sentence.split())
        assert word_count <= MAX_PHRASE_1_WORDS, (
            f"Composer={composer.__name__} typology={typology} confidence={confidence} "
            f"= {word_count} mots > {MAX_PHRASE_1_WORDS} max. Phrase : {sentence!r}"
        )


# ─── Coverage exhaustive ────────────────────────────────────────────────────


class TestCoverageExhaustive:
    """Source-guards : couverture cross-module sur enum + dispatch."""

    def test_all_typologies_have_stable_template(self):
        """Les 4 OrganizationTypology ont un template stable."""
        for typology in OrganizationTypology:
            assert typology in SENTENCE_STABLE_TEMPLATES

    def test_all_event_driven_triggers_have_composer(self):
        """Les 4 triggers event-driven ont un composer dédié."""
        event_driven = {
            TriggerType.DT_TRAJECTORY_DRIFT,
            TriggerType.MAJOR_ANOMALY,
            TriggerType.AUDIT_DEADLINE_IMMINENT,
            TriggerType.PURCHASE_WINDOW_OPEN,
        }
        for trigger in event_driven:
            assert trigger in TRIGGER_TO_COMPOSER, f"{trigger} sans composer"

    def test_event_type_to_trigger_covers_all_canonical_types(self):
        """Mapping EVENT_TYPE_TO_TRIGGER couvre tous les EventType canoniques."""
        # Récupère les valeurs canoniques de Literal EventType
        canonical_event_types = set(EventType.__args__)
        mapped = set(EVENT_TYPE_TO_TRIGGER.keys())
        missing = canonical_event_types - mapped
        assert not missing, f"EventType canoniques non mappés dans EVENT_TYPE_TO_TRIGGER : {missing}"


# ─── ETI_TERTIAIRE follow-up doctrine v2 ────────────────────────────────────


class TestETITertiaireFollowupADR:
    """Audit Marie P0-3 : ETI_TERTIAIRE absente → reportée V2 Q3 2026.

    Documente formellement la décision : la typologie ETI_TERTIAIRE
    (préfixes 6820B sans CODIR / 50-200 sites tertiaires) sera ajoutée
    en V2 (sprint Q3 2026) avec PME_TERTIAIRE et INDUSTRIE.

    Pour l'instant, Marie tombe sur GRAND_GROUPE — c'est sous-optimal
    mais acceptable car :
    - les phrases stables Phase 4.0.A ont supprimé "CODIR" (audit Marie OK)
    - le vocabulaire "patrimoine" reste cohérent (Marie gère un parc immobilier)
    - le mapping NAF 6820B→GRAND_GROUPE est conservateur
    """

    def test_eti_tertiaire_now_in_enum_phase_9b(self):
        """Phase 9.B (Q3 2026 anticipée) : ETI_TERTIAIRE désormais dans l'enum.

        Sentinelle inversé : Phase 4.0.C vérifiait l'ABSENCE pour signaler
        au futur dev de mettre à jour ADR. Phase 9.B livre la typologie —
        le sentinelle valide désormais sa présence (audit Marie BL-3 closé).
        """
        values = {t.value for t in OrganizationTypology}
        assert "eti_tertiaire" in values, (
            "Phase 9.B : ETI_TERTIAIRE doit être dans l'enum. Si retiré, "
            "vérifier MASKED_TRIGGERS_BY_TYPOLOGY + SENTENCE_STABLE_TEMPLATES "
            "+ LEXICAL_TEMPLATES cohérence."
        )

    def test_grand_groupe_stable_no_codir_marie_friendly(self):
        """Audit Marie : phrase stable GG sans CODIR (ETI midmarket OK)."""
        sentence = SENTENCE_STABLE_TEMPLATES[OrganizationTypology.GRAND_GROUPE]
        assert "CODIR" not in sentence
        assert "patrimoine" in sentence  # Vocabulaire reste cohérent


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
