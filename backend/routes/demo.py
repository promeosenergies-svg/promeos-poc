"""
PROMEOS - Demo Mode API Routes
POST /api/demo/enable, POST /api/demo/disable, GET /api/demo/status
POST /api/demo/seed - Peuple la DB avec un jeu de donnees demo (legacy 3 sites)
POST /api/demo/seed-pack - Seed complet par pack (casino, tertiaire)
POST /api/demo/reset-pack - Reset des donnees demo
GET /api/demo/status-pack - Status detaille des donnees demo
GET /api/demo/packs - Liste des packs disponibles
GET /api/demo/manifest - Source de verite: org, portefeuilles, sites, compteurs
GET /api/demo/templates, GET /api/demo/templates/{template_id}
"""
import hashlib
import json
import random
import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import require_admin
from models import (
    Organisation, EntiteJuridique, Portefeuille, Site, Compteur,
    TypeSite, TypeCompteur, EnergyVector,
)
from services.demo_state import DemoState
from services.onboarding_service import provision_site

router = APIRouter(prefix="/api/demo", tags=["Demo Mode"])

# Concurrency guard — prevent double-click / concurrent seed runs
_seed_lock = threading.Lock()


# --- Pydantic models for new endpoints ---

class SeedPackRequest(BaseModel):
    pack: str = "helios"
    size: str = "S"
    rng_seed: Optional[int] = 42
    reset: bool = False
    days: int = 90


class ResetPackRequest(BaseModel):
    mode: str = "soft"
    confirm: bool = False


# --- Mode toggle ---

@router.post("/enable")
def enable_demo():
    DemoState.enable()
    return DemoState.status()


@router.post("/disable")
def disable_demo():
    DemoState.disable()
    return DemoState.status()


@router.get("/status")
def get_demo_status():
    return DemoState.status()


# --- Pack-based endpoints ---

@router.get("/packs")
def list_demo_packs():
    """Liste des packs demo disponibles."""
    from services.demo_seed.packs import list_packs
    return {"packs": list_packs()}


@router.post("/seed-pack")
def seed_demo_pack(
    request: SeedPackRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin()),
):
    """
    Seed complet par pack. Admin-only. Concurrency-safe (409 on double-click).
    Returns org_id, summary counts, and checksum for idempotency verification.
    """
    acquired = _seed_lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(
            status_code=409,
            detail="Un chargement est deja en cours. Veuillez patienter.",
        )
    try:
        from services.demo_seed import SeedOrchestrator

        orch = SeedOrchestrator(db)

        if request.reset:
            orch.reset(mode="hard")

        result = orch.seed(
            pack=request.pack, size=request.size,
            rng_seed=request.rng_seed, days=request.days,
        )

        if result.get("error"):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": result["error"],
                    "available_packs": result.get("available", []),
                    "hint": "Si le pack existe dans packs.py mais n'est pas trouve, "
                            "redemarrez le backend: uvicorn main:app --reload",
                },
            )

        # Compute deterministic checksum for idempotency verification
        result["checksum"] = _compute_checksum(result)
        return result
    finally:
        _seed_lock.release()


