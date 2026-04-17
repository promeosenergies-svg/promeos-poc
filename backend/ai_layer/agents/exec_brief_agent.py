"""
PROMEOS AI - Executive Brief Agent (portfolio narrative)
Live Claude API + fallback stub.

HARD RULE : le brief exec est enrichi avec les items KB validés du portefeuille
(reglementaire + facturation + flex) pour éviter toute hallucination de fait.
"""

import json

from models import AiInsight, EntiteJuridique, InsightType, Organisation, Portefeuille, Site

from ..client import get_client
from .kb_context import build_portfolio_kb_context

SYSTEM_PROMPT = """Tu es un directeur énergie-environnement d'un grand groupe tertiaire français.
Contexte PROMEOS : plateforme B2B de gestion énergétique multi-sites, post-ARENH/VNU (depuis 01/01/2026).

Tu dois :
- Fournir un brief exécutif de 2 minutes pour le DG
- Résumer la situation du portefeuille : conformité, risques, consommation
- Prioriser les 3 actions les plus urgentes tirées des items KB fournis
- T'appuyer EXCLUSIVEMENT sur les items KB validés fournis (pas d'invention)
- Utiliser les unités : kWh, m², €, dates au format FR
- Être factuel et chiffré, pas de langue de bois
- Citer les kb_item_ids utilisés pour traçabilité

Format JSON : executive_summary, key_metrics, top_3_actions, risks, outlook, kb_item_ids"""


def _gather_portfolio_data(db, org_id):
    """Collecte les métriques clés du portefeuille."""
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        return {"org_name": "Inconnue", "total_sites": 0, "sites": []}

    sites = (
        db.query(Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    )

    total_surface = sum(s.surface_m2 or 0 for s in sites)
    total_risk = sum(s.risque_financier_euro or 0 for s in sites)
    avg_avancement = sum(getattr(s, "avancement_decret_pct", 0) or 0 for s in sites) / len(sites) if sites else 0

    return {
        "org_name": org.nom,
        "total_sites": len(sites),
        "total_surface_m2": total_surface,
        "total_risk_eur": total_risk,
        "avg_avancement_pct": round(avg_avancement, 1),
        "sites": sites,
    }


def _stub_response(data, kb_context):
    """Fallback déterministe enrichi avec items KB."""
    top_actions = []
    for item in (kb_context.get("applicable_items") or [])[:3]:
        for action in (item.get("actions") or [])[:1]:
            top_actions.append(f"[{item['kb_item_id']}] {action.get('label', '')}")

    key_metrics = {k: v for k, v in data.items() if k != "sites"}

    return {
        "executive_summary": (
            f"[Stub KB] Portefeuille {data['org_name']} : {data['total_sites']} sites, "
            f"{data.get('total_surface_m2', 0):,.0f} m². "
            f"{kb_context.get('total_items', 0)} items KB applicables. "
            f"Risque financier : {data.get('total_risk_eur', 0):,.0f} EUR."
        ),
        "key_metrics": key_metrics,
        "top_3_actions": top_actions[:3] or ["Aucun item KB applicable — enrichir les données sites"],
        "risks": [],
        "outlook": "Analyse détaillée nécessite AI_API_KEY.",
        "kb_item_ids": kb_context["kb_item_ids"],
        "stats_by_domain": kb_context.get("stats_by_domain", {}),
        "mode": "stub",
        "confidence": "low",
    }


def run(db, org_id: int = 1, **kwargs):
    """Génère un brief exécutif pour le portefeuille de l'organisation."""
    client = get_client()
    data = _gather_portfolio_data(db, org_id)
    sites = data.pop("sites", [])

    kb_context = build_portfolio_kb_context(sites)

    user_prompt = f"""Organisation : {data["org_name"]}
Portefeuille : {data["total_sites"]} sites, {data.get("total_surface_m2", 0):,.0f} m²
Risque financier total : {data.get("total_risk_eur", 0):,.0f} EUR
Avancement moyen Décret Tertiaire : {data.get("avg_avancement_pct", 0)}%

{kb_context["prompt_section"]}

Génère un brief exécutif de 2 minutes en t'appuyant STRICTEMENT sur les items KB."""

    response_text = client.complete(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    is_stub = "[AI Stub Mode]" in response_text or "[AI Fallback]" in response_text

    if is_stub:
        content = _stub_response(data, kb_context)
    else:
        try:
            content = json.loads(response_text)
            content["mode"] = "live"
            content["confidence"] = "high"
        except json.JSONDecodeError:
            content = {
                "executive_summary": response_text,
                "key_metrics": data,
                "mode": "live",
                "confidence": "medium",
            }
        content.setdefault("kb_item_ids", kb_context["kb_item_ids"])
        content["stats_by_domain"] = kb_context.get("stats_by_domain", {})

    insight = AiInsight(
        object_type="org",
        object_id=org_id,
        insight_type=InsightType.EXEC_BRIEF,
        content_json=json.dumps(content, ensure_ascii=False),
        ai_version=client.model,
        sources_used_json=json.dumps(["portfolio_data"] + kb_context["kb_item_ids"]),
    )
    db.add(insight)
    db.commit()
    return insight
