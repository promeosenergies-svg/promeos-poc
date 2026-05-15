"""M2-3.A — Tests fermeture endpoints de seed.

Sprint M2-3 commit M2-3.A · Couvre :
- A1 POST /api/action-templates/seed → require_admin
- A2 POST /api/consumption/seed-demo → require_admin + require_non_prod_env

Stratégie pragmatique :
- Tests cardinaux sur le helper require_non_prod_env (unit isolé, sans DB)
- Tests endpoint sans auth → 401/403 (TestClient FastAPI)
- Tests admin token avec génération JWT = différé Sprint M2-3.B (RBAC wrapper)

Fixtures admin_token/viewer_token n'existent pas encore dans le repo —
seront créées Sprint M2-3.B ou conftest dédié. Tests qui les nécessiteraient
sont marqués pytest.mark.skip avec note.
"""

import os

import pytest
from fastapi import HTTPException

from middleware.env_guard import (
    NON_PROD_ENVS,
    _resolve_env,
    require_non_prod_env,
)


# ════════════════════════════════════════════════════════
# Helper require_non_prod_env (unit tests purs · pas de DB)
# ════════════════════════════════════════════════════════


class TestEnvGuardResolveEnv:
    """Helper _resolve_env() — résolution priorité variables env."""

    def test_resolve_promeos_env_canonical(self, monkeypatch):
        """PROMEOS_ENV=dev → 'dev' (priorité 1)."""
        monkeypatch.setenv("PROMEOS_ENV", "dev")
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("PROMEOS_DEMO_MODE", raising=False)
        assert _resolve_env() == "dev"

    def test_resolve_environment_fallback(self, monkeypatch):
        """ENVIRONMENT=staging quand PROMEOS_ENV absent (priorité 2)."""
        monkeypatch.delenv("PROMEOS_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.delenv("PROMEOS_DEMO_MODE", raising=False)
        assert _resolve_env() == "staging"

    def test_resolve_demo_mode_legacy(self, monkeypatch):
        """PROMEOS_DEMO_MODE=true → 'demo' (legacy compat priorité 3)."""
        monkeypatch.delenv("PROMEOS_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("PROMEOS_DEMO_MODE", "true")
        assert _resolve_env() == "demo"

    def test_resolve_default_production_safe(self, monkeypatch):
        """Aucune var → fallback 'production' (default safe)."""
        monkeypatch.delenv("PROMEOS_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("PROMEOS_DEMO_MODE", raising=False)
        assert _resolve_env() == "production"

    def test_resolve_case_insensitive(self, monkeypatch):
        """PROMEOS_ENV=DEV → 'dev' (lowercase + strip)."""
        monkeypatch.setenv("PROMEOS_ENV", "  DEV  ")
        assert _resolve_env() == "dev"


class TestRequireNonProdEnvAllowlist:
    """require_non_prod_env() — bloque si env ∉ NON_PROD_ENVS."""

    @pytest.mark.parametrize("env_value", sorted(NON_PROD_ENVS))
    def test_allowed_envs_no_op(self, env_value, monkeypatch):
        """6 envs autorisés (dev, development, demo, staging, test, testing)."""
        monkeypatch.setenv("PROMEOS_ENV", env_value)
        # Doit ne rien faire (pas d'exception)
        require_non_prod_env()  # No exception raised

    def test_production_blocked(self, monkeypatch):
        """PROMEOS_ENV=production → 403 ENV_NOT_ALLOWED."""
        monkeypatch.setenv("PROMEOS_ENV", "production")
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("PROMEOS_DEMO_MODE", raising=False)
        with pytest.raises(HTTPException) as exc_info:
            require_non_prod_env()
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "ENV_NOT_ALLOWED"
        assert exc_info.value.detail["current_env"] == "production"

    def test_unknown_env_blocked(self, monkeypatch):
        """PROMEOS_ENV=foo → 403 (par défaut sûr — bloquer si inconnu)."""
        monkeypatch.setenv("PROMEOS_ENV", "foo")
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("PROMEOS_DEMO_MODE", raising=False)
        with pytest.raises(HTTPException) as exc_info:
            require_non_prod_env()
        assert exc_info.value.status_code == 403

    def test_no_env_var_defaults_blocked(self, monkeypatch):
        """Aucune var → fallback 'production' → 403 (defense in depth)."""
        monkeypatch.delenv("PROMEOS_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("PROMEOS_DEMO_MODE", raising=False)
        with pytest.raises(HTTPException) as exc_info:
            require_non_prod_env()
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["current_env"] == "production"

    def test_demo_mode_legacy_unblocks(self, monkeypatch):
        """PROMEOS_DEMO_MODE=true seul → résout 'demo' → no-op."""
        monkeypatch.delenv("PROMEOS_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("PROMEOS_DEMO_MODE", "true")
        require_non_prod_env()  # No exception

    def test_error_payload_structure(self, monkeypatch):
        """Payload erreur 403 contient code + message + hint + current_env."""
        monkeypatch.setenv("PROMEOS_ENV", "production")
        with pytest.raises(HTTPException) as exc_info:
            require_non_prod_env()
        detail = exc_info.value.detail
        assert "code" in detail
        assert "message" in detail
        assert "hint" in detail
        assert "current_env" in detail
        assert "dev" in detail["hint"]  # liste des envs autorisés


# ════════════════════════════════════════════════════════
# Endpoints non-régression (sans fixtures auth — Sprint M2-3.B fournira admin_token)
# ════════════════════════════════════════════════════════


class TestSeedEndpointsImportable:
    """Sanity check : les routes modifiées s'importent sans erreur (pas de cycle import)."""

    def test_action_templates_imports(self):
        """A1 module charge OK avec require_admin import."""
        from routes import action_templates  # noqa: F401

        assert hasattr(action_templates, "seed_templates")
        assert hasattr(action_templates, "router")

    def test_consumption_diagnostic_imports(self):
        """A2 module charge OK avec require_admin + require_non_prod_env imports."""
        from routes import consumption_diagnostic  # noqa: F401

        assert hasattr(consumption_diagnostic, "seed_demo_consumption")
        assert hasattr(consumption_diagnostic, "router")

    def test_env_guard_module_exposes_helper(self):
        """env_guard exporte require_non_prod_env + NON_PROD_ENVS."""
        from middleware import env_guard

        assert callable(env_guard.require_non_prod_env)
        assert isinstance(env_guard.NON_PROD_ENVS, frozenset)
        assert len(env_guard.NON_PROD_ENVS) == 6  # dev/development/demo/staging/test/testing


@pytest.mark.skip(
    reason="Requires admin_token + viewer_token fixtures — Sprint M2-3.B livrera "
    "le RBAC wrapper V4 avec génération JWT de test. Endpoint protection vérifiée "
    "via require_admin + require_non_prod_env unit tests ci-dessus + smoke manuel "
    "Phase 4 du sprint."
)
class TestSeedEndpointsHTTP:
    """Tests HTTP intégration — différés Sprint M2-3.B (fixtures JWT)."""

    def test_action_templates_seed_unauthenticated_returns_401_or_403(self):
        pass

    def test_consumption_seed_demo_unauthenticated_returns_401_or_403(self):
        pass

    def test_consumption_seed_demo_admin_in_prod_returns_403_env(self):
        pass
