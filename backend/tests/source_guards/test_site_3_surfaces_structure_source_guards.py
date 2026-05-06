"""
PROMEOS — Source guards Site 3 surfaces distinctes (Sprint C-7 Phase 7.1, clôture D-Phase4-2-Operat-Surfaces-3-Distinct).

Anti-régression cardinal post-livraison Phase 7.1 :
- SG_SITE_3_SURFACES_01 : Site model expose 3 cols surfaces distinctes (surface_m2 + tertiaire_area_m2 + s_ce_m2)
- SG_SITE_3_SURFACES_02 : 3 cols sont Float (vs Integer — précision décimale obligatoire)
- SG_SITE_3_SURFACES_03 : 3 cols nullable (pas de NOT NULL imposé MVP — migration progressive sites legacy)

Si quelqu'un retire ou renomme une des 3 cols cardinaux, ces SG flaggent fail-fast.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_SITE_MODEL_PATH = _BACKEND_ROOT / "models" / "site.py"


def test_sg_site_3_surfaces_01_three_distinct_cols_present():
    """SG_SITE_3_SURFACES_01 cardinal : Site model contient 3 cols surfaces distinctes.

    Doctrine clôture D-Phase4-2-Operat-Surfaces-3-Distinct-001 (Sprint C-2 → C-7 P7.1) :
    - surface_m2 = SDP (Surface De Plancher) — Code construction art. R111-22
    - tertiaire_area_m2 = surface tertiaire assujettie OPERAT (sous-périmètre SDP)
    - s_ce_m2 = Surface CE OPERAT — Arrêté 10/04/2020 art. 2-j
    """
    content = _SITE_MODEL_PATH.read_text(encoding="utf-8")

    cardinal_cols = ["surface_m2", "tertiaire_area_m2", "s_ce_m2"]
    missing = [col for col in cardinal_cols if f"{col} = Column" not in content]
    assert not missing, (
        f"Cols Site cardinaux manquants : {missing}.\n"
        "Sprint C-7 Phase 7.1 (clôture D-Phase4-2-Operat-Surfaces-3-Distinct-001) requiert "
        "ces 3 cols distinctes (Arrêté 10/04/2020 art. 2-j).\n"
        "S_CE ≠ SDP ≠ tertiaire_area_m2 — voir docstring site.py + tracker dette."
    )


def test_sg_site_3_surfaces_02_all_float_type():
    """SG_SITE_3_SURFACES_02 : 3 cols typées Float (précision décimale, pas Integer).

    Surfaces architecturales typiquement décimales (ex: 1234.56 m²). Integer = perte précision.
    """
    content = _SITE_MODEL_PATH.read_text(encoding="utf-8")

    # Pattern : `<col_name> = Column(Float, ...)`
    cardinal_cols = ["surface_m2", "tertiaire_area_m2", "s_ce_m2"]
    for col in cardinal_cols:
        pattern = rf"{col}\s*=\s*Column\(\s*Float\b"
        assert re.search(pattern, content), (
            f"SG_SITE_3_SURFACES_02 : col `{col}` doit être typée Float (vs Integer).\n"
            "Précision décimale obligatoire pour surfaces architecturales (ex: 1234.56 m²)."
        )


def test_sg_site_3_surfaces_03_all_nullable():
    """SG_SITE_3_SURFACES_03 : 3 cols nullable=True (migration progressive sites legacy).

    Pas de NOT NULL imposé MVP — sites pré-Phase 7.1 ont s_ce_m2 NULL légitimement.
    """
    content = _SITE_MODEL_PATH.read_text(encoding="utf-8")

    # Pattern : `<col_name> = Column(Float, nullable=True, ...)` ou `<col_name> = Column(Float, comment=...)`
    # surface_m2 dans models/site.py n'a pas nullable explicite (default = nullable=True SQLAlchemy)
    # tertiaire_area_m2 + s_ce_m2 ont nullable=True explicite
    for col in ["tertiaire_area_m2", "s_ce_m2"]:
        pattern = rf"{col}\s*=\s*Column\([^)]*nullable\s*=\s*True"
        assert re.search(pattern, content), (
            f"SG_SITE_3_SURFACES_03 : col `{col}` doit être nullable=True explicite.\n"
            "MVP autorise sites legacy avec col=NULL (migration progressive)."
        )

    # surface_m2 (SDP) : pattern Float() sans NOT NULL imposé (default nullable=True OK)
    pattern_surface = r"surface_m2\s*=\s*Column\(Float[^)]*\)"
    match = re.search(pattern_surface, content)
    assert match, "SG_SITE_3_SURFACES_03 : col surface_m2 introuvable avec Column(Float...)."
    # Vérifier qu'il n'y a PAS nullable=False explicite
    assert "nullable=False" not in match.group(0), (
        "SG_SITE_3_SURFACES_03 : surface_m2 ne doit pas avoir nullable=False (MVP)."
    )
