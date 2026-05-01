"""Phase 4.0.B — Source-guards wiring builder + contrat Narrative étendu.

Vérifie que les structures Phase 1-3 sont correctement exposées au FE :

1. `Narrative.typology` exposé après wiring _build_cockpit_comex
2. `Narrative.primary_trigger` payload {type, event_id, linked_site_ids}
3. `Narrative.weekly_deltas` payload structuré (4 métriques canoniques)
4. `Narrative.primary_push` payload (None si silence, dict si push actif)
5. `narrative` text contient phrase 1 événementielle si trigger primary actif
6. `narrative` text contient phrase stable si pas de trigger
7. `to_dict()` sérialise tous les nouveaux champs

Audit triple Phase 3 P0-3 : « contrat Narrative ne expose ni primary_trigger
ni weekly_deltas ni typology → tout l'investissement Phase 1-3 invisible FE ».

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
+ audit Phase 4.0 (Marie + Ergonomie + CX) 2026-05-01.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from doctrine.naf_to_typology import OrganizationTypology
from doctrine.triggers import TriggerType
from models import (
    Base,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)
from services.event_bus.types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventSource,
    SolEventCard,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def helios_org(db_session):
    """Org HELIOS-like avec 1 site GRAND_GROUPE (NAF 6820B)."""
    org = Organisation(nom="HELIOS Test", type_client="bureau", actif=True)
    db_session.add(org)
    db_session.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="HELIOS EJ", siren="111111111")
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="HELIOS PF")
    db_session.add(pf)
    db_session.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Siège Paris",
        type=TypeSite.BUREAU,
        naf_code="6820B",
        surface_m2=3500,
        actif=True,
    )
    db_session.add(site)
    db_session.commit()
    return org, site


def _make_event(event_type: str, title: str, site_ids: list[int]) -> SolEventCard:
    return SolEventCard(
        id=f"{event_type}:test",
        event_type=event_type,
        severity="warning",
        title=title,
        narrative=f"Test {event_type}",
        impact=EventImpact(value=1000.0, unit="€", period="week"),
        source=EventSource(
            system="RegOps",
            last_updated_at=datetime.now(timezone.utc),
            confidence="high",
        ),
        action=EventAction(label="Voir", route="/test"),
        linked_assets=EventLinkedAssets(org_id=1, site_ids=site_ids),
    )


# ─── Tests contrat Narrative étendu ─────────────────────────────────────────


class TestNarrativeContractExtension:
    """Source-guards : Phase 1-3 exposées au FE via Narrative dataclass."""

    def test_narrative_dataclass_has_typology_field(self):
        """Narrative dataclass expose le champ `typology`."""
        from services.narrative.narrative_generator import Narrative

        # Vérifier que le champ est défini (avec default None)
        annotations = Narrative.__dataclass_fields__
        assert "typology" in annotations, "Champ `typology` manquant dans Narrative"

    def test_narrative_dataclass_has_primary_trigger_field(self):
        from services.narrative.narrative_generator import Narrative

        assert "primary_trigger" in Narrative.__dataclass_fields__
        assert "secondary_trigger" in Narrative.__dataclass_fields__

    def test_narrative_dataclass_has_weekly_deltas_field(self):
        from services.narrative.narrative_generator import Narrative

        assert "weekly_deltas" in Narrative.__dataclass_fields__

    def test_narrative_dataclass_has_primary_push_field(self):
        from services.narrative.narrative_generator import Narrative

        assert "primary_push" in Narrative.__dataclass_fields__

    def test_narrative_to_dict_serializes_phase4_fields(self):
        """to_dict() sérialise tous les nouveaux champs Phase 4.0.B."""
        from services.data_provenance import Provenance, ProvenanceConfidence
        from services.narrative.narrative_generator import Narrative, NarrativeTone

        narrative = Narrative(
            page_key="cockpit_comex",
            persona="comex",
            kicker="TEST",
            title="Test",
            italic_hook=None,
            narrative="Test narrative",
            narrative_tone=NarrativeTone.NEUTRAL,
            kpis=(),
            week_cards=(),
            fallback_body="fallback",
            provenance=Provenance(
                source="test",
                confidence=ProvenanceConfidence.HIGH,
            ),
            typology="grand_groupe_tertiaire",
            primary_trigger={"type": "dt_trajectory_drift", "event_id": "t:1"},
            weekly_deltas={"exposure_eur": {"current": 1000, "previous": None}},
        )
        d = narrative.to_dict()
        assert d["typology"] == "grand_groupe_tertiaire"
        assert d["primary_trigger"]["type"] == "dt_trajectory_drift"
        assert "weekly_deltas" in d
        assert d["secondary_trigger"] is None
        assert d["primary_push"] is None


# ─── Tests wiring builder _build_cockpit_comex ──────────────────────────────


class TestBuilderWiring:
    """Source-guards : _build_cockpit_comex injecte phrase 1 + payloads structurés."""

    def test_builder_injects_typology_value(self, db_session, helios_org):
        """Builder résout la typologie et l'expose via Narrative.typology."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1)

        # NAF 6820B → préfixe 68 → GRAND_GROUPE
        assert narrative.typology == OrganizationTypology.GRAND_GROUPE.value
        assert narrative.typology == "grand_groupe_tertiaire"

    def test_builder_injects_stable_sentence_when_no_events(self, db_session, helios_org):
        """Pas d'events → narrative préfixée par phrase de stabilité positive."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1)

        # Phrase stable GG (Phase 4.0.A reformulation positive)
        assert "tient" in narrative.narrative.lower(), (
            f"Narrative doit débuter par phrase stable 'tient sa trajectoire/le cap', trouvé : {narrative.narrative!r}"
        )
        assert narrative.primary_trigger is None
        assert narrative.secondary_trigger is None

    def test_builder_injects_primary_trigger_payload_when_events(self, db_session, helios_org):
        """Events présents → primary_trigger payload exposé au FE."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org
        # Mock compute_events pour retourner un consumption_drift
        drift_event = _make_event(
            "consumption_drift",
            title="Dérive sur sites tertiaires",
            site_ids=[1, 2],
        )
        with (
            patch("services.event_bus.event_service.compute_events", return_value=[drift_event]),
            patch("services.event_bus.compute_events", return_value=[drift_event]),
        ):
            narrative = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1)

        # Primary trigger payload exposé
        assert narrative.primary_trigger is not None
        assert narrative.primary_trigger["type"] == TriggerType.DT_TRAJECTORY_DRIFT.value
        assert narrative.primary_trigger["linked_site_ids"] == [1, 2]
        assert narrative.primary_trigger["event_id"] == "consumption_drift:test"

    def test_builder_injects_phrase1_in_narrative_text_when_drift(self, db_session, helios_org):
        """Events drift → phrase 1 événementielle prepend au narrative legacy."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org
        drift_event = _make_event(
            "consumption_drift",
            title="Dérive consommation Q1",
            site_ids=[1, 2, 3],
        )
        with (
            patch("services.event_bus.event_service.compute_events", return_value=[drift_event]),
            patch("services.event_bus.compute_events", return_value=[drift_event]),
        ):
            narrative = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1)

        # Phase 1 événementielle GG injectée en préfixe
        assert "patrimoine" in narrative.narrative
        assert "Décret Tertiaire" in narrative.narrative
        # Sourçage §7 visible (Phase 4.0.A)
        assert "(source " in narrative.narrative
        assert "confiance" in narrative.narrative

    def test_builder_exposes_weekly_deltas_structure(self, db_session, helios_org):
        """weekly_deltas exposé avec 4 métriques canoniques."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1)

        assert narrative.weekly_deltas is not None
        canonical = {"exposure_eur", "potential_mwh_year", "sites_in_drift", "compliance_score"}
        assert canonical.issubset(set(narrative.weekly_deltas.keys()))

    def test_builder_primary_push_silence_when_previous_none(self, db_session, helios_org):
        """MVP état actuel : previous=None partout → primary_push None (silence)."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1)

        # Silence garanti tant que previous_value pas seedé (MVP Phase 2.2)
        assert narrative.primary_push is None


# ─── Tests sérialisation FE-ready (to_dict) ─────────────────────────────────


class TestToDictFEContract:
    """Source-guards : to_dict() expose un payload consommable FE complet."""

    def test_to_dict_contains_all_phase4_keys(self, db_session, helios_org):
        """to_dict() expose typology + primary_trigger + weekly_deltas + primary_push."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1)

        d = narrative.to_dict()
        for key in ["typology", "primary_trigger", "secondary_trigger", "weekly_deltas", "primary_push"]:
            assert key in d, f"Clé Phase 4.0.B manquante dans to_dict() : {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
