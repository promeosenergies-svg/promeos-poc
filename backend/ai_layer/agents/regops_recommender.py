"""
PROMEOS AI - RegOps Recommender (suggestions tagged AI_SUGGESTION)
"""

import json
from models import Site, AiInsight, InsightType
from ..client import get_client
from ..kb_context import build_kb_prompt_section


def run(db, site_id: int, **kwargs):
    client = get_client()
    site = db.query(Site).filter(Site.id == site_id).first()

    base_prompt = "Expert en optimisation energetique. Suggere des actions (AI_SUGGESTION tag)."
    kb_section = build_kb_prompt_section(
        site_context={"energy_vector": ["ELEC"], "building_type": getattr(site, "type", None)},
        domain="reglementaire",
    )
    system_prompt = base_prompt + kb_section if kb_section else base_prompt

    response = client.complete(
        system_prompt=system_prompt,
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
