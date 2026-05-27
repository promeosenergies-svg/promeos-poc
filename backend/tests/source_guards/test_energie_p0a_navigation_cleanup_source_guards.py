"""Source-guards Énergie P0a navigation cleanup (2026-05-27).

Verrous structurels post-sprint claude/energie-p0a-navigation-cleanup,
issus de l'audit menu Énergie #313 (§7-§9). Empêchent toute régression
silencieuse sur les 4 axes :

  G1. /flex retiré de la sidebar publique (brief « Aucun Flex visible client »).
      Reste accessible via HIDDEN_PAGES + deep-link.
  G2. /cockpit/pilotage FE redirige vers /cockpit/jour (pas de page legacy
      CockpitPilotage rendue).
  G3. /api/cockpit/pilotage retourne 410 Gone FR (alternatif documenté).
  G4. /usage-steering interdit (aucun nouveau silo, anti-pattern §6.2).
  G5. « Pilotage des usages » jamais en menu hors /usages (4e tab interne
      uniquement, pas de menu sidebar dédié).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NAV_REGISTRY = REPO_ROOT.parent / "frontend" / "src" / "layout" / "NavRegistry.js"
APP_JSX = REPO_ROOT.parent / "frontend" / "src" / "App.jsx"
COCKPIT_ROUTE = REPO_ROOT / "routes" / "cockpit.py"
FRONTEND_SRC = REPO_ROOT.parent / "frontend" / "src"


# ── G1 : Flex Intelligence retiré de la sidebar publique ────────────────


def test_g1_flex_not_in_nav_sections_visible():
    """Le module 'energie' de NavRegistry NAV_SECTIONS ne doit plus
    contenir un item avec to: '/flex' visible (cf. brief P0a C1).
    Tolère les mentions /flex en commentaires (// ... /flex ...)."""
    text = NAV_REGISTRY.read_text(encoding="utf-8")
    m = re.search(
        r"key:\s*'energie',(.*?)// === PATRIMOINE",
        text,
        re.DOTALL,
    )
    assert m, "Bloc module 'energie' introuvable dans NAV_SECTIONS"
    energie_block = m.group(1)
    # On filtre les lignes de commentaire pour ne tester que le vrai code.
    code_lines = [ln for ln in energie_block.splitlines() if not ln.lstrip().startswith("//")]
    code_only = "\n".join(code_lines)
    assert "/flex" not in code_only, (
        "Énergie P0a régression : /flex ne doit plus apparaître comme item "
        "visible du module energie (cf. audit §1 + brief contrainte "
        "« Aucun Flex visible client »)."
    )


def test_g1_flex_present_in_hidden_pages():
    """/flex reste accessible via HIDDEN_PAGES (deep-link + ⌘K search)."""
    text = NAV_REGISTRY.read_text(encoding="utf-8")
    # On vérifie qu'une entrée HIDDEN_PAGES pointe vers /flex avec reason
    # documentée (convention SG_NAV_FE_04).
    hidden_block = re.search(
        r"export const HIDDEN_PAGES = \[(.*?)\];",
        text,
        re.DOTALL,
    )
    assert hidden_block, "HIDDEN_PAGES array introuvable"
    assert "to: '/flex'" in hidden_block.group(1), (
        "/flex doit rester dans HIDDEN_PAGES après retrait sidebar pour "
        "préserver l'accès Energy Manager via deep-link + ⌘K (audit §7.1)."
    )


# ── G2 : /cockpit/pilotage FE → redirect /cockpit/jour ──────────────────


def test_g2_cockpit_pilotage_route_is_redirect_to_jour():
    """La route /cockpit/pilotage doit utiliser <Navigate to=/cockpit/jour>,
    pas rendre <CockpitPilotage/>. Anti-régression doublon D1 (audit §5.1)."""
    text = APP_JSX.read_text(encoding="utf-8")
    # Cherche le bloc Route path="/cockpit/pilotage"
    m = re.search(
        r'path="/cockpit/pilotage"\s*element=\{([^}]+)\}',
        text,
        re.DOTALL,
    )
    assert m, "Route /cockpit/pilotage introuvable dans App.jsx"
    element = m.group(1)
    assert "Navigate" in element and "/cockpit/jour" in element, (
        f"Énergie P0a régression : /cockpit/pilotage doit redirect vers "
        f"/cockpit/jour, pas rendre une page legacy. Got element : {element[:120]}"
    )
    assert "<CockpitPilotage" not in element, (
        "<CockpitPilotage/> ne doit plus être rendu (legacy 1722 l, remplacé par redirect + 4e tab /usages futur)."
    )


def test_g2_no_active_cockpit_pilotage_link_in_fe():
    """Aucun composant FE ne doit pousser un lien actif vers
    /cockpit/pilotage (ni <Link to=>, ni navigate(), ni href=)."""
    violations = []
    # Patterns interdits : <Link to="/cockpit/pilotage" + navigate('/cockpit/pilotage')
    forbidden = [
        re.compile(r'to=["\']\/cockpit\/pilotage["\']'),
        re.compile(r'navigate\(["\']\/cockpit\/pilotage["\']'),
        re.compile(r'href=["\']\/cockpit\/pilotage["\']'),
    ]
    for f in FRONTEND_SRC.rglob("*.jsx"):
        if "__tests__" in str(f) or ".test." in f.name:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for pat in forbidden:
            if pat.search(text):
                violations.append((f.relative_to(REPO_ROOT.parent), pat.pattern))
    assert not violations, (
        "Liens actifs vers /cockpit/pilotage interdits — utiliser /cockpit/jour "
        f"ou /action-center-v4/pilotage. Violations : {violations}"
    )


# ── G3 : /api/cockpit/pilotage = 410 Gone FR ────────────────────────────


def test_g3_cockpit_pilotage_endpoint_returns_410_with_fr_message():
    """L'endpoint BE /api/cockpit/pilotage doit lever 410 avec un message FR
    et la clé 'replacement' documentant les alternatives canoniques."""
    text = COCKPIT_ROUTE.read_text(encoding="utf-8")
    m = re.search(
        r'@router\.get\(\s*"/cockpit/pilotage".*?def\s+cockpit_pilotage_gone.*?HTTPException\([^)]*status_code\s*=\s*410[^)]*detail\s*=\s*\{(.*?)\}\s*,?\s*\)',
        text,
        re.DOTALL,
    )
    assert m, (
        "Endpoint /cockpit/pilotage en 410 Gone introuvable dans cockpit.py "
        "(cf. brief P0a C3 : message FR + replacement + hint)."
    )
    detail = m.group(1)
    for required in (
        '"code": "ENDPOINT_GONE"',
        "Cette route historique a été retirée",
        "/api/cockpit/jour",
        "/api/cockpit/strategique",
        "Centre d'Action",
    ):
        assert required in detail, f"Clé/texte manquant dans le 410 Gone /cockpit/pilotage : {required!r}"


# ── G4 + G5 : Anti-silo Usage Steering ──────────────────────────────────


def test_g4_no_usage_steering_route_in_fe():
    """Aucune route frontend ne doit déclarer /usage-steering (anti-silo
    explicite brief P0a C4 et audit §7 architecture cible)."""
    violations = []
    forbidden = re.compile(r'["\']\/usage-steering["\']')
    for f in FRONTEND_SRC.rglob("*.jsx"):
        if "__tests__" in str(f) or ".test." in f.name:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        if forbidden.search(text):
            violations.append(f.relative_to(REPO_ROOT.parent))
    assert not violations, (
        "Route /usage-steering interdite — Pilotage des usages doit être un "
        f"4e onglet dans /usages, PAS un nouveau silo. Violations : {violations}"
    )


def test_g4_no_usage_steering_path_in_navregistry():
    """NavRegistry ne doit jamais déclarer un item to: '/usage-steering'."""
    text = NAV_REGISTRY.read_text(encoding="utf-8")
    assert "/usage-steering" not in text, (
        "Énergie P0a régression : NavRegistry contient /usage-steering. Anti-silo strict (audit §7.3 + brief P0a C4)."
    )


def test_g4_no_flex_intelligence_in_nav_sections_label():
    """Le label « Flex Intelligence » ne doit plus apparaître dans
    NAV_SECTIONS (visible sidebar). Toléré dans HIDDEN_PAGES (label
    « Flex Intelligence (deep-link) »)."""
    text = NAV_REGISTRY.read_text(encoding="utf-8")
    nav_sections_block = re.search(
        r"export const NAV_SECTIONS = \[(.*?)\];",
        text,
        re.DOTALL,
    )
    assert nav_sections_block, "NAV_SECTIONS array introuvable"
    block = nav_sections_block.group(1)
    # Recherche du label brut « Flex Intelligence » dans NAV_SECTIONS
    # (sans le suffixe « (deep-link) » qui caractérise HIDDEN_PAGES).
    forbidden = re.compile(r"label:\s*'Flex Intelligence'(?!\s*\(deep-link\))")
    assert not forbidden.search(block), (
        "Énergie P0a régression : « Flex Intelligence » visible dans la "
        "sidebar publique (NAV_SECTIONS). Doit rester en HIDDEN_PAGES "
        "uniquement (brief P0a C1 « Aucun Flex visible client »)."
    )


def test_g5_no_pilotage_des_usages_menu_label_in_nav_sections():
    """Pilotage des usages ne doit pas exister comme item sidebar dédié —
    seulement comme 4e tab dans /usages (audit §7.1 + brief P0a C4)."""
    text = NAV_REGISTRY.read_text(encoding="utf-8")
    nav_sections_block = re.search(
        r"export const NAV_SECTIONS = \[(.*?)\];",
        text,
        re.DOTALL,
    )
    assert nav_sections_block, "NAV_SECTIONS array introuvable"
    block = nav_sections_block.group(1)
    forbidden = re.compile(r"label:\s*['\"]Pilotage des usages['\"]")
    assert not forbidden.search(block), (
        "Énergie P0a régression : « Pilotage des usages » présent comme "
        "menu sidebar. Doit rester un 4e tab interne dans /usages, jamais "
        "un nouveau menu (brief P0a C4 + audit §7.1)."
    )
