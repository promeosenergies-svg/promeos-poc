"""
Chargeur de tarifs reglementes depuis YAML -> DB.
Insert-only: chaque chargement ajoute les tarifs manquants, ne modifie jamais.
"""

import yaml
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models.market_models import RegulatedTariff, TariffType, TariffComponent

REFERENTIAL_DIR = Path(__file__).parent.parent / "referentials"


def load_tariffs_from_yaml(db: Session, filepath: str = None) -> dict:
    """
    Charge les tarifs depuis le YAML dans la DB.
    Retourne {"inserted": N, "skipped": N, "version": "..."}
    """
    if filepath is None:
        filepath = REFERENTIAL_DIR / "market_tariffs_2026.yaml"

    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    version = data.get("version", "unknown")
    inserted = 0
    skipped = 0

    for section_key, section in data.items():
        if section_key in ("version", "last_updated", "next_review"):
            continue
        if not isinstance(section, dict):
            continue

        tariff_type = _map_tariff_type(section_key)
        if tariff_type is None:
            continue

        source_name = section.get("source", "unknown")
        source_url = section.get("source_url")

        rates = section.get("rates") or section.get("values") or []
        valid_from_str = section.get("valid_from")
        valid_to_str = section.get("valid_to")

        valid_from = _parse_date(valid_from_str) if valid_from_str else datetime.now(timezone.utc)
        valid_to = _parse_date(valid_to_str) if valid_to_str else None

        for rate in rates:
            component_str = rate.get("component")
            try:
                component = TariffComponent(component_str)
            except ValueError:
                continue

            # Verifier si deja present (meme composant + version + valid_from)
            existing = (
                db.query(RegulatedTariff)
                .filter(
                    RegulatedTariff.tariff_type == tariff_type,
                    RegulatedTariff.component == component,
                    RegulatedTariff.version == version,
                    RegulatedTariff.valid_from == valid_from,
                )
                .first()
            )

            if existing:
                skipped += 1
                continue

            tariff = RegulatedTariff(
                tariff_type=tariff_type,
                component=component,
                value=rate["value"],
                unit=rate["unit"],
                valid_from=valid_from,
                valid_to=valid_to,
                source_name=source_name,
                source_reference=source_url,
                version=version,
                notes=rate.get("notes"),
                applies_to_profile=rate.get("applies_to_profile"),
                applies_to_voltage=rate.get("applies_to_voltage"),
                applies_to_power_range=rate.get("applies_to_power_range"),
            )
            db.add(tariff)
            inserted += 1

    db.commit()
    return {"inserted": inserted, "skipped": skipped, "version": version}


def get_current_tariff(
    db: Session, tariff_type: TariffType, component: TariffComponent, at_date: datetime = None
) -> RegulatedTariff | None:
    """
    Retourne le tarif en vigueur a une date donnee.
    Si at_date=None, retourne le tarif courant.
    """
    if at_date is None:
        at_date = datetime.now(timezone.utc)

    return (
        db.query(RegulatedTariff)
        .filter(
            RegulatedTariff.tariff_type == tariff_type,
            RegulatedTariff.component == component,
            RegulatedTariff.valid_from <= at_date,
            (RegulatedTariff.valid_to.is_(None)) | (RegulatedTariff.valid_to >= at_date),
        )
        .order_by(RegulatedTariff.valid_from.desc())
        .first()
    )


def _map_tariff_type(key: str) -> TariffType | None:
    """Mappe une cle YAML vers un TariffType, en ignorant les suffixes de version.

    Exemples: 'turpe' -> TURPE, 'turpe_v6' -> TURPE, 'cspe_2024' -> CSPE,
    'capacity_2025' -> CAPACITY, 'cee_p5' -> CEE, 'cta_2021' -> CTA.
    """
    mapping = {
        "cspe": TariffType.CSPE,
        "capacity": TariffType.CAPACITY,
        "vnu": TariffType.VNU,
        "cee": TariffType.CEE,
        "cta": TariffType.CTA,
        "tva": TariffType.TVA,
        "turpe": TariffType.TURPE,
        "atrd": TariffType.ATRD,
        "atrt": TariffType.ATRT,
        "ticgn": TariffType.TICGN,
    }
    # Correspondance exacte d'abord
    if key in mapping:
        return mapping[key]
    # Puis par prefixe (turpe_v6 -> turpe, cspe_2024 -> cspe, etc.)
    for prefix, tt in mapping.items():
        if key.startswith(prefix + "_"):
            return tt
    return None


def _parse_date(s: str) -> datetime:
    return (
        datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        if "T" in s
        else datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    )
