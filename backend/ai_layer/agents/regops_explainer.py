"""
PROMEOS AI - RegOps Explainer (2-min site brief)
Live Claude API + fallback stub.
"""

import json
from datetime import datetime
from models import Site, AiInsight, InsightType
from ..client import get_client
from ..kb_context import build_kb_prompt_section

SYSTEM_PROMPT = """Tu es un expert en réglementation énergétique française pour les bâtiments tertiaires.
Contexte PROMEOS : plateforme B2B de gestion énergétique multi-sites, post-ARENH/VNU (depuis 01/01/2026).

Tu dois :
- Fournir un brief concis (3-5 paragraphes) sur le statut réglementaire du site
- Citer les obligations applicables (Décret Tertiaire, BACS, DPE, OPERAT)
- Utiliser les unités : kWh, m², €, dates au format FR (JJ/MM/AAAA)
- Citer tes sources : données du site, règles réglementaires applicables
- Identifier les risques et recommander des actions prioritaires

Format de sortie : JSON structuré avec les clés : brief, risks, recommendations, sources"""


def _build_user_prompt(site):
    return f"""Site : {site.nom}
Type : {site.type or "Non renseigné"}
Surface : {site.surface_m2 or 0} m²
Ville : {site.ville or "Non renseignée"}

Statut réglementaire :
- Décret Tertiaire : {site.statut_decret_tertiaire or "Non évalué"}
- BACS : {site.statut_bacs or "Non évalué"}
- Risque financier : {site.risque_financier_euro or 0} EUR
- Avancement décret : {getattr(site, "avancement_decret_pct", 0) or 0}%

Génère un brief réglementaire de 2 minutes pour ce site."""


def _stub_response(site):
    """Fallback déterministe quand l'IA n'est pas disponible."""
    return {
        "brief": (
            f"[Stub] Le site {site.nom} ({site.surface_m2 or 0} m²) "
            f"est soumis au Décret Tertiaire (objectif -40% en 2030). "
            f"Statut actuel : {site.statut_decret_tertiaire or 'non évalué'}. "
            f"Risque financier estimé : {site.risque_financier_euro or 0} EUR."
        ),
        "sources_used": ["site_data"],
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

    client = get_client()
    user_prompt = _build_user_prompt(site)

    # Injection contexte KB
    kb_section = build_kb_prompt_section(
        site_context={"energy_vector": ["ELEC"], "building_type": site.type},
        domain="reglementaire",
    )
    enriched_prompt = SYSTEM_PROMPT + kb_section if kb_section else SYSTEM_PROMPT

    response_text = client.complete(
        system_prompt=enriched_prompt,
        user_prompt=user_prompt,
    )

    # Determine mode from response
    is_stub = "[AI Stub Mode]" in response_text or "[AI Fallback]" in response_text

    if is_stub:
        content = _stub_response(site)
    else:
        # Try to parse structured JSON from live response
        try:
            content = json.loads(response_text)
            content["mode"] = "live"
            content["confidence"] = "high"
            content["needs_human_review"] = False
        except json.JSONDecodeError:
            content = {
                "brief": response_text,
                "sources_used": ["site_data", "claude_api"],
                "assumptions": [],
                "confidence": "medium",
                "needs_human_review": True,
                "mode": "live",
            }

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
