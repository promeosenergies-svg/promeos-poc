"""
PROMEOS — Source-guards lifecycle KB items (audit KB 2026-05-20).

Verrouille les invariants doctrinaux de `docs/kb/items/` (items validés) afin
qu'aucune régression silencieuse ne ré-introduise un item sans status, sans
confidence suffisante, ou — pour les règles — sans logique d'apply câblée.

Doctrine source : `docs/kb/README.md` ("Items in items/ folder MUST have
status=validated") + `kb_promote_item.py` (validated MUST have confidence>=medium
+ sources non vides + tags non vides).

Patterns vérifiés :
- SG_KB_LIFECYCLE_01 : tout item dans `docs/kb/items/` a `status: validated`
- SG_KB_LIFECYCLE_02 : confidence ∈ {medium, high} (pas de `low` validé)
- SG_KB_LIFECYCLE_03 : sources non vides avec au minimum `doc_id` ou `label`
- SG_KB_LIFECYCLE_04 : tags non vides (au moins une catégorie remplie)
- SG_KB_RULE_LOGIC_05 : si type=rule → `logic.when` ET `logic.then.outputs` non vides
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ITEMS_DIR = PROJECT_ROOT / "docs" / "kb" / "items"

VALID_CONFIDENCES = {"medium", "high"}


def _items() -> list[Path]:
    return sorted(ITEMS_DIR.glob("**/*.yaml"))


def _load(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), f"{path.name}: YAML root is not a dict"
    return data


_ITEM_PATHS = _items()
_IDS = [str(p.relative_to(ITEMS_DIR)) for p in _ITEM_PATHS]


@pytest.mark.parametrize("path", _ITEM_PATHS, ids=_IDS)
def test_sg_kb_item_status_validated(path: Path) -> None:
    """SG_KB_LIFECYCLE_01 — items/ ⇒ status: validated."""
    item = _load(path)
    assert item.get("status") == "validated", (
        f"{path.name}: status={item.get('status')!r}, expected 'validated' "
        f"(use backend/scripts/kb_fix_status.py to repair)"
    )


@pytest.mark.parametrize("path", _ITEM_PATHS, ids=_IDS)
def test_sg_kb_item_confidence_medium_or_high(path: Path) -> None:
    """SG_KB_LIFECYCLE_02 — confidence ∈ {medium, high}."""
    item = _load(path)
    conf = item.get("confidence")
    assert conf in VALID_CONFIDENCES, (
        f"{path.name}: confidence={conf!r}, expected one of {sorted(VALID_CONFIDENCES)}"
    )


@pytest.mark.parametrize("path", _ITEM_PATHS, ids=_IDS)
def test_sg_kb_item_sources_present(path: Path) -> None:
    """SG_KB_LIFECYCLE_03 — sources non vides avec doc_id ou label."""
    item = _load(path)
    sources = item.get("sources") or []
    assert sources, f"{path.name}: sources list is empty"
    for i, src in enumerate(sources):
        assert isinstance(src, dict), f"{path.name}: sources[{i}] is not a dict"
        assert src.get("doc_id") or src.get("label"), (
            f"{path.name}: sources[{i}] has neither doc_id nor label"
        )


@pytest.mark.parametrize("path", _ITEM_PATHS, ids=_IDS)
def test_sg_kb_item_tags_at_least_one_category(path: Path) -> None:
    """SG_KB_LIFECYCLE_04 — au moins une catégorie de tags remplie."""
    item = _load(path)
    tags = item.get("tags") or {}
    assert any(tags.get(cat) for cat in ("energy", "segment", "asset", "reg", "granularity", "naf")), (
        f"{path.name}: all tag categories empty"
    )


@pytest.mark.parametrize("path", _ITEM_PATHS, ids=_IDS)
def test_sg_kb_rule_has_apply_logic(path: Path) -> None:
    """SG_KB_RULE_LOGIC_05 — type=rule ⇒ logic.when ET logic.then.outputs non vides."""
    item = _load(path)
    if item.get("type") != "rule":
        pytest.skip("not a rule item")
    logic = item.get("logic") or {}
    assert logic.get("when"), f"{path.name}: rule item without logic.when"
    outputs = (logic.get("then") or {}).get("outputs") or []
    assert outputs, f"{path.name}: rule item without logic.then.outputs"
