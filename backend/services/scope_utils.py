"""
PROMEOS — Scope utilities : résolution canonique de l'org_id.

Priorité canonique PROMEOS (du plus au moins sûr) :
  1. auth.org_id  — JWT token (si authentifié)
  2. X-Org-Id     — header injecté par l'intercepteur frontend (setApiScope)
  3. None         — pas d'org résolu

Usage :
    from services.scope_utils import get_scope_org_id, resolve_org_id

    org_id = get_scope_org_id(request, auth)
    if org_id is None:
        from services.demo_state import DemoState
        org_id = DemoState.get_demo_org_id()
"""

import logging

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from middleware.auth import AuthContext, DEMO_MODE

_security_logger = logging.getLogger("promeos.security")


def get_scope_org_id(
    request: Request,
    auth: Optional[AuthContext],
    db: Optional[Session] = None,
) -> Optional[int]:
    """
    Résout l'org_id de la requête avec la chaîne de priorité canonique.

    Args:
        request:  FastAPI Request (pour lire les headers)
        auth:     AuthContext injecté par get_optional_auth (None en mode démo)
        db:       Session SQLAlchemy pour validation DB X-Org-Id (Sprint C-7 Phase 7.2 ADR-017
                  Option B). Si None (callers legacy), validation DB skippée — backward-compat
                  transitoire (à migrer Sprint C-8+).

    Returns:
        int org_id si résolu, None sinon.

    Security : si auth présent, le header X-Org-Id DOIT correspondre à `auth.org_id` sinon
    il est ignoré (cross-tenant guard JWT). En DEMO_MODE sans auth, **X-Org-Id est validé
    contre la DB** (Organisation existante + actif + non soft-deleted) pour empêcher IDOR
    cross-tenant énumération via header forgé (Sprint C-7 Phase 7.2 fix SEC-2026-012).

    Pattern Sprint C-5 Phase 5.5 audit + 5.7 audit transversal AXE 4 → Phase 7.2 fix runtime.
    """
    # 1. JWT token (le plus sûr)
    if auth is not None:
        # Cross-check optionnel : si X-Org-Id présent ET ≠ auth.org_id → ignorer le header
        raw = request.headers.get("X-Org-Id")
        if raw:
            try:
                if int(raw) != auth.org_id:
                    _security_logger.warning(
                        "x_org_id_mismatch_jwt_wins",
                        extra={
                            "header_org_id": int(raw),
                            "jwt_org_id": auth.org_id,
                            "user_id": auth.user.id if auth.user else None,
                        },
                    )
            except ValueError:
                pass
        return auth.org_id

    # 2. X-Org-Id header (injecté par le scope interceptor frontend en démo)
    raw = request.headers.get("X-Org-Id")
    if raw:
        try:
            org_id = int(raw)
        except ValueError:
            _security_logger.warning("x_org_id_invalid_format", extra={"raw": raw[:50]})
            return None

        # Sprint C-7 Phase 7.2 fix ADR-017 Option B (SEC-2026-012) : validation DB stricte.
        # Sans ce check, X-Org-Id forgé permettait IDOR cross-tenant énumération (~25 endpoints).
        if db is not None:
            from models import Organisation, not_deleted

            org_exists = (
                db.query(Organisation.id)
                .filter(
                    Organisation.id == org_id,
                    Organisation.actif.is_(True),
                    not_deleted(Organisation),
                )
                .first()
            )
            if org_exists is None:
                _security_logger.warning(
                    "x_org_id_rejected_db_check",
                    extra={"requested_org_id": org_id, "reason": "not_found_or_inactive"},
                )
                return None  # Fail securely — pas 403, laisse fallback DEMO_MODE/DemoState
            return org_id

        # Backward-compat transitoire : db=None → callers legacy. Validation skippée
        # pour ne pas casser les callsites Sprint C-1 → C-6. À migrer Sprint C-8+ pour
        # généralisation enforcement (cf. dette Sprint C-8 si applicable).
        return org_id

    return None


def get_scope_site_id(request: Request, auth: Optional[AuthContext]) -> Optional[int]:
    """
    Résout le site_id optionnel depuis X-Site-Id header.
    (auth.site_ids contient une liste — pas utilisé ici pour la sélection unique)

    Returns:
        int site_id si présent dans X-Site-Id, None sinon.
    """
    raw = request.headers.get("X-Site-Id")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return None


