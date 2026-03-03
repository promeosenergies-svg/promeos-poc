"""
PROMEOS Jobs - Worker pour traiter les jobs de l'outbox
"""
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import JobOutbox, JobType, JobStatus
from database import SessionLocal


# Cascade rules: meter -> site -> entity -> org
CASCADE_RULES = {
    "meter": ["site", "entity", "org"],
    "site": ["site", "entity", "org"],
    "entity": ["entity", "org"],
    "org": ["org"],
}


def enqueue_job(db: Session, job_type: JobType, payload: dict, priority: int = 0):
    """Enqueue un job dans l'outbox."""
    job = JobOutbox(
        job_type=job_type,
        payload_json=json.dumps(payload),
        priority=priority,
        status=JobStatus.PENDING,
        created_at=datetime.now(timezone.utc)
    )
    db.add(job)
    db.commit()
    return job


def enqueue_cascade(db: Session, object_type: str, object_id: int):
    """Enqueue recompute jobs suivant les regles de cascade."""
    cascade_types = CASCADE_RULES.get(object_type, [])
    for target_type in cascade_types:
        payload = {
            "object_type": target_type,
            "object_id": object_id
        }
        enqueue_job(db, JobType.RECOMPUTE_ASSESSMENT, payload, priority=5)


def process_one(db: Session) -> bool:
    """
    Traite le job PENDING le plus ancien.
    Retourne True si un job a ete traite, False sinon.
    """
    # Pick oldest PENDING job
    job = db.query(JobOutbox).filter(
        JobOutbox.status == JobStatus.PENDING
    ).order_by(
        JobOutbox.priority.desc(),
        JobOutbox.created_at.asc()
    ).first()

    if not job:
        return False

    # Mark RUNNING
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    try:
        payload = json.loads(job.payload_json)

        # Execute based on job_type
        if job.job_type == JobType.RECOMPUTE_ASSESSMENT:
            _handle_recompute_assessment(db, payload)
        elif job.job_type == JobType.SYNC_CONNECTOR:
            _handle_sync_connector(db, payload)
        elif job.job_type == JobType.RUN_WATCHER:
            _handle_run_watcher(db, payload)
        elif job.job_type == JobType.RUN_AI_AGENT:
            _handle_run_ai_agent(db, payload)

        # Mark DONE
        job.status = JobStatus.DONE
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        return True

    except Exception as e:
        # Mark FAILED
        job.status = JobStatus.FAILED
        job.finished_at = datetime.now(timezone.utc)
        job.error = str(e)
        db.commit()
        print(f"Job {job.id} failed: {e}")
        return True


def _handle_recompute_assessment(db: Session, payload: dict):
    """Handler pour RECOMPUTE_ASSESSMENT."""
    from regops.engine import evaluate_site, persist_assessment

    object_type = payload.get("object_type")
    object_id = payload.get("object_id")

    if object_type == "site":
        summary = evaluate_site(db, object_id)
        persist_assessment(db, summary)
    elif object_type in ["entity", "org"]:
        # TODO: implement entity/org level recompute
        pass


def _handle_sync_connector(db: Session, payload: dict):
    """Handler pour SYNC_CONNECTOR."""
    from connectors.registry import get_connector

    connector_name = payload.get("connector_name")
    connector = get_connector(connector_name)
    if connector:
        connector.sync(db, **payload)


def _handle_run_watcher(db: Session, payload: dict):
    """Handler pour RUN_WATCHER."""
    from watchers.registry import run_watcher

    watcher_name = payload.get("watcher_name")
    run_watcher(watcher_name, db)


def _handle_run_ai_agent(db: Session, payload: dict):
    """Handler pour RUN_AI_AGENT."""
    from ai_layer.registry import run_agent

    agent_name = payload.get("agent_name")
    run_agent(agent_name, db, **payload)
