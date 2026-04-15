"""
CLI runner pour les agents PROMEOS (Claude Agent SDK).

Usage :
    cd backend && python -m orchestration qa [scope]
    cd backend && python -m orchestration --list
    cd backend && python -m orchestration --list --json
    cd backend && python -m orchestration qa source-guards --json
    cd backend && python -m orchestration qa full --dry-run

NOTE : Chaque invocation d'agent spawn un process Claude Code CLI via le SDK.
       Adapté dev/CI, pas runtime serveur. Pour la production, voir
       `backend/ai_layer/` (API Anthropic directe).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

# Windows cp1252 console cannot print CO₂, €, etc. — force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except AttributeError:
    pass

import anyio


AGENTS_REGISTRY: dict[str, dict] = {
    "qa": {
        "name": "QA Guardian",
        "description": "Audit read-only : tests, source guards, constantes, seed",
        "scopes": ["full", "tests", "source-guards", "constants", "seed"],
        "default_scope": "full",
        "status": "active",
        "write_access": False,
    },
    "regulatory": {
        "name": "Regulatory Analyst",
        "description": "Audit YAML tarifs réglementaires (TURPE/CTA/accises/ATRD) via MCP tools",
        "scopes": ["audit-coherence", "audit-cesures", "audit-tariff"],
        "default_scope": "audit-coherence",
        "status": "active",
        "write_access": False,
    },
    # P2 :
    # "lead": {...},
}


def _print_list(as_json: bool) -> None:
    if as_json:
        print(json.dumps(AGENTS_REGISTRY, indent=2, ensure_ascii=False))
        return
    print("Agents PROMEOS disponibles :\n")
    for key, info in AGENTS_REGISTRY.items():
        icon = "OK" if info["status"] == "active" else "WIP"
        rw = "RO" if not info["write_access"] else "RW"
        print(f"  [{icon}] {key:15s} - {info['name']} [{rw}]")
        print(f"       Scopes : {', '.join(info['scopes'])}")


def _dry_run(agent: str, scope: str) -> None:
    if agent == "qa":
        from .agents.qa_guardian import SCOPE_PROMPTS, SYSTEM_PROMPT
    elif agent == "regulatory":
        from .agents.regulatory import SCOPE_PROMPTS, SYSTEM_PROMPT
    else:
        raise ValueError(f"Agent inconnu : {agent}")

    print("=== SYSTEM PROMPT ===")
    print(SYSTEM_PROMPT[:600] + ("..." if len(SYSTEM_PROMPT) > 600 else ""))
    print()
    print(f"=== TASK PROMPT ({agent} / scope={scope}) ===")
    print(SCOPE_PROMPTS[scope])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PROMEOS Agent Runner (Claude Agent SDK)",
        epilog="Exemple : cd backend && python -m orchestration qa source-guards --json",
    )
    parser.add_argument(
        "agent",
        nargs="?",
        choices=list(AGENTS_REGISTRY.keys()),
        help="Agent à exécuter",
    )
    parser.add_argument(
        "scope",
        nargs="?",
        default=None,
        help="Scope de l'audit (par défaut le default_scope de l'agent)",
    )
    parser.add_argument("--list", action="store_true", help="Lister les agents disponibles")
    parser.add_argument("--json", action="store_true", help="Sortie JSON")
    parser.add_argument("--dry-run", action="store_true", help="Afficher le prompt sans exécuter")

    args = parser.parse_args()

    if args.list:
        _print_list(args.json)
        return

    if not args.agent:
        parser.print_help()
        return

    agent_info = AGENTS_REGISTRY[args.agent]
    if args.scope is None:
        args.scope = agent_info["default_scope"]
    if args.scope not in agent_info["scopes"]:
        print(
            f"Scope '{args.scope}' invalide pour {args.agent}. Valides : {', '.join(agent_info['scopes'])}",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.dry_run:
        _dry_run(args.agent, args.scope)
        return

    if args.agent == "qa":
        from .agents.qa_guardian import run_qa_audit

        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if not args.json:
            print(f"[{ts}] QA Guardian - scope={args.scope}")
            print("=" * 60)

        async def _run():
            return await run_qa_audit(args.scope)
    elif args.agent == "regulatory":
        from .agents.regulatory import run_regulatory_audit

        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if not args.json:
            print(f"[{ts}] Regulatory Analyst - scope={args.scope}")
            print("=" * 60)

        async def _run():
            return await run_regulatory_audit(args.scope)

        try:
            result = anyio.run(_run)
        except Exception as exc:
            error = {
                "status": "error",
                "error": str(exc),
                "hint": ("Verifier que ANTHROPIC_API_KEY est definie. Le SDK ne fonctionne pas en mode stub."),
            }
            if args.json:
                print(json.dumps(error, indent=2, ensure_ascii=False))
            else:
                print(f"Erreur : {exc}")
                print(f"Hint : {error['hint']}")
            sys.exit(1)

        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            status_icon = "OK" if result["status"] == "green" else "KO"
            print(f"\n[{status_icon}] Status: {result['status'].upper()}")
            print(f"\n{result['summary']}")


if __name__ == "__main__":
    main()
