# Task 01 — Status baseline branche courante

**Agent cible** : `qa-guardian`
**Difficulté** : easy
**Sprint origin** : QA

## Prompt exact

> Donne le statut baseline tests de la branche courante. PASS ou FAIL ?

## Golden output (PASS)

- [ ] Commandes exécutées : `pytest --collect-only` + `vitest list`
- [ ] Compare à `origin/main` tip
- [ ] Verdict `PASS` ou `FAIL` explicite
- [ ] Format JSON `{status, criteria_passed, criteria_failed, blockers}`
- [ ] Read-only strict (aucun Write)

## Anti-patterns (FAIL)

- ❌ Donne un nombre inventé sans exécuter
- ❌ Verdict flou "ça devrait être OK"
- ❌ Utilise Write/Edit

## Rationale

Rôle central qa-guardian. Erreur ici = release dangereuse.
