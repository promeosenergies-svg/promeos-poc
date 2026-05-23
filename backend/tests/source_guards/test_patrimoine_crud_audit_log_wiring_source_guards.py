"""
PROMEOS — Source-guard P0-A 2026-05-23 : chaque PATCH/DELETE de routes/patrimoine_crud.py
doit contenir un appel à `log_patrimoine_change`. Empêche toute régression future
qui ré-introduirait un setattr+commit silencieux.

Anti-pattern verrouillé :
    @router.patch(...)
    def update_x():
        ...
        setattr(x, field, value)
        db.commit()      # ❌ aucun audit log
        return ...

Pattern attendu :
    @router.patch(...)
    def update_x():
        ...
        setattr(x, field, value)
        db.flush()
        log_patrimoine_change(db, ...)   # ✅ audit log wired
        db.commit()
        return ...
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
    """Retourne 'patch'/'delete'/etc. si le décorateur est @router.<method>."""
    if isinstance(decorator, ast.Call):
        target = decorator.func
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "router":
            return target.attr
    return None


def _contains_call(node: ast.AST, func_name: str) -> bool:
    """Vrai si l'AST contient un appel `func_name(...)` (au top ou imbriqué)."""
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


def _mutating_endpoints(tree: ast.Module):
    """Itère sur (function_node, http_method) pour chaque PATCH/DELETE/POST CRUD."""
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            method = _decorator_method(deco)
            if method in {"patch", "delete"}:
                yield node, method


def test_every_patch_delete_calls_log_patrimoine_change(crud_ast):
    """Chaque PATCH/DELETE de patrimoine_crud doit invoquer log_patrimoine_change."""
    missing = []
    for func, http_method in _mutating_endpoints(crud_ast):
        if not _contains_call(func, "log_patrimoine_change"):
            missing.append(f"{http_method.upper()} {func.name}")
    assert not missing, "Les endpoints suivants mutent patrimoine sans appeler log_patrimoine_change :\n" + "\n".join(
        f"  - {m}" for m in missing
    )


def test_no_swallow_recompute_in_crud_sites(crud_ast):
    """PATCH /sites/{id} ne doit plus contenir le pattern try/except qui log un warning
    sans re-raise. P0-A 2026-05-23 : exception → HTTP 500 explicite + rollback."""

    target_func = None
    for func, http_method in _mutating_endpoints(crud_ast):
        if http_method == "patch" and func.name == "update_site_crud":
            target_func = func
            break
    assert target_func is not None, "update_site_crud introuvable dans patrimoine_crud.py"

    # Détection anti-pattern : try/except qui contient un warning et PAS de raise
    for try_node in ast.walk(target_func):
        if not isinstance(try_node, ast.Try):
            continue
        for handler in try_node.handlers:
            has_raise = any(isinstance(n, ast.Raise) for n in ast.walk(handler))
            has_warning = any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "warning"
                for n in ast.walk(handler)
            )
            assert not (has_warning and not has_raise), (
                "update_site_crud contient un try/except qui log un warning sans re-raise "
                "(anti-pattern : swallow + conformité stale silencieuse)."
            )
