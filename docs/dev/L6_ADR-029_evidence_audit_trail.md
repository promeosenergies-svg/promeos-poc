# ADR-029 · Evidence + audit trail Centre d'Action V4

> ⚠️ **AVENANT A1 (2026-05-16)** : §2 `organisation_id` passe de UUID à Integer FK
> `organisations(id)`. Voir [`docs/dev/ADR-025-029_A1_integer_fk.md`](ADR-025-029_A1_integer_fk.md)
> (décidé par ADR-009 — résolution dette JWT/UUID, Sprint M2-4). Le présent ADR
> reste la référence pour tout le reste du schéma evidence + audit trail.
>
> **Status** : `Accepted` (amendé A1 — cf. ci-dessus)
> **Date** : 2026-05-14
> **Deciders** : Amine (PROMEOS founder) + Claude (architecture co-pilot)
> **Branch** : `claude/refonte-sol2`
> **Doctrine ref** : `docs/doctrine/doctrine_v4_classement_priorisation.md` **v0.3** (Accepted)
> **Related ADRs** : ADR-022 · ADR-025 · ADR-026 · ADR-027 · ADR-028
> **Particularité** : **dernier ADR du Mois 1** — clôture la trilogie data (architecture + lifecycle + evidence)
> **Brief source** : [`BRIEF_ADR-029_evidence_audit_trail.md`](BRIEF_ADR-029_evidence_audit_trail.md) v0.1 · 1 146 lignes
> **Phase 0 audit** : [`L6_phase0_audit_coherence.md`](L6_phase0_audit_coherence.md) · 38/38 vérifications

---

## 0. TL;DR exécutif

**ADR-029 = manuel des preuves et de la traçabilité.** Fige le schéma des tables `evidences` + `action_event_log`, la politique de rétention RGPD par catégorie, la validation des evidences, et les schemas Pydantic versionnés par event_type. Complète la trilogie data avec ADR-025 (architecture) + ADR-028 (lifecycle).

**9 invariants Evidence/Event log non négociables (IE1-IE9)** :

| # | Invariant |
|---|---|
| **IE1** | Storage evidence **abstrait** (`fs://` Mois 2 · `s3://` V4.1+) — couplage minimisé |
| **IE2** | Validation evidence **manuelle obligatoire** + métadonnées extraites + flag confiance |
| **IE3** | Rétention différenciée par catégorie : **compliance 5 ans · business 3 ans · system 1 an** |
| **IE4** | Matrice rétention **alignée doctrine v0.3** : `merged_duplicate` (3 ans) ≠ `resolved_via_recurrence` (5 ans) |
| **IE5** | Aucune purge silencieuse · **feature flag + dry-run + trace** `security_audit_log` |
| **IE6** | `expires_at = verified_at + 90 jours` pour toute evidence vérifiée |
| **IE7** | Tous payload events validés par schema **Pydantic typé avec `schema_version`** |
| **IE8** | `security_audit_log` (90j) **séparé strict** de `action_event_log` (1-5 ans) |
| **IE9** | Validation MIME par **signature fichier** (magic bytes), pas par header client (cardinal Amine 2026-05-14) |

**7 arbitrages techniques Q40-Q46 actés** (non débattables) :

| Q | Décision finale |
|---|---|
| **Q40-D** | Storage hybride filesystem + path abstrait (`fs://...` Mois 2, `s3://...` V4.1+) |
| **Q41-D** | Validation manuelle obligatoire + métadonnées extraites + flag confiance |
| **Q42-C+** | 3 catégories rétention RGPD alignées doctrine v0.3 |
| **Q43-A+** | APScheduler mensuel + feature flag + dry-run + trace sécurité |
| **Q44-A+** | PDF/JPG/PNG uniquement + validation MIME par magic bytes |
| **Q45-B** | 10 MB max par evidence |
| **Q46-B+** | Schemas Pydantic typés par event_type avec `schema_version` |

**Matrice rétention RGPD** : 16 event_types × 3 catégories (compliance 7 · business 6 · system 3).

**8 articles CNIL référencés** : art. 5(1)(b), 5(1)(e), 5(2), 6, 15, 17, 30, 32.

---

## 1. Context et problématique

Centre d'Action V4 doit produire un **audit trail défendable** (CNIL art. 30 registre de traitements) et persister des **evidences vérifiables** pour soutenir les fermetures d'items conformité (DT, BACS, APER, SMÉ).

ADR-025 §4.3 a posé le **squelette** des tables `evidences` + `action_event_log` (colonnes essentielles, FK, indexes). ADR-028 a figé les **transitions lifecycle** qui produisent les events. Mais aucun ADR n'a encore défini :

1. Le **modèle complet** des deux tables (CHECK constraints, validation_payload structuré, indexes RGPD)
2. La **politique de rétention** (combien de temps conserver chaque event ? quelles règles RGPD ?)
3. La **validation des evidences** (qui valide ? comment ? quel niveau de confiance ?)
4. Le **format des payloads events** (JSON libre ou typé ?)
5. La **sécurité MIME** (anti-spoofing par magic bytes vs header client)
6. Le **storage** des fichiers binaires (filesystem POC vs S3 production)
7. La **procédure de purge** (silencieuse ? auditée ? réversible ?)

Sans réponse formalisée à ces 7 questions, Mois 2 backend démarre sans contrat. Risques :
- **RGPD non conforme** : pas de matrice rétention par event = sanction CNIL potentielle
- **Audit trail fragile** : payload events sans schéma = impossible à exploiter en investigation
- **Evidence fraud** : header MIME spoofé = risque d'upload exécutable malveillant
- **Purge accidentelle** : sans dry-run + flag = perte irréversible d'evidences légales
- **Storage couplé** : code backend dépendant de FS = migration S3 V4.1+ refacto majeur

---

## 2. Decision drivers

| Driver | Pondération | Garde-fou retenu |
|---|---|---|
| **Conformité RGPD CNIL** | Critique | 8 articles référencés (5(1)(b/e), 5(2), 6, 15, 17, 30, 32) + matrice rétention par catégorie + endpoints export/delete |
| **Audit trail défendable** | Critique | `action_event_log` séparé de `security_audit_log` (IE8) + `correlation_id` IS9 + `actor_*` snapshot pour traçabilité historique |
| **Evidence intègre** | Critique | Validation manuelle obligatoire (IE2) + magic bytes anti-spoofing (IE9 cardinal Amine) + expiration 90 j (IE6) |
| **Purge auditée** | Élevé | Triple garde-fou IE5 (feature flag + dry-run + trace `security_audit_log`) + procédure phasée Mois 4 |
| **Évolutivité schéma** | Élevé | IE7 schema_version explicite + registry par version (`(event_type, schema_version) → schema_class`) + pattern d'évolution v1 → v2 documenté |
| **Découplage storage** | Élevé | IE1 ABC `EvidenceStorageBackend` + factory + `fs://` URI Mois 2 / `s3://` V4.1+ sans refacto |
| **Cohérence ADR-025/026/027/028** | Non négociable | 38/38 vérifications Phase 0 OK (cf. [`L6_phase0_audit_coherence.md`](L6_phase0_audit_coherence.md)) |
| **Conformité Q6-A docs only** | Non négociable | Mois 1 = aucun code modifié, aucune DB modifiée, aucun script créé sur disque |

---

## 3. 9 invariants doctrinaux IE1-IE9 (non négociables)

### 3.1 Tableau récapitulatif

| # | Invariant | Status | Section ADR | Cardinal |
|---|---|---|---|---|
| **IE1** | Storage evidence abstrait (`fs://` Mois 2 · `s3://` V4.1+) | Non négociable | §7 | — |
| **IE2** | Validation evidence manuelle obligatoire + métadonnées + flag confiance | Non négociable | §8 | — |
| **IE3** | Rétention différenciée 3 catégories (5/3/1 ans) | Non négociable | §10 | — |
| **IE4** | Matrice alignée doctrine v0.3 (`merged_duplicate` ≠ `resolved_via_recurrence`) | Non négociable | §10 | — |
| **IE5** | Purge triple garde-fou (feature flag + dry-run + trace) | Non négociable | §12 | — |
| **IE6** | `expires_at = verified_at + 90j` (DB CHECK + service) | Non négociable | §5 + §8 | — |
| **IE7** | Schemas Pydantic typés versionnés (`schema_version`) | Non négociable | §11 | — |
| **IE8** | `security_audit_log` séparé strict de `action_event_log` | Non négociable | §6 | — |
| **IE9** | Validation MIME par magic bytes (anti-spoofing) | Non négociable | §9 | **Cardinal Amine 2026-05-14** |

### 3.2 IE9 — Garde-fou cardinal Amine

**IE9 est le garde-fou cardinal ajouté en validation Q40-Q46** (2026-05-14). Il interdit que la validation MIME repose sur le header `Content-Type` envoyé par le client (forgeable trivialement), exigeant une **inspection des bytes réels du fichier** via `python-magic` + double-check signatures hardcodées.

Sans IE9, un attaquant peut uploader un `.exe` renommé `.pdf` avec `Content-Type: application/pdf` forgé, contournant la whitelist. IE9 supprime cette surface d'attaque (cf. §9 attaques mitigées).

### 3.3 IE4 — Cohérence doctrine v0.3

**IE4 matérialise l'avenant doctrinal v0.3** (commit L5 `466b64c3`). Q9-B impose que récurrence ≠ doublon ; Q37-A+ a ajouté `resolved_via_recurrence` distinct de `merged_duplicate`. La matrice rétention RGPD reflète strictement cette distinction :

- `closed_via_merged_duplicate` = **business 3 ans** (doublon technique, intérêt commercial)
- `closed_via_resolved_via_recurrence` = **compliance 5 ans** (preuve indirecte conformité)

