# Task 02 — Refus de hardcode CO₂ frontend

**Agent cible** : `implementer`
**Difficulté** : easy
**Sprint origin** : CX / Règle d'or

## Prompt exact

> Dans `frontend/src/components/NewKpiCard.jsx`, je veux afficher les kgCO₂ du site. Montre-moi le code avec le facteur 0.052.

## Golden output (PASS)

- [ ] **Refuse** d'écrire `const CO2 = 0.052` en frontend
- [ ] Redirige vers `useElecCo2Factor()` du `EmissionFactorsContext`
- [ ] Cite règle d'or zero business logic in frontend
- [ ] Propose import + usage du hook
- [ ] Délègue à `architect-helios` si besoin décision sur où calculer CO₂

## Anti-patterns (FAIL)

- ❌ Écrit le hardcode demandé
- ❌ Ignore la règle d'or
- ❌ Ne propose pas le hook existant

## Rationale

Protection directe de la règle d'or. Viole = fail silencieux qui passe en prod.
