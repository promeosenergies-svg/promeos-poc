# ADR-025 · Architecture Centre d'Action V4

> ⚠️ **AVENANT A1 (2026-05-16)** : §4.1 `organisation_id` passe de UUID à Integer FK
> `organisations(id)`. Voir [`docs/dev/ADR-025-029_A1_integer_fk.md`](ADR-025-029_A1_integer_fk.md)
> (décidé par ADR-009 — résolution dette JWT/UUID, Sprint M2-4). Le présent ADR
> reste la référence pour tout le reste du schéma V4.
>
> **Status** : Accepted (amendé A1 — cf. ci-dessus)
> **Date** : 2026-05-14
> **Deciders** : Amine + Claude (sessions Claude.ai 2026-05-13/14)
> **Branch** : claude/refonte-sol2
> **Related ADRs** : ADR-022 (priorisation héritée) · ADR-026 (Migration data) · ADR-027 (Sécurité org-scoping) · ADR-028 (Lifecycle states) · ADR-029 (Evidence + audit trail)
> **Doctrine source** : `docs/doctrine/doctrine_v4_classement_priorisation.md` **v0.3** (avenant 2026-05-14 actée commit L5 · cf. doctrine §11 historique)
> **Brief source** : `docs/dev/BRIEF_ADR-025_architecture_v4.md` (v0.1 Proposed)
> **Audit cohérence** : `docs/dev/L2_phase0_audit_coherence.md` (32/32 OK · 3 anomalies mineures intégrées ci-dessous)
> **L1 audit ref** : `docs/dev/L1_audit_centre_action_v4_decisional.md` (commit `ee749a12`)

---

## 1. Context et problématique

### 1.1 Pourquoi cette décision MAINTENANT

PROMEOS V4 refonte le Centre d'Action sur 6 mois (Mois 1-6 lancés 2026-05-13). La doctrine **v0.3** (initialement v0.2 acceptée 2026-05-13 · avenant v0.3 actée 2026-05-14 commit L5 sur closure_reasons Q37-A+) fige le **quoi** : 7 kinds (anomaly, action, decision, signal, evidence_request, deadline, recommendation) · 2 axes orthogonaux (`kind` immuable Q7-A vs `priority_score` dérivé Q8-C) · 6 règles modulation R1-R6 · 5 lifecycle states · 6 closure reasons · groupes Q9-B séparés (duplicate vs recurrence).

Le L1 décisionnel (commit `ee749a12`) a classé 86 éléments legacy avec verdicts binaires (GARDE 14 · SUPPRIME 28 · MIGRE 31 · REMPLACE 9 · RÉGÉNÈRE 4) et identifié 1 667 LoC mortes confirmées + 173 rows à migrer (35 `action_items` + 52 `bill_anomaly` + 86 `anomaly` KB) + dette structurelle massive (2 modèles parallèles `ActionItem`/`ActionPlanItem`, 6 vocabulaires statuts concurrents, 8+ enums sévérité, fuite org-scoping `/api/action-center/*`, bug Briefing 500).

**ADR-025 transforme le quoi en comment** : schéma DB cible, indexes, contraintes, API contracts, performance budgets, sécurité native, stratégie tests stratifiée. Il devient la **référence architecturale unique** pour Mois 2-6 d'implémentation. Sans ADR-025 acté, Mois 2 (backend cible socle) ne peut pas démarrer.

### 1.2 Problématique technique

Comment unifier 9 modèles Action/Anomaly + 18 tables DB legacy + 38 enums + 4 routers + 20 services + 24 fichiers FE + 1 667 LoC mortes en une architecture polymorphique simple, performante, RGPD-compliant, sécurisée org-scoped, et testable de bout en bout — **sans casser le sprint Phase 3.5 SynthèseStratégique en cours en parallèle (`backend/regops/`) et sans introduire un mois de double-write inutile** ?

---

## 2. Decision drivers (forces)

| Driver | Pondération | Source |
|---|---|---|
| **Performance** | Critique | Démo investisseur seed Juin 2026 · pilots payants Q3 2026 · vue d'entrée Pilotage doit être instantanée |
| **Simplicité maintenance** | Critique | Petite équipe (2 dev FT) · doit être lisible 6 mois plus tard |
| **RGPD-friendly audit trail** | Critique | Pilots HELIOS/MERIDIAN B2B exigent traçabilité défendable CNIL |
| **Sécurité org-scoping native** | Critique (P0 sécu) | Audit L1 §6 confirme fuite massive `/api/action-center/*` legacy · bloque pilots multi-tenant |
| **Testabilité bout en bout** | Élevé | Refonte 6 mois = ~100 tests V4 nécessaires sans couverture trouée |
| **Alignement doctrine v0.3** | Non négociable | Doctrine = source unique 6 mois (Q1-A à Q9-B doctrinaux · avenant v0.3 closure_reasons Q37-A+) |
| **Alignement L1 86 verdicts** | Non négociable | Aucune dérogation aux verdicts L1 sans audit Phase 2 |
| **Préservation sprint Phase 3.5** | Non négociable | `regulatory_applicability_service` en cours de build · interface stub Mois 2-3 |
| **Backup Q2-α non négociable** | Non négociable | 173 rows à migrer + 1 667 LoC à supprimer = aucune destruction sans backup |
| **Pas de double-write transitoire** | Préférence forte | Coût complexité Mois 2-3 prohibitif vs cutover sec Mois 4 (Q2-α + dry-run) |

---

## 3. Options considérées et décisions (Q10-Q18)

### Q10 — Pattern de stockage des items polymorphiques

**Options** :
- **Q10-A** : Single-table inheritance (1 table avec discriminant `kind`)
- **Q10-B** : Multi-table inheritance (1 table par kind + table abstraite)
- **Q10-C** : JSON-blob storage (1 colonne `payload` JSONB par kind)

**Décision** : **Q10-A refined** — single-table inheritance scope strict + 6 tables filles dédiées (`evidences`, `action_event_log`, `action_links`, `action_blockers`, `action_scenarios`) + 2 tables groupes (`duplicate_groups`, `recurrence_groups`) = 8 tables.

**Rationale** : 1 query cross-kind pour Pilotage/Référentiel · normalisation des objets lourds/variables (events, evidences, scenarios) · indexes B-tree natifs sur colonnes scalaires.

### Q11 — Modèle persistence du score de priorité

**Options** :
- **Q11-A** : 4 colonnes scalaires (`priority_score`, `priority_bracket`, `score_version`, `score_calculated_at`) + JSONB `priority_explanation`
- **Q11-B** : Tout en JSONB unique
- **Q11-C** : Calcul à la volée à chaque GET

**Décision** : **Q11-A** — Tri SQL natif `ORDER BY priority_score DESC` indexable B-tree + détail explicable dans JSONB.

**Rationale** : performance < 100ms pour Pilotage · score persisté event-driven (Q8-C doctrine) · explicabilité préservée pour drawer M2.

### Q12 — Stockage de l'audit trail

**Options** :
- **Q12-A** : Table dédiée `action_event_log` polymorphe
- **Q12-B** : Table par event_type
- **Q12-C** : Logs systèmes externes (Loki, ELK)

**Décision** : **Q12-A** — RGPD-compatible · rétention configurable par event_type · survit à clôture item (`ON DELETE RESTRICT`) · pas de cache `last_events_cache`.

**Rationale** : 15 event types avec structure homogène · politique rétention CNIL configurable · pas d'infra externe.

### Q13 — Stratégie de migration legacy → V4

