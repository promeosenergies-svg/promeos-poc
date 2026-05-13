"""PROMEOS — Évaluateur APER (parkings + ombrières) v1.0.

Référence normative : Loi n° 2023-175 du 10/03/2023 art. 40 (NOR : ENER2300175L)
+ Décret n° 2024-1023.

Règle cardinale v1.0 :
    Un site est assujetti APER si :
      - `parking_area_m2` ≥ 1 500 m² (catégories SMALL / LARGE)  OU
      - `roof_area_m2`    ≥ 500 m²  (obligation toiture solaire associée)

Catégories taille parking :
    SMALL : 1 500 - 10 000 m² → deadline 01/07/2028
    LARGE : > 10 000 m²       → deadline 01/07/2026

Cas DATA_MISSING : `parking_area_m2` ET `roof_area_m2` tous deux absents.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from regulatory.applicability_types import (
    ApplicabilityStatus,
    RuleApplicability,
    RuleCode,
)
from regulatory.rules.base import RuleEvaluator


APER_PARKING_THRESHOLD_M2: float = 1500.0
APER_PARKING_LARGE_M2: float = 10000.0
APER_ROOF_THRESHOLD_M2: float = 500.0

APER_DEADLINE_LARGE: date = date(2026, 7, 1)
APER_DEADLINE_SMALL: date = date(2028, 7, 1)


class APEREvaluator(RuleEvaluator):
    """Évaluateur Loi APER art. 40."""

    code = RuleCode.APER
    version = "APER-2023-175-v2024-07-01"
    scope = "site"

    def evaluate(self, site: Any) -> RuleApplicability:
        """Évalue l'assujettissement APER d'un site.

        Args:
            site: instance `models.Site` avec `parking_area_m2`, `roof_area_m2`.

        Returns:
            RuleApplicability immuable.
        """
        scope_id: int | None = getattr(site, "id", None)
        scope_label: str = f"Site {getattr(site, 'nom', f'#{scope_id}')}"
        parking_area: float | None = getattr(site, "parking_area_m2", None)
        roof_area: float | None = getattr(site, "roof_area_m2", None)

        inputs: dict[str, Any] = {
            "parking_area_m2": parking_area,
            "roof_area_m2": roof_area,
            "threshold_parking_m2": APER_PARKING_THRESHOLD_M2,
            "threshold_roof_m2": APER_ROOF_THRESHOLD_M2,
        }
        audit = self._build_audit(data_source="models.Site.{parking_area_m2,roof_area_m2}")

        # ── DATA_MISSING si les 2 champs sont absents ───────────────────
        if parking_area is None and roof_area is None:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.DATA_MISSING,
                reason_code="APER.DATA_MISSING.PARKING_AREA",
                reason_human=(
                    f"{scope_label} : ni surface parking ni surface toiture renseignées. APER non statuable."
                ),
                inputs_used=inputs,
                missing_inputs=["site.parking_area_m2", "site.roof_area_m2"],
                confidence=0.0,
                evidence_refs=["Loi 2023-175 art. 40"],
                _audit=audit,
            )

        # ── APPLICABLE.PARKING ──────────────────────────────────────────
        if parking_area is not None and parking_area >= APER_PARKING_THRESHOLD_M2:
            is_large = parking_area > APER_PARKING_LARGE_M2
            deadline = APER_DEADLINE_LARGE if is_large else APER_DEADLINE_SMALL
            category = "LARGE" if is_large else "SMALL"
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.APPLICABLE,
                reason_code="APER.APPLICABLE.PARKING",
                reason_human=(
                    f"{scope_label} : parking {parking_area:.0f} m² ≥ "
                    f"{APER_PARKING_THRESHOLD_M2:.0f} m² (catégorie {category}). "
                    f"Solarisation ombrière requise avant {deadline.strftime('%d/%m/%Y')}."
                ),
                inputs_used={**inputs, "category": category},
                confidence=1.0,
                evidence_refs=[
                    "Loi 2023-175 art. 40",
                    "Décret 2024-1023",
                ],
                deadline=deadline,
                _audit=audit,
            )

        # ── APPLICABLE.TOITURE ──────────────────────────────────────────
        if roof_area is not None and roof_area >= APER_ROOF_THRESHOLD_M2:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.APPLICABLE,
                reason_code="APER.APPLICABLE.TOITURE",
                reason_human=(
                    f"{scope_label} : toiture {roof_area:.0f} m² ≥ "
                    f"{APER_ROOF_THRESHOLD_M2:.0f} m². Obligation EnR toiture activée."
                ),
                inputs_used=inputs,
                confidence=1.0,
                evidence_refs=["Loi 2023-175 art. 40"],
                _audit=audit,
            )

        # ── NOT_APPLICABLE.PARKING_LT_1500 (priorité parking) ───────────
        if parking_area is not None and parking_area < APER_PARKING_THRESHOLD_M2:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason_code="APER.NOT_APPLICABLE.PARKING_LT_1500",
                reason_human=(
                    f"{scope_label} : parking {parking_area:.0f} m² < "
                    f"{APER_PARKING_THRESHOLD_M2:.0f} m². APER non applicable."
                ),
                inputs_used=inputs,
                confidence=1.0,
                evidence_refs=["Loi 2023-175 art. 40"],
                _audit=audit,
            )

        # ── NOT_APPLICABLE.NO_ELIGIBLE_AREA ─────────────────────────────
        return RuleApplicability(
            rule_code=self.code,
            rule_version=self.version,
            scope_level=self.scope,
            scope_id=scope_id,
            scope_label=scope_label,
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason_code="APER.NOT_APPLICABLE.NO_ELIGIBLE_AREA",
            reason_human=(
                f"{scope_label} : aucune surface éligible APER (parking={parking_area} m², toiture={roof_area} m²)."
            ),
            inputs_used=inputs,
            confidence=1.0,
            evidence_refs=["Loi 2023-175 art. 40"],
            _audit=audit,
        )
