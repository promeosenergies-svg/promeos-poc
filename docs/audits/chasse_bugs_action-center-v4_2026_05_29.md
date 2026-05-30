# Chasse-bugs Tour 3 — `/action-center-v4`

**Date** : 2026-05-29
**Branche** : `claude/chasse-bugs-action-center-v4-2026-05-29`
**Base** : `claude/refonte-sol2` HEAD `96242460` (post #337 P1.S5 coût contrat)
**Skill** : `chasse-bugs-promeos` (3e tour, cycle 1)

## Périmètre audité

- 3 pages : `ActionCenterV4ListPage.jsx`, `ActionCenterV4PilotagePage.jsx`, `ActionCenterV4JournalPage.jsx`
- Composants dans `frontend/src/pages/action-center-v4/components/` (drawer, items, modals, narrative, shared)
- Constants et utils
- Routes vérifiées : `/action-center-v4`, `/action-center-v4/pilotage`, `/action-center-v4/pilotage/journal` (App.jsx lignes 388-413)

**Contexte** : refonte Centre d'Action V4 lancée 13/05/2026 (Mois 1-6, ADR-025..029 Accepted, doctrine v0.3). Code récent, propre, doctrine appliquée.

## Findings par catégorie

### Cat 1 — Boutons/liens inactifs : 1 finding **MAJEUR (a11y)** ✅ fixé

**[MAJEUR a11y]** `frontend/src/pages/action-center-v4/components/drawer/LinkItem.jsx:65-77` — lien `<a href="#" onClick={(e) => e.preventDefault()}>` avec contenu textuel `{LINKS_COPY.linkActionOpen}` ("Ouvrir"). MV3 intentionnel (le module cible n'est pas encore implémenté côté liens cliquables), mais le lien rendu n'expose pas la cible aux lecteurs d'écran — un assistive reader entend seulement "Ouvrir".

**Fix appliqué** : ajout `aria-label={\`${LINKS_COPY.linkActionOpen} ${moduleLabel} ${truncatedId || ''}\`.trim()}` — préserve le visuel intact, expose le contexte aux screenreaders ("Ouvrir Patrimoine 5a3f8c1e…").

### Cat 2 — Routes mortes : 0 finding

Routes V4 toutes présentes. `navigate('/action-center-v4?without_owner=true')` (NarrativeBar.jsx:39) cible valide.

### Cat 3 — Jargon technique exposé : 0 finding

Aucun `rule_id`, `correlation_id`, `efa_id`, `score_stale`, `[object Object]`, `undefined`/`NaN`/`null` string, `TODO`/`FIXME` dans le JSX rendu. Acronymes (OPERAT, etc.) référencés uniquement dans mocks tests, jamais affichés inline.

### Cat 4 — Texte non-FR : 0 finding

Aucune string anglaise rendue (Error, Loading, Submit, OK, Cancel...). Textes centralisés dans constants `COPY`, `JOURNAL_COPY`, `PILOTAGE_COPY` (FR). Espaces insécables auto via `toLocaleString('fr-FR')`.

### Cat 5 — « ? » indicatifs morts : 0 finding

Aucun `<Info>` / `<HelpCircle>` / `<QuestionMark>` orphelin. `title=` natif HTML utilisé systématiquement sur éléments interactifs (DrawerActions, NarrativeBar, ImpactSection).

### Cat 6 — Calculs faux ou incohérents : 0 finding

- `Math.round(value)` dans `ImpactSection.jsx:24` et `PriorityBadge.jsx:26,40` : **formatting d'affichage**, pas calcul métier. Valeurs viennent du backend. Conforme doctrine §8.1 (zero biz FE).
- Aucune division par zéro sans guard.

### Cat 7 — KPI mensongers : 0 finding

`NarrativeBar` `?? 0` sur tuiles P0/P1/Risk/Secured = volontaire (palette neutre ink, pas color-coding). `EditorialNarrativeBlock` impact `0 €` accepté (CFO money semantics — zéro est une mesure valide, pas un fallback). `ImpactSection` expose `source` + `formula` sous chaque card (lignes 71-86) ✅.

### Cat 8 — Console errors : pas testé ce tour

2 `console.error` détectés (PilotagePage:113 export PDF, DrawerErrorBoundary:19 React error boundary) — patterns standards, acceptables. Vérification Playwright reportée.

### Cat 9 — Network 4xx/5xx : pas testé ce tour

`ErrorState` composants présents partout. Vérification Playwright reportée.

### Cat 10 — Dette technique : 0 finding

- Aucun `{false && ...}` ni `{true && ...}` code mort.
- Aucun `// removed`, `// deprecated` autour de code actif.
- Imports inutilisés : zéro flagrant (spot-check 3 pages + modals).
- Aucune duplication apparente (tab views réutilisent drawer/items/modals).
- Test `V15Scope.test.js` fail pré-existant (déjà reporté Tour 2 docs/audits/chasse_bugs_usages_2026_05_29.md Cat 10 — owner = PR #335 P1.S4 énergie).

## Décisions appliquées ce tour

| Finding | Sévérité | Décision | Fichier |
|---|---|---|---|
| Cat 1 a11y LinkItem `<a>` sans aria-label | MAJEUR (a11y) | **Fixer** | LinkItem.jsx (+3 lignes) |
| EditorialNarrativeBlock CTA MV3 grisés | MINEUR | Pas un bug — MV3 intentionnel + tooltip présent | Backlog M2-6 si feedback user |
| DrawerBreadcrumb retourne null silencieux | MINEUR | Conforme doctrine §6.6 — M3 BE task déjà tracked | Pas d'action |

## Tests

- `vitest LinkItem.test.jsx` : 10/10 ✅
- `vitest run` full : 5 478 pass / 3 skipped / 1 fail pré-existant (V15Scope, déjà reporté Tour 2) — **0 régression**

## Verdict tour 3

✅ **GO** — 1 finding MAJEUR a11y fixé (1 ligne), 0 régression. Périmètre `/action-center-v4` confirmé **très sain** (refonte Mois 1-6 propre, doctrine appliquée).

## Suite (tour 4 selon skill)

`/bill-intel` + composants.
