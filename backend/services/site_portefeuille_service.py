"""Service bascule Site↔Portefeuille avec historique et audit (matrice v1 §6.5).

Sprint C-2 Phase 2 — comble GAP audit Phase B R4 (temporalité).

API publique :
- transfer_site_to_portefeuille : bascule + entrée history + audit log
- get_site_history : historique complet desc
- get_portefeuille_at_date : analyse rétrospective

Invariant métier (CrossEjTransferError) :
- Bascule cross-EJ INTERDITE (un Site doit rester dans la même Entité Juridique).
- Le portefeuille cible doit appartenir à la même EJ que le portefeuille courant
  du site.

Audit log automatique via `audit_log_service.log_patrimoine_change` (Phase 1.3
wiring), résilience erreur audit préservée (try/except).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from models import EntiteJuridique, Portefeuille, Site
from models.site_portefeuille_history import SitePortefeuilleHistory


_logger = logging.getLogger(__name__)


# ─── Exceptions métier ────────────────────────────────────────────────────────


class CrossEjTransferError(Exception):
    """Transfert Site vers Portefeuille d'une autre EJ interdit (cohérence hiérarchique)."""


class PortefeuilleNotFoundError(Exception):
    """Portefeuille cible inexistant."""


class SiteNotFoundError(Exception):
    """Site inexistant."""


# ─── API publique ────────────────────────────────────────────────────────────


def transfer_site_to_portefeuille(
    db: Session,
    site_id: int,
    new_portefeuille_id: int,
    *,
    user_id: Optional[int] = None,
    org_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    raison: Optional[str] = None,
) -> SitePortefeuilleHistory:
    """Bascule un site vers un nouveau portefeuille (même EJ).

    Algorithme :
      1. Charger site + valider existence
      2. Charger portefeuille cible + valider existence
      3. Invariant cross-EJ : refuser si EJs différentes
      4. Fermer l'entrée history courante (valid_to = now) si existe
      5. Créer nouvelle entrée history (valid_from = now, valid_to = None)
      6. Mettre à jour Site.portefeuille_id (FK directe)
      7. Audit log via log_patrimoine_change (résilience try/except)
      8. db.flush() pour populate new_entry.id (caller commit)

    Raises:
        SiteNotFoundError: site_id introuvable
        PortefeuilleNotFoundError: new_portefeuille_id introuvable
        CrossEjTransferError: tentative bascule cross-EJ
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise SiteNotFoundError(f"Site {site_id} introuvable")

    new_portefeuille = db.query(Portefeuille).filter(Portefeuille.id == new_portefeuille_id).first()
    if not new_portefeuille:
        raise PortefeuilleNotFoundError(f"Portefeuille {new_portefeuille_id} introuvable")

    # ⚠️ Invariant : même EJ
    current_ej_id = site.portefeuille.entite_juridique_id if site.portefeuille else None
    new_ej_id = new_portefeuille.entite_juridique_id

    if current_ej_id is not None and current_ej_id != new_ej_id:
        raise CrossEjTransferError(
            f"Transfert cross-EJ interdit : site {site_id} appartient à EJ "
            f"{current_ej_id}, portefeuille cible appartient à EJ {new_ej_id}"
        )

    old_portefeuille_id = site.portefeuille_id
    now = datetime.utcnow()

    # Idempotence : si nouveau == ancien, pas de bascule (return entry courante)
    if old_portefeuille_id == new_portefeuille_id:
        _logger.info(
            "transfer_site_to_portefeuille no-op : site %s déjà dans portefeuille %s",
            site_id,
            new_portefeuille_id,
        )
        # Retourner l'entry courante (créer si inexistante, pour cohérence retro)
        current = (
            db.query(SitePortefeuilleHistory)
            .filter(
                and_(
                    SitePortefeuilleHistory.site_id == site_id,
                    SitePortefeuilleHistory.valid_to.is_(None),
                )
            )
            .first()
        )
        if current:
            return current
        # Pas d'entrée courante : créer une rétro-active (cas DB sans history préalable)
        backfill = SitePortefeuilleHistory(
            site_id=site_id,
            portefeuille_id=new_portefeuille_id,
            valid_from=now,
            valid_to=None,
            transferred_by_user_id=user_id,
            raison=raison or "Backfill no-op transfer",
        )
        db.add(backfill)
        db.flush()
        return backfill

    # 1. Fermer l'entrée history courante si elle existe
    current_entry = (
        db.query(SitePortefeuilleHistory)
        .filter(
            and_(
                SitePortefeuilleHistory.site_id == site_id,
                SitePortefeuilleHistory.valid_to.is_(None),
            )
        )
        .first()
    )
    if current_entry:
        current_entry.valid_to = now

    # 2. Créer la nouvelle entrée history
    new_entry = SitePortefeuilleHistory(
        site_id=site_id,
        portefeuille_id=new_portefeuille_id,
        valid_from=now,
        valid_to=None,
        transferred_by_user_id=user_id,
        raison=raison,
    )
    db.add(new_entry)

    # 3. Mettre à jour la FK directe Site.portefeuille_id
    site.portefeuille_id = new_portefeuille_id

    # 4. Audit log via Phase 1.3 wiring (résilience préservée)
    try:
        from services.audit_log_service import log_patrimoine_change

        db.flush()  # populate new_entry.id pour le payload audit

        log_patrimoine_change(
            db,
            user_id=user_id,
            org_id=org_id,
            entity_type="site",
            entity_id=site_id,
            action="site.transfer_portefeuille",
            field_modified="portefeuille_id",
            old_value=old_portefeuille_id,
            new_value=new_portefeuille_id,
            correlation_id=correlation_id,
            detail={
                "raison": raison,
                "history_entry_id": new_entry.id,
                "old_ej_id": current_ej_id,
                "new_ej_id": new_ej_id,
            },
        )
    except Exception as audit_err:
        # ⚠️ Résilience : un échec audit log NE BLOQUE PAS la bascule
        _logger.warning(
            "audit_log_service.log_patrimoine_change failed for site transfer: %s",
            audit_err,
            exc_info=True,
        )

    db.flush()
    return new_entry


def get_site_history(db: Session, site_id: int) -> list[SitePortefeuilleHistory]:
    """Retourne l'historique complet des bascules pour un site (du plus récent au plus ancien)."""
    return (
        db.query(SitePortefeuilleHistory)
        .filter(SitePortefeuilleHistory.site_id == site_id)
        .order_by(SitePortefeuilleHistory.valid_from.desc())
        .all()
    )


def get_portefeuille_at_date(db: Session, site_id: int, at_date: datetime) -> Optional[Portefeuille]:
    """Retourne le Portefeuille auquel appartenait un Site à une date donnée.

    Logique : trouver l'entrée history avec `valid_from <= at_date < valid_to`
    (ou `valid_to IS NULL` si période courante).
    """
    entry = (
        db.query(SitePortefeuilleHistory)
        .filter(
            and_(
                SitePortefeuilleHistory.site_id == site_id,
                SitePortefeuilleHistory.valid_from <= at_date,
                ((SitePortefeuilleHistory.valid_to.is_(None)) | (SitePortefeuilleHistory.valid_to > at_date)),
            )
        )
        .first()
    )
    return entry.portefeuille if entry else None
