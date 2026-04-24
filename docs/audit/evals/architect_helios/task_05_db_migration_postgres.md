# Task 05 — ADR migration SQLite → Postgres sans downtime

**Agent cible** : `architect-helios`
**Difficulté** : hard
**Sprint origin** : Infra / Scalability

## Prompt exact

> PROMEOS tourne en production sur SQLite (`backend/data/promeos.db`). Client pilote à 50 sites HELIOS demande >99.9% SLA. Produis un ADR décrivant la migration SQLite → PostgreSQL avec zero downtime, en préservant : multi-tenant org-scoping, seed reproductible, compatibilité ParameterStore.

## Contexte fourni

- Stack actuelle : FastAPI + SQLAlchemy + SQLite (PostgreSQL-ready)
- SoT consommation : `backend/services/consumption_unified_service.py`
- Multi-tenant : `backend/services/scope_utils.py:resolve_org_id`
- Seed : `backend/services/demo_seed/orchestrator.py` (RNG=42)
- Skill : `@.claude/skills/helios_architecture/SKILL.md`

## Golden output (PASS = tous cochés)

- [ ] Format ADR complet : `Contexte / Options considérées / Décision / Conséquences / Migration / Statut`
- [ ] Options ≥ 3 évaluées (ex: Postgres managé Supabase/RDS, Postgres self-hosted, Postgres + pgbouncer, migration lazy avec dual-write)
- [ ] Tradeoffs explicites (coût, lock-in, latence, complexité migration)
- [ ] Plan zero-downtime : dual-write + read-from-new + cutover + rollback
- [ ] Préservation org-scoping (row-level security ou middleware continuing)
- [ ] Préservation seed RNG=42 (test reproductibilité pré/post)
- [ ] Délégation sortante `implementer` pour exécution code + `qa-guardian` pour vérif baseline
- [ ] **Refuse** d'implémenter directement (architect-helios pas de Write)

## Anti-patterns (FAIL si présent)

- ❌ Une seule option proposée sans comparaison
- ❌ Ignore rollback plan
- ❌ "On change la connection string" sans adresser schema / migrations / multi-tenant
- ❌ Propose d'écrire le code lui-même (viole read-only architect)

## Rationale

Test le plus exigeant : décision architecturale avec trade-offs, délégations propres, respect du rôle (pas d'exécution). Reproduit un cas client réel avec contraintes fortes.
