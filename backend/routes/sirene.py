"""
PROMEOS - Routes Referentiel Sirene
Recherche, admin import, onboarding from-sirene.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    not_deleted,
)
from models.sirene import (
    SireneUniteLegale,
    SireneEtablissement,
    SireneDoublon,
    SireneSyncRun,
    CustomerCreationTrace,
)
from schemas.sirene import (
    SireneUniteLegaleOut,
    SireneEtablissementOut,
    SireneSearchResult,
    SireneEtablissementListResult,
    SireneImportRequest,
    SireneSyncRunOut,
    OnboardingFromSireneRequest,
    OnboardingFromSireneResponse,
    OnboardingFromSireneWarning,
    SiteCreatedOut,
    LeadScoreOut,
)
from services.naf_classifier import classify_naf
from models.enums import TypeSite

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Sirene"])

# NAF 2025 entre en vigueur le 01/01/2027 (transition officielle INSEE).
# Avant : on garde NAF Rev2. Apres : on bascule sur NAF25.
_NAF25_EFFECTIVE = datetime(2027, 1, 1, tzinfo=timezone.utc)


# ======================================================================
# Recherche Sirene (referentiel local)
# ======================================================================


@router.get("/api/reference/sirene/search", response_model=SireneSearchResult)
def search_sirene(
    q: str = Query(..., min_length=2, max_length=200, description="Nom, SIREN, SIRET, CP ou commune"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    etat: Optional[str] = Query(None, description="A=actif, C=cesse"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Recherche d'unites legales dans le referentiel Sirene local."""
    q_clean = q.strip()
    query = db.query(SireneUniteLegale)

    if etat:
        query = query.filter(SireneUniteLegale.etat_administratif == etat.upper())

    query = query.filter(SireneUniteLegale.statut_diffusion == "O")

    if q_clean.isdigit():
        if len(q_clean) == 9:
            query = query.filter(SireneUniteLegale.siren == q_clean)
        elif len(q_clean) == 14:
            query = query.filter(SireneUniteLegale.siren == q_clean[:9])
        else:
            # CP partiel ou autre numerique
            query = query.filter(SireneUniteLegale.siren.like(f"{q_clean}%"))
    else:
        q_escaped = q_clean.replace("%", r"\%").replace("_", r"\_")
        pattern = f"%{q_escaped}%"
        query = query.filter(
            or_(
                SireneUniteLegale.denomination.ilike(pattern, escape="\\"),
                SireneUniteLegale.sigle.ilike(pattern, escape="\\"),
                SireneUniteLegale.nom_unite_legale.ilike(pattern, escape="\\"),
            )
        )

    total = query.count()
    offset = (page - 1) * per_page
    results = query.order_by(SireneUniteLegale.denomination).offset(offset).limit(per_page).all()

    return SireneSearchResult(
        query=q_clean,
        total=total,
        results=[SireneUniteLegaleOut.model_validate(ul) for ul in results],
    )


