"""
Seed Power Intelligence : PowerContract + HCPlageReference + PowerReading (CDC synthétique).

Règles Enedis :
- Unité stockée : kW (converti depuis Watts à l'ingestion)
- Horodate : débutante UTC
- Pas : 30 minutes (PME-PMI / Linky C5)
- tan φ ≈ 0.28 (réaliste bureau/tertiaire)
"""

import hashlib
import math
import re
import logging
from datetime import datetime, timedelta, date, timezone

from sqlalchemy.orm import Session

from models.power import PowerReading, PowerContract, HCPlageReference
from models.energy_models import Meter
from models.site import Site

logger = logging.getLogger(__name__)

# ── HC Plages de référence (C15 v5.1.3 §5.5.3) ──────────────────────────

HC_PLAGES_DATA = [
    (1, "HC (1H00-6H00;12H30-15H30)"),
    (2, "HC (1H00-7H00;11H00-13H00)"),
    (3, "HC (1H00-7H00;12H00-14H00)"),
    (4, "HC (1H00-7H00;12H30-14H30)"),
    (5, "HC (1H00-7H00;14H00-16H00)"),
    (6, "HC (1H00-7H00;14H30-16H30)"),
    (7, "HC (1H00-7H00;15H00-17H00)"),
    (8, "HC (1H00-7H00;20H00-22H00)"),
    (9, "HC (1H00-7H00;21H00-23H00)"),
    (10, "HC (1H00-7H30;12H00-13H30)"),
    (56, "HC (20H00-4H00)"),
    (57, "HC (20H30-4H30)"),
    (58, "HC (21H00-5H00)"),
    (62, "HC (22H00-6H00)"),
    (64, "HC (23H00-7H00)"),
    (65, "HC (23H30-7H30)"),
    (68, "HC (0H00-8H00)"),
    (70, "HC (1H00-7H00;13H00-15H00)"),
]


def _parse_hc_segments(libelle: str) -> list[dict]:
    """Parse 'HC (1H00-7H00;12H00-14H00)' → [{"debut": "01:00", "fin": "07:00"}, ...]"""
    match = re.search(r"\((.+?)\)", libelle)
    if not match:
        return []
    segments = []
    for seg in match.group(1).split(";"):
        parts = seg.strip().split("-")
        if len(parts) == 2:

            def fmt(h):
                h = h.strip().replace("H", ":")
                p = h.split(":")
                return f"{int(p[0]):02d}:{p[1] if len(p) > 1 else '00'}"

            segments.append({"debut": fmt(parts[0]), "fin": fmt(parts[1])})
    return segments


# ── PowerContract par site HELIOS ─────────────────────────────────────────

HELIOS_CONTRACTS = {
    "Paris": {
        "domaine_tension": "BTSUP",
        "fta_code": "BTSUPCU4",
        "type_compteur": "PME-PMI",
        "ps_par_poste_kva": {"HPH": 250, "HCH": 250, "HPE": 250, "HCE": 250},
        "p_raccordement_kva": 250,
    },
    "Lyon": {
        "domaine_tension": "BTSUP",
        "fta_code": "BTSUPCU4",
        "type_compteur": "PME-PMI",
        "ps_par_poste_kva": {"HPH": 90, "HCH": 90, "HPE": 90, "HCE": 90},
        "p_raccordement_kva": 90,
    },
    "Toulouse": {
        "domaine_tension": "HTA",
        "fta_code": "HTACU5",
        "type_compteur": "ICE",
        "ps_par_poste_kva": {"Pointe": 430, "HPH": 450, "HCH": 450, "HPE": 460, "HCE": 460},
        "p_raccordement_kva": 500,
    },
    "Nice": {
        "domaine_tension": "BTSUP",
        "fta_code": "BTSUPLU4",
        "type_compteur": "PME-PMI",
        "ps_par_poste_kva": {"Pointe": 180, "HPH": 220, "HCH": 220, "HPE": 220, "HCE": 220},
        "p_raccordement_kva": 250,
    },
    "Marseille": {
        "domaine_tension": "BTSUP",
        "fta_code": "BTSUPCU4",
        "type_compteur": "PME-PMI",
        "ps_par_poste_kva": {"HPH": 156, "HCH": 156, "HPE": 156, "HCE": 156},
        "p_raccordement_kva": 156,
    },
}

# Archétypes par ville (pour la CDC synthétique)
SITE_ARCHETYPES = {
    "Paris": ("BUREAU_STANDARD", 200),  # ps_max_kw
    "Lyon": ("BUREAU_STANDARD", 75),
    "Toulouse": ("LOGISTIQUE_SEC", 380),
    "Nice": ("HOTEL_HEBERGEMENT", 180),
    "Marseille": ("ENSEIGNEMENT", 130),
}


