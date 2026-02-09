"""
PROMEOS - Compliance Engine
Calculates Site conformity snapshots from their Obligations.
Source of truth: Obligation rows -> derived to Site snapshot fields.
BACS statut is refined using Evidences (attestation_bacs, derogation_bacs).
"""
from collections import defaultdict
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from models import (
    Obligation, Site, Portefeuille, EntiteJuridique, Organisation,
    Evidence,
    StatutConformite, TypeObligation, TypeEvidence, StatutEvidence,
)

# Status severity ranking for "worst status" logic
_STATUS_SEVERITY = {
    StatutConformite.CONFORME: 0,
    StatutConformite.DEROGATION: 1,
    StatutConformite.A_RISQUE: 2,
    StatutConformite.NON_CONFORME: 3,
}

# BACS thresholds (kW CVC nominal)
BACS_SEUIL_HAUT = 290.0   # deadline 2025-01-01
BACS_SEUIL_BAS = 70.0     # deadline 2030-01-01
BACS_DEADLINE_290 = date(2025, 1, 1)
BACS_DEADLINE_70 = date(2030, 1, 1)

# Base penalty per non-conforme obligation (euros)
BASE_PENALTY_EURO = 7500.0

# Action text templates ordered by priority (highest first)
_ACTION_TEMPLATES = [
    (TypeObligation.BACS, StatutConformite.NON_CONFORME,
     "Installer GTB/GTC conforme (BACS obligatoire)"),
    (TypeObligation.DECRET_TERTIAIRE, StatutConformite.NON_CONFORME,
     "Audit decret tertiaire - trajectoire 2030 KO"),
    (TypeObligation.BACS, StatutConformite.A_RISQUE,
     "Planifier mise en conformite BACS avant echeance"),
    (TypeObligation.DECRET_TERTIAIRE, StatutConformite.A_RISQUE,
     "Verifier trajectoire decret tertiaire"),
]


# ========================================
# Layer A: Pure calculation functions
# ========================================

def worst_status(obligations: List[Obligation]) -> Optional[StatutConformite]:
    """Return the worst (most severe) status from a list of obligations."""
    if not obligations:
        return None
    return max(obligations, key=lambda o: _STATUS_SEVERITY[o.statut]).statut


def _worst_from_statuts(statuts: List[StatutConformite]) -> Optional[StatutConformite]:
    """Return the worst status from a plain list of StatutConformite values."""
    if not statuts:
        return None
    return max(statuts, key=lambda s: _STATUS_SEVERITY[s])


def average_avancement(obligations: List[Obligation]) -> float:
    """Return the average avancement_pct across obligations."""
    if not obligations:
        return 0.0
    return round(sum(o.avancement_pct for o in obligations) / len(obligations), 1)


def compute_risque_financier(obligations: List[Obligation]) -> float:
    """Calculate financial risk: BASE_PENALTY_EURO * count(non_conforme)."""
    non_conforme_count = sum(
        1 for o in obligations
        if o.statut == StatutConformite.NON_CONFORME
    )
    return round(BASE_PENALTY_EURO * non_conforme_count, 2)


def compute_action_recommandee(obligations: List[Obligation]) -> Optional[str]:
    """Return the highest-priority recommended action."""
    for ob_type, ob_statut, action_text in _ACTION_TEMPLATES:
        for o in obligations:
            if o.type == ob_type and o.statut == ob_statut:
                return action_text
    return None


def bacs_deadline_for_power(cvc_power_kw: float) -> Optional[date]:
    """Return the BACS regulatory deadline based on CVC power.

    >290 kW -> 2025-01-01
    >70 kW  -> 2030-01-01
    <=70 kW -> None (not concerned)
    """
    if cvc_power_kw > BACS_SEUIL_HAUT:
        return BACS_DEADLINE_290
    if cvc_power_kw > BACS_SEUIL_BAS:
        return BACS_DEADLINE_70
    return None


def compute_bacs_statut(
    evidences: List[Evidence],
    echeance: date,
    today: Optional[date] = None,
) -> StatutConformite:
    """
    Compute BACS obligation statut from evidences and deadline.

    Priority:
    1. Valid DEROGATION_BACS evidence  -> DEROGATION
    2. Valid ATTESTATION_BACS evidence -> CONFORME
    3. Deadline passed (today > echeance) -> NON_CONFORME
    4. Otherwise -> A_RISQUE
    """
    if today is None:
        today = date.today()

    bacs_evidences = [
        e for e in evidences
        if e.type in (TypeEvidence.ATTESTATION_BACS, TypeEvidence.DEROGATION_BACS)
    ]

    has_valid_derogation = any(
        e.type == TypeEvidence.DEROGATION_BACS and e.statut == StatutEvidence.VALIDE
        for e in bacs_evidences
    )
    if has_valid_derogation:
        return StatutConformite.DEROGATION

    has_valid_attestation = any(
        e.type == TypeEvidence.ATTESTATION_BACS and e.statut == StatutEvidence.VALIDE
        for e in bacs_evidences
    )
    if has_valid_attestation:
        return StatutConformite.CONFORME

    if today > echeance:
        return StatutConformite.NON_CONFORME

    return StatutConformite.A_RISQUE


