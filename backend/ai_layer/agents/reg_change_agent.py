"""
PROMEOS AI - Regulatory Change Impact Agent
"""

import json
from models import AiInsight, InsightType
from ..client import get_client
from ..kb_context import build_kb_prompt_section


def run(db, event_id: int, **kwargs):
    client = get_client()
    kb_section = build_kb_prompt_section(domain="reglementaire")
    system_prompt = "Regulatory expert" + kb_section if kb_section else "Regulatory expert"
    response = client.complete(system_prompt, f"Analyze impact of event {event_id}")
    insight = AiInsight(
        object_type="event",
        object_id=event_id,
        insight_type=InsightType.CHANGE_IMPACT,
        content_json=json.dumps({"impact": response}),
        ai_version=client.model,
    )
    db.add(insight)
    db.commit()
    return insight
