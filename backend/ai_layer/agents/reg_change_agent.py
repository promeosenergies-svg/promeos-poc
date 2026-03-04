"""
PROMEOS AI - Regulatory Change Impact Agent
"""

import json
from models import AiInsight, InsightType
from ..client import get_client


def run(db, event_id: int, **kwargs):
    client = get_client()
    response = client.complete("Regulatory expert", f"Analyze impact of event {event_id}")
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
