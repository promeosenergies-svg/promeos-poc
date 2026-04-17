"""
PROMEOS AI — KB Context Builder
Helper pour enrichir les prompts LLM avec des items KB validés.

HARD RULE : toute recommandation réglementaire DOIT s'appuyer sur des items KB
validated (cf. app/kb/service.py doctrine).
Usage :
    from ai_layer.agents.kb_context import build_kb_context
    kb_ctx = build_kb_context(site, domain="reglementaire")
    user_prompt = f"{base_prompt}\n\n{kb_ctx['prompt_section']}"
"""

from __future__ import annotations

import logging
from typing import Any

from app.kb.service import KBService

logger = logging.getLogger(__name__)

# Limite défensive : ne pas injecter plus de 15 items dans un prompt
MAX_ITEMS_IN_PROMPT = 15


def _site_to_context(site: Any) -> dict[str, Any]:
    """Convertit un Site ORM en site_context pour KBService.apply().

    Mapping : champs Site → champs scope/logic attendus par les items KB
    (hvac_kw, surface_m2, building_type, energy_vector, segment...).
    """
    context: dict[str, Any] = {}

    if getattr(site, "surface_m2", None):
        context["surface_m2"] = site.surface_m2

    if getattr(site, "type", None):
        context["building_type"] = str(site.type).lower()

    if getattr(site, "hvac_kw", None):
        context["hvac_kw"] = site.hvac_kw

    if getattr(site, "parking_surface_m2", None):
        context["parking_surface_m2"] = site.parking_surface_m2

    # Défaut énergie : site élec sauf indication contraire
    context["energy_vector"] = getattr(site, "energy_vector", None) or "elec"

    # Segment : le modèle Site n'a pas de champ segment clair, on infère depuis type
    if context.get("building_type") in ("bureau", "commerce", "enseignement", "sante"):
        context["segment"] = "tertiaire_multisite"

    return context


def _format_item_for_prompt(item: dict[str, Any]) -> str:
    """Format un item KB en bloc texte concis pour LLM."""
    lines = [f"**[{item['kb_item_id']}]** {item['title']}"]

    for action in (item.get("actions") or [])[:3]:
        label = action.get("label", "")
        deadline = action.get("deadline")
        suffix = f" (deadline {deadline})" if deadline else ""
        lines.append(f"  • {label}{suffix}")

    for src in (item.get("sources") or [])[:2]:
        label = src.get("label", src.get("doc_id", "source"))
        lines.append(f"  (src: {label})")

    return "\n".join(lines)


def build_kb_context(
    site: Any,
    domain: str | None = None,
    allow_drafts: bool = False,
) -> dict[str, Any]:
    """Évalue la KB contre un Site et retourne le contexte à injecter dans le prompt.

    Args:
        site: instance ORM Site
        domain: filtre optionnel (reglementaire/usages/acc/facturation/flex)
        allow_drafts: False par défaut — HARD RULE doctrine PROMEOS

    Returns:
        dict avec :
        - prompt_section: texte formaté à injecter dans le user_prompt
        - applicable_items: liste brute des items matchés (pour traçabilité)
        - kb_item_ids: liste des IDs (pour sources_used)
        - missing_fields: champs absents de site_context (pour transparence)
        - status: "ok" / "partial" / "insufficient" / "error"
    """
    try:
        svc = KBService()
        site_context = _site_to_context(site)
        result = svc.apply(site_context, domain=domain, allow_drafts=allow_drafts)
    except Exception:
        logger.warning("KB apply failed for site, returning empty context", exc_info=True)
        return {
            "prompt_section": "",
            "applicable_items": [],
            "kb_item_ids": [],
            "missing_fields": [],
            "status": "error",
        }

    items = (result.get("applicable_items") or [])[:MAX_ITEMS_IN_PROMPT]

    if not items:
        prompt_section = (
            "AUCUN ITEM KB VALIDÉ NE CORRESPOND À CE SITE.\n"
            "N'invente PAS de fait réglementaire. Indique explicitement le manque de données."
        )
    else:
        blocks = [_format_item_for_prompt(i) for i in items]
        prompt_section = (
            "ITEMS KB VALIDÉS APPLICABLES À CE SITE (à utiliser STRICTEMENT comme source) :\n\n"
            + "\n\n".join(blocks)
            + "\n\nRÈGLE : ne cite que ces items. Si une info n'est pas dans la liste, écris "
            "'Non couvert par la KB' — n'invente JAMAIS un décret, une date ou un seuil."
        )

    return {
        "prompt_section": prompt_section,
        "applicable_items": items,
        "kb_item_ids": [i["kb_item_id"] for i in items],
        "missing_fields": result.get("missing_fields", []),
        "status": result.get("status", "ok"),
    }
