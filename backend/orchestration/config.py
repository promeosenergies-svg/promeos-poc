"""
Configuration centralisée pour le Claude Agent SDK (orchestration dev/CI).

Sépare la config orchestration de la config ai_layer (production).

IMPORTANT :
- Ce module cible l'orchestration DEV (QA, audits, sprints).
- Les agents PRODUCTION restent dans `backend/ai_layer/` (API Anthropic directe).
- Le SDK spawn un process Claude Code CLI par query() → à ne PAS appeler en
  boucle depuis FastAPI. Usage : scripts ponctuels, CLI, CI/CD.
"""

from __future__ import annotations

import os
from pathlib import Path

# Racine du repo (remonte depuis backend/orchestration/config.py)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

# SDK — alias modèles Claude : sonnet / opus / haiku
AGENT_MODEL = os.getenv("AGENT_SDK_MODEL", "sonnet")
AGENT_FALLBACK_MODEL = os.getenv("AGENT_SDK_FALLBACK", "haiku")
AGENT_MAX_TURNS = int(os.getenv("AGENT_SDK_MAX_TURNS", "15"))

# QA Guardian = read-only strict (source guard testé)
QA_GUARDIAN_ALLOWED_TOOLS = ["Read", "Glob", "Grep", "Bash"]
QA_GUARDIAN_DISALLOWED_TOOLS = ["Write", "Edit", "MultiEdit", "NotebookEdit"]

# Chemins critiques PROMEOS (validés au démarrage)
PATHS: dict[str, str] = {
    "regops_rules": str(BACKEND_DIR / "regops" / "rules"),
    "regops_config": str(BACKEND_DIR / "regops" / "config"),
    "ai_layer": str(BACKEND_DIR / "ai_layer"),
    "tests_dir": str(BACKEND_DIR / "tests"),
    "tarifs_yaml": str(BACKEND_DIR / "config" / "tarifs_reglementaires.yaml"),
    "emission_factors": str(BACKEND_DIR / "config" / "emission_factors.py"),
}


def validate_paths() -> list[str]:
    """Retourne la liste des chemins critiques manquants (vide = OK)."""
    missing: list[str] = []
    for key, path_str in PATHS.items():
        if not Path(path_str).exists():
            missing.append(f"{key}: {path_str}")
    return missing
