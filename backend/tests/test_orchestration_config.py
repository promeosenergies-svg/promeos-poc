"""
Tests unitaires pour le module orchestration (Claude Agent SDK).
Aucune API key requise — tests structurels uniquement.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    """Run `python -m orchestration ...` from backend/, UTF-8 safe."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "orchestration", *args],
        capture_output=True,
        text=True,
        cwd=str(BACKEND_DIR),
        env=env,
        encoding="utf-8",
        errors="replace",
    )


# --- Config ---------------------------------------------------------------


def test_config_imports():
    """Le module config s'importe sans erreur."""
    from orchestration.config import (
        AGENT_MODEL,
        BACKEND_DIR,
        PATHS,
        QA_GUARDIAN_ALLOWED_TOOLS,
        QA_GUARDIAN_DISALLOWED_TOOLS,
        REPO_ROOT as CONFIG_REPO_ROOT,
    )

    assert CONFIG_REPO_ROOT.exists()
    assert BACKEND_DIR.exists()
    assert isinstance(AGENT_MODEL, str) and AGENT_MODEL
    assert len(PATHS) >= 5
    assert isinstance(QA_GUARDIAN_ALLOWED_TOOLS, list)
    assert isinstance(QA_GUARDIAN_DISALLOWED_TOOLS, list)


def test_qa_guardian_is_readonly():
    """SOURCE GUARD : QA Guardian ne doit JAMAIS avoir Write/Edit."""
    from orchestration.config import (
        QA_GUARDIAN_ALLOWED_TOOLS,
        QA_GUARDIAN_DISALLOWED_TOOLS,
    )

    forbidden = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
    assert not forbidden.intersection(set(QA_GUARDIAN_ALLOWED_TOOLS)), (
        "QA Guardian MUST NOT have write tools in allowed_tools"
    )
    assert forbidden.issubset(set(QA_GUARDIAN_DISALLOWED_TOOLS)), "QA Guardian MUST explicitly disallow write tools"


def test_paths_exist():
    """Les chemins critiques existent."""
    from orchestration.config import validate_paths

    missing = validate_paths()
    assert missing == [], f"Chemins manquants : {missing}"


# --- Agent module ---------------------------------------------------------


def test_agent_module_imports():
    """Le module qa_guardian s'importe et expose ses symboles clés."""
    from orchestration.agents.qa_guardian import (
        SCOPE_PROMPTS,
        SYSTEM_PROMPT,
        run_qa_audit,
    )

    assert callable(run_qa_audit)
    assert "0.052" in SYSTEM_PROMPT  # Facteur CO₂ ADEME
    assert "7500" in SYSTEM_PROMPT  # Pénalité DT
    assert "READ-ONLY" in SYSTEM_PROMPT
    assert set(SCOPE_PROMPTS.keys()) == {
        "full",
        "tests",
        "source-guards",
        "constants",
        "seed",
    }


def test_scope_validation_rejects_unknown():
    """run_qa_audit rejette tout scope inconnu sans appeler l'API."""
    import anyio

    from orchestration.agents.qa_guardian import run_qa_audit

    with pytest.raises(ValueError, match="Scope inconnu"):
        anyio.run(lambda: run_qa_audit("nope"))


# --- CLI ------------------------------------------------------------------


def test_cli_list_json():
    """--list --json retourne le registry en JSON valide."""
    result = _run_cli(["--list", "--json"])
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert "qa" in data
    assert data["qa"]["status"] == "active"
    assert data["qa"]["write_access"] is False


def test_cli_dry_run_shows_prompt():
    """--dry-run affiche le prompt sans exécuter."""
    result = _run_cli(["qa", "source-guards", "--dry-run"])
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "SYSTEM PROMPT" in result.stdout
    assert "grep" in result.stdout  # Le prompt source-guards contient grep


def test_cli_invalid_scope_rejected():
    """Le CLI rejette un scope invalide avec exit != 0."""
    result = _run_cli(["qa", "FAKE_SCOPE"])
    assert result.returncode != 0
    combined = (result.stderr + result.stdout).lower()
    assert "invalide" in combined or "invalid" in combined
