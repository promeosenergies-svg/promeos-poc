"""Source-guards Conformite S1 OPERAT/DEET (2026-05-27).

Verrous structurels post-sprint claude/conformite-s1-operat-deet-p0.
Closure des 4 divergences P0 OPERAT/DEET identifiees memoire 2026-05-27 et
confirmees par cross-check officiel Legifrance (cf.
docs/audits/crosscheck_legifrance_operat_deet_2026_05_27.md) :

  G1. Constantes OPERAT separees ADEME (D1) — 0,064 vs 0,052 distinctes.
  G2. Constantes EP OPERAT separees RE2020 (D2) — 2,3 vs 1,9 distinctes.
  G3. Helpers d'acces (get_operat_emission_factor / get_operat_ep_coefficient)
      avec docstring scope OPERAT et fail-closed sur vecteurs inconnus.
  G4. Validation annee de reference OPERAT (D4) — plage 2010-2022 + butoir
      30/09/2027 + flag is_first_full_year_of_operation explicite.
  G5. TRI par typologie (D5) — 3 typologies STRUCTURAL_ENVELOPE (30 ans) /
      ENERGY_EQUIPMENT (15 ans) / OPTIMIZATION_SYSTEM (10 ans).
  G6. ModulationAction.typologie ajoute + ModulationResult.tri_par_typologie
      + decision disproportion_globale exposee.
  G7. Aucun melange silencieux : fichiers ADEME/RE2020 ont avertissements
      explicites pointant vers operat_constants.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OPERAT_CONSTANTS = REPO_ROOT / "config" / "operat_constants.py"
EMISSION_FACTORS = REPO_ROOT / "config" / "emission_factors.py"
ENERGY_INTENSITY = REPO_ROOT / "services" / "energy_intensity_service.py"
OPERAT_TRAJECTORY = REPO_ROOT / "services" / "operat_trajectory.py"
TERTIAIRE_MODULATION = REPO_ROOT / "services" / "tertiaire_modulation_service.py"
TERTIAIRE_ROUTE = REPO_ROOT / "routes" / "tertiaire.py"


# ── G1 : Constantes OPERAT CO2 separees ADEME ──────────────────────────


def test_g1_operat_emission_factors_distinct_from_ademe():
    assert OPERAT_CONSTANTS.exists(), "Fichier config/operat_constants.py manquant (S1 #324 Chantier 1)."
    text = OPERAT_CONSTANTS.read_text(encoding="utf-8")
    # Valeur Annexe VII (verbatim Legifrance).
    assert '"kgco2e_per_kwh": 0.064' in text, (
        "Conformite S1 #324 regression : facteur CO2 OPERAT electricite "
        "doit etre 0.064 kgCO2/kWh (Annexe VII arrete 10/04/2020). "
        "Cf. docs/audits/crosscheck_legifrance_operat_deet_2026_05_27.md."
    )
    # Source officielle citee.
    assert "JORFTEXT000041842389" in text, "Source officielle Legifrance JORFTEXT000041842389 doit etre citee."
    # Le fichier ADEME garde sa valeur ADEME (anti-confusion).
    ademe_text = EMISSION_FACTORS.read_text(encoding="utf-8")
    assert '"kgco2e_per_kwh": 0.052' in ademe_text, (
        "Conformite S1 #324 regression : facteur ADEME 0.052 doit etre "
        "preserve dans config/emission_factors.py pour Bilan GES / CSRD."
    )


# ── G2 : Constantes EP OPERAT separees RE2020 ──────────────────────────


def test_g2_operat_ep_coefficients_distinct_from_re2020():
    text = OPERAT_CONSTANTS.read_text(encoding="utf-8")
    # EP OPERAT Article 16 (changement de source) = 2,3.
    assert '"coeff_ep": 2.3' in text, (
        "Conformite S1 #324 regression : coefficient EP OPERAT electricite "
        "doit etre 2.3 (Annexe VII Article 16 changement de source). "
        "RE2020 / DPE 2026+ garde 1,9 dans energy_intensity_service.py."
    )
    # Le service RE2020 garde sa valeur RE2020.
    re2020_text = ENERGY_INTENSITY.read_text(encoding="utf-8")
    assert "EnergyVector.ELECTRICITY: 1.9" in re2020_text, (
        "Conformite S1 #324 regression : coefficient EP RE2020 (1.9) doit "
        "etre preserve dans energy_intensity_service.py."
    )


# ── G3 : Helpers acces avec fail-closed ────────────────────────────────


def test_g3_operat_helpers_fail_closed():
    text = OPERAT_CONSTANTS.read_text(encoding="utf-8")
    assert "def get_operat_emission_factor" in text, "Helper get_operat_emission_factor() doit etre expose."
    assert "def get_operat_ep_coefficient" in text, "Helper get_operat_ep_coefficient() doit etre expose."
    assert "def get_operat_tri_threshold" in text, "Helper get_operat_tri_threshold() doit etre expose."
    assert "def is_valid_operat_reference_year" in text, "Helper is_valid_operat_reference_year() doit etre expose."
    # Fail-closed : les helpers doivent raise KeyError pour vecteur inconnu
    # (pas de fallback silencieux a une valeur par defaut).
    assert "raise KeyError" in text, (
        "Helpers OPERAT doivent fail-closed (raise KeyError) sur vecteur/typologie "
        "inconnu - pas de fallback silencieux (doctrine 'aucun fallback silencieux')."
    )


# ── G4 : Validation annee de reference OPERAT ──────────────────────────


def test_g4_operat_reference_year_validation():
    text = OPERAT_CONSTANTS.read_text(encoding="utf-8")
    assert "OPERAT_REFERENCE_YEAR_MIN: int = 2010" in text, (
        "Constante OPERAT_REFERENCE_YEAR_MIN doit etre 2010 (Article 3.I)."
    )
    assert "OPERAT_REFERENCE_YEAR_MAX: int = 2022" in text, (
        "Constante OPERAT_REFERENCE_YEAR_MAX doit etre 2022 (Article 3.I)."
    )
    assert "OPERAT_REFERENCE_YEAR_DEADLINE_ISO" in text, (
        "Constante OPERAT_REFERENCE_YEAR_DEADLINE_ISO doit exister (butoir 30/09/2027)."
    )
    assert "2027-09-30" in text, "Butoir 30 septembre 2027 doit etre code (Article 3.I)."
    # Le service operat_trajectory doit consommer ces constantes.
    traj_text = OPERAT_TRAJECTORY.read_text(encoding="utf-8")
    assert "OPERAT_REFERENCE_YEAR_MAX" in traj_text and "OPERAT_REFERENCE_YEAR_MIN" in traj_text, (
        "operat_trajectory.py doit importer les constantes OPERAT_REFERENCE_YEAR_*."
    )
    assert "is_first_full_year_of_operation" in traj_text, (
        "Le service declare_consumption doit accepter le flag "
        "is_first_full_year_of_operation (Article 3.I cas batiment neuf)."
    )
    # Ancienne plage 2000-2060 retiree.
    assert "2000 or year > 2060" not in traj_text, (
        "Conformite S1 #324 regression : ancienne plage 2000-2060 encore presente. "
        "Doit etre remplacee par 2010-2022 (Article 3.I)."
    )
    # Le router expose le flag.
    route_text = TERTIAIRE_ROUTE.read_text(encoding="utf-8")
    assert "is_first_full_year_of_operation" in route_text, (
        "ConsumptionDeclareRequest doit exposer is_first_full_year_of_operation."
    )


# ── G5 : Typologies TRI Article 11.I ───────────────────────────────────


def test_g5_operat_tri_typologies_complete():
    text = OPERAT_CONSTANTS.read_text(encoding="utf-8")
    # 3 typologies obligatoires avec leurs seuils canoniques.
    expected = {
        "STRUCTURAL_ENVELOPE": 30,
        "ENERGY_EQUIPMENT": 15,
        "OPTIMIZATION_SYSTEM": 10,
    }
    for typology, threshold in expected.items():
        assert typology in text, (
            f"Typologie {typology} manquante dans OPERAT_TRI_TYPOLOGIES (Article 11.I arrete 10/04/2020)."
        )
        # Verifie qu'au moins une occurrence du seuil est associee.
        assert f'"tri_threshold_years": {threshold}' in text, (
            f"Seuil {threshold} ans manquant pour la typologie {typology}."
        )


# ── G6 : ModulationAction.typologie + ModulationResult enrichi ─────────


def test_g6_modulation_service_uses_typology():
    text = TERTIAIRE_MODULATION.read_text(encoding="utf-8")
    # Action a un champ typologie.
    assert re.search(r"typologie:\s*str\s*=\s*TYPOLOGY_DEFAULT", text), (
        "ModulationAction doit avoir un champ typologie (S1 #324 Chantier 3)."
    )
    # Result expose la decomposition par typologie + decision globale.
    assert "tri_par_typologie" in text, "ModulationResult doit exposer tri_par_typologie."
    assert "disproportion_globale" in text and "disproportion_explication" in text, (
        "ModulationResult doit exposer disproportion_globale + explication FR."
    )
    # Le service importe les helpers OPERAT (pas de magic number).
    assert "from config.operat_constants import" in text, (
        "tertiaire_modulation_service doit importer depuis config.operat_constants "
        "(pas de hardcoding des seuils 30/15/10)."
    )
    # Plus de hardcoded `tri > 15` generique applique a toutes les actions.
    # On accepte les seuils 30/15/10 dans le contexte du test typologique
    # mais pas comme seul seuil de warning.
    assert not re.search(r"if\s+tri\s*>\s*15:\s*\n\s+warnings\.append", text), (
        "S1 #324 regression : seuil generique TRI > 15 ans encore applique. "
        "Doit utiliser get_operat_tri_threshold(typologie) selon Article 11.I."
    )


# ── G7 : Pas de melange silencieux ADEME/OPERAT/RE2020 ─────────────────


def test_g7_no_silent_mix_between_ademe_operat_re2020():
    """Les 3 fichiers de constantes doivent se referencer mutuellement
    avec un avertissement explicite anti-confusion."""
    ademe_text = EMISSION_FACTORS.read_text(encoding="utf-8")
    re2020_text = ENERGY_INTENSITY.read_text(encoding="utf-8")
    operat_text = OPERAT_CONSTANTS.read_text(encoding="utf-8")
    # config/emission_factors.py doit avertir sur le scope ADEME vs OPERAT.
    assert "OPERAT" in ademe_text and "operat_constants" in ademe_text, (
        "config/emission_factors.py doit avertir explicitement sur la "
        "separation ADEME / OPERAT et pointer vers operat_constants."
    )
    # energy_intensity_service.py doit avertir sur le scope RE2020 vs OPERAT.
    assert "OPERAT" in re2020_text and "operat_constants" in re2020_text, (
        "energy_intensity_service.py doit avertir explicitement sur la "
        "separation RE2020 / OPERAT et pointer vers operat_constants."
    )
    # operat_constants.py doit documenter la coexistence des 3 referentiels.
    assert "ADEME" in operat_text and ("RE2020" in operat_text or "DPE 2026" in operat_text), (
        "operat_constants.py doit documenter explicitement la coexistence "
        "avec ADEME et RE2020 / DPE 2026+ pour eviter toute confusion."
    )
