"""Tests unitaires email_provider — Phase 2.B Sprint α-push.

Couvre :
- Success 201 → EmailResult(success=True, message_id=...)
- 4xx définitif (400/401/403/404) → success=False, no retry
- 5xx → retry × 2 puis silent fail
- 429 rate-limit → retry × 1
- Timeout / NetworkError → silent fail (no exception au caller)
- Payload format Brevo API v3 (sender / to / subject / htmlContent)
- Factory get_email_provider variants (brevo OK / missing key / unsupported)

Mock pattern : monkeypatch sur `httpx.post` (Q5 audit Phase 0.bis arbitrée
— pas de nouvelle dep `httpx_mock` / `responses`).
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.email_provider import (
    BrevoProvider,
    EmailResult,
    get_email_provider,
)


# ── Helpers ─────────────────────────────────────────────────────────


def _make_response(status_code: int, json_body: dict | None = None) -> MagicMock:
    """Construit un mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json = MagicMock(return_value=json_body or {})
    return resp


@pytest.fixture
def fast_backoff(monkeypatch):
    """Désactive le sleep backoff pour ne pas ralentir les tests retry."""
    monkeypatch.setattr(BrevoProvider, "_backoff_sleep", staticmethod(lambda _attempt: None))


@pytest.fixture
def provider():
    return BrevoProvider(api_key="test-key", from_email="noreply@test.io", from_name="Test")


# ── Tests BrevoProvider.send_email ──────────────────────────────────


class TestBrevoSendEmail:
    def test_send_email_success_201_returns_message_id(self, provider, monkeypatch):
        """201 + messageId → EmailResult(success=True)."""
        resp = _make_response(201, {"messageId": "<abc-123@brevo>"})
        monkeypatch.setattr("services.email_provider.httpx.post", MagicMock(return_value=resp))

        result = provider.send_email(
            to="marie@client.example",
            subject="Digest 7h45",
            html_body="<p>hi</p>",
        )

        assert isinstance(result, EmailResult)
        assert result.success is True
        assert result.provider == "brevo"
        assert result.message_id == "<abc-123@brevo>"
        assert result.error is None
        assert result.attempts == 1

    def test_send_email_4xx_returns_failure_no_exception(self, provider, monkeypatch):
        """4xx définitif (400/401/403/404) → success=False, no retry, no raise."""
        for status in (400, 401, 403, 404):
            resp = _make_response(status, {"message": "config error"})
            mock_post = MagicMock(return_value=resp)
            monkeypatch.setattr("services.email_provider.httpx.post", mock_post)

            result = provider.send_email(to="x@y.io", subject="s", html_body="b")

            assert result.success is False, f"Status {status} should fail"
            assert result.error and result.error.startswith("client_error:"), (
                f"Status {status} expected client_error:* — got {result.error!r}"
            )
            # Pas de retry sur 4xx définitif
            assert mock_post.call_count == 1, f"Status {status} should not retry"

    def test_send_email_5xx_retries_then_silent_fail(self, provider, monkeypatch, fast_backoff):
        """5xx → 2 retries (3 attempts total) puis silent fail."""
        resp = _make_response(503, {"message": "service unavailable"})
        mock_post = MagicMock(return_value=resp)
        monkeypatch.setattr("services.email_provider.httpx.post", mock_post)

        result = provider.send_email(to="x@y.io", subject="s", html_body="b")

        assert result.success is False
        assert result.error == "server_error:503"
        assert result.attempts == 3  # 1 initial + 2 retries
        assert mock_post.call_count == 3

    def test_send_email_429_rate_limit_retries_once(self, provider, monkeypatch, fast_backoff):
        """429 → 1 retry. Si 2e tentative renvoie 201, success."""
        resp_429 = _make_response(429)
        resp_201 = _make_response(201, {"messageId": "ok-after-rate-limit"})
        mock_post = MagicMock(side_effect=[resp_429, resp_201])
        monkeypatch.setattr("services.email_provider.httpx.post", mock_post)

        result = provider.send_email(to="x@y.io", subject="s", html_body="b")

        assert result.success is True
        assert result.attempts == 2
        assert result.message_id == "ok-after-rate-limit"

    def test_send_email_timeout_silent_fail(self, provider, monkeypatch, fast_backoff):
        """httpx.TimeoutException → silent fail, pas d'exception au caller."""
        mock_post = MagicMock(side_effect=httpx.TimeoutException("read timeout"))
        monkeypatch.setattr("services.email_provider.httpx.post", mock_post)

        result = provider.send_email(to="x@y.io", subject="s", html_body="b")

        assert result.success is False
        assert result.error and "transport_error:TimeoutException" in result.error
        assert result.attempts == 3  # 2 retries pour timeout

    def test_send_email_network_error_silent_fail(self, provider, monkeypatch, fast_backoff):
        """httpx.NetworkError (ex: DNS) → silent fail."""
        mock_post = MagicMock(side_effect=httpx.NetworkError("connection refused"))
        monkeypatch.setattr("services.email_provider.httpx.post", mock_post)

        result = provider.send_email(to="x@y.io", subject="s", html_body="b")

        assert result.success is False
        assert result.error and "transport_error:NetworkError" in result.error

    def test_payload_format_brevo_api_v3(self, provider, monkeypatch):
        """Payload doit matcher contrat Brevo v3 : sender / to / subject /
        htmlContent (+ textContent + tags optionnels)."""
        resp = _make_response(201, {"messageId": "x"})
        mock_post = MagicMock(return_value=resp)
        monkeypatch.setattr("services.email_provider.httpx.post", mock_post)

        provider.send_email(
            to="marie@client.example",
            to_name="Marie DAF",
            subject="Digest 7h45",
            html_body="<p>events</p>",
            text_body="events",
            tags=["digest", "marie"],
        )

        # 1 call attendu
        assert mock_post.call_count == 1
        call_kwargs = mock_post.call_args.kwargs
        # URL Brevo v3
        assert mock_post.call_args.args[0] == "https://api.brevo.com/v3/smtp/email"
        # Auth header api-key (pas Bearer)
        assert call_kwargs["headers"]["api-key"] == "test-key"
        assert call_kwargs["headers"]["Content-Type"] == "application/json"
        # Payload structure
        payload = call_kwargs["json"]
        assert payload["sender"] == {"email": "noreply@test.io", "name": "Test"}
        assert payload["to"] == [{"email": "marie@client.example", "name": "Marie DAF"}]
        assert payload["subject"] == "Digest 7h45"
        assert payload["htmlContent"] == "<p>events</p>"
        assert payload["textContent"] == "events"
        assert payload["tags"] == ["digest", "marie"]

    def test_payload_omits_optional_fields_when_none(self, provider, monkeypatch):
        """text_body et tags omis si None — payload propre Brevo."""
        resp = _make_response(201, {"messageId": "x"})
        mock_post = MagicMock(return_value=resp)
        monkeypatch.setattr("services.email_provider.httpx.post", mock_post)

        provider.send_email(to="x@y.io", subject="s", html_body="b")

        payload = mock_post.call_args.kwargs["json"]
        assert "textContent" not in payload
        assert "tags" not in payload
        # Recipient sans name optionnel
        assert payload["to"] == [{"email": "x@y.io"}]


