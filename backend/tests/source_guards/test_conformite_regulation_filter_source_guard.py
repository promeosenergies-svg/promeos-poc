"""
PROMEOS — Source-guard ConformitePage regulationFilter (Sprint Site360 P1).

Doctrine : interdit la régression du bug Site360 P1 (2026-05-31) où
les 4 chips réglementaires (Décret Tertiaire / BACS / APER / SMÉ-BEGES)
changeaient l'URL mais ne filtraient pas la synthèse, le bandeau urgence,
le parcours guidé et la NBA.

Tout consumer de `obligations` / `actionableFindings` / `score` /
`timeline` qui rend la synthèse haute ou la prochaine action métier
doit consommer la version `*Filtered` quand `regulationFilter` est actif.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast


REPO_ROOT = Path(__file__).resolve().parents[3]
CONFORMITE_PAGE = REPO_ROOT / "frontend" / "src" / "pages" / "ConformitePage.jsx"


class TestConformiteRegulationFilter:
    """Sprint Site360 P1 — propagation regulationFilter."""

    def test_page_file_exists(self):
        assert CONFORMITE_PAGE.exists()

    def test_filtered_obligations_memo_declared(self):
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        assert "filteredObligationsByRegulation" in src
        # La useMemo doit consulter REGULATION_FILTER_MAP[regulationFilter]
        assert re.search(
            r"filteredObligationsByRegulation\s*=\s*useMemo\([\s\S]*?REGULATION_FILTER_MAP\[regulationFilter\]",
            src,
        ), "filteredObligationsByRegulation doit dériver de REGULATION_FILTER_MAP[regulationFilter]"

    def test_filtered_actionable_findings_memo_declared(self):
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        assert "filteredActionableFindings" in src

    def test_score_filtered_recompute_formula(self):
        """Le score filtré doit recompter conformes/total sur le subset."""
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        assert "scoreFiltered" in src
        assert re.search(r"conformes\s*/\s*subset\.length", src), (
            "scoreFiltered doit recalculer pct = conformes / subset.length × 100 "
            "(formule d'affichage transparente, pas de calcul métier neuf)."
        )

    def test_timeline_filtered_memo_declared(self):
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        assert "timelineFiltered" in src

    def test_proofs_missing_filtered_memo_declared(self):
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        assert "proofsMissingCountFiltered" in src

    def test_synthese_compacte_consumes_filtered_versions(self):
        """ConformiteSyntheseCompacte DOIT consommer scoreFiltered."""
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        # Pattern : la balise <ConformiteSyntheseCompacte ... score={scoreFiltered} ...>
        assert re.search(
            r"<ConformiteSyntheseCompacte[\s\S]*?score=\{scoreFiltered\}[\s\S]*?proofsMissingCount=\{proofsMissingCountFiltered\}",
            src,
        ), "<ConformiteSyntheseCompacte> doit recevoir scoreFiltered + proofsMissingCountFiltered (Sprint Site360 P1)."

    def test_summary_banner_consumes_filtered_versions(self):
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        assert re.search(
            r"<ComplianceSummaryBanner[\s\S]*?score=\{scoreFiltered\}[\s\S]*?timeline=\{timelineFiltered\}",
            src,
        ), "<ComplianceSummaryBanner> doit recevoir scoreFiltered + timelineFiltered (Sprint Site360 P1)."

    def test_guided_steps_uses_filtered_obligations(self):
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        assert re.search(
            r"computeGuidedSteps\([\s\S]*?obligations:\s*filteredObligationsByRegulation",
            src,
        ), "computeGuidedSteps doit recevoir filteredObligationsByRegulation."

    def test_next_best_action_uses_filtered_obligations(self):
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        assert re.search(
            r"computeNextBestAction\([\s\S]*?obligations:\s*filteredObligationsByRegulation",
            src,
        ), "computeNextBestAction doit recevoir filteredObligationsByRegulation."

    def test_filter_banner_visible_with_clear_action(self):
        """Quand un chip est actif, l'utilisateur doit voir un bandeau
        « Vue filtrée » avec un lien pour effacer le filtre.
        """
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        assert 'data-testid="regulation-filter-banner"' in src
        assert "Vue filtrée" in src
        assert 'data-testid="regulation-filter-clear"' in src
        assert "voir toutes les obligations" in src

    def test_no_legacy_score_passed_to_synthese(self):
        """Anti-régression : ConformiteSyntheseCompacte ne doit PAS
        recevoir le score global brut (`score={score}`) en même temps
        que `nextDeadline={timeline?.next_deadline}`.
        """
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        assert not re.search(
            r"<ConformiteSyntheseCompacte[\s\S]*?score=\{score\}[\s\S]*?nextDeadline=\{timeline\?\.next_deadline",
            src,
        ), "Site360 P1 régression : <ConformiteSyntheseCompacte> reçoit encore le score brut au lieu de scoreFiltered."

    def test_no_legacy_banner_props(self):
        src = CONFORMITE_PAGE.read_text(encoding="utf-8")
        assert not re.search(
            r"<ComplianceSummaryBanner[\s\S]*?score=\{score\}[\s\S]*?timeline=\{timeline\}",
            src,
        ), (
            "Site360 P1 régression : <ComplianceSummaryBanner> reçoit "
            "encore score+timeline bruts au lieu des versions filtrées."
        )
