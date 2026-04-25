"""
PROMEOS — Catalogue d'erreurs métier en français.

Sprint CX item #3 : traduction des 20 codes d'erreur backend les plus fréquents
en messages lisibles par un utilisateur non technique, avec suggestion d'action.

Format de chaque entrée :
    CODE = {
        "message":    "Ce qui s'est passé, en langage métier (phrase courte)",
        "suggestion": "Ce que l'utilisateur peut faire maintenant",
        "http_status": 400|404|409|422|500,
    }

Usage depuis une route :
    from services.error_catalog import business_error
    raise HTTPException(**business_error("ACTION_NOT_FOUND"))

Le helper retourne un kwargs prêt pour HTTPException :
    { "status_code": 404, "detail": {"code": "...", "message": "...", "suggestion": "..."} }
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Sprint CX 2.5-bis (S3) : anti-PII guard sur le context sérialisé au client.
#
# Contexte : business_error(**context) sérialise le dict `context` directement
# dans detail.context. Un dev pressé peut passer `user_email=u.email` ou
# `action=action_orm_obj` → leak PII ou objet SQLAlchemy au client.
#
# Stratégie :
#   1. Allowlist de clés neutres (IDs, codes fiscaux, champs techniques).
#   2. Regex de blocklist pour les clés "dangereuses" (email, token, nom…) —
#      filet de sécurité si un dev ajoute une nouvelle clé sans maj l'allowlist.
#   3. Warning log si une clé est strippée (pour détecter les usages à
#      corriger côté caller).
_SAFE_CONTEXT_KEYS: frozenset[str] = frozenset(
    {
        "action_id",
        "site_id",
        "org_id",
        "siren",
        "siret",
        "module",
        "field",
        "value_reçue",
        "limite",
        "period_start",
        "period_end",
        "count",
    }
)

# Regex case-insensitive : toute clé matchant ce pattern est strippée même
# si elle finit dans l'allowlist un jour par erreur (defense in depth).
_PII_KEY_PATTERN = re.compile(r"email|phone|token|password|_at$|name$|nom", re.IGNORECASE)


def _sanitize_context(code: str, context: dict[str, Any]) -> dict[str, Any]:
    """Filtre un dict de context pour ne garder que les clés safe.

    - Garde uniquement les clés dans _SAFE_CONTEXT_KEYS.
    - Strippe aussi toute clé matchant _PII_KEY_PATTERN (même si dans l'allowlist).
    - Log un warning par clé strippée avec le code d'erreur pour traçabilité.
    """
    safe: dict[str, Any] = {}
    for key, value in context.items():
        if _PII_KEY_PATTERN.search(key):
            logger.warning(
                "business_error[%s] : clé context '%s' strippée (match PII pattern)",
                code,
                key,
            )
            continue
        if key not in _SAFE_CONTEXT_KEYS:
            logger.warning(
                "business_error[%s] : clé context '%s' strippée (pas dans allowlist)",
                code,
                key,
            )
            continue
        safe[key] = value
    return safe


ERROR_CATALOG: dict[str, dict[str, Any]] = {
    # ── Actions ─────────────────────────────────────────────────────────────
    "ACTION_NOT_FOUND": {
        "message": "Cette action n'existe plus ou a été supprimée.",
        "suggestion": "Rafraîchissez la page pour voir la liste à jour.",
        "http_status": 404,
    },
    "ACTION_CLOSE_BLOCKED": {
        "message": "Cette action ne peut pas être clôturée : certaines conditions ne sont pas remplies.",
        "suggestion": "Ajoutez les pièces justificatives requises et renseignez le motif de clôture.",
        "http_status": 400,
    },
    "TITLE_REQUIRED": {
        "message": "Le titre de l'action est obligatoire.",
        "suggestion": "Ajoutez un titre explicite (ex. « Renégocier contrat site Toulouse »).",
        "http_status": 422,
    },
    "PRIORITY_REQUIRED": {
        "message": "La priorité est obligatoire.",
        "suggestion": "Choisissez une valeur de 1 (critique) à 5 (faible).",
        "http_status": 400,
    },
    "PRIORITY_OUT_OF_RANGE": {
        "message": "La priorité doit être comprise entre 1 et 5.",
        "suggestion": "Ajustez la valeur : 1 = critique, 5 = faible.",
        "http_status": 400,
    },
    "REASON_REQUIRED": {
        "message": "Un motif est obligatoire pour cette opération (5 caractères minimum).",
        "suggestion": "Expliquez brièvement la raison pour garder un historique clair.",
        "http_status": 400,
    },
    # ── Patrimoine & données ────────────────────────────────────────────────
    "SITE_NOT_FOUND": {
        "message": "Ce site n'existe plus dans votre patrimoine.",
        "suggestion": "Rafraîchissez la liste de vos sites ou vérifiez l'identifiant.",
        "http_status": 404,
    },
    "ALERT_NOT_FOUND": {
        "message": "Cette alerte n'est plus disponible.",
        "suggestion": "Rafraîchissez la liste pour voir les alertes actives.",
        "http_status": 404,
    },
    # ── Sirene / Onboarding ─────────────────────────────────────────────────
    "SIREN_INVALID": {
        "message": "Le SIREN saisi n'est pas valide (9 chiffres attendus).",
        "suggestion": "Vérifiez le numéro sur votre Kbis et réessayez.",
        "http_status": 400,
    },
    "SIRET_INVALID": {
        "message": "Le SIRET saisi n'est pas valide (14 chiffres attendus).",
        "suggestion": "Vérifiez le numéro sur votre document officiel et réessayez.",
        "http_status": 400,
    },
    "ETABLISSEMENT_NOT_FOUND": {
        "message": "Aucun établissement trouvé pour ce SIRET.",
        "suggestion": "Utilisez la recherche par SIREN pour voir tous les établissements de l'entreprise.",
        "http_status": 404,
    },
    "INVALID_DATE_FORMAT": {
        "message": "Le format de date est invalide.",
        "suggestion": "Utilisez le format AAAA-MM-JJ (ex. 2026-04-17).",
        "http_status": 400,
    },
    # ── Administration / Utilisateurs ───────────────────────────────────────
    "EMAIL_ALREADY_EXISTS": {
        "message": "Cette adresse email est déjà utilisée par un autre utilisateur.",
        "suggestion": "Utilisez une autre adresse ou contactez votre administrateur si c'est une erreur.",
        "http_status": 409,
    },
    "USER_NOT_FOUND": {
        "message": "Utilisateur introuvable.",
        "suggestion": "Vérifiez votre sélection ou rafraîchissez la liste des utilisateurs.",
        "http_status": 404,
    },
    "LAST_DG_OWNER_PROTECTION": {
        "message": "Impossible de retirer le dernier DG OWNER de l'organisation.",
        "suggestion": "Ajoutez un autre utilisateur avec le rôle DG OWNER avant de retirer celui-ci.",
        "http_status": 400,
    },
    "USER_NO_ROLE_IN_ORG": {
        "message": "Cet utilisateur n'a aucun rôle dans cette organisation.",
        "suggestion": "Assignez-lui d'abord un rôle depuis l'administration.",
        "http_status": 404,
    },
    # ── Versioning / Pondération ────────────────────────────────────────────
    "VERSION_NOT_FOUND": {
        "message": "Cette version de configuration n'existe pas.",
        "suggestion": "Vérifiez la liste des versions disponibles.",
        "http_status": 404,
    },
    "VERSION_ALREADY_EXISTS": {
        "message": "Cette version existe déjà.",
        "suggestion": "Utilisez un numéro de version différent ou modifiez la version existante.",
        "http_status": 400,
    },
    "WEIGHTS_SUM_INVALID": {
        "message": "La somme des pondérations doit être égale à 1,0 (100 %).",
        "suggestion": "Ajustez les poids pour que leur total fasse exactement 1,0.",
        "http_status": 400,
    },
    "NO_PREVIOUS_VERSION": {
        "message": "Aucune version précédente n'est disponible pour rollback.",
        "suggestion": "C'est la première version enregistrée.",
        "http_status": 400,
    },
}


def business_error(code: str, **context: Any) -> dict[str, Any]:
    """
    Formate une entrée du catalogue en kwargs prêt pour HTTPException.

    Args:
        code: Clé du catalogue (ex. "ACTION_NOT_FOUND")
        **context: Champs additionnels à ajouter dans `detail` (ex. action_id=42).
            Sprint CX 2.5-bis (S3) : les clés sont filtrées par _SAFE_CONTEXT_KEYS
            avant sérialisation. Toute clé hors allowlist ou matchant le pattern
            PII (email/phone/token/password/*_at/*name/nom) est strippée avec
            un warning log. Passer `user_email=x` ne leak RIEN au client.

    Returns:
        dict avec status_code et detail, utilisable comme :
            raise HTTPException(**business_error("ACTION_NOT_FOUND", action_id=42))

    Raises:
        KeyError: si le code n'existe pas dans le catalogue.
    """
    entry = ERROR_CATALOG[code]
    detail: dict[str, Any] = {
        "code": code,
        "message": entry["message"],
        "suggestion": entry["suggestion"],
    }
    if context:
        safe_context = _sanitize_context(code, context)
        if safe_context:
            detail["context"] = safe_context
    return {"status_code": entry["http_status"], "detail": detail}
