"""
PROMEOS AI - Data Quality Agent
"""

import json
from models import AiInsight, InsightType
from ..client import get_client


def run(db, site_id: int, **kwargs):
    client = get_client()
    response = client.complete("Data quality expert", f"Analyze site {site_id} data quality")
    insight = AiInsight(
        object_type="site",
        object_id=site_id,
        insight_type=InsightType.DATA_QUALITY,
        content_json=json.dumps({"analysis": response}),
        ai_version=client.model,
    )
    db.add(insight)
    db.commit()
    return insight
