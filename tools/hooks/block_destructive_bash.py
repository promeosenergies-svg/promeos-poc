#!/usr/bin/env python3
"""PreToolUse hook — block destructive Bash commands.

Reads Claude Code hook JSON on stdin (tool_name + tool_input.command).
Exit 2 + stderr message if match; exit 0 otherwise.

Patterns (french-ops doctrine PROMEOS, cf docs/dev/workframe-contract.md) :
- rm -rf / ... (mass delete)
- DROP TABLE / DROP DATABASE (SQL destructive)
- git push --force origin main/master (force push upstream protected)
- git reset --hard (destructive unless user-approved)
- find -delete, curl | bash (unsafe patterns)
"""
import json
import re
import sys

DESTRUCTIVE_PATTERNS = [
    (r"\brm\s+-rf?\s+/(?:\s|$)", "rm -rf / — mass root delete"),
    (r"\brm\s+-rf?\s+~(?:\s|$|/)", "rm -rf ~ — home delete"),
    (r"\bDROP\s+(?:TABLE|DATABASE|SCHEMA)\b", "SQL DROP destructive"),
    (r"git\s+push\s+.*--force\s+.*\b(main|master|origin/main|origin/master)\b",
     "git push --force sur main/master"),
    (r"git\s+push\s+.*\b(main|master)\b.*--force", "git push --force sur main/master"),
    (r"git\s+reset\s+--hard(?!\s+HEAD)", "git reset --hard (destructif)"),
    (r"find\s+.*-delete\b", "find -delete (mass delete)"),
    (r"curl\s+[^|]*\|\s*(?:ba)?sh\b", "curl | bash (RCE pattern)"),
    (r">\s*/dev/sd[a-z]", "écriture /dev/sdX (disque)"),
    (r"mkfs\.", "mkfs (format disque)"),
    (r":\(\)\{.*:\|:&\};:", "fork bomb"),
    (r"--no-verify", "--no-verify (skip hooks) — doctrine PROMEOS interdit"),
    (r"--no-gpg-sign", "--no-gpg-sign — doctrine interdit"),
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # no payload → allow
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = payload.get("tool_input", {}).get("command", "") or ""
    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, cmd):
            sys.stderr.write(
                f"[block_destructive_bash] BLOCKED ({reason}) — "
                f"command: {cmd[:200]}\n"
                f"Doctrine PROMEOS : pas de destructif silencieux. "
                f"Si intentionnel, demande confirmation à l'utilisateur.\n"
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
