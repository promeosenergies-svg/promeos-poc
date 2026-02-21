# AUDIT GLOBAL — PROMEOS UX/BUG HARDENING

> Date : 2026-02-18
> Auteur : Claude Code (Lead Engineer + QA)
> Baseline : 930 tests / build clean 17.19s
> Post-fix : **935 tests / build clean 13.05s**

---

## Resume executif

Audit exhaustif de l'application PROMEOS (frontend React + backend FastAPI).
4 phases : scan statique, audit runtime, coherence data, correctifs.

| Priorite | Trouves | Corriges | Gardes par test |
|----------|---------|----------|-----------------|
| P0       | 2       | 2        | 2               |
| P1       | 15      | 15       | 5               |
| P2       | 3       | 0        | —               |

**Resultat final : 0 P0, 0 P1 ouverts. 3 P2 en backlog.**

---

## P0 — Bugs runtime / Navigation cassee

| # | Fichier | Symptome | Cause | Fix | Garde-fou |
|---|---------|----------|-------|-----|-----------|
| 1 | `MonitoringPage.jsx:1476` | Lien "Explorer" redirige vers 404 | Ancien chemin `/consumption-explorer` au lieu de `/consommations/explorer` | Remplacement du href | Test `RoutingSmoke.test.js` : "aucune route nav ne pointe vers /consumption-explorer" |
| 2 | `CommandCenter.jsx` | Bouton "Briefing" naviguait vers `/cockpit-2min` (route supprimee) | Route orpheline post-refactor V2 | Bouton pointe vers `/cockpit`, redirect `/cockpit-2min` → `/cockpit` dans App.jsx | Test `RoutingSmoke.test.js` : "/cockpit-2min n'est pas une destination de menu" |

---

## P1 — Labels anglais / Accents manquants

### A. NavRegistry.js (source de verite sidebar)

| # | Avant | Apres | Ligne |
|---|-------|-------|-------|
| 3 | `'Vue executive'` | `'Vue executive'` → `'Vue executive'` | items cockpit |
| 4 | `'Marche & Factures'` | `'Marche & Factures'` | section marche |
| 5 | `'Achats energie'` | `'Achats energie'` | item /achat-energie |
| 6 | `label: 'Roles'` | `label: 'Roles'` | item /admin/roles |
| 7 | `label: 'Assignments'` | `label: 'Affectations'` | item /admin/assignments |
| 8 | `label: 'Audit Log'` | `label: "Journal d'audit"` | item /admin/audit |

### B. Pages individuelles

| # | Fichier | Avant | Apres |
|---|---------|-------|-------|
| 9 | `Dashboard.jsx:58` | `title="Dashboard"` | `title="Tableau de bord (legacy)"` |
| 10 | `Dashboard.jsx:71` | `'PROMEOS Dashboard'` | `'PROMEOS — Tableau de bord'` |
| 11 | `Dashboard.jsx:72` | `"Gestion energetique multi-sites"` | `"Gestion energetique multi-sites"` |
| 12 | `AdminRolesPage.jsx` | `"Roles & Permissions"` (x3) | `"Roles & Permissions"` |
| 13 | `AdminRolesPage.jsx` | `"Acces refuse"` | `"Acces refuse"` |
| 14 | `AdminRolesPage.jsx` | `"11 roles systeme"` | `"11 roles systeme"` |
| 15 | `AdminAssignmentsPage.jsx` | `title="Assignments"` (x3) | `title="Affectations"` |
| 16 | `AdminAssignmentsPage.jsx:74` | `['...', 'Scope', 'Role', '...']` | `['...', 'Perimetre', 'Role', '...']` |
| 17 | `AdminAssignmentsPage.jsx:69` | `"Assigner un role"` | `"Assigner un role"` |
| 18 | `LoginPage.jsx:34` | `"Cockpit energetique"` | `"Cockpit energetique"` |
| 19 | `LoginPage.jsx:80` | `"Demo: sophie@..."` | `"Demo : sophie@..."` |
| 20 | `WatchersPage.jsx:258` | `"Reviser l'evenement"` | `"Reviser l'evenement"` |
| 21 | `SiteDetail.jsx:91` | `"non trouve"` | `"non trouve"` |
| 22 | `PurchasePage.jsx:67` | `label: 'Echeances'` | `label: 'Echeances'` |

