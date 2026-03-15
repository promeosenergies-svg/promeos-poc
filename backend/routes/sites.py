"""
PROMEOS - Routes API pour les Sites
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import (
    Site,
    Portefeuille,
    EntiteJuridique,
    Compteur,
    Alerte,
    Consommation,
    Obligation,
    Evidence,
    Batiment,
    StatutConformite,
    StatutEvidence,
    TypeObligation,
    not_deleted,
)
from routes.schemas import SiteResponse, SiteListResponse, SiteStats, SiteComplianceResponse, BatimentResponse
from services.compliance_engine import compute_action_recommandee, _ACTION_TEMPLATES
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import check_site_access, apply_scope_filter
from services.scope_utils import resolve_org_id
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/sites", tags=["Sites"])


class SiteCreateRequest(BaseModel):
    nom: str = Field(..., min_length=1, max_length=300)
    type: Optional[str] = Field(None, max_length=50)
    naf_code: Optional[str] = Field(None, max_length=10)
    adresse: Optional[str] = Field(None, max_length=500)
    code_postal: Optional[str] = Field(None, max_length=10)
    ville: Optional[str] = Field(None, max_length=200)
    surface_m2: Optional[float] = Field(None, ge=0, le=1e7)


class QuickCreateRequest(BaseModel):
    """Création rapide de site — 2 champs obligatoires, tout le reste auto-généré."""

    nom: str = Field(..., min_length=1, max_length=300, description="Nom du site")
    usage: Optional[str] = Field(None, max_length=50, description="Usage (bureau, commerce, etc.)")
    adresse: Optional[str] = Field(None, max_length=500)
    code_postal: Optional[str] = Field(None, max_length=10)
    ville: Optional[str] = Field(None, max_length=200)
    surface_m2: Optional[float] = Field(None, ge=0, le=1e7)
    siret: Optional[str] = Field(None, max_length=14)
    naf_code: Optional[str] = Field(None, max_length=10)


@router.post("/quick-create", status_code=201)
def quick_create_site(
    body: QuickCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Création rapide d'un site B2B France.

    Auto-crée la hiérarchie (Société + Entité juridique + Portefeuille)
    si aucune n'existe. Auto-provisionne bâtiment + obligations + compliance.
    Détecte les doublons par nom + code postal.
    """
    from models import Organisation
    from services.onboarding_service import (
        create_organisation_full,
        create_site_from_data,
        provision_site,
    )

    # ── 1. Résoudre ou créer l'organisation ────────────────────────────
    org_id = None
    auto_created = {}

    # Essayer de résoudre l'org depuis le scope (header X-Org-Id)
    try:
        org_id = resolve_org_id(request, auth, db)
    except Exception:
        pass

    if org_id is None:
        # Aucune org → auto-créer "Mon entreprise"
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

    # ── 2. Trouver le portefeuille ─────────────────────────────────────
    pf = (
        db.query(Portefeuille)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id, not_deleted(Portefeuille))
        .first()
    )
    if not pf:
        # Org existe mais pas de PF → en créer un
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

    # ── 3. Anti-doublons (nom + code_postal) ───────────────────────────
    if body.code_postal:
        existing = (
            db.query(Site)
            .filter(
                Site.nom == body.nom,
                Site.code_postal == body.code_postal,
                not_deleted(Site),
            )
            .first()
        )
        if existing:
            return {
                "status": "duplicate_detected",
                "existing_site": {
                    "id": existing.id,
                    "nom": existing.nom,
                    "ville": existing.ville,
                    "code_postal": existing.code_postal,
                },
                "message": f'Un site "{existing.nom}" existe déjà à {existing.ville or existing.code_postal}',
            }

    # ── 4. Créer le site + auto-provision ──────────────────────────────
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

    # Auto-evaluate compliance
    from services.compliance_rules import evaluate_site as eval_rules

    findings = eval_rules(db, site.id)

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
            "findings": len(findings),
        },
        "auto_created": auto_created,
    }


@router.post("")
def create_site(
    req: SiteCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Cree un site dans le premier portefeuille de l'organisation resolue.
    Auto-provision: batiment + obligations + compliance recompute.
    """
    from models import Portefeuille, EntiteJuridique
    from services.onboarding_service import create_site_from_data, provision_site

    org_id = resolve_org_id(request, auth, db)
    pf = (
        db.query(Portefeuille)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .first()
    )
    if not pf:
        raise HTTPException(status_code=400, detail="Aucun portefeuille pour cette organisation.")

    site = create_site_from_data(
        db=db,
        portefeuille_id=pf.id,
        nom=req.nom,
        type_site=req.type,
        naf_code=req.naf_code,
        adresse=req.adresse,
        code_postal=req.code_postal,
        ville=req.ville,
        surface_m2=req.surface_m2,
    )
    prov = provision_site(db, site)

    # Auto-evaluate compliance rules
    from services.compliance_rules import evaluate_site as eval_rules

    findings = eval_rules(db, site.id)

    db.commit()
    return {
        "id": site.id,
        "nom": site.nom,
        "type": site.type.value,
        "findings_count": len(findings),
        **prov,
    }


@router.get("", response_model=SiteListResponse)
def get_sites(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    org_id: Optional[int] = None,
    ville: Optional[str] = None,
    type: Optional[str] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Liste les sites PROMEOS avec pagination et filtres.
    Scope: org_id query param OR X-Org-Id header (header takes priority when both present).
    """
    query = not_deleted(db.query(Site), Site).options(
        joinedload(Site.portefeuille).joinedload(Portefeuille.entite_juridique).joinedload(EntiteJuridique.organisation)
    )

    # DEMO_MODE-aware scope resolution (auth > org_id param > header > demo fallback > 401)
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)

    query = (
        query.join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == effective_org_id)
    )

    # Site-level scope: restrict to accessible sites when auth has site_ids
    if auth and auth.site_ids is not None:
        query = query.filter(Site.id.in_(auth.site_ids))

    # Additional filters
    if ville:
        query = query.filter(Site.ville.ilike(f"%{ville}%"))
    if type:
        query = query.filter(Site.type == type)

    limit = min(limit, 500)  # cap pagination
    total = query.count()
    sites = query.offset(skip).limit(limit).all()

    return {"total": total, "sites": sites}