# ── Tests get_email_provider factory ────────────────────────────────


class TestGetEmailProvider:
    def test_brevo_with_api_key(self, monkeypatch):
        """EMAIL_PROVIDER=brevo + BREVO_API_KEY → BrevoProvider."""
        monkeypatch.setenv("EMAIL_PROVIDER", "brevo")
        monkeypatch.setenv("BREVO_API_KEY", "live-key-xyz")

        prov = get_email_provider()
        assert isinstance(prov, BrevoProvider)
        assert prov.name == "brevo"

    def test_default_is_brevo(self, monkeypatch):
        """EMAIL_PROVIDER non défini → default brevo."""
        monkeypatch.delenv("EMAIL_PROVIDER", raising=False)
        monkeypatch.setenv("BREVO_API_KEY", "key")

        prov = get_email_provider()
        assert prov.name == "brevo"

    def test_missing_api_key_raises(self, monkeypatch):
        """EMAIL_PROVIDER=brevo sans BREVO_API_KEY → ValueError fail-fast."""
        monkeypatch.setenv("EMAIL_PROVIDER", "brevo")
        monkeypatch.delenv("BREVO_API_KEY", raising=False)

        with pytest.raises(ValueError, match="BREVO_API_KEY"):
            get_email_provider()

    def test_unsupported_provider_raises(self, monkeypatch):
        """EMAIL_PROVIDER=mailgun (non implémenté) → ValueError."""
        monkeypatch.setenv("EMAIL_PROVIDER", "mailgun")

        with pytest.raises(ValueError, match="Unsupported EMAIL_PROVIDER"):
            get_email_provider()

    def test_explicit_arg_overrides_env(self, monkeypatch):
        """provider_name=... arg override env var."""
        monkeypatch.setenv("EMAIL_PROVIDER", "mailgun")  # non supporté
        monkeypatch.setenv("BREVO_API_KEY", "key")

        prov = get_email_provider(provider_name="brevo")
        assert prov.name == "brevo"

    def test_case_insensitive(self, monkeypatch):
        """EMAIL_PROVIDER=BREVO (majuscules) → tolérant."""
        monkeypatch.setenv("EMAIL_PROVIDER", "BREVO")
        monkeypatch.setenv("BREVO_API_KEY", "key")

        prov = get_email_provider()
        assert prov.name == "brevo"


# ── Test contractuel BrevoProvider.__init__ ─────────────────────────


class TestBrevoProviderInit:
    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="non-empty api_key"):
            BrevoProvider(api_key="")
