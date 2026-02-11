"""
PROMEOS - Dashboard "2 minutes"
GET /api/dashboard/2min - Vue synthetique en 3 blocs pour un prospect
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import (
    Organisation, Site, Obligation, Compteur, ComplianceFinding,
    ConsumptionInsight, StatutConformite, TypeObligation,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard 2min"])


@router.get("/2min")
def get_dashboard_2min(db: Session = Depends(get_db)):
    """
    Retourne un JSON minimal pour le cockpit "2 minutes":
    - conformite_status: etat global conformite
    - pertes_estimees_eur: risque financier total
    - action_1: action prioritaire (#1)
    - organisation: nom + type
    - completude: % de remplissage du patrimoine
    """
    org = db.query(Organisation).first()
    if not org:
        return {
            "has_data": False,
            "conformite_status": None,
            "pertes_estimees_eur": None,
            "action_1": None,
            "organisation": None,
            "completude": _empty_completude(),
        }

    # Stats sites
    total_sites = db.query(Site).count()
    sites_actifs = db.query(Site).filter(Site.actif == True).count()
    total_compteurs = db.query(Compteur).count()

    # Conformite globale
    obligations = db.query(Obligation).all()
    if obligations:
        nb_conforme = sum(1 for o in obligations if o.statut == StatutConformite.CONFORME)
        nb_non_conforme = sum(1 for o in obligations if o.statut == StatutConformite.NON_CONFORME)
        nb_a_risque = sum(1 for o in obligations if o.statut == StatutConformite.A_RISQUE)
        total_obl = len(obligations)

        if nb_non_conforme > 0:
            conformite_label = "Non conforme"
            conformite_color = "red"
        elif nb_a_risque > 0:
            conformite_label = "A risque"
            conformite_color = "orange"
        elif nb_conforme == total_obl:
            conformite_label = "Conforme"
            conformite_color = "green"
        else:
            conformite_label = "En cours"
            conformite_color = "blue"

        conformite_status = {
            "label": conformite_label,
            "color": conformite_color,
            "obligations_total": total_obl,
            "conformes": nb_conforme,
            "a_risque": nb_a_risque,
            "non_conformes": nb_non_conforme,
        }
    else:
        conformite_status = {
            "label": "A evaluer",
            "color": "gray",
            "obligations_total": 0,
            "conformes": 0,
            "a_risque": 0,
            "non_conformes": 0,
        }

    # Risque financier (base: obligations) + pertes estimees (insights conso)
    risque_total = db.query(func.sum(Site.risque_financier_euro)).scalar() or 0
    pertes_conso = db.query(func.sum(ConsumptionInsight.estimated_loss_eur)).scalar() or 0

    # Action prioritaire #1
    action_1 = _get_top_action(db, obligations)

    # Completude du patrimoine
    completude = _compute_completude(total_sites, total_compteurs, org)

    # ComplianceFinding-based summary (Sprint 4)
    findings = db.query(ComplianceFinding).all()
    nok_findings = [f for f in findings if f.status == "NOK"]
    unknown_findings = [f for f in findings if f.status == "UNKNOWN"]

    findings_summary = None
    if findings:
        findings_summary = {
            "total": len(findings),
            "nok": len(nok_findings),
            "unknown": len(unknown_findings),
            "ok": sum(1 for f in findings if f.status == "OK"),
        }
        # Override action_1 from findings if more specific
        if nok_findings:
            import json
            nok_findings.sort(
                key=lambda f: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(f.severity, 0),
                reverse=True,
            )
            top = nok_findings[0]
            actions = json.loads(top.recommended_actions_json) if top.recommended_actions_json else []
            if actions:
                action_1 = {
                    "texte": actions[0],
                    "priorite": top.severity or "high",
                    "nb_sites_concernes": len(set(f.site_id for f in nok_findings if f.rule_id == top.rule_id)),
                    "reglementation": top.regulation,
                }

    # V1.1: If no critical compliance NOK, try top conso insight for action_1
    if not nok_findings:
        import json as _json
        top_insight = (
            db.query(ConsumptionInsight)
            .filter(ConsumptionInsight.estimated_loss_eur > 0)
            .order_by(ConsumptionInsight.estimated_loss_eur.desc())
            .first()
        )
        if top_insight and top_insight.recommended_actions_json:
            rec = _json.loads(top_insight.recommended_actions_json)
            if rec:
                site_obj = db.query(Site).filter(Site.id == top_insight.site_id).first()
                action_1 = {
                    "texte": rec[0]["title"],
                    "priorite": top_insight.severity or "high",
                    "nb_sites_concernes": 1,
                    "reglementation": None,
                    "source": "conso_insight",
                    "site_nom": site_obj.nom if site_obj else None,
                    "expected_gain_eur": rec[0].get("expected_gain_eur", 0),
                }

    return {
        "has_data": True,
        "organisation": {
            "nom": org.nom,
            "type_client": org.type_client,
        },
        "conformite_status": conformite_status,
        "pertes_estimees_eur": round(risque_total + pertes_conso, 2),
        "action_1": action_1,
        "completude": completude,
        "findings_summary": findings_summary,
        "stats": {
            "total_sites": total_sites,
            "sites_actifs": sites_actifs,
            "total_compteurs": total_compteurs,
            "total_obligations": len(obligations),
        },
    }


def _get_top_action(db: Session, obligations) -> dict:
    """Determine l'action prioritaire #1."""
    # Priorite: non_conforme decret_tertiaire > non_conforme bacs > a_risque decret > a_risque bacs
    priority_order = [
        (TypeObligation.DECRET_TERTIAIRE, StatutConformite.NON_CONFORME,
         "Declarer vos consommations sur OPERAT", "critical"),
        (TypeObligation.BACS, StatutConformite.NON_CONFORME,
         "Installer un systeme GTB/GTC conforme", "critical"),
        (TypeObligation.DECRET_TERTIAIRE, StatutConformite.A_RISQUE,
         "Accelerer votre trajectoire Decret Tertiaire 2030", "high"),
        (TypeObligation.BACS, StatutConformite.A_RISQUE,
         "Planifier la mise en conformite BACS", "high"),
    ]

    for obl_type, obl_statut, action_text, priority in priority_order:
        matching = [o for o in obligations if o.type == obl_type and o.statut == obl_statut]
        if matching:
            return {
                "texte": action_text,
                "priorite": priority,
                "nb_sites_concernes": len(set(o.site_id for o in matching)),
                "reglementation": obl_type.value,
            }

    # Si tout est conforme ou pas d'obligations
    if not obligations:
        return {
            "texte": "Ajouter vos sites pour evaluer votre conformite",
            "priorite": "info",
            "nb_sites_concernes": 0,
            "reglementation": None,
        }

    return {
        "texte": "Maintenir votre conformite et surveiller les echeances",
        "priorite": "low",
        "nb_sites_concernes": 0,
        "reglementation": None,
    }


def _compute_completude(total_sites: int, total_compteurs: int, org) -> dict:
    """Calcule le % de completude du patrimoine."""
    checks = {
        "organisation": org is not None,
        "sites": total_sites > 0,
        "compteurs": total_compteurs > 0,
    }
    done = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "pct": round(done / total * 100),
        "checks": checks,
        "message": "Patrimoine complet" if done == total else f"{total - done} etape(s) restante(s)",
    }


def _empty_completude() -> dict:
    return {
        "pct": 0,
        "checks": {"organisation": False, "sites": False, "compteurs": False},
        "message": "Creez votre organisation pour commencer",
    }
