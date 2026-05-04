"""
PROMEOS — Sprint C-3 Phase 3.2 : Tests regulatory_sources_loader.

Vérifie le SoT `sources_reglementaires.yaml` + service loader (~68 termes / 9 domaines) :
- Structure YAML valide + schéma cohérent (value, unit, domain, source, formula, notes)
- Cache `@lru_cache(maxsize=1)` actif + reload_* fonctionnel
- Helpers typés par domaine (CO2, accises, compliance penalties, DT milestones, audit SMÉ)
- Lookup par term_id + filtre par domaine
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Structure YAML de base ──────────────────────────────────────────────────


def test_load_yaml_returns_dict_with_terms_key():
    from config.regulatory_sources_loader import load_regulatory_sources

    data = load_regulatory_sources()
    assert isinstance(data, dict)
    assert "terms" in data
    assert isinstance(data["terms"], dict)


def test_yaml_has_all_required_top_level_keys():
    from config.regulatory_sources_loader import load_regulatory_sources

    data = load_regulatory_sources()
    required = {"version", "last_updated", "sprint_origin", "terms"}
    assert required.issubset(set(data.keys())), f"Top-level keys manquantes: {required - set(data.keys())}"


def test_yaml_has_at_least_60_terms():
    """Volumétrie cible Sprint C-3 Phase 3.2 = ~68-100 termes."""
    from config.regulatory_sources_loader import list_all_term_ids

    terms = list_all_term_ids()
    assert len(terms) >= 60, f"Trop peu de termes: {len(terms)} (attendu ≥60)"


# ─── API publique : get_term ─────────────────────────────────────────────────


def test_get_term_by_id_returns_dict():
    from config.regulatory_sources_loader import get_term

    term = get_term("CO2_FACTOR_ELEC_KGCO2_PER_KWH")
    assert isinstance(term, dict)
    assert term["value"] == 0.052
    assert term["unit"] == "kgCO2e/kWh"
    assert term["domain"] == "co2"


def test_get_term_unknown_raises_keyerror():
    from config.regulatory_sources_loader import get_term

    with pytest.raises(KeyError, match="UNKNOWN_TERM_XYZ"):
        get_term("UNKNOWN_TERM_XYZ")


def test_get_term_value_returns_value_only():
    from config.regulatory_sources_loader import get_term_value

    assert get_term_value("CO2_FACTOR_ELEC_KGCO2_PER_KWH") == 0.052
    assert get_term_value("COMPLIANCE_DT_PENALTY_EUR") == 7500


# ─── Filtres par domaine ─────────────────────────────────────────────────────


def test_get_terms_by_domain_co2_returns_3_terms():
    from config.regulatory_sources_loader import get_terms_by_domain

    co2_terms = get_terms_by_domain("co2")
    assert len(co2_terms) == 3, f"Attendu 3 termes CO2, trouvé {len(co2_terms)}"
    assert "CO2_FACTOR_ELEC_KGCO2_PER_KWH" in co2_terms
    assert "CO2_FACTOR_GAZ_NATUREL_KGCO2_PER_KWH" in co2_terms
    assert "CO2_FACTOR_GNL_KGCO2_PER_KWH" in co2_terms


def test_list_all_domains_returns_9_distinct():
    from config.regulatory_sources_loader import list_all_domains

    domains = list_all_domains()
    expected = {"co2", "tarifs", "accises", "tva", "dt", "bacs", "aper", "audit_sme", "operat"}
    assert set(domains) == expected, f"Domaines incohérents: {set(domains) ^ expected}"


# ─── Schema strict de chaque term ────────────────────────────────────────────


def test_each_term_has_required_keys():
    """Tous les termes doivent avoir : value, unit, domain, source, formula, notes."""
    from config.regulatory_sources_loader import load_regulatory_sources

    required_keys = {"value", "unit", "domain", "source", "formula", "notes"}
    data = load_regulatory_sources()
    for tid, term in data["terms"].items():
        missing = required_keys - set(term.keys())
        assert not missing, f"Term {tid} manque keys: {missing}"


def test_each_term_source_has_required_keys():
    """source.label, source.url, source.version, source.effective_date, source.legal_reference."""
    from config.regulatory_sources_loader import load_regulatory_sources

    required_source_keys = {"label", "url", "version", "effective_date", "legal_reference"}
    data = load_regulatory_sources()
    for tid, term in data["terms"].items():
        source = term.get("source", {})
        missing = required_source_keys - set(source.keys())
        assert not missing, f"Term {tid} source manque keys: {missing}"


# ─── Cache LRU ───────────────────────────────────────────────────────────────


def test_lru_cache_returns_same_dict_object():
    """2 appels successifs → même objet en mémoire (cache hit)."""
    from config.regulatory_sources_loader import load_regulatory_sources, reload_regulatory_sources

    reload_regulatory_sources()  # garantit cache fresh
    d1 = load_regulatory_sources()
    d2 = load_regulatory_sources()
    assert d1 is d2, "Cache LRU non actif — chaque appel relit le fichier"


def test_reload_clears_cache():
    """reload_regulatory_sources() invalide cache → nouveau dict object."""
    from config.regulatory_sources_loader import load_regulatory_sources, reload_regulatory_sources

    d1 = load_regulatory_sources()
    d2 = reload_regulatory_sources()
    # Après reload, c'est un objet distinct
    assert d1 is not d2, "reload_regulatory_sources() n'a pas invalidé le cache"


# ─── Helpers typés par domaine ───────────────────────────────────────────────


def test_get_co2_factor_elec_returns_0_052():
    from config.regulatory_sources_loader import get_co2_factor

    assert get_co2_factor("elec") == 0.052


def test_get_co2_factor_gaz_returns_0_227():
    from config.regulatory_sources_loader import get_co2_factor

    assert get_co2_factor("gaz") == 0.227


def test_get_co2_factor_gnl_returns_0_238():
    from config.regulatory_sources_loader import get_co2_factor

    assert get_co2_factor("gnl") == 0.238


def test_get_co2_factor_unknown_raises_valueerror():
    from config.regulatory_sources_loader import get_co2_factor

    with pytest.raises(ValueError, match="Fuel inconnu"):
        get_co2_factor("charbon")


def test_get_compliance_penalty_dt_returns_7500():
    from config.regulatory_sources_loader import get_compliance_penalty

    assert get_compliance_penalty("dt") == 7500


def test_get_compliance_penalty_dt_at_risk_returns_3750():
    from config.regulatory_sources_loader import get_compliance_penalty

    assert get_compliance_penalty("dt_at_risk") == 3750


def test_get_compliance_penalty_bacs_returns_1500():
    from config.regulatory_sources_loader import get_compliance_penalty

    assert get_compliance_penalty("bacs") == 1500


def test_get_compliance_penalty_unknown_raises_valueerror():
    from config.regulatory_sources_loader import get_compliance_penalty

    with pytest.raises(ValueError, match="Réglementation inconnue"):
        get_compliance_penalty("unknown_reg")


def test_get_accise_rate_elec_returns_t2():
    from config.regulatory_sources_loader import get_accise_rate

    assert get_accise_rate("elec") == 26.58
    assert get_accise_rate("elec_t1") == 30.85
    assert get_accise_rate("gaz") == 10.73


def test_get_dt_milestone_returns_negative_pct():
    from config.regulatory_sources_loader import get_dt_milestone

    assert get_dt_milestone(2030) == -40.0
    assert get_dt_milestone(2040) == -50.0
    assert get_dt_milestone(2050) == -60.0


def test_get_dt_milestone_unknown_year_raises():
    from config.regulatory_sources_loader import get_dt_milestone

    with pytest.raises(ValueError, match="Année jalon DT inconnue"):
        get_dt_milestone(2025)


def test_get_audit_sme_threshold_periodic_returns_2_75():
    from config.regulatory_sources_loader import get_audit_sme_threshold

    assert get_audit_sme_threshold("audit_4ans") == 2.75
    assert get_audit_sme_threshold("iso50001") == 23.6