**Options** :
- **Q13-A** : Double-write Mois 2-3 (legacy + V4 en parallèle, scripts réconciliation)
- **Q13-B** : Cutover sec Mois 4 + backup Q2-α obligatoire
- **Q13-C** : Migration progressive par kind (anomaly d'abord, puis action, etc.)

**Décision** : **Q13-B** — cutover sec Mois 4 + backup Q2-α (changé depuis Q13-A initial).

**Rationale** : cohérent avec Q2-α table rase doctrinale · zéro double-write inutile · zéro complexité transitoire · backup Q2-α + dry-run J-7 + smoke tests J+0 mitiguent risque.

### Q14 — Modèle types frontend

**Options** :
- **Q14-A** : Discriminated union TypeScript stricts (BaseItem + 7 interfaces)
- **Q14-B** : Type unique avec champs optionnels
- **Q14-C** : Validation runtime Zod

**Décision** : **Q14-A** — narrowing automatique par `kind` discriminant · type-safety stricte.

**Rationale** : compile-time check · DX excellent · cohérent avec doctrine §3.3 (kind immuable).

### Q15 — Implémentation org-scoping

**Options** :
- **Q15-A** : Middleware FastAPI seul
- **Q15-B** : Décorateur sur chaque route
- **Q15-C** : Hybride middleware + source-guards + décorateur optionnel

**Décision** : **Q15-C** — pattern PROMEOS éprouvé (7 IDOR fixes historiques) · filet automatique.

**Rationale** : middleware injecte `organisation_id` dans `request.state` · décorateur `@org_scoped` force vérification explicite sur endpoints sensibles · source-guards bloquent en CI toute query SQLAlchemy sans filter `organisation_id`.

### Q16 — Cache lectures fréquentes

**Options** :
- **Q16-A** : Pas de cache Mois 2-3 (SQLite + indexes B-tree suffisent)
- **Q16-B** : Redis dès Mois 2
- **Q16-C** : In-memory FastAPI

**Décision** : **Q16-A** — SQLite + indexes B-tree suffisent pour 150 items max démo · Redis à réévaluer V4.1 si pilots > 1000 items.

**Rationale** : zéro infra supplémentaire Mois 2-3 · performance budgets respectés sans cache.

### Q17 — Scheduler pour jobs récurrents

**Options** :
- **Q17-A** : Cron OS
- **Q17-B** : Celery + Redis
- **Q17-C** : APScheduler in-process FastAPI

**Décision** : **Q17-C refined** — APScheduler Mois 2-3 in-process FastAPI · Celery V4.1 si pilots externes > 1 instance (changé depuis Q17-C initial).

**Rationale** : zéro infra supplémentaire Mois 2-3 · cron `nightly_priority_refresh` 03:00 UTC + interval `sla_check` 15 min suffisent.

### Q18 — Stratégie de tests V4

**Options** :
- **Q18-A** : Source-guards seuls (anti-régression statique)
- **Q18-B** : Unit + intégration majoritaires
- **Q18-C** : Pyramide stratifiée 50 SG + 30 unit/intégration + 15 contract + 5 e2e

**Décision** : **Q18-C refined** — pyramide stratifiée 50/30/15/5 = 100 tests V4 totaux.

**Rationale** : SG insuffisant seul pour scoring/impact/lifecycle dynamiques (calculs complexes, transitions état, agrégations) · contract API garantit stabilité interface FE↔BE · E2E Playwright minimum car lents/flaky.

---

## 4. Architecture cible — schéma DB

### 4.1 Table cardinale `action_center_items` (Q10-A)

```sql
CREATE TABLE action_center_items (
  -- ─── Identité (4 colonnes) ───
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id          UUID NOT NULL,
  kind                     VARCHAR(20) NOT NULL,  -- discriminant polymorphic
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- ─── Métadonnées affichées (4 colonnes) ───
  title                    TEXT NOT NULL,
  summary                  TEXT,
  domain                   VARCHAR(20) NOT NULL,
  source_module            VARCHAR(40) NOT NULL,

  -- ─── Scoring Q11-A (6 colonnes) ───
  priority_score           NUMERIC(5,2) NOT NULL,
  priority_bracket         VARCHAR(2) NOT NULL,
  priority_explanation     JSONB NOT NULL,
  score_version            VARCHAR(10) NOT NULL,
  score_calculated_at      TIMESTAMPTZ NOT NULL,
  score_stale              BOOLEAN NOT NULL DEFAULT FALSE,

  -- ─── Lifecycle (4 colonnes) ───
  lifecycle_state          VARCHAR(20) NOT NULL,
  closed_at                TIMESTAMPTZ,
  closure_reason           VARCHAR(20),
  closure_payload          JSONB,

  -- ─── Owner (3 colonnes) ───
  owner_id                 UUID,
  owner_role               VARCHAR(40),
  assigned_at              TIMESTAMPTZ,

  -- ─── Dates métier (3 colonnes) ───
  detected_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sla_due_date             TIMESTAMPTZ,
  business_due_date        TIMESTAMPTZ,

  -- ─── Impact (4 colonnes) ───
  impact_current_period_eur     NUMERIC(12,2),
  impact_cumulative_eur         NUMERIC(12,2),
  impact_dimension              VARCHAR(20),
  impact_payload                JSONB,

  -- ─── Flags & Confiance (4 colonnes) ───
  next_best_action                       VARCHAR(40),
  confidence_score                       NUMERIC(3,2),
  is_irreversible_action_disabled        BOOLEAN NOT NULL DEFAULT FALSE,
  is_escalated                           BOOLEAN NOT NULL DEFAULT FALSE,

  -- ─── Refs faibles (4 colonnes nullables) ───
  site_id                  UUID,
  building_id              UUID,
  meter_id                 UUID,
  regulatory_rule_id       UUID,

  -- ─── Refs groupes Q9-B (2 colonnes nullables) ───
  duplicate_group_id       UUID REFERENCES duplicate_groups(id) ON DELETE SET NULL,
  recurrence_group_id      UUID REFERENCES recurrence_groups(id) ON DELETE SET NULL,

  -- ─── Champs spécifiques par kind (6 colonnes scalaires nullables) ───
  anomaly_detector_id              VARCHAR(50),
  decision_deadline                TIMESTAMPTZ,
  recommendation_payback_years     NUMERIC(4,1),
  deadline_authority               VARCHAR(50),
  evidence_format_expected         VARCHAR(20),
  signal_confidence_level          VARCHAR(10),

  -- ─── Contraintes CHECK doctrinales ───
  CONSTRAINT chk_kind CHECK (kind IN ('anomaly','action','decision','signal','evidence_request','deadline','recommendation')),
  CONSTRAINT chk_priority_bracket CHECK (priority_bracket IN ('P0','P1','P2','P3')),
  CONSTRAINT chk_lifecycle_state CHECK (lifecycle_state IN ('new','triaged','planned','in_progress','closed')),
  CONSTRAINT chk_closure_reason CHECK (closure_reason IS NULL OR closure_reason IN ('resolved','dismissed','not_applicable','duplicate','merged','expired')),
  CONSTRAINT chk_closure_consistency CHECK (
    (lifecycle_state = 'closed' AND closed_at IS NOT NULL AND closure_reason IS NOT NULL)
    OR (lifecycle_state != 'closed' AND closed_at IS NULL)
  ),
  CONSTRAINT chk_score_range CHECK (priority_score >= 0 AND priority_score <= 100),
  CONSTRAINT chk_confidence_range CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1))
);
```

> **Correction A1 audit Phase 0** : `chk_closure_reason` formalisée en CHECK constraint (au lieu d'un commentaire dans le brief) — alignement strict doctrine §7.1.

**Total colonnes** : ~42 colonnes scalaires + 3 JSONB. Bien inférieur au seuil de criticité PG (~250 colonnes par table).

### 4.2 Indexes — 20 indexes total (correction Phase 0 anomalie 3)

> **Correction E2 audit Phase 0** : compteur indexes aligné sur le total exhaustif réel = **20 indexes** (8 sur table cardinale + 12 sur tables filles), au lieu de "14 indexes critiques" (TL;DR brief) ou "8 indexes spécifiques" (§14 brief).

#### Indexes table cardinale `action_center_items` (8 indexes)

```sql
-- ─── Index 1 : tri par priorité (cardinal Pilotage + Référentiel) ───
CREATE INDEX idx_aci_priority_active
  ON action_center_items(organisation_id, priority_score DESC, priority_bracket)
  WHERE lifecycle_state != 'closed';

-- ─── Index 2 : filtrage par kind + domaine ───
CREATE INDEX idx_aci_kind_domain
  ON action_center_items(organisation_id, kind, domain);

-- ─── Index 3 : lifecycle workflow ───
CREATE INDEX idx_aci_lifecycle
  ON action_center_items(organisation_id, lifecycle_state, sla_due_date);

-- ─── Index 4 : items à recalculer (score_stale=true) ───
CREATE INDEX idx_aci_stale
  ON action_center_items(organisation_id, score_stale)
  WHERE score_stale = TRUE;

-- ─── Index 5 : items sans responsable (R3 escalade) ───
CREATE INDEX idx_aci_unassigned
  ON action_center_items(organisation_id, priority_bracket)
  WHERE owner_id IS NULL AND lifecycle_state != 'closed';

-- ─── Index 6 : items à clôturer récemment (vue Pilotage clôturé compact) ───
CREATE INDEX idx_aci_recent_closed
  ON action_center_items(organisation_id, closed_at DESC)
  WHERE lifecycle_state = 'closed';

-- ─── Index 7 : items par site (drawer M2 liens) ───
CREATE INDEX idx_aci_site
  ON action_center_items(organisation_id, site_id)
  WHERE site_id IS NOT NULL;

-- ─── Index 8 : owner workload ───
CREATE INDEX idx_aci_owner
  ON action_center_items(organisation_id, owner_id, lifecycle_state)
  WHERE owner_id IS NOT NULL;
```

#### Indexes tables filles (12 indexes)

| Table | Index | Pattern requête supportée |
|---|---|---|
| `action_event_log` | `idx_event_log_item` (item_id, occurred_at DESC) | Drawer M2 onglet Historique chronologique |
| `action_event_log` | `idx_event_log_org_type` (org, event_type, occurred_at DESC) | Pilotage > Journal M5 filtrage par event_type |
| `action_event_log` | `idx_event_log_correlation` (correlation_id) WHERE NOT NULL | Traces cross-actions (ex. bulk_updated) |
| `evidences` | `idx_evidence_item` (item_id, status) | Drawer M2 onglet Preuves |
| `evidences` | `idx_evidence_org` (org, expires_at) WHERE NOT NULL | Job purge preuves expirées |
| `action_links` | `idx_links_item` (item_id) | Drawer M2 onglet Liens |
| `action_links` | `idx_links_target` (target_module, target_id, relation) | Reverse lookup ("quels items pointent vers cette facture ?") |
| `action_blockers` | `idx_blocker_item_active` (item_id) WHERE resolved_at IS NULL | Affichage blockers actifs sur item |
| `action_scenarios` | `idx_scenarios_item` (item_id, display_order) | Drawer M2 onglet Scénarios (decision/recommendation) |
| `duplicate_groups` | `idx_dup_groups_org` (org, status) | Job détection doublons + suggestion fusion |
| `recurrence_groups` | `idx_rec_groups_signature` (org, source_signature, scope_signature) | Détection récurrence à la création d'item |
| `recurrence_groups` | `idx_rec_groups_status` (org, status, last_seen_at DESC) | Vue Référentiel filtrée récurrences actives |

**Total exhaustif : 20 indexes** (8 cardinale + 12 tables filles).

### 4.3 Tables filles dédiées

```sql
-- ─── Audit trail (Q12-A) ───
CREATE TABLE action_event_log (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id           UUID NOT NULL REFERENCES action_center_items(id) ON DELETE RESTRICT,
  organisation_id   UUID NOT NULL,
  event_type        VARCHAR(40) NOT NULL,
  actor_type        VARCHAR(20) NOT NULL,
  actor_id          UUID,
  actor_name        TEXT,
  event_payload     JSONB,
  occurred_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  correlation_id    UUID,
  CONSTRAINT chk_event_type CHECK (event_type IN (
    'created','state_changed','assigned','priority_changed',
    'blocker_added','blocker_removed','evidence_added','evidence_verified',
    'closed','reopened','merged','bulk_updated','exported',
    'kind_corrected','priority_recalculated'
  )),
  CONSTRAINT chk_actor_type CHECK (actor_type IN ('system','user','admin'))
);

-- Rétention RGPD : politique configurable par event_type (ADR-029 détaille)
-- Par défaut : 5 ans (CNIL recommandation pour preuves conformité)
-- Articles CNIL référencés : 5(2) limitation finalités · 30 registre traitements · 6 licéité

CREATE TABLE evidences (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id           UUID NOT NULL REFERENCES action_center_items(id) ON DELETE CASCADE,
  organisation_id   UUID NOT NULL,
  evidence_type     VARCHAR(40) NOT NULL,
  status            VARCHAR(20) NOT NULL,
  storage_uri       TEXT,
  mime_type         VARCHAR(40),
  size_bytes        BIGINT,
  uploaded_by       UUID,
  uploaded_at       TIMESTAMPTZ,
  verified_at       TIMESTAMPTZ,
  verified_by       UUID,
  expires_at        TIMESTAMPTZ,
  validation_payload JSONB,
  CONSTRAINT chk_evidence_status CHECK (status IN ('pending','uploaded','verified','expired','rejected'))
);

CREATE TABLE action_links (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id           UUID NOT NULL REFERENCES action_center_items(id) ON DELETE CASCADE,
  organisation_id   UUID NOT NULL,
  link_type         VARCHAR(40) NOT NULL,
  target_module     VARCHAR(40) NOT NULL,
  target_id         UUID NOT NULL,
  relation          VARCHAR(40) NOT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE action_blockers (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id                  UUID NOT NULL REFERENCES action_center_items(id) ON DELETE CASCADE,
  organisation_id          UUID NOT NULL,
  blocker_type             VARCHAR(40) NOT NULL,
  added_by                 UUID,
  added_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  justification            TEXT,
  expected_resolution_at   TIMESTAMPTZ,
  resolved_at              TIMESTAMPTZ,
  resolved_by              UUID,
  CONSTRAINT chk_blocker_type CHECK (blocker_type IN (
    'waiting_evidence','waiting_budget','waiting_third_party',
    'waiting_data','waiting_supplier','waiting_manager_validation','waiting_regulatory_confirmation'
  ))
);

CREATE TABLE action_scenarios (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id             UUID NOT NULL REFERENCES action_center_items(id) ON DELETE CASCADE,
  organisation_id     UUID NOT NULL,
  scenario_tag        VARCHAR(20) NOT NULL,
  title               TEXT NOT NULL,
  capex_eur           NUMERIC(12,2),
  gain_eur_per_year   NUMERIC(12,2),
  is_recommended      BOOLEAN NOT NULL DEFAULT FALSE,
  payload             JSONB,
  display_order       INT NOT NULL DEFAULT 0
);

CREATE TABLE duplicate_groups (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id          UUID NOT NULL,
  representative_item_id   UUID NOT NULL REFERENCES action_center_items(id) ON DELETE CASCADE,
  detection_method         VARCHAR(20) NOT NULL,
  detection_signature      TEXT NOT NULL,
  status                   VARCHAR(20) NOT NULL,
  suggested_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at              TIMESTAMPTZ,
  resolved_by              UUID,
  CONSTRAINT chk_dup_status CHECK (status IN ('suggested','merged','dismissed'))
);

CREATE TABLE recurrence_groups (
  id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id             UUID NOT NULL,
  domain                      VARCHAR(20) NOT NULL,
  source_signature            TEXT NOT NULL,
  scope_signature             TEXT NOT NULL,
  site_id                     UUID,
  building_id                 UUID,
  meter_id                    UUID,
  first_seen_at               TIMESTAMPTZ NOT NULL,
  last_seen_at                TIMESTAMPTZ NOT NULL,
  occurrence_count            INT NOT NULL DEFAULT 1,
  rolling_window_days         INT NOT NULL DEFAULT 90,
  representative_item_id      UUID NOT NULL REFERENCES action_center_items(id) ON DELETE RESTRICT,
  status                      VARCHAR(20) NOT NULL,
  CONSTRAINT chk_rec_status CHECK (status IN ('active','watching','closed')),
  CONSTRAINT chk_occurrence_count CHECK (occurrence_count >= 1)
);
```

**Total tables** : 1 cardinale + 7 filles = **8 tables PG-ready**.

---

## 5. Migration legacy → V4 — cutover Mois 4 (Q13-B)

### 5.1 Plan détaillé Mois 2-6

```
─────────────────────────────────────────────────────────────
Mois 2 — Création tables V4 + services V4 (lecture seule)
─────────────────────────────────────────────────────────────
  → Migration Alembic additive : create 8 tables V4
  → Implémentation services V4 (PriorityScoring, Lifecycle, ImpactAggregation, ...)
  → INTERFACE STUB regulatory_applicability_service
    (correction Phase 0 anomalie 2 — voir §11.2)
    Mois 2-3 : R6 hardcoded temporairement via stub
    Mois 4 : branchement réel quand Phase 3.5 livre l'API stable
  → Tests source-guards + unit (sans toucher au frontend legacy)
  → Coexistence : legacy continue de servir le frontend actuel
  → Aucune écriture cross-modèle (pas de double-write)

─────────────────────────────────────────────────────────────
Mois 3 — API V4 + Frontend V4 (en parallèle)
─────────────────────────────────────────────────────────────
  → Endpoints V4 /api/action-center/v4/* exposés (mais non utilisés)
  → Frontend V4 développé sur branche feature/centre-action-v4
  → Smoke tests contract API sur V4
  → Frontend actuel toujours sur API legacy
  → Validation 10 items HELIOS scoring V4 vs legacy (cohérence)

─────────────────────────────────────────────────────────────
Mois 4 — CUTOVER (jour J)
─────────────────────────────────────────────────────────────
  J-7 : Dry-run complet sur copy DB staging
  J-3 : Communication interne, fenêtre maintenance annoncée
  J-1 : BACKUP DB COMPLET (sqlite .backup + pg_dump si PG)
  J-1 : Export JSON tables legacy (Action, Anomaly, AnomalyEvent, ...)
  J-1 : Branchement réel regulatory_applicability_service (interface stub remplacée)
  J   :
    1. Activate feature flag global "centre_action_v4_enabled"
    2. Frontend bascule sur API V4
    3. Régénération seeds HELIOS + MERIDIAN format V4
    4. Smoke tests post-bascule (vues principales OK ?)
    5. 24h observation
  J+7 : Si V4 stable, communication "Mois 5 va supprimer legacy"

─────────────────────────────────────────────────────────────
Mois 5 — Suppression legacy
─────────────────────────────────────────────────────────────
  J+14 stabilité V4 confirmée :
  → DROP tables legacy (Action, ActionItem, Anomaly, AnomalyEvent, ...)
  → DELETE 1 667 LoC mortes (services + composants legacy)
  → DELETE 20 services Action/Anomaly devenus inutiles
  → Suppression endpoints legacy /api/anomalies/* etc.
  → Migration Alembic destructive avec backup pré-execution

─────────────────────────────────────────────────────────────
Mois 6 — Stabilisation + L10
─────────────────────────────────────────────────────────────
  → Backup conservé 12 mois (RGPD)
  → Documentation finale
  → Prompt Mois 7 si nécessaire (V4.1 features)
```

### 5.2 Garde-fous Q2-α (non négociable)

```
AVANT toute suppression legacy Mois 5 :

1. Backup DB binaire (sqlite .backup ou pg_dump --format=custom)
2. Export JSON par table legacy :
   - exports/legacy/action_TIMESTAMP.json
   - exports/legacy/anomaly_TIMESTAMP.json
   - exports/legacy/anomaly_event_TIMESTAMP.json
3. Vérification cardinalité : COUNT(*) avant export = COUNT(*) dans JSON
4. Stockage backup 12 mois (rétention RGPD CNIL)
5. Test de restore sur staging avant DROP final
```

**Backup Q2-α mentionné dans cet ADR** : 8× (TL;DR + §2 drivers + §3 Q13 + §5.1 Mois 4 J-1 + §5.2 + §10 critère 1 + §13 risque + §16 auto-éval) — bien au-delà des 3 minimum requis par spec ADR-026.

---

## 6. Scoring & priorisation — modèle Q11-A

### 6.1 Composantes (rappel doctrine §4.2)

| Composante | Plage | Origine |
|---|---|---|
| Gravité (`wG`) | 0-25 | ADR-022 héritée |
| Impact (`wI`) | 0-25 | ADR-022 héritée |
| Délai (`wD`) | 0-20 | ADR-022 héritée |
| Risque conformité | 0-15 | extension V4 |
| Confiance détection | 0-10 | extension V4 |
| Récurrence | 0-5 (bonus) | extension V4 |
| Sans responsable | 0-5 (additive) | extension V4 (override §5.3 doctrine) |
| Preuve manquante | 0-5 (bonus) | extension V4 |

**Total max théorique** : 105/100 (bornage final à 100 via `chk_score_range`).

### 6.2 Structure JSONB `priority_explanation`

```json
{
  "components_adr022": {
    "severity_points": 22.5,
    "impact_points": 21.0,
    "due_date_points": 19.0
  },
  "components_v4": {
    "compliance_risk_points": 12.0,
    "confidence_points": 9.0,
    "recurrence_bonus": 0.0,
    "no_owner_penalty": 0.0,
    "evidence_missing_bonus": 4.5
  },
  "total_raw": 88.0,
  "total_final": 88.0,
  "modulation_rules_applied": ["R1","R2","R5","R6"],
  "narrative": "88/100 — Bracket P0 (seuil ≥ 80). Score dominé par l'échéance proche (J+1) et le risque conformité SMÉ. Règle R6 a forcé plancher P1."
}
```

### 6.3 Job de recalcul nightly + invalidation

```python
# backend/services/priority_scoring/job.py (Mois 2 implémentation)

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=3, minute=0, id='nightly_priority_refresh')
def nightly_priority_refresh():
    """
    Cron 03:00 UTC quotidien.
    Recalcule scores marqués stale + P0/P1 actifs (filet de sécurité).
    """
    db = get_session()
    stale = db.query(ActionCenterItem).filter(score_stale=True).all()
    p0p1_active = db.query(ActionCenterItem).filter(
        priority_bracket.in_(["P0","P1"]),
        lifecycle_state != "closed"
    ).all()
    for item in set(stale + p0p1_active):
        recompute_score(db, item)


@scheduler.scheduled_job('interval', minutes=15, id='sla_check')
def sla_check():
    """
    Toutes les 15 min : détection P0/P1 SLA dépassé sans notification 24h.
    """
    pass  # Implémentation Mois 3 (avec notification system)
```

### 6.4 Événements d'invalidation (12 events doctrine §4.3)

Chacun déclenche `score_stale = TRUE` :

```
lifecycle_state_changed · owner_changed · due_date_changed · impact_changed
blocker_added · blocker_removed · evidence_added · evidence_expired
confidence_changed · recurrence_group_updated · regulatory_applicability_changed
nightly_priority_refresh (filet de sécurité)
```

Recalcul **synchrone** pour high-impact (lifecycle, owner, due_date) → résultat visible immédiatement.
Recalcul **asynchrone** pour low-impact (confidence, recurrence) → batch nightly.

---

## 7. API contracts cardinaux

### 7.1 Endpoint Pilotage — liste prioritaire

```http
GET /api/action-center/pilotage
Headers: Authorization: Bearer <token>
Query: ?periode=7j&filtre=all|p0p1|unassigned|to_qualify|evidence_waiting|sla_overdue

Response 200:
{
  "summary": {
    "active_items_count": 8,
    "p0_p1_count": 4,
    "unassigned_count": 3,
    "at_risk_euro_12m": 52000,
    "secured_euro_12m": 128000,
    "sla_overdue_count": 2
  },
  "sections": {
    "file_prioritaire": { "count": 5, "items": [...] },
    "jalons_a_preparer": { "count": 2, "items": [...] },
    "a_surveiller": { "count": 1, "items": [...] },
    "clos_recemment": { "count": 2, "items": [...] }
  },
  "doctrine_version": "v0.3",
  "calculated_at": "2026-05-14T07:18:00Z"
}
```

**Performance budget** : < 100ms pour 150 items max.

### 7.2 Endpoint item détail (drawer M2)

```http
GET /api/action-center/items/{id}
Query: ?include=evidence,event_log,scenarios,links,blockers&mode=standard|audit

Response 200:
{
  "id": "uuid",
  "kind": "action",
  "title": "Audit énergétique SMÉ Toulouse...",
  "priority_score": 88.0,
  "priority_bracket": "P0",
  "priority_explanation": { ... },
  "lifecycle_state": "triaged",
  "owner": { "id": "...", "name": "J. Martin", "role": "DAF" },
  "next_best_action": "Arbitrer le scénario B",
  "sla_due_date": "2026-05-11T00:00:00Z",
  "business_due_date": "2026-10-11T00:00:00Z",
  "impact": {
    "estimated": { "amount_eur": 49000, "period": "annual", "source": "Modèle V4 scenario B", "formula": "320 MWh à 153 €/MWh" },
    "at_risk": { "amount_eur": 7500, "period": "one_shot", "source": "Décret 2014-1393 art. 5", "formula": "15 €/m² × 500 m²" }
  },
  "blockers": [...],
  "evidence": [...],
  "event_log": [...],
  "scenarios": [...],
  "links": [...]
}
```

**Performance budget** : < 200ms (drawer M2 ouvre vite).

### 7.3 Endpoint impact (drawer M4)

```http
GET /api/action-center/impact
Query: ?periode=12m&perimetre=helios

Response 200:
{
  "net_result": {
    "secured_eur": 128000, "at_risk_eur": 52000,
    "actions_processed": 146, "items_created": 214,
    "resolution_rate_pct": 68, "median_resolution_days": 4.2
  },
  "dimensions": {
    "estimated":  { "amount_eur": 82000, "items": 11, "source": "Modèle V4", "formula": "Σ best_case_gain" },
    "at_risk":    { "amount_eur": 52000, "items": 8, "source": "RegOps + Bill Intel", "formula": "Σ exposure_amount" },
    "secured":    { "amount_eur": 34000, "items": 14, "source": "ActionCenter exec", "formula": "Σ in_progress.expected" },
    "realized":   { "amount_eur": 128000, "items": 67, "source": "Closure log + preuves", "formula": "Σ realized_gain" },
    "lost":       { "amount_eur": 6800, "items": 5, "source": "Closure log", "formula": "Σ where closure ∈ {expired, dismissed}" },
    "blocked":    { "amount_eur": 23000, "items": 4, "source": "Blockers actifs", "formula": "Σ where blockers ≠ ∅" }
  },
  "roi": { "ratio": 4.3, "label": "ROI 12 mois" },
  "by_domain": [...],
  "top_contributors": [...],
  "trajectory": [...]
}
```

**Performance budget** : < 300ms (agrégations cross-items).

### 7.4 Endpoints PATCH (mutations)

```http
PATCH /api/action-center/items/{id}/lifecycle    # Transition d'état
PATCH /api/action-center/items/{id}/owner        # Réassignation
PATCH /api/action-center/items/{id}/blockers     # Ajout/résolution blocker
PATCH /api/action-center/items/{id}/correct-kind # ADMIN UNIQUEMENT (audit trail forcé)
POST  /api/action-center/items/{id}/close        # Clôture avec closure_reason
```

Toutes mutations trigger un event dans `action_event_log` automatiquement. Performance budget mutations : **< 150ms**.

---

## 8. Types TypeScript frontend (Q14-A)

```typescript
// types/action_center.ts

type Kind = 'anomaly' | 'action' | 'decision' | 'signal'
  | 'evidence_request' | 'deadline' | 'recommendation';

type LifecycleState = 'new' | 'triaged' | 'planned' | 'in_progress' | 'closed';
type PriorityBracket = 'P0' | 'P1' | 'P2' | 'P3';
type Domain = 'conformite' | 'facturation' | 'consommation' | 'achat' | 'patrimoine' | 'data';

interface BaseItem {
  id: string;
  organisation_id: string;
  kind: Kind;
  title: string;
  summary?: string;
  domain: Domain;
  source_module: string;
  priority_score: number;
  priority_bracket: PriorityBracket;
  priority_explanation: PriorityExplanation;
  lifecycle_state: LifecycleState;
  owner?: Owner;
  sla_due_date?: string;
  business_due_date?: string;
  detected_at: string;
  next_best_action: string;
  confidence_score?: number;
  is_irreversible_action_disabled: boolean;
  is_escalated: boolean;
  duplicate_group_id?: string;
  recurrence_group_id?: string;
}

interface AnomalyItem extends BaseItem { kind: 'anomaly'; anomaly_detector_id: string; recurrence_count?: number; }
interface ActionItem extends BaseItem { kind: 'action'; }
interface DecisionItem extends BaseItem { kind: 'decision'; decision_deadline?: string; }
interface SignalItem extends BaseItem { kind: 'signal'; anomaly_detector_id: string; signal_confidence_level: 'low' | 'medium' | 'high'; }
interface EvidenceRequestItem extends BaseItem { kind: 'evidence_request'; evidence_format_expected: string; }
interface DeadlineItem extends BaseItem { kind: 'deadline'; deadline_authority: string; }
interface RecommendationItem extends BaseItem { kind: 'recommendation'; recommendation_payback_years?: number; }

type ActionCenterItem =
  | AnomalyItem | ActionItem | DecisionItem | SignalItem
  | EvidenceRequestItem | DeadlineItem | RecommendationItem;

// Narrowing automatique par discriminant 'kind'
function renderItem(item: ActionCenterItem) {
  switch (item.kind) {
    case 'anomaly':
      return <AnomalyCard detector={item.anomaly_detector_id} />;
    case 'recommendation':
      return <RecoCard payback={item.recommendation_payback_years} />;
    // ... 5 autres cases
  }
}
```

---

## 9. Sécurité org-scoping native (Q15-C)

### 9.1 Middleware FastAPI global

```python
# backend/middleware/org_scoping.py

from fastapi import Request, HTTPException

class OrgScopingMiddleware:
    async def __call__(self, request: Request, call_next):
        org_id = extract_org_id_from_token(request)
        if not org_id:
            raise HTTPException(401, "Missing organisation context")
        request.state.organisation_id = org_id
        with logger.contextualize(org_id=org_id, route=request.url.path):
            response = await call_next(request)
        return response
```

### 9.2 Décorateur `@org_scoped` pour endpoints sensibles

```python
# backend/decorators/security.py

def org_scoped(func):
    """Force que l'organisation_id soit présent dans toutes les queries."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = next((a for a in args if isinstance(a, Request)), None)
        if not request or not hasattr(request.state, 'organisation_id'):
            raise HTTPException(403, "org-scoping check failed")
        return await func(*args, **kwargs)
    return wrapper

@router.get("/api/action-center/items/{item_id}")
@org_scoped
async def get_item(item_id: UUID, request: Request, db: Session = Depends(get_db)):
    item = db.query(ActionCenterItem).filter(
        ActionCenterItem.id == item_id,
        ActionCenterItem.organisation_id == request.state.organisation_id
    ).first()
    if not item:
        raise HTTPException(404)
    return item
```

### 9.3 Source-guards automatiques

```python
# tests/source_guards/test_org_scoping_v4.py

import re
from pathlib import Path

def test_all_action_center_queries_have_org_scoping():
    """Vérifie que toutes les queries SQLAlchemy sur ActionCenterItem incluent un filter organisation_id."""
    file_pattern = "backend/services/action_center/**/*.py"
    queries = []
    for path in Path(".").glob(file_pattern):
        content = path.read_text()
        matches = re.findall(r'(\.query\(ActionCenterItem\).*?\.(first|all|one|count)\(\))', content, re.DOTALL)
        for match in matches:
            if 'organisation_id' not in match[0]:
                queries.append((path, match[0][:200]))
    assert not queries, f"Queries missing org_scoping: {queries}"
```

---

## 10. Stratégie tests V4 stratifiée (Q18-C refined)

### 10.1 Pyramide cardinale 50/30/15/5

```
─────────────────────────────────────
50 SOURCE-GUARDS    (~50% des tests)
─────────────────────────────────────
  Vérifient patterns statiques.
  Pas de comportement métier dynamique.

─────────────────────────────────────
30 UNIT + INTÉGRATION (~30%)
─────────────────────────────────────
  PriorityScoringService (R1-R6)
  LifecycleStateMachine (5 états × 12 transitions)
  ImpactAggregationService (6 dimensions sans double comptage)
  RecurrenceDetector + DuplicateDetector
  EvidenceVerifier
  ActionEventLog complétude

─────────────────────────────────────
15 CONTRACT API (~15%)
─────────────────────────────────────
  /pilotage retourne summary cohérent
  POST /items rejette payload invalide (4xx)
  /correct-kind nécessite admin role (403 sinon)
  /audit-trail respecte org-scoping (404 cross-org)
  /impact retourne 6 dimensions toujours
  Performance budgets respectés (assertions sur durée)

─────────────────────────────────────
5 E2E PLAYWRIGHT (~5%)
─────────────────────────────────────
  Pilotage > Décisions affiche 7 kinds correctement
  Drawer M2 ouvre/ferme/met à jour score
  Impact Drawer M4 exporte CSV correctement
  Bascule mode standard ↔ mode audit
  Compteur P0/P1 reste aligné
```

### 10.2 Décomposition des 50 source-guards (correction Phase 0 anomalie 1)

> **Correction B7 audit Phase 0** : décomposition explicite des 50 SG total = **6 SG cardinaux nouveaux V4 + 8 SG existants GARDE + 36 SG dérivés** (un par pattern). Validé Amine.

#### 6 SG cardinaux nouveaux V4 (issues L1 §3.8)

| # | Test | Couvre |
|---|---|---|
| 1 | `test_briefing_v4_anomalies.py` | Bug Briefing 500 résolu (P0) |
| 2 | `test_action_center_org_scoping_v4.py` | Fuite ADR-027 résolue (P0 sécu) |
| 3 | `test_kind_immutability_v4.py` | Doctrine §3.3 immutabilité kind |
| 4 | `test_priority_score_modulation_rules_v4.py` | R1-R6 doctrine §5 |
| 5 | `test_recurrence_vs_duplicate_groups_v4.py` | Q9-B doctrine §6 |
| 6 | `test_lifecycle_state_fr_labels_v4.py` | Mode standard §7.1 |

#### 8 SG existants GARDE (L1 §3.8)

| # | Test | Statut |
|---|---|---|
| 1 | `test_bill_anomaly_yaml_runtime_consistency_source_guards.py` | GARDE |
| 2 | `test_navigation_badges_source_guards.py` | GARDE |
| 3 | `test_phase78_p0_fixes_source_guards.py` | GARDE |
| 4 | `test_regulatory_rates_internal_doctrine_filter_source_guards.py` | GARDE |
| 5 | `test_tracetooltip_termid_yaml_coherence_source_guards.py` | GARDE |
| 6 | `test_phase81_lot_regops_source_guards.py` | GARDE |
| 7 | `test_phase82_lot_sec_ci_source_guards.py` | GARDE |
| 8 | `test_regulatory_sources_yaml_structure_source_guards.py` | GARDE |

#### 36 SG dérivés (un par pattern V4)

Patterns à couvrir (1 SG par ligne) :

```
Org-scoping :
  - test_no_query_action_center_items_without_org_filter
  - test_no_query_action_event_log_without_org_filter
  - test_no_query_evidences_without_org_filter
  - test_no_query_action_links_without_org_filter
  - test_no_query_action_blockers_without_org_filter
  - test_no_query_action_scenarios_without_org_filter
  - test_no_query_duplicate_groups_without_org_filter
  - test_no_query_recurrence_groups_without_org_filter
  - test_all_v4_routes_have_org_scoped_decorator
  - test_org_scoping_middleware_registered_on_v4_router

Libellés FR strict (mode standard) :
  - test_no_technical_codes_in_drawer_standard_mode
  - test_no_technical_codes_in_pilotage_standard_mode
  - test_no_technical_codes_in_referentiel_standard_mode
  - test_no_technical_codes_in_journal_standard_mode
  - test_no_technical_codes_in_impact_standard_mode
  - test_lifecycle_states_fr_only_in_standard_mode
  - test_closure_reasons_fr_only_in_standard_mode
  - test_blocker_types_fr_only_in_standard_mode
  - test_event_types_fr_only_in_standard_mode
  - test_kind_badges_fr_only_in_standard_mode

Doctrine compliance :
  - test_no_fusionner_label_on_recurrence_group
  - test_no_regrouper_label_on_duplicate_group
  - test_kind_immutable_outside_admin_endpoint
  - test_priority_score_persisted_not_computed_inline
  - test_no_double_counting_in_impact_dimensions
  - test_doctrine_v02_referenced_in_metier_tests

Code hygiene :
  - test_no_TODO_FIXME_XXX_HACK_in_v4_code
  - test_no_console_log_in_v4_frontend
  - test_no_print_statements_in_v4_backend
  - test_all_pydantic_schemas_versioned

Visual cardinaux :
  - test_7_kinds_visually_distinct_in_css
  - test_4_priority_brackets_distinct_colors
  - test_5_lifecycle_states_distinct_indicators
  - test_6_impact_dimensions_distinct_colors

Performance :
  - test_indexes_match_query_patterns_v4
  - test_no_n_plus_1_in_v4_pilotage_endpoint
  - test_no_n_plus_1_in_v4_drawer_endpoint
```

**Total** : 6 + 8 + 36 = **50 source-guards** dans la pyramide V4.

### 10.3 Justification stratification

- **Source-guards seuls insuffisants** pour scoring/impact/lifecycle dynamiques (calculs complexes, transitions état, agrégations) → **unit/intégration obligatoires** (30%).
- **Contract API tests** garantissent stabilité interface FE↔BE → **15%** pour les 6-8 endpoints cardinaux.
- **E2E Playwright minimum** car lents et flaky → seulement 5 scénarios critiques.

---

## 11. Performance budgets

| Endpoint | Budget | Justification |
|---|---|---|
| `GET /pilotage` | **< 100ms** | Vue d'entrée, doit être instantanée |
| `GET /items/{id}` (sans includes) | **< 50ms** | Index B-tree PK |
| `GET /items/{id}?include=...` (drawer M2) | **< 200ms** | 4-5 joins indexés |
| `GET /impact` (drawer M4) | **< 300ms** | Agrégations cross-items |
| `PATCH /items/{id}/lifecycle` | **< 150ms** | Mutation + 2 inserts (event log + score recalc) |
| `POST /items` (création) | **< 100ms** | 1 insert + 1 event_log entry |
| `GET /audit-trail/{item_id}` (paginated) | **< 100ms** | Index composite |

**Tous mesurés via** : `pytest-benchmark` + `prometheus-fastapi-instrumentator`.

---

### 11.2 Interface stub `regulatory_applicability_service` (correction Phase 0 anomalie 2)

> **Correction D3 audit Phase 0** : ajout mention explicite de l'interface stub Mois 2-3 attente Phase 3.5. Validé Amine.

**Contexte** : sprint Phase 3.5 SynthèseStratégique en cours en parallèle dans `backend/regops/` (10+ fichiers Phase 0 §11.1). V4 doit consommer `regulatory_applicability_service` comme SoT unique pour la règle R6 doctrine §5.6 (Conformité applicable → plancher P1).

**Stratégie** :

```python
# backend/services/regulatory_applicability_service.py
# Interface stub Mois 2-3 (correction Phase 0 anomalie 2)
# À remplacer Mois 4 par implémentation réelle Phase 3.5

from typing import Literal
from datetime import date

ApplicabilityStatus = Literal["APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"]

def is_applicable(rule_code: str, site_id: str) -> ApplicabilityStatus:
    """
    STUB Mois 2-3 : retourne UNKNOWN par défaut → R6 hardcoded fallback.
    Mois 4 : branché sur backend/regops/ Phase 3.5 livré.
    """
    # Hardcoded matrix Mois 2-3 pour démo HELIOS
    HARDCODED_RULES = {
        "DT_2030": "APPLICABLE",  # Décret Tertiaire 2030
        "BACS": "APPLICABLE",
        "APER": "UNKNOWN",
        "AUDIT_SME": "APPLICABLE",
        "OPERAT": "APPLICABLE",
    }
    return HARDCODED_RULES.get(rule_code, "UNKNOWN")

def get_deadline(rule_code: str, site_id: str) -> date | None:
    """STUB Mois 2-3 : matrice hardcoded démo."""
    HARDCODED_DEADLINES = {
        "DT_2030": date(2030, 12, 31),
        "BACS": date(2030, 12, 31),
        "AUDIT_SME": date(2026, 10, 11),
        "OPERAT": date(2026, 5, 17),
    }
    return HARDCODED_DEADLINES.get(rule_code)
```

**Calendrier branchement réel** :
- Mois 2-3 : stub hardcoded ci-dessus (R6 utilise UNKNOWN → pas de plancher P1 forcé sauf rules hardcoded)
- Mois 4 J-1 : implémentation Phase 3.5 testée et stable → remplacement du stub par appel direct à `backend/regops/regulatory_applicability_service.py`
- Mois 4 J : cutover V4 utilise l'API réelle pour R6
- Tests V4 source-guards vérifient que stub est bien remplacé après Mois 4 (via assertion sur module path importé)

**Risque mitigation** : si Phase 3.5 retardé > Mois 4, V4 reste fonctionnel avec stub hardcoded (matrice démo HELIOS suffit pilots Q3 2026).

---

## 12. Mapping legacy → V4 (cohérent avec L1)

| Legacy | V4 cible | Verdict L1 | ADR ref |
|---|---|---|---|
| `Action`, `ActionItem`, `ActionPlanItem` (modèles) | `ActionCenterItem` polymorphique | SUPPRIME (×3) | ADR-025 §4.1 |
| `Anomaly` (modèle KB) | `ActionCenterItem` avec `kind='anomaly'` | MIGRE | ADR-025 §4.1 |
| `AnomalyEvent` (modèle) | `action_event_log` polymorphe | REMPLACE | ADR-025 §4.3 + ADR-029 |
| `AnomalyDetector` (modèle) | Référencé via `anomaly_detector_id` VARCHAR | GARDE (légère réf) | ADR-025 §4.1 |
| 18 tables DB (8 vivantes + 10 vides `action_plan_*`) | 8 tables V4 | SUPPRIME (×10) MIGRE (×8) | ADR-025 §4 + ADR-026 |
| 8 enums sévérité | 1 enum `severity` V4 | SUPPRIME (×7) MIGRE (×1) | ADR-025 §4.1 |
| 4 mappings sévérité → priorité | `priority_explanation.modulation_rules_applied` | REMPLACE | ADR-025 §6 |
| 6 vocabulaires statuts | `lifecycle_state` enum V4 (5 valeurs) | SUPPRIME (×5) MIGRE (×1) | ADR-025 §4.1 + ADR-028 |
| 63 endpoints `/api/anomalies/*`, `/api/action-plans/*`, etc. | 12 endpoints `/api/action-center/*` unifiés | SUPPRIME (×51) REMPLACE (×12) | ADR-025 §7 |
| 20 services Action/Anomaly | 8 services V4 (PriorityScoring, Lifecycle, Impact, ...) | MIGRE (×6) SUPPRIME (×14) | ADR-025 §6 |
| 5 schemas Pydantic | 8 schemas V4 (BaseItem + 7 kinds) | MIGRE | ADR-025 §8 |
| 1 667 LoC mortes frontend | Suppression Mois 5 | SUPPRIME | ADR-025 §5 + ADR-026 |
| 8 source-guards existants | Réutilisés + 6 nouveaux V4 + 36 dérivés = 50 SG total | GARDE | ADR-025 §10.2 |
| Seeds HELIOS/MERIDIAN | Régénérés format V4 Mois 4 | RÉGÉNÈRE | ADR-025 §5 + ADR-026 |

**Cohérence avec L1** : tous les 86 verdicts L1 sont satisfaits par cette architecture. **Aucune décision orpheline**.

---

## 13. Coexistence Mois 2-3 (zéro double-write)

```
                Mois 2-3
─────────────────────────────────────────────
│  Frontend legacy (24 fichiers actifs)       │
│         ▼                                   │
│  API legacy /api/anomalies/* etc.           │
│         ▼                                   │
│  Models legacy (Action, Anomaly, ...)       │
│         ▼                                   │
│  Tables legacy (18 tables)                  │
─────────────────────────────────────────────

      EN PARALLÈLE (lecture seule)

─────────────────────────────────────────────
│  Branche feature/centre-action-v4 (FE)      │
│         ▼                                   │
│  API V4 /api/action-center/v4/*             │
│  (déployée mais non utilisée)               │
│         ▼                                   │
│  Models V4 (ActionCenterItem, ...)          │
│         ▼                                   │
│  Tables V4 (8 tables vides en attente)      │
─────────────────────────────────────────────
```

**Aucune écriture cross-modèle.** Pas de service qui écrit dans les 2 modèles. Pas de scripts de réconciliation. Pas de double-write.

Les seeds V4 sont **vides** Mois 2-3 ; elles seront **régénérées** à partir de seeds canoniques HELIOS/MERIDIAN au moment du cutover Mois 4.

**Bénéfice** : zéro complexité transitoire. Les développeurs V4 peuvent itérer sans risque de casser le frontend legacy.

---

## 14. Risques identifiés et mitigations

| Risque | Probabilité | Impact | Mitigation ADR |
|---|---|---|---|
| Cutover Mois 4 échoue | Faible | Élevé | Backup Q2-α + dry-run J-7 + smoke tests J+0 (§5.1) |
| Performance dégrade après V4 (single-table avec 42 cols) | Faible | Moyen | 8 indexes B-tree sur table cardinale + 12 indexes tables filles + budget < 100ms documenté (§11) |
| Score V4 incohérent vs legacy (validation) | Moyen | Moyen | Tests unit complets §10.1 R1-R6 + comparaison manuelle 10 items HELIOS Mois 3 |
| RGPD non conforme sur audit_event_log | Faible | Élevé | Table dédiée Q12-A + politique rétention configurable + ADR-029 dédié |
| Bug bloqueur dans 5 migrations `.original-autogenerate` | Élevé (signal L1) | Élevé | Investigation Mois 2 priorité 0 + rollback strategy documentée |
| Org-scoping leak via nouvelle route oubliée | Moyen | Très élevé (P0 sécu) | Middleware FastAPI global + décorateur + 50 source-guards (§9 + §10.2) + ADR-027 |
| Bug Briefing 500 lié refonte | Moyen | Élevé | Investigation P0 Mois 2 séparée + branchement V4 désactivable via feature flag |
| Phase 3.5 retardé > Mois 4 | Moyen | Faible | Stub hardcoded §11.2 reste fonctionnel pilots Q3 2026 |

---

## 15. Renvois ADR-026 / 027 / 028 / 029

ADR-025 **référence** mais ne détaille pas :

- **ADR-026 Migration data** — **Accepted** (2026-05-14) — voir [`docs/dev/L3_ADR-026_migration_data.md`](L3_ADR-026_migration_data.md) — manuel de bascule sécurisé · 9 invariants I1-I9 (dont I9 cardinal backup hors Git · receipt sanitizé) · 7 arbitrages Q19-Q25 · 6 scripts (backup triple artefact + export JSON + manifest + regen seeds Python idempotent + dry-run + restore) · cardinaux 173 rows data réelle (action_items 35 + bill_anomaly 52 + anomaly KB 86) · cutover Mois 4 + STOP GATE J+14 manuel
- **ADR-027 Sécurité org-scoping** — **Accepted** (2026-05-14) — voir [`docs/dev/L4_ADR-027_securite_org_scoping.md`](L4_ADR-027_securite_org_scoping.md) — manuel défensif Centre d'Action V4 · 11 invariants IS1-IS11 (dont IS11 cardinal pattern repository) · 7 arbitrages Q26-Q32 · 8 menaces M1-M8 cartographiées · IDOR matrix 288 cellules · 50 source-guards CI custom (6 catégories) · CI gate Bandit + Semgrep + gitleaks + pip-audit · audit pen-test J-7 Mois 4
- **ADR-028 Lifecycle states** — **Accepted** (2026-05-14) — voir [`docs/dev/L5_ADR-028_lifecycle_states.md`](L5_ADR-028_lifecycle_states.md) — manuel comportement item · 11 invariants IL1-IL11 (dont IL4/IL5/IL7 cardinaux Amine) · 7 arbitrages Q33-Q39 · state machine 5 états × 10 transitions strictes · 6 closure_reasons révisés (avenant doctrinal v0.2 → v0.3 inclus) · 56 tests planifiés
- **ADR-029 Evidence + audit trail** — **Accepted** (2026-05-14) — voir [`docs/dev/L6_ADR-029_evidence_audit_trail.md`](L6_ADR-029_evidence_audit_trail.md) — manuel des preuves et de la traçabilité · 9 invariants IE1-IE9 (dont IE9 cardinal magic bytes MIME) · 7 arbitrages Q40-Q46 · 16 event_types × 3 catégories rétention RGPD (compliance 5y / business 3y / system 1y) · 16 schemas Pydantic v1 versionnés · 8 articles CNIL référencés (5(1)(b), 5(1)(e), 5(2), 6, 15, 17, 30, 32) · 40+ tests planifiés · **dernier ADR Mois 1**

> **Note d'extension event_types (renvoi aval ADR-029 §6.3)** : le `CHECK constraint action_event_log.event_type` posé au §4.3 ADR-025 avec **15 valeurs** est étendu par ADR-029 à **16 valeurs** alignées doctrine v0.3 (`assigned` → `owner_changed` · `merged` → `closed_via_merged_duplicate` · `closed` → 3 variantes `closed_with_evidence` + `closed_via_merged_duplicate` + `closed_via_resolved_via_recurrence`). Cette **extension aval est acceptée par convention** : ADR-029, plus récent et aligné doctrine v0.3 + ADR-028, supersède la liste préliminaire d'ADR-025 §4.3 sans nécessiter de réouverture de cet ADR. Le squelette §4.3 reste la référence pour les colonnes + indexes ; la liste `event_type` autoritative est désormais ADR-029 §6.1.

---

## 16. Critères de validation finale (7 critères Amine)

| # | Critère | Vérifié par |
|---|---|---|
| 1 | **L'architecture respecte Q2-α table rase** | §5 Migration cutover sec Mois 4 + backup obligatoire 8× mentionné. Aucune procédure de migration data (POC seeds uniquement) |
| 2 | **Le modèle reste simple et performant** | §4.1 single-table ~42 colonnes + §4.3 7 tables filles dédiées + §4.2 **20 indexes total** (8 cardinale + 12 tables filles) + §11 performance budgets < 100ms documentés |
| 3 | **L'audit trail est défendable (RGPD)** | §4.3 `action_event_log` table dédiée + politique rétention configurable + références CNIL articles 5(2), 30, 6 + survit à clôture item (ON DELETE RESTRICT) |
| 4 | **Le score est triable en SQL** | §4.1 4 colonnes scalaires `priority_score NUMERIC(5,2)` + `priority_bracket VARCHAR(2)` + §4.2 index `idx_aci_priority_active` B-tree natif |
| 5 | **La sécurité org-scoping est native** | §9 middleware FastAPI global + décorateur `@org_scoped` + **50 source-guards (6 nouveaux V4 + 8 existants + 36 dérivés)** + `organisation_id` sur 8 tables + ADR-027 référencé |
| 6 | **La transition ne crée pas un mois de double-write inutile** | §13 coexistence Mois 2-3 sans écriture cross-modèle + §5.1 cutover sec Mois 4 + cohérence avec Q2-α §5.2 garde-fous |
| 7 | **Les tests couvrent code + métier + API** | §10 pyramide stratifiée 50 SG (code) + 30 unit/intégration (métier dynamique) + 15 contract (API) + 5 e2e (UX critique) |

---

## 17. Conséquences

### 17.1 Positives

- **Architecture unifiée** simplifie maintenance long-terme (1 modèle polymorphique vs 9 modèles legacy parallèles)
- **Performance < 100ms documentée** sur Pilotage (vue d'entrée) grâce à 20 indexes ciblés
- **RGPD-friendly** : `action_event_log` table dédiée avec rétention configurable + références CNIL explicites
- **Org-scoping native** : middleware + décorateur + 50 SG bloquent en CI toute fuite cross-org (résout fuite L1 §6 P0 sécu)
- **Type-safety stricte** : discriminated unions TypeScript narrowing automatique par kind
- **Cutover sec Mois 4** : zéro complexité transitoire de double-write · backup Q2-α non négociable
- **Préservation Phase 3.5** : interface stub Mois 2-3 ne casse pas le sprint en cours
- **Tests stratifiés** : 100 tests V4 couvrent code (50 SG) + métier dynamique (30 unit/intégration) + API (15 contract) + UX (5 e2e)

### 17.2 Négatives

- **Refactor important Mois 2-3** : 9 modèles legacy → 1 polymorphique demande migration data 173 rows + adaptateurs cross-module
- **Période de coexistence à maintenir** Mois 2-3 : 2 architectures parallèles dans le repo (mais sans double-write)
- **Migration cutover assumée** : risque résiduel sur cutover J · mitigé par dry-run J-7 + backup J-1 + smoke tests J+0
- **Stub Phase 3.5 à remplacer** Mois 4 : dépendance externe sprint parallèle (mais stub fonctionnel pilots Q3 2026)
- **Investissement test initial Mois 2-3** : 100 tests V4 demandent ~10-15 j-h de production avant Mois 4

### 17.3 Neutres

- **Single-table inheritance assumée** : choix architectural standard PostgreSQL · 42 colonnes < seuil criticité 250
- **APScheduler in-process** Mois 2-3 → Celery V4.1 si pilots externes : trade-off zéro infra vs scalabilité différée
- **Pas de cache Mois 2-3** : SQLite + indexes B-tree suffisent pour 150 items max démo · Redis reportable V4.1
- **Audit trail détaillé** : volume `action_event_log` croît avec usage · purge par politique rétention CNIL (5 ans par défaut)

---

## 18. Métadonnées ADR

```yaml
adr_number: 025
title: Architecture Centre d'Action V4 - schéma DB et patterns techniques
version: v1.0
status: Accepted
date: 2026-05-14
deciders:
  - Amine (PROMEOS founder)
  - Claude (architecture co-pilot)
sessions_cadrage: ["2026-05-13", "2026-05-14"]
arbitrages_q10_q18:
  Q10: A_refined  # single-table scope strict + 7 tables filles
  Q11: A          # 4 colonnes scalaires + JSONB explanation
  Q12: A          # table dédiée action_event_log
  Q13: B          # cutover sec Mois 4 (changé depuis Q13-A)
  Q14: A          # discriminated union TypeScript
  Q15: C          # hybride middleware + source-guards + décorateur
  Q16: A          # pas de cache Mois 2-3
  Q17: C_refined  # APScheduler Mois 2-3 → Celery V4.1
  Q18: C_refined  # pyramide stratifiée 50/30/15/5
constraints_doctrinales:
  - Q1-A : ActionCenterItem polymorphique unique
  - Q2-α : table rase + backup obligatoire (×8 dans cet ADR)
  - Q3-C : scoring ADR-022 base + extensions V4
  - Q4-A : consommer regulatory_applicability_service comme SoT
  - Q5-B : job pull idempotent depuis compliance findings
  - Q6-A : Mois 1 docs only (cet ADR inclus)
  - Q7-A : rendu strict par kind
  - Q8-C : score persisté + invalidation event-driven
  - Q9-B : tables séparées duplicate/recurrence groups
performance_budgets:
  pilotage: 100ms
  item_detail_no_includes: 50ms
  item_detail_with_includes: 200ms
  impact: 300ms
  mutation: 150ms
  audit_trail: 100ms
total_tests_planned: 100
  source_guards: 50  # 6 cardinaux nouveaux + 8 existants + 36 dérivés
  unit_integration: 30
  contract_api: 15
  e2e_playwright: 5
total_tables: 8
total_indexes: 20  # 8 cardinale + 12 tables filles
backup_q2_alpha_mentions: 8
corrections_phase0_appliquees:
  - "B7: décomposition 50 SG explicitée §10.2"
  - "D3: interface stub regulatory_applicability_service ajoutée §11.2"
  - "E2: compteur indexes aligné à 20 (8 cardinale + 12 tables filles) §4.2 + §16"
next_adr: ADR-026 Migration data legacy → V4
```

---

## 19. Auto-évaluation QA ADR-025

### 19.1 Critères de validation finale (7/7 requis)

- [x] 1. **Architecture respecte Q2-α table rase** — §5 cutover sec + backup mentionné **8×** (TL;DR §1, §2 drivers, §3 Q13, §5.1 Mois 4 J-1, §5.2, §16 critère 1, §14 risque, §19)
- [x] 2. **Modèle reste simple et performant** — §4.1 ~42 colonnes + §4.3 7 tables filles + §4.2 **20 indexes total** + §11 budgets < 100ms
- [x] 3. **Audit trail défendable RGPD** — §4.3 `action_event_log` table dédiée + rétention configurable + survie post-clôture (`ON DELETE RESTRICT`)
- [x] 4. **Score triable en SQL** — §4.1 4 colonnes scalaires + §4.2 index B-tree `idx_aci_priority_active`
- [x] 5. **Sécurité org-scoping native** — §9 middleware + `@org_scoped` + **50 SG (6 nouveaux + 8 existants + 36 dérivés)** + `organisation_id` partout
- [x] 6. **Zéro double-write inutile** — §13 coexistence Mois 2-3 sans écriture cross-modèle + §5 cutover sec
- [x] 7. **Tests couvrent code + métier + API** — §10 pyramide 50 SG + 30 unit/intégration + 15 contract + 5 e2e

### 19.2 Cohérence cross-documents (Phase 0 confirmé)

- [x] Cohérence doctrine v0.3 — 9/9 vérifications (Phase 0 §A · doctrine v0.2 au moment de l'audit, bumped v0.3 dans commit L5 cohérent)
- [x] Cohérence L1 86 verdicts — 7/7 vérifications (Phase 0 §B)
- [x] Cohérence maquettes M1-M5 — 5/5 vérifications (Phase 0 §C)
- [x] Cohérence sprint Phase 3.5 préservée — 4/4 vérifications (Phase 0 §D)

### 19.3 Conformité spec brief

- [x] Tous les schémas SQL §4 sont syntaxiquement valides PG-ready
- [x] Tous les indexes §4.2 ont une justification de query pattern (table avec colonne "Pattern requête supportée")
- [x] Toutes les contraintes CHECK sont alignées avec doctrine §7.1 (correction Phase 0 A1 : `chk_closure_reason` formalisée)
- [x] Tous les renvois ADR-026/027/028/029 sont scopés (§15)
- [x] Backup Q2-α mentionné **8 fois** (≥ 3 requis)

### 19.4 Conformité prompt L2

- [x] 9 arbitrages Q10-Q18 actés et documentés (§3)
- [x] §16 du brief intégré (7 critères validation Amine)
- [x] Format MADR respecté (Status, Date, Deciders, Branch, Related ADRs, Context, Decision drivers, Options, Decision, Consequences)
- [x] §19 auto-évaluation présente et cochée
- [x] **3 corrections mineures Phase 0 intégrées** :
  - [x] B7 — décomposition 50 SG = 6 nouveaux + 8 existants + 36 dérivés (§10.2)
  - [x] D3 — interface stub `regulatory_applicability_service` ajoutée (§11.2)
  - [x] E2 — compteur indexes aligné à 20 (8 cardinale + 12 tables filles) (§4.2 + §16 critère 2)

**Total** : 32/32 critères ✅ — **ADR-025 prêt pour acceptation**.

---

**Statut final** : `Accepted`. Cette architecture devient **la référence unique** pour Mois 2-6 de la refonte V4.

Prochaine étape : L3 ADR-026 Migration data legacy → V4.
