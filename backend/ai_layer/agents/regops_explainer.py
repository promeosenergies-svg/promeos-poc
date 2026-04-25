"""
PROMEOS AI - RegOps Explainer (2-min site brief)
Live Claude API + fallback stub.

HARD RULE doctrine PROMEOS : toute recommandation réglementaire DOIT
s'appuyer sur des items KB validated (cf. app/kb/service.py).
Le prompt est enrichi avec KBService.apply() avant appel LLM.
"""

import json

from models import AiInsight, InsightType, Site

from ..client import get_client
from .kb_context import build_kb_context

SYSTEM_PROMPT = """Tu es un expert en réglementation énergétique française pour les bâtiments tertiaires.
Contexte PROMEOS : plateforme B2B de gestion énergétique multi-sites, post-ARENH/VNU (depuis 01/01/2026).

Tu dois :
- Fournir un brief concis (3-5 paragraphes) sur le statut réglementaire du site
- T'appuyer EXCLUSIVEMENT sur les items KB validés fournis dans le contexte
- NE PAS inventer de faits réglementaires absents des items KB (pas de décret ni date ni seuil hors liste)
- Utiliser les unités : kWh, m², €, dates au format FR (JJ/MM/AAAA)
- Citer les IDs des items KB utilisés (ex: [BACS-290KW], [DT-SCOPE-1000M2])
- Identifier les risques et recommander des actions prioritaires tirées des items KB

Format de sortie : JSON structuré avec les clés : brief, risks, recommendations, sources, kb_item_ids"""


def _build_user_prompt(site, kb_context):
    return f"""Site : {site.nom}
Type : {site.type or "Non renseigné"}
Surface : {site.surface_m2 or 0} m²
Ville : {site.ville or "Non renseignée"}

Statut réglementaire :
- Décret Tertiaire : {site.statut_decret_tertiaire or "Non évalué"}
- BACS : {site.statut_bacs or "Non évalué"}
- Risque financier : {site.risque_financier_euro or 0} EUR
- Avancement décret : {getattr(site, "avancement_decret_pct", 0) or 0}%

{kb_context["prompt_section"]}

Génère un brief réglementaire de 2 minutes pour ce site, en t'appuyant STRICTEMENT
sur les items KB listés ci-dessus."""


def _stub_response(site, kb_context):
    """Fallback déterministe quand l'IA n'est pas disponible.

    Même en stub, on s'appuie sur les items KB pour ne pas halluciner.
    """
    items = kb_context.get("applicable_items", [])
    item_ids = kb_context.get("kb_item_ids", [])

    if items:
        applicable_summary = ", ".join(f"{i['title'][:60]} [{i['kb_item_id']}]" for i in items[:3])
        brief = (
            f"[Stub KB] Site {site.nom} ({site.surface_m2 or 0} m²). "
            f"{len(items)} item(s) KB applicable(s) : {applicable_summary}. "
            f"Statut : {site.statut_decret_tertiaire or 'non évalué'}. "
            f"Risque : {site.risque_financier_euro or 0} EUR."
        )
    else:
        brief = (
            f"[Stub KB] Site {site.nom}. Aucun item KB validé applicable au contexte "
            f"actuel. Vérifier la qualité des données du site (surface, puissance CVC, type)."
        )

    return {
        "brief": brief,
        "sources_used": ["site_data"] + item_ids,
        "kb_item_ids": item_ids,
        "assumptions": ["Mode stub — configurez AI_API_KEY pour l'analyse IA"],
        "confidence": "low",
        "needs_human_review": True,
        "mode": "stub",
    }


def run(db, site_id: int, **kwargs):
    """
    Génère un brief de 2 minutes sur le statut réglementaire du site.
    HARD RULE : Ne modifie JAMAIS le statut déterministe.
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    # KB-first : on évalue la KB avant tout appel LLM
    kb_context = build_kb_context(site, domain="reglementaire")

    client = get_client()
    user_prompt = _build_user_prompt(site, kb_context)

    response_text = client.complete(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    is_stub = "[AI Stub Mode]" in response_text or "[AI Fallback]" in response_text

    if is_stub:
        content = _stub_response(site, kb_context)
    else:
        try:
            content = json.loads(response_text)
            content["mode"] = "live"
            content["confidence"] = "high"
            content["needs_human_review"] = False
        except json.JSONDecodeError:
            content = {
                "brief": response_text,
                "sources_used": ["site_data", "claude_api"] + kb_context["kb_item_ids"],
                "kb_item_ids": kb_context["kb_item_ids"],
                "assumptions": [],
                "confidence": "medium",
                "needs_human_review": True,
                "mode": "live",
            }

        # Traçabilité : toujours inclure les items KB utilisés
        content.setdefault("kb_item_ids", kb_context["kb_item_ids"])
        if kb_context["kb_item_ids"]:
            existing_sources = content.get("sources_used", []) or []
            content["sources_used"] = list(dict.fromkeys(existing_sources + kb_context["kb_item_ids"]))

    insight = AiInsight(
        object_type="site",
        object_id=site_id,
        insight_type=InsightType.EXPLAIN,
        content_json=json.dumps(content, ensure_ascii=False),
        ai_version=client.model,
        sources_used_json=json.dumps(content.get("sources_used", ["site"])),
    )
    db.add(insight)
    db.commit()

    return insight
