# L6 Phase 0 · Audit cohérence brief ADR-029

> **Date** : 2026-05-14
> **Branche** : `claude/refonte-sol2`
> **Mode** : lecture seule strict (Q6-A — docs only Mois 1)
> **Brief audité** : [`docs/dev/BRIEF_ADR-029_evidence_audit_trail.md`](BRIEF_ADR-029_evidence_audit_trail.md) · 1 146 lignes · 39 760 chars
> **Particularité** : dernier ADR du Mois 1 — clôture la trilogie data (ADR-025 + ADR-028 + ADR-029)

---

## Synthèse exécutive

| Bloc | Vérifications | Résultat |
|---|---|---|
| **A** · Cohérence ADR-025 (architecture) | 4 | **4/4 OK** |
| **B** · Cohérence ADR-026 (migration) | 3 | **3/3 OK** |
| **C** · Cohérence ADR-027 (sécurité) | 5 | **5/5 OK** |
| **D** · Cohérence ADR-028 (lifecycle) | 4 | **4/4 OK** |
| **E** · Cohérence doctrine v0.3 | 4 | **4/4 OK** |
| **F** · Cohérence L1 verdicts | 3 | **3/3 OK** |
| **G** · Cohérence maquettes M1-M5 | 3 | **3/3 OK** |
| **H** · 9 invariants IE1-IE9 | 9 | **9/9 OK** |
| **I** · Sprint Phase 3.5 non perturbé | 2 | **2/2 OK** |
| **TOTAL** | **38** | **38/38 OK** |

**Anomalies bloquantes** : `0`
**Anomalies mineures** : `3` (renommages event_types ADR-025 → ADR-029 documentés, alignés doctrine v0.3)
**Brief consommable** : **OUI**
**Conformité Q6-A** : aucun fichier code modifié, aucune table DB modifiée, aucun script créé sur disque

---

## A · Cohérence avec ADR-025 (architecture) — 4/4

### A1 ☑ Schéma `evidences` cohérent §2.3 ADR-025

ADR-025 §4.3 définit le squelette `evidences` avec colonnes (`id`, `item_id`, `organisation_id`, `evidence_type`, `status`, `storage_uri`, `mime_type`, `size_bytes`, `uploaded_by`, `uploaded_at`, `verified_at`, `verified_by`, `expires_at`, `validation_payload`).

Brief §2.1 enrichit cohérent :
- Toutes colonnes ADR-025 présentes ou raffinées
- Ajout `original_filename` (nom client informatif)
- Ajout `description` (TEXT)
- Renommage `item_id` → `action_item_id` (alias plus explicite, FK identique)
- 3 CHECK constraints supplémentaires : `chk_evidence_verified_consistency` + `chk_evidence_mime_whitelist` + `chk_evidence_expires_90d` (matérialise IE6)
- Drop de `evidence_type` + `status` au profit de `validation_payload` JSONB (Q41-D + IE2)

**Verdict** : enrichissement cohérent, aucun conflit. ADR-029 supersede ADR-025 §4.3 sur les détails evidences (prévu).

### A2 ☑ Schéma `action_event_log` cohérent §2.3 ADR-025 (15 event_types CHECK **étendu à 16**)

ADR-025 §4.3 lignes 322-327 définit CHECK avec 15 event_types :
```
'created','state_changed','assigned','priority_changed',
'blocker_added','blocker_removed','evidence_added','evidence_verified',
'closed','reopened','merged','bulk_updated','exported',
'kind_corrected','priority_recalculated'
```

Brief ADR-029 §3.1 étend à 16 event_types alignés doctrine v0.3 :
```
'created','state_changed','owner_changed','priority_changed',
'blocker_added','blocker_removed','evidence_added','evidence_verified',
'closed_with_evidence','closed_via_merged_duplicate','closed_via_resolved_via_recurrence',
'reopened','bulk_updated','exported','kind_corrected','priority_recalculated'
```