def seed_power(db: Session, days: int = 365) -> dict:
    """Seed HC plages + PowerContract + PowerReading pour HELIOS."""
    stats = {"hc_plages": 0, "contracts": 0, "readings": 0}

    # 1. HC Plages
    if db.query(HCPlageReference).count() == 0:
        for plage_id, libelle in HC_PLAGES_DATA:
            db.add(
                HCPlageReference(
                    id=plage_id,
                    libelle=libelle,
                    segments=_parse_hc_segments(libelle),
                    is_active=True,
                )
            )
        db.flush()
        stats["hc_plages"] = len(HC_PLAGES_DATA)

    # 2. PowerContracts + PowerReadings
    sites = db.query(Site).all()
    end_dt = datetime(2026, 4, 1, 0, 0)
    start_dt = end_dt - timedelta(days=days)

    for site in sites:
        # Trouver la ville dans le nom du site
        city = None
        for c in HELIOS_CONTRACTS:
            if c.lower() in site.nom.lower():
                city = c
                break
        if not city:
            continue

        # Compteur principal
        meter = (
            db.query(Meter)
            .filter(
                Meter.site_id == site.id,
                Meter.parent_meter_id.is_(None),
            )
            .first()
        )
        if not meter:
            continue

        # PowerContract (idempotent)
        existing_contract = (
            db.query(PowerContract)
            .filter(
                PowerContract.meter_id == meter.id,
            )
            .first()
        )
        if not existing_contract:
            cfg = HELIOS_CONTRACTS[city]
            db.add(
                PowerContract(
                    meter_id=meter.id,
                    date_debut=date(2020, 1, 1),
                    domaine_tension=cfg["domaine_tension"],
                    fta_code=cfg["fta_code"],
                    type_compteur=cfg["type_compteur"],
                    ps_par_poste_kva=cfg["ps_par_poste_kva"],
                    p_raccordement_kva=cfg["p_raccordement_kva"],
                    source_flux="manual",
                    created_at=datetime.now(timezone.utc),
                )
            )
            stats["contracts"] += 1

        # PowerReading (idempotent)
        existing_readings = (
            db.query(PowerReading)
            .filter(
                PowerReading.meter_id == meter.id,
            )
            .count()
        )
        if existing_readings > 100:
            continue

        archetype, ps_max_kw = SITE_ARCHETYPES.get(city, ("BUREAU_STANDARD", 100))
        count = _seed_power_readings(db, meter.id, archetype, ps_max_kw, start_dt, end_dt)
        stats["readings"] += count

    db.commit()
    logger.info(f"Power seed: {stats}")
    return stats


def _seed_power_readings(
    db: Session,
    meter_id: int,
    archetype: str,
    ps_max_kw: float,
    start_dt: datetime,
    end_dt: datetime,
) -> int:
    """Génère la CDC synthétique pour un compteur."""
    batch = []
    current = start_dt
    while current < end_dt:
        p_kw = _compute_power(archetype, current, ps_max_kw)
        batch.append(
            PowerReading(
                meter_id=meter_id,
                ts_debut=current,
                pas_minutes=30,
                P_active_kw=round(p_kw, 3),
                P_reactive_ind_kvar=round(p_kw * 0.28, 3),
                sens="CONS",
                mode_calcul="BRUT",
                nature_point="M",
                indice_vraisemblance=0,
                periode_tarif=_classify_tariff_period(current),
                source_flux="synthetic",
                imported_at=datetime.now(timezone.utc),
            )
        )
        current += timedelta(minutes=30)

        # Flush par batch de 5000
        if len(batch) >= 5000:
            db.bulk_save_objects(batch)
            db.flush()
            batch.clear()

    if batch:
        db.bulk_save_objects(batch)
        db.flush()

    return int((end_dt - start_dt).total_seconds() / 1800)


def _compute_power(archetype: str, ts: datetime, ps_max: float) -> float:
    """Puissance déterministe basée sur hash (reproductible)."""
    seed_str = f"{archetype}{ts.date()}{ts.hour}{ts.minute}"
    noise = (int(hashlib.md5(seed_str.encode()).hexdigest()[:4], 16) / 65535) * 0.1

    hour = ts.hour
    is_weekend = ts.weekday() >= 5
    is_summer = 4 <= ts.month <= 9

    if archetype == "BUREAU_STANDARD":
        if is_weekend:
            base = 0.08
        elif 9 <= hour < 12:
            base = 0.75 + (0.10 if not is_summer else -0.05)
        elif 14 <= hour < 17:
            base = 0.70 + (0.05 if not is_summer else -0.05)
        elif 8 <= hour < 9 or 12 <= hour < 14 or 17 <= hour < 19:
            base = 0.45
        elif 7 <= hour < 8 or 19 <= hour < 20:
            base = 0.25
        else:
            base = 0.12
    elif archetype == "HOTEL_HEBERGEMENT":
        if 6 <= hour < 23:
            base = 0.72 if is_summer else 0.70
        elif hour < 3 or hour >= 23:
            base = 0.35
        else:
            base = 0.45
    elif archetype == "ENSEIGNEMENT":
        if is_weekend or ts.month in (7, 8):
            base = 0.05
        elif 8 <= hour < 17:
            base = 0.60 + (0.05 if ts.month in (11, 12, 1, 2) else 0)
        elif 7 <= hour < 8 or 17 <= hour < 19:
            base = 0.30
        else:
            base = 0.08
    elif archetype == "LOGISTIQUE_SEC":
        if is_weekend:
            base = 0.15
        elif 8 <= hour < 18:
            base = 0.70
        elif 6 <= hour < 8 or 18 <= hour < 20:
            base = 0.35
        else:
            base = 0.10
    else:
        base = 0.30

    return min(ps_max * 0.95, max(ps_max * 0.03, ps_max * (base + noise - 0.05)))


def _classify_tariff_period(ts: datetime) -> str:
    """Classification simplifiée HP/HC (calendrier TURPE 7)."""
    hour = ts.hour
    is_hiver = ts.month in (11, 12, 1, 2, 3)
    heure_dec = hour + ts.minute / 60
    is_hc = (1.0 <= heure_dec < 7.0) or (12.0 <= heure_dec < 14.0)

    if ts.weekday() >= 5:
        if is_hiver:
            return "HCH" if is_hc else "HPH"
        return "HCE" if is_hc else "HPE"

    if is_hiver:
        if (9.0 <= heure_dec < 11.0) or (18.0 <= heure_dec < 20.0):
            return "Pointe"
        return "HCH" if is_hc else "HPH"
    return "HCE" if is_hc else "HPE"
