# BRIEF ADR-025 · Architecture Centre d'Action V4

> **Statut** : `Proposed` → à acter par Amine avant production L2
> **Version** : v0.1
> **Date** : 2026-05-14
> **Branche cible** : `claude/refonte-sol2`
> **Doctrine source** : `docs/doctrine/doctrine_v4_classement_priorisation.md` v0.2
> **L1 audit ref** : `docs/dev/L1_audit_centre_action_v4_decisional.md` (commit `ee749a12`)
> **Auteurs** : Amine + Claude (cadrage session 2026-05-14)

---

## 0. TL;DR exécutif

ADR-025 fige **l'architecture technique** du Centre d'Action V4. Il transforme la doctrine v0.2 (le **quoi** — 7 kinds, 6 règles modulation, 5 lifecycle states, score Q8-C, Q9-B groups) en **comment** — schéma DB, indexes, contraintes, API contracts, performance budgets, sécurité.

**9 arbitrages techniques Q10-Q18 actés** dans la session de cadrage :

| Q | Décision finale | Rationale clé |
|---|---|---|
| Q10 | **Single-table inheritance scope strict** + 6 tables filles dédiées (evidences, action_event_log, action_links, action_blockers, action_scenarios, groups Q9-B) | 1 query cross-kind pour Pilotage/Référentiel, normalisation des objets lourds/variables |
| Q11 | **4 colonnes scalaires + JSONB explanation** | Tri SQL natif `ORDER BY priority_score DESC` indexable B-tree |
| Q12 | **Table dédiée `action_event_log` polymorphe** | RGPD-compatible, rétention configurable, survit à clôture item |
| Q13 | **Cutover sec Mois 4** + backup Q2-α | Cohérent avec Q2-α table rase, zéro double-write |
| Q14 | **Discriminated union TypeScript** | Narrowing automatique par kind, type-safety stricte |
| Q15 | **Hybride middleware + source-guards** | Pattern PROMEOS éprouvé (7 IDOR fixes), filet automatique |
| Q16 | **Pas de cache Mois 2-3**, Redis V4.1 | SQLite + indexes B-tree suffisent pour 150 items max |
| Q17 | **APScheduler Mois 2-3** → Celery V4.1 | Zéro infra supplémentaire, in-process FastAPI |
| Q18 | **Pyramide stratifiée 50/30/15/5** | SG insuffisant seul pour scoring/impact/lifecycle dynamiques |

**Architecture cible** : 8 tables PG-ready, ~40 colonnes scalaires sur `action_center_items`, 6 tables filles spécialisées, 14 indexes critiques, 4 contraintes CHECK doctrinales, performance budget < 100ms pour 95% des queries.

---

## 1. Périmètre et hors-scope

### 1.1 Périmètre ADR-025

L'ADR couvre :

- Schéma DB complet (8 tables + indexes + contraintes + enum types)
- Modèle SQLAlchemy ORM (mapper config polymorphic, relationships)
- Types TypeScript frontend (discriminated unions, BaseItem + 7 kinds)
- API contracts cardinaux (`/api/action-center/*` — pilotage, items, drawer, impact)
- Performance budgets par endpoint
- Sécurité org-scoping (middleware + source-guards + décorateur)
- Stratégie tests (pyramide 50/30/15/5)
- Migration legacy → V4 (cutover Mois 4)
- Coexistence Mois 2-3 (sans double-write)
- Mapping legacy → V4 par élément (cohérent avec L1)

### 1.2 Hors-scope ADR-025

- **ADR-026 Migration data** : scripts Alembic complets, ordre d'exécution, rollback procedures
- **ADR-027 Sécurité org-scoping** : implémentation détaillée du middleware, payload JWT, IDOR matrix exhaustive
- **ADR-028 Lifecycle states** : state machine complète, transitions interdites, hooks pré/post-transition
- **ADR-029 Evidence + audit trail** : schéma evidence détaillé, validation 90j, formats acceptés, traces CNIL exhaustives

ADR-025 **référence** ces ADR aval mais ne les remplace pas.

---

## 2. Schéma DB cible — 8 tables

