"""PROMEOS — Catalogue des évaluateurs cataloguées v1.0.

Référence : `docs/adr/ADR-024-moteur-assujettissement.md` §5.

Dispatcher unique consommé par `regulatory.applicability_service.compute_applicability`.
Chaque RuleCode est associé à son évaluateur.

Politique de versioning :
    L'ajout / modification d'un évaluateur passe par ADR. Les versions sont
    figées en attribut `version` de chaque classe et exposées dans le payload
    via `RuleApplicability.rule_version` + footer `version_tags`.
"""

from __future__ import annotations

from regulatory.applicability_types import RuleCode
from regulatory.rules.aper import APEREvaluator
from regulatory.rules.bacs import BACSEvaluator
from regulatory.rules.beges import BEGESEvaluator
from regulatory.rules.dt import DTEvaluator
from regulatory.rules.sme import SMEEvaluator


RULE_EVALUATORS: dict[RuleCode, object] = {
    RuleCode.DT: DTEvaluator(),
    RuleCode.BACS: BACSEvaluator(),
    RuleCode.APER: APEREvaluator(),
    RuleCode.SME: SMEEvaluator(),
    RuleCode.BEGES: BEGESEvaluator(),
}


RULES_VERSIONS: dict[RuleCode, str] = {
    RuleCode.DT: DTEvaluator.version,
    RuleCode.BACS: BACSEvaluator.version,
    RuleCode.APER: APEREvaluator.version,
    RuleCode.SME: SMEEvaluator.version,
    RuleCode.BEGES: BEGESEvaluator.version,
}
