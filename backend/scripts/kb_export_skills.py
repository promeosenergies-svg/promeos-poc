"""
kb_export_skills.py — Synchronise kb.db vers .claude/skills/
Garantit que les agents de construction (Claude Code, Paperclip)
utilisent les mêmes constantes que les agents runtime.

À exécuter après chaque mise à jour de kb.db.

Usage:
    cd backend && python scripts/kb_export_skills.py
"""

import hashlib
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.kb.store import KBStore


SKILLS_OUTPUT = {
    "promeos-constants": {
        "path": ".claude/skills/promeos-constants/SKILL.md",
        "filter_tag": "constants",
        "description": "Constantes métier PROMEOS — valeurs réglementaires et physiques",
    },
}

# Project root (2 levels up from backend/scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def export_skills():
    """Lit kb.db -> génère les fichiers SKILL.md avec checksum."""
    store = KBStore()

    for skill_id, config in SKILLS_OUTPUT.items():
        # Récupérer les items dont tags_json contient le namespace
        all_items = store.get_items(status="validated", limit=1000)
        items = [item for item in all_items if item.get("tags", {}).get("namespace") == config["filter_tag"]]

        skill_content = _format_as_skill_md(skill_id, config["description"], items)

        output_path = PROJECT_ROOT / config["path"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(skill_content, encoding="utf-8")

        checksum = hashlib.md5(skill_content.encode()).hexdigest()[:8]
        print(f"[export_skills] OK {skill_id} -> {config['path']} [{checksum}] ({len(items)} items)")

    return True


def _format_as_skill_md(skill_id: str, description: str, items: list) -> str:
    """Formate les items KB en SKILL.md lisible par Claude Code."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    lines = [
        "---",
        f"name: {skill_id}",
        f"description: {description}",
        f"generated_at: {now}",
        "---",
        "",
        f"# {description}",
        "",
        "## ⚠️ CONSTANTES CRITIQUES (NE JAMAIS MODIFIER EN DUR)",
        "",
    ]

    for item in items:
        sources = item.get("sources", [])
        source_ref = sources[0].get("reference", "N/A") if sources else "N/A"
        lines += [
            f"### {item['id']}",
            f"**{item['title']}**",
            f"- **Résumé** : {item['summary']}",
            f"- **Confiance** : {item['confidence']}",
            f"- **Source** : {source_ref}",
            "",
        ]

    return "\n".join(lines)


if __name__ == "__main__":
    export_skills()
