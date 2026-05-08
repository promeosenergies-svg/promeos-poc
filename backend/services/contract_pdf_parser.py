"""
PROMEOS — Phase F3 (ADR-F-03) : parser PDF contrat d'énergie.

Extrait 8 champs cardinaux d'un PDF de contrat signé pour pré-remplir un
`EnergyContract` à valider par l'utilisateur (pas de persistance auto Phase F3).

Réutilise :
- `extract_text_with_fitz` (parser PDF facture Phase F2)
- `extract_siren_from_pdf_text` (Phase F2 — patterns SIRET/SIREN/RCS)
- `resolve_fournisseur_from_siren` (Phase F2 — bridge Fournisseur F1)

Champs cardinaux extraits (ADR-F-03 D2) :
1. supplier_name — nom fournisseur en tête contrat
2. fournisseur_id — résolu via Phase F2 (canonique ou privé scope)
3. reference_fournisseur — numéro contrat fournisseur
4. date_signature — date signature DD/MM/YYYY
5. start_date — début effet contrat
6. end_date — fin contrat (si fixe)
7. price_ref_eur_per_kwh — prix référence EUR/kWh
8. fixed_fee_eur_per_month — abonnement EUR/mois
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


@dataclass
class ContractParseResult:
    """Résultat parsing contrat — 8 champs cardinaux + métadonnées."""

    supplier_name: Optional[str] = None
    fournisseur_id: Optional[int] = None
    fournisseur_nom_canonique: Optional[str] = None
    reference_fournisseur: Optional[str] = None
    date_signature: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    price_ref_eur_per_kwh: Optional[float] = None
    fixed_fee_eur_per_month: Optional[float] = None
    siren_extracted: Optional[str] = None
    confidence: float = 0.0
    fields_extracted: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "supplier_name": self.supplier_name,
            "fournisseur_id": self.fournisseur_id,
            "fournisseur_nom_canonique": self.fournisseur_nom_canonique,
            "reference_fournisseur": self.reference_fournisseur,
            "date_signature": self.date_signature.isoformat() if self.date_signature else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "price_ref_eur_per_kwh": self.price_ref_eur_per_kwh,
            "fixed_fee_eur_per_month": self.fixed_fee_eur_per_month,
            "siren_extracted": self.siren_extracted,
            "confidence": round(self.confidence, 2),
            "fields_extracted": self.fields_extracted,
        }


# Phase F dette fix : helpers regex consolidés dans pdf_parser.py SoT (variadic).
# Import lazy pour éviter cycle import (pdf_parser dans `app/`, ce module dans `services/`).


# ─── Parser principal ─────────────────────────────────────────────────────────


def parse_contract_pdf_text(
    text: str,
    db: Optional[Session] = None,
    *,
    scope_org_id: Optional[int] = None,
) -> ContractParseResult:
    """Extrait 8 champs cardinaux d'un texte de contrat + résout Fournisseur.

    Args:
        text: texte extrait du PDF (via extract_text_with_fitz)
        db: session SQLAlchemy pour résolution Fournisseur (optionnel)
        scope_org_id: scope tenant pour Phase E IDOR (optionnel)

    Returns:
        ContractParseResult avec champs extraits + confidence + fields_extracted.
    """
    from app.bill_intelligence.parsers.pdf_parser import (
        _find_date,
        _find_float,
        _find_str,
        extract_siren_from_pdf_text,
    )

    result = ContractParseResult()

    # 1. Supplier name + SIREN extraction (réutilise F2)
    siren = extract_siren_from_pdf_text(text)
    result.siren_extracted = siren

    supplier_name = _find_str(
        text,
        r"(?:Fournisseur|Founisseur|Vendeur)\s*[:\s]*([A-Z][\w\s&\-\.]{2,50})",
    )
    # Fallback : 1ère ligne non vide en MAJUSCULES (souvent supplier en header)
    # P1 fix code-reviewer : exclure les stopwords contractuels génériques
    # (CONTRAT/ANNEXE/AVENANT...) qui matcheraient le pattern et donneraient
    # un supplier_name erroné avec haute confiance silencieuse.
    if not supplier_name:
        contract_stopwords = {
            "CONTRAT",
            "ANNEXE",
            "AVENANT",
            "CONDITIONS",
            "GENERALES",
            "PARTICULIERES",
            "ELECTRICITE",
            "GAZ",
            "ENERGIE",
            "FOURNITURE",
            "REGLEMENT",
        }
        for line in text.split("\n")[:5]:
            line = line.strip()
            if (
                len(line) >= 3
                and line.upper() == line
                and re.match(r"^[A-Z][A-Z\s\.\-&]{2,50}$", line)
                and not any(stopword in line for stopword in contract_stopwords)
            ):
                supplier_name = line
                break
    result.supplier_name = supplier_name

    # 2. Bridge Fournisseur F1 — appels directs aux 2 resolvers F2 (Phase F dette fix :
    # élimine le proxy intermédiaire fragile, plus explicite + même cardinal SoT).
    if db is not None:
        from services.fournisseur_resolver_service import (
            resolve_fournisseur_from_siren,
            resolve_fournisseur_from_supplier_name,
        )

        # Pass 1 : SIREN extrait (priorité — déterministe haute confiance)
        fournisseur = None
        if siren:
            fournisseur = resolve_fournisseur_from_siren(db, siren, scope_org_id=scope_org_id)
        # Pass 2 : fallback supplier_name mapping
        if fournisseur is None and supplier_name:
            fournisseur = resolve_fournisseur_from_supplier_name(db, supplier_name, scope_org_id=scope_org_id)
        if fournisseur:
            result.fournisseur_id = fournisseur.id
            result.fournisseur_nom_canonique = fournisseur.nom

    # 3. Reference fournisseur (numéro contrat)
    result.reference_fournisseur = _find_str(
        text,
        r"(?:N[°o]\s*(?:de\s*)?contrat|R[ée]f\.?\s*contrat|Contrat\s+n[°o])\s*[:\s]*(\S{4,40})",
    )

    # 4. Date signature
    result.date_signature = _find_date(
        text,
        r"(?:Date\s+de\s+signature|Sign[ée]\s+le|Fait\s+le)\s*[:\s]*(\d{2}/\d{2}/\d{4})",
    )

    # 5. Start date / 6. End date
    result.start_date = _find_date(
        text,
        r"(?:Date\s+de\s+d[ée]but|Effet\s+au|Du)\s*[:\s]*(\d{2}/\d{2}/\d{4})",
        r"(?:P[ée]riode\s+contractuelle|Validit[ée])\s*[:\s]*(?:du\s+)?(\d{2}/\d{2}/\d{4})",
    )
    result.end_date = _find_date(
        text,
        r"(?:Date\s+de\s+fin|[ÉE]ch[ée]ance|Fin\s+(?:du\s+contrat|d'effet))\s*[:\s]*(\d{2}/\d{2}/\d{4})",
        r"(?:au|jusqu['’]au)\s*(\d{2}/\d{2}/\d{4})",
    )

    # 7. Price ref EUR/kWh
    result.price_ref_eur_per_kwh = _find_float(
        text,
        r"(?:Prix\s+(?:de\s+r[ée]f[ée]rence|fix(?:e|é))|Prix\s+(?:HT|du)\s*kWh)[^€\n]*?([\d,.]+)\s*(?:EUR|€)?\s*/\s*kWh",
        r"([\d,.]+)\s*(?:EUR|€)\s*/\s*kWh",
    )

    # 8. Fixed fee EUR/mois (abonnement)
    result.fixed_fee_eur_per_month = _find_float(
        text,
        r"(?:Abonnement|Redevance\s+fixe)[^€\n]*?([\d,.]+)\s*(?:EUR|€)\s*/\s*mois",
        r"(?:Abonnement\s+mensuel)\s*[:\s]*([\d,.]+)\s*(?:EUR|€)",
    )

    # ── Confidence + fields_extracted ────────────────────────────────────────
    # P1 fix code-reviewer + /simplify : confidence sur 8 champs cardinaux ADR-F-03 D2.
    # `fournisseur_id` remplace `siren_extracted` quand db fourni (résolution prouvée).
    # Si db=None (parsing-only standalone), `siren_extracted` sert de proxy.
    cardinal_fields = {
        "supplier_name": result.supplier_name,
        "reference_fournisseur": result.reference_fournisseur,
        "date_signature": result.date_signature,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "price_ref_eur_per_kwh": result.price_ref_eur_per_kwh,
        "fixed_fee_eur_per_month": result.fixed_fee_eur_per_month,
        # 8e cardinal : fournisseur_id (db fourni) ou siren_extracted (fallback proxy)
        "fournisseur_id" if db is not None else "siren_extracted": (
            result.fournisseur_id if db is not None else result.siren_extracted
        ),
    }
    result.fields_extracted = [name for name, val in cardinal_fields.items() if val is not None]
    result.confidence = len(result.fields_extracted) / len(cardinal_fields)

    if result.confidence < 0.3:
        logger.warning(
            "contract_parse_low_confidence: %.2f fields=%s",
            result.confidence,
            result.fields_extracted,
        )

    return result


def parse_contract_pdf_bytes(
    content: bytes,
    db: Optional[Session] = None,
    *,
    scope_org_id: Optional[int] = None,
) -> ContractParseResult:
    """Entry point : PDF bytes → ContractParseResult.

    Réutilise `extract_text_with_fitz` du parser facture (Phase F2).
    """
    from app.bill_intelligence.parsers.pdf_parser import extract_text_with_fitz

    text = extract_text_with_fitz(content)
    return parse_contract_pdf_text(text, db, scope_org_id=scope_org_id)
