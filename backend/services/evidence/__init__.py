"""
PROMEOS V4 · Evidence storage + validation (ADR-029).

Scaffold Sprint M2-1. Implémentation Sprint M2-6.

Invariants applicables (cf. ADR-029 §3) :
- IE1 : storage abstrait `EvidenceStorageBackend` ABC (`fs://` Mois 2 · `s3://` V4.1+)
- IE2 : validation evidence manuelle obligatoire + métadonnées + flag confiance
- IE6 : `expires_at = verified_at + 90 jours` (DB CHECK + service)
- 🛡️ IE9 : validation MIME par magic bytes (cardinal Amine — anti-spoofing 4 lignes
            défense : libmagic + whitelist + log mismatch + double-check signatures)

Modules planifiés Sprint M2-6 :
- storage.py : `EvidenceStorageBackend` ABC + `FilesystemBackend` + factory
- mime_validator.py : `validate_evidence_mime()` (python-magic + signatures)
- metadata_extractor.py : `extract_pdf_metadata()` + `extract_image_metadata()`

Source : docs/dev/L6_ADR-029_evidence_audit_trail.md (commit 15711df4 · 48/48 ✓).
"""
