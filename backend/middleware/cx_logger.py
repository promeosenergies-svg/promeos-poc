"""
PROMEOS — CX Event Logger
Réutilise AuditLog model (V117) avec event_type préfixé CX_*
Fire-and-forget : les erreurs sont loggées mais ne bloquent pas la requête.
"""

import json
import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from models.iam import AuditLog, UserOrgRole

logger = logging.getLogger(__name__)

# Sprint CX 2.5-bis (P2) : cache membership (user_id, org_id) → bool avec TTL.
# Motivation : log_cx_event est sur le hot path (polling /api/cockpit toutes les 30s).
# Le check UserOrgRole ajoute +1 query SQL par event. Avec un cache TTL 5 min, on
# absorbe la majorité des appels répétés (même utilisateur sur la même org).
#
# Format entrée : _MEMBERSHIP_CACHE[(user_id, org_id)] = (is_member: bool, expires_at: float)
# Simple dict module-level ; pas de lock car GIL + écritures idempotentes
# (collision de race = re-query une fois, pas un problème de correctness).
#
# NOTE : l'invalidation explicite via invalidate_membership_cache() doit être appelée
# quand une UserOrgRole est créée/supprimée/modifiée. HORS SCOPE de ce commit :
# les endpoints admin mutant UserOrgRole devront invoquer cette helper dans un
# sprint ultérieur (sans quoi le cache peut rester chaud jusqu'à 5 min après un
# changement de rôle). Impact acceptable : un user qui perd accès à une org peut
# voir ses events loggés pendant ≤ 5 min, mais la transaction est déjà isolée
# côté route via require_platform_admin / get_current_user.
_MEMBERSHIP_CACHE: dict[tuple[int, int], tuple[bool, float]] = {}
_MEMBERSHIP_TTL_SEC = 300  # 5 minutes


def _is_member_cached(db: Session, user_id: int, org_id: int, ttl_sec: int = _MEMBERSHIP_TTL_SEC) -> bool:
    """Retourne True si user_id est membre de org_id (via UserOrgRole), avec cache TTL.

    Cache miss → 1 query SELECT UserOrgRole.id. Cache hit → 0 query.
    """
    key = (user_id, org_id)
    now = time.monotonic()
    cached = _MEMBERSHIP_CACHE.get(key)
    if cached is not None and cached[1] > now:
        return cached[0]

    is_member = (
        db.query(UserOrgRole.id).filter(UserOrgRole.user_id == user_id, UserOrgRole.org_id == org_id).first()
    ) is not None
    _MEMBERSHIP_CACHE[key] = (is_member, now + ttl_sec)
    return is_member


def invalidate_membership_cache(user_id: Optional[int] = None, org_id: Optional[int] = None) -> None:
    """Invalide le cache membership.

    - Sans argument : vide tout le cache (utile en tests).
    - Avec (user_id, org_id) : invalide cette paire.
    - Avec user_id seul : invalide toutes les paires pour cet utilisateur.
    - Avec org_id seul : invalide toutes les paires pour cette org.
    """
    if user_id is None and org_id is None:
        _MEMBERSHIP_CACHE.clear()
        return
    to_delete = [
        key
        for key in _MEMBERSHIP_CACHE
        if (user_id is None or key[0] == user_id) and (org_id is None or key[1] == org_id)
    ]
    for key in to_delete:
        _MEMBERSHIP_CACHE.pop(key, None)


def safe_invalidate_membership_cache(user_id: Optional[int] = None, org_id: Optional[int] = None) -> None:
    """Wrapper fire-and-forget autour de invalidate_membership_cache.

    Usage : call-sites CRUD (iam_service, admin_users, demo reset) qui veulent
    purger le cache sans risquer de casser le flow métier si l'invalidation
    échoue (pire cas : staleness ≤ 5 min, comportement pré-wiring).
    """
    try:
        invalidate_membership_cache(user_id=user_id, org_id=org_id)
    except Exception:
        logger.debug(
            "invalidate_membership_cache failed (user_id=%s, org_id=%s)",
            user_id,
            org_id,
            exc_info=True,
        )


def has_recent_audit_event(
    db: Session,
    user_id: int,
    action: str,
    cooldown_days: int,
) -> bool:
    """Retourne True si un AuditLog `action` pour `user_id` existe dans les N derniers jours.

    Pattern utilisé pour anti-flood d'events CX (NPS, CSAT, ...) où on veut ne
    pas harceler un même utilisateur. `action` doit être une des constantes
    CX_* ou un action_type d'AuditLog existant.
    """
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=cooldown_days)
    existing = (
        db.query(AuditLog.id)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.action == action,
            AuditLog.created_at >= cutoff,
        )
        .first()
    )
    return existing is not None


# Event type constants — utiliser ces constantes plutôt que des strings hardcodés
# pour éviter drift silencieux (la validation log_cx_event return si event_type
# n'est pas dans CX_EVENT_TYPES, sans trace).
CX_INSIGHT_CONSULTED = "CX_INSIGHT_CONSULTED"
CX_MODULE_ACTIVATED = "CX_MODULE_ACTIVATED"
CX_REPORT_EXPORTED = "CX_REPORT_EXPORTED"
CX_ONBOARDING_COMPLETED = "CX_ONBOARDING_COMPLETED"
CX_ACTION_FROM_INSIGHT = "CX_ACTION_FROM_INSIGHT"
CX_DASHBOARD_OPENED = "CX_DASHBOARD_OPENED"
# Sprint CX P1 residual : NPS micro-survey (scorecard 10% "NPS/CES")
CX_NPS_SUBMITTED = "CX_NPS_SUBMITTED"

