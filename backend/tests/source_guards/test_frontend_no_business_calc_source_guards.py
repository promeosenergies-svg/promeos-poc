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
    # Ratchet baseline post-P0.S1b (2026-05-29). État après migrations :
    #
    #   ✓ P0.5 CO₂ frontend → migré vers helper utils/co2.js (whitelisté
    #     par regex spéciale : helper canonique, conversion d'unité pure).
    #     OverviewRow.jsx 100 % nettoyé → RETIRÉ de la whitelist.
    #
    #   ✓ P0.6 quartiles Q1/Q3 → SoT backend
    #     consumption_granularity_service.compute_quantiles disponible
    #     (cf. test_consumption_quantiles.py 23 cas verts). Migration FE
    #     MonitoringPage.jsx:1306-1308 prévue P0.S1c.
    #
    #   ✓ P0.7 score fraîcheur → SoT backend
    #     data_freshness_service.compute_meter_freshness disponible
    #     (cf. test_data_freshness_service.py 13 cas verts). Migration FE
    #     MonitoringPage.jsx:202-217 prévue P0.S1c.
    #
    #   ⏳ P0.4 heatmap synthétique → ConsumptionDiagPage.jsx
    #     `generateComparisonChart` SUPPRIMÉ + placeholder visible
    #     (cf. tests Diag « no Math.sin » verts). Mais l'export
    #     `generateComparisonChart` reste référencé dans le bloc
    #     commentaire DELETED pour traçabilité — donc la whitelist
    #     Diag est conservée pour cette session, à retirer post-cleanup
    #     du bloc commentaire P0.S1c (audit P0 #4).
    #
    #   ⏳ P0.8 computeInsights → reste en frontend (consumption/
    #     insightRules.js + ConsumptionExplorerPage.jsx:883). Migration
    #     vers consumption_diagnostic.insights planifiée P0.S1c (lourd
    #     refactor — règles déterministes talon/WE/pic à formaliser).
    #
    "frontend/src/pages/ConsumptionDiagPage.jsx": (
        "P0.S1c ratchet : bloc commentaire historique DELETED contient "
        "encore les patterns sin/cos pour traçabilité du fix (cf. "
        "commentaire l.126+ « DELETED generateComparisonChart »). "
        "À retirer du commentaire en P0.S1c quand l'historique sera "
        "documenté dans le CHANGELOG."
    ),
    "frontend/src/pages/MonitoringPage.jsx": (
        "P0.S1c ratchet : quartiles Q1/Q3 frontend _filterOutliers "
        "l.1304-1313 + score fraîcheur computeConfidence l.199-217 + "
        "reduce wasteAlerts. SoT backend déjà disponible "
        "(compute_quantiles + data_freshness_service). Migration FE "
        "planifiée P0.S1c — risque haut (3 231 LoC, tests Playwright "
        "indispensables avant refactor)."
    ),
    "frontend/src/pages/ConsumptionExplorerPage.jsx": (
        "P0.S1c ratchet : appel computeInsights l.883 (règles "
        "d'anomalie déterministes). CO₂ frontend MIGRÉ vers "
        "kwhToCo2Kg (utils/co2.js). Reste à migrer computeInsights "
        "vers consumption_diagnostic.insights backend P0.S1c."
    ),
    "frontend/src/pages/consumption/insightRules.js": (
        "P0.S1c ratchet : fonction computeInsights — règles d'anomalie "
        "métier frontend. À supprimer après migration "
        "consumption_diagnostic.insights backend P0.S1c. Fichier "
        "candidat à DELETE (cf. audit P0 #8)."
    ),
    # frontend/src/pages/consumption/OverviewRow.jsx — RETIRÉ post-P0.S1b
    # (toutes violations CO₂ migrées vers kwhToCo2Kg, plus aucune
    # violation détectée par les patterns du guard).
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
