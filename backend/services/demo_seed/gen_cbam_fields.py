"""Seed CBAM — expose l'audit CBAM sur 1-2 sites industriels démo.

Par défaut, les sites tertiaires n'ont aucune exposition CBAM. Pour que la
démo montre concrètement la brique P3 (Règlement UE 2023/956, 75,36 €/tCO2),
on seed des volumes d'importation hors UE sur les sites dont l'archétype
correspond à un scope couvert (INDUSTRIE_LEGERE, LOGISTIQUE_FRIGO — si le
pack inclut un site industriel).

Sans cette seed, tous les sites démo afficheraient "CBAM : non applicable"
dans le cockpit, masquant le différenciateur stratégique.

Idempotent : n'écrase pas un site déjà configuré (`cbam_imports_tonnes` renseigné).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import Site

# Profils CBAM type par archétype — calibré sur ordre de grandeur industriel
# moyen FR (PME 20-250 salariés). Volumes annuels tonnes/an hors UE.
# Source heuristique : INSEE Bilan carbone sectoriel × part import extra-UE.
CBAM_PROFILES_BY_ARCHETYPE: dict[str, dict[str, float]] = {
    # Industrie légère : imports acier/aluminium pour production/structure
    "INDUSTRIE_LEGERE": {
        "acier": 50.0,
        "aluminium": 8.0,
    },
    # Commerce spécialisé (BTP/outillage) : plus modeste sur acier
    "COMMERCE_SPECIALISE": {
        "acier": 15.0,
    },
}


def seed_cbam_fields(db: Session, sites: list[Site]) -> dict:
    """Populise `cbam_imports_tonnes` sur les sites démo éligibles par archétype.

    Idempotent : skip si le site a déjà `cbam_imports_tonnes` renseigné.

    Returns:
        {"updated": N, "skipped_existing": M, "skipped_no_profile": K}
    """
    stats = {"updated": 0, "skipped_existing": 0, "skipped_no_profile": 0}

    for site in sites:
        if getattr(site, "cbam_imports_tonnes", None):
            stats["skipped_existing"] += 1
            continue

        profile = CBAM_PROFILES_BY_ARCHETYPE.get(site.archetype_code or "")
        if profile is None:
            stats["skipped_no_profile"] += 1
            continue

        site.cbam_imports_tonnes = dict(profile)
        stats["updated"] += 1

    if stats["updated"]:
        db.flush()
    return stats
