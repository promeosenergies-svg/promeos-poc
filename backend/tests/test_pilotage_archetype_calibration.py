"""
PROMEOS - Tests du calibrage archetypes Barometre Flex 2026.

Source de reference : Barometre Flex 2026 RTE / Enedis / GIMELEC (avril 2026).
Verifie la coherence structurelle et quantitative du dict
`ARCHETYPE_CALIBRATION_2024` ainsi que l'integration dans
`compute_potential_score` (priorite calibrage + fallback heuristique).
"""

from __future__ import annotations

import pytest

from services.pilotage.constants import (
    ARCHETYPE_CALIBRATION_2024,
    ARCHETYPE_RULES,
    TAUX_DECALABLE_MAX,
    TAUX_DECALABLE_MIN,
)
from services.pilotage.score_potential import compute_potential_score


EXPECTED_ARCHETYPES = {
    "BUREAU_STANDARD",
    "COMMERCE_ALIMENTAIRE",
    "COMMERCE_SPECIALISE",
    "LOGISTIQUE_FRIGO",
    "ENSEIGNEMENT",
    "SANTE",
    "HOTELLERIE",
    "INDUSTRIE_LEGERE",
}


def test_all_8_archetypes_calibrated():
    """Les 8 archetypes Barometre Flex 2026 doivent etre dans ARCHETYPE_CALIBRATION_2024."""
    actual = set(ARCHETYPE_CALIBRATION_2024.keys())
    missing = EXPECTED_ARCHETYPES - actual
    assert not missing, f"Archetypes manquants dans le calibrage 2024 : {missing}"
    # Chaque archetype calibre doit exposer la structure attendue.
    required_fields = {
        "taux_decalable_moyen",
        "plages_pointe_h",
        "conso_journaliere_pointe_pct",
        "source",
    }
    for code in EXPECTED_ARCHETYPES:
        entry = ARCHETYPE_CALIBRATION_2024[code]
        assert required_fields <= entry.keys(), f"{code} : champs manquants {required_fields - entry.keys()}"
        assert "Baromètre Flex 2026" in entry["source"] or "GIMELEC" in entry["source"], (
            f"{code} : source doit citer le Barometre Flex 2026 / GIMELEC (got {entry['source']!r})"
        )


def test_taux_decalable_within_sanity_bounds():
    """Tous les taux decalables doivent rester dans [0.10, 0.60] (bornes sanity)."""
    for code, entry in ARCHETYPE_CALIBRATION_2024.items():
        taux = entry["taux_decalable_moyen"]
        assert isinstance(taux, float), f"{code} : taux_decalable_moyen doit etre un float"
        assert TAUX_DECALABLE_MIN <= taux <= TAUX_DECALABLE_MAX, (
            f"{code} : taux_decalable_moyen={taux} hors bornes [{TAUX_DECALABLE_MIN}, {TAUX_DECALABLE_MAX}]"
        )


def test_plages_pointe_non_chevauchantes():
    """
    Pour chaque archetype, les plages de pointe doivent etre disjointes
    (pas de tranche horaire dans deux plages simultanement). On autorise
    toutefois la plage unique [0, 24) pour les sites 24/7.
    """
    for code, entry in ARCHETYPE_CALIBRATION_2024.items():
        plages = entry["plages_pointe_h"]
        assert plages, f"{code} : plages_pointe_h ne doit pas etre vide"
        # Bornes coherentes
        for h_debut, h_fin in plages:
            assert 0 <= h_debut < h_fin <= 24, f"{code} : plage ({h_debut}, {h_fin}) invalide (0 <= debut < fin <= 24)"
        # Pas de chevauchement entre deux plages du meme archetype
        plages_sorted = sorted(plages, key=lambda p: p[0])
        for (a_deb, a_fin), (b_deb, b_fin) in zip(plages_sorted, plages_sorted[1:]):
            assert a_fin <= b_deb, f"{code} : plages {(a_deb, a_fin)} et {(b_deb, b_fin)} se chevauchent"


def test_compute_potential_score_uses_calibration_when_present():
    """compute_potential_score doit puiser dans ARCHETYPE_CALIBRATION_2024 si dispo."""
    # Archetype calibre : LOGISTIQUE_FRIGO (taux 55%, pointe 100%)
    result = compute_potential_score("LOGISTIQUE_FRIGO")
    assert result["used_calibration"] is True
    assert result["taux_decalable"] == pytest.approx(0.55)
    assert result["conso_pointe_pct"] == pytest.approx(1.0)
    assert "Baromètre Flex 2026" in result["source"]
    # Score doit etre plus eleve que celui d'un bureau standard (logique metier)
    result_bureau = compute_potential_score("BUREAU_STANDARD")
    assert result_bureau["used_calibration"] is True
    assert result["score"] > result_bureau["score"], "LOGISTIQUE_FRIGO doit avoir un score superieur a BUREAU_STANDARD"


def test_compute_potential_score_falls_back_on_unknown_archetype():
    """Archetype inconnu => fallback heuristique (comportement historique preserve)."""
    result = compute_potential_score("ARCHETYPE_INCONNU_XYZ")
    assert result["used_calibration"] is False
    assert "Heuristique" in result["source"]
    # Le score reste dans [0, 100]
    assert 0.0 <= result["score"] <= 100.0
    # Idem pour archetype None (meter sans signature)
    result_none = compute_potential_score(None)
    assert result_none["used_calibration"] is False
    assert 0.0 <= result_none["score"] <= 100.0


def test_archetype_rules_coherent_with_calibration():
    """
    Sanity cross-check : les archetypes calibres doivent tous exister dans
    ARCHETYPE_RULES (evolution, pas rupture) pour eviter qu'un code soit
    calibre mais pas detectable.
    """
    rules_codes = set(ARCHETYPE_RULES.keys())
    for code in EXPECTED_ARCHETYPES:
        assert code in rules_codes, f"{code} calibre mais absent de ARCHETYPE_RULES (rupture de coherence)"
