# Task 02 — Regression test pour bug fixé

**Agent cible** : `test-engineer`
**Difficulté** : easy
**Sprint origin** : TDD

## Prompt exact

> Un bug dans `resolve_naf_code` retournait `None` pour les NAFs commençant par "99". Écris un regression test.

## Golden output (PASS)

- [ ] Test pytest dans `backend/tests/` scopé au module
- [ ] Assert positif : "99XX" retourne archétype correct
- [ ] Assert ne pas-None
- [ ] Test < 30L
- [ ] Commit : `test(naf): regression — "99" prefix resolution`

## Anti-patterns (FAIL)

- ❌ Test dans le fichier de prod (mélange)
- ❌ Mock excessif (doctrine : intégration > mocks)
- ❌ Pas d'assert du bug reproduit

## Rationale

Protection non-régression post-fix. TDD basique.