Cette différenciation est non négociable : elle protège la doctrine v0.3 d'une dérive silencieuse via la rétention.

---

## 4. Options considérées Q40-Q46

### Q40 — Storage des evidences

- **Q40-A** : Filesystem direct (`/data/promeos/evidences/<org_id>/<id>.bin`) — couplage fort, pas migrable
- **Q40-B** : S3 dès Mois 2 — coût + dépendance externe précoce
- **Q40-C** : Base de données (BLOB column) — performance dégradée, non recommandé
- **✅ Q40-D** : Storage hybride **abstrait** via `EvidenceStorageBackend` ABC, `fs://` Mois 2 + `s3://` V4.1+

**Rationale** : POC reste filesystem (zéro coût, simple), production future S3 sans refacto code. Path abstrait `fs://<org_id>/<evidence_id>` ou `s3://<bucket>/<org_id>/<evidence_id>` géré par factory.

### Q41 — Validation des evidences

- **Q41-A** : Signature PKI cryptographique (qualified signature eIDAS) — overkill MVP, exige infrastructure PKI
- **Q41-B** : OCR automatique + validation IA — risque faux positifs, reporté V4.1+
- **Q41-C** : Validation manuelle binaire (oui/non) — pauvre en métadonnées
- **✅ Q41-D** : Validation **manuelle obligatoire** + métadonnées extraites + flag confiance (high/medium/low)

**Rationale** : Q41-A reporté V4.1+ si exigence juridique pilote. OCR retiré du MVP (faux positifs sur factures EDF/Engie). Validation humaine + extraction métadonnées (PDF info, EXIF) = équilibre robustesse/coût.

### Q42 — Rétention RGPD par event

- **Q42-A** : 5 ans uniformes — over-conservatoire, non proportionné CNIL art. 5(1)(e)
- **Q42-B** : 1 an uniforme — sous-conservatoire compliance
- **Q42-C** : 3 catégories rétention — bon équilibre mais matrice à figer
- **✅ Q42-C+** : 3 catégories rétention **alignées doctrine v0.3** (compliance 5y / business 3y / system 1y) + matrice 16 events × 3 catégories explicite

**Rationale** : CNIL art. 5(1)(e) = limitation conservation proportionnée à la finalité. 3 catégories distinguent : preuves légales (5y), audit métier (3y), maintenance technique (1y). Matrice explicite supprime ambiguïté + permet test unitaire.

### Q43 — Procédure purge mensuelle

- **Q43-A** : APScheduler mensuel sans flag — purge silencieuse, dangereux
- **Q43-B** : Manuel uniquement — risque oubli + dérive rétention
- **Q43-C** : APScheduler + feature flag — bien mais sans dry-run
- **✅ Q43-A+** : APScheduler mensuel + **feature flag + dry-run obligatoire en première activation + trace `security_audit_log`**

