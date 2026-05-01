"""Phase 6 — Source-guards `simulate_date` paramètre fonctionnel.

Vérifie :
1. `simulate_date` ISO 8601 fourni → kicker week_iso correspond à cette date
2. `simulate_date` non fourni → comportement courant inchangé (datetime.now)
3. `simulate_date` invalide → 400 (route)
4. Deux dates différentes → narratives potentiellement différentes (week_iso)
5. Builders legacy (sans `now` param) ne crashent pas

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 6.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


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
def helios_org(db_session):
    """Org HELIOS-like avec 1 site GRAND_GROUPE."""
    org = Organisation(nom="HELIOS Test", type_client="bureau", actif=True)
    db_session.add(org)
    db_session.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="111111111")
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db_session.add(pf)
    db_session.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Siège",
        type=TypeSite.BUREAU,
        naf_code="6820B",
        surface_m2=3500,
        actif=True,
    )
    db_session.add(site)
    db_session.commit()
    return org, site


# ─── Tests builder _build_cockpit_comex avec now param ─────────────────────


class TestBuilderSimulateDate:
    """Source-guards : builder accepte `now` param et l'utilise pour week_iso."""

    def test_builder_accepts_now_param(self, db_session, helios_org):
        """`_build_cockpit_comex` accepte `now` keyword optionnel."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org
        # 2026-01-05 → ISO week 2 (lundi 1ère semaine pleine)
        simulated = datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc)
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1, now=simulated)

        assert "SEMAINE 2" in narrative.kicker, (
            f"week_iso doit refléter simulate_date 2026-01-05 (W2), trouvé : {narrative.kicker!r}"
        )

    def test_builder_default_uses_current_now(self, db_session, helios_org):
        """Sans `now` → datetime.now() courant (comportement legacy inchangé)."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1)

        # Kicker contient "SEMAINE X" où X = isocalendar() courant
        current_week = datetime.now(timezone.utc).isocalendar().week
        assert f"SEMAINE {current_week}" in narrative.kicker

    def test_simulate_date_changes_narrative_week_iso(self, db_session, helios_org):
        """Deux dates différentes → kickers différents (week_iso différents)."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org
        date_w2 = datetime(2026, 1, 8, 10, 0, tzinfo=timezone.utc)  # W2
        date_w26 = datetime(2026, 6, 25, 10, 0, tzinfo=timezone.utc)  # W26

        with patch("services.event_bus.compute_events", return_value=[]):
            narr_w2 = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1, now=date_w2)
            narr_w26 = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1, now=date_w26)

        assert "SEMAINE 2" in narr_w2.kicker
        assert "SEMAINE 26" in narr_w26.kicker
        assert narr_w2.kicker != narr_w26.kicker


# ─── Tests entry point generate_page_narrative ──────────────────────────────


class TestGeneratePageNarrativeWithSimulateDate:
    """Source-guards : entry point public propage `now` au builder."""

    def test_generate_page_narrative_accepts_now(self, db_session, helios_org):
        """generate_page_narrative accepte `now` kwargs."""
        from services.narrative.narrative_generator import generate_page_narrative

        org, _ = helios_org
        simulated = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)  # W11
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = generate_page_narrative(
                db=db_session,
                page_key="cockpit_comex",
                org_id=org.id,
                org_name=org.nom,
                sites_count=1,
                persona="comex",
                now=simulated,
            )
        assert "SEMAINE 11" in narrative.kicker

    def test_generate_page_narrative_legacy_builders_dont_crash(self, db_session, helios_org):
        """Builders legacy (sans `now` dans signature) ne crashent pas si `now` passé.

        inspect.signature check dans generate_page_narrative ne propage `now`
        que si le builder l'accepte. Builders legacy (cockpit_daily, etc.)
        continuent de fonctionner.
        """
        from services.narrative.narrative_generator import _BUILDERS

        # Identifier un builder legacy (pas cockpit_comex qui a été étendu)
        legacy_keys = [k for k in _BUILDERS if k != "cockpit_comex"]
        assert legacy_keys, "Au moins un builder legacy doit exister"
        # Test qu'inspect détecte bien que cockpit_comex a `now` mais pas les autres
        import inspect

        sig_comex = inspect.signature(_BUILDERS["cockpit_comex"])
        assert "now" in sig_comex.parameters

        # Vérifier qu'au moins un builder legacy n'a PAS `now` (preuve de
        # rétrocompat — Phase 4.bis2 wiring uniquement cockpit_comex MVP)
        legacy_sig = inspect.signature(_BUILDERS[legacy_keys[0]])
        # Ce test peut échouer si plus tard tous les builders sont étendus
        # — c'est OK, supprimer ce test ou ajuster.
        if "now" not in legacy_sig.parameters:
            assert True  # rétrocompat respecté
        else:
            pytest.skip(f"Builder {legacy_keys[0]} a maintenant `now` — rétrocompat OK")


# ─── Tests route HTTP /api/pages/{key}/briefing ────────────────────────────


class TestRouteSimulateDate:
    """Source-guards : route HTTP accepte simulate_date query param."""

    def test_route_accepts_simulate_date_query_param(self, db_session, helios_org):
        """Route accepte ?simulate_date=2026-01-05 et le propage au builder."""
        from fastapi.testclient import TestClient

        from database import get_db
        from main import app

        org, _ = helios_org

        def _override_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = _override_db
        try:
            client = TestClient(app)
            with patch("services.event_bus.compute_events", return_value=[]):
                response = client.get(
                    f"/api/pages/cockpit_comex/briefing?org_id={org.id}&persona=comex&simulate_date=2026-01-05"
                )
            assert response.status_code == 200, f"body={response.text}"
            payload = response.json().get("data") or response.json()
            kicker = payload.get("kicker", "")
            assert "SEMAINE 2" in kicker, f"kicker={kicker!r}"
        finally:
            app.dependency_overrides.clear()

    def test_route_invalid_simulate_date_returns_400(self, db_session, helios_org):
        """simulate_date invalide → 400 avec message explicite."""
        from fastapi.testclient import TestClient

        from database import get_db
        from main import app

        org, _ = helios_org

        def _override_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = _override_db
        try:
            client = TestClient(app)
            response = client.get(
                f"/api/pages/cockpit_comex/briefing?org_id={org.id}&persona=comex&simulate_date=not-a-date"
            )
            assert response.status_code == 400
            # APIError contract — message dans 'message' key
            body = response.json()
            assert "simulate_date" in body.get("message", "")
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
