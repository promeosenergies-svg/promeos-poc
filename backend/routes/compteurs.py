"""
PROMEOS - Routes API pour les Compteurs
"""

import time
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database import get_db
from models import Compteur, Site, TypeCompteur, EnergyVector, not_deleted
from routes.schemas import CompteurResponse
from typing import List, Optional

router = APIRouter(prefix="/api/compteurs", tags=["Compteurs"])


def _generate_unique_meter_id(site_id: int) -> str:
    """Generate a deterministic, collision-free meter_id.

    Format: AUTO-{site_id:06d}-{timestamp_hex} (14+ chars, unique by construction).
    This is a placeholder value — real PRM/PCE should come from import or manual entry.
    """
    ts_hex = format(int(time.time() * 1000) % 0xFFFFFFFF, "08x")
    return f"AUTO-{site_id:06d}-{ts_hex}"


def _generate_unique_numero_serie(db: Session, site_id: int) -> str:
    """Generate next sequential numero_serie for a site.

    Format: CPT-{site_id}-{seq} where seq is max(existing) + 1.
    """
    max_seq = (
        db.query(func.max(Compteur.numero_serie))
        .filter(Compteur.site_id == site_id, Compteur.numero_serie.like(f"CPT-{site_id}-%"))
        .scalar()
    )
    if max_seq:
        try:
            last_num = int(max_seq.rsplit("-", 1)[-1])
        except (ValueError, IndexError):
            last_num = 0
    else:
        last_num = 0
    return f"CPT-{site_id}-{last_num + 1}"


class CompteurCreateRequest(BaseModel):
    site_id: int
    type: str  # "electricite", "gaz", "eau"
    numero_serie: Optional[str] = None
    puissance_souscrite_kw: Optional[float] = None
    meter_id: Optional[str] = None  # PRM/PCE (14 chiffres) — auto-cree le DeliveryPoint


@router.post("")
def create_compteur(req: CompteurCreateRequest, db: Session = Depends(get_db)):
    """Cree un compteur sur un site existant."""
    site = db.query(Site).filter(Site.id == req.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    try:
        tc = TypeCompteur(req.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Type invalide: {req.type}. Valeurs: electricite, gaz, eau")

    ev_map = {
        TypeCompteur.ELECTRICITE: EnergyVector.ELECTRICITY,
        TypeCompteur.GAZ: EnergyVector.GAS,
        TypeCompteur.EAU: EnergyVector.OTHER,
    }

    num_serie = req.numero_serie or _generate_unique_numero_serie(db, site.id)
    meter_id = req.meter_id or _generate_unique_meter_id(site.id)

    c = Compteur(
        site_id=site.id,
        type=tc,
        numero_serie=num_serie,
        puissance_souscrite_kw=req.puissance_souscrite_kw,
        meter_id=meter_id,
        energy_vector=ev_map.get(tc, EnergyVector.OTHER),
        actif=True,
    )
    db.add(c)

    # Retry up to 3 times on IntegrityError (numero_serie collision)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            db.commit()
            break
        except IntegrityError:
            db.rollback()
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=409,
                    detail="Impossible de generer un numero de serie unique apres 3 tentatives",
                )
            c.numero_serie = _generate_unique_numero_serie(db, site.id)
            c.meter_id = _generate_unique_meter_id(site.id)
            db.add(c)

    db.refresh(c)

    # Auto-créer DeliveryPoint si meter_id reel (#105)
    from services.onboarding_service import ensure_delivery_points_for_site

    ensure_delivery_points_for_site(db, site.id)
    db.commit()

    return {
        "id": c.id,
        "site_id": c.site_id,
        "type": c.type.value,
        "numero_serie": c.numero_serie,
        "puissance_souscrite_kw": c.puissance_souscrite_kw,
    }


@router.get("", response_model=List[CompteurResponse])
def get_compteurs(
    site_id: Optional[int] = Query(None, description="Filtrer par site"),
    type: Optional[str] = Query(None, description="Filtrer par type (electricite, gaz, eau)"),
    db: Session = Depends(get_db),
):
    """
    Liste les compteurs avec filtres
    """
    query = not_deleted(db.query(Compteur), Compteur)

    if site_id:
        query = query.filter(Compteur.site_id == site_id)
    if type:
        query = query.filter(Compteur.type == type)

    compteurs = query.all()
    return compteurs


@router.get("/{compteur_id}", response_model=CompteurResponse)
def get_compteur(compteur_id: int, db: Session = Depends(get_db)):
    """
    Récupère un compteur spécifique
    """
    compteur = not_deleted(db.query(Compteur), Compteur).filter(Compteur.id == compteur_id).first()

    if not compteur:
        raise HTTPException(status_code=404, detail="Compteur non trouvé")

    return compteur
