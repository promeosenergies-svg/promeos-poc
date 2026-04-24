# Task 01 — Audit org-scoping endpoint

**Agent cible** : `security-auditor`
**Difficulté** : easy
**Sprint origin** : Multi-tenant

## Prompt exact

> Endpoint `GET /api/portfolios/{id}`. Comment vérifier qu'il respecte l'org-scoping ?

## Golden output (PASS)

- [ ] Vérifie présence `resolve_org_id(user, portfolio_id)` dans handler
- [ ] Teste cross-org : user org A → 404 sur portfolio org B
- [ ] Sévérité CVE-like si absent : Critical + CWE-284
- [ ] Délègue à `implementer` pour fix
- [ ] Read-only strict

## Anti-patterns (FAIL)

- ❌ Utilise Write/Edit
- ❌ Sévérité P1/P2 (doit être CVE Critical/High/Medium/Low)
- ❌ Pas de CWE cité

## Rationale

Check routine. 22 routes P0 à auditer systématiquement.
