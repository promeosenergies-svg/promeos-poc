---
title: Audit lecture-seule — Module "Centre d'Action" PROMEOS HELIOS
date: 2026-05-13
branch: claude/refonte-sol2
scope: Frontend + Backend + Modèle de données
mode: read-only (aucun fichier modifié)
auditeurs: 4 sub-agents en parallèle (frontend, backend, data-model, bug-hunt)
---

# AUDIT — Centre d'Action PROMEOS HELIOS

**Branche** : `claude/refonte-sol2` · **Date** : 2026-05-13 · **Mode** : lecture seule, aucun fichier modifié.

Le Centre d'Action est l'écran central HELIOS pour le Responsable Énergie : 2 onglets (**Anomalies** + **Plan d'actions**), c'est l'écran le plus exposé en démo prospect (courtier, DG, CFO).

---

## TL;DR — Synthèse cardinale

**Score module global : 58/100**

| Force | Faiblesse |
|---|---|
| `AnomaliesPage` (refonte Sprint 1.9bis + Sol v1.1) propre | 6 vocabulaires de statuts concurrents non réconciliés |
| `ActionDetailDrawer` riche (5 onglets) | Bug `false_positive → done` masqué côté UI (= "Terminée" affichée pour faux positifs) |
| `ActionCenterSlideOver` (cloche) soigné, polling 60s | ~1 469 LoC mortes (~20 % du module) |
| `ROISummaryBar` pro côté backend | 2 modèles parallèles `ActionItem` ↔ `ActionPlanItem` non fusionnés |
| Vue Semaine pertinente | Bug `TypeError` latent sur clôture OPERAT (`d` référencé avant déclaration) |
| | **Fuite org-scoping massive sur `/api/action-center/*`** (sauf `/issues` et `/summary`) |
| | Briefing 500 — top hypothèse : migration DB manquante |

**4 corrections < 4 h** (QW1→QW5 ci-dessous) suffisent à passer 58 → 78. Le reste (consolidation `ActionItem`/`ActionPlanItem`) est du moyen-terme.

---

## 1. Inventaire fonctionnel

### 1.1 Routes frontend → composant

| Path | Composant | Statut |
|---|---|---|
| `/anomalies` | `AnomaliesPage` (lazy) | **CANONIQUE** — hub Centre d'actions, 2 onglets |
| `/anomalies?tab=actions` | `AnomaliesPage` → embarque `<ActionsPageInline bare />` | onglet Plan d'actions |
| `/actions` | `ActionsPage` (lazy) | route directe avec PageShell |
| `/actions/new` | `ActionsPage autoCreate` | ouvre drawer création |
| `/actions/:actionId` | `ActionsPage` | ouvre `ActionDetailDrawer` sur l'ID |
| `/action-center` | `<Navigate to="/anomalies" replace />` | redirige (`App.jsx:300-307`) |
| `/action-plan` | redirect → `/anomalies` (`routes/legacyRedirects.js:34`) | legacy |
| `/conformite/tertiaire/anomalies` | `TertiaireAnomaliesPage` | hors scope (cockpit conformité) |

Sidebar/badge cloche : `ActionCenterSlideOver` rendu globalement par `AppShell.jsx:409` + cloche `computeActionCenterBadge`.

### 1.2 Composants en production (frontend)

| Fichier | Rôle |
|---|---|
| `pages/AnomaliesPage.jsx` (835 L) | Hub Centre — onglets Anomalies / Plan d'actions |
| `pages/ActionsPage.jsx` (1 579 L) | Plan d'actions — table/kanban/semaine, filtres, bulk, KPI |
| `pages/useAnomalyFilters.js` | Hook filtres URL+localStorage |
| `pages/anomalyEvidence.js` | `buildAnomalyEvidence` pour drawer "Pourquoi ?" |
| `components/ActionDetailDrawer.jsx` (1 327 L) | Drawer 5 onglets (Détail/Impact/Pièces/Comm./Hist.) |
| `components/CreateActionDrawer.jsx` | Drawer création action |
| `components/ActionCenterSlideOver.jsx` | Slide-over global LEDGER (cloche header) |
| `components/SiteAnomalyPanel.jsx` | Panneau anomalies dans drawer Site |
| `components/TabActionsSite.jsx` | Onglet Actions dans Site360 |
| `contexts/ActionDrawerContext.jsx` | Provider centralisé pour ouvrir le drawer |
| `services/api/actions.js` | Wrappers REST |
| `models/actionProofLinkModel.js` | Helpers OPERAT proof link |

### 1.3 DEAD CODE / orphelins (frontend) — ~1 469 LoC

| Fichier | Statut | Évidence |
|---|---|---|
| `pages/ActionCenterPage.jsx` (378 L) | **MORT** | Aucun import. Remplacé par AnomaliesPage. Contient `console.error` (L98, 107, 116) |
| `pages/ActionPlan.jsx` (299 L) | **MORT** | Aucun import. Utilise `fetch()` brut au lieu de wrapper api. Path `/action-plan` redirigé |
| `components/ActionDetailPanel.jsx` (203 L) | **MORT** | Importé uniquement par `ActionCenterPage` (mort) |
| `components/CreateActionModal.jsx` | **MORT** | Aucun import prod (tests source-guards vérifient son absence) |
| `components/AnomalyActionModal.jsx` | **MORT** | Aucun import prod (V92 migration) |
| `mocks/actions.js` (266 L) | **MORT** | Aucun import. `getActionsByStatus` exporté mais jamais consommé |
| `services/anomalyActions.js` (103 L) | **MORT EN PROD** | Importé uniquement par `AnomalyActionModal` (mort). Persiste dans `localStorage` clé `promeos_anomaly_actions` — données fantômes potentielles |

### 1.4 Inventaire endpoints backend (extrait)

#### `routes/pages_briefing.py` (préfixe `/api/pages`)

| Method | Path | Service | Statut |
|---|---|---|---|
| GET | `/api/pages/{page_key}/briefing` | `narrative_generator.generate_page_narrative` | ✅ ACTIF (consommé par `AnomaliesPage.jsx:101` + 7 autres pages) — **mais renvoie 500, cf §4** |

#### `routes/action_center.py` (préfixe `/api/action-center`)

37 endpoints. Tous actifs frontend, sauf :
- ⚠️ ORPHELIN : `POST /api/action-center/actions/{id}/override-priority`
- 🎭 MOCK : `GET /api/action-center/views` (dict en mémoire `action_center.py:13-18`, jamais persisté)

#### `routes/actions.py` (préfixe `/api/actions`)

20 endpoints. Tous actifs.

#### `routes/action_templates.py`

3 endpoints. Orphelin : `GET /api/action-templates/{code}` (aucun callsite FE).

#### Anomalies billing (legacy)

- 🚨 LEGACY mais critique : `GET /api/billing/anomalies-scoped` (`billing.py:1526`) — appelé par `AnomaliesPage.jsx:153`. MEMORY signale Phase L18.2 cardinal — re-câblé pour unifier `BillingInsight` (legacy) + `BillAnomaly` R19→R31.

---

## 2. Composants par onglet

### Onglet "Anomalies" (`AnomaliesPage`)

| Brique | Fichier:line |
|---|---|
| Header éditorial Sol §5 | `AnomaliesPage.jsx:415-427` |
| Tabs | `:438-443` |
| Toolbar (search + 3 QuickSelect) | `:466-538` |
| ActiveFiltersBar | `:541-571` |
| Liste cards anomalies | `:603-787` |
| EvidenceDrawer "Pourquoi ?" | `:800-804` |
| **Pas de pagination** | — (max 20 sites × N anomalies) |
| **Pas de stats KPI cards** | supprimées (`:459-463`) |

### Onglet "Plan d'actions" (`ActionsPage`)

| Brique | Fichier:line |
|---|---|
| Bandeau ROI | `:970` (`<ROISummaryBar />`, fetch `/actions/roi_summary`) |
| Barre progression | `:973-1014` |
| Quick views (3 chips) | `:1017-1054` |
| 5 stats cards cliquables | `:1057-1124` |
| Filtres (Tabs statut + Select type) | `:1127-1146` |
| Toolbar (search + group-by + view toggle) | `:1149-1197` |
| **Vue "table"** (par défaut, pagination 15/page) | `:1318-1442` |
| **Vue "kanban"** (drag-and-drop natif) | `:1294-1304` → `KanbanBoard:205-313` |
| **Vue "semaine"** (overdue/today/week/later) | `:1286-1293` → `WeekView:449-548` |
| **Vue "groupée"** | `:1305-1316` → `GroupedTableView:316-446` |
| Sticky bulk bar | `:1444-1483` |
| ActionDetailDrawer | `:1531-1538` |

⚠️ **PAS DE VUE CALENDRIER** au sens strict — la "vue Semaine" est une liste groupée par bucket temporel, pas un calendrier mensuel/hebdomadaire. La spec audit mentionne "calendrier" mais elle n'existe pas.

---

## 3. Audit qualité (notes /100)

### 3.1 Cohérence sémantique des statuts — **42/100**

**6 sources de vérité concurrentes** :

1. **SoT prétendue** : `domain/compliance/complianceLabels.fr.js:83` — `ACTION_STATUS_LABELS = { backlog, planned, in_progress, done }` (4 statuts FE).
2. **Mapping BE→FE dupliqué** :
   - `pages/ActionsPage.jsx:74-80` — `STATUS_TO_FE = { open→backlog, in_progress, done, blocked→planned, false_positive→done }`
   - `components/ActionDetailDrawer.jsx:61-67` — copié-collé identique
3. **STATUS_WORKFLOW** dans `ActionDetailDrawer.jsx:94-100` expose 5 statuts BE (open, in_progress, blocked, done, **false_positive**)
4. **TabActionsSite.jsx:14-20** — labels différents : "Ouverte" vs "À planifier", "Bloquée" vs "Planifiée"
5. **services/anomalyActions.js:18-22** — `ACTION_STATUS_LABEL` avec 3 statuts (`todo`/`in_progress`/`resolved`) — **encore une autre nomenclature**, mort en prod
6. **ActionCenterPage.jsx:26-32** (mort) — 5 autres labels (`open/in_progress/resolved/dismissed/reopened`)

**Backend** :
- `ActionStatus` enum DB (`enums.py:400-407`) : `open / in_progress / done / blocked / false_positive`
- `ActionPlanItem.status` String libre : `open / in_progress / resolved / dismissed / reopened` ← **incompatible avec ci-dessus**

**Conséquence** : Le label "Abandonnée" demandé dans la mission **n'existe nulle part**. Le seul équivalent est `false_positive` ou `dismissed` (modèle parallèle). Les développeurs ont hésité.

### 3.2 Sévérité (anomalies) vs Priorité (actions) — **48/100**

**8+ enums sévérité distinctes** dans le repo (`BillAnomalySeverity`, `Severity`, `AnomalySeverity`, `SeveriteAlerte`, `AlertSeverity`, `NotificationSeverity`, `QualityRuleSeverity`, `DataQualityIssueSeverity`...).

**4 mappings sévérité→priorité parallèles** :

| Service | Mapping | Échelle sortie |
|---|---|---|
| `action_hub_service.compute_priority:57` | `{critical:1, high:2, medium:3, low:4}` + bonus gain/deadline | Integer 1-5 |
| `action_workflow_service.SEVERITY_TO_PRIORITY:11` | `{critical:critical, high:high, medium:medium, low:low, info:low}` | String |
| `bill_intelligence/priority.severity_to_priority_score` | `{CRITICAL:90, HIGH:70, MEDIUM:50, LOW:30}` | Score 0-100 |
| `bill_intelligence/r_codes_registry.BA_SEVERITY_UI_MAP:47` | `{critical:CRITICAL, warning:HIGH, info:MEDIUM}` | **élévation systématique d'un cran** ⚠️ |

`AnomaliesPage` : `severity ∈ {CRITICAL, HIGH, MEDIUM, LOW}` (uppercase) — `:63, :67`.
`ActionsPage` : `priorite ∈ {critical, high, medium, low}` (lowercase, recodé via `PRIO_TO_FE:87`).
`ActionDetailDrawer` : `priority` numérique 1-5 avec `PRIORITY_LABEL:77-83`.

**Pas de mapping documenté `severity → priority`.** Le passage anomalie → action prefill `prefill: { titre, type: 'anomalie' }` (`:716`) **ne transmet PAS la sévérité** — `CreateActionDrawer:79` met `priorite: 'high'` par défaut.

### 3.3 Indicateurs financiers — **55/100**

| Indicateur | DB | API | FE | Note |
|---|---|---|---|---|
| **Estimé** | `ActionItem.estimated_gain_eur` | `estimated_gain_eur` | `impact_eur` (mappé `\|\| 0`) | mock `actions.js` utilise `impact_eur` qui n'existe pas en BE |
| **Réalisé** | `ActionItem.realized_gain_eur` | exposé | Drawer édition | NULL très fréquent (seed seulement si `status==DONE`) |
| **Impact total** | non stocké | `/actions/roi_summary` (calcul BE) + recalc FE | calc inline `:752` | drift garanti si filtres divergent |
| **ROI** | non stocké | non exposé | dérivé Drawer `:1067-1078` | NULL si l'un des deux NULL |
| **Gain CO₂** | `ActionItem.co2e_savings_est_kg` | `co2e_savings_est_kg` | `co2e_kg` (mappé `\|\| 0`) | **NULL systématique en démo** : seed `gen_actions.py` ne le set jamais |

⚠️ `ActionsPage.jsx:752` `total_impact: enrichedActions.reduce((s, a) => s + a.impact_eur, 0)` somme **TOUS** les statuts (incl. `done`, `false_positive`) → "x € d'impact total" surévalué de la part déjà capturée.

⚠️ Anomalies : `business_impact.estimated_risk_eur` côté BE (sommé front pour KPI `risque` `AnomaliesPage:266`) — **base différente de `impact_eur` côté actions**. Le narratif "Voir N actions = X € récupérables" mélange risque évité et gain estimé.

### 3.4 Traçabilité Anomalie ↔ Action — **60/100**

**Pas de FK directe `action.anomaly_id`.** Le lien passe par `AnomalyActionLink` (`action_detail_models.py:99-141`) :

| Champ | Type | Note |
|---|---|---|
| `anomaly_source` | String(50) | string libre "patrimoine\|billing\|monitoring" |
| `anomaly_ref` | String(200) | code anomaly OU insight ID — **typage hétéroclite** |
| `site_id` | FK sites | |
| `action_id` | FK action_items | cascade implicite SQLite |

`UniqueConstraint(anomaly_source, anomaly_ref, site_id, action_id)`.

**Bidirectionnel** :
- **Anomalie → Action** : `getAnomalyStatuses` renvoie `linked_actions: [...]`. Bouton "Voir action(s)" navigue `/anomalies?tab=actions` (`AnomaliesPage:681`) **mais ne pousse PAS le filtre `linked_anomaly`** → l'utilisateur arrive sur la liste complète. **Bug B4**.
- **Action → Anomalie** : `ActionsPage` lit `?linked_anomaly=` (`:563, :681-688`) — **mais aucun bouton dans l'UI ne génère cette URL**. Filtrage utilisable seulement via deep-link manuel.
- Pas de bouton "Aller à l'anomalie source" dans `ActionDetailDrawer` (l'unique deep-link `buildSourceDeepLink:520-532` pointe vers la fiche conformité/billing, pas l'anomalie d'origine).

🚨 **Pipeline `sync_actions` ne crée jamais de `AnomalyActionLink`** : seules les actions créées explicitement depuis l'UI Anomalies ont un lien tracé. Les actions auto-générées par compliance/consumption/billing/purchase sont **orphelines de toute traçabilité anomalie**. Le différenciateur produit "système de contrôle énergétique" (CLAUDE.md vision v1.3) est partiellement non-réalisé en données.

### 3.5 Robustesse — **58/100**

| Aspect | AnomaliesPage | ActionsPage |
|---|---|---|
| `loading` skeleton | OK (`:581-586`) | **CASSÉ** — `_loading` underscored (`:558`), pas de skeleton table |
| `error` banner | OK (`:574-578`) | OK (`<ErrorState />:967`) |
| Empty state global | OK (`:587-601`) | OK avec branches contextuelles |
| Toast erreurs | partiel | OK (sync, PDF, status, assign) |
| Error boundary | absente | absente |
| Optimistic update | aucun | partiel |

### 3.6 Performance — **40/100**

- ⚠️ **AnomaliesPage** : limite arbitraire `MAX_SITES = 20` (`:61`) — au-delà, anomalies invisibles. N requêtes parallèles via `Promise.all:148-156`. **Bug B5** : risque démo Marie DAF > 20 sites.
- **Pas de pagination ni virtualization** sur la liste anomalies — 105 anomalies × 5 wrappers React = ~500 nodes monté d'un coup.
- **ActionsPage** : pagination 15/page sur table OK, mais kanban/week/grouped affichent TOUT.
- `AnomaliesPage` refetch sur chaque dismiss — pourrait amplifier.
- Memos OK sur `filtered`, `kpis`, `siteName`, `enrichedActions`, `groups`. Pas de `React.memo` sur lignes/cards.

---

## 4. Bugs / incohérences

### 🚨 Bloquant-démo (P0)

#### **B1 — `ActionDetailDrawer` : `d` référencé avant déclaration** ⭐⭐⭐
**Fichier** : `ActionDetailDrawer.jsx:307-329` (`d` défini au `:431`)
**Symptôme** : En cliquant "Terminer" sur une action OPERAT/`evidence_required` → `TypeError: Cannot read properties of undefined`.
**Cause** : `handleStatusChange` utilise `isOperatAction(d)` et `d.evidence_required` mais `const d = detail || action._backend || {}` est déclaré ligne 431, après le handler.

#### **B2 — Mapping inverse `false_positive → done`** ⭐⭐⭐
**Fichier** : `ActionsPage.jsx:79` + `ActionDetailDrawer.jsx:66`
**Symptôme** : Actions classées "Faux positif" côté backend s'affichent "Terminée" (vert, succès) côté front. Compteur `stats.done` (`:751`), barre de progression (`:979-987`), tab Kanban "Terminée" (`:1084-1088`), export CSV — tout est gonflé.
**Cause** : `STATUS_TO_FE = { ..., false_positive: 'done' }`. Le label "Faux positif" existe dans `complianceLabels.fr.js:78` mais n'est pas utilisé.
**Confiance** : haute (root cause exacte).

#### **B3 — Endpoint `Briefing` renvoie 500** ⭐⭐⭐
**Endpoint** : `GET /api/pages/{page_key}/briefing` (`pages_briefing.py:49`)
**Confiance** : moyenne — non confirmé sans repro runtime, top-3 hypothèses ranked :

1. 🥇 **H6 — Migration manquante** : 5 fichiers `.original-autogenerate` en suspens (cf git status). Colonnes `closed_at` / `evidence_required` / `closure_justification` potentiellement absentes. Vérifier `sqlite3 backend/data/promeos.db ".schema action_items"`.
2. 🥈 **H3 — Status hors enum** : `routes/actions.py:432` documente `?status=backlog,planned,in_progress` mais l'enum BE (`enums.py:400-407`) ne contient ni `backlog` ni `planned` ni `reopened`. Une valeur corrompue dans `action_items.status` lèverait `LookupError` à l'hydratation `_build_anomalies:2658`.
3. 🥉 **H_extra — `narrative_generator.py:756`** : `primary_push["clause"]` accès dict non-défensif (KeyError si `compose_primary_push` retourne dict sans cette clé).

**Action recommandée** : `tail` des logs `promeos.narrative` pendant `curl http://localhost:8001/api/pages/cockpit_daily/briefing?persona=daily` pour identifier le builder fautif en 30 secondes.

#### **B4 — CTA "Voir action(s)" déroute** ⭐⭐
**Fichier** : `AnomaliesPage.jsx:681`
**Symptôme** : Navigue `/anomalies?tab=actions` sans push `linked_anomaly=…` → l'utilisateur arrive sur la liste complète, pas sur l'action liée.
**Le filtre existe** dans `ActionsPage` (`:563, :681-688`) mais aucun appelant ne le fournit.

#### **B5 — `MAX_SITES = 20` silencieusement coupant** ⭐⭐
**Fichier** : `AnomaliesPage.jsx:143, 791-792`
**Symptôme** : Si l'org a 21+ sites, anomalies des sites #21+ invisibles. Footer mentionne ce fait mais c'est noyé.
**Risque** : démo Marie DAF (tertiaire multi-sites > 20).

---

### ⚠️ Gênant (P1)

| # | Fichier:line | Bug |
|---|---|---|
| G1 | `ActionsPage.jsx:752` | `total_impact` somme TOUS les statuts (incl. `done`, `false_positive`) ⇒ surévalué |
| G2 | `ActionsPage.jsx:1387` | Colonne "CO₂e" : quasi systématiquement `—` (seed `gen_actions.py:196-211` ne renseigne JAMAIS `co2e_savings_est_kg` ni `owner`) |
| G3 | `ActionsPage.jsx:281,283` | Owner systématiquement `Non assigné` (même seed). Colonne morte |
| G4 | `SiteAnomalyPanel.jsx:55` vs `AnomaliesPage.jsx:76` | DECRET_TERTIAIRE rendu **purple** dans le panel site et **slate neutre** dans le centre d'actions ⇒ même framework, 2 couleurs |
| G5 | `pages/ActionPlan.jsx:46` | Page morte mais utilise `fetch('/api/...')` brut au lieu de wrapper `api.get` ⇒ pas d'org-scoping/auth header |
| G6 | `services/anomalyActions.js` | Persiste actions en `localStorage` clé `promeos_anomaly_actions` — données fantômes accumulées |
| G7 | `ActionsPage.jsx:62` | `ACTION_STATUS_LABELS` exclut `blocked` du `BULK_STATUS_OPTIONS` ⇒ impossible de bloquer en bulk |
| G8 | `AnomaliesPage.jsx:153,176` | `getBillingAnomaliesScoped()` fetch global puis filtre côté front ⇒ anomalies billing avec `site_id=null` exclues silencieusement |
| G9 | `AnomaliesPage.jsx:609` | clé React `${anom.site_id}-${anom.code}-${idx}` inclut `idx` ⇒ casse memoization stable |
| G10 | `AnomaliesPage.jsx:271-288` | Pas de dédup PDL × règle × dates proches ⇒ N cards distinctes pour la même anomalie |

#### Anomalies dupliquées non agrégées (G10 détaillé)

Plusieurs sources de duplication coexistent :
1. **BillAnomaly (R19→R31)** : `UniqueConstraint(invoice_id, code)` (`bill_anomaly.py:39`) MAIS pipeline `detect_anomalies_for_invoice` (`anomaly_detector.py:1705-1859`) appelle `db.add(...)` sans pré-check. `IntegrityError` avalée silencieusement → données stale.
2. **R20 (capacity_variance)** : retourne 0..N anomalies, 1 par poste tarifaire. Pas de dédoublonnage par poste — UniqueConstraint tue les inserts → utilisateur voit moins d'anomalies que prévu.
3. **`patrimoine_anomalies`** : `_rule_meter_no_delivery_point` (`patrimoine_anomalies.py:172-193`) émet **1 anomalie par compteur** sans agrégation. 5 compteurs sans PRM dans le même site = 5 anomalies au lieu d'1.
4. **Pas de dédup côté FE** : `AnomaliesPage.jsx:271-288`.

#### Compteur sidebar "4" vs page liste 35 (badge incohérent)

**Confiance** : haute. Les 2 chiffres ne sont pas calculés sur la même base :
- **Sidebar badge** : `GET /api/v1/navigation/badges` → `_count_action_center_open` → `get_action_center_issues(db, org_id).total` (`navigation_badges_service.py:123-126`). Source = SITES dérivés temps réel.
- **Page liste** : `GET /api/actions/list` → `db.query(ActionItem).filter(ActionItem.org_id == oid)` SANS filtre status par défaut, jusqu'à 500 actions (`actions.py:406-452`).

Datasets totalement disjoints (issues = snapshot patrimoine ; ActionItem = workflow persisté).

**Fix** : Option A (simple) — badge utilise `getActionsSummary()` (`/actions/summary`) `counts.open + counts.in_progress`. Option B — ajouter `?status=open,in_progress` au call FE de la page liste.

---

### 🚨 Sécurité — Org-scoping (P0 sécu)

| Endpoint | Statut |
|---|---|
| `GET /api/pages/{page_key}/briefing` | ✅ scoped |
| `POST/GET /api/actions` (sync, list, summary, export, batches) | ✅ scoped |
| `PATCH /api/actions/{id}` | ⚠️ **PAS DE SCOPING** : `db.query(ActionItem).filter(id == action_id).first()` (`actions.py:517`) — n'importe quel user peut PATCHer n'importe quelle action de n'importe quelle org |
| `GET /api/actions/{id}` + sous-resources | ⚠️ idem |
| `POST /api/actions/anomaly-dismiss` | ⚠️ pas de scoping |
| `POST /api/actions/anomaly-statuses` | ⚠️ idem |
| **Tous les `/api/action-center/*` (sauf `issues`/`summary`)** | 🚨 **AUCUN ORG-SCOPING** : `list_actions(db, site_id=None, ...)` query `db.query(ActionPlanItem).all()` sans filtre org → **fuite cross-org garantie** |
| `GET /api/action-center/management-summary` | 🚨 idem |
| `GET /api/action-center/executive-summary` | 🚨 idem |
| `POST /api/action-center/actions/bulk/*` | 🚨 idem — bulk update sans vérification d'org |

**Doctrine PROMEOS règle non-négociable #2 violée. Risque RGPD si plusieurs orgs sur même DB.**

---

### 🎨 Cosmétique (P2)

- C1 `AnomaliesPage.jsx:614-651` : badges site/sev/framework wrap sur 2 lignes en mobile
- C2 `ActionsPage.jsx:1284-1442` : pagination ne reset pas au changement de viewMode
- C3 `ActionsPage.jsx:1057-1124` : 5 stats cards en `grid-cols-5` hard-coded — overflow tablette < 1024px
- C4 `ActionDetailDrawer.jsx:55` : `_STATUS_TO_BE` underscored = inutilisé → dead variable
- C5 Sticky bulk bar (`ActionsPage:1444`) : `bottom-4` sans `safe-area-inset-bottom` → masquée iOS

---

## 5. Modèle de données — synthèse cardinale

### 5.1 Cinq modèles d'anomalies, cinq modèles d'actions

**Anomalies** :
- `BillAnomaly` (`bill_anomaly.py:28`) — table `bill_anomaly`, R19→R31 facturation, persisté
- `Anomaly` (KB) (`energy_models.py:287`) — table `anomaly` singulier, KB analytique
- `Alerte` (`alerte.py:12`) — table `alertes` FR pluriel, modèle ancien
- `compute_site_anomalies` — in-memory, 9 règles patrimoine, jamais persisté
- `MonitoringAlert` (`energy_models.py:492`) — table `monitoring_alerts`

**Actions** :
- `ActionItem` (`action_item.py:27`) — table `action_items`, **canonique post-Sprint 10/V5.0**
- `ActionPlanItem` (`action_plan_item.py:8`) — table `action_plan_items`, **DOUBLON Sprint 13** (legacy)
- `ActionEvent` (`action_detail_models.py:27`) — audit trail pour `ActionItem`
- `ActionPlanEvent` (`action_event.py:8`) — audit trail pour `ActionPlanItem` ⚠️ **collision de nom**
- `ActionTemplate` (`action_template.py:11`) — bibliothèque 20 modèles V113

### 5.2 Discordance enums statuts

| Enum | Valeurs | Source |
|---|---|---|
| `ActionStatus` | `open / in_progress / done / blocked / false_positive` | `enums.py:400-407` (SAEnum DB sur `action_items.status`) |
| `ActionPlanItem.status` String | `open / in_progress / resolved / dismissed / reopened` | Column String(30) sur `action_plan_items.status` |

→ `ActionItem` n'a pas `resolved`/`reopened`/`dismissed` (a `done`/`blocked`/`false_positive`).
→ `ActionPlanItem` n'a pas `done`/`blocked`/`false_positive` (a `resolved`/`reopened`/`dismissed`).
→ FE `actions.js:432` mentionne `backlog,planned,in_progress` qui ne sont dans **aucun** des deux enums.

### 5.3 Champs financiers — gaps en démo

- ❌ `co2e_savings_est_kg` — seed `gen_actions.py:196-211` ne le set jamais
- ❌ `owner` — idem
- ❌ `realized_gain_eur` — set uniquement si `status==DONE` au seed
- ❌ `category` — jamais setté
- ❌ `description` (distinct de `rationale`) — jamais setté
- ❌ `closure_justification` — uniquement via Drawer V49 OPERAT

### 5.4 Bugs sémantiques cardinaux

1. **Mock `actions.js` schéma divergent du backend** : utilise `titre`/`priorite`/`statut` (FR) + champs inventés (`effort`) qui n'existent ni en DB ni en API.
2. **`AnomalyStatus` enum** (`enums.py:888`) **défini mais sans table** — calculé runtime depuis `AnomalyActionLink + AnomalyDismissal + Action.status`.
3. **`anomaly_ref` typage** : Pour `BillAnomaly`, le FE utilise `a.code` (`R20`) ou `a.id` selon code (`AnomaliesPage.jsx:275, 321`) — `UniqueConstraint` peut accepter deux liens pour la même anomalie sous deux refs distinctes.
4. **`mark_action_done` n'est pas appelé pour `false_positive`** → `closed_at` reste NULL → KPI "actions fermées par mois" faussé.
5. **Désync sémantique briefing↔table** : narratif compte `ActionItem`, page affiche anomalies brutes patrimoine+billing. Marie verra "5 anomalies actives" puis dans la table "12 lignes". **Désync cardinale.**
6. **Notes "campaign sites" hackées** : `routes/actions.py:178-184` encode `campaign_sites` en préfixe `##CAMPAIGN:` du champ `notes`. Si user édite `notes`, casse le parsing JSON.
7. **Saved Views en mémoire** : `action_center.py:13-18` dict en mémoire jamais persisté → toute restart perd l'état utilisateur. Marqueur `# in-memory for POC` mais exposé en endpoint actif.

---

## 6. Cohérence services backend

### 6.1 Trois services de statut/clôture chevauchent

| Service | Modèle visé | Décision statut |
|---|---|---|
| `action_status_service.mark_action_done:50` | `ActionItem` | Force `status=DONE`, set `closed_at` |
| `action_close_rules.check_closable:46` | `ActionItem` | Évalue (preuve, justification ≥10 chars, OPERAT) → renvoie `{closable, code, reason}`. Ne mute pas |
| `action_workflow_service.resolve_action:101` | `ActionPlanItem` | Set `status="resolved"` + `resolved_at` ; bloque si `evidence_required AND NOT evidence_received` |

**Chevauchement** : `mark_action_done` + `check_closable` opèrent sur `ActionItem` ; `resolve_action` opère sur `ActionPlanItem`. **Pas de conflit direct mais double pipeline.** Le frontend appelle les deux (cf `actions.js:97` PATCH `/action-center/{id}` puis `actions.js:19` PATCH `/actions/{id}`).

`action_workflow_service.resolve_action:106-107` retourne `None` silencieusement si evidence manquante (handler `action_center.py:489` lève alors un `400` générique sans code structuré).

### 6.2 Combien de moteurs d'anomalies actifs ?

5 détecteurs trouvés :
1. `services/patrimoine_anomalies.compute_site_anomalies:336` — règles patrimoniales (sortie dict, pas persisté)
2. `services/bill_intelligence/anomaly_detector.detect_anomalies_for_invoice:1705` — R19→R31, persiste `BillAnomaly` (Phase L17.1 désormais câblé)
3. `services/action_center_service.collect_compliance_issues / collect_billing_issues / collect_patrimoine_issues:12,61,113` — anomalies dérivées de la complétude site
4. `services/event_bus/detectors/_protocol.EventDetector:33` — Sprint 2 vague C
5. KB `Anomaly` "consumption" — référencée par MEMORY mais pas trouvée dans services scannés

**Aucune agrégation backend.** Le frontend `AnomaliesPage.jsx:148` agrège côté FE `Promise.all([getPatrimoineAnomalies, getBillingAnomaliesScoped])`.

### 6.3 Try/except trop larges (masquent erreurs)

- `actions.py:184` `_serialize_action` parse `notes` JSON — `except Exception: pass` masque tout
- `actions.py:257` `_mark_reco_in_progress` `except Exception: pass`
- `actions.py:1029` `get_action_proofs` `except Exception: return {"docs": []}` masque toute erreur KBStore
- `action_close_rules.py:39` `_count_valid_proofs` `except Exception: return 0`
- `narrative_generator.py:266-292` `_resolve_org_typology_value` triple try/except

---

## 7. Tests — Coverage du module

| Module | Tests |
|---|---|
| `routes/pages_briefing.py` | **Aucun test direct trouvé** |
| `_build_anomalies` | **AUCUN TEST** (grep → 0 résultats) |
| `generate_page_narrative` | testé `cockpit_daily` + `__unknown__`. Pas `anomalies` |
| `routes/action_center.py` | tests partiels |
| `routes/actions.py` | tests partiels |
| `services/action_workflow_service.py` | tests partiels |
| `services/action_close_rules.py` | tests présumés (V49) |

### Lacunes critiques

1. **Briefing `anomalies` non testé bout-en-bout** → toute régression sur `_build_anomalies` ne surface que via UI 500.
2. **Aucun test cross-modèle ActionItem ↔ ActionPlanItem** — la cohabitation n'est pas vérifiée.
3. **Aucun test source-guard org-scoping `/api/action-center/*`** — la fuite §6 ne sera détectée que par audit manuel.
4. **Aucun test mapping statuts FE↔BE** — désync `backlog/planned` vs enum non tracée.

---

## 8. Dette de design (par vue)

| Vue | Statut |
|---|---|
| AnomaliesPage — onglet Anomalies (liste) | ✅ **demo-ready** (refonte Sol §6.2 propre, tokens warm OK) |
| AnomaliesPage — onglet Plan d'actions (table par défaut) | ⚠️ **retouche avant pilote** (skeleton manquant + total_impact incorrect) |
| ActionsPage — vue Kanban | ✅ **demo-ready** mais drag manuel non testable au clavier (a11y) |
| ActionsPage — vue Semaine (Runbook) | ✅ **demo-ready** (groupage clair, "En retard" rouge utile) |
| ActionsPage — vue groupée | ⚠️ **retouche** : sums correctes mais sort alphabétique sur clés FR ne place pas "Critique" en tête |
| ActionDetailDrawer — Détail tab | ⚠️ **retouche** (B1 bloquant, sinon UI riche) |
| ActionDetailDrawer — Impact tab | ✅ **demo-ready** (édition realized inline élégante) |
| ActionDetailDrawer — Pièces / Comments / History | ✅ **demo-ready** |
| ActionCenterSlideOver (cloche header) | ✅ **demo-ready** (LEDGER soigné, polling 60s) |
| `ActionCenterPage` / `ActionPlan` / `ActionDetailPanel` / `CreateActionModal` / `AnomalyActionModal` / `mocks/actions` / `services/anomalyActions` | ❌ **refonte → suppression** (~1 469 LoC mortes) |
| TabActionsSite (Site360) | ⚠️ **retouche** : labels statuts ≠ ceux du Plan d'actions ("Ouverte" vs "À planifier") |
| SiteAnomalyPanel | ⚠️ **retouche** : palette divergente du centre |

---

## 9. Quick wins (5 corrections < 2 h, gros impact démo)

| # | Action | Fichier:line | ETA | Impact |
|---|---|---|---|---|
| **QW1** | **Fix B1** — déplacer `const d = detail \|\| action._backend \|\| {};` AVANT `handleStatusChange` (top du composant). Sans ce fix, le bouton "Terminer" plante sur action OPERAT/evidence_required en démo | `ActionDetailDrawer.jsx:307` | 30 min | ⭐⭐⭐ |
| **QW2** | **Fix B2 + B3-skeleton** — (a) supprimer le préfixe `_` sur `loading`, ajouter `<SkeletonTable rows={6}/>` quand `loading && !error` ; (b) remplacer `false_positive: 'done'` par `false_positive: 'dismissed'` (ou `'false_positive'`) + ajouter label "Faux positif" au lieu de mapper silencieusement | `ActionsPage.jsx:79, 558, 1318` + `complianceLabels.fr.js:83` | 60 min | ⭐⭐⭐ |
| **QW3** | **Wire B4** — push `linked_anomaly=${getAnomalyKey(anom)}` dans `AnomaliesPage:681` ; ajouter bouton "Voir l'anomalie source" dans `ActionDetailDrawer` si `_backend.anomaly_links?.length > 0` | `AnomaliesPage.jsx:681` + `ActionDetailDrawer.jsx:534` | 45 min | ⭐⭐⭐ |
| **QW4** | **Suppression dead code** — `rm` 7 fichiers (~1 469 LoC). Vérifier `nav_v7_parity.test.js` ne dépend plus de `ActionCenterPage` | divers | 60 min | ⭐⭐ |
| **QW5** | **Fix G1 + G2 + G3 (seed)** — (a) `total_impact` filtrer `statut !== 'done' && statut !== 'false_positive'` ; (b) seed `gen_actions.py:196-211` ajouter 2 lignes `owner=rng.choice([...])` + `co2e_savings_est_kg=round(estimated_gain * 4.5)` | `ActionsPage.jsx:752` + `gen_actions.py:196-211` | 45 min | ⭐⭐ |

**Total : ~4 h** pour passer 58 → 78.

---

## 10. Briefing 500 — investigation prioritaire

Le 500 du Briefing est le **bug le plus visible en démo** (cassé sur la page d'entrée du Centre d'Action). Trois hypothèses ranked :

1. 🥇 **Migration manquante** (5 fichiers `.original-autogenerate` en suspens). Vérifier d'abord `sqlite3 backend/data/promeos.db ".schema action_items"` et comparer avec `models/action_item.py:27-148`.
2. 🥈 **Status hors enum** dans `action_items.status` (e.g. `"backlog"`, `"reopened"` glissée par script ou seed) → `LookupError` à hydratation.
3. 🥉 **`primary_push["clause"]` accès dict non-défensif** ligne `narrative_generator.py:756`.

**Action recommandée** (30 secondes) :
```bash
tail -f backend/logs/*.log &
curl http://localhost:8001/api/pages/anomalies/briefing?persona=daily -H "X-Org-Id: 1"
curl http://localhost:8001/api/pages/cockpit_daily/briefing?persona=daily -H "X-Org-Id: 1"
```
Ou tester un par un les 10 page_keys (`cockpit_daily, cockpit_comex, patrimoine, conformite, bill_intel, achat_energie, monitoring, diagnostic, anomalies, flex`) pour identifier le builder fautif.

---

## 11. Recommandations sémantiques moyen-terme

### 11.1 Statuts à fusionner

1. **Choisir une seule table d'action** : déprécier `ActionPlanItem` + `ActionPlanEvent` + `ActionPlanEvidence` au profit de `ActionItem` + `ActionEvent` + `ActionEvidence`.
2. **Statut canonique unique** : élargir `ActionStatus` pour intégrer la sémantique manquante :
   ```
   OPEN, PLANNED, IN_PROGRESS, DONE, ABANDONED, FALSE_POSITIVE, BLOCKED
   ```
   et formaliser le mapping FR au seul endroit `complianceLabels.fr.js:ACTION_STATUS_LABELS`.
3. **Distinguer "abandon utilisateur" vs "auto-close source résolue"** : ajouter colonne `closure_reason` Enum (`{user_done, user_abandoned, user_false_positive, system_source_resolved}`).
4. **Toujours appeler `mark_action_done`** — y compris pour `FALSE_POSITIVE` et tout statut terminal — afin que `closed_at` soit toujours set.
5. **Renommer `ActionItem.status=BLOCKED` → `PLANNED`** OU supprimer l'aliasing FE "Planifiée" : le mapping `blocked → planned → "Planifiée"` est un mensonge (`ActionsPage.jsx:78`). Le Drawer affiche "Bloquée" pour la même valeur (`ActionDetailDrawer.jsx:97`).

### 11.2 Mapping sévérité ↔ priorité

1. Créer **un service unique** `services/severity_priority_mapper.py`.
2. Supprimer les 4 mappings dispersés.
3. Imposer **convention lowercase canonique** `low|medium|high|critical` partout.
4. **Supprimer l'élévation systématique** dans `BA_SEVERITY_UI_MAP` (`r_codes_registry.py:47`) qui transforme `info → MEDIUM` et `warning → HIGH`. **Bug sémantique.**

### 11.3 Champs à dégager

- `ActionPlanItem.sla_status` (calculé runtime, pas persisté)
- `ActionPlanItem.evidence_type` (jamais setté)
- `ActionPlanItem.priority_override_reason`, `reason_codes`
- `ActionItem.notes` overload `##CAMPAIGN:` → créer une vraie colonne `campaign_sites JSON`
- `Alerte` : modèle entier semble obsolète (FR, sans lien Action)
- `AnomalyStatus` enum (`enums.py:888`) — défini mais sans colonne SQL

### 11.4 Champs manquants

- `effort` (mock `actions.js`) : utilisé Kanban mais inexistant. Soit ajouter colonne `effort_days Integer`, soit retirer affichage.
- `comments[]` : `ActionItem` a relation `comments` mais pas exposée dans `_serialize_action`.
- `description` distinct de `rationale` : ambiguïté DB. Choisir l'un.
- "Anomalies liées" en bandeau Drawer : la donnée existe (`actions.py:1092-1102`) mais le Drawer ne la lit pas.

### 11.5 Ajouts structurels recommandés

- `ActionItem.anomaly_id` FK directe vers une **canonique anomaly table** (à créer en consolidation des 4 sources actuelles), OU imposer `AnomalyActionLink` à toutes les voies de création (y compris `sync_actions`).
- Enum strict `AnomalySource{PATRIMOINE, BILLING, MONITORING, COMPLIANCE, CONSUMPTION}` pour `AnomalyActionLink.anomaly_source`.
- Index unique partiel `(anomaly_source, anomaly_ref, site_id) WHERE NOT dismissed` (PG-only).
- **Contract test FE↔BE** qui vérifie que tout `STATUS_TO_BE.values() ⊆ ActionStatus.__members__` — éviterait le 400 silencieux.

---

## Fichiers cités (paths absolus)

### Frontend
- `/Users/amine/projects/promeos-poc/frontend/src/pages/AnomaliesPage.jsx`
- `/Users/amine/projects/promeos-poc/frontend/src/pages/ActionsPage.jsx`
- `/Users/amine/projects/promeos-poc/frontend/src/pages/ActionCenterPage.jsx` (mort)
- `/Users/amine/projects/promeos-poc/frontend/src/pages/ActionPlan.jsx` (mort)
- `/Users/amine/projects/promeos-poc/frontend/src/pages/useAnomalyFilters.js`
- `/Users/amine/projects/promeos-poc/frontend/src/pages/anomalyEvidence.js`
- `/Users/amine/projects/promeos-poc/frontend/src/components/ActionDetailDrawer.jsx`
- `/Users/amine/projects/promeos-poc/frontend/src/components/CreateActionDrawer.jsx`
- `/Users/amine/projects/promeos-poc/frontend/src/components/ActionDetailPanel.jsx` (mort)
- `/Users/amine/projects/promeos-poc/frontend/src/components/AnomalyActionModal.jsx` (mort)
- `/Users/amine/projects/promeos-poc/frontend/src/components/CreateActionModal.jsx` (mort)
- `/Users/amine/projects/promeos-poc/frontend/src/components/ActionCenterSlideOver.jsx`
- `/Users/amine/projects/promeos-poc/frontend/src/components/SiteAnomalyPanel.jsx`
- `/Users/amine/projects/promeos-poc/frontend/src/components/TabActionsSite.jsx`
- `/Users/amine/projects/promeos-poc/frontend/src/components/ROISummaryBar.jsx`
- `/Users/amine/projects/promeos-poc/frontend/src/contexts/ActionDrawerContext.jsx`
- `/Users/amine/projects/promeos-poc/frontend/src/services/api/actions.js`
- `/Users/amine/projects/promeos-poc/frontend/src/services/anomalyActions.js` (mort)
- `/Users/amine/projects/promeos-poc/frontend/src/mocks/actions.js` (mort)
- `/Users/amine/projects/promeos-poc/frontend/src/domain/compliance/complianceLabels.fr.js`
- `/Users/amine/projects/promeos-poc/frontend/src/App.jsx` (routes)

### Backend — routes
- `/Users/amine/projects/promeos-poc/backend/routes/pages_briefing.py`
- `/Users/amine/projects/promeos-poc/backend/routes/action_center.py`
- `/Users/amine/projects/promeos-poc/backend/routes/actions.py`
- `/Users/amine/projects/promeos-poc/backend/routes/action_templates.py`
- `/Users/amine/projects/promeos-poc/backend/routes/billing.py:1526` (anomalies-scoped)

### Backend — services
- `/Users/amine/projects/promeos-poc/backend/services/narrative/narrative_generator.py:2623-2916` (`_build_anomalies`)
- `/Users/amine/projects/promeos-poc/backend/services/narrative/narrative_generator.py:3257-3317` (dispatcher `_BUILDERS` + `generate_page_narrative`)
- `/Users/amine/projects/promeos-poc/backend/services/action_center_service.py`
- `/Users/amine/projects/promeos-poc/backend/services/action_workflow_service.py`
- `/Users/amine/projects/promeos-poc/backend/services/action_management_service.py`
- `/Users/amine/projects/promeos-poc/backend/services/action_status_service.py`
- `/Users/amine/projects/promeos-poc/backend/services/action_close_rules.py`
- `/Users/amine/projects/promeos-poc/backend/services/action_audit_service.py`
- `/Users/amine/projects/promeos-poc/backend/services/action_hub_service.py`
- `/Users/amine/projects/promeos-poc/backend/services/patrimoine_anomalies.py`
- `/Users/amine/projects/promeos-poc/backend/services/bill_intelligence/anomaly_detector.py:1705`
- `/Users/amine/projects/promeos-poc/backend/services/bill_intelligence/priority.py`
- `/Users/amine/projects/promeos-poc/backend/services/bill_intelligence/r_codes_registry.py:47`
- `/Users/amine/projects/promeos-poc/backend/services/navigation_badges_service.py:123-126`
- `/Users/amine/projects/promeos-poc/backend/services/demo_seed/gen_actions.py:196-211`
- `/Users/amine/projects/promeos-poc/backend/services/demo_seed/gen_seed_completion.py:564-580`

### Backend — modèles
- `/Users/amine/projects/promeos-poc/backend/models/action_item.py`
- `/Users/amine/projects/promeos-poc/backend/models/action_plan_item.py`
- `/Users/amine/projects/promeos-poc/backend/models/action_event.py` (`ActionPlanEvent` — table `action_plan_events`)
- `/Users/amine/projects/promeos-poc/backend/models/action_detail_models.py` (`ActionEvent`, `ActionComment`, `ActionEvidence`, `AnomalyActionLink`, `AnomalyDismissal`)
- `/Users/amine/projects/promeos-poc/backend/models/bill_anomaly.py`
- `/Users/amine/projects/promeos-poc/backend/models/enums.py:386,400,888,898` (ActionSourceType, ActionStatus, AnomalyStatus, DismissReason)
- `/Users/amine/projects/promeos-poc/backend/models/energy_models.py:287,492` (Anomaly, MonitoringAlert)
- `/Users/amine/projects/promeos-poc/backend/models/alerte.py`
- `/Users/amine/projects/promeos-poc/backend/schemas/action_center.py` (ActionableIssue Pydantic)

---

## Annexe — Méthodologie

Audit réalisé en **4 sub-agents parallèles** (lecture seule stricte) :
1. **Frontend mapping + UX** : composants, routes, dead code, robustesse, perf
2. **Backend endpoints + Briefing 500** : inventaire endpoints, hypothèses 500, services, org-scoping
3. **Data model + cohérence sémantique** : 5 modèles anomaly × 5 modèles action, enums statuts, mappings sévérité/priorité, indicateurs financiers, traçabilité
4. **Bug hunt ciblé** : 5 symptômes spécifiques (Briefing 500, false_positive→done, anomalies dupliquées, badge 4 vs 35, colonnes vides)

Aucune modification de fichier. Toute action corrective fera l'objet d'un plan séparé à valider.
