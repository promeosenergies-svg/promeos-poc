"""
PROMEOS AI - Executive Brief Agent (portfolio narrative)
Live Claude API + fallback stub.
"""

import json
from sqlalchemy import func
from models import AiInsight, InsightType, Site, Portefeuille, EntiteJuridique, Organisation
from ..client import get_client
from ..kb_context import build_kb_prompt_section

SYSTEM_PROMPT = """Tu es un directeur énergie-environnement d'un grand groupe tertiaire français.
Contexte PROMEOS : plateforme B2B de gestion énergétique multi-sites, post-ARENH/VNU (depuis 01/01/2026).

Tu dois :
- Fournir un brief exécutif de 2 minutes pour le DG
- Résumer la situation du portefeuille immobilier : conformité, risques, consommation
- Prioriser les 3 actions les plus urgentes
- Utiliser les unités : kWh, m², €, dates au format FR
- Être factuel et chiffré, pas de langue de bois

Format : JSON avec les clés : executive_summary, key_metrics, top_3_actions, risks, outlook"""


def _gather_portfolio_data(db, org_id):
    """Collecte les métriques clés du portefeuille."""
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        return {"org_name": "Inconnue", "total_sites": 0}

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
    }


def _stub_response(data):
    """Fallback déterministe."""
    return {
        "executive_summary": (
            f"[Stub] Le portefeuille {data['org_name']} comprend {data['total_sites']} sites "
            f"pour {data.get('total_surface_m2', 0):,.0f} m². "
            f"Risque financier total : {data.get('total_risk_eur', 0):,.0f} EUR."
        ),
        "key_metrics": data,
        "top_3_actions": ["Configurer AI_API_KEY pour l'analyse IA complète"],
        "risks": [],
        "outlook": "Non disponible en mode stub.",
        "mode": "stub",
        "confidence": "low",
    }


def run(db, org_id: int = 1, **kwargs):
    """Génère un brief exécutif pour le portefeuille de l'organisation."""
    client = get_client()
    data = _gather_portfolio_data(db, org_id)

    user_prompt = f"""Organisation : {data["org_name"]}
Portefeuille : {data["total_sites"]} sites, {data.get("total_surface_m2", 0):,.0f} m²
Risque financier total : {data.get("total_risk_eur", 0):,.0f} EUR
Avancement moyen Décret Tertiaire : {data.get("avg_avancement_pct", 0)}%

Génère un brief exécutif de 2 minutes."""

    # Injection contexte KB
    kb_section = build_kb_prompt_section(domain="facturation")
    enriched_system = SYSTEM_PROMPT + kb_section if kb_section else SYSTEM_PROMPT

    response_text = client.complete(
        system_prompt=enriched_system,
        user_prompt=user_prompt,
    )

    is_stub = "[AI Stub Mode]" in response_text or "[AI Fallback]" in response_text

    if is_stub:
        content = _stub_response(data)
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

    insight = AiInsight(
        object_type="org",
        object_id=org_id,
        insight_type=InsightType.EXEC_BRIEF,
        content_json=json.dumps(content, ensure_ascii=False),
        ai_version=client.model,
        sources_used_json=json.dumps(["portfolio_data"]),
    )
    db.add(insight)
    db.commit()
    return insight
