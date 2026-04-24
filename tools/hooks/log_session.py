#!/usr/bin/env python3
"""Stop hook — append session summary to docs/audit/agent_sessions.jsonl.

Log JSONL format : {timestamp, session_id, cwd, duration_s?, tools_used?}.
Exit 0 toujours (log non-bloquant).

Support --test flag pour self-check (écrit entrée fictive).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


LOG_FILE = Path("docs/audit/agent_sessions.jsonl")


def write_entry(entry: dict) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> int:
    if "--test" in sys.argv:
        write_entry({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": "test-session",
            "cwd": str(Path.cwd()),
            "kind": "self-test",
        })
        print(f"OK — entry appended to {LOG_FILE}")
        return 0
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": payload.get("session_id", "unknown"),
        "cwd": payload.get("cwd", str(Path.cwd())),
        "transcript_path": payload.get("transcript_path", ""),
    }
    try:
        write_entry(entry)
    except OSError:
        pass  # filesystem read-only → silent
    return 0


if __name__ == "__main__":
    sys.exit(main())
