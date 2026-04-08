"""
PROMEOS — Service d'alertes d'expiration de contrats (D.3)

Génère automatiquement des alertes pour les contrats énergie
dont la date de fin est dans les 90 prochains jours.
Idempotent : ne crée pas de doublons si l'alerte existe déjà.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import Alerte, Site, EnergyContract
from models.enums import SeveriteAlerte

_logger = logging.getLogger("promeos.contract_expiration_alerts")

# Titre canonique utilisé pour la déduplication
_ALERT_TITLE_PREFIX = "Contrat expire sous 90j"


def generate_contract_expiration_alerts(
    db: Session,
    site_ids: list[int],
    horizon_days: int = 90,
) -> dict:
    """
    Crée des alertes pour les contrats expirant dans `horizon_days` jours.

    Retour :
        {
            "contrats_expirant_90j": int,
            "alertes_creees": int,
            "alertes_existantes": int,
        }
    """
    if not site_ids:
        return {"contrats_expirant_90j": 0, "alertes_creees": 0, "alertes_existantes": 0}

    today = date.today()
    deadline = today + timedelta(days=horizon_days)

    # Contrats expirant dans la fenêtre
    expiring_contracts = (
        db.query(EnergyContract)
        .filter(
            EnergyContract.site_id.in_(site_ids),
            EnergyContract.end_date >= today,
            EnergyContract.end_date <= deadline,
        )
        .all()
    )

    count_expiring = len(expiring_contracts)
    alertes_creees = 0
    alertes_existantes = 0

    for ct in expiring_contracts:
        days_left = (ct.end_date - today).days
        titre = f"{_ALERT_TITLE_PREFIX} — {ct.supplier_name} (#{ct.id})"

        # Sévérité selon le nombre de jours restants
        severite = (
            SeveriteAlerte.CRITICAL
            if days_left <= 30
            else SeveriteAlerte.WARNING
            if days_left <= 60
            else SeveriteAlerte.INFO
        )

        description = (
            f"Le contrat {ct.reference_fournisseur or ct.supplier_name} "
            f"(site #{ct.site_id}) expire le {ct.end_date.isoformat()} "
            f"({days_left} jours restants). "
            f"Préavis : {ct.notice_period_days or 90} jours. "
            f"Reconduction tacite : {'Oui' if ct.auto_renew else 'Non'}."
        )

        # Déduplication : vérifier si une alerte non résolue existe déjà pour ce site + titre (inclut contract id)
        existing = (
            db.query(Alerte)
            .filter(
                Alerte.site_id == ct.site_id,
                Alerte.titre == titre,
                Alerte.resolue == False,
            )
            .first()
        )
        if existing:
            # Update severity and description if the tier changed
            if existing.severite != severite:
                existing.severite = severite
                existing.description = description
            alertes_existantes += 1
            continue

        db.add(
            Alerte(
                site_id=ct.site_id,
                severite=severite,
                titre=titre,
                description=description,
                timestamp=datetime.now(timezone.utc),
                resolue=False,
            )
        )
        alertes_creees += 1

    if alertes_creees > 0:
        db.flush()

    _logger.info(
        f"Contract expiration alerts: {count_expiring} expiring, "
        f"{alertes_creees} created, {alertes_existantes} already existed"
    )

    return {
        "contrats_expirant_90j": count_expiring,
        "alertes_creees": alertes_creees,
        "alertes_existantes": alertes_existantes,
    }
