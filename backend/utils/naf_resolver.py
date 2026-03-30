"""
PROMEOS — Résolution NAF en cascade (V110).

Stratégie :
  1. Site.naf_code (override local)
  2. EntiteJuridique.naf_code (via portefeuille)
  3. None
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from models import Site


def resolve_naf_code(site: "Site", db: "Session") -> Optional[str]:
    """
    Résolution NAF en cascade :
      1. Site.naf_code (override)
      2. EntiteJuridique.naf_code (via portefeuille)
      3. None
    """
    if site.naf_code:
        return site.naf_code

    if site.portefeuille_id:
        from models import Portefeuille, EntiteJuridique

        pf = db.query(Portefeuille).filter(Portefeuille.id == site.portefeuille_id).first()
        if pf and pf.entite_juridique_id:
            ej = db.query(EntiteJuridique).filter(EntiteJuridique.id == pf.entite_juridique_id).first()
            if ej and ej.naf_code:
                return ej.naf_code

    return None