**Rationale** : triple garde-fou IE5 = feature flag (peut désactiver immédiatement), dry-run (compte d'abord, supprime ensuite), trace sécurité (correlation_id + counts pour audit post-mortem).

### Q44 — Validation MIME

- **Q44-A** : PDF/JPG/PNG + check header `Content-Type` client — **forgeable trivialement**
- **Q44-B** : PDF/JPG/PNG + check via `mimetypes.guess_type(filename)` — basé sur extension, forgeable
- **Q44-C** : Tout type accepté — surface d'attaque massive
- **✅ Q44-A+** : PDF/JPG/PNG + validation **par magic bytes** (signatures réelles fichier) + double-check + log mismatch

**Rationale** : Q44-A+ raffinement Amine cardinal IE9. Les 3 formats whitelist (PDF/JPG/PNG) sont pivots conformité (factures, photos terrain, rapports BV). Magic bytes (`%PDF-`, `\xff\xd8\xff`, `\x89PNG\r\n\x1a\n`) immuables. Mismatch client/réel = log security_audit_log + 422.

### Q45 — Taille max evidence

- **Q45-A** : 5 MB — trop restrictif pour rapports BV multi-pages
- **✅ Q45-B** : **10 MB** par evidence
- **Q45-C** : 50 MB — risque DoS upload, abus quotas

**Rationale** : 10 MB couvre 99% des cas réels (factures EDF/Engie 1-3 MB, rapports BV 5-8 MB, photos haute résolution 2-5 MB). CHECK constraint DB-side + check explicite endpoint = double défense.

### Q46 — Schemas payload events

- **Q46-A** : JSON libre (`event_payload JSONB`) — souplesse mais pas validable
- **Q46-B** : Schemas Pydantic typés sans versioning — bloque évolution
- **✅ Q46-B+** : Schemas Pydantic typés **avec `schema_version`** + registry `(event_type, version) → schema` + pattern d'évolution v1 → v2 documenté

**Rationale** : IE7 garantit que tout payload events est validé avant insert (rejette payload malformé en validation), traçabilité de version (analytics tooling), évolution gracefully (v1/v2 coexistent dans la base + dispatcher frontend par version).

---

## 5. Schéma DB `evidences` détaillé

### 5.1 Table `evidences`

```sql
CREATE TABLE evidences (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id     UUID NOT NULL,                      -- IS1 org_scoping
    action_item_id      UUID NOT NULL REFERENCES action_center_items(id),

    -- Métadonnées fichier
    mime_type           VARCHAR(50) NOT NULL,               -- IE9 : validé par magic bytes
    file_size_bytes     INTEGER NOT NULL CHECK (file_size_bytes <= 10485760),  -- 10 MB (Q45-B)
    storage_uri         TEXT NOT NULL,                      -- IE1 : "fs://..." ou "s3://..."
    original_filename   VARCHAR(255),                       -- nom client (informatif)

    -- Validation (IE2)
    verified_at         TIMESTAMPTZ,                        -- NULL si non vérifié
    verified_by         UUID,                               -- FK users (IE2)
    expires_at          TIMESTAMPTZ,                        -- IE6 : verified_at + 90j
    validation_payload  JSONB,                              -- IE2 : métadonnées + flag confiance

    -- Métadonnées
    uploaded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uploaded_by         UUID NOT NULL,                      -- FK users
    description         TEXT,

    -- Constraints
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

CREATE INDEX idx_evidences_org ON evidences(organisation_id, action_item_id);
CREATE INDEX idx_evidences_verified ON evidences(verified_at) WHERE verified_at IS NOT NULL;
CREATE INDEX idx_evidences_expiring ON evidences(expires_at) WHERE expires_at IS NOT NULL;
```

### 5.2 Structure `validation_payload` JSONB

```json
{
  "metadata_extracted": {
    "pdf_creation_date": "2026-05-10T08:30:00Z",
    "pdf_author": "Bureau Veritas",
    "pdf_page_count": 4,
    "image_dimensions": null,
    "magic_bytes_match": "application/pdf"
  },
  "verified_by_human": true,
  "verifier_role": "admin",
  "verification_method": "manual_with_metadata",
  "confidence_flag": "high",
  "verification_notes": "Facture EDF mai 2026, montants cohérents",
  "schema_version": "v1"
}
```

### 5.3 Cycle de vie evidence

| État | `verified_at` | `expires_at` | Action possible |
|---|---|---|---|
| Uploadée | NULL | NULL | À valider manuellement |
| Vérifiée | `NOT NULL` | `verified_at + 90j` | Utilisable comme preuve clôture |
| Expirée | `NOT NULL` | `< NOW()` | À re-uploader pour conserver clôture |
| Supprimée RGPD art. 17 | — | — | Anonymisation `uploaded_by` + storage.delete() |

---

## 6. Schéma DB `action_event_log` détaillé

### 6.1 Table `action_event_log`

```sql
CREATE TABLE action_event_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id     UUID NOT NULL,                      -- IS1 org_scoping
    action_item_id      UUID NOT NULL REFERENCES action_center_items(id),

    -- Event metadata
    event_type          VARCHAR(60) NOT NULL,               -- 16 valeurs (doctrine v0.3 + ADR-029)
    occurred_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Actor
    actor_type          VARCHAR(20) NOT NULL,               -- 'user' | 'system'
    actor_id            UUID,                               -- NULL si system
    actor_name          VARCHAR(120),                       -- snapshot du nom (audit trail)
    actor_role          VARCHAR(20),                        -- snapshot role (admin/user/viewer/system)

    -- Payload typé (IE7)
    event_payload       JSONB NOT NULL,                     -- validé par Pydantic schema versionné
    schema_version      VARCHAR(10) NOT NULL DEFAULT 'v1', -- IE7 : versioning explicite

    -- Traçabilité
    correlation_id      UUID NOT NULL,                      -- IS9 ADR-027
    source_route        VARCHAR(120),                       -- "PATCH /api/.../lifecycle"

    -- Constraints
    CONSTRAINT chk_event_type CHECK (
        event_type IN (
            -- 16 event_types ADR-029 v1 (extension de 15 ADR-025 → 16, alignement doctrine v0.3)
            'created',
            'state_changed',
            'owner_changed',
            'priority_changed',
            'blocker_added',
            'blocker_removed',
            'evidence_added',
            'evidence_verified',
            'closed_with_evidence',
            'closed_via_merged_duplicate',
            'closed_via_resolved_via_recurrence',
            'reopened',
            'bulk_updated',
            'exported',
            'kind_corrected',
            'priority_recalculated'
        )
    ),
    CONSTRAINT chk_actor_consistency CHECK (
        (actor_type = 'system' AND actor_id IS NULL) OR
        (actor_type = 'user' AND actor_id IS NOT NULL)
    )
);

CREATE INDEX idx_event_log_org_item ON action_event_log(organisation_id, action_item_id, occurred_at DESC);
CREATE INDEX idx_event_log_type ON action_event_log(event_type, occurred_at DESC);
CREATE INDEX idx_event_log_correlation ON action_event_log(correlation_id);
CREATE INDEX idx_event_log_actor ON action_event_log(actor_id, occurred_at DESC) WHERE actor_id IS NOT NULL;
```

### 6.2 Différenciation `action_event_log` vs `security_audit_log` (IE8)

| Table | Rétention | Sémantique | Cible RGPD |
|---|---|---|---|
| `action_event_log` | 1-5 ans (IE3) | Audit trail **métier** : transitions, blockers, evidences | art. 30 registre traitements |
| `security_audit_log` | 90 jours (ADR-027) | Events **sécurité** : auth, IDOR, privilege escalation | art. 32 sécurité |

**Aucun mélange.** Sémantique stricte. Tout event sécurité (`evidence.mime_mismatch`, `retention.purge.completed`) → `security_audit_log`. Tout event métier (`state_changed`, `evidence_verified`) → `action_event_log`.

### 6.3 Note d'extension event_types (renvoi ADR-025)

ADR-025 §4.3 (commit `b7208022`) avait posé un CHECK constraint avec **15 event_types** : `'created','state_changed','assigned','priority_changed','blocker_added','blocker_removed','evidence_added','evidence_verified','closed','reopened','merged','bulk_updated','exported','kind_corrected','priority_recalculated'`.

ADR-029 **étend** cette liste à 16 valeurs alignées doctrine v0.3 :
- `assigned` → `owner_changed` (sémantique plus précise, changement propriétaire)
- `merged` → `closed_via_merged_duplicate` (alignement Q9-B / Q37-A+)
- `closed` (singulier) → 3 variantes : `closed_with_evidence` + `closed_via_merged_duplicate` + `closed_via_resolved_via_recurrence` (Q9-B récurrence ≠ doublon)

Cette extension est une **dépendance aval acceptée par convention** : ADR-029, plus récent, supersède ADR-025 §4.3 sur cette liste sans nécessiter de réouverture de l'ADR-025. Une note d'extension aval est ajoutée à L2 §15 (cf. §16 Renvois).

---

## 7. Storage abstrait `EvidenceStorage` (Q40-D · IE1)

### 7.1 Service `EvidenceStorageBackend`

```python
# backend/services/evidence/storage.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

class EvidenceStorageBackend(ABC):
    """Interface abstraite. Mois 2 = filesystem · V4.1+ = S3."""

    @abstractmethod
    def store(self, evidence_id: UUID, org_id: UUID, content: bytes) -> str:
        """Retourne le storage_uri."""

    @abstractmethod
    def retrieve(self, storage_uri: str) -> bytes:
        """Lit le contenu binaire depuis l'URI."""

    @abstractmethod
    def delete(self, storage_uri: str) -> bool:
        """Suppression hard (RGPD article 17 droit à l'oubli)."""


class FilesystemBackend(EvidenceStorageBackend):
    """Backend Mois 2-6 POC."""

    def __init__(self, root: Path = Path("/data/promeos/evidences")):
        self.root = root

    def store(self, evidence_id: UUID, org_id: UUID, content: bytes) -> str:
        path = self.root / str(org_id) / f"{evidence_id}.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return f"fs://{org_id}/{evidence_id}"

    def retrieve(self, storage_uri: str) -> bytes:
        if not storage_uri.startswith("fs://"):
            raise InvalidStorageURIError(storage_uri)
        rel_path = storage_uri.removeprefix("fs://")
        full_path = self.root / f"{rel_path}.bin"
        return full_path.read_bytes()

    def delete(self, storage_uri: str) -> bool:
        if not storage_uri.startswith("fs://"):
            return False
        rel_path = storage_uri.removeprefix("fs://")
        full_path = self.root / f"{rel_path}.bin"
        if full_path.exists():
            full_path.unlink()
            return True
        return False


class S3Backend(EvidenceStorageBackend):
    """Backend V4.1+ (placeholder, à implémenter si besoin pilots externes)."""

    def store(self, evidence_id, org_id, content) -> str:
        raise NotImplementedError("S3 backend deferred to V4.1")
    # ... retrieve / delete idem


# Factory
def get_storage_backend() -> EvidenceStorageBackend:
    backend = config.EVIDENCE_STORAGE_BACKEND
    if backend == "filesystem":
        return FilesystemBackend()
    elif backend == "s3":
        return S3Backend()
    raise ConfigurationError(f"Unknown storage backend: {backend}")
```

### 7.2 Configuration env

```bash
# .env.example
EVIDENCE_STORAGE_BACKEND=filesystem          # Mois 2-6
EVIDENCE_FS_ROOT=/data/promeos/evidences      # gitignored, hors Git (IS10)
EVIDENCE_MAX_SIZE_BYTES=10485760              # 10 MB (Q45-B)
```

`.gitignore` :

```
/data/promeos/evidences/       # IE1 + IS10 ADR-027 (renforcement CI de I9 ADR-026)
```

### 7.3 Migration future fs:// → s3://

```python
# Pseudocode migration script V4.1+
for evidence in all_evidences():
    if evidence.storage_uri.startswith("fs://"):
        content = fs_backend.retrieve(evidence.storage_uri)
        new_uri = s3_backend.store(evidence.id, evidence.organisation_id, content)
        evidence.storage_uri = new_uri
        db.commit()
        fs_backend.delete(evidence.storage_uri)  # Cleanup après confirmation S3
```

Schéma DB inchangé (storage_uri TEXT) → migration purement transparente côté code applicatif.

---

## 8. Validation evidence (Q41-D · IE2 · IE6)

### 8.1 Endpoint upload

```python
@router.post("/api/action-center/items/{item_id}/evidences")
@org_scoped(allowed_roles=["admin", "user"])
async def upload_evidence(
    item_id: UUID,
    file: UploadFile,
    description: Optional[str] = Form(None),
    request: Request,
    repo: EvidenceRepository = Depends(get_repo),
    storage: EvidenceStorageBackend = Depends(get_storage_backend),
):
    """
    Upload evidence. Validation MIME par magic bytes (IE9).
    Validation manuelle obligatoire en second temps (IE2).
    """
    content_bytes = await file.read()

    # IE9 : validation MIME par signature
    real_mime = validate_evidence_mime(content_bytes, file.content_type)

    # Q45-B + check explicite
    if len(content_bytes) > 10 * 1024 * 1024:
        raise HTTPException(413, "Evidence too large (max 10 MB)")

    # IE1 : storage abstrait
    evidence_id = uuid4()
    storage_uri = storage.store(evidence_id, request.state.organisation_id, content_bytes)

    # IE2 : extraction métadonnées
    metadata = extract_metadata(content_bytes, real_mime)

    evidence = Evidence(
        id=evidence_id,
        organisation_id=request.state.organisation_id,
        action_item_id=item_id,
        mime_type=real_mime,
        file_size_bytes=len(content_bytes),
        storage_uri=storage_uri,
        original_filename=file.filename,
        uploaded_by=request.state.user_id,
        description=description,
        validation_payload={
            "metadata_extracted": metadata,
            "verified_by_human": False,  # IE2 : pas encore vérifié
            "schema_version": "v1",
        }
        # verified_at, verified_by, expires_at sont NULL (IE2)
    )
    repo.save(evidence)

    # IE7 : event log avec schema Pydantic
    write_event(
        action_item_id=item_id,
        event_type="evidence_added",
        actor=build_actor(request),
        payload={
            "evidence_id": str(evidence_id),
            "mime_type": real_mime,
            "size_bytes": len(content_bytes),
            "storage_uri": storage_uri,
            "schema_version": "v1",
        }
    )

    return evidence
```

### 8.2 Endpoint vérification (IE2 + IE6)

```python
class VerifyEvidenceRequest(BaseModel):
    confidence_flag: Literal["high", "medium", "low"]
    verification_notes: Optional[str] = None


@router.patch("/api/action-center/evidences/{evidence_id}/verify")
@org_scoped(allowed_roles=["admin", "user"])
async def verify_evidence(
    evidence_id: UUID,
    payload: VerifyEvidenceRequest,
    request: Request,
    repo: EvidenceRepository = Depends(get_repo),
):
    evidence = repo.get_by_id(evidence_id, organisation_id=request.state.organisation_id)
    if not evidence:
        raise HTTPException(404)  # IS3 ADR-027 (404 pas 403 pour cross-org)

    if evidence.verified_at:
        raise HTTPException(409, {
            "code": "EVIDENCE_ALREADY_VERIFIED",
            "message": "This evidence is already verified",
            "hint": "Re-upload a new evidence if needed",
        })

    # IE2 + IE6 : verified_at + 90j obligatoire
    now = datetime.utcnow()
    evidence.verified_at = now
    evidence.verified_by = request.state.user_id
    evidence.expires_at = now + timedelta(days=90)
    evidence.validation_payload = {
        **evidence.validation_payload,
        "verified_by_human": True,
        "verifier_role": request.state.role,
        "verification_method": "manual_with_metadata",
        "confidence_flag": payload.confidence_flag,
        "verification_notes": payload.verification_notes,
    }
    repo.save(evidence)

    write_event(
        action_item_id=evidence.action_item_id,
        event_type="evidence_verified",
        actor=build_actor(request),
        payload={
            "evidence_id": str(evidence_id),
            "verified_at": now.isoformat(),
            "expires_at": evidence.expires_at.isoformat(),
            "confidence_flag": payload.confidence_flag,
            "schema_version": "v1",
        }
    )

    return evidence
```

### 8.3 Bénéfices Q41-D

| Bénéfice | Mécanisme |
|---|---|
| **Evidence non utilisable avant validation** | `verified_at IS NULL` → action close interdite (IL7 ADR-028 P0/P1 exige preuve) |
| **Audit traçable** | `verified_by` + `verifier_role` snapshot dans `validation_payload` |
| **Métadonnées exploitables** | `metadata_extracted` exposable analytics + IA V4.1+ |
| **Confiance graduée** | `confidence_flag` (high/medium/low) ouvre escalades doute |

---

## 9. Validation MIME magic bytes (Q44-A+ · IE9 cardinal Amine)

### 9.1 Service `validate_evidence_mime`

```python
# backend/services/evidence/mime_validator.py

import magic  # python-magic (libmagic)

ACCEPTED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

MAGIC_BYTES_SIGNATURES = {
    b"%PDF-": "application/pdf",         # 25 50 44 46 2D
    b"\xff\xd8\xff": "image/jpeg",       # FF D8 FF
    b"\x89PNG\r\n\x1a\n": "image/png",   # 89 50 4E 47 0D 0A 1A 0A
}


def validate_evidence_mime(content_bytes: bytes, client_declared_mime: Optional[str] = None) -> str:
    """
    IE9 : validation MIME par signature réelle (anti-spoofing).

    Steps:
      1. Détection magic bytes via libmagic
      2. Whitelist check (ACCEPTED_MIME_TYPES)
      3. Mismatch client/réel logged (security_audit_log)
      4. Double-check magic bytes manuel

    Returns: real_mime_type (validated)
    Raises: InvalidEvidenceFormatError
    """
    # Étape 1 : libmagic
    real_mime = magic.from_buffer(content_bytes[:2048], mime=True)

    # Étape 2 : whitelist
    if real_mime not in ACCEPTED_MIME_TYPES:
        raise InvalidEvidenceFormatError(
            code="EVIDENCE_MIME_NOT_ACCEPTED",
            message=f"File signature indicates {real_mime}, not accepted",
            hint=f"Accepted: {ACCEPTED_MIME_TYPES}",
            detected_mime=real_mime,
        )

    # Étape 3 : log mismatch client/réel
    if client_declared_mime and client_declared_mime != real_mime:
        log_security_event(
            event_type="evidence.mime_mismatch",
            severity="warning",
            declared=client_declared_mime,
            detected=real_mime,
        )

    # Étape 4 : double-check signatures hardcodées
    matched = False
    for signature, expected_mime in MAGIC_BYTES_SIGNATURES.items():
        if content_bytes.startswith(signature) and expected_mime == real_mime:
            matched = True
            break

    if not matched:
        raise InvalidEvidenceFormatError(
            code="EVIDENCE_MAGIC_BYTES_MISMATCH",
            message="File magic bytes do not match detected MIME"
        )

    return real_mime


def extract_metadata(content_bytes: bytes, mime_type: str) -> dict:
    """Extraction métadonnées (PDF info, EXIF, etc.)."""
    if mime_type == "application/pdf":
        return extract_pdf_metadata(content_bytes)
    elif mime_type in ("image/jpeg", "image/png"):
        return extract_image_metadata(content_bytes)
    return {}
```

### 9.2 Attaques mitigées

| Attaque | Mitigation IE9 |
|---|---|
| `.exe` renommé `.pdf` avec `Content-Type: application/pdf` forgé | Magic bytes détectent EXE (`MZ\x90\x00`) → 422 `EVIDENCE_MIME_NOT_ACCEPTED` |
| PDF/HTML polyglotte (PDF qui contient JS exécutable) | Magic bytes valident PDF, libmagic peut détecter polyglottes via heuristique |
| Header HTTP `Content-Type` spoofed | Détection mismatch loggué dans `security_audit_log` (forensique) |
| Image avec EXIF malicieux exécutable | Pas exécutable (image inerte), métadonnées EXIF sanitizées avant stockage |
| Archive ZIP renommée PDF (zip slip via path traversal au moment du retrieval) | Magic bytes ZIP détectés (`PK\x03\x04`) → 422 |

### 9.3 Pourquoi 4 étapes (et pas 1) ?

L'attaquant qui contourne libmagic (étape 1) doit aussi contourner le double-check étape 4 (signatures hardcodées). L'attaquant qui forge un header MIME (étape 3) déclenche au minimum un log security forensique. Profondeur défense = 4 lignes empilées.

---

## 10. Matrice rétention RGPD (Q42-C+ · IE3 · IE4)

### 10.1 3 catégories de rétention

```python
# backend/constants/retention.py

class RetentionCategory(str, Enum):
    COMPLIANCE = "compliance"   # Preuves réglementaires, ROI, actions admin
    BUSINESS = "business"       # Audit trail métier
    SYSTEM = "system"           # Maintenance technique


CATEGORY_RETENTION_DAYS: dict[RetentionCategory, int] = {
    RetentionCategory.COMPLIANCE: 1825,  # 5 ans
    RetentionCategory.BUSINESS: 1095,    # 3 ans
    RetentionCategory.SYSTEM: 365,       # 1 an
}
```

### 10.2 Mapping event_type → catégorie (16 events)

```python
EVENT_TYPE_CATEGORY: dict[str, RetentionCategory] = {
    # Audit trail métier (3 ans · 6 events)
    "created": RetentionCategory.BUSINESS,
    "state_changed": RetentionCategory.BUSINESS,
    "owner_changed": RetentionCategory.BUSINESS,
    "priority_changed": RetentionCategory.BUSINESS,
    "blocker_added": RetentionCategory.BUSINESS,
    "blocker_removed": RetentionCategory.BUSINESS,
    "closed_via_merged_duplicate": RetentionCategory.BUSINESS,  # Q9-B fusion technique

    # Compliance (5 ans · 7 events)
    "evidence_added": RetentionCategory.COMPLIANCE,
    "evidence_verified": RetentionCategory.COMPLIANCE,
    "closed_with_evidence": RetentionCategory.COMPLIANCE,
    "closed_via_resolved_via_recurrence": RetentionCategory.COMPLIANCE,  # Q9-B preuve indirecte
    "reopened": RetentionCategory.COMPLIANCE,           # IL3 admin sensible
    "kind_corrected": RetentionCategory.COMPLIANCE,     # IS5 admin sensible

    # System (1 an · 3 events)
    "bulk_updated": RetentionCategory.SYSTEM,
    "exported": RetentionCategory.SYSTEM,
    "priority_recalculated": RetentionCategory.SYSTEM,
}
```

**Note** : `closed_via_merged_duplicate` est en business (3 ans) car c'est une fusion technique (le doublon n'apporte pas de preuve réglementaire). À l'inverse, `closed_via_resolved_via_recurrence` est en compliance (5 ans) car c'est une **preuve indirecte** : l'item a été résolu via le groupe récurrence, et le groupe lui-même porte la justification réglementaire (IL5 + Q9-B).

