# Dev Notes — QW3-5 Accent Sweep (2026-02-18)

## Diagnostic

Scan codebase-wide des strings FR visibles utilisateur.
80+ occurrences de mots sans diacritiques dans 24+ fichiers `.jsx`.

Patterns les plus frequents :

- `donnees` → `données` (22 occurrences)
- `detecte/detectee/detectees` → `détecté(e)(s)` (14)
- `conformite` → `conformité` (12)
- `reglementaire` → `réglementaire` (8)
- `evenement` → `événement` (6)
- `resultat(s)` → `résultat(s)` (8)
- Divers : `generez`, `terminee`, `energetique`, `selectionnee`, `reinitialiser`...

## Hypotheses

- Les accents manquants sont des oublis de saisie (pas un choix technique)
- Aucun impact runtime (strings purement display)
- Risque de regression : nul si guard tests en place

## Plan

3 batches pour respecter la regle "max 8 fichiers modifies" :

| Batch | Fichiers | Corrections |
| ----- | -------- | ----------- |
| A | 8 (ConsommationsUsages, ConsumptionExplorer, Watchers, Patrimoine, Site360, Import, BillIntel, SiteDetail) | ~50 |
| B | 8 (AdminAuditLog, Connectors, KBExplorer, PurchaseAssistant, Purchase, Notifications, AdminUsers, ConsumptionDiag) | ~28 |
| C | 8 (AdminAssignments, Compliance, Dashboard, Status, Consommations, Cockpit2Min, AdminRoles, Patrimoine fix extra) | ~11 |

## Guard tests

`AccentSweepGuard.test.js` — 37 tests source-level (`readFileSync` + regex negatives).
Chaque batch a ses describe blocks dedies.
Un test echoue = une regression d'accent detectee immediatement.

## Definition of Done

- [x] Batch A : 8 fichiers, ~50 corrections appliquees
- [x] Batch B : 8 fichiers, ~28 corrections appliquees
- [x] Batch C : 8 fichiers, ~11 corrections appliquees
- [x] vitest : 986 tests green (935 → 986 = +51)
- [x] build : clean 13.81s
- [x] Guard tests : 37/37 green
- [x] CHANGELOG.md mis a jour
- [x] Aucune regression

## Backlog (non traite)

- Patrimoine.jsx USAGE_OPTIONS : `Entrepot`, `Hotel`, `Sante` sans accents (labels de donnees mock, pas prioritaire)
- Quelques `defaut` dans des contextes de tri/sort (non user-visible)
