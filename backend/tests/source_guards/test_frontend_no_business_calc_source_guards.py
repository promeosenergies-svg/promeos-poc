"""
PROMEOS — Source-guard : zéro calcul métier énergie côté frontend.

Sprint Énergie P0.S1a (2026-05-29, brief P2.1).

Doctrine non-négociable (cf. CLAUDE.md « Règle d'or — ZERO calcul métier
frontend ») : tout calcul énergétique (CO₂, kWh, kW, coût, baseline,
quartiles, score qualité, règles d'anomalie) DOIT vivre dans un service
backend SoT, être exposé via REST, et consommé en lecture seule côté FE.

Ce source-guard bloque toute régression :
- Calcul CO₂ frontend (`kwh * co2Factor`, ADEME front).
- Génération de données synthétiques heatmap (Math.sin/cos baseline démo).
- Quartiles statistiques (Q1, Q3, percentile).
- Score fraîcheur / qualité métier (formule pénalité).
- `computeInsights` règles métier déterministes.
- Coût €/MWh / €/kWh agrégé côté FE.

Whitelist : opérations UI pures restent autorisées (formatage, tri d'affichage,
arrondi cosmétique, calcul de layout, Math.PI géométrie chart, conversion
unité formatée).

Périmètre : `frontend/src/pages/{Monitoring,Consumption*,Usages*,Consommations*}.jsx`
et `frontend/src/pages/{consumption,usages}/**.jsx` (sous-modules brique Énergie).

Si un nouveau calcul métier est REQUIS, ouvrir une PR qui :
1. Crée le service backend SoT.
2. Expose un endpoint `/api/energy/*`.
3. Met à jour le hook FE pour consommer le payload.
NE PAS ajouter à la whitelist sans audit qualifié.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

# Racine repo : tests/source_guards/ → tests/ → backend/ → repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_PAGES = REPO_ROOT / "frontend" / "src" / "pages"


# Périmètre fichiers énergie suivis (pattern glob).
ENERGY_PAGES_GLOB = [
    "Monitoring*.jsx",
    "Consumption*.jsx",
    "Consommations*.jsx",
    "Usages*.jsx",
    # Sous-modules
    "consumption/**/*.jsx",
    "consumption/**/*.js",
    "usages/**/*.jsx",
    "usages/**/*.js",
]


# Patterns interdits — règles d'anomalie / calculs métier reconnaissables.
# Chaque entrée = (regex, label métier, sévérité).
FORBIDDEN_PATTERNS: list[tuple[re.Pattern, str]] = [
    # 1. CO₂ frontend — multiplication par facteur émission
    (
        re.compile(r"\b(co2Factor|emission_factor|CO2_FACTOR)\s*\*"),
        "calcul CO₂ frontend (multiplication facteur émission) — doit consommer /api/monitoring/emissions",
    ),
    (
        re.compile(r"\*\s*(co2Factor|emission_factor|CO2_FACTOR)\b"),
        "calcul CO₂ frontend (multiplication facteur émission) — doit consommer /api/monitoring/emissions",
    ),
    # 2. Génération synthétique heatmap baseline démo
    (
        re.compile(r"baseline\s*=\s*.*Math\.sin"),
        "génération sinusoïdale baseline frontend — doit venir de services/demo_seed/orchestrator backend",
    ),
    (
        re.compile(r"actual\s*=\s*baseline\s*[\+\*]"),
        "calcul actual = baseline + ... frontend — doit venir backend (demo_seed ou diagnostic_service)",
    ),
    # 3. Quartiles statistiques métier
    (
        re.compile(r"Math\.floor\s*\(\s*\w+\.length\s*\*\s*0\.(25|5|75)\s*\)"),
        "calcul quartile/médiane frontend — doit être consumption_granularity_service.compute_quantiles backend",
    ),
    # 4. Score fraîcheur / qualité métier (formule cumulative)
    # Pattern : let score = ... ; if (...) score = Math.min(score, X)
    # On cible la séquence min(score, N) répétée (formule pénalité métier).
    (
        re.compile(r"score\s*=\s*Math\.min\s*\(\s*score\s*,\s*\d+\s*\).*?\n.*?score\s*=\s*Math\.min", re.DOTALL),
        "score qualité avec pénalité cumulative frontend — doit être data_freshness_service backend",
    ),
    # 5. computeInsights règles métier
    (
        re.compile(r"\bcomputeInsights\s*\("),
        "règles d'anomalie frontend (computeInsights) — doit être consumption_diagnostic.insights backend",
    ),
    # 6. Reduce d'agrégation impact financier (waste / loss)
    (
        re.compile(r"\.reduce\s*\(\s*\([\w,\s]*\)\s*=>\s*\w+\s*\+\s*\(?\s*\w+\.estimated_(impact|loss)_eur"),
        "agrégation impact financier frontend (reduce sur estimated_*_eur) — doit être pré-calculé backend",
    ),
]


# Whitelist : fichiers explicitement autorisés (ratchet baseline P0.S1a).
# Chaque entrée DOIT documenter pourquoi + sprint cible de cleanup.
#
# Doctrine ratchet : cette whitelist ne doit JAMAIS grossir. Toute nouvelle
# violation hors whitelist fait échouer le guard. Les entrées existantes
# doivent être retirées au fur et à mesure des sprints de migration P0.S1b
# + (cf. docs/audits/audit_menu_energie_monitoring_conso_2026_05_29.md
# §11 P0 #4-8 + plan refonte P0).
WHITELIST: dict[str, str] = {
    # ════════════════════════════════════════════════════════════════════
    # Ratchet baseline post-P0.S1c (2026-05-29).
    #
    # État final P0.S1c : la dette « zéro calcul métier frontend » est
    # CLÔTURÉE pour les patterns historiques (CO₂, heatmap sinusoïdale,
    # quartiles Q1/Q3, score fraîcheur, computeInsights). Les SoT backend
    # sont tous en place et consommés (ou la fonction est supprimée si
    # elle était orpheline / code mort).
    #
    # Récap migrations effectuées :
    #
    #   ✓ P0.5 CO₂ frontend (P0.S1b) → helper canonique utils/co2.js
    #     (HELPER_WHITELIST ci-dessous), 6 occurrences migrées.
    #
    #   ✓ P0.4 heatmap synthétique (P0.S1b) → ConsumptionDiagPage
    #     `generateComparisonChart` SUPPRIMÉE + placeholder Evidence.
    #
    #   ✓ P0.6 quartiles Q1/Q3 (P0.S1c) → backend
    #     consumption_granularity_service.compute_quantiles +
    #     enrichissement payload climate.outlier_bounds sur
    #     /api/monitoring/kpis. MonitoringPage:_filterOutliers
    #     devient un filtre UI pur consommant les bornes backend.
    #
    #   ✓ P0.7 score fraîcheur (P0.S1c) → MonitoringPage
    #     `computeConfidence` SUPPRIMÉE (code mort sans consommateur).
    #     SoT backend data_freshness_service disponible pour P1.S2.
    #
    #   ✓ P0.8 computeInsights (P0.S1c) → backend
    #     explorer_insights_service.build_explorer_insights + endpoint
    #     POST /api/consumption/explorer-insights. ConsumptionExplorerPage
    #     consomme via hook getExplorerInsights().
    #     `frontend/src/pages/consumption/insightRules.js` SUPPRIMÉ.
    #
    # ════════════════════════════════════════════════════════════════════
    # Dette résiduelle P1.S2 — agrégations post-filtre scope FE.
    #
    # Ces 2 reduces somment les `estimated_*_eur` d'insights déjà filtrés
    # côté FE par le scope (selectedSiteId, queryStatus). Le total
    # affiché varie donc avec le filtre UI. Migration backend nécessite
    # de pousser le filtre scope au BE (endpoints orchestration
    # /api/energy/* livrés P1.S2 — cf. brief P1.S2). À retirer dès que
    # ces endpoints exposeront `total_estimated_eur` calculé post-scope.
    # ════════════════════════════════════════════════════════════════════
    "frontend/src/pages/ConsumptionDiagPage.jsx": (
        "P1.S2 dette résiduelle — `computeSummaryFromInsights` "
        "reduce les insights après filtre scope FE (selectedSiteId, "
        "queryStatus). Migration vers endpoint orchestration "
        "/api/energy/synthesis (P1.S2) qui pré-filtrera + pré-agrégera "
        "côté backend. Code FE devient consommation pure du payload."
    ),
    "frontend/src/pages/MonitoringPage.jsx": (
        "P1.S2 dette résiduelle — 2 sources distinctes : "
        "(1) `totalWasteEur` reduce sur wasteAlerts post-filtre "
        "scope, migration vers /api/monitoring/alerts qui exposera "
        "`total_impact_eur` pré-calculé. "
        "(2) `computeConfidence` (climateConf + qualityConf via useMemo) "
        "— combinaison cosmétique de r²/n_points/coverage_pct déjà "
        "calculés backend, en attente du payload `confidence_score` "
        "pré-calculé via /api/energy/synthesis (data_freshness_service "
        "SoT déjà livré P0.S1b, exposition endpoint P1.S2)."
    ),
}


# Modules helpers explicitement autorisés à faire la multiplication
# `kwh * factor` (conversion d'unité pure, pas calcul métier). Voir
# documentation in-file pour chaque entrée.
HELPER_WHITELIST: dict[str, str] = {
    "frontend/src/utils/co2.js": (
        "Helper canonique P0.S1b — module dédié conversion kWh → "
        "kgCO₂eq via facteur ADEME V23.6 fourni par backend. Unique "
        "point autorisé pour la multiplication `kwh * facteur_CO2` "
        "côté frontend. Documentation doctrine dans le fichier."
    ),
}


def _energy_page_files() -> list[Path]:
    """Retourne la liste des fichiers énergie suivis par ce guard."""
    files: set[Path] = set()
    for pattern in ENERGY_PAGES_GLOB:
        files.update(FRONTEND_PAGES.glob(pattern))
    # Tri pour reproductibilité output
    return sorted(files)


def _check_file(path: Path) -> list[tuple[int, str, str]]:
    """Retourne les violations détectées : [(line_no, label, snippet)]."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    if rel in WHITELIST or rel in HELPER_WHITELIST:
        return []
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError):
        return []

    violations: list[tuple[int, str, str]] = []
    for pattern, label in FORBIDDEN_PATTERNS:
        for match in pattern.finditer(content):
            # Calculer le numéro de ligne approximatif
            line_no = content[: match.start()].count("\n") + 1
            snippet = match.group(0).split("\n")[0][:120]
            violations.append((line_no, label, snippet))
    return violations