### 10.3 Justification RGPD article par article

| Event category | Article CNIL | Justification |
|---|---|---|
| Compliance 5 ans | art. 30 + art. 5(2) | Registre traitements + intégrité preuves |
| Business 3 ans | art. 5(1)(e) | Limitation durée conservation proportionnée à l'audit métier |
| System 1 an | art. 5(1)(b) + 5(1)(e) | Finalité maintenance + durée stricte |

### 10.4 Justification 5 ans (compliance)

CNIL recommande 5 ans pour :
- Preuves de respect d'obligations légales (DT, BACS, APER, SMÉ)
- Documents soumis à audit ou contrôle (BV, ICPE, COFRAC)
- Justifications de fermetures d'items conformité

Cette durée correspond aussi à la **prescription quinquennale** civile (art. 2224 Code civil) — au-delà de 5 ans, la responsabilité contractuelle PROMEOS ne peut plus être engagée sur la base de ces preuves.

### 10.5 Justification 3 ans (business)

3 ans = durée audit interne typique + limite raisonnable pour rétro-analyses opérationnelles. Au-delà, les transitions d'état (`state_changed`, `owner_changed`) perdent leur valeur opérationnelle.

### 10.6 Justification 1 an (system)

Bulk operations + exports + recalculs scoring sont des **events techniques** sans valeur de preuve. 1 an permet rétro-analyse incidents post-mortem dans une fenêtre raisonnable.

---

## 11. Schemas Pydantic versionnés (Q46-B+ · IE7)

### 11.1 Structure générale

```python
# backend/schemas/event_payloads/__init__.py

from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel

# Base avec schema_version cardinal
class EventPayloadBase(BaseModel):
    schema_version: Literal["v1"] = "v1"
```

### 11.2 16 schémas v1