def resolve_org_id_from_site(db: Session, site_id: int) -> int | None:
    """Resolve organisation_id from a site_id via Site->Portefeuille->EntiteJuridique chain."""
    from models import Site, Portefeuille, EntiteJuridique

    row = (
        db.query(EntiteJuridique.organisation_id)
        .join(Portefeuille, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .join(Site, Site.portefeuille_id == Portefeuille.id)
        .filter(Site.id == site_id)
        .first()
    )
    return row[0] if row else None


def resolve_org_id(
    request: Request,
    auth: Optional[AuthContext],
    db: Session,
    *,
    org_id_override: Optional[int] = None,
) -> int:
    """
    Résout l'org_id avec la chaîne canonique, puis applique le guard DEMO_MODE.

    Priorité :
      1. auth.org_id   — JWT token
      2. org_id_override — explicit param (query param / request body)
      3. X-Org-Id header — frontend scope interceptor
      4. DEMO_MODE=true  → fallback DemoState puis première org active en DB.
      5. DEMO_MODE=false → 401 Unauthorized (pas de données sensibles sans auth).

    Raises:
        HTTPException 401 si non résolu et DEMO_MODE=false.
        HTTPException 403 si résolu mais org introuvable.
    """
    from models import Organisation

    # Sprint C-7 Phase 7.2 fix ADR-017 Option B : passer `db` pour validation X-Org-Id stricte.
    org_id = get_scope_org_id(request, auth, db=db)
    if org_id is not None:
        return org_id

    if org_id_override is not None:
        # Sprint C-7 Phase 7.8 — Fix IDOR critique D-Audit-Phase7-IDOR-Org-Id-Override-Bypass-003 :
        # avant ce fix, `org_id_override` était retourné brut sans validation DB. Bypass DEMO_MODE
        # via query param possible (attaquant en DEMO_MODE sans JWT/X-Org-Id pouvait fournir
        # org_id_override=<id_tierce> via params billing.py). Maintenant : validation DB stricte
        # (Organisation existe + actif + not_deleted) cohérente avec X-Org-Id Phase 7.2 Option B.
        from models import not_deleted

        org = (
            db.query(Organisation)
            .filter(
                Organisation.id == org_id_override,
                Organisation.actif.is_(True),
                not_deleted(Organisation),
            )
            .first()
        )
        if org is None:
            _security_logger.warning("org_id_override_rejected_db_check override=%s", org_id_override)
            raise HTTPException(
                status_code=403,
                detail="Forbidden — org_id_override invalid (org not found / inactive / deleted)",
            )
        return org_id_override

    # No org resolved — check DEMO_MODE
    if not DEMO_MODE:
        raise HTTPException(
            status_code=401,
            detail="Authentication required — org could not be resolved (DEMO_MODE is off)",
        )

    # DEMO_MODE=true: fallback chain
    from services.demo_state import DemoState
    from models import not_deleted

    demo_org_id = DemoState.get_demo_org_id()
    if demo_org_id:
        return demo_org_id

    org = db.query(Organisation).filter(Organisation.actif.is_(True), not_deleted(Organisation)).first()
    if org:
        return org.id

    raise HTTPException(status_code=403, detail="Organisation non résolue")


# ── Scope resolver multi-niveaux ─────────────────────────────────────────


def sites_for_org_query(db: Session, org_id: int | None):
    """Canonical query for non-deleted sites filtered by org_id + is_demo coherence.

    Phase 3.4-bis Correctif #3 — factorisation des 4 clones `_sites_for_org`
    historiques (cockpit.py, cockpit_v2.py, services/cockpit_facts_service.py,
    services/narrative/typology_resolver.py) et `_sites_for_org_query`
    (dashboard_2min.py) en un seul helper canonique partagé.

    Applique le filtre `Site.is_demo == Organisation.is_demo` introduit en
    F.4 (commit ff2b3a4d) qui ferme la fuite cosmétique cross-tenant
    identifiée audit Phase D P0.1. Règle de sécurité symétrique :
      - org demo (is_demo=True)  → voit uniquement les sites demo
      - org prod (is_demo=False) → voit uniquement les sites prod

    Retourne une query SQLAlchemy (pas une liste) pour permettre le chaînage
    `.filter()` / `.count()` / `.with_entities()` / `.all()` selon le besoin
    du caller.

    Params :
      db      : session SQLAlchemy
      org_id  : organization_id (int) ou None (pas de filtre org)

    Cf :
      - Audit Sprint F (synthèse CS 20/24 + dette `P2-debt-BE-sites-isdemo-
        filter-other-endpoints`).
      - F.4 commit ff2b3a4d (introduction du filtre is_demo).
    """
    from models.site import Site
    from models.portefeuille import Portefeuille
    from models.entite_juridique import EntiteJuridique
    from models.organisation import Organisation
    from models import not_deleted

    q = (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .join(Organisation, Organisation.id == EntiteJuridique.organisation_id)
        .filter(Site.is_demo == Organisation.is_demo)
    )
    if org_id is not None:
        q = q.filter(EntiteJuridique.organisation_id == org_id)
    return q


def resolve_site_ids(
    db: Session,
    org_id: int,
    entity_id: int = None,
    portefeuille_id: int = None,
    site_id: int = None,
    archetype_code: str = None,
) -> List[int]:
    """
    Résout les site_ids depuis n'importe quel niveau de la hiérarchie patrimoine.

    Priorité : site_id > portefeuille_id > entity_id > org_id
    Filtre optionnel par archetype_code (TypeSite value).
    """
    from models.site import Site
    from models.portefeuille import Portefeuille
    from models.entite_juridique import EntiteJuridique
    from models import not_deleted

    # All branches verify org_id ownership + soft-delete filtering
    q = (
        db.query(Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id, not_deleted(Site))
    )
    if site_id:
        q = q.filter(Site.id == site_id)
    elif portefeuille_id:
        q = q.filter(Site.portefeuille_id == portefeuille_id)
    elif entity_id:
        q = q.filter(Portefeuille.entite_juridique_id == entity_id)
    if archetype_code:
        q = q.filter(Site.type == archetype_code)
    return [row[0] for row in q.all()]
