"""
PROMEOS AI - RegOps Explainer (2-min site brief)
"""

import json
from datetime import datetime
from models import Site, AiInsight, InsightType
from ..client import get_client


def run(db, site_id: int, **kwargs):
    """
    Genere un brief de 2 minutes sur le statut reglementaire du site.
    HARD RULE: Ne modifie JAMAIS le statut deterministe.
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    client = get_client()

    user_prompt = f"""Site: {site.nom}
Type: {site.type}
Surface: {site.surface_m2}m2
Statut deterministe:
- Decret tertiaire: {site.statut_decret_tertiaire}
- BACS: {site.statut_bacs}
- Risque financier: {site.risque_financier_euro}EUR

Brief de 2 minutes sur le statut reglementaire du site."""

    response = client.complete(
        system_prompt="Tu es un expert en reglementation energetique francaise. Fournis un brief concis.",
        user_prompt=user_prompt,
    )

    # Create AiInsight
    insight = AiInsight(
        object_type="site",
        object_id=site_id,
        insight_type=InsightType.EXPLAIN,
        content_json=json.dumps(
            {
                "brief": response,
                "sources_used": ["site_data"],
                "assumptions": ["Stub mode AI"],
                "confidence": "low",
                "needs_human_review": True,
            }
        ),
        ai_version=client.model,
        sources_used_json=json.dumps(["site"]),
    )
    db.add(insight)
    db.commit()

    return insight