def _compute_checksum(result: dict) -> str:
    """SHA-256 checksum over deterministic seed result fields."""
    payload = json.dumps({
        "pack": result.get("pack"),
        "size": result.get("size"),
        "org_id": result.get("org_id"),
        "sites_count": result.get("sites_count"),
        "meters_count": result.get("meters_count"),
        "readings_count": result.get("readings_count"),
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@router.get("/status-pack")
def get_demo_pack_status(db: Session = Depends(get_db)):
    """Status détaillé: comptage par table + current org/site for scope.

    Uses DemoState to resolve the correct org — not Organisation.first() which
    would return a stale/wrong org when multiple seeds have been run.
    Returns sites_count scoped to the seeded org.
    """
    from services.demo_seed import SeedOrchestrator
    ctx = DemoState.get_demo_context()
    org_id = ctx.get("org_id")

    # Resolve org from DemoState only — NO fallback to avoid stale org after reset
    org = db.query(Organisation).filter(Organisation.id == org_id).first() if org_id else None

    orch = SeedOrchestrator(db)
    counts = orch.status(org_id=org.id if org else None)

    result = {
        "demo_enabled": DemoState.is_enabled(),
        "counts": counts,
        "total_rows": sum(counts.values()),
        "pack": ctx.get("pack"),
        "size": ctx.get("size"),
    }

    if org:
        result["org_id"] = org.id
        result["org_nom"] = org.nom
        # sites_count is already scoped to org (from orch.status(org_id=...))
        result["sites_count"] = counts.get("sites", 0)

        # default_site: use DemoState-registered; fallback to first active site of this org
        dsid = ctx.get("default_site_id")
        if dsid:
            result["default_site_id"] = dsid
            result["default_site_name"] = ctx.get("default_site_name")
        else:
            from models import Portefeuille, EntiteJuridique
            first_site = (
                db.query(Site)
                .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
                .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
                .filter(EntiteJuridique.organisation_id == org.id, Site.actif == True)
                .first()
            )
            if first_site:
                result["default_site_id"] = first_site.id
                result["default_site_name"] = first_site.nom

    return result


@router.get("/manifest")
def get_demo_manifest(db: Session = Depends(get_db)):
    """Source de verite de la demo: org, portefeuilles, sites, compteurs.

    Returns the canonical state after seed — live counts from DB.
    Used by the frontend to guarantee consistency across all views.
    """
    ctx = DemoState.get_demo_context()
    org_id = ctx.get("org_id")

    if not org_id:
        raise HTTPException(status_code=404, detail="No demo seeded")

    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found in DB")

    entites = db.query(EntiteJuridique).filter(
        EntiteJuridique.organisation_id == org.id
    ).all()

    portefeuilles = []
    total_sites = 0
    total_compteurs = 0
    all_site_ids = []

    for ej in entites:
        for p in db.query(Portefeuille).filter(
            Portefeuille.entite_juridique_id == ej.id
        ).all():
            sites = db.query(Site).filter(Site.portefeuille_id == p.id).all()
            compteurs_count = (
                db.query(Compteur).filter(Compteur.site_id.in_([s.id for s in sites])).count()
                if sites else 0
            )
            total_sites += len(sites)
            total_compteurs += compteurs_count
            site_ids = [s.id for s in sites]
            all_site_ids.extend(site_ids)
            portefeuilles.append({
                "id": p.id,
                "nom": p.nom,
                "entite_juridique_id": ej.id,
                "sites_count": len(sites),
                "site_ids": site_ids,
            })

    return {
        "org_id": org.id,
        "org_nom": org.nom,
        "pack": ctx.get("pack"),
        "size": ctx.get("size"),
        "portefeuilles": portefeuilles,
        "total_sites": total_sites,
        "total_compteurs": total_compteurs,
        "all_site_ids": all_site_ids,
    }


def _reset_iam_demo(db):
    """Delete @atlas.demo users and their roles, then re-seed IAM."""
    from models import User, UserOrgRole
    demo_users = db.query(User).filter(User.email.like("%@atlas.demo")).all()
    for u in demo_users:
        db.query(UserOrgRole).filter(UserOrgRole.user_id == u.id).delete()
        db.query(User).filter(User.id == u.id).delete()
    db.commit()
    # Re-seed IAM if an org still exists
    org = db.query(Organisation).first()
    if org:
        from scripts.seed_data import seed_iam_demo
        seed_iam_demo(db, org)


@router.post("/reset-pack")
def reset_demo_pack(
    request: ResetPackRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin()),
):
    """Reset des donnees demo. Admin-only.
    mode=soft (demo only) ou hard (tout). Also resets IAM demo users."""
    if request.mode == "hard" and not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Hard reset requires confirm=true. This will delete ALL data."
        )

    from services.demo_seed import SeedOrchestrator
    orch = SeedOrchestrator(db)
    result = orch.reset(mode=request.mode)

    # Also reset IAM demo users
    _reset_iam_demo(db)

    # V62 — invalider le cache trend portfolio (les snapshots ne sont plus valides)
    from services.patrimoine_portfolio_cache import clear_all as _clear_portfolio_cache
    _clear_portfolio_cache()

    return result


