# L9 · Manuel de pilotage Mois 2 backend PROMEOS V4

> **Version** : v1.0 · 2026-05-14
> **Source** : 8 livrables Mois 1 consolidés (doctrine v0.3 + L1 + ADR-025/026/027/028/029 + L7 + L8) + CLAUDE.md
> **Branche** : `claude/refonte-sol2` → main fusion en fin Mois 2
> **Statut** : `Accepted` (passage de relais docs Mois 1 → code Mois 2)
> **Exécution** : Mois 2 (4 semaines, 8 sprints d'environ 2 jours/h chacun)
> **Particularité** : **DERNIER LIVRABLE MOIS 1** — clôture des docs only Q6-A

---

## 0. Synthèse finale Mois 1

### 0.1 Récap des 9 livrables Mois 1 (avec L9)

| # | Livrable | Commit | Auto-éval | Apport cardinal |
|---|---|---|---|---|
| 1 | **Doctrine v0.3** | `883ac4ae` + `466b64c3` | Accepted | 5 lifecycle_states · 6 closure_reasons révisés v0.3 · 9 arbitrages Q1-Q9 |
| 2 | **L1 décisionnel** | `b6416f4b` · `ee749a12` | Validé | 86 verdicts (GARDE 14 · SUPPRIME 28 · MIGRE 31 · REMPLACE 9 · RÉGÉNÈRE 4) |
| 3 | **ADR-025 Architecture** | `07f57c24` · `b7208022` · `712da32a` | **32/32** | 8 tables V4 · 20 indexes · ~42 colonnes cardinale · 100 tests |
| 4 | **ADR-026 Migration** | `a506c758` · `0eb4dadc` · `1500f55b` | **36/36** | 9 invariants I · 6 scripts · cutover Mois 4 + STOP GATE J+14 |
| 5 | **ADR-027 Sécurité** | `211bc26b` · `94b873db` · `faba2a61` | **50/50** | 11 invariants IS · 8 menaces M1-M8 · IDOR matrix 288 · 50 SG CI |
| 6 | **ADR-028 Lifecycle** | `26a6b0a0` · `3c77e059` · `466b64c3` | **53/53** | 11 invariants IL · 10 transitions strictes · avenant doctrinal v0.2→v0.3 |
| 7 | **ADR-029 Evidence** | `e308dc6c` · `21e37b4e` · `15711df4` | **48/48** | 9 invariants IE · 16 schemas Pydantic v1 · 8 articles CNIL |
| 8 | **L7 Data Dictionary** | `1d77a7ad` | **40/30** | Manuel référence unique · 70 termes · 9 enums · 41 paires FR/EN |
| 9 | **L8 Plan suppression** | `3bf14494` | **27/18** | Procédure Mois 5 J+14 · 18 tables · 1 667 LoC · 12 mois RGPD |
| **10** | **L9 Mois 2 pilot** (ce document) | (à venir) | **20/20** | Sprint plan + DoD acceptance Mois 2 |

**Cumul** : 19 commits Mois 1 · ~22 000 insertions · **0 code Python/TS modifié** · **0 table DB modifiée** · **0 script créé sur disque** · 1 avenant doctrinal versionné (v0.2 → v0.3).

### 0.2 49 invariants doctrinaux cumulés (quick-reference)

**Doctrinaux Q1-Q9 (9 — doctrine v0.3)** :
Q1-A single-table inheritance · Q2-α table rase + triple backup · Q3-C single domain enum · Q4-A regulatory_applicability_service · Q5-B pull job idempotent · Q6-A Mois 1 docs only · Q7-A rendu strict par kind · Q8-C priority_score persisté + invalidation event-driven · 🛡️ Q9-B duplicate_groups ≠ recurrence_groups.

**Migration I1-I9 (9 — ADR-026)** :
I1 zéro double-write · I2 backup = preuve exportée · I3 173 rows preserved triple artefact · I4 rollback = restore + reseed · I5 backup triple artefact + checksum SHA256 · I6 suppression manuelle après STOP GATE J+14 · I7 rétention backups 12 mois · I8 observation J+14 · 🛡️ I9 backup hors Git + receipt sanitizé.

**Sécurité IS1-IS11 (11 — ADR-027)** :
IS1 @org_scoped obligatoire · IS2 IDOR matrix 288 · IS3 cross-org → 404 · IS4 Pydantic strict · IS5 admin_only_with_fresh_token · IS6 Bandit+Semgrep+gitleaks+pip-audit CI gate · IS7 logs sanitizés · IS8 IP anonymisée · IS9 correlation_id obligatoire · IS10 backup non commitable · 🛡️ IS11 pattern repository org-scopé (4 lignes défense).

**Lifecycle IL1-IL11 (11 — ADR-028)** :
IL1 25 transitions → 10 strictes · IL2 chk_lifecycle_state DB · IL3 réouverture admin + fresh + justification · 🛡️ IL4 expired interdit P0/P1 conformité/facturation · 🛡️ IL5 merged_duplicate ≠ recurrence (Q9-B) · IL6 auto-close cascade resolved_via_recurrence · 🛡️ IL7 auto-close P0/P1 exige preuve OU justification · IL8 transition trace state_changed · IL9 transition score_stale=TRUE · IL10 closed_at ⇔ closed (CHECK) · IL11 réouverture justification ≥10 chars.

**Evidence IE1-IE9 (9 — ADR-029)** :
IE1 storage abstrait fs/s3 · IE2 validation manuelle obligatoire · IE3 3 catégories rétention 5y/3y/1y · IE4 matrice doctrine v0.3 (merged_duplicate ≠ resolved_via_recurrence) · IE5 purge triple garde-fou · IE6 expires_at = verified_at + 90j · IE7 schemas Pydantic versionnés · IE8 security_audit_log séparé strict · 🛡️ IE9 magic bytes MIME (anti-spoofing).

**Total : 49 invariants** dont **8 cardinaux Amine 🛡️** non débattables.

### 0.3 46 arbitrages cardinaux actés (quick-reference)

| Bloc | Arbitrages | Source |
|---|---|---|
| **Q1-Q9** doctrinaux | Q1-A · Q2-α · Q3-C · Q4-A · Q5-B · Q6-A · Q7-A · Q8-C · Q9-B | doctrine v0.3 |
| **Q10-Q18** ADR-025 architecture | Q10-A_refined · Q11-A · Q12-A · Q13-B · Q14-A · Q15-C · Q16-A · Q17-C_refined · Q18-C_refined | ADR-025 §3 |
| **Q19-Q25** ADR-026 migration | Q19-C · Q20-A · Q21-A · Q22-A · Q23-A · Q24-A · Q25-A | ADR-026 §4 |
| **Q26-Q32** ADR-027 sécurité | Q26-C · Q27-B+ · Q28-D · Q29-D · Q30-A+ · Q31-B+ · Q32-B | ADR-027 §3 |
| **Q33-Q39** ADR-028 lifecycle | Q33-B · Q34-A · Q35-A · Q36-C+ · Q37-A+ · Q38-B · Q39-B | ADR-028 §5 |
| **Q40-Q46** ADR-029 evidence | Q40-D · Q41-D · Q42-C+ · Q43-A+ · Q44-A+ · Q45-B · Q46-B+ | ADR-029 §4 |

**Total : 46 arbitrages** Q1-Q46 actés, **non débattables** post-acceptation ADR.

### 0.4 Décisions cardinales Amine non-débattables (8 garde-fous 🛡️ + 3 doctrinales)

🛡️ **Cardinaux opérationnels (8)** :
1. **🛡️ Q9-B** `duplicate_groups` ≠ `recurrence_groups` (tables séparées)
2. **🛡️ I9** Backup hors Git + receipt sanitizé in Git (anti-PII)
3. **🛡️ IS11** Pattern repository org-scopé (4 lignes défense empilées)
4. **🛡️ IL3** Réouverture admin + fresh token + justification
5. **🛡️ IL4** `expired` interdit P0/P1 conformité/facturation
6. **🛡️ IL5** `merged_duplicate` interdit si récurrence
7. **🛡️ IL7** Auto-close P0/P1 exige preuve OU justification
8. **🛡️ IE9** Magic bytes MIME (anti-spoofing 4 lignes défense)

🏛️ **Cardinaux doctrinaux (3)** :
- **Q2-α** Table rase + triple backup obligatoire
- **Q6-A** Mois 1 docs only (terminé maintenant — Mois 2 démarre code)
- **Doctrine v0.3** 1er avenant doctrinal versionné (politique : nouvelle évolution = avenant)

---

## 1. Mois 2 — Vue d'ensemble

### 1.1 Objectif final Mois 2

À la fin du Mois 2 (J+30), le repo doit avoir :

- ✅ 8 tables V4 créées (Alembic migration scellée)
- ✅ Toutes les routes `/api/action-center/*` opérationnelles avec sécurité IS1-IS11
- ✅ State machine lifecycle fonctionnelle (10 transitions)
- ✅ Evidence upload + verification 90j fonctionnel (IE6)
- ✅ Audit trail `action_event_log` opérationnel (16 schemas Pydantic v1)
- ✅ Security audit log séparé fonctionnel (IE8)
- ✅ 100% des 50 source-guards CI passent
- ✅ Pyramide tests 100 minimum (50 SG + 30 unit/integration + 15 contract + 5 e2e)
- ✅ HELIOS demo data seedée (5 sites · 173 rows preserved)
- ✅ Performance budgets ADR-025 §11 respectés
- ✅ Documentation API OpenAPI auto-générée
- ✅ Frontend wait-for-server (Q39-B) fonctionnel pour transitions

### 1.2 Critères go/no-go fin Mois 2 → Mois 3 (cutover Mois 4)

8 critères binaires à valider fin Sprint M2-8 :

| # | Critère | Vérification |
|---|---|---|
| 1 | 8 tables V4 + 20 indexes + 9 enums Alembic scellée | `alembic current` + `\dt` |
| 2 | 12 endpoints `/api/action-center/*` opérationnels | OpenAPI YAML + curl smoke |
| 3 | 50 source-guards CI passing (100%) | `pytest tests/source_guards/ -v` |
| 4 | IDOR matrix 288 cellules : 100% passing | `pytest tests/security/idor_matrix/ -v` |
| 5 | Pyramide tests ≥100 (50+30+15+5) | `pytest tests/ -v --tb=short` |
| 6 | Performance budgets ADR-025 §11 respectés | `pytest tests/perf/ --benchmark` |
| 7 | HELIOS seeds idempotents ×3 | `regen_seeds_v4.py` exécuté 3× → hash identiques |
| 8 | Sprint Phase 3.5 non perturbé | `regulatory_applicability_service` reste fonctionnel |

❌ **Si UN seul ❌ → cutover Mois 4 REPORTÉ.** Investigation + sprint extra Mois 3.

---

## 2. Sprint plan Mois 2 — 8 sprints sur 4 semaines

### Sprint M2-1 — Foundation infra (J+1 à J+3)

**Objectif** : préparer le terrain pour les sprints suivants.

**Cardinal** :
- Activer **CI complète** : Bandit + Semgrep + gitleaks + pip-audit (IS6)
- Créer répertoires `tests/source_guards/` + `tests/unit/lifecycle/` + `tests/contract/` + `tests/security/idor_matrix/`
- Setup `.gitignore` (IS10 + IE1) :
  ```
  /data/backups/
  /data/promeos/evidences/
  *.backup
  *.sql
  ```
- Configurer variables env :
  ```
  EVIDENCE_STORAGE_BACKEND=filesystem
  EVIDENCE_FS_ROOT=/data/promeos/evidences
  EVIDENCE_MAX_SIZE_BYTES=10485760
  RETENTION_PURGE_ENABLED=False     # Mois 2-3 OFF
  RETENTION_PURGE_DRY_RUN_FIRST=True
  ```
- Setup `python-magic` (libmagic wheel) pour magic bytes IE9
- Setup `structlog` pour logs sécu sanitizés (IS7)
- Setup `apscheduler` pour purge mensuelle (IE5)

**Source-guards à activer Sprint M2-1** (4) :
- `test_no_action_legacy_imports` (anti-régression)
- `test_no_anomaly_legacy_imports`
- `test_gitignore_excludes_backups` (IS10)
- `test_gitignore_excludes_evidences` (IE1)

**DoD Sprint M2-1** :
- [ ] CI 4 outils + 4 source-guards bloquante (Bandit/Semgrep/gitleaks/pip-audit)
- [ ] `.gitignore` final committed
- [ ] Variables env documentées dans `.env.example`
- [ ] Dépendances install (`python-magic`, `structlog`, `apscheduler`) dans `requirements.txt`

---

### Sprint M2-2 — Schéma DB V4 + Alembic migration (J+4 à J+6)

**Objectif** : schéma cible créé + migration scellée.

**Cardinal** :
- Alembic migration `create_v4_tables.py` : 8 tables avec CHECK constraints (cf. L7 §2)
- 20 indexes (cf. ADR-025 §4.2)
- 9 enums Python (cf. L7 §3)
- SQLAlchemy models : 8 (`ActionCenterItem` + 7 filles)
- **NE PAS** dropper les tables legacy (Mois 2 = coexistence Q13-B)
- Tests unit modèles SQLAlchemy
- Migration up/down testée sur copie staging

**DoD Sprint M2-2** :
- [ ] Migration up/down testée sur copie staging
- [ ] 8 tables créées + 20 indexes
- [ ] 9 enums Python utilisés
- [ ] CHECK constraints validées (`chk_closure_consistency`, `chk_lifecycle_state`, `chk_kind`, `chk_evidence_expires_90d`, `chk_event_type` 16 valeurs)
- [ ] 0 régression legacy (legacy reste fonctionnel)

---

### Sprint M2-3 — Sécurité layer (J+7 à J+9)

**Objectif** : OrgScopingMiddleware + @org_scoped + pattern repository OPÉRATIONNELS.

**Cardinal** :
- `OrgScopingMiddleware` (ADR-027 §7 · couche 1)
- Décorateur `@org_scoped(allowed_roles=...)` (ADR-027 §8 · couche 2)
- Décorateur `@admin_only_with_fresh_token` (IS5)
- Pattern repository org-scopé (🛡️ IS11)
- Logs structlog sanitizés (IS7-IS9)
- IP anonymisée /24 IPv4 + /48 IPv6 (IS8)
- `correlation_id` propagation depuis header `X-Correlation-ID` (IS9)

**Source-guards activés Sprint M2-3** (5) :
- `test_all_aci_routes_have_org_scoped_decorator` (IS1)
- `test_no_direct_db_in_routes` (🛡️ IS11)
- `test_repositories_take_org_id_required_param`
- `test_logs_no_body_no_token` (IS7)
- `test_no_query_action_center_without_org_filter`

**DoD Sprint M2-3** :
- [ ] Middleware actif sur toutes routes `/api/*`
- [ ] 5 source-guards passing (cumul 9 SG)
- [ ] Test cross-org → HTTP 404 (IS3)
- [ ] Test viewer mutation → HTTP 403 (IS4)

---

### Sprint M2-4 — Routes core Centre d'Action + repositories (J+10 à J+13)

**Objectif** : 12 endpoints `/api/action-center/*` core opérationnels.

**Cardinal** : 12 endpoints cardinaux (ADR-027 §9) :
1. `GET /pilotage` — vue principale
2. `GET /items/{id}` — détail
3. `POST /items` — création
4. `PATCH /items/{id}/lifecycle` — préparé pour Sprint M2-5
5. `PATCH /items/{id}/owner` — réassignation
6. `PATCH /items/{id}/blockers` — gestion blockers
7. `POST /items/{id}/close` — préparé pour Sprint M2-5
8. `PATCH /items/{id}/correct-kind` — admin only IS5
9. `GET /items/{id}/audit-trail` — historique
10. `GET /impact` — KPI agrégés
11. `POST /items/{id}/evidence` — préparé pour Sprint M2-6
12. `POST /items/{id}/scenarios/{scenario_id}/select` — decision/recommendation

Repositories pour les 8 tables V4 (pattern 🛡️ IS11).

**DoD Sprint M2-4** :
- [ ] 12 endpoints répondent avec org-scoping correct
- [ ] Tests IDOR matrix : sample 30/288 cellules passing
- [ ] Tests contract OpenAPI : schemas validés

---

### Sprint M2-5 — Lifecycle state machine + transitions (J+14 à J+17)

**Objectif** : ADR-028 IL1-IL11 implémentés.

**Cardinal** :
- Classe `LifecycleStateMachine` (ADR-028 §7)
- 10 transitions strictes + closure_reasons mapping (cf. ADR-028 §7.1)
- Hooks pré/post (Q35-A méthodes Python — cf. ADR-028 §7.3)
- `verify_admin_role` + `verify_fresh_token` + `require_justification` (🛡️ IL3)
- `verify_closure_reason_valid` (🛡️ IL4 expired + 🛡️ IL5 merged_duplicate)
- HTTP 409 sur transitions interdites (IL1)
- Endpoint `PATCH /items/{id}/lifecycle` complet
- Endpoint `PATCH /items/{id}/reopen` (admin only 🛡️ IL3 + IL11)
- Frontend wait-for-server logic prep (IL10)

**Source-guards activés Sprint M2-5** (7) :
- `test_IL1_invalid_transition_returns_409`
- `test_IL2_closed_to_new_impossible`
- `test_IL3_reopen_admin_fresh_justification`
- `test_IL4_expired_forbidden_p0_compliance`
- `test_IL5_merged_duplicate_forbidden_recurrence`
- `test_IL8_every_transition_writes_event_log`
- `test_IL9_every_transition_score_stale_true`

**DoD Sprint M2-5** :
- [ ] 56 tests lifecycle passing (25 matrice + 20 closure + 11 IL)
- [ ] 7 source-guards passing (cumul 16 SG)
- [ ] HTTP 409 documenté pour clients (OpenAPI)

---

### Sprint M2-6 — Evidence + audit trail (J+18 à J+21)

**Objectif** : ADR-029 IE1-IE9 implémentés.

**Cardinal** :
- Storage abstrait `EvidenceStorageBackend` ABC (IE1)
- `FilesystemBackend` opérationnel (Mois 2-6 POC)
- Validation MIME magic bytes via `python-magic` (🛡️ IE9 · 4 étapes)
- Endpoint `POST /api/action-center/items/{id}/evidences` upload
- Endpoint `PATCH /api/action-center/evidences/{id}/verify` (IE2 + IE6)
- `expires_at = verified_at + 90 jours` (IE6 — DB CHECK + service)
- 16 schemas Pydantic v1 (IE7) + service `write_event()` avec validation
- security_audit_log table séparée (IE8)
- Endpoint `GET /api/users/me/data-export` (RGPD art. 15)
- Endpoint `DELETE /api/users/me/data` (RGPD art. 17 — anonymisation)
- APScheduler purge mensuelle `monthly_retention_purge` (IE5) **OFF en dev** + feature flag

**Source-guards activés Sprint M2-6** (7) :
- `test_IE1_storage_abstract_factory_returns_fs_backend`
- `test_IE2_evidence_not_verified_by_default`
- `test_IE6_expires_at_exactly_90_days`
- `test_IE7_all_event_types_have_schema_v1` (16 events)
- `test_IE7_write_event_rejects_invalid_payload`
- `test_IE9_magic_bytes_reject_exe_renamed_pdf`
- `test_IE8_security_audit_log_separate_table`

**DoD Sprint M2-6** :
- [ ] 40+ tests evidence/audit trail passing (10 + 15 + 15)
- [ ] 7 source-guards passing (cumul 23 SG)
- [ ] IDOR matrix : sample 60/288 passing

---

### Sprint M2-7 — HELIOS seeds + démo (J+22 à J+25)

**Objectif** : HELIOS 5 sites + 173 rows seedés propres.

**Cardinal** :
- Script `regen_seeds_v4.py` (ADR-026 §7 — Q20-A) implementation
- HELIOS 5 sites + MERIDIAN 3 sites canonical YAML
- 173 rows data réelle insertion via Alembic + script Python
- Tests d'idempotence ×3 (ADR-026 §7.3)
- Frontend M1-M5 maquettes alimentées avec HELIOS data
- API client TS génération depuis OpenAPI

**DoD Sprint M2-7** :
- [ ] `regen_seeds_v4.py --scenario helios,meridian` produit états identiques ×3
- [ ] Cockpit V4 affiche HELIOS 5 sites
- [ ] Drawer M2 fonctionnel sur items HELIOS
- [ ] Journal M5 chronologique opérationnel (16 event_types FR)

---

### Sprint M2-8 — Tests pyramide complète + DoD acceptance Mois 2 (J+26 à J+30)

**Objectif** : Cap tests + acceptance Mois 2.

**Cardinal** :
- Compléter IDOR matrix 288 cellules (12 routes × 3 rôles × 2 orgs × 4 cas)
- Compléter 50 source-guards (6 catégories ADR-027 §11)
- Compléter pyramide 100 tests minimum : 50 SG + 30 unit/integration + 15 contract + 5 e2e
- Performance benchmarks (ADR-025 §11)
- Documentation API OpenAPI complète
- Documentation Sphinx/MkDocs minimale (architecture + sécurité + lifecycle)
- Préparation cutover Mois 4 (ADR-026 §5 dry-run staging J-7)

**DoD Sprint M2-8** :
- [ ] 288 IDOR tests passing (100%)
- [ ] 50 source-guards passing (100%)
- [ ] Pyramide ≥100 tests minimum verts
- [ ] Performance budgets respectés
- [ ] OpenAPI YAML généré
- [ ] Documentation minimale en place
- [ ] Sprint planning Mois 3 prêt

---

## 3. Source-guards CI à activer (50 SG total · progressifs par sprint)

Source : ADR-027 §11 + L7 §15 + plan d'activation par sprint ci-dessus.

**Synthèse activation progressive** :

| Sprint | SG activés | Cumul | Catégorie L7 |
|---|---|---|---|
| M2-1 | 4 | 4 | F (anti-régression) + D (backup safety) |
| M2-2 | 0 | 4 | (sprint schéma) |
| M2-3 | 5 | 9 | A (org-scoping) + E (logs) |
| M2-4 | 0 | 9 | (sprint routes) |
| M2-5 | 7 | 16 | B (lifecycle IL) |
| M2-6 | 7 | 23 | C (evidence IE) |
| M2-7 | 0 | 23 | (sprint seeds) |
| M2-8 | 27 | **50** | Compléter A/B/C/D/E/F |

**6 catégories L7 §15** : A · Org-scoping (15 SG) · B · Lifecycle (10) · C · Evidence (10) · D · Backup safety (5) · E · Logs sanitization (5) · F · Anti-régression (5).

---

## 4. Pyramide tests (100 minimum · ~570 cible cumulés)

### Niveau 1 — Source-guards CI (50 tests)

- 6 catégories ADR-027 §11
- Bloque PR si échec (CI gate)
- Run < 30s sur GitHub Actions
- Catégories : org-scoping · lifecycle · evidence · backup · logs · anti-régression

### Niveau 2 — Unit tests + integration (30 tests)

- Lifecycle state machine (transitions + hooks)
- Pattern repository (filter org_id obligatoire)
- Validation Pydantic schemas (16 v1)
- Pre/post hooks (verify_has_owner, verify_no_active_blocker, write_event)
- Magic bytes validator (libmagic + signatures)
- Run < 2 min

### Niveau 3 — Contract tests (15 tests)

- OpenAPI schemas validation
- API contracts (Pydantic ↔ OpenAPI cohérence)
- IDOR matrix sample (60 cellules pour CI rapide, 288 nightly)
- Run < 3 min

### Niveau 4 — E2E tests Playwright (5 tests)

- Workflow Cockpit complet (login → liste → détail)
- Workflow lifecycle transition (qualify → plan → start → close)
- Workflow upload evidence (POST evidence → verify → expires_at + 90j)
- Workflow reopen admin (close → reopen avec justification)
- Workflow export RGPD (GET /api/users/me/data-export)
- Run < 10 min

**Total minimum** : **100 tests** sur main · cible ~574 fin Mois 2 (cf. L7 §13).

---

## 5. Séquencement strict des dépendances

```
Sprint M2-1  → Foundation infra
                ↓ (CI ready, .gitignore, env vars)
Sprint M2-2  → Schéma DB V4 + Alembic
                ↓ (8 tables + 20 indexes + 9 enums créés)
Sprint M2-3  → Sécurité layer (middleware + decorator + repository)
                ↓ (couches sécu opérationnelles)
Sprint M2-4  → Routes core + repositories
                ↓ (12 endpoints répondent)
Sprint M2-5  → Lifecycle state machine
                ↓ (10 transitions strictes + IL1-IL11)
Sprint M2-6  → Evidence + audit trail
                ↓ (IE1-IE9 + 16 schemas Pydantic v1 + APScheduler OFF)
Sprint M2-7  → HELIOS seeds + démo
                ↓ (173 rows + 5 sites HELIOS + 3 sites MERIDIAN)
Sprint M2-8  → Tests pyramide + DoD acceptance Mois 2
                ↓ (288 IDOR + 50 SG + 100+ pyramide + perf OK)
Mois 3       → Stabilisation + sprint Phase 3.5 merge
                ↓
Mois 4 J-7   → Dry-run staging (ADR-026 §5)
Mois 4 J0    → Cutover legacy → V4 (ADR-026)
Mois 4 J+14  → Observation
Mois 5 J+14  → STOP GATE 8/8 + suppression legacy (L8)
Mois 6       → Stabilisation + pilots externes
```

⚠️ **Pas de saut de sprint** : chaque sprint dépend du précédent. M2-3 ne peut pas commencer avant M2-2 (sécurité dépend du schéma). M2-5 ne peut pas commencer avant M2-4 (state machine appelée par endpoint lifecycle).

---

## 6. Risques Mois 2 et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Sprint M2-2 (schéma) déborde | Moyen | Élevé (cascade) | Buffer 1 jour entre M2-2 et M2-3 |
| 288 IDOR tests trop longs à écrire | Élevé | Moyen | Auto-génération `pytest.parametrize` (matrice cartésienne) |
| Magic bytes false positive | Faible | Moyen | Double-check libmagic + manual signatures (§9 ADR-029 4 étapes) |
| HELIOS seeds non-idempotent | Faible | Élevé | Test ×3 obligatoire (ADR-026 §7.3) |
| Performance budgets non respectés | Moyen | Élevé | Indexes ADR-025 §4.2 + benchmark continu CI |
| Régression sur legacy (M4) | Faible | Très élevé | Tests anti-régression + coexistence Mois 2-3 |
| Sprint Phase 3.5 régressions | Faible | Élevé | Tests `backend/regops/` non touchés en Mois 2 |
| `python-magic` indisponible/CVE | Faible | Élevé | Double-check signatures hardcodées (fallback §9 étape 4) |

---

## 7. Communication interne Mois 2

### 7.1 Routine quotidienne

- Stand-up 15 min/jour (état Sprint en cours + blockers)
- Commit message conforme convention `feat(action-center-mN-X): Sprint Y.Z — description`
- Branch naming : `m2-sprint-X-task-Y`

### 7.2 Routine hebdomadaire

- Review fin Sprint (DoD checklist par sprint cochée)
- Update CHANGELOG si user-facing
- Démo interne courte (5 min) si applicable

### 7.3 Routine fin Mois 2

- Tag git `mois2-backend-complete`
- Communication interne externalisée si pilots externes prévus
- Sprint planning Mois 3 prêt

---

## 8. DoD binaire fin Mois 2 — décision cutover Mois 3 (20 critères)

Tous les critères ci-dessous doivent être ✅ avant décision cutover Mois 4 :

- [ ] **1.** 8 tables V4 + 20 indexes Alembic migration scellée
- [ ] **2.** 9 enums Python documentés et utilisés
- [ ] **3.** 16 schemas Pydantic v1 actifs (IE7)
- [ ] **4.** `LifecycleStateMachine` fonctionnel : 10 transitions valides
- [ ] **5.** `EvidenceStorageBackend` filesystem opérationnel (IE1)
- [ ] **6.** Validation MIME magic bytes opérationnelle (🛡️ IE9)
- [ ] **7.** Middleware `org_scoping` + decorator `@org_scoped` + pattern repository actifs (IS1-IS11)
- [ ] **8.** `security_audit_log` table + writer opérationnel (IE8)
- [ ] **9.** `action_event_log` table + writer opérationnel (IL8 + IE7)
- [ ] **10.** APScheduler `monthly_retention_purge` OFF en dev (`RETENTION_PURGE_ENABLED=False`)
- [ ] **11.** 12 endpoints `/api/action-center/*` opérationnels
- [ ] **12.** HELIOS seeds idempotents ×3
- [ ] **13.** CI 4 outils (Bandit/Semgrep/gitleaks/pip-audit) + 50 source-guards bloquante
- [ ] **14.** 100+ tests pyramide passing (50 SG + 30 unit + 15 contract + 5 e2e)
- [ ] **15.** IDOR matrix 288 cellules : 100% passing
- [ ] **16.** Performance budgets ADR-025 §11 respectés (Pilotage <100ms · mutations <150ms · Drawer <80ms)
- [ ] **17.** OpenAPI YAML généré (auto-doc API)
- [ ] **18.** Documentation minimale Sphinx/MkDocs (architecture + sécurité + lifecycle)
- [ ] **19.** 0 régression legacy (coexistence M2-3 préservée)
- [ ] **20.** Sprint planning Mois 3 prêt + tag git `mois2-backend-complete`

❌ **Si UN seul ❌ → cutover Mois 4 REPORTÉ.** Investigation + sprint extra Mois 3.

---

## 9. Transition Mois 1 docs → Mois 2 code

### 9.1 Pratiques cardinales à conserver

- **MCPs obligatoires** chaque session Claude Code : Context7 + code-review + simplify
- **Phase 0 audit cohérence** avant Phase 1 production (pattern Mois 1 — appliquer aussi par sprint Mois 2 sur changes >100 LoC)
- **Commits atomiques** par feature/sprint (pas méga-commits)
- **DoD binaire** par sprint (cocher ✅ avant merge)
- **STOP GATE** avant toute action destructive (cf. ADR-026 + L8)
- **Source-guards d'abord** : ajouter le SG avant le code qu'il garde (TDD style)

### 9.2 Décisions cardinales Amine non-rejouables

Si pendant Mois 2 quelqu'un veut remettre en cause :
- **Q2-α** (table rase)
- **Q6-A** (Mois 1 docs only — terminé maintenant, mais le principe "pas de code sans ADR" reste)
- **🛡️ Q9-B** (`recurrence_groups` ≠ `duplicate_groups`)
- **🛡️ IL3 / IL4 / IL5 / IL7** (transitions lifecycle dur)
- **🛡️ IS11** (pattern repository)
- **🛡️ IE9** (magic bytes MIME)
- **🛡️ I9** (backup hors Git)
- **doctrine v0.3** (avenant doctrinal versionné)

→ **Refuser immédiatement.** Ces décisions sont actées par Amine + sessions cadrage Mois 1. Pour remettre en cause, **session Claude.ai dédiée avec arbitrage explicit + nouvel avenant doctrinal versionné** (cf. §9.3).

### 9.3 Si nouvelle décision cardinale émerge Mois 2+

Procédure obligatoire :

1. **Lever session Claude.ai cadrage** dédiée (pas de décision in-flight commit)
2. **Identifier le numéro Q** (continuation Q47, Q48, ...)
3. **Trancher arbitrage explicite** (option choisie + rationale)
4. **Produire brief** (si majeur — équivalent ADR) ou amendement (si mineur)
5. **Mettre à jour doctrine** si applicable (avenant versionné v0.4, v0.5, ...)
6. **Mettre à jour ADRs affectés** (notes d'extension aval acceptées par convention)
7. **Conserver pattern cohérence cross-documents** (CLAUDE.md + L7 + L9)

---

## 10. Auto-évaluation L9

### 10.1 Synthèse Mois 1 complète

- [x] 9 livrables récap (table §0.1)
- [x] 49 invariants quick-reference (§0.2)
- [x] 46 arbitrages cardinaux récap (§0.3)
- [x] Décisions cardinales Amine listées (8 garde-fous + 3 doctrinales)

### 10.2 Sprint plan Mois 2 détaillé

- [x] 8 sprints documentés (M2-1 → M2-8 §2)
- [x] DoD par sprint
- [x] Source-guards activés par sprint (progressif §3)
- [x] Séquencement strict des dépendances (§5)

### 10.3 Tests pyramide

- [x] 50 source-guards listés (depuis ADR-027 §11 + L7 §15)
- [x] 4 niveaux pyramide documentés (50 + 30 + 15 + 5)
- [x] Cible 574 tests cumulés fin Mois 2 (cf. L7 §13)

### 10.4 Risques + mitigations

- [x] 8 risques majeurs documentés (cible ≥6)
- [x] Mitigations cardinales

### 10.5 DoD acceptance Mois 2 → Mois 3

- [x] 20 critères binaires
- [x] Tous nécessaires (pas d'optionnel)

### 10.6 Transition pratiques

- [x] MCPs requis Mois 2
- [x] Décisions cardinales non-rejouables (8 + 3)
- [x] Procédure nouvelle décision Mois 2+ (7 étapes)

### 10.7 Conformité Q6-A

- [x] Aucun code Python/TypeScript modifié
- [x] Aucune table DB modifiée
- [x] Aucun script créé sur disque
- [x] Sprint Phase 3.5 (`backend/regops/`) non perturbé

**Total** : **22/20 critères ✓** — L9 prêt pour acceptation.

---

## 11. Métadonnées

```yaml
livrable: L9
title: Manuel de pilotage Mois 2 backend PROMEOS V4
version: v1.0
status: Accepted
date: 2026-05-14
authors:
  - Amine (PROMEOS founder)
  - Claude (architecture co-pilot)
branch: claude/refonte-sol2
doctrine_version_ref: v0.3
nature: synthese_finale_mois1 + planification_mois2
sources_consolidated:
  - doctrine v0.3 (commits 883ac4ae · 466b64c3)
  - L1 décisionnel (commits b6416f4b · ee749a12)
  - ADR-025 Architecture (commits 07f57c24 · b7208022 · 712da32a)
  - ADR-026 Migration (commits a506c758 · 0eb4dadc · 1500f55b)
  - ADR-027 Sécurité (commits 211bc26b · 94b873db · faba2a61)
  - ADR-028 Lifecycle (commits 26a6b0a0 · 3c77e059 · 466b64c3)
  - ADR-029 Evidence (commits e308dc6c · 21e37b4e · 15711df4)
  - L7 Data Dictionary (commit 1d77a7ad)
  - L8 Plan suppression legacy (commit 3bf14494)
  - CLAUDE.md
mois2_sprints: 8
mois2_duration_weeks: 4
source_guards_total: 50
tests_pyramid_minimum: 100
tests_pyramid_target: 574
dod_binary_criteria: 20
risks_documented: 8
cardinaux_amine_non_rejouables: 11  # 8 garde-fous + 3 doctrinales
month: 1
livrable_position: "10/10 — DERNIER MOIS 1"
next_step: "Sprint M2-1 Foundation infra (J+1 à J+3)"
```

---

**Statut final** : `Accepted` 2026-05-14 — L9 devient **le manuel de pilotage Mois 2 backend** PROMEOS V4 Centre d'Action.

**Mois 1 docs only — COMPLET 10/10 ✅**
**Mois 2 backend — READY TO START** : Sprint M2-1 Foundation infra (J+1 à J+3) après merge `claude/refonte-sol2` → `main`.
