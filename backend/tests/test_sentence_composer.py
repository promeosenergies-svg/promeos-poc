"""Phase 3.3 + 4.0.A — Source-guards composition phrase 1 événementielle.

Vérifie :

## Phase 3.3 (initiale)
1. GRAND_GROUPE phrase DT_drift contient "patrimoine"
2. COMMERCE phrase DT_drift NE contient PAS "patrimoine" (anti-pattern doctrinal)
3. Pas de trigger → phrase de stabilité spécifique typologie

## Phase 4.0.A (corrections audit drift §6 + §7)
4. Sourçage §7 : chaque sentence cite (source X, confiance Y)
5. NO `.lower()` sur event.title (préservation sigles TURPE/CTA/etc)
6. Format FR sur chiffres (espaces milliers, %, €)
7. Anti-paternalisme COMMERCE : chiffre ou qualification présent
8. Garde-fou MAX_PHRASE_1_WORDS (lecture 3 min §11.3)
9. Phrases stables avec ancrage positif (audit Marie/CX)

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 3.3 + audit Phase 4.0.A (3 P0 convergents).
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
    MAX_PHRASE_1_WORDS,
    SENTENCE_STABLE_BY_TYPOLOGY,
    SENTENCE_STABLE_TEMPLATES,
    TRIGGER_TO_COMPOSER,
    _format_eur_fr,
    _format_pct_fr,
    compose_audit_deadline_sentence,
    compose_dt_drift_sentence,
    compose_major_anomaly_sentence,
    compose_purchase_window_sentence,
    compose_sentence_1_eventful,
)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_event(
    event_type: str,
    title: str = "Test event",
    site_ids: list[int] = None,
    impact_value: float = 1000.0,
    impact_unit: str = "€",
    source_system: str = "RegOps",
    confidence: str = "high",
) -> SolEventCard:
    """Construit un SolEventCard minimal."""
    return SolEventCard(
        id=f"{event_type}:test",
        event_type=event_type,  # type: ignore
        severity="warning",  # type: ignore
        title=title,
        narrative=f"Test narrative pour {event_type}",
        impact=EventImpact(value=impact_value, unit=impact_unit, period="week"),  # type: ignore
        source=EventSource(
            system=source_system,  # type: ignore
            last_updated_at=datetime.now(timezone.utc),
            confidence=confidence,  # type: ignore
        ),
        action=EventAction(label="Voir", route="/test"),
        linked_assets=EventLinkedAssets(org_id=1, site_ids=site_ids or []),
    )


# ─── Phase 3.3 — Tests phrase 1 par typologie ───────────────────────────────


class TestSentence1DriftByTypology:
    """Source-guards Phase 3.3 : phrase DT drift respecte le registre typologique."""

    def test_sentence_1_drift_grand_groupe_has_patrimoine(self):
        """Phrase GRAND_GROUPE doit contenir 'patrimoine' (vocabulaire CODIR)."""
        event = _make_event("consumption_drift", site_ids=[1, 2, 3])
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.GRAND_GROUPE)
        assert "patrimoine" in sentence, f"Phrase GRAND_GROUPE doit contenir 'patrimoine', trouvé : {sentence!r}"
        # Phase 4.0.A : jalon canonique remplace 'trajectoire 2030' générique
        assert "Décret Tertiaire" in sentence

    def test_sentence_1_drift_commerce_no_patrimoine(self):
        """Phrase COMMERCE NE doit JAMAIS contenir 'patrimoine'."""
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
        assert "magasin" in sentence  # fallback NAF None
        assert "région" in sentence

    def test_sentence_1_drift_commerce_naf_propagated_uses_boulangerie(self):
        """Phase 7 correctif B : NAF 4724Z propagé → 'boulangerie' (pas 'magasin')."""
        event = _make_event("consumption_drift", site_ids=[1])
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.COMMERCE, naf_code="4724Z")
        assert "boulangerie" in sentence
        assert "magasin" not in sentence

    def test_sentence_1_drift_commerce_naf_5610a_uses_restaurant(self):
        """Phase 7 correctif B : NAF 5610A → 'restaurant'."""
        event = _make_event("consumption_drift", site_ids=[1])
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.COMMERCE, naf_code="5610A")
        assert "restaurant" in sentence

    def test_compose_sentence_1_eventful_propagates_naf(self):
        """compose_sentence_1_eventful propage naf_code à compose_dt_drift_sentence."""
        event = _make_event("consumption_drift", site_ids=[1])
        prioritization = {
            "primary": TriggerType.DT_TRAJECTORY_DRIFT,
            "primary_event": event,
            "secondary": None,
            "secondary_event": None,
            "all_active_triggers": [TriggerType.DT_TRAJECTORY_DRIFT],
        }
        sentence = compose_sentence_1_eventful(prioritization, OrganizationTypology.COMMERCE, naf_code="4724Z")
        assert "boulangerie" in sentence

    def test_compose_sentence_1_eventful_naf_ignored_for_non_drift(self):
        """naf_code ignoré silencieusement pour composers qui ne l'acceptent pas."""
        event = _make_event("billing_anomaly", title="TURPE")
        prioritization = {
            "primary": TriggerType.MAJOR_ANOMALY,
            "primary_event": event,
            "secondary": None,
            "secondary_event": None,
            "all_active_triggers": [TriggerType.MAJOR_ANOMALY],
        }
        # naf_code passé mais major_anomaly_sentence ne l'utilise pas → pas d'erreur
        sentence = compose_sentence_1_eventful(prioritization, OrganizationTypology.COMMERCE, naf_code="4724Z")
        assert "TURPE" in sentence

    def test_sentence_1_drift_erp_uses_etablissement(self):
        """Phrase ERP utilise 'établissement' (vocabulaire service public)."""
        event = _make_event("consumption_drift", site_ids=[1])
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.ERP)
        assert "établissement" in sentence
        assert "patrimoine" not in sentence.lower()

    def test_sentence_1_drift_grand_groupe_pluriel_singulier(self):
        """GRAND_GROUPE : phrase s'accorde correctement selon nombre de sites."""
        event_1 = _make_event("consumption_drift", site_ids=[1])
        sentence_1 = compose_dt_drift_sentence(event_1, OrganizationTypology.GRAND_GROUPE)
        assert "1 site " in sentence_1
        assert "a basculé" in sentence_1

        event_3 = _make_event("consumption_drift", site_ids=[1, 2, 3])
        sentence_3 = compose_dt_drift_sentence(event_3, OrganizationTypology.GRAND_GROUPE)
        assert "3 sites " in sentence_3
        assert "ont basculé" in sentence_3


