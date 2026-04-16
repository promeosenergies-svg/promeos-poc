"""
PROMEOS AI - Data Quality Agent
"""

import json
from models import AiInsight, InsightType
from ..client import get_client
from ..kb_context import build_kb_prompt_section


def run(db, site_id: int, **kwargs):
    client = get_client()
    kb_section = build_kb_prompt_section(domain="facturation")
    system_prompt = "Data quality expert" + kb_section if kb_section else "Data quality expert"
    response = client.complete(system_prompt, f"Analyze site {site_id} data quality")
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
