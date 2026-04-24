# Task 04 — Anti-pattern React : business logic dans JSX

**Agent cible** : `code-reviewer`
**Difficulté** : medium
**Sprint origin** : CX / Règle d'or

## Prompt exact

> Revue : JSX contenant `{Math.round(data.kwh * 0.052)} kgCO₂`

## Golden output (PASS)

- [ ] Flag severity P0 (violation règle d'or zero business logic frontend)
- [ ] Détecte hardcode 0.052 aussi
- [ ] Suggestion : data pré-calculée backend OU hook `useElecCo2Factor()`
- [ ] 2 findings distincts (business logic + hardcode)

## Anti-patterns (FAIL)

- ❌ Un seul finding
- ❌ Flag P2 (sous-estimation)
- ❌ Accepte "c'est juste un affichage"

## Rationale

Double violation classique frontend. Dette V120 Option C à détecter en routine.
