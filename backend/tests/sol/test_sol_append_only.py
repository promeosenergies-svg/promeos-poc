"""
Tests append-only event listener pour SolActionLog.

Vérifie que :
- UPDATE sur fields métier (outcome_code, plan_json, confidence) → AppendOnlyViolation
- UPDATE anonymized=True + anonymized_at → autorisé (RGPD rétention 3 ans)
- INSERT puis DELETE possibles (event listener cible uniquement UPDATE)

Voir models/sol.py → _block_sol_action_log_update + models/sol.py AppendOnlyViolation.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from models.sol import AppendOnlyViolation, SolActionLog


def _make_log(sol_db, sol_org, sol_user, correlation_id: str, outcome_code: str | None = None) -> SolActionLog:
    log = SolActionLog(
        org_id=sol_org.id,
        user_id=sol_user.id,
        correlation_id=correlation_id,
        intent_kind="invoice_dispute",
        action_phase="executed",
        inputs_hash="e" * 64,
        plan_json={"total_eur": 1847.20},
        outcome_code=outcome_code,
    )
    sol_db.add(log)
    sol_db.commit()
    sol_db.refresh(log)
    return log


def test_update_outcome_code_raises_append_only_violation(sol_db, sol_org, sol_user, sol_correlation_id):
    """Modifier outcome_code d'une entrée existante lève AppendOnlyViolation."""
    log = _make_log(sol_db, sol_org, sol_user, sol_correlation_id, outcome_code="success")

    log.outcome_code = "modified_after_fact"
    with pytest.raises(AppendOnlyViolation) as exc:
        sol_db.commit()
    assert "outcome_code" in str(exc.value)
    sol_db.rollback()


def test_update_plan_json_raises_append_only_violation(sol_db, sol_org, sol_user, sol_correlation_id):
    """Modifier plan_json lève AppendOnlyViolation (détection altération audit)."""
    log = _make_log(sol_db, sol_org, sol_user, sol_correlation_id)

    log.plan_json = {"total_eur": 9999.99}  # tentative altération
    with pytest.raises(AppendOnlyViolation) as exc:
        sol_db.commit()
    assert "plan_json" in str(exc.value)
    sol_db.rollback()


def test_update_confidence_raises_append_only_violation(sol_db, sol_org, sol_user, sol_correlation_id):
    """Modifier confidence lève AppendOnlyViolation."""
    log = _make_log(sol_db, sol_org, sol_user, sol_correlation_id)

    log.confidence = 0.50
    with pytest.raises(AppendOnlyViolation):
        sol_db.commit()
    sol_db.rollback()


def test_anonymization_allowed(sol_db, sol_org, sol_user, sol_correlation_id):
    """Seul cas autorisé : anonymized=True + anonymized_at (RGPD rétention 3 ans)."""
    log = _make_log(sol_db, sol_org, sol_user, sol_correlation_id, outcome_code="success")

    log.anonymized = True
    log.anonymized_at = datetime.now(timezone.utc)
    sol_db.commit()  # ne doit pas lever

    sol_db.refresh(log)
    assert log.anonymized is True
    assert log.anonymized_at is not None
    # Les autres fields sont inchangés
    assert log.outcome_code == "success"
    assert log.plan_json == {"total_eur": 1847.20}


def test_anonymization_alongside_metier_field_rejected(sol_db, sol_org, sol_user, sol_correlation_id):
    """Même si on anonymise, modifier un autre field dans la même transaction lève."""
    log = _make_log(sol_db, sol_org, sol_user, sol_correlation_id, outcome_code="success")

    # Tente anonymisation + altération d'un autre champ
    log.anonymized = True
    log.anonymized_at = datetime.now(timezone.utc)
    log.outcome_code = "tampered"

    with pytest.raises(AppendOnlyViolation) as exc:
        sol_db.commit()
    assert "outcome_code" in str(exc.value)
    sol_db.rollback()


def test_delete_allowed_event_listener_covers_update_only(sol_db, sol_org, sol_user, sol_correlation_id):
    """DELETE physique autorisé (event listener = before_update uniquement).

    L'append-only au niveau applicatif ≠ interdiction totale de DELETE SQL.
    La politique métier empêche les DELETE via code (audit RGPD attend
    anonymisation, pas suppression). Test documente le comportement actuel.
    """
    log = _make_log(sol_db, sol_org, sol_user, sol_correlation_id)

    sol_db.delete(log)
    sol_db.commit()

    count = sol_db.query(SolActionLog).filter_by(correlation_id=sol_correlation_id).count()
    assert count == 0


def test_insert_after_insert_allowed(sol_db, sol_org, sol_user):
    """Plusieurs INSERT successifs sur la même table autorisés (chaîne d'événements)."""
    for i, phase in enumerate(("proposed", "previewed", "confirmed")):
        log = SolActionLog(
            org_id=sol_org.id,
            user_id=sol_user.id,
            correlation_id=f"corr-insert-{i}",
            intent_kind="invoice_dispute",
            action_phase=phase,
            inputs_hash="f" * 64,
            plan_json={"phase": phase},
        )
        sol_db.add(log)
    sol_db.commit()

    total = sol_db.query(SolActionLog).count()
    assert total == 3
