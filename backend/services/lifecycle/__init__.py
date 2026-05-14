"""
PROMEOS V4 · LifecycleStateMachine (ADR-028).

Scaffold Sprint M2-1. Implémentation Sprint M2-5.

Invariants applicables (cf. ADR-028 §3) :
- IL1 : 25 transitions théoriques → 10 strictes (HTTP 409 sur reste)
- IL2 : `chk_lifecycle_state` CHECK constraint DB whitelist 5 valeurs
- 🛡️ IL3 : réouverture admin + fresh token + justification (cardinal Amine)
- 🛡️ IL4 : `expired` interdit P0/P1 conformité/facturation (cardinal Amine)
- 🛡️ IL5 : `merged_duplicate` interdit si recurrence sans duplicate (cardinal Amine, Q9-B)
- IL6 : auto-close récurrence cascade `resolved_via_recurrence`
- 🛡️ IL7 : auto-close P0/P1 exige preuve OU justification (cardinal Amine)
- IL8 : toute transition écrit `action_event_log` (event_type=`state_changed`)
- IL9 : toute transition déclenche `score_stale = TRUE`
- IL10 : `closed_at IS NOT NULL` ⇔ `lifecycle_state=closed` (CHECK DB)
- IL11 : réouverture trace event avec `justification` non vide (≥10 chars)

Source : docs/dev/L5_ADR-028_lifecycle_states.md (commit 466b64c3 · 53/53 ✓).
"""
