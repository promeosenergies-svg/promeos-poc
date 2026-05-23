"""PROMEOS — Contract coverage service (P0-C 2026-05-23).

Vue agrégée par site de la couverture contractuelle de ses points de
livraison (PRM électricité / PDL / PCE gaz).

Règle produit P0-C : *"Un site ne peut pas être considéré prêt facture /
achat / audit si ses points de livraison actifs ne sont pas reliés à un
contrat énergie actif ou explicitement justifiés."*

Référence canonique : `docs/dev/patrimoine_routes_canonical.md §11 P0-C`.

Réutilise sans dupliquer :
- `ContractDeliveryPoint` (N-N) — table de liaison contrat ↔ DP
- `EnergyContract.delivery_points` relationship
- `models.DeliveryPoint` + `DeliveryPointStatus` / `DeliveryPointEnergyType`
- `services.contrat_coherence.validate_contrat` pour le détail R1-R16
- `services.perimeter_check.check_perimeter` pour la vue facture

Source-guard `test_perimeter_check_requires_contract_when_delivery_points_active`
verrouille la cohérence Bill Intelligence ↔ couverture contractuelle.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from models import (
    EnergyContract,
    Site,
    not_deleted,
)
from models.enums import (
    BillingEnergyType,
    DeliveryPointEnergyType,
    DeliveryPointStatus,
)
from models.patrimoine import DeliveryPoint


_logger = logging.getLogger(__name__)


# ─── Status canoniques de couverture (5 valeurs cardinales) ──────────────────


COVERAGE_CONTRAT_RATTACHE = "contrat_rattache"
COVERAGE_CONTRAT_PARTIEL = "contrat_partiel"
COVERAGE_CONTRAT_MANQUANT = "contrat_manquant"
COVERAGE_CONTRAT_EXPIRE = "contrat_expire"
COVERAGE_CONTRAT_INCOHERENT = "contrat_incoherent"

ALL_COVERAGE_STATUSES = frozenset(
    {
        COVERAGE_CONTRAT_RATTACHE,
        COVERAGE_CONTRAT_PARTIEL,
        COVERAGE_CONTRAT_MANQUANT,
        COVERAGE_CONTRAT_EXPIRE,
        COVERAGE_CONTRAT_INCOHERENT,
    }
)


# ─── Mapping énergie : compatibilité contrat ↔ DP ───────────────────────────


_DP_TO_BILLING: dict[str, str] = {
    "elec": "elec",
    "gaz": "gaz",
}


def _is_energy_compatible(
    contract_energy: Optional[BillingEnergyType], dp_energy: Optional[DeliveryPointEnergyType]
) -> bool:
    """Vrai si l'énergie du contrat correspond à celle du DP.

    Cas tolérés : valeurs nulles des deux côtés (donnée manquante traitée ailleurs).
    """
    if contract_energy is None or dp_energy is None:
        return True
    return contract_energy.value == _DP_TO_BILLING.get(dp_energy.value, dp_energy.value)


# ─── Dataclasses résultat ────────────────────────────────────────────────────


@dataclass(frozen=True)
class DeliveryPointSummary:
    """Snapshot d'un point de livraison pour la vue couverture."""

    id: int
    code: str
    energy_type: Optional[str]  # "elec" | "gaz"
    status: Optional[str]  # "active" | "inactive"
    grd_code: Optional[str]
    label_fr: str  # "Point de livraison électricité — PRM/PDL XXXXX"
    covering_contract_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContractSummary:
    """Snapshot d'un contrat énergie pour la vue couverture."""

    id: int
    supplier_name: Optional[str]
    energy_type: Optional[str]
    reference_fournisseur: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    is_expired: bool
    delivery_point_ids: list[int]
    label_fr: str  # "EDF — Électricité (contrat n° CTR-2025-001)"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EnergyMismatch:
    """Incohérence d'énergie contrat ↔ point de livraison."""

    contract_id: int
    delivery_point_id: int
    contract_energy: Optional[str]
    delivery_point_energy: Optional[str]
    message_fr: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CoverageAction:
    """Action recommandée pour fermer un trou de couverture."""

    code: str  # "ATTACH_CONTRACT" | "RENEW_CONTRACT" | "FIX_ENERGY_MISMATCH" | "DETACH_FOREIGN_DP"
    label_fr: str
    target_type: str  # "delivery_point" | "contract"
    target_id: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SiteContractCoverage:
    """Vue agrégée de la couverture contractuelle d'un site."""

    site_id: int
    org_id: int
    status: str  # un des ALL_COVERAGE_STATUSES
    delivery_points_active: list[DeliveryPointSummary]
    contracts_active: list[ContractSummary]
    uncovered_delivery_points: list[DeliveryPointSummary]
    expired_contracts: list[ContractSummary]
    energy_mismatches: list[EnergyMismatch]
    foreign_delivery_point_links: list[dict[str, Any]]  # contrat lié à un DP hors site
    ready_for_billing: bool
    ready_for_purchase: bool
    actions: list[CoverageAction]
    computed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "org_id": self.org_id,
            "status": self.status,
            "delivery_points_active": [dp.to_dict() for dp in self.delivery_points_active],
            "contracts_active": [c.to_dict() for c in self.contracts_active],
            "uncovered_delivery_points": [dp.to_dict() for dp in self.uncovered_delivery_points],
            "expired_contracts": [c.to_dict() for c in self.expired_contracts],
            "energy_mismatches": [m.to_dict() for m in self.energy_mismatches],
            "foreign_delivery_point_links": list(self.foreign_delivery_point_links),
            "ready_for_billing": self.ready_for_billing,
            "ready_for_purchase": self.ready_for_purchase,
            "actions": [a.to_dict() for a in self.actions],
            "computed_at": self.computed_at,
        }


