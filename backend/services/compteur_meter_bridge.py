"""
PROMEOS — Compteur ↔ Meter bridge service (Phase D-2 hotfix Tier 1 P0.3 — ADR-D-01).

Bridge cardinal pour résoudre la dualité Compteur (SoT onboarding/wizard) vs Meter
(SoT runtime consommation/breakdown/cost-by-period). Audit cardinal :
`docs/audits/AUDIT_D6_DUALITE_RUNTIME_2026_05_07.md` Option C.

Le différenciateur Phase D-0 "pilotage CVC/IT/éclairage par sous-compteur" est exposé
runtime via `Meter.parent_meter_id` + `meter_unified_service.get_site_meters_tree`.
Compteur sert au stade onboarding (wizard, CSV, API import) et est bridgé vers Meter
**post-create** par les wizards via `ensure_meter_pair()`.

Anti-pattern Pilier 8 candidat ADR-016 :
    "Self-FK orphelin sans wiring service runtime" — toute self-FK ajoutée à un modèle
    SoT-onboarding doit déclarer un bridge explicite vers le SoT runtime.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from models.compteur import Compteur
from models.energy_models import EnergyVector, Meter


def _energy_vector_from_type(type_compteur: str | None) -> EnergyVector:
    """Mappe le type de compteur (FR) vers EnergyVector enum runtime."""
    if not type_compteur:
        return EnergyVector.ELECTRICITY
    t = type_compteur.lower()
    if "gaz" in t or t == "gas":
        return EnergyVector.GAS
    if "eau" in t or t == "water":
        return EnergyVector.WATER
    return EnergyVector.ELECTRICITY


def find_meter_by_compteur(db: Session, compteur: Compteur) -> Optional[Meter]:
    """Recherche le Meter sœur d'un Compteur.

    Match (priorité décroissante) — toutes les recherches sont **scopées site_id**
    pour éviter les collisions cross-tenant (P1-3 code-reviewer Phase D-2 audit) :
    1. `meter.numero_serie == compteur.numero_serie` AND `meter.site_id == compteur.site_id`
    2. `meter.meter_id == compteur.meter_id` (PRM/PCE) AND `meter.site_id == compteur.site_id`
    3. `meter.delivery_point_id == compteur.delivery_point_id` AND `meter.site_id == compteur.site_id`
    """
    if compteur.numero_serie:
        m = (
            db.query(Meter)
            .filter(Meter.numero_serie == compteur.numero_serie, Meter.site_id == compteur.site_id)
            .first()
        )
        if m is not None:
            return m

    if compteur.meter_id:
        m = db.query(Meter).filter(Meter.meter_id == compteur.meter_id, Meter.site_id == compteur.site_id).first()
        if m is not None:
            return m

    if compteur.delivery_point_id:
        m = (
            db.query(Meter)
            .filter(
                Meter.delivery_point_id == compteur.delivery_point_id,
                Meter.site_id == compteur.site_id,
            )
            .first()
        )
        if m is not None:
            return m

    return None


def ensure_meter_pair(
    db: Session,
    compteur: Compteur,
    *,
    commit: bool = False,
    _visited: Optional[set[int]] = None,
) -> Meter:
    """Garantit qu'un Meter sœur existe pour un Compteur (cardinal Phase D-2 P0.3).

    Si absent, le crée en propageant `numero_serie`, `meter_id`, `site_id`,
    `delivery_point_id`, et la hiérarchie sub_meter_of_id → parent_meter_id.

    À appeler post-create par tout wizard onboarding qui matérialise un Compteur
    avec `sub_meter_of_id` pour garantir le drill-down runtime.

    Phase D-2.2 fix P1-1 code-reviewer : garde anti-cycle `_visited` empêche la
    récursion infinie en cas d'auto-référence (`sub_meter_of_id == self.id`) ou
    de chaîne circulaire A→B→A non interceptée par contrainte DB.

    Args:
        db: SQLAlchemy session.
        compteur: Compteur source (déjà flushé en DB — id requis pour bridge parent).
        commit: si True, commit la transaction. Sinon, flush only.
        _visited: set d'ids de Compteur déjà traversés (param interne récursion).

    Returns:
        Meter sœur (existant ou nouvellement créé).

    Raises:
        ValueError si compteur.id est None (non flushé), si numero_serie + meter_id
        absents, ou si cycle détecté dans la hiérarchie sub_meter_of_id.
    """
    if compteur.id is None:
        raise ValueError("ensure_meter_pair: compteur doit être flushé en DB (compteur.id requis)")

    if _visited is None:
        _visited = set()
    if compteur.id in _visited:
        raise ValueError(
            f"ensure_meter_pair: cycle détecté dans la hiérarchie Compteur "
            f"(id={compteur.id} déjà visité, chaîne {sorted(_visited)})"
        )
    # Auto-référence directe = cycle trivial à intercepter immédiatement.
    if compteur.sub_meter_of_id == compteur.id:
        raise ValueError(
            f"ensure_meter_pair: cycle détecté — auto-référence Compteur id={compteur.id} "
            f"(sub_meter_of_id == id) — état pathologique non autorisé."
        )
    _visited.add(compteur.id)

    existing = find_meter_by_compteur(db, compteur)
    if existing is not None:
        # Bridge hiérarchie : si compteur a un parent Compteur, propager vers Meter.parent_meter_id
        if compteur.sub_meter_of_id is not None and existing.parent_meter_id is None:
            parent_compteur = db.query(Compteur).filter(Compteur.id == compteur.sub_meter_of_id).first()
            if parent_compteur is not None:
                parent_meter = find_meter_by_compteur(db, parent_compteur)
                if parent_meter is not None:
                    existing.parent_meter_id = parent_meter.id
                    db.flush()
        if commit:
            db.commit()
        return existing

    # Création Meter sœur
    if not compteur.numero_serie and not compteur.meter_id:
        raise ValueError(
            f"ensure_meter_pair: Compteur {compteur.id} doit avoir numero_serie OU meter_id "
            f"pour créer un Meter sœur (clé d'identification cardinale)."
        )

    meter_identifier = compteur.meter_id or compteur.numero_serie
    meter = Meter(
        meter_id=meter_identifier,
        name=f"Meter from Compteur#{compteur.id}",
        energy_vector=_energy_vector_from_type(compteur.type.value if compteur.type else None),
        site_id=compteur.site_id,
        is_active=compteur.actif,
        numero_serie=compteur.numero_serie,
        type_compteur=compteur.type.value if compteur.type else None,
        delivery_point_id=compteur.delivery_point_id,
        subscribed_power_kva=compteur.puissance_souscrite_kw,
    )
    db.add(meter)
    db.flush()

    # Bridge hiérarchie (récursion safe via _visited)
    if compteur.sub_meter_of_id is not None:
        parent_compteur = db.query(Compteur).filter(Compteur.id == compteur.sub_meter_of_id).first()
        if parent_compteur is not None:
            parent_meter = find_meter_by_compteur(db, parent_compteur)
            if parent_meter is None:
                parent_meter = ensure_meter_pair(db, parent_compteur, commit=False, _visited=_visited)
            meter.parent_meter_id = parent_meter.id
            db.flush()

    if commit:
        db.commit()
    return meter
