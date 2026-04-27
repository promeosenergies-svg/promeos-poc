"""Détecteur `asset_registry_issue` — chantier α Vague C ét13e.

Doctrine §10 event_type `asset_registry_issue` : émet un événement quand
le registre patrimoine présente des incohérences (PRM/PCE non rattaché à
un site, contrat orphelin sans annexes, GRD non renseigné…).

Sans qualité du registre, la facturation TURPE/ATRD est faussée
(impossible de router vers la bonne grille), le shadow billing perd ses
points de référence, et le scoring conformité dérape.

Owner DAF (responsabilité contractuelle / patrimoine). 3 contrôles MVP :
1. PRM/PCE sans site rattaché (FK orphan)
2. PRM/PCE sans grd_code (impossible de router TURPE/ATRD)
3. ContratCadre sans annexes (couvre 0 site)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..freshness import compute_freshness
from ..types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventSource,
    SolEventCard,
)


def _severity_for_count(count: int) -> str | None:
    """Mappe nombre d'incohérences → severity.

    Une incohérence est suffisante pour signaler ; le seuil monte la
    severity quand le volume reflète une dérive systémique du registre.
    """
    if count >= 10:
        return "critical"
    if count >= 3:
        return "warning"
    if count >= 1:
        return "watch"
    return None


def detect(db: Session, org_id: int) -> list[SolEventCard]:
    """Émet 0..3 événements `asset_registry_issue` (3 contrôles MVP)."""
    # Imports locaux pour éviter cycle
    from models import EntiteJuridique, Portefeuille, Site, not_deleted
    from models.contract_v2_models import ContractAnnexe, ContratCadre
    from models.patrimoine import DeliveryPoint

    now = datetime.now(timezone.utc)
    events: list[SolEventCard] = []

    # ── Contrôle 1 : DeliveryPoint sans grd_code ──
    # (le grd_code est obligatoire pour router vers la bonne grille TURPE/ATRD)
    dps_org = (
        not_deleted(db.query(DeliveryPoint), DeliveryPoint)
        .join(Site, Site.id == DeliveryPoint.site_id)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    )
    no_grd = [dp for dp in dps_org if not dp.grd_code]
    no_grd_severity = _severity_for_count(len(no_grd))
    if no_grd_severity:
        events.append(
            SolEventCard(
                id=f"asset_registry_issue:org:{org_id}:no_grd",
                event_type="asset_registry_issue",
                severity=no_grd_severity,  # type: ignore[arg-type]
                title=f"{len(no_grd)} point{'s' if len(no_grd) > 1 else ''} de livraison sans gestionnaire de réseau",
                narrative=(
                    f"{len(no_grd)} PRM/PCE n'ont pas de gestionnaire de réseau "
                    "renseigné (Enedis, GRDF, ELD…). Sans cette information, le "
                    "calcul TURPE/ATRD est faussé et la conformité OPERAT à risque. "
                    "Compléter depuis la fiche site ou via import SGE."
                ),
                impact=EventImpact(
                    value=float(len(no_grd)),
                    unit="kWh",  # proxy "comptage incertain"
                    period="year",
                ),
                source=EventSource(
                    system="manual",  # registre patrimoine alimenté manuellement
                    last_updated_at=now,
                    confidence="high",
                    freshness_status=compute_freshness("manual", now, now=now),
                    methodology=(
                        "Comptage des DeliveryPoint dont grd_code est NULL. "
                        "Le code GRD (gestionnaire de réseau) détermine la grille tarifaire "
                        "réglementée applicable (TURPE pour Enedis, ATRD pour GRDF, etc.). "
                        "Sans ce code, le shadow billing ne peut pas valider les factures."
                    ),
                ),
                action=EventAction(
                    label="Voir le patrimoine",
                    route="/patrimoine",
                    owner_role="DAF",
                ),
                linked_assets=EventLinkedAssets(
                    org_id=org_id,
                    site_ids=sorted({dp.site_id for dp in no_grd}),
                ),
            )
        )

    # ── Contrôle 2 : ContratCadre sans annexes (couvre 0 site) ──
    contrats = not_deleted(db.query(ContratCadre), ContratCadre).filter(ContratCadre.org_id == org_id).all()
    contracts_no_annexes = []
    for c in contrats:
        annex_count = (
            not_deleted(db.query(ContractAnnexe), ContractAnnexe)
            .filter(ContractAnnexe.contrat_cadre_id == c.id)
            .count()
        )
        if annex_count == 0:
            contracts_no_annexes.append(c)

    orphan_severity = _severity_for_count(len(contracts_no_annexes))
    if orphan_severity:
        events.append(
            SolEventCard(
                id=f"asset_registry_issue:org:{org_id}:orphan_contract",
                event_type="asset_registry_issue",
                severity=orphan_severity,  # type: ignore[arg-type]
                title=f"{len(contracts_no_annexes)} contrat{'s' if len(contracts_no_annexes) > 1 else ''} sans site rattaché",
                narrative=(
                    f"{len(contracts_no_annexes)} contrat{'s' if len(contracts_no_annexes) > 1 else ''} "
                    "fournisseur ne couvre aucun site dans le registre PROMEOS. "
                    "Risque : facturation reçue sans pouvoir l'imputer ou la contester. "
                    "Vérifier les annexes site et compléter les rattachements."
                ),
                impact=EventImpact(
                    value=float(len(contracts_no_annexes)),
                    unit="kWh",  # proxy "facturation orpheline"
                    period="contract",
                ),
                source=EventSource(
                    system="manual",
                    last_updated_at=now,
                    confidence="high",
                    freshness_status=compute_freshness("manual", now, now=now),
                    methodology=(
                        "Comptage ContratCadre dont COUNT(ContractAnnexe.contrat_cadre_id) = 0. "
                        "Un contrat cadre sans annexe site est techniquement actif "
                        "(facturation reçue) mais non auditable. Action : créer les annexes "
                        "ou archiver si le contrat est obsolète."
                    ),
                ),
                action=EventAction(
                    label="Voir les contrats",
                    route="/contrats",
                    owner_role="DAF",
                ),
                linked_assets=EventLinkedAssets(
                    org_id=org_id,
                    contract_ids=[c.id for c in contracts_no_annexes],
                ),
            )
        )

    return events