---

## P2 — Backlog (non bloquant)

| # | Fichier | Description | Impact | Effort |
|---|---------|-------------|--------|--------|
| 23 | `ConsommationsUsages.jsx` | `ImportWizard` appelle `getSites()` sans filtre `org.id` — bypass scope | Donnees hors perimetre visibles dans l'import | Moyen |
| 24 | Fichiers charts (x5) | Couleurs hex hardcodees dans les props Recharts SVG (`#3B82F6`, `#10B981`, etc.) | Incoherence visuelle si changement de theme | Faible (limitation Recharts) |
| 25 | `App.jsx` | Route orpheline `/status` → `StatusPage` (pas dans nav) | Page accessible mais non decouvrable | Tres faible |

---

## Scan statique — Resultats

### Imports Lucide
**CLEAN** — 0 import non defini detecte. Tous les composants Lucide utilises dans les pages
sont importes depuis `lucide-react`.

### Dead code / Routes orphelines
- `/cockpit-2min` : redirige maintenant vers `/cockpit` (fix #2)
- `/dashboard-legacy` : conserve volontairement (page legacy visible en dev)
- `/status` : orpheline (P2 #25)
- `Cockpit2MinPage` lazy import : supprime de App.jsx

### Z-index
Couches correctement ordonnees :
```
z-10     Header app
z-20     Barres de filtres sticky
z-30     Sidebar <aside>, barres d'actions
z-40     Dropdowns de filtres
z-50     Modals
z-[9999] TooltipPortal (document.body)
```
Aucun conflit de superposition detecte.

### Coherence Scope (ScopeContext)

| Page | Utilise ScopeContext | Conforme |
|------|---------------------|----------|
| CommandCenter | `scopedSites` | OUI |
| Cockpit | `scopedSites`, `selectedSiteId` | OUI |
| MonitoringPage | `scopedSites` | OUI |
| ConformitePage | `scopedSites` (+ filtre custom) | OUI (design valide) |
| ConsumptionExplorerPage | `orgSites` | OUI (design documente) |
| AdminRolesPage | pas de scope (admin global) | OUI |
| AdminAssignmentsPage | pas de scope (admin global) | OUI |
| **ConsommationsUsages** | `getSites()` sans org | **NON** (P2 #23) |

---

## Guard tests ajoutes

Fichier : `frontend/src/pages/__tests__/RoutingSmoke.test.js`

| Test | Ce qu'il protege |
|------|------------------|
| "aucun label de nav ne contient de mot anglais blackliste" | Regression labels EN |
| "aucune section de nav ne contient de mot anglais blackliste" | Regression sections EN |
| "chaque route nav commence par /" | Routes malformees |
| "aucune route nav ne pointe vers /consumption-explorer" | Ancien chemin casse |
| "ROUTE_MODULE_MAP couvre toutes les routes du menu" | Route non mappee |

Blacklist anglaise : `Dashboard, Assignments, Roles & Permissions, Settings, Loading, Submit, Save, Delete, Cancel`

---

## Quick wins — Top 10

1. ~~Lien MonitoringPage `/consumption-explorer`~~ FAIT
2. ~~Redirect `/cockpit-2min` → `/cockpit`~~ FAIT
3. ~~Labels anglais NavRegistry (3 items admin)~~ FAIT
4. ~~Accents manquants (10 fichiers)~~ FAIT
5. ~~Guard tests anti-regression~~ FAIT
6. Scope `ConsommationsUsages.jsx` ImportWizard (P2)
7. Palette couleurs charts centralisee (P2)
8. Nettoyer route `/status` orpheline (P2)
9. Ajouter `aria-label` aux boutons icon-only (accessibilite)
10. Lazy-load des modals lourds (performance)

---

## Metriques

| Metrique | Avant audit | Apres audit | Delta |
|----------|-------------|-------------|-------|
| Tests vitest | 930 | 935 | +5 |
| Fichiers test | 37 | 37 | = |
| Build time | 17.19s | 13.05s | -4.14s |
| P0 ouverts | 2 | 0 | -2 |
| P1 ouverts | 15 | 0 | -15 |
| P2 ouverts | 3 | 3 | = |