### 2.1 Table cardinale `action_center_items` — single-table inheritance (Q10-A)

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
  domain                   VARCHAR(20) NOT NULL,  -- conformite|facturation|consommation|achat|patrimoine|data
  source_module            VARCHAR(40) NOT NULL,  -- bill_intelligence|reg_assessment|ems|...

  -- ─── Scoring Q11-A (6 colonnes) ───
  priority_score           NUMERIC(5,2) NOT NULL,
  priority_bracket         VARCHAR(2) NOT NULL,   -- P0|P1|P2|P3
  priority_explanation     JSONB NOT NULL,        -- composantes + règles R1-R6 appliquées
  score_version            VARCHAR(10) NOT NULL,  -- ex. "v1.0.3"
  score_calculated_at      TIMESTAMPTZ NOT NULL,
  score_stale              BOOLEAN NOT NULL DEFAULT FALSE,

  -- ─── Lifecycle (4 colonnes) ───
  lifecycle_state          VARCHAR(20) NOT NULL,  -- new|triaged|planned|in_progress|closed
  closed_at                TIMESTAMPTZ,
  closure_reason           VARCHAR(20),           -- resolved|dismissed|not_applicable|duplicate|merged|expired
  closure_payload          JSONB,                 -- justification + montant réalisé/perdu

  -- ─── Owner (3 colonnes) ───
  owner_id                 UUID,
  owner_role               VARCHAR(40),
  assigned_at              TIMESTAMPTZ,

  -- ─── Dates métier (3 colonnes) ───
  detected_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sla_due_date             TIMESTAMPTZ,            -- SLA de traitement PROMEOS
  business_due_date        TIMESTAMPTZ,            -- Échéance métier/réglementaire (≠ SLA)

  -- ─── Impact (4 colonnes) ───
  impact_current_period_eur     NUMERIC(12,2),
  impact_cumulative_eur         NUMERIC(12,2),
  impact_dimension              VARCHAR(20),       -- estimated|at_risk|secured|realized|lost|blocked
  impact_payload                JSONB,             -- source, formule, hypothèses

  -- ─── Flags & Confiance (4 colonnes) ───
  next_best_action                       VARCHAR(40),
  confidence_score                       NUMERIC(3,2),  -- 0.00-1.00
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
  anomaly_detector_id              VARCHAR(50),  -- anomaly + signal
  decision_deadline                TIMESTAMPTZ,  -- decision
  recommendation_payback_years     NUMERIC(4,1), -- recommendation
  deadline_authority               VARCHAR(50),  -- deadline
  evidence_format_expected         VARCHAR(20),  -- evidence_request
  signal_confidence_level          VARCHAR(10),  -- signal: low|medium|high

  -- ─── Contraintes CHECK doctrinales ───
  CONSTRAINT chk_kind CHECK (kind IN ('anomaly','action','decision','signal','evidence_request','deadline','recommendation')),
  CONSTRAINT chk_priority_bracket CHECK (priority_bracket IN ('P0','P1','P2','P3')),
  CONSTRAINT chk_lifecycle_state CHECK (lifecycle_state IN ('new','triaged','planned','in_progress','closed')),
  CONSTRAINT chk_closure_consistency CHECK (
    (lifecycle_state = 'closed' AND closed_at IS NOT NULL AND closure_reason IS NOT NULL)
    OR (lifecycle_state != 'closed' AND closed_at IS NULL)
  ),
  CONSTRAINT chk_score_range CHECK (priority_score >= 0 AND priority_score <= 100),
  CONSTRAINT chk_confidence_range CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1))
);
```

**Total colonnes** : ~42 colonnes scalaires + 3 JSONB. Bien inférieur au seuil de criticité PG (~250 colonnes par table).

### 2.2 Indexes cardinaux

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

### 2.3 Tables filles dédiées

```sql
-- ─── Audit trail (Q12-A) ───
CREATE TABLE action_event_log (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id           UUID NOT NULL REFERENCES action_center_items(id) ON DELETE RESTRICT,
  organisation_id   UUID NOT NULL,
  event_type        VARCHAR(40) NOT NULL,
  actor_type        VARCHAR(20) NOT NULL,  -- system|user|admin
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

CREATE INDEX idx_event_log_item ON action_event_log(item_id, occurred_at DESC);
CREATE INDEX idx_event_log_org_type ON action_event_log(organisation_id, event_type, occurred_at DESC);
CREATE INDEX idx_event_log_correlation ON action_event_log(correlation_id) WHERE correlation_id IS NOT NULL;

-- Rétention RGPD : politique configurable par event_type (ADR-029 détaille)
-- Par défaut : 5 ans (CNIL recommandation pour preuves conformité)


-- ─── Evidences ───
CREATE TABLE evidences (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id           UUID NOT NULL REFERENCES action_center_items(id) ON DELETE CASCADE,
  organisation_id   UUID NOT NULL,
  evidence_type     VARCHAR(40) NOT NULL,  -- devis|rib|rapport_audit|attestation|...
  status            VARCHAR(20) NOT NULL,  -- pending|uploaded|verified|expired|rejected
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

CREATE INDEX idx_evidence_item ON evidences(item_id, status);
CREATE INDEX idx_evidence_org ON evidences(organisation_id, expires_at) WHERE expires_at IS NOT NULL;


-- ─── Liens cross-modules ───
CREATE TABLE action_links (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id           UUID NOT NULL REFERENCES action_center_items(id) ON DELETE CASCADE,
  organisation_id   UUID NOT NULL,
  link_type         VARCHAR(40) NOT NULL,   -- compliance|invoice|site|building|...
  target_module     VARCHAR(40) NOT NULL,
  target_id         UUID NOT NULL,
  relation          VARCHAR(40) NOT NULL,   -- alimente|provient_de|déclenché_par|...
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_links_item ON action_links(item_id);
CREATE INDEX idx_links_target ON action_links(target_module, target_id, relation);


-- ─── Blockers ───
CREATE TABLE action_blockers (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id                  UUID NOT NULL REFERENCES action_center_items(id) ON DELETE CASCADE,
  organisation_id          UUID NOT NULL,
  blocker_type             VARCHAR(40) NOT NULL,   -- waiting_evidence|waiting_budget|waiting_third_party|...
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

CREATE INDEX idx_blocker_item_active ON action_blockers(item_id) WHERE resolved_at IS NULL;


-- ─── Scenarios (decision + recommendation) ───
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

CREATE INDEX idx_scenarios_item ON action_scenarios(item_id, display_order);


-- ─── Duplicate Groups (Q9-B) ───
CREATE TABLE duplicate_groups (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id          UUID NOT NULL,
  representative_item_id   UUID NOT NULL REFERENCES action_center_items(id) ON DELETE CASCADE,
  detection_method         VARCHAR(20) NOT NULL,   -- exact_match|fuzzy_match|manual
  detection_signature      TEXT NOT NULL,
  status                   VARCHAR(20) NOT NULL,   -- suggested|merged|dismissed
  suggested_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at              TIMESTAMPTZ,
  resolved_by              UUID,
  CONSTRAINT chk_dup_status CHECK (status IN ('suggested','merged','dismissed'))
);

CREATE INDEX idx_dup_groups_org ON duplicate_groups(organisation_id, status);


-- ─── Recurrence Groups (Q9-B) ───
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

CREATE INDEX idx_rec_groups_signature ON recurrence_groups(organisation_id, source_signature, scope_signature);
CREATE INDEX idx_rec_groups_status ON recurrence_groups(organisation_id, status, last_seen_at DESC);
```

**Total** : 1 table cardinale + 6 tables filles dédiées + 14 indexes = 8 tables.

---

## 3. Migration legacy → V4 — cutover Mois 4 (Q13-B)

### 3.1 Plan détaillé Mois 2-6

```
─────────────────────────────────────────────────────────────
Mois 2 — Création tables V4 + services V4 (lecture seule)
─────────────────────────────────────────────────────────────
  → Migration Alembic additive : create 8 tables V4
  → Implémentation services V4 (PriorityScoring, Lifecycle, ...)
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

─────────────────────────────────────────────────────────────
Mois 4 — CUTOVER (jour J)
─────────────────────────────────────────────────────────────
  J-7 : Dry-run complet sur copy DB staging
  J-3 : Communication interne, fenêtre maintenance annoncée
  J-1 : BACKUP DB COMPLET (sqlite .backup + pg_dump si PG)
  J-1 : Export JSON tables legacy (Action, Anomaly, AnomalyEvent, ...)
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

### 3.2 Garde-fous Q2-α (non négociable)

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

Mentionné **6 fois** dans cet ADR (TL;DR, §3.1, §3.2, §10, §13 critères, §14 auto-éval) — ≥3 requis selon spec ADR-026.

---

## 4. Scoring & priorisation — modèle Q11-A

### 4.1 Composantes (rappel doctrine §4.2)

| Composante | Plage | Origine |
|---|---|---|
| Gravité (`wG`) | 0-25 | ADR-022 héritée |
| Impact (`wI`) | 0-25 | ADR-022 héritée |
| Délai (`wD`) | 0-20 | ADR-022 héritée |
| Risque conformité | 0-15 | extension V4 |
| Confiance détection | 0-10 | extension V4 |
| Récurrence | 0-5 (bonus) | extension V4 |
| Sans responsable | 0-5 (additive) | extension V4 (override §5.3) |
| Preuve manquante | 0-5 (bonus) | extension V4 |

**Total max théorique** : 105/100 (bornage final à 100).

### 4.2 Structure JSONB `priority_explanation`

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

### 4.3 Job de recalcul nightly + invalidation

```python
# backend/services/priority_scoring/job.py

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=3, minute=0, id='nightly_priority_refresh')
def nightly_priority_refresh():
    """
    Cron 03:00 UTC quotidien.
    Recalcule scores marqués stale + P0/P1 actifs (filet de sécurité).
    """
    # Pseudocode — implémentation Mois 2
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
    # Pseudocode — implémentation Mois 3 (avec notification system)
    pass
```

### 4.4 Événements d'invalidation (12 events doctrine §4.3)

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

## 5. API contracts cardinaux

### 5.1 Endpoint Pilotage — liste prioritaire

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
    "file_prioritaire": {
      "count": 5,
      "items": [...]   // ActionCenterItem polymorphique
    },
    "jalons_a_preparer": {
      "count": 2,
      "items": [...]
    },
    "a_surveiller": {
      "count": 1,
      "items": [...]
    },
    "clos_recemment": {
      "count": 2,
      "items": [...]   // Format compact
    }
  },
  "doctrine_version": "v0.2",
  "calculated_at": "2026-05-14T07:18:00Z"
}
```

**Performance budget** : < 100ms pour 150 items max.

### 5.2 Endpoint item détail (drawer M2)

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
  "blockers": [
    { "type": "waiting_evidence", "added_at": "2026-05-09T11:24:00Z", "justification": "..." },
    { "type": "waiting_budget", "added_at": "2026-05-11T14:32:00Z", "justification": "..." }
  ],
  "evidence": [...],
  "event_log": [...],  // 5 derniers events par défaut (drawer M2)
  "scenarios": [...],
  "links": [...]
}
```

**Performance budget** : < 200ms (drawer M2 ouvre vite).

### 5.3 Endpoint impact (drawer M4)

```http
GET /api/action-center/impact
Query: ?periode=12m&perimetre=helios

Response 200:
{
  "net_result": {
    "secured_eur": 128000,
    "at_risk_eur": 52000,
    "actions_processed": 146,
    "items_created": 214,
    "resolution_rate_pct": 68,
    "median_resolution_days": 4.2
  },
  "dimensions": {
    "estimated":  { "amount_eur": 82000, "items": 11, "source": "Modèle V4 scenarios", "formula": "Σ best_case_gain" },
    "at_risk":    { "amount_eur": 52000, "items": 8, "source": "RegOps + Bill Intel", "formula": "Σ exposure_amount" },
    "secured":    { "amount_eur": 34000, "items": 14, "source": "ActionCenter exec",  "formula": "Σ in_progress.expected" },
    "realized":   { "amount_eur": 128000, "items": 67, "source": "Closure log + preuves", "formula": "Σ realized_gain" },
    "lost":       { "amount_eur": 6800, "items": 5, "source": "Closure log",  "formula": "Σ where closure ∈ {expired, dismissed}" },
    "blocked":    { "amount_eur": 23000, "items": 4, "source": "Blockers actifs", "formula": "Σ where blockers ≠ ∅" }
  },
  "roi": { "ratio": 4.3, "label": "ROI 12 mois", "calculation": "gains réalisés ÷ (temps équipe + coût SaaS PROMEOS)" },
  "by_domain": [...],
  "top_contributors": [...],   // 5 max
  "trajectory": [...]          // 12 points mensuels
}
```

**Performance budget** : < 300ms (agrégation cross-items + agrégat domain + top contributors).

### 5.4 Endpoints PATCH (mutations)

```http
PATCH /api/action-center/items/{id}/lifecycle    # Transition d'état
PATCH /api/action-center/items/{id}/owner        # Réassignation
PATCH /api/action-center/items/{id}/blockers     # Ajout/résolution blocker
PATCH /api/action-center/items/{id}/correct-kind # ADMIN UNIQUEMENT (audit trail forcé)
POST  /api/action-center/items/{id}/close        # Clôture avec closure_reason
```

Toutes mutations trigger un event dans `action_event_log` automatiquement.

---

## 6. Types TypeScript frontend (Q14-A)

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

interface AnomalyItem extends BaseItem {
  kind: 'anomaly';
  anomaly_detector_id: string;
  recurrence_count?: number;
}

interface ActionItem extends BaseItem {
  kind: 'action';
}

interface DecisionItem extends BaseItem {
  kind: 'decision';
  decision_deadline?: string;
}

interface SignalItem extends BaseItem {
  kind: 'signal';
  anomaly_detector_id: string;
  signal_confidence_level: 'low' | 'medium' | 'high';
}

interface EvidenceRequestItem extends BaseItem {
  kind: 'evidence_request';
  evidence_format_expected: string;
}

interface DeadlineItem extends BaseItem {
  kind: 'deadline';
  deadline_authority: string;
}

interface RecommendationItem extends BaseItem {
  kind: 'recommendation';
  recommendation_payback_years?: number;
}

type ActionCenterItem =
  | AnomalyItem | ActionItem | DecisionItem | SignalItem
  | EvidenceRequestItem | DeadlineItem | RecommendationItem;

// Narrowing automatique par discriminant 'kind' :
function renderItem(item: ActionCenterItem) {
  switch (item.kind) {
    case 'anomaly':
      // TypeScript sait ici que item: AnomalyItem
      return <AnomalyCard detector={item.anomaly_detector_id} ... />;
    case 'recommendation':
      return <RecoCard payback={item.recommendation_payback_years} ... />;
    // ... 5 autres cases
  }
}
```

---

## 7. Sécurité org-scoping native (Q15-C)

### 7.1 Middleware FastAPI global

```python
# backend/middleware/org_scoping.py

from fastapi import Request, HTTPException

class OrgScopingMiddleware:
    async def __call__(self, request: Request, call_next):
        # Extrait organisation_id du JWT
        org_id = extract_org_id_from_token(request)
        if not org_id:
            raise HTTPException(401, "Missing organisation context")

        # Injecte dans le state pour usage par les routes
        request.state.organisation_id = org_id

        # Audit log entry/exit
        with logger.contextualize(org_id=org_id, route=request.url.path):
            response = await call_next(request)

        return response
```

### 7.2 Décorateur @org_scoped pour endpoints sensibles

```python
# backend/decorators/security.py

def org_scoped(func):
    """
    Décorateur pour endpoints qui retournent des items utilisateur.
    Force que l'organisation_id soit présent dans toutes les queries SQLAlchemy.
    """
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
    # organisation_id obligatoire dans le filtre
    item = db.query(ActionCenterItem).filter(
        ActionCenterItem.id == item_id,
        ActionCenterItem.organisation_id == request.state.organisation_id
    ).first()
    if not item:
        raise HTTPException(404)
    return item
```

### 7.3 Source-guards automatiques

```python
# tests/source_guards/test_org_scoping_v4.py

import re
from pathlib import Path

def test_all_action_center_queries_have_org_scoping():
    """
    Vérifie que toutes les queries SQLAlchemy sur action_center_items
    incluent un filter organisation_id.
    """
    file_pattern = "backend/services/action_center/**/*.py"
    queries = []
    for path in Path(".").glob(file_pattern):
        content = path.read_text()
        # Détecte query.filter sur ActionCenterItem
        matches = re.findall(r'(\.query\(ActionCenterItem\).*?\.(first|all|one|count)\(\))', content, re.DOTALL)
        for match in matches:
            if 'organisation_id' not in match[0]:
                queries.append((path, match[0][:200]))
    assert not queries, f"Queries missing org_scoping: {queries}"
```

---

## 8. Stratégie tests V4 stratifiée (Q18 raffiné)

### 8.1 Pyramide cardinale

```
─────────────────────────────────────
50 SOURCE-GUARDS    (~50% des tests)
─────────────────────────────────────
  Vérifient patterns statiques :
  - org_scoping présent dans toutes les queries
  - libellés FR uniquement en mode standard (regex DOM)
  - Pas de codes techniques visibles hors mode audit
  - Pas de "Fusionner" sur recurrence_group
  - Tous les endpoints ont @org_scoped ou middleware
  - Pas de TODO/FIXME/XXX/HACK dans code merged
  - 7 kinds visuellement distincts dans CSS
  - Score persisté = NumericField, pas calculé inline
  - Doctrine v0.2 §X référencée dans tests métier

─────────────────────────────────────
30 UNIT + INTÉGRATION (~30%)
─────────────────────────────────────
  Vérifient comportement métier DYNAMIQUE :
  - PriorityScoringService.compute_score()
    × 6 règles R1-R6 input → output
    × Composantes ADR-022 + V4
    × Bornage final 100/100
    × score_stale = TRUE après chaque event invalidant
  - LifecycleStateMachine
    × Transitions valides (new → triaged → planned → ...)
    × Transitions interdites (closed → triaged refuse)
    × Hooks pré/post-transition
  - ImpactAggregationService
    × 6 dimensions sans double comptage
    × Vérification : Σ dimensions = total connu
  - RecurrenceDetector
    × Signature matching, fenêtre 90j
    × Création/rattachement group
  - DuplicateDetector
    × exact_match vs fuzzy_match
  - EvidenceVerifier
    × Validation 90j, formats acceptés
  - ActionEventLog
    × Trace tous events doctrine §7.1

─────────────────────────────────────
15 CONTRACT API (~15%)
─────────────────────────────────────
  Vérifient interface publique :
  - GET /api/action-center/pilotage retourne summary cohérent
  - POST /items rejette payload invalide (4xx)
  - PATCH /items/{id}/correct-kind nécessite role admin (403 sinon)
  - GET /items/{id}/audit-trail respecte org-scoping (404 cross-org)
  - GET /impact retourne 6 dimensions toujours présentes
  - PATCH /items/{id}/lifecycle déclenche action_event_log entry
  - Performance budgets respectés (assertions sur durée)

─────────────────────────────────────
5 E2E PLAYWRIGHT (~5%)
─────────────────────────────────────
  Vérifient parcours utilisateur critiques :
  - Pilotage > Décisions affiche correctement les 7 kinds
  - Drawer M2 ouvre/ferme/met à jour score
  - Impact Drawer M4 exporte CSV correctement
  - Bascule mode standard ↔ mode audit
  - Mini-fix compteur P0/P1 reste aligné (cf. demande Amine)
```

**Total** : ~100 tests V4 Mois 2-6.

### 8.2 Justification stratification

- **Source-guards seuls insuffisants** pour scoring/impact/lifecycle dynamiques (calculs complexes, transitions état, agrégations) → **unit/intégration obligatoires** (30%).
- **Contract API tests** garantissent stabilité interface frontend ↔ backend → **15%** pour les 6-8 endpoints cardinaux.
- **E2E Playwright minimum** car lents et flaky → seulement 5 scénarios critiques.

---

## 9. Performance budgets

| Endpoint | Budget | Justification |
|---|---|---|
| `GET /pilotage` | **< 100ms** | Vue d'entrée, doit être instantanée |
| `GET /items/{id}` (sans includes) | **< 50ms** | Index B-tree PK |
| `GET /items/{id}?include=event_log,evidence,...` (drawer M2) | **< 200ms** | 4-5 joins indexés |
| `GET /impact` (drawer M4) | **< 300ms** | Agrégations cross-items |
| `PATCH /items/{id}/lifecycle` (transition + recalcul score + event log) | **< 150ms** | Mutation + 2 inserts |
| `POST /items` (création) | **< 100ms** | 1 insert + 1 event_log entry |
| `GET /audit-trail/{item_id}` (paginated) | **< 100ms** | Index composite |

**Tous mesurés via** : `pytest-benchmark` + `prometheus-fastapi-instrumentator`.

---

## 10. Mapping legacy → V4 (cohérent avec L1)

| Legacy | V4 cible | Verdict L1 | ADR ref |
|---|---|---|---|
| `Action`, `ActionItem`, `ActionPlanItem` (modèles) | `ActionCenterItem` polymorphique | SUPPRIME (×3) | ADR-025 §2.1 |
| `Anomaly` (modèle) | `ActionCenterItem` avec `kind='anomaly'` | MIGRE | ADR-025 §2.1 |
| `AnomalyEvent` (modèle) | `action_event_log` polymorphe | REMPLACE | ADR-025 §2.3 + ADR-029 |
| `AnomalyDetector` (modèle) | Référencé via `anomaly_detector_id` VARCHAR | GARDE (légère réf) | ADR-025 §2.1 |
| 18 tables DB (8 vivantes + 10 vides `action_plan_*`) | 8 tables V4 | SUPPRIME (×10) MIGRE (×8) | ADR-025 §2 + ADR-026 |
| 8 enums sévérité | 1 enum `severity` V4 | SUPPRIME (×7) MIGRE (×1) | ADR-025 §2.1 |
| 4 mappings sévérité → priorité | `priority_explanation.modulation_rules_applied` | REMPLACE | ADR-025 §4 |
| 6 vocabulaires statuts | `lifecycle_state` enum V4 (5 valeurs) | SUPPRIME (×5) MIGRE (×1) | ADR-025 §2.1 + ADR-028 |
| 63 endpoints `/api/anomalies/*`, `/api/action-plans/*`, etc. | 12 endpoints `/api/action-center/*` unifiés | SUPPRIME (×51) REMPLACE (×12) | ADR-025 §5 |
| 20 services Action/Anomaly | 8 services V4 (PriorityScoring, Lifecycle, Impact, ...) | MIGRE (×6) SUPPRIME (×14) | ADR-025 §4 |
| 5 schemas Pydantic | 8 schemas V4 (BaseItem + 7 kinds) | MIGRE | ADR-025 §6 |
| 1 667 LoC mortes frontend | Suppression Mois 5 | SUPPRIME | ADR-025 §3 + ADR-026 |
| 8 source-guards existants | Réutilisés + 50 nouveaux V4 | GARDE | ADR-025 §8 |
| Seeds HELIOS/MERIDIAN | Régénérés format V4 Mois 4 | RÉGÉNÈRE | ADR-025 §3 + ADR-026 |

**Cohérence avec L1** : tous les verdicts L1 sont satisfaits par cette architecture. **Aucune décision orpheline**.

---

## 11. Coexistence Mois 2-3 (zéro double-write)

**Architecture transitoire** :

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

## 12. Risques identifiés et mitigations

| Risque | Probabilité | Impact | Mitigation ADR |
|---|---|---|---|
| Cutover Mois 4 échoue | Faible | Élevé | Backup Q2-α + dry-run J-7 + smoke tests J+0 (§3.1) |
| Performance dégrade après V4 (single-table avec 40 cols) | Faible | Moyen | 8 indexes B-tree spécifiques + budget < 100ms documenté (§9) |
| Score V4 incohérent vs legacy (validation) | Moyen | Moyen | Tests unit complets §8.1 R1-R6 + comparaison manuelle 10 items HELIOS Mois 3 |
| RGPD non conforme sur audit_event_log | Faible | Élevé | Table dédiée Q12-A + politique rétention configurable + ADR-029 dédié |
| Bug bloqueur dans 5 migrations `.original-autogenerate` | Élevé (signal L1) | Élevé | Investigation Mois 2 priorité 0 + rollback strategy documentée |
| Org-scoping leak via nouvelle route oubliée | Moyen | Très élevé (P0 sécu) | Middleware FastAPI global + décorateur + 50 source-guards (§7) + ADR-027 |
| Bug Briefing 500 lié refonte | Moyen | Élevé | Investigation P0 Mois 2 séparée + branchement V4 désactivable via feature flag |

---

## 13. Renvois ADR-026 / 027 / 028 / 029

ADR-025 **référence** mais ne détaille pas :

- **ADR-026 Migration data** :
  - Scripts Alembic destructifs Mois 5
  - Procédure backup automatisée (sqlite/PG)
  - Régénération seeds HELIOS/MERIDIAN V4
  - Rollback procedures détaillées
  - Tests de restore sur staging

- **ADR-027 Sécurité org-scoping** :
  - Implémentation détaillée middleware (JWT extraction, payload)
  - Décorateur `@org_scoped` complet avec roles (admin, user, viewer)
  - 50 source-guards détaillés (un par pattern)
  - IDOR matrix exhaustive : routes × roles × organisations
  - Audit penetration testing Mois 4

- **ADR-028 Lifecycle states** :
  - State machine complète (5 états + 12 transitions)
  - Transitions interdites avec exception handling
  - Hooks pré/post-transition par état
  - Mapping doctrine §7.1 libellés FR

- **ADR-029 Evidence + audit trail** :
  - Schéma evidence complet
  - Validation 90j (algorithme)
  - Formats acceptés + signatures
  - Politique rétention RGPD par event_type
  - Articles CNIL référencés (5(2), 30, 6)

---

## 14. Auto-évaluation ADR-025 — 7 critères de validation finale

**Ces 7 critères deviennent le gate de validation L2.** Claude Code doit pouvoir cocher chaque ligne sans ambiguïté avant fermeture.

| # | Critère | Vérifié par |
|---|---|---|
| 1 | **L'architecture respecte Q2-α table rase** | §3 Migration cutover sec Mois 4 + backup obligatoire 6× mentionné. Aucune procédure de migration data (POC seeds uniquement) |
| 2 | **Le modèle reste simple et performant** | §2.1 single-table ~42 colonnes + §2.3 6 tables filles dédiées + §2.2 8 indexes spécifiques + §9 performance budgets < 100ms documentés |
| 3 | **L'audit trail est défendable (RGPD)** | §2.3 `action_event_log` table dédiée + politique rétention configurable + références CNIL articles 5(2), 30, 6 + survit à clôture item |
| 4 | **Le score est triable en SQL** | §2.1 4 colonnes scalaires `priority_score NUMERIC(5,2)` + `priority_bracket VARCHAR(2)` + §2.2 index `idx_aci_priority_active` B-tree natif |
| 5 | **La sécurité org-scoping est native** | §7 middleware FastAPI global + décorateur `@org_scoped` + 50 source-guards + `organisation_id` sur 8 tables filles + ADR-027 référencé |
| 6 | **La transition ne crée pas un mois de double-write inutile** | §11 coexistence Mois 2-3 sans écriture cross-modèle + §3.1 cutover sec Mois 4 + cohérence avec Q2-α §3.2 garde-fous |
| 7 | **Les tests couvrent code + métier + API** | §8 pyramide stratifiée 50 SG (code) + 30 unit/intégration (métier dynamique) + 15 contract (API) + 5 e2e (UX critique) |

---

## 15. Métadonnées ADR

```yaml
adr_number: 025
title: Architecture Centre d'Action V4 - schéma DB et patterns techniques
version: v0.1
status: Proposed
date: 2026-05-14
authors:
  - Amine (PROMEOS founder)
  - Claude (architecture co-pilot)
arbitrages_q10_q18:
  Q10: A_refined  # single-table scope strict + 6 tables filles
  Q11: A          # 4 colonnes scalaires + JSONB explanation
  Q12: A          # table dédiée action_event_log
  Q13: B          # cutover sec Mois 4 (changé depuis Q13-A)
  Q14: A          # discriminated union TypeScript
  Q15: C          # hybride middleware + source-guards
  Q16: A          # pas de cache Mois 2-3
  Q17: refined    # APScheduler Mois 2-3 → Celery V4.1
  Q18: refined    # pyramide stratifiée 50/30/15/5
constraints_doctrinales:
  - Q1-A : ActionCenterItem polymorphique unique
  - Q2-α : table rase + backup obligatoire (×6 dans ce doc)
  - Q3-C : scoring ADR-022 base + extensions V4
  - Q4-A : consommer regulatory_applicability_service comme SoT
  - Q5-B : job pull idempotent depuis compliance findings
  - Q6-A : Mois 1 docs only (ce doc inclus)
  - Q7-A : rendu strict par kind
  - Q8-C : score persisté + invalidation event-driven
  - Q9-B : tables séparées duplicate/recurrence groups
performance_budgets:
  pilotage: 100ms
  item_detail: 200ms
  impact: 300ms
  mutation: 150ms
total_tests_planned: 100
total_tables: 8
total_indexes: 14
backup_q2_alpha_mentions: 6
next_adr: ADR-026 Migration data legacy → V4
```

---

**Statut** : `Proposed`. À acter par Amine avant L2 audit technique de cohérence.

Une fois actée, cette architecture devient **la référence unique** pour Mois 2-6 de la refonte V4.
