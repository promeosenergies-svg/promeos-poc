"""
PROMEOS - Onboarding Stepper Service (V119 extraction route-to-service).

Extrait les helpers _get_or_create + _auto_detect auparavant prives dans
routes/onboarding_stepper.py pour eviter la leaky abstraction route-to-route.

Utilise par :
  - routes/onboarding_stepper.py (auto-detect explicite via endpoint)
  - routes/sirene.py (onboarding_from_sirene cable le funnel apres creation)

Toute logique de detection des steps vit ici, pas dans les routes.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import (
    ActionItem,
    Compteur,
    EnergyInvoice,
    EntiteJuridique,
    OnboardingProgress,
    Organisation,
    Portefeuille,
    Site,
    UserOrgRole,
)

STEP_FIELDS = (
    "step_org_created",
    "step_sites_added",
    "step_meters_connected",
    "step_invoices_imported",
    "step_users_invited",
    "step_first_action",
)


def get_or_create_progress(db: Session, org_id: int) -> OnboardingProgress:
    """Retourne ou cree un OnboardingProgress pour une organisation."""
    progress = db.query(OnboardingProgress).filter(OnboardingProgress.org_id == org_id).first()
    if not progress:
        progress = OnboardingProgress(org_id=org_id)
        db.add(progress)
        db.flush()
    return progress


def auto_detect_steps(db: Session, org_id: int, progress: OnboardingProgress) -> OnboardingProgress:
    """Auto-detecte les steps completes depuis l'etat reel de la base.

    Mutates progress in place et retourne la reference.
    """
    # Step 1 : org existe
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if org:
        progress.step_org_created = True

    # Step 2 : a des sites
    pf_ids = [
        r.id
        for r in (
            db.query(Portefeuille.id)
            .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
            .filter(EntiteJuridique.organisation_id == org_id)
            .all()
        )
    ]
    site_count = 0
    if pf_ids:
        site_count = db.query(Site).filter(Site.portefeuille_id.in_(pf_ids), Site.actif).count()
    if site_count > 0:
        progress.step_sites_added = True

    # Step 3 : compteurs connectes
    if pf_ids:
        site_ids = [r.id for r in db.query(Site.id).filter(Site.portefeuille_id.in_(pf_ids)).all()]
        if site_ids:
            meter_count = db.query(Compteur).filter(Compteur.site_id.in_(site_ids)).count()
            if meter_count > 0:
                progress.step_meters_connected = True

            # Step 4 : factures importees
            inv_count = db.query(EnergyInvoice).filter(EnergyInvoice.site_id.in_(site_ids)).count()
            if inv_count > 0:
                progress.step_invoices_imported = True

    # Step 5 : utilisateurs invites
    user_count = db.query(UserOrgRole).filter(UserOrgRole.org_id == org_id).count()
    if user_count >= 1:
        progress.step_users_invited = True

    # Step 6 : premiere action
    action_count = db.query(ActionItem).filter(ActionItem.org_id == org_id).count()
    if action_count > 0:
        progress.step_first_action = True

    # Completion globale
    if all(getattr(progress, f) for f in STEP_FIELDS) and not progress.completed_at:
        progress.completed_at = datetime.now(timezone.utc)

    return progress


def wire_funnel_best_effort(db: Session, org_id: int, context: str = "") -> None:
    """Cable best-effort le funnel onboarding apres une creation.

    Ne bloque jamais l'appelant si le service echoue — log et continue.
    Utilise depuis onboarding_from_sirene et autres flux qui creent un patrimoine.
    """
    import logging

    logger = logging.getLogger(__name__)
    try:
        progress = get_or_create_progress(db, org_id)
        auto_detect_steps(db, org_id, progress)
    except Exception as e:
        logger.warning("onboarding_progress wiring failed [%s]: %s", context, e)
