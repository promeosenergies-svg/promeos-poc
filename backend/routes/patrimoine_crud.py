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
from schemas.patrimoine_schemas import QuickCreateSiteRequest
from sqlalchemy import func
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
from services.auth_guards import (  # noqa: E402
    require_admin_access as _require_admin_access,
    require_write_access as _require_write_access,
)


# ── Audit helpers (P0-A 2026-05-23) ──────────────────────────────────────────
# Pattern cardinal : capture before/after sur les mutations, écrit un audit log
# par requête via `audit_log_service.log_patrimoine_change`. Source-guard AST
# `test_patrimoine_crud_audit_log_wiring_source_guards.py` verrouille la
# présence de l'appel sur chaque PATCH/DELETE.


def _coerce_value(v):
    """Sérialise les Enum SQLAlchemy en .value pour comparaison et stockage."""
    return v.value if hasattr(v, "value") else v


def _capture_before(entity, fields):
    """Snapshot des valeurs avant mutation pour audit diff."""
    return {f: _coerce_value(getattr(entity, f, None)) for f in fields}


def _diff_after(entity, before):
    """Retourne {field: {before, after}} pour les seuls champs réellement modifiés."""
    diff = {}
    for f, old in before.items():
        new = _coerce_value(getattr(entity, f, None))
        if new != old:
            diff[f] = {"before": old, "after": new}
    return diff