_DEMO_SITES = [
    {"nom": "Hypermarche Montreuil", "type": TypeSite.COMMERCE, "ville": "Montreuil", "cp": "93100", "surface": 4500},
    {"nom": "Bureau Haussmann", "type": TypeSite.BUREAU, "ville": "Paris", "cp": "75008", "surface": 1200},
    {"nom": "Entrepot Rungis", "type": TypeSite.ENTREPOT, "ville": "Rungis", "cp": "94150", "surface": 8000},
]


@router.post("/seed")
def seed_demo(db: Session = Depends(get_db)):
    """
    Peuple la DB avec un jeu de donnees demo:
    1 org + 2 entites juridiques + 1 portefeuille + 3 sites + compteurs + obligations.
    Erreur 409 si une organisation existe deja.
    """
    existing = db.query(Organisation).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Organisation '{existing.nom}' existe deja. Supprimez d'abord l'existante."
        )

    # Organisation
    org = Organisation(nom="Demo PROMEOS", type_client="tertiaire", actif=True, siren="999888777")
    db.add(org)
    db.flush()

    # 2 entites juridiques
    ej1 = EntiteJuridique(organisation_id=org.id, nom="Demo SAS", siren="999888777")
    ej2 = EntiteJuridique(organisation_id=org.id, nom="Demo Logistics SARL", siren="999888666")
    db.add_all([ej1, ej2])
    db.flush()

    # 1 portefeuille
    pf = Portefeuille(entite_juridique_id=ej1.id, nom="Portefeuille Demo", description="Sites de demonstration")
    db.add(pf)
    db.flush()

    sites_created = []
    for s_data in _DEMO_SITES:
        site = Site(
            portefeuille_id=pf.id,
            nom=s_data["nom"],
            type=s_data["type"],
            ville=s_data["ville"],
            code_postal=s_data["cp"],
            surface_m2=s_data["surface"],
            actif=True,
            tertiaire_area_m2=s_data["surface"],
        )
        db.add(site)
        db.flush()

        # 2 compteurs par site (elec + gaz)
        for i, (tc, ev) in enumerate([(TypeCompteur.ELECTRICITE, EnergyVector.ELECTRICITY), (TypeCompteur.GAZ, EnergyVector.GAS)]):
            c = Compteur(
                site_id=site.id,
                type=tc,
                numero_serie=f"DEMO-{site.id}-{i+1:02d}",
                puissance_souscrite_kw=random.randint(50, 300) if tc == TypeCompteur.ELECTRICITE else None,
                meter_id=f"{random.randint(10000000000000, 99999999999999)}",
                energy_vector=ev,
                actif=True,
            )
            db.add(c)

        prov = provision_site(db, site)
        sites_created.append({
            "id": site.id,
            "nom": site.nom,
            "type": site.type.value,
            **prov,
        })

    db.commit()

    DemoState.enable()

    return {
        "status": "ok",
        "organisation_id": org.id,
        "entites_juridiques": 2,
        "portefeuilles": 1,
        "sites_created": len(sites_created),
        "compteurs_created": len(sites_created) * 2,
        "sites": sites_created,
    }


@router.get("/templates")
def get_templates():
    """Liste des profils demo disponibles."""
    from services.demo_templates import get_all_templates
    return {"templates": get_all_templates()}


@router.get("/templates/{template_id}")
def get_template_detail(template_id: str):
    """Detail d'un profil demo."""
    from services.demo_templates import get_template
    tpl = get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template non trouve")
    return tpl
