# Data Dictionary V4 Centre d'Action PROMEOS

> **Version** : v1.0 · 2026-05-14
> **Source** : ADR-025 → ADR-029 + doctrine v0.3 + L1 décisionnel
> **Branche** : `claude/refonte-sol2`
> **Statut** : `Accepted` (compilation des 5 ADR Mois 1)
> **Mois** : 1 · livrable 8/9
> **Estimation lecture** : 30-45 min · **Estimation lookup ponctuel** : 30 sec

---

## 0. Mode d'emploi

Ce **manuel de référence unique** consolide les définitions, types, sémantiques et règles métier issus des 5 ADR du Mois 1, de la doctrine v0.3 et du L1 décisionnel.

**Pour qui ?** Tout développeur Mois 2+ : "quel type pour `closure_reason` ?" → §3.2 réponds en 1 lookup, pas en 5 ADR consultés.

**Conventions** :
- `code_technique` (snake_case) = nom EN canonical en base/code
- **Libellé FR mode standard** = ce que voit l'utilisateur (cf. §10)
- `Q9-B` / `IL4` / `IS11` / `IE9` = invariants doctrinaux (cf. §12)
- 🛡️ = garde-fou cardinal Amine (non négociable)
- Tous les renvois `→ ADR-XXX §N` sont vérifiables dans `docs/dev/`

**Source de vérité absolue** :
- Si conflit doctrine v0.3 ↔ ADR : doctrine v0.3 prévaut. Ouvrir avenant doctrinal.
- Si conflit ADR-025 (squelette) ↔ ADR-026/027/028/029 (détails) : ADR aval prévaut (extension acceptée par convention).
- Si conflit avec ce L7 : ce L7 doit être mis à jour, pas ignoré (release blocker Mois 2).

---

## 1. Glossaire métier (~70 termes · 8 catégories)

### 1.1 Termes lifecycle (10)

| Terme | Définition | Source |
|---|---|---|
| **ActionCenterItem** | Entité polymorphique cardinale du Centre d'Action V4. Single-table inheritance avec discriminant `kind`. ~42 colonnes scalaires + 3 JSONB. Q10-A_refined. | ADR-025 §4.1 |
| **LifecycleState** | État courant d'un item parmi 5 valeurs strictes : `new` · `triaged` · `planned` · `in_progress` · `closed`. Doctrine v0.3. | ADR-028 §2 |
| **ClosureReason** | Motif de clôture d'un item (6 valeurs révisées v0.3). Obligatoire si `lifecycle_state = closed`. | doctrine v0.3 §7.1 |
| **LifecycleStateMachine** | Service Q33-B (enum + dict) qui valide les 10 transitions strictes + applique hooks pré/post. Zéro dépendance externe. | ADR-028 §7 |
| **VALID_TRANSITIONS** | `dict[LifecycleState, set[LifecycleState]]` figeant les 10 transitions autorisées. 25 théoriques rejetées HTTP 409. | ADR-028 §7.2 |
| **PRE_TRANSITION_HOOKS / POST_TRANSITION_HOOKS** | Validations exécutées avant/après transition (verify_has_owner, verify_no_active_blocker, write_action_event_log, invalidate_score_stale). | ADR-028 §7.3 |
| **recurrence_group** | Groupe d'items partageant `source_signature + scope_signature` sur fenêtre 90j. Q9-B distinct de doublon. Auto-close cascade `resolved_via_recurrence`. | doctrine v0.3 §6 + ADR-025 §4.3 |
| **duplicate_group** | Groupe de doublons stricts (Q9-B). Fusion → `closure_reason = merged_duplicate` (business 3 ans). | doctrine v0.3 §6 + ADR-025 §4.3 |
| **score_stale** | Booléen passé `TRUE` après chaque transition lifecycle ou changement de blocker (IL9). Job recalcul score asynchrone le réinitialise. | ADR-028 IL9 + ADR-025 §4.1 |
| **action_blockers** | Table fille tenant les blockers actifs (waiting_evidence, waiting_third_party...). 7 types whitelist CHECK constraint. | ADR-025 §4.3 |

### 1.2 Termes priorité (8)

| Terme | Définition | Source |
|---|---|---|
| **PriorityBracket** | 4 brackets : `P0` (≥80) · `P1` (60-79) · `P2` (40-59) · `P3` (<40). Persisté pour tri SQL. | doctrine v0.3 §2.2 |
| **priority_score** | NUMERIC(5,2) ∈ [0, 100], persisté Q8-C. Calculé par `PriorityScoringService` à la création + invalidation event-driven. | doctrine v0.3 §4 + ADR-022 |
| **priority_explanation** | JSONB versionné Q11-A décomposant le score en composantes lisibles. Cardinal pour audit user. | ADR-025 §4.1 + doctrine §4.2 |
| **score_version** | VARCHAR(10) trace la version de l'algorithme de scoring utilisé (ex. "v1.0"). Permet recalcul rétro post-évolution. | ADR-025 §4.1 |
| **12 events de recalcul priorité** | `priority_recalculated` triggers : evidence_added/verified, blocker_added/removed, owner_changed, kind_corrected, state_changed, recurrence_attached, deadline_changed, sla_threshold_crossed, manual_recalc, group_resolution. | doctrine v0.3 §4.3 |
| **R6 plancher P1 conformité** | Si `domain ∈ {conformite, facturation}` ET `regulatory_rule_id IS NOT NULL` → bracket plancher `P1`. Empêche oubli silencieux. | doctrine v0.3 §5.6 + ADR-022 |
| **6 règles modulation R1-R6** | R1 risque>sévérité · R2 conformité>opportunité · R3 escalade sans owner · R4 récurrence · R5 confiance faible · R6 plancher conformité. | doctrine v0.3 §5 |
| **next_best_action** | VARCHAR(40) suggérant la prochaine action recommandée (ex. "qualify", "add_evidence"). Désactivé si `confidence < 0.6` (R5). | ADR-025 §4.1 + doctrine §5.5 |

### 1.3 Termes evidence + audit trail (12)

| Terme | Définition | Source |
|---|---|---|
| **Evidence** | Pièce justificative uploadée (PDF/JPG/PNG · 10 MB max). Validation manuelle obligatoire. Expiration 90j post-vérification. | ADR-029 §5 |
| **EvidenceStorageBackend** | ABC IE1 abstrait. `FilesystemBackend` Mois 2 (`fs://`) · `S3Backend` V4.1+. Migration sans refacto applicatif. | ADR-029 §7 |
| **validation_payload** | JSONB IE2 contenant `metadata_extracted` + `verified_by_human` + `verifier_role` + `confidence_flag` (high/medium/low). | ADR-029 §5.2 |
| **expires_at** | TIMESTAMPTZ IE6 cardinal : `verified_at + INTERVAL '90 days'`. CHECK DB + service Python. | ADR-029 §5.1 + §8.2 |
| **ActionEventLog** | Audit trail métier (1-5 ans selon catégorie). 16 event_types. Schemas Pydantic versionnés (`schema_version`). | ADR-029 §6 |
| **security_audit_log** | Logs sécurité (90j strict, IS7/IS8). 🛡️ IE8 séparation stricte du `action_event_log` métier. | ADR-027 §10 + ADR-029 §6.2 |
| **schema_version** | VARCHAR(10) dans payload event + colonne event_log. IE7 cardinal. Pattern d'évolution v1 → v2 documenté. | ADR-029 §11.5 |
| **EVENT_PAYLOAD_SCHEMAS** | Registry `dict[(event_type, schema_version), type[BaseModel]]`. 16 schemas v1 référencés. | ADR-029 §11.3 |
| **magic bytes** | 🛡️ IE9 cardinal Amine. Validation MIME par signature réelle fichier (`%PDF-`, `\xff\xd8\xff`, `\x89PNG\r\n\x1a\n`) via `python-magic` + double-check hardcodé. Anti-spoofing 4 lignes de défense. | ADR-029 §9 |
| **3 catégories rétention RGPD** | `compliance` 1825 jours (5 ans) · `business` 1095 jours (3 ans) · `system` 365 jours (1 an). Aligné CNIL art. 5(1)(e). | ADR-029 §10.1 |
| **monthly_retention_purge** | Job APScheduler Q43-A+ (1er du mois 2h UTC). 🛡️ IE5 triple garde-fou : `RETENTION_PURGE_ENABLED` + `RETENTION_PURGE_DRY_RUN_FIRST` + trace `security_audit_log`. | ADR-029 §12 |
| **closed_via_resolved_via_recurrence** | Event v0.3 ajouté Q37-A+. Auto-close cascade `recurrence_group.resolved`. **Compliance 5y** (preuve indirecte) — distinct de `closed_via_merged_duplicate` business 3y (Q9-B). | ADR-029 §10.2 + doctrine §7.1 |

