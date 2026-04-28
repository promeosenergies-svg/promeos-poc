"""Détecteur `asset_registry_issue` — chantier α Vague C ét13e/14/15.

Doctrine §10 event_type `asset_registry_issue` : émet un événement quand
le registre patrimoine présente des incohérences (PRM/PCE non rattaché à
un site, contrat orphelin sans annexes, GRD non renseigné…).

Sans qualité du registre, la facturation TURPE/ATRD est faussée
(impossible de router vers la bonne grille), le shadow billing perd ses
points de référence, et le scoring conformité dérape.

Owner DAF (responsabilité contractuelle / patrimoine). 3 contrôles MVP :
1. PRM/PCE sans grd_code (impossible de router TURPE/ATRD) — ét13e
2. ContratCadre sans annexes (couvre 0 site) — ét13e
3. PRM/PCE rattaché à un Site soft-deleted (FK pointing vers cadavre) — ét14
   (audit EM P0 #3 : 3ᵉ contrôle annoncé docstring mais non livré ét13e)

## Frontière vs `data_quality_issue_detector` (ét15 audit EM P1 #3)

Ce détecteur s'occupe **uniquement de la cohérence STRUCTURELLE** du
registre (champs manquants, FK orphelins, soft-delete cadavres). Il ne
touche **PAS** à la fraîcheur des données réseau (PHOTO D020 obsolète,
R6X CDC ancien, SGE snapshot non rafraîchi) — cette responsabilité
revient à `data_quality_issue_detector` (consume tout insight type
`('data_gap', 'photo_d020_stale', 'sge_snapshot_stale')`).

Cette frontière de responsabilité est verrouillée par le test
`test_data_quality_owns_photo_d020_freshness_not_asset_registry`.

Vague C ét14 (audit CFO P0 #2) : convertit les counts en € risque shadow
billing via `asset_registry` defaults YAML (exposition par DP/contrat
non auditable). Plus de proxy kWh ambigu.
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
    from config.mitigation_loader import get_asset_registry_defaults
    from models import EntiteJuridique, Portefeuille, Site, not_deleted
    from models.contract_v2_models import ContractAnnexe, ContratCadre
    from models.patrimoine import DeliveryPoint

    ar_defaults = get_asset_registry_defaults()  # ét14 P0 #2 CFO

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
        # ét14 (CFO P0 #2) : impact € = count × exposition shadow billing/DP
        no_grd_impact_eur = len(no_grd) * ar_defaults.blind_billing_exposure_per_dp_eur
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
                    f"Exposition shadow billing estimée : {int(no_grd_impact_eur):,} €/an."
                ).replace(",", " "),
                impact=EventImpact(
                    value=no_grd_impact_eur,
                    unit="€",
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
                        f"Exposition € = count × {int(ar_defaults.blind_billing_exposure_per_dp_eur):,} €/PRM/an "
                        f"({ar_defaults.blind_billing_source})."
                    ).replace(",", " "),
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
        # ét14 (CFO P0 #2) : impact € = count × exposition contrat orphelin
        orphan_impact_eur = len(contracts_no_annexes) * ar_defaults.orphan_contract_exposure_eur
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
                    f"Exposition estimée : {int(orphan_impact_eur):,} €/an. "
                    "Vérifier les annexes site et compléter les rattachements."
                ).replace(",", " "),
                impact=EventImpact(
                    value=orphan_impact_eur,
                    unit="€",
                    period="year",
                ),
                source=EventSource(
                    system="manual",
                    last_updated_at=now,
                    confidence="high",
                    freshness_status=compute_freshness("manual", now, now=now),
                    methodology=(
                        "Comptage ContratCadre dont COUNT(ContractAnnexe.contrat_cadre_id) = 0. "
                        "Un contrat cadre sans annexe site est techniquement actif "
                        "(facturation reçue) mais non auditable. "
                        f"Exposition € = count × {int(ar_defaults.orphan_contract_exposure_eur):,} €/contrat "
                        f"({ar_defaults.orphan_contract_source})."
                    ).replace(",", " "),
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

    # ── Contrôle 3 : DeliveryPoint dont le Site a été soft-deleted ──
    # ét14 (audit EM P0 #3) : 3ᵉ contrôle MVP annoncé docstring ét13e mais
    # non livré. Site.site_id est NOT NULL côté schéma → impossible d'avoir
    # un FK strictement orphelin. Le cas réel = Site soft-deleted (deleted_at
    # NOT NULL) mais DP toujours actif → comptage TURPE/ATRD pointe vers
    # un site fantôme. Détection via outerjoin + filtre Site.deleted_at IS NOT NULL.
    from models import Site as SiteModel

    dps_with_deleted_site = (
        db.query(DeliveryPoint)
        .join(SiteModel, SiteModel.id == DeliveryPoint.site_id)
        .join(Portefeuille, Portefeuille.id == SiteModel.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .filter(DeliveryPoint.deleted_at.is_(None))
        .filter(SiteModel.deleted_at.isnot(None))  # ← Site soft-deleted
        .all()
    )
    orphan_dp_severity = _severity_for_count(len(dps_with_deleted_site))
    if orphan_dp_severity:
        orphan_dp_impact_eur = len(dps_with_deleted_site) * ar_defaults.blind_billing_exposure_per_dp_eur
        events.append(
            SolEventCard(
                id=f"asset_registry_issue:org:{org_id}:dp_orphan_site",
                event_type="asset_registry_issue",
                severity=orphan_dp_severity,  # type: ignore[arg-type]
                title=(
                    f"{len(dps_with_deleted_site)} point"
                    f"{'s' if len(dps_with_deleted_site) > 1 else ''} de livraison rattaché"
                    f"{'s' if len(dps_with_deleted_site) > 1 else ''} à un site supprimé"
                ),
                narrative=(
                    f"{len(dps_with_deleted_site)} PRM/PCE pointent vers un site "
                    "désactivé dans le registre. Le compteur TURPE/ATRD continue "
                    "d'être facturé sans périmètre auditable côté patrimoine. "
                    "Réaffecter le PRM à un site actif ou archiver le DP."
                ),
                impact=EventImpact(
                    value=orphan_dp_impact_eur,
                    unit="€",
                    period="year",
                ),
                source=EventSource(
                    system="manual",
                    last_updated_at=now,
                    confidence="high",
                    freshness_status=compute_freshness("manual", now, now=now),
                    methodology=(
                        "DeliveryPoint (deleted_at NULL) joint à Site (deleted_at NOT NULL). "
                        "Le contrôle vérifie la cohérence du chaînage soft-delete : un DP "
                        "ne doit pas survivre à la désactivation du site qu'il alimente. "
                        f"Exposition € = count × {int(ar_defaults.blind_billing_exposure_per_dp_eur):,} €/PRM/an."
                    ).replace(",", " "),
                ),
                action=EventAction(
                    label="Voir le patrimoine",
                    route="/patrimoine",
                    owner_role="DAF",
                ),
                linked_assets=EventLinkedAssets(
                    org_id=org_id,
                    site_ids=sorted({dp.site_id for dp in dps_with_deleted_site}),
                ),
            )
        )

    return events
