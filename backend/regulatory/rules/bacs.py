"""PROMEOS — Évaluateur BACS (régulation CVC) v1.0.

Référence normative : Décret n° 2020-887 (R175-3 Code construction) +
Décret n° 2025-1343 (abaissement seuil à 70 kW au 01/01/2030).

Seuils figés v1.0 (cf. `backend/doctrine/constants.py`) :
    BACS_THRESHOLD_KW_INITIAL = 290 kW (2025, période initiale)
    BACS_THRESHOLD_KW_EXISTING = 70 kW (2030, abaissé pour parc existant)

Règle cardinale v1.0 :
    Un site est assujetti BACS si **au moins un bâtiment** a une puissance
    CVC nominale (`cvc_power_kw`) > BACS_THRESHOLD_KW_EXISTING (70 kW).

Cas DATA_MISSING : aucun bâtiment, ou bâtiment(s) sans `cvc_power_kw`.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from datetime import datetime

from doctrine.constants import (
    BACS_DEADLINE_EXISTING,
    BACS_DEADLINE_INITIAL,
    BACS_THRESHOLD_KW_EXISTING,
    BACS_THRESHOLD_KW_INITIAL,
)

from regulatory.applicability_types import (
    ApplicabilityStatus,
    RuleApplicability,
    RuleCode,
)
from regulatory.rules.base import RuleEvaluator


def _parse_iso_date(s: str) -> date:
    """Parse YYYY-MM-DD."""
    return datetime.strptime(s, "%Y-%m-%d").date()


class BACSEvaluator(RuleEvaluator):
    """Évaluateur Décret BACS (régulation CVC)."""

    code = RuleCode.BACS
    version = "BACS-2020-887+2025-1343-v2025-12-31"
    scope = "site"

    def evaluate(self, site: Any, batiments: Iterable[Any]) -> RuleApplicability:
        """Évalue l'assujettissement BACS d'un site sur la base de ses bâtiments.

        Args:
            site: instance `models.Site` (pour `id`/`nom`).
            batiments: itérable de `models.Batiment` avec `cvc_power_kw`.

        Returns:
            RuleApplicability immuable.
        """
        scope_id: int | None = getattr(site, "id", None)
        scope_label: str = f"Site {getattr(site, 'nom', f'#{scope_id}')}"

        batiments_list = list(batiments)
        audit = self._build_audit(data_source="models.Batiment.cvc_power_kw")

        # ── Gate NOT_APPLICABLE.NO_BUILDINGS ─────────────────────────────
        if not batiments_list:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason_code="BACS.NOT_APPLICABLE.NO_BUILDINGS",
                reason_human=(f"{scope_label} : aucun bâtiment référencé. BACS non applicable."),
                inputs_used={"batiments_count": 0, "threshold_kw": BACS_THRESHOLD_KW_EXISTING},
                confidence=1.0,
                evidence_refs=["Décret 2020-887 art. R175-3"],
                _audit=audit,
            )

        # ── Gate DATA_MISSING ────────────────────────────────────────────
        powers = [getattr(b, "cvc_power_kw", None) for b in batiments_list]
        missing_buildings = [b for b, p in zip(batiments_list, powers) if p is None]
        if missing_buildings:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.DATA_MISSING,
                reason_code="BACS.DATA_MISSING.CVC_POWER",
                reason_human=(
                    f"{scope_label} : puissance CVC manquante pour "
                    f"{len(missing_buildings)} bâtiment(s) sur {len(batiments_list)}. "
                    f"Statut BACS non statuable."
                ),
                inputs_used={
                    "batiments_count": len(batiments_list),
                    "missing_count": len(missing_buildings),
                    "threshold_kw": BACS_THRESHOLD_KW_EXISTING,
                },
                missing_inputs=[f"batiment.cvc_power_kw[{getattr(b, 'id', '?')}]" for b in missing_buildings],
                confidence=0.0,
                evidence_refs=["Décret 2020-887 art. R175-3"],
                _audit=audit,
            )

        # Tous les bâtiments ont cvc_power_kw → on peut statuer
        powers_clean: list[float] = [float(p) for p in powers if p is not None]
        max_power: float = max(powers_clean) if powers_clean else 0.0

        # ── APPLICABLE Tier 1 (initial 290 kW) — deadline 01/01/2025 ──
        # Fix audit regulatory-expert 13/05/2026 : distinction Tier 1 vs Tier 2.
        # Sites > 290 kW étaient assujettis dès 2020-887 art. R175-3 avec
        # deadline 01/01/2025 (expirée). On l'expose pour faire remonter
        # le risque infraction au CFO.
        if max_power > BACS_THRESHOLD_KW_INITIAL:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.APPLICABLE,
                reason_code="BACS.APPLICABLE.TIER1_EXPIRED",
                reason_human=(
                    f"{scope_label} : puissance CVC max {max_power:.0f} kW > "
                    f"{BACS_THRESHOLD_KW_INITIAL} kW (Tier 1). BACS exigé "
                    f"deadline {BACS_DEADLINE_INITIAL} (expirée — risque sanction)."
                ),
                inputs_used={
                    "batiments_count": len(batiments_list),
                    "cvc_power_max_kw": max_power,
                    "threshold_kw": BACS_THRESHOLD_KW_INITIAL,
                    "tier": "initial",
                },
                confidence=1.0,
                evidence_refs=[
                    "Décret 2020-887 art. R175-3",
                ],
                deadline=_parse_iso_date(BACS_DEADLINE_INITIAL),
                _audit=audit,
            )

        # ── APPLICABLE Tier 2 (existing 70 kW) — deadline 01/01/2030 ──
        if max_power > BACS_THRESHOLD_KW_EXISTING:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.APPLICABLE,
                reason_code="BACS.APPLICABLE.TIER2_UPCOMING",
                reason_human=(
                    f"{scope_label} : puissance CVC max {max_power:.0f} kW > "
                    f"{BACS_THRESHOLD_KW_EXISTING} kW (Tier 2). Système de régulation BACS exigé."
                ),
                inputs_used={
                    "batiments_count": len(batiments_list),
                    "cvc_power_max_kw": max_power,
                    "threshold_kw": BACS_THRESHOLD_KW_EXISTING,
                    "tier": "existing",
                },
                confidence=1.0,
                evidence_refs=[
                    "Décret 2020-887 art. R175-3",
                    "Décret 2025-1343 art. 1",
                ],
                deadline=_parse_iso_date(BACS_DEADLINE_EXISTING),
                _audit=audit,
            )

        # ── NOT_APPLICABLE — aucun bâtiment au-dessus du seuil ──────────
        return RuleApplicability(
            rule_code=self.code,
            rule_version=self.version,
            scope_level=self.scope,
            scope_id=scope_id,
            scope_label=scope_label,
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason_code="BACS.NOT_APPLICABLE.NO_SYSTEM_GT_THRESHOLD",
            reason_human=(
                f"{scope_label} : puissance CVC max {max_power:.0f} kW ≤ "
                f"{BACS_THRESHOLD_KW_EXISTING} kW. BACS non applicable."
            ),
            inputs_used={
                "batiments_count": len(batiments_list),
                "cvc_power_max_kw": max_power,
                "threshold_kw": BACS_THRESHOLD_KW_EXISTING,
            },
            confidence=1.0,
            evidence_refs=["Décret 2020-887 art. R175-3"],
            _audit=audit,
        )