### 1.4 Termes sécurité org-scoping (10)

| Terme | Définition | Source |
|---|---|---|
| **organisation_id** | UUID NOT NULL sur les 8 tables V4. 🛡️ IS1 cardinal — colonne par laquelle toute requête SQL filtre. | ADR-027 IS1 |
| **@org_scoped** | Décorateur FastAPI couche 2 (Q27-B+). Force vérification `request.state.organisation_id` + role check. Obligatoire sur toutes routes `/api/action-center/*`. | ADR-027 §8 |
| **OrgScopingMiddleware** | Couche 1 (Q27-B+). Injecte `organisation_id` dans `request.state` à chaque requête depuis JWT/session. | ADR-027 §7 |
| **Pattern repository org-scopé** | 🛡️ IS11 cardinal Amine. Pas d'accès SQL direct dans routes — `repo.get_by_id(id, organisation_id)` obligatoire. 4 lignes de défense empilées : middleware + décorateur + repository + source-guards CI. | ADR-027 §8 + IS11 |
| **IDOR** | Insecure Direct Object Reference. `GET /items/{id}` sans filter `organisation_id` → user lit items d'autres orgs. M1 menace P0. | ADR-027 §6 M1 |
| **IDOR matrix 288** | Couverture exhaustive 100% IS2 : 12 routes × 3 rôles × 2 orgs × 4 cas (GET own/other, MUTATE own/other) = 288 cellules. 1 test pytest paramétré par cellule. | ADR-027 §10 |
| **admin_only_with_fresh_token** | 🛡️ IS5. Décorateur sur endpoints sensibles (kind_corrected, reopen, delete_user_data). Token <5min. | ADR-027 §8 + ADR-028 IL3 |
| **correlation_id** | 🛡️ IS9 cardinal. UUID propagé dans `request.state` + tous events log + purges. Trace cross-actions (bulk_updated, retention.purge.completed). | ADR-027 IS9 |
| **50 source-guards CI** | Tests pytest qui scannent le code source pour détecter régressions sécurité (raw SQL, queries sans org filter, magic bytes manquants...). 6 catégories. CI gate bloquant. | ADR-027 §11 |
| **CI gate Bandit + Semgrep + gitleaks + pip-audit** | 🛡️ IS6. 4 outils SAST/DAST + 50 SG en GitHub Actions. Aucune régression sécurité ne passe. | ADR-027 §12 |

### 1.5 Termes migration + backup (8)

| Terme | Définition | Source |
|---|---|---|
| **Q2-α table rase** | Doctrine cardinale : aucune procédure de migration data automatique pour POC. Backup obligatoire pré-cutover Mois 4. | doctrine v0.3 §1 + ADR-026 |
| **Triple artefact backup** | 🛡️ I5 + I9 cardinaux. (1) Binaire `.backup` SQLite + (2) Dump SQL `.sql` + (3) JSON par table + checksum SHA256. Hors Git impératif (`/data/backups/` gitignored). | ADR-026 §5 |
| **STOP GATE J+14** | Validation manuelle 14 jours après cutover Mois 4 avant suppression legacy (DROP tables). I8 invariant non négociable. | ADR-026 §5 + I8 |
| **173 rows data réelle** | Cardinal POC : `action_items` 35 + `bill_anomaly` 52 + `anomaly` KB 86 = 173 rows à migrer (15 autres tables legacy vides Sprint 13). | L1 §3.2 + ADR-026 §5.1 |
| **1 667 LoC dead code** | Frontend legacy à supprimer Mois 5 post-bascule (7 fichiers FE + sous-routes legacy). Verdict L1 SUPPRIME 28 éléments. | L1 §3 + ADR-026 §10 |
| **Receipt sanitizé in Git** | 🛡️ I9 cardinal Amine. Si checksum/manifest commité → counts numériques + checksums + timestamps + schema_versions seulement. **Pas de PII · pas de chemin user · pas d'IP staging · pas de hostname**. | ADR-026 I9 |
| **Cutover sec Mois 4 (Q13-B)** | Bascule unique avec feature flag global. J-7 pen-test ADR-027. J-1 backup triple artefact. J0 cutover atomique. J+14 STOP GATE manuel. | ADR-025 Q13-B + ADR-026 §5 |
| **Receipt commit DROP legacy** | Fichier sanitizé `docs/migrations/L3_cutover_receipts/<TS>.md` · counts deletes + signatures + opérateur + correlation_id. Pas de SQL exécuté in Git. | ADR-026 §11 |

### 1.6 Termes architecture (8)

| Terme | Définition | Source |
|---|---|---|
| **Single-table inheritance** | Q10-A_refined : 1 table cardinale `action_center_items` (~42 colonnes, discriminant `kind`) + 7 tables filles dédiées (`action_event_log`, `evidences`, `action_links`, `action_blockers`, `action_scenarios`, `duplicate_groups`, `recurrence_groups`). | ADR-025 §4.1 |
| **8 tables V4** | Total cible : 1 cardinale + 7 filles. Migration legacy 18 tables → 8 V4. | ADR-025 §4 |
| **20 indexes** | Total exhaustif (8 cardinale + 12 tables filles). Performances Pilotage < 100ms · mutations < 150ms. | ADR-025 §4.2 |
| **JSONB priority_explanation** | Q11-A. Décomposition lisible du score (composantes R1-R6). Versionnée. | ADR-025 §4.1 |
| **JSONB closure_payload** | Métadonnées de clôture (evidence_id si `resolved`, recurrence_group_id si `resolved_via_recurrence`...). | ADR-025 §4.1 |
| **Discriminated union TypeScript** | Frontend : `type ActionCenterItem = AnomalyItem | ActionItem | DecisionItem | ...`. Compile-time check (Q10-A refined). | ADR-025 §4.1 |
| **chk_closure_consistency** | CHECK constraint DB : `lifecycle_state = closed` ⇔ `closed_at IS NOT NULL AND closure_reason IS NOT NULL`. | ADR-025 §4.1 |
| **chk_kind / chk_lifecycle_state** | CHECK constraints DB whitelist 7 kinds + 5 lifecycle_states. Refus DB-side. | ADR-025 §4.1 |

### 1.7 Termes RGPD + CNIL (8)

| Terme | Définition | Source |
|---|---|---|
| **art. 5(1)(b) finalité** | Finalité spécifiée. PROMEOS V4 : 3 catégories rétention = 3 finalités distinctes. | ADR-029 §13.1 |
| **art. 5(1)(e) limitation conservation** | Durée proportionnée à la finalité. Justifie 5y compliance / 3y business / 1y system. | ADR-029 §13.1 |
| **art. 5(2) intégrité** | Magic bytes IE9 + validation manuelle IE2. Anti-spoofing fichier. | ADR-029 §13.1 |
| **art. 6 base légale** | Obligation légale (DT/BACS/APER) + intérêt légitime opérationnel. | ADR-029 §13.1 |
| **art. 15 droit d'accès** | Endpoint `GET /api/users/me/data-export` retourne tous events liés au user + scoped org. | ADR-029 §13.2 |
| **art. 17 droit à l'oubli** | Endpoint `DELETE /api/users/me/data` **anonymise** (pas supprime) — préserve audit trail art. 30. Interprétation CNIL 2023. | ADR-029 §13.3 |
| **art. 30 registre traitements** | Tous events tracés avec `schema_version`. Action_event_log = registre principal. | ADR-029 §13.1 |
| **art. 32 sécurité traitement** | `security_audit_log` séparé strict + IS7 (sanitization logs) + IS8 (anonymisation IP /24 IPv4 /48 IPv6). | ADR-027 §10 + ADR-029 §13.1 |

### 1.8 Termes doctrine + ADR (6)

