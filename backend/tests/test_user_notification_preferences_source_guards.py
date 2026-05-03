"""Source guards user_notification_preferences — Phase 2.C Sprint α-push.

SG_USER_PREFS_01 : aucun champ PII secondaire (email, phone, address)
                   dans le modèle table — la table porte uniquement les
                   préférences digest, jamais les données identifiables
                   (PII restent dans `users` table primaire).
                   RGPD : data minimization principle.

SG_USER_PREFS_02 : `UserNotificationPreferenceUpdate` Pydantic n'accepte
                   pas `user_id` (champ ignoré silencieusement par défaut
                   Pydantic — vérifier qu'il n'est pas explicitement
                   listé comme champ optionnel modifiable).

SG_USER_PREFS_03 : isolation user — les endpoints `/me/...` résolvent
                   user_id depuis `current_user.id` (token JWT), JAMAIS
                   depuis body / path param / query. Le service ne reçoit
                   que ce user_id authentifié.
"""

from __future__ import annotations

import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODEL_PATH = os.path.join(_BACKEND_ROOT, "models", "user_notification_preference.py")
_SCHEMA_PATH = os.path.join(_BACKEND_ROOT, "schemas", "user_notification_preference.py")
_ROUTE_PATH = os.path.join(_BACKEND_ROOT, "routes", "users.py")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class TestUserPrefsSourceGuards:
    def test_sg_user_prefs_01_no_pii_in_model(self):
        """SG_USER_PREFS_01 : aucun champ PII secondaire dans le modèle.

        Les PII (email, prénom/nom, téléphone, adresse) doivent rester
        exclusivement dans la table `users` primaire. La table
        `user_notification_preferences` ne porte que les préférences
        digest (booléen, locale, JSON channels).

        FK `user_id` référence users.id — autorisé (référence, pas PII).
        """
        src = _read(_MODEL_PATH)

        # Strip docstrings + comments pour éviter faux positifs sur les
        # commentaires explicatifs (ex: "PII restent dans `users`").
        src_clean = re.sub(r'"""[\s\S]*?"""', "", src, flags=re.MULTILINE)
        src_clean = re.sub(r"#.*$", "", src_clean, flags=re.MULTILINE)

        # Patterns PII directement comme nom de Column
        # Note : `digest_daily_email_enabled` (hypothétique) serait OK
        # car c'est un flag, pas une PII. On flag les noms exacts.
        forbidden_pii_columns = (
            r"\b(email|email_address)\s*=\s*Column",
            r"\b(phone|phone_number|tel|mobile)\s*=\s*Column",
            r"\b(first_name|last_name|full_name|nom|prenom)\s*=\s*Column",
            r"\b(address|adresse|postal_code|city|ville)\s*=\s*Column",
        )
        for pattern in forbidden_pii_columns:
            assert not re.search(pattern, src_clean, re.IGNORECASE), (
                f"SG_USER_PREFS_01 violated: PII column matching {pattern!r} "
                f"detected in model. PII must stay in `users` table primary. "
                f"RGPD data minimization."
            )

    def test_sg_user_prefs_02_update_schema_excludes_user_id(self):
        """SG_USER_PREFS_02 : Pydantic Update model ne liste pas `user_id`
        comme champ modifiable.

        Pydantic v2 ignore les champs inconnus par défaut (`extra='ignore'`)
        donc un `user_id` dans le body sera silently dropped — mais on
        veut garantir qu'il n'est jamais listé explicitement comme champ
        Optional, ce qui pourrait laisser penser qu'il est modifiable.
        """
        from schemas.user_notification_preference import (
            UserNotificationPreferenceUpdate,
        )

        fields = UserNotificationPreferenceUpdate.model_fields
        assert "user_id" not in fields, (
            "SG_USER_PREFS_02 violated: `user_id` listed as updatable field "
            "in UserNotificationPreferenceUpdate. user_id must be derived "
            "from auth token only — JAMAIS du body."
        )
        # Vérifie aussi l'absence de variantes
        forbidden_field_names = {"user_id", "userId", "owner_id", "owner_user_id"}
        leaked = forbidden_field_names & set(fields.keys())
        assert not leaked, f"SG_USER_PREFS_02 violated: forbidden fields {leaked}"

    def test_sg_user_prefs_03_route_isolation_user_from_token(self):
        """SG_USER_PREFS_03 : les endpoints /me/... lisent user_id depuis
        `current_user.id` (token), JAMAIS depuis body/path/query.

        Vérification :
        1. Handler signature inclut `current_user: User = Depends(get_current_user)`
        2. Aucun appel à `body.user_id` / `request.query_params["user_id"]`
        3. Service appelé avec `current_user.id` (pas autre source)
        """
        from routes.users import (
            get_my_notification_preferences,
            patch_my_notification_preferences,
        )

        for handler in (get_my_notification_preferences, patch_my_notification_preferences):
            sig = inspect.signature(handler)
            # Doit avoir current_user via Depends(get_current_user)
            assert "current_user" in sig.parameters, (
                f"{handler.__name__} doit recevoir `current_user` via Depends(get_current_user)"
            )

            body = inspect.getsource(handler)
            # Doit appeler avec current_user.id
            assert "current_user.id" in body, (
                f"SG_USER_PREFS_03 violated: {handler.__name__} doit utiliser "
                f"current_user.id (token JWT). user_id ne doit pas venir d'ailleurs."
            )

            # Patterns interdits (extraction user_id depuis ailleurs que le token)
            forbidden_user_id_sources = (
                r"body\.user_id",
                r'request\.query_params\[\s*[\'"]user_id[\'"]',
                r'kwargs\[\s*[\'"]user_id[\'"]',
                r"path_param.*user_id",
            )
            for pattern in forbidden_user_id_sources:
                assert not re.search(pattern, body), (
                    f"SG_USER_PREFS_03 violated in {handler.__name__}: "
                    f"user_id sourcing from {pattern!r} detected. "
                    f"Must use current_user.id (auth token) only."
                )

    def test_sg_user_prefs_03b_no_user_id_in_route_path(self):
        """SG_USER_PREFS_03b : aucun endpoint avec `{user_id}` dans le
        path — uniquement /me/... (self-service).

        Empêche la régression vers un pattern admin-style
        `/users/{user_id}/notification-preferences` qui leakerait l'ID
        cible en paramètre URL et nécessiterait des contrôles d'accès
        cross-user complexes.
        """
        src = _read(_ROUTE_PATH)

        # Pas de path param {user_id} ni {id}
        forbidden_path_params = (
            r"@router\.(get|patch|post|put|delete)\([^)]*\{user_id\}",
            r"@router\.(get|patch|post|put|delete)\([^)]*\{id\}",
        )
        for pattern in forbidden_path_params:
            assert not re.search(pattern, src), (
                f"SG_USER_PREFS_03b violated: route with path param "
                f"matching {pattern!r}. Use /me/... self-service only."
            )

        # /me/ doit être présent (positive check)
        assert "/me/" in src, "Routes users.py doit utiliser pattern /me/... pour self-service"
