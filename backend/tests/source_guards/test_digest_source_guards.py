"""Source guards digest_service — Phase 2.D Sprint α-push.

SG_DIGEST_01 : aucune PII (email, nom, prenom de l'utilisateur)
               dans les logs `logger.{info,warning,error}`. Uniquement
               cid + user_id + tags + classe d'erreur.

SG_DIGEST_02 : digest_service délègue à events_query_service +
               email_provider — pas de duplication compute_events ni
               d'appel httpx direct. Voie C maintenue (event_bus pure).

SG_DIGEST_03 : `_event_to_template_dict` n'expose pas event.id /
               source.system / source.last_updated_at — anti-leak
               identifiants techniques dans le HTML email.

SG_DIGEST_04 : endpoint POST /digest/dispatch utilise
               require_platform_admin (cohérent /events/refresh
               Phase 2.A).
"""

from __future__ import annotations

import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SERVICE_PATH = os.path.join(_BACKEND_ROOT, "services", "digest_service.py")
_ROUTE_PATH = os.path.join(_BACKEND_ROOT, "routes", "digest.py")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class TestDigestSourceGuards:
    def test_sg_digest_01_no_pii_in_logs(self):
        """SG_DIGEST_01 : logs sans PII (email/nom/prenom).

        user.id (entier) toléré comme identifiant interne (pas PII directe
        au sens RGPD lourd). user.email / user.nom / user.prenom interdits
        dans logs (les leaker dans observability platform = violation RGPD
        data minimization).
        """
        src = _read(_SERVICE_PATH)

        log_lines = [line for line in src.splitlines() if re.search(r"\blogger\.(info|warning|error|debug)\(", line)]
        assert log_lines, "digest_service doit logger pour observability"

        forbidden_pii_in_logs = (
            r"\buser\.email\b",
            r"\buser\.nom\b",
            r"\buser\.prenom\b",
            r"\bemail=\{",
            r"\b%\(email\)",
            r'%s["\'].*user\.email',
        )
        for line in log_lines:
            for pattern in forbidden_pii_in_logs:
                assert not re.search(pattern, line), (
                    f"SG_DIGEST_01 violated: log call contains PII pattern "
                    f"{pattern!r}.\n  Line: {line.strip()}\n  "
                    f"RGPD: log uniquement user_id (int), pas email/nom/prenom."
                )

    def test_sg_digest_02_delegates_to_existing_services(self):
        """SG_DIGEST_02 : digest_service ne ré-implémente pas
        compute_events ni d'appel httpx direct vers Brevo.

        Doit déléguer à :
        - events_query_service.get_upcoming_events
        - email_provider.get_email_provider() + .send_email()
        """
        src = _read(_SERVICE_PATH)

        # Doit importer get_upcoming_events
        assert "from services.events_query_service import" in src
        assert "get_upcoming_events" in src

        # Doit importer get_email_provider
        assert "from services.email_provider import" in src
        assert "get_email_provider" in src

        # NE doit PAS importer event_bus (passe par events_query_service)
        assert "from services.event_bus" not in src, (
            "SG_DIGEST_02 violated: digest_service doit passer par "
            "events_query_service, pas event_bus directement (Voie C)."
        )

        # NE doit PAS faire d'appel httpx direct (passe par email_provider)
        assert "import httpx" not in src
        assert "httpx.post" not in src
        assert "httpx.Client" not in src

    def test_sg_digest_03_template_dict_excludes_technical_identifiers(self):
        """SG_DIGEST_03 : `_event_to_template_dict` n'expose pas les
        identifiants techniques (event.id, source.system, source.last_updated_at)
        dans le dict rendu au template.

        Anti-leak : ces champs ne doivent pas se retrouver dans le HTML
        email envoyé au destinataire.
        """
        from services.digest_service import _event_to_template_dict

        body = inspect.getsource(_event_to_template_dict)
        # Strip docstring + line comments — éviter faux positifs sur les
        # commentaires explicatifs qui MENTIONNENT les champs interdits
        # (anti-pattern docstring "Pas de PII : event.id...")
        body_no_doc = re.sub(r'"""[\s\S]*?"""', "", body, flags=re.MULTILINE)
        body_no_doc = re.sub(r"#.*$", "", body_no_doc, flags=re.MULTILINE)

        # Champs techniques non exposés
        forbidden_attrs = (
            r"\bevent\.id\b",
            r"\bsource\.system\b",
            r"\bsource\.last_updated_at\b",
            r"\bsource\.confidence\b",  # interne, pas pour user
        )
        for pattern in forbidden_attrs:
            assert not re.search(pattern, body_no_doc), (
                f"SG_DIGEST_03 violated: _event_to_template_dict expose "
                f"{pattern!r} dans le dict rendu. Anti-leak technique requis."
            )

        # Champs métier OK
        assert "severity" in body_no_doc
        assert "title" in body_no_doc
        assert "narrative" in body_no_doc
        assert "methodology" in body_no_doc  # Cat A/B traçabilité OK

    def test_sg_digest_04_dispatch_endpoint_uses_strict_admin(self):
        """SG_DIGEST_04 : POST /digest/dispatch utilise require_platform_admin
        (cohérent /events/refresh Phase 2.A SG_EVENTS_06).
        """
        from routes.digest import dispatch_digest_endpoint

        body = inspect.getsource(dispatch_digest_endpoint)

        assert "require_platform_admin" in body, (
            "POST /digest/dispatch doit utiliser require_platform_admin (strict, pas de bypass DEMO_MODE)."
        )

        # Pas de variantes lenient
        for forbidden in ("require_admin()", "Depends(require_admin)", "get_optional_auth"):
            assert forbidden not in body, f"POST /digest/dispatch ne doit pas utiliser {forbidden!r}"
