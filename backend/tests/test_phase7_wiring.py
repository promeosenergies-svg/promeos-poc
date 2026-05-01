"""Phase 7 correctifs C+D — tests wiring persona_mention + tone_variation
+ fix activity_name NAF DT_DRIFT.

Vérifie :
1. `_build_cockpit_comex` accepte `user_first_name` + `user_role` kwargs
2. Si user fourni, italic_hook = mention persona italique
3. Si pas de user, italic_hook conserve "vue mensuelle direction"
4. Tone variation appliqué au narrative final
5. NAF du site primaire propagé à compose_dt_drift_sentence (Commerce)

Ref : audit final 2026-05-01 P0+P1 corrections.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from doctrine.naf_to_typology import OrganizationTypology
from models import (
    Base,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)
from services.event_bus.types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventSource,
    SolEventCard,
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
def helios_org_with_commerce_site(db_session):
    """Org HELIOS-like avec 1 site COMMERCE (NAF 4724Z boulangerie)."""
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
        nom="Boulangerie Test",
        type=TypeSite.BUREAU,
        naf_code="4724Z",  # Boulangerie
        surface_m2=120,
        actif=True,
    )
    db_session.add(site)
    db_session.commit()
    return org, site


@pytest.fixture
def helios_org_grand_groupe(db_session):
    """Org HELIOS-like avec 1 site GRAND_GROUPE (NAF 6820B)."""
    org = Organisation(nom="HELIOS Test GG", type_client="bureau", actif=True)
    db_session.add(org)
    db_session.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="222222222")
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db_session.add(pf)
    db_session.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Siège Paris",
        type=TypeSite.BUREAU,
        naf_code="6820B",
        surface_m2=3500,
        actif=True,
    )
    db_session.add(site)
    db_session.commit()
    return org, site


def _make_drift_event(site_id: int) -> SolEventCard:
    return SolEventCard(
        id="consumption_drift:test",
        event_type="consumption_drift",
        severity="warning",
        title="Dérive consommation",
        narrative="Test drift",
        impact=EventImpact(value=14.0, unit="%", period="week"),
        source=EventSource(
            system="Enedis",
            last_updated_at=datetime.now(timezone.utc),
            confidence="high",
        ),
        action=EventAction(label="Voir", route="/test"),
        linked_assets=EventLinkedAssets(org_id=1, site_ids=[site_id]),
    )


# ─── Correctif B — NAF propagation DT_DRIFT COMMERCE ───────────────────────


class TestPhase7CorrectifBNafPropagation:
    """Bug latent audit final : get_activity_name(None) → "magasin" générique."""

    def test_builder_resolves_naf_from_primary_event_site(self, db_session, helios_org_with_commerce_site):
        """Builder lookup le NAF du site primaire et le propage au composer."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, site = helios_org_with_commerce_site
        drift = _make_drift_event(site.id)

        with (
            patch("services.event_bus.event_service.compute_events", return_value=[drift]),
            patch("services.event_bus.compute_events", return_value=[drift]),
        ):
            narrative = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1)

        # Phrase 1 doit citer "boulangerie" (NAF 4724Z), pas "magasin" générique
        # ATTENTION : ici typology dépend du NAF dominant. NAF 4724Z préfixe 47
        # → COMMERCE selon naf_to_typology. Le builder résout bien typology=COMMERCE.
        assert "boulangerie" in narrative.narrative, (
            f"Phase 7 correctif B : NAF 4724Z doit donner 'boulangerie', narrative={narrative.narrative!r}"
        )


# ─── Correctif C — wiring persona_mention + tone_variation ─────────────────


class TestPhase7CorrectifCWiringPersona:
    """Wiring compose_persona_mention via italic_hook."""

    def test_builder_accepts_user_kwargs(self, db_session, helios_org_grand_groupe):
        """Builder accepte user_first_name + user_role keywords."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org_grand_groupe
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = _build_cockpit_comex(
                db_session,
                org.id,
                org.nom,
                sites_count=1,
                user_first_name="Jean-Marc",
                user_role="cfo",
            )

        # italic_hook surchargé par mention persona
        assert "Jean-Marc" in narrative.italic_hook
        assert "DAF" in narrative.italic_hook

    def test_builder_default_italic_hook_when_no_user(self, db_session, helios_org_grand_groupe):
        """Sans user_first_name → italic_hook par défaut 'vue mensuelle direction'."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org_grand_groupe
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1)

        assert narrative.italic_hook == "vue mensuelle direction"

    def test_builder_invalid_user_role_falls_back_default(self, db_session, helios_org_grand_groupe):
        """user_role inconnu → fallback silencieux sur italic_hook par défaut."""
        from services.narrative.narrative_generator import _build_cockpit_comex

        org, _ = helios_org_grand_groupe
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = _build_cockpit_comex(
                db_session,
                org.id,
                org.nom,
                sites_count=1,
                user_first_name="Test",
                user_role="role_xyz_inconnu",
            )

        # Fallback sur le hook par défaut (pas de crash)
        assert narrative.italic_hook == "vue mensuelle direction"


class TestPhase7CorrectifCWiringTone:
    """Wiring apply_tone_variation au narrative final."""

    def test_tone_variation_module_imported_in_builder(self):
        """Source-guard structurel : import tone_variator présent dans builder."""
        from services.narrative import narrative_generator

        # Vérifier que le module importe bien apply_tone_variation
        # (une régression supprimerait l'import, le test le détecterait)
        source = open(narrative_generator.__file__).read()
        assert "from services.narrative.tone_variator import apply_tone_variation" in source

    def test_tone_variation_actually_called_in_builder(self, db_session, helios_org_grand_groupe):
        """apply_tone_variation est bien appelée dans _build_cockpit_comex."""
        org, _ = helios_org_grand_groupe
        with (
            patch(
                "services.narrative.tone_variator.apply_tone_variation",
                wraps=lambda body, tone, typology: body,
            ) as mock_tone,
            patch("services.event_bus.compute_events", return_value=[]),
        ):
            from services.narrative.narrative_generator import _build_cockpit_comex

            _build_cockpit_comex(db_session, org.id, org.nom, sites_count=1)

        # Au moins 1 appel à apply_tone_variation pendant la construction
        assert mock_tone.called, "apply_tone_variation doit être appelé dans le builder"


# ─── Test propagation generate_page_narrative ──────────────────────────────


class TestPhase7GeneratePropagation:
    """generate_page_narrative propage user_first_name + user_role au builder."""

    def test_generate_page_narrative_propagates_user_kwargs(self, db_session, helios_org_grand_groupe):
        from services.narrative.narrative_generator import generate_page_narrative

        org, _ = helios_org_grand_groupe
        with patch("services.event_bus.compute_events", return_value=[]):
            narrative = generate_page_narrative(
                db=db_session,
                page_key="cockpit_comex",
                org_id=org.id,
                org_name=org.nom,
                sites_count=1,
                persona="comex",
                user_first_name="Marie",
                user_role="cfo",
            )
        assert "Marie" in narrative.italic_hook
        assert "DAF" in narrative.italic_hook


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
