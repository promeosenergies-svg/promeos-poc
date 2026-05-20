"""
PROMEOS V4 · ActionEventLog writer (ADR-029).

Scaffold Sprint M2-1. Implémentation Sprint M2-6.

Invariants applicables (cf. ADR-029 §3) :
- IE7 : tous payload events validés par schema Pydantic typé avec `schema_version`
- IE8 : `security_audit_log` (90j) séparé strict de `action_event_log` (1-5 ans)

Modules planifiés Sprint M2-6 :
- writer.py : `write_event(event_type, payload_dict, ...)` avec validation Pydantic
              + lookup `EVENT_PAYLOAD_SCHEMAS` registry
- security_writer.py : `log_security_event()` séparé (90j rétention)

Mapping 16 event_types → catégorie rétention RGPD : cf. backend/schemas/event_payloads/.
Détails : docs/dev/L6_ADR-029_evidence_audit_trail.md §6 + §10 + §11 (16 schemas).

Source : commit 15711df4.
"""
