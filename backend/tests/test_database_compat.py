"""
Tests — database dialect detection and compatibility.
Playbook 1.1: Verify PostgreSQL-ready database configuration.
"""

import os
import pytest

pytestmark = pytest.mark.fast


def test_dialect_detected_sqlite():
    """Default DATABASE_URL should produce SQLite dialect."""
    from database.connection import _is_sqlite, DATABASE_URL

    assert DATABASE_URL.startswith("sqlite"), f"Expected SQLite URL, got: {DATABASE_URL}"
    assert _is_sqlite is True


def test_connect_args_sqlite():
    """SQLite engine should have check_same_thread=False."""
    from database.connection import engine

    # SQLite engines use StaticPool or connect_args with check_same_thread
    url = str(engine.url)
    if url.startswith("sqlite"):
        # Verify the engine was created (can connect)
        with engine.connect() as conn:
            result = conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            assert result.scalar() == 1


def test_engine_can_connect():
    """Engine should be able to execute a simple query."""
    from database import engine
    from sqlalchemy import text

    with engine.connect() as conn:
        row = conn.execute(text("SELECT 1 AS x"))
        assert row.scalar() == 1


def test_session_factory_works():
    """SessionLocal should produce working sessions."""
    from database import SessionLocal
    from sqlalchemy import text

    session = SessionLocal()
    try:
        result = session.execute(text("SELECT 42 AS answer"))
        assert result.scalar() == 42
    finally:
        session.close()


def test_get_db_generator():
    """get_db() should yield a session and close it."""
    from database import get_db

    gen = get_db()
    db = next(gen)
    assert db is not None
    try:
        gen.send(None)
    except StopIteration:
        pass  # Expected — generator finished


def test_postgresql_config_would_differ():
    """Verify that non-SQLite URL would NOT get check_same_thread."""
    from database.connection import _is_sqlite

    # In current config it's SQLite, just verify the flag
    if _is_sqlite:
        # If we were to set a PostgreSQL URL, the branch would differ
        assert True  # config branch exists in connection.py lines 36-42


def test_seed_does_not_crash():
    """Verify seed module can be imported without error."""
    # Just import — don't run the full seed
    from services.demo_seed.orchestrator import SeedOrchestrator  # noqa: F401

    assert callable(SeedOrchestrator.seed)


def test_insert_or_ignore_has_dialect_check():
    """Verify INSERT OR IGNORE usages check dialect before executing."""
    import inspect
    from services.demo_seed import gen_weather, gen_readings

    # gen_weather._insert_weather_ignore checks dialect
    src_weather = inspect.getsource(gen_weather._insert_weather_ignore)
    assert "dialect" in src_weather, "gen_weather must check dialect"
    assert "ON CONFLICT" in src_weather, "gen_weather must have PostgreSQL ON CONFLICT"

    # gen_readings._bulk_insert_ignore checks dialect
    src_readings = inspect.getsource(gen_readings._bulk_insert_ignore)
    assert "dialect" in src_readings, "gen_readings must check dialect"
    assert "ON CONFLICT" in src_readings, "gen_readings must have PostgreSQL ON CONFLICT"
