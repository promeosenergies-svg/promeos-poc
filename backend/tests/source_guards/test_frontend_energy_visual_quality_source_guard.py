"""
PROMEOS — Source-guard : qualité visuelle frontend Énergie (Sprint P2.5).

Garde-fou statique Python complémentaire à
`test_frontend_energy_provenance_visible_source_guard.py` (P2.4).

Scanne les vues Énergie et interdit :
- identifiants techniques type « Site #${id} »
- doublons « Site Site »
- jargon anglais générique (« No data », « See more », « Click here »,
  « Retry », « Loading… » en JSX rendu)
- sentinelles techniques en JSX rendu (« undefined », « NaN », « [object
  Object] »)
- TODO/FIXME visibles en JSX rendu (les commentaires sont OK)
- codes ENERGY_* hardcodés en literal hors fallback ApiErrorState
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast


REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND = REPO_ROOT / "frontend" / "src"


# Vues énergie auditées (mêmes que test_frontend_energy_provenance_visible)
ENERGY_FILES_REL = [
    "pages/MonitoringPage.jsx",
    "pages/monitoring/MonitoringClimateScatter.jsx",
    "pages/monitoring/monitoringConfidenceHelper.js",
    "pages/consumption/LoadCurveTab.jsx",
    "pages/consumption/CostContractTab.jsx",
    "pages/consumption/MarketExposureTab.jsx",
    "pages/usages/WeekProfileTab.jsx",
    "ui/energy/EnergyFilterBar.jsx",
    "ui/energy/MonitoringSynthesisStrip.jsx",
    "ui/energy/KpiCardWithProvenance.jsx",
    "ui/energy/LoadCurveChart.jsx",
    "ui/energy/WeekProfileHeatmap.jsx",
    "ui/energy/CostVsContractCard.jsx",
    "ui/energy/PriceDecompositionTable.jsx",
    "ui/energy/ExposureScoreGauge.jsx",
    "ui/energy/TopExpensiveHoursTable.jsx",
    "ui/energy/FavorableHoursPanel.jsx",
    "ui/energy/BaseloadComparisonCard.jsx",
    "ui/energy/DisplacementSimulationCard.jsx",
    "ui/energy/EnergyCrossLinks.jsx",
    "ui/energy/SiteRequiredState.jsx",
    "ui/energy/TopPeaksTable.jsx",
    # Sprint P3.1 — Profil moyen par jour + Répartition par jour.
    "ui/energy/WeekdayOverlayChart.jsx",
    "ui/energy/WeekdayDecompositionBar.jsx",
    "ui/energy/scopeLabel.js",
]


def _code_without_comments(content: str) -> str:
    """Retire les lignes commentaires (// + *)."""
    out: list[str] = []
    for line in content.split("\n"):
        s = line.strip()
        if s.startswith("//") or s.startswith("*"):
            continue
        out.append(line)
    return "\n".join(out)


def _iter_energy_files() -> list[tuple[str, str]]:
    """Retourne (rel_path, code_without_comments) pour chaque vue Énergie."""
    files: list[tuple[str, str]] = []
    for rel in ENERGY_FILES_REL:
        path = FRONTEND / rel
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        files.append((rel, _code_without_comments(content)))
    return files


class TestEnergyVisualQualityP2_5:
    """Sprint P2.5 — qualité visuelle frontend Énergie.

    Patterns interdits dans le code JSX rendu (hors commentaires).
    """

    def test_no_technical_site_id_pattern(self):
        """Aucun fallback `Site #${id}` ni concat `#${scope.id}`."""
        violations: list[str] = []
        for rel, code in _iter_energy_files():
            for pattern in (
                r"`Site #\$\{[^}]+\}`",
                r"`Compteur #\$\{[^}]+\}`",
                r"`Organisation #\$\{[^}]+\}`",
                r"`Entité #\$\{[^}]+\}`",
                r"['\"`]#\$\{scope\?\.id\}['\"`]",
                r"['\"`]#\$\{site\.id\}['\"`]",
            ):
                m = re.search(pattern, code)
                if m:
                    violations.append(f"  {rel} → « {m.group(0)} »")
        if violations:
            pytest.fail(
                "\n🔴 P2.5 — Identifiant technique « Site #id » détecté en JSX rendu :\n\n"
                + "\n".join(violations)
                + "\n\nUtiliser `formatSiteLabel(...)` depuis `ui/energy/scopeLabel.js`.\n"
            )

    def test_no_english_generic_jargon_rendered(self):
        """Aucun jargon anglais générique en JSX rendu."""
        violations: list[str] = []
        forbidden = [
            (r">\s*No data\s*<", "No data"),
            (r">\s*See more\s*<", "See more"),
            (r">\s*Click here\s*<", "Click here"),
            (r">\s*Learn more\s*<", "Learn more"),
            (r">\s*Loading\.\.\.\s*<", "Loading..."),
            (r">\s*Retry\s*<", "Retry"),
            (r">\s*Error\s*<", "Error"),
        ]
        for rel, code in _iter_energy_files():
            for pattern, label in forbidden:
                if re.search(pattern, code):
                    violations.append(f"  {rel} → « {label} »")
        if violations:
            pytest.fail(
                "\n🔴 P2.5 — Jargon anglais générique détecté en JSX rendu :\n\n"
                + "\n".join(violations)
                + "\n\nUtiliser des libellés FR métier équivalents.\n"
            )

    def test_no_technical_sentinels_rendered(self):
        """Aucune sentinelle technique (undefined, NaN, [object Object]) en JSX rendu."""
        violations: list[str] = []
        forbidden = [
            (r">\s*undefined\s*<", "undefined"),
            (r">\s*NaN\s*<", "NaN"),
            (r">\s*\[object Object\]\s*<", "[object Object]"),
            (r">\s*lorem ipsum\b", "lorem ipsum"),
            (r">\s*TODO\s*<", "TODO"),
            (r">\s*FIXME\s*<", "FIXME"),
        ]
        for rel, code in _iter_energy_files():
            for pattern, label in forbidden:
                if re.search(pattern, code, re.IGNORECASE):
                    violations.append(f"  {rel} → « {label} »")
        if violations:
            pytest.fail(
                "\n🔴 P2.5 — Sentinelle technique détectée en JSX rendu :\n\n"
                + "\n".join(violations)
                + "\n\nRemplacer par un libellé FR métier ou un EmptyState.\n"
            )

    def test_no_console_log_in_energy_code(self):
        """Aucun appel `console.log` dans le code Énergie (production)."""
        violations: list[str] = []
        for rel, code in _iter_energy_files():
            if re.search(r"\bconsole\.log\s*\(", code):
                violations.append(f"  {rel}")
        if violations:
            pytest.fail(
                "\n🔴 P2.5 — `console.log` détecté dans code Énergie :\n\n"
                + "\n".join(violations)
                + "\n\nRetirer ou remplacer par tracker analytique si nécessaire.\n"
            )

    def test_energy_codes_only_as_api_error_fallback(self):
        """Les literals ENERGY_* n'apparaissent que comme fallback detail.code."""
        violations: list[str] = []
        for rel, code in _iter_energy_files():
            # Compte les literals ENERGY_*
            literals = re.findall(r"['\"](ENERGY_[A-Z_]+)['\"]", code)
            if not literals:
                continue
            # Compte les usages comme fallback `detail.code ||`
            fallback_pattern = re.compile(r"detail\.code\s*\|\|\s*['\"]ENERGY_[A-Z_]+['\"]")
            fallbacks = fallback_pattern.findall(code)
            if len(literals) != len(fallbacks):
                violations.append(
                    f"  {rel} → {len(literals)} literal(s) ENERGY_* mais {len(fallbacks)} en fallback detail.code"
                )
        if violations:
            pytest.fail(
                "\n🔴 P2.5 — Code ENERGY_* literal en JSX rendu non-fallback :\n\n"
                + "\n".join(violations)
                + "\n\nLes codes ENERGY_* ne doivent apparaître qu'en fallback de "
                "`detail.code` dans les composants ApiErrorState.\n"
            )

    def test_scope_label_helper_exists_and_documented(self):
        """Le helper canonique `scopeLabel.js` existe et documente la doctrine."""
        path = FRONTEND / "ui" / "energy" / "scopeLabel.js"
        assert path.exists(), (
            "frontend/src/ui/energy/scopeLabel.js manquant — helper canonique "
            "P2.5 nécessaire pour éviter les fallbacks techniques."
        )
        content = path.read_text(encoding="utf-8")
        assert "formatSiteLabel" in content
        assert "INTERDIT" in content
        assert "FALLBACK_SITE_SELECTED" in content
        assert "FALLBACK_NO_SITE" in content

    def test_loadcurve_and_filterbar_use_canonical_helper(self):
        """LoadCurveTab et EnergyFilterBar importent et utilisent formatSiteLabel."""
        for rel in (
            "pages/consumption/LoadCurveTab.jsx",
            "ui/energy/EnergyFilterBar.jsx",
        ):
            content = (FRONTEND / rel).read_text(encoding="utf-8")
            assert "formatSiteLabel" in content, f"{rel} doit importer/utiliser `formatSiteLabel` (P2.5)."

    def test_simulation_warning_phrase_preserved(self):
        """La phrase « Simulation indicative — … » reste hardcodée fallback."""
        for rel in (
            "ui/energy/CostVsContractCard.jsx",
            "ui/energy/DisplacementSimulationCard.jsx",
        ):
            content = (FRONTEND / rel).read_text(encoding="utf-8")
            assert "Simulation indicative" in content, (
                f"{rel} doit conserver la phrase « Simulation indicative » (doctrine P1.S5/S6)."
            )
            assert "promesse d'économie" in content, f"{rel} doit conserver la mention « promesse d'économie »."

    def test_no_old_top_pics_microcopy_p3_1(self):
        """Sprint P3.1 — l'ancien wording « Top pics » (placeholder P1.S3a) est interdit.

        Microcopy canonique : « Pics de puissance » (cf.
        `TopPeaksTable.jsx` + brief P3.1).
        """
        violations: list[str] = []
        forbidden_patterns = [
            r"['\"`>]\s*Top pics indisponible",
            r"['\"`>]\s*Top pics\s*['\"`<]",
        ]
        for rel, code in _iter_energy_files():
            for pattern in forbidden_patterns:
                if re.search(pattern, code):
                    violations.append(f"  {rel} → ancien libellé « Top pics » détecté ({pattern})")
        if violations:
            pytest.fail(
                "\n🔴 P3.1 — Microcopy « Top pics » obsolète détectée :\n\n"
                + "\n".join(violations)
                + "\n\nUtiliser « Pics de puissance » (cf. brief Énergie P3.1).\n"
            )

    def test_weekday_components_render_provenance_p3_1(self):
        """Sprint P3.1 — WeekdayOverlayChart + WeekdayDecompositionBar exposent provenance."""
        for rel in (
            "ui/energy/WeekdayOverlayChart.jsx",
            "ui/energy/WeekdayDecompositionBar.jsx",
        ):
            path = FRONTEND / rel
            assert path.exists(), f"Composant P3.1 manquant : {rel}"
            content = path.read_text(encoding="utf-8")
            assert "provenance" in content, (
                f"{rel} doit lire `provenance` du payload backend (P3.1 doctrine zéro calcul)."
            )
            # Au moins un data-testid provenance visible.
            assert re.search(r'data-testid="weekday-(overlay|decomposition)-provenance"', content), (
                f"{rel} doit exposer un data-testid de provenance visible (P3.1)."
            )

    def test_french_microcopy_emptystates(self):
        """Les empty states sont en FR (pas de fallback anglais)."""
        # Énumérer les vues qui ont des EmptyState
        TABS = [
            "pages/consumption/LoadCurveTab.jsx",
            "pages/consumption/CostContractTab.jsx",
            "pages/consumption/MarketExposureTab.jsx",
            "pages/usages/WeekProfileTab.jsx",
        ]
        for rel in TABS:
            content = (FRONTEND / rel).read_text(encoding="utf-8")
            # Vérifie qu'aucun EmptyState ne porte un titre anglais
            # (les vrais EmptyStates sont en FR — cf. doctrine S3a→S6)
            assert "No data available" not in content, f"{rel} → titre EmptyState anglais détecté"
