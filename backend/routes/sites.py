"""
PROMEOS - Routes API pour les Sites (LEGACY — en sunset).

P0-A 2026-05-23 (`claude/patrimoine-p0a-clean-routes-audit-cascade`) :
3 endpoints retournent désormais HTTP 410 Gone — frontend canonisé sur
`/api/patrimoine/sites` (GET premium) et `/api/patrimoine/crud/sites/*`
(POST/PATCH/DELETE + quick-create).

Référence canonique : `docs/dev/patrimoine_routes_canonical.md`.

Les endpoints `GET /api/sites/{site_id}/stats|guardrails|compliance` restent
encore opérationnels (replacements non encore livrés côté `/api/patrimoine/`)
mais sont marqués deprecated. Ils basculeront en 410 dans un futur sprint
quand les équivalents premium seront en place.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import (
    Site,
    Portefeuille,
    EntiteJuridique,
    Organisation,
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
from routes.schemas import SiteResponse, SiteStats, SiteComplianceResponse
from services.compliance_utils import _ACTION_TEMPLATES
from services.error_catalog import business_error
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import check_site_access
from typing import Optional
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/sites", tags=["Sites"])


# ─────────────────────────────────────────────────────────────────────────────
# HTTP 410 GONE — routes canonisées dans /api/patrimoine/*
# ─────────────────────────────────────────────────────────────────────────────


_GONE_MESSAGE = "Cette route est dépréciée. Utilisez le parcours Patrimoine."

_GONE_REPLACEMENTS = {
    "post_quick_create": "POST /api/patrimoine/crud/sites/quick-create",
    "post_create": "POST /api/patrimoine/crud/sites",
    "get_list": "GET /api/patrimoine/sites",
}


def _raise_gone(replacement_key: str) -> None:
    """Retourne HTTP 410 Gone avec un message standardisé FR + pointeur canonique."""
    raise HTTPException(
        status_code=410,
        detail={
            "code": "PATRIMOINE_ROUTE_GONE",
            "message": _GONE_MESSAGE,
            "replacement": _GONE_REPLACEMENTS[replacement_key],
            "doc": "docs/dev/patrimoine_routes_canonical.md",
        },
    )


@router.post(
    "/quick-create",
    status_code=410,
    deprecated=True,
    summary="[GONE] Use /api/patrimoine/crud/sites/quick-create",
)
def quick_create_site_gone():
    """HTTP 410 — endpoint relocalisé dans le namespace patrimoine canonique."""
    _raise_gone("post_quick_create")


@router.post(
    "",
    status_code=410,
    deprecated=True,
    summary="[GONE] Use /api/patrimoine/crud/sites",
)
def create_site_gone():
    """HTTP 410 — création canonisée sous /api/patrimoine/crud/sites."""
    _raise_gone("post_create")


@router.get(
    "",
    status_code=410,
    deprecated=True,
    summary="[GONE] Use /api/patrimoine/sites",
)
def get_sites_gone():
    """HTTP 410 — listing canonisé sous /api/patrimoine/sites (premium)."""
    _raise_gone("get_list")


@router.get(
    "/{site_id}",
    response_model=SiteResponse,
    deprecated=True,
    summary="[DEPRECATED] Use /api/patrimoine/sites/{site_id}",
)
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
        raise HTTPException(**business_error("SITE_NOT_FOUND"))

    return site


@router.get("/{site_id}/stats", response_model=SiteStats, deprecated=True)
def get_site_stats(
    site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)
):
    """
    Statistiques d'un site
    """
    check_site_access(auth, site_id)
    site = not_deleted(db.query(Site), Site).filter(Site.id == site_id).first()

    if not site:
        raise HTTPException(**business_error("SITE_NOT_FOUND"))

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


@router.get("/{site_id}/compliance", response_model=SiteComplianceResponse, deprecated=True)
def get_site_compliance(
    site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)
):
    """
    Conformité détaillée d'un site : obligations, evidences, explications et actions.
    """
    check_site_access(auth, site_id)
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(**business_error("SITE_NOT_FOUND"))

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


@router.get("/{site_id}/guardrails", deprecated=True)
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
        raise HTTPException(**business_error("SITE_NOT_FOUND"))
    return validate_site(db, site_id)