# ─── Phase 4.0.A — Source-guards sourçage §7 ────────────────────────────────


class TestSentenceContainsSourceCitation:
    """Source-guards §7 : chaque phrase 1 cite la source + le niveau de confiance."""

    def test_dt_drift_grand_groupe_cites_source(self):
        """GRAND_GROUPE DT_drift contient '(source ...)'."""
        event = _make_event("consumption_drift", site_ids=[1, 2], source_system="RegOps", confidence="high")
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.GRAND_GROUPE)
        assert "(source " in sentence, f"Sourçage §7 manquant : {sentence!r}"
        assert "confiance" in sentence

    def test_dt_drift_grand_groupe_cites_confidence_haute(self):
        """confidence=high → 'confiance haute' (libellé FR)."""
        event = _make_event("consumption_drift", site_ids=[1], confidence="high")
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.GRAND_GROUPE)
        assert "confiance haute" in sentence

    def test_dt_drift_cites_confidence_moyenne(self):
        """confidence=medium → 'confiance moyenne' (pas 'medium' brut)."""
        event = _make_event("consumption_drift", site_ids=[1], confidence="medium")
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.GRAND_GROUPE)
        assert "confiance moyenne" in sentence

    def test_major_anomaly_cites_source(self):
        """MAJOR_ANOMALY contient (source X, confiance Y) toutes typologies."""
        event = _make_event("billing_anomaly", title="Surfacturation TURPE")
        for typology in [
            OrganizationTypology.GRAND_GROUPE,
            OrganizationTypology.COMMERCE,
            OrganizationTypology.ERP,
        ]:
            sentence = compose_major_anomaly_sentence(event, typology)
            assert "(source " in sentence, f"Sourçage manquant {typology}: {sentence!r}"
            assert "confiance" in sentence

    def test_audit_deadline_cites_source(self):
        event = _make_event("compliance_deadline", title="OPERAT 30/09/2026")
        sentence = compose_audit_deadline_sentence(event, OrganizationTypology.GRAND_GROUPE)
        assert "(source " in sentence
        assert "confiance" in sentence

    def test_purchase_window_cites_source(self):
        event = _make_event("contract_renewal", title="Contrat fournisseur expire 31/12/2026")
        sentence = compose_purchase_window_sentence(event, OrganizationTypology.GRAND_GROUPE)
        assert "(source " in sentence


