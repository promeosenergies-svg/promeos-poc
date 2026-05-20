"""
PROMEOS V4 · Pattern repository org-scopé (🛡️ IS11 cardinal Amine).

Scaffold Sprint M2-1. Implémentation Sprint M2-3 (sécurité layer) puis enrichi
sprint par sprint.

Invariant cardinal :
- 🛡️ IS11 : pas d'accès DB direct dans routes — `repo.get_by_id(id, organisation_id=...)`
            obligatoire. 4 lignes de défense empilées :
            (1) middleware OrgScopingMiddleware — injection request.state.organisation_id
            (2) décorateur @org_scoped(allowed_roles=...) — vérification + role check
            (3) repository pattern — `organisation_id` paramètre obligatoire
            (4) source-guards CI — `test_no_query_action_center_without_org_filter`

Repositories planifiés Mois 2 :
- ActionCenterItemRepository (Sprint M2-4)
- ActionEventLogRepository (Sprint M2-6)
- EvidenceRepository (Sprint M2-6)
- ActionLinksRepository · ActionBlockersRepository · ActionScenariosRepository
- DuplicateGroupRepository · RecurrenceGroupRepository

Source : docs/dev/L4_ADR-027_securite_org_scoping.md §8 (commit faba2a61 · 50/50 ✓).
"""
