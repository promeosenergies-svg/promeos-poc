"""
PROMEOS Referentiel — Tests for watchlist YAML validation.
Checks: YAML loads, ids unique, HTTPS only, whitelisted domains, enums, tags.
"""

import sys
import os
import re
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import yaml

WATCHLIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "referential", "sources_watchlist_24m.yaml"
)


@pytest.fixture(scope="module")
def watchlist():
    """Load the watchlist YAML once for all tests."""
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ========================================
# Tests
# ========================================


def test_yaml_loads(watchlist):
    """YAML file loads without errors."""
    assert watchlist is not None
    assert isinstance(watchlist, dict)


def test_top_level_keys(watchlist):
    """Required top-level keys present."""
    for key in ("version", "window", "allowed_domains", "sources"):
        assert key in watchlist, f"Missing key: {key}"


def test_window_format(watchlist):
    """Window has start and end dates in YYYY-MM-DD format."""
    window = watchlist["window"]
    assert "start" in window
    assert "end" in window
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", window["start"])
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", window["end"])
    assert window["start"] < window["end"]


def test_sources_non_empty(watchlist):
    """At least 20 sources configured."""
    sources = watchlist["sources"]
    assert len(sources) >= 20, f"Expected >=20 sources, got {len(sources)}"


def test_ids_unique(watchlist):
    """All source ids are unique."""
    ids = [s["id"] for s in watchlist["sources"]]
    assert len(ids) == len(set(ids)), f"Duplicate ids found: {[x for x in ids if ids.count(x) > 1]}"


def test_id_format(watchlist):
    """All ids match [a-z0-9_]+ pattern."""
    for src in watchlist["sources"]:
        sid = src["id"]
        assert re.match(r"^[a-z0-9_]+$", sid), f"Invalid id format: {sid}"


def test_all_urls_https(watchlist):
    """All source URLs use HTTPS."""
    for src in watchlist["sources"]:
        url = src.get("url", "")
        assert url.startswith("https://"), f"{src['id']}: URL not HTTPS: {url}"


def test_domains_whitelisted(watchlist):
    """All source URL domains are in allowed_domains."""
    allowed = set(watchlist["allowed_domains"])
    for src in watchlist["sources"]:
        url = src["url"]
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        domain_ok = any(domain == d or domain.endswith("." + d) for d in allowed)
        assert domain_ok, f"{src['id']}: domain '{domain}' not in allowed_domains"


def test_required_fields(watchlist):
    """Each source has all required fields."""
    required = ("id", "category", "energy", "authority", "url", "expected_type", "description", "tags")
    for src in watchlist["sources"]:
        for field in required:
            assert field in src, f"{src.get('id', '?')}: missing field '{field}'"


def test_category_enum(watchlist):
    """Category is tarif_reseau or taxe."""
    for src in watchlist["sources"]:
        assert src["category"] in ("tarif_reseau", "taxe"), f"{src['id']}: invalid category '{src['category']}'"


def test_energy_enum(watchlist):
    """Energy is electricite, gaz, or multi."""
    for src in watchlist["sources"]:
        assert src["energy"] in ("electricite", "gaz", "multi"), f"{src['id']}: invalid energy '{src['energy']}'"


def test_authority_enum(watchlist):
    """Authority is CRE, Legifrance, BOFiP, or impots.gouv."""
    for src in watchlist["sources"]:
        assert src["authority"] in ("CRE", "Legifrance", "BOFiP", "impots.gouv"), (
            f"{src['id']}: invalid authority '{src['authority']}'"
        )


def test_tags_non_empty(watchlist):
    """Each source has at least one tag."""
    for src in watchlist["sources"]:
        assert len(src["tags"]) > 0, f"{src['id']}: tags must be non-empty"


def test_date_hint_format(watchlist):
    """date_hint (when present) is YYYY-MM-DD."""
    for src in watchlist["sources"]:
        dh = src.get("date_hint")
        if dh:
            assert re.match(r"^\d{4}-\d{2}-\d{2}$", dh), f"{src['id']}: bad date_hint '{dh}'"


def test_coverage_tarifs(watchlist):
    """We cover TURPE, ATRD, ATRT, ATS regulations."""
    regulations = {src.get("regulation") for src in watchlist["sources"]}
    for reg in ("TURPE6", "TURPE7", "ATRD7", "ATRT8", "ATS3"):
        assert reg in regulations, f"Missing regulation coverage: {reg}"


def test_coverage_taxes(watchlist):
    """We cover CTA, CIBS, TVA, accise."""
    regulations = {src.get("regulation") for src in watchlist["sources"]}
    tags_all = set()
    for src in watchlist["sources"]:
        tags_all.update(src.get("tags", []))
    assert "CTA" in regulations, "Missing CTA"
    assert "CIBS" in regulations or "cibs" in tags_all, "Missing CIBS"
    assert "TVA" in regulations, "Missing TVA"
    assert "accise" in tags_all, "Missing accise"


def test_baseline_sources_exist(watchlist):
    """At least some sources are marked baseline=true."""
    baselines = [s for s in watchlist["sources"] if s.get("baseline")]
    assert len(baselines) >= 3, f"Expected >=3 baselines, got {len(baselines)}"


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
