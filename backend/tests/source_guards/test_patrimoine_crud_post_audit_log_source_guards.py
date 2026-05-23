"""
PROMEOS — Source-guard P0-B 2026-05-23 : chaque POST création de patrimoine_crud.py
doit contenir un appel à `log_patrimoine_change`. Complète le guard P0-A
qui couvrait déjà PATCH/DELETE.

Patrimoine entièrement audité : aucun create silencieux possible.
"""

from __future__ import annotations

import ast
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


CRUD_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "routes",
    "patrimoine_crud.py",
)


def _decorator_method(decorator: ast.expr) -> str | None:
    """Retourne 'post'/'patch'/etc. si le décorateur est @router.<method>."""
    if isinstance(decorator, ast.Call):
        target = decorator.func
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "router"
        ):
            return target.attr
    return None


def _contains_call(node: ast.AST, func_name: str) -> bool:
    """Vrai si l'AST contient un appel `func_name(...)`."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            target = sub.func
            if isinstance(target, ast.Name) and target.id == func_name:
                return True
            if isinstance(target, ast.Attribute) and target.attr == func_name:
                return True
    return False


@pytest.fixture(scope="module")
def crud_ast():
    with open(CRUD_FILE, "r", encoding="utf-8") as f:
        source = f.read()
    return ast.parse(source, filename=CRUD_FILE)


def _post_endpoints(tree: ast.Module):
    """Itère sur les fonctions décorées @router.post(...)."""
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if _decorator_method(deco) == "post":
                yield node


def test_every_post_calls_log_patrimoine_change(crud_ast):
    """Chaque POST création de patrimoine_crud doit invoquer log_patrimoine_change."""
    missing = []
    for func in _post_endpoints(crud_ast):
        if not _contains_call(func, "log_patrimoine_change"):
            missing.append(f"POST {func.name}")
    assert not missing, (
        "Les endpoints POST suivants créent du patrimoine sans appeler log_patrimoine_change :\n"
        + "\n".join(f"  - {m}" for m in missing)
    )


def test_get_endpoints_do_not_call_log_patrimoine_change(crud_ast):
    """GET ne doit jamais appeler log_patrimoine_change (read-only sémantique)."""
    forbidden = []
    for node in crud_ast.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if _decorator_method(deco) == "get":
                if _contains_call(node, "log_patrimoine_change"):
                    forbidden.append(f"GET {node.name}")
    assert not forbidden, (
        "Les endpoints GET suivants appellent log_patrimoine_change (anti-pattern read-only) :\n"
        + "\n".join(f"  - {m}" for m in forbidden)
    )
