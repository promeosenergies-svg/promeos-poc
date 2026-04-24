# Task 03 — Génération carpet plot 24h × 365j

**Agent cible** : `ems-expert`
**Difficulté** : medium
**Sprint origin** : EMS / Visualisation

## Prompt exact

> Implémente endpoint `/api/sites/{id}/carpet` qui retourne matrice 24×365 pour carpet plot Recharts. Seed HELIOS pour test.

## Golden output (PASS)

- [ ] Backend calcule matrice pré-formatée (règle d'or)
- [ ] Org-scoping via `resolve_org_id`
- [ ] CDC 30min via `data-connector` si manquant
- [ ] Format JSON `{matrix: [[...], ...], period, unit}`
- [ ] Seed HELIOS RNG=42 pour reproductibilité
- [ ] Délègue à `implementer` pour code + `test-engineer` pour test

## Anti-patterns (FAIL)

- ❌ Calcul côté frontend (violation règle d'or)
- ❌ Pas d'org-scoping
- ❌ Hardcode seed

## Rationale

Feature centrale EMS visualisation. Teste archi + règle d'or.