CX_EVENT_TYPES = frozenset(
    {
        CX_INSIGHT_CONSULTED,
        CX_MODULE_ACTIVATED,
        CX_REPORT_EXPORTED,
        CX_ONBOARDING_COMPLETED,
        CX_ACTION_FROM_INSIGHT,
        CX_DASHBOARD_OPENED,
        CX_NPS_SUBMITTED,
    }
)


def make_dedup_key(key: str, value: str) -> str:
    """Construit le fragment canonique matché par log_cx_event_first_only.

    Format : `"<key>": "<value>"` (doit matcher exactement la sortie json.dumps).
    Exemple : make_dedup_key("module_key", "flex") → '"module_key": "flex"'.

    Garantit l'absence de false positive (ex. "flex" vs "flexibilite") via
    les guillemets fermants autour de la valeur.
    """
    if not key or not value:
        raise ValueError("make_dedup_key requires non-empty key and value")
    if '"' in key or '"' in value:
        raise ValueError(f"make_dedup_key does not support double quotes in key={key!r} or value={value!r}")
    return f'"{key}": "{value}"'


def log_cx_event_first_only(
    db: Session,
    org_id: int,
    user_id: Optional[int],
    event_type: str,
    dedup_key: str,
    context: Optional[dict] = None,
) -> bool:
    """
    Sprint CX 3 P0.4 : variante "1er only" de log_cx_event.

    Fire l'event UNIQUEMENT si aucun AuditLog précédent n'existe pour ce
    couple (org_id, event_type, dedup_key). `dedup_key` est cherché dans
    `detail_json` via LIKE (match sous-chaîne — sqlite-friendly).

    ⚠ `dedup_key` DOIT être un fragment JSON canonique au format exact
    `"<key>": "<value>"` produit par json.dumps avec terminateurs de valeur
    (guillemets fermants) — utiliser `make_dedup_key(key, value)` pour le
    construire et éviter les false positives ("flex" vs "flexibilite").

    Motivation : CX_MODULE_ACTIVATED doit signaler la *1ère* activation d'un
    module par une org (pour driver WAU-MAU / T2V). Sans dédup, chaque write
    dans le module re-fire l'event → pollution et métriques biaisées.

    Retourne True si l'event a été loggé (1ère activation), False sinon.

    Pattern d'usage :
        log_cx_event_first_only(
            db, org_id, user_id,
            CX_MODULE_ACTIVATED,
            dedup_key=make_dedup_key("module_key", "flex"),
            context={"module_key": "flex"},
        )
    """
    if event_type not in CX_EVENT_TYPES:
        return False

    existing = (
        db.query(AuditLog.id)
        .filter(
            AuditLog.action == event_type,
            AuditLog.resource_type == "cx_event",
            AuditLog.resource_id == str(org_id),
            AuditLog.detail_json.like(f"%{dedup_key}%"),
        )
        .first()
    )
    if existing is not None:
        return False

    log_cx_event(db, org_id, user_id, event_type, context)
    return True


def log_cx_event(
    db: Session,
    org_id: int,
    user_id: Optional[int],
    event_type: str,
    context: Optional[dict] = None,
) -> None:
    """
    Fire-and-forget log d'un event CX_*.

    Sprint CX 2.5 hardening (F2) : utilise db.flush() au lieu de db.commit()
    pour ne pas engager la transaction parente du caller. Si le handler
    parent raise après cet appel, les modifs pending ne sont PAS persistées.
    Le commit/rollback final est la responsabilité du caller (route handler).

    Sprint CX 2.5 hardening (S1) : si user_id fourni, valide que l'utilisateur
    est bien membre de org_id via UserOrgRole avant de logger. Protège
    DEMO_MODE contre forge de X-Org-Id par un user authentifié.
    """
    if event_type not in CX_EVENT_TYPES:
        return

    # S1 hardening : validation membership user → org
    # P2 hardening : membership check mis en cache (TTL 5 min) pour absorber le hot path
    # (polling /api/cockpit 30s). Voir _is_member_cached + invalidate_membership_cache.
    if user_id is not None and org_id is not None:
        if not _is_member_cached(db, user_id, org_id):
            logger.warning(
                "CX event rejeté : user_id=%s pas membre de org_id=%s (event=%s)",
                user_id,
                org_id,
                event_type,
            )
            return

    try:
        entry = AuditLog(
            user_id=user_id,
            action=event_type,
            resource_type="cx_event",
            resource_id=str(org_id),
            detail_json=json.dumps({"org_id": org_id, **(context or {})}),
        )
        db.add(entry)
        db.flush()  # F2 : ne commit pas la transaction parente
    except Exception:
        # Pas de rollback : on ne casse pas la transaction du caller.
        logger.debug("CX event logging failed for %s", event_type, exc_info=True)
