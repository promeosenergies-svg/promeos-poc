"""
PROMEOS - Action Plan Engine
Generates a prioritized, cross-portfolio action plan from compliance data.
"Waze for energy compliance" - tells the user what to do next, in order.
"""
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    Site, Obligation, Evidence, Portefeuille,
    StatutConformite, TypeObligation, StatutEvidence,
    not_deleted,
)

# Priority weight: higher = more urgent
_PRIORITY_WEIGHTS = {
    (TypeObligation.BACS, StatutConformite.NON_CONFORME): 100,
    (TypeObligation.DECRET_TERTIAIRE, StatutConformite.NON_CONFORME): 90,
    (TypeObligation.BACS, StatutConformite.A_RISQUE): 70,
    (TypeObligation.DECRET_TERTIAIRE, StatutConformite.A_RISQUE): 60,
}

_ACTION_LABELS = {
    (TypeObligation.BACS, StatutConformite.NON_CONFORME):
        "Installer GTB/GTC conforme (BACS obligatoire)",
    (TypeObligation.DECRET_TERTIAIRE, StatutConformite.NON_CONFORME):
        "Lancer audit decret tertiaire - trajectoire 2030 KO",
    (TypeObligation.BACS, StatutConformite.A_RISQUE):
        "Planifier mise en conformite BACS avant echeance",
    (TypeObligation.DECRET_TERTIAIRE, StatutConformite.A_RISQUE):
        "Accelerer trajectoire decret tertiaire",
}


def compute_action_plan(
    db: Session,
    portefeuille_id: Optional[int] = None,
    site_id: Optional[int] = None,
) -> dict:
    """
    Build prioritized action plan across all sites (or filtered by portfolio/site).
    Uses bulk queries (no N+1).
    """
    site_query = not_deleted(db.query(Site), Site).filter(Site.actif == True)
    if site_id:
        site_query = site_query.filter(Site.id == site_id)
    elif portefeuille_id:
        site_query = site_query.filter(Site.portefeuille_id == portefeuille_id)
    sites = site_query.all()
    site_ids = [s.id for s in sites]

    if not site_ids:
        return {
            "total_actions": 0,
            "readiness_score": 0.0,
            "actions": [],
            "summary": {
                "total_sites": 0,
                "sites_conformes": 0,
                "sites_a_risque": 0,
                "sites_non_conformes": 0,
                "risque_financier_total": 0.0,
                "evidence_gaps_total": 0,
            },
        }

    # Bulk load
    all_obligations = db.query(Obligation).filter(
        Obligation.site_id.in_(site_ids)
    ).all()
    all_evidences = db.query(Evidence).filter(
        Evidence.site_id.in_(site_ids)
    ).all()

    obs_by_site = defaultdict(list)
    for ob in all_obligations:
        obs_by_site[ob.site_id].append(ob)

    evs_by_site = defaultdict(list)
    for ev in all_evidences:
        evs_by_site[ev.site_id].append(ev)

    # Portfolio names
    ptf_ids = list({s.portefeuille_id for s in sites if s.portefeuille_id})
    ptf_map = {}
    if ptf_ids:
        ptfs = db.query(Portefeuille).filter(Portefeuille.id.in_(ptf_ids)).all()
        ptf_map = {p.id: p.nom for p in ptfs}

    # Build actions
    actions = []
    sites_conformes = 0
    sites_a_risque = 0
    sites_non_conformes = 0
    risque_total = 0.0
    evidence_gaps_total = 0

    for site in sites:
        site_obs = obs_by_site.get(site.id, [])
        site_evs = evs_by_site.get(site.id, [])
        evidence_gaps = sum(1 for e in site_evs if e.statut == StatutEvidence.MANQUANT)
        evidence_gaps_total += evidence_gaps

        # Actions from non-conforme/a_risque obligations
        for ob in site_obs:
            key = (ob.type, ob.statut)
            weight = _PRIORITY_WEIGHTS.get(key)
            if weight:
                actions.append({
                    "site_id": site.id,
                    "site_nom": site.nom,
                    "ville": site.ville or "",
                    "portefeuille_nom": ptf_map.get(site.portefeuille_id, ""),
                    "obligation_type": ob.type.value,
                    "statut": ob.statut.value,
                    "action_label": _ACTION_LABELS.get(key, "Action requise"),
                    "priority": weight,
                    "risque_financier_euro": site.risque_financier_euro or 0,
                    "avancement_pct": ob.avancement_pct,
                    "echeance": ob.echeance.isoformat() if ob.echeance else None,
                    "evidence_gaps": evidence_gaps,
                })

        # Evidence gap action
        if evidence_gaps > 0:
            actions.append({
                "site_id": site.id,
                "site_nom": site.nom,
                "ville": site.ville or "",
                "portefeuille_nom": ptf_map.get(site.portefeuille_id, ""),
                "obligation_type": "evidence",
                "statut": "manquant",
                "action_label": f"Fournir {evidence_gaps} preuve(s) manquante(s)",
                "priority": 50,
                "risque_financier_euro": 0,
                "avancement_pct": 0,
                "echeance": None,
                "evidence_gaps": evidence_gaps,
            })

        # Classify for summary
        risque_total += site.risque_financier_euro or 0
        if site.statut_decret_tertiaire == StatutConformite.NON_CONFORME or \
           site.statut_bacs == StatutConformite.NON_CONFORME:
            sites_non_conformes += 1
        elif site.statut_decret_tertiaire == StatutConformite.A_RISQUE or \
             site.statut_bacs == StatutConformite.A_RISQUE:
            sites_a_risque += 1
        else:
            sites_conformes += 1

    # Sort by priority DESC, then risque_financier DESC
    actions.sort(key=lambda a: (-a["priority"], -a["risque_financier_euro"]))

    # Add rank
    for i, action in enumerate(actions):
        action["rank"] = i + 1

    total_sites = len(sites)
    readiness_score = round(
        (sites_conformes / total_sites * 100) if total_sites > 0 else 0, 1
    )

    return {
        "total_actions": len(actions),
        "readiness_score": readiness_score,
        "actions": actions,
        "summary": {
            "total_sites": total_sites,
            "sites_conformes": sites_conformes,
            "sites_a_risque": sites_a_risque,
            "sites_non_conformes": sites_non_conformes,
            "risque_financier_total": round(risque_total, 2),
            "evidence_gaps_total": evidence_gaps_total,
        },
    }