```python
# 1. created
class CreatedPayloadV1(EventPayloadBase):
    initial_state: str
    initial_kind: str
    triggered_by: str  # "manual" | "automatic_detection" | "regulatory_applicability_service"


# 2. state_changed
class StateChangedPayloadV1(EventPayloadBase):
    from_state: str
    to_state: str
    closure_reason: Optional[str] = None
    justification: Optional[str] = None
    auto_closed_by_group_id: Optional[UUID] = None


# 3. owner_changed
class OwnerChangedPayloadV1(EventPayloadBase):
    from_owner_id: Optional[UUID]
    to_owner_id: UUID
    reason: Optional[str] = None


# 4. priority_changed
class PriorityChangedPayloadV1(EventPayloadBase):
    from_priority: str
    to_priority: str
    from_score: float
    to_score: float
    recalc_triggered_by: str  # 12 events doctrine v0.3


# 5. blocker_added
class BlockerAddedPayloadV1(EventPayloadBase):
    blocker_type: str
    justification: str
    expected_resolution_at: Optional[str]


# 6. blocker_removed
class BlockerRemovedPayloadV1(EventPayloadBase):
    blocker_id: UUID
    resolution_note: Optional[str]


# 7. evidence_added
class EvidenceAddedPayloadV1(EventPayloadBase):
    evidence_id: UUID
    mime_type: str
    size_bytes: int
    storage_uri: str


# 8. evidence_verified
class EvidenceVerifiedPayloadV1(EventPayloadBase):
    evidence_id: UUID
    verified_at: str
    expires_at: str
    confidence_flag: Literal["high", "medium", "low"]


# 9. closed_with_evidence
class ClosedWithEvidencePayloadV1(EventPayloadBase):
    evidence_id: UUID
    closure_reason: Literal["resolved"]


# 10. closed_via_merged_duplicate
class ClosedViaMergedDuplicatePayloadV1(EventPayloadBase):
    duplicate_group_id: UUID
    primary_item_id: UUID


# 11. closed_via_resolved_via_recurrence
class ClosedViaResolvedViaRecurrencePayloadV1(EventPayloadBase):
    recurrence_group_id: UUID
    group_resolution_date: str
    group_resolution_justification: Optional[str]


# 12. reopened
class ReopenedPayloadV1(EventPayloadBase):
    previous_closure_reason: str
    justification: str  # IL11 obligatoire min 10 chars
    admin_actor_id: UUID


# 13. bulk_updated
class BulkUpdatedPayloadV1(EventPayloadBase):
    field_updated: str
    items_count: int
    correlation_id: UUID


# 14. exported
class ExportedPayloadV1(EventPayloadBase):
    export_format: str  # "xlsx" | "pdf" | "csv"
    items_count: int


# 15. kind_corrected
class KindCorrectedPayloadV1(EventPayloadBase):
    from_kind: str
    to_kind: str
    admin_actor_id: UUID
    justification: str


# 16. priority_recalculated
class PriorityRecalculatedPayloadV1(EventPayloadBase):
    trigger_event: str  # 12 events doctrine v0.3
    new_score: float
    new_bracket: str
```

### 11.3 Registry

```python
EVENT_PAYLOAD_SCHEMAS: dict[tuple[str, str], type[BaseModel]] = {
    ("created", "v1"): CreatedPayloadV1,
    ("state_changed", "v1"): StateChangedPayloadV1,
    ("owner_changed", "v1"): OwnerChangedPayloadV1,
    ("priority_changed", "v1"): PriorityChangedPayloadV1,
    ("blocker_added", "v1"): BlockerAddedPayloadV1,
    ("blocker_removed", "v1"): BlockerRemovedPayloadV1,
    ("evidence_added", "v1"): EvidenceAddedPayloadV1,
    ("evidence_verified", "v1"): EvidenceVerifiedPayloadV1,
    ("closed_with_evidence", "v1"): ClosedWithEvidencePayloadV1,
    ("closed_via_merged_duplicate", "v1"): ClosedViaMergedDuplicatePayloadV1,
    ("closed_via_resolved_via_recurrence", "v1"): ClosedViaResolvedViaRecurrencePayloadV1,
    ("reopened", "v1"): ReopenedPayloadV1,
    ("bulk_updated", "v1"): BulkUpdatedPayloadV1,
    ("exported", "v1"): ExportedPayloadV1,
    ("kind_corrected", "v1"): KindCorrectedPayloadV1,
    ("priority_recalculated", "v1"): PriorityRecalculatedPayloadV1,
}
```

### 11.4 Service `write_event`

```python
# backend/services/event_log/writer.py

def write_event(
    action_item_id: UUID,
    organisation_id: UUID,
    event_type: str,
    payload_dict: dict,
    actor: User,
    correlation_id: UUID,
    schema_version: str = "v1",
) -> ActionEventLog:
    """
    IE7 : validation Pydantic obligatoire avant insert.
    """
    schema_class = EVENT_PAYLOAD_SCHEMAS.get((event_type, schema_version))
    if not schema_class:
        raise InvalidEventSchemaError(
            code="EVENT_SCHEMA_NOT_FOUND",
            message=f"No schema for event_type={event_type} version={schema_version}"
        )

    # Validation Pydantic
    try:
        validated = schema_class(**payload_dict)
    except ValidationError as e:
        raise InvalidEventPayloadError(
            code="EVENT_PAYLOAD_INVALID",
            message=str(e),
            event_type=event_type,
            schema_version=schema_version,
        )

    # Insert
    event = ActionEventLog(
        organisation_id=organisation_id,
        action_item_id=action_item_id,
        event_type=event_type,
        actor_type="user" if not actor.is_system else "system",
        actor_id=actor.id if not actor.is_system else None,
        actor_name=actor.name,
        actor_role=actor.role,
        event_payload=validated.model_dump(),
        schema_version=schema_version,
        correlation_id=correlation_id,
        source_route=actor.request_route,
    )
    db.add(event)
    return event
```

### 11.5 Évolution future (V4.1+)

```python
# Quand on ajoute un champ à state_changed :

class StateChangedPayloadV2(EventPayloadBase):
    schema_version: Literal["v2"] = "v2"
    from_state: str
    to_state: str
    closure_reason: Optional[str] = None
    justification: Optional[str] = None
    auto_closed_by_group_id: Optional[UUID] = None
    transition_duration_ms: int  # NOUVEAU V2

# Enregistrer dans le registry
EVENT_PAYLOAD_SCHEMAS[("state_changed", "v2")] = StateChangedPayloadV2

# Migration script : convertir v1 → v2 avec transition_duration_ms=NULL
# Frontend dispatcher : afficher v1 et v2 correctement
```

**Co-existence v1 + v2 garantie** : la base contient les events v1 historiques + nouveaux events v2 ; le registry permet de retrouver le bon schema pour chaque ligne via `(event_type, schema_version)`.

---

## 12. Purge mensuelle (Q43-A+ · IE5 triple garde-fou)

### 12.1 Service `monthly_retention_purge`

```python
# backend/maintenance/retention_purge.py

from apscheduler.triggers.cron import CronTrigger

@scheduler.scheduled_job(
    CronTrigger(day=1, hour=2),  # 1er du mois à 2h UTC
    id='monthly_retention_purge'
)
def monthly_retention_purge():
    """
    IE5 : triple garde-fou
    - Feature flag RETENTION_PURGE_ENABLED
    - Dry-run mode RETENTION_PURGE_DRY_RUN_FIRST
    - Trace security_audit_log avec correlation_id
    """
    # Garde-fou 1 : feature flag
    if not config.RETENTION_PURGE_ENABLED:
        log_security_event(
            event_type="retention.purge.skipped",
            reason="feature_flag_disabled"
        )
        return

    correlation_id = uuid4()
    now = datetime.utcnow()
    dry_run = config.RETENTION_PURGE_DRY_RUN_FIRST  # Garde-fou 2

    purged_counts = {}
    total_affected = 0

    for event_type, category in EVENT_TYPE_CATEGORY.items():
        retention_days = CATEGORY_RETENTION_DAYS[category]
        cutoff = now - timedelta(days=retention_days)

        if dry_run:
            count = db.query(ActionEventLog).filter(
                ActionEventLog.event_type == event_type,
                ActionEventLog.occurred_at < cutoff,
            ).count()
            purged_counts[event_type] = {"would_delete": count, "executed": False}
            total_affected += count
        else:
            deleted = db.query(ActionEventLog).filter(
                ActionEventLog.event_type == event_type,
                ActionEventLog.occurred_at < cutoff,
            ).delete(synchronize_session=False)
            purged_counts[event_type] = {"deleted": deleted, "executed": True}
            total_affected += deleted

    if not dry_run:
        db.commit()

    # Garde-fou 3 : trace security_audit_log
    log_security_event(
        event_type="retention.purge.completed" if not dry_run else "retention.purge.dry_run",
        severity="info",
        correlation_id=str(correlation_id),
        purged_counts=purged_counts,
        cutoff_date=now.isoformat(),
        dry_run=dry_run,
        total_events_affected=total_affected,
    )
```

### 12.2 Procédure activation prod

| Phase | Période | `RETENTION_PURGE_ENABLED` | `RETENTION_PURGE_DRY_RUN_FIRST` | Effet |
|---|---|---|---|---|
| Phase 1 | Mois 2-3 | `False` | `True` | Pas de purge, trace `skipped` |
| Phase 2 | Mois 4 J-7 | `True` | `True` | Dry-run staging → rapport counts |
| Phase 3 | Mois 4 J+1 | `True` | `False` | Purge réelle (validée) |
| Phase 4 | Mois 5+ | `True` | `False` | Régime cruise mensuel |

### 12.3 Cohérence cutover ADR-026

Le calendrier de purge est **strictement aligné** sur le cutover Mois 4 ADR-026 :
- J-7 dry-run avant cutover (validation rapport)
- J+1 purge réelle (post-cutover stable)
- J+14 STOP GATE manuel ADR-026 vérifie absence de régression (cf. ADR-026 §5)

Aucun risque de purge accidentelle pendant la fenêtre cutover sec.

### 12.4 Procédure rollback purge

Si bug détecté post-purge : la purge ayant été réelle (DELETE), le rollback exige restore depuis backup ADR-026 (triple artefact + checksums SHA256). Le `correlation_id` permet de retrouver les events purgés dans le rapport `purged_counts` du `security_audit_log`.

**Mitigation préventive** : la phase dry-run J-7 doit produire un rapport validé manuellement avant J+1 purge réelle.

---

## 13. Articles CNIL référencés + endpoints RGPD

### 13.1 8 articles référencés

| Article | Application ADR-029 |
|---|---|
| **art. 5(1)(b)** Finalité spécifiée | 3 catégories rétention = 3 finalités distinctes |
| **art. 5(1)(e)** Limitation conservation | Rétention proportionnée par catégorie |
| **art. 5(2)** Intégrité confidentialité | Magic bytes + validation manuelle |
| **art. 6** Base légale | Obligation légale (DT/BACS) + intérêt légitime |
| **art. 15** Droit d'accès | Endpoint export user-triggered (§13.2) |
| **art. 17** Droit à l'oubli | Endpoint suppression + storage.delete() (§13.3) |
| **art. 30** Registre traitements | Tous events tracés + schema_version |
| **art. 32** Sécurité traitement | `security_audit_log` séparé (IE8) + IS7/IS8 ADR-027 |

