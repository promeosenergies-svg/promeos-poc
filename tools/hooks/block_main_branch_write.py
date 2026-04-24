#!/usr/bin/env python3
"""PreToolUse hook — block Write/Edit on main/master branch.

Doctrine PROMEOS (feedback_no_main_pollution.md) :
main et master sont intouchables en local. Tout write passe par une
branche `claude/*` ou `feat/*`.

Exit 2 + stderr message if on main/master and tool_name is Write/Edit.
Exit 0 otherwise. Merges via git tooling ne déclenchent pas ce hook.
"""
import json
import subprocess
import sys
from typing import Optional

PROTECTED_BRANCHES = {"main", "master"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def current_branch() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in WRITE_TOOLS:
        return 0
    branch = current_branch()
    if branch in PROTECTED_BRANCHES:
        file_path = payload.get("tool_input", {}).get("file_path", "<unknown>")
        sys.stderr.write(
            f"[block_main_branch_write] BLOCKED — tentative de "
            f"{payload.get('tool_name')} sur branche protégée '{branch}'.\n"
            f"Fichier ciblé : {file_path}\n"
            f"Doctrine PROMEOS : créer une branche `claude/<topic>` d'abord.\n"
            f"  git checkout -b claude/<topic>\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