class TestFrontendNoBusinessCalc:
    """Aucun calcul métier énergie ne doit vivre côté frontend."""

    def test_energy_pages_have_no_business_calc(self):
        """Scan exhaustif des pages énergie frontend.

        Si ce test échoue : votre PR introduit un calcul métier côté FE.
        - Solution principale : créer / étendre un service backend +
          endpoint REST, consommer le résultat en hook.
        - Solution exceptionnelle : ajouter le fichier à WHITELIST
          ci-dessus avec justification ADR.
        """
        files = _energy_page_files()
        assert files, (
            f"Aucun fichier énergie trouvé sous {FRONTEND_PAGES} avec patterns "
            f"{ENERGY_PAGES_GLOB}. Vérifier l'arborescence frontend."
        )

        all_violations: list[str] = []
        for path in files:
            rel = path.relative_to(REPO_ROOT).as_posix()
            for line_no, label, snippet in _check_file(path):
                all_violations.append(f"  {rel}:{line_no} → {label}\n      « {snippet} »")

        if all_violations:
            msg = (
                "\n\n🔴 Calcul métier énergie détecté côté frontend "
                "(doctrine `ZERO calcul métier frontend` — cf. CLAUDE.md).\n\n"
                + "\n".join(all_violations)
                + "\n\nMigration recommandée : créer service backend SoT + endpoint REST.\n"
                + "Si dérogation nécessaire : ajouter à WHITELIST avec justification ADR.\n"
            )
            pytest.fail(msg)

    def test_whitelist_entries_have_justification(self):
        """Toute entrée de WHITELIST doit avoir une justification non vide."""
        for path, reason in WHITELIST.items():
            assert reason and reason.strip(), (
                f"WHITELIST entry '{path}' has empty justification. "
                "Document why this file is exempted (ADR ref, audit, etc.)."
            )

    def test_guard_scope_is_not_empty(self):
        """Sanity check : le guard scanne effectivement des fichiers."""
        files = _energy_page_files()
        # Au moins les 5 pages principales doivent exister
        names = {f.name for f in files}
        for must_exist in [
            "MonitoringPage.jsx",
            "ConsumptionPortfolioPage.jsx",
            "ConsumptionExplorerPage.jsx",
            "UsagesDashboardPage.jsx",
            "ConsumptionDiagPage.jsx",
        ]:
            assert must_exist in names, (
                f"Page énergie attendue '{must_exist}' introuvable. Mise à jour ENERGY_PAGES_GLOB requise."
            )
