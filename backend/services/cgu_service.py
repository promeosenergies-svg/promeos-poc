"""
PROMEOS — CGU service (Sprint C-8 Phase 8.1).

Source unique vérité versions CGU acceptables — fix dette
D-Sprint-C7-CGU-Referentiel-Central-001 P1 reportée Phase 7.7 → Sprint C-8.

Référentiel central : `backend/config/cgu_referentiel.yaml`.
Cohérent ADR-019 PATCH endpoints RGPD + CNIL article 7 (preuve d'origine forte).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

_CGU_YAML_PATH = Path(__file__).resolve().parent.parent / "config" / "cgu_referentiel.yaml"


@lru_cache(maxsize=1)
def _load_cgu_referentiel() -> dict:
    """Charge le référentiel CGU YAML (cache LRU pour performance)."""
    if not _CGU_YAML_PATH.exists():
        raise RuntimeError(f"CGU referentiel YAML introuvable : {_CGU_YAML_PATH}")
    with _CGU_YAML_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def reload_cgu_referentiel(*, admin_token: Optional[str] = None) -> dict:
    """Force le rechargement du référentiel (tests + admin runtime updates).

    Sprint C-8 Phase 8.4 fix D-Audit-C8-CGU-Cache-Reload-Auth-004 P1 SEC :
    helper INTERNE — caller endpoint admin DOIT vérifier role ADMIN avant appel.
    Le paramètre `admin_token` est documentaire (le caller route doit valider).

    Anti-pattern à proscrire : exposer cet endpoint sans guard `require_role(ADMIN)`
    permettrait à un attaquant de vider le cache + recharger un YAML substitué
    (path traversal si le path n'est pas hardcodé `_CGU_YAML_PATH`).
    """
    _load_cgu_referentiel.cache_clear()
    return _load_cgu_referentiel()


def get_current_cgu_version() -> str:
    """Retourne la version CGU avec statut='actuel' (cardinal CNIL).

    Raises:
        RuntimeError si aucune version 'actuel' trouvée dans le référentiel.
    """
    config = _load_cgu_referentiel()
    for v in config.get("versions", []):
        if v.get("statut") == "actuel":
            return v["version"]
    raise RuntimeError("Aucune version CGU avec statut='actuel' trouvée dans cgu_referentiel.yaml")


def is_valid_cgu_version(version: Optional[str], *, allow_archive: bool = False) -> bool:
    """True si `version` correspond à une version CGU acceptable pour PATCH consentement runtime.

    Cardinal validation Phase 7.3 PATCH endpoints RGPD : empêche stockage AuditLog
    avec version arbitraire (CNIL article 7 preuve d'origine forte = version vérifiable).

    Sprint C-8 Phase 8.4 fix D-Audit-C8-CGU-Archives-Accepted-002 P0 SEC :
    par défaut, n'accepte QUE les versions `statut='actuel'` (cardinal CNIL —
    consentement courant uniquement). `allow_archive=True` réservé aux endpoints
    admin/audit historique séparés (lookup AuditLog passé).

    Avant fix : versions `statut='archive'` étaient acceptées (notamment 2.0/2.1.0
    chronologiquement POSTÉRIEURES à 1.0 actuel) → preuve CNIL formellement invalide.

    None ou empty string → False (rejet — cgu_version doit être explicite).
    """
    if not version:
        return False
    config = _load_cgu_referentiel()
    for v in config.get("versions", []):
        if v.get("version") != version:
            continue
        # Phase 8.4 cardinal : runtime PATCH n'accepte que statut='actuel'
        if allow_archive:
            return True
        return v.get("statut") == "actuel"
    return False


def is_known_cgu_version(version: Optional[str]) -> bool:
    """True si `version` est connue (actuel OU archive) — pour audit historique.

    Sprint C-8 Phase 8.4 : helper séparé pour lookup AuditLog passé (vs validation
    runtime PATCH `is_valid_cgu_version`).
    """
    return is_valid_cgu_version(version, allow_archive=True)


def list_active_cgu_versions() -> list[dict]:
    """Liste toutes les versions CGU connues (actuel + archives) — pour endpoint admin."""
    config = _load_cgu_referentiel()
    return list(config.get("versions", []))


_CGU_PDF_ALLOWED_ROOT = Path(__file__).resolve().parent.parent.parent / "docs" / "cgu"
"""Phase D-3 Tier 2 SEC-1 — root unique autorisé pour les PDFs CGU (anti path-traversal).

Discipline cardinale : aucun PDF hors `<repo>/docs/cgu/*.pdf` ne peut être hashé via
ce helper, indépendamment du chemin fourni en argument. Empêche l'oracle de hash sur
fichiers système (cas Phase D-1 P1-AUDIT-D-006 audit deep multi-agents).
"""


def compute_cgu_pdf_sha256(pdf_path: str) -> str:
    """Phase D-1 — D-Audit-C8-CGU-Pdf-Hash-007 P1 REG : helper SHA256 PDF CGU.

    Calcule le hash SHA-256 du fichier PDF CGU pour preuve d'origine forte CNIL Article 7
    (vs nominal version étiquette). À appeler lors publication nouvelle version CGU pour
    renseigner `contenu_sha256` dans `cgu_referentiel.yaml`.

    Phase D-3 Tier 2 SEC-1 (fix P1-AUDIT-D-006) : allowlist `<repo>/docs/cgu/*.pdf`
    cardinale anti path-traversal. Le `pdf_path` peut être absolu ou relatif, mais
    après résolution doit être strictement à l'intérieur de `_CGU_PDF_ALLOWED_ROOT`.

    Usage admin :
        sha = compute_cgu_pdf_sha256("docs/cgu/CGU_v1.0_2026-01-15.pdf")
        # Mettre à jour cgu_referentiel.yaml avec contenu_sha256: <sha>

    Returns:
        Hash SHA-256 hexadécimal (64 chars).

    Raises:
        FileNotFoundError si PDF introuvable.
        ValueError si `pdf_path` hors allowlist `<repo>/docs/cgu/`.
    """
    import hashlib

    pdf_p = Path(pdf_path)

    # Résolution sécurisée : si chemin relatif, l'ancrer sur _CGU_PDF_ALLOWED_ROOT.
    if not pdf_p.is_absolute():
        # Cas : "CGU_v1.0.pdf" ou "docs/cgu/CGU_v1.0.pdf" → résoudre depuis repo root.
        repo_root = _CGU_PDF_ALLOWED_ROOT.parent.parent
        candidate = (repo_root / pdf_p).resolve()
        if str(candidate).startswith(str(_CGU_PDF_ALLOWED_ROOT.resolve()) + os.sep):
            pdf_p = candidate
        else:
            # Fallback : tenter direct depuis allowlist root
            pdf_p = (_CGU_PDF_ALLOWED_ROOT / pdf_p.name).resolve()

    pdf_p = pdf_p.resolve()
    allowed_root = _CGU_PDF_ALLOWED_ROOT.resolve()
    try:
        pdf_p.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError(
            f"Phase D-3 SEC-1 violation : chemin {pdf_path!r} hors allowlist "
            f"{allowed_root}/ — anti path-traversal cardinal."
        ) from exc

    if not pdf_p.exists():
        raise FileNotFoundError(f"CGU PDF introuvable : {pdf_path}")

    h = hashlib.sha256()
    with pdf_p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_cgu_version_integrity(version: str, pdf_path: Optional[str] = None) -> dict:
    """Phase D-1 — vérifie intégrité d'une version CGU (preuve CNIL Article 7).

    Si `pdf_path` fourni, calcule SHA256 et compare au `contenu_sha256` du référentiel.
    Sinon, retourne le contenu_sha256 attendu pour vérification manuelle.

    Returns:
        dict avec status (`'valid'`, `'mismatch'`, `'no_hash_yet'`, `'unknown_version'`),
        version, expected_sha256, computed_sha256 (si pdf_path fourni).
    """
    config = _load_cgu_referentiel()
    target = next((v for v in config.get("versions", []) if v.get("version") == version), None)
    if target is None:
        return {"status": "unknown_version", "version": version}

    expected = target.get("contenu_sha256")
    if expected is None:
        return {"status": "no_hash_yet", "version": version, "expected_sha256": None}

    if pdf_path is None:
        return {"status": "expected_sha256_only", "version": version, "expected_sha256": expected}

    computed = compute_cgu_pdf_sha256(pdf_path)
    return {
        "status": "valid" if computed == expected else "mismatch",
        "version": version,
        "expected_sha256": expected,
        "computed_sha256": computed,
    }
