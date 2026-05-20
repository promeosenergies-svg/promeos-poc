"""
PROMEOS V4 · 12 endpoints `/api/action-center/*` (ADR-027 §9).

Scaffold Sprint M2-1. Implémentation Sprint M2-4 (routes core) + M2-5 (lifecycle)
+ M2-6 (evidence).

Invariants applicables (cf. ADR-027 §3) :
- IS1 : toutes routes `/api/action-center/*` ont `@org_scoped` obligatoire
- IS3 : cross-org → HTTP 404 (pas 403, anti-énumération)
- IS4 : Pydantic strict (whitelist + Literal)
- IS5 : `@admin_only_with_fresh_token` sur endpoints sensibles
- IS9 : `correlation_id` propagé dans tous events

12 endpoints planifiés (cf. L9 §2 Sprint M2-4) :
  1. GET /pilotage
  2. GET /items/{id}
  3. POST /items
  4. PATCH /items/{id}/lifecycle      (Sprint M2-5)
  5. PATCH /items/{id}/owner
  6. PATCH /items/{id}/blockers
  7. POST /items/{id}/close            (Sprint M2-5)
  8. PATCH /items/{id}/correct-kind    (admin only IS5)
  9. GET /items/{id}/audit-trail
  10. GET /impact
  11. POST /items/{id}/evidence        (Sprint M2-6)
  12. POST /items/{id}/scenarios/{scenario_id}/select

Couverture sécurité : IDOR matrix 288 cellules (12 routes × 3 rôles × 2 orgs × 4 cas).

Source : docs/dev/L4_ADR-027_securite_org_scoping.md §9 (commit faba2a61 · 50/50 ✓).
"""
