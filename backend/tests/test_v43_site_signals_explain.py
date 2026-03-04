"""
PROMEOS V43 — Tests: Explainable Site Signals
Backward compat V42 + new fields: rules_applied, reasons_fr,
recommended_next_step, recommended_cta, top_missing_fields
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine
from models.base import Base

Base.metadata.create_all(bind=engine)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Backward compatibility — V42 fields still present
# ══════════════════════════════════════════════════════════════════════════════


class TestV42BackwardCompat:
    """V42 response shape must remain intact."""

    def test_v42_top_level_fields(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        assert "sites" in data
        assert "total_sites" in data
        assert "counts" in data
        assert "uncovered_probable" in data
        assert "incomplete_data" in data

    def test_v42_site_fields_preserved(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        for site in data["sites"]:
            assert "site_id" in site
            assert "site_nom" in site
            assert "signal" in site
            assert site["signal"] in ("assujetti_probable", "a_verifier", "non_concerne")
            assert "is_covered" in site
            assert "data_complete" in site
            assert "surface_tertiaire_m2" in site
            assert "nb_batiments" in site
            assert "efa_ids" in site

    def test_counts_sum_matches_total(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        total = sum(data["counts"].values())
        assert total == data["total_sites"]


# ══════════════════════════════════════════════════════════════════════════════
# 2. V43 new fields — explainability per site
# ══════════════════════════════════════════════════════════════════════════════


class TestV43ExplainFields:
    """Each site in response must have V43 explainability fields."""

    def test_signal_version_present(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        for site in data["sites"]:
            assert site["signal_version"] == "V1"

    def test_rules_applied_present_and_shaped(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        for site in data["sites"]:
            assert "rules_applied" in site
            assert isinstance(site["rules_applied"], list)
            assert len(site["rules_applied"]) >= 1
            for rule in site["rules_applied"]:
                assert "code" in rule
                assert "label_fr" in rule
                assert "ok" in rule
                assert isinstance(rule["ok"], bool)

    def test_rules_applied_has_surface_threshold(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        for site in data["sites"]:
            codes = [r["code"] for r in site["rules_applied"]]
            assert "surface_threshold" in codes

    def test_reasons_fr_present(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        for site in data["sites"]:
            assert "reasons_fr" in site
            assert isinstance(site["reasons_fr"], list)
            assert len(site["reasons_fr"]) >= 1
            for reason in site["reasons_fr"]:
                assert isinstance(reason, str)
                assert len(reason) > 0

    def test_missing_fields_present(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        for site in data["sites"]:
            assert "missing_fields" in site
            assert isinstance(site["missing_fields"], list)

    def test_recommended_next_step_valid(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        valid_steps = ("creer_efa", "completer_patrimoine", "aucune_action")
        for site in data["sites"]:
            assert "recommended_next_step" in site
            assert site["recommended_next_step"] in valid_steps

    def test_recommended_cta_shape(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        for site in data["sites"]:
            assert "recommended_cta" in site
            cta = site["recommended_cta"]
            if cta is not None:
                assert "label_fr" in cta
                assert "to" in cta
                assert isinstance(cta["label_fr"], str)
                assert cta["to"].startswith("/")


# ══════════════════════════════════════════════════════════════════════════════
# 3. V43 enriched summary
# ══════════════════════════════════════════════════════════════════════════════


class TestV43Summary:
    """Top-level response has enriched summary."""

    def test_top_missing_fields_present(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        assert "top_missing_fields" in data
        assert isinstance(data["top_missing_fields"], dict)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Determinism — same input, same output
# ══════════════════════════════════════════════════════════════════════════════


class TestV43Determinism:
    """Two identical calls must return identical reasons_fr."""

    def test_deterministic_reasons(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data1 = client.get("/api/tertiaire/site-signals").json()
        data2 = client.get("/api/tertiaire/site-signals").json()
        for s1, s2 in zip(data1["sites"], data2["sites"]):
            assert s1["reasons_fr"] == s2["reasons_fr"]
            assert s1["rules_applied"] == s2["rules_applied"]
            assert s1["recommended_next_step"] == s2["recommended_next_step"]


# ══════════════════════════════════════════════════════════════════════════════
# 5. Semantic coherence
# ══════════════════════════════════════════════════════════════════════════════


class TestV43SemanticCoherence:
    """Signals and explanations must be logically coherent."""

    def test_assujetti_probable_has_surface_rule_ok(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        for site in data["sites"]:
            if site["signal"] == "assujetti_probable":
                surface_rule = next(
                    (r for r in site["rules_applied"] if r["code"] == "surface_threshold"),
                    None,
                )
                assert surface_rule is not None
                assert surface_rule["ok"] is True

    def test_uncovered_probable_recommends_creer_efa(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        for site in data["sites"]:
            if site["signal"] == "assujetti_probable" and not site["is_covered"]:
                assert site["recommended_next_step"] == "creer_efa"
                assert site["recommended_cta"] is not None
                assert "wizard?site_id=" in site["recommended_cta"]["to"]

    def test_a_verifier_has_missing_fields(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        for site in data["sites"]:
            if site["signal"] == "a_verifier":
                assert not site["data_complete"]


# ══════════════════════════════════════════════════════════════════════════════
# 6. Source guards
# ══════════════════════════════════════════════════════════════════════════════


class TestV43SourceGuards:
    """Verify V43 code exists in service file."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        self.service_code = (Path(__file__).resolve().parent.parent / "services" / "tertiaire_service.py").read_text(
            encoding="utf-8"
        )

    def test_build_site_explanation_exists(self):
        assert "def _build_site_explanation" in self.service_code

    def test_signal_version_v1(self):
        assert '"V1"' in self.service_code or "'V1'" in self.service_code

    def test_rules_applied_in_service(self):
        assert "rules_applied" in self.service_code

    def test_reasons_fr_in_service(self):
        assert "reasons_fr" in self.service_code

    def test_recommended_next_step_in_service(self):
        assert "recommended_next_step" in self.service_code

    def test_top_missing_fields_in_response(self):
        assert "top_missing_fields" in self.service_code
