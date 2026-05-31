"""
PROMEOS — Source-guard : provenance visible obligatoire côté frontend Énergie.

Sprint Énergie P2.4 (2026-05-30).

Doctrine traçabilité étendue P1.S7 → P2.4 :
- P1.S7 a livré couverture provenance 100 % KPI (backend + frontend) via
  `EnergyProvenanceCoverage.test.jsx` (16 tests vitest) +
  `TestProvenanceCoveragePolishP1S7` (+17 tests pytest schémas Pydantic).
- P2.4 ajoute ce source-guard STATIQUE Python qui scanne tous les
  composants `frontend/src/ui/energy/*.jsx` et vérifie qu'un composant
  qui accepte une prop métier (kpi, kpis, scenario, scenarios, simulation,
  priceDecomposition, topExpensiveHours, favorableHours,
  baseloadComparison, matrix, points avec provenance backend) rend AU
  MOINS un marqueur provenance visible.

Marqueurs acceptés :
- `KpiCardWithProvenance` (composant canonique délégation)
- `data-testid="*-provenance*"` ou contenant le mot `provenance`
- `ScenarioProvenanceDot` / `SimulationProvenanceDot` (composants dédiés)
- `aria-label` contenant `provenance` ou `Provenance`
- usage explicite de `provenance.source` ou `provenance.formula`
- whitelist explicite documentée (non-KPI, navigation, EmptyState pure)

Tout composant qui :
- accepte une prop métier listée
- ET ne rend AUCUN marqueur
- ET n'est pas dans la whitelist

→ FAIT ÉCHOUER ce guard avec message d'erreur explicite.

Doctrine : retirer de la WHITELIST dès qu'un composant peut rendre
visible sa provenance (correction minimale : ajouter testid + texte
sobre dans un footer).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast


REPO_ROOT = Path(__file__).resolve().parents[3]
ENERGY_UI = REPO_ROOT / "frontend" / "src" / "ui" / "energy"


# Props qui DÉCLENCHENT l'obligation d'un marqueur provenance.
# Tous ces noms correspondent à des structures backend qui exposent
# `provenance` (cf. schémas Pydantic /api/energy/*).
METIER_PROPS = (
    "kpi",
    "kpis",
    "scenarios",
    "simulation",
    "priceDecomposition",
    "topExpensiveHours",
    "favorableHours",
    "baseloadComparison",
    "activeContract",
    "topPeaks",
)


# Marqueurs provenance reconnus (regex compilées).
PROVENANCE_MARKERS = [
    re.compile(r"KpiCardWithProvenance"),
    re.compile(r'data-testid=["\'][^"\']*provenance[^"\']*["\']', re.IGNORECASE),
    re.compile(r"ScenarioProvenanceDot"),
    re.compile(r"SimulationProvenanceDot"),
    re.compile(r"ProvenanceTooltip"),
    re.compile(r"ProvenanceDot"),
    re.compile(r"""aria-label=["'][^"']*[Pp]rovenance[^"']*["']"""),
    re.compile(r"provenance\.source"),
    re.compile(r"provenance\.formula"),
    re.compile(r"provenance\.service"),
]


