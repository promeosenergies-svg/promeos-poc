"""
PROMEOS — Source-guard Phase 1.8 : dictionnaire acronymes → récit (Q6).

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.8.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest

from doctrine.acronyms import (
    ACRONYM_TO_NARRATIVE,
    ACRONYMS_FORBIDDEN_IN_TITLES,
    has_forbidden_acronym,
    transform_acronym,
)


# ── Dictionnaire ────────────────────────────────────────────────────────


class TestAcronymDictionary:
    def test_12_canonical_entries(self):
        """Doctrine §6.4 + prompt §2.B Phase 1.8 : 12 entrées canoniques minimum."""
        assert len(ACRONYM_TO_NARRATIVE) >= 12

    def test_all_canonical_acronyms_present(self):
        canonical = {"DT", "BACS", "GTB", "TURPE", "APER", "OPERAT", "CDC", "VNU", "CBAM", "ARENH", "CEE", "EPEX"}
        assert canonical.issubset(set(ACRONYM_TO_NARRATIVE.keys()))

    def test_forbidden_subset_8_strict(self):
        """ACRONYMS_FORBIDDEN_IN_TITLES = subset critique 8 acronymes."""
        expected = {"DT", "BACS", "GTB", "TURPE", "APER", "VNU", "CBAM", "ARENH"}
        assert set(ACRONYMS_FORBIDDEN_IN_TITLES) == expected


# ── transform_acronym narrative mode ────────────────────────────────────


class TestTransformAcronymNarrative:
    def test_replaces_known_acronym(self):
        assert transform_acronym("Le DT impose -40%") == "Le Décret Tertiaire impose -40%"

    def test_replaces_multiple_occurrences(self):
        result = transform_acronym("DT et BACS convergent")
        assert "Décret Tertiaire" in result
        assert "BACS" in result
        assert "Décret BACS" in result

    def test_unknown_acronym_kept_as_is(self):
        # "XYZ" non glossé → laissé tel quel (no-op safe)
        assert transform_acronym("XYZ inconnu") == "XYZ inconnu"

    def test_word_boundary_respected(self):
        """'DT' dans 'BUDGET' ne doit pas être transformé."""
        assert "Décret Tertiaire" not in transform_acronym("Le BUDGET 2026")

    def test_longer_acronym_matches_first(self):
        """OPERAT doit matcher avant 'OP' fictif."""
        assert "déclaration énergie tertiaire" in transform_acronym("Plateforme OPERAT")

    def test_empty_or_none_safe(self):
        assert transform_acronym("") == ""
        assert transform_acronym(None) is None


# ── transform_acronym inline mode ───────────────────────────────────────


class TestTransformAcronymInline:
    def test_inline_first_occurrence_glossed(self):
        result = transform_acronym("DT impose", mode="inline")
        assert "Décret Tertiaire (DT)" == result.split(" impose")[0]

    def test_inline_second_occurrence_naked(self):
        """2e occurrence du même acronyme = nu (déjà glossé)."""
        result = transform_acronym("DT impose. Le DT prévoit.", mode="inline")
        # 1ère = glossée
        assert "Décret Tertiaire (DT)" in result
        # 2e = nu — vérifier qu'il n'y a qu'UNE occurrence de la forme glossée
        assert result.count("Décret Tertiaire (DT)") == 1


# ── has_forbidden_acronym (source-guard helper) ─────────────────────────


class TestHasForbiddenAcronym:
    def test_detects_forbidden(self):
        assert has_forbidden_acronym("Le DT impose") == "DT"
        assert has_forbidden_acronym("Décret BACS critique") == "BACS"

    def test_returns_none_when_clean(self):
        assert has_forbidden_acronym("Décret Tertiaire impose -40%") is None

    def test_word_boundary_prevents_false_positive(self):
        assert has_forbidden_acronym("Le BUDGET 2026") is None

    def test_empty_title_safe(self):
        assert has_forbidden_acronym("") is None
        assert has_forbidden_acronym(None) is None


# ── Source-guard Vue Exécutive (anti-régression) ────────────────────────


class TestAcronymsTransformedVueExecutive:
    def test_no_forbidden_acronym_in_canonical_titles(self):
        """Les titres canoniques de la Vue Exécutive doivent être transformés.

        Liste alignée avec le rendu maquette `cockpit-synthese-strategique.html`
        — vérifie qu'aucun titre testé ne contient d'acronyme interdit brut.
        """
        canonical_clean_titles = [
            "Trajectoire 2030 — risque Décret Tertiaire",
            "Exposition réglementaire — pilotage CVC obligatoire et obligation solaire parking",
            "Versement Nucléaire Universel — impact contractuel",
            "Tarif d'acheminement réseau — composantes",
        ]
        for title in canonical_clean_titles:
            assert has_forbidden_acronym(title) is None, f"Titre '{title}' contient un acronyme interdit"

    def test_dirty_titles_caught(self):
        """Les titres bruts (anti-pattern §6.3) sont détectés et transformés."""
        dirty = "Trajectoire DT — risque DT 2030 + BACS impacts"
        assert has_forbidden_acronym(dirty) == "DT" or has_forbidden_acronym(dirty) == "BACS"
        cleaned = transform_acronym(dirty)
        assert "DT" not in cleaned.split(" ")  # pas DT comme mot isolé
        assert "Décret Tertiaire" in cleaned
