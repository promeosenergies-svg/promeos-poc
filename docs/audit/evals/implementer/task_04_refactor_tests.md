# Task 04 — Refacto service avec test coverage

**Agent cible** : `implementer`
**Difficulté** : medium
**Sprint origin** : Qualité

## Prompt exact

> Refacto `backend/services/billing_engine/catalog.py:get_turpe_rate()` : la logique date est dupliquée 3 fois. Extrait un helper. Baseline tests = 5691 BE.

## Golden output (PASS)

- [ ] Helper extrait (pattern DRY)
- [ ] 3 call sites mis à jour
- [ ] Baseline tests ne régresse pas (> 5691)
- [ ] Commit atomique
- [ ] Délègue à `code-reviewer` avant merge
- [ ] Délègue à `test-engineer` si nouveau test requis

## Anti-patterns (FAIL)

- ❌ Casse tests existants
- ❌ Nouvelle duplication de logique
- ❌ Oublie pre-merge `/code-review:code-review`

## Rationale

Refacto classique sans régression — vérifie discipline baseline.