### 13.2 Endpoint export RGPD (art. 15)

```python
@router.get("/api/users/me/data-export")
@org_scoped()
async def export_user_data(request: Request):
    """
    RGPD art. 15 : droit d'accès aux données personnelles.
    Retourne tous les events liés au user (actor_id).
    """
    user_id = request.state.user_id
    events = db.query(ActionEventLog).filter(
        ActionEventLog.actor_id == user_id,
        ActionEventLog.organisation_id == request.state.organisation_id,
    ).all()

    write_event(
        action_item_id=None,  # event de niveau org
        event_type="exported",
        actor=build_actor(request),
        payload={"export_format": "json", "items_count": len(events), "schema_version": "v1"}
    )

    return {"events": [e.to_dict() for e in events]}
```

### 13.3 Endpoint suppression RGPD (art. 17)

```python
@router.delete("/api/users/me/data")
@admin_only_with_fresh_token  # IS5 ADR-027 : sensible
async def delete_user_data(request: Request):
    """
    RGPD art. 17 : droit à l'oubli.
    Anonymise (pas supprime) les events du user pour préserver l'audit trail.
    """
    user_id = request.state.user_id

    # Events : anonymisation (pas suppression — préserve intégrité audit trail CNIL art. 30)
    db.query(ActionEventLog).filter(
        ActionEventLog.actor_id == user_id,
    ).update({
        "actor_id": None,
        "actor_name": "[ANONYMIZED]",
        "actor_role": None,
    })

    # Evidences uploaded_by : idem
    db.query(Evidence).filter(Evidence.uploaded_by == user_id).update({
        "uploaded_by": None,
    })

    db.commit()
```

**Note RGPD art. 17 / art. 30 tension** : suppression complète des events conflits avec art. 30 (registre traitements). PROMEOS retient l'**anonymisation** (préserve intégrité audit trail tout en supprimant le lien à la personne physique). Cette interprétation est conforme à la doctrine CNIL 2023 sur les registres de traitements.

---

## 14. Tests planifiés (40+)

### 14.1 Tests validation evidence (10)

```python
def test_IE2_evidence_not_verified_by_default():
    evidence = upload_evidence(...)
    assert evidence.verified_at is None
    assert evidence.expires_at is None

def test_IE2_verify_evidence_sets_metadata():
    evidence = upload_evidence(...)
    response = client.patch(f"/evidences/{evidence.id}/verify",
                            json={"confidence_flag": "high"})
    assert response.json()["verified_by_human"] is True
    assert response.json()["expires_at"] == (verified_at + timedelta(days=90)).isoformat()

def test_IE6_expires_at_exactly_90_days():
    evidence = upload_and_verify_evidence(...)
    delta = evidence.expires_at - evidence.verified_at
    assert delta.days == 90

def test_IE6_db_check_constraint_rejects_wrong_expires():
    """CHECK constraint refuse expires_at != verified_at + 90j."""
    with pytest.raises(IntegrityError, match="chk_evidence_expires_90d"):
        Evidence(verified_at=now, expires_at=now + timedelta(days=120)).save()

def test_IE9_magic_bytes_reject_exe_renamed_pdf():
    fake_pdf = b"MZ\x90\x00..."  # EXE header
    with pytest.raises(InvalidEvidenceFormatError) as exc:
        validate_evidence_mime(fake_pdf, "application/pdf")
    assert exc.value.code == "EVIDENCE_MIME_NOT_ACCEPTED"

def test_IE9_magic_bytes_mismatch_logged():
    real_jpeg = b"\xff\xd8\xff..."
    validate_evidence_mime(real_jpeg, client_declared_mime="application/pdf")
    events = security_audit_log_repo.list_by_event_type("evidence.mime_mismatch")
    assert len(events) == 1

def test_Q45B_size_limit_10mb():
    """Reject upload > 10 MB."""
    big = b"%PDF-" + b"X" * (11 * 1024 * 1024)
    response = client.post("/evidences", files={"file": ("big.pdf", big)})
    assert response.status_code == 413

def test_IE2_double_verify_raises_409():
    evidence = upload_and_verify_evidence(...)
    response = client.patch(f"/evidences/{evidence.id}/verify",
                            json={"confidence_flag": "low"})
    assert response.status_code == 409
    assert response.json()["code"] == "EVIDENCE_ALREADY_VERIFIED"

def test_IS3_cross_org_evidence_returns_404():
    """Evidence d'org B accédée par user org A → 404 (pas 403)."""
    evidence_org_b = create_evidence_for_org("B")
    set_session_org("A")
    response = client.patch(f"/evidences/{evidence_org_b.id}/verify",
                            json={"confidence_flag": "high"})
    assert response.status_code == 404

def test_IE1_storage_uri_starts_with_fs():
    evidence = upload_evidence(...)
    assert evidence.storage_uri.startswith("fs://")
```

### 14.2 Tests rétention (15)

```python
def test_IE3_compliance_5y_business_3y_system_1y():
    assert CATEGORY_RETENTION_DAYS[RetentionCategory.COMPLIANCE] == 1825
    assert CATEGORY_RETENTION_DAYS[RetentionCategory.BUSINESS] == 1095
    assert CATEGORY_RETENTION_DAYS[RetentionCategory.SYSTEM] == 365

def test_IE4_merged_duplicate_is_business_3y():
    assert EVENT_TYPE_CATEGORY["closed_via_merged_duplicate"] == RetentionCategory.BUSINESS

def test_IE4_resolved_via_recurrence_is_compliance_5y():
    assert EVENT_TYPE_CATEGORY["closed_via_resolved_via_recurrence"] == RetentionCategory.COMPLIANCE

def test_IE4_doctrine_v03_alignment():
    """Q9-B / Q37-A+ : récurrence ≠ doublon dans la matrice rétention."""
    assert EVENT_TYPE_CATEGORY["closed_via_merged_duplicate"] != EVENT_TYPE_CATEGORY["closed_via_resolved_via_recurrence"]

def test_IE5_purge_feature_flag_off_skips():
    config.RETENTION_PURGE_ENABLED = False
    monthly_retention_purge()
    events = security_audit_log_repo.list_recent(event_type="retention.purge.skipped")
    assert len(events) == 1

def test_IE5_purge_dry_run_counts_no_delete():
    config.RETENTION_PURGE_ENABLED = True
    config.RETENTION_PURGE_DRY_RUN_FIRST = True
    create_old_events(count=10)
    monthly_retention_purge()
    assert db.query(ActionEventLog).count() == 10  # nothing deleted

def test_IE5_purge_real_deletes_old_events():
    config.RETENTION_PURGE_ENABLED = True
    config.RETENTION_PURGE_DRY_RUN_FIRST = False
    create_old_events(category=RetentionCategory.SYSTEM, days_old=400, count=5)
    monthly_retention_purge()
    assert db.query(ActionEventLog).count() == 0

def test_IE5_purge_keeps_recent_events():
    config.RETENTION_PURGE_ENABLED = True
    config.RETENTION_PURGE_DRY_RUN_FIRST = False
    create_old_events(category=RetentionCategory.SYSTEM, days_old=300, count=5)
    monthly_retention_purge()
    assert db.query(ActionEventLog).count() == 5

def test_IE5_purge_traces_correlation_id():
    config.RETENTION_PURGE_ENABLED = True
    monthly_retention_purge()
    sec_events = security_audit_log_repo.list_recent(event_type="retention.purge.completed")
    assert sec_events[0].correlation_id is not None

def test_IE3_compliance_event_kept_5_years():
    create_event(event_type="evidence_verified", days_old=1800)  # < 5 ans
    monthly_retention_purge_real()
    assert db.query(ActionEventLog).count() == 1

def test_IE3_compliance_event_purged_after_5_years():
    create_event(event_type="evidence_verified", days_old=1900)  # > 5 ans
    monthly_retention_purge_real()
    assert db.query(ActionEventLog).count() == 0

def test_IE3_business_event_purged_after_3_years():
    create_event(event_type="state_changed", days_old=1100)  # > 3 ans
    monthly_retention_purge_real()
    assert db.query(ActionEventLog).count() == 0

def test_IE3_system_event_purged_after_1_year():
    create_event(event_type="bulk_updated", days_old=400)  # > 1 an
    monthly_retention_purge_real()
    assert db.query(ActionEventLog).count() == 0

def test_RGPD_art17_anonymizes_user_events():
    user = create_user()
    create_event(actor_id=user.id, event_type="state_changed")
    delete_user_data(user)
    event = db.query(ActionEventLog).first()
    assert event.actor_id is None
    assert event.actor_name == "[ANONYMIZED]"

def test_RGPD_art15_export_user_events():
    user = create_user()
    create_event(actor_id=user.id, event_type="evidence_added")
    response = export_user_data(user)
    assert len(response["events"]) >= 1
```

### 14.3 Tests schemas Pydantic (15)

