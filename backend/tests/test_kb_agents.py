"""
Tests KB Agents -- verifie que les 5 agents injectent le contexte KB.
"""

from pathlib import Path


AGENTS_DIR = Path(__file__).parent.parent / "ai_layer" / "agents"


class TestAllAgentsUseKB:
    """Phase 2.2 -- chaque agent appelle build_kb_prompt_section"""

    def test_regops_explainer_uses_kb(self):
        source = (AGENTS_DIR / "regops_explainer.py").read_text()
        assert "build_kb_prompt_section" in source

    def test_regops_recommender_uses_kb(self):
        source = (AGENTS_DIR / "regops_recommender.py").read_text()
        assert "build_kb_prompt_section" in source

    def test_data_quality_agent_uses_kb(self):
        source = (AGENTS_DIR / "data_quality_agent.py").read_text()
        assert "build_kb_prompt_section" in source

    def test_exec_brief_agent_uses_kb(self):
        source = (AGENTS_DIR / "exec_brief_agent.py").read_text()
        assert "build_kb_prompt_section" in source

    def test_reg_change_agent_uses_kb(self):
        source = (AGENTS_DIR / "reg_change_agent.py").read_text()
        assert "build_kb_prompt_section" in source

    def test_all_5_agents_counted(self):
        agent_files = [f for f in AGENTS_DIR.glob("*.py") if f.name != "__init__.py"]
        assert len(agent_files) == 5


class TestKBContextModule:
    """Verifie que le module kb_context est fonctionnel"""

    def test_import_kb_context(self):
        from ai_layer.kb_context import build_kb_prompt_section, kb_apply, kb_warnings

        assert callable(build_kb_prompt_section)
        assert callable(kb_apply)
        assert callable(kb_warnings)

    def test_kb_apply_returns_string(self):
        from ai_layer.kb_context import kb_apply

        result = kb_apply(domain="facturation")
        assert isinstance(result, str)

    def test_build_kb_prompt_section_returns_string(self):
        from ai_layer.kb_context import build_kb_prompt_section

        result = build_kb_prompt_section(domain="facturation")
        assert isinstance(result, str)
