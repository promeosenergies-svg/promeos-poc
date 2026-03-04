"""
PROMEOS AI - RegOps Recommender (suggestions tagged AI_SUGGESTION)
"""

import json
from models import Site, AiInsight, InsightType
from ..client import get_client


def run(db, site_id: int, **kwargs):
    client = get_client()
    site = db.query(Site).filter(Site.id == site_id).first()

    response = client.complete(
        system_prompt="Expert en optimisation energetique. Suggere des actions (AI_SUGGESTION tag).",
        user_prompt=f"Site {site.nom}: suggere 3 actions d'optimisation.",
    )

    insight = AiInsight(
        object_type="site",
        object_id=site_id,
        insight_type=InsightType.SUGGEST,
        content_json=json.dumps({"suggestions": response, "is_ai_suggestion": True}),
        ai_version=client.model,
    )
    db.add(insight)
    db.commit()
    return insight
