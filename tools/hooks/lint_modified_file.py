#!/usr/bin/env python3
"""PostToolUse hook — lint file after Write/Edit.

Reçoit le payload Claude Code hook. Si le fichier modifié est :
- .py → ruff check (non-bloquant : avertit sans stopper)
- .ts / .tsx / .js / .jsx → eslint (non-bloquant)
- sinon : no-op

Output sur stderr si violations. Exit 0 toujours (post-hook non-bloquant par design).
"""
import json
import subprocess
import sys
from pathlib import Path


PYTHON_EXT = {".py"}
FRONTEND_EXT = {".ts", ".tsx", ".js", ".jsx"}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    file_path = payload.get("tool_input", {}).get("file_path")
    if not file_path:
        return 0
    path = Path(file_path)
    if not path.exists():
        return 0
    ext = path.suffix.lower()
    try:
        if ext in PYTHON_EXT:
            result = subprocess.run(
                ["ruff", "check", "--quiet", str(path)],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0 and result.stdout:
                sys.stderr.write(f"[ruff] {path}\n{result.stdout[:2000]}\n")
        elif ext in FRONTEND_EXT:
            # eslint peut être lent au démarrage ; skip si node_modules absent
            if not Path("frontend/node_modules").exists():
                return 0
            result = subprocess.run(
                ["npx", "eslint", "--quiet", str(path)],
                capture_output=True, text=True, timeout=30,
                cwd="frontend" if str(path).startswith("frontend/") else None,
            )
            if result.returncode != 0 and result.stdout:
                sys.stderr.write(f"[eslint] {path}\n{result.stdout[:2000]}\n")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass  # outil absent → silencieux
    return 0


if __name__ == "__main__":
    sys.exit(main())
