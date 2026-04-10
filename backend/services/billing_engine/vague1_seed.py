"""
PROMEOS — Seed de compatibilité data model Vague 1.

Alimente les nouvelles colonnes/tables introduites par la Vague 1 à partir
des données déjà présentes dans la base. Idempotent : ne touche aucune
valeur non-null existante.

Règles de dérivation :

- `DeliveryPoint.grd_code` :
    * energy_type == elec → "ENEDIS"
    * energy_type == gaz  → "GRDF"
    * inconnu             → None (laissé vide)

- `TaxProfile` par DeliveryPoint :
    * élec BT ≤ 36 kVA (C5_BT)   → HOUSEHOLD
    * élec BT > 36 kVA (C4_BT)   → SME
    * élec HTA (C3_HTA)          → HIGH_POWER
    * gaz                         → NORMAL
    * regime_reduit = False par défaut

- `EnergyContract` pass-through :
    * cee_pass_through      → False (CEE inclus dans le prix)
    * accise_pass_through   → True  (ligne séparée standard)
    * network_cost_model    → INCLUDED (TURPE/ATRD refacturé)

  Ces valeurs sont déjà les defaults DB ; seul le NULL→INCLUDED sur
  network_cost_model doit être forcé explicitement.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class SeedSummary:
    """Résumé des modifications appliquées par le seed."""

    grd_codes_set: int = 0
    tax_profiles_created: int = 0
    network_cost_model_set: int = 0
    skipped_already_populated: int = 0
    errors: list[str] = field(default_factory=list)


def _derive_grd_code(energy_type_value: Optional[str]) -> Optional[str]:
    """Déduit le GRD par défaut depuis le type d'énergie du PDL."""
    if energy_type_value is None:
        return None
    v = str(energy_type_value).lower()
    if v in ("elec", "electricity", "electricite"):
        return "ENEDIS"
    if v in ("gaz", "gas", "natural_gas"):
        return "GRDF"
    return None


def _derive_tax_profile_elec(segment: Optional[str]):
    """Déduit la catégorie accise élec depuis le segment TURPE."""
    from models.enums import AcciseCategoryElec

    if not segment:
        return AcciseCategoryElec.HOUSEHOLD  # fallback prudent
    s = str(segment).upper()
    if "C3" in s or "HTA" in s:
        return AcciseCategoryElec.HIGH_POWER
    if "C4" in s:
        return AcciseCategoryElec.SME
    return AcciseCategoryElec.HOUSEHOLD


def seed_vague1(db: Session) -> SeedSummary:
    """
    Exécute le seed de compatibilité. Idempotent : les valeurs déjà
    renseignées sont laissées intactes.
    """
    from models.billing_models import EnergyContract
    from models.enums import (
        AcciseCategoryElec,
        AcciseCategoryGaz,
        NetworkCostModel,
    )
    from models.patrimoine import DeliveryPoint
    from models.tax_profile import TaxProfile

    summary = SeedSummary()

    # ── 1. Dériver grd_code sur DeliveryPoint ────────────────────────────
    pdls = db.query(DeliveryPoint).filter(DeliveryPoint.grd_code.is_(None)).all()
    for pdl in pdls:
        energy_val = getattr(pdl.energy_type, "value", pdl.energy_type)
        grd = _derive_grd_code(energy_val)
        if grd is not None:
            pdl.grd_code = grd
            summary.grd_codes_set += 1
        else:
            summary.skipped_already_populated += 1

    # ── 2. Créer TaxProfile par défaut (1 par PDL sans profil existant) ─
    existing_pdl_ids = {tp.delivery_point_id for tp in db.query(TaxProfile).all()}
    all_pdls = db.query(DeliveryPoint).all()

    for pdl in all_pdls:
        if pdl.id in existing_pdl_ids:
            summary.skipped_already_populated += 1
            continue

        energy_val = getattr(pdl.energy_type, "value", pdl.energy_type)
        energy_val_s = str(energy_val).lower() if energy_val else ""

        tp = TaxProfile(
            delivery_point_id=pdl.id,
            regime_reduit=False,
        )

        if energy_val_s in ("elec", "electricity", "electricite"):
            segment_val = getattr(pdl.tariff_segment, "value", pdl.tariff_segment)
            tp.accise_category_elec = _derive_tax_profile_elec(segment_val)
        elif energy_val_s in ("gaz", "gas", "natural_gas"):
            tp.accise_category_gaz = AcciseCategoryGaz.NORMAL
        else:
            # Énergie inconnue : on pose un profil HOUSEHOLD par prudence
            tp.accise_category_elec = AcciseCategoryElec.HOUSEHOLD

        db.add(tp)
        summary.tax_profiles_created += 1

    # ── 3. Forcer network_cost_model = INCLUDED sur les contrats nulls ──
    contracts = db.query(EnergyContract).filter(EnergyContract.network_cost_model.is_(None)).all()
    for c in contracts:
        c.network_cost_model = NetworkCostModel.INCLUDED
        summary.network_cost_model_set += 1

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        summary.errors.append(f"commit failed: {exc}")
        logger.exception("seed_vague1 commit failed")

    logger.info(
        "seed_vague1: grd_codes=%d, tax_profiles=%d, network_cost=%d, skipped=%d, errors=%d",
        summary.grd_codes_set,
        summary.tax_profiles_created,
        summary.network_cost_model_set,
        summary.skipped_already_populated,
        len(summary.errors),
    )
    return summary


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Permet de lancer depuis backend/ : `python -m services.billing_engine.vague1_seed`
    BACKEND_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(BACKEND_DIR))

    from database.connection import SessionLocal  # type: ignore

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    with SessionLocal() as db:
        result = seed_vague1(db)
    print(f"Seed summary: {result}")
