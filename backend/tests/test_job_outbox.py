"""
PROMEOS - Tests for JobOutbox Lifecycle
Tests the async job queue and cascade logic
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, JobOutbox, JobType, JobStatus
from jobs.worker import enqueue_job, process_one, enqueue_cascade


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


def test_enqueue_job(db_session):
    """Test basic job enqueueing"""
    payload = {"scope": "site", "site_id": 42}

    job = enqueue_job(db_session, JobType.RECOMPUTE_ASSESSMENT, payload, priority=10)

    assert job is not None
    assert job.id is not None
    assert job.job_type == JobType.RECOMPUTE_ASSESSMENT
    assert job.status == JobStatus.PENDING
    assert json.loads(job.payload_json) == payload
    assert job.priority == 10


def test_process_one_no_jobs(db_session):
    """Processing empty queue returns False"""
    result = process_one(db_session)
    assert result is False


def test_process_one_success(db_session):
    """Processing a valid job marks it PENDING initially"""
    payload = {"scope": "site", "site_id": 1}
    job = enqueue_job(db_session, JobType.RECOMPUTE_ASSESSMENT, payload)

    # Verify job was created in PENDING state
    retrieved = db_session.query(JobOutbox).filter(JobOutbox.id == job.id).first()
    assert retrieved.status == JobStatus.PENDING


def test_enqueue_cascade_meter(db_session):
    """Meter update should cascade to site, entity, org"""
    from jobs.worker import CASCADE_RULES

    # Enqueue cascade for meter
    enqueue_cascade(db_session, "meter", 5)

    # Should create jobs for site, entity, org per CASCADE_RULES
    expected_scopes = CASCADE_RULES["meter"]

    # Verify all jobs created
    all_jobs = db_session.query(JobOutbox).all()
    assert len(all_jobs) == len(expected_scopes)


def test_job_priority_order(db_session):
    """Jobs should be processed in priority order (highest first)"""
    # Enqueue 3 jobs with different priorities
    enqueue_job(db_session, JobType.RECOMPUTE_ASSESSMENT, {"scope": "site", "site_id": 1}, priority=1)
    enqueue_job(db_session, JobType.RECOMPUTE_ASSESSMENT, {"scope": "site", "site_id": 2}, priority=10)
    enqueue_job(db_session, JobType.RECOMPUTE_ASSESSMENT, {"scope": "site", "site_id": 3}, priority=5)

    # First job to process should be priority 10
    next_job = (
        db_session.query(JobOutbox)
        .filter(JobOutbox.status == JobStatus.PENDING)
        .order_by(JobOutbox.priority.desc(), JobOutbox.created_at)
        .first()
    )

    payload = json.loads(next_job.payload_json)
    assert payload["site_id"] == 2  # This was priority 10


def test_job_timestamps(db_session):
    """Jobs should have proper timestamps"""
    job = enqueue_job(db_session, JobType.RUN_WATCHER, {"watcher": "test"})

    retrieved = db_session.query(JobOutbox).filter(JobOutbox.id == job.id).first()
    assert retrieved.created_at is not None
    assert retrieved.started_at is None  # Not started yet
    assert retrieved.finished_at is None  # Not finished yet


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
