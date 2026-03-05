"""
Tests — AI Client (Playbook 2.1).
Verifies stub mode, live mode (mocked), and fallback on error.
No real API tokens consumed.
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.fast


class TestAIClientStubMode:
    """Without AI_API_KEY, client should return stubs."""

    def test_stub_mode_when_no_key(self):
        """Client should be in stub mode without API key."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AI_API_KEY", None)
            # Reimport to get fresh singleton
            import ai_layer.client as mod
            client = mod.AIClient()
            assert client.stub_mode is True

    def test_stub_response_contains_marker(self):
        """Stub response should contain [AI Stub Mode] marker."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AI_API_KEY", None)
            import ai_layer.client as mod
            client = mod.AIClient()
            result = client.complete("system", "user prompt")
            assert "[AI Stub Mode]" in result

    def test_stub_includes_prompt_preview(self):
        """Stub response should include a preview of the prompt."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AI_API_KEY", None)
            import ai_layer.client as mod
            client = mod.AIClient()
            result = client.complete("system", "analyse du site Lyon")
            assert "analyse du site Lyon" in result


class TestAIClientLiveMode:
    """With AI_API_KEY, client should call Claude API (mocked)."""

    def test_live_mode_when_key_present(self):
        """Client should NOT be in stub mode with API key."""
        with patch.dict(os.environ, {"AI_API_KEY": "test-key-123"}):
            import ai_layer.client as mod
            client = mod.AIClient()
            assert client.stub_mode is False

    @patch("ai_layer.client.httpx.post")
    def test_live_call_format(self, mock_post):
        """Live call should use correct API format."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "content": [{"text": "AI response text"}]
        }
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {"AI_API_KEY": "test-key-123"}):
            import ai_layer.client as mod
            client = mod.AIClient()
            result = client.complete("system prompt", "user prompt")

        assert result == "AI response text"
        call_kwargs = mock_post.call_args
        assert "api.anthropic.com" in call_kwargs[0][0]
        headers = call_kwargs[1]["headers"]
        assert headers["x-api-key"] == "test-key-123"
        body = call_kwargs[1]["json"]
        assert body["system"] == "system prompt"
        assert body["messages"][0]["content"] == "user prompt"

    @patch("ai_layer.client.httpx.post")
    def test_fallback_on_api_error(self, mock_post):
        """On API error, should fallback to stub instead of crashing."""
        mock_post.side_effect = Exception("Connection refused")

        with patch.dict(os.environ, {"AI_API_KEY": "test-key-123"}):
            import ai_layer.client as mod
            client = mod.AIClient()
            result = client.complete("system", "user prompt")

        assert "[AI Fallback]" in result
        assert "Connection refused" in result or "échoué" in result

    @patch("ai_layer.client.httpx.post")
    def test_max_tokens_passed(self, mock_post):
        """max_tokens parameter should be forwarded to API."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"content": [{"text": "ok"}]}
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {"AI_API_KEY": "test-key-123"}):
            import ai_layer.client as mod
            client = mod.AIClient()
            client.complete("sys", "user", max_tokens=2048)

        body = mock_post.call_args[1]["json"]
        assert body["max_tokens"] == 2048


class TestAgentStubs:
    """Verify agents work in stub mode."""

    def test_regops_explainer_stub_has_fields(self):
        """regops_explainer._stub_response should return required fields."""
        from ai_layer.agents.regops_explainer import _stub_response

        class FakeSite:
            nom = "Site Test"
            surface_m2 = 1000
            statut_decret_tertiaire = "CONFORME"
            statut_bacs = "A_RISQUE"
            risque_financier_euro = 5000

        result = _stub_response(FakeSite())
        assert "brief" in result
        assert "sources_used" in result
        assert "confidence" in result
        assert result["mode"] == "stub"

    def test_exec_brief_stub_has_fields(self):
        """exec_brief_agent._stub_response should return required fields."""
        from ai_layer.agents.exec_brief_agent import _stub_response

        data = {"org_name": "Test Org", "total_sites": 5, "total_surface_m2": 10000, "total_risk_eur": 25000}
        result = _stub_response(data)
        assert "executive_summary" in result
        assert "key_metrics" in result
        assert result["mode"] == "stub"
