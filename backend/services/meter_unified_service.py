"""
PROMEOS — Service unifié pour les compteurs (Step 25).

Abstraction qui lit Meter (source primaire) et Compteur (legacy fallback).
Tous les nouveaux modules doivent passer par ce service.
"""

from sqlalchemy.orm import Session

from models.energy_models import Meter


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
                "energy_vector": sm.energy_vector.value if sm.energy_vector else None,
            }
            for sm in (m.sub_meters or [])
        ],
    }


def _add_legacy_compteurs(db: Session, site_id: int, meters: list, result: list):
    """Ajoute les compteurs legacy non couverts par Meter."""
    from models.compteur import Compteur
    from models import not_deleted

    compteurs = not_deleted(db.query(Compteur), Compteur).filter(
        Compteur.site_id == site_id
    ).all()

    # Clés de dédup
    meter_serials = {m.numero_serie for m in meters if m.numero_serie}
    meter_prms = {m.meter_id for m in meters if m.meter_id}

    for c in compteurs:
        # Skip si déjà couvert par un Meter
        if c.numero_serie and c.numero_serie in meter_serials:
            continue
        if c.meter_id and c.meter_id in meter_prms:
            continue

        result.append({
            "id": f"legacy_{c.id}",
            "source": "compteur_legacy",
            "meter_id": getattr(c, "meter_id", None),
            "numero_serie": c.numero_serie,
            "energy_vector": c.energy_vector.value if c.energy_vector else _type_to_vector(c.type.value if c.type else None),
            "type_compteur": c.type.value if c.type else None,
            "subscribed_power_kva": c.puissance_souscrite_kw,
            "site_id": c.site_id,
            "delivery_point_id": c.delivery_point_id,
            "has_readings": False,
            "is_active": c.actif,
            "name": c.numero_serie or f"Compteur #{c.id}",
            "marque": None,
            "modele": None,
            "sub_meters": [],
        })


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
