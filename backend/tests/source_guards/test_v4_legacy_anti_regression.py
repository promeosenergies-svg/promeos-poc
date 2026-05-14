"""
PROMEOS V4 · 4 source-guards anti-régression Sprint M2-1.

Source : L9 §2 Sprint M2-1 + ADR-027 §11 (50 SG progressif).

Objectif : empêcher toute régression vers le code legacy supprimé Mois 5.
Activés dès Sprint M2-1, AVANT que le code backend V4 soit écrit.

Garde-fous cardinaux ancrés :
- 🛡️ I9 (ADR-026) : backup hors Git
- 🛡️ IS10 (ADR-027) : .gitignore exclut backups + evidences (renforcement CI de I9)
- 🛡️ IE1 (ADR-029) : storage evidences gitignored (`fs://` → `/data/promeos/evidences/`)
- Anti-régression L8 : aucun import vers models legacy supprimés Mois 5

Path canonique CI : `backend/tests/source_guards/` (cf. .github/workflows/source_guards.yml).

Cumul SG fin M2-1 : 4 (sur 50 cible fin Mois 2 — cf. L9 §3 progressif par sprint).
"""

import re
from pathlib import Path

# Repo root = .../promeos-poc/ (3 levels up from this file)
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"


def _grep_files(root: Path, pattern: str, extensions: tuple = (".py",)) -> list[Path]:
    """Helper grep récursif. Skip files unreadable."""
    if not root.exists():
        return []
    matches = []
    for ext in extensions:
        for f in root.rglob(f"*{ext}"):
            # Skip __pycache__, venv, alembic versions (legacy migrations conservées historique)
            if any(part in f.parts for part in ("__pycache__", "venv", ".venv")):
                continue
            try:
                content = f.read_text(encoding="utf-8")
                if re.search(pattern, content):
                    matches.append(f)
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
    return matches


# Baseline whitelist : fichiers legacy connus qui consomment encore
# les modules / classes scheduled-for-deletion Mois 5 (cf. L8 §3.1 + §3.2).
# Pendant Mois 2-3 = coexistence Q13-B (legacy + V4 actifs en parallèle).
# Mois 5 J+14 STOP GATE → ces fichiers seront supprimés par L8, et cette
# whitelist devra être vidée.
#
# Tout NOUVEAU fichier (créé après Sprint M2-1) qui ajouterait ces imports
# fera échouer SG-1 ou SG-2 → vraie anti-régression sur code récent.
LEGACY_BASELINE_WHITELIST_SG1 = set()  # vide aujourd'hui : pas de fichier *_legacy.py existant
LEGACY_BASELINE_WHITELIST_SG2 = {
    "backend/models/__init__.py",
    "backend/services/action_audit_service.py",
}


def test_sg_1_no_action_legacy_imports_v4():
    """
    SG-1 (V4 anti-régression) : aucun NOUVEAU import vers `*_legacy.py` modules.

    Cible Mois 5 L8 §3.1 : `backend/models/action_legacy.py`,
    `backend/models/anomaly_legacy.py` (si créés Mois 4 cutover).

    Baseline : `LEGACY_BASELINE_WHITELIST_SG1` (vide aujourd'hui — aucun fichier
    *_legacy.py n'existe encore en Mois 1).
    """
    forbidden_patterns = [
        r"from backend\.models\.action_legacy import",
        r"from backend\.models\.anomaly_legacy import",
        r"import backend\.models\.action_legacy\b",
        r"import backend\.models\.anomaly_legacy\b",
    ]
    new_violations = []
    for pattern in forbidden_patterns:
        matches = _grep_files(BACKEND_ROOT, pattern)
        for m in matches:
            if "test_v4_legacy_anti_regression" in m.name:
                continue  # exclure le SG lui-même
            rel = str(m.relative_to(REPO_ROOT))
            if rel not in LEGACY_BASELINE_WHITELIST_SG1:
                new_violations.append((pattern, rel))

    assert not new_violations, (
        f"SG-1 violation: {len(new_violations)} new legacy import(s) introduced. "
        f"violations={new_violations}. "
        f"Cf. L8 §3.1 — `*_legacy.py` modules scheduled for deletion Mois 5 J+14. "
        f"Si vraiment nécessaire pendant coexistence Mois 2-3, ajouter à "
        f"LEGACY_BASELINE_WHITELIST_SG1 (avec justification + ticket de cleanup)."
    )


