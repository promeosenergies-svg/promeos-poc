"""
PROMEOS — Phase F2.2 (ADR-F-02) : résolution Fournisseur depuis facture parsée.

Bridge cardinal entre `pdf_parser.parse_pdf_bytes()` et `Fournisseur` Phase F1.

Stratégie cardinal de résolution (3 passes ordonnées par confiance) :
1. **SIREN extrait du PDF** (plus haute confiance) → match canonique exact
2. **Mapping supplier_name** (variantes orthographiques) → canonique normalisé
3. **Fallback None** + log warning (action manuelle requise)

Pattern Phase E IDOR : `scope_org_id` permet de chercher aussi les fournisseurs
privés du tenant courant en plus des canoniques.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from config.fournisseur_mappings import (
    SUPPLIER_NAME_TO_CANONICAL,
    normalize_supplier_name,
)
from models.fournisseur import Fournisseur
from services.fournisseur_service import canonical_or_scoped_filter


logger = logging.getLogger(__name__)


def resolve_fournisseur_from_supplier_name(
    db: Session,
    supplier_name: Optional[str],
    *,
    scope_org_id: Optional[int] = None,
) -> Optional[Fournisseur]:
    """Résout un Fournisseur depuis un supplier_name libre extrait d'une facture.

    Pattern cohérent backfill F1.7 — mapping insensible casse + trim.
    Cherche d'abord dans canoniques (organisation_id NULL), puis dans privés
    du `scope_org_id` si fourni.

    Returns:
        Fournisseur si trouvé, None sinon.
    """
    if not supplier_name:
        return None

    normalized = normalize_supplier_name(supplier_name)
    canonical_key = SUPPLIER_NAME_TO_CANONICAL.get(normalized)
    if not canonical_key:
        # Pas de match dans le mapping canonique connu
        return None

    # Cherche dans canoniques d'abord (most likely)
    f = (
        db.query(Fournisseur)
        .filter(
            Fournisseur.nom == canonical_key,
            Fournisseur.organisation_id.is_(None),
        )
        .first()
    )
    if f:
        return f

    # Fallback : privés du tenant scope (ELD régionale custom mapping)
    if scope_org_id is not None:
        f = (
            db.query(Fournisseur)
            .filter(
                Fournisseur.nom == canonical_key,
                Fournisseur.organisation_id == scope_org_id,
            )
            .first()
        )
        if f:
            return f

    return None


def resolve_fournisseur_from_siren(
    db: Session,
    siren: Optional[str],
    *,
    scope_org_id: Optional[int] = None,
) -> Optional[Fournisseur]:
    """Résout un Fournisseur par SIREN exact (déterministe, plus haute confiance).

    Pattern Phase E IDOR : UNION canoniques + privés du scope_org_id.

    Returns:
        Fournisseur si SIREN match, None sinon.
    """
    if not siren or len(siren) != 9 or not siren.isdigit():
        return None

    return (
        db.query(Fournisseur)
        .filter(
            Fournisseur.siren == siren,
            canonical_or_scoped_filter(scope_org_id),
        )
        .first()
    )


def resolve_fournisseur_from_invoice(
    db: Session,
    invoice_domain: Any,
    *,
    scope_org_id: Optional[int] = None,
    pdf_text: Optional[str] = None,
) -> Optional[Fournisseur]:
    """Résolution composite cardinale : 2 passes ordonnées par confiance.

    1. SIREN extrait du PDF (`pdf_text` fourni) → match déterministe canonique
    2. Mapping supplier_name (variantes) → canonique normalisé

    Args:
        db: session SQLAlchemy
        invoice_domain: objet Invoice retourné par parse_pdf_bytes
        scope_org_id: scope tenant courant (None = canoniques uniquement)
        pdf_text: texte brut extrait du PDF pour extraction SIREN (optionnel)

    Returns:
        Fournisseur résolu ou None (avec log warning).
    """
    # Pass 1 : SIREN extrait (plus haute confiance)
    if pdf_text:
        from app.bill_intelligence.parsers.pdf_parser import extract_siren_from_pdf_text

        siren = extract_siren_from_pdf_text(pdf_text)
        if siren:
            f = resolve_fournisseur_from_siren(db, siren, scope_org_id=scope_org_id)
            if f:
                logger.info(
                    "fournisseur_resolved via SIREN extract: nom=%s siren=%s",
                    f.nom,
                    siren,
                )
                return f

    # Pass 2 : mapping supplier_name (variantes orthographiques)
    supplier_name = getattr(invoice_domain, "supplier", None) or ""
    f = resolve_fournisseur_from_supplier_name(
        db,
        supplier_name,
        scope_org_id=scope_org_id,
    )
    if f:
        logger.info(
            "fournisseur_resolved via supplier_name mapping: nom=%s raw=%r",
            f.nom,
            supplier_name,
        )
        return f

    # Pass 3 : fallback None + log warning
    logger.warning(
        "fournisseur_unresolved: supplier_name=%r — action manuelle requise (Phase F2 unmapped)",
        supplier_name,
    )
    return None
