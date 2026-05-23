"""PROMEOS — Conformité P1 2026-05-23 : durée de validité Evidence par règle.

Avant ce service : `expires_at = uploaded_at + 90 jours` hardcoded dans
`PATCH /evidences/{id}/verify`. Inadapté aux preuves réglementaires dont la
validité légale dépasse largement 90 jours (ISO 50001 = 3 ans, audit
énergétique = 4 ans, etc.).

Source des durées :
- DT/OPERAT : déclaration annuelle (1 an) — Décret 2019-771 art. 6
- BACS : rapport conformité (3 ans pour certificat ISO 16484 typique) —
  Décret 2020-887 / 2025-1343
- APER : attestation annuelle (1 an, suivi conformité) — Loi 2023-175
- SMÉ : certificat ISO 50001 valide 3 ans — NF EN ISO 50001:2018
- SMÉ alt : rapport audit énergétique valide 4 ans — Loi 2025-391 art. 25
- BEGES : périodicité 3 ans — Décret 2022-982
- Défaut : 90 jours (preuves non réglementaires ou type inconnu)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional


# Durées de validité par règle réglementaire (jours).
# Source : sources officielles dans le docstring du module.
EVIDENCE_VALIDITY_DAYS_BY_RULE: dict[str, int] = {
    "DT": 365,
    "OPERAT": 365,
    "BACS": 365 * 3,
    "APER": 365,
    "SME": 365 * 3,
    "SMÉ": 365 * 3,
    "BEGES": 365 * 3,
}

# Pour les preuves "audit énergétique" (alternative à ISO 50001 pour SMÉ),
# la validité est de 4 ans (Loi 2025-391 art. 25 modifiant Code énergie L233-1).
EVIDENCE_VALIDITY_DAYS_AUDIT_ENERGETIQUE = 365 * 4

# Défaut quand le rule_code ne peut pas être déterminé.
DEFAULT_EVIDENCE_VALIDITY_DAYS = 90


def _detect_rule_code_from_title(title: Optional[str]) -> Optional[str]:
    """Heuristique : détecte le rule_code d'un item depuis son titre FR.

    Le `title_fr` produit par `conformite_action_sync_service` suit le pattern
    `"<règle FR> — <champ> à compléter"` (ex : `"Décret Tertiaire — Surface tertiaire à compléter"`).
    On scanne le préfixe pour deviner DT/BACS/APER/SME/BEGES.

    Retourne `None` si aucun pattern reconnu (item non-réglementaire ou titre custom).
    """
    if not title:
        return None
    lower = title.lower()
    # Ordre important : tester les libellés plus spécifiques d'abord
    if "audit énergétique" in lower or "audit energetique" in lower or " smé" in lower or "(smé)" in lower:
        return "SME"
    if "décret tertiaire" in lower or "decret tertiaire" in lower:
        return "DT"
    if "régulation chauffage" in lower or "regulation chauffage" in lower or "(bacs)" in lower:
        return "BACS"
    if "parking / toiture" in lower or "(aper)" in lower or "solarisation" in lower:
        return "APER"
    if "bilan ges" in lower or "beges" in lower:
        return "BEGES"
    if "operat" in lower:
        return "OPERAT"
    return None


def compute_default_expires_at(
    *,
    uploaded_at: datetime,
    parent_item_title: Optional[str] = None,
    rule_code_override: Optional[str] = None,
    is_audit_energetique: bool = False,
) -> datetime:
    """Calcule l'`expires_at` par défaut pour une Evidence selon sa règle parente.

    Doctrine Conformité P1 2026-05-23 : remplace le hardcoded 90 jours par une
    durée légale réaliste (3 ans ISO 50001, 4 ans audit énergétique, 1 an
    OPERAT/APER, défaut 90j).

    Args:
        uploaded_at: timestamp d'upload de la preuve (base du calcul).
        parent_item_title: titre du parent `ActionCenterItem` (heuristique
            pour deviner le rule_code).
        rule_code_override: si fourni, court-circuite l'heuristique titre.
        is_audit_energetique: marque la preuve comme "rapport audit énergétique"
            (durée 4 ans vs 3 ans ISO 50001 standard).

    Returns:
        datetime de validité (= uploaded_at + durée selon règle).
    """
    rule_code = rule_code_override or _detect_rule_code_from_title(parent_item_title)

    if is_audit_energetique and rule_code in {"SME", "SMÉ"}:
        days = EVIDENCE_VALIDITY_DAYS_AUDIT_ENERGETIQUE
    elif rule_code and rule_code in EVIDENCE_VALIDITY_DAYS_BY_RULE:
        days = EVIDENCE_VALIDITY_DAYS_BY_RULE[rule_code]
    else:
        days = DEFAULT_EVIDENCE_VALIDITY_DAYS

    return uploaded_at + timedelta(days=days)
