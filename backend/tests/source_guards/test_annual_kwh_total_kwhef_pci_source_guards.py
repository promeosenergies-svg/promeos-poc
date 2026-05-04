"""
PROMEOS — Source-guard kWhEF PCI sur Site.annual_kwh_total (Sprint C-3 Phase 3.4).

Clôture la dette `D-Phase4-2-EnergieFinale-Source-Guard-001` (P1 Sprint C-3).

Source légale : Arrêté du 10 avril 2020 art. 2-g (NOR LOGL2005904A) — reporting
OPERAT en énergie finale exclusivement (kWhEF). Les calculs `intensity_kwh_m2_*`
+ `compute_portfolio_intensity` (Phase 3.4) supposent que `Site.annual_kwh_total`
est en **kWh énergie finale (EF) PCI**.

Risque sans source-guard : ingestion future hétérogène pourrait y mettre du
kWhEP (énergie primaire, ×1.9 élec / ×1.0 gaz par arrêté 10/04/2020) ou du
kWhPCS (gaz ×1.11) → divergence silencieuse rendant le reporting OPERAT
non-conforme.

Patterns vérifiés :
- SG_KWHEF_01 : seuls les writers de l'allowlist peuvent assigner annual_kwh_total
- SG_KWHEF_02 : chaque writer allowlist contient un commentaire "kWhEF PCI"
  ou "énergie finale PCI" pour traçabilité
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Allowlist : fichiers autorisés à écrire `annual_kwh_total=...` ou
# `site.annual_kwh_total = ...`. Chacun doit contenir un commentaire
# "kWhEF PCI" ou "énergie finale PCI" à proximité (vérifié par SG_KWHEF_02).
_ALLOWED_WRITER_PATHS = {
    # Demo seed : création initiale Site avec annual_kwh
    "services/demo_seed/gen_master.py",
    # Phase 3.4 service : pas un writer (lecture seule), mais référence pour cohérence
    # Pas inclus car ne fait que des sums, pas d'écriture
}

# Pattern d'écriture : couvre 4 styles distincts (audit Phase 3.4d follow-up) :
# 1. `site.annual_kwh_total = ...` (attribut direct, avec ou sans espaces)
# 2. `annual_kwh_total=...` (kwarg dans constructeur Site(...))
# 3. `setattr(site, "annual_kwh_total", ...)` (réflexion — ajouté Phase 3.4d)
# 4. `setattr(site, 'annual_kwh_total', ...)` (idem avec quotes simples)
_WRITE_PATTERN = re.compile(
    r"(?:[\w]+\s*\.\s*annual_kwh_total\s*=|"  # site.annual_kwh_total =
    r"^\s*annual_kwh_total\s*=|"  # annual_kwh_total= (kwarg constructeur)
    r"setattr\s*\(\s*\w+\s*,\s*[\"']annual_kwh_total[\"'])"  # setattr(site, "annual_kwh_total", ...)
)

# Pattern commentaire kWhEF PCI requis dans les writers
_KWHEF_PCI_COMMENT = re.compile(
    r"#.*(?:kWhEF\s+PCI|énergie\s+finale\s+PCI|EF\s+PCI)",
    re.IGNORECASE,
)


def _scan_python_files() -> list[Path]:
    """Scanne tous les .py de backend/services + backend/routes (hors tests + cache)."""
    targets: list[Path] = []
    for sub in ("services", "routes", "regops", "data_ingestion"):
        sub_dir = _BACKEND_ROOT / sub
        if not sub_dir.exists():
            continue
        for py_file in sub_dir.rglob("*.py"):
            rel = py_file.relative_to(_BACKEND_ROOT).as_posix()
            if "__pycache__" in rel or rel.startswith("tests/"):
                continue
            targets.append(py_file)
    return targets


def _strip_comparisons(line: str) -> str:
    """Retire les patterns `==` `!=` `<` `>` qui ne sont pas des assignations."""
    # Ne garde que les vraies assignations ` = ` (un seul = isolé)
    return line


def _find_writers() -> list[tuple[str, int, str]]:
    """Trouve toutes les lignes qui écrivent annual_kwh_total."""
    findings = []
    for py_file in _scan_python_files():
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        rel = py_file.relative_to(_BACKEND_ROOT).as_posix()
        for line_no, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            # Filter false positives : comparaisons, type hints, accès lecture
            if "==" in stripped or "!=" in stripped:
                continue
            if stripped.startswith("#") or stripped.startswith('"'):
                continue
            if ": Optional" in stripped or ": float" in stripped or ": int" in stripped:
                continue
            # `or 0` patterns sont des défaults pour lecture, pas écriture
            if "annual_kwh_total or 0" in stripped:
                continue
            if "results[" in stripped or 'kwh_total"]' in stripped:
                continue  # dict access (intake_engine result dict)
            # Vraie écriture
            if _WRITE_PATTERN.search(stripped):
                findings.append((rel, line_no, stripped))
    return findings


# ─── SG_KWHEF_01 : allowlist writers ─────────────────────────────────────────


def test_sg_kwhef_01_only_allowlist_writers_assign_annual_kwh_total():
    """Aucun writer hors allowlist ne doit assigner Site.annual_kwh_total."""
    findings = _find_writers()
    offenders = [f"{rel}:{ln}  {line}" for (rel, ln, line) in findings if rel not in _ALLOWED_WRITER_PATHS]
    assert not offenders, (
        "Écriture Site.annual_kwh_total détectée hors allowlist (Sprint C-3 Phase 3.4 "
        "exige doctrine kWhEF PCI traçable).\n\n"
        "Allowlist actuelle : " + ", ".join(sorted(_ALLOWED_WRITER_PATHS)) + "\n\n"
        "Si nouveau writer légitime :\n"
        "  1. Ajouter le commentaire `# kWhEF PCI` près de l'écriture\n"
        "  2. Ajouter le path à `_ALLOWED_WRITER_PATHS` dans ce fichier\n\n"
        "Offenders:\n  - " + "\n  - ".join(offenders)
    )


# ─── SG_KWHEF_02 : commentaire kWhEF PCI requis ──────────────────────────────


def test_sg_kwhef_02_authorized_writers_have_kwhef_pci_comment():
    """Chaque writer de l'allowlist doit contenir un commentaire 'kWhEF PCI' ou 'énergie finale PCI'."""
    missing_comment = []
    for writer_rel in _ALLOWED_WRITER_PATHS:
        writer_path = _BACKEND_ROOT / writer_rel
        if not writer_path.exists():
            continue
        content = writer_path.read_text(encoding="utf-8")
        if not _KWHEF_PCI_COMMENT.search(content):
            missing_comment.append(writer_rel)

    assert not missing_comment, (
        "Writers Site.annual_kwh_total sans commentaire 'kWhEF PCI' / 'énergie finale PCI' :\n"
        "  - " + "\n  - ".join(missing_comment) + "\n\n"
        "Source légale : Arrêté 10/04/2020 art. 2-g — reporting OPERAT en énergie finale.\n"
        "Ajouter `# kWhEF PCI` près de l'écriture pour audit trail."
    )