def test_sg_2_no_anomaly_event_legacy_imports():
    """
    SG-2 (V4 anti-régression) : aucun NOUVEAU import des classes legacy
    `ActionPlanItem`, `ActionPlanEvent`, `ActionPlanNotification`, `ActionPlanEvidence`
    (Sprint 13 dette pure · L8 §3.1 — suppression Mois 5).

    Baseline : `LEGACY_BASELINE_WHITELIST_SG2` (callsites existants tolérés
    pendant coexistence Mois 2-3). Mois 5 L8 supprime ces fichiers → whitelist
    devient vide naturellement.
    """
    forbidden_patterns = [
        r"from\s+\S+\s+import\s+(\w+,\s*)*ActionPlanItem(\s*,|\s*$|\s*\))",
        r"from\s+\S+\s+import\s+(\w+,\s*)*ActionPlanEvent(\s*,|\s*$|\s*\))",
        r"from\s+\S+\s+import\s+(\w+,\s*)*ActionPlanNotification(\s*,|\s*$|\s*\))",
        r"from\s+\S+\s+import\s+(\w+,\s*)*ActionPlanEvidence(\s*,|\s*$|\s*\))",
    ]
    new_violations = []
    for pattern in forbidden_patterns:
        matches = _grep_files(BACKEND_ROOT, pattern)
        for m in matches:
            if "test_v4_legacy_anti_regression" in m.name:
                continue
            rel = str(m.relative_to(REPO_ROOT))
            if rel not in LEGACY_BASELINE_WHITELIST_SG2:
                new_violations.append((pattern, rel))

    assert not new_violations, (
        f"SG-2 violation: {len(new_violations)} new Sprint 13 legacy class import(s). "
        f"violations={new_violations}. "
        f"Cf. L8 §3.1 — these classes are dead Sprint 13 code (0 rows DB), "
        f"scheduled for deletion Mois 5 J+14. NEW V4 code must use "
        f"`ActionCenterItem` (single-table inheritance Q1-A) instead."
    )


def test_sg_3_gitignore_excludes_backups_and_sql():
    """
    SG-3 (🛡️ IS10 + 🛡️ I9) : .gitignore exclut /backups/, *.backup, *.sql.

    Cardinal Amine : renforcement CI de I9 ADR-026 (backup hors Git impératif).
    Tout backup binaire ou dump SQL committé = violation RGPD potentielle (PII)
    + violation taille repo.
    """
    gitignore_path = REPO_ROOT / ".gitignore"
    assert gitignore_path.exists(), (
        f"SG-3 violation: .gitignore must exist at repo root ({gitignore_path}). Cf. ADR-026 I9 + ADR-027 IS10."
    )
    content = gitignore_path.read_text(encoding="utf-8")
    required_patterns = ["/backups/", "*.backup", "*.sql"]
    missing = [p for p in required_patterns if p not in content]
    assert not missing, (
        f"SG-3 violation: .gitignore missing required patterns: {missing}. "
        f"Cf. ADR-026 I9 + ADR-027 IS10. Add a 'PROMEOS V4 cardinal' section "
        f"with these patterns to protect from accidental backup commit."
    )


def test_sg_4_gitignore_excludes_evidences():
    """
    SG-4 (🛡️ IE1) : .gitignore exclut /data/promeos/evidences/.

    Cardinal Amine : storage evidences `fs://` toujours gitignored (Mois 2 POC).
    Migration `fs://` → `s3://` V4.1+ ne change pas ce SG (le path reste sur disque
    local pendant Mois 2-6, et S3 est par essence non gitignorable).
    """
    gitignore_path = REPO_ROOT / ".gitignore"
    content = gitignore_path.read_text(encoding="utf-8")
    required_pattern = "/data/promeos/evidences/"
    assert required_pattern in content, (
        f"SG-4 violation: .gitignore missing required pattern: {required_pattern!r}. "
        f"Cf. ADR-029 IE1 — storage evidences abstrait fs://, gitignored impératif."
    )
