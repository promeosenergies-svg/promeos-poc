"""
PROMEOS AI - Regulatory Change Impact Agent

HARD RULE : l'impact d'un changement réglementaire DOIT être évalué contre les
items KB validated du domaine concerné — pas de jugement libre du LLM.
"""

import json

from models import AiInsight, InsightType

from ..client import get_client
from .kb_context import build_portfolio_kb_context

SYSTEM_PROMPT = """Expert en analyse d'impact réglementaire pour bâtiments tertiaires français.

Ta mission : évaluer l'impact d'un événement réglementaire sur le portefeuille client,
en t'appuyant STRICTEMENT sur les items KB validés fournis.

RÈGLES :
- Ne cite QUE des items KB de la liste fournie
- Pour chaque site impacté, référence les kb_item_ids concernés
- Quantifie l'impact quand possible (€, m², deadline)

Format JSON : {"impact_summary", "impacted_kb_item_ids", "recommended_actions", "urgency"}"""


def run(db, event_id: int, sites: list | None = None, **kwargs):
    """Analyse l'impact d'un événement réglementaire."""
    client = get_client()

    if sites:
        kb_context = build_portfolio_kb_context(sites, domains=["reglementaire", "facturation"])
        context_section = kb_context["prompt_section"]
        kb_ids = kb_context["kb_item_ids"]
    else:
        context_section = "Pas de sites fournis — analyse générique de l'événement."
        kb_ids = []

    user_prompt = (
        f"Événement réglementaire : event_id={event_id}\n"
        f"Portefeuille impacté : {len(sites or [])} sites\n\n"
        f"{context_section}\n\n"
        f"Évalue l'impact sur le portefeuille en t'appuyant sur les items KB ci-dessus."
    )

    response = client.complete(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
    is_stub = "[AI Stub Mode]" in response or "[AI Fallback]" in response

    if is_stub:
        content = {
            "impact_summary": (
                f"[Stub KB] Événement {event_id} : {len(kb_ids)} item(s) KB applicable(s) "
                f"au portefeuille. Revue manuelle recommandée."
            ),
            "impacted_kb_item_ids": kb_ids,
            "recommended_actions": [],
            "urgency": "medium",
            "mode": "stub",
        }
    else:
        try:
            content = json.loads(response)
            content["mode"] = "live"
        except json.JSONDecodeError:
            content = {"impact": response, "impacted_kb_item_ids": kb_ids, "mode": "live_fallback"}
        content.setdefault("impacted_kb_item_ids", kb_ids)

    insight = AiInsight(
        object_type="event",
        object_id=event_id,
        insight_type=InsightType.CHANGE_IMPACT,
        content_json=json.dumps(content, ensure_ascii=False),
        ai_version=client.model,
        sources_used_json=json.dumps(kb_ids),
    )
    db.add(insight)
    db.commit()
    return insight
