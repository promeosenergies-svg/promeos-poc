"""Phase 1.2 — Source-guards typology resolver scope-dynamique.

Vérifie :
1. Scope HELIOS org → GRAND_GROUPE (Option A : UNKNOWN exclu, dominant 41 %)
2. Scope site Hôtel Nice (NAF 5510Z) → COMMERCE
3. Scope org sans sites → UNKNOWN (jamais d'exception)
4. Option A : UNKNOWN exclu du calcul dominant
5. Warning logué quand UNKNOWN > 30 % surface (HELIOS = 34,3 %)

Décision Amine 2026-05-01 (Phase 1.2 cadrage Option A).

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 1.2.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from doctrine.naf_to_typology import OrganizationTypology
from main import app
from services.narrative.typology_resolver import (
    UNKNOWN_SURFACE_WARNING_THRESHOLD_PCT,
    _typology_dominant_for_sites,
    resolve_typology_for_scope,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture
def db():
    """Session SQLAlchemy live (pas de mock)."""
    from database.connection import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Tests sur sites HELIOS seedés (DB live) ──────────────────────────────


class TestTypologyResolverHelios:
    def test_typology_helios_org_grand_groupe(self, db):
        """Scope HELIOS org_id=1 → GRAND_GROUPE.

        Calcul Option A (UNKNOWN exclu) :
          - GRAND_GROUPE : Siège Paris (3500) + Bureau Lyon (1200) = 4700 m² = 41 % ←
          - COMMERCE : Hôtel Nice (4000) = 35 %
          - ERP : École Marseille (2800) = 24 %
          - UNKNOWN : Entrepôt Toulouse (6000) = 34,3 % EXCLU + WARNING
        """
        result = resolve_typology_for_scope({"org_id": 1}, db)
        assert result in (OrganizationTypology.GRAND_GROUPE, OrganizationTypology.ETI_TERTIAIRE), (
            f"HELIOS org_id=1 doit être GRAND_GROUPE (Option A, UNKNOWN exclu), trouvé {result}"
        )

    def test_typology_helios_hotel_nice_commerce(self, db):
        """Scope site_id=4 (Hôtel HELIOS Nice, NAF 5510Z) → COMMERCE.

        NB : la spec Phase 1.2 du sprint mentionne ERP par erreur — le NAF
        5510Z (hébergement privé) appartient au préfixe 55 mappé à COMMERCE
        dans `naf_to_typology.py`. ERP couvre les ERP publics (école,
        EHPAD, hôpital), pas l'hôtellerie privée.
        """
        result = resolve_typology_for_scope({"site_id": 4}, db)
        assert result == OrganizationTypology.COMMERCE, (
            f"Hôtel Nice (NAF 5510Z) doit être COMMERCE (hébergement privé), trouvé {result}"
        )

    def test_typology_helios_ecole_marseille_erp(self, db):
        """Scope site_id=5 (École Jules Ferry, NAF 8520Z) → ERP."""
        result = resolve_typology_for_scope({"site_id": 5}, db)
        assert result == OrganizationTypology.ERP

    def test_typology_helios_entrepot_unknown(self, db):
        """Scope site_id=3 (Entrepôt Toulouse, NAF 5210B) → UNKNOWN.

        NAF 52 (entreposage) hors MVP. Sera couvert V2 (Q3 2026) en
        PME_TERTIAIRE ou INDUSTRIE selon arbitrages futurs.
        """
        result = resolve_typology_for_scope({"site_id": 3}, db)
        assert result == OrganizationTypology.UNKNOWN


# ── Tests Option A purs (sans DB) ────────────────────────────────────────


def _mock_site(nom: str, naf_code: str, surface: float):
    """Crée un Site mock pour tester _typology_dominant_for_sites isolément."""
    return SimpleNamespace(nom=nom, naf_code=naf_code, surface_m2=surface)


class TestOptionAUnknownExcluded:
    """Source-guards Option A : UNKNOWN exclu du calcul dominant."""

    def test_unknown_excluded_from_dominant_calculation(self):
        """Si UNKNOWN > GRAND_GROUPE en surface, dominant reste GRAND_GROUPE."""
        sites = [
            _mock_site("Siège", "6820B", 1000),  # GRAND_GROUPE
            _mock_site("Entrepôt", "5210B", 5000),  # UNKNOWN (5x plus grand)
        ]
        result = _typology_dominant_for_sites(sites, scope_label="test")
        assert result in (OrganizationTypology.GRAND_GROUPE, OrganizationTypology.ETI_TERTIAIRE), (
            "Option A : UNKNOWN doit être exclu même s'il domine en surface"
        )

    def test_dominant_among_known_typologies(self):
        """Plusieurs typologies connues + UNKNOWN → dominant = max(known)."""
        sites = [
            _mock_site("École", "8510Z", 800),  # ERP
            _mock_site("Boulangerie", "4724Z", 200),  # COMMERCE
            _mock_site("Siège", "6420Z", 600),  # GRAND_GROUPE
            _mock_site("Mystère", "0111Z", 5000),  # UNKNOWN (massif mais exclu)
        ]
        result = _typology_dominant_for_sites(sites, scope_label="test")
        assert result == OrganizationTypology.ERP  # 800 > 600 > 200

    def test_all_unknown_returns_unknown(self):
        """Si 100 % des sites sont UNKNOWN → typologie UNKNOWN (pas crash)."""
        # Phase 11.C : sidérurgie (24) → INDUSTRIE désormais. On utilise
        # uniquement des NAF non mappés (agriculture 0111Z + entreposage 5210B).
        sites = [
            _mock_site("Ferme", "0111Z", 1000),  # UNKNOWN (agriculture)
            _mock_site("Entrepôt", "5210B", 5000),  # UNKNOWN (entreposage)
        ]
        result = _typology_dominant_for_sites(sites, scope_label="test")
        assert result == OrganizationTypology.UNKNOWN

    def test_no_sites_returns_unknown(self):
        """Liste vide → UNKNOWN (jamais d'exception)."""
        result = _typology_dominant_for_sites([], scope_label="test")
        assert result == OrganizationTypology.UNKNOWN

    def test_sites_without_surface_fallback_count(self):
        """Sites avec surface_m2 = 0 → fallback compte par occurrence."""
        sites = [
            _mock_site("A", "8510Z", 0),  # ERP
            _mock_site("B", "8520Z", 0),  # ERP
            _mock_site("C", "6420Z", 0),  # GRAND_GROUPE
            _mock_site("D", "5210B", 0),  # UNKNOWN exclu
        ]
        result = _typology_dominant_for_sites(sites, scope_label="test")
        assert result == OrganizationTypology.ERP  # 2 ERP > 1 GG (UNKNOWN exclu)


class TestUnknownWarning:
    """Source-guards : log warning si UNKNOWN > 30 % surface."""

    def test_warning_logged_when_unknown_exceeds_30pct(self, caplog):
        """HELIOS-like : 34,3 % UNKNOWN → warning explicit."""
        sites = [
            _mock_site("Siège", "6820B", 3500),
            _mock_site("Lyon", "6820B", 1200),
            _mock_site("Toulouse", "5210B", 6000),  # UNKNOWN 34,3 %
            _mock_site("Nice", "5510Z", 4000),
            _mock_site("Marseille", "8520Z", 2800),
        ]
        with caplog.at_level(logging.WARNING, logger="promeos.narrative.typology_resolver"):
            result = _typology_dominant_for_sites(sites, scope_label="org_id=1")
        assert result in (OrganizationTypology.GRAND_GROUPE, OrganizationTypology.ETI_TERTIAIRE)  # confirmé Option A
        # Vérifier qu'au moins un warning UNKNOWN a été loggé
        unknown_warnings = [r for r in caplog.records if r.levelname == "WARNING" and "UNKNOWN" in r.message]
        assert unknown_warnings, (
            f"Phase 1.2 Option A : warning UNKNOWN > 30 % attendu. Logs récents : {[r.message for r in caplog.records]}"
        )

    def test_no_warning_when_unknown_under_30pct(self, caplog):
        """Surface UNKNOWN < 30 % → pas de warning (silence éditorial log)."""
        sites = [
            _mock_site("Siège", "6820B", 8000),
            _mock_site("Toulouse", "5210B", 1000),  # UNKNOWN ~ 11 %
        ]
        with caplog.at_level(logging.WARNING, logger="promeos.narrative.typology_resolver"):
            result = _typology_dominant_for_sites(sites, scope_label="org_id=test")
        assert result in (OrganizationTypology.GRAND_GROUPE, OrganizationTypology.ETI_TERTIAIRE)
        unknown_warnings = [
            r
            for r in caplog.records
            if r.levelname == "WARNING" and "UNKNOWN" in r.message and "promeos.narrative.typology_resolver" in r.name
        ]
        assert not unknown_warnings, (
            f"Pas de warning attendu si UNKNOWN < {UNKNOWN_SURFACE_WARNING_THRESHOLD_PCT} %, "
            f"trouvé : {[r.message for r in unknown_warnings]}"
        )


class TestScopeFallbacks:
    """Source-guards : fallback robustes."""

    def test_typology_resolver_no_sites_unknown(self, db):
        """Org_id inexistant → UNKNOWN (jamais d'exception)."""
        result = resolve_typology_for_scope({"org_id": 99999}, db)
        assert result == OrganizationTypology.UNKNOWN

    def test_typology_resolver_empty_scope_unknown(self, db):
        """Scope vide → UNKNOWN."""
        result = resolve_typology_for_scope({}, db)
        assert result == OrganizationTypology.UNKNOWN

    def test_typology_resolver_invalid_site_id_unknown(self, db):
        """site_id inexistant → UNKNOWN."""
        result = resolve_typology_for_scope({"site_id": 99999}, db)
        assert result == OrganizationTypology.UNKNOWN

    def test_typology_resolver_priority_site_over_org(self, db):
        """Si site_id ET org_id présents, site_id l'emporte (plus spécifique)."""
        # Site 4 = Hôtel Nice (COMMERCE) ; org_id=1 = HELIOS (GRAND_GROUPE)
        # Le scope priorise site_id → COMMERCE
        result = resolve_typology_for_scope({"site_id": 4, "org_id": 1}, db)
        assert result == OrganizationTypology.COMMERCE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
