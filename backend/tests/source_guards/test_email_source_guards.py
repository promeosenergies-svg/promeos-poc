"""PROMEOS — Source guards Phase 2.B — Email provider abstraction.

Garde-fous statiques sur `services/email_provider.py` :

SG_EMAIL_01 : aucune PII (adresse email, nom destinataire) dans les logs
              — uniquement tags + status code + classe d'erreur.
              RGPD : data minimization principle.

SG_EMAIL_02 : aucune API key hardcoded (regex sur tokens Brevo standard
              + sentinelles connues). Doit toujours passer par
              os.environ.get("BREVO_API_KEY").

SG_EMAIL_03 : send_email retourne EmailResult, ne raise JAMAIS au caller.
              Vérifié par inspection signature + scan return paths.

Réf : docs/audits/sprint_alpha_push_phase0_audit_20260502.md (Q1),
docs/adr/ADR-002-chantier-alpha-moteur-evenements.md.
"""

from __future__ import annotations

import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROVIDER_PATH = os.path.join(_BACKEND_ROOT, "services", "email_provider.py")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class TestEmailSourceGuards:
    def test_sg_email_01_no_pii_in_log_calls(self):
        """SG_EMAIL_01 : aucun appel logger.{info,warning,error} ne doit
        contenir une expression accédant aux PII directement.

        PII protégées :
          - `to` (adresse email destinataire)
          - `to_name` (nom destinataire)
          - `payload["to"]` (adresse via payload)
          - `recipient` (variable du payload builder)

        Tags + status code + classe d'erreur sont OK.
        """
        src = _read(_PROVIDER_PATH)

        # Toutes les lignes contenant un appel logger.*
        log_lines = [line for line in src.splitlines() if re.search(r"\blogger\.(info|warning|error|debug)\(", line)]
        assert log_lines, "email_provider doit avoir des logs (observabilité)"

        forbidden_pii_in_logs = (
            r"\bto\s*=",  # to=... directement dans un log call
            r"\bto_name\b",
            r'payload\["to"\]',
            r'payload\["sender"\]',
            r"\brecipient\b",
            r"\bemail=\{",  # f-string ou format avec email=
        )

        for line in log_lines:
            for pattern in forbidden_pii_in_logs:
                assert not re.search(pattern, line), (
                    f"SG_EMAIL_01 violated: log call contains PII expression "
                    f"matching {pattern!r}.\n  Line: {line.strip()}\n  "
                    f"RGPD: ne pas logger l'adresse email du destinataire."
                )

    def test_sg_email_02_no_hardcoded_api_key(self):
        """SG_EMAIL_02 : aucune API key Brevo hardcoded dans le code.

        Pattern Brevo : `xkeysib-...` (clés v3 transactionnelles).
        Sentinelles connues : tokens longs hex/base64.

        Toute clé doit passer par `os.environ.get("BREVO_API_KEY")`.
        """
        src = _read(_PROVIDER_PATH)

        # Pattern clé Brevo officiel
        assert not re.search(r"xkeysib-[a-zA-Z0-9]{20,}", src), (
            "SG_EMAIL_02 violated: clé Brevo `xkeysib-...` détectée hardcoded. "
            "Utiliser os.environ.get('BREVO_API_KEY')."
        )

        # Pattern générique : assignation directe d'un long token
        # Tolère "test-key" (utilisé en tests) en strippant docstrings
        src_no_doc = re.sub(r'"""[\s\S]*?"""', "", src, flags=re.MULTILINE)
        suspicious = re.findall(r'api_key\s*=\s*[\'"]([^\'"\s]{30,})[\'"]', src_no_doc)
        assert not suspicious, (
            f"SG_EMAIL_02 violated: long string assigned to api_key ({suspicious}). Suspecté hardcoded API key."
        )

        # Doit lire la clé via env var
        assert 'os.environ.get("BREVO_API_KEY"' in src or 'os.environ.get("BREVO_API_KEY"' in src, (
            "BREVO_API_KEY doit être lu via os.environ.get"
        )

    def test_sg_email_03_send_email_returns_email_result_never_raises(self):
        """SG_EMAIL_03 : `BrevoProvider.send_email` retourne EmailResult,
        ne raise JAMAIS au caller.

        Vérification par inspection :
        1. Annotation de retour = `EmailResult` (signature)
        2. Tous les chemins du body se terminent par `return EmailResult(...)`
           — pas de `raise` non protégé.
        """
        from services.email_provider import BrevoProvider, EmailResult

        # PEP 563 : `from __future__ import annotations` rend les
        # annotations en strings. Comparaison par nom acceptable ici.
        sig = inspect.signature(BrevoProvider.send_email)
        ret_str = sig.return_annotation if isinstance(sig.return_annotation, str) else sig.return_annotation.__name__
        assert ret_str == "EmailResult", f"send_email() doit annoter `-> EmailResult` (got {sig.return_annotation!r})"
        # Vérification cohérence : le symbole EmailResult existe bien
        assert EmailResult.__name__ == "EmailResult"

        body = inspect.getsource(BrevoProvider.send_email)

        # Tout `raise` dans le corps de send_email est interdit
        # (les helpers internes _build_payload, _send_with_retries
        # peuvent raise mais send_email lui-même ne doit pas).
        raise_in_send = re.findall(r"^\s*raise\b", body, flags=re.MULTILINE)
        assert not raise_in_send, (
            "SG_EMAIL_03 violated: send_email contient un `raise`. "
            "Le contrat est silent fail — capturer toute exception en "
            "EmailResult(success=False, error=...)."
        )

        # _send_with_retries (helper appelé par send_email) ne doit pas
        # propager d'exception non plus.
        retries_body = inspect.getsource(BrevoProvider._send_with_retries)
        raise_in_retries = re.findall(r"^\s*raise\b", retries_body, flags=re.MULTILINE)
        assert not raise_in_retries, (
            "SG_EMAIL_03 violated: _send_with_retries contient un `raise`. "
            "Le contrat est silent fail jusqu'à send_email."
        )

    def test_sg_email_03b_email_result_dataclass_frozen(self):
        """SG_EMAIL_03b complément : `EmailResult` est frozen — immutable
        après création (pas de mutation post-fact qui masquerait un état)."""
        from services.email_provider import EmailResult

        result = EmailResult(success=True, provider="brevo")
        with pytest.raises(Exception):  # FrozenInstanceError ou AttributeError
            result.success = False  # type: ignore[misc]


# Pytest import requis pour le raises ci-dessus
import pytest  # noqa: E402
