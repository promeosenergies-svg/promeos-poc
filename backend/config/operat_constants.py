"""PROMEOS — Constantes réglementaires OPERAT / DEET (Décret Tertiaire).

Sprint S1 P0 cleanup #324 (2026-05-27, brief Chantier 1) — constantes
spécifiques OPERAT séparées des constantes ADEME (Bilan GES / CSRD) et
RE2020 (DPE 2026+).

**Pourquoi ces constantes séparées** :
Le Décret Tertiaire (arrêté 10/04/2020 modifié, NOR DEVR2007365A, version
consolidée 07/09/2025) impose ses propres facteurs de conversion CO2 et
ses propres coefficients d'énergie primaire pour le reporting OPERAT.
Ces valeurs **diffèrent légitimement** des autres référentiels :

  | Constante | OPERAT/DEET | ADEME V23.6 | RE2020 / DPE 2026+ |
  |-----------|-------------|-------------|---------------------|
  | CO2 élec  | 0,064       | 0,052       | (n/a)               |
  | EP élec   | 2,3 (Art.16)| (n/a)       | 1,9                 |

**Mélanger silencieusement ADEME et OPERAT est un bug** : le scoring DT
calcule sur une base CO2 OPERAT 0,064 (Annexe VII), tandis que le Bilan
GES réglementaire / CSRD scope 2 location-based utilise ADEME 0,052.
Cf. cross-check officiel Légifrance : docs/audits/crosscheck_legifrance_operat_deet_2026_05_27.md

**Sources officielles primaires** :
- Arrêté 10 avril 2020 modifié :
  https://www.legifrance.gouv.fr/loda/id/JORFTEXT000041842389
- Annexe VII (CO2 + EP) :
  https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000045682100
- Arrêté 1er août 2025 (consolidation, NOR ATDL2430864A) :
  https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052198856
"""

from __future__ import annotations

# ── Métadonnées source ──────────────────────────────────────────────────

OPERAT_SOURCE_TEXT: str = "Arrêté du 10 avril 2020 modifié (NOR DEVR2007365A), Annexe VII"
OPERAT_SOURCE_URL: str = "https://www.legifrance.gouv.fr/loda/id/JORFTEXT000041842389"
OPERAT_SOURCE_CONSOLIDATION_DATE: str = "2025-09-07"
OPERAT_SOURCE_NOR_LATEST: str = "ATDL2430864A"  # arrêté consolidant du 01/08/2025

# ── D1 — Facteurs CO2 OPERAT (Annexe VII tableau VII-2) ────────────────
# Verbatim Légifrance — équivalent CO2 par kWh d'énergie finale (PCI).
# À utiliser EXCLUSIVEMENT pour les calculs OPERAT / DEET.
# Pour Bilan GES / CSRD, utiliser config.emission_factors (ADEME V23.6).

EMISSION_FACTORS_OPERAT: dict[str, dict[str, str | float]] = {
    "ELEC": {
        "kgco2e_per_kwh": 0.064,
        "source": OPERAT_SOURCE_TEXT + " — électricité (hors autoconsommation) tous usages confondus",
        "source_url": OPERAT_SOURCE_URL,
        "unit": "kgCO2/kWh EF PCI",
        "scope": "OPERAT / DEET — reporting Décret Tertiaire uniquement",
        "consolidation_date": OPERAT_SOURCE_CONSOLIDATION_DATE,
    },
    "GAZ": {
        "kgco2e_per_kwh": 0.227,
        "source": OPERAT_SOURCE_TEXT + " — gaz naturel",
        "source_url": OPERAT_SOURCE_URL,
        "unit": "kgCO2/kWh EF PCI",
        "scope": "OPERAT / DEET",
        "consolidation_date": OPERAT_SOURCE_CONSOLIDATION_DATE,
    },
    "FIOUL": {
        "kgco2e_per_kwh": 0.324,
        "source": OPERAT_SOURCE_TEXT + " — fioul domestique",
        "source_url": OPERAT_SOURCE_URL,
        "unit": "kgCO2/kWh EF PCI",
        "scope": "OPERAT / DEET",
        "consolidation_date": OPERAT_SOURCE_CONSOLIDATION_DATE,
    },
    "BOIS": {
        "kgco2e_per_kwh": 0.030,
        "source": OPERAT_SOURCE_TEXT + " — bois / biomasse (granulés)",
        "source_url": OPERAT_SOURCE_URL,
        "unit": "kgCO2/kWh EF PCI",
        "scope": "OPERAT / DEET",
        "consolidation_date": OPERAT_SOURCE_CONSOLIDATION_DATE,
    },
    "CHARBON": {
        "kgco2e_per_kwh": 0.385,
        "source": OPERAT_SOURCE_TEXT + " — charbon",
        "source_url": OPERAT_SOURCE_URL,
        "unit": "kgCO2/kWh EF PCI",
        "scope": "OPERAT / DEET",
        "consolidation_date": OPERAT_SOURCE_CONSOLIDATION_DATE,
    },
}


