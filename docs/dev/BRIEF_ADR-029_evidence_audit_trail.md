# BRIEF ADR-029 · Evidence + audit trail Centre d'Action V4

> **Statut** : `Proposed` — à acter par Amine avant production L6
> **Version** : v0.1
> **Date** : 2026-05-14
> **Branche cible** : `claude/refonte-sol2`
> **Doctrine source** : `docs/doctrine/doctrine_v4_classement_priorisation.md` **v0.3** (Accepted)
> **ADR amont** : ADR-022 · ADR-025 · ADR-026 · ADR-027 · ADR-028
> **Auteurs** : Amine + Claude (cadrage session 2026-05-14)

---

## 0. TL;DR exécutif

**ADR-029 = manuel des preuves et de la traçabilité.** Fige le schéma des tables `evidences` + `action_event_log`, la politique de rétention RGPD par catégorie, la validation des evidences, et les schemas Pydantic versionnés par event_type.

C'est le **dernier ADR du Mois 1** — il complète la trilogie data (ADR-025 architecture + ADR-028 lifecycle + ADR-029 preuves) et finalise les prérequis cardinaux pour Mois 2 backend.

**9 invariants Evidence/Event log non négociables (IE1-IE9)** :

| # | Invariant |
|---|---|
| IE1 | Storage evidence **abstrait** (`fs://` Mois 2 · `s3://` V4.1+) — couplage minimisé |
| IE2 | Validation evidence **manuelle obligatoire** + métadonnées extraites + flag confiance |
| IE3 | Rétention différenciée par catégorie : **compliance 5 ans · business 3 ans · system 1 an** |
| IE4 | Matrice rétention **alignée doctrine v0.3** : `merged_duplicate` (3 ans) ≠ `resolved_via_recurrence` (5 ans) |
| IE5 | Aucune purge silencieuse · **feature flag + dry-run + trace** `security_audit_log` |
| IE6 | `expires_at = verified_at + 90 jours` pour toute evidence vérifiée |
| IE7 | Tous payload events validés par schema **Pydantic typé avec `schema_version`** |
| IE8 | `security_audit_log` (90j) **séparé strict** de `action_event_log` (1-5 ans) |
| IE9 | Validation MIME par **signature fichier** (magic bytes), pas par header client (anti-spoofing) |

**7 arbitrages techniques Q40-Q46 actés** :

| Q | Décision finale |
|---|---|
| Q40-D | Storage hybride filesystem + path abstrait (`fs://...` Mois 2, `s3://...` V4.1+) |
| Q41-D | Validation manuelle obligatoire + métadonnées extraites + flag confiance |
| Q42-C+ | 3 catégories rétention RGPD alignées doctrine v0.3 |
| Q43-A+ | APScheduler mensuel + feature flag + dry-run + trace sécurité |
| Q44-A+ | PDF/JPG/PNG uniquement + validation MIME par magic bytes |
| Q45-B | 10 MB max par evidence |
| Q46-B+ | Schemas Pydantic typés par event_type avec `schema_version` |

**Matrice rétention RGPD** : 16 event_types × 3 catégories (compliance 7 · business 6 · system 3).

---

## 1. Périmètre et hors-scope

### 1.1 Périmètre ADR-029

L'ADR couvre :