# ─── Phase 4.0.A — Source-guards préservation sigles ───────────────────────


class TestSiglesPreservation:
    """Source-guards §6 : pas de .lower() sur event.title (sigles préservés)."""

    def test_no_lower_on_turpe_sigle(self):
        """TURPE doit rester TURPE (pas turpe) — perte de crédibilité CFO sinon."""
        event = _make_event("billing_anomaly", title="Surfacturation TURPE 6 sur PDL 14529")
        sentence = compose_major_anomaly_sentence(event, OrganizationTypology.GRAND_GROUPE)
        assert "TURPE" in sentence, f"Sigle TURPE cassé en lowercase : {sentence!r}"
        assert "PDL" in sentence

    def test_no_lower_on_audit_deadline_title(self):
        """Échéance OPERAT/BACS/APER conserve les majuscules."""
        event = _make_event("compliance_deadline", title="OPERAT déclaration 30/09/2026")
        sentence = compose_audit_deadline_sentence(event, OrganizationTypology.GRAND_GROUPE)
        assert "OPERAT" in sentence, f"Sigle OPERAT cassé : {sentence!r}"

    def test_no_lower_on_purchase_window_title(self):
        """Fenêtre achat conserve les majuscules de marque (CRE / VNU / etc)."""
        event = _make_event("market_window", title="Capacité RTE 1/11/2026 + VNU post-ARENH")
        sentence = compose_purchase_window_sentence(event, OrganizationTypology.GRAND_GROUPE)
        assert "RTE" in sentence
        assert "VNU" in sentence
        assert "ARENH" in sentence


# ─── Phase 4.0.A — Source-guards anti-paternalisme COMMERCE ────────────────


class TestCommerceAntiPaternalisme:
    """Source-guards §6 : phrase COMMERCE doit ancrer un chiffre ou une qualification."""

    def test_commerce_dt_drift_with_pct_impact_uses_pct(self):
        """COMMERCE DT_drift avec impact en % → injecte +X %."""
        event = _make_event("consumption_drift", site_ids=[1], impact_value=14.0, impact_unit="%")
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.COMMERCE)
        assert "+14 %" in sentence, f"Pourcentage attendu : {sentence!r}"

    def test_commerce_dt_drift_with_eur_impact_uses_surcout(self):
        """COMMERCE DT_drift avec impact en € → injecte 'surcoût X €'."""
        event = _make_event("consumption_drift", site_ids=[1], impact_value=230.0, impact_unit="€")
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.COMMERCE)
        assert "230 €" in sentence
        assert "surcoût" in sentence

    def test_commerce_dt_drift_no_impact_qualifies_ecart(self):
        """COMMERCE sans impact → qualifie l'écart (pas paternaliste, pas vague)."""
        event = _make_event("consumption_drift", site_ids=[1], impact_value=None)
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.COMMERCE)
        # Doit contenir une qualification ou une mention concrète, pas juste "plus"
        assert "écart marqué" in sentence or "+" in sentence


# ─── Phase 4.0.A — Source-guards format FR ─────────────────────────────────


class TestFormatFR:
    """Source-guards : helpers format_eur_fr et format_pct_fr."""

    def test_format_eur_fr_thousands_separator_space(self):
        """1234 → '1 234 €' (espace milliers FR)."""
        assert _format_eur_fr(1234) == "1 234 €"

    def test_format_eur_fr_million(self):
        assert _format_eur_fr(1234567) == "1 234 567 €"

    def test_format_pct_fr_positive_sign(self):
        assert _format_pct_fr(14.3) == "+14 %"

    def test_format_pct_fr_negative_unicode_minus(self):
        """Pourcentage négatif utilise minus Unicode (− ≠ - hyphen)."""
        assert _format_pct_fr(-12.7) == "−13 %"

    def test_format_pct_fr_zero(self):
        assert _format_pct_fr(0) == "0 %"


# ─── Phase 4.0.A — Source-guards garde-fou longueur ─────────────────────────


