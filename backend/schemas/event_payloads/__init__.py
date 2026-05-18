"""
PROMEOS V4 · 16 schemas Pydantic v1 event_payload (ADR-029).

Scaffold Sprint M2-1. Implémentation Sprint M2-6.

Invariant cardinal :
- IE7 : `class EventPayloadBase(BaseModel): schema_version: Literal["v1"] = "v1"`

16 schemas v1 planifiés Sprint M2-6 (cf. ADR-029 §11.2 + L7 §4) :

Business 3 ans (7 events) :
  CreatedPayloadV1 · StateChangedPayloadV1 · OwnerChangedPayloadV1 ·
  PriorityChangedPayloadV1 · BlockerAddedPayloadV1 · BlockerRemovedPayloadV1 ·
  ClosedViaMergedDuplicatePayloadV1

Compliance 5 ans (6 events) :
  EvidenceAddedPayloadV1 · EvidenceVerifiedPayloadV1 · ClosedWithEvidencePayloadV1 ·
  ClosedViaResolvedViaRecurrencePayloadV1 · ReopenedPayloadV1 · KindCorrectedPayloadV1

System 1 an (3 events) :
  BulkUpdatedPayloadV1 · ExportedPayloadV1 · PriorityRecalculatedPayloadV1

Registry final :
  EVENT_PAYLOAD_SCHEMAS: dict[(event_type, schema_version), type[BaseModel]]

Pattern d'évolution v1 → v2 : cf. ADR-029 §11.5 (co-existence garantie via schema_version).

Source : docs/dev/L6_ADR-029_evidence_audit_trail.md (commit 15711df4 · 48/48 ✓).
"""
