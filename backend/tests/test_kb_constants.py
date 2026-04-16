"""
Tests KB Constants — vérifie l'ingestion et la cohérence des constantes métier.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.kb.store import KBStore
from scripts.kb_ingest_constants import CONSTANTS, ingest_constants_to_kb


@pytest.fixture(scope="module")
def kb_store():
    """Ingère les constantes et retourne un KBStore connecté."""
    ingest_constants_to_kb()
    return KBStore()


class TestConstantsIngestion:
    """Phase 1.3 — les 11 constantes sont dans kb.db"""

    def test_all_constants_ingested(self, kb_store):
        for const in CONSTANTS:
            item = kb_store.get_item(const["id"])
            assert item is not None, f"Constante {const['id']} absente de kb.db"

    def test_count_constants(self, kb_store):
        count = 0
        for const in CONSTANTS:
            if kb_store.get_item(const["id"]):
                count += 1
        assert count == len(CONSTANTS), f"Attendu {len(CONSTANTS)}, trouvé {count}"

    def test_co2_elec_value(self, kb_store):
        item = kb_store.get_item("constants.co2_elec_france")
        assert item is not None
        assert "0.052" in item["summary"]
        assert item["confidence"] == "high"
        assert item["status"] == "validated"

    def test_co2_gaz_value(self, kb_store):
        item = kb_store.get_item("constants.co2_gaz_france")
        assert item is not None
        assert "0.227" in item["summary"]

    def test_accise_t1_value(self, kb_store):
        item = kb_store.get_item("constants.accise_elec_t1_2026")
        assert item is not None
        assert "30.85" in item["summary"]

    def test_accise_t2_value(self, kb_store):
        item = kb_store.get_item("constants.accise_elec_t2_2026")
        assert item is not None
        assert "26.58" in item["summary"]

    def test_accise_gaz_value(self, kb_store):
        item = kb_store.get_item("constants.accise_gaz_2026")
        assert item is not None
        assert "10.73" in item["summary"]

    def test_cta_value(self, kb_store):
        item = kb_store.get_item("constants.cta_pct_2026")
        assert item is not None
        assert "27.04" in item["summary"]

    def test_dt_penalties(self, kb_store):
        nc = kb_store.get_item("constants.dt_penalty_non_conforme")
        ar = kb_store.get_item("constants.dt_penalty_a_risque")
        assert nc is not None
        assert ar is not None
        assert "7 500" in nc["summary"] or "7500" in nc["summary"]
        assert "3 750" in ar["summary"] or "3750" in ar["summary"]

    def test_no_validated_low_combination(self, kb_store):
        """HARD RULE : jamais validated + confidence=low"""
        for const in CONSTANTS:
            item = kb_store.get_item(const["id"])
            if item and item["status"] == "validated":
                assert item["confidence"] != "low", f"{const['id']} est validated+low — violation hard rule"


class TestNoDriftWithSource:
    """Vérifie que les constantes KB == les valeurs dans config/"""

    def test_co2_elec_matches_config(self):
        from config.emission_factors import EMISSION_FACTORS

        assert EMISSION_FACTORS["ELEC"]["kgco2e_per_kwh"] == 0.052

    def test_co2_gaz_matches_config(self):
        from config.emission_factors import EMISSION_FACTORS

        assert EMISSION_FACTORS["GAZ"]["kgco2e_per_kwh"] == 0.227

    def test_penalties_match_config(self):
        from config.emission_factors import BASE_PENALTY_EURO, A_RISQUE_PENALTY_EURO

        assert BASE_PENALTY_EURO == 7500
        assert A_RISQUE_PENALTY_EURO == 3750

    def test_bacs_thresholds_match_config(self):
        from config.emission_factors import BACS_SEUIL_HAUT, BACS_SEUIL_BAS

        assert BACS_SEUIL_HAUT == 290.0
        assert BACS_SEUIL_BAS == 70.0
