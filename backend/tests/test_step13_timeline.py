"""
Step 13 — Timeline reglementaire : tests unitaires + integration.
"""

import pytest
from datetime import date


# ============================================================
# Unit tests for _deadline_status and _build_timeline_events
# ============================================================


class TestDeadlineStatus:
    """Test the _deadline_status helper."""

    def test_import(self):
        from routes.compliance import _deadline_status

        assert callable(_deadline_status)

    def test_passed_for_old_deadline(self):
        from routes.compliance import _deadline_status

        today = date(2026, 3, 6)
        one_year = date(2027, 3, 6)
        assert _deadline_status(date(2025, 1, 1), today, one_year) == "passed"

    def test_upcoming_for_near_deadline(self):
        from routes.compliance import _deadline_status

        today = date(2026, 3, 6)
        one_year = date(2027, 3, 6)
        assert _deadline_status(date(2026, 7, 1), today, one_year) == "upcoming"

    def test_future_for_far_deadline(self):
        from routes.compliance import _deadline_status

        today = date(2026, 3, 6)
        one_year = date(2027, 3, 6)
        assert _deadline_status(date(2030, 1, 1), today, one_year) == "future"

    def test_today_is_upcoming(self):
        from routes.compliance import _deadline_status

        today = date(2026, 3, 6)
        one_year = date(2027, 3, 6)
        # Deadline == today should not be "passed"
        assert _deadline_status(today, today, one_year) == "upcoming"

    def test_one_year_boundary_is_upcoming(self):
        from routes.compliance import _deadline_status

        today = date(2026, 3, 6)
        one_year = date(2027, 3, 6)
        assert _deadline_status(one_year, today, one_year) == "upcoming"


class TestBuildTimeline:
    """Test _build_timeline_events with real DB via fixture."""

    def test_import(self):
        from routes.compliance import _build_timeline_events

        assert callable(_build_timeline_events)


class TestTimelineEndpoint:
    """Test the /api/compliance/timeline route registration."""

    def test_route_exists(self):
        """The timeline route should be registered in the compliance router."""
        from routes.compliance import router

        paths = [getattr(r, "path", "") for r in router.routes]
        assert any("/timeline" in p for p in paths), f"No /timeline in {paths}"

    def test_route_is_get(self):
        from routes.compliance import router

        for route in router.routes:
            path = getattr(route, "path", "")
            if "/timeline" in path:
                assert "GET" in route.methods
                break


class TestTimelineEventStructure:
    """Test that _build_timeline_events returns properly structured data."""

    def _make_result(self):
        """Build timeline with a mock-free approach: use _build_timeline_events
        against the real DB (demo seeded)."""
        from database import SessionLocal
        from routes.compliance import _build_timeline_events

        db = SessionLocal()
        try:
            # Use org_id=1 (demo HELIOS)
            return _build_timeline_events(db, 1, date(2026, 3, 6))
        finally:
            db.close()

    def test_events_is_list(self):
        result = self._make_result()
        assert isinstance(result["events"], list)

    def test_events_sorted_by_date(self):
        result = self._make_result()
        deadlines = [e["deadline"] for e in result["events"]]
        assert deadlines == sorted(deadlines)

    def test_event_has_required_fields(self):
        result = self._make_result()
        required = {"id", "framework", "label", "deadline", "status", "severity", "sites_concerned"}
        for evt in result["events"]:
            missing = required - set(evt.keys())
            assert not missing, f"Event {evt.get('id')} missing fields: {missing}"

    def test_status_values_valid(self):
        result = self._make_result()
        valid = {"passed", "upcoming", "future"}
        for evt in result["events"]:
            assert evt["status"] in valid, f"Invalid status: {evt['status']}"

    def test_bacs_290_is_passed(self):
        """BACS 290kW deadline (2025-01-01) should be 'passed' on 2026-03-06."""
        result = self._make_result()
        bacs = [e for e in result["events"] if e["id"] == "bacs_290kw"]
        if bacs:
            assert bacs[0]["status"] == "passed"

    def test_tertiaire_affichage_is_upcoming(self):
        """Tertiaire affichage (2026-07-01) should be 'upcoming' on 2026-03-06."""
        result = self._make_result()
        dt = [e for e in result["events"] if e["id"] == "tertiaire_affichage"]
        if dt:
            assert dt[0]["status"] == "upcoming"

    def test_bacs_70_is_future(self):
        """BACS 70kW (2030-01-01) should be 'future' on 2026-03-06."""
        result = self._make_result()
        bacs = [e for e in result["events"] if e["id"] == "bacs_70kw"]
        if bacs:
            assert bacs[0]["status"] == "future"

    def test_next_deadline_populated(self):
        result = self._make_result()
        nd = result.get("next_deadline")
        if nd:
            assert nd["days_remaining"] > 0
            assert "label" in nd
            assert "deadline" in nd

    def test_penalty_exposure_non_negative(self):
        result = self._make_result()
        assert result["total_penalty_exposure_eur"] >= 0

    def test_today_field(self):
        result = self._make_result()
        assert result["today"] == "2026-03-06"

    def test_at_least_5_events(self):
        """With regs.yaml having DT+BACS+APER, we expect at least 5 events."""
        result = self._make_result()
        assert len(result["events"]) >= 5