def compute_site_snapshot(
    obligations: List[Obligation],
    evidences: Optional[List[Evidence]] = None,
) -> dict:
    """
    Compute all Site snapshot fields from Obligations (+ Evidences for BACS).
    Does NOT touch anomalie_facture (not derivable from obligations).

    Pure function: does NOT mutate the obligation objects.
    """
    decret = [o for o in obligations if o.type == TypeObligation.DECRET_TERTIAIRE]
    bacs = [o for o in obligations if o.type == TypeObligation.BACS]

    # Resolve BACS statuts without mutating obligations
    if evidences is not None:
        bacs_resolved = []
        for ob in bacs:
            if ob.echeance:
                bacs_resolved.append(compute_bacs_statut(evidences, ob.echeance))
            else:
                bacs_resolved.append(ob.statut)
    else:
        bacs_resolved = [ob.statut for ob in bacs]

    worst_bacs = _worst_from_statuts(bacs_resolved)

    # Count non-conforme across both dimensions
    non_conforme_count = sum(
        1 for o in decret if o.statut == StatutConformite.NON_CONFORME
    ) + sum(
        1 for s in bacs_resolved if s == StatutConformite.NON_CONFORME
    )

    # Build resolved obligation pairs for action recommendation
    resolved_pairs = [(o.type, o.statut) for o in decret]
    resolved_pairs += [(TypeObligation.BACS, s) for s in bacs_resolved]

    action = None
    for ob_type, ob_statut, action_text in _ACTION_TEMPLATES:
        if (ob_type, ob_statut) in resolved_pairs:
            action = action_text
            break

    return {
        "statut_decret_tertiaire": worst_status(decret) or StatutConformite.A_RISQUE,
        "avancement_decret_pct": average_avancement(decret),
        "statut_bacs": worst_bacs or StatutConformite.A_RISQUE,
        "action_recommandee": action,
        "risque_financier_euro": round(BASE_PENALTY_EURO * non_conforme_count, 2),
    }


# ========================================
# Layer B: Database persistence
# ========================================

def _apply_snapshot(site: Site, snapshot: dict):
    """Apply a computed snapshot dict to a Site ORM object."""
    for key, value in snapshot.items():
        setattr(site, key, value)


def recompute_site(db: Session, site_id: int) -> dict:
    """Recompute and persist compliance snapshot for a single Site."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    obligations = db.query(Obligation).filter(Obligation.site_id == site_id).all()
    evidences = db.query(Evidence).filter(Evidence.site_id == site_id).all()
    snapshot = compute_site_snapshot(obligations, evidences)
    _apply_snapshot(site, snapshot)
    db.commit()
    return snapshot


def _bulk_recompute(db: Session, sites: List[Site]):
    """Recompute snapshots for a list of sites (3 queries total, no N+1)."""
    if not sites:
        return

    site_ids = [s.id for s in sites]

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

    for site in sites:
        snapshot = compute_site_snapshot(
            obs_by_site[site.id], evs_by_site[site.id]
        )
        _apply_snapshot(site, snapshot)


def recompute_portfolio(db: Session, portefeuille_id: int) -> dict:
    """Recompute compliance for all sites in a portfolio."""
    portefeuille = db.query(Portefeuille).filter(
        Portefeuille.id == portefeuille_id
    ).first()
    if not portefeuille:
        raise ValueError(f"Portefeuille {portefeuille_id} not found")

    sites = db.query(Site).filter(
        Site.portefeuille_id == portefeuille_id
    ).all()

    _bulk_recompute(db, sites)
    db.commit()
    return {
        "portefeuille_id": portefeuille_id,
        "portefeuille_nom": portefeuille.nom,
        "sites_recomputed": len(sites),
    }


def recompute_organisation(db: Session, organisation_id: int) -> dict:
    """Recompute compliance for ALL sites in an organisation."""
    org = db.query(Organisation).filter(
        Organisation.id == organisation_id
    ).first()
    if not org:
        raise ValueError(f"Organisation {organisation_id} not found")

    portefeuille_ids = [
        row[0] for row in
        db.query(Portefeuille.id)
        .join(EntiteJuridique)
        .filter(EntiteJuridique.organisation_id == organisation_id)
        .all()
    ]

    sites = db.query(Site).filter(
        Site.portefeuille_id.in_(portefeuille_ids)
    ).all()

    _bulk_recompute(db, sites)
    db.commit()
    return {
        "organisation_id": organisation_id,
        "organisation_nom": org.nom,
        "sites_recomputed": len(sites),
    }
