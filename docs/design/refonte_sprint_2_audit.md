# Refonte Sprint 2 — Audit read-only (Phase 0)

**Branche** : `claude/refonte-visuelle-sol` · **Base** : `85da03cd`

## Inventaire 4 pages flagship

| Page | Lignes `className` | PageShell | KpiCard utilisé |
|---|---|---|---|
| `Cockpit.jsx` | 134 | oui (via `PageShell`) | `KpiCardInline` + `ExecutiveKpiRow` (composant custom local) |
| `ConformitePage.jsx` | 22 | oui | `KpiCard` (générique `ui/`) |
| `BillIntelPage.jsx` | 116 | oui | `KpiCard` (générique) |
| `Patrimoine.jsx` | 207 | oui | `KpiCard` |

**37 pages** utilisent `PageShell` au total — pas de refonte du Shell (hors scope Sprint 2).

## PageShell — hideHeader absent

Signature actuelle : `{icon, title, subtitle, actions, inlineActions, children, className, tintColor, moduleKey}`.
Pas de prop `hideHeader`. **Décision** : ajouter une prop `hideHeader=false` (pure présentation, défaut false → rétro-compat). Permet aux pages refontes d'utiliser `<SolPageHeader>` dedans sans duplication visuelle.

## Headlines + phrase d'introduction actuelles

**Cockpit** : `PageShell subtitle="..."` = ligne grise en dessous du titre. Pas de narrative éditoriale. À remplacer par `<SolPageHeader narrative={…}>`.

**ConformitePage** / **BillIntelPage** / **Patrimoine** : pareil, `subtitle` factuel. Pas de voix humaine.

## AppShell — footer timerail

`AppShell.jsx` ligne 362 : `<main id="main-content" className="flex-1 overflow-y-auto">{children}</main>`. Pas de zone footer dédiée, layout `flex flex-col h-screen`.

**Décision** : injecter `<SolTimerail>` comme composant **fixé** `position: fixed; bottom: 0` (pas dans le layout flex, évite casser le `overflow-y-auto` du main). Hauteur 36px, padding main ajusté `pb-10` pour que le contenu ne soit pas mangé.

## Courbes existantes

Existing Recharts usage probable dans :
- `pages/Usages*.jsx`
- `pages/Performance*.jsx`
- `components/LoadCurveChart.jsx` (si existe)

Sprint 5 les inventoriera et basculera sur `<SolLoadCurve>`.

## Questions ouvertes (à résoudre en Phase 2+)

- `buildCockpitNarrative(kpis, alerts)` : fonction pure présentation (nouvelle) — helpers dans `pages/cockpit/sol_interpreters.js`
- `solProposal` : feature-flag off par défaut Sprint 2 (mock `null`) — wiring réel Sprint 4
- Format FR : utiliser `utils/format.js` existant (`fmtEur`, `fmtKwh`) + créer `frenchifier.js` si nécessaire (pure fn)

## GO Phase 1

Stop gate 0 validé. Phase 1 démarre : 8 composants Sol dans `frontend/src/ui/sol/`.
