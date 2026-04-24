# Task 03 — Test intégration endpoint org-scopé

**Agent cible** : `test-engineer`
**Difficulté** : medium
**Sprint origin** : API / Multi-tenant

## Prompt exact

> Test intégration pour `GET /api/sites/{id}/kpi` : vérifier org-scoping (user org A ne voit pas site org B) + auth + format réponse.

## Golden output (PASS)

- [ ] Fixture 2 orgs + 2 users
- [ ] Assert 200 sur son org, 404 sur l'autre
- [ ] Assert format JSON (conso + CO₂ + score)
- [ ] DB réelle (SQLite test), pas mock
- [ ] Fixture reproductible (seed RNG=42)

## Anti-patterns (FAIL)

- ❌ Mock la DB (doctrine user : intégration > mocks)
- ❌ Hardcode user_id dans test
- ❌ Pas de test cross-org

## Rationale

Pattern récurrent. Org-scoping doit être testé sur chaque endpoint.
