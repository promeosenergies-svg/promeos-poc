"""
PROMEOS Bill Intelligence — PDF Parser Framework
Template-based PDF parsing for electricity and gas invoices.

Architecture:
- PDFTemplate: defines regex patterns + extraction logic for a supplier layout
- parse_pdf_text(): extracts Invoice from raw text (from PDF extraction)
- parse_pdf_file(): extracts text from PDF then parses (requires pdfplumber)

V0 POC: 2 templates (EDF elec, Engie gaz).
Uses raw text extraction — real PDF extraction via pdfplumber is optional.
"""

import re
import os
import hashlib
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

from ..domain import (
    Invoice,
    InvoiceComponent,
    InvoiceStatus,
    EnergyType,
    ComponentType,
)


@dataclass
class PDFTemplate:
    """Template for parsing a specific supplier's PDF layout."""

    template_id: str
    supplier_pattern: str  # Regex to match supplier name in text
    energy_type: EnergyType
    description: str

    def match(self, text: str) -> bool:
        """Check if this template matches the given text."""
        return bool(re.search(self.supplier_pattern, text, re.IGNORECASE | re.DOTALL))


# ========================================
# Text extraction
# ========================================


def extract_text_with_fitz(content: bytes) -> str:
    """Extract text from PDF bytes via pymupdf (fitz) — in requirements.txt."""
    import fitz  # pymupdf

    doc = fitz.open(stream=content, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def parse_pdf_bytes(content: bytes, source_filename: str = "upload.pdf"):
    """Entry point: PDF bytes → Invoice domain object or None."""
    text = extract_text_with_fitz(content)
    return parse_pdf_text(text, source_filename)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file path (legacy — used in tests).
    Reads file bytes and delegates to extract_text_with_fitz.
    """
    with open(file_path, "rb") as f:
        content = f.read()
    # Fallback: if it's a .txt file pretending to be a PDF (demo mode)
    if file_path.endswith(".txt"):
        return content.decode("utf-8", errors="replace")
    return extract_text_with_fitz(content)


# ========================================
# Common regex helpers
# ========================================


def _find_float(text: str, pattern: str) -> Optional[float]:
    """Extract a float value from text using regex pattern."""
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        val = m.group(1).replace(",", ".").replace(" ", "")
        try:
            return float(val)
        except ValueError:
            return None
    return None


def _find_date(text: str, pattern: str) -> Optional[date]:
    """Extract a date from text using regex pattern."""
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        try:
            return datetime.strptime(m.group(1).strip(), "%d/%m/%Y").date()
        except (ValueError, IndexError):
            pass
    return None


def _find_str(text: str, pattern: str) -> Optional[str]:
    """Extract a string from text using regex pattern."""
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


# ========================================
# EDF Electricity Template
# ========================================


def parse_edf_elec(text: str, source_file: Optional[str] = None) -> Invoice:
    """
    Parse EDF electricity invoice from extracted text.
    Handles typical EDF Pro/Entreprises PDF layout.
    """
    # Invoice ID
    invoice_id = _find_str(text, r"(?:N[°o]\s*(?:de\s*)?facture|Ref\.?\s*facture)\s*[:\s]*(\S+)")
    if not invoice_id:
        invoice_id = _find_str(text, r"Facture\s+n[°o]\s*(\S+)")
    if not invoice_id:
        invoice_id = f"PDF-ELEC-{hashlib.md5(text[:200].encode()).hexdigest()[:8].upper()}"

    # Contract
    contract_ref = _find_str(text, r"(?:Ref\.?\s*contrat|N[°o]\s*contrat)\s*[:\s]*(\S+)")

    # PDL
    pdl = _find_str(text, r"(?:PDL|Point\s+de\s+livraison)\s*[:\s]*(\d{14})")

    # Dates
    invoice_date = _find_date(text, r"(?:Date\s+(?:de\s+)?facture|Emise?\s+le)\s*[:\s]*(\d{2}/\d{2}/\d{4})")
    due_date = _find_date(text, r"(?:Date\s+(?:d['\u2019])?echeance|[AÀ]\s*payer\s+avant)\s*[:\s]*(\d{2}/\d{2}/\d{4})")
    period_start = _find_date(text, r"(?:Periode|Du|Consommation\s+du)\s*[:\s]*(\d{2}/\d{2}/\d{4})")
    period_end = _find_date(text, r"(?:au|Periode.*?au)\s*(\d{2}/\d{2}/\d{4})")

    # Totals
    total_ht = _find_float(text, r"(?:Total\s+HT|Montant\s+HT)\s*[:\s]*([\d\s,.]+)\s*(?:EUR|€)")
    total_tva = _find_float(text, r"(?:Total\s+TVA|Montant\s+TVA)\s*[:\s]*([\d\s,.]+)\s*(?:EUR|€)")
    total_ttc = _find_float(text, r"(?:Total\s+TTC|Montant\s+TTC|Net\s+[àa]\s+payer)\s*[:\s]*([\d\s,.]+)\s*(?:EUR|€)")

    # Consumption
    conso = _find_float(text, r"(?:Consommation|Conso\.?)\s*[:\s]*([\d\s,.]+)\s*kWh")
    puissance = _find_float(text, r"(?:Puissance\s+souscrite)\s*[:\s]*([\d\s,.]+)\s*kVA")

    # Parse components from text
    components = _extract_elec_components(text)

    input_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    return Invoice(
        invoice_id=invoice_id,
        energy_type=EnergyType.ELEC,
        supplier="EDF Entreprises",
        contract_ref=contract_ref,
        pdl_pce=pdl,
        invoice_date=invoice_date,
        due_date=due_date,
        period_start=period_start,
        period_end=period_end,
        total_ht=total_ht,
        total_tva=total_tva,
        total_ttc=total_ttc,
        conso_kwh=conso,
        puissance_souscrite_kva=puissance,
        components=components,
        status=InvoiceStatus.PARSED,
        source_file=source_file,
        source_format="pdf",
        parsing_confidence=_compute_confidence(total_ht, total_ttc, components),
        input_hash=input_hash,
    )


def _extract_elec_components(text: str) -> List[InvoiceComponent]:
    """Extract electricity invoice components from text."""
    components = []

    # Abonnement
    abo = _find_float(text, r"Abonnement[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
    if abo:
        components.append(
            InvoiceComponent(
                component_type=ComponentType.ABONNEMENT,
                label="Abonnement",
                amount_ht=abo,
                tva_rate=5.5,
            )
        )

    # HP
    hp_qty = _find_float(text, r"[Hh]eures?\s*[Pp]leines?\s*[\s:]*?([\d\s,.]+)\s*kWh")
    hp_price = _find_float(text, r"[Hh]eures?\s*[Pp]leines?[^€\n]*?([\d,.]+)\s*(?:EUR|€)/kWh")
    hp_amount = _find_float(text, r"[Hh]eures?\s*[Pp]leines?[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)\s*$")
    if hp_amount or (hp_qty and hp_price):
        components.append(
            InvoiceComponent(
                component_type=ComponentType.CONSO_HP,
                label="Energie heures pleines",
                quantity=hp_qty,
                unit="kWh",
                unit_price=hp_price,
                amount_ht=hp_amount or (round(hp_qty * hp_price, 2) if hp_qty and hp_price else None),
                tva_rate=20.0,
            )
        )

    # HC
    hc_qty = _find_float(text, r"[Hh]eures?\s*[Cc]reuses?\s*[\s:]*?([\d\s,.]+)\s*kWh")
    hc_price = _find_float(text, r"[Hh]eures?\s*[Cc]reuses?[^€\n]*?([\d,.]+)\s*(?:EUR|€)/kWh")
    hc_amount = _find_float(text, r"[Hh]eures?\s*[Cc]reuses?[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)\s*$")
    if hc_amount or (hc_qty and hc_price):
        components.append(
            InvoiceComponent(
                component_type=ComponentType.CONSO_HC,
                label="Energie heures creuses",
                quantity=hc_qty,
                unit="kWh",
                unit_price=hc_price,
                amount_ht=hc_amount or (round(hc_qty * hc_price, 2) if hc_qty and hc_price else None),
                tva_rate=20.0,
            )
        )

    # Base (if not HP/HC)
    if not hp_amount and not hc_amount:
        base_qty = _find_float(text, r"(?:Energie|Consommation)\s*(?:base)?\s*[\s:]*?([\d\s,.]+)\s*kWh")
        base_price = _find_float(text, r"(?:Energie|Consommation)[^€\n]*?([\d,.]+)\s*(?:EUR|€)/kWh")
        base_amount = _find_float(text, r"(?:Energie|Consommation)\s*(?:base)?[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
        if base_amount:
            components.append(
                InvoiceComponent(
                    component_type=ComponentType.CONSO_BASE,
                    label="Energie base",
                    quantity=base_qty,
                    unit="kWh",
                    unit_price=base_price,
                    amount_ht=base_amount,
                    tva_rate=20.0,
                )
            )

    # TURPE
    turpe_gestion = _find_float(text, r"(?:TURPE|Acheminement).*?[Gg]estion[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
    if turpe_gestion:
        components.append(
            InvoiceComponent(
                component_type=ComponentType.TURPE_FIXE,
                label="TURPE - Composante de gestion",
                amount_ht=turpe_gestion,
                tva_rate=5.5,
            )
        )

    turpe_soutirage = _find_float(text, r"(?:TURPE|Acheminement).*?[Ss]outirage[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
    if turpe_soutirage:
        components.append(
            InvoiceComponent(
                component_type=ComponentType.TURPE_PUISSANCE,
                label="TURPE - Composante de soutirage",
                amount_ht=turpe_soutirage,
                tva_rate=20.0,
            )
        )

    # CTA
    cta = _find_float(text, r"CTA[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
    if cta:
        components.append(
            InvoiceComponent(
                component_type=ComponentType.CTA,
                label="CTA",
                amount_ht=cta,
                tva_rate=5.5,
                metadata={"tax_code": "CTA"},
            )
        )

    # Accise / CSPE / TICFE / Contrib. service public élec (ENGIE label for ACCISE_ELEC)
    accise = _find_float(text, r"(?:Accise|CSPE|TICFE|Contrib\.?\s*(?:service\s+public|aux\s+charges))[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
    if accise:
        # Detect label_source for traceability
        label_source = "Accise sur l'electricite"
        if re.search(r"Contrib\.?\s*(?:service\s+public|aux\s+charges)", text, re.IGNORECASE):
            label_source = "Contrib. service public elec"
        components.append(
            InvoiceComponent(
                component_type=ComponentType.ACCISE,
                label=label_source,
                amount_ht=accise,
                tva_rate=20.0,
                metadata={"tax_code": "ACCISE_ELEC"},
            )
        )

    return components


# ========================================
# Engie Gas Template
# ========================================


def parse_engie_gaz(text: str, source_file: Optional[str] = None) -> Invoice:
    """
    Parse Engie gas invoice from extracted text.
    """
    invoice_id = _find_str(text, r"(?:N[°o]\s*(?:de\s*)?facture|Ref\.?\s*facture)\s*[:\s]*(\S+)")
    if not invoice_id:
        invoice_id = f"PDF-GAZ-{hashlib.md5(text[:200].encode()).hexdigest()[:8].upper()}"

    contract_ref = _find_str(text, r"(?:Ref\.?\s*contrat|N[°o]\s*contrat)\s*[:\s]*(\S+)")
    pce = _find_str(text, r"(?:PCE|Point\s+de\s+comptage)\s*[:\s]*(GI\d{12})")

    invoice_date = _find_date(text, r"(?:Date\s+(?:de\s+)?facture|Emise?\s+le)\s*[:\s]*(\d{2}/\d{2}/\d{4})")
    due_date = _find_date(text, r"(?:Date\s+(?:d['\u2019])?echeance|[AÀ]\s*payer\s+avant)\s*[:\s]*(\d{2}/\d{2}/\d{4})")
    period_start = _find_date(text, r"(?:Periode|Du|Consommation\s+du)\s*[:\s]*(\d{2}/\d{2}/\d{4})")
    period_end = _find_date(text, r"(?:au|Periode.*?au)\s*(\d{2}/\d{2}/\d{4})")

    total_ht = _find_float(text, r"(?:Total\s+HT|Montant\s+HT)\s*[:\s]*([\d\s,.]+)\s*(?:EUR|€)")
    total_tva = _find_float(text, r"(?:Total\s+TVA|Montant\s+TVA)\s*[:\s]*([\d\s,.]+)\s*(?:EUR|€)")
    total_ttc = _find_float(text, r"(?:Total\s+TTC|Montant\s+TTC|Net\s+[àa]\s+payer)\s*[:\s]*([\d\s,.]+)\s*(?:EUR|€)")
    conso = _find_float(text, r"(?:Consommation|Conso\.?)\s*[:\s]*([\d\s,.]+)\s*kWh")

    components = _extract_gaz_components(text)

    input_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    return Invoice(
        invoice_id=invoice_id,
        energy_type=EnergyType.GAZ,
        supplier="Engie Entreprises",
        contract_ref=contract_ref,
        pdl_pce=pce,
        invoice_date=invoice_date,
        due_date=due_date,
        period_start=period_start,
        period_end=period_end,
        total_ht=total_ht,
        total_tva=total_tva,
        total_ttc=total_ttc,
        conso_kwh=conso,
        components=components,
        status=InvoiceStatus.PARSED,
        source_file=source_file,
        source_format="pdf",
        parsing_confidence=_compute_confidence(total_ht, total_ttc, components),
        input_hash=input_hash,
    )


def _extract_gaz_components(text: str) -> List[InvoiceComponent]:
    """Extract gas invoice components from text."""
    components = []

    # Abonnement
    abo = _find_float(text, r"Abonnement[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
    if abo:
        components.append(
            InvoiceComponent(
                component_type=ComponentType.ABONNEMENT,
                label="Abonnement distribution gaz",
                amount_ht=abo,
                tva_rate=5.5,
            )
        )

    # Molecule
    mol_qty = _find_float(text, r"[Mm]ol[eé]cule[^€\n]*?([\d\s,.]+)\s*kWh")
    mol_price = _find_float(text, r"[Mm]ol[eé]cule[^€\n]*?([\d,.]+)\s*(?:EUR|€)/kWh")
    mol_amount = _find_float(text, r"[Mm]ol[eé]cule[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
    if mol_amount:
        components.append(
            InvoiceComponent(
                component_type=ComponentType.TERME_VARIABLE,
                label="Molecule gaz naturel",
                quantity=mol_qty,
                unit="kWh",
                unit_price=mol_price,
                amount_ht=mol_amount,
                tva_rate=20.0,
            )
        )

    # ATRD / distribution fixe
    atrd_fixe = _find_float(text, r"(?:ATRD|Distribution).*?(?:[Ff]ixe|[Pp]art\s+fixe)[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
    if atrd_fixe:
        components.append(
            InvoiceComponent(
                component_type=ComponentType.TERME_FIXE,
                label="ATRD - Part fixe distribution",
                amount_ht=atrd_fixe,
                tva_rate=5.5,
            )
        )

    # ATRD proportionnelle
    atrd_prop = _find_float(text, r"(?:ATRD|Distribution).*?[Pp]roportionnelle[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
    if atrd_prop:
        components.append(
            InvoiceComponent(
                component_type=ComponentType.TURPE_ENERGIE,
                label="ATRD - Part proportionnelle",
                amount_ht=atrd_prop,
                tva_rate=20.0,
            )
        )

    # CTA
    cta = _find_float(text, r"CTA[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
    if cta:
        components.append(
            InvoiceComponent(
                component_type=ComponentType.CTA,
                label="CTA",
                amount_ht=cta,
                tva_rate=5.5,
                metadata={"tax_code": "CTA"},
            )
        )

    # Accise / TICGN
    accise = _find_float(text, r"(?:Accise|TICGN)[^€\n]*?([\d\s,.]+)\s*(?:EUR|€)")
    if accise:
        components.append(
            InvoiceComponent(
                component_type=ComponentType.ACCISE,
                label="Accise sur le gaz naturel",
                amount_ht=accise,
                tva_rate=20.0,
                metadata={"tax_code": "ACCISE_GAZ"},
            )
        )

    return components


# ========================================
# Engie Electricity Template
# ========================================


def parse_engie_elec(text: str, source_file: Optional[str] = None) -> Invoice:
    """
    Parse Engie electricity invoice from extracted text.
    Handles ENGIE Pro PDF layout for electricity (C5, C4, C3 segments).
    """
    invoice_id = _find_str(text, r"N[°\u00b0]+\s*(\d+)")
    if not invoice_id:
        invoice_id = _find_str(text, r"(?:N[°o]\s*(?:de\s*)?facture|Ref\.?\s*facture)\s*[:\s]*(\S+)")
    if not invoice_id:
        invoice_id = f"PDF-ELEC-ENGIE-{hashlib.md5(text[:200].encode()).hexdigest()[:8].upper()}"

    contract_ref = _find_str(text, r"(?:Ref\.?\s*contrat|N[°o]\s*contrat)\s*[:\s]*(\S+)")
    pdl = _find_str(text, r"(?:PDL|Point\s+de\s+livraison)\s*[:\s]*(\d{14})")

    invoice_date = _find_date(text, r"(?:Date\s+(?:de\s+)?facture|Emise?\s+le|facture du)\s*[:\s]*(\d{2}/\d{2}/\d{4})")
    due_date = _find_date(text, r"(?:Date\s+(?:d['\u2019])?echeance|[AÀ]\s*payer\s+avant|pr[eé]lev[eé]\s+le)\s*[:\s]*(\d{2}/\d{2}/\d{4})")
    period_start = _find_date(text, r"(?:Periode|Du|Consommation\s+du|Abonnement\s+du)\s*[:\s]*(\d{2}/\d{2}/\d{4})")
    period_end = _find_date(text, r"(?:au|Periode.*?au)\s*(\d{2}/\d{2}/\d{4})")

    total_ht = _find_float(text, r"(?:Total\s+HT|total\s+hors\s+toutes\s+taxes|Montant\s+HT)\s*[:\s]*([\d\s,.]+)\s*(?:EUR|€)")
    total_tva = _find_float(text, r"(?:Total\s+TVA|Montant\s+TVA)\s*[:\s]*([\d\s,.]+)\s*(?:EUR|€)")
    total_ttc = _find_float(text, r"(?:total\s+TTC|Montant\s+TTC|Net\s+[àa]\s+payer)\s*[:\s]*([\d\s,.]+)\s*(?:EUR|€)")

    # ENGIE-specific: HTVA (hors toutes taxes + taxes)
    htva = _find_float(text, r"total\s+HTVA\s*\n?\s*([\d\s,.]+)\s*(?:EUR|€)")
    if htva and not total_ht:
        total_ht = htva

    conso = _find_float(text, r"(?:Consommation|Conso\.?)\s*[:\s]*([\d\s,.]+)\s*kWh")
    puissance = _find_float(text, r"(?:Puissance\s+souscrite)\s+(\d+)\s*kVA")

    components = _extract_elec_components(text)

    input_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    return Invoice(
        invoice_id=invoice_id,
        energy_type=EnergyType.ELEC,
        supplier="Engie Entreprises",
        contract_ref=contract_ref,
        pdl_pce=pdl,
        invoice_date=invoice_date,
        due_date=due_date,
        period_start=period_start,
        period_end=period_end,
        total_ht=total_ht,
        total_tva=total_tva,
        total_ttc=total_ttc,
        conso_kwh=conso,
        puissance_souscrite_kva=puissance,
        components=components,
        status=InvoiceStatus.PARSED,
        source_file=source_file,
        source_format="pdf",
        parsing_confidence=_compute_confidence(total_ht, total_ttc, components),
        input_hash=input_hash,
    )


# ========================================
# Confidence scoring
# ========================================


def _compute_confidence(
    total_ht: Optional[float], total_ttc: Optional[float], components: List[InvoiceComponent]
) -> float:
    """Compute parsing confidence score (0.0 to 1.0)."""
    score = 0.0
    checks = 0

    # Has totals?
    if total_ht is not None:
        score += 1.0
    checks += 1

    if total_ttc is not None:
        score += 1.0
    checks += 1

    # Has components?
    if len(components) >= 3:
        score += 1.0
    elif len(components) >= 1:
        score += 0.5
    checks += 1

    # Components have amounts?
    if components:
        with_amounts = sum(1 for c in components if c.amount_ht is not None)
        score += with_amounts / len(components)
    checks += 1

    return round(score / max(checks, 1), 2)


# ========================================
# Template registry
# ========================================

TEMPLATES = [
    PDFTemplate(
        template_id="edf_elec_v1",
        supplier_pattern=r"EDF|Electricit[eé]\s+de\s+France",
        energy_type=EnergyType.ELEC,
        description="EDF Entreprises - Facture electricite",
    ),
    # ENGIE elec — must be checked BEFORE engie_gaz: if text contains
    # "Electricite" section markers it's elec, otherwise fall through to gaz.
    PDFTemplate(
        template_id="engie_elec_v1",
        supplier_pattern=r"(?:Engie|GDF\s+Suez).*(?:[Ee]lectricit|Point de livraison)",
        energy_type=EnergyType.ELEC,
        description="Engie Entreprises - Facture electricite",
    ),
    PDFTemplate(
        template_id="engie_gaz_v1",
        supplier_pattern=r"Engie|GDF\s+Suez",
        energy_type=EnergyType.GAZ,
        description="Engie Entreprises - Facture gaz",
    ),
]


def detect_template(text: str) -> Optional[PDFTemplate]:
    """Detect which template matches the given text."""
    for tpl in TEMPLATES:
        if tpl.match(text):
            return tpl
    return None


def parse_pdf_text(text: str, source_file: Optional[str] = None) -> Invoice:
    """
    Parse extracted PDF text into an Invoice using template matching.
    """
    template = detect_template(text)
    if template is None:
        raise ValueError("No matching PDF template found for this document")

    if template.template_id == "edf_elec_v1":
        return parse_edf_elec(text, source_file)
    elif template.template_id == "engie_elec_v1":
        return parse_engie_elec(text, source_file)
    elif template.template_id == "engie_gaz_v1":
        return parse_engie_gaz(text, source_file)
    else:
        raise ValueError(f"Template {template.template_id} has no parser implementation")


def parse_pdf_file(file_path: str) -> Invoice:
    """
    Extract text from a PDF file and parse it.
    """
    text = extract_text_from_pdf(file_path)
    return parse_pdf_text(text, source_file=file_path)


def list_templates() -> List[Dict[str, Any]]:
    """List available PDF templates."""
    return [
        {
            "template_id": t.template_id,
            "supplier_pattern": t.supplier_pattern,
            "energy_type": t.energy_type.value,
            "description": t.description,
        }
        for t in TEMPLATES
    ]
