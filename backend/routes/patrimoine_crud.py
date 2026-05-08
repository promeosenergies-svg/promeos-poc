"""
PROMEOS — CRUD Organisation / EntiteJuridique / Portefeuille / Site (Step 19)
Endpoints manuels pour ajouter/modifier/archiver des entités patrimoniales.

✅ Phase E IDOR Sprint (commit `<HEAD>`) : org-scoping cardinal appliqué sur 22 endpoints.
- `resolve_org_id` (services/scope_utils.py) résout scope canonique JWT/X-Org-Id/DEMO_MODE.
- `assert_org_owns_*` (services/patrimoine_scope_guard.py) impose JOIN chain Org→EJ→Pf→Site→Bati.
- 404 (pas 403) délibéré pour anti-énumération cross-tenant.
- Filtres LIST côté serveur (query param `org_id` ignoré, scope_org_id forcé).

Pattern Pilier 12 ADR-016 cardinal multi-tenant. Rétro-compat DEMO_MODE préservée
(scope fallback DemoState ou première Organisation active).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Batiment,
    TypeSite,
    not_deleted,
)
from schemas.patrimoine_crud import (
    OrganisationCreate,
    OrganisationUpdate,
    EntiteJuridiqueCreate,
    EntiteJuridiqueUpdate,
    PortefeuilleCreate,
    PortefeuilleUpdate,
    SiteCreate,
    SiteUpdate,
    BatimentCreate,
    BatimentUpdate,
)
from services.scope_utils import resolve_org_id  # noqa: E402
from services.patrimoine_scope_guard import (  # noqa: E402
    assert_org_owns_batiment,
    assert_org_owns_entite,
    assert_org_owns_organisation,
    assert_org_owns_portefeuille,
    assert_org_owns_site,
)

router = APIRouter(prefix="/api/patrimoine/crud", tags=["Patrimoine CRUD"])


# V119 J3 : helper centralise dans services/auth_guards.py
from services.auth_guards import require_write_access as _require_write_access  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────────────


def _org_to_dict(org: Organisation) -> dict:
    return {
        "id": org.id,
        "nom": org.nom,
        "type_client": org.type_client,
        "siren": org.siren,
        "actif": org.actif,
        "is_demo": org.is_demo,
    }


def _entite_to_dict(e: EntiteJuridique) -> dict:
    return {
        "id": e.id,
        "organisation_id": e.organisation_id,
        "nom": e.nom,
        "siren": e.siren,
        "siret": e.siret,
        "naf_code": e.naf_code,
        "region_code": e.region_code,
    }


def _pf_to_dict(pf: Portefeuille) -> dict:
    return {
        "id": pf.id,
        "entite_juridique_id": pf.entite_juridique_id,
        "nom": pf.nom,
        "description": pf.description,
    }


def _site_to_dict(s: Site) -> dict:
    return {
        "id": s.id,
        "portefeuille_id": s.portefeuille_id,
        "nom": s.nom,
        "type": s.type.value if s.type else None,
        "adresse": s.adresse,
        "code_postal": s.code_postal,
        "ville": s.ville,
        "region": s.region,
        "surface_m2": s.surface_m2,
        "tertiaire_area_m2": s.tertiaire_area_m2,
        "siret": s.siret,
        "naf_code": s.naf_code,
        "latitude": s.latitude,
        "longitude": s.longitude,
        "actif": s.actif,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ORGANISATIONS
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/organisations")
def list_organisations(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste l'organisation du scope courant (multi-tenant strict).

    Phase E IDOR : un tenant ne voit que sa propre organisation, pas l'inventaire global.
    """
    scope_org_id = resolve_org_id(request, auth, db)
    orgs = db.query(Organisation).filter(Organisation.id == scope_org_id, not_deleted(Organisation)).all()
    return {"count": len(orgs), "organisations": [_org_to_dict(o) for o in orgs]}