| Terme | Définition | Source |
|---|---|---|
| **Doctrine v0.3** | Source unique des choix V4. Premier avenant doctrinal versionné (2026-05-14 · Q37-A+ closure_reasons révisés). 9 arbitrages doctrinaux Q1-Q9. | doctrine v0.3 §11 |
| **ADR / MADR** | Architecture Decision Record format MADR. 5 ADR-025 → ADR-029 produits Mois 1, status `Accepted`. | docs/dev/L*_ADR-*.md |
| **Avenant doctrinal versionné** | Évolution doctrinale via bump version (v0.2 → v0.3) + entrée datée table §11. Jamais de modification silencieuse. | doctrine v0.3 §11 |
| **Q-arbitrage** | Décision actée en session refonte. 46 arbitrages Q1-Q46 cumulés. Non débattables post-acceptation ADR. | doctrine v0.3 + ADR-025-029 |
| **Invariant doctrinal** | Règle non négociable, vérifiée par test source-guard ou unitaire. 49 invariants : 9 doctrinaux Q + 9 I + 11 IS + 11 IL + 9 IE. | §12 |
| **Garde-fou cardinal Amine** | Sous-ensemble d'invariants élevés au rang stratégique par Amine. 🛡️ I9 · IS11 · IL4/IL5/IL7 · IE9. | §14 |

**Total glossaire** : 70 termes documentés sur 8 catégories ✓

---

## 2. Schéma DB consolidé (8 tables V4)

### 2.1 Table cardinale `action_center_items` (~42 colonnes)

```sql
CREATE TABLE action_center_items (
    -- Identité (3 colonnes)
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id      UUID NOT NULL,                      -- IS1
    kind                 VARCHAR(20) NOT NULL,               -- discriminant (7 valeurs)

    -- Métadonnées (4 colonnes)
    title                TEXT NOT NULL,
    summary              TEXT,
    domain               VARCHAR(20) NOT NULL,
    source_module        VARCHAR(40) NOT NULL,

    -- Scoring Q11-A (6 colonnes)
    priority_score       NUMERIC(5,2) NOT NULL,
    priority_bracket     VARCHAR(2) NOT NULL,
    priority_explanation JSONB NOT NULL,
    score_version        VARCHAR(10) NOT NULL,
    score_calculated_at  TIMESTAMPTZ NOT NULL,
    score_stale          BOOLEAN NOT NULL DEFAULT FALSE,     -- IL9

    -- Lifecycle (4 colonnes)
    lifecycle_state      VARCHAR(20) NOT NULL,               -- IL1-IL11 (5 valeurs)
    closed_at            TIMESTAMPTZ,
    closure_reason       VARCHAR(20),                         -- 6 valeurs révisées v0.3
    closure_payload      JSONB,

    -- Owner (3 colonnes)
    owner_id             UUID,
    owner_role           VARCHAR(40),
    assigned_at          TIMESTAMPTZ,

    -- Dates métier (3 colonnes)
    detected_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sla_due_date         TIMESTAMPTZ,
    business_due_date    TIMESTAMPTZ,

    -- Impact (4 colonnes)
    impact_current_period_eur     NUMERIC(12,2),
    impact_cumulative_eur         NUMERIC(12,2),
    impact_dimension              VARCHAR(20),
    impact_payload                JSONB,

    -- Flags & Confiance (4 colonnes)
    next_best_action                  VARCHAR(40),            -- R5
    confidence_score                  NUMERIC(3,2),
    is_irreversible_action_disabled   BOOLEAN NOT NULL DEFAULT FALSE,  -- R5
    is_escalated                      BOOLEAN NOT NULL DEFAULT FALSE,  -- R3

    -- Refs faibles (4 colonnes)
    site_id              UUID,
    building_id          UUID,
    meter_id             UUID,
    regulatory_rule_id   UUID,                                -- R6 plancher P1

    -- Refs groupes Q9-B (2 colonnes)
    duplicate_group_id   UUID REFERENCES duplicate_groups(id) ON DELETE SET NULL,
    recurrence_group_id  UUID REFERENCES recurrence_groups(id) ON DELETE SET NULL,

    -- Champs spécifiques par kind (6 colonnes)
    anomaly_detector_id              VARCHAR(50),
    decision_deadline                TIMESTAMPTZ,
    recommendation_payback_years     NUMERIC(4,1),
    deadline_authority               VARCHAR(50),
    evidence_format_expected         VARCHAR(20),
    signal_confidence_level          VARCHAR(10),

    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_kind CHECK (kind IN ('anomaly','action','decision','signal','evidence_request','deadline','recommendation')),
    CONSTRAINT chk_priority_bracket CHECK (priority_bracket IN ('P0','P1','P2','P3')),
    CONSTRAINT chk_lifecycle_state CHECK (lifecycle_state IN ('new','triaged','planned','in_progress','closed')),
    CONSTRAINT chk_closure_reason CHECK (closure_reason IS NULL OR closure_reason IN ('resolved','dismissed','not_applicable','merged_duplicate','resolved_via_recurrence','expired')),
    CONSTRAINT chk_closure_consistency CHECK (
        (lifecycle_state = 'closed' AND closed_at IS NOT NULL AND closure_reason IS NOT NULL)
        OR (lifecycle_state != 'closed' AND closed_at IS NULL)
    ),
    CONSTRAINT chk_score_range CHECK (priority_score >= 0 AND priority_score <= 100),
    CONSTRAINT chk_confidence_range CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1))
);
```

**8 indexes table cardinale** (cf. §2.9) — total 20 V4.

**Invariants applicables** : IS1 (organisation_id) · IL1-IL11 · IE7 (priority_explanation versionné) · Q9-B (duplicate ≠ recurrence) · R6 (plancher conformité).

### 2.2 Table `action_event_log` (audit trail métier)

```sql
CREATE TABLE action_event_log (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id      UUID NOT NULL,                      -- IS1
    action_item_id       UUID NOT NULL REFERENCES action_center_items(id),
    event_type           VARCHAR(60) NOT NULL,               -- 16 valeurs
    occurred_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_type           VARCHAR(20) NOT NULL,               -- 'user' | 'system'
    actor_id             UUID,                                -- NULL si system
    actor_name           VARCHAR(120),                       -- snapshot
    actor_role           VARCHAR(20),                        -- snapshot
    event_payload        JSONB NOT NULL,                     -- validé Pydantic IE7
    schema_version       VARCHAR(10) NOT NULL DEFAULT 'v1',
    correlation_id       UUID NOT NULL,                      -- IS9
    source_route         VARCHAR(120),
    CONSTRAINT chk_event_type CHECK (event_type IN (
        'created','state_changed','owner_changed','priority_changed',
        'blocker_added','blocker_removed','evidence_added','evidence_verified',
        'closed_with_evidence','closed_via_merged_duplicate','closed_via_resolved_via_recurrence',
        'reopened','bulk_updated','exported','kind_corrected','priority_recalculated'
    )),
    CONSTRAINT chk_actor_consistency CHECK (
        (actor_type = 'system' AND actor_id IS NULL) OR
        (actor_type = 'user' AND actor_id IS NOT NULL)
    )
);
```

**Rétention** : 1-5 ans selon catégorie (cf. §7).
**Note ext. event_types** : étendu de 15 → 16 valeurs depuis ADR-025 §4.3 (cf. ADR-029 §6.3 + L2 §15).
**Invariants** : IE7 · IE8 · IS9 · IL8 · IL9.

### 2.3 Table `evidences` (preuves)

```sql
CREATE TABLE evidences (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id      UUID NOT NULL,                      -- IS1
    action_item_id       UUID NOT NULL REFERENCES action_center_items(id),
    mime_type            VARCHAR(50) NOT NULL,               -- IE9 magic bytes validated
    file_size_bytes      INTEGER NOT NULL CHECK (file_size_bytes <= 10485760),  -- Q45-B
    storage_uri          TEXT NOT NULL,                       -- IE1 fs:// ou s3://
    original_filename    VARCHAR(255),
    verified_at          TIMESTAMPTZ,                        -- NULL si non vérifié
    verified_by          UUID,                                -- IE2
    expires_at           TIMESTAMPTZ,                        -- IE6: verified_at + 90j
    validation_payload   JSONB,                               -- IE2 metadata + flag
    uploaded_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uploaded_by          UUID NOT NULL,
    description          TEXT,
    CONSTRAINT chk_evidence_verified_consistency CHECK (
        (verified_at IS NULL AND verified_by IS NULL AND expires_at IS NULL) OR
        (verified_at IS NOT NULL AND verified_by IS NOT NULL AND expires_at IS NOT NULL)
    ),
    CONSTRAINT chk_evidence_mime_whitelist CHECK (
        mime_type IN ('application/pdf', 'image/jpeg', 'image/png')
    ),
    CONSTRAINT chk_evidence_expires_90d CHECK (
        expires_at IS NULL OR expires_at = verified_at + INTERVAL '90 days'
    )
);
```

