# Backlog — Investissement suite RTL runtime (sprint dédié)

> **Date** : 2026-04-23 · **Origine** : Sprint 1 Vague B post-audit F4
> **Décision** : source-guards renforcés (F4 immédiat), RTL complet reporté

## Contexte

L'audit tests Vague B (Agent 3) a identifié **4 P0 faux négatifs** où un
bug runtime passerait les tests source-guards actuels :

- **P0.1** `SolAppShell` : 2 `useEffect` avec dep `[location.pathname]` non
  discriminés par regex (drawer-close vs trackRouteChange)
- **P0.2** `SolPanel` : ordre DOM Épinglés/Récents/NAV non verrouillé —
  **fixé F1 commit `1e8a5be0`** via test `indexOf` comparison
- **P0.3** `useRouteTracker` : guard `EXCLUDED_PATHS` comportement
  non-vérifié (bug typo `if (...) /* return manquant */`)
- **P0.4** `SolPanel` : `pinsVersion` incrément non-comportemental (bug
  `setPinsVersion(0)` sans incrément passerait)

## Fix appliqué F4 (immédiat)

`frontend/src/__tests__/sol_panel_runtime_guards.test.js` — 9 tests
source-guards **renforcés** avec regex atomiques qui :
- Matchent le bloc `useEffect(() => {...}, [deps])` complet (pas juste
  la présence de strings isolées)
- Vérifient l'ordre des instructions (guard early-return AVANT l'appel
  addRecent)
- Verrouillent le pattern exact `setPinsVersion((v) => v + 1)` (attrape
  `setPinsVersion(0)` ou `setPinsVersion(v)` sans incrément)
- Comptent les occurrences pour les vecteurs multiples (3 `onClose`
  equivalents : Escape, overlay, close button × 2)

**Couvre effectivement 3/4 P0** + test Drawer `onClose` invariant bonus.

## Limite des source-guards

Les regex renforcées attrapent les refactos **syntaxiquement naïfs**
mais restent impuissantes face à :
- **Inversion logique** : `if (!EXCLUDED_PATHS.has(pathname)) return;`
  → regex stricte match toujours, bug runtime persiste
- **Conditions indirectes** : `const shouldSkip = compute(); if
  (shouldSkip) return;` → aucun pattern atomique ne capture
- **State update batching** : React peut batcher les updates, un test
  runtime détecterait un deadlock de render, pas le source-guard

## Proposition sprint dédié RTL (post-Sprint 1)

### Scope
- Installer `@testing-library/react @testing-library/user-event
  @testing-library/jest-dom jsdom` (4 deps ~50 transitive)
- Vitest config : ajouter `test.environment: 'jsdom'` soit global soit
  par-fichier via `// @vitest-environment jsdom` comment
- Setup file `src/test-setup.js` avec `import '@testing-library/jest-dom'`

### Tests cibles (ordre de priorité)
1. `SolPanel.runtime.test.jsx` — pin toggle effectif, ordre DOM Épinglés
   avant Récents (rendu DOM réel), sections-hidden filters
2. `SolAppShell.runtime.test.jsx` — drawer close sur navigation, hamburger
   click, Escape ferme drawer, overlay click ferme
3. `useRouteTracker.runtime.test.jsx` — wrap `renderHook` avec
   `MemoryRouter`, assert `addRecent` NOT called sur `/login`
4. `Drawer.runtime.test.jsx` — 3 vecteurs `onClose` équivalents
   sémantiquement (Escape, overlay, close button)

### Coût estimé
- Setup : ~1h (deps + config + setup file)
- 4 suites × ~20 LOC each = ~80 LOC tests
- CI : +3-5s au boot vitest (jsdom = ~10MB RAM supplémentaire)
- Total sprint : **~2-3h**

### Bénéfice
- Attrape les 4 P0 faux négatifs Sprint 1 Vague B **et tous les futurs
  équivalents**
- Convention projet évolue : source-guards pour structure + RTL pour
  comportement critique (complémentaires, pas exclusifs)

## Décision user

**Immédiat** : F4 source-guards renforcés suffisent pour Sprint 1
(9 tests couvrent 3/4 P0 + bonus Drawer onClose invariant).

**Post-Sprint 1** (avant Sprint 2 Vague C câblage pages Sol) : user
décide si l'investissement RTL vaut le coup. La convention projet
(source-guards stricts) est explicite et a été défendue ; briser
cette convention nécessite un alignement produit.

Si GO :
- Créer branche dédiée `claude/rtl-runtime-suite`
- Commit atomique "chore(deps): add RTL + jsdom for runtime tests"
- Suivre par 4 suites tests cibles
