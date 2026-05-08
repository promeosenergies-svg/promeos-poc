"""
PROMEOS — Phase E IDOR Sprint : guards org-scoping cardinaux patrimoine_crud.

Cardinal multi-tenant : tous les endpoints CRUD patrimoine
(Organisation / EntiteJuridique / Portefeuille / Site / Batiment) DOIVENT
appliquer ces guards pour empêcher l'IDOR cross-tenant par énumération d'IDs.

Design :
- 5 fonctions `assert_org_owns_<entity>` retournent l'entité chargée ou raise 404.
- 404 (pas 403) délibéré : anti-énumération (l'attaquant ne peut pas
  distinguer "n'existe pas" de "appartient à autre tenant").
- JOIN chain cardinale : Bâtiment → Site → Portefeuille → EntiteJuridique → Organisation.
- Lecture seule (SELECT) : impose `not_deleted` + `actif` filter cohérent runtime.

Usage :
    from services.patrimoine_scope_guard import assert_org_owns_site

    org_id = resolve_org_id(request, auth, db)
    site = assert_org_owns_site(db, site_id, org_id)
    # site est garanti appartenir à scope_org_id ici, sinon 404 déjà raise.

Sources doctrine :
- ADR-017 Option B (X-Org-Id stricte DB Sprint C-7 Phase 7.2 SEC-2026-012)
- Phase D-4 Tier 4 P0-3 audit code-reviewer (~30 endpoints sans resolve_org_id)
- Pilier 12 ADR-016 (org-scoping cardinal multi-tenant)
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import (
    Batiment,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    not_deleted,
)


# ── Organisation ─────────────────────────────────────────────────────────────


def assert_org_owns_organisation(db: Session, org_id: int, scope_org_id: int) -> Organisation:
    """Garde IDOR Organisation : l'org demandée DOIT être == scope.

    404 (pas 403) délibéré pour anti-énumération cross-tenant.
    """
    if org_id != scope_org_id:
        raise HTTPException(404, "Organisation introuvable")

    org = db.query(Organisation).filter(Organisation.id == org_id, not_deleted(Organisation)).first()
    if not org:
        raise HTTPException(404, "Organisation introuvable")
    return org


# ── EntiteJuridique ──────────────────────────────────────────────────────────


def assert_org_owns_entite(db: Session, entite_id: int, scope_org_id: int) -> EntiteJuridique:
    """Garde IDOR EntiteJuridique : JOIN EJ.organisation_id == scope_org_id."""
    e = (
        db.query(EntiteJuridique)
        .filter(
            EntiteJuridique.id == entite_id,
            EntiteJuridique.organisation_id == scope_org_id,
            not_deleted(EntiteJuridique),
        )
        .first()
    )
    if not e:
        raise HTTPException(404, "Entité juridique introuvable")
    return e


# ── Portefeuille ─────────────────────────────────────────────────────────────


def assert_org_owns_portefeuille(db: Session, pf_id: int, scope_org_id: int) -> Portefeuille:
    """Garde IDOR Portefeuille : JOIN Pf → EJ.organisation_id == scope_org_id."""
    pf = (
        db.query(Portefeuille)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(
            Portefeuille.id == pf_id,
            EntiteJuridique.organisation_id == scope_org_id,
            not_deleted(Portefeuille),
        )
        .first()
    )
    if not pf:
        raise HTTPException(404, "Portefeuille introuvable")
    return pf


# ── Site ─────────────────────────────────────────────────────────────────────


def assert_org_owns_site(db: Session, site_id: int, scope_org_id: int) -> Site:
    """Garde IDOR Site : JOIN Site → Pf → EJ.organisation_id == scope_org_id."""
    site = (
        db.query(Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(
            Site.id == site_id,
            EntiteJuridique.organisation_id == scope_org_id,
            not_deleted(Site),
        )
        .first()
    )
    if not site:
        raise HTTPException(404, "Site introuvable")
    return site


# ── Batiment ─────────────────────────────────────────────────────────────────


def assert_org_owns_batiment(db: Session, batiment_id: int, scope_org_id: int) -> Batiment:
    """Garde IDOR Batiment : JOIN Bati → Site → Pf → EJ.organisation_id == scope_org_id."""
    bat = (
        db.query(Batiment)
        .join(Site, Site.id == Batiment.site_id)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(
            Batiment.id == batiment_id,
            EntiteJuridique.organisation_id == scope_org_id,
            not_deleted(Batiment),
        )
        .first()
    )
    if not bat:
        raise HTTPException(404, "Bâtiment introuvable")
    return bat
