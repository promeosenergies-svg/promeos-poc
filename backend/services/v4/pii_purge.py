"""M2-6.A.2 — Service de purge PII RGPD article 17 + audit CNIL article 30.

Implémente le droit à l'effacement pour un user identifié, en respectant
l'architecture V4 « UUID isolé + snapshot label » (ADR-029 §3.4) :

- `actor_id` (event_log) et `owner_id` (action_center_items) sont des UUID5
  déterministes dérivés de `User.id` Integer via le namespace V4_ACTOR. Une
  fois `User.id` purgé (PII effacée mais id préservé pour cohérence FK
  historiques), ces UUID5 deviennent **opaques** : on ne peut plus retrouver
  le user d'origine sans accès aux mappings users.email + recalcul.

- Les **snapshots label** (`actor_name`, `owner_display_name`) en revanche
  contiennent du PII direct (nom/prénom). Ils DOIVENT être anonymisés.

- `Evidence.uploaded_by/verified_by` et `Blocker.added_by/resolved_by` sont
  des UUID5 sans snapshot label → l'anonymisation par hard-clear du User PII
  suffit (rien à toucher sur les tables filles).

Stratégie hybride (Q1=A CNIL recommandé) :
  1. Anonymisation snapshots (`actor_name`, `owner_display_name`) → libellé sentinel
  2. Hard-delete `UserOrgRole` (relation user-org disparaît)
  3. Hard-clear User PII (email/nom/prenom/hashed_password/actif=False)
  4. Audit log `purge_log` (SHA256 hash, jamais user_id en clair)

Garde-fous :
- Q5=B whitelist : emails terminant par `.demo` non purgeables (422)
- Idempotency : 2e purge sur user déjà purgé → 409
- Transaction atomique : un seul commit en fin, rollback implicite sur exception
- dry_run : simule + rollback final, report compteurs renvoyé en preview

Référence : route V4 `_actor_uuid` ligne ~513 (pattern réutilisé strict).
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from models.iam import User, UserOrgRole
from models.v4.action_center_items import ActionCenterItem
from models.v4.action_event_log import ActionEventLog
from models.v4.purge_log import PurgeLog

logger = logging.getLogger(__name__)

ANONYMIZED_NAME = "Utilisateur supprimé"
PROTECTED_DEMO_SUFFIX = ".demo"

# Reproduit `_V4_ACTOR_NAMESPACE` de `routes/v4/action_center.py` (ligne 510).
# Single-source serait préférable, mais cela créerait un import circulaire
# service→routes. Le NAMESPACE est figé par convention V4 (jamais re-tiré).
_V4_ACTOR_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "promeos:v4:actor")


def _actor_uuid_for_user_id(user_id: int) -> uuid.UUID:
    """UUID5 déterministe identique à `routes/v4/action_center._actor_uuid`."""
    return uuid.uuid5(_V4_ACTOR_NAMESPACE, str(user_id))


def _hash_user_id(user_id: int) -> str:
    """SHA256 hex du user_id — traçabilité audit sans nominatif."""
    return hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()


def _is_protected_demo_user(user: User) -> bool:
    """Q5=B : emails terminant par '.demo' non purgeables (données fictives)."""
    return user.email.lower().endswith(PROTECTED_DEMO_SUFFIX)


def _is_already_purged(user: User) -> bool:
    """Convention M2-6.A.2 : user purgé a email = `purged_<hash>@purged.local`
    ET nom = ANONYMIZED_NAME (double check, pas seul email — défense en profondeur)."""
    return user.email is not None and user.email.startswith("purged_") and user.nom == ANONYMIZED_NAME


def _random_password_hash() -> str:
    """Hash bcrypt d'un secret aléatoire — jamais re-loggable (sécu défensive).

    Le user purgé ne doit JAMAIS pouvoir se reconnecter (POST /api/auth/login
    rejette tout password contre ce hash). bcrypt cost-12 standard.
    """
    random_password = secrets.token_urlsafe(32).encode("utf-8")
    return bcrypt.hashpw(random_password, bcrypt.gensalt()).decode("utf-8")


@dataclass
class PurgeReport:
    """Compteurs des entités anonymisées/supprimées lors de la purge."""

    user_pii_cleared: bool = False
    user_org_roles_deleted: int = 0
    event_logs_anonymized: int = 0
    action_items_owner_anonymized: int = 0
    purge_log_id: Optional[int] = None
    dry_run: bool = False


class PIIPurgeError(Exception):
    """Erreur métier purge (whitelist, déjà purgé, inexistant)."""

    def __init__(self, code: str, message: str, status_code: int = 422):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def purge_user(
    db: Session,
    user_id: int,
    purged_by_admin_id: int,
    reason: str,
    dry_run: bool = False,
) -> PurgeReport:
    """Purge PII du `user_id` en respect RGPD article 17.

    Args:
        db: SQLAlchemy session (transaction atomique gérée ici)
        user_id: id du user cible
        purged_by_admin_id: id de l'admin auteur (CNIL art. 30 chain of custody)
        reason: justification métier (≥ 10 chars validée côté endpoint)
        dry_run: si True, simule sans commit (report rendu en preview)

    Returns:
        PurgeReport : compteurs des entités traitées + flag dry_run

    Raises:
        PIIPurgeError(404) USER_NOT_FOUND : user inexistant
        PIIPurgeError(422) PROTECTED_DEMO_USER : email .demo whitelisté
        PIIPurgeError(409) USER_ALREADY_PURGED : 2e purge sur même user
        PIIPurgeError(500) PURGE_INTERNAL_ERROR : erreur cascade (rollback effectué)
    """
    # 1. Charger user
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise PIIPurgeError("USER_NOT_FOUND", "Utilisateur inexistant.", 404)

    # 2. Whitelist demo (Q5=B) — vérifié AVANT idempotency pour rejeter même
    # une 2e tentative sur compte démo (message clair, pas 409 confusant)
    if _is_protected_demo_user(user):
        raise PIIPurgeError(
            "PROTECTED_DEMO_USER",
            "Les comptes démo (suffixe .demo) ne sont pas purgeables.",
            422,
        )

    # 3. Idempotency (déjà purgé → 409, pas re-purge)
    if _is_already_purged(user):
        raise PIIPurgeError(
            "USER_ALREADY_PURGED",
            "Cet utilisateur a déjà été purgé.",
            409,
        )

    report = PurgeReport(dry_run=dry_run)
    user_id_int = user.id  # capturé avant clear (référence stable pour hash + log)
    user_id_hash = _hash_user_id(user_id_int)
    actor_uuid = _actor_uuid_for_user_id(user_id_int)

    try:
        # 4. Anonymiser snapshots V4 (PII direct dans actor_name / owner_display_name).
        #    NE PAS toucher actor_id/owner_id (UUID5 opaque, anonymisé via clear PII user).
        #    NE PAS toucher actor_type (CheckConstraint chk_actor_consistency : 'user'
        #    avec actor_id non-NULL reste cohérent — l'event A ÉTÉ un user, juste anonymisé).
        report.event_logs_anonymized = (
            db.query(ActionEventLog)
            .filter(ActionEventLog.actor_id == actor_uuid)
            .update(
                {ActionEventLog.actor_name: ANONYMIZED_NAME},
                synchronize_session=False,
            )
        )
        report.action_items_owner_anonymized = (
            db.query(ActionCenterItem)
            .filter(ActionCenterItem.owner_id == actor_uuid)
            .update(
                {ActionCenterItem.owner_display_name: ANONYMIZED_NAME},
                synchronize_session=False,
            )
        )

        # 5. Hard-delete UserOrgRole (cascade scopes via ORM relationship
        #    cascade="all, delete-orphan" — défini sur UserOrgRole.scopes).
        report.user_org_roles_deleted = (
            db.query(UserOrgRole).filter(UserOrgRole.user_id == user_id_int).delete(synchronize_session="fetch")
        )

        # 6. Hard-clear User PII (id préservé pour FK historiques + auditabilité).
        #    email unique → on génère `purged_<hash16>@purged.local` pour ne pas
        #    casser la contrainte UNIQUE et garantir l'invisibilité (`@purged.local`
        #    = TLD réservé, jamais routable).
        user.email = f"purged_{user_id_hash[:16]}@purged.local"
        user.nom = ANONYMIZED_NAME
        user.prenom = ""
        user.hashed_password = _random_password_hash()  # jamais re-loggable
        user.actif = False
        report.user_pii_cleared = True

        # 7. Audit log CNIL art. 30 — TOUJOURS créé, y compris en dry_run (l'entrée
        #    sera rollback-ée par le `db.rollback()` final si dry_run=True, mais on
        #    flush pour avoir l'id en preview).
        purge_log_entry = PurgeLog(
            user_id_hash=user_id_hash,
            purged_at=datetime.now(timezone.utc),
            purged_by_admin_id=purged_by_admin_id,
            reason=reason[:500],
            report_json=json.dumps(asdict(report)),
            dry_run=dry_run,
        )
        db.add(purge_log_entry)
        db.flush()
        report.purge_log_id = purge_log_entry.id

        # 8. Commit ou rollback selon dry_run.
        if dry_run:
            db.rollback()
            logger.info(
                "purge_user dry_run user_id_hash=%s admin=%d report=%s",
                user_id_hash,
                purged_by_admin_id,
                asdict(report),
            )
        else:
            db.commit()
            logger.info(
                "purge_user EXECUTED user_id_hash=%s admin=%d report=%s",
                user_id_hash,
                purged_by_admin_id,
                asdict(report),
            )

        return report

    except PIIPurgeError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        # Log volontairement sans le user.id ni email — défense PII (le hash suffit).
        logger.exception(
            "purge_user ERREUR user_id_hash=%s admin=%d : %s",
            user_id_hash,
            purged_by_admin_id,
            str(e)[:200],
        )
        raise PIIPurgeError(
            "PURGE_INTERNAL_ERROR",
            f"Erreur interne pendant la purge : {str(e)[:200]}",
            500,
        )
