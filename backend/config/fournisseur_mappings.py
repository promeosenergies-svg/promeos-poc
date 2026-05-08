"""
PROMEOS — config/fournisseur_mappings.py (Phase F2 P1 fix code-reviewer).

SoT canonique du mapping `supplier_name → nom canonique Fournisseur` partagé
entre :
- `services/fournisseur_resolver_service.py` (runtime)
- `scripts/backfill_fournisseur_id.py` (one-shot migration)

Pattern doctrine PROMEOS : tout couplage runtime → service. Les scripts
one-shot importent depuis ce module canonique, jamais l'inverse.

Source vérité : variantes orthographiques observées en production + Vision v1.3
fournisseurs FR majeurs (cf. demo_seed/fournisseurs_canoniques.py).
"""

from __future__ import annotations


# Mapping supplier_name normalisé → nom canonique Fournisseur Phase F1.
# Toutes les clés sont normalisées en upper-strip-deduplicate-spaces avant lookup.
SUPPLIER_NAME_TO_CANONICAL: dict[str, str] = {
    # EDF variantes
    "EDF": "EDF",
    "E.D.F.": "EDF",
    "E D F": "EDF",
    "EDF ENTREPRISES": "EDF",
    "EDF SA": "EDF",
    # ENGIE variantes (incl. ancien GDF SUEZ)
    "ENGIE": "ENGIE",
    "GDF SUEZ": "ENGIE",
    "GDF-SUEZ": "ENGIE",
    "GDF": "ENGIE",
    "ENGIE SA": "ENGIE",
    # TOTALENERGIES variantes
    "TOTALENERGIES": "TOTALENERGIES",
    "TOTAL ENERGIES": "TOTALENERGIES",
    "TOTAL DIRECT ENERGIE": "TOTALENERGIES",
    "TOTAL ENERGIES ELECTRICITE ET GAZ": "TOTALENERGIES",
    # Autres canoniques FR Phase F1 seed
    "EKWATEUR": "EKWATEUR",
    "ALPIQ": "ALPIQ",
    "ENERCOOP": "ENERCOOP",
    "PLUM ENERGIE": "PLUM_ENERGIE",
    "PLÜM ENERGIE": "PLUM_ENERGIE",
    "MINT ENERGIE": "MINT_ENERGIE",
    "OHM ENERGIE": "OHM_ENERGIE",
    "GAZ DE BORDEAUX": "GAZ_DE_BORDEAUX",
}


def normalize_supplier_name(raw: str | None) -> str:
    """Normalise un supplier_name libre pour matching mapping canonique.

    Pipeline cardinal :
    1. None → "" (safe)
    2. strip espaces avant/après
    3. upper case
    4. deduplicate doubles espaces ("  " → " ")
    """
    if raw is None:
        return ""
    return raw.strip().upper().replace("  ", " ")
