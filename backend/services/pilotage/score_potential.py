"""
PROMEOS - Score de potentiel pilotable (0-100) par site / compteur.

`compute_potential_score` retourne un score 0-100 combinant :

  - taux decalable de l'archetype (pondere 60%)
  - concentration de la conso sur les plages de pointe (pondere 30%)
  - penetration BACS du segment (pondere 10%)

Quand l'archetype est present dans `ARCHETYPE_CALIBRATION_2024` (calibrage
Barometre Flex 2026 RTE/Enedis/GIMELEC), les valeurs officielles 2024 sont
utilisees. Sinon, on retombe sur l'heuristique par defaut (comportement
historique) calee sur la mediane tertiaire.

Source : Barometre Flex 2026 RTE / Enedis / GIMELEC (avril 2026).
"""

from __future__ import annotations

from typing import Optional

from services.pilotage.constants import (
    ARCHETYPE_CALIBRATION_2024,
    ARCHETYPE_RULES,
)


# --- Heuristique fallback (comportement historique) --------------------------
# Utilisee quand l'archetype n'est pas dans le calibrage Barometre Flex 2026.
_FALLBACK_TAUX_DECALABLE = 0.20  # mediane tertiaire, legacy PROMEOS
_FALLBACK_CONSO_POINTE = 0.35  # pointe typique tertiaire diurne
_FALLBACK_BACS = 0.15  # taux BACS tertiaire moyen 2024


# --- Ponderation du score ----------------------------------------------------
_W_DECALABLE = 0.60
_W_POINTE = 0.30
_W_BACS = 0.10


def compute_potential_score(
    archetype_code: Optional[str],
    conso_pointe_observee_pct: Optional[float] = None,
    bacs_equipe: Optional[bool] = None,
) -> dict:
    """
    Calcule le score de potentiel pilotable pour un site / compteur.

    Args:
        archetype_code: code canonique d'archetype (ex: "BUREAU_STANDARD").
            Si present dans ARCHETYPE_CALIBRATION_2024, les valeurs officielles
            Barometre Flex 2026 sont utilisees. Sinon, fallback heuristique.
        conso_pointe_observee_pct: part observee de la conso sur la pointe
            (fraction 0.0-1.0). Si None, valeur calibree utilisee.
        bacs_equipe: True si site equipe GTB/BACS. Si None, penetration
            sectorielle du calibrage utilisee.

    Returns:
        dict avec :
          - score : float 0-100
          - taux_decalable : fraction utilisee
          - conso_pointe_pct : fraction utilisee
          - bacs_factor : fraction utilisee
          - used_calibration : True si valeurs 2024 utilisees
          - source : citation source courte
    """
    calib = ARCHETYPE_CALIBRATION_2024.get(archetype_code) if archetype_code else None
    used_calibration = calib is not None

    if calib is not None:
        taux_decalable = calib["taux_decalable_moyen"]
        conso_pointe_pct = (
            conso_pointe_observee_pct
            if conso_pointe_observee_pct is not None
            else calib["conso_journaliere_pointe_pct"]
        )
        bacs_factor = 1.0 if bacs_equipe is True else (0.0 if bacs_equipe is False else calib["bacs_penetration_2024"])
        source = calib["source"]
    else:
        # Fallback : heuristique historique. Utilise le rule legacy si dispo,
        # sinon les valeurs medianes tertiaires.
        rule = ARCHETYPE_RULES.get(archetype_code or "", {})
        # Sites 24/7 -> pointe plus diffuse, potentiel legerement relev.
        taux_decalable = 0.30 if rule.get("continu_24_7") else _FALLBACK_TAUX_DECALABLE
        conso_pointe_pct = (
            conso_pointe_observee_pct if conso_pointe_observee_pct is not None else _FALLBACK_CONSO_POINTE
        )
        bacs_factor = 1.0 if bacs_equipe is True else (0.0 if bacs_equipe is False else _FALLBACK_BACS)
        source = "Heuristique PROMEOS (archetype non calibre)"

    # Normalisation : les trois composantes sont des fractions 0.0-1.0.
    # Le score final est ramene sur 0-100 apres ponderation.
    raw = taux_decalable * _W_DECALABLE + conso_pointe_pct * _W_POINTE + bacs_factor * _W_BACS
    score = round(max(0.0, min(1.0, raw)) * 100.0, 1)

    return {
        "score": score,
        "taux_decalable": taux_decalable,
        "conso_pointe_pct": conso_pointe_pct,
        "bacs_factor": bacs_factor,
        "used_calibration": used_calibration,
        "source": source,
    }
