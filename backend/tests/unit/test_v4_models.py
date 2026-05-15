"""10 unit tests V4 models (Sprint M2-2 commit 5/5).

Couvre CHECK constraints + 7 kinds (D1) + 16 event_types (renommages ADR-029)
+ D2 evidences + D3 scenarios + D4 duplicate_groups vocabulary.

Critère d'attention M2-2 #8 : tests utilisent :memory: SQLite (cf. conftest.py voisin).
Critère d'attention M2-2 #9 : SG-6 chk_event_type 16 valeurs validées en DB.
Critère d'attention M2-2 #10 : organisation_id présent et NOT NULL sur 8 tables V4.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from models.v4.action_center_items import ActionCenterItem
from models.v4.action_event_log import ActionEventLog
from models.v4.action_scenarios import ActionScenario
from models.v4.duplicate_groups import DuplicateGroup
from models.v4.enums import EventType, Kind
from models.v4.evidences import Evidence


def _minimal_item(**overrides) -> ActionCenterItem:
    """Helper : ActionCenterItem minimal valid pour tests."""
    defaults = {
        "id": uuid4(),
        "organisation_id": uuid4(),
        "kind": "anomaly",
        "title": "Test item",
        "lifecycle_state": "new",
        "priority_bracket": "P1",
        "priority_score": 50.0,
    }
    defaults.update(overrides)
    return ActionCenterItem(**defaults)


# ─────────────────────────────────────────────────────────────────────
# Test 1 : Création minimale + IS1 (organisation_id) + score_stale default
# ─────────────────────────────────────────────────────────────────────
def test_action_center_item_minimal_create_ok(v4_session):
    """Création minimale ActionCenterItem (defaults score_stale=False, lifecycle=new)."""
    item = _minimal_item()
    v4_session.add(item)
    v4_session.commit()

    assert item.id is not None
    assert item.organisation_id is not None  # IS1
    assert item.score_stale is False  # default IL9
    assert item.lifecycle_state == "new"
    assert item.priority_bracket == "P1"


# ─────────────────────────────────────────────────────────────────────
# Test 2 : 🛡️ D1 cardinal — chk_kind accepte les 7 valeurs
# ─────────────────────────────────────────────────────────────────────
def test_chk_kind_accepts_all_7_values_d1_cardinal(v4_session):
    """🛡️ D1 : les 7 kinds doctrine v0.3 sont tous acceptés."""
    expected_7 = ["anomaly", "action", "decision", "signal", "evidence_request", "deadline", "recommendation"]
    assert Kind.values() == expected_7  # Sanity : enum aligné

    for kind_value in expected_7:
        item = _minimal_item(kind=kind_value)
        v4_session.add(item)
    v4_session.commit()  # No error → 7 kinds tous acceptés

    # Vérifier qu'on a bien 7 items insérés
    count = v4_session.query(ActionCenterItem).count()
    assert count == 7, f"Expected 7 items (7 kinds D1), got {count}"


# ─────────────────────────────────────────────────────────────────────
# Test 3 : 🛡️ D1 cardinal — chk_kind rejette une 8e valeur invalide
# ─────────────────────────────────────────────────────────────────────
def test_chk_kind_rejects_invalid_value_d1_cardinal(v4_session):
    """🛡️ D1 : kind invalide → IntegrityError (CHECK constraint enforcing 7 valeurs)."""
    item = _minimal_item(kind="invalid_kind_8")
    v4_session.add(item)
    with pytest.raises(IntegrityError):
        v4_session.commit()


# ─────────────────────────────────────────────────────────────────────
# Test 4 : chk_lifecycle_state rejette une valeur hors enum
# ─────────────────────────────────────────────────────────────────────
def test_chk_lifecycle_state_rejects_invalid(v4_session):
    """5 lifecycle_state strict (ADR-028 §6.1) — valeur hors enum rejetée."""
    item = _minimal_item(lifecycle_state="archived")  # Pas dans (new/triaged/planned/in_progress/closed)
    v4_session.add(item)
    with pytest.raises(IntegrityError):
        v4_session.commit()


# ─────────────────────────────────────────────────────────────────────
# Test 5 : 🛡️ IL10 cardinal — chk_closure_consistency enforcement
# ─────────────────────────────────────────────────────────────────────
def test_chk_closure_consistency_il10_cardinal(v4_session):
    """🛡️ IL10 : lifecycle_state=closed exige closed_at + closure_reason NOT NULL."""
    # Cas invalide : closed sans closed_at
    item_invalid = _minimal_item(
        lifecycle_state="closed",
        closed_at=None,
        closure_reason=None,
    )
    v4_session.add(item_invalid)
    with pytest.raises(IntegrityError):
        v4_session.commit()
    v4_session.rollback()

    # Cas valide : closed + closed_at + closure_reason
    item_valid = _minimal_item(
        lifecycle_state="closed",
        closed_at=datetime.now(UTC),
        closure_reason="resolved",
    )
    v4_session.add(item_valid)
    v4_session.commit()  # No error
    assert item_valid.closed_at is not None


# ─────────────────────────────────────────────────────────────────────
# Test 6 : closure_reason valid rejette ancien vocabulaire v0.2 ('merged')
# ─────────────────────────────────────────────────────────────────────
def test_chk_closure_reason_rejects_old_v0_2_vocabulary(v4_session):
    """Ancien vocabulaire v0.2 ('merged' avant Q37-A+ unification) rejeté.

    Doctrine v0.3 §7.1 : 'merged' a été unifié à 'merged_duplicate'.
    Le CHECK chk_closure_reason_valid n'accepte plus 'merged' seul.
    """
    item = _minimal_item(
        lifecycle_state="closed",
        closed_at=datetime.now(UTC),
        closure_reason="merged",  # OLD v0.2 — should be 'merged_duplicate' v0.3
    )
    v4_session.add(item)
    with pytest.raises(IntegrityError):
        v4_session.commit()


# ─────────────────────────────────────────────────────────────────────
# Test 7 : SG-6 cohérent — 16 event_types tous acceptés (renommages ADR-029)
# ─────────────────────────────────────────────────────────────────────
def test_action_event_log_16_event_types_accepted(v4_session):
    """SG-6 cohérent : 16 event_types ADR-029 tous insérables (renommages OK)."""
    item = _minimal_item()
    v4_session.add(item)
    v4_session.commit()

    correlation_id = uuid4()
    for event_value in EventType.values():
        actor_type = "system"  # Permet actor_id NULL (chk_actor_consistency)
        event = ActionEventLog(
            id=uuid4(),
            organisation_id=item.organisation_id,
            action_item_id=item.id,
            event_type=event_value,
            actor_type=actor_type,
            actor_id=None,
            event_payload={"schema_version": "v1"},
            correlation_id=correlation_id,
        )
        v4_session.add(event)
    v4_session.commit()  # No error → 16 events tous valides

    count = v4_session.query(ActionEventLog).count()
    assert count == 16, f"Expected 16 events (one per EventType), got {count}"


# ─────────────────────────────────────────────────────────────────────
# Test 8 : action_event_log rejette ancien vocabulaire 'assigned' (v0.2)
# ─────────────────────────────────────────────────────────────────────
def test_action_event_log_rejects_old_assigned_v0_2(v4_session):
    """Ancien event_type 'assigned' (ADR-025 §4.3 squelette préliminaire) rejeté.

    ADR-029 §6.1 a renommé 'assigned' → 'owner_changed' (cohérent avec
    sémantique "changement propriétaire" vs "assignation initiale").
    Le CHECK chk_event_type n'accepte plus 'assigned' seul.
    """
    item = _minimal_item()
    v4_session.add(item)
    v4_session.commit()

    event = ActionEventLog(
        id=uuid4(),
        organisation_id=item.organisation_id,
        action_item_id=item.id,
        event_type="assigned",  # OLD v0.2 / ADR-025 — should be 'owner_changed' v0.3
        actor_type="user",
        actor_id=uuid4(),
        event_payload={},
        correlation_id=uuid4(),
    )
    v4_session.add(event)
    with pytest.raises(IntegrityError):
        v4_session.commit()


# ─────────────────────────────────────────────────────────────────────
# Test 9 : 🛡️ D2 — chk_evidence_mime_whitelist rejette MIME hors whitelist
# ─────────────────────────────────────────────────────────────────────
def test_chk_evidence_mime_whitelist_d2(v4_session):
    """🛡️ D2 : seuls PDF/JPG/PNG acceptés. application/exe rejeté (anti-spoofing IE9 préparé)."""
    item = _minimal_item()
    v4_session.add(item)
    v4_session.commit()

    evidence = Evidence(
        id=uuid4(),
        organisation_id=item.organisation_id,
        action_item_id=item.id,
        mime_type="application/exe",  # Hors whitelist — rejeté
        file_size_bytes=1024,
        storage_uri="fs://test/evil.exe",
        uploaded_by=uuid4(),
    )
    v4_session.add(evidence)
    with pytest.raises(IntegrityError):
        v4_session.commit()


# ─────────────────────────────────────────────────────────────────────
# Test 10 : 🛡️ D2 + Q45-B — chk_evidence_size_max_10mb rejette > 10485760
# ─────────────────────────────────────────────────────────────────────
def test_chk_evidence_size_max_10mb_q45b(v4_session):
    """🛡️ Q45-B : file_size_bytes > 10485760 (10 MB) rejeté."""
    item = _minimal_item()
    v4_session.add(item)
    v4_session.commit()

    # 1 byte au-dessus de 10 MB
    evidence = Evidence(
        id=uuid4(),
        organisation_id=item.organisation_id,
        action_item_id=item.id,
        mime_type="application/pdf",
        file_size_bytes=10 * 1024 * 1024 + 1,  # 10485761
        storage_uri="fs://test/oversize.pdf",
        uploaded_by=uuid4(),
    )
    v4_session.add(evidence)
    with pytest.raises(IntegrityError):
        v4_session.commit()


# ─────────────────────────────────────────────────────────────────────
# Test 11 : IE2 — chk_evidence_verified_consistency partial NULL fails
# ─────────────────────────────────────────────────────────────────────
def test_chk_evidence_verified_consistency_ie2(v4_session):
    """IE2 : verified_at sans verified_by (partial NULL) → IntegrityError."""
    item = _minimal_item()
    v4_session.add(item)
    v4_session.commit()

    now = datetime.now(UTC)
    evidence = Evidence(
        id=uuid4(),
        organisation_id=item.organisation_id,
        action_item_id=item.id,
        mime_type="application/pdf",
        file_size_bytes=1024,
        storage_uri="fs://test/partial.pdf",
        uploaded_by=uuid4(),
        verified_at=now,
        verified_by=None,  # ← partial NULL inconsistency
        expires_at=now + timedelta(days=90),
    )
    v4_session.add(evidence)
    with pytest.raises(IntegrityError):
        v4_session.commit()


# ─────────────────────────────────────────────────────────────────────
# Test 12 : 🛡️ D4 — duplicate_groups status vocabulaire UX 'merged' OK
# ─────────────────────────────────────────────────────────────────────
def test_duplicate_groups_d4_vocabulary(v4_session):
    """🛡️ D4 : status 'merged' OK (cohérent UX), 'confirmed' rejeté (vs L7 §2.5 erroné)."""
    org_id = uuid4()
    item_id = uuid4()

    # Cas valide : status 'merged' (D4 vocabulaire)
    dup_valid = DuplicateGroup(
        id=uuid4(),
        organisation_id=org_id,
        detection_method="signature_hash",
        detection_signature="hash_abc123",
        representative_item_id=item_id,
        status="merged",  # D4 — cohérent UX "Fusionner"
    )
    v4_session.add(dup_valid)
    v4_session.commit()  # No error
    assert dup_valid.status == "merged"

    # Cas invalide : status 'confirmed' (vocabulaire L7 §2.5 erroné, corrigé D4)
    dup_invalid = DuplicateGroup(
        id=uuid4(),
        organisation_id=org_id,
        detection_method="signature_hash",
        detection_signature="hash_xyz789",
        representative_item_id=item_id,
        status="confirmed",  # PAS dans whitelist D4 ('suggested', 'merged', 'dismissed')
    )
    v4_session.add(dup_invalid)
    with pytest.raises(IntegrityError):
        v4_session.commit()


# ─────────────────────────────────────────────────────────────────────
# Test 13 : 🛡️ D3 — action_scenarios chk_scenario_selection_consistency
# ─────────────────────────────────────────────────────────────────────
def test_action_scenarios_d3_selection_consistency(v4_session):
    """🛡️ D3 : selected_at sans selected_by (partial NULL) → IntegrityError."""
    item = _minimal_item(kind="decision")
    v4_session.add(item)
    v4_session.commit()

    # Cas invalide : selected_at sans selected_by
    scenario = ActionScenario(
        id=uuid4(),
        organisation_id=item.organisation_id,
        item_id=item.id,
        scenario_tag="option_a",
        label="Option A : low cost",
        capex_eur=10000.00,
        gain_eur_per_year=2500.00,
        is_recommended=True,
        display_order=1,
        selected_at=datetime.now(UTC),
        selected_by=None,  # ← partial NULL
    )
    v4_session.add(scenario)
    with pytest.raises(IntegrityError):
        v4_session.commit()
