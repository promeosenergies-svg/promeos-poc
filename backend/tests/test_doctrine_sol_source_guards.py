"""
Source guards — Doctrine PROMEOS Sol v1.0.1.

Garde-fous automatiques pour empêcher toute régression doctrinale
pendant la refonte 12 semaines (Sprint 0bis → Sprint 6 démo juillet 2026).

Référence : docs/vision/promeos_sol_doctrine.md
ADR : docs/adr/ADR-001-grammaire-sol-industrialisee.md
      docs/adr/ADR-002-chantier-alpha-moteur-evenements.md
      docs/adr/ADR-003-chantier-beta-multi-archetype.md
      docs/adr/ADR-004-chantier-delta-transformation-acronymes.md

Trois familles de garde-fous :

1. Anti-pattern §6.5 — zéro logique métier frontend (règle d'or §8.1)
2. Anti-pattern §6.3 — aucun acronyme brut en titre H1/H2 frontend
3. Grammaire §5 — toute page Sol porte SolPageHeader (Sprint 1+ progressif)

Ces tests sont volontairement scoped sur les fichiers nouveaux/migrés
de la refonte sol2 (claude/refonte-sol2). Les fichiers legacy POC sont
exemptés via REFONTE_SCOPE pour éviter la régression sur la baseline.
"""

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"

# ── Scope refonte sol2 (Sprint 1+ progressif) ────────────────────────
# Au démarrage Sprint 0bis, scope = composants Sol nouveaux + DashboardHero
# livré Phase 4. À élargir sprint après sprint au fur et à mesure que
# les 8 pages legacy migrent vers la grammaire Sol (cf ADR-001 migration plan).
REFONTE_SCOPE = [
    FRONTEND_SRC / "ui" / "sol",
    FRONTEND_SRC / "pages" / "dashboard",
    # Sprint 1.1+ ajouter : pages/cockpit/ après refactor briefing-grade
    # Sprint 1.2+ ajouter : pages/sol/ (nouvelles pages Sol-grade)
]

# ── Acronymes interdits en titres (§6.3 + ADR-004) ───────────────────
# Whitelist : forme transformée "DT — trajectoire 2030" autorisée
# (acronyme suivi d'un tiret long et d'une narrative court).
RAW_ACRONYMS_FORBIDDEN_IN_TITLES = {
    "DT",
    "BACS",
    "APER",
    "OPERAT",
    "TURPE 7",
    "TURPE7",
    "CTA",
    "NEBCO",
    "ARENH",
    "VNU",
    "EUI",
    "DJU",
    "CUSUM",
    "TICGN",
    "aFRR",
    "AOFD",
}

# ── Patterns logique métier interdits frontend (§8.1 + §6.5) ─────────
# Détecte les calculs métier inacceptables dans .jsx (pas .js — les pure
# models comme dashboardEssentials.js sont autorisés en attente migration
# backend Sprint 2 chantier α).
BUSINESS_LOGIC_PATTERNS = [
    # Constantes ADEME en dur (doit venir backend)
    (
        r"OID_BENCHMARKS\s*=",
        "Constante ADEME ODP en dur — viole §8.1, doit venir backend (cf audit Patrimoine utils/benchmarks.js)",
    ),
    # Coefficient CO2 en dur
    (r"\b0\.0569\b", "Confusion possible TURPE 7 HPH (€/kWh) vs facteur CO₂ — anti-pattern doctrinal §8.3"),
    # Calculs intensité énergétique dans .jsx (à migrer backend)
    (
        r"const\s+ipe\s*=.*totalKwh.*totalSurface",
        "Calcul intensité énergétique frontend — viole §8.1, doit venir backend",
    ),
    # Hardcoded RegOps poids
    (r"WEIGHT_AUDIT_SME\s*=\s*0\.16", "Poids RegOps hardcodé — doit venir regs.yaml ParameterStore"),
]


def _list_jsx_files(scope_dirs):
    """Retourne tous les .jsx sous les dossiers du scope refonte."""
    files = []
    for scope_dir in scope_dirs:
        if not scope_dir.exists():
            continue
        files.extend(scope_dir.rglob("*.jsx"))
    return files


def _list_js_files(scope_dirs):
    """Retourne tous les .js sous les dossiers du scope refonte (hors tests/__tests__)."""
    files = []
    for scope_dir in scope_dirs:
        if not scope_dir.exists():
            continue
        for p in scope_dir.rglob("*.js"):
            if "__tests__" in p.parts or p.name.endswith(".test.js"):
                continue
            files.append(p)
    return files


def _read(path):
    return path.read_text(encoding="utf-8", errors="replace")


# ── Tests §6.5 — pas de logique métier frontend ──────────────────────


class TestNoBusinessLogicInRefonteFrontend:
    """ADR-001 — règle d'or §8.1 : zéro logique métier frontend dans le scope refonte sol2."""

    @pytest.mark.parametrize("pattern,reason", BUSINESS_LOGIC_PATTERNS)
    def test_no_forbidden_business_pattern(self, pattern, reason):
        violations = []
        for f in _list_jsx_files(REFONTE_SCOPE) + _list_js_files(REFONTE_SCOPE):
            content = _read(f)
            for match in re.finditer(pattern, content):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(f"{f.relative_to(REPO_ROOT)}:{line_num} — {match.group(0)}")
        assert not violations, (
            f"Violation §8.1 (logique métier frontend) — {reason}\nFichiers en faute :\n  " + "\n  ".join(violations)
        )


# ── Tests §6.3 — pas d'acronyme brut en titres ──────────────────────