# ── D2 — Coefficients d'énergie primaire OPERAT (Annexe VII, Art. 16) ──
# Utilisés UNIQUEMENT dans le cadre de l'Article 16 (changement de source
# énergétique) du Décret Tertiaire. Ne PAS confondre avec :
#   - RE2020 / DPE 2026+ : EP élec = 1,9 (cf. services/energy_intensity_service.py)
#   - DPE legacy < 2026 : EP élec = 2,58

EP_COEFFICIENTS_OPERAT: dict[str, dict[str, str | float]] = {
    "ELEC": {
        "coeff_ep": 2.3,
        "source": OPERAT_SOURCE_TEXT + " — Article 16 changement de source énergétique",
        "source_url": OPERAT_SOURCE_URL,
        "scope": "OPERAT / DEET — Article 16 (changement de source énergétique) uniquement",
        "consolidation_date": OPERAT_SOURCE_CONSOLIDATION_DATE,
    },
    "GAZ": {
        "coeff_ep": 1.0,
        "source": OPERAT_SOURCE_TEXT + " — Article 16",
        "source_url": OPERAT_SOURCE_URL,
        "scope": "OPERAT / DEET — Article 16",
        "consolidation_date": OPERAT_SOURCE_CONSOLIDATION_DATE,
    },
    "FIOUL": {
        "coeff_ep": 1.0,
        "source": OPERAT_SOURCE_TEXT + " — Article 16 énergies fossiles",
        "source_url": OPERAT_SOURCE_URL,
        "scope": "OPERAT / DEET — Article 16",
        "consolidation_date": OPERAT_SOURCE_CONSOLIDATION_DATE,
    },
    "BOIS": {
        "coeff_ep": 0.0,
        "source": OPERAT_SOURCE_TEXT + " — Article 16 bois (énergie renouvelable)",
        "source_url": OPERAT_SOURCE_URL,
        "scope": "OPERAT / DEET — Article 16",
        "consolidation_date": OPERAT_SOURCE_CONSOLIDATION_DATE,
    },
}


# ── D4 — Année de référence OPERAT (Article 3.I) ───────────────────────
# Plage stricte autorisée + butoir + fallback documenté.

OPERAT_REFERENCE_YEAR_MIN: int = 2010
OPERAT_REFERENCE_YEAR_MAX: int = 2022
OPERAT_REFERENCE_YEAR_DEADLINE_ISO: str = "2027-09-30"
OPERAT_REFERENCE_YEAR_DEADLINE_LABEL: str = "30 septembre 2027"
OPERAT_REFERENCE_YEAR_FALLBACK_RULE: str = (
    "À défaut de renseignement avant le 30 septembre 2027, la consommation "
    "de référence correspond à la consommation de la première année pleine "
    "d'exploitation (Article 3.I de l'arrêté 10/04/2020)."
)

# Cas particulier explicite : bâtiment neuf dont la première année pleine
# d'exploitation est > 2022. Ce cas doit être déclaré explicitement par le
# saisisseur (flag `is_first_full_year_of_operation`) et l'année peut alors
# dépasser 2022 mais ne peut pas être dans le futur.


# ── D5 — TRI par typologie (Article 11.I — disproportion économique) ───
# Verbatim Légifrance : 3 typologies de travaux avec seuils TRI distincts.

OPERAT_TRI_TYPOLOGIES: dict[str, dict[str, int | str]] = {
    "STRUCTURAL_ENVELOPE": {
        "tri_threshold_years": 30,
        "label_fr": "Rénovations de l'enveloppe (travaux structuraux)",
        "source": "Arrêté 10/04/2020 modifié, Article 11.I",
        "source_url": OPERAT_SOURCE_URL,
    },
    "ENERGY_EQUIPMENT": {
        "tri_threshold_years": 15,
        "label_fr": "Renouvellement des équipements énergétiques (CVC, ECS, éclairage…)",
        "source": "Arrêté 10/04/2020 modifié, Article 11.I",
        "source_url": OPERAT_SOURCE_URL,
    },
    "OPTIMIZATION_SYSTEM": {
        "tri_threshold_years": 10,
        "label_fr": "Systèmes d'optimisation et d'exploitation (GTB, BACS, pilotage)",
        "source": "Arrêté 10/04/2020 modifié, Article 11.I",
        "source_url": OPERAT_SOURCE_URL,
    },
}


