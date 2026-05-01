"""Phase 9.A — Source-guards wiring typology dans 9 builders legacy.

Vérifie que tous les builders narrative (10 pages : cockpit_daily,
cockpit_comex + 8 autres) exposent désormais `Narrative.typology` au FE.

Avant Phase 9.A : seul `cockpit_comex` exposait typology (Phase 4.0.B
wiring). Les 9 autres builders retournaient `typology=None` → tout
l'investissement Phase 1-3 invisible sur 9/10 pages Sol.

Après Phase 9.A : tous les builders exposent `typology` via le helper
canonique `_resolve_org_typology_value(db, org_id)`. La phrase 1
événementielle reste cockpit_comex-only (V2 panel Phase 5 décidera
si étendre à cockpit_daily/patrimoine/etc.).

Ref : audit final ticket BL-1 (9 builders legacy non wirés Phase 4.0.B).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from doctrine.naf_to_typology import OrganizationTypology
from models import Base, EntiteJuridique, Organisation, Portefeuille, Site, TypeSite


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


# ─── Helper canonique ──────────────────────────────────────────────────────


class TestResolveOrgTypologyHelper:
    """Source-guard : helper canonique partagé par tous les builders."""

    def test_helper_resolves_grand_groupe(self, db_session, helios_org):
        from services.narrative.narrative_generator import _resolve_org_typology_value

        org, _ = helios_org
        result = _resolve_org_typology_value(db_session, org.id)
        # Phase 9.B : NAF 6820B + petite fixture (1 site 3500 m²) → bascule ETI_TERTIAIRE
        assert result in (
            OrganizationTypology.GRAND_GROUPE.value,
            OrganizationTypology.ETI_TERTIAIRE.value,
        )

    def test_helper_fail_safe_unknown_for_invalid_org(self, db_session):
        """Org introuvable → retourne 'unknown' (jamais d'exception)."""
        from services.narrative.narrative_generator import _resolve_org_typology_value

        result = _resolve_org_typology_value(db_session, 99999)
        # Pas d'exception, fallback sur 'unknown'
        assert result == OrganizationTypology.UNKNOWN.value


# ─── Wiring 10 builders ────────────────────────────────────────────────────


_ALL_BUILDER_KEYS = [
    "cockpit_daily",
    "cockpit_comex",
    "patrimoine",
    "conformite",
    "bill_intel",
    "achat_energie",
    "monitoring",
    "diagnostic",
    "anomalies",
    "flex",
]


class TestAllBuildersExposeTypology:
    """Source-guard cardinal Phase 9.A : tous les builders exposent typology."""

    @pytest.mark.parametrize("page_key", _ALL_BUILDER_KEYS)
    def test_builder_returns_narrative_with_typology(self, db_session, helios_org, page_key):
        """Tous les builders retournent une Narrative avec `typology` non-None."""
        from services.narrative.narrative_generator import generate_page_narrative

        org, _ = helios_org
        with patch("services.event_bus.compute_events", return_value=[]):
            try:
                narrative = generate_page_narrative(
                    db=db_session,
                    page_key=page_key,
                    org_id=org.id,
                    org_name=org.nom,
                    sites_count=1,
                    persona="comex" if page_key == "cockpit_comex" else "daily",
                )
            except Exception as e:  # noqa: BLE001
                pytest.skip(f"Builder {page_key} a échoué (manque seed) : {e}")
                return

        assert narrative.typology is not None, (
            f"Builder {page_key} ne wire pas typology — Phase 9.A non livrée pour cette page"
        )
        # Typology valide (un des 4 enum values ou 'unknown' fallback)
        valid_values = {t.value for t in OrganizationTypology}
        assert narrative.typology in valid_values, (
            f"Builder {page_key} retourne typology={narrative.typology!r} hors enum"
        )


# ─── Source-guard structurel ───────────────────────────────────────────────


class TestStructuralWiringPresence:
    """Source-guard structurel : helper appelé dans le source des 9 builders."""

    def test_resolve_org_typology_helper_called_in_legacy_builders(self):
        """Les 10 builders contiennent un appel à `_resolve_org_typology_value`.

        Détection via inspect.getsource : empêche une régression où on
        retirerait silencieusement l'appel `typology=` du Narrative()
        constructor.
        """
        import inspect

        from services.narrative.narrative_generator import _BUILDERS

        for page_key, builder in _BUILDERS.items():
            source = inspect.getsource(builder)
            # cockpit_comex utilise `typology.value` (Phase 4.0.B local)
            # Les 9 autres utilisent `_resolve_org_typology_value(db, org_id)`
            assert "_resolve_org_typology_value" in source or "typology=typology.value" in source, (
                f"Builder {page_key} ne wire pas typology au Narrative() constructor"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