class TestNoRawAcronymsInTitles:
    """ADR-004 — aucun acronyme brut en H1/H2/titre carte. Whitelist : "ACRONYM — narrative"."""

    @staticmethod
    def _has_raw_acronym(text, acronym):
        """Détecte acronyme brut hors whitelist (suivi tiret long ou em dash + narrative)."""
        # Whitelist forme "DT — trajectoire", "DT - trajectoire", "DT (Décret Tertiaire)"
        whitelist_patterns = [
            rf"\b{re.escape(acronym)}\s*[—–-]\s*\w",  # "DT — trajectoire"
            rf"\b{re.escape(acronym)}\s*\(",  # "DT (Décret Tertiaire)"
        ]
        for wl in whitelist_patterns:
            if re.search(wl, text):
                return False
        # Acronyme nu détecté
        return bool(re.search(rf"\b{re.escape(acronym)}\b", text))

    def test_no_raw_acronym_in_h1_h2_titles(self):
        # Match attribut className contenant text-* + balise H1/H2/title puis contenu
        # Heuristique : on cherche les chaînes JSX dans des titres explicites.
        title_patterns = [
            r"<h1[^>]*>([^<]+)</h1>",
            r"<h2[^>]*>([^<]+)</h2>",
            r'title=\{?"([^"]+)"',
            r"title=\'([^\']+)\'",
            r"kicker=\{?\"([^\"]+)\"",
        ]
        violations = []
        for f in _list_jsx_files(REFONTE_SCOPE):
            content = _read(f)
            for tp in title_patterns:
                for match in re.finditer(tp, content):
                    title_text = match.group(1)
                    for acronym in RAW_ACRONYMS_FORBIDDEN_IN_TITLES:
                        if self._has_raw_acronym(title_text, acronym):
                            line_num = content[: match.start()].count("\n") + 1
                            violations.append(
                                f"{f.relative_to(REPO_ROOT)}:{line_num} — acronyme '{acronym}' "
                                f"brut dans titre : '{title_text[:80]}'"
                            )
        assert not violations, (
            "Violation §6.3 (acronymes bruts en titres) — ADR-004 transformation systématique :\n  "
            + "\n  ".join(violations[:20])  # limite output si beaucoup de violations
            + (f"\n  (...{len(violations) - 20} autres violations)" if len(violations) > 20 else "")
        )


# ── Tests §5 — grammaire Sol invariant ──────────────────────────────


class TestSolGrammarInvariant:
    """ADR-001 — toute page Sol nouvelle/migrée doit porter SolPageHeader.

    Au Sprint 0bis : scope = pages/dashboard/ (Phase 4 livré). Au Sprint 1+ :
    élargir progressivement à pages/sol/, pages/cockpit/ etc. via REFONTE_SCOPE.
    """

    def test_dashboard_pages_use_sol_components(self):
        """Pages dashboard Sol doivent importer SolPageHeader ou être reconnues comme composants enfants."""
        dashboard_dir = FRONTEND_SRC / "pages" / "dashboard"
        if not dashboard_dir.exists():
            pytest.skip("pages/dashboard non encore créé (Sprint 1)")
        page_files = list(dashboard_dir.rglob("*Page.jsx"))
        # Sprint 0bis : pas encore de Page.jsx dans /dashboard (DashboardHeroFeatured est composant child).
        # Le test devient bloquant à partir Sprint 1.1 quand DashboardPage.jsx existera.
        if not page_files:
            pytest.skip("pages/dashboard ne contient pas encore de *Page.jsx (Sprint 1.1+)")
        violations = []
        for pf in page_files:
            content = _read(pf)
            if "SolPageHeader" not in content and "SolNarrative" not in content:
                violations.append(str(pf.relative_to(REPO_ROOT)))
        assert not violations, (
            "Violation §5 grammaire Sol — pages doivent porter SolPageHeader/SolNarrative :\n  "
            + "\n  ".join(violations)
        )


# ── Tests doctrine v1.0.1 — triptyque typo ──────────────────────────


class TestTriptyqueTypoSol:
    """v1.0.1 patch — triptyque Fraunces + DM Sans + JetBrains Mono inviolable."""

    def test_tokens_sol_declares_correct_fonts(self):
        tokens_path = FRONTEND_SRC / "ui" / "sol" / "tokens.css"
        assert tokens_path.exists(), f"tokens.css absent : {tokens_path}"
        content = _read(tokens_path)
        assert "Fraunces" in content, "Triptyque Sol : Fraunces (display) absent de tokens.css"
        assert "DM Sans" in content, "Triptyque Sol v1.0.1 : DM Sans (body) absent de tokens.css"
        assert "JetBrains Mono" in content, "Triptyque Sol v1.0.1 : JetBrains Mono (mono) absent de tokens.css"

    def test_no_inter_font_imported(self):
        """Inter banni — devenu font B2B SaaS générique, viole signal éditorial Sol."""
        index_html = REPO_ROOT / "frontend" / "index.html"
        if index_html.exists():
            content = _read(index_html)
            # Tolérance : Inter peut apparaître dans commentaires, mais pas chargé Google Fonts
            forbidden = re.search(r"family=Inter[&:\s]", content)
            assert not forbidden, (
                "Violation v1.0.1 — Inter chargé dans index.html. Triptyque doctrine = "
                "Fraunces + DM Sans + JetBrains Mono."
            )

    def test_no_ibm_plex_mono_imported(self):
        """IBM Plex Mono banni — JetBrains Mono est canonical mono Sol (tabular-nums supérieur)."""
        index_html = REPO_ROOT / "frontend" / "index.html"
        if index_html.exists():
            content = _read(index_html)
            forbidden = re.search(r"family=IBM\+Plex\+Mono", content)
            assert not forbidden, (
                "Violation v1.0.1 — IBM Plex Mono chargé. Triptyque doctrine = Fraunces + DM Sans + JetBrains Mono."
            )
