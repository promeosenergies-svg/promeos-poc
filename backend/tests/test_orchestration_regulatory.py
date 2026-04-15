"""
Tests structurels pour le Regulatory Analyst (P1).
Aucune API key requise — pas d'appel SDK.
"""

from __future__ import annotations

import anyio
import pytest


# --- Module imports -------------------------------------------------------


def test_regulatory_module_imports():
    from orchestration.agents.regulatory import (
        REGULATORY_ALLOWED_TOOLS,
        REGULATORY_DISALLOWED_TOOLS,
        SCOPE_PROMPTS,
        SYSTEM_PROMPT,
        find_active_at_date,
        list_sections,
        read_section,
        run_regulatory_audit,
    )

    assert callable(run_regulatory_audit)
    # 3 MCP tools attendus
    assert list_sections is not None
    assert read_section is not None
    assert find_active_at_date is not None
    # Doctrine PROMEOS dans le system prompt
    assert "30.85" in SYSTEM_PROMPT  # accise T1 LF 2026
    assert "20.80" in SYSTEM_PROMPT  # CTA gaz formule additive
    assert "1/08/2025" in SYSTEM_PROMPT  # césure triple
    assert "ParameterStore" in SYSTEM_PROMPT
    assert set(SCOPE_PROMPTS.keys()) == {
        "audit-coherence",
        "audit-cesures",
        "audit-tariff",
    }
    # Read-only strict
    forbidden = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
    assert not forbidden.intersection(set(REGULATORY_ALLOWED_TOOLS))
    assert forbidden.issubset(set(REGULATORY_DISALLOWED_TOOLS))
    # Bash interdit aussi (Regulatory ne lance pas de commandes shell)
    assert "Bash" in REGULATORY_DISALLOWED_TOOLS


def test_regulatory_scope_validation_rejects_unknown():
    from orchestration.agents.regulatory import run_regulatory_audit

    with pytest.raises(ValueError, match="Scope inconnu"):
        anyio.run(lambda: run_regulatory_audit("nope"))


# --- MCP tools (in-process, sans appel SDK) -------------------------------


def test_mcp_tool_list_sections():
    from orchestration.agents.regulatory import list_sections

    result = anyio.run(lambda: list_sections.handler({}))
    assert "content" in result
    text = result["content"][0]["text"]
    # Doit mentionner les sections clés du YAML PROMEOS
    assert "turpe" in text
    assert "cta" in text
    assert "accise_elec" in text
    assert "atrd_gaz" in text or "atrd7_gaz_tiers" in text
    assert "Sections trouvées" in text


def test_mcp_tool_read_section_existing():
    from orchestration.agents.regulatory import read_section

    result = anyio.run(lambda: read_section.handler({"section_name": "cta"}))
    assert "content" in result
    text = result["content"][0]["text"]
    assert "cta" in text
    assert "taux_pct" in text or "elec" in text  # contenu réel de la section


def test_mcp_tool_read_section_missing():
    from orchestration.agents.regulatory import read_section

    result = anyio.run(lambda: read_section.handler({"section_name": "ne_sait_quoi"}))
    assert result.get("isError") is True
    assert "introuvable" in result["content"][0]["text"].lower()


def test_mcp_tool_find_active_at_date_cesure_triple():
    """Césure 1/08/2025 : TURPE 7 doit devenir actif."""
    from orchestration.agents.regulatory import find_active_at_date

    result = anyio.run(lambda: find_active_at_date.handler({"target_date": "2025-08-01"}))
    assert "content" in result
    text = result["content"][0]["text"]
    assert "2025-08-01" in text
    assert "turpe" in text  # TURPE 7 actif


def test_mcp_tool_find_active_at_date_invalid_format():
    from orchestration.agents.regulatory import find_active_at_date

    result = anyio.run(lambda: find_active_at_date.handler({"target_date": "01/08/2025"}))
    assert result.get("isError") is True


# --- CLI registry ---------------------------------------------------------


def test_cli_registry_contains_regulatory():
    from orchestration.cli import AGENTS_REGISTRY

    assert "regulatory" in AGENTS_REGISTRY
    info = AGENTS_REGISTRY["regulatory"]
    assert info["status"] == "active"
    assert info["write_access"] is False
    assert info["default_scope"] == "audit-coherence"
    assert "audit-cesures" in info["scopes"]
