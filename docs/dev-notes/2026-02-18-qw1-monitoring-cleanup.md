# Dev Notes — QW1+QW2: MonitoringPage Cleanup + Import Hygiene

**Date:** 2026-02-18
**Scope:** MonitoringPage.jsx, Patrimoine.jsx, MonitoringPage.test.js

---

## Diagnostic

Audit du repo a identifie 5 quick wins. Ce batch couvre QW1 (MonitoringPage) + QW2 (unused imports).

### MonitoringPage.jsx
- 11 strings user-visible sans accents (Ecole, Hopital, Resolu, Severite, etc.)
- 1 `useMemo(() => mockSites, [])` sur une constante importee (zero benefice)
- 2 handlers `onClick={() => {}}` morts (Modifier/Appliquer dans UsagePanel) — identifies mais non supprimes (fonctionnalite future)

### Patrimoine.jsx
- 1 import `TrendingUp` jamais utilise dans le fichier

---

## Hypotheses

1. Les accents manquants sont des oublis de saisie (pas un choix delibere)
2. Le useMemo sur mockSites n'a aucun impact fonctionnel (referential equality inutile ici)
3. Les handlers vides dans UsagePanel sont des placeholders intentionnels pour une future feature "Modifier horaires"

---

## Corrections appliquees

| Ligne | Avant | Apres |
|-------|-------|-------|
| 110 | `'Ecole'` | `'École'` |
| 111 | `'Hopital'` | `'Hôpital'` |
| 1041 | `recommandee` | `recommandée` |
| 1077 | `Resolu` | `Résolu` |
| 1235 | `Resolu depuis UI` | `Résolu depuis UI` |
| 1241 | `la resolution` | `la résolution` |
| 1362 | `useMemo(() => mockSites, [])` | `mockSites` |
| 1377 | `(defaut)` | `(défaut)` |
| 1808 | `Resolus` | `Résolus` |
| 1850 | `detecter` | `détecter` |
| 1866 | `Severite` | `Sévérité` |
| 1923 | `Resoudre` | `Résoudre` |
| Patrimoine:11 | `TrendingUp` import | supprime |

---

## Guard tests

8 tests dans `MonitoringPage.test.js` > `QW1 guard`:
- Source-level (readFileSync) pour detecter les regressions d'accents
- Verifie aussi la suppression du useMemo inutile

---

## Definition of Done

- [x] 11 accents corriges dans MonitoringPage.jsx
- [x] useMemo inutile supprime
- [x] Import TrendingUp supprime dans Patrimoine.jsx
- [x] 8 guard tests ajoutés
- [x] `npx vitest run` → 943 tests green
- [x] `npm run build` → clean 13.54s
- [x] Zero regression
- [x] CHANGELOG.md mis a jour
- [x] Dev-notes cree

---

## Backlog restant (non traite)

| QW | Description | Fichiers |
|----|-------------|----------|
| QW3 | Accent sweep "donnees" (23 occurrences, 8 fichiers) | ConsumptionExplorerPage, ConsommationsUsages, ImportPage, etc. |
| QW4 | Accent sweep "detecte" + "conformite" (23 occurrences) | Patrimoine, Site360, SiteDetail, etc. |
| QW5 | Accent sweep "reglementaire" + "evenement" + "resultat" (18 occurrences) | WatchersPage, KBExplorerPage, AdminAuditLogPage, etc. |
