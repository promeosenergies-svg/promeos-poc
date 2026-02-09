"""
PROMEOS AI - Executive Brief Agent (portfolio narrative)
"""
import json
from models import AiInsight, InsightType
from ..client import get_client


def run(db, org_id: int = 1, **kwargs):
    client = get_client()
    response = client.complete("Executive advisor", f"Portfolio brief for org {org_id}")
    insight = AiInsight(
        object_type="org",
        object_id=org_id,
        insight_type=InsightType.EXEC_BRIEF,
        content_json=json.dumps({"brief": response}),
        ai_version=client.model
    )
    db.add(insight)
    db.commit()
    return insight
