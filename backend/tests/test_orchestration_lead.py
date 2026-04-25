"""
Tests structurels Lead Engineer (P2).
Aucune API key requise — les runs sont mockés pour éviter les appels SDK.
"""

from __future__ import annotations

from unittest.mock import patch

import anyio
import pytest


def test_lead_module_imports():
    from orchestration.agents.lead import LEAD_SYNTHESIS_SYSTEM_PROMPT, run_lead_audit

    assert callable(run_lead_audit)
    assert "CTO" in LEAD_SYNTHESIS_SYSTEM_PROMPT
    assert "P0" in LEAD_SYNTHESIS_SYSTEM_PROMPT


def test_lead_scope_validation_rejects_unknown():
    from orchestration.agents.lead import run_lead_audit

    with pytest.raises(ValueError, match="Scope inconnu"):
        anyio.run(lambda: run_lead_audit("nope"))


def _fake_result(status: str, scope: str, summary: str = "fake summary"):
    return {"status": status, "findings": [], "summary": summary, "scope": scope}


def test_lead_full_aggregates_green():
    """Scope full : QA source-guards + Regulatory audit-cesures, tous verts."""
    from orchestration.agents import lead

    async def _fake_qa(scope):
        assert scope == "source-guards"
        return _fake_result("green", scope, "0 violation source-guard")

    async def _fake_reg(scope):
        assert scope == "audit-cesures"
        return _fake_result("green", scope, "5/5 cesures OK")

    with patch.object(lead, "run_qa_audit", _fake_qa), patch.object(lead, "run_regulatory_audit", _fake_reg):
        result = anyio.run(lambda: lead.run_lead_audit("full"))

    assert result["status"] == "green"
    assert result["scope"] == "full"
    assert "qa_guardian" in result["sub_reports"]
    assert "regulatory" in result["sub_reports"]
    assert result["sub_reports"]["qa_guardian"]["status"] == "green"
    assert result["sub_reports"]["regulatory"]["status"] == "green"
    assert "0 violation" in result["summary"]
    assert "5/5 cesures" in result["summary"]


def test_lead_full_red_if_one_sub_red():
    """Scope full : si un sous-agent est rouge, le global est rouge."""
    from orchestration.agents import lead

    async def _fake_qa(scope):
        return _fake_result("green", scope)

    async def _fake_reg(scope):
        return _fake_result("red", scope, "3 P0 trouvés")

    with patch.object(lead, "run_qa_audit", _fake_qa), patch.object(lead, "run_regulatory_audit", _fake_reg):
        result = anyio.run(lambda: lead.run_lead_audit("full"))

    assert result["status"] == "red"  # un seul rouge suffit
    assert "3 P0" in result["summary"]


def test_lead_quick_skips_regulatory():
    """Scope quick : QA tests seulement, pas d'appel Regulatory (économie SDK)."""
    from orchestration.agents import lead

    qa_called_with = []

    async def _fake_qa(scope):
        qa_called_with.append(scope)
        return _fake_result("green", scope)

    async def _fake_reg(scope):
        raise AssertionError("Regulatory should NOT be called in quick scope")

    with patch.object(lead, "run_qa_audit", _fake_qa), patch.object(lead, "run_regulatory_audit", _fake_reg):
        result = anyio.run(lambda: lead.run_lead_audit("quick"))

    assert qa_called_with == ["tests"]
    assert "regulatory" not in result["sub_reports"]
    assert result["status"] == "green"


def test_cli_registry_contains_lead():
    from orchestration.cli import AGENTS_REGISTRY

    assert "lead" in AGENTS_REGISTRY
    info = AGENTS_REGISTRY["lead"]
    assert info["status"] == "active"
    assert info["write_access"] is False
    assert info["default_scope"] == "full"
    assert set(info["scopes"]) == {"full", "quick", "synthesis"}
