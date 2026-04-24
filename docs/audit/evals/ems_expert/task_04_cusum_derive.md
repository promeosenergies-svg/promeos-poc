# Task 04 — CUSUM détection dérive consommation

**Agent cible** : `ems-expert`
**Difficulté** : medium
**Sprint origin** : EMS / ISO 50001

## Prompt exact

> Implémente détection dérive CUSUM sur signature énergétique de référence. Site X : signature de ref année N-1, seuil 5%. Alerte si dérive > 3 périodes consécutives.

## Golden output (PASS)

- [ ] CUSUM référence à signature énergétique (pas mois N-1)
- [ ] Formule CUSUM correcte : S_i = max(0, S_{i-1} + (x_i - μ) - k)
- [ ] Seuil h configurable
- [ ] Output JSON `{kpi, value, unit, method: "ISO 50001 CUSUM", variance_pct}`
- [ ] Délègue à `test-engineer` pour test avec seed

## Anti-patterns (FAIL)

- ❌ Baseline = mois N-1 (mauvais pattern)
- ❌ Seuil hardcodé
- ❌ Formule CUSUM erronée

## Rationale

Méthode ISO 50001 canonique. Erreur formule = fausses alertes.