class TestPhraseLengthGuard:
    """Source-guards : MAX_PHRASE_1_WORDS respecté pour lecture 3 min §11.3."""

    def test_max_phrase_1_words_constant_defined(self):
        """MAX_PHRASE_1_WORDS exposé (≤ 35 mots pour budget 3 min)."""
        assert isinstance(MAX_PHRASE_1_WORDS, int)
        assert MAX_PHRASE_1_WORDS <= 35

    def test_dt_drift_grand_groupe_within_budget(self):
        """Phrase DT_drift GG ne dépasse pas MAX_PHRASE_1_WORDS."""
        event = _make_event("consumption_drift", site_ids=[1, 2, 3])
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.GRAND_GROUPE)
        word_count = len(sentence.split())
        assert word_count <= MAX_PHRASE_1_WORDS, (
            f"Phrase trop longue : {word_count} mots > {MAX_PHRASE_1_WORDS} max — {sentence!r}"
        )

    def test_all_stable_sentences_within_budget(self):
        """Phrases stables des 4 typologies sous le budget."""
        for typology, sentence in SENTENCE_STABLE_TEMPLATES.items():
            word_count = len(sentence.split())
            assert word_count <= MAX_PHRASE_1_WORDS, f"Stable {typology} = {word_count} mots > {MAX_PHRASE_1_WORDS} max"


# ─── Phase 4.0.A — Source-guards stabilité positive ────────────────────────


class TestStableSentencesPositive:
    """Source-guards audit Marie/CX : stabilité = ancrage positif (pas creux)."""

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
        assert sentence
        # Phase 4.0.A : ton confiant "tient sa trajectoire" (pas "rien à signaler")
        assert "tient" in sentence.lower(), (
            f"Phrase stable doit avoir un ancrage positif (ex: 'tient'), trouvé : {sentence!r}"
        )

    def test_sentence_1_stable_no_codir_for_grand_groupe(self):
        """GRAND_GROUPE stable : pas de mention CODIR (audit Marie — vocabulaire trop corporate)."""
        sentence = SENTENCE_STABLE_TEMPLATES[OrganizationTypology.GRAND_GROUPE]
        assert "CODIR" not in sentence, f"Audit Marie : 'CODIR' inutilisable ETI midmarket — trouvé : {sentence!r}"

    def test_sentence_1_stable_commerce_no_patrimoine(self):
        sentence = SENTENCE_STABLE_TEMPLATES[OrganizationTypology.COMMERCE]
        assert "patrimoine" not in sentence.lower()

    def test_sentence_1_stable_erp_uses_etablissement(self):
        sentence = SENTENCE_STABLE_TEMPLATES[OrganizationTypology.ERP]
        assert "établissement" in sentence

    def test_all_typologies_have_stable_sentence(self):
        """Les 4 typologies ont une phrase de stabilité définie."""
        for typology in OrganizationTypology:
            assert typology in SENTENCE_STABLE_TEMPLATES
            assert SENTENCE_STABLE_TEMPLATES[typology]

    def test_backward_compat_alias(self):
        """SENTENCE_STABLE_BY_TYPOLOGY alias garde rétrocompat des imports."""
        assert SENTENCE_STABLE_BY_TYPOLOGY is SENTENCE_STABLE_TEMPLATES


# ─── Phase 3.3 — Tests dispatch trigger → composer ─────────────────────────


class TestTriggerDispatch:
    """Source-guards Phase 3.3 : dispatch trigger → composer cohérent."""

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
        assert "Décret Tertiaire" in sentence
        assert "2 sites" in sentence

    def test_dispatch_major_anomaly_includes_event_title(self):
        """MAJOR_ANOMALY composer inclut le title (sans .lower())."""
        event = _make_event("billing_anomaly", title="Surfacturation TURPE détectée")
        prioritization = {
            "primary": TriggerType.MAJOR_ANOMALY,
            "primary_event": event,
            "secondary": None,
            "secondary_event": None,
            "all_active_triggers": [TriggerType.MAJOR_ANOMALY],
        }
        sentence = compose_sentence_1_eventful(prioritization, OrganizationTypology.GRAND_GROUPE)
        assert "Surfacturation TURPE détectée" in sentence  # casse préservée

    def test_dispatch_unsupported_trigger_falls_back_stable(self):
        """Trigger non-event-driven → fallback stable typologique."""
        prioritization = {
            "primary": TriggerType.EXPOSURE_VARIATION,
            "primary_event": _make_event("consumption_drift"),
            "secondary": None,
            "secondary_event": None,
            "all_active_triggers": [TriggerType.EXPOSURE_VARIATION],
        }
        sentence = compose_sentence_1_eventful(prioritization, OrganizationTypology.GRAND_GROUPE)
        assert sentence in SENTENCE_STABLE_TEMPLATES.values()

    def test_trigger_to_composer_covers_event_driven_triggers(self):
        """Tous les triggers event-driven (4) ont un composer dédié."""
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
