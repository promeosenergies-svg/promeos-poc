"""PROMEOS — Évaluateur BEGES (Bilan GES réglementaire) v1.0.

Référence normative : Loi Grenelle 2 art. 75 (Code envir. R229-46 à R229-50).

Règle cardinale v1.0 :
  Une organisation est assujettie BEGES si :
    (a) effectif ≥ 500 salariés (siège métropole)               OU
    (b) effectif ≥ 250 salariés (siège DOM-TOM)

Cas DATA_MISSING : `effectif_total` absent.

Évaluation à granularité **organisation** (scope_level = "organisation").

Note : la détection siège DOM se fait via `Organisation.pays` ou un champ
dédié `siege_dom` (bool). En v1.0 du modèle PROMEOS, seul `pays` existe.
Métropole = pays == "FR" (par défaut) ; DOM = code FR-DOM (TODO v2.0).
Pour v1.0, on applique le seuil métropole (500) systématiquement, et on
laisse une note dans `inputs_used` pour clarifier la décision.
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


BEGES_EFFECTIF_THRESHOLD_METROPOLE: int = 500
BEGES_EFFECTIF_THRESHOLD_DOM: int = 250

# Périodicité réglementaire : 3 ans pour BEGES réglementaire post-2023
# (Décret 2022-982 art. 1 — réduit de 4 ans à 3 ans pour entreprises privées
# soumises à l'art. L229-25 du Code de l'environnement, effet 01/01/2023).
# Fix audit regulatory-expert 13/05/2026 (était 4, valeur obsolète).
BEGES_PERIODICITY_YEARS: int = 3


class BEGESEvaluator(RuleEvaluator):
    """Évaluateur Bilan GES réglementaire (Grenelle 2 art. 75)."""

    code = RuleCode.BEGES
    version = "BEGES-Grenelle2-art-75+Decret-2022-982-v2023-01-01"
    scope = "organisation"

    def evaluate(self, organisation: Any) -> RuleApplicability:
        """Évalue l'assujettissement BEGES d'une organisation.

        Args:
            organisation: instance `models.Organisation` avec `effectif_total`
                          et `pays` (optionnel).

        Returns:
            RuleApplicability immuable.
        """
        scope_id: int | None = getattr(organisation, "id", None)
        scope_label: str = f"Organisation {getattr(organisation, 'nom', f'#{scope_id}')}"
        effectif: int | None = getattr(organisation, "effectif_total", None)
        pays_attr = getattr(organisation, "pays", None)
        # Normalisation pays (Enum ou str)
        if pays_attr is None:
            pays: str = "FR"  # défaut métropole
        elif hasattr(pays_attr, "value"):
            pays = str(pays_attr.value).upper()
        else:
            pays = str(pays_attr).upper()

        # En v1.0, seul FR métropole est supporté. DOM = TODO v2.0.
        is_dom: bool = pays.startswith("FR-DOM") or pays in {"GP", "MQ", "RE", "GF", "YT"}
        threshold: int = BEGES_EFFECTIF_THRESHOLD_DOM if is_dom else BEGES_EFFECTIF_THRESHOLD_METROPOLE

        inputs: dict[str, Any] = {
            "effectif_total": effectif,
            "pays": pays,
            "is_dom": is_dom,
            "threshold": threshold,
        }
        audit = self._build_audit(data_source="models.Organisation.{effectif_total,pays}")

        # ── DATA_MISSING ─────────────────────────────────────────────────
        if effectif is None:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.DATA_MISSING,
                reason_code="BEGES.DATA_MISSING.EFFECTIF",
                reason_human=(f"{scope_label} : effectif non renseigné. Bilan GES non statuable."),
                inputs_used=inputs,
                missing_inputs=["organisation.effectif_total"],
                confidence=0.0,
                evidence_refs=["Loi Grenelle 2 art. 75"],
                _audit=audit,
            )

        # ── APPLICABLE ──────────────────────────────────────────────────
        if effectif >= threshold:
            reason_code = "BEGES.APPLICABLE.EFFECTIF_DOM" if is_dom else "BEGES.APPLICABLE.EFFECTIF_METROPOLE"
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.APPLICABLE,
                reason_code=reason_code,
                reason_human=(
                    f"{scope_label} : effectif {effectif} ≥ {threshold} "
                    f"({'DOM' if is_dom else 'métropole'}). Bilan GES réglementaire "
                    f"obligatoire (périodicité {BEGES_PERIODICITY_YEARS} ans)."
                ),
                inputs_used=inputs,
                confidence=1.0,
                evidence_refs=[
                    "Loi Grenelle 2 art. 75",
                    "Code envir. R229-46",
                ],
                _audit=audit,
            )

        # ── NOT_APPLICABLE ──────────────────────────────────────────────
        return RuleApplicability(
            rule_code=self.code,
            rule_version=self.version,
            scope_level=self.scope,
            scope_id=scope_id,
            scope_label=scope_label,
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason_code="BEGES.NOT_APPLICABLE.EFFECTIF_LT_250",
            reason_human=(
                f"{scope_label} : effectif {effectif} < {threshold}. Bilan GES réglementaire non applicable."
            ),
            inputs_used=inputs,
            confidence=1.0,
            evidence_refs=["Loi Grenelle 2 art. 75"],
            _audit=audit,
        )
