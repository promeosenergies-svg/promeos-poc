"""
PROMEOS — Service trajectoire OPERAT (Decret Tertiaire)

Calcul des objectifs -40% (2030) / -50% (2040) / -60% (2050)
a partir de la consommation de reference d'une EFA.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import TertiaireEfa, TertiaireEfaConsumption

logger = logging.getLogger("promeos.operat.trajectory")

# Objectifs reglementaires Decret Tertiaire (relatifs a la baseline)
TARGETS = {
    2030: 0.60,  # -40%
    2040: 0.50,  # -50%
    2050: 0.40,  # -60%
}


def declare_consumption(
    db: Session,
    efa_id: int,
    year: int,
    kwh_total: float,
    kwh_elec: Optional[float] = None,
    kwh_gaz: Optional[float] = None,
    kwh_reseau: Optional[float] = None,
    is_reference: bool = False,
    source: Optional[str] = None,
) -> dict:
    """Declare ou met a jour la consommation annuelle d'une EFA.

    Si is_reference=True, verrouille cette annee comme reference sur l'EFA.
    Contrainte : une seule annee de reference par EFA.
    """
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if not efa:
        raise ValueError(f"EFA {efa_id} introuvable")

    if kwh_total < 0:
        raise ValueError("kwh_total ne peut pas etre negatif")
    if year < 2000 or year > 2060:
        raise ValueError(f"Annee {year} hors plage valide (2000-2060)")

    # Verifier unicite annee de reference
    if is_reference:
        existing_ref = (
            db.query(TertiaireEfaConsumption)
            .filter(
                TertiaireEfaConsumption.efa_id == efa_id,
                TertiaireEfaConsumption.is_reference.is_(True),
                TertiaireEfaConsumption.year != year,
            )
            .first()
        )
        if existing_ref:
            raise ValueError(
                f"Une annee de reference existe deja pour cette EFA (annee {existing_ref.year}). Modifiez-la d'abord."
            )

    # Upsert consommation
    conso = (
        db.query(TertiaireEfaConsumption)
        .filter(
            TertiaireEfaConsumption.efa_id == efa_id,
            TertiaireEfaConsumption.year == year,
        )
        .first()
    )
    if conso:
        conso.kwh_total = kwh_total
        conso.kwh_elec = kwh_elec
        conso.kwh_gaz = kwh_gaz
        conso.kwh_reseau = kwh_reseau
        conso.is_reference = is_reference
        conso.is_normalized = False
        conso.source = source
    else:
        conso = TertiaireEfaConsumption(
            efa_id=efa_id,
            year=year,
            kwh_total=kwh_total,
            kwh_elec=kwh_elec,
            kwh_gaz=kwh_gaz,
            kwh_reseau=kwh_reseau,
            is_reference=is_reference,
            is_normalized=False,
            source=source,
        )
        db.add(conso)

    # Mettre a jour les champs cache sur l'EFA si reference
    if is_reference:
        efa.reference_year = year
        efa.reference_year_kwh = kwh_total

    db.flush()

    return {
        "id": conso.id,
        "efa_id": efa_id,
        "year": year,
        "kwh_total": kwh_total,
        "is_reference": is_reference,
        "action": "updated" if conso.id else "created",
    }


def validate_trajectory(
    db: Session,
    efa_id: int,
    observation_year: int,
) -> dict:
    """Calcule la trajectoire OPERAT pour une EFA a une annee d'observation.

    Retourne baseline, conso courante, objectifs, ecart, statut.
    """
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if not efa:
        raise ValueError(f"EFA {efa_id} introuvable")

    warnings = []
    missing_fields = []

    # 1. Baseline
    baseline_conso = (
        db.query(TertiaireEfaConsumption)
        .filter(
            TertiaireEfaConsumption.efa_id == efa_id,
            TertiaireEfaConsumption.is_reference.is_(True),
        )
        .first()
    )
    if not baseline_conso:
        return {
            "efa_id": efa_id,
            "observation_year": observation_year,
            "status": "not_evaluable",
            "baseline": None,
            "current": None,
            "targets": _compute_targets(None),
            "applicable_target_kwh": None,
            "applicable_target_year": None,
            "delta_kwh": None,
            "delta_percent": None,
            "is_normalized": False,
            "missing_fields": ["reference_year_consumption"],
            "warnings": ["Consommation de reference absente — trajectoire non evaluable"],
        }

    baseline_kwh = baseline_conso.kwh_total

    # 2. Consommation annee d'observation
    current_conso = (
        db.query(TertiaireEfaConsumption)
        .filter(
            TertiaireEfaConsumption.efa_id == efa_id,
            TertiaireEfaConsumption.year == observation_year,
        )
        .first()
    )
    current_kwh = current_conso.kwh_total if current_conso else None

    if current_kwh is None:
        missing_fields.append("current_year_consumption")
        warnings.append(f"Consommation {observation_year} absente")

    if not baseline_conso.is_normalized:
        warnings.append("Donnees non normalisees climatiquement")

    # 3. Objectifs
    targets = _compute_targets(baseline_kwh)

    # 4. Objectif applicable
    applicable_year = _applicable_target_year(observation_year)
    applicable_kwh = targets.get(str(applicable_year))

    # 5. Delta et statut
    if current_kwh is not None and applicable_kwh is not None:
        delta_kwh = current_kwh - applicable_kwh
        delta_percent = round((current_kwh / applicable_kwh - 1) * 100, 1)
        status = "on_track" if current_kwh <= applicable_kwh else "off_track"
    elif current_kwh is None:
        delta_kwh = None
        delta_percent = None
        status = "not_evaluable"
    else:
        delta_kwh = None
        delta_percent = None
        status = "not_evaluable"

    # 6. Mettre a jour le cache EFA
    efa.trajectory_status = status
    efa.trajectory_last_calculated_at = datetime.now(timezone.utc)
    db.flush()

    return {
        "efa_id": efa_id,
        "observation_year": observation_year,
        "baseline": {
            "year": baseline_conso.year,
            "kwh": baseline_kwh,
            "source": baseline_conso.source,
        },
        "current": {
            "year": observation_year,
            "kwh": current_kwh,
            "source": current_conso.source if current_conso else None,
        },
        "targets": targets,
        "applicable_target_kwh": applicable_kwh,
        "applicable_target_year": applicable_year,
        "delta_kwh": delta_kwh,
        "delta_percent": delta_percent,
        "status": status,
        "is_normalized": bool(baseline_conso.is_normalized and (current_conso and current_conso.is_normalized)),
        "missing_fields": missing_fields,
        "warnings": warnings,
    }


def get_consumption_history(db: Session, efa_id: int) -> list:
    """Retourne l'historique des consommations d'une EFA, par annee."""
    rows = (
        db.query(TertiaireEfaConsumption)
        .filter(TertiaireEfaConsumption.efa_id == efa_id)
        .order_by(TertiaireEfaConsumption.year)
        .all()
    )
    return [
        {
            "id": r.id,
            "year": r.year,
            "kwh_total": r.kwh_total,
            "kwh_elec": r.kwh_elec,
            "kwh_gaz": r.kwh_gaz,
            "kwh_reseau": r.kwh_reseau,
            "is_reference": r.is_reference,
            "is_normalized": r.is_normalized,
            "source": r.source,
        }
        for r in rows
    ]


def get_efa_baseline_kwh(db: Session, efa_id: int) -> Optional[float]:
    """Retourne la conso de reference d'une EFA, ou None si absente."""
    ref = (
        db.query(TertiaireEfaConsumption)
        .filter(
            TertiaireEfaConsumption.efa_id == efa_id,
            TertiaireEfaConsumption.is_reference.is_(True),
        )
        .first()
    )
    return ref.kwh_total if ref else None


# ── Helpers ────────────────────────────────────────────────────────────


def _compute_targets(baseline_kwh: Optional[float]) -> dict:
    """Calcule les objectifs 2030/2040/2050 depuis la baseline."""
    if baseline_kwh is None:
        return {"2030": None, "2040": None, "2050": None}
    return {str(y): round(baseline_kwh * factor) for y, factor in TARGETS.items()}


def _applicable_target_year(observation_year: int) -> int:
    """Determine l'objectif applicable pour une annee d'observation."""
    if observation_year >= 2050:
        return 2050
    if observation_year >= 2040:
        return 2040
    return 2030