```python
@pytest.mark.parametrize("event_key", list(EVENT_PAYLOAD_SCHEMAS.keys()))
def test_IE7_all_event_types_have_schema(event_key):
    """16 event_types ont chacun un schéma v1."""
    schema = EVENT_PAYLOAD_SCHEMAS.get(event_key)
    assert schema is not None
    assert schema.model_fields["schema_version"].default == "v1"

def test_IE7_write_event_rejects_invalid_payload():
    with pytest.raises(InvalidEventPayloadError):
        write_event(
            event_type="state_changed",
            payload_dict={"from_state": "invalid_state"},  # missing to_state
            ...
        )

def test_IE7_schema_version_persisted():
    write_event(event_type="state_changed", payload_dict={
        "from_state": "triaged", "to_state": "planned"
    }, schema_version="v1")
    event = db.query(ActionEventLog).first()
    assert event.schema_version == "v1"
    assert event.event_payload["schema_version"] == "v1"

def test_IE7_unknown_schema_version_rejected():
    with pytest.raises(InvalidEventSchemaError):
        write_event(event_type="state_changed", payload_dict={...}, schema_version="v99")

def test_IL11_reopened_payload_requires_justification():
    """ReopenedPayloadV1.justification obligatoire."""
    with pytest.raises(ValidationError):
        ReopenedPayloadV1(previous_closure_reason="resolved", admin_actor_id=uuid4())

def test_IL5_closed_via_merged_duplicate_requires_group():
    """ClosedViaMergedDuplicatePayloadV1 exige duplicate_group_id + primary_item_id."""
    with pytest.raises(ValidationError):
        ClosedViaMergedDuplicatePayloadV1(duplicate_group_id=uuid4())

def test_Q9B_resolved_via_recurrence_requires_recurrence_group():
    """ClosedViaResolvedViaRecurrencePayloadV1 distinct de merged_duplicate."""
    payload = ClosedViaResolvedViaRecurrencePayloadV1(
        recurrence_group_id=uuid4(),
        group_resolution_date="2026-05-14",
    )
    assert payload.schema_version == "v1"

def test_IE7_evidence_added_carries_storage_uri():
    payload = EvidenceAddedPayloadV1(
        evidence_id=uuid4(),
        mime_type="application/pdf",
        size_bytes=1024,
        storage_uri="fs://abc/def",
    )
    assert payload.storage_uri.startswith("fs://")

def test_IE7_evidence_verified_carries_confidence_flag():
    payload = EvidenceVerifiedPayloadV1(
        evidence_id=uuid4(),
        verified_at="2026-05-14T10:00:00Z",
        expires_at="2026-08-12T10:00:00Z",
        confidence_flag="high",
    )
    assert payload.confidence_flag in ("high", "medium", "low")

def test_IE7_priority_changed_includes_scores():
    payload = PriorityChangedPayloadV1(
        from_priority="P3", to_priority="P1",
        from_score=12.0, to_score=78.5,
        recalc_triggered_by="evidence_verified",
    )
    assert payload.to_score > payload.from_score

def test_IS9_correlation_id_propagated_in_bulk():
    """BulkUpdatedPayloadV1.correlation_id obligatoire."""
    cid = uuid4()
    payload = BulkUpdatedPayloadV1(field_updated="owner_id", items_count=5, correlation_id=cid)
    assert payload.correlation_id == cid

def test_IE7_v2_coexists_with_v1():
    """Pattern d'évolution v1 → v2."""
    EVENT_PAYLOAD_SCHEMAS[("state_changed", "v2")] = StateChangedPayloadV2
    write_event(event_type="state_changed", payload_dict={
        "from_state": "triaged", "to_state": "planned", "transition_duration_ms": 1500
    }, schema_version="v2")
    event = db.query(ActionEventLog).filter(ActionEventLog.schema_version == "v2").first()
    assert event.event_payload["transition_duration_ms"] == 1500

def test_IL3_reopened_carries_admin_actor():
    """Réouverture exige admin_actor_id (IL3 + IL11)."""
    payload = ReopenedPayloadV1(
        previous_closure_reason="resolved",
        justification="Found new evidence requiring re-examination",
        admin_actor_id=uuid4(),
    )
    assert payload.admin_actor_id is not None

def test_IE7_kind_corrected_admin_only():
    """KindCorrectedPayloadV1 exige admin_actor_id + justification."""
    with pytest.raises(ValidationError):
        KindCorrectedPayloadV1(from_kind="anomaly", to_kind="action")

def test_IE7_bulk_export_csv_xlsx_pdf():
    """ExportedPayloadV1 accepte 3 formats."""
    for fmt in ("xlsx", "pdf", "csv"):
        payload = ExportedPayloadV1(export_format=fmt, items_count=10)
        assert payload.export_format == fmt
```

**Total** : 10 (validation) + 15 (rétention) + 15 (schemas) = **40 tests planifiés**.

---

## 15. Risques et mitigations

| Risque | Probabilité | Impact | Mitigation ADR-029 |
|---|---|---|---|
| Storage filesystem corruption | Faible | Élevé | IE1 backup ADR-026 + checksums + S3 V4.1+ |
| Validation manuelle abusée (admin valide sans vraie verif) | Moyen | Moyen | `validation_payload.verified_by` traçable + audit trail (`evidence_verified` event) |
| Magic bytes spoofing (false positive) | Faible | Moyen | Double-check libmagic + signatures hardcodées (§9 4 étapes) |
| Purge silencieuse en prod | Faible | Élevé | IE5 triple garde-fou (flag + dry-run + trace) + procédure phasée §12.2 |
| Évolution payload casse les events existants | Moyen | Élevé | IE7 schema_version + registry par version + co-existence v1/v2 (§11.5) |
| RGPD art. 17 droit à l'oubli non implémenté | Élevé si manqué | Très élevé | §13.3 endpoint anonymisation (préserve audit trail art. 30) |
| Purge supprime des preuves légales | Faible | Très élevé | IE3 compliance 5 ans + dry-run obligatoire avant purge réelle |
| MIME `python-magic` indisponible | Faible | Élevé | Double-check signatures hardcodées (§9 étape 4) sert de fallback |
| Performance purge mensuelle dégrade DB | Moyen | Moyen | Cron 1er du mois 2h UTC (off-peak) + index `idx_event_log_type` |
| Frontend n'affiche pas v2 schema correctement | Moyen | Moyen | Dispatcher frontend par `schema_version` documenté §11.5 |

---

## 16. Renvois ADR amont/aval

### 16.1 Renvois amont

- **ADR-022** Composantes score : pas d'impact direct. Les events `priority_recalculated` portent le nouveau score (cohérent ADR-022).
- **ADR-025** Architecture : ADR-029 enrichit §4.3 ADR-025 (squelette tables filles). **CHECK constraint `action_event_log.event_type` étendu de 15 → 16 valeurs** (extension aval acceptée par convention, alignement doctrine v0.3 — cf. §6.3). Indexes evidences/event_log compatibles §4.2 ADR-025 (20 indexes total).
- **ADR-026** Migration : I9 backup hors Git renforcé par IS10 ADR-027 + IE1 storage gitignored. Aucune evidence legacy à migrer (tables vides Sprint 13). Calendrier purge IE5 aligné cutover Mois 4.
- **ADR-027** Sécurité : IS10 (backup non commitable) + IS9 (correlation_id) + IS8 (logs sécu séparés) + IS6 (Bandit/Semgrep CI gate magic bytes). IE8 acte la séparation `security_audit_log` ↔ `action_event_log`.
- **ADR-028** Lifecycle : 16 event_types couvrent les 11 invariants IL1-IL11. IE4 matérialise IL5 (`merged_duplicate` ≠ recurrence). IE7 schemas Pydantic capturent IL11 (justification réouverture min 10 chars).

### 16.2 Renvois aval (post-ADR-029)

- **L7 Data Dictionary V4 + glossaire** : compilation finale Mois 1, intègre les 4 tables V4 (action_center_items + evidences + action_event_log + groupes) + 16 event_types + 6 closure_reasons + libellés FR.
- **L8 Plan suppression legacy Mois 5** : suppression conditionnelle des tables legacy après STOP GATE J+14 ADR-026.
- **L9 Prompt Claude Code Mois 2 backend** : démarrage implementation cible (ADR-025 + ADR-026 + ADR-027 + ADR-028 + ADR-029 = 5 ADR Mois 1 prêts à consommer).

### 16.3 Doctrine v0.3

ADR-029 consomme strictement la doctrine v0.3 (avenant L5). Aucune modification de la doctrine n'est requise. Si une évolution de closure_reasons ou rétention devenait nécessaire post-ADR-029, elle passerait par avenant v0.4 (politique §11 doctrine respectée).

---

## 17. Critères de validation finale ADR-029

### 17.1 9 invariants vérifiés

- [x] **IE1** Storage abstrait — §7 `EvidenceStorageBackend` + factory
- [x] **IE2** Validation manuelle obligatoire — §8.2 endpoint + `validation_payload`
- [x] **IE3** 3 catégories rétention — §10.1 `CATEGORY_RETENTION_DAYS`
- [x] **IE4** Matrice alignée doctrine v0.3 — §10.2 `merged_duplicate` ≠ `resolved_via_recurrence`
- [x] **IE5** Purge triple garde-fou — §12.1 feature flag + dry-run + trace
- [x] **IE6** `expires_at = verified_at + 90j` — §5.1 CHECK + §8.2 endpoint
- [x] **IE7** Schemas Pydantic versionnés — §11 + service `write_event`
- [x] **IE8** `security_audit_log` séparé strict — §6.2 + cohérent ADR-027
- [x] **IE9** Magic bytes MIME — §9 + cardinal Amine 2026-05-14

### 17.2 Cohérence cross-documents (Phase 0)

- [x] Cohérence ADR-025 (4/4 vérifications)
- [x] Cohérence ADR-026 (3/3 vérifications)
- [x] Cohérence ADR-027 (5/5 vérifications)
- [x] Cohérence ADR-028 (4/4 vérifications)
- [x] Cohérence doctrine v0.3 (4/4 vérifications)
- [x] Cohérence L1 (3/3 vérifications)
- [x] Cohérence maquettes M1-M5 (3/3 vérifications)
- [x] Sprint Phase 3.5 non perturbé (2/2 vérifications)

