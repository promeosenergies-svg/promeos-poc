# Followup — CO₂ frontend cleanup (P0 résiduel)

**Origine** : Audit Agents SDK — Phase 0 (2026-04-24) faille #3
**Sévérité** : P0 — hardcoded constant visible utilisateur
**Hors scope** : audit agents (à traiter en PR dédiée)

## Problème

Migration Option C de V120 (EmissionFactorsContext) incomplète sur `main` :

```
frontend/src/components/ConsoKpiHeader.jsx:12   import { CO2E_FACTOR_KG_PER_KWH } from '../pages/consumption/constants';
frontend/src/components/ConsoKpiHeader.jsx:138  const co2Kg = totalKwh != null ? Math.round(totalKwh * CO2E_FACTOR_KG_PER_KWH) : null;
```

Le calcul CO₂ reste côté frontend avec constante hardcodée, **violant la règle d'or** "zero business logic in frontend".

## Impact

- Valeur CO₂ affichée = 0.052 kg/kWh hardcodée
- Si ADEME met à jour le facteur (V24.0+), divergence backend/frontend
- Pattern dupliqué ailleurs : à auditer exhaustivement

## Action proposée

1. **Grep exhaustif** : `grep -rnE "CO2E_FACTOR|0\.052" frontend/src` — lister tous les usages résiduels
2. **Migrer vers `useElecCo2Factor()`** du `EmissionFactorsContext` (déjà mergé via V115/V120)
3. **Supprimer** `frontend/src/pages/consumption/constants.js:CO2E_FACTOR_KG_PER_KWH`
4. **Source-guard** : test Vitest qui échoue si `CO2E_FACTOR_KG_PER_KWH` réapparaît dans le code

## Lien avec audit agents SDK

- **Phase 4** du catalogue : ajouter un **source-guard xfail** pour tracer la dette sans bloquer la PR
- Le fix lui-même est hors scope de l'audit — PR dédiée

## Owner

À assigner. Estimation : ~1h (migration simple, pattern déjà établi).

## Références

- V120 migration : `project_agent_sdk_migration_2026_04_15.md` (memory)
- Context : `frontend/src/contexts/EmissionFactorsContext.jsx`
- Hook : `useElecCo2Factor()`
