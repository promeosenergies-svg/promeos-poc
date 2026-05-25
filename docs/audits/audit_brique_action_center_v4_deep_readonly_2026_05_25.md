# Audit brique — Action Center V4 deep READ-ONLY (2026-05-25)

**Branche** : `claude/action-center-v4-deep-audit-transversal`
**Base** : `claude/refonte-sol2` après merge PR #309 (squash `f07df58a`)
**Mode** : READ-ONLY strict — aucun code modifié.
**Verdict global** : 🟡 **OK avec dette** — fondations V4 solides (8 tables ORM, 10 endpoints, RBAC + rate-limit + idempotency UUID, drawer 4 onglets), mais 4 défauts P0 bloquants pour faire du hub un vrai centre opérationnel transversal (cf. §6).

---

## 1 — Cartographie modèles / routes / services / composants

### 1.1 Modèles ORM V4 (8 tables + 1 audit) — `backend/models/v4/`

| Table | Rôle | Lignes-clés | Indexes |
|---|---|---|---|
| `action_center_items` | Item cardinal (54 colonnes) | [action_center_items.py:36](backend/models/v4/action_center_items.py#L36) | 8 indexes (priority_active, kind_domain, lifecycle, stale, unassigned, recent_closed, site, owner) + idx_aci_idempotency_key UNIQUE partial |
| `action_blockers` | 7 blocker_types (waiting_evidence, waiting_budget, …) | [action_blockers.py:31](backend/models/v4/action_blockers.py#L31) | idx_blocker_item_active partial WHERE resolved_at IS NULL |
| `action_evidences` | Preuves (MIME whitelist + 10 MB max + 90 j expiry IE6) | [action_evidences.py](backend/models/v4/action_evidences.py) | — |
| `action_events` | Audit trail (16 event_types) | [action_events.py:75](backend/models/v4/action_events.py#L75) | 4 indexes (corr_id, occurred_at, item_id, event_type) |
| `action_links` | Liens cross-module (target_module, target_id, relation) | [action_links.py:20](backend/models/v4/action_links.py#L20) | — |
| `action_scenarios` | CAPEX / gain € scenarios | [action_scenarios.py:35](backend/models/v4/action_scenarios.py#L35) | — |
| `duplicate_groups` | Détection doublons (status: suggested/merged/dismissed) | [duplicate_groups.py:19](backend/models/v4/duplicate_groups.py#L19) | — |
| `recurrence_groups` | Récurrences (rolling_window_days 90, Q9-B Amine rule) | [recurrence_groups.py:19](backend/models/v4/recurrence_groups.py#L19) | — |

**Enums clés** (`backend/models/v4/enums/`) :
- `Domain` (7 valeurs) : `conformite`, `facturation`, `maintenance`, `optimisation`, `purchase`, `flexibilite`, `data_quality` — **ne contient ni `patrimoine` ni `energie` ni `cockpit`**.
- `Kind` (7 valeurs D1 cardinal) : `anomaly`, `action`, `decision`, `signal`, `evidence_request`, `deadline`, `recommendation`.
- `LifecycleState` (5 valeurs IL2) : `new`, `triaged`, `planned`, `in_progress`, `closed`.
- `ClosureReason` (6 valeurs) : `resolved`, `dismissed`, `not_applicable`, `merged_duplicate`, `resolved_via_recurrence`, `expired`.
- `EventType` (16 valeurs) couvrant lifecycle/owner/priority/blocker/evidence/closure/reopened/export/bulk/kind_correction.

**Contraintes CHECK DB** (7) : `chk_kind`, `chk_lifecycle_state`, `chk_priority_bracket` (P0-P3), `chk_closure_consistency` (closed → closed_at + closure_reason NOT NULL), `chk_closure_reason_valid`, `chk_score_range` (0-100), `chk_confidence_range` (0-1).

### 1.2 Routes V4 — `backend/routes/v4/action_center.py` (prefix `/api/v4/action-center`)

| Méthode | Path | Rôle |
|---|---|---|
| POST | `/items` | Create avec `Idempotency-Key` (UUID v4) + SHA256 body hash → 201/200/409 |
| GET | `/items` | List paginated, filtres `domain`, `lifecycle_state`, `priority_bracket`, `kind` |
| GET | `/items/{id}` | Détail (404 cross-org fail-closed) |
| GET | `/items/{id}/events` | Timeline audit |
| GET | `/items/{id}/evidences` | Preuves (storage_uri JAMAIS retourné, sécurité) |
| GET | `/items/{id}/blockers` | Actifs + résolus |
| GET | `/items/{id}/links` | ActionLink cross-module |
| GET | `/items/{id}/impact` | 4 quadrants CFO |
| GET | `/summary` | 10 compteurs (P0/P1/sans pilote/à risque/sécurisés/sums € par P) |
| GET | `/pilotage/file-prioritaire` | Top N (P0/P1, actifs, score DESC) |
| GET | `/pilotage/journal` | Cross-items events depuis N jours |
| POST | `/export/comex.pdf` | PDF report |
| PATCH | `/items/{id}` | Update cosmétique (title/description) |
| PATCH | `/items/{id}/lifecycle` | Transition 5×10 + evidence required pour closed (P0 conformité) |
| PATCH | `/items/{id}/assign` | Assign/unassign + snapshot display_name |
| POST/PATCH | `/items/{id}/evidences[/...]` | Upload + verify (90 j expiry) |
| POST/PATCH | `/items/{id}/blockers[/...]` | Add + resolve |
| POST | `/items/{id}/links` | Crée ActionLink |

**Middlewares systématiques** : `populate_org_context` (Depends) + `require_v4_role` (RBAC) + `@limiter.limit(QUOTA_*)` + `verify_parent_item_access` (404 cross-org). Defense-in-depth IS1-IS11 validée.

### 1.3 Routes legacy non-V4 — toujours vivantes

| Route | Statut | Risque |
|---|---|---|
| `/api/action-center/*` (legacy) | LIVE sans deprecation | UX-orphan : remplacée par V4, mais aucun 410 Gone |
| `/api/actions` (legacy ActionItem) | LIVE | Cutover L8 Mois 5 (irréversible) — 173 rows migration |
| `/api/action-templates` | LIVE | À évaluer |
| `/api/cockpit/priorities` ([cockpit.py:1069](backend/routes/cockpit.py#L1069)) | **LIVE et appelle action_center_service** | Renvoie `[{rank, title, action_url:'/anomalies?issue=…'}]` → **pointe vers `/anomalies` qui est gated OFF en mode V4 ON** → cliquer = 404 utilisateur |

### 1.4 Services métier — `backend/services/`

| Service | Type | Statut |
|---|---|---|
| `v4/conformite_action_sync_service.py` | Sync Conformité → V4 (READ-ONLY P0, P1 endpoint pas livré) | `external_ref` pattern stable `rule_code:scope:scope_id:reason_code` |
| `billing_sync_actions_service.py` (via [routes/billing_sync.py](backend/routes/billing_sync.py)) | Sync Billing anomaly → V4 | `external_ref` encodé en **texte plain dans `description`** (`"EXTERNAL_REF: billing_anomaly:1"`) — **pas de colonne dédiée** |
| `action_hub_service.py` | Legacy ActionItem builders (compliance/consumption/billing) | À supprimer L8 Mois 5 |
| `action_audit_service.py` · `action_bulk_service.py` · `action_notification_service.py` · `action_management_service.py` | Legacy | Idem |

**Aucun cron / APScheduler** pour sync Billing/Conformité → ActionCenter détecté. Les syncs sont **on-demand** (endpoint billing `/sync-actions-from-anomalies` ou service Conformité appelé manuellement).

### 1.5 Frontend — `frontend/src/pages/action-center-v4/`

| Page | Route | Rôle |
|---|---|---|
| `ActionCenterV4ListPage.jsx` | `/action-center-v4` (alias `/centre-action`) | Référentiel paginé 20/page + filtres + drawer |
| `ActionCenterV4PilotagePage.jsx` | `/action-center-v4/pilotage` | File prioritaire (5 items P0/P1) |
| `ActionCenterV4JournalPage.jsx` | `/action-center-v4/pilotage/journal` | Flux events 7 j |

**Behind feature flag** `VITE_FEATURE_ACTION_CENTER_V4`. Si flag OFF → fallback `/anomalies` (legacy AnomaliesPage v1).

**Drawer** — `pages/action-center-v4/components/drawer/ItemDetailDrawer.jsx` (760 px Sol shell) :
- Header sticky : `DrawerBreadcrumb` + 3 boutons d'actions.
- Body : `ItemClosedBanner` (terminal) + `ItemHeader` + **4 onglets** (`Preuves` / `Blocages` / `Liens` / `Historique`).
- Footer sticky : timestamps création + MAJ.
- Lazy tab loading (`loadedTabs` Set).
- **Lien retour spécifique** : `BillingAnomalyBackLink.jsx` (uniquement Billing → présent).

**Filtres** (`ListFilterBar.jsx`) :
- Row 1 : 7 chips Kind (+ « Tous »).
- Row 2 : `<select>` lifecycle_state + bouton « Réinitialiser ».
- Filtre persistent « Sans responsable » (banner pink + clear).
- Filtre `domain` ajouté en P2-B C1 (2026-05-24).

**Pages legacy physiques (orphelines V4 ON)** :
- `pages/ActionCenterPage.jsx` (378 l, v1 console legacy) — **orphelin total**.
- `pages/ActionsPage.jsx` (1 579 l, v1) — routée si V4 OFF.
- `pages/AnomaliesPage.jsx` (835 l, v1) — routée si V4 OFF, et **cible des CTAs `/api/cockpit/priorities`**.

**Composants legacy** (`components/action-center/*`) : `ActionDetailDrawer.jsx`, `AnomalyActionModal.jsx`, `CreateActionDrawer.jsx`, `ActionCenterSlideOver.jsx`, `CreateActionModal.jsx` — pour routes legacy.

---

## 2 — Live smoke (HELIOS, git_sha=`f07df58a`)

```
GET /api/v4/action-center/summary
  → count_p0=53, count_p1=3, count_without_owner=55,
    sums_eur_total=47 500 €, items_total=61
GET /api/v4/action-center/items (sans filtre)        → 200, 61 items
GET /api/v4/action-center/items?domain=facturation   → 200, filtre OK
GET /api/v4/action-center/items?lifecycle_state=closed → 200, filtre OK
GET /api/v4/action-center/items?priority_bracket=P0    → 200, filtre OK
GET /items/{id} + /events + /evidences + /blockers + /links + /impact → 200 ✅
GET /pilotage/file-prioritaire   → 200, 3 776 B
GET /pilotage/journal            → 200, 49 B (peu d'events)

POST /items + Idempotency-Key X  → 201, id=b1aa5f64
POST /items + Idempotency-Key X (rejeu) → 200, id=b1aa5f64 ✅ idempotency OK

GET  /api/cockpit/priorities     → 200, 5 priorités pointant vers
   /anomalies?issue=compliance_review_2  ← cible legacy gated OFF !
```

---

## 3 — Audit UX/UI

### 3.1 Hiérarchie visuelle

1. Masthead (H1 « Centre d'action » + total).
2. PilotageTabs (Pilotage / Référentiel).
3. NarrativeBar (5 tuiles CFO : P0/P1/sans pilote/à risque/sécurisés).
4. ListFilterBar (kind chips + lifecycle dropdown + reset).
5. Filter banner (« Sans responsable » si actif).
6. ItemsTable (paginée 20/page).
7. Drawer 760 px (sticky header + 4 tabs + sticky footer).

### 3.2 Forces

| ✅ | Détail |
|---|---|
| Tous les états critiques présents | Loading skeleton + Empty + Empty filtered (distinct copy) + Error retry sur les 3 pages V4 |
| Filtres URL params validés | Whitelist stricte (anti-injection) sur `state`/`kind`/`domain`/`without_owner`/`page` |
| Lazy tab loading | Set `loadedTabs` → UX rapide, pas de fetch superflu |
| Coordination refetch | Mutation → invalidate list + drawer + timeline (refreshKey) |
| 44 fichiers de tests (575 KB) | 3 pages + 40+ composants + 7 hooks |
| Aucun acronyme nu | DT/OPERAT/BACS/APER tous via `DOMAIN_LABELS`/`KIND_LABELS` FR ou `SolAcronymTooltip` |

### 3.3 Défauts UX/UI détectés

| ⚠️ | Détail | Sévérité |
|---|---|---|
| **Drawer pas d'error boundary** | Si `useActionCenterV4Item` échoue → drawer blank, utilisateur aveugle | P1 |
| **Item-not-found fallback manquant** | itemId valide mais item supprimé backend → data=null sans message clair | P1 |
| **Deep-link drawer `?item={id}` pas implémenté** | M2-5.11.K acte la déc° : limite la partageabilité d'un lien Cockpit P1 vers une action précise | P1 |
| **Test FilterBar domain léger** | `ListFilterBar_domain_p2b.test.jsx` 3.9 KB seulement vs `ListFilterBar.test.jsx` 8.5 KB | P2 |
| **Tooltips « pourquoi cette action »** | Absents au niveau drawer (présents en Cockpit P1.5 « Pourquoi cette priorité ? » mais pas dans Centre d'Action) | P2 |
| **3 pages legacy + 5 composants legacy** physiques | `ActionCenterPage`/`ActionsPage`/`AnomaliesPage` + drawer/modal legacy ; bloquant cutover L8 Mois 5 | P2 |

---

## 4 — Audit personas

### 4.1 DG / DAF (lecture-30s)

| Question DAF | Réponse cockpit | Réponse Centre d'Action |
|---|---|---|
| « Où en est-on ? » | 5 KPI hero | 5 tuiles NarrativeBar (P0=53, P1=3, sums=47 500 €) |
| « Que faire en priorité ? » | Top 2-3 priorités | File prioritaire (top 5 P0/P1) |
| « Combien ça vaut ? » | Surfact total 19 808 € | sums_eur_by_priority ventilation |
| « Qui s'en occupe ? » | — | « Sans responsable = 55 / 61 » → ⚠️ **97 % des items n'ont pas de pilote** |
| **Verdict** | ✅ Lecture rapide | ⚠️ DAF voit qu'il y a 55 items sans pilote — pas d'indication « qui dois-je nommer ? » |

### 4.2 Energy Manager / Operations

| Use case | OK ? |
|---|---|
| Voir les anomalies du jour | ✅ filtre `lifecycle_state=new` + drawer |
| Ajouter une preuve | ✅ EvidenceUploadModal + magic bytes validation |
| Marquer un blocker | ✅ BlockerAddModal (7 blocker_types) |
| Clôturer en justifiant | ✅ LifecycleTransitionModal (6 closure_reasons + evidence required P0) |
| Revenir à la source (anomalie facture) | ⚠️ `BillingAnomalyBackLink` parsing `description` (string match) — fragile |
| Revenir à la source (règle conformité) | ❌ **pas de back-link** côté FE pour CONFORMITE |

### 4.3 Auditeur / Compliance officer

| Use case | OK ? |
|---|---|
| Voir le motif d'une action | ⚠️ `description` libre — pas de champ « source » structuré |
| Voir la chaîne d'événements | ✅ Timeline (16 event_types, correlation_id) |
| Vérifier l'evidence (90 j) | ✅ EvidenceVerifyDialog + expires_at |
| Tracer qui a fait quoi | ✅ actor_type/id/name/role sur ActionEventLog |

### 4.4 Customer Success — workflow expliqué en 2 min ?

| Étape | Lisibilité |
|---|---|
| « Voici les 53 P0 » | ✅ tuile P0 cliquable |
| « Cliquez pour ouvrir, assignez un pilote » | ✅ assign modal |
| « Ajoutez une preuve » | ✅ upload modal |
| « Marquez closed avec une raison » | ✅ lifecycle transition modal |
| « La preuve expire dans 90 j » | ✅ visible sur la card preuve |
| **Mais** | ❌ « D'où vient cette action ? » est seulement partiellement expliqué (Billing oui via back-link parsing, Conformité non, autres non) |

---

## 5 — Audit doublons / idempotence

### 5.1 Mécanismes en place

| Brique | Clé d'idempotence | Persistée DB | Index UNIQUE |
|---|---|---|---|
| POST `/items` (header `Idempotency-Key`) | UUID v4 + SHA256 body | ✅ `idempotency_key` + `idempotency_payload_hash` | ✅ `idx_aci_idempotency_key` UNIQUE partial (org_id, idempotency_key) WHERE NOT NULL |
| Billing sync | **Title-based** (`org_id, kind=anomaly, domain=facturation, title`) | ❌ pas de colonne `external_ref` | ❌ **pas d'index UNIQUE** — race possible |
| Conformité sync (P0) | `external_ref` = `rule_code:scope:scope_id:reason_code` | ❌ pas persisté en P0 (READ-ONLY) | ❌ — sera à créer en P1 |

### 5.2 Test live idempotency POST `/items`

```
POST + Idempotency-Key UUID X (body Y) → 201 Created, id=b1aa5f64
POST + Idempotency-Key UUID X (body Y) → 200 OK,      id=b1aa5f64  ← rejeu sûr ✅
```

### 5.3 Risques de doublons

| Scénario | Risque |
|---|---|
| Billing sync re-run sans Idempotency-Key | **MOYEN** — title-based, pas d'index UNIQUE |
| Conformité P1 sans index `external_ref` UNIQUE | **MOYEN à venir** |
| 2 anomalies similaires titre identique | **BAS** mais protocole faible |
| Item clos puis source rouvre | ✅ **PROTÉGÉ** : `if existing.lifecycle_state == CLOSED: skip` |

---

## 6 — Audit liens source (back-links)

### 6.1 Champs disponibles ActionCenterItem

- `site_id` UUID (weak ref) → **NULL** sur tous les items billing testés live ❌
- `building_id`, `meter_id`, `regulatory_rule_id` → idem, jamais peuplés en P0 par les syncs
- Table `action_links` (target_module, target_id, relation) → **JAMAIS PEUPLÉE** :
  ```
  GET /api/v4/action-center/items/{id}/links → {"items":[],"total":0}
  ```

### 6.2 Mécanismes de back-link actuels

| Brique | Mécanisme | Robustesse |
|---|---|---|
| Billing | `description` plain-text contient `EXTERNAL_REF: billing_anomaly:1` ; FE parse pour `BillingAnomalyBackLink` | ❌ **fragile** : parsing chaîne, pas un champ structuré |
| Conformité | `external_ref` calculé en P0 mais **non persisté** | ❌ aucun back-link FE |
| Patrimoine | **N/A** — Patrimoine n'émet pas d'action | — |
| Cockpit | Référence par insight_id (pas par action_id) | — |

### 6.3 Impact CX

- L'auditeur ne peut pas cliquer une action conformité pour voir la règle source.
- L'Energy Manager doit deviner depuis le titre (« Litige facture — anomalie #1 (R27) ») au lieu d'un lien explicite.
- L'auditeur ne peut pas vérifier la non-régression « cette action conformité → cette règle DT → ce site ».

---

## 7 — Réponses aux 10 questions clés du brief

| # | Question | Réponse | Détail |
|---|---|---|---|
| 1 | Toutes les actions ont-elles une source claire ? | ⚠️ **Partiellement** | Billing : oui via title + description plain-text ; Conformité : oui via title + champ `external_ref` non persisté ; autres briques : pas d'émission donc N/A |
| 2 | Les domaines sont-ils cohérents (Patrimoine/Conformité/Facturation) ? | ⚠️ **Non cohérents avec brief** | Enum Domain = {`conformite`, `facturation`, `maintenance`, `optimisation`, `purchase`, `flexibilite`, `data_quality`} — **pas de `patrimoine`** |
| 3 | Les filtres fonctionnent-ils vraiment ? | ✅ **Oui** | `domain`/`lifecycle_state`/`priority_bracket`/`without_owner` tous testés live HTTP 200 + whitelist validée |
| 4 | Une action peut-elle revenir vers sa source ? | ❌ **Non systématiquement** | Billing : back-link fragile (string parsing description) ; Conformité : aucun back-link ; ActionLink jamais peuplée |
| 5 | Les actions clôturées restent-elles clôturées ? | ✅ **Oui** | Constraint DB `chk_closure_consistency` + Billing sync `if CLOSED: skip` |
| 6 | Les preuves bloquantes sont-elles visibles ? | ✅ **Oui** | Blocker `waiting_evidence` + ItemClosedBanner + EvidenceUploadModal + magic bytes + 90 j expiry |
| 7 | Les doublons sont-ils empêchés ? | ⚠️ **Partiellement** | POST `/items` ✅ via UUID Idempotency-Key + index UNIQUE ; Billing sync ❌ pas d'index UNIQUE structuré |
| 8 | Le DAF comprend-il quoi traiter en premier ? | ✅ **Oui via Cockpit P1** | 5 KPI + 2-3 priorités + « Pourquoi cette priorité ? » ; mais dans /centre-action seul, 55/61 sans pilote — pas d'indicateur « par où commencer » |
| 9 | Le Customer Success peut-il expliquer le workflow en 2 min ? | ✅ **Oui** | Voir → assigner → preuve → clôturer + lifecycle 5 états documentés ; mais explique mal « d'où vient cette action ? » |
| 10 | Y a-t-il des routes mortes, composants morts ou états silencieux ? | ⚠️ **Oui** | `/api/cockpit/priorities` LIVE pointant vers `/anomalies` (gated OFF) ; `ActionCenterPage.jsx` (378 l) orphelin total ; 5 composants drawer/modal legacy ; pages `ActionsPage`/`AnomaliesPage` mortes en V4 ON ; drawer sans error boundary |

---

## 8 — Plan P0 / P1 / P2

### 8.1 P0 — Bloquant (à fix avant prochain release)

| # | Item | Effort | Risque actuel |
|---|---|---|---|
| **P0-1** | `/api/cockpit/priorities` renvoie des CTAs `action_url=/anomalies?issue=…` qui pointent vers la page LEGACY gated OFF en V4 ON → clic = 404 utilisateur | 0,5 j — Soit retirer la route (410 Gone), soit corriger `action_url` vers `/action-center-v4?item={id}` | UX : un DG/DAF qui clique tombe sur 404 |
| **P0-2** | Drawer V4 sans error boundary + sans fallback « item not found » → si fetch fail ou item supprimé, modal blank → utilisateur aveugle | 0,5 j — Ajouter `<ErrorBoundary>` + condition `if (!item) return <NotFoundState/>` | UX/CX : silence opérationnel |
| **P0-3** | Billing sync sans index UNIQUE structuré (`external_ref` plain-text dans `description`) → 2 sync parallèles ⇒ 2 items créés (la 2e fois title match mais race-window) | 1 j — Ajouter colonne `external_ref` VARCHAR + index UNIQUE (org_id, external_ref) + migrer le parsing description vers le champ | Data : doublons billing en production |
| **P0-4** | `ActionLink` jamais peuplée par les syncs → impossible de revenir à la source (anomalie/règle/site) depuis le drawer | 1 j — Patcher `billing_sync` et `conformite_action_sync` pour `INSERT INTO action_links` à chaque création | UX/CX : auditeur/EM ne peut pas tracer |

**Total P0 = ~3 j-dev**

### 8.2 P1 — Important (à fix prochain sprint)

| # | Item | Effort |
|---|---|---|
| P1-1 | Activer l'endpoint Conformité `POST /api/conformite/sync-remediation-actions` (contrat défini P0 mais pas livré) | 1 j |
| P1-2 | Persister `external_ref` côté Conformité + index UNIQUE (org_id, external_ref) | 0,5 j |
| P1-3 | Deep-link drawer `?item={id}` (M2-5.11.K) — partage Cockpit P1 → Centre d'Action ciblé | 1 j |
| P1-4 | Sync inverse : action CLOSED → BillingInsight RESOLVED / RuleApplicability sortie de DATA_MISSING | 2 j (cascade + tests) |
| P1-5 | Bloc « Pourquoi cette action ? » dans le drawer (équivalent Cockpit P1.5) avec source structurée | 1 j |
| P1-6 | Test coverage filtre domain `ListFilterBar_domain_p2b.test.jsx` (3.9 KB → 8+ KB) | 0,5 j |

**Total P1 = ~6 j-dev**

### 8.3 P2 — Souhaitable (M2-6+ ou cutover legacy L8)

| # | Item | Effort |
|---|---|---|
| P2-1 | Suppression `ActionCenterPage.jsx` orphelin (378 l) + 5 composants legacy | 0,5 j |
| P2-2 | Cutover L8 ActionsPage + AnomaliesPage (Mois 5, planifié) | 3 j cf. L8 doc |
| P2-3 | 410 Gone sur `/api/action-center/*` (legacy) + `/api/actions` (legacy) | 0,5 j |
| P2-4 | Ajouter `patrimoine` dans enum Domain si on veut classer les actions « données patrimoine manquantes » distinctement | 0,5 j + ADR |
| P2-5 | Ajouter Tooltips/Aria-label sur chips Kind/Domain pour CS onboarding < 30 s | 0,5 j |
| P2-6 | Couverture Playwright E2E Centre d'Action (filtres + drawer + lifecycle full path) | 1 j |

---

## 9 — Prompt de correction P0 (uniquement)

Le prompt suivant est destiné à un sprint correctif **strict P0** (3 j-dev). Il assume que les 4 items P0 sont indépendants et peuvent être traités en parallèle si plusieurs devs.

```
Tu es Staff Engineer Full-Stack + QA Manager sur PROMEOS.

BRANCHE
Créer :
  claude/action-center-v4-p0-fixes

Base :
  claude/refonte-sol2 après merge PR audit deep #310 (si mergé), sinon
  branche directe sur refonte-sol2.

OBJECTIF
Corriger les 4 items P0 issus de l'audit deep Action Center V4 du
2026-05-25 (cf. docs/audits/audit_brique_action_center_v4_deep_readonly_2026_05_25.md
§8.1) — sans nouvelle feature, sans nouveau menu, sans refonte.

À FAIRE

P0-1 — Désorienter le DG vers une 404 : interdit.
  - Soit retirer `/api/cockpit/priorities` (410 Gone via
    `_gone_cockpit_p0_2026_05_25("/cockpit/priorities", alternative="/api/cockpit/strategique → top_priorities")`)
    si on confirme qu'aucun FE ne l'appelle après #303 ;
  - Soit patcher `backend/routes/cockpit.py:1069` pour que `action_url`
    pointe vers `/action-center-v4?item={item_id}` au lieu de
    `/anomalies?issue={issue}` (qui est gated OFF).
  - Choix recommandé : 410 Gone (Cockpit P1 a déjà top_priorities).
  - Test source-guard : ajouter `test_g6_cockpit_priorities_410_gone` dans
    `tests/source_guards/test_cockpit_p1_executive_narrative_source_guards.py`.

P0-2 — Drawer aveugle quand item supprimé : interdit.
  - `frontend/src/pages/action-center-v4/components/drawer/ItemDetailDrawer.jsx` :
    wrapper `<ErrorBoundary>` autour de `<V4Drawer>` + condition explicite
    `if (item === null && !loading) return <ItemNotFoundState onClose=…/>`
    avec message FR clair et CTA « Retour à la liste ».
  - Tests FE : ajouter 2 cases dans
    `pages/action-center-v4/components/drawer/__tests__/ItemDetailDrawer.test.jsx` :
    `it('affiche un fallback quand fetch fail')` et
    `it('affiche un fallback quand item supprimé entre-temps')`.

P0-3 — Billing sync sans index UNIQUE : data corruptible.
  - Migration Alembic : ajouter colonne `external_ref VARCHAR(120)` sur
    `action_center_items` + index UNIQUE partial
    `idx_aci_external_ref UNIQUE (organisation_id, external_ref) WHERE external_ref IS NOT NULL`.
  - Patcher `backend/routes/billing_sync.py` :
    - retirer le parsing `description` ;
    - poser `external_ref = f"billing_anomaly:{anomaly.id}"` à la création ;
    - utiliser UPSERT (ou query par external_ref) pour idempotence ;
    - garder Idempotency-Key UUID en double-defense.
  - Backfill : script de migration qui parse les items existants
    `domain=facturation`, extrait `EXTERNAL_REF: billing_anomaly:N` depuis
    `description`, et peuple `external_ref`.
  - Tests BE : ajouter dans
    `backend/tests/test_billing_sync_actions_service.py` :
    `test_external_ref_index_unique_protects_concurrent_writes` +
    `test_backfill_parses_legacy_description_pattern`.

P0-4 — ActionLink jamais peuplée : auditeur aveugle.
  - Patcher `backend/routes/billing_sync.py` pour `INSERT INTO action_links`
    à chaque création d'item :
      target_module="billing", target_id=anomaly.id, relation="caused_by".
  - Patcher `backend/services/v4/conformite_action_sync_service.py` (et son
    futur endpoint P1) pour faire pareil :
      target_module="conformity", target_id=rule.id, relation="caused_by".
  - Backfill : script qui boucle sur les items existants billing et crée
    rétroactivement les ActionLink depuis le parsing description.
  - Test FE : vérifier que `LinksTab.jsx` rend bien la liste retournée par
    `/items/{id}/links` (existant) ET que `BillingAnomalyBackLink`
    consomme désormais le link structuré au lieu du parsing description.

CRITÈRES D'ACCEPTATION

| # | Critère | Vérification |
|---|---|---|
| 1 | `/api/cockpit/priorities` retourne 410 OU action_url pointe vers /action-center-v4 | curl + source-guard |
| 2 | Drawer V4 : ouvrir un id inexistant → message FR + CTA, pas blank | Playwright manual + FE test |
| 3 | 2 POST `/api/billing/sync-actions-from-anomalies` consécutifs → 0 doublon | BE test transactionnel |
| 4 | GET `/items/{id}/links` retourne ≥ 1 link sur item billing migré | curl HELIOS |
| 5 | Aucun acronyme nu réintroduit | grep + SolNarrativeText |
| 6 | 0 console error + 0 network 4xx/5xx golden path /centre-action | Playwright réel |
| 7 | Tests : BE +4, FE +4, source-guards +2 ; tous verts | pytest + vitest |
| 8 | Cockpit P1.5 non régressé (#306, #308) | source-guards cockpit 67/67 |

COMMIT
  fix(action-center): close 4 P0 audit findings (no menu, no ghost screen)

AUDIT POSTFIX
  docs/audits/audit_postfix_action_center_p0_fixes_2026_05_25.md
  avec verdict GO/NO GO + Playwright réel + curl smoke.

CONTRAINTES
  - Aucun nouveau menu, aucun écran fantôme, aucun KPI magique.
  - Migration Alembic réversible.
  - Backfill idempotent (relançable sans dégât).
  - Pas de skip-test, pas de --no-verify.
  - Branche `claude/*`, pas main.
```

---

## 10 — Verdict global

🟡 **OK avec dette** — Les fondations V4 (ORM 8 tables + 7 enums + 16 event_types, 10 endpoints RBAC + rate-limit + idempotency UUID, drawer 4 onglets + lazy load + refetch coordination, 44 fichiers de tests 575 KB) sont **solides et bien doctrineuses** (cf. ADR-025 à ADR-029).

**4 défauts P0** empêchent toutefois le Centre d'Action V4 d'être un **vrai** hub opérationnel transversal :
1. `/api/cockpit/priorities` envoie le DG sur une 404 (pointe vers `/anomalies` gated OFF).
2. Le drawer V4 est aveugle si fetch fail ou item supprimé.
3. La sync Billing n'a pas d'index UNIQUE structuré → race possible doublons en production.
4. `ActionLink` n'est jamais peuplée → impossible de revenir à la source depuis le drawer.

**Aucun de ces 4 défauts** n'est régression — ce sont des **dettes héritées** identifiées par le brief Lead Product. Un sprint correctif P0 ciblé (~3 j-dev) suffit à les clore. Le prompt §9 est prêt à l'emploi.

**Aucun fichier modifié dans cet audit** (mode READ-ONLY strict respecté).