# ─── Helpers ────────────────────────────────────────────────────────────────


def _dp_label_fr(dp: DeliveryPoint) -> str:
    """Libellé utilisateur d'un point de livraison.

    Toujours préfixer "Point de livraison <énergie> —" puis détail technique
    (PRM/PDL pour élec, PCE pour gaz). Cf. règle terminologie P0-C.
    """
    if dp.energy_type == DeliveryPointEnergyType.ELEC:
        return f"Point de livraison électricité — PRM/PDL {dp.code}"
    if dp.energy_type == DeliveryPointEnergyType.GAZ:
        return f"Point de livraison gaz — PCE {dp.code}"
    return f"Point de livraison — {dp.code}"


def _contract_label_fr(ct: EnergyContract) -> str:
    """Libellé utilisateur d'un contrat."""
    supplier = ct.supplier_name or "Fournisseur inconnu"
    energy = (
        "Électricité"
        if ct.energy_type == BillingEnergyType.ELEC
        else "Gaz"
        if ct.energy_type == BillingEnergyType.GAZ
        else "Énergie"
    )
    ref = ct.reference_fournisseur or f"interne #{ct.id}"
    return f"{supplier} — {energy} (contrat n° {ref})"


def _is_contract_active_today(ct: EnergyContract, today: date) -> bool:
    """Actif : start_date ≤ today ≤ end_date (les bornes nulles sont permissives)."""
    if ct.start_date and ct.start_date > today:
        return False
    if ct.end_date and ct.end_date < today:
        return False
    return True


def _summarize_dp(dp: DeliveryPoint, covering_contract_ids: Iterable[int]) -> DeliveryPointSummary:
    return DeliveryPointSummary(
        id=dp.id,
        code=dp.code,
        energy_type=dp.energy_type.value if dp.energy_type else None,
        status=dp.status.value if dp.status else None,
        grd_code=dp.grd_code,
        label_fr=_dp_label_fr(dp),
        covering_contract_ids=list(covering_contract_ids),
    )


