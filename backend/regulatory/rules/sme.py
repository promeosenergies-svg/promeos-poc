"""PROMEOS — Évaluateur Audit énergétique SMÉ v1.0.

Référence normative : Code de l'énergie L233-1 (transposition Directive Efficacité
Énergétique 2012/27/UE) + Loi 2025-391 art. 4 (deadlines).

Règle cardinale v1.0 — Audit énergétique obligatoire si :
  (a) effectif total ≥ 250 salariés                          OU
  (b) chiffre d'affaires ≥ 50 M€ ET bilan ≥ 43 M€            OU
  (c) consommation annuelle > 2.75 GWh (cf. SKILL.md `AUDIT`)

Cas DATA_MISSING : effectif, CA, bilan, **et** conso tous absents.

Évaluation à granularité **organisation** (scope_level = "organisation").

Note : la SoT de consommation pour le critère (c) est `AuditSME.conso_annuelle_moy_gwh`
si renseigné (sinon non statué sur ce critère). Le critère (b) bilan n'est pas
disponible aujourd'hui dans le modèle Organisation — donc on s'appuie sur (a) ou
(c) en v1.0. Le critère (b) sera ré-évaluable lorsque le champ `bilan_eur` sera
ajouté à `Organisation` (cf. TODO ADR-024 v2.0).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from doctrine.constants import (
    AUDIT_SME_THRESHOLD_GWH_PERIODIC,
    SME_BILAN_THRESHOLD_EUR,
    SME_CA_THRESHOLD_EUR,
    SME_EFFECTIF_THRESHOLD,
)
from regulatory.applicability_types import (
    ApplicabilityStatus,
    RuleApplicability,
    RuleCode,
)
from regulatory.rules.base import RuleEvaluator


# Phase 3.7 P1 — Seuils importes depuis doctrine.constants (SoT unique).
# Garde l'alias local pour compatibilite tests existants.
SME_CONSO_THRESHOLD_GWH: float = AUDIT_SME_THRESHOLD_GWH_PERIODIC  # 2.75 GWh canonical

# Deadline cardinale Loi 2025-391 art. 4 : avant 11/10/2026
SME_DEADLINE: date = date(2026, 10, 11)


class SMEEvaluator(RuleEvaluator):
    """Évaluateur Audit énergétique L233-1 (SMÉ)."""

    code = RuleCode.SME
    version = "SME-L233-1+loi-2025-391-v2025-12-31"
    scope = "organisation"

    def evaluate(self, organisation: Any, audit_sme: Any = None) -> RuleApplicability:
        """Évalue l'assujettissement audit énergétique d'une organisation.

        Args:
            organisation: instance `models.Organisation` avec `id`, `nom`,
                          `effectif_total`, `chiffre_affaires_eur`.
            audit_sme: instance optionnelle `models.AuditSME` (pour le critère
                       consommation `conso_annuelle_moy_gwh`).

        Returns:
            RuleApplicability immuable.
        """
        scope_id: int | None = getattr(organisation, "id", None)
        scope_label: str = f"Organisation {getattr(organisation, 'nom', f'#{scope_id}')}"
        effectif: int | None = getattr(organisation, "effectif_total", None)
        ca: float | None = getattr(organisation, "chiffre_affaires_eur", None)
        # Bilan : champ absent du modèle v1.0 — traité comme None systématique
        bilan: float | None = getattr(organisation, "bilan_eur", None)
        conso_gwh: float | None = getattr(audit_sme, "conso_annuelle_moy_gwh", None) if audit_sme is not None else None

        inputs: dict[str, Any] = {
            "effectif_total": effectif,
            "chiffre_affaires_eur": ca,
            "bilan_eur": bilan,
            "conso_annuelle_moy_gwh": conso_gwh,
            "thresholds": {
                "effectif": SME_EFFECTIF_THRESHOLD,
                "ca_eur": SME_CA_THRESHOLD_EUR,
                "bilan_eur": SME_BILAN_THRESHOLD_EUR,
                "conso_gwh": SME_CONSO_THRESHOLD_GWH,
            },
        }
        audit = self._build_audit(
            data_source="models.Organisation.{effectif_total,chiffre_affaires_eur}+AuditSME.conso_annuelle_moy_gwh"
        )

        # ── Gate APPLICABLE.EFFECTIF (critère prioritaire) ─────────────
        if effectif is not None and effectif >= SME_EFFECTIF_THRESHOLD:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.APPLICABLE,
                reason_code="SME.APPLICABLE.EFFECTIF",
                reason_human=(
                    f"{scope_label} : effectif {effectif} ≥ {SME_EFFECTIF_THRESHOLD}. "
                    f"Audit énergétique obligatoire avant le {SME_DEADLINE.strftime('%d/%m/%Y')}."
                ),
                inputs_used=inputs,
                confidence=1.0,
                evidence_refs=[
                    "Code énergie L233-1",
                    "Loi 2025-391 art. 4",
                ],
                deadline=SME_DEADLINE,
                _audit=audit,
            )

        # ── Gate APPLICABLE.CA_BILAN ───────────────────────────────────
        if ca is not None and ca >= SME_CA_THRESHOLD_EUR and bilan is not None and bilan >= SME_BILAN_THRESHOLD_EUR:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.APPLICABLE,
                reason_code="SME.APPLICABLE.CA_BILAN",
                reason_human=(
                    f"{scope_label} : CA {ca / 1e6:.1f} M€ ≥ 50 M€ ET bilan {bilan / 1e6:.1f} M€ "
                    f"≥ 43 M€. Audit énergétique obligatoire."
                ),
                inputs_used=inputs,
                confidence=1.0,
                evidence_refs=["Code énergie L233-1"],
                deadline=SME_DEADLINE,
                _audit=audit,
            )

        # ── Gate APPLICABLE.CONSO_GT_THRESHOLD ─────────────────────────
        if conso_gwh is not None and conso_gwh > SME_CONSO_THRESHOLD_GWH:
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.APPLICABLE,
                reason_code="SME.APPLICABLE.CONSO_GT_THRESHOLD",
                reason_human=(
                    f"{scope_label} : consommation annuelle {conso_gwh:.2f} GWh > "
                    f"{SME_CONSO_THRESHOLD_GWH} GWh. Audit énergétique obligatoire."
                ),
                inputs_used=inputs,
                confidence=1.0,
                evidence_refs=["Code énergie L233-1", "SKILL.md AUDIT"],
                deadline=SME_DEADLINE,
                _audit=audit,
            )

        # ── Gate DATA_MISSING : choisir le code le plus représentatif ───
        # Phase 3.7 KK : bijection reason_codes — émet le code le plus précis
        # selon le champ manquant prioritaire (effectif > CA > conso).
        if effectif is None and ca is None and conso_gwh is None:
            missing = [
                "organisation.effectif_total",
                "organisation.chiffre_affaires_eur",
                "AuditSME.conso_annuelle_moy_gwh",
            ]
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.DATA_MISSING,
                reason_code="SME.DATA_MISSING.EFFECTIF",
                reason_human=(f"{scope_label} : effectif, CA et consommation tous absents. Audit SMÉ non statuable."),
                inputs_used=inputs,
                missing_inputs=missing,
                confidence=0.0,
                evidence_refs=["Code énergie L233-1"],
                _audit=audit,
            )
        if ca is None and effectif is not None and effectif < SME_EFFECTIF_THRESHOLD:
            # Bijection KK : émet SME.DATA_MISSING.CA si effectif présent + sous seuil + CA absent
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.DATA_MISSING,
                reason_code="SME.DATA_MISSING.CA",
                reason_human=(
                    f"{scope_label} : effectif {effectif} < seuil mais CA non renseigné. Critère SMÉ (b) non statuable."
                ),
                inputs_used=inputs,
                missing_inputs=["organisation.chiffre_affaires_eur"],
                confidence=0.0,
                evidence_refs=["Code énergie L233-1"],
                _audit=audit,
            )
        if (
            conso_gwh is None
            and effectif is not None
            and effectif < SME_EFFECTIF_THRESHOLD
            and ca is not None
            and ca < SME_CA_THRESHOLD_EUR
        ):
            # Bijection KK : émet SME.DATA_MISSING.CONSO si autres critères statués + conso absente
            return RuleApplicability(
                rule_code=self.code,
                rule_version=self.version,
                scope_level=self.scope,
                scope_id=scope_id,
                scope_label=scope_label,
                status=ApplicabilityStatus.DATA_MISSING,
                reason_code="SME.DATA_MISSING.CONSO",
                reason_human=(
                    f"{scope_label} : effectif et CA sous seuils, conso non renseignée. Critère SMÉ (c) non statuable."
                ),
                inputs_used=inputs,
                missing_inputs=["AuditSME.conso_annuelle_moy_gwh"],
                confidence=0.0,
                evidence_refs=["Code énergie L233-1", "SKILL.md AUDIT"],
                _audit=audit,
            )

        # ── NOT_APPLICABLE.PME ─────────────────────────────────────────
        return RuleApplicability(
            rule_code=self.code,
            rule_version=self.version,
            scope_level=self.scope,
            scope_id=scope_id,
            scope_label=scope_label,
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason_code="SME.NOT_APPLICABLE.PME",
            reason_human=(
                f"{scope_label} : aucun critère SMÉ rempli (effectif={effectif}, "
                f"CA={ca}, conso_gwh={conso_gwh}). Statut PME / hors périmètre."
            ),
            inputs_used=inputs,
            confidence=1.0,
            evidence_refs=["Code énergie L233-1"],
            _audit=audit,
        )
