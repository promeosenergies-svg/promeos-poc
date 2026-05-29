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
    # Dettes héritées identifiées par audit 2026-05-29 §9 (violations doctrine
    # « zero calcul frontend »). Cleanup P0.S1b prévu :
    #   - P0.5 CO₂ frontend → emissions_service backend
    #   - P0.4 heatmap synthétique → demo_seed backend
    #   - P0.6 quartiles Q1/Q3 → consumption_granularity_service backend
    #   - P0.7 score fraîcheur → data_freshness_service backend
    #   - P0.8 computeInsights → consumption_diagnostic backend
    "frontend/src/pages/ConsumptionDiagPage.jsx": (
        "P0.S1b ratchet : violations connues — CO₂ frontend l.225 + heatmap "
        "sinusoïdale l.132-152 + agrégation totalCo2eKg l.247. Migration "
        "vers emissions_service + demo_seed backend prévue P0.S1b "
        "(audit P0 #4-5, brief sprint correction)."
    ),
    "frontend/src/pages/MonitoringPage.jsx": (
        "P0.S1b ratchet : violations connues — quartiles Q1/Q3 l.1306-1308 + "
        "score fraîcheur computeConfidence l.202-211 + reduce wasteAlerts. "
        "Migration vers consumption_granularity_service.compute_quantiles + "
        "data_freshness_service backend prévue P0.S1b (audit P0 #6-7)."
    ),
    "frontend/src/pages/ConsumptionExplorerPage.jsx": (
        "P0.S1b ratchet : violations connues — CO₂ frontend l.384 + appel "
        "computeInsights l.883 (règles d'anomalie déterministes). Migration "
        "vers emissions_service + consumption_diagnostic.insights backend "
        "prévue P0.S1b (audit P0 #5, #8)."
    ),
    "frontend/src/pages/consumption/OverviewRow.jsx": (
        "P0.S1b ratchet : CO₂ frontend l.43 — sous-composant Overview "
        "consommé par Explorer. Migration corrélée à ConsumptionExplorerPage "
        "(emissions_service backend) en P0.S1b."
    ),
    "frontend/src/pages/consumption/insightRules.js": (
        "P0.S1b ratchet : fonction computeInsights l.17 — règles d'anomalie "
        "métier frontend. À supprimer après migration consumption_diagnostic."
        "insights backend (audit P0 #8). Fichier candidat à DELETE en P0.S1b."
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
    if rel in WHITELIST:
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
