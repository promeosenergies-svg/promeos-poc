"""
PROMEOS — Phase F1.5 (ADR-F-01) : seed canonique fournisseurs FR majeurs.

10 fournisseurs canoniques (organisation_id=NULL) servant de catalogue partagé
Promeos master. Idempotent : skip si SIREN déjà présent en canonique.

Source : Vision Consolidée v1.3 + cartographie marché FR Mix-E 2026.

Usage :
    from services.demo_seed.fournisseurs_canoniques import seed_fournisseurs_canoniques

    seed_fournisseurs_canoniques(db)
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.enums import TypeFournitureEnum
from models.fournisseur import Fournisseur


# 10 fournisseurs FR cardinaux (ADR-F-01 Tableau §Seed canonique).
# SIREN à valider regulatory-expert Phase F1 — sources Sirène/INSEE publiques.
FOURNISSEURS_CANONIQUES_FR: list[dict] = [
    {
        "nom": "EDF",
        "siren": "552081317",
        "type_fourniture": TypeFournitureEnum.MULTI,
        "site_web": "https://www.edf.fr",
        "naf_code": "35.11Z",
    },
    {
        "nom": "ENGIE",
        "siren": "542107651",
        "type_fourniture": TypeFournitureEnum.MULTI,
        "site_web": "https://www.engie.com",
        "naf_code": "35.23Z",
    },
    {
        "nom": "TOTALENERGIES",
        "siren": "542051180",
        "type_fourniture": TypeFournitureEnum.MULTI,
        "site_web": "https://www.totalenergies.fr",
        "naf_code": "35.14Z",
    },
    {
        "nom": "EKWATEUR",
        "siren": "814488395",
        "type_fourniture": TypeFournitureEnum.ELEC,
        "site_web": "https://www.ekwateur.fr",
        "naf_code": "35.14Z",
    },
    {
        "nom": "ALPIQ",
        "siren": "484549526",
        "type_fourniture": TypeFournitureEnum.ELEC,
        "site_web": "https://www.alpiq.fr",
        "naf_code": "35.14Z",
    },
    {
        "nom": "ENERCOOP",
        "siren": "484223094",
        "type_fourniture": TypeFournitureEnum.ELEC,
        "site_web": "https://www.enercoop.fr",
        "naf_code": "35.14Z",
    },
    {
        "nom": "PLUM_ENERGIE",
        "siren": "813292475",
        "type_fourniture": TypeFournitureEnum.ELEC,
        "site_web": "https://www.plum.fr",
        "naf_code": "35.14Z",
    },
    {
        "nom": "MINT_ENERGIE",
        "siren": "821530771",
        "type_fourniture": TypeFournitureEnum.MULTI,
        "site_web": "https://www.mint-energie.com",
        "naf_code": "35.14Z",
    },
    {
        "nom": "OHM_ENERGIE",
        "siren": "851251411",
        "type_fourniture": TypeFournitureEnum.ELEC,
        "site_web": "https://www.ohm-energie.com",
        "naf_code": "35.14Z",
    },
    {
        "nom": "GAZ_DE_BORDEAUX",
        "siren": "552108220",
        "type_fourniture": TypeFournitureEnum.GAZ,
        "site_web": "https://www.gazdebordeaux.fr",
        "naf_code": "35.23Z",
    },
]


def seed_fournisseurs_canoniques(db: Session) -> dict:
    """Idempotent : insert seulement les fournisseurs canoniques absents.

    Returns:
        dict: {"created": [nom1, ...], "skipped": [nom2, ...], "total_canoniques": N}
    """
    created: list[str] = []
    skipped: list[str] = []

    for spec in FOURNISSEURS_CANONIQUES_FR:
        existing = (
            db.query(Fournisseur)
            .filter(
                Fournisseur.siren == spec["siren"],
                Fournisseur.organisation_id.is_(None),
            )
            .first()
        )
        if existing:
            skipped.append(spec["nom"])
            continue

        f = Fournisseur(
            organisation_id=None,  # canonique global
            nom=spec["nom"],
            siren=spec["siren"],
            type_fourniture=spec["type_fourniture"],
            site_web=spec.get("site_web"),
            naf_code=spec.get("naf_code"),
            actif=True,
        )
        db.add(f)
        # Flush per-item pour détecter violations intégrité individuellement
        # (P2 fix code-reviewer Phase F1 — défense seed partiellement non-idempotent)
        db.flush()
        created.append(spec["nom"])

    db.commit()

    total = db.query(Fournisseur).filter(Fournisseur.organisation_id.is_(None)).count()
    return {"created": created, "skipped": skipped, "total_canoniques": total}