# WHITELIST — composants explicitement non-métier OU pure
# layout/navigation. Chaque entrée DOIT documenter sa raison + cible
# de suppression si dette réelle.
NON_METIER_WHITELIST: dict[str, str] = {
    "EnergyCrossLinks.jsx": (
        "Composant de navigation pure (livré P1.S7, étendu P2.2). Accepte "
        "uniquement `links` (array de {kind, to, label}) — aucune donnée "
        "métier énergie. Pas de dette."
    ),
    "EnergyFilterBar.jsx": (
        "Composant filtre UI pur (livré P1.S3a). Accepte `scope`, "
        "`period`, `granularity`, `compare`, `display` — aucune donnée "
        "métier énergie (les filtres pilotent les requêtes API). "
        "Pas de dette."
    ),
    "SiteRequiredState.jsx": (
        "EmptyState métier (livré P1.S6 fix UX scope). Accepte `title`, "
        "`text`, `ctaLabel`, `onChooseSite` — aucune donnée KPI. "
        "Pas de dette."
    ),
    "LoadCurveChart.jsx": (
        "Composant chart Recharts pur (livré P1.S3a). Accepte `series` "
        "(données points temporels) ; la provenance racine du payload "
        "`/api/energy/loadcurve` est rendue par le parent `LoadCurveTab` "
        "via les 4 KPI `KpiCardWithProvenance`. Pas de dette frontend ; "
        "exposer provenance directement dans le chart = redondance UX."
    ),
    "TopPeaksTable.jsx": (
        "Placeholder EmptyState « Top pics indisponible dans cette version » "
        "(livré P1.S3a). L'API `/api/energy/loadcurve` n'expose pas encore "
        "`top_peaks` côté backend. Cible : extension API backend (P3.x) "
        "puis ajout marqueur provenance et retrait whitelist."
    ),
}


def _iter_energy_components() -> list[Path]:
    """Liste tous les composants Énergie à scanner."""
    if not ENERGY_UI.exists():
        return []
    return sorted(ENERGY_UI.glob("*.jsx"))


def _component_accepts_metier_prop(content: str) -> tuple[bool, list[str]]:
    """Détecte si le composant accepte au moins une prop métier."""
    detected: list[str] = []
    # Cherche les destructurations du type `export default function X({ kpi, ... })`
    # ou `function X({ provenance, ... })`.
    # Pattern simple : nom de prop dans une déstructuration `{ ... }`.
    for prop in METIER_PROPS:
        # Match `{...prop,` ou `{ prop,` ou `{ prop }` ou `{...prop=`
        pattern = re.compile(
            rf"\b{re.escape(prop)}\b\s*(?:[,=}}]|\s*=\s*\[)",
            re.MULTILINE,
        )
        if pattern.search(content):
            detected.append(prop)
    return bool(detected), detected


def _component_renders_provenance_marker(content: str) -> tuple[bool, list[str]]:
    """Détecte si le composant rend au moins un marqueur provenance."""
    matched: list[str] = []
    for pattern in PROVENANCE_MARKERS:
        if pattern.search(content):
            matched.append(pattern.pattern[:60])
    return bool(matched), matched


