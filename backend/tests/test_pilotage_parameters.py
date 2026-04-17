"""
PROMEOS - Tests ParameterStore pilotage (Sprint 2 Item 6 — migration 7
constantes MVP hardcodées vers YAML versionné sourcé).

Vérifie :
    1. Happy path : chaque code retourne la valeur YAML attendue
    2. Scope archetype : HEURES_FAVORABLES_AN récupéré par archetype spécifique
       prioritaire sur wildcard "*"
    3. Fallback wildcard : archetype inconnu → wildcard (médiane tertiaire)
    4. Fallback défensif : YAML vide / code inconnu + default fourni → default
    5. Missing : code inconnu sans default → source="missing", value=0
    6. Traçabilité : chaque résolution porte source + valid_from + unite
"""

from __future__ import annotations

import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.tarif_loader import reload_tarifs  # noqa: E402
from services.pilotage.parameters import (  # noqa: E402
    KNOWN_PILOTAGE_CODES,
    PilotageParameterResolution,
    get_pilotage_param,
    get_pilotage_value,
)


@pytest.fixture(autouse=True)
def _reset_yaml_cache():
    """Reload YAML cache entre tests pour isoler."""
    reload_tarifs()
    yield
    reload_tarifs()


# ---------------------------------------------------------------------------
# Test 1 : Happy path — chaque code retourne la valeur YAML attendue
# ---------------------------------------------------------------------------
class TestHappyPath:
    def test_heures_fenetres_favorables_an(self):
        r = get_pilotage_param("HEURES_FENETRES_FAVORABLES_AN", at_date=date(2026, 4, 1))
        assert r.source == "yaml"
        assert r.value == 200
        assert r.unite == "h/an"
        assert r.source_ref is not None
        assert "Baromètre Flex 2026" in r.source_ref

    def test_spread_moyen_eur_mwh(self):
        r = get_pilotage_param("SPREAD_MOYEN_EUR_MWH", at_date=date(2026, 4, 1))
        assert r.source == "yaml"
        assert r.value == 60.0
        assert r.unite == "EUR/MWh"

    def test_spread_pointe_eur_mwh(self):
        r = get_pilotage_param("SPREAD_POINTE_EUR_MWH", at_date=date(2026, 4, 1))
        assert r.source == "yaml"
        assert r.value == 120.0

    def test_jours_effacement_par_an(self):
        r = get_pilotage_param("JOURS_EFFACEMENT_PAR_AN", at_date=date(2026, 4, 1))
        assert r.source == "yaml"
        assert r.value == 200
        assert r.unite == "j/an"

    def test_cee_bacs_eur_m2(self):
        r = get_pilotage_param("CEE_BACS_EUR_M2", at_date=date(2026, 4, 1))
        assert r.source == "yaml"
        assert r.value == 3.5
        assert r.unite == "EUR/m2"
        assert "BAT-TH-116" in r.source_ref

    def test_spread_eur_par_kwh(self):
        r = get_pilotage_param("SPREAD_EUR_PAR_KWH", at_date=date(2026, 4, 1))
        assert r.source == "yaml"
        assert r.value == 0.08
        assert r.unite == "EUR/kWh"


# ---------------------------------------------------------------------------
# Test 2 : Scope archetype — prioritaire sur wildcard
# ---------------------------------------------------------------------------
class TestArchetypeScopeOverride:
    @pytest.mark.parametrize(
        "archetype,attendu",
        [
            ("BUREAU_STANDARD", 900),
            ("COMMERCE_ALIMENTAIRE", 1400),
            ("COMMERCE_SPECIALISE", 800),
            ("LOGISTIQUE_FRIGO", 1600),
            ("ENSEIGNEMENT", 700),
            ("SANTE", 600),
            ("HOTELLERIE", 1100),
            ("INDUSTRIE_LEGERE", 1000),
        ],
    )
    def test_heures_favorables_par_archetype(self, archetype, attendu):
        r = get_pilotage_param(
            "HEURES_FAVORABLES_AN",
            at_date=date(2026, 4, 1),
            archetype=archetype,
        )
        assert r.source == "yaml"
        assert r.value == attendu, f"{archetype}: attendu {attendu}, obtenu {r.value}"
        assert r.scope.get("archetype") == archetype, f"scope doit etre precis, pas wildcard"

    def test_heures_favorables_wildcard_fallback_archetype_inconnu(self):
        """Archetype inexistant au YAML → retombe sur wildcard '*' (800h médiane)."""
        r = get_pilotage_param(
            "HEURES_FAVORABLES_AN",
            at_date=date(2026, 4, 1),
            archetype="ARCHETYPE_INEXISTANT_FOO",
        )
        assert r.source == "yaml"
        assert r.value == 800
        assert r.scope.get("archetype") == "*"

    def test_heures_favorables_sans_archetype_prend_wildcard(self):
        """archetype=None → seul le scope wildcard '*' est considere."""
        r = get_pilotage_param(
            "HEURES_FAVORABLES_AN",
            at_date=date(2026, 4, 1),
            archetype=None,
        )
        assert r.source == "yaml"
        assert r.value == 800  # médiane wildcard