- Schéma DB détaillé `evidences` (cohérent ADR-025 §2.3)
- Schéma DB détaillé `action_event_log` (cohérent ADR-025 §2.3)
- Storage abstrait `EvidenceStorage` (Q40-D)
- Validation evidence manuelle + métadonnées (Q41-D)
- Validation MIME par magic bytes (Q44-A+ raffinement Amine)
- Matrice 16 event_types × 3 catégories de rétention RGPD
- Schemas Pydantic versionnés (`schema_version`) par event_type
- Purge mensuelle APScheduler avec triple garde-fou
- Articles CNIL référencés (art. 5(1)(b), 5(1)(e), 5(2), 6, 15, 17, 30)
- Procédure d'export RGPD article 15 (droit d'accès user)
- Procédure de suppression RGPD article 17 (droit à l'oubli)
- 40+ tests planifiés (validation + rétention + schemas + magic bytes)

### 1.2 Hors-scope ADR-029

- **ADR-025** : schéma global tables filles (déjà acté)
- **ADR-026** : migration data + backup (déjà acté)
- **ADR-027** : sécurité org-scoping + `security_audit_log` (déjà acté)
- **ADR-028** : lifecycle state machine (déjà acté)
- **OCR automatique** : pas en MVP (Q41-D rejette Q41-B), réservé V4.1
- **Signatures PKI cryptographiques** : pas en MVP (Q41-A rejeté), réservé V4.1+ si exigence juridique
- **Storage S3** : implémentation Mois 2 = filesystem, S3 V4.1+ via abstraction
- **Notifications expiration evidence** : couvert par notifications service hors-ADR

---

## 2. Schéma DB `evidences` détaillé

### 2.1 Table `evidences`

```sql
CREATE TABLE evidences (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id     UUID NOT NULL,                      -- IS1 org_scoping
    action_item_id      UUID NOT NULL REFERENCES action_center_items(id),

    -- Métadonnées fichier
    mime_type           VARCHAR(50) NOT NULL,               -- IE9 : validé par magic bytes
    file_size_bytes     INTEGER NOT NULL CHECK (file_size_bytes <= 10485760),  -- 10 MB
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

### 2.2 Structure `validation_payload` JSONB

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

---

## 3. Schéma DB `action_event_log` détaillé

### 3.1 Table `action_event_log`

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
            -- 16 event_types ADR-029 v1
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

### 3.2 Différenciation `action_event_log` vs `security_audit_log` (IE8)

| Table | Rétention | Sémantique | Cible RGPD |
|---|---|---|---|
| `action_event_log` | 1-5 ans (IE3) | Audit trail **métier** : transitions, blockers, evidences | art. 30 registre traitements |
| `security_audit_log` | 90 jours (ADR-027) | Events **sécurité** : auth, IDOR, privilege escalation | art. 32 sécurité |

**Aucun mélange.** Sémantique stricte.

---

## 4. Storage evidence abstrait (Q40-D · IE1)

### 4.1 Service `EvidenceStorage`

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
    # ...


# Factory
def get_storage_backend() -> EvidenceStorageBackend:
    backend = config.EVIDENCE_STORAGE_BACKEND
    if backend == "filesystem":
        return FilesystemBackend()
    elif backend == "s3":
        return S3Backend()
    raise ConfigurationError(f"Unknown storage backend: {backend}")
```

### 4.2 Configuration env

```bash
# .env.example
EVIDENCE_STORAGE_BACKEND=filesystem          # Mois 2-6
EVIDENCE_FS_ROOT=/data/promeos/evidences      # gitignored, hors Git (IS10)
EVIDENCE_MAX_SIZE_BYTES=10485760              # 10 MB
```

`.gitignore` :

```
/data/promeos/evidences/       # IE1 + IS10 ADR-027
```

---

## 5. Validation evidence (Q41-D · IE2 · IE6)

### 5.1 Endpoint upload

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
    """
    content_bytes = await file.read()

    # IE9 : validation MIME par signature
    real_mime = validate_evidence_mime(content_bytes, file.content_type)

    # Taille (IE9 + check explicite)
    if len(content_bytes) > 10 * 1024 * 1024:
        raise HTTPException(413, "Evidence too large (max 10 MB)")

    # Storage abstrait (IE1)
    evidence_id = uuid4()
    storage_uri = storage.store(evidence_id, request.state.organisation_id, content_bytes)

    # Extraction métadonnées (IE2)
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

    # Event log (IE7)
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

### 5.2 Endpoint vérification (IE2 + IE6)

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
        raise HTTPException(404)  # IS3

    if evidence.verified_at:
        raise HTTPException(409, {
            "code": "EVIDENCE_ALREADY_VERIFIED",
            "message": "This evidence is already verified",
            "hint": "Re-upload a new evidence if needed",
        })

    # IE2 + IE6
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

    # Event log
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

---

## 6. Validation MIME par magic bytes (Q44-A+ · IE9)

### 6.1 Service `validate_evidence_mime`

```python
# backend/services/evidence/mime_validator.py

import magic  # python-magic

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
    # Étape 1
    real_mime = magic.from_buffer(content_bytes[:2048], mime=True)

    # Étape 2
    if real_mime not in ACCEPTED_MIME_TYPES:
        raise InvalidEvidenceFormatError(
            code="EVIDENCE_MIME_NOT_ACCEPTED",
            message=f"File signature indicates {real_mime}, not accepted",
            hint=f"Accepted: {ACCEPTED_MIME_TYPES}",
            detected_mime=real_mime,
        )

    # Étape 3 : log mismatch
    if client_declared_mime and client_declared_mime != real_mime:
        log_security_event(
            event_type="evidence.mime_mismatch",
            severity="warning",
            declared=client_declared_mime,
            detected=real_mime,
        )

    # Étape 4 : double-check magic bytes
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

### 6.2 Bénéfices

| Attaque | Mitigation |
|---|---|
| `.exe` renommé `.pdf` avec Content-Type forgé | Magic bytes détectent EXE → 422 Unprocessable Entity |
| PDF/HTML polyglotte (PDF qui contient JS) | Magic bytes valident PDF, mais libmagic peut détecter polyglottes |
| Header HTTP `Content-Type` spoofed | Détection mismatch loggué dans `security_audit_log` |

---

## 7. Matrice rétention RGPD (Q42-C+ · IE3 · IE4)

### 7.1 3 catégories de rétention

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

### 7.2 Mapping event_type → catégorie (16 events)

```python
EVENT_TYPE_CATEGORY: dict[str, RetentionCategory] = {
    # Audit trail métier (3 ans)
    "created": RetentionCategory.BUSINESS,
    "state_changed": RetentionCategory.BUSINESS,
    "owner_changed": RetentionCategory.BUSINESS,
    "priority_changed": RetentionCategory.BUSINESS,
    "blocker_added": RetentionCategory.BUSINESS,
    "blocker_removed": RetentionCategory.BUSINESS,
    "closed_via_merged_duplicate": RetentionCategory.BUSINESS,  # Q9-B fusion technique

    # Compliance (5 ans)
    "evidence_added": RetentionCategory.COMPLIANCE,
    "evidence_verified": RetentionCategory.COMPLIANCE,
    "closed_with_evidence": RetentionCategory.COMPLIANCE,
    "closed_via_resolved_via_recurrence": RetentionCategory.COMPLIANCE,  # Q9-B preuve indirecte
    "reopened": RetentionCategory.COMPLIANCE,           # IL3 admin sensible
    "kind_corrected": RetentionCategory.COMPLIANCE,     # IS5 admin sensible

    # System (1 an)
    "bulk_updated": RetentionCategory.SYSTEM,
    "exported": RetentionCategory.SYSTEM,
    "priority_recalculated": RetentionCategory.SYSTEM,
}
```

### 7.3 Justification RGPD article par article

| Event category | Article CNIL | Justification |
|---|---|---|
| Compliance 5 ans | art. 30 + art. 5(2) | Registre traitements + intégrité preuves |
| Business 3 ans | art. 5(1)(e) | Limitation durée conservation proportionnée |
| System 1 an | art. 5(1)(b) + 5(1)(e) | Finalité maintenance + durée stricte |

---

## 8. Schemas Pydantic versionnés (Q46-B+ · IE7)

### 8.1 Structure générale

```python
# backend/schemas/event_payloads/__init__.py

from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel

# Base avec schema_version cardinal
class EventPayloadBase(BaseModel):
    schema_version: Literal["v1"] = "v1"


# 16 schémas v1
class CreatedPayloadV1(EventPayloadBase):
    initial_state: str
    initial_kind: str
    triggered_by: str  # "manual" | "automatic_detection" | "regulatory_applicability_service"


class StateChangedPayloadV1(EventPayloadBase):
    from_state: str
    to_state: str
    closure_reason: Optional[str] = None
    justification: Optional[str] = None
    auto_closed_by_group_id: Optional[UUID] = None


class OwnerChangedPayloadV1(EventPayloadBase):
    from_owner_id: Optional[UUID]
    to_owner_id: UUID
    reason: Optional[str] = None


class PriorityChangedPayloadV1(EventPayloadBase):
    from_priority: str
    to_priority: str
    from_score: float
    to_score: float
    recalc_triggered_by: str  # 12 events doctrine v0.3


class BlockerAddedPayloadV1(EventPayloadBase):
    blocker_type: str
    justification: str
    expected_resolution_at: Optional[str]


class BlockerRemovedPayloadV1(EventPayloadBase):
    blocker_id: UUID
    resolution_note: Optional[str]


class EvidenceAddedPayloadV1(EventPayloadBase):
    evidence_id: UUID
    mime_type: str
    size_bytes: int
    storage_uri: str


class EvidenceVerifiedPayloadV1(EventPayloadBase):
    evidence_id: UUID
    verified_at: str
    expires_at: str
    confidence_flag: Literal["high", "medium", "low"]


class ClosedWithEvidencePayloadV1(EventPayloadBase):
    evidence_id: UUID
    closure_reason: Literal["resolved"]


class ClosedViaMergedDuplicatePayloadV1(EventPayloadBase):
    duplicate_group_id: UUID
    primary_item_id: UUID


class ClosedViaResolvedViaRecurrencePayloadV1(EventPayloadBase):
    recurrence_group_id: UUID
    group_resolution_date: str
    group_resolution_justification: Optional[str]


class ReopenedPayloadV1(EventPayloadBase):
    previous_closure_reason: str
    justification: str  # IL11 obligatoire min 10 chars
    admin_actor_id: UUID


class BulkUpdatedPayloadV1(EventPayloadBase):
    field_updated: str
    items_count: int
    correlation_id: UUID


class ExportedPayloadV1(EventPayloadBase):
    export_format: str  # "xlsx" | "pdf" | "csv"
    items_count: int


class KindCorrectedPayloadV1(EventPayloadBase):
    from_kind: str
    to_kind: str
    admin_actor_id: UUID
    justification: str


class PriorityRecalculatedPayloadV1(EventPayloadBase):
    trigger_event: str  # 12 events doctrine v0.3
    new_score: float
    new_bracket: str


# Schema registry
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

### 8.2 Service `write_event`

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
        event_payload=validated.model_dump(),  # contient schema_version
        schema_version=schema_version,
        correlation_id=correlation_id,
        source_route=actor.request_route,
    )
    db.add(event)
    return event
```

### 8.3 Évolution future (V4.1+)

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

---

## 9. Purge mensuelle (Q43-A+ · IE5)

### 9.1 Service `monthly_retention_purge`

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
    if not config.RETENTION_PURGE_ENABLED:
        log_security_event(
            event_type="retention.purge.skipped",
            reason="feature_flag_disabled"
        )
        return

    correlation_id = uuid4()
    now = datetime.utcnow()
    dry_run = config.RETENTION_PURGE_DRY_RUN_FIRST

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

    # Trace IE5
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

### 9.2 Procédure activation prod

```
Phase 1 (Mois 2-3)  : RETENTION_PURGE_ENABLED=False                    · Pas de purge
Phase 2 (Mois 4 J-7): RETENTION_PURGE_ENABLED=True                     · Activation
                      RETENTION_PURGE_DRY_RUN_FIRST=True                · Dry-run staging
                      Validation rapport counts                          · Si OK → Phase 3
Phase 3 (Mois 4 J+1): RETENTION_PURGE_DRY_RUN_FIRST=False               · Purge réelle
Phase 4 (Mois 5+)   : Régime cruise · purge mensuelle automatique
```

---

## 10. Articles CNIL référencés

| Article | Application |
|---|---|
| **art. 5(1)(b)** Finalité spécifiée | 3 catégories rétention = 3 finalités distinctes |
| **art. 5(1)(e)** Limitation conservation | Rétention proportionnée par catégorie |
| **art. 5(2)** Intégrité confidentialité | Magic bytes + validation manuelle |
| **art. 6** Base légale | Obligation légale (DT/BACS) + intérêt légitime |
| **art. 15** Droit d'accès | Endpoint export user-triggered |
| **art. 17** Droit à l'oubli | Endpoint suppression + storage.delete() |
| **art. 30** Registre traitements | Tous events tracés + schema_version |
| **art. 32** Sécurité traitement | security_audit_log séparé + IS7/IS8 |

### 10.1 Endpoint export RGPD (art. 15)

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
        action_item_id=None,  # event de niveau org, pas item
        event_type="exported",
        actor=build_actor(request),
        payload={"export_format": "json", "items_count": len(events), "schema_version": "v1"}
    )

    return {"events": [e.to_dict() for e in events]}
```

### 10.2 Endpoint suppression RGPD (art. 17)

```python
@router.delete("/api/users/me/data")
@admin_only_with_fresh_token  # Sensible
async def delete_user_data(request: Request):
    """
    RGPD art. 17 : droit à l'oubli.
    Anonymise (pas supprime) les events du user.
    """
    user_id = request.state.user_id
    db.query(ActionEventLog).filter(
        ActionEventLog.actor_id == user_id,
    ).update({
        "actor_id": None,
        "actor_name": "[ANONYMIZED]",
        "actor_role": None,
    })
    # Evidences uploaded_by aussi
    db.query(Evidence).filter(Evidence.uploaded_by == user_id).update({
        "uploaded_by": None,
    })
    db.commit()
```

---

## 11. Tests planifiés (40+)

### 11.1 Tests validation evidence (10)

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
```

### 11.2 Tests rétention (15)

```python
def test_IE3_compliance_5y_business_3y_system_1y():
    assert CATEGORY_RETENTION_DAYS[RetentionCategory.COMPLIANCE] == 1825
    assert CATEGORY_RETENTION_DAYS[RetentionCategory.BUSINESS] == 1095
    assert CATEGORY_RETENTION_DAYS[RetentionCategory.SYSTEM] == 365

def test_IE4_merged_duplicate_is_business_3y():
    assert EVENT_TYPE_CATEGORY["closed_via_merged_duplicate"] == RetentionCategory.BUSINESS

def test_IE4_resolved_via_recurrence_is_compliance_5y():
    assert EVENT_TYPE_CATEGORY["closed_via_resolved_via_recurrence"] == RetentionCategory.COMPLIANCE

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
```

### 11.3 Tests schemas Pydantic (15)

```python
@pytest.mark.parametrize("event_type", list(EVENT_PAYLOAD_SCHEMAS.keys()))
def test_IE7_all_event_types_have_schema(event_type):
    """16 event_types ont chacun un schéma v1."""
    schema = EVENT_PAYLOAD_SCHEMAS.get(event_type)
    assert schema is not None
    assert schema.__fields__["schema_version"].default == "v1"

def test_IE7_write_event_rejects_invalid_payload():
    with pytest.raises(InvalidEventPayloadError):
        write_event(
            event_type="state_changed",
            payload_dict={"from_state": "invalid_state"},  # missing to_state
            ...
        )

def test_IE7_schema_version_persisted():
    write_event(event_type="state_changed", payload_dict={...}, schema_version="v1")
    event = db.query(ActionEventLog).first()
    assert event.schema_version == "v1"
    assert event.event_payload["schema_version"] == "v1"
```

---

## 12. Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Storage filesystem corruption | Faible | Élevé | IE1 backup ADR-026 + checksums + S3 V4.1+ |
| Validation manuelle abusée (admin valide sans vraie verif) | Moyen | Moyen | `validation_payload.verified_by` traçable + audit trail |
| Magic bytes spoofing (false positive) | Faible | Moyen | Double-check libmagic + manual signatures |
| Purge silencieuse en prod | Faible | Élevé | IE5 triple garde-fou (flag + dry-run + trace) |
| Évolution payload casse les events existants | Moyen | Élevé | IE7 schema_version + registry par version |
| RGPD art. 17 droit à l'oubli non implémenté | Élevé si manqué | Très élevé | §10.2 endpoint anonymisation |
| Purge supprime des preuves légales | Faible | Très élevé | IE3 compliance 5 ans + dry-run obligatoire |

---

## 13. Renvois ADR amont/aval

- **ADR-022** : composantes score · pas d'impact direct
- **ADR-025** : schéma tables filles (`evidences` + `action_event_log`) — ADR-029 détaille payload + rétention
- **ADR-026** : I9 backup non commitable · cohérent IS10 ADR-027
- **ADR-027** : IS10 + IS8 logs sécu · IE8 séparation stricte
- **ADR-028** : IL8/IL9 events lifecycle → ADR-029 figé le schéma payload
- **Doctrine v0.3 §7.1** : 6 closure_reasons → ADR-029 mappe 16 event_types

---

## 14. Critères de validation finale ADR-029

### 14.1 9 invariants vérifiés

- [ ] **IE1** Storage abstrait — §4 `EvidenceStorageBackend` + factory
- [ ] **IE2** Validation manuelle obligatoire — §5.2 endpoint + `validation_payload`
- [ ] **IE3** 3 catégories rétention — §7.1 `CATEGORY_RETENTION_DAYS`
- [ ] **IE4** Matrice alignée doctrine v0.3 — §7.2 `merged_duplicate` ≠ `resolved_via_recurrence`
- [ ] **IE5** Purge triple garde-fou — §9.1 feature flag + dry-run + trace
- [ ] **IE6** `expires_at = verified_at + 90j` — §2.1 CHECK + §5.2 endpoint
- [ ] **IE7** Schemas Pydantic versionnés — §8 + service `write_event`
- [ ] **IE8** `security_audit_log` séparé strict — §3.2 + cohérent ADR-027
- [ ] **IE9** Magic bytes MIME — §6 + cardinal Amine 2026-05-14

### 14.2 Cohérence cross-documents

- [ ] Cohérence ADR-025 (schéma tables filles)
- [ ] Cohérence ADR-026 (backup non commitable + IE1 fs://)
- [ ] Cohérence ADR-027 (IS10 backup, IS8 logs sépares, IS9 correlation_id)
- [ ] Cohérence ADR-028 (16 event_types + IL8/IL9 + closure_reasons révisés)
- [ ] Cohérence doctrine v0.3 (closure_reasons + libellés FR)
- [ ] Cohérence L1 (action_event_log v0 → V4 cohérent)
- [ ] Cohérence maquettes M1-M5 (drawer evidences + journal events)

### 14.3 Conformité Q6-A

- [ ] Aucun code Python/TypeScript modifié
- [ ] Aucune table DB modifiée
- [ ] Aucun script créé sur disque

---

## 15. Métadonnées ADR

```yaml
adr_number: 029
title: Evidence + audit trail Centre d'Action V4
version: v0.1
status: Proposed
date: 2026-05-14
authors:
  - Amine (PROMEOS founder)
  - Claude (architecture co-pilot)
doctrine_version_ref: v0.3
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
  IE3: "3 catégories rétention RGPD"
  IE4: "Matrice alignée doctrine v0.3 (merged_duplicate vs resolved_via_recurrence)"
  IE5: "Purge feature flag + dry-run + trace"
  IE6: "expires_at = verified_at + 90j"
  IE7: "Schemas Pydantic typés avec schema_version"
  IE8: "security_audit_log séparé strict (90j) vs action_event_log (1-5 ans)"
  IE9: "Validation MIME par magic bytes (cardinal Amine)"
retention_policy:
  compliance: 1825   # 5 ans
  business: 1095     # 3 ans
  system: 365        # 1 an
event_types: 16
schemas_pydantic_v1: 16
cnil_articles_referenced: ["5(1)(b)", "5(1)(e)", "5(2)", "6", "15", "17", "30", "32"]
tests_planned: 40
next_adr: null  # Dernier ADR Mois 1
```

---

**Statut** : `Proposed`. À acter par Amine avant L6 production.

Une fois acté, ADR-029 devient **le manuel des preuves et de la traçabilité** pour Mois 2-6 + V4.1.
