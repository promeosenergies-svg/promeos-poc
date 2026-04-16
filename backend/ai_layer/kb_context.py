"""
kb_context.py -- Helper pour injecter le contexte KB dans les prompts agents.
Chaque agent appelle build_kb_prompt_section() pour enrichir son prompt.
"""

from app.kb.service import KBService
from app.kb.store import KBStore


def kb_apply(site_context: dict | None = None, domain: str | None = None, max_items: int = 20) -> str:
    """
    Applique la KB au contexte donne et retourne un bloc texte injectable.
    Si site_context est None, retourne toutes les constantes validees du domaine.
    """
    service = KBService()
    ctx = site_context or {}
    result = service.apply(ctx, domain=domain, allow_drafts=False)

    lines = []
    items = result.get("applicable_items", [])[:max_items]

    if not items:
        store = KBStore()
        raw_items = store.get_items(domain=domain, status="validated", limit=max_items)
        for item in raw_items:
            lines.append(f"- **{item['title']}** : {item['summary']}")
        if not raw_items:
            return ""
    else:
        for item in items:
            why_list = item.get("why", [])
            why_text = why_list[0] if why_list else ""
            lines.append(f"- **{item['title']}** ({item['confidence']}) : {why_text}")
            sources = item.get("sources", [])
            if sources:
                lines.append(f"  Source : {sources[0].get('reference', 'N/A')}")

    return "\n".join(lines)


def kb_warnings(domains: list[str] | None = None) -> str:
    """Retourne les avertissements critiques des items KB."""
    store = KBStore()
    all_items = store.get_items(status="validated", limit=500)

    warnings = []
    for item in all_items:
        content = item.get("content_md", "")
        if domains and item.get("domain") not in domains:
            if item.get("tags", {}).get("namespace") not in domains:
                continue
        if "NE PAS CONFONDRE" in content or "warning" in content.lower():
            warnings.append(f"- {item['title']} : {item['summary']}")

    return "\n".join(warnings) if warnings else ""


def build_kb_prompt_section(site_context: dict | None = None, domain: str | None = None) -> str:
    """
    Construit la section complete a injecter dans un prompt agent.
    Retourne une string vide si aucun item KB applicable.
    """
    context_block = kb_apply(site_context, domain)
    warnings_block = kb_warnings()

    if not context_block and not warnings_block:
        return ""

    parts = ["\n## CONTEXTE KB PROMEOS (source de verite)"]
    if context_block:
        parts.append(context_block)
    if warnings_block:
        parts.append("\n## AVERTISSEMENTS CRITIQUES")
        parts.append(warnings_block)
    parts.append("\nINSTRUCTION : Utiliser UNIQUEMENT les valeurs du contexte KB ci-dessus.")
    parts.append("Ne jamais inventer ou supposer des valeurs reglementaires.")

    return "\n".join(parts)
