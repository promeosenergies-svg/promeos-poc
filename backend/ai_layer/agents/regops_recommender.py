"""
PROMEOS AI - RegOps Recommender (suggestions tagged AI_SUGGESTION)

HARD RULE doctrine PROMEOS : toute recommandation DOIT s'appuyer sur des items
KB validated. Le LLM ne sert qu'à reformuler/prioriser les actions déjà extraites
de la KB — jamais à inventer des faits réglementaires.
"""

import json

from models import AiInsight, InsightType, Site

from ..client import get_client
from .kb_context import build_kb_context

SYSTEM_PROMPT = """Expert en optimisation énergétique pour bâtiments tertiaires français.

Ta mission : reformuler et prioriser les actions issues de la KB PROMEOS (items validés).

RÈGLES STRICTES :
- Ne propose QUE des actions tirées des items KB fournis (pas d'invention)
- Priorise par criticité (deadline proche, severity high/critical d'abord)
- Chaque action citée doit référencer son kb_item_id d'origine [ID]
- Tag chaque suggestion avec AI_SUGGESTION + kb_item_id

Format JSON : {"suggestions": [{"label", "priority", "kb_item_id", "deadline"}]}"""


def _stub_suggestions(kb_context):
    """Fallback déterministe : extrait les actions directement des items KB."""
    suggestions = []
    for item in kb_context.get("applicable_items", [])[:5]:
        for action in (item.get("actions") or [])[:2]:
            suggestions.append(
                {
                    "label": action.get("label", ""),
                    "priority": action.get("priority", action.get("severity", "medium")),
                    "kb_item_id": item["kb_item_id"],
                    "deadline": action.get("deadline"),
                    "is_ai_suggestion": True,
                }
            )
    return suggestions[:6]


def run(db, site_id: int, **kwargs):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    kb_context = build_kb_context(site, domain="reglementaire")

    client = get_client()
    user_prompt = (
        f"Site {site.nom} (surface {site.surface_m2 or 0} m², type {site.type or 'N/A'}).\n\n"
        f"{kb_context['prompt_section']}\n\n"
        f"Sélectionne 3-5 actions prioritaires parmi les items KB ci-dessus, "
        f"reformulées pour ce site. Respecte le format JSON attendu."
    )

    response = client.complete(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

    is_stub = "[AI Stub Mode]" in response or "[AI Fallback]" in response

    if is_stub:
        content = {
            "suggestions": _stub_suggestions(kb_context),
            "kb_item_ids": kb_context["kb_item_ids"],
            "is_ai_suggestion": True,
            "mode": "stub",
        }
    else:
        try:
            parsed = json.loads(response)
            content = {
                "suggestions": parsed.get("suggestions", []),
                "kb_item_ids": kb_context["kb_item_ids"],
                "is_ai_suggestion": True,
                "mode": "live",
            }
        except json.JSONDecodeError:
            content = {
                "suggestions": _stub_suggestions(kb_context),
                "raw_response": response,
                "kb_item_ids": kb_context["kb_item_ids"],
                "is_ai_suggestion": True,
                "mode": "live_fallback",
            }

    insight = AiInsight(
        object_type="site",
        object_id=site_id,
        insight_type=InsightType.SUGGEST,
        content_json=json.dumps(content, ensure_ascii=False),
        ai_version=client.model,
        sources_used_json=json.dumps(kb_context["kb_item_ids"]),
    )
    db.add(insight)
    db.commit()
    return insight
