"""
PROMEOS Referentiel — Tests for fetch pipeline (dry-run mode + normalizer + CRE extractor).
No real HTTP calls are made.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from scripts.referential.fetch_sources import fetch_source, fetch_all
from scripts.referential.normalize_text import html_to_markdown, extract_title
from scripts.referential.extract_cre_metadata import extract_cre_metadata, _normalize_french_date


# ========================================
# Normalize text tests
# ========================================

def test_html_to_markdown_basic():
    """Basic HTML is converted to text."""
    html = "<html><body><h1>Title</h1><p>Hello world</p></body></html>"
    md = html_to_markdown(html)
    assert "# Title" in md
    assert "Hello world" in md


def test_html_to_markdown_strips_scripts():
    """Script and style tags are stripped."""
    html = "<html><body><script>alert('xss')</script><p>Safe text</p><style>.x{}</style></body></html>"
    md = html_to_markdown(html)
    assert "alert" not in md
    assert "Safe text" in md
    assert ".x{}" not in md


def test_html_to_markdown_strips_nav():
    """Navigation elements are stripped."""
    html = "<html><body><nav>Menu items</nav><main><p>Content</p></main></body></html>"
    md = html_to_markdown(html)
    assert "Menu items" not in md
    assert "Content" in md


def test_html_to_markdown_headings():
    """Heading levels are preserved as markdown."""
    html = "<h1>H1</h1><h2>H2</h2><h3>H3</h3>"
    md = html_to_markdown(html)
    assert "# H1" in md
    assert "## H2" in md
    assert "### H3" in md


def test_extract_title():
    """Title extraction from HTML."""
    html = "<html><head><title>  Mon Titre  </title></head><body></body></html>"
    assert extract_title(html) == "Mon Titre"


def test_extract_title_missing():
    """No title returns None."""
    assert extract_title("<html><body>no title</body></html>") is None


# ========================================
# CRE metadata extractor tests
# ========================================

def test_cre_extract_deliberation_number():
    """Extracts deliberation number from CRE page."""
    html = '<div>Deliberation N° 2025-018 du 16 janvier 2025</div>'
    meta = extract_cre_metadata(html)
    assert meta.get("deliberation_number") == "2025-018"


def test_cre_extract_document_type_decision():
    """Detects Decision document type."""
    html = "<div>Cette décision fixe le tarif</div>"
    meta = extract_cre_metadata(html)
    assert meta["document_type"] == "Decision"


def test_cre_extract_document_type_projet():
    """Detects Projet document type."""
    html = "<div>Projet de modification des tarifs</div>"
    meta = extract_cre_metadata(html)
    assert meta["document_type"] == "Projet"


def test_cre_extract_energy_electricite():
    """Detects electricity energy."""
    html = "<div>tarif TURPE electricite</div>"
    meta = extract_cre_metadata(html)
    assert meta["energy_detected"] == "electricite"


def test_cre_extract_energy_gaz():
    """Detects gas energy."""
    html = "<div>tarif distribution de gaz naturel</div>"
    meta = extract_cre_metadata(html)
    assert meta["energy_detected"] == "gaz"


def test_cre_extract_energy_multi():
    """Detects multi energy when both present."""
    html = "<div>tarif electricite et gaz naturel</div>"
    meta = extract_cre_metadata(html)
    assert meta["energy_detected"] == "multi"


def test_cre_extract_pdf_url():
    """Extracts PDF link."""
    html = '<a href="/documents/test.pdf">Telecharger</a>'
    meta = extract_cre_metadata(html)
    assert meta["pdf_url"] == "https://www.cre.fr/documents/test.pdf"


def test_normalize_french_date():
    """French date normalization."""
    assert _normalize_french_date("16 janvier 2025") == "2025-01-16"
    assert _normalize_french_date("1 mars 2024") == "2024-03-01"
    assert _normalize_french_date("5 décembre 2026") == "2026-12-05"


def test_normalize_french_date_invalid():
    """Invalid French date returns None."""
    assert _normalize_french_date("not a date") is None
    assert _normalize_french_date("16 foobar 2025") is None


# ========================================
# Fetch dry-run tests
# ========================================

def test_fetch_source_dry_run():
    """Dry run returns dry_run_ok without downloading."""
    source = {
        "id": "test_source",
        "url": "https://www.cre.fr/test",
        "category": "tarif_reseau",
        "energy": "electricite",
        "authority": "CRE",
    }
    result = fetch_source(source, today="2025-01-01", dry_run=True)
    assert result["status"] == "dry_run_ok"
    assert result["source_id"] == "test_source"
    assert result["snapshot_path"] is None


def test_fetch_all_dry_run():
    """Dry run processes all sources without HTTP calls."""
    sources = [
        {"id": "src1", "url": "https://www.cre.fr/src1", "category": "tarif_reseau",
         "energy": "electricite", "authority": "CRE"},
        {"id": "src2", "url": "https://www.cre.fr/src2", "category": "tarif_reseau",
         "energy": "gaz", "authority": "CRE"},
        {"id": "src3", "url": "https://www.cre.fr/src3", "category": "taxe",
         "energy": "multi", "authority": "CRE"},
    ]
    results = fetch_all(sources, dry_run=True)
    assert len(results) == 3
    assert all(r["status"] == "dry_run_ok" for r in results)


def test_fetch_all_dry_run_skip_before_window():
    """Sources before window are skipped (non-baseline)."""
    sources = [
        {"id": "old_src", "url": "https://www.cre.fr/old", "date_hint": "2023-01-01",
         "category": "tarif_reseau", "energy": "electricite", "authority": "CRE"},
    ]
    results = fetch_all(sources, since="2024-02-01", dry_run=True)
    assert len(results) == 1
    assert results[0]["status"] == "skipped_before_window"


def test_fetch_all_dry_run_skip_after_window():
    """Sources after window are skipped."""
    sources = [
        {"id": "future_src", "url": "https://www.cre.fr/future", "date_hint": "2027-01-01",
         "category": "tarif_reseau", "energy": "electricite", "authority": "CRE"},
    ]
    results = fetch_all(sources, until="2026-02-10", dry_run=True)
    assert len(results) == 1
    assert results[0]["status"] == "skipped_after_window"


def test_fetch_all_dry_run_baseline_not_skipped():
    """Baseline sources are NOT skipped even if before window."""
    sources = [
        {"id": "baseline_src", "url": "https://www.cre.fr/baseline", "date_hint": "2023-01-01",
         "baseline": True, "category": "tarif_reseau", "energy": "gaz", "authority": "CRE"},
    ]
    results = fetch_all(sources, since="2024-02-01", dry_run=True)
    assert len(results) == 1
    assert results[0]["status"] == "dry_run_ok"


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
