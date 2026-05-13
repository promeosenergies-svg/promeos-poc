"""PROMEOS — Évaluateur Décret Tertiaire (DT) v1.0.

Référence normative : Décret n° 2019-771 du 23/07/2019 (NOR : TRELxxx) +
arrêtés OPERAT (Arrêté 10/04/2020 art. 2).

Règle cardinale :
    Un site est assujetti au DT si :
      - `site.tertiaire_area_m2` ≥ 1 000 m²  ET
      - `site.usage_principal`   ∈ usages tertiaires reconnus (OperatUsagePrincipalEnum)

Cas UNKNOWN : `usage_principal == MIXTE` → qualification fine requise.
Cas DATA_MISSING : `tertiaire_area_m2` ou `usage_principal` non renseigné.

Trajectoire applicable (cf. SKILL.md jalons DT) :
    2030 : -40 %   |   2040 : -50 %   |   2050 : -60 %

Date de référence : entre 2010 et 2022 (champ `annee_reference_operat`).
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


# Seuil cardinal — fixé par Décret 2019-771 art. R175-1 (Code construction)
DT_SDP_THRESHOLD_M2: float = 1000.0

# Usage MIXTE → UNKNOWN (qualification fine requise v1.0)
_TERTIARY_USAGES: frozenset[str] = frozenset(
    {
        "BUREAUX",
        "COMMERCES",
        "ENSEIGNEMENT",
        "HOTELLERIE",
        "RESTAURATION",
        "SANTE",
        "SPORT_LOISIRS",
        "LOGISTIQUE",
    }
)


class DTEvaluator(RuleEvaluator):
    """Évaluateur Décret Tertiaire."""

    code = RuleCode.DT
    version = "DT-2019-771-v2024-10-01"
    scope = "site"

    def evaluate(self, site: Any) -> RuleApplicability:
        """Évalue l'assujettissement DT d'un site.

        Args:
            site: instance `models.Site` avec attributs `id`, `nom`,
                  `tertiaire_area_m2`, `usage_principal`.

        Returns:
            RuleApplicability immuable.
        """
        scope_id: int | None = getattr(site, "id", None)
        scope_label: str = f"Site {getattr(site, 'nom', f'#{scope_id}')}"
        tertiaire_area: float | None = getattr(site, "tertiaire_area_m2", None)
        usage_attr = getattr(site, "usage_principal", None)
        usage: str | None = self._normalize_usage(usage_attr)

        inputs: dict[str, Any] = {
            "tertiaire_area_m2": tertiaire_area,
            "usage_principal": usage,
        }
        audit = self._build_audit(data_source="models.Site.{tertiaire_area_m2,usage_principal}")

        # ── Gate DATA_MISSING ────────────────────────────────────────────
        missing: list[str] = []
        if tertiaire_area is None:
            missing.append("site.tertiaire_area_m2")
        if usage is None:
            missing.append("site.usage_principal")
        if missing:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.DATA_MISSING,
                reason_code="DT.DATA_MISSING.SURFACE"
                if "site.tertiaire_area_m2" in missing
                else "DT.DATA_MISSING.USAGE",
                reason_human=(
                    f"{scope_label} : champ(s) requis manquant(s) {', '.join(missing)}. Décret tertiaire non statuable."
                ),
                inputs_used=inputs,
                missing_inputs=missing,
                confidence=0.0,
                evidence_refs=["Décret 2019-771 art. R175-1"],
                _audit=audit,
            )

        # ── Gate UNKNOWN (usage mixte) ──────────────────────────────────
        if usage == "MIXTE":
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.UNKNOWN,
                reason_code="DT.UNKNOWN.USAGE_MIXTE",
                reason_human=(
                    f"{scope_label} : usage déclaré « MIXTE ». Qualification fine "
                    f"de la part tertiaire requise pour statuer."
                ),
                inputs_used=inputs,
                confidence=0.5,
                evidence_refs=["Arrêté 10/04/2020 art. 2"],
                _audit=audit,
            )

        # ── Gate NOT_APPLICABLE.SDP_LT_1000 ─────────────────────────────
        if tertiaire_area < DT_SDP_THRESHOLD_M2:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason_code="DT.NOT_APPLICABLE.SDP_LT_1000",
                reason_human=(
                    f"{scope_label} : surface tertiaire {tertiaire_area:.0f} m² "
                    f"< {DT_SDP_THRESHOLD_M2:.0f} m². Décret tertiaire non applicable."
                ),
                inputs_used=inputs,
                confidence=1.0,
                evidence_refs=["Décret 2019-771 art. R175-1"],
                _audit=audit,
            )

        # ── Gate NOT_APPLICABLE.USAGE_NON_TERTIARY ──────────────────────
        if usage not in _TERTIARY_USAGES:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason_code="DT.NOT_APPLICABLE.USAGE_NON_TERTIARY",
                reason_human=(
                    f"{scope_label} : usage « {usage} » hors périmètre tertiaire OPERAT. "
                    f"Décret tertiaire non applicable."
                ),
                inputs_used=inputs,
                confidence=1.0,
                evidence_refs=["Arrêté 10/04/2020 art. 2"],
                _audit=audit,
            )

        # ── APPLICABLE — trajectoire active ─────────────────────────────
        return RuleApplicability(
            rule_code=self.code,
            rule_version=self.version,
            scope_level=self.scope,
            scope_id=scope_id,
            scope_label=scope_label,
            status=ApplicabilityStatus.APPLICABLE,
            reason_code="DT.APPLICABLE",
            reason_human=(
                f"{scope_label} : surface tertiaire {tertiaire_area:.0f} m² ≥ "
                f"{DT_SDP_THRESHOLD_M2:.0f} m², usage « {usage} ». "
                f"Trajectoire -40 %/2030, -50 %/2040, -60 %/2050."
            ),
            inputs_used=inputs,
            confidence=1.0,
            evidence_refs=[
                "Décret 2019-771 art. R175-1",
                "Arrêté 10/04/2020 art. 2",
            ],
            deadline=date(2030, 12, 31),
            _audit=audit,
        )

    @staticmethod
    def _normalize_usage(usage_attr: Any) -> str | None:
        """Normalise l'attribut usage en chaîne canonique (uppercase) ou None.

        Tolère :
            - Enum (OperatUsagePrincipalEnum) → .value
            - str (déjà normalisé)
            - None
        """
        if usage_attr is None:
            return None
        if hasattr(usage_attr, "value"):
            return str(usage_attr.value).upper()
        return str(usage_attr).upper()
