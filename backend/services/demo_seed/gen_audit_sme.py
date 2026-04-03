"""
PROMEOS - Demo Seed: Audit Energetique / SME
Seed pour les donnees de conformite Audit/SME (Loi 2025-391).
"""

from datetime import date
from sqlalchemy.orm import Session

from models.audit_sme import AuditEnergetique
from services.audit_sme_service import compute_obligation, compute_statut, compute_score_audit_sme


def seed_audit_sme(db: Session, org_id: int, org_nom: str, conso_kwh_an: float):
    """
    Seed un record AuditEnergetique pour une organisation.
    Utilise les fonctions canoniques du service pour determiner obligation/statut/score.
    """
    existing = db.query(AuditEnergetique).filter_by(organisation_id=org_id).first()
    if existing:
        return existing

    conso_gwh = conso_kwh_an / 1_000_000
    obligation_info = compute_obligation(conso_kwh_an)
    obligation = obligation_info["obligation"]

    record = AuditEnergetique(
        organisation_id=org_id,
        organisation_libelle=org_nom,
        annee_ref_debut=2022,
        annee_ref_fin=2024,
        conso_annuelle_moy_kwh=conso_kwh_an,
        conso_annuelle_moy_gwh=round(conso_gwh, 3),
        obligation=obligation,
        date_premier_audit_limite=date(2026, 10, 11) if obligation != "AUCUNE" else None,
        auditeur_identifie=False,
        audit_realise=False,
        plan_action_publie=False,
        transmission_realisee=False,
        sme_certifie_iso50001=False,
        source="seed",
    )

    statut = compute_statut(record, obligation)
    score = compute_score_audit_sme(record, obligation, statut)
    record.statut = statut
    record.score_audit_sme = score

    db.add(record)
    db.flush()
    return record