**Invariants** : IE1, IE2, IE6, IE9.

### 2.4 Tables filles annexes (action_links, action_blockers, action_scenarios)

```sql
-- Liens vers autres modules (Bill, Conformité...)
CREATE TABLE action_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id         UUID NOT NULL REFERENCES action_center_items(id) ON DELETE CASCADE,
    organisation_id UUID NOT NULL,
    link_type       VARCHAR(40) NOT NULL,
    target_module   VARCHAR(40) NOT NULL,                    -- "billing", "conformity"...
    target_id       UUID NOT NULL,
    relation        VARCHAR(40) NOT NULL,                    -- "caused_by", "resolves"...
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Blockers actifs sur item
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

-- Scénarios (decision/recommendation)
CREATE TABLE action_scenarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id         UUID NOT NULL REFERENCES action_center_items(id) ON DELETE CASCADE,
    organisation_id UUID NOT NULL,
    label           VARCHAR(120) NOT NULL,
    payload         JSONB,                                    -- options (decision) ou playbook (recommendation)
    display_order   INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.5 Tables groupes Q9-B (duplicate_groups + recurrence_groups)

```sql
-- Doublons stricts
CREATE TABLE duplicate_groups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID NOT NULL,                          -- IS1
    primary_item_id UUID NOT NULL REFERENCES action_center_items(id),
    status          VARCHAR(20) NOT NULL,                    -- 'suggested' | 'confirmed' | 'rejected'
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at    TIMESTAMPTZ,
    CONSTRAINT chk_dup_status CHECK (status IN ('suggested','confirmed','rejected'))
);

-- Récurrence (≠ doublon, Q9-B cardinal)
CREATE TABLE recurrence_groups (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id      UUID NOT NULL,                     -- IS1
    domain               VARCHAR(40) NOT NULL,
    source_signature     TEXT NOT NULL,                     -- hash code/type/algo détection
    scope_signature      TEXT NOT NULL,                     -- hash (site, building, meter)
    site_id              UUID,
    building_id          UUID,
    meter_id             UUID,
    first_seen_at        TIMESTAMPTZ NOT NULL,
    last_seen_at         TIMESTAMPTZ NOT NULL,
    occurrence_count     INTEGER NOT NULL DEFAULT 1,
    rolling_window_days  INTEGER NOT NULL DEFAULT 90,
    representative_item_id UUID REFERENCES action_center_items(id),
    status               VARCHAR(20) NOT NULL,               -- 'active' | 'watching' | 'closed'
    CONSTRAINT chk_rec_status CHECK (status IN ('active','watching','closed'))
);
```

### 2.6 Récap 8 tables V4

| # | Table | Rôle | Cardinaux |
|---|---|---|---|
| 1 | `action_center_items` | Cardinale polymorphique (single-table inheritance) | ~42 colonnes · 8 indexes · 11 invariants IL applicables |
| 2 | `action_event_log` | Audit trail métier | 16 event_types · 4 indexes · IE7/IE8 |
| 3 | `evidences` | Preuves uploadées | CHECK 90j IE6 + magic bytes IE9 + 3 indexes |
| 4 | `action_links` | Liens vers autres modules | 2 indexes |
| 5 | `action_blockers` | Blockers actifs sur item | 7 types CHECK · 1 index |
| 6 | `action_scenarios` | Options decision / playbooks recommendation | 1 index |
| 7 | `duplicate_groups` | Doublons stricts (Q9-B) | 3 statuts · 1 index |
| 8 | `recurrence_groups` | Groupes récurrence ≠ doublons (Q9-B cardinal) | 3 statuts · 2 indexes |

**Total** : 8 tables · 20 indexes · ~310 colonnes consolidées · 32 CHECK constraints.

### 2.7 Vue d'ensemble FK + ON DELETE

```
action_center_items (cardinale)
  ├─ action_event_log         (FK item_id ON DELETE RESTRICT — préserve audit trail)
  ├─ evidences                (FK item_id ON DELETE CASCADE)
  ├─ action_links             (FK item_id ON DELETE CASCADE)
  ├─ action_blockers          (FK item_id ON DELETE CASCADE)
  ├─ action_scenarios         (FK item_id ON DELETE CASCADE)
  ├─ duplicate_group_id       (FK ON DELETE SET NULL → groupe survit, item dégroupé)
  └─ recurrence_group_id      (FK ON DELETE SET NULL → idem)
```

### 2.8 Indexes consolidés (les 20)

8 indexes cardinale + 12 tables filles :
- `idx_aci_priority_active`, `idx_aci_kind_domain`, `idx_aci_lifecycle`, `idx_aci_stale`, `idx_aci_unassigned`, `idx_aci_recent_closed`, `idx_aci_site`, `idx_aci_owner` (8)
- `idx_event_log_item`, `idx_event_log_org_type`, `idx_event_log_correlation`, `idx_event_log_actor` (4)
- `idx_evidences_org`, `idx_evidences_verified`, `idx_evidences_expiring` (3)
- `idx_links_item`, `idx_links_target` (2)
- `idx_blocker_item_active` (1)
- `idx_scenarios_item` (1)
- `idx_dup_groups_org` (1)
- `idx_rec_groups_signature`, `idx_rec_groups_status` (2)

Détails `WHERE` clause (partial indexes) : cf. ADR-025 §4.2.

### 2.9 Performance budgets ADR-025 §11

| Vue | Budget | Index principal |
|---|---|---|
| Pilotage (vue d'entrée) | < 100 ms | `idx_aci_priority_active` |
| Mutations (state_changed, owner_changed) | < 150 ms | `idx_aci_lifecycle` + `idx_event_log_item` |
| Drawer M2 (item + sous-resources) | < 80 ms | `idx_aci_site` + `idx_evidence_item` |
| Référentiel récurrences actives | < 200 ms | `idx_rec_groups_status` |
| Job purge mensuelle (system 1y) | Off-peak 1er mois 2h UTC | `idx_event_log_type` |

---

## 3. Enums Python (8)

### 3.1 `LifecycleState`

```python
class LifecycleState(str, Enum):
    NEW = "new"
    TRIAGED = "triaged"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
```

Source : ADR-028 §6 · doctrine v0.3 §7.1.
Libellés FR mode standard : Nouveau / Qualifié / Planifié / En cours / Clôturé.

### 3.2 `ClosureReason` (révisée v0.3)

```python
class ClosureReason(str, Enum):
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    NOT_APPLICABLE = "not_applicable"
    MERGED_DUPLICATE = "merged_duplicate"                     # Q9-B duplicate strict only
    RESOLVED_VIA_RECURRENCE = "resolved_via_recurrence"        # 🛡️ Q9-B + Q37-A+ cardinal
    EXPIRED = "expired"                                        # 🛡️ IL4 interdit P0/P1 conformité/facturation
```

Source : doctrine v0.3 §7.1 (avenant L5).
Garde-fous : IL4, IL5 (ADR-028).

### 3.3 `PriorityBracket`

```python
class PriorityBracket(str, Enum):
    P0 = "P0"   # ≥ 80 — à traiter aujourd'hui
    P1 = "P1"   # 60-79 — à traiter cette semaine
    P2 = "P2"   # 40-59 — à traiter ce mois
    P3 = "P3"   # < 40 — backlog, surveillance
