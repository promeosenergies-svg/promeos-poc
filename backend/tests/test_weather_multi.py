"""
PROMEOS - Tests for multi-site weather + ensure_weather pipeline.
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, TypeSite
from models.ems_models import EmsWeatherCache
from services.ems.weather_service import get_weather, get_weather_multi, ensure_weather


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _seed_sites(db, n=3):
    sites = []
    for i in range(1, n + 1):
        s = Site(nom=f"Site {i}", type=TypeSite.BUREAU, latitude=48.86 + i * 0.1)
        db.add(s)
        db.flush()
        sites.append(s)
    return sites


class TestGetWeatherMulti:
    def test_returns_averaged_temps(self, db):
        """Multi-site weather averages temperatures across sites."""
        sites = _seed_sites(db, 2)
        result = get_weather_multi(db, [s.id for s in sites], date(2025, 7, 1), date(2025, 7, 3))
        assert len(result["days"]) == 3  # 3 days
        # Each day should have avg temp
        for day in result["days"]:
            assert "temp_avg_c" in day
            assert "date" in day

    def test_single_site_same_as_get_weather(self, db):
        """Multi-site with 1 site returns same temps as single-site."""
        sites = _seed_sites(db, 1)
        single = get_weather(db, sites[0].id, date(2025, 6, 1), date(2025, 6, 5))
        multi = get_weather_multi(db, [sites[0].id], date(2025, 6, 1), date(2025, 6, 5))
        assert len(single) == len(multi["days"])
        for s, m in zip(single, multi["days"]):
            assert s["temp_avg_c"] == m["temp_avg_c"]

    def test_empty_site_ids_returns_empty(self, db):
        result = get_weather_multi(db, [], date(2025, 1, 1), date(2025, 1, 5))
        assert result["days"] == []
        assert result["meta"]["n_sites"] == 0

    def test_multi_site_source_is_average(self, db):
        """Multi-site weather source should indicate averaging."""
        sites = _seed_sites(db, 3)
        result = get_weather_multi(db, [s.id for s in sites], date(2025, 3, 1), date(2025, 3, 2))
        assert len(result["days"]) == 2
        assert result["days"][0]["source"] == "demo_avg"


class TestEnsureWeather:
    def test_ensures_all_sites_have_data(self, db):
        """ensure_weather generates weather for all sites."""
        sites = _seed_sites(db, 3)
        result = ensure_weather(db, [s.id for s in sites], date(2025, 1, 1), date(2025, 1, 10))
        assert result["sites_ok"] == 3
        assert result["sites_total"] == 3
        assert result["days_generated"] > 0
        # Verify data exists in cache
        count = db.query(EmsWeatherCache).count()
        assert count == 30  # 3 sites x 10 days

    def test_idempotent(self, db):
        """Running ensure_weather twice doesn't create duplicates."""
        sites = _seed_sites(db, 2)
        ensure_weather(db, [s.id for s in sites], date(2025, 5, 1), date(2025, 5, 5))
        count1 = db.query(EmsWeatherCache).count()
        ensure_weather(db, [s.id for s in sites], date(2025, 5, 1), date(2025, 5, 5))
        count2 = db.query(EmsWeatherCache).count()
        assert count1 == count2
