"""
PROMEOS AI - Data Quality Agent

HARD RULE : s'appuie sur la KB usages (archétypes sectoriels + règles anomalies)
pour qualifier la qualité des données d'un site (ratios kWh/m², profils attendus).
"""

import json

from models import AiInsight, InsightType, Site

from ..client import get_client
from .kb_context import build_kb_context

SYSTEM_PROMPT = """Expert en qualité de données énergétiques pour bâtiments tertiaires.

Ta mission : évaluer la cohérence des données d'un site en les confrontant aux
ratios et règles d'anomalie issus de la KB PROMEOS (archétypes sectoriels).

RÈGLES STRICTES :
- Ne cite QUE des ratios/seuils présents dans les items KB fournis
- Pour chaque anomalie, référence le kb_item_id d'origine [ID]
- N'invente PAS de "ratio typique" ni de "seuil métier"

Format JSON : {"anomalies": [...], "missing_data": [...], "quality_score": 0-100, "kb_item_ids": [...]}"""


def _stub_analysis(site, kb_context):
    """Fallback : liste les données manquantes, sans inventer."""
    missing = []
    if not site.surface_m2:
        missing.append("surface_m2 (nécessaire pour ratios KB)")
    if not getattr(site, "hvac_kw", None):
        missing.append("hvac_kw (seuils BACS)")
    if not getattr(site, "type", None):
        missing.append("type (archétype sectoriel)")

    applicable = kb_context.get("applicable_items", [])
    quality_score = max(0, 100 - len(missing) * 25)

    return {
        "anomalies": [],
        "missing_data": missing,
        "quality_score": quality_score,
        "kb_item_ids": kb_context["kb_item_ids"],
        "kb_items_available": len(applicable),
        "mode": "stub",
        "note": "Mode stub — l'analyse IA confrontant les ratios nécessite AI_API_KEY.",
    }


def run(db, site_id: int, **kwargs):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    kb_context = build_kb_context(site, domain="usages")

    client = get_client()
    user_prompt = (
        f"Site {site.nom}\n"
        f"Type : {getattr(site, 'type', 'N/A')}\n"
        f"Surface : {site.surface_m2 or 0} m²\n"
        f"CVC : {getattr(site, 'hvac_kw', 0) or 0} kW\n\n"
        f"{kb_context['prompt_section']}\n\n"
        f"Évalue la qualité des données du site en les confrontant aux ratios KB ci-dessus."
    )

    response = client.complete(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
    is_stub = "[AI Stub Mode]" in response or "[AI Fallback]" in response

    if is_stub:
        content = _stub_analysis(site, kb_context)
    else:
        try:
            content = json.loads(response)
            content["mode"] = "live"
        except json.JSONDecodeError:
            content = {"analysis": response, "mode": "live_fallback"}
        content.setdefault("kb_item_ids", kb_context["kb_item_ids"])

    insight = AiInsight(
        object_type="site",
        object_id=site_id,
        insight_type=InsightType.DATA_QUALITY,
        content_json=json.dumps(content, ensure_ascii=False),
        ai_version=client.model,
        sources_used_json=json.dumps(kb_context["kb_item_ids"]),
    )
    db.add(insight)
    db.commit()
    return insight
