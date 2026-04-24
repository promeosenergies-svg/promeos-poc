# Task 05 — Migration Alembic avec rollback safe

**Agent cible** : `implementer`
**Difficulté** : hard
**Sprint origin** : DB / Release

## Prompt exact

> Ajouter colonne `tax_profile_code` (nullable) à la table `sites` via Alembic. Rollback plan inclus.

## Golden output (PASS)

- [ ] Migration Alembic (up + down symétriques)
- [ ] Colonne `nullable=True` (backward-compat)
- [ ] Backfill script si défaut requis
- [ ] Test migration up → baseline OK → down → baseline OK
- [ ] Commit canonical `fix(db-pN): Phase X.Y — add tax_profile_code column`
- [ ] Délègue à `qa-guardian` pour baseline validation

## Anti-patterns (FAIL)

- ❌ `nullable=False` sans défaut (casse DB)
- ❌ Down migration oubliée
- ❌ `DROP COLUMN` dans down sans warning data-loss
- ❌ Ignore baseline tests

## Rationale

Migration DB = risque production. Rollback = obligation. Test `up/down/up` réel.