@router.get("/api/reference/sirene/unites-legales/{siren}", response_model=SireneUniteLegaleOut)
def get_unite_legale(
    siren: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Detail d'une unite legale par SIREN."""
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(
            400,
            detail={"code": "INVALID_SIREN", "message": "SIREN invalide (9 chiffres)", "hint": "Verifiez le format"},
        )

    ul = db.query(SireneUniteLegale).filter(SireneUniteLegale.siren == siren).first()
    if not ul:
        raise HTTPException(
            404,
            detail={
                "code": "NOT_FOUND",
                "message": f"Unite legale {siren} non trouvee",
                "hint": "Verifiez le SIREN ou lancez un import Sirene",
            },
        )

    return SireneUniteLegaleOut.model_validate(ul)


@router.get(
    "/api/reference/sirene/unites-legales/{siren}/etablissements",
    response_model=SireneEtablissementListResult,
)
def get_etablissements_by_siren(
    siren: str,
    etat: Optional[str] = Query(None, description="A=actif, F=ferme"),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste des etablissements d'une unite legale (max 500 par defaut)."""
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(400, detail={"code": "INVALID_SIREN", "message": "SIREN invalide"})

    query = db.query(SireneEtablissement).filter(
        SireneEtablissement.siren == siren,
        SireneEtablissement.statut_diffusion == "O",
    )
    if etat:
        query = query.filter(SireneEtablissement.etat_administratif == etat.upper())

    total = query.count()
    etabs = (
        query.order_by(
            SireneEtablissement.etablissement_siege.desc(),
            SireneEtablissement.etat_administratif,
            SireneEtablissement.libelle_commune,
        )
        .limit(limit)
        .all()
    )

    return SireneEtablissementListResult(
        siren=siren,
        total=total,
        etablissements=[SireneEtablissementOut.model_validate(e) for e in etabs],
    )


@router.get("/api/reference/sirene/etablissements/{siret}", response_model=SireneEtablissementOut)
def get_etablissement(
    siret: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Detail d'un etablissement par SIRET."""
    if not siret.isdigit() or len(siret) != 14:
        raise HTTPException(400, detail={"code": "INVALID_SIRET", "message": "SIRET invalide (14 chiffres)"})

    e = db.query(SireneEtablissement).filter(SireneEtablissement.siret == siret).first()
    if not e:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": f"Etablissement {siret} non trouve"})

    return SireneEtablissementOut.model_validate(e)


# ======================================================================
# Lead Score (V116 — wedge monetisation)
# ======================================================================


@router.get("/api/reference/sirene/lead-score/{siren}", response_model=LeadScoreOut)
def get_lead_score(
    siren: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Calcule un score de lead depuis les donnees Sirene locales.

    Pre-qualifie commercialement un SIREN avant meme l'inscription :
    segment, MRR estime, priorite A/B/C.
    """
    from services.lead_score import compute_lead_score

    try:
        return LeadScoreOut(**compute_lead_score(db, siren))
    except ValueError as e:
        raise HTTPException(400, detail={"code": "INVALID_SIREN", "message": str(e)})
    except LookupError as e:
        raise HTTPException(
            404,
            detail={
                "code": "SIREN_NOT_HYDRATED",
                "message": str(e),
                "hint": "Lancez un import Sirene ou appelez /hydrate/{siren}",
            },
        )


# ======================================================================
# Admin — Hydratation per-SIREN (F1 V117)
# ======================================================================


@router.post("/api/admin/sirene/hydrate/{siren}")
def admin_hydrate_siren(
    siren: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Hydrate un SIREN depuis l'API recherche-entreprises.api.gouv.fr.

    Bypass l'import CSV complet (2.6 GB) pour les cas demo/pilote/test.
    Insere UL + tous les etablissements retournes par l'API.
    """
    _require_admin(auth, allow_demo=True)
    from services.sirene_hydrate import hydrate_siren_from_api

    try:
        return hydrate_siren_from_api(db, siren)
    except ValueError as e:
        raise HTTPException(400, detail={"code": "INVALID_SIREN", "message": str(e)})
    except LookupError as e:
        raise HTTPException(
            404,
            detail={
                "code": "SIREN_NOT_FOUND_API",
                "message": str(e),
                "hint": "Verifiez le numero SIREN sur annuaire-entreprises.data.gouv.fr",
            },
        )
    except RuntimeError as e:
        raise HTTPException(
            503,
            detail={
                "code": "API_GOUV_UNAVAILABLE",
                "message": str(e),
                "hint": "L'API publique est indisponible. Reessayez ou utilisez l'import CSV.",
            },
        )


# ======================================================================
# Admin — Import Sirene
# ======================================================================


def _run_admin_import(req: SireneImportRequest, db: Session, auth, sync_type: str):
    _require_admin(auth)
    from services.sirene_import import run_sirene_import

    snapshot = None
    if req.snapshot_date:
        try:
            snapshot = datetime.strptime(req.snapshot_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(400, detail={"code": "INVALID_DATE", "message": "Format attendu: YYYY-MM-DD"})

    run = run_sirene_import(
        db=db,
        sync_type=sync_type,
        ul_path=_resolve_safe_path(req.ul_path),
        etab_path=_resolve_safe_path(req.etab_path),
        snapshot_date=snapshot,
    )
    return _sync_run_to_out(run)


@router.post("/api/admin/sirene/import-full", response_model=SireneSyncRunOut)
def admin_import_full(
    req: SireneImportRequest, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)
):
    """Lance un import full Sirene (admin uniquement)."""
    return _run_admin_import(req, db, auth, "full")


@router.post("/api/admin/sirene/import-delta", response_model=SireneSyncRunOut)
def admin_import_delta(
    req: SireneImportRequest, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)
):
    """Lance un import delta Sirene (admin uniquement)."""
    return _run_admin_import(req, db, auth, "delta")


@router.get("/api/admin/sirene/sync-runs")
def admin_list_sync_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste l'historique des imports Sirene (lecture seule)."""
    _require_admin(auth, allow_demo=True)
    runs = db.query(SireneSyncRun).order_by(SireneSyncRun.started_at.desc()).limit(limit).all()
    return [_sync_run_to_out(r) for r in runs]


# ======================================================================
# Onboarding from-sirene
# ======================================================================


@router.post("/api/onboarding/from-sirene", response_model=OnboardingFromSireneResponse)
def onboarding_from_sirene(
    req: OnboardingFromSireneRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Cree un client PROMEOS (Organisation + EntiteJuridique + Sites) depuis le referentiel Sirene.

    NE CREE PAS : batiment, compteur, contrat, obligation.
    """
    correlation_id = uuid.uuid4().hex[:12]
    warnings: list[OnboardingFromSireneWarning] = []

    # ── 1. Lire l'unite legale Sirene ──
    ul = db.query(SireneUniteLegale).filter(SireneUniteLegale.siren == req.siren).first()
    if not ul:
        raise HTTPException(
            404,
            detail={
                "code": "SIREN_NOT_FOUND",
                "message": f"SIREN {req.siren} introuvable dans le referentiel Sirene local",
                "hint": "Lancez d'abord un import Sirene ou verifiez le numero",
                "correlation_id": correlation_id,
            },
        )

    # ── 2. Anti-doublons SIREN ──
    existing_ej = (
        db.query(EntiteJuridique).filter(EntiteJuridique.siren == req.siren, not_deleted(EntiteJuridique)).first()
    )
    if existing_ej:
        raise HTTPException(
            409,
            detail={
                "code": "SIREN_ALREADY_EXISTS",
                "message": f"Le SIREN {req.siren} existe deja (Entite juridique #{existing_ej.id}: {existing_ej.nom})",
                "hint": "Rattachez les sites a cette entite juridique existante plutot que de creer un doublon",
                "correlation_id": correlation_id,
            },
        )

    # ── 3. Verifier doublons Sirene (batch query) ──
    doublons = db.query(SireneDoublon).filter(SireneDoublon.siren == req.siren).all()
    if doublons:
        doublon_sirens = [d.siren_doublon for d in doublons]
        ej_doublons = {
            ej.siren: ej
            for ej in db.query(EntiteJuridique)
            .filter(EntiteJuridique.siren.in_(doublon_sirens), not_deleted(EntiteJuridique))
            .all()
        }
        for d in doublons:
            ej_doublon = ej_doublons.get(d.siren_doublon)
            if ej_doublon:
                warnings.append(
                    OnboardingFromSireneWarning(
                        type="doublon_sirene",
                        message=f"Le SIREN {d.siren_doublon} (doublon INSEE de {req.siren}) existe deja comme Entite juridique #{ej_doublon.id}",
                        existing_id=ej_doublon.id,
                    )
                )

    # ── 4. Lire les etablissements selectionnes ──
    etabs = db.query(SireneEtablissement).filter(SireneEtablissement.siret.in_(req.etablissement_sirets)).all()
    etabs_by_siret = {e.siret: e for e in etabs}
    missing_sirets = set(req.etablissement_sirets) - set(etabs_by_siret.keys())
    if missing_sirets:
        raise HTTPException(
            404,
            detail={
                "code": "SIRET_NOT_FOUND",
                "message": f"SIRET(s) introuvable(s) dans le referentiel: {', '.join(missing_sirets)}",
                "hint": "Verifiez les SIRET ou lancez un import Sirene",
                "correlation_id": correlation_id,
            },
        )

    # ── 4b. Verifier coherence SIREN/SIRET ──
    for siret, etab in etabs_by_siret.items():
        if etab.siren != req.siren:
            raise HTTPException(
                400,
                detail={
                    "code": "SIRET_SIREN_MISMATCH",
                    "message": f"Le SIRET {siret} appartient au SIREN {etab.siren}, pas a {req.siren}",
                    "hint": "Tous les SIRET doivent appartenir au meme SIREN",
                    "correlation_id": correlation_id,
                },
            )

    # ── 5. Anti-doublons SIRET (batch query, warning pas bloquant) ──
    existing_sites_by_siret = {
        s.siret: s for s in db.query(Site).filter(Site.siret.in_(req.etablissement_sirets), not_deleted(Site)).all()
    }
    for siret, existing_site in existing_sites_by_siret.items():
        warnings.append(
            OnboardingFromSireneWarning(
                type="siret_exists",
                message=f"Le SIRET {siret} existe deja sur le site #{existing_site.id} ({existing_site.nom})",
                existing_id=existing_site.id,
            )
        )

    # ── 6. Anti-doublons nom + CP (warning) ──
    org_nom = req.org_nom_override or ul.denomination or ul.nom_unite_legale or f"Organisation {req.siren}"
    nom_escaped = org_nom[:30].replace("%", r"\%").replace("_", r"\_")
    similar_org = (
        db.query(Organisation)
        .filter(Organisation.nom.ilike(f"%{nom_escaped}%", escape="\\"), not_deleted(Organisation))
        .first()
    )
    if similar_org:
        warnings.append(
            OnboardingFromSireneWarning(
                type="nom_similaire",
                message=f"Une organisation au nom similaire existe deja: #{similar_org.id} ({similar_org.nom})",
                existing_id=similar_org.id,
            )
        )

    # ── 7. Creation Organisation ──
    org = Organisation(
        nom=org_nom,
        siren=req.siren,
        type_client=req.type_client,
        actif=True,
    )
    db.add(org)
    db.flush()

    # ── 8. Creation Entite Juridique ──
    siege = etabs_by_siret.get(req.siren + (ul.nic_siege or ""))
    ej = EntiteJuridique(
        organisation_id=org.id,
        nom=ul.denomination or ul.nom_unite_legale or org_nom,
        siren=req.siren,
        siret=(req.siren + ul.nic_siege) if ul.nic_siege else None,
        naf_code=_resolve_naf(None, ul),
        insee_code=siege.code_commune if siege else None,
    )
    db.add(ej)
    db.flush()

    # ── 9. Creation Portefeuille par defaut ──
    pf = Portefeuille(
        entite_juridique_id=ej.id,
        nom="Principal",
        description="Portefeuille par defaut (creation Sirene)",
    )
    db.add(pf)
    db.flush()

    # ── 10. Creation Sites (1 etablissement = 1 site, pas de batiment/compteur) ──
    site_objects = []
    for siret in req.etablissement_sirets:
        etab = etabs_by_siret[siret]
        site_obj, site_nom = _create_site_from_etab(db, pf.id, etab, ul, org_nom)
        site_objects.append((site_obj, site_nom, etab))

    db.flush()  # single flush → all site IDs available

    sites_created = [
        SiteCreatedOut(id=s.id, siret=s.siret, nom=nom, code_postal=e.code_postal, ville=e.libelle_commune)
        for s, nom, e in site_objects
    ]

    # ── 11. Trace de creation ──
    trace = CustomerCreationTrace(
        source_type="sirene",
        source_siren=req.siren,
        source_sirets=json.dumps(req.etablissement_sirets),
        organisation_id=org.id,
        entite_juridique_id=ej.id,
        portefeuille_id=pf.id,
        site_ids=json.dumps([s.id for s in sites_created]),
        user_id=auth.user.id if auth else None,
        user_email=auth.user.email if auth and hasattr(auth.user, "email") else None,
        status="success",
        warnings=json.dumps([w.model_dump() for w in warnings]) if warnings else None,
        correlation_id=correlation_id,
    )
    db.add(trace)

    # Funnel onboarding — best-effort, ne doit pas bloquer la creation.
    # TODO(V116): extraire _get_or_create/_auto_detect vers services/onboarding_stepper
    # pour eviter le route-to-route import (leaky abstraction).
    try:
        from routes.onboarding_stepper import _get_or_create, _auto_detect

        progress = _get_or_create(db, org.id)
        _auto_detect(db, org.id, progress)
    except Exception as e:
        logger.warning("onboarding_progress wiring failed [%s]: %s", correlation_id, e)

    # Lead score — best-effort, enrichit la reponse pour CRM/commercial.
    # Utilise les donnees deja en scope (ul, etabs_by_siret) : zero query supplementaire.
    lead_score_payload = None
    try:
        from services.lead_score import compute_lead_score_from_loaded

        n_etabs_actifs = sum(1 for e in etabs_by_siret.values() if e.etat_administratif == "A")
        lead_score_payload = LeadScoreOut(**compute_lead_score_from_loaded(ul, n_etabs_actifs))
    except Exception as e:
        logger.warning("lead_score computation failed [%s]: %s", correlation_id, e)

    db.commit()

    logger.info(
        "onboarding_from_sirene: org=%d, ej=%d, pf=%d, sites=%d, warnings=%d [%s]",
        org.id,
        ej.id,
        pf.id,
        len(sites_created),
        len(warnings),
        correlation_id,
    )

    return OnboardingFromSireneResponse(
        organisation_id=org.id,
        entite_juridique_id=ej.id,
        portefeuille_id=pf.id,
        sites=sites_created,
        warnings=warnings,
        trace_id=correlation_id,
        lead_score=lead_score_payload,
    )


# ======================================================================
# Helpers
# ======================================================================


def _resolve_naf(etab, ul) -> Optional[str]:
    """Resout le code NAF en priorisant NAF25 apres 2027-01-01 (transition INSEE).

    Fallback chain : NAF25 etab -> NAF25 ul -> NAF Rev2 etab -> NAF Rev2 ul.
    Avant 2027, NAF Rev2 reste la reference officielle.
    """
    rev2 = (etab.activite_principale if etab else None) or ul.activite_principale
    if datetime.now(timezone.utc) < _NAF25_EFFECTIVE:
        return rev2
    naf25 = (etab.activite_principale_naf25 if etab else None) or ul.activite_principale_naf25
    return naf25 or rev2


def _create_site_from_etab(db: Session, portefeuille_id: int, etab, ul, org_nom: str) -> tuple:
    """Cree un Site PROMEOS depuis un etablissement Sirene. Ne cree PAS de batiment/compteur."""
    site_nom = (
        etab.enseigne
        or etab.denomination_usuelle
        or f"{org_nom} — {etab.libelle_commune or etab.code_postal or etab.siret}"
    )
    naf = _resolve_naf(etab, ul)
    try:
        type_site = classify_naf(naf) if naf else TypeSite.BUREAU
    except Exception:
        type_site = TypeSite.BUREAU

    adresse_parts = [etab.numero_voie, etab.type_voie, etab.libelle_voie]
    adresse = " ".join(p for p in adresse_parts if p) or None

    site = Site(
        portefeuille_id=portefeuille_id,
        nom=site_nom,
        type=type_site,
        siret=etab.siret,
        naf_code=naf,
        adresse=adresse,
        code_postal=etab.code_postal,
        ville=etab.libelle_commune,
        insee_code=etab.code_commune,
        actif=True,
        data_source="sirene",
        data_source_ref=f"sirene:{etab.siret}",
    )
    db.add(site)
    return site, site_nom


def _require_admin(auth: Optional[AuthContext], allow_demo: bool = False):
    """Verifie que l'utilisateur est admin.

    allow_demo=True : autorise les endpoints de lecture en demo mode.
    allow_demo=False (defaut) : bloque les operations destructives meme en demo.
    """
    if auth is None:
        if allow_demo:
            return  # Lecture OK en demo
        raise HTTPException(
            403,
            detail={
                "code": "AUTH_REQUIRED",
                "message": "Authentification requise pour les operations admin Sirene",
                "hint": "Connectez-vous avec un compte DG_OWNER ou DSI_ADMIN",
            },
        )
    if auth.role and auth.role.value not in ("DG_OWNER", "DSI_ADMIN"):
        raise HTTPException(
            403,
            detail={
                "code": "FORBIDDEN",
                "message": "Acces reserve aux administrateurs",
                "hint": "Connectez-vous avec un compte DG_OWNER ou DSI_ADMIN",
            },
        )


SIRENE_DATA_DIR = os.environ.get(
    "SIRENE_DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sirene")
)


def _resolve_safe_path(relative_path: Optional[str]) -> Optional[str]:
    """Resout un chemin relatif dans SIRENE_DATA_DIR. Empeche la traversee de repertoire."""
    if not relative_path:
        return None
    base = os.path.realpath(SIRENE_DATA_DIR)
    full = os.path.realpath(os.path.join(base, relative_path))
    if not full.startswith(base):
        raise HTTPException(
            400,
            detail={
                "code": "PATH_TRAVERSAL",
                "message": "Chemin invalide",
                "hint": f"Le fichier doit etre dans {SIRENE_DATA_DIR}",
            },
        )
    return full


def _sync_run_to_out(run: SireneSyncRun) -> SireneSyncRunOut:
    return SireneSyncRunOut(
        id=run.id,
        sync_type=run.sync_type,
        source_file=os.path.basename(run.source_file) if run.source_file else None,
        started_at=run.started_at.isoformat() if run.started_at else "",
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        lines_read=run.lines_read or 0,
        lines_inserted=run.lines_inserted or 0,
        lines_updated=run.lines_updated or 0,
        lines_rejected=run.lines_rejected or 0,
        status=run.status,
        error_message=run.error_message,
        correlation_id=run.correlation_id,
    )