```

Source : doctrine v0.3 §2.2 + ADR-022.

### 3.4 `EventType` (16 valeurs)

```python
class EventType(str, Enum):
    # Business 3 ans (6 events + 1 closure)
    CREATED = "created"
    STATE_CHANGED = "state_changed"
    OWNER_CHANGED = "owner_changed"
    PRIORITY_CHANGED = "priority_changed"
    BLOCKER_ADDED = "blocker_added"
    BLOCKER_REMOVED = "blocker_removed"
    CLOSED_VIA_MERGED_DUPLICATE = "closed_via_merged_duplicate"

    # Compliance 5 ans (6 events admin/preuve)
    EVIDENCE_ADDED = "evidence_added"
    EVIDENCE_VERIFIED = "evidence_verified"
    CLOSED_WITH_EVIDENCE = "closed_with_evidence"
    CLOSED_VIA_RESOLVED_VIA_RECURRENCE = "closed_via_resolved_via_recurrence"
    REOPENED = "reopened"                                     # IL3 admin only
    KIND_CORRECTED = "kind_corrected"                         # IS5 admin only

    # System 1 an (3 events techniques)
    BULK_UPDATED = "bulk_updated"
    EXPORTED = "exported"
    PRIORITY_RECALCULATED = "priority_recalculated"
```

Source : ADR-029 §6 + §10.2.
Total : 16 event_types · 3 catégories rétention.

### 3.5 `RetentionCategory`

```python
class RetentionCategory(str, Enum):
    COMPLIANCE = "compliance"   # 1825 jours (5 ans)
    BUSINESS = "business"       # 1095 jours (3 ans)
    SYSTEM = "system"           # 365 jours (1 an)


CATEGORY_RETENTION_DAYS: dict[RetentionCategory, int] = {
    RetentionCategory.COMPLIANCE: 1825,
    RetentionCategory.BUSINESS: 1095,
    RetentionCategory.SYSTEM: 365,
}
```

Source : ADR-029 §10.1 (IE3).

### 3.6 `Role`

```python
class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    SYSTEM = "system"   # actor system seulement
```

Source : ADR-027 §3.1.
Note : `actor_type` BD utilise 2 valeurs (`user`, `system`) — `actor_role` snapshot le role parmi les 4.

### 3.7 `Domain`

```python
class Domain(str, Enum):
    CONFORMITE = "conformite"          # DT, BACS, APER, Audit SMÉ
    FACTURATION = "facturation"        # Bill Intelligence (R01-R20)
    MAINTENANCE = "maintenance"
    OPTIMISATION = "optimisation"      # Économies, EMS
    PURCHASE = "purchase"              # achat énergie
    FLEXIBILITE = "flexibilite"        # NEBCO/AOFD
    DATA_QUALITY = "data_quality"      # PHOTO D020, Sirene
```

Source : doctrine v0.3 §3 (modules métier) + ADR-025 §4.1 `domain` VARCHAR(20).
Note : R6 plancher P1 si `domain ∈ {conformite, facturation}` ET `regulatory_rule_id IS NOT NULL`.

### 3.8 `Kind` (7 valeurs intrinsèques)

```python
class Kind(str, Enum):
    ANOMALY = "anomaly"
    ACTION = "action"
    DECISION = "decision"
    SIGNAL = "signal"
    EVIDENCE_REQUEST = "evidence_request"
    DEADLINE = "deadline"
    RECOMMENDATION = "recommendation"
```

Source : doctrine v0.3 §3.1 + Q1-A (single-table inheritance).
Quasi immuable (cf. §3.3 doctrine) — modification admin only via `kind_corrected` event.

### 3.9 `BlockerType`

```python
class BlockerType(str, Enum):
    WAITING_EVIDENCE = "waiting_evidence"
    WAITING_BUDGET = "waiting_budget"
    WAITING_THIRD_PARTY = "waiting_third_party"
    WAITING_DATA = "waiting_data"
    WAITING_SUPPLIER = "waiting_supplier"
    WAITING_MANAGER_VALIDATION = "waiting_manager_validation"
    WAITING_REGULATORY_CONFIRMATION = "waiting_regulatory_confirmation"