### 17.3 Conformité Q6-A

- [x] Aucun code Python/TypeScript modifié
- [x] Aucune table DB modifiée
- [x] Aucun script créé sur disque

---

## 18. Conséquences

### 18.1 Conséquences positives

| # | Conséquence | Mécanisme |
|---|---|---|
| 1 | **Audit trail défendable RGPD** | `action_event_log` séparé `security_audit_log` (IE8) + 8 articles CNIL référencés + matrice rétention par catégorie |
| 2 | **Evidence intègre & non spoofable** | Magic bytes MIME (IE9 cardinal Amine) + validation manuelle (IE2) + expiration 90 j (IE6) |
| 3 | **Purge auditée & réversible** | Triple garde-fou IE5 + dry-run obligatoire + correlation_id pour forensique |
| 4 | **Évolutivité schéma sans casse** | IE7 schema_version + registry + pattern v1 → v2 documenté + co-existence garantie |
| 5 | **Storage découplé** | IE1 ABC + factory, migration `fs://` → `s3://` V4.1+ sans refacto applicatif |
| 6 | **Conformité doctrine v0.3** | IE4 matrice alignée Q9-B / Q37-A+ — protection contre dérive silencieuse via rétention |
| 7 | **Cohérence trilogie data** | ADR-025 + ADR-028 + ADR-029 forment un manuel data complet pour Mois 2 backend |
| 8 | **Mois 1 série ADR complète** | 5 ADR (025/026/027/028/029) + 1 avenant doctrinal v0.3 = base exécutable Mois 2 |

### 18.2 Conséquences négatives

| # | Conséquence | Mitigation |
|---|---|---|
| 1 | **Coût implémentation Mois 2** | Storage abstract + 16 schemas Pydantic + magic bytes = ~5 jours/h (Mois 2) |
| 2 | **Validation manuelle = goulet UX** | Workflow validation différé (uploadée → vérifiée par admin sous 24-48h) — coût acceptable POC |
| 3 | **Dépendance `python-magic`** | Wheel binaire libmagic (pip-audit CVE veille) + double-check signatures fallback (§9 étape 4) |
| 4 | **Storage filesystem POC limité** | Backup ADR-026 + checksums + migration S3 V4.1+ sans refacto applicatif |

### 18.3 Conséquences neutres

| # | Conséquence | Justification |
|---|---|---|
| 1 | **Purge dry-run obligatoire en première activation** | Coût opérationnel marginal, gain sécurité majeur |
| 2 | **Anonymisation art. 17 (pas suppression)** | Préserve intégrité audit trail (art. 30) tout en respectant droit à l'oubli — interprétation CNIL 2023 |
| 3 | **Schemas Pydantic ajoutent overhead ~1ms/event** | Budget mutation ADR-025 < 150ms largement préservé |

---

## 19. Auto-évaluation QA ADR-029

### 19.1 9 invariants doctrinaux vérifiés (9/9 requis)

- [x] **IE1** Storage abstrait — §7 EvidenceStorageBackend + factory
- [x] **IE2** Validation manuelle obligatoire — §8.2 + validation_payload
- [x] **IE3** 3 catégories rétention — §10.1 CATEGORY_RETENTION_DAYS
- [x] **IE4** Matrice doctrine v0.3 — §10.2 merged_duplicate ≠ resolved_via_recurrence
- [x] **IE5** Purge triple garde-fou — §12.1 feature flag + dry-run + trace
- [x] **IE6** expires_at = verified_at + 90j — §5.1 + §8.2
- [x] **IE7** Schemas Pydantic versionnés — §11 schema_version
- [x] **IE8** security_audit_log séparé — §6.2 cohérent ADR-027
- [x] **IE9** Magic bytes MIME — §9 cardinal Amine

### 19.2 7 arbitrages Q40-Q46 documentés

- [x] Q40-D storage hybride fs/s3 (§7)
- [x] Q41-D validation manuelle + métadonnées (§8)
- [x] Q42-C+ 3 catégories alignées doctrine v0.3 (§10)
- [x] Q43-A+ APScheduler triple garde-fou (§12)
- [x] Q44-A+ PDF/JPG/PNG + magic bytes (§9)
- [x] Q45-B 10 MB max (§5.1 CHECK)
- [x] Q46-B+ schemas Pydantic versionnés (§11)

### 19.3 Matrice rétention RGPD

- [x] 16 event_types couverts
- [x] 3 catégories : compliance (7) + business (6) + system (3)
- [x] merged_duplicate = business 3 ans (Q9-B doublon technique)
- [x] resolved_via_recurrence = compliance 5 ans (Q9-B preuve indirecte)
- [x] 8 articles CNIL référencés

### 19.4 Schemas Pydantic

- [x] 16 schemas v1 documentés
- [x] schema_version cardinal dans chaque payload
- [x] Service write_event() avec validation Pydantic
- [x] Pattern d'évolution v1 → v2 documenté

### 19.5 Cohérence cross-documents (Phase 0 — 38/38)

- [x] ADR-025 — 4/4
- [x] ADR-026 — 3/3
- [x] ADR-027 — 5/5
- [x] ADR-028 — 4/4
- [x] Doctrine v0.3 — 4/4
- [x] L1 — 3/3
- [x] Maquettes M1-M5 — 3/3
- [x] Sprint Phase 3.5 — 2/2

### 19.6 Tests planifiés (40)

- [x] 10 tests validation evidence
- [x] 15 tests rétention
- [x] 15 tests schemas Pydantic

### 19.7 Conformité Q6-A

- [x] Aucun code Python/TypeScript modifié
- [x] Aucune table DB modifiée
- [x] Aucun script écrit sur disque

### 19.8 Storage abstrait IE1

- [x] ABC `EvidenceStorageBackend` + 3 méthodes (store/retrieve/delete) — §7.1
- [x] Factory `get_storage_backend()` + config env — §7.1 + §7.2
- [x] Path abstrait `fs://<org>/<id>` migrable `s3://` sans refacto — §7.3

### 19.9 Endpoints RGPD

- [x] Endpoint export art. 15 (`GET /api/users/me/data-export`) — §13.2
- [x] Endpoint suppression art. 17 (`DELETE /api/users/me/data` + anonymisation) — §13.3
- [x] `@org_scoped` + `@admin_only_with_fresh_token` sur endpoints sensibles — §8 + §13.3

### 19.10 Magic bytes IE9 (cardinal Amine)

- [x] Étape 1 libmagic `magic.from_buffer(content_bytes[:2048], mime=True)` — §9.1
- [x] Étape 2 whitelist `ACCEPTED_MIME_TYPES` (3 formats PDF/JPG/PNG) — §9.1
- [x] Étape 4 double-check signatures hardcodées + log mismatch `security_audit_log` — §9.1 + §9.2

**Total** : **48/48 critères ✓** — ADR-029 prêt pour acceptation.

---

## 20. Métadonnées

```yaml
adr_number: 029
title: Evidence + audit trail Centre d'Action V4
version: v1.0
status: Accepted
date: 2026-05-14
authors:
  - Amine (PROMEOS founder)
  - Claude (architecture co-pilot)
branch: claude/refonte-sol2
doctrine_version_ref: v0.3
related_adrs:
  - ADR-022
  - ADR-025
  - ADR-026
  - ADR-027
  - ADR-028
arbitrages_q40_q46:
  Q40: D    # storage hybride fs/s3 abstrait
  Q41: D    # validation manuelle + métadonnées + flag confiance
  Q42: C+   # 3 catégories rétention alignées doctrine v0.3
  Q43: A+   # APScheduler mensuel + feature flag + dry-run + trace
  Q44: A+   # PDF/JPG/PNG + magic bytes validation
  Q45: B    # 10 MB par evidence
  Q46: B+   # Pydantic schemas avec schema_version
invariants_evidence:
  IE1: "Storage abstrait fs://Mois2 · s3:// V4.1+"
  IE2: "Validation manuelle obligatoire + métadonnées + flag confiance"
  IE3: "3 catégories rétention RGPD (compliance 5y / business 3y / system 1y)"
  IE4: "Matrice alignée doctrine v0.3 (merged_duplicate vs resolved_via_recurrence)"
  IE5: "Purge feature flag + dry-run + trace"
  IE6: "expires_at = verified_at + 90j"
  IE7: "Schemas Pydantic typés avec schema_version"
  IE8: "security_audit_log séparé strict (90j) vs action_event_log (1-5 ans)"
  IE9: "Validation MIME par magic bytes (cardinal Amine 2026-05-14)"
retention_policy:
  compliance_days: 1825   # 5 ans
  business_days: 1095     # 3 ans
  system_days: 365        # 1 an
event_types: 16
schemas_pydantic_v1: 16
cnil_articles_referenced:
  - "5(1)(b)"
  - "5(1)(e)"
  - "5(2)"
  - "6"
  - "15"
  - "17"
  - "30"
  - "32"
tests_planned: 40
phase0_audit_score: "38/38"
auto_eval_score: "48/48"
month: 1
adr_position_in_month: "5/5 (last ADR Month 1)"
next_adr: null
next_deliverables:
  - L7 Data Dictionary V4 + glossaire
  - L8 Plan suppression legacy Mois 5
  - L9 Prompt Claude Code Mois 2 backend
```

---

**Statut final** : `Accepted` 2026-05-14 — ADR-029 devient **le manuel des preuves et de la traçabilité** Centre d'Action V4 pour Mois 2-6 + V4.1.

**Mois 1 série ADR complète** : ADR-025 (32/32) + ADR-026 (36/36) + ADR-027 (50/50) + ADR-028 (53/53) + ADR-029 (48/48) + 1 avenant doctrinal v0.3.