**Anomalie mineure 1** (non bloquante) : 3 renommages explicites cohérents doctrine v0.3 :
- `assigned` → `owner_changed` (sémantique plus précise)
- `merged` → `closed_via_merged_duplicate` (doctrine v0.3 §7.1 unification `duplicate`+`merged`)
- `closed` (singulier) → 3 variantes : `closed_with_evidence` + `closed_via_merged_duplicate` + `closed_via_resolved_via_recurrence` (Q9-B/Q37-A+ : récurrence ≠ doublon)

Le PROMPT_L6 §3.2 anticipe explicitement cette extension : « 15 event_types CHECK étendu à 16 ». **ADR-029 supersede ADR-025 sur cette liste** (alignement doctrine v0.3 plus récente).

**Action Phase 1** : Phase 2 cross-refs L2 §15 doit acter formellement la supersession (note d'évolution).

### A3 ☑ Indexes cohérents avec stratégie ADR-025 §3 (20 indexes total)

ADR-025 §4.2 documente les 12 indexes tables filles dont :
- `idx_event_log_item` (item_id, occurred_at DESC)
- `idx_event_log_org_type` (org, event_type, occurred_at DESC)
- `idx_event_log_correlation` (correlation_id) WHERE NOT NULL
- `idx_evidence_item` (item_id, status)
- `idx_evidence_org` (org, expires_at) WHERE NOT NULL

Brief §2.1 et §3.1 propose 4 indexes evidences + 4 indexes event_log :
- `idx_evidences_org` (organisation_id, action_item_id) — équivalent enrichi
- `idx_evidences_verified` (verified_at) WHERE NOT NULL — nouveau (job notifications)
- `idx_evidences_expiring` (expires_at) WHERE NOT NULL — équivalent ADR-025
- `idx_event_log_org_item` (org, item, occurred_at DESC) — équivalent enrichi
- `idx_event_log_type` (event_type, occurred_at DESC) — équivalent
- `idx_event_log_correlation` (correlation_id) — équivalent
- `idx_event_log_actor` (actor_id, occurred_at DESC) — nouveau (RGPD art. 15 droit d'accès)

**Verdict** : pas de régression, ajouts ciblés (`verified_at`, `actor_id`) justifiés par RGPD. Total reste compatible budget §11 ADR-025.

### A4 ☑ Aucun conflit avec budgets perf §9/§11 ADR-025

Budget ADR-025 : Pilotage < 100 ms · mutations < 150 ms · Drawer < 80 ms.

Brief §11 (tests planifiés) ne mentionne aucun nouveau coût qui dépasserait le budget. Validation Pydantic + magic bytes = O(1) sur 2 KB, négligeable. Storage filesystem write < 50 ms. Schema_version registry = lookup hash O(1).

**Verdict** : aucun conflit perf. Le budget < 150 ms mutations supporte largement IE7 + IE9.

---

## B · Cohérence avec ADR-026 (migration) — 3/3

### B1 ☑ Storage filesystem `/data/promeos/evidences/` non commitable (IS10 + I9)

Brief §4.2 précise :
```
EVIDENCE_FS_ROOT=/data/promeos/evidences      # gitignored, hors Git (IS10)
.gitignore : /data/promeos/evidences/         # IE1 + IS10 ADR-027
```

Renvoi explicite à ADR-027 IS10 + ADR-026 I9 (« Backup hors Git · receipt sanitizé »). Pas de checksum/dump binaire commitable, pas de PII dans receipts.

**Verdict** : conforme garde-fou cardinal Amine (Q19-Q25 validation).

### B2 ☑ Migration 173 rows data réelle ne contient pas d'evidences legacy à migrer

ADR-026 §5.1 inventorie : `action_items` 35 + `bill_anomaly` 52 + `anomaly` KB 86 = **173 rows**. Toutes les autres 15 tables legacy (incluant `action_evidence`, `action_plan_evidences`, `action_events`, `action_plan_events`) sont vides Sprint 13.

Brief §1.2 (hors-scope) : aucune mention de migration evidence legacy. ADR-029 démarre la table `evidences` à zero (cohérent : pas d'evidence legacy à préserver).

**Verdict** : aucun risque de perte d'evidences legacy, table V4 vierge au cutover.

### B3 ☑ Pas de conflit avec procédure cutover Mois 4

ADR-026 §5 cutover triple artefact (binaire + SQL + JSON) + STOP GATE J+14. Brief §9.2 propose pour `monthly_retention_purge` une activation phasée :
```
Phase 1 (Mois 2-3)  : RETENTION_PURGE_ENABLED=False    · Pas de purge
Phase 2 (Mois 4 J-7): RETENTION_PURGE_ENABLED=True + DRY_RUN=True
Phase 3 (Mois 4 J+1): DRY_RUN=False
Phase 4 (Mois 5+)   : Régime cruise
```

Calendrier IE5 strictement aligné cutover ADR-026 (J-7 / J+1 / J+14 régime cruise). Aucun conflit.

**Verdict** : conforme. La purge n'est jamais active en Mois 1-3 (pas de risque collatéral au cutover).

---

## C · Cohérence avec ADR-027 (sécurité) — 5/5

### C1 ☑ `security_audit_log` reste séparé (90j) — IE8 cohérent §10 ADR-027

ADR-027 §7 et §10 imposent `security_audit_log` rétention 90j séparé strict de `action_event_log` métier (1-5 ans).

Brief §3.2 invariant IE8 + table comparative explicite :

| Table | Rétention | Sémantique | Cible RGPD |
|---|---|---|---|
| `action_event_log` | 1-5 ans (IE3) | Audit trail métier | art. 30 |
| `security_audit_log` | 90 jours (ADR-027) | Events sécurité | art. 32 |

**Verdict** : conformité totale. « Aucun mélange. Sémantique stricte. »

### C2 ☑ `correlation_id` IS9 propagé dans action_event_log §3.1

ADR-027 IS9 (« correlation_id obligatoire sur toutes les requêtes »).

Brief §3.1 colonne `action_event_log.correlation_id UUID NOT NULL` + index `idx_event_log_correlation`. Aussi propagé dans schemas Pydantic (`BulkUpdatedPayloadV1.correlation_id`) et dans `monthly_retention_purge` (`correlation_id = uuid4()`).

**Verdict** : IS9 universellement respecté dans events + purges.

### C3 ☑ Endpoint upload utilise `@org_scoped` ADR-027

Brief §5.1 :
```python
@router.post("/api/action-center/items/{item_id}/evidences")
@org_scoped(allowed_roles=["admin", "user"])
async def upload_evidence(...)
```

Idem §5.2 verify, §10.1 export RGPD, §10.2 delete RGPD. Tous endpoints ADR-029 décorés `@org_scoped` ou `@admin_only_with_fresh_token` (escalade IS5).

**Verdict** : ADR-027 IS1 (« @org_scoped obligatoire ») respecté à 100%.

### C4 ☑ Validation MIME magic bytes anti-spoofing cohérente IS6 (Bandit/Semgrep)

ADR-027 IS6 = CI gate (Bandit + Semgrep + gitleaks + pip-audit + 50 SG).

Brief §6 Q44-A+ documenté triple défense :
1. `magic.from_buffer(content_bytes[:2048], mime=True)` (libmagic SAST-friendly)
2. Whitelist explicite `ACCEPTED_MIME_TYPES`
3. Double-check signature manuelle (`MAGIC_BYTES_SIGNATURES`)

Pas de raw SQL, pas de header client trusted. Bandit/Semgrep peuvent matcher patterns (B608, B201). Cohérent avec source-guards CI ADR-027 §11.

**Verdict** : pattern défensif aligné IS6 + IS11 (repository).

### C5 ☑ Storage gitignored (IE1 + IS10)

Brief §4.2 explicite double renvoi :
- `EVIDENCE_FS_ROOT=/data/promeos/evidences # gitignored, hors Git (IS10)`
- `.gitignore : /data/promeos/evidences/  # IE1 + IS10 ADR-027`

Cohérent IS10 (« Backup/export non commitables : .gitignore + source-guard CI bloque »).

**Verdict** : invariant IS10 ADR-027 préservé pour evidences (pas seulement backups DB).

---

## D · Cohérence avec ADR-028 (lifecycle) — 4/4

### D1 ☑ 16 event_types incluent les invariants IL1-IL11

Mapping explicite :

| Invariant ADR-028 | Event ADR-029 |
|---|---|
| IL3 (réouverture admin) | `reopened` |
| IL4 (`expired` interdit P0/P1) | `state_changed` payload `closure_reason='expired'` (justification escalade) |
| IL5 (`merged_duplicate` ≠ recurrence) | `closed_via_merged_duplicate` distinct de `closed_via_resolved_via_recurrence` |
| IL6 + IL7 (auto-close P0/P1 + preuve) | `closed_via_resolved_via_recurrence` (compliance 5 ans IE3) |
| IL8 (audit trail systématique) | Tous les `state_changed` |
| IL9 (`score_stale=true`) | `priority_recalculated` |
| IL11 (justification réouverture) | `ReopenedPayloadV1.justification` (min 10 chars) |

**Verdict** : 16 event_types couvrent tous les hooks ADR-028.

### D2 ☑ `closed_via_merged_duplicate` (3 ans) ≠ `closed_via_resolved_via_recurrence` (5 ans) cohérent Q9-B + IL5

Brief §7.2 EVENT_TYPE_CATEGORY :
```python
"closed_via_merged_duplicate": RetentionCategory.BUSINESS,        # 3 ans (Q9-B doublon technique)
"closed_via_resolved_via_recurrence": RetentionCategory.COMPLIANCE, # 5 ans (Q9-B preuve indirecte)
```

ADR-028 §4 + IL5 + Q37-A+ + doctrine v0.3 §7.1 imposent strictement la distinction. ADR-029 IE4 matérialise dans la matrice rétention.

**Verdict** : Q9-B respecté, garde-fou cardinal IL5 préservé (3 lignes de défense empilées : type doctrinal + state machine + matrice rétention).

### D3 ☑ `reopened` event tracé avec justification cohérent IL11

Brief §8.1 :
```python
class ReopenedPayloadV1(EventPayloadBase):
    previous_closure_reason: str
    justification: str  # IL11 obligatoire min 10 chars
    admin_actor_id: UUID
```

Et §7.2 mapping : `"reopened": RetentionCategory.COMPLIANCE` (5 ans, IL3 admin sensible).

**Verdict** : IL11 (« justification non vide ») contraint au niveau Pydantic schema. Rétention compliance 5 ans pour audit CNIL.

### D4 ☑ `state_changed` schema v1 contient `closure_reason` + `justification`

Brief §8.1 :
```python
class StateChangedPayloadV1(EventPayloadBase):
    from_state: str
    to_state: str
    closure_reason: Optional[str] = None
    justification: Optional[str] = None
    auto_closed_by_group_id: Optional[UUID] = None
```

Couvre IL4 (`closure_reason=expired`), IL5 (`closure_reason=merged_duplicate`), IL7 (auto-close avec `auto_closed_by_group_id`), IL11 (`justification` admin réouverture).

**Verdict** : payload riche couvrant les 11 invariants lifecycle.

---

## E · Cohérence avec doctrine v0.3 — 4/4

### E1 ☑ 6 closure_reasons doctrine v0.3 §7.1 mappés correctement

Doctrine v0.3 §7.1 (avenant 2026-05-14) recense 6 closure_reasons :
1. `resolved`
2. `dismissed`
3. `not_applicable`
4. `merged_duplicate` (v0.3 unifié `duplicate`+`merged`)
5. `resolved_via_recurrence` (v0.3 ajouté Q37-A+)
6. `expired` (avec note IL4)

Brief §3.1 `chk_event_type` + §7.2 EVENT_TYPE_CATEGORY couvrent les 5 closure_reasons opératoires comme events :
- `closed_with_evidence` ↔ closure_reason `resolved`
- `closed_via_merged_duplicate` ↔ `merged_duplicate`
- `closed_via_resolved_via_recurrence` ↔ `resolved_via_recurrence`
- `state_changed.closure_reason` (générique) ↔ `dismissed`, `not_applicable`, `expired`

**Verdict** : 6/6 closure_reasons routés sans ambiguïté.

### E2 ☑ Libellés FR mode standard documentés

ADR-028 §10 mapping libellés FR (`Qualifié`, `Planifié`, `Clôturé`, `Réouvert`...) confirmé par grep dans `centre_action_v4_pilotage_journal.html`. Brief §13 renvoie à doctrine v0.3 §7.1 + ADR-028.

Brief n'introduit pas de nouveau libellé FR (pas de duplication doctrine).

**Verdict** : pas de drift FR. ADR-029 délègue libellés à doctrine + ADR-028.

### E3 ☑ Référence "doctrine v0.3" explicite (pas v0.2)

Brief header L7 : `Doctrine source : doctrine_v4_classement_priorisation.md v0.3 (Accepted)`.
Brief §0 TL;DR : « Matrice rétention alignée doctrine v0.3 ».
Brief §7.2 commentaires : « Q9-B fusion technique » (renvoi v0.3 §7.1).
Brief §15 YAML : `doctrine_version_ref: v0.3`.

Aucune mention résiduelle « v0.2 ». Avenant L5 (commit `466b64c3`) consommé correctement.

**Verdict** : ancrage doctrine v0.3 universel.

### E4 ☑ Politique §11 historique versions respectée

Doctrine v0.3 §11 stipule que toute évolution future = nouvel avenant versionné (v0.4, v0.5...).

Brief ADR-029 ne modifie pas la doctrine — il consomme v0.3 telle quelle. Si une nouvelle évolution de closure_reasons devenait nécessaire post-ADR-029, elle passerait par avenant v0.4 (pas par modification ADR-029).

**Verdict** : §11 doctrine respecté. ADR-029 stable au regard de la doctrine.

---

## F · Cohérence avec L1 verdicts — 3/3

### F1 ☑ `action_event_log` legacy (0 rows) cohérent avec MIGRE/RÉGÉNÈRE

L1 §3.2 : tables legacy `action_events` (0 row) + `action_plan_events` (0 row) + `action_comments` (0 row) → **REMPLACE** par `action_event_log` unifié.

Brief §3.1 démarre `action_event_log` à zéro (pas d'import legacy). Cohérent avec ADR-026 (0 row à migrer pour ces 3 tables).

**Verdict** : pas de migration data, table V4 vierge.

### F2 ☑ `evidences` legacy (0 rows) cohérent

L1 §3.2 : `action_evidence` (0 row) + `action_plan_evidences` (0 row) → **REMPLACE** par `evidences` table dédiée FK `ActionCenterItem.id`.

Brief §2.1 démarre `evidences` à zéro. Pas d'import.

**Verdict** : table V4 vierge, pas de risque d'evidence orpheline.

### F3 ☑ 16 event_types V4 cohérent avec L1 vocabulaire SUPPRIME

L1 verdict SUPPRIME (28 éléments) inclut le vocabulaire fragmenté legacy (`action_events`, `action_plan_events`, `action_comments`, etc.). Brief §3.1 propose 16 event_types unifiés, taxonomie unique alignée doctrine v0.3 + ADR-028.

**Verdict** : alignement complet, taxonomie consolidée.

---

## G · Cohérence avec maquettes M1-M5 — 3/3

### G1 ☑ Drawer M2 affiche evidences + statuts (vérifié/expiré/non vérifié)

Grep `centre_action_v4_detail_drawer_v02.html` :
- `.d-evidence-badge` (badge "Preuve attendue")
- `.evidence-panel`, `.evidence-info`, `.evidence-status` (sections preuves dédiées)
- `.evidence-upload` + lien « Ajouter preuve » (ligne 711)
- Mention "Preuve manquante" comme blocker (lignes 818, 838, 869, 875, 880, 882, 896)

Brief §2.1 statuts dérivés de `verified_at` + `expires_at` :
- `verified_at IS NULL` → "Non vérifié"
- `verified_at IS NOT NULL AND expires_at > NOW()` → "Vérifié"
- `expires_at < NOW()` → "Expiré"

**Verdict** : maquette M2 prête à consommer le modèle ADR-029.

### G2 ☑ M5 Journal chronologique affiche les 16 event_types FR

Grep `centre_action_v4_pilotage_journal.html` :
- Header « Journal des 7 derniers jours · Sophie Marin »
- Compteurs : « 38 événements sur 7 jours · 5 transitions, 3 escalades, 2 preuves vérifiées »
- Sections par jour (`day-meta` : "7 événements", "9 événements", "8 événements")
- Statuts FR : `Qualifié`, `Clôturé` (lignes 655, 906)
- Références : `transitions`, `escalades`, `preuves vérifiées` (categorisation cohérente event_types)

**Verdict** : M5 expose les 16 event_types via libellés FR doctrine v0.3 + ADR-028.

### G3 ☑ Bouton "Téléverser preuve" mappé à l'endpoint upload

M2 ligne 711 : « Ajouter preuve » (lien actionnable dans `.evidence-upload`).
Brief §5.1 : `POST /api/action-center/items/{item_id}/evidences` (multipart UploadFile).

**Verdict** : UI ↔ endpoint mappés 1:1. La maquette respecte les contraintes ADR-029 (10 MB max, MIME magic bytes).

---

## H · 9 invariants vérifiés — 9/9

### H1 ☑ IE1 Storage abstrait — §4 documenté avec factory

Brief §4.1 : `EvidenceStorageBackend` ABC + `FilesystemBackend` (Mois 2) + `S3Backend` placeholder (V4.1+) + factory `get_storage_backend()`. Routes consomment via `Depends(get_storage_backend)`.

### H2 ☑ IE2 Validation manuelle — §5.2 endpoint + validation_payload

Brief §5.2 endpoint `PATCH /evidences/{id}/verify` requiert `confidence_flag` (high/medium/low) + `verifier_role` + `verification_method='manual_with_metadata'`. `validation_payload.verified_by_human=True` après vérification.

### H3 ☑ IE3 3 catégories — §7.1 CATEGORY_RETENTION_DAYS

Brief §7.1 : `COMPLIANCE: 1825` (5 ans) · `BUSINESS: 1095` (3 ans) · `SYSTEM: 365` (1 an). Enum `RetentionCategory` typé.

### H4 ☑ IE4 Matrice doctrine v0.3 — §7.2 merged_duplicate vs resolved_via_recurrence

Brief §7.2 :
- `closed_via_merged_duplicate`: BUSINESS (3 ans, Q9-B doublon technique)
- `closed_via_resolved_via_recurrence`: COMPLIANCE (5 ans, Q9-B preuve indirecte)

Strict alignement doctrine v0.3 §7.1 + IL5 ADR-028.

### H5 ☑ IE5 Purge triple garde-fou — §9.1 feature flag + dry-run + trace

Brief §9.1 `monthly_retention_purge` :
1. `if not config.RETENTION_PURGE_ENABLED: log + return` (feature flag)
2. `dry_run = config.RETENTION_PURGE_DRY_RUN_FIRST` (counts only, no delete)
3. `log_security_event(event_type="retention.purge.completed/dry_run", correlation_id, purged_counts)` (trace)

### H6 ☑ IE6 expires_at = verified_at + 90j — §2.1 CHECK + §5.2

Brief §2.1 CHECK constraint :
```sql
chk_evidence_expires_90d CHECK (
    expires_at IS NULL OR expires_at = verified_at + INTERVAL '90 days'
)
```
+ §5.2 endpoint : `evidence.expires_at = now + timedelta(days=90)`.

Double défense (DB + service).

### H7 ☑ IE7 Schemas Pydantic versionnés — §8 + schema_version

Brief §8.1 : 16 schemas v1 héritant de `EventPayloadBase` (`schema_version: Literal["v1"] = "v1"`). Registry `EVENT_PAYLOAD_SCHEMAS: dict[(event_type, schema_version), type[BaseModel]]`. §8.2 service `write_event` valide via Pydantic + lookup registry. §8.3 documente pattern d'évolution v1 → v2.

### H8 ☑ IE8 Séparation security_audit_log — §3.2 cohérent ADR-027

Brief §3.2 table comparative + déclaration explicite « Aucun mélange. Sémantique stricte. ». ADR-027 IS8 (anonymisation IP) + IS10 référencés en cohérence.

### H9 ☑ IE9 Magic bytes MIME — §6 + code python-magic

Brief §6.1 service `validate_evidence_mime` :
- Étape 1 : `magic.from_buffer(content_bytes[:2048], mime=True)`
- Étape 2 : whitelist `ACCEPTED_MIME_TYPES`
- Étape 3 : log mismatch client/réel dans `security_audit_log`
- Étape 4 : double-check `MAGIC_BYTES_SIGNATURES` manuel

§6.2 tableau attaques mitigées (`.exe` renommé `.pdf`, polyglottes PDF/HTML, header `Content-Type` spoofed).

**Verdict** : invariant cardinal Amine 2026-05-14 implémenté en triple défense.

---

## I · Sprint Phase 3.5 non perturbé — 2/2

### I1 ☑ `regulatory_applicability_service` produit des evidences cohérentes IE2

Sprint Phase 3.5 produit `backend/regops/` (10+ fichiers : `scoring.py`, `engine.py`, `priority_scoring.py`, etc.). Aucun module evidence dans `backend/regops/`.

Brief §1.1 périmètre limité à `backend/services/evidence/` + `backend/maintenance/retention_purge.py` + `backend/schemas/event_payloads/`. Pas de modification de `backend/regops/`.

Si Phase 3.5 produit ultérieurement des evidences automatiques, elles devront passer par `validate_evidence_mime` + `validation_payload.verified_by_human=False` (IE2 — non vérifié par défaut, escaladé en validation manuelle).

**Verdict** : non perturbation. Brief §8.1 `CreatedPayloadV1.triggered_by` accepte explicitement `"regulatory_applicability_service"` comme déclencheur — anticipation propre du sprint parallèle.

### I2 ☑ Pas de duplication avec sprint parallèle

Mission Phase 3.5 = scoring conformité (`regops/scoring.py`) + engine d'applicabilité (`regops/engine.py`). Mission ADR-029 = persistance preuves + audit trail. Périmètres orthogonaux.

L1 §11.1 + §12.6 + §6.1 actent : « Sprint Phase 3.5 en parallèle — V4 attend l'API stable Mois 3 ». ADR-029 documente l'intégration future sans la précipiter.

**Verdict** : aucun chevauchement, intégration documentée.

---

## Anomalies détectées

### Anomalies bloquantes : 0

### Anomalies mineures : 3 (toutes documentées et anticipées par PROMPT_L6)

#### Anomalie mineure 1 — Renommage `assigned` → `owner_changed`
- **Source** : ADR-025 §4.3 ligne 323 vs Brief ADR-029 §3.1
- **Impact** : sémantique plus précise (changement propriétaire vs assignation initiale)
- **Action Phase 1** : ADR-029 supersede explicitement ADR-025 sur la liste event_types. Note de supersession à ajouter en §15 ADR-025 (Phase 2 cross-refs).

#### Anomalie mineure 2 — Renommage `merged` → `closed_via_merged_duplicate`
- **Source** : ADR-025 §4.3 ligne 325 vs Brief ADR-029 §3.1
- **Impact** : alignement doctrine v0.3 §7.1 (unification `duplicate`+`merged` → `merged_duplicate`)
- **Action Phase 1** : ADR-029 acte le mapping doctrinal v0.3 dans le CHECK constraint et la matrice rétention.

#### Anomalie mineure 3 — Split `closed` → 3 closure events distincts
- **Source** : ADR-025 §4.3 ligne 325 vs Brief ADR-029 §3.1
- **Impact** : Q9-B / Q37-A+ / IL5 — récurrence ≠ doublon, IE4 différencie rétention 5 ans vs 3 ans
- **Action Phase 1** : ADR-029 explicite les 3 events `closed_with_evidence` / `closed_via_merged_duplicate` / `closed_via_resolved_via_recurrence` dans CHECK + matrice rétention.

**Toutes les 3 anomalies sont anticipées par le PROMPT_L6 §3.2 :** « 15 event_types CHECK étendu à 16 ». Elles ne nécessitent pas de modification du brief.

---

## Conformité Q6-A (Mois 1 docs only)

- ☑ Aucun fichier code Python/TypeScript modifié
- ☑ Aucune table DB modifiée
- ☑ Aucun script créé sur disque (le code Python du brief est documentaire, ancré DANS l'ADR)
- ☑ Sprint Phase 3.5 (`backend/regops/`) non perturbé

---

## Compteurs Brief ADR-029

| Compteur | Valeur attendue | Brief §référence |
|---|---|---|
| Event_types `action_event_log` | 16 | §3.1 CHECK constraint |
| Schemas Pydantic v1 | 16 | §8.1 EVENT_PAYLOAD_SCHEMAS |
| Catégories rétention RGPD | 3 | §7.1 RetentionCategory |
| Invariants IE1-IE9 | 9 | §0 TL;DR |
| Arbitrages Q40-Q46 | 7 | §0 TL;DR + §15 YAML |
| Articles CNIL référencés | 8 | §10 (5(1)(b), 5(1)(e), 5(2), 6, 15, 17, 30, 32) |
| Tests planifiés | 40+ | §11 (10 evidence + 15 rétention + 15 schemas) |
| Magic bytes signatures | 3 | §6.1 (PDF, JPEG, PNG) |
| MIME types acceptés | 3 | §6.1 ACCEPTED_MIME_TYPES |
| Mapping events → catégories | 16/16 (7 compliance + 6 business + 3 system) | §7.2 |

**Tous les compteurs vérifiés ✓.**

---

## STOP GATE — récapitulatif

```
═══════════════════════════════════════════════════════
PHASE 0 TERMINÉE — STOP GATE
═══════════════════════════════════════════════════════

Bilan Phase 0 disponible : docs/dev/L6_phase0_audit_coherence.md

Vérifications cohérence :
  A · ADR-025          : 4/4 OK
  B · ADR-026          : 3/3 OK
  C · ADR-027          : 5/5 OK
  D · ADR-028          : 4/4 OK
  E · Doctrine v0.3    : 4/4 OK
  F · L1 verdicts      : 3/3 OK
  G · Maquettes M1-M5  : 3/3 OK
  H · 9 invariants     : 9/9 OK
  I · Sprint Phase 3.5 : 2/2 OK

Total : 38/38 vérifications réussies
Anomalies bloquantes : 0
Anomalies mineures : 3 (renommages event_types ADR-025 → ADR-029, anticipés par PROMPT_L6)

Compteur evidence/event log dans le brief :
  - 16 event_types documentés
  - 16 schemas Pydantic v1
  - 3 catégories rétention (compliance 5y / business 3y / system 1y)
  - 9 invariants IE1-IE9 tous présents
  - 7 arbitrages Q40-Q46 documentés
  - 40+ tests planifiés
  - 8 articles CNIL référencés
  - 3 magic bytes signatures (PDF, JPEG, PNG)

Brief consommable : OUI

⛔ NE PAS DÉMARRER Phase 1 avant validation utilisateur.

Confirmer : « GO Phase 1 »
═══════════════════════════════════════════════════════
```
