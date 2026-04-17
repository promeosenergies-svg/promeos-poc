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

from typing import Any


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
        **context: Champs additionnels à ajouter dans `detail` (ex. action_id=42)

    Returns:
        dict avec status_code et detail, utilisable comme :
            raise HTTPException(**business_error("ACTION_NOT_FOUND", action_id=42))

    Raises:
        KeyError: si le code n'existe pas dans le catalogue.
    """
    entry = ERROR_CATALOG[code]
    detail = {
        "code": code,
        "message": entry["message"],
        "suggestion": entry["suggestion"],
    }
    if context:
        detail["context"] = context
    return {"status_code": entry["http_status"], "detail": detail}
