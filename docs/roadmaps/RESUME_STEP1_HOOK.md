# Rapport Step 1 — useCockpitData Hook

**Branche** : `feat/cockpit-world-class`
**Commit** : `0bcddd6` — `feat(step1): useCockpitData hook — parallel fetch, display-only`
**Date** : 2026-03-23
**Statut** : DONE — 17/17 tests verts, 0 regression, build OK

---

## Ce qui a ete livre

### Hook `useCockpitData.js`
Hook React dedie au cockpit executif. Regle absolue : **display-only, zero calcul metier**.

**4 appels paralleles** via `Promise.all` :
| Endpoint | Wrapper API | Donnees |
|----------|------------|---------|
| `GET /api/cockpit` | `getCockpit()` | KPIs, risque, conformite |
| `GET /api/cockpit/trajectory` | `getCockpitTrajectory()` | Trajectoire DT pre-calculee |
| `GET /api/actions/summary` | `getActionsSummary()` | Compteurs actions |
| `GET /api/billing/summary` | `getBillingSummary()` | Anomalies billing |

**Shape retournee** :
```
{
  kpis: { conformiteScore, conformiteSource, conformiteComputedAt, risqueTotal, risqueBreakdown, totalSites, sitesActifs, avancementDecretPct, orgNom },
  trajectoire: { refYear, refKwh, reductionPctActuelle, objectif2026Pct, annees, reelMwh, objectifMwh, projectionMwh, jalons, surfaceM2Total, computedAt },
  actions: { total, enCours, urgentes, potentielEur },
  billing: { anomalies, montantEur },
  loading, error, lastFetchedAt, refetch
}
```

**Resilience** : chaque appel encapsule son `.catch()` — un echec partiel n'empêche pas les autres donnees d'être disponibles.

### Wrappers API ajoutes
- `getCockpit()` — `api/cockpit.js` (utilise `cachedGet`)
- `getCockpitTrajectory()` — `api/cockpit.js` (utilise `cachedGet`)

Les wrappers existants reutilises sans modification :
- `getActionsSummary()` — `api/actions.js`
- `getBillingSummary()` — `api/billing.js`

---

## Fichiers modifies/crees

| Fichier | Type |
|---------|------|
| `frontend/src/hooks/useCockpitData.js` | **NOUVEAU** — Hook principal |
| `frontend/src/services/api/cockpit.js` | Ajout 2 wrappers (`getCockpit`, `getCockpitTrajectory`) |
| `frontend/src/__tests__/useCockpitData.test.js` | **NOUVEAU** — 17 tests source guard + structure |

---

## Tests (17/17)

### Source Guards (no-calc-in-hook)
- Aucun `/ total * 100`
- Aucun `1 - x/y * 100`
- Aucun `Math.round(`
- Aucun `* 7500` ou `* 3750`
- Aucun `compliance_score = Math...`

### Structure
- Export `useCockpitData` present
- Import `useScope`, `logger`, 4 wrappers API
- `Promise.all` pour parallelisme
- `mountedRef` guard

### Normalize Functions
- `normalizeCockpitKpis` expose les champs P0
- `normalizeTrajectory` expose les champs trajectoire
- `normalizeActions` expose total/enCours/urgentes
- `normalizeBilling` expose anomalies/montantEur

### Return Shape
- 8 champs exposes : kpis, trajectoire, actions, billing, loading, error, lastFetchedAt, refetch

---

## Regressions
- 0 regression introduite (133/134 tests passent, le 1 fail pre-existant est `compliance_safety.test.js` — non lie)
- Build frontend OK

---

## Definition of Done

- [x] `npx vitest run src/__tests__/useCockpitData.test.js` — 17/17 verts
- [x] `npx vitest run` — 0 regression
- [x] `npm run build` — exit 0
- [x] `useCockpitData` expose : `{ kpis, trajectoire, actions, billing, loading, error, lastFetchedAt, refetch }`
- [x] `kpis.conformiteScore` vient de `compliance_score` (RegAssessment) — pas recalcule
- [x] `trajectoire.reductionPctActuelle` vient du backend — pas recalcule front
- [x] Aucune formule de calcul dans le hook
- [x] Partial failure : si un appel echoue, les autres donnees restent disponibles
- [x] Commit propre sur `feat/cockpit-world-class`
- [x] Push sur origin
