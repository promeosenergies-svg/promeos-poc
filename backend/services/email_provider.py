"""Email provider — abstraction pluggable Sprint α-push Phase 2.B.

Q1 audit Phase 0.bis arbitré : **Brevo (FR)** comme provider par défaut
(serveurs UE → RGPD natif, pas de SCC UE-US ni DPIA).

Architecture pluggable : `EMAIL_PROVIDER` env var permet de pivoter vers
Scaleway TEM / Tipimail / AWS SES eu-west-1 sans toucher au code
consommateur. Première implémentation = Brevo via httpx direct (pas de
SDK officiel — `httpx>=0.25.2` déjà dans requirements, 0 nouvelle dep).

**Contrat appelant** : `send_email()` ne lève jamais d'exception au
caller. Toute erreur (4xx, 5xx, timeout, réseau) est capturée dans
`EmailResult(success=False, error="...")`. Le digest Marie 7h45 ne doit
pas crasher le cron GHA si Brevo est down — silent fail + log + métrique.

**Retry strategy** :
- 4xx légers (429 rate-limit) → 1 retry après 1s
- 5xx → 2 retries exponential backoff (1s, 2s)
- timeout / network error → 2 retries idem 5xx
- 4xx définitifs (400/401/403/404) → pas de retry (configuration cassée)

Réf : docs/audits/sprint_alpha_push_phase0_audit_20260502.md (Q1 + Q5),
docs/adr/ADR-002-chantier-alpha-moteur-evenements.md (§notifications).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


# ── Configuration ──────────────────────────────────────────────────


DEFAULT_PROVIDER = "brevo"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_FROM_EMAIL = "noreply@promeos.io"
DEFAULT_FROM_NAME = "PROMEOS"

# Retries : 5xx + timeout/network → 2 retries, 429 rate-limit → 1 retry,
# autres 4xx (400/401/403/404) → pas de retry (config cassée).
_MAX_RETRIES_TRANSIENT = 2
_BACKOFF_INITIAL_SECONDS = 1.0


# ── Result dataclass ───────────────────────────────────────────────


@dataclass(frozen=True)
class EmailResult:
    """Résultat opaque d'un envoi email — jamais d'exception au caller.

    Le caller (digest dispatcher Phase 2.D) inspecte `success` pour
    décider de la suite. `error` est sourcé pour log/métrique. Pas de
    PII dans `error` (cf. SG_EMAIL_01).
    """

    success: bool
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    attempts: int = 1
    tags: tuple[str, ...] = field(default_factory=tuple)


# ── Provider Brevo ─────────────────────────────────────────────────


class BrevoProvider:
    """Provider Brevo (ex-Sendinblue) — API v3 transactionnelle.

    Endpoint : POST https://api.brevo.com/v3/smtp/email
    Auth : header `api-key: <BREVO_API_KEY>`
    Réponse success : 201 + `{"messageId": "<...>"}`
    Doc : https://developers.brevo.com/reference/sendtransacemail

    Serveurs : UE (Paris/Roubaix) → RGPD natif, pas de SCC UE-US.
    """

    name = "brevo"
    api_url = "https://api.brevo.com/v3/smtp/email"

    def __init__(
        self,
        api_key: str,
        from_email: str = DEFAULT_FROM_EMAIL,
        from_name: str = DEFAULT_FROM_NAME,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not api_key:
            raise ValueError("BrevoProvider requires non-empty api_key")
        self._api_key = api_key
        self._from_email = from_email
        self._from_name = from_name
        self._timeout = timeout_seconds

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        to_name: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> EmailResult:
        """Envoie un email. Ne lève JAMAIS d'exception — silent fail.

        Parameters
        ----------
        to : str
            Adresse email destinataire (PII — ne jamais logger en clair).
        subject : str
        html_body : str
        text_body : Optional[str]
            Fallback text/plain. Recommandé pour deliverability.
        to_name : Optional[str]
            Nom destinataire (PII — ne jamais logger).
        tags : Optional[list[str]]
            Tags Brevo (ex: ["digest", "marie", "v2026-05"]) pour filtrage
            dashboard Brevo.

        Returns
        -------
        EmailResult
            Toujours retourné, jamais raised.
        """
        payload = self._build_payload(to, subject, html_body, text_body, to_name, tags)
        return self._send_with_retries(payload, tags or [])

    def _build_payload(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str],
        to_name: Optional[str],
        tags: Optional[list[str]],
    ) -> dict:
        recipient: dict = {"email": to}
        if to_name:
            recipient["name"] = to_name
        payload: dict = {
            "sender": {"email": self._from_email, "name": self._from_name},
            "to": [recipient],
            "subject": subject,
            "htmlContent": html_body,
        }
        if text_body:
            payload["textContent"] = text_body
        if tags:
            payload["tags"] = list(tags)
        return payload

    def _send_with_retries(self, payload: dict, tags: list[str]) -> EmailResult:
        """Boucle d'envoi avec retry transient errors.

        Pas de PII (to, to_name) dans les logs — uniquement tags +
        attempt count + status code + error class.
        """
        headers = {
            "api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        start = time.monotonic()
        attempts = 0
        last_error = "unknown"

        while attempts <= _MAX_RETRIES_TRANSIENT:
            attempts += 1
            try:
                resp = httpx.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = f"transport_error:{type(exc).__name__}"
                logger.warning(
                    "brevo.send_email transport error attempt=%d tags=%s err=%s",
                    attempts,
                    tags,
                    type(exc).__name__,
                )
                if attempts > _MAX_RETRIES_TRANSIENT:
                    break
                self._backoff_sleep(attempts)
                continue

            # Success
            if resp.status_code in (200, 201):
                latency_ms = (time.monotonic() - start) * 1000
                try:
                    message_id = resp.json().get("messageId")
                except Exception:
                    message_id = None
                logger.info(
                    "brevo.send_email success attempts=%d tags=%s latency_ms=%.1f",
                    attempts,
                    tags,
                    latency_ms,
                )
                return EmailResult(
                    success=True,
                    provider=self.name,
                    message_id=message_id,
                    latency_ms=latency_ms,
                    attempts=attempts,
                    tags=tuple(tags),
                )

            # Rate limit (429) : retry une fois
            if resp.status_code == 429 and attempts <= 1:
                last_error = "rate_limited:429"
                logger.warning(
                    "brevo.send_email rate-limited (429) attempt=%d tags=%s",
                    attempts,
                    tags,
                )
                self._backoff_sleep(attempts)
                continue

            # 5xx : retry exponential backoff
            if 500 <= resp.status_code < 600:
                last_error = f"server_error:{resp.status_code}"
                logger.warning(
                    "brevo.send_email server error %d attempt=%d tags=%s",
                    resp.status_code,
                    attempts,
                    tags,
                )
                if attempts > _MAX_RETRIES_TRANSIENT:
                    break
                self._backoff_sleep(attempts)
                continue

            # 4xx définitif (400/401/403/404) : pas de retry, config cassée
            last_error = f"client_error:{resp.status_code}"
            logger.error(
                "brevo.send_email client error %d (no retry) tags=%s",
                resp.status_code,
                tags,
            )
            break

        latency_ms = (time.monotonic() - start) * 1000
        return EmailResult(
            success=False,
            provider=self.name,
            error=last_error,
            latency_ms=latency_ms,
            attempts=attempts,
            tags=tuple(tags),
        )

    @staticmethod
    def _backoff_sleep(attempt: int) -> None:
        """Exponential backoff : 1s, 2s, 4s..."""
        time.sleep(_BACKOFF_INITIAL_SECONDS * (2 ** (attempt - 1)))


# ── Factory ────────────────────────────────────────────────────────


_SUPPORTED_PROVIDERS = {"brevo"}


def get_email_provider(
    provider_name: Optional[str] = None,
) -> BrevoProvider:
    """Factory du provider email courant — lit `EMAIL_PROVIDER` env.

    Default = `brevo` (Q1 audit Phase 0.bis arbitré).

    Architecturalement extensible : ajouter ScalewayTemProvider ou
    AwsSesEuWest1Provider revient à étendre `_SUPPORTED_PROVIDERS` et
    mapper le nom ici.

    Raises
    ------
    ValueError
        Si EMAIL_PROVIDER inconnu, ou si BREVO_API_KEY absent quand
        provider=brevo (config cassée → fail fast au démarrage de
        l'application, pas au runtime du digest).
    """
    name = (provider_name or os.environ.get("EMAIL_PROVIDER", DEFAULT_PROVIDER)).lower()

    if name not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported EMAIL_PROVIDER={name!r}. "
            f"Supported: {sorted(_SUPPORTED_PROVIDERS)}. "
            f"To add a new provider, extend _SUPPORTED_PROVIDERS in "
            f"services/email_provider.py."
        )

    if name == "brevo":
        api_key = os.environ.get("BREVO_API_KEY", "")
        if not api_key:
            raise ValueError(
                "BREVO_API_KEY env var is required when EMAIL_PROVIDER=brevo. Set it in .env or platform secrets."
            )
        return BrevoProvider(
            api_key=api_key,
            from_email=os.environ.get("EMAIL_FROM", DEFAULT_FROM_EMAIL),
            from_name=os.environ.get("EMAIL_FROM_NAME", DEFAULT_FROM_NAME),
        )

    # Unreachable (covered by _SUPPORTED_PROVIDERS check)
    raise ValueError(f"Provider {name!r} not implemented")
