# Task 02 — Prompt migration data model

**Agent cible** : `prompt-architect`
**Difficulté** : easy
**Sprint origin** : Prompts / Migration

## Prompt exact

> Génère un prompt pour migrer le data model : ajouter `tax_profile_code` sur `Site`, migration Alembic, backfill, pas de downtime.

## Golden output (PASS)

- [ ] Phase 0 audit existant read-only
- [ ] Phase 1 design migration
- [ ] Phase 2 alembic up + down
- [ ] Phase 3 backfill script
- [ ] Phase 4 test migration up/down/up
- [ ] **Rollback plan** explicite
- [ ] Atomic commits par phase

## Anti-patterns (FAIL)

- ❌ Pas de rollback
- ❌ Phases fusionnées (pas atomic)
- ❌ Ignore backfill

## Rationale

Migration = risque prod. Prompt bien structuré sauve vies.
