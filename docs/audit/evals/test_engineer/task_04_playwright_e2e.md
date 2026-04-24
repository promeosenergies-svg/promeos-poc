# Task 04 — Playwright E2E parcours Site360

**Agent cible** : `test-engineer`
**Difficulté** : medium
**Sprint origin** : CX / E2E

## Prompt exact

> Écris un test Playwright : login user → navigue vers Site360 site HELIOS #1 → vérifie présence carpet plot + 3 KPIs + pas d'erreur console.

## Golden output (PASS)

- [ ] Fichier `tests/e2e/site360.spec.js` (scope correct)
- [ ] Seed HELIOS préalable (RNG=42)
- [ ] Assert no console.error (doctrine user stricte)
- [ ] Pas de sleep(X) arbitraire → `waitFor*` selectors
- [ ] Screenshot before/after pour régression visuelle

## Anti-patterns (FAIL)

- ❌ `sleep(1000)` arbitraire
- ❌ Ignore console errors
- ❌ Hardcode URL prod

## Rationale

Teste discipline E2E sans flaky. Cas usage audit front.