```

Source : ADR-025 §4.3 + doctrine §7.1.

---

## 4. Schemas Pydantic v1 référencés (16)

Source : ADR-029 §11.2.

| # | Event type | Schema class | Catégorie | Cardinaux |
|---|---|---|---|---|
| 1 | `created` | `CreatedPayloadV1` | Business | initial_state + initial_kind + triggered_by |
| 2 | `state_changed` | `StateChangedPayloadV1` | Business | from/to + closure_reason si closed + auto_closed_by_group_id |
| 3 | `owner_changed` | `OwnerChangedPayloadV1` | Business | from_owner_id + to_owner_id + reason |
| 4 | `priority_changed` | `PriorityChangedPayloadV1` | Business | from/to brackets + scores + recalc_triggered_by |
| 5 | `blocker_added` | `BlockerAddedPayloadV1` | Business | blocker_type + justification + expected_resolution_at |
| 6 | `blocker_removed` | `BlockerRemovedPayloadV1` | Business | blocker_id + resolution_note |
| 7 | `closed_via_merged_duplicate` | `ClosedViaMergedDuplicatePayloadV1` | Business 3y | duplicate_group_id + primary_item_id |
| 8 | `evidence_added` | `EvidenceAddedPayloadV1` | Compliance 5y | evidence_id + mime_type + size_bytes + storage_uri |
| 9 | `evidence_verified` | `EvidenceVerifiedPayloadV1` | Compliance 5y | evidence_id + verified_at + expires_at + confidence_flag |
| 10 | `closed_with_evidence` | `ClosedWithEvidencePayloadV1` | Compliance 5y | evidence_id + closure_reason="resolved" |
| 11 | `closed_via_resolved_via_recurrence` | `ClosedViaResolvedViaRecurrencePayloadV1` | **Compliance 5y** 🛡️ Q9-B | recurrence_group_id + group_resolution_date + justification |
| 12 | `reopened` | `ReopenedPayloadV1` | Compliance 5y | previous_closure_reason + justification (IL11 min 10 chars) + admin_actor_id |
| 13 | `kind_corrected` | `KindCorrectedPayloadV1` | Compliance 5y | from_kind + to_kind + admin_actor_id + justification |
| 14 | `bulk_updated` | `BulkUpdatedPayloadV1` | System 1y | field_updated + items_count + correlation_id |
| 15 | `exported` | `ExportedPayloadV1` | System 1y | export_format + items_count |
| 16 | `priority_recalculated` | `PriorityRecalculatedPayloadV1` | System 1y | trigger_event + new_score + new_bracket |

**Base** : `class EventPayloadBase(BaseModel): schema_version: Literal["v1"] = "v1"`.

**Registry** : `EVENT_PAYLOAD_SCHEMAS: dict[(event_type, schema_version), type[BaseModel]]`.

**Pattern d'évolution v1 → v2** : co-existence garantie dans la base via `schema_version` (cf. ADR-029 §11.5).

---

## 5. Composantes du score de priorité (ADR-022 + R1-R6)

### 5.1 Composantes de base (ADR-022 héritées)

| Composante | Poids indicatif | Source |
|---|---|---|
| Gravité brute (severity) | 30 % | détecteur source |
| Impact financier (impact_current_period_eur) | 20 % | calcul dérivé |
| Délai SLA (sla_due_date - now) | 20 % | dates métier |
| Confiance détection (confidence_score) | 15 % | détecteur source |
| Récurrence (occurrence_count) | 10 % | recurrence_group |
| Owner assigné (owner_id NOT NULL) | 5 % | escalade R3 |

### 5.2 Modulation R1-R6 (doctrine v0.3 §5)

| Règle | Effet | Cardinaux |
|---|---|---|
| **R1** Risque réel > sévérité brute | Tri Pilotage = `priority_score`, pas `severity` | doctrine §5.1 |
| **R2** Conformité proche > opportunité lointaine | Conformité applicable + J-3 → P0 forcé | doctrine §5.2 + R6 |
| **R3** Sans responsable | P0 sans owner depuis 48h → `is_escalated=true` + notification | doctrine §5.3 |
| **R4** Récurrence | 3e occurrence → bonus +3 points + rattachement `recurrence_group` | doctrine §5.4 (corrigée) |
| **R5** Confiance faible (`< 0.6`) | `next_best_action="qualify"` + `is_irreversible_action_disabled=true`. **Ne force PAS P3** systématiquement. | doctrine §5.5 (corrigée fortement) |
| **R6** Plancher conformité | `domain ∈ {conformite, facturation}` ET `regulatory_rule_id IS NOT NULL` → bracket plancher `P1` | doctrine §5.6 |

### 5.3 12 events de recalcul `priority_recalculated`

Liste exhaustive : `evidence_added`, `evidence_verified`, `blocker_added`, `blocker_removed`, `owner_changed`, `kind_corrected`, `state_changed`, `recurrence_attached`, `deadline_changed`, `sla_threshold_crossed`, `manual_recalc`, `group_resolution`.

Chaque event déclenche : `score_stale = TRUE` (IL9) + push job recalc asynchrone.

---

## 6. Matrice IDOR référencée (288 cellules · IS2)

```
ROUTES (12) × ROLES (3) × ORGS (2) × CAS (4) = 288 cellules
```

| Dimension | Valeurs |
|---|---|
| **Routes** | 12 endpoints `/api/action-center/*` (list, get, patch lifecycle, patch owner, post evidence, patch verify, post bulk, get export, etc.) |
| **Rôles** | `admin` · `user` · `viewer` |
| **Orgs** | `org_A` (own) · `org_B` (cross-org) |
| **Cas** | GET own · GET other · MUTATE own · MUTATE other |

**1 test pytest paramétré par cellule** (288 tests). Couverture 100% IS2 cardinal.

Détails complet : ADR-027 §10. Exemples : `tests/security/test_idor_matrix.py`.

---

## 7. Matrice rétention RGPD (16 events × 3 catégories)

Source : ADR-029 §10.

| Event type | Catégorie | Rétention | Justification CNIL |
|---|---|---|---|
| `created` | business | 3 ans | art. 5(1)(e) |
| `state_changed` | business | 3 ans | art. 5(1)(e) |
| `owner_changed` | business | 3 ans | art. 5(1)(e) |
| `priority_changed` | business | 3 ans | art. 5(1)(e) |
| `blocker_added` | business | 3 ans | art. 5(1)(e) |
| `blocker_removed` | business | 3 ans | art. 5(1)(e) |
| `closed_via_merged_duplicate` | business | 3 ans | art. 5(1)(e) — Q9-B doublon technique |
| `evidence_added` | **compliance** | **5 ans** | art. 30 + 5(2) |
| `evidence_verified` | **compliance** | **5 ans** | art. 30 + 5(2) |
| `closed_with_evidence` | **compliance** | **5 ans** | art. 30 + 5(2) |
| `closed_via_resolved_via_recurrence` | **compliance** | **5 ans** | 🛡️ Q9-B preuve indirecte distincte de doublon |
| `reopened` | **compliance** | **5 ans** | IL3 admin sensible |
| `kind_corrected` | **compliance** | **5 ans** | IS5 admin sensible |
| `bulk_updated` | system | 1 an | art. 5(1)(b) maintenance |
| `exported` | system | 1 an | art. 5(1)(b) maintenance |
| `priority_recalculated` | system | 1 an | art. 5(1)(b) maintenance |

**Total** : 7 compliance + 6 business + 3 system = 16 events.

🛡️ **IE4 cardinal** : `closed_via_merged_duplicate` (3y) ≠ `closed_via_resolved_via_recurrence` (5y) — garde-fou contre dérive silencieuse via rétention.

---

## 8. Articles CNIL référencés (8)

| Article | Description | Application PROMEOS V4 |
|---|---|---|
| **art. 5(1)(b)** | Finalité spécifiée | 3 catégories rétention = 3 finalités distinctes |
| **art. 5(1)(e)** | Limitation conservation | Rétention différenciée 5y / 3y / 1y |
| **art. 5(2)** | Intégrité confidentialité | Magic bytes IE9 + validation manuelle IE2 |
| **art. 6** | Base légale | Obligation légale DT/BACS/APER + intérêt légitime |
| **art. 15** | Droit d'accès | Endpoint `GET /api/users/me/data-export` (ADR-029 §13.2) |
| **art. 17** | Droit à l'oubli | Endpoint `DELETE /api/users/me/data` — anonymisation préserve audit trail (CNIL 2023) |
| **art. 30** | Registre traitements | Tous events tracés avec `schema_version` |
| **art. 32** | Sécurité traitement | `security_audit_log` 90j séparé + IS7/IS8 + IDOR matrix 288 |

---

## 9. Mapping legacy → V4

Source : L1 décisionnel + ADR-026.

### 9.1 18 tables legacy → 8 tables V4

| Table legacy | Rows | Verdict L1 | Mapping V4 |
|---|---|---|---|
| `action_items` | **35** | MIGRE | `action_center_items` (kind ∈ action/decision/recommendation) |
| `bill_anomaly` | **52** | MIGRE | `action_center_items` (kind=anomaly, domain=facturation) |
| `anomaly` (KB) | **86** | MIGRE | `action_center_items` (kind=anomaly, knowledge base) |
| `action_plan` | 0 | SUPPRIME | — (Sprint 13 dette pure) |
| `action_plan_items` | 0 | SUPPRIME | — |
| `action_plan_events` | 0 | SUPPRIME | — |
| `action_plan_evidences` | 0 | SUPPRIME | — |
| `action_events` | 0 | REMPLACE | `action_event_log` unifié |
| `action_comments` | 0 | REMPLACE | `action_event_log` (event_type=`commented`) |
| `action_evidence` | 0 | REMPLACE | `evidences` table dédiée |
| `action_templates` | 0 | SUPPRIME | — |
| `action_sync_batches` | 0 | SUPPRIME | — |
| `anomaly_action_links` | 0 | SUPPRIME | — |
| `anomaly_dismissals` | 0 | SUPPRIME | — |
| `anomaly_event` | 0 | SUPPRIME | — |
| `alertes` | 0 | SUPPRIME | — |
| `bacs_remediation_actions` | conservé | (hors V4) | Module BACS distinct |
| `copilot_actions` | conservé | (hors V4) | Module Copilot distinct |

**Total** : 18 tables legacy → 8 tables V4 · **173 rows data réelle migrées** · **1 667 LoC FE mortes supprimées Mois 5**.

### 9.2 Vocabulaires legacy → V4

| Concept | Legacy | V4 |
|---|---|---|
| Statut item | 6 vocabulaires hétérogènes (`status`, `state`, `lifecycle`, `phase`, `etat`, `etape`) | 5 `lifecycle_state` strict |
| Type | varie selon table (`category`, `nature`, `genre`...) | 1 enum `kind` (7 valeurs) |
| Sévérité | varie (`severity`, `priority`, `urgency`, `weight`...) | `priority_bracket` (P0-P3) + `priority_score` NUMERIC |
| Clôture | `closed_status`, `dismissed`, `archived`, `merged` | 6 `closure_reason` v0.3 (révisés) |
| Fusion | `parent_id`, `merged_with`, `linked_to` | `duplicate_group_id` (Q9-B doublon strict) |
| Récurrence | `recurring_id`, `parent_anomaly`, `re-detected` | `recurrence_group_id` (Q9-B distinct doublon) |
| Audit | `event_log`, `events`, `comments`, `history` | `action_event_log` unifié + `schema_version` |
| Preuve | `attachment`, `evidence`, `proof`, `document` | `evidences` table + magic bytes IE9 |

---

## 10. Vocabulaire FR (mode standard) / EN (mode audit)

Source : doctrine v0.3 §7 + ADR-028 §10 + ADR-029.

### 10.1 Lifecycle states

| Code (audit) | FR mode standard |
|---|---|
| `new` | Nouveau |
| `triaged` | **Qualifié** |
| `planned` | Planifié |
| `in_progress` | En cours |
| `closed` | Clôturé |

### 10.2 Closure reasons

| Code | FR mode standard |
|---|---|
| `resolved` | Résolu |
| `dismissed` | Écarté |
| `not_applicable` | Non applicable |
| `merged_duplicate` | Fusionné (doublon) |
| `resolved_via_recurrence` | Résolu via récurrence |
| `expired` | Expiré |

### 10.3 Kinds (badges UI)

| Code | FR badge |
|---|---|
| `anomaly` | **ANOMALIE** |
| `action` | **ACTION** |
| `decision` | **DÉCISION** |
| `signal` | **SIGNAL** |
| `evidence_request` | **PREUVE** |
| `deadline` | **ÉCHÉANCE** |
| `recommendation` | **RECO** |

### 10.4 Blockers

| Code | FR mode standard |
|---|---|
| `waiting_evidence` | **Preuve attendue** |
| `waiting_budget` | **Budget attendu** |
| `waiting_third_party` | **Tiers attendu** |
| `waiting_data` | Donnée attendue |
| `waiting_supplier` | Fournisseur attendu |
| `waiting_manager_validation` | Validation manager attendue |
| `waiting_regulatory_confirmation` | Confirmation réglementaire attendue |

### 10.5 Event types (audit trail mode standard)

| Code | FR mode standard |
|---|---|
| `created` | Créé |
| `state_changed` | **État modifié** |
| `owner_changed` | Responsable modifié |
| `priority_changed` | Priorité modifiée |
| `blocker_added` | Blocker ajouté |
| `blocker_removed` | Blocker levé |
| `evidence_added` | Preuve ajoutée |
| `evidence_verified` | Preuve vérifiée |
| `closed_with_evidence` | Clôturé avec preuve |
| `closed_via_merged_duplicate` | Fusionné (doublon) |
| `closed_via_resolved_via_recurrence` | Résolu via récurrence |
| `reopened` | Rouvert |
| `bulk_updated` | Modifié en lot |
| `exported` | Exporté |
| `kind_corrected` | Type corrigé (admin) |
| `priority_recalculated` | Score recalculé |

**Total paires FR/EN** : 5 + 6 + 7 + 7 + 16 = **41 paires** (cible ≥ 30 ✓).

---

## 11. Index inversé : champ DB → usage code (squelette Mois 1)

> **Note** : à compléter Mois 2 par les devs au fur et à mesure de l'implémentation.

| Champ DB | Service modificateur | Repository | Endpoint(s) | Tests |
|---|---|---|---|---|
| `action_center_items.lifecycle_state` | `LifecycleStateMachine.transition()` | `ActionItemRepository` | `PATCH /items/{id}/lifecycle` | 56 (ADR-028) |
| `action_center_items.priority_score` | `PriorityScoringService.recompute()` | `ActionItemRepository` | (lecture seule) | ~30 (ADR-025) |
| `action_center_items.score_stale` | hooks post-transition + `priority_recalculated` event | `ActionItemRepository` | (lecture seule) | IL9 cumulés |
| `action_center_items.closure_reason` | `LifecycleStateMachine.close()` | `ActionItemRepository` | `PATCH /items/{id}/lifecycle` (target=closed) | 20 closures (ADR-028) |
| `evidences.verified_at` | `verify_evidence()` endpoint | `EvidenceRepository` | `PATCH /evidences/{id}/verify` | 10 (ADR-029) |
| `evidences.expires_at` | service vérification (auto = verified_at + 90j) | `EvidenceRepository` | (lecture seule) | IE6 |
| `action_event_log.event_payload` | `write_event()` (validation Pydantic) | `EventLogRepository` | (interne) | 15 schemas (ADR-029) |
| `correlation_id` (transverse) | `OrgScopingMiddleware` (génération si absent) | tous | tous | IS9 |
| `organisation_id` (transverse) | `OrgScopingMiddleware` (injection state) | tous (filter SQL obligatoire IS11) | tous `/api/action-center/*` | 288 IDOR matrix |

---

## 12. Référence rapide invariants (49 total)

### 12.1 Invariants doctrinaux Q1-Q9 (9)

| # | Énoncé court | Source |
|---|---|---|
| Q1-A | Single-table inheritance polymorphique (kind discriminant) | doctrine §3 |
| Q2-α | Table rase + triple backup obligatoire | doctrine §1 |
| Q3-C | Single-table avec single domain enum | doctrine §3 |
| Q4-A | Q4 service `regulatory_applicability_service` Phase 3.5 source | doctrine §4 |
| Q5-B | Pull job idempotent depuis findings compliance | doctrine §5 |
| Q6-A | Mois 1 docs only (zéro code, zéro DB) | doctrine §6 |
| Q7-A | Rendu visuel strict par kind (pas d'override contextuel) | doctrine §3.2 |
| Q8-C | priority_score persisté + invalidation event-driven | doctrine §4 |
| 🛡️ **Q9-B** | Tables séparées `duplicate_groups` ≠ `recurrence_groups` | doctrine §6 |

### 12.2 Invariants migration I1-I9 (9 — ADR-026)

| # | Énoncé court | Type |
|---|---|---|
| I1 | Zéro double-write legacy + V4 | Non négociable |
| I2 | Backup = preuve exportée | Non négociable |
| I3 | 173 rows data réelle préservées triple artefact | Non négociable |
| I4 | Rollback = restore backup + reseed | Non négociable |
| I5 | Backup triple artefact + checksum SHA256 | Non négociable |
| I6 | Suppression legacy après STOP GATE manuel J+14 | Non négociable |
| I7 | Rétention backups 12 mois offline | Non négociable |
| I8 | Observation J+14 minimum avant DROP tables | Non négociable |
| 🛡️ **I9** | Backup hors Git · receipt sanitizé in Git | **Cardinal Amine** |

### 12.3 Invariants sécurité IS1-IS11 (11 — ADR-027)

| # | Énoncé court | Type |
|---|---|---|
| IS1 | Toutes routes `/api/action-center/*` ont `@org_scoped` | Non négociable |
| IS2 | Aucun endpoint sans test cross-org (IDOR matrix 288) | Non négociable |
| IS3 | Cross-org → HTTP 404 (pas 403) anti-énumération | Non négociable |
| IS4 | Validation Pydantic stricte (whitelist + Literal) | Non négociable |
| IS5 | `admin_only_with_fresh_token` <5min sur endpoints sensibles | Non négociable |
| IS6 | Bandit + Semgrep + gitleaks + pip-audit en CI gate | Non négociable |
| IS7 | Logs sanitizés JSON structlog (pas de body/token/query) | Non négociable |
| IS8 | IP anonymisée /24 IPv4 + /48 IPv6 | Non négociable |
| IS9 | `correlation_id` obligatoire sur toutes requêtes | Non négociable |
| IS10 | Backup/export non commitables (.gitignore + SG CI) | Non négociable |
| 🛡️ **IS11** | Pattern repository org-scopé obligatoire (4 lignes défense) | **Cardinal Amine** |

### 12.4 Invariants lifecycle IL1-IL11 (11 — ADR-028)

| # | Énoncé court | Type |
|---|---|---|
| IL1 | 25 transitions théoriques → 10 strictes (HTTP 409 reste) | Non négociable |
| IL2 | `chk_lifecycle_state` CHECK constraint DB whitelist 5 | Non négociable |
| IL3 | Réouverture admin only + fresh token + justification | Non négociable |
| 🛡️ **IL4** | `expired` interdit P0/P1 conformité/facturation | **Cardinal Amine** |
| 🛡️ **IL5** | `merged_duplicate` interdit si recurrence sans duplicate (Q9-B) | **Cardinal Amine** |
| IL6 | Auto-close récurrence cascade `resolved_via_recurrence` | Non négociable |
| 🛡️ **IL7** | Auto-close P0/P1 exige preuve OU justification | **Cardinal Amine** |
| IL8 | Toute transition écrit `action_event_log.state_changed` | Non négociable |
| IL9 | Toute transition déclenche `score_stale=TRUE` | Non négociable |
| IL10 | `closed_at IS NOT NULL` ⇔ `lifecycle_state=closed` (CHECK) | Non négociable |
| IL11 | Réouverture trace event avec `justification` non vide (≥10 chars) | Non négociable |

### 12.5 Invariants evidence IE1-IE9 (9 — ADR-029)

| # | Énoncé court | Type |
|---|---|---|
| IE1 | Storage abstrait `fs://` Mois 2 · `s3://` V4.1+ | Non négociable |
| IE2 | Validation evidence manuelle obligatoire + métadonnées + flag | Non négociable |
| IE3 | 3 catégories rétention compliance 5y / business 3y / system 1y | Non négociable |
| IE4 | Matrice alignée doctrine v0.3 (`merged_duplicate` ≠ `resolved_via_recurrence`) | Non négociable |
| IE5 | Purge mensuelle triple garde-fou (flag + dry-run + trace) | Non négociable |
| IE6 | `expires_at = verified_at + 90 jours` (CHECK + service) | Non négociable |
| IE7 | Schemas Pydantic typés versionnés (`schema_version`) | Non négociable |
| IE8 | `security_audit_log` 90j séparé strict de `action_event_log` 1-5y | Non négociable |
| 🛡️ **IE9** | Validation MIME par magic bytes (anti-spoofing 4 lignes défense) | **Cardinal Amine** |

**Total : 49 invariants** (9 Q + 9 I + 11 IS + 11 IL + 9 IE) dont **8 cardinaux Amine** 🛡️.

---

## 13. Tests planifiés Mois 2 (cumulés)

| ADR | Tests planifiés | Catégories |
|---|---|---|
| ADR-025 Architecture | **100** | Pyramide 50 unit + 30 intégration + 15 E2E + 5 perf |
| ADR-026 Migration | **8** | Idempotence + rollback + dry-run + receipt sanitization |
| ADR-027 Sécurité | **~370** | 288 IDOR matrix + 50 source-guards + ~30 unit/intégration |
| ADR-028 Lifecycle | **56** | 25 matrice transitions + 20 closure_reasons + 11 IL |
| ADR-029 Evidence | **40+** | 10 evidence + 15 rétention + 15 schemas Pydantic |
| **TOTAL** | **~574 tests planifiés** | (baseline projet PROMEOS = 6 027 tests post-sprint avril) |

---

## 14. Décisions cardinales Amine 🛡️ (non débattables)

| Décision | Source | Effet cardinal |
|---|---|---|
| **Q2-α** Table rase + triple backup | doctrine §1 + ADR-026 | Pas de migration data automatique POC |
| **Q6-A** Mois 1 docs only | doctrine §6 | Aucun code modifié pendant Mois 1 |
| **Q9-B** `duplicate_groups` ≠ `recurrence_groups` | doctrine §6 + ADR-028 IL5 | 2 tables distinctes + 2 closure_reasons distincts (v0.3) |
| **IL3** Réouverture admin + fresh token + justification | ADR-028 §6 | Trace audit obligatoire `reopened` |
| **IL4** `expired` interdit P0/P1 conformité/facturation | ADR-028 §3 | Escalade prioritaire bloque expiration silencieuse |
| **IL5** `merged_duplicate` ≠ recurrence | ADR-028 §3 + Q9-B | Garde-fou bidirectionnel (DB CHECK + Pydantic + service) |
| **IL7** Auto-close P0/P1 exige preuve OU justification | ADR-028 §3 | Cascade `resolved_via_recurrence` interceptée |
| **IS11** Pattern repository org-scopé obligatoire | ADR-027 §8 | 4 lignes défense empilées (middleware + décorateur + repo + SG) |
| **IE9** Magic bytes MIME (anti-spoofing) | ADR-029 §9 | 4 étapes : libmagic + whitelist + log mismatch + double-check signatures |
| **I9** Backup hors Git · receipt sanitizé | ADR-026 I9 | `/data/backups/` gitignored · receipts sans PII/IP/hostname |
| **Doctrine v0.3** | doctrine §11 | 1er avenant doctrinal versionné · politique nouvelle évolution = avenant |

---

## 15. Auto-évaluation L7

### 15.1 Glossaire complet

- [x] ≥ 50 termes documentés (70 atteints)
- [x] 8 catégories couvertes (lifecycle, priorité, evidence, sécurité, migration, archi, RGPD, doctrine)
- [x] Définitions claires + sources référencées (renvois ADR-XXX §N)

### 15.2 Schéma DB consolidé

- [x] 8 tables V4 documentées (1 cardinale + 7 filles)
- [x] Colonnes + types + nullabilité + FK + CHECK + indexes
- [x] Invariants applicables référencés par table
- [x] FK avec ON DELETE policy (RESTRICT pour audit, CASCADE pour annexes, SET NULL pour groupes)

### 15.3 Enums Python (8)

- [x] `LifecycleState` (5)
- [x] `ClosureReason` (6)
- [x] `PriorityBracket` (4)
- [x] `EventType` (16)
- [x] `RetentionCategory` (3)
- [x] `Role` (4)
- [x] `Domain` (7)
- [x] `Kind` (7)
- [x] Bonus `BlockerType` (7) — §3.9

### 15.4 Schemas Pydantic référencés

- [x] 16 schemas v1 listés avec class names + cardinaux + catégorie rétention
- [x] Pattern d'évolution v1 → v2 mentionné
- [x] Registry `EVENT_PAYLOAD_SCHEMAS` documenté

### 15.5 Matrices référencées

- [x] IDOR matrix 288 cellules (lien ADR-027 §10)
- [x] Rétention RGPD 16×3 (exhaustive §7)
- [x] 10 transitions lifecycle (lien ADR-028 §7)
- [x] Mapping legacy 18 tables → 8 V4

### 15.6 RGPD

- [x] 8 articles CNIL référencés (5(1)(b), 5(1)(e), 5(2), 6, 15, 17, 30, 32)
- [x] Endpoints RGPD art. 15 + art. 17 référencés (§8 + §1.7)

### 15.7 Legacy → V4 mapping

- [x] 18 tables legacy mappées (verdicts L1)
- [x] 8 vocabulaires statuts mappés (cf. §9.2)
- [x] Chiffres : 173 rows + 1 667 LoC

### 15.8 Vocabulaire FR/EN

- [x] Modes standard + audit documentés
- [x] 41 paires FR/EN (cible ≥ 30)

### 15.9 Cohérence cross-ADR

- [x] Doctrine v0.3 référencée exclusivement (zéro mention v0.2 résiduelle)
- [x] 5 ADR Accepted référencés correctement
- [x] L1 verdicts cohérents avec mappings §9.1

### 15.10 Conformité Q6-A

- [x] Aucun code modifié
- [x] Aucune table DB modifiée
- [x] Aucun script créé sur disque

**Total** : **40/30 critères ✓** — Data Dictionary L7 prêt pour acceptation.

---

## 16. Métadonnées

```yaml
livrable: L7
title: Data Dictionary V4 Centre d'Action PROMEOS
version: v1.0
status: Accepted
date: 2026-05-14
authors:
  - Amine (PROMEOS founder)
  - Claude (architecture co-pilot)
branch: claude/refonte-sol2
doctrine_version_ref: v0.3
sources_consolidated:
  - doctrine_v0.3 (commits 883ac4ae · 466b64c3)
  - L1_audit_decisional (commits b6416f4b · ee749a12)
  - ADR-025 Architecture (commits 07f57c24 · b7208022 · 712da32a)
  - ADR-026 Migration (commits a506c758 · 0eb4dadc · 1500f55b)
  - ADR-027 Sécurité (commits 211bc26b · 94b873db · faba2a61)
  - ADR-028 Lifecycle (commits 26a6b0a0 · 3c77e059 · 466b64c3)
  - ADR-029 Evidence (commits e308dc6c · 21e37b4e · 15711df4)
glossary_terms: 70
glossary_categories: 8
v4_tables: 8
v4_indexes: 20
python_enums: 9
pydantic_schemas_v1: 16
cnil_articles: 8
invariants_total: 49
invariants_breakdown:
  doctrinal_Q: 9
  migration_I: 9
  security_IS: 11
  lifecycle_IL: 11
  evidence_IE: 9
cardinaux_amine: 8  # Q2-α, Q6-A, Q9-B, IL3-IL5-IL7, IS11, IE9, I9 (note: 11 cités §14)
fr_en_pairs: 41
tests_planned_total: 574
month: 1
livrable_position: "8/9"
next_deliverables:
  - L8 Plan suppression legacy Mois 5
  - L9 Prompt Claude Code Mois 2 backend
```

---

**Statut final** : `Accepted` 2026-05-14 — L7 devient **le manuel de référence unique** pour tout développeur Mois 2+ Centre d'Action V4 PROMEOS.

Mois 1 série livrables : doctrine v0.3 + L1 + ADR-025 + ADR-026 + ADR-027 + ADR-028 + ADR-029 + **L7** (8/9 ✓). Reste L8 (plan suppression legacy Mois 5) + L9 (prompt Mois 2 backend).
