"""Tests unitaires events_query_service — Phase 1.A Sprint α-fin.

Couverture isolation (sans DB réelle) des 4 fonctions publiques + privées :
- get_upcoming_events (orchestrateur)
- _apply_persona_filter
- _apply_page_key_filter
- _apply_horizon_filter
- _paginate (cursor base64 offset MVP)

Mock de compute_events pour découpler des détecteurs réels — la couche
query est testée indépendamment du moteur event_bus.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.event_bus.types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventSource,
    SolEventCard,
)
from services.events_query_service import (
    DEFAULT_HORIZON_DAYS,
    DEFAULT_LIMIT,
    PAGE_KEY_TO_EVENT_TYPES,
    PERSONA_TO_OWNER_ROLES,
    _decode_cursor,
    _encode_cursor,
    get_upcoming_events,
)


# ── Fixtures ────────────────────────────────────────────────────────


def _make_event(
    event_id: str = "e1",
    event_type: str = "compliance_deadline",
    severity: str = "warning",
    owner_role: str | None = "DAF",
    impact_period: str = "deadline",
    impact_value: float | None = 10.0,
    impact_unit: str = "days",
    last_updated: datetime | None = None,
) -> SolEventCard:
    """Helper construction SolEventCard pour tests."""
    if last_updated is None:
        last_updated = datetime.now(timezone.utc)
    return SolEventCard(
        id=event_id,
        event_type=event_type,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        title=f"title-{event_id}",
        narrative="narrative",
        impact=EventImpact(
            value=impact_value,
            unit=impact_unit,  # type: ignore[arg-type]
            period=impact_period,  # type: ignore[arg-type]
        ),
        source=EventSource(
            system="RegOps",
            last_updated_at=last_updated,
            confidence="high",
        ),
        action=EventAction(
            label="Voir",
            route="/conformite",
            owner_role=owner_role,  # type: ignore[arg-type]
        ),
        linked_assets=EventLinkedAssets(org_id=1),
    )


# ── Tests get_upcoming_events ───────────────────────────────────────


class TestGetUpcomingEvents:
    def test_returns_dict_with_expected_keys(self):
        """get_upcoming_events retourne dict avec events / next_cursor / total."""
        with patch("services.events_query_service.compute_events", return_value=[]):
            result = get_upcoming_events(db=None, org_id=1)  # type: ignore[arg-type]
        assert set(result.keys()) == {"events", "next_cursor", "total"}
        assert result["events"] == []
        assert result["next_cursor"] is None
        assert result["total"] == 0

    def test_compute_events_called_with_org_id(self):
        """Délégation pure — compute_events reçoit (db, org_id) inchangé."""
        with patch("services.events_query_service.compute_events", return_value=[]) as mock:
            get_upcoming_events(db="DB_SENTINEL", org_id=42)  # type: ignore[arg-type]
            mock.assert_called_once_with("DB_SENTINEL", 42)


# ── Tests filtre persona ────────────────────────────────────────────


class TestPersonaFilter:
    def test_persona_energy_manager_excludes_daf_events(self):
        """persona='energy_manager' garde EM+SiteManager, exclut DAF."""
        events = [
            _make_event("daf-1", owner_role="DAF"),
            _make_event("em-1", owner_role="Energy Manager"),
            _make_event("site-1", owner_role="Site Manager"),
        ]
        with patch("services.events_query_service.compute_events", return_value=events):
            result = get_upcoming_events(db=None, org_id=1, persona="energy_manager")  # type: ignore[arg-type]
        ids = [e.id for e in result["events"]]
        assert "daf-1" not in ids
        assert "em-1" in ids
        assert "site-1" in ids

    def test_persona_daf_excludes_energy_manager_events(self):
        """persona='daf' garde uniquement DAF."""
        events = [
            _make_event("daf-1", owner_role="DAF"),
            _make_event("em-1", owner_role="Energy Manager"),
        ]
        with patch("services.events_query_service.compute_events", return_value=events):
            result = get_upcoming_events(db=None, org_id=1, persona="daf")  # type: ignore[arg-type]
        ids = [e.id for e in result["events"]]
        assert ids == ["daf-1"]

    def test_persona_unknown_returns_unfiltered(self):
        """persona inconnu → no-op (pas de 400, pas de filtre)."""
        events = [_make_event("e1"), _make_event("e2")]
        with patch("services.events_query_service.compute_events", return_value=events):
            result = get_upcoming_events(db=None, org_id=1, persona="ceo_unknown")  # type: ignore[arg-type]
        assert len(result["events"]) == 2

    def test_persona_none_returns_unfiltered(self):
        events = [_make_event("e1"), _make_event("e2")]
        with patch("services.events_query_service.compute_events", return_value=events):
            result = get_upcoming_events(db=None, org_id=1, persona=None)  # type: ignore[arg-type]
        assert len(result["events"]) == 2

    def test_persona_to_owner_roles_constant_complete(self):
        """Constante mapping doit couvrir les 4 valeurs canoniques."""
        assert set(PERSONA_TO_OWNER_ROLES.keys()) == {
            "energy_manager",
            "daf",
            "admin",
            "operator",
        }


# ── Tests filtre page_key ───────────────────────────────────────────


class TestPageKeyFilter:
    def test_page_key_cockpit_daily_includes_compliance(self):
        events = [
            _make_event("comp-1", event_type="compliance_deadline"),
            _make_event("contract-1", event_type="contract_renewal"),
        ]
        with patch("services.events_query_service.compute_events", return_value=events):
            result = get_upcoming_events(db=None, org_id=1, page_key="cockpit_daily")  # type: ignore[arg-type]
        ids = [e.id for e in result["events"]]
        assert "comp-1" in ids
        assert "contract-1" not in ids

    def test_page_key_conformite_only_compliance(self):
        events = [
            _make_event("comp-1", event_type="compliance_deadline"),
            _make_event("flex-1", event_type="flex_opportunity"),
        ]
        with patch("services.events_query_service.compute_events", return_value=events):
            result = get_upcoming_events(db=None, org_id=1, page_key="conformite")  # type: ignore[arg-type]
        ids = [e.id for e in result["events"]]
        assert ids == ["comp-1"]

    def test_page_key_unknown_returns_unfiltered(self):
        events = [_make_event("e1"), _make_event("e2")]
        with patch("services.events_query_service.compute_events", return_value=events):
            result = get_upcoming_events(db=None, org_id=1, page_key="lol_unknown")  # type: ignore[arg-type]
        assert len(result["events"]) == 2

    def test_page_key_constant_matches_canonical_pagekey_literal(self):
        """Toute clé de PAGE_KEY_TO_EVENT_TYPES doit exister dans le
        Literal `PageKey` canonique de narrative_generator."""
        from services.narrative.narrative_generator import PageKey

        canonical = set(PageKey.__args__)  # type: ignore[attr-defined]
        for key in PAGE_KEY_TO_EVENT_TYPES.keys():
            assert key in canonical, f"page_key '{key}' absent du Literal canonique PageKey"


# ── Tests filtre horizon_days ───────────────────────────────────────


class TestHorizonFilter:
    def test_excludes_far_future_deadlines(self):
        """Deadline à +60j exclu si horizon=30."""
        events = [
            _make_event("near", impact_period="deadline", impact_value=10.0),
            _make_event("far", impact_period="deadline", impact_value=60.0),
        ]
        with patch("services.events_query_service.compute_events", return_value=events):
            result = get_upcoming_events(db=None, org_id=1, horizon_days=30)  # type: ignore[arg-type]
        ids = [e.id for e in result["events"]]
        assert "near" in ids
        assert "far" not in ids

    def test_default_horizon_is_30(self):
        assert DEFAULT_HORIZON_DAYS == 30

    def test_recent_event_in_horizon(self):
        """Événement non-deadline avec last_updated récent → inclus."""
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        events = [
            _make_event(
                "fresh",
                impact_period="month",
                impact_value=None,
                impact_unit="€",
                last_updated=recent,
            ),
        ]
        with patch("services.events_query_service.compute_events", return_value=events):
            result = get_upcoming_events(db=None, org_id=1, horizon_days=30)  # type: ignore[arg-type]
        assert len(result["events"]) == 1


# ── Tests pagination cursor ─────────────────────────────────────────


class TestPagination:
    def test_pagination_cursor_advances_offset(self):
        events = [_make_event(f"e{i}") for i in range(50)]
        with patch("services.events_query_service.compute_events", return_value=events):
            page1 = get_upcoming_events(db=None, org_id=1, limit=20)  # type: ignore[arg-type]
            assert len(page1["events"]) == 20
            assert page1["events"][0].id == "e0"
            assert page1["next_cursor"] is not None
            assert page1["total"] == 50

            page2 = get_upcoming_events(  # type: ignore[arg-type]
                db=None, org_id=1, limit=20, cursor=page1["next_cursor"]
            )
            assert len(page2["events"]) == 20
            assert page2["events"][0].id == "e20"
            assert page2["next_cursor"] is not None

            page3 = get_upcoming_events(  # type: ignore[arg-type]
                db=None, org_id=1, limit=20, cursor=page2["next_cursor"]
            )
            assert len(page3["events"]) == 10
            assert page3["next_cursor"] is None  # dernière page

    def test_pagination_cursor_invalid_returns_first_page(self):
        events = [_make_event(f"e{i}") for i in range(5)]
        with patch("services.events_query_service.compute_events", return_value=events):
            result = get_upcoming_events(  # type: ignore[arg-type]
                db=None, org_id=1, cursor="not-base64-!!!"
            )
        assert len(result["events"]) == 5
        assert result["events"][0].id == "e0"

    def test_decode_cursor_negative_offset_returns_zero(self):
        """Cursor encodant un offset négatif → décodé comme 0 (sécurité)."""
        bad_cursor = _encode_cursor(-5).rstrip()
        # _encode_cursor n'accepte pas négatif normalement, mais on teste
        # un cursor manuel encodant '-5' brut.
        import base64

        manual = base64.b64encode(b"-5").decode("utf-8")
        assert _decode_cursor(manual) == 0

    def test_default_limit_is_20(self):
        assert DEFAULT_LIMIT == 20


# ── Test composition filtres ────────────────────────────────────────


class TestComposition:
    def test_persona_and_page_key_compose(self):
        """Filtres composables : persona + page_key appliqués séquentiellement."""
        events = [
            _make_event(
                "daf-comp",
                event_type="compliance_deadline",
                owner_role="DAF",
            ),
            _make_event(
                "em-comp",
                event_type="compliance_deadline",
                owner_role="Energy Manager",
            ),
            _make_event(
                "daf-flex",
                event_type="flex_opportunity",
                owner_role="DAF",
            ),
        ]
        with patch("services.events_query_service.compute_events", return_value=events):
            result = get_upcoming_events(  # type: ignore[arg-type]
                db=None, org_id=1, persona="daf", page_key="conformite"
            )
        ids = [e.id for e in result["events"]]
        assert ids == ["daf-comp"]
