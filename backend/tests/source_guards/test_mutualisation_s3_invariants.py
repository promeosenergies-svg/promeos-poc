"""Source-guards Sprint S3 — invariants juridiques Mutualisation Art. 14.

Verrouille la présence des références réglementaires sourcées + la
discipline « zéro concurrent dans UI » pour ce nouveau périmètre.
"""

from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


def _read(rel_path: str) -> str:
    return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")


# ─── A. Sources réglementaires obligatoires ──────────────────────────────


@pytest.fixture(scope="module")
def service_src() -> str:
    return _read("backend/services/tertiaire_groupe_structures_service.py")


@pytest.fixture(scope="module")
def routes_src() -> str:
    return _read("backend/routes/tertiaire_mutualisation.py")


@pytest.fixture(scope="module")
def model_src() -> str:
    return _read("backend/models/tertiaire_mutualisation.py")


@pytest.fixture(scope="module")
def ui_src() -> str:
    return _read("frontend/src/components/conformite/MutualisationSection.jsx")


@pytest.fixture(scope="module")
def crosscheck_src() -> str:
    return _read("docs/audits/crosscheck_legifrance_mutualisation_art14_2026_05_28.md")


def test_service_cite_article_14(service_src: str) -> None:
    """Le service doit citer l'Article 14 dans les messages opposables."""
    assert "Art. 14 §1 al.3" in service_src or "Art. 14 §1 al.4" in service_src
    assert "10 avril 2020" in service_src


def test_service_cite_l174_1_recodifie(service_src: str) -> None:
    """Le service doit utiliser la référence L.174-1 (recodifiée) ou R.174-31."""
    assert "L.174-1" in service_src or "R.174-31" in service_src


def test_routes_expose_source_in_violation_payload(routes_src: str) -> None:
    """Toute violation métier retourne une référence Légifrance."""
    assert "Article 14" in routes_src
    assert "L.174-1" in routes_src or "R.174-31" in routes_src


def test_model_documente_les_5_invariants(model_src: str) -> None:
    """Les 5 invariants juridiques sont documentés dans le module modèle."""
    for inv in ("I1.", "I2.", "I3.", "I4.", "I5."):
        assert inv in model_src, f"Invariant {inv} non documenté dans le modèle"


def test_export_csv_mentionne_table_1b(routes_src: str) -> None:
    """L'endpoint export Table 1B doit citer la Table 1B Annexe IV."""
    assert "Table 1B" in routes_src
    assert "Annexe IV" in routes_src


def test_ui_mentionne_module_operat_mutualisation(ui_src: str) -> None:
    """L'UI doit afficher le message 'Module OPERAT mutualisation' du brief."""
    assert "Module OPERAT mutualisation" in ui_src


def test_ui_mentionne_article_14(ui_src: str) -> None:
    """L'UI doit afficher la source Art. 14 dans le warning juridique."""
    assert "Article 14" in ui_src


def test_ui_expose_groupe_structures_bloc(ui_src: str) -> None:
    """Le bloc doit exposer un testid pour Playwright."""
    assert 'data-testid="groupe-structures-bloc"' in ui_src


def test_ui_expose_warning_juridique(ui_src: str) -> None:
    """Warning juridique visible quand groupe non opposable (I2)."""
    assert "Groupe non opposable" in ui_src


def test_ui_expose_bouton_export_conditionnel(ui_src: str) -> None:
    """Boutons CSV + PDF Table 1B doivent exister + variante désactivée.

    Sprint S4 (2026-05-29) : le bouton unique « Exporter Table 1B » a été
    décliné en CSV + PDF (le PDF inclut le hash SHA256 opposable). La
    sémantique reste identique : un seul CTA primaire conditionnel selon
    `allRlOk`.
    """
    assert "CSV Table 1B" in ui_src
    assert "PDF Table 1B" in ui_src
    assert "Export indisponible" in ui_src


def test_crosscheck_phase_0_present(crosscheck_src: str) -> None:
    """Le cross-check Légifrance Phase 0 doit être livré."""
    assert "Article 14" in crosscheck_src
    assert "L.174-1" in crosscheck_src
    assert "R.174-31" in crosscheck_src
    assert "Table 1B" in crosscheck_src
    assert "STOP gate franchie" in crosscheck_src


# ─── B. Anti-concurrent (la doctrine zéro-concurrent S2 reste vraie) ────


def test_no_competitor_in_service(service_src: str) -> None:
    for name in ("Advizeo", "Deepki", "Metron", "Citron", "Energisme"):
        assert name not in service_src


def test_no_competitor_in_routes(routes_src: str) -> None:
    for name in ("Advizeo", "Deepki", "Metron", "Citron", "Energisme"):
        assert name not in routes_src


def test_no_competitor_in_ui(ui_src: str) -> None:
    for name in ("Advizeo", "Deepki", "Metron", "Citron", "Energisme"):
        assert name not in ui_src


# ─── C. Pas de nouveau menu (hub /conformite conservé) ──────────────────


def test_no_new_menu_in_ui(ui_src: str) -> None:
    """Le composant ne doit pas ajouter de route ni de navigation parente."""
    # Le bloc s'insère dans MutualisationSection rendu par /conformite ;
    # toute apparition de `navigate(` ou `<Link to=` vers une route hors
    # /conformite trahirait un menu fantôme.
    assert "navigate(" not in ui_src or "/conformite" in ui_src
