"""
PROMEOS — Service unifié pour les compteurs (Step 25 + Step 26).

Abstraction qui lit Meter (source primaire) et Compteur (legacy fallback).
Step 26 : arbre sous-compteurs, création, breakdown.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.energy_models import Meter, MeterReading


# ── Step 25 : service unifié ────────────────────────────────────────────────


def get_site_meters(db: Session, site_id: int) -> list[dict]:
    """
    Retourne tous les compteurs d'un site, unifiés.
    Source primaire : Meter. Fallback : Compteur legacy (si pas de Meter correspondant).
    """
    meters = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active.is_(True),
            Meter.parent_meter_id.is_(None),
        )
        .all()
    )

    result = []
    for m in meters:
        result.append(_meter_to_dict(m))

    # Fallback : Compteurs legacy sans Meter correspondant
    if _has_compteur_model():
        _add_legacy_compteurs(db, site_id, meters, result)

    return result


# ── Step 26 : arbre, sous-compteurs, breakdown ─────────────────────────────


def get_site_meters_tree(db: Session, site_id: int) -> list[dict]:
    """
    Retourne les compteurs avec arbre hiérarchique (1 niveau).
    Compteur principal → sous-compteurs enrichis.
    """
    # Principaux
    principals = get_site_meters(db, site_id)

    # Sous-compteurs du site
    subs = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active.is_(True),
            Meter.parent_meter_id.isnot(None),
        )
        .all()
    )

    sub_by_parent = {}
    for s in subs:
        sub_by_parent.setdefault(s.parent_meter_id, []).append(_meter_to_dict(s))

    for p in principals:
        p["sub_meters"] = sub_by_parent.get(p["id"], [])

    return principals


def create_sub_meter(db: Session, parent_meter_id: int, data: dict) -> dict:
    """
    Crée un sous-compteur rattaché à un compteur principal.
    Hérite le site_id et energy_vector du parent si non spécifié.
    Refuse si le parent est lui-même un sous-compteur (1 niveau max).
    """
    parent = db.query(Meter).filter(Meter.id == parent_meter_id).first()
    if not parent:
        raise ValueError(f"Compteur principal {parent_meter_id} non trouvé")

    if parent.parent_meter_id is not None:
        raise ValueError("Impossible de créer un sous-compteur d'un sous-compteur (1 niveau max)")

    sub = Meter(
        site_id=parent.site_id,
        parent_meter_id=parent.id,
        meter_id=data.get(
            "meter_id",
            f"SUB-{parent.meter_id}-{db.query(Meter).filter(Meter.parent_meter_id == parent.id).count() + 1}",
        ),
        name=data.get(
            "name", f"Sous-compteur #{db.query(Meter).filter(Meter.parent_meter_id == parent.id).count() + 1}"
        ),
        energy_vector=data.get("energy_vector") or parent.energy_vector,
        type_compteur=data.get("type_compteur") or parent.type_compteur,
        subscribed_power_kva=data.get("subscribed_power_kva"),
        numero_serie=data.get("numero_serie"),
        is_active=True,
    )
    db.add(sub)
    db.flush()
    return _meter_to_dict(sub)


def delete_sub_meter(db: Session, parent_meter_id: int, sub_meter_id: int) -> bool:
    """Supprime un sous-compteur. Vérifie le rattachement parent."""
    sub = db.query(Meter).filter(Meter.id == sub_meter_id).first()
    if not sub or sub.parent_meter_id != parent_meter_id:
        return False
    sub.is_active = False
    db.flush()
    return True


def get_meter_breakdown(db: Session, meter_id: int, date_from=None, date_to=None) -> dict:
    """
    Compare la consommation du compteur principal vs somme des sous-compteurs.
    Retourne le breakdown avec delta (pertes & parties communes).
    """
    # Conso du principal
    q_principal = db.query(func.sum(MeterReading.value_kwh)).filter(MeterReading.meter_id == meter_id)
    if date_from:
        q_principal = q_principal.filter(MeterReading.timestamp >= date_from)
    if date_to:
        q_principal = q_principal.filter(MeterReading.timestamp <= date_to)
    principal_kwh = q_principal.scalar() or 0

    # Sous-compteurs
    subs = (
        db.query(Meter)
        .filter(
            Meter.parent_meter_id == meter_id,
            Meter.is_active.is_(True),
        )
        .all()
    )

    sub_details = []
    sub_total = 0

    for s in subs:
        q_sub = db.query(func.sum(MeterReading.value_kwh)).filter(MeterReading.meter_id == s.id)
        if date_from:
            q_sub = q_sub.filter(MeterReading.timestamp >= date_from)
        if date_to:
            q_sub = q_sub.filter(MeterReading.timestamp <= date_to)
        kwh = q_sub.scalar() or 0
        sub_total += kwh
        sub_details.append(
            {
                "id": s.id,
                "meter_id": s.meter_id,
                "name": s.name,
                "kwh": round(kwh, 2),
                "pct_of_total": round(kwh / principal_kwh * 100, 1) if principal_kwh > 0 else 0,
            }
        )

    delta = principal_kwh - sub_total
    delta_pct = (delta / principal_kwh * 100) if principal_kwh > 0 else 0

    return {
        "principal_kwh": round(principal_kwh, 2),
        "sub_meters_total_kwh": round(sub_total, 2),
        "delta_kwh": round(delta, 2),
        "delta_pct": round(delta_pct, 1),
        "delta_label": "Pertes & parties communes" if delta >= 0 else "Écart négatif (anomalie)",
        "sub_meters": sub_details,
    }


# ── Helpers ─────────────────────────────────────────────────────────────────


def _meter_to_dict(m: Meter) -> dict:
    """Convertit un Meter en dict unifié."""
    return {
        "id": m.id,
        "source": "meter",
        "meter_id": m.meter_id,
        "numero_serie": m.numero_serie,
        "energy_vector": m.energy_vector.value if m.energy_vector else None,
        "type_compteur": m.type_compteur or _infer_type(m.energy_vector),
        "subscribed_power_kva": m.subscribed_power_kva,
        "site_id": m.site_id,
        "parent_meter_id": m.parent_meter_id,
        "delivery_point_id": m.delivery_point_id,
        "has_readings": len(m.readings) > 0 if m.readings else False,
        "is_active": m.is_active,
        "name": m.name,
        "marque": m.marque,
        "modele": m.modele,
        "sub_meters": [
            {
                "id": sm.id,
                "meter_id": sm.meter_id,
                "name": sm.name,
                "energy_vector": sm.energy_vector.value if sm.energy_vector else None,
            }
            for sm in (m.sub_meters or [])
        ],
    }


def _add_legacy_compteurs(db: Session, site_id: int, meters: list, result: list):
    """Ajoute les compteurs legacy non couverts par Meter."""
    from models.compteur import Compteur
    from models import not_deleted

    compteurs = not_deleted(db.query(Compteur), Compteur).filter(Compteur.site_id == site_id).all()

    # Clés de dédup
    meter_serials = {m.numero_serie for m in meters if m.numero_serie}
    meter_prms = {m.meter_id for m in meters if m.meter_id}

    for c in compteurs:
        # Skip si déjà couvert par un Meter
        if c.numero_serie and c.numero_serie in meter_serials:
            continue
        if c.meter_id and c.meter_id in meter_prms:
            continue

        result.append(
            {
                "id": f"legacy_{c.id}",
                "source": "compteur_legacy",
                "meter_id": getattr(c, "meter_id", None),
                "numero_serie": c.numero_serie,
                "energy_vector": c.energy_vector.value
                if c.energy_vector
                else _type_to_vector(c.type.value if c.type else None),
                "type_compteur": c.type.value if c.type else None,
                "subscribed_power_kva": c.puissance_souscrite_kw,
                "site_id": c.site_id,
                "parent_meter_id": None,
                "delivery_point_id": c.delivery_point_id,
                "has_readings": False,
                "is_active": c.actif,
                "name": c.numero_serie or f"Compteur #{c.id}",
                "marque": None,
                "modele": None,
                "sub_meters": [],
            }
        )


def _infer_type(energy_vector) -> str | None:
    """Déduit le type_compteur depuis l'energy_vector."""
    if energy_vector is None:
        return None
    ev = energy_vector.value if hasattr(energy_vector, "value") else str(energy_vector)
    return {"electricity": "electricite", "gas": "gaz", "other": "eau"}.get(ev.lower() if ev else "")


def _type_to_vector(type_compteur: str | None) -> str | None:
    """Convertit un type_compteur en energy_vector string."""
    if not type_compteur:
        return None
    return {"electricite": "electricity", "gaz": "gas", "eau": "other"}.get(type_compteur)


def _has_compteur_model() -> bool:
    try:
        from models.compteur import Compteur  # noqa: F401

        return True
    except ImportError:
        return False