# ---------------------------------------------------------------------------
# Test 3 : Fallback défensif + code inconnu
# ---------------------------------------------------------------------------
class TestFallbackAndMissing:
    def test_fallback_when_code_unknown_with_default(self, caplog):
        """Code hors KNOWN_PILOTAGE_CODES avec default → fallback (pas crash)."""
        import logging

        with caplog.at_level(logging.WARNING):
            r = get_pilotage_param(
                "FOO_BAR_UNKNOWN",
                at_date=date(2026, 4, 1),
                default=42.0,
            )
        assert r.source == "fallback"
        assert r.value == 42.0
        assert "hardcoded fallback" in (r.source_ref or "")

    def test_missing_when_code_unknown_no_default(self, caplog):
        """Code inconnu sans default → source='missing', value=0 (pas crash)."""
        import logging

        with caplog.at_level(logging.WARNING):
            r = get_pilotage_param("BAZ_UNKNOWN_QUX", at_date=date(2026, 4, 1))
        assert r.source == "missing"
        assert r.value == 0

    def test_get_pilotage_value_raccourci(self):
        """Helper get_pilotage_value retourne la valeur seule (int/float)."""
        v = get_pilotage_value("SPREAD_MOYEN_EUR_MWH", at_date=date(2026, 4, 1))
        assert v == 60.0

    def test_get_pilotage_value_default_si_missing(self):
        v = get_pilotage_value(
            "INEXISTENT_XYZ",
            at_date=date(2026, 4, 1),
            default=1234.0,
        )
        assert v == 1234.0


# ---------------------------------------------------------------------------
# Test 4 : Traçabilité — serialisation to_trace + KNOWN_PILOTAGE_CODES
# ---------------------------------------------------------------------------
class TestAuditTrail:
    def test_to_trace_serializable(self):
        r = get_pilotage_param("CEE_BACS_EUR_M2", at_date=date(2026, 4, 1))
        trace = r.to_trace()
        assert trace["code"] == "CEE_BACS_EUR_M2"
        assert trace["source"] == "yaml"
        assert trace["valid_from"] == "2025-01-01"
        assert trace["unite"] == "EUR/m2"
        assert "BAT-TH-116" in trace["source_ref"]

    def test_known_pilotage_codes_complets(self):
        """Sanity : les 7 codes MVP sont enregistres."""
        required = {
            "HEURES_FENETRES_FAVORABLES_AN",
            "SPREAD_MOYEN_EUR_MWH",
            "SPREAD_POINTE_EUR_MWH",
            "JOURS_EFFACEMENT_PAR_AN",
            "CEE_BACS_EUR_M2",
            "HEURES_FAVORABLES_AN",
            "SPREAD_EUR_PAR_KWH",
        }
        assert required.issubset(KNOWN_PILOTAGE_CODES)

    def test_valid_from_present_pour_chaque_code(self):
        """Chaque code known doit avoir un valid_from (audit trail complet)."""
        for code in [
            "HEURES_FENETRES_FAVORABLES_AN",
            "SPREAD_MOYEN_EUR_MWH",
            "SPREAD_POINTE_EUR_MWH",
            "JOURS_EFFACEMENT_PAR_AN",
            "CEE_BACS_EUR_M2",
            "SPREAD_EUR_PAR_KWH",
        ]:
            r = get_pilotage_param(code, at_date=date(2026, 4, 1))
            assert r.source == "yaml", f"{code} doit etre resolu YAML"
            assert r.valid_from is not None, f"{code} doit exposer valid_from"
            assert r.source_ref is not None, f"{code} doit exposer source_ref"

    def test_resolution_instance_type(self):
        """Sanity : le résultat est bien typé PilotageParameterResolution."""
        r = get_pilotage_param("CEE_BACS_EUR_M2", at_date=date(2026, 4, 1))
        assert isinstance(r, PilotageParameterResolution)
