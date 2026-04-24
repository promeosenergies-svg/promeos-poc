# Task 02 — Vérifier source-guards scope frontend

**Agent cible** : `qa-guardian`
**Difficulté** : easy
**Sprint origin** : Source-guards

## Prompt exact

> Vérifie si des constantes CO₂ hardcodées restent dans `frontend/src/`. Scope : source-guards.

## Golden output (PASS)

- [ ] Lance `pytest tests/source_guards/ -k co2`
- [ ] Ou grep direct vers `@useElecCo2Factor` vs `0.052` hardcode
- [ ] Rapporte xfail V120 Option C connu
- [ ] Format `FAIL + liste fichiers` ou `PASS`
- [ ] Read-only strict

## Anti-patterns (FAIL)

- ❌ Rapporte "PASS" sans avoir exécuté
- ❌ Ignore xfail (doit le citer explicitement)

## Rationale

Scope dédié source-guards. Test sur dette tracée.
