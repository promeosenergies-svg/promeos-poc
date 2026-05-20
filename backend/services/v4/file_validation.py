"""M2-4.4 — Validation minimale des fichiers uploadés (evidences PDF/JPG/PNG).

Différé M2-6 (documenté SECURITY.md §5.4) : formats DOCX/XLSX/ZIP/CSV,
scan antivirus (ClamAV), chiffrement at-rest, backend de stockage S3.
"""

import re

from fastapi import HTTPException, status

# Signature binaire (magic bytes) attendue par Content-Type déclaré.
_MAGIC_BYTES: dict[str, bytes] = {
    "application/pdf": b"%PDF-",
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}

MAX_EVIDENCE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB (cohérent chk_evidence_size_max_10mb)

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]")


def validate_file_upload(
    content: bytes,
    declared_content_type: str,
    declared_filename: str,
) -> str:
    """Valide un fichier uploadé. Retourne le nom de fichier assaini.

    Lève :
    - 413 si la taille dépasse 10 MB ;
    - 415 si le Content-Type est hors whitelist OU si les magic bytes ne
      correspondent pas au type déclaré (anti-spoofing MIME) ;
    - 400 si le nom de fichier est invalide après assainissement.
    """
    if len(content) > MAX_EVIDENCE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"File exceeds {MAX_EVIDENCE_SIZE_BYTES // 1024 // 1024} MB",
                "hint": "Compress or split the file before upload",
            },
        )

    expected_magic = _MAGIC_BYTES.get(declared_content_type)
    if expected_magic is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": f"Content type {declared_content_type!r} not allowed",
                "hint": "Allowed: application/pdf, image/jpeg, image/png",
            },
        )

    if not content.startswith(expected_magic):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "MAGIC_BYTES_MISMATCH",
                "message": "File content does not match the declared Content-Type",
                "hint": "Re-export the file or verify it is not corrupted",
            },
        )

    sanitized = _SAFE_FILENAME_RE.sub("_", declared_filename)
    if not sanitized or sanitized.startswith(".") or "/" in sanitized or "\\" in sanitized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILENAME",
                "message": "Filename contains invalid characters",
                "hint": "Use alphanumeric characters, dashes and underscores only",
            },
        )

    return sanitized