@router.get("/{site_id}", response_model=SiteResponse)
def get_site(site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)):
    """
    Récupère les détails d'un site spécifique
    """
    check_site_access(auth, site_id)
    site = (
        not_deleted(db.query(Site), Site)
        .options(
            joinedload(Site.portefeuille)
            .joinedload(Portefeuille.entite_juridique)
            .joinedload(EntiteJuridique.organisation)
        )
        .filter(Site.id == site_id)
        .first()
    )

    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    return site


@router.get("/{site_id}/stats", response_model=SiteStats)
def get_site_stats(
    site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)
):
    """
    Statistiques d'un site
    """
    check_site_access(auth, site_id)
    site = not_deleted(db.query(Site), Site).filter(Site.id == site_id).first()

    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    # Nombre de compteurs
    nb_compteurs = db.query(Compteur).filter(Compteur.site_id == site_id).count()

    # Nombre d'alertes actives
    nb_alertes_actives = db.query(Alerte).filter(Alerte.site_id == site_id, Alerte.resolue == False).count()

    # Consommation du mois dernier
    date_debut = datetime.now() - timedelta(days=30)

    consommations = (
        db.query(
            func.sum(Consommation.valeur).label("total_valeur"), func.sum(Consommation.cout_euro).label("total_cout")
        )
        .join(Compteur)
        .filter(Compteur.site_id == site_id, Consommation.timestamp >= date_debut)
        .first()
    )

    return {
        "nb_compteurs": nb_compteurs,
        "nb_alertes_actives": nb_alertes_actives,
        "consommation_totale_mois": consommations.total_valeur or 0,
        "cout_total_mois": consommations.total_cout or 0,
    }


@router.get("/{site_id}/compliance", response_model=SiteComplianceResponse)
def get_site_compliance(
    site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)
):
    """
    Conformité détaillée d'un site : obligations, evidences, explications et actions.
    """
    check_site_access(auth, site_id)
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    obligations = db.query(Obligation).filter(Obligation.site_id == site_id).all()
    evidences = db.query(Evidence).filter(Evidence.site_id == site_id).all()
    batiments = db.query(Batiment).filter(Batiment.site_id == site_id).all()

    # Build explanations from obligations
    explanations = []
    for ob in obligations:
        if ob.type == TypeObligation.DECRET_TERTIAIRE:
            label = "Décret Tertiaire"
            if ob.statut == StatutConformite.CONFORME:
                why = f"Trajectoire 2030 respectée (avancement {ob.avancement_pct:.0f}%)"
            elif ob.statut == StatutConformite.A_RISQUE:
                why = f"Avancement insuffisant ({ob.avancement_pct:.0f}%) - trajectoire 2030 menacée"
            else:
                why = f"Avancement critique ({ob.avancement_pct:.0f}%) - objectif 2030 compromis"
        elif ob.type == TypeObligation.BACS:
            label = "BACS (GTB/GTC)"
            if ob.statut == StatutConformite.CONFORME:
                why = "Système GTB/GTC installé et conforme"
            elif ob.statut == StatutConformite.A_RISQUE:
                why = f"GTB/GTC partiellement conforme (avancement {ob.avancement_pct:.0f}%)"
            else:
                why = "Site >290 kW sans GTB/GTC conforme - pénalité applicable"
        else:
            label = ob.type.value.upper()
            why = ob.description or f"Statut: {ob.statut.value}"

        explanations.append(
            {
                "label": label,
                "statut": ob.statut,
                "why": why,
            }
        )

    # Add evidence gap explanation
    manquantes = [e for e in evidences if e.statut == StatutEvidence.MANQUANT]
    if manquantes:
        explanations.append(
            {
                "label": "Preuves manquantes",
                "statut": StatutConformite.A_RISQUE,
                "why": f"{len(manquantes)} document(s) manquant(s) : {', '.join(e.note.split(' - ')[0] for e in manquantes)}",
            }
        )

    # Build actions list from engine templates + evidence gaps
    actions = []
    for ob_type, ob_statut, action_text in _ACTION_TEMPLATES:
        if any(o.type == ob_type and o.statut == ob_statut for o in obligations):
            actions.append(action_text)
    if manquantes:
        actions.append(f"Fournir {len(manquantes)} preuve(s) manquante(s)")

    return {
        "site": site,
        "batiments": batiments,
        "obligations": obligations,
        "evidences": evidences,
        "explanations": explanations,
        "actions": actions,
    }


@router.get("/{site_id}/guardrails")
def get_site_guardrails(
    site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)
):
    """
    Regles de validation (guardrails) pour un site.
    """
    check_site_access(auth, site_id)
    from services.guardrails import validate_site

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")
    return validate_site(db, site_id)