@router.post("/organisations", status_code=201)
def create_organisation(
    body: OrganisationCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Crée une nouvelle organisation.

    Phase E IDOR : pas de scope_org_id check ici — création d'une nouvelle org est
    explicitement hors scope existant (provisioning admin / onboarding initial).
    Protection : `_require_write_access` rôle DG_OWNER/DSI_ADMIN.
    """
    _require_write_access(auth)
    org = Organisation(
        nom=body.nom,
        type_client=body.type_client,
        siren=body.siren,
        actif=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return _org_to_dict(org)


@router.get("/organisations/{org_id}")
def get_organisation(
    org_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détail d'une organisation (org-scoping cardinal Phase E)."""
    scope_org_id = resolve_org_id(request, auth, db)
    org = assert_org_owns_organisation(db, org_id, scope_org_id)
    return _org_to_dict(org)


@router.patch("/organisations/{org_id}")
def update_organisation(
    org_id: int,
    body: OrganisationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Met à jour une organisation.

    Sprint C-5 Phase 5.8 fix G1 (audit transversal AXE 2 F2) : wiring cascade
    runtime sur mutations `consentement_dataconnect_global` / `consentement_grdf_global`.
    Phase E IDOR : org-scoping cardinal via `assert_org_owns_organisation`.
    """
    from regops.services.cascade_recompute_service import cascade_recompute_on_change

    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    org = assert_org_owns_organisation(db, org_id, scope_org_id)

    # Capture old values pour audit cascade (champs consent uniquement — autres = setattr direct)
    cascade_fields = {
        "consentement_dataconnect_global": getattr(org, "consentement_dataconnect_global", None),
        "consentement_grdf_global": getattr(org, "consentement_grdf_global", None),
    }
    payload = body.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(org, field, value)
    db.commit()
    db.refresh(org)

    # G1 Phase 5.8 — Cascade wiring runtime (Phase 4.5 effectivement déclenchée)
    cascade_results = []
    for cascade_field in ("consentement_dataconnect_global", "consentement_grdf_global"):
        if cascade_field in payload:
            try:
                result = cascade_recompute_on_change(
                    db=db,
                    entity=org,
                    field_modified=f"Organisation.{cascade_field}",
                    old_value=cascade_fields[cascade_field],
                    new_value=payload[cascade_field],
                    persist=True,
                    user_id=getattr(auth, "user_id", None),
                    org_id=org_id,
                )
                cascade_results.append({"field": cascade_field, "actions": len(result.actions)})
            except Exception as exc:  # noqa: BLE001 — résilience cascade (audit transversal pattern)
                import logging

                logging.getLogger("promeos.cascade").error("Cascade Org consent failed: %s", type(exc).__name__)

    response = _org_to_dict(org)
    if cascade_results:
        response["cascade"] = cascade_results
    return response


@router.delete("/organisations/{org_id}")
def archive_organisation(
    org_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Archive (soft-delete) une organisation (org-scoping cardinal Phase E)."""
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    org = assert_org_owns_organisation(db, org_id, scope_org_id)
    org.soft_delete()
    db.commit()
    return {"status": "archived", "id": org_id}


# ══════════════════════════════════════════════════════════════════════════════
# ENTITES JURIDIQUES
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/entites")
def list_entites(
    request: Request,
    org_id: Optional[int] = Query(None, description="Ignoré : forcé == scope_org_id (Phase E IDOR)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les entités juridiques du scope_org_id (Phase E IDOR cardinal).

    Le query param `org_id` est ignoré : l'org-scoping est forcé côté serveur via JWT/X-Org-Id.
    """
    scope_org_id = resolve_org_id(request, auth, db)
    entites = (
        db.query(EntiteJuridique)
        .filter(
            EntiteJuridique.organisation_id == scope_org_id,
            not_deleted(EntiteJuridique),
        )
        .all()
    )
    return {"count": len(entites), "entites": [_entite_to_dict(e) for e in entites]}


@router.post("/entites", status_code=201)
def create_entite(
    body: EntiteJuridiqueCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Crée une entité juridique (org-scoping cardinal Phase E).

    `assert_org_owns_organisation` couvre cardinal-ment :
    organisation_id == scope_org_id ET organisation existe non-soft-deleted.
    """
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    assert_org_owns_organisation(db, body.organisation_id, scope_org_id)
    # Vérifier unicité SIREN
    existing = (
        db.query(EntiteJuridique)
        .filter(
            EntiteJuridique.siren == body.siren,
            not_deleted(EntiteJuridique),
        )
        .first()
    )
    if existing:
        raise HTTPException(409, f"SIREN {body.siren} déjà utilisé par l'entité #{existing.id}")
    entite = EntiteJuridique(
        organisation_id=body.organisation_id,
        nom=body.nom,
        siren=body.siren,
        siret=body.siret,
        naf_code=body.naf_code,
        region_code=body.region_code,
    )
    db.add(entite)
    db.commit()
    db.refresh(entite)
    return _entite_to_dict(entite)


@router.get("/entites/{entite_id}")
def get_entite(
    entite_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détail d'une entité juridique (org-scoping cardinal Phase E)."""
    scope_org_id = resolve_org_id(request, auth, db)
    e = assert_org_owns_entite(db, entite_id, scope_org_id)
    return _entite_to_dict(e)


@router.patch("/entites/{entite_id}")
def update_entite(
    entite_id: int,
    body: EntiteJuridiqueUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Met à jour une entité juridique (org-scoping cardinal Phase E)."""
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    e = assert_org_owns_entite(db, entite_id, scope_org_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(e, field, value)
    db.commit()
    db.refresh(e)
    return _entite_to_dict(e)


@router.delete("/entites/{entite_id}")
def archive_entite(
    entite_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Archive (soft-delete) une entité juridique (org-scoping cardinal Phase E)."""
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    e = assert_org_owns_entite(db, entite_id, scope_org_id)
    e.soft_delete()
    db.commit()
    return {"status": "archived", "id": entite_id}


# ══════════════════════════════════════════════════════════════════════════════
# PORTEFEUILLES
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/portefeuilles")
def list_portefeuilles(
    request: Request,
    entite_id: Optional[int] = Query(None),
    org_id: Optional[int] = Query(None, description="Ignoré : forcé == scope_org_id (Phase E IDOR)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les portefeuilles du scope_org_id (Phase E IDOR cardinal).

    Le query param `org_id` est ignoré : org-scoping forcé côté serveur.
    `entite_id` est validé : doit appartenir au scope_org_id sinon résultat vide.
    """
    scope_org_id = resolve_org_id(request, auth, db)
    q = (
        db.query(Portefeuille)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(
            EntiteJuridique.organisation_id == scope_org_id,
            not_deleted(Portefeuille),
        )
    )
    if entite_id:
        q = q.filter(Portefeuille.entite_juridique_id == entite_id)
    pfs = q.all()
    return {"count": len(pfs), "portefeuilles": [_pf_to_dict(pf) for pf in pfs]}


@router.post("/portefeuilles", status_code=201)
def create_portefeuille(
    body: PortefeuilleCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Crée un portefeuille (org-scoping cardinal Phase E).

    L'EntiteJuridique parente DOIT appartenir au scope_org_id.
    """
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    assert_org_owns_entite(db, body.entite_juridique_id, scope_org_id)
    pf = Portefeuille(
        entite_juridique_id=body.entite_juridique_id,
        nom=body.nom,
        description=body.description,
    )
    db.add(pf)
    db.commit()
    db.refresh(pf)
    return _pf_to_dict(pf)


@router.get("/portefeuilles/{pf_id}")
def get_portefeuille(
    pf_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détail d'un portefeuille (org-scoping cardinal Phase E)."""
    scope_org_id = resolve_org_id(request, auth, db)
    pf = assert_org_owns_portefeuille(db, pf_id, scope_org_id)
    return _pf_to_dict(pf)


@router.patch("/portefeuilles/{pf_id}")
def update_portefeuille(
    pf_id: int,
    body: PortefeuilleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Met à jour un portefeuille (org-scoping cardinal Phase E)."""
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    pf = assert_org_owns_portefeuille(db, pf_id, scope_org_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pf, field, value)
    db.commit()
    db.refresh(pf)
    return _pf_to_dict(pf)


@router.delete("/portefeuilles/{pf_id}")
def archive_portefeuille(
    pf_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Archive (soft-delete) un portefeuille (org-scoping cardinal Phase E)."""
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    pf = assert_org_owns_portefeuille(db, pf_id, scope_org_id)
    pf.soft_delete()
    db.commit()
    return {"status": "archived", "id": pf_id}


# ══════════════════════════════════════════════════════════════════════════════
# SITES (CRUD complet via patrimoine_crud)
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/sites")
def list_sites_crud(
    request: Request,
    pf_id: Optional[int] = Query(None),
    org_id: Optional[int] = Query(None, description="Ignoré : forcé == scope_org_id (Phase E IDOR)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les sites du scope_org_id (Phase E IDOR cardinal).

    Le query param `org_id` est ignoré : org-scoping forcé côté serveur.
    """
    scope_org_id = resolve_org_id(request, auth, db)
    q = (
        db.query(Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(
            EntiteJuridique.organisation_id == scope_org_id,
            not_deleted(Site),
        )
    )
    if pf_id:
        q = q.filter(Site.portefeuille_id == pf_id)
    sites = q.all()
    return {"count": len(sites), "sites": [_site_to_dict(s) for s in sites]}


@router.post("/sites", status_code=201)
def create_site_crud(
    body: SiteCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Crée un site dans un portefeuille (org-scoping cardinal Phase E).

    Le portefeuille parent DOIT appartenir au scope_org_id.
    """
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    pf = assert_org_owns_portefeuille(db, body.portefeuille_id, scope_org_id)

    # Résoudre le TypeSite enum
    try:
        site_type = TypeSite(body.type)
    except ValueError:
        valid = [t.value for t in TypeSite]
        raise HTTPException(422, f"Type de site invalide : {body.type}. Valides : {valid}")

    site = Site(
        portefeuille_id=body.portefeuille_id,
        nom=body.nom,
        type=site_type,
        adresse=body.adresse,
        code_postal=body.code_postal,
        ville=body.ville,
        region=body.region,
        surface_m2=body.surface_m2,
        tertiaire_area_m2=body.tertiaire_area_m2,
        siret=body.siret,
        naf_code=body.naf_code,
        latitude=body.latitude,
        longitude=body.longitude,
        actif=True,
        data_source="manual",
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return _site_to_dict(site)


@router.get("/sites/{site_id}")
def get_site_crud(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détail d'un site (org-scoping cardinal Phase E)."""
    scope_org_id = resolve_org_id(request, auth, db)
    site = assert_org_owns_site(db, site_id, scope_org_id)
    return _site_to_dict(site)


@router.patch("/sites/{site_id}")
def update_site_crud(
    site_id: int,
    body: SiteUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Met à jour un site (org-scoping cardinal Phase E).

    F3 V117 : si surface_m2/type/tertiaire_area_m2 changent, re-declenche
    le scoring compliance (DT/BACS/APER) pour que le NextStepsHub post-Sirene
    affiche des scores reels au lieu d'un ecran vide.
    """
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    site = assert_org_owns_site(db, site_id, scope_org_id)
    updates = body.model_dump(exclude_unset=True)
    if "type" in updates and updates["type"] is not None:
        try:
            updates["type"] = TypeSite(updates["type"])
        except ValueError:
            raise HTTPException(422, f"Type de site invalide : {updates['type']}")

    compliance_impacting = {"surface_m2", "type", "tertiaire_area_m2"}
    needs_recompute = bool(compliance_impacting & updates.keys())

    for field, value in updates.items():
        setattr(site, field, value)

    # Propagation automatique tertiaire_area_m2 = surface_m2 si tertiaire + absent
    if "surface_m2" in updates and site.surface_m2 and not site.tertiaire_area_m2:
        from services.onboarding_service import is_tertiaire

        if is_tertiaire(site.type):
            site.tertiaire_area_m2 = site.surface_m2

    db.flush()

    if needs_recompute:
        try:
            from services.compliance_coordinator import recompute_site_full

            recompute_site_full(db, site_id)
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning("compliance recompute failed for site %d: %s", site_id, e)

    db.commit()
    db.refresh(site)
    return _site_to_dict(site)


@router.delete("/sites/{site_id}")
def archive_site_crud(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Archive (soft-delete) un site (org-scoping cardinal Phase E)."""
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    site = assert_org_owns_site(db, site_id, scope_org_id)
    site.soft_delete()
    from services.patrimoine_conformite_sync import cascade_site_archive

    cascade_site_archive(db, site_id)
    db.commit()
    return {"status": "archived", "id": site_id}


# ══════════════════════════════════════════════════════════════════════════════
# BATIMENTS
# ══════════════════════════════════════════════════════════════════════════════


def _bat_to_dict(b: Batiment) -> dict:
    return {
        "id": b.id,
        "site_id": b.site_id,
        "nom": b.nom,
        "surface_m2": b.surface_m2,
        "annee_construction": b.annee_construction,
        "cvc_power_kw": b.cvc_power_kw,
    }


@router.post("/batiments", status_code=201)
def create_batiment(
    body: BatimentCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Cree un batiment rattache a un site (org-scoping cardinal Phase E).

    Phase D-4 Tier 4 P0-2 fix audit code-reviewer : déclenche cascade BACS active
    (ADR-D-04) après commit pour recalculer Site.bacs_assujetti + bacs_puissance_cvc_totale_kw.
    """
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    site = assert_org_owns_site(db, body.site_id, scope_org_id)
    bat = Batiment(
        site_id=body.site_id,
        nom=body.nom,
        surface_m2=body.surface_m2,
        annee_construction=body.annee_construction,
        cvc_power_kw=body.cvc_power_kw,
    )
    db.add(bat)
    db.commit()
    db.refresh(bat)

    # Phase D-4 Tier 4 P0-2 : cascade BACS active si cvc_power_kw défini
    if bat.cvc_power_kw is not None:
        from services.cascade_bacs_service import recompute_site_bacs_aggregate

        recompute_site_bacs_aggregate(db, body.site_id, commit=True)

    return _bat_to_dict(bat)


@router.patch("/batiments/{batiment_id}")
def update_batiment(
    batiment_id: int,
    body: BatimentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Phase D-4 Tier 4 P1 : modifier un bâtiment + cascade BACS (Phase E IDOR cardinal).

    Phase E review : aligné sur le pattern PATCH canonique `model_dump(exclude_unset=True)`
    cohérent avec les autres endpoints (Org, EJ, Pf, Site).
    """
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    bat = assert_org_owns_batiment(db, batiment_id, scope_org_id)

    updates = body.model_dump(exclude_unset=True)
    cvc_changed = "cvc_power_kw" in updates and updates["cvc_power_kw"] != bat.cvc_power_kw
    for field, value in updates.items():
        setattr(bat, field, value)
    db.commit()
    db.refresh(bat)

    # Cascade BACS si cvc_power_kw modifié (ADR-D-04)
    if cvc_changed:
        from services.cascade_bacs_service import recompute_site_bacs_aggregate

        recompute_site_bacs_aggregate(db, bat.site_id, commit=True)

    return _bat_to_dict(bat)


@router.delete("/batiments/{batiment_id}")
def delete_batiment(
    batiment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Phase D-4 Tier 4 P1 : soft-delete bâtiment + cascade BACS rebuild (Phase E IDOR cardinal)."""
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    bat = assert_org_owns_batiment(db, batiment_id, scope_org_id)
    site_id = bat.site_id
    bat.soft_delete(by="api", reason="user_delete_batiment")
    db.commit()

    # Cascade BACS rebuild post soft-delete (ADR-D-04)
    from services.cascade_bacs_service import recompute_site_bacs_aggregate

    recompute_site_bacs_aggregate(db, site_id, commit=True)
    return {"status": "deleted", "id": batiment_id}