def _summarize_contract(ct: EnergyContract, today: date) -> ContractSummary:
    return ContractSummary(
        id=ct.id,
        supplier_name=ct.supplier_name,
        energy_type=ct.energy_type.value if ct.energy_type else None,
        reference_fournisseur=ct.reference_fournisseur,
        start_date=ct.start_date.isoformat() if ct.start_date else None,
        end_date=ct.end_date.isoformat() if ct.end_date else None,
        is_expired=bool(ct.end_date and ct.end_date < today),
        delivery_point_ids=[dp.id for dp in (ct.delivery_points or [])],
        label_fr=_contract_label_fr(ct),
    )


# ─── API publique ───────────────────────────────────────────────────────────


def compute_site_contract_coverage(
    db: Session,
    site_id: int,
    org_id: int,
    *,
    today: Optional[date] = None,
) -> SiteContractCoverage:
    """Vue agrégée de la couverture contractuelle d'un site.

    Args:
        db: session SQLAlchemy
        site_id: identifiant du site
        org_id: scope organisationnel (anti-IDOR — l'appelant doit avoir
            validé que le site appartient à l'org via `assert_org_owns_site`).
        today: date de référence pour le calcul d'expiration (défaut today).

    Returns:
        `SiteContractCoverage` avec status cardinal + listes typées.
        Si le site n'existe pas dans la session : status `contrat_manquant`
        et listes vides (l'appelant gère le 404).

    Statuts cardinaux :
        - `contrat_rattache` : tous les DP actifs ont au moins un contrat actif
          couvrant, énergies cohérentes, aucun contrat expiré bloquant.
        - `contrat_partiel` : au moins un DP actif sans contrat actif (le site
          a des contrats mais pas pour tous ses DP).
        - `contrat_manquant` : DP actifs mais aucun contrat actif rattaché.
        - `contrat_expire` : tous les contrats du site sont expirés.
        - `contrat_incoherent` : mismatch d'énergie (ex : contrat élec sur PCE
          gaz) ou contrat liant un DP hors site.

    Le statut le plus dégradé domine (incoherent > expire > manquant > partiel > rattache).
    """
    today = today or date.today()
    now_iso = datetime.now(timezone.utc).isoformat()

    site = db.query(Site).filter(Site.id == site_id, not_deleted(Site)).first()
    if site is None:
        return SiteContractCoverage(
            site_id=site_id,
            org_id=org_id,
            status=COVERAGE_CONTRAT_MANQUANT,
            delivery_points_active=[],
            contracts_active=[],
            uncovered_delivery_points=[],
            expired_contracts=[],
            energy_mismatches=[],
            foreign_delivery_point_links=[],
            ready_for_billing=False,
            ready_for_purchase=False,
            actions=[],
            computed_at=now_iso,
        )

    # ── DP actifs du site ──
    dp_active: list[DeliveryPoint] = (
        not_deleted(db.query(DeliveryPoint), DeliveryPoint)
        .filter(
            DeliveryPoint.site_id == site_id,
            DeliveryPoint.status == DeliveryPointStatus.ACTIVE,
        )
        .all()
    )

    # ── Contrats du site (tous, on filtrera active/expired après) ──
    contracts_all: list[EnergyContract] = db.query(EnergyContract).filter(EnergyContract.site_id == site_id).all()
    contracts_active = [c for c in contracts_all if _is_contract_active_today(c, today)]
    contracts_expired = [c for c in contracts_all if c.end_date and c.end_date < today]

    # ── Couverture DP par contrat actif ──
    coverage_map: dict[int, list[int]] = {dp.id: [] for dp in dp_active}
    mismatches: list[EnergyMismatch] = []
    foreign_links: list[dict[str, Any]] = []
    site_dp_ids = {dp.id for dp in dp_active}

    for ct in contracts_active:
        for linked_dp in ct.delivery_points or []:
            if linked_dp.id in coverage_map:
                coverage_map[linked_dp.id].append(ct.id)
                if not _is_energy_compatible(ct.energy_type, linked_dp.energy_type):
                    mismatches.append(
                        EnergyMismatch(
                            contract_id=ct.id,
                            delivery_point_id=linked_dp.id,
                            contract_energy=ct.energy_type.value if ct.energy_type else None,
                            delivery_point_energy=linked_dp.energy_type.value if linked_dp.energy_type else None,
                            message_fr=(
                                f"Contrat {_contract_label_fr(ct)} rattaché à "
                                f"{_dp_label_fr(linked_dp)} — énergies incompatibles."
                            ),
                        )
                    )
            else:
                # Contrat du site liant un DP qui n'est pas du site
                # (ou DP archivé / appartenant à un autre site)
                foreign_links.append(
                    {
                        "contract_id": ct.id,
                        "delivery_point_id": linked_dp.id,
                        "delivery_point_code": linked_dp.code,
                        "delivery_point_site_id": linked_dp.site_id,
                        "message_fr": (
                            f"Contrat {_contract_label_fr(ct)} rattaché à un point de "
                            f"livraison qui n'appartient pas à ce site (DP #{linked_dp.id})."
                        ),
                    }
                )

    # ── Synthèse DP ──
    dp_summaries: list[DeliveryPointSummary] = [_summarize_dp(dp, coverage_map[dp.id]) for dp in dp_active]
    uncovered = [s for s in dp_summaries if not s.covering_contract_ids]

    # ── Status cardinal (le plus dégradé domine) ──
    if mismatches or foreign_links:
        status = COVERAGE_CONTRAT_INCOHERENT
    elif dp_active and not contracts_active:
        status = COVERAGE_CONTRAT_EXPIRE if contracts_expired else COVERAGE_CONTRAT_MANQUANT
    elif uncovered:
        status = COVERAGE_CONTRAT_PARTIEL
    elif dp_active:
        status = COVERAGE_CONTRAT_RATTACHE
    else:
        # Pas de DP actifs : on considère le site comme non-prêt facture
        # mais sans incohérence, donc rattache (rien à couvrir).
        status = COVERAGE_CONTRAT_RATTACHE

    # ── Ready flags ──
    ready_for_billing = (
        status == COVERAGE_CONTRAT_RATTACHE and bool(contracts_active) and not mismatches and not foreign_links
    )
    ready_for_purchase = ready_for_billing and bool(dp_active)

    # ── Actions FR ──
    actions: list[CoverageAction] = []
    for dp_sum in uncovered:
        actions.append(
            CoverageAction(
                code="ATTACH_CONTRACT",
                label_fr=f"Rattacher un contrat à {dp_sum.label_fr}",
                target_type="delivery_point",
                target_id=dp_sum.id,
            )
        )
    for ct in contracts_expired:
        actions.append(
            CoverageAction(
                code="RENEW_CONTRACT",
                label_fr=f"Renouveler le contrat {_contract_label_fr(ct)} (expiré le {ct.end_date.isoformat() if ct.end_date else '?'})",
                target_type="contract",
                target_id=ct.id,
            )
        )
    for m in mismatches:
        actions.append(
            CoverageAction(
                code="FIX_ENERGY_MISMATCH",
                label_fr=f"Corriger le rattachement énergie du contrat #{m.contract_id}",
                target_type="contract",
                target_id=m.contract_id,
            )
        )
    for fl in foreign_links:
        actions.append(
            CoverageAction(
                code="DETACH_FOREIGN_DP",
                label_fr=f"Détacher le point de livraison #{fl['delivery_point_id']} du contrat #{fl['contract_id']}",
                target_type="contract",
                target_id=fl["contract_id"],
            )
        )

    return SiteContractCoverage(
        site_id=site_id,
        org_id=org_id,
        status=status,
        delivery_points_active=dp_summaries,
        contracts_active=[_summarize_contract(c, today) for c in contracts_active],
        uncovered_delivery_points=uncovered,
        expired_contracts=[_summarize_contract(c, today) for c in contracts_expired],
        energy_mismatches=mismatches,
        foreign_delivery_point_links=foreign_links,
        ready_for_billing=ready_for_billing,
        ready_for_purchase=ready_for_purchase,
        actions=actions,
        computed_at=now_iso,
    )