def _audit_headers(request: Request, auth: Optional[AuthContext]):
    """Extrait correlation_id / ip / user-agent / user_id pour audit log."""
    return {
        "correlation_id": request.headers.get("X-Correlation-ID"),
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "user_id": getattr(auth, "user_id", None) if auth else None,
    }


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

    Phase F audit P0-3 fix code-reviewer : `_require_admin_access` strict
    DG_OWNER/DSI_ADMIN uniquement (avant ce fix, `_require_write_access` autorisait
    8 rôles à créer des organisations orphelines en DEMO_MODE).
    """
    _require_admin_access(auth)
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
    P0-A 2026-05-23 : audit log explicite sur toutes les mutations (avant fix,
    seul le wiring cascade consent existait — les autres champs étaient mutés
    silencieusement).
    """
    from regops.services.cascade_recompute_service import cascade_recompute_on_change
    from services.audit_log_service import log_patrimoine_change

    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    org = assert_org_owns_organisation(db, org_id, scope_org_id)

    payload = body.model_dump(exclude_unset=True)
    before = _capture_before(org, list(payload.keys()))
    cascade_old_consent = {
        "consentement_dataconnect_global": before.get("consentement_dataconnect_global"),
        "consentement_grdf_global": before.get("consentement_grdf_global"),
    }

    for field, value in payload.items():
        setattr(org, field, value)
    db.flush()
    diff = _diff_after(org, before)

    headers = _audit_headers(request, auth)
    if diff:
        log_patrimoine_change(
            db,
            user_id=headers["user_id"],
            org_id=org_id,
            entity_type="organisation",
            entity_id=org_id,
            action="organisation.update",
            field_modified=",".join(diff.keys()) if len(diff) > 1 else next(iter(diff)),
            old_value={k: v["before"] for k, v in diff.items()},
            new_value={k: v["after"] for k, v in diff.items()},
            correlation_id=headers["correlation_id"],
            ip_address=headers["ip_address"],
            user_agent=headers["user_agent"],
            detail=diff,
        )

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
                    old_value=cascade_old_consent[cascade_field],
                    new_value=payload[cascade_field],
                    persist=True,
                    user_id=headers["user_id"],
                    org_id=org_id,
                    correlation_id=headers["correlation_id"],
                    ip_address=headers["ip_address"],
                    user_agent=headers["user_agent"],
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
    """Archive (soft-delete) une organisation (org-scoping cardinal Phase E).

    P0-A 2026-05-23 : log_patrimoine_change wiré (avant fix, soft-delete silencieux).
    """
    from services.audit_log_service import log_patrimoine_change

    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    org = assert_org_owns_organisation(db, org_id, scope_org_id)
    snapshot = {"nom": org.nom, "siren": org.siren}
    org.soft_delete()
    db.flush()

    headers = _audit_headers(request, auth)
    log_patrimoine_change(
        db,
        user_id=headers["user_id"],
        org_id=org_id,
        entity_type="organisation",
        entity_id=org_id,
        action="organisation.archive",
        old_value=snapshot,
        correlation_id=headers["correlation_id"],
        ip_address=headers["ip_address"],
        user_agent=headers["user_agent"],
    )
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
    """Met à jour une entité juridique (org-scoping cardinal Phase E).

    P0-A 2026-05-23 : audit log wiré (avant fix, setattr+commit silencieux).
    """
    from services.audit_log_service import log_patrimoine_change

    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    e = assert_org_owns_entite(db, entite_id, scope_org_id)

    payload = body.model_dump(exclude_unset=True)
    before = _capture_before(e, list(payload.keys()))
    for field, value in payload.items():
        setattr(e, field, value)
    db.flush()
    diff = _diff_after(e, before)

    if diff:
        headers = _audit_headers(request, auth)
        log_patrimoine_change(
            db,
            user_id=headers["user_id"],
            org_id=scope_org_id,
            entity_type="entite_juridique",
            entity_id=entite_id,
            action="entite_juridique.update",
            field_modified=",".join(diff.keys()) if len(diff) > 1 else next(iter(diff)),
            old_value={k: v["before"] for k, v in diff.items()},
            new_value={k: v["after"] for k, v in diff.items()},
            correlation_id=headers["correlation_id"],
            ip_address=headers["ip_address"],
            user_agent=headers["user_agent"],
            detail=diff,
        )

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
    """Archive (soft-delete) une entité juridique (org-scoping cardinal Phase E).

    P0-A 2026-05-23 : log_patrimoine_change wiré.
    """
    from services.audit_log_service import log_patrimoine_change

    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    e = assert_org_owns_entite(db, entite_id, scope_org_id)
    snapshot = {"nom": e.nom, "siren": e.siren, "siret": e.siret}
    e.soft_delete()
    db.flush()

    headers = _audit_headers(request, auth)
    log_patrimoine_change(
        db,
        user_id=headers["user_id"],
        org_id=scope_org_id,
        entity_type="entite_juridique",
        entity_id=entite_id,
        action="entite_juridique.archive",
        old_value=snapshot,
        correlation_id=headers["correlation_id"],
        ip_address=headers["ip_address"],
        user_agent=headers["user_agent"],
    )
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
    """Met à jour un portefeuille (org-scoping cardinal Phase E).

    P0-A 2026-05-23 : audit log wiré.
    """
    from services.audit_log_service import log_patrimoine_change

    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    pf = assert_org_owns_portefeuille(db, pf_id, scope_org_id)

    payload = body.model_dump(exclude_unset=True)
    before = _capture_before(pf, list(payload.keys()))
    for field, value in payload.items():
        setattr(pf, field, value)
    db.flush()
    diff = _diff_after(pf, before)

    if diff:
        headers = _audit_headers(request, auth)
        log_patrimoine_change(
            db,
            user_id=headers["user_id"],
            org_id=scope_org_id,
            entity_type="portefeuille",
            entity_id=pf_id,
            action="portefeuille.update",
            field_modified=",".join(diff.keys()) if len(diff) > 1 else next(iter(diff)),
            old_value={k: v["before"] for k, v in diff.items()},
            new_value={k: v["after"] for k, v in diff.items()},
            correlation_id=headers["correlation_id"],
            ip_address=headers["ip_address"],
            user_agent=headers["user_agent"],
            detail=diff,
        )

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
    """Archive (soft-delete) un portefeuille (org-scoping cardinal Phase E).

    P0-A 2026-05-23 : log_patrimoine_change wiré.
    """
    from services.audit_log_service import log_patrimoine_change

    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    pf = assert_org_owns_portefeuille(db, pf_id, scope_org_id)
    snapshot = {"nom": pf.nom, "entite_juridique_id": pf.entite_juridique_id}
    pf.soft_delete()
    db.flush()

    headers = _audit_headers(request, auth)
    log_patrimoine_change(
        db,
        user_id=headers["user_id"],
        org_id=scope_org_id,
        entity_type="portefeuille",
        entity_id=pf_id,
        action="portefeuille.archive",
        old_value=snapshot,
        correlation_id=headers["correlation_id"],
        ip_address=headers["ip_address"],
        user_agent=headers["user_agent"],
    )
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

    Phase F.9 — Audit page cockpit/jour : ce endpoint sert le scope switcher
    de l'AppShell (ScopeContext.orgSites). Sans filtre `is_demo`, les 2 sites
    "Site Test Phase 2" parasites apparaissaient dans le label "Groupe HELIOS
    — 7 sites" du switcher, désynchronisé du hero meta cockpit/jour "5 SITES"
    (qui passe par `_sites_for_org` factorisé Correctif #3).

    Délégation à `services.scope_utils.sites_for_org_query` pour appliquer
    le même filtre `Site.is_demo == Organisation.is_demo` cross-tenant.
    """
    from services.scope_utils import sites_for_org_query

    scope_org_id = resolve_org_id(request, auth, db)
    q = sites_for_org_query(db, scope_org_id)
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

    # Audit log : création site explicite
    from services.audit_log_service import log_patrimoine_change

    log_patrimoine_change(
        db,
        user_id=getattr(auth, "user_id", None) if auth else None,
        org_id=scope_org_id,
        entity_type="site",
        entity_id=site.id,
        action="site.create",
        new_value={
            "nom": site.nom,
            "portefeuille_id": site.portefeuille_id,
            "type": site.type.value if site.type else None,
            "code_postal": site.code_postal,
            "surface_m2": site.surface_m2,
        },
        correlation_id=request.headers.get("X-Correlation-ID"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return _site_to_dict(site)


@router.post("/sites/quick-create", status_code=201)
def quick_create_site_crud(
    body: QuickCreateSiteRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Création rapide d'un site B2B France (route canonique Patrimoine).

    Auto-crée la hiérarchie (Société + Entité juridique + Portefeuille)
    si aucune n'existe pour le scope courant. Auto-provisionne bâtiment +
    obligations + compliance. Détecte les doublons par nom + code postal.

    P0-A 2026-05-23 : route relocalisée depuis `/api/sites/quick-create`
    (legacy déprécié, retourne 410 Gone) vers le namespace patrimoine canonique.
    Wire audit_log_service + cascade conformité explicite.
    """
    _require_write_access(auth)

    from services.onboarding_service import (
        create_organisation_full,
        create_site_from_data,
        provision_site,
    )
    from services.audit_log_service import log_patrimoine_change

    correlation_id = request.headers.get("X-Correlation-ID")
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    user_id = getattr(auth, "user_id", None) if auth else None

    # ── 1. Résoudre ou créer l'organisation (scope multi-tenant) ──────────
    org_id: Optional[int] = None
    auto_created: dict = {}

    try:
        org_id = resolve_org_id(request, auth, db)
    except Exception:
        org_id = None

    if org_id is None:
        existing_org = db.query(Organisation).filter(Organisation.actif.is_(True), not_deleted(Organisation)).first()
        if existing_org:
            org_id = existing_org.id
        else:
            result = create_organisation_full(
                db=db,
                org_nom="Mon entreprise",
                org_siren="000000000",
                org_type_client="tertiaire",
                portefeuilles_data=[{"nom": "Principal"}],
            )
            org_id = result["organisation_id"]
            auto_created["organisation"] = result["organisation_id"]
            auto_created["entite_juridique"] = result["entite_juridique_id"]
            auto_created["portefeuille"] = result["default_portefeuille_id"]
            db.flush()

    # ── 2. Résoudre ou créer le portefeuille parent ───────────────────────
    pf = (
        db.query(Portefeuille)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id, not_deleted(Portefeuille))
        .first()
    )
    if not pf:
        ej = (
            db.query(EntiteJuridique)
            .filter(EntiteJuridique.organisation_id == org_id, not_deleted(EntiteJuridique))
            .first()
        )
        if not ej:
            org = db.query(Organisation).filter(Organisation.id == org_id).first()
            ej = EntiteJuridique(
                organisation_id=org_id,
                nom=org.nom if org else "Entité principale",
                siren=org.siren if org and org.siren else "000000000",
            )
            db.add(ej)
            db.flush()
            auto_created["entite_juridique"] = ej.id
        pf = Portefeuille(entite_juridique_id=ej.id, nom="Principal")
        db.add(pf)
        db.flush()
        auto_created["portefeuille"] = pf.id

    # ── 3. Anti-doublons (case-insensitive, 2 niveaux) ────────────────────
    if not body.skip_duplicate_check:
        nom_lower = func.lower(Site.nom)
        body_nom_lower = body.nom.strip().lower()

        if body.code_postal:
            exact = (
                db.query(Site)
                .filter(
                    nom_lower == body_nom_lower,
                    Site.code_postal == body.code_postal.strip(),
                    not_deleted(Site),
                )
                .first()
            )
            if exact:
                return {
                    "status": "duplicate_detected",
                    "level": "exact",
                    "existing_site": {
                        "id": exact.id,
                        "nom": exact.nom,
                        "ville": exact.ville,
                        "code_postal": exact.code_postal,
                    },
                    "message": f'Un site "{exact.nom}" existe déjà à {exact.ville or exact.code_postal}',
                }

        if body.ville:
            similar = (
                db.query(Site)
                .filter(
                    nom_lower == body_nom_lower,
                    func.lower(Site.ville) == body.ville.strip().lower(),
                    not_deleted(Site),
                )
                .first()
            )
            if similar:
                return {
                    "status": "duplicate_detected",
                    "level": "similar",
                    "existing_site": {
                        "id": similar.id,
                        "nom": similar.nom,
                        "ville": similar.ville,
                        "code_postal": similar.code_postal,
                    },
                    "message": f'Un site similaire "{similar.nom}" existe à {similar.ville}',
                }

    # ── 4. Créer le site + auto-provision (bâtiment + obligations) ────────
    site = create_site_from_data(
        db=db,
        portefeuille_id=pf.id,
        nom=body.nom,
        type_site=body.usage,
        naf_code=body.naf_code,
        adresse=body.adresse,
        code_postal=body.code_postal,
        ville=body.ville,
        surface_m2=body.surface_m2,
    )
    if body.siret:
        site.siret = body.siret
    site.data_source = "manual"

    prov = provision_site(db, site)

    # ── 5. Cascade conformité + audit log (idempotent batch) ──────────────
    from regops.services.cascade_recompute_service import batch_cascade_recompute_sites

    cascade_summary = batch_cascade_recompute_sites(
        db,
        site_ids=[site.id],
        org_id=org_id,
        user_id=user_id,
        correlation_id=correlation_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Audit log explicite création site (cascade a son propre log_cascade)
    log_patrimoine_change(
        db,
        user_id=user_id,
        org_id=org_id,
        entity_type="site",
        entity_id=site.id,
        action="site.create",
        new_value={
            "nom": site.nom,
            "portefeuille_id": pf.id,
            "type": site.type.value if site.type else None,
            "code_postal": site.code_postal,
            "ville": site.ville,
            "surface_m2": site.surface_m2,
            "siret": site.siret,
        },
        correlation_id=correlation_id,
        ip_address=ip_address,
        user_agent=user_agent,
        detail={"auto_created": auto_created} if auto_created else None,
    )

    db.commit()

    return {
        "status": "created",
        "site": {
            "id": site.id,
            "nom": site.nom,
            "usage": site.type.value if site.type else None,
            "adresse": site.adresse,
            "code_postal": site.code_postal,
            "ville": site.ville,
            "surface_m2": site.surface_m2,
            "actif": site.actif,
        },
        "auto_provisioned": {
            "batiment_id": prov.get("batiment_id"),
            "cvc_power_kw": prov.get("cvc_power_kw"),
            "obligations": prov.get("obligations", 0),
            "delivery_points": prov.get("delivery_points_created", 0),
        },
        "auto_created": auto_created,
        "cascade": cascade_summary,
    }


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

    P0-A 2026-05-23 :
    - audit log explicite (avant fix, mutation silencieuse)
    - recompute échoué → HTTP 500 PATRIMOINE_RECOMPUTE_FAILED + rollback
      (avant fix, exception avalée → conformité stale silencieuse).
    """
    from services.audit_log_service import log_patrimoine_change

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

    before = _capture_before(site, list(updates.keys()))

    for field, value in updates.items():
        setattr(site, field, value)

    # Propagation automatique tertiaire_area_m2 = surface_m2 si tertiaire + absent
    if "surface_m2" in updates and site.surface_m2 and not site.tertiaire_area_m2:
        from services.onboarding_service import is_tertiaire

        if is_tertiaire(site.type):
            site.tertiaire_area_m2 = site.surface_m2

    db.flush()
    diff = _diff_after(site, before)

    headers = _audit_headers(request, auth)
    if diff:
        log_patrimoine_change(
            db,
            user_id=headers["user_id"],
            org_id=scope_org_id,
            entity_type="site",
            entity_id=site_id,
            action="site.update",
            field_modified=",".join(diff.keys()) if len(diff) > 1 else next(iter(diff)),
            old_value={k: v["before"] for k, v in diff.items()},
            new_value={k: v["after"] for k, v in diff.items()},
            correlation_id=headers["correlation_id"],
            ip_address=headers["ip_address"],
            user_agent=headers["user_agent"],
            detail=diff,
        )

    if needs_recompute:
        # P0-A 2026-05-23 : ne plus avaler les erreurs — rollback + erreur claire.
        from services.compliance_coordinator import recompute_site_full

        try:
            recompute_site_full(db, site_id)
        except Exception as exc:  # noqa: BLE001 — re-raise propre via HTTPException
            import logging

            db.rollback()
            logging.getLogger(__name__).error("compliance recompute failed for site %d: %s", site_id, exc)
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "PATRIMOINE_RECOMPUTE_FAILED",
                    "message": "Le site a été modifié mais le recalcul réglementaire a échoué.",
                    "hint": "Réessayez ou vérifiez les données du site.",
                    "correlation_id": headers["correlation_id"],
                    "blocking": True,
                },
            )

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
    """Archive (soft-delete) un site (org-scoping cardinal Phase E).

    P0-A 2026-05-23 : log_patrimoine_change wiré (avant fix, cascade silencieuse).
    """
    from services.audit_log_service import log_patrimoine_change
    from services.patrimoine_conformite_sync import cascade_site_archive

    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    site = assert_org_owns_site(db, site_id, scope_org_id)
    snapshot = {
        "nom": site.nom,
        "portefeuille_id": site.portefeuille_id,
        "type": site.type.value if site.type else None,
        "code_postal": site.code_postal,
        "ville": site.ville,
    }
    site.soft_delete()
    cascade_site_archive(db, site_id)
    db.flush()

    headers = _audit_headers(request, auth)
    log_patrimoine_change(
        db,
        user_id=headers["user_id"],
        org_id=scope_org_id,
        entity_type="site",
        entity_id=site_id,
        action="site.archive",
        old_value=snapshot,
        correlation_id=headers["correlation_id"],
        ip_address=headers["ip_address"],
        user_agent=headers["user_agent"],
    )
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
    P0-A 2026-05-23 : audit log wiré (avant fix, mutation silencieuse).
    """
    from services.audit_log_service import log_patrimoine_change

    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    bat = assert_org_owns_batiment(db, batiment_id, scope_org_id)

    updates = body.model_dump(exclude_unset=True)
    before = _capture_before(bat, list(updates.keys()))
    cvc_changed = "cvc_power_kw" in updates and updates["cvc_power_kw"] != bat.cvc_power_kw
    for field, value in updates.items():
        setattr(bat, field, value)
    db.flush()
    diff = _diff_after(bat, before)

    headers = _audit_headers(request, auth)
    if diff:
        log_patrimoine_change(
            db,
            user_id=headers["user_id"],
            org_id=scope_org_id,
            entity_type="batiment",
            entity_id=batiment_id,
            action="batiment.update",
            field_modified=",".join(diff.keys()) if len(diff) > 1 else next(iter(diff)),
            old_value={k: v["before"] for k, v in diff.items()},
            new_value={k: v["after"] for k, v in diff.items()},
            correlation_id=headers["correlation_id"],
            ip_address=headers["ip_address"],
            user_agent=headers["user_agent"],
            detail=diff,
        )

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
    """Phase D-4 Tier 4 P1 : soft-delete bâtiment + cascade BACS rebuild (Phase E IDOR cardinal).

    P0-A 2026-05-23 : log_patrimoine_change wiré.
    """
    from services.audit_log_service import log_patrimoine_change

    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    bat = assert_org_owns_batiment(db, batiment_id, scope_org_id)
    site_id = bat.site_id
    snapshot = {
        "site_id": site_id,
        "nom": bat.nom,
        "surface_m2": bat.surface_m2,
        "cvc_power_kw": bat.cvc_power_kw,
    }
    bat.soft_delete(by="api", reason="user_delete_batiment")
    db.flush()

    headers = _audit_headers(request, auth)
    log_patrimoine_change(
        db,
        user_id=headers["user_id"],
        org_id=scope_org_id,
        entity_type="batiment",
        entity_id=batiment_id,
        action="batiment.delete",
        old_value=snapshot,
        correlation_id=headers["correlation_id"],
        ip_address=headers["ip_address"],
        user_agent=headers["user_agent"],
    )
    db.commit()

    # Cascade BACS rebuild post soft-delete (ADR-D-04)
    from services.cascade_bacs_service import recompute_site_bacs_aggregate

    recompute_site_bacs_aggregate(db, site_id, commit=True)
    return {"status": "deleted", "id": batiment_id}
