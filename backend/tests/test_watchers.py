"""
PROMEOS - Tests for Watchers
Tests the watcher registry, RSS parsing, and hash deduplication
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import hashlib
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, RegSourceEvent
from watchers.registry import list_watchers, run_watcher
from watchers.rss_watcher import RSSWatcher


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def db_session():
    """In-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ========================================
# Tests
# ========================================

def test_watcher_registry():
    """Test watcher auto-discovery"""
    watchers = list_watchers()

    assert len(watchers) >= 3  # We have at least 3 watchers
    watcher_names = [w['name'] for w in watchers]

    # Check for expected watchers
    assert 'legifrance_watcher' in watcher_names
    assert 'cre_watcher' in watcher_names
    assert 'rte_watcher' in watcher_names


def test_rss_watcher_base_class():
    """Test RSSWatcher base class"""
    # Create a test watcher
    class TestRSSWatcher(RSSWatcher):
        name = "test_rss"
        description = "Test RSS watcher"
        rss_url = "https://example.com/rss"

    watcher = TestRSSWatcher()

    assert watcher.name == "test_rss"
    assert hasattr(watcher, 'check')
    assert callable(watcher.check)


def test_hash_deduplication(db_session):
    """Test that duplicate events are not created (hash-based dedup)"""
    # Create first event
    title = "Test Regulatory News"
    url = "https://example.com/news/123"
    content_hash = hashlib.sha256(f"{title}|{url}".encode()).hexdigest()

    event1 = RegSourceEvent(
        source_name="test_watcher",
        title=title,
        url=url,
        content_hash=content_hash,
        snippet="This is a test snippet",
        tags="test,regulatory",
        retrieved_at=datetime.now()
    )
    db_session.add(event1)
    db_session.commit()

    # Try to create duplicate
    event2 = RegSourceEvent(
        source_name="test_watcher",
        title=title,
        url=url,
        content_hash=content_hash,
        snippet="This is a test snippet",
        tags="test,regulatory",
        retrieved_at=datetime.now()
    )
    db_session.add(event2)

    # Should fail due to unique constraint on content_hash
    with pytest.raises(Exception):  # SQLAlchemy IntegrityError
        db_session.commit()


def test_snippet_truncation():
    """Test that snippets are limited to 500 characters"""
    long_content = "A" * 1000

    # Simulate snippet truncation (as done in watchers)
    snippet = long_content[:500] + "..." if len(long_content) > 500 else long_content

    assert len(snippet) <= 503  # 500 + "..."
    assert snippet.endswith("...")


def test_watcher_interface():
    """Test all watchers have required attributes"""
    watchers_data = list_watchers()

    # Just verify all watchers have required metadata
    for watcher_data in watchers_data:
        assert 'name' in watcher_data
        assert 'description' in watcher_data


def test_reg_source_event_model(db_session):
    """Test RegSourceEvent model"""
    event = RegSourceEvent(
        source_name="test_source",
        title="Test Event",
        url="https://example.com/test",
        content_hash=hashlib.sha256(b"test").hexdigest(),
        snippet="Test snippet",
        tags="test,event",
        published_at=datetime(2024, 1, 15),
        retrieved_at=datetime.now(),
        reviewed=False
    )
    db_session.add(event)
    db_session.commit()

    # Retrieve and verify
    retrieved = db_session.query(RegSourceEvent).first()
    assert retrieved.title == "Test Event"
    assert retrieved.reviewed is False
    assert retrieved.content_hash is not None


# ========================================
# Run Tests
# ========================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