class TestFrontendEnergyProvenanceVisible:
    """Sprint Énergie P2.4 — provenance visible obligatoire frontend.

    Garde-fou statique : tout composant `frontend/src/ui/energy/*.jsx`
    qui accepte une prop métier doit rendre au moins un marqueur
    provenance, sauf entrée explicite WHITELIST.
    """

    def test_energy_ui_directory_exists(self):
        """Sanity check : le dossier composants Énergie existe."""
        assert ENERGY_UI.exists(), f"frontend/src/ui/energy/ introuvable : {ENERGY_UI}"

    def test_at_least_one_energy_component_present(self):
        """Sanity check : au moins 10 composants attendus."""
        files = _iter_energy_components()
        assert len(files) >= 10, (
            f"Moins de 10 composants Énergie trouvés ({len(files)}) — régression de l'arborescence ui/energy/ probable."
        )

    def test_all_metier_components_render_provenance_marker(self):
        """Tout composant métier rend ≥ 1 marqueur provenance ou est whitelisté."""
        violations: list[str] = []
        for path in _iter_energy_components():
            name = path.name
            content = path.read_text(encoding="utf-8")

            # Skip whitelist
            if name in NON_METIER_WHITELIST:
                continue

            # Accepte une prop métier ?
            accepts_metier, detected_props = _component_accepts_metier_prop(content)
            if not accepts_metier:
                # Pas de prop métier → ce composant pourrait être whitelistable
                # mais on tolère silencieusement (peut-être un wrapper).
                continue

            # Rend un marqueur provenance ?
            renders_marker, matched_markers = _component_renders_provenance_marker(content)
            if not renders_marker:
                violations.append(f"  {name} accepte {detected_props} mais ne rend AUCUN marqueur provenance visible.")

        if violations:
            msg = (
                "\n\n🔴 P2.4 — Composants Énergie sans provenance visible :\n\n"
                + "\n".join(violations)
                + "\n\nAction : ajouter un marqueur provenance — soit\n"
                "  - `KpiCardWithProvenance` ou autre composant délégation ;\n"
                '  - `data-testid="*-provenance"` + texte sobre rendu ;\n'
                "  - `ScenarioProvenanceDot` / `SimulationProvenanceDot` ;\n"
                "  - `aria-label` Provenance ;\n"
                "  - usage explicite `provenance.source` / `provenance.formula`.\n"
                "\nSi composant légitimement sans provenance (filtre, EmptyState, "
                "navigation pure) : ajouter à NON_METIER_WHITELIST avec justification.\n"
            )
            pytest.fail(msg)

    def test_whitelist_entries_exist_on_disk(self):
        """Toute entrée whitelist correspond à un fichier réel."""
        for name in NON_METIER_WHITELIST:
            path = ENERGY_UI / name
            assert path.exists(), (
                f"WHITELIST entry '{name}' référence un fichier inexistant : {path}. "
                "Retirer l'entrée si le composant a été supprimé."
            )

    def test_whitelist_entries_have_justification(self):
        """Toute entrée whitelist a une justification non vide."""
        for name, reason in NON_METIER_WHITELIST.items():
            assert reason and reason.strip(), f"WHITELIST entry '{name}' a une justification vide."
            assert len(reason) >= 50, (
                f"WHITELIST entry '{name}' justification trop courte "
                f"({len(reason)} chars) — documenter le pourquoi + cible "
                "de suppression."
            )

    def test_whitelisted_components_explicitly_dont_accept_kpi_provenance(self):
        """Les composants whitelistés ne doivent pas accepter `provenance` ou `kpi`
        en prop (cohérence avec la justification non-métier)."""
        ALLOW_PROP = {"LoadCurveChart.jsx", "TopPeaksTable.jsx"}
        for name in NON_METIER_WHITELIST:
            if name in ALLOW_PROP:
                # Ces composants reçoivent des données métier mais ont une
                # raison documentée (chart pur, placeholder).
                continue
            path = ENERGY_UI / name
            content = path.read_text(encoding="utf-8")
            # `provenance` ou `kpi/kpis` ne doivent pas apparaître en
            # déstructuration de props pour les composants non-métier purs.
            for prop in ("kpi", "kpis", "provenance"):
                pattern = re.compile(rf"\b{prop}\b\s*[,=}}]", re.MULTILINE)
                if pattern.search(content):
                    pytest.fail(
                        f"🔴 P2.4 — {name} est whitelisté comme non-métier "
                        f"mais accepte la prop `{prop}`. "
                        "Soit corriger la justification, soit retirer de la "
                        "whitelist + ajouter un marqueur provenance."
                    )

    def test_canonical_kpi_card_with_provenance_renders_5_axes(self):
        """`KpiCardWithProvenance` rend les 5 axes provenance canoniques."""
        path = ENERGY_UI / "KpiCardWithProvenance.jsx"
        content = path.read_text(encoding="utf-8")
        for axis in ("Source", "Service", "Formule", "Période", "Confiance"):
            assert axis in content, (
                f"KpiCardWithProvenance.jsx ne rend pas l'axe canonique « {axis} ». Régression P1.S7."
            )

    def test_p2_4_corrected_favorable_hours_panel(self):
        """Sprint P2.4 — FavorableHoursPanel expose désormais un marqueur provenance."""
        path = ENERGY_UI / "FavorableHoursPanel.jsx"
        content = path.read_text(encoding="utf-8")
        assert "favorable-hours-provenance" in content, (
            'FavorableHoursPanel.jsx doit exposer data-testid="favorable-hours-provenance" (correction P2.4).'
        )