# ── Helpers d'accès doctriné ───────────────────────────────────────────


def get_operat_emission_factor(energy_vector: str) -> float:
    """Retourne le facteur CO2 OPERAT en kgCO2/kWh EF PCI.

    À utiliser EXCLUSIVEMENT pour les calculs OPERAT / DEET.
    Pour Bilan GES / CSRD, utiliser `config.emission_factors.get_emission_factor()`.

    Raises:
        KeyError: si le vecteur n'est pas couvert par l'Annexe VII OPERAT
                  (fail-closed — pas de fallback silencieux).
    """
    key = energy_vector.upper()
    if key not in EMISSION_FACTORS_OPERAT:
        raise KeyError(
            f"Vecteur '{energy_vector}' non couvert par l'Annexe VII OPERAT. "
            f"Vecteurs supportés : {list(EMISSION_FACTORS_OPERAT.keys())}. "
            f"Cf. {OPERAT_SOURCE_URL}"
        )
    return EMISSION_FACTORS_OPERAT[key]["kgco2e_per_kwh"]  # type: ignore[return-value]


def get_operat_ep_coefficient(energy_vector: str) -> float:
    """Retourne le coefficient EP OPERAT (Article 16 — changement de source).

    À utiliser EXCLUSIVEMENT pour le contexte Article 16 du Décret Tertiaire.
    Pour RE2020 / DPE 2026+, utiliser `services.energy_intensity_service.EP_COEFFICIENTS`.

    Raises:
        KeyError: si le vecteur n'est pas couvert (fail-closed).
    """
    key = energy_vector.upper()
    if key not in EP_COEFFICIENTS_OPERAT:
        raise KeyError(
            f"Vecteur '{energy_vector}' non couvert par l'Article 16 OPERAT. "
            f"Vecteurs supportés : {list(EP_COEFFICIENTS_OPERAT.keys())}. "
            f"Cf. {OPERAT_SOURCE_URL}"
        )
    return EP_COEFFICIENTS_OPERAT[key]["coeff_ep"]  # type: ignore[return-value]


def get_operat_tri_threshold(typology: str) -> int:
    """Retourne le seuil de TRI (années) pour la typologie de travaux.

    Typologies valides :
        - STRUCTURAL_ENVELOPE → 30 ans
        - ENERGY_EQUIPMENT    → 15 ans
        - OPTIMIZATION_SYSTEM → 10 ans

    Raises:
        KeyError: si la typologie est inconnue (fail-closed).
    """
    if typology not in OPERAT_TRI_TYPOLOGIES:
        raise KeyError(
            f"Typologie '{typology}' inconnue. Typologies OPERAT Art. 11.I : {list(OPERAT_TRI_TYPOLOGIES.keys())}."
        )
    return OPERAT_TRI_TYPOLOGIES[typology]["tri_threshold_years"]  # type: ignore[return-value]


def is_valid_operat_reference_year(year: int, is_first_full_year: bool = False) -> bool:
    """Valide qu'une année est conforme aux règles OPERAT (Article 3.I).

    Args:
        year: année à valider.
        is_first_full_year: True si l'utilisateur déclare explicitement que
                            cette année est la « première année pleine
                            d'exploitation » du bâtiment (cas bâtiment neuf
                            post-2022 légitime).

    Returns:
        True si l'année est conforme, False sinon.

    Règles :
        - Cas standard : 2010 ≤ year ≤ 2022.
        - Cas « première année pleine » : year ≤ année courante (pas de futur).
        - Pas de fallback silencieux : si False, l'appelant doit rejeter
          la saisie avec un message FR doctriné.
    """
    from datetime import date

    current_year = date.today().year
    if is_first_full_year:
        # Cas bâtiment neuf post-2022 : doit être <= année courante.
        return 2010 <= year <= current_year
    # Cas standard : plage stricte Article 3.I.
    return OPERAT_REFERENCE_YEAR_MIN <= year <= OPERAT_REFERENCE_YEAR_MAX
