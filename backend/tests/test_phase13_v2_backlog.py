"""Phase 13 — Source-guards V2 backlog (BL-2 + BL-7 + BL-8 + BL-9 BE).

Vérifie les 4 tickets backlog V2 traités :

- **13.A** : BL-2 factorisation `_fmt_eur_short` → SoT canonique
- **13.B** : BL-7 cross-org typology_override (user_id, org_id) composite
- **13.C** : BL-8 féminin enrichissements V2 (Joshua/Luca/Andrea/Garance)
- **13.D** : BL-9 glossaire TURPE COMMERCE (test FE séparé)

Sprint Q3 2026 backlog clôturé. Tag v1.0 ready.

Ref : audit personas Phase 12.bis + tickets BL-2/7/8/9.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import os

# Phase 13.B — set JWT secret avant import iam_service (test-only)
os.environ.setdefault("PROMEOS_JWT_SECRET", "test_secret_phase13_v2_backlog")

from doctrine.naf_to_typology import OrganizationTypology  # noqa: E402
from models import Base, Organisation, User  # noqa: E402
from services.iam_service import hash_password  # noqa: E402
from services.user_preference_service import (  # noqa: E402
    get_or_create_user_preference,
    get_user_typology_override,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def user(db_session):
    u = User(
        email="test@test.io",
        hashed_password=hash_password("test"),
        nom="Test",
        prenom="User",
        actif=True,
    )
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def two_orgs(db_session):
    org_a = Organisation(nom="Org A Tertiaire", type_client="bureau", actif=True)
    org_b = Organisation(nom="Org B Industriel", type_client="bureau", actif=True)
    db_session.add_all([org_a, org_b])
    db_session.commit()
    return org_a, org_b


# ─── Phase 13.A — BL-2 factorisation _fmt_eur_short ───────────────────────


class TestPhase13aFmtEurFactorise:
    """Source-guard : _fmt_eur_short délègue à format_eur_short SoT."""

    def test_fmt_eur_short_delegates_to_sot(self):
        """_fmt_eur_short utilise format_eur_short avec none_as_zero=True."""
        from services.narrative.narrative_generator import _fmt_eur_short

        # Comportement legacy préservé : None → "0 €"
        assert _fmt_eur_short(None) == "0 €"
        assert _fmt_eur_short(0) == "0 €"

    def test_fmt_eur_short_uses_fr_comma_decimal(self):
        """Phase 13.A — virgule décimale FR (vs ancien point ASCII)."""
        from services.narrative.narrative_generator import _fmt_eur_short

        # 12 700 → 12,7 k€ (virgule FR)
        result = _fmt_eur_short(12_700)
        assert "12,7 k€" in result
        # Pas de point ASCII résiduel
        assert "12.7" not in result

    def test_fmt_eur_short_million_format(self):
        from services.narrative.narrative_generator import _fmt_eur_short

        result = _fmt_eur_short(1_500_000)
        assert "1,5 M€" in result

    def test_format_eur_short_sot_none_as_zero_param(self):
        """SoT canonique expose `none_as_zero` pour compatibilité legacy."""
        from services.narrative.formatters import format_eur_short

        assert format_eur_short(None) == "—"  # convention SoT
        assert format_eur_short(None, none_as_zero=True) == "0 €"  # legacy


# ─── Phase 13.B — BL-7 cross-org typology_override ────────────────────────


class TestPhase13bCrossOrgTypology:
    """Source-guards (user_id, org_id) composite + priorité résolution."""

    def test_user_preference_has_org_id_field(self):
        from models import UserPreference

        assert "org_id" in UserPreference.__table__.columns

    def test_global_override_works_when_no_org_id(self, db_session, user):
        """org_id=None → override global user (rétrocompat Phase 1.4)."""
        pref = get_or_create_user_preference(db_session, user.id)
        pref.typology_override = OrganizationTypology.COMMERCE
        db_session.commit()

        # Lookup sans org_id → trouve override global
        result = get_user_typology_override(db_session, user.id)
        assert result == OrganizationTypology.COMMERCE

    def test_org_scoped_overrides_global(self, db_session, user, two_orgs):
        """Override scopé org_id prime sur override global user."""
        org_a, org_b = two_orgs

        # Override global (org_id=NULL)
        pref_global = get_or_create_user_preference(db_session, user.id)
        pref_global.typology_override = OrganizationTypology.GRAND_GROUPE
        db_session.commit()

        # Override scopé Org A
        pref_a = get_or_create_user_preference(db_session, user.id, org_id=org_a.id)
        pref_a.typology_override = OrganizationTypology.ETI_TERTIAIRE
        db_session.commit()

        # Lookup Org A → override scopé
        result_a = get_user_typology_override(db_session, user.id, org_id=org_a.id)
        assert result_a == OrganizationTypology.ETI_TERTIAIRE

        # Lookup Org B (sans override scopé) → fallback global
        result_b = get_user_typology_override(db_session, user.id, org_id=org_b.id)
        assert result_b == OrganizationTypology.GRAND_GROUPE

    def test_no_override_returns_none(self, db_session, user):
        """Aucun override (ni global ni scopé) → None."""
        result = get_user_typology_override(db_session, user.id)
        assert result is None

    def test_create_global_and_scoped_for_same_user(self, db_session, user, two_orgs):
        """User peut avoir override global + override scopé simultanément."""
        org_a, _ = two_orgs

        pref_global = get_or_create_user_preference(db_session, user.id)
        assert pref_global.org_id is None

        pref_scoped = get_or_create_user_preference(db_session, user.id, org_id=org_a.id)
        assert pref_scoped.org_id == org_a.id

        # 2 prefs distinctes
        assert pref_global.id != pref_scoped.id


# ─── Phase 13.C — BL-8 féminin enrichissements V2 ─────────────────────────


class TestPhase13cFeminineV2:
    """Heuristique V2 : épicènes internationaux + INSEE FR top."""

    def test_joshua_masculin_us_not_feminized(self):
        """Joshua se termine en -a mais est masculin US/anglo (pas féminin FR)."""
        from services.narrative.persona_context import _is_feminine_first_name

        assert _is_feminine_first_name("Joshua") is False

    def test_luca_masculin_italien_not_feminized(self):
        from services.narrative.persona_context import _is_feminine_first_name

        assert _is_feminine_first_name("Luca") is False

    def test_andrea_epicene_not_feminized(self):
        """Andrea est épicène (italien masculin / anglo féminin) → False."""
        from services.narrative.persona_context import _is_feminine_first_name

        assert _is_feminine_first_name("Andrea") is False

    def test_noah_masculin_not_feminized(self):
        from services.narrative.persona_context import _is_feminine_first_name

        assert _is_feminine_first_name("Noah") is False

    def test_louise_feminin_override(self):
        """Louise se termine en -e mais est féminin sans ambiguïté."""
        from services.narrative.persona_context import _is_feminine_first_name

        assert _is_feminine_first_name("Louise") is True

    def test_garance_feminin_override(self):
        """Garance se termine en -e mais est féminin (top INSEE 2020s)."""
        from services.narrative.persona_context import _is_feminine_first_name

        assert _is_feminine_first_name("Garance") is True

    def test_baptiste_masculin_exception(self):
        """Baptiste se termine en -e mais est masculin (top INSEE)."""
        from services.narrative.persona_context import _is_feminine_first_name

        assert _is_feminine_first_name("Baptiste") is False

    def test_loic_masculin_exception(self):
        """Loïc se termine en -c mais on doit pas le fléchir féminin."""
        from services.narrative.persona_context import _is_feminine_first_name

        # Loïc termine en -c → pas dans feminine_endings, donc heuristique False
        assert _is_feminine_first_name("Loïc") is False
        assert _is_feminine_first_name("Loic") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
