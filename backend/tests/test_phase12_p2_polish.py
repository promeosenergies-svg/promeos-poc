"""Phase 12 — Source-guards P2 polish post-audit personas Phase 11.

Vérifie les 3 frictions résiduelles P2 traitées :

- **12.A** : Marie accroche enrichie (sites_count + surface dans phrase stable)
- **12.B** : Closing ERP conditionnel selon proximité deadline (< 30j)
- **12.C** : Sourçage scope 3 INDUSTRIE (citation ADEME V23.6 dans focus_text CSR)

Audit personas Phase 11 score 9,20/10 — Phase 12 vise 9,5/10 polish.

Ref : audit personas final Phase 11 (commit f8fe39ac).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
from services.narrative.persona_context import (
    PersonaRole,
    compose_persona_mention,
)
from services.narrative.sentence_composer import (
    URGENT_DEADLINE_THRESHOLD_DAYS,
    compose_audit_deadline_sentence,
    compose_sentence_1_eventful,
    compose_sentence_stable_with_archetype,
)


# ─── Phase 12.A — Marie accroche enrichie ──────────────────────────────────


class TestPhase12aArchetypeStable:
    """P2 friction 1 : phrase stable avec ancrage chiffré sites + surface."""

    def test_eti_with_sites_and_surface_enriched(self):
        """Marie ETI 15 sites 35k m² → phrase enrichie 'parc tertiaire de 15 sites'."""
        result = compose_sentence_stable_with_archetype(
            OrganizationTypology.ETI_TERTIAIRE,
            sites_count=15,
            surface_m2_total=35000,
        )
        assert "Votre parc tertiaire de 15 sites" in result
        assert "35 k m²" in result
        # Phrase reste cohérente — préserve la suite "tient sa trajectoire..."
        assert "tient sa trajectoire" in result

    def test_grand_groupe_with_sites_and_surface_enriched(self):
        """Jean-Marc GG 100 sites 500k m² → phrase enrichie 'patrimoine de 100 sites'."""
        result = compose_sentence_stable_with_archetype(
            OrganizationTypology.GRAND_GROUPE,
            sites_count=100,
            surface_m2_total=500_000,
        )
        assert "Votre patrimoine de 100 sites" in result
        assert "500 k m²" in result

    def test_industrie_with_sites_and_surface_enriched(self):
        """Inès groupe industriel 8 sites → phrase enrichie 'groupe industriel de 8 sites'."""
        result = compose_sentence_stable_with_archetype(
            OrganizationTypology.INDUSTRIE,
            sites_count=8,
            surface_m2_total=120_000,
        )
        assert "Votre groupe industriel de 8 sites" in result

    def test_no_sites_falls_back_to_template(self):
        """sites_count=None → fallback sur SENTENCE_STABLE_TEMPLATES."""
        result = compose_sentence_stable_with_archetype(
            OrganizationTypology.ETI_TERTIAIRE, sites_count=None, surface_m2_total=None
        )
        # Pas d'enrichissement, phrase générique
        assert "Votre parc tertiaire de" not in result
        assert result.startswith("Votre parc tient")

    def test_zero_sites_falls_back(self):
        result = compose_sentence_stable_with_archetype(
            OrganizationTypology.ETI_TERTIAIRE, sites_count=0, surface_m2_total=0
        )
        assert "Votre parc tertiaire de" not in result

    def test_commerce_no_enrichment(self):
        """COMMERCE / ERP gardent phrase générique (mono-site typique)."""
        result = compose_sentence_stable_with_archetype(
            OrganizationTypology.COMMERCE, sites_count=1, surface_m2_total=120
        )
        assert "Votre activité" in result
        # Pas d'injection sites
        assert "1 site" not in result

    def test_singular_form_for_1_site(self):
        result = compose_sentence_stable_with_archetype(
            OrganizationTypology.GRAND_GROUPE, sites_count=1, surface_m2_total=200_000
        )
        assert "1 site (" in result  # singulier

    def test_compose_sentence_1_eventful_propagates_archetype_in_silence(self):
        """compose_sentence_1_eventful avec sites_count → phrase stable enrichie."""
        prioritization = {
            "primary": None,
            "primary_event": None,
            "secondary": None,
            "secondary_event": None,
            "all_active_triggers": [],
        }
        result = compose_sentence_1_eventful(
            prioritization,
            OrganizationTypology.ETI_TERTIAIRE,
            sites_count=15,
            surface_m2_total=35000,
        )
        assert "parc tertiaire de 15 sites" in result


# ─── Phase 12.B — Closing ERP conditionnel deadline ────────────────────────


def _make_deadline_event(title: str, deadline_in_days: int) -> SolEventCard:
    """Helper : event AUDIT_DEADLINE avec deadline ISO embarquée dans title."""
    deadline = datetime.now(timezone.utc) + timedelta(days=deadline_in_days)
    title_with_date = f"{title} {deadline.strftime('%Y-%m-%d')}"
    return SolEventCard(
        id="compliance_deadline:test",
        event_type="compliance_deadline",
        severity="warning",
        title=title_with_date,
        narrative="Test deadline",
        impact=EventImpact(value=None, unit="€", period="deadline"),
        source=EventSource(
            system="RegOps",
            last_updated_at=datetime.now(timezone.utc),
            confidence="high",
        ),
        action=EventAction(label="Voir", route="/test"),
        linked_assets=EventLinkedAssets(org_id=1, site_ids=[1]),
    )


class TestPhase12bUrgentDeadline:
    """P2 friction 2 : closing ERP "à porter au prochain conseil" peut diluer
    l'urgence si deadline imminente (< 30j)."""

    def test_urgent_deadline_threshold_constant(self):
        assert URGENT_DEADLINE_THRESHOLD_DAYS == 30

    def test_erp_deadline_dans_60j_uses_conseil_closing(self):
        """ERP deadline > 30j → closing standard 'prochain conseil'."""
        event = _make_deadline_event("OPERAT", deadline_in_days=60)
        result = compose_audit_deadline_sentence(event, OrganizationTypology.ERP)
        assert "prochain conseil" in result
        assert "avant échéance" not in result

    def test_erp_deadline_dans_15j_uses_urgent_closing(self):
        """ERP deadline < 30j → closing urgence 'à traiter avant échéance'."""
        event = _make_deadline_event("OPERAT", deadline_in_days=15)
        result = compose_audit_deadline_sentence(event, OrganizationTypology.ERP)
        assert "avant échéance" in result
        # Closing urgence override le "prochain conseil"
        assert "prochain conseil" not in result

    def test_gg_deadline_imminente_also_urgent(self):
        """GG deadline < 30j → closing urgence (override 'prochain comité')."""
        event = _make_deadline_event("Audit énergétique", deadline_in_days=20)
        result = compose_audit_deadline_sentence(event, OrganizationTypology.GRAND_GROUPE)
        assert "avant échéance" in result

    def test_commerce_deadline_imminente_urgent(self):
        """COMMERCE deadline < 30j → closing urgence override 'cette semaine'."""
        event = _make_deadline_event("Renouvellement contrat", deadline_in_days=10)
        result = compose_audit_deadline_sentence(event, OrganizationTypology.COMMERCE)
        assert "avant échéance" in result

    def test_deadline_passee_pas_urgente(self):
        """Deadline passée (< 0 jours) → pas d'override urgence (déjà ratée)."""
        event = _make_deadline_event("OPERAT", deadline_in_days=-5)
        result = compose_audit_deadline_sentence(event, OrganizationTypology.ERP)
        # Closing standard car deadline déjà passée (pas dans la fenêtre 0-30j)
        assert "prochain conseil" in result

    def test_no_date_in_title_no_urgency(self):
        """Title sans date → closing standard."""
        event = SolEventCard(
            id="test:no-date",
            event_type="compliance_deadline",
            severity="warning",
            title="Échéance à venir",  # pas de date parsable
            narrative="Test",
            impact=EventImpact(value=None, unit="€", period="deadline"),
            source=EventSource(
                system="RegOps",
                last_updated_at=datetime.now(timezone.utc),
                confidence="high",
            ),
            action=EventAction(label="Voir", route="/test"),
            linked_assets=EventLinkedAssets(org_id=1, site_ids=[1]),
        )
        result = compose_audit_deadline_sentence(event, OrganizationTypology.ERP)
        assert "prochain conseil" in result

    def test_fr_date_format_recognized(self):
        """Format DD/MM/YYYY reconnu (en plus du ISO)."""
        deadline = datetime.now(timezone.utc) + timedelta(days=10)
        title_fr = f"OPERAT échéance {deadline.strftime('%d/%m/%Y')}"
        event = SolEventCard(
            id="test:fr-date",
            event_type="compliance_deadline",
            severity="warning",
            title=title_fr,
            narrative="Test",
            impact=EventImpact(value=None, unit="€", period="deadline"),
            source=EventSource(
                system="RegOps",
                last_updated_at=datetime.now(timezone.utc),
                confidence="high",
            ),
            action=EventAction(label="Voir", route="/test"),
            linked_assets=EventLinkedAssets(org_id=1, site_ids=[1]),
        )
        result = compose_audit_deadline_sentence(event, OrganizationTypology.ERP)
        assert "avant échéance" in result


# ─── Phase 12.C — Sourçage scope 3 INDUSTRIE ───────────────────────────────


class TestPhase12cIndustrieScopeSource:
    """P2 friction 3 : focus_text CSR_MANAGER cite désormais ADEME V23.6."""

    def test_csr_manager_focus_text_cites_ademe_v236(self):
        """CSR_MANAGER mention contient 'facteurs ADEME V23.6' pour sourcer scope 3."""
        mention = compose_persona_mention(
            "Inès",
            PersonaRole.CSR_MANAGER,
            {"emissions_tco2e": 1245},
            OrganizationTypology.INDUSTRIE,
        )
        assert "ADEME V23.6" in mention
        assert "1245 tCO₂e" in mention
        assert "scope 1-2-3" in mention

    def test_csr_manager_no_emissions_fallback(self):
        """Sans facts['emissions_tco2e'] → fallback générique sans citation ADEME."""
        mention = compose_persona_mention(
            "Inès",
            PersonaRole.CSR_MANAGER,
            {},
            OrganizationTypology.INDUSTRIE,
        )
        # Pas de citation forcée si pas de chiffre à sourcer
        assert "ADEME V23.6" not in mention


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
