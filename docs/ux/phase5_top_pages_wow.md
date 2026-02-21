# Phase 5 — Top Pages WOW : Audit & Plan

**Sprint**: `sprint-wow-ux-ui-top-pages-v1`
**Date**: 2026-02-14
**Pages cibles**: Dashboard (/), Vue Executive (/cockpit), Alertes (/notifications)

---

## 1. Audit — Etat actuel

### 1.1 Dashboard — CommandCenter.jsx (318 lignes)
**Route**: `/` | **Fichier**: `frontend/src/pages/CommandCenter.jsx`

| Critere | Etat | Probleme |
|---------|------|----------|
| Donnees | Mock | `mockKpis`, `mockTodos`, `mockTopAnomalies` — aucun appel API reel |
| Couleurs | Excessives | KpiCard avec bg-blue/red/amber-600, TodoItem avec border-l-4 colores |
| Actions | Colorees | RecommendedActionCard avec bg-blue-50/amber-50/green-50 |
| Etats vides | Partiel | EmptyState pour 0 anomalies, mais pas pour erreur API |
| Accessibilite | Partiel | onClick sur div sans role=button (KPI wraps) |
| Scope | Non utilise | Lit `org` et `scopedSites` mais affiche uniquement des mocks |

**Verdict**: Structure correcte mais donnees fausses et trop de couleur.

### 1.2 Vue Executive — Cockpit.jsx (352 lignes)
**Route**: `/cockpit` | **Fichier**: `frontend/src/pages/Cockpit.jsx`

| Critere | Etat | Probleme |
|---------|------|----------|
| Donnees | Client-side | KPIs calcules sur `scopedSites` — pas de backend |
| Couleurs | Excessives | Gradient indigo→purple (Maturite), gradient blue→indigo (CTA) |
| KPI cards | 5 cards colorees | bg-blue/green/orange/red-600 + gradient card |
| Portefeuilles | Cards custom | Pas de composant reutilisable, Progress avec couleurs conditionnelles |
| Table sites | Bonne | Search, sort, pagination, expert mode — conserver |
| Error state | Absent | Aucun catch, aucun ErrorState |
| CTA | Gradient bar | "Rendre mon patrimoine actionnable" — trop agressif visuellement |

**Verdict**: Bonnes interactions (table, search, sort) mais design trop colore et CTA gradient.

### 1.3 Alertes — NotificationsPage.jsx (349 lignes)
**Route**: `/notifications` | **Fichier**: `frontend/src/pages/NotificationsPage.jsx`

| Critere | Etat | Probleme |
|---------|------|----------|
| Donnees | API reelle | `getNotificationsList`, `syncNotifications` — OK |
| Couleurs | Excessives | KpiCard rouge/ambre/bleu, severity pills colores |
| Triage | Absent | Pas de tabs All/New/Read/Dismissed — filtres dropdown |
| Detail | Absent | Clic sur alerte = rien, pas de Drawer |
| Bulk | Expert only | Checkboxes + "Ignorer N" — uniquement en mode expert |
| Bulk API | Sequentiel | `handleBulkDismiss` fait N requetes sequentielles |
| Search | Client-side | Filtre sur events deja charges — OK |
| Pagination | OK | Composant Pagination existant |
| Empty state | OK | EmptyState avec CTA conditionnel |

**Verdict**: Meilleure page des 3 (API reelle) mais manque triage tabs et detail drawer.

---

## 2. Design cible — Principes

1. **Couleurs neutres** — bg-gray-50/white/gray-100 pour les conteneurs. Couleur uniquement pour severity badges.
2. **KPI refactor** — Pas d'icone colore en bg-X-600. Valeur grande + label + badge severity discret.
3. **Progressive disclosure** — Detail dans Drawer, pas inline.
4. **Tous les etats** — loading (Skeleton), empty (EmptyState), error (ErrorState), partial.
5. **CTA explicite** — Bouton texte clair, pas de gradient bar.

---

## 3. Plan d'implementation

### Commit 1: MetricCard v2 + StatusDot (UI kit)
- `MetricCard`: neutral card, big value, label, optional trend arrow, optional severity dot
- `StatusDot`: tiny colored dot (ok/warn/crit/neutral) — remplace les gros badges colores

### Commit 2: Dashboard refactor
- Remplacer mocks par appel API scope-aware (ou au minimum utiliser scopedSites reels)
- 3 MetricCards neutres en haut (Sites, Conformite %, Risque EUR)
- Priority #1 action card (neutre, pas gradient)
- Ranked action list (numerotee, neutre)
- Top anomalies table (garde)
- Todo list (neutre, sans border-l colores)

### Commit 3: Vue Executive refactor
- Supprimer gradient cards (Maturite, CTA)
- 4 MetricCards neutres + Maturite en Progress ring
- Portefeuille tabs (Tabs component)
- Sites table (conserver, deja bonne)
- Error state

### Commit 4: Alertes refactor
- Triage tabs (Toutes / Nouvelles / Lues / Ignorees)
- Severity KPIs en MetricCard neutre avec StatusDot
- Detail Drawer sur clic ligne
- Bulk actions toujours visibles (pas expert-only)
- Bulk API parallel

### Commit 5: Tests + QA
- Tests unitaires pour nouveaux helpers
- Build 0 errors
- Vitest all pass
