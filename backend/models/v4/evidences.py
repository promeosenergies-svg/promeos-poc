"""Evidence — preuves uploadées V4 (ADR-029 §2.1 + L7 §2.3).

🛡️ D2 SUPERSESSION ADR-025 §4.3 → ADR-029 §2.1 autoritatif :
- PAS de colonne `status` enum
- `file_size_bytes` INTEGER + CHECK ≤ 10485760 (Q45-B 10 MB)
- `mime_type` VARCHAR(50) + CHECK whitelist 3 MIMEs
- CHECK `chk_evidence_expires_90d` (IE6)
- Sémantique "status" portée par verified_at + expires_at (verified_consistency)

Invariants applicables :
- IS1 : organisation_id
- IE1 : storage_uri abstrait `fs://` Mois 2 / `s3://` V4.1+
- IE2 : validation manuelle obligatoire (verified_at + verified_by + validation_payload)
- IE6 : expires_at = verified_at + 90 jours (CHECK PG · enforced service en SQLite)
- IE9 : magic bytes MIME validation côté service (Sprint M2-6) — CHECK whitelist DB

Note SQLite : `INTERVAL '90 days'` est PostgreSQL-only. SQLite ignore silently
le CHECK chk_evidence_expires_90d. La règle 90j est aussi enforced côté service
Python (Sprint M2-6 verify_evidence endpoint) — double défense.
"""

from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from backend.models.base import Base


class Evidence(Base):
    """Preuve uploadée (PDF/JPG/PNG · 10 MB max · expiration 90j post-vérification)."""

    __tablename__ = "evidences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organisation_id = Column(UUID(as_uuid=True), nullable=False)  # IS1
    action_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("action_center_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Métadonnées fichier (D2 — ADR-029 §2.1)
    mime_type = Column(String(50), nullable=False)  # IE9 magic bytes validated (Sprint M2-6)
    file_size_bytes = Column(Integer, nullable=False)  # CHECK ≤ 10485760
    storage_uri = Column(Text, nullable=False)  # IE1 : "fs://..." ou "s3://..."
    original_filename = Column(String(255))  # nom client (informatif)

    # Validation (IE2 + IE6)
    verified_at = Column(DateTime(timezone=True))  # NULL si non vérifié
    verified_by = Column(UUID(as_uuid=True))  # FK virtual users
    expires_at = Column(DateTime(timezone=True))  # IE6 : verified_at + 90j
    validation_payload = Column(JSON)  # IE2 : metadata + verifier_role + confidence_flag

    # Métadonnées
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    uploaded_by = Column(UUID(as_uuid=True), nullable=False)
    description = Column(Text)

    __table_args__ = (
        # Q45-B : 10 MB max
        CheckConstraint(
            "file_size_bytes > 0 AND file_size_bytes <= 10485760",
            name="chk_evidence_size_max_10mb",
        ),
        # IE9 whitelist 3 MIMEs (validation magic bytes côté service Sprint M2-6)
        CheckConstraint(
            "mime_type IN ('application/pdf', 'image/jpeg', 'image/png')",
            name="chk_evidence_mime_whitelist",
        ),
        # IE2 : verified_at NULL ⇔ verified_by NULL ⇔ expires_at NULL
        CheckConstraint(
            "(verified_at IS NULL AND verified_by IS NULL AND expires_at IS NULL)"
            " OR (verified_at IS NOT NULL AND verified_by IS NOT NULL AND expires_at IS NOT NULL)",
            name="chk_evidence_verified_consistency",
        ),
        # IE6 : 90 jours strict (PG-only ; SQLite ignore + service enforce)
        CheckConstraint(
            "expires_at IS NULL OR expires_at = verified_at + INTERVAL '90 days'",
            name="chk_evidence_expires_90d",
        ),
        # ─── Indexes (cohérent ADR-025 §4.2 — 3 indexes pour cette table) ───
        Index("idx_evidences_org_item", "organisation_id", "action_item_id"),
        Index(
            "idx_evidences_verified",
            "verified_at",
            sqlite_where=text("verified_at IS NOT NULL"),
            postgresql_where=text("verified_at IS NOT NULL"),
        ),
        Index(
            "idx_evidences_expiring",
            "expires_at",
            sqlite_where=text("expires_at IS NOT NULL"),
            postgresql_where=text("expires_at IS NOT NULL"),
        ),
    )
