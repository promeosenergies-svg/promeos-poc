#!/usr/bin/env python
"""
golden_build.py — Extract billing lines from French B2B electricity PDFs
and produce normalized JSON for golden tests.

Supplier-grade extraction: ENGIE elec + EDF elec.
Uses pymupdf (fitz) for text extraction + regex.

Usage:
    python tools/billing/golden_build.py <pdf_path>
    python tools/billing/golden_build.py <pdf_path> --output tests/billing_golden/expected/
    python tools/billing/golden_build.py --all --pdf-dir <dir> --output <dir>
"""

import json
import re
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

import fitz  # pymupdf


# ======================================================================
# Constants
# ======================================================================

CATEGORY_SUPPLY = "SUPPLY"
CATEGORY_NETWORK = "NETWORK"
CATEGORY_TAX = "TAX"

# Canonical tax_code mapping (label_source keywords → tax_code)
TAX_CODE_MAP = {
    "accise": "ACCISE_ELEC",
    "cspe": "ACCISE_ELEC",
    "ticfe": "ACCISE_ELEC",
    "contrib. service public": "ACCISE_ELEC",
    "contrib service public": "ACCISE_ELEC",
    "contribution tarifaire": "CTA",
    "cta": "CTA",
    "taxes locales": "TCFE",
    "taxe communale": "TCFE",
    "taxe departementale": "TCFE",
}


def resolve_tax_code(label: str) -> Optional[str]:
    """Map a tax line label to its canonical tax_code."""
    lower = label.lower()
    for key, code in TAX_CODE_MAP.items():
        if key in lower:
            return code
    return None


# ======================================================================
# Text extraction
# ======================================================================


def extract_text(pdf_path: str) -> str:
    """Extract text from PDF using pymupdf/fitz."""
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def extract_pages(pdf_path: str) -> List[str]:
    """Extract text per page."""
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return pages


# ======================================================================
# Helpers
# ======================================================================


def parse_fr_float(s: str) -> Optional[float]:
    """Parse French-format float: '1 542,27' → 1542.27, '-17,90' → -17.9"""
    if s is None:
        return None
    s = s.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_fr_date(s: str) -> Optional[str]:
    """Parse French date dd/mm/yyyy or dd/mm/yy → ISO yyyy-mm-dd."""
    if s is None:
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def find_float(text: str, pattern: str) -> Optional[float]:
    """Extract a float from text using regex."""
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return parse_fr_float(m.group(1))
    return None


def find_str(text: str, pattern: str) -> Optional[str]:
    """Extract a string from text using regex."""
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def detect_supplier(text: str) -> str:
    """Detect the supplier from PDF text."""
    if re.search(r"\bEDF\b", text):
        return "EDF"
    if re.search(r"\bENGIE\b", text):
        return "ENGIE"
    if re.search(r"TotalEnergies|Total\s*[EÉ\xc9]nergies?", text, re.IGNORECASE):
        return "TOTALENERGIES"
    return "UNKNOWN"


# ======================================================================
# ENGIE Electricity Parser
# ======================================================================


def parse_engie_elec(text: str, pages: List[str], source_file: str) -> Dict[str, Any]:
    """Parse ENGIE electricity invoice → normalized JSON."""

    # --- Invoice meta ---
    invoice_id = find_str(text, r"N[°\u00b0]+\s*(\d+)")
    pdl = find_str(text, r"Point de livraison\s*:\s*(\d{14})")
    invoice_date = find_str(text, r"facture du (\d{1,2}\s+\w+\s+\d{4})")
    # Try numeric date format too
    invoice_date_iso = None
    m = re.search(r"facture du (\d{2}/\d{2}/\d{2,4})", text, re.IGNORECASE)
    if m:
        invoice_date_iso = parse_fr_date(m.group(1))
    if not invoice_date_iso:
        # Parse French month name
        months_fr = {
            "janvier": "01", "f\xe9vrier": "02", "fevrier": "02", "mars": "03",
            "avril": "04", "mai": "05", "juin": "06", "juillet": "07",
            "ao\xfbt": "08", "aout": "08", "septembre": "09", "octobre": "10",
            "novembre": "11", "d\xe9cembre": "12", "decembre": "12",
        }
        m = re.search(r"facture du (\d{1,2})\s+(\w+)\s+(\d{4})", text, re.IGNORECASE)
        if m:
            day, month_name, year = m.group(1), m.group(2).lower(), m.group(3)
            mm = months_fr.get(month_name)
            if mm:
                invoice_date_iso = f"{year}-{mm}-{day.zfill(2)}"

    # Period
    period_m = re.search(r"du (\d{2}/\d{2}/\d{2,4}) au (\d{2}/\d{2}/\d{2,4})", text)
    period_start = parse_fr_date(period_m.group(1)) if period_m else None
    period_end = parse_fr_date(period_m.group(2)) if period_m else None

    # Segment / puissance
    segment = find_str(text, r"Segment\s+(C\d)")
    puissance_kva = find_float(text, r"Puissance souscrite\s+(\d+)\s*kVA")

    # Client
    client = find_str(text, r"Lieu de consommation\s*:\s*\n\s*(\S+)")
    if not client:
        client = find_str(text, r"4Lieu de consommation\s*:\s*\n\s*(\S+)")

    # --- Page 1 category totals ---
    supply_ht = find_float(text, r"[<\u00e9\xe9]lectricit[eé\xe9]\s*(?::\s*)?\n?\s*([\d\s,.]+)\s*\u20ac")
    if supply_ht is None:
        supply_ht = find_float(text, r"[Ee]lectricit[eé]\s*:?\s*\n?\s*([\d\s,.]+)\s*\u20ac")
    network_ht = find_float(text, r"acheminement\s*\n?\s*([\d\s,.]+)\s*\u20ac")
    taxes_ht = find_float(text, r"Taxes et contributions\s*\n?\s*([\d\s,.]+)\s*\u20ac")
    htva = find_float(text, r"total HTVA\s*\n?\s*([\d\s,.]+)\s*\u20ac")
    ttc = find_float(text, r"total TTC\s*\n?\s*([\d\s,.]+)\s*\u20ac")

    # TVA breakdown from page 1
    vat_breakdown = []
    for vm in re.finditer(r"TVA\s+[àa\xe0]\s+([\d,.]+)\s*%\s+calcul[eé\xe9]e sur\s+([\d\s,.]+)\s*\u20ac\s*\n?\s*([\d\s,.]+)\s*\u20ac", text):
        vat_breakdown.append({
            "rate": parse_fr_float(vm.group(1)),
            "base": parse_fr_float(vm.group(2)),
            "amount": parse_fr_float(vm.group(3)),
        })

    # --- Detail lines from page 2+ ---
    lines = []

    # Find section boundaries in text
    detail_text = "\n".join(pages[1:]) if len(pages) > 1 else text

    # Split into sections: Électricité, Acheminement, Taxes et Contributions
    elec_section = _extract_section(detail_text, r"Electricit", r"Acheminement")
    network_section = _extract_section(detail_text, r"Acheminement", r"Taxes et Contributions")
    tax_section = _extract_section(detail_text, r"Taxes et Contributions", r"Services et prestations|Total de votre facture")

    # Parse SUPPLY lines from Électricité section
    lines.extend(_parse_engie_section_lines(elec_section, CATEGORY_SUPPLY))

    # Parse NETWORK lines from Acheminement section
    lines.extend(_parse_engie_section_lines(network_section, CATEGORY_NETWORK))

    # Parse TAX lines from Taxes section
    lines.extend(_parse_engie_tax_lines(tax_section))

    return {
        "invoice_meta": {
            "supplier": "ENGIE",
            "invoice_id": invoice_id,
            "pdl": pdl,
            "invoice_date": invoice_date_iso,
            "period_start": period_start,
            "period_end": period_end,
            "segment": segment,
            "puissance_kva": int(puissance_kva) if puissance_kva else None,
            "client": client,
            "source_file": os.path.basename(source_file),
        },
        "totals": {
            "supply_ht": supply_ht,
            "network_ht": network_ht,
            "taxes_ht": taxes_ht,
            "htva": htva,
            "vat_breakdown": vat_breakdown,
            "ttc": ttc,
        },
        "lines": lines,
    }


def _extract_section(text: str, start_pattern: str, end_pattern: str) -> str:
    """Extract text between two section markers.
    The end marker is searched AFTER the start marker position.
    """
    m_start = re.search(start_pattern, text, re.IGNORECASE)
    if m_start is None:
        return ""
    start = m_start.start()
    # Search for end AFTER start
    m_end = re.search(end_pattern, text[start + 1:], re.IGNORECASE)
    end = (start + 1 + m_end.start()) if m_end else len(text)
    return text[start:end]


def _parse_engie_section_lines(section: str, category: str) -> List[Dict]:
    """Parse ENGIE billing lines from a section (Électricité or Acheminement).

    ENGIE line patterns in fitz text:
    - "Label du DD/MM/YY au DD/MM/YY\\nQty\\nUnit_price\\nAmount\\nTVA_rate"
    - "Label du DD/MM/YY au DD/MM/YY\\nAmount\\nTVA_rate" (no qty/price for abo)
    """
    lines = []
    # Match lines with period and amount
    # Pattern: label + period + optional qty/price + amount + TVA rate
    for m in re.finditer(
        r"^(.+?)\s+du\s+(\d{2}/\d{2}/\d{2,4})\s+au\s+(\d{2}/\d{2}/\d{2,4})\s*$",
        section, re.MULTILINE
    ):
        label = m.group(1).strip()
        period_start = parse_fr_date(m.group(2))
        period_end = parse_fr_date(m.group(3))

        # Skip table header lines
        if any(kw in label.lower() for kw in ["compteur", "index", "taux de"]):
            continue

        # Skip "Consommation" header in network section — it's a sub-header
        # for the HP/HC lines that follow (which are parsed separately)
        if category == CATEGORY_NETWORK and label.lower().startswith("consommation"):
            continue

        # Get the text after this match to find amount/qty/price
        after = section[m.end():]
        after_lines = [l.strip() for l in after.split("\n") if l.strip()][:8]

        qty, unit_price, amount_ht, vat_rate = None, None, None, None
        subtype = _guess_subtype(label, category)

        # Parse the numeric values after the label line
        nums = []
        for al in after_lines:
            # Stop at next label line (starts with letter and has "du DD/MM")
            if re.match(r"[A-Z]", al) and "du " in al:
                break
            # Stop at HP/HC sub-section headers
            if re.match(r"^Heures\s+", al):
                break
            if re.match(r"^[\d,.%-]+$", al):
                nums.append(al)
            elif re.match(r"^\d+$", al):
                nums.append(al)

        if nums:
            # Last numeric before % is amount_ht, last with % is TVA
            vat_idx = None
            for i, n in enumerate(nums):
                if "%" in n:
                    vat_idx = i
                    vat_rate = parse_fr_float(n.replace("%", ""))
                    break

            if vat_idx is not None:
                amount_candidates = nums[:vat_idx]
            else:
                amount_candidates = nums

            if len(amount_candidates) >= 3:
                # qty, unit_price, amount
                qty = parse_fr_float(amount_candidates[-3])
                unit_price = parse_fr_float(amount_candidates[-2])
                amount_ht = parse_fr_float(amount_candidates[-1])
            elif len(amount_candidates) >= 1:
                amount_ht = parse_fr_float(amount_candidates[-1])
                if len(amount_candidates) >= 2:
                    # Could be qty+amount or price+amount
                    candidate = parse_fr_float(amount_candidates[-2])
                    if candidate and candidate > 10:  # likely qty (kWh)
                        qty = candidate

        # Skip 0.00 amount lines
        if amount_ht == 0.0 and "taxes locales" not in label.lower():
            continue

        line = {
            "category": category,
            "subtype": subtype,
            "label_source": label,
            "tax_code": None,
            "period_start": period_start,
            "period_end": period_end,
            "qty": qty,
            "unit": "kWh" if qty and qty > 1 else None,
            "unit_price": unit_price,
            "amount_ht": amount_ht,
            "vat_rate": vat_rate,
        }
        lines.append(line)

    # Also match lines WITHOUT period (like "Heures pleines saison haute")
    for m in re.finditer(
        r"^(Heures\s+(?:pleines|creuses)\s+saison\s+\w+)\s*$",
        section, re.MULTILINE
    ):
        label = m.group(1).strip()
        after = section[m.end():]
        after_lines = [l.strip() for l in after.split("\n") if l.strip()][:10]

        qty, unit_price, amount_ht, vat_rate = None, None, None, None
        subtype = _guess_subtype(label, category)

        nums = []
        for al in after_lines:
            if re.match(r"[A-Z]", al) and ("du " in al or al.startswith("Heures")):
                break
            if re.match(r"^[\d,.%-]+$", al):
                nums.append(al)

        if nums:
            vat_idx = None
            for i, n in enumerate(nums):
                if "%" in n:
                    vat_idx = i
                    vat_rate = parse_fr_float(n.replace("%", ""))
                    break

            amount_candidates = nums[:vat_idx] if vat_idx is not None else nums

            if len(amount_candidates) >= 3:
                # Filter: meter number, old index, new index, qty, price, amount
                # For ENGIE the format is: meter_no, old_idx, new_idx, qty, price, amount
                # We want the last 3: qty, price, amount
                qty = parse_fr_float(amount_candidates[-3])
                unit_price = parse_fr_float(amount_candidates[-2])
                amount_ht = parse_fr_float(amount_candidates[-1])

        if amount_ht is not None:
            lines.append({
                "category": category,
                "subtype": subtype,
                "label_source": label,
                "tax_code": None,
                "period_start": None,
                "period_end": None,
                "qty": qty,
                "unit": "kWh" if qty and qty > 1 else None,
                "unit_price": unit_price,
                "amount_ht": amount_ht,
                "vat_rate": vat_rate,
            })

    return lines


def _parse_engie_tax_lines(section: str) -> List[Dict]:
    """Parse ENGIE tax lines (CTA, CSPE/Accise, Taxes locales)."""
    lines = []

    # CTA lines: "Contribution tarifaire d'acheminement (8,53 € x 0,2193)"
    for m in re.finditer(
        r"(Contribution tarifaire d'acheminement)\s*\(([\d,.]+)\s*\u20ac?\s*x\s*([\d,.]+)\)",
        section
    ):
        label = m.group(0)
        base = parse_fr_float(m.group(2))
        rate = parse_fr_float(m.group(3))
        # Get amount from lines after
        after = section[m.end():]
        after_lines = [l.strip() for l in after.split("\n") if l.strip()][:4]
        amount_ht, vat_rate = None, None
        for al in after_lines:
            if re.match(r"^[\d,.]+$", al) and amount_ht is None:
                amount_ht = parse_fr_float(al)
            elif "%" in al:
                vat_rate = parse_fr_float(al.replace("%", ""))
                break

        lines.append({
            "category": CATEGORY_TAX,
            "subtype": "CTA",
            "label_source": f"Contribution tarifaire d'acheminement ({m.group(2)} \u20ac x {m.group(3)})",
            "tax_code": "CTA",
            "period_start": None,
            "period_end": None,
            "qty": base,
            "unit": "EUR",
            "unit_price": rate,
            "amount_ht": amount_ht,
            "vat_rate": vat_rate,
        })

    # Taxes locales
    for m in re.finditer(
        r"(Taxes locales[^\n]*)",
        section
    ):
        label = m.group(1).strip()
        after = section[m.end():]
        after_lines = [l.strip() for l in after.split("\n") if l.strip()][:4]
        amount_ht, vat_rate = None, None
        for al in after_lines:
            if re.match(r"^[\d,.]+$", al) and amount_ht is None:
                val = parse_fr_float(al)
                if val is not None and val < 100:
                    amount_ht = val
            elif "%" in al:
                vat_rate = parse_fr_float(al.replace("%", ""))
                break

        lines.append({
            "category": CATEGORY_TAX,
            "subtype": "TCFE",
            "label_source": label,
            "tax_code": "TCFE",
            "period_start": None,
            "period_end": None,
            "qty": None,
            "unit": None,
            "unit_price": None,
            "amount_ht": amount_ht,
            "vat_rate": vat_rate,
        })

    # CSPE / Contrib. service public élec
    for m in re.finditer(
        r"(Contrib\.\s*service public [eé\xe9]lec)\s+du\s+(\d{2}/\d{2}/\d{2,4})\s+au\s+(\d{2}/\d{2}/\d{2,4})",
        section
    ):
        label = m.group(1).strip()
        period_start = parse_fr_date(m.group(2))
        period_end = parse_fr_date(m.group(3))

        after = section[m.end():]
        after_lines = [l.strip() for l in after.split("\n") if l.strip()][:6]
        qty, unit_price, amount_ht, vat_rate = None, None, None, None
        nums = []
        for al in after_lines:
            if re.match(r"[A-Z]", al):
                break
            if re.match(r"^[\d,.%-]+$", al):
                nums.append(al)

        if nums:
            vat_idx = None
            for i, n in enumerate(nums):
                if "%" in n:
                    vat_idx = i
                    vat_rate = parse_fr_float(n.replace("%", ""))
                    break
            amount_candidates = nums[:vat_idx] if vat_idx is not None else nums
            if len(amount_candidates) >= 3:
                qty = parse_fr_float(amount_candidates[0])
                unit_price = parse_fr_float(amount_candidates[1])
                amount_ht = parse_fr_float(amount_candidates[2])
            elif len(amount_candidates) >= 1:
                amount_ht = parse_fr_float(amount_candidates[-1])

        lines.append({
            "category": CATEGORY_TAX,
            "subtype": "ACCISE_ELEC",
            "label_source": f"{label} du {m.group(2)} au {m.group(3)}",
            "tax_code": "ACCISE_ELEC",
            "period_start": period_start,
            "period_end": period_end,
            "qty": qty,
            "unit": "kWh",
            "unit_price": unit_price,
            "amount_ht": amount_ht,
            "vat_rate": vat_rate,
        })

    return lines


def _guess_subtype(label: str, category: str) -> str:
    """Guess subtype from label text."""
    lower = label.lower()
    if "abonnement" in lower:
        return "ABONNEMENT"
    if "heures pleines" in lower or "hp" in lower:
        return "CONSO_HP"
    if "heures creuses" in lower or "hc" in lower:
        return "CONSO_HC"
    if "consommation" in lower and "base" in lower:
        return "CONSO_BASE"
    if "consommation" in lower:
        return "CONSO"
    if "garanties" in lower or "origine" in lower:
        return "GARANTIES_ORIGINE"
    if "obligations" in lower:
        return "OBLIGATIONS_ENV"
    return "OTHER"


# ======================================================================
# EDF Electricity Parser
# ======================================================================


def parse_edf_elec(text: str, pages: List[str], source_file: str) -> Dict[str, Any]:
    """Parse EDF electricity invoice → normalized JSON."""

    # --- Invoice meta ---
    invoice_id = find_str(text, r"n[°\u00b0]\s*(\d+)")
    pdl = find_str(text, r"[Rr][eé\xe9]f(?:\.|[eé\xe9]rence)?\s+[Aa]cheminement\s*(?:[Ee]lectricit[eé\xe9])?\s*:\s*(\d{14})")
    invoice_date_str = find_str(text, r"Facture du\s+(\d{2}/\d{2}/\d{4})")
    invoice_date_iso = parse_fr_date(invoice_date_str) if invoice_date_str else None

    # Contract
    contract_ref = find_str(text, r"R[eé\xe9]f\.\s+de votre contrat\s+(\S+)")

    # Segment / puissance
    segment = find_str(text, r"Acheminement\s*:\s*Tarif\s+(.+?)(?:\n|$)")
    puissance = find_float(text, r"Puissance souscrite (?:actuelle\s+)?\(kW ou kVA\)\s*:\s*(\d+)")

    # Client
    client = find_str(text, r"Nom du client\s*\n\s*(.+)")

    # --- Category totals ---
    supply_ht = find_float(text, r"Total EDF Electricit[eé\xe9]\s*(?:\n\s*I\s*\n)?\s*([\d\s,.]+)\s*\u20ac")
    if supply_ht is None:
        supply_ht = find_float(text, r"Total EDF Electricit[eé\xe9]\s*\n\s*\w?\s*\n?\s*([\d\s,.]+)\s*\u20ac")
    network_ht = find_float(text, r"Utilisation du r[eé\xe9]seau[^\n]*\n\s*([\d\s,.]+)\s*\u20ac")
    # Taxes amount appears AFTER the "Taxes et contributions" label
    taxes_ht = find_float(text, r"Taxes et contributions[^\n]*\n\s*([\d\s,.]+)\s*\u20ac")
    if taxes_ht is None:
        taxes_ht = find_float(text, r"([\d\s,.]+)\s*\u20ac\s*\nTaxes et contributions")

    # Services / Divers (non-energy items included in Total HT)
    services_ht = find_float(text, r"Services\s*\(HT\)\s*\n\s*([\d\s,.]+)\s*\u20ac")
    divers_ht = find_float(text, r"Divers\s*\(HT\)\s*\n\s*([\d\s,.]+)\s*\u20ac")
    other_ht = round((services_ht or 0) + (divers_ht or 0), 2) or None

    # Global totals
    htva = find_float(text, r"(?:Montant Hors TVA|Total Hors TVA[^\n]*)\s*\n?\s*([\d\s,.]+)\s*\u20ac")
    total_tva = find_float(text, r"Montant TVA[^\n]*\n?\s*([\d\s,.]+)\s*\u20ac")
    ttc = find_float(text, r"Facture TTC\s*\n?\s*([\d\s,.]+)\s*\u20ac")
    if ttc is None:
        ttc = find_float(text, r"Montant total [àa\xe0] payer \(TTC\)\s*\n?\s*([\d\s,.]+)\s*\u20ac")

    # TVA breakdown
    vat_breakdown = []
    for vm in re.finditer(r"TVA [àa\xe0]\s+([\d,.]+)\s*%\s*\n?\s*([\d\s,.]+)\s*\u20ac\s*\n?\s*([\d\s,.]+)\s*\u20ac", text):
        vat_breakdown.append({
            "rate": parse_fr_float(vm.group(1)),
            "base": parse_fr_float(vm.group(2)),
            "amount": parse_fr_float(vm.group(3)),
        })

    # --- Period from consumption lines only (exclude Echoir advance periods) ---
    period_start, period_end = None, None
    # Look for periods in the supply/consumption section only
    supply_text = _extract_section(text, r"Total EDF Electricit", r"Utilisation du r")
    conso_periods = re.findall(r"du\s+(\d{2}/\d{2}/\d{4})\s+au\s+(\d{2}/\d{2}/\d{4})", supply_text)
    if conso_periods:
        all_starts = [parse_fr_date(p[0]) for p in conso_periods if parse_fr_date(p[0])]
        all_ends = [parse_fr_date(p[1]) for p in conso_periods if parse_fr_date(p[1])]
        if all_starts:
            period_start = min(all_starts)
        if all_ends:
            period_end = max(all_ends)

    # Consumption
    conso_kwh = find_float(text, r"Conso\s+([\d\s,.]+)\s*kWh")

    # --- Detail lines ---
    lines = []
    detail_text = "\n".join(pages[1:]) if len(pages) > 1 else text

    # ---- SUPPLY lines ----
    supply_section = _extract_section(detail_text,
                                       r"Total EDF Electricit",
                                       r"Utilisation du r[eé\xe9]seau")
    lines.extend(_parse_edf_supply_lines(supply_section))

    # ---- NETWORK lines ----
    network_section = _extract_section(detail_text,
                                        r"Utilisation du r[eé\xe9]seau",
                                        r"(?:Services|Taxes et contributions)")
    lines.extend(_parse_edf_network_lines(network_section))

    # ---- TAX lines ----
    # Search entire detail text — EDF may have a summary "Taxes et contributions"
    # on page 2 AND a detail section on page 4. The specific regex patterns
    # (period + qty + price) prevent false matches.
    lines.extend(_parse_edf_tax_lines(detail_text))

    return {
        "invoice_meta": {
            "supplier": "EDF",
            "invoice_id": invoice_id,
            "pdl": pdl,
            "invoice_date": invoice_date_iso,
            "period_start": period_start,
            "period_end": period_end,
            "segment": segment.strip() if segment else None,
            "puissance_kva": int(puissance) if puissance else None,
            "client": client,
            "contract_ref": contract_ref,
            "source_file": os.path.basename(source_file),
        },
        "totals": {
            "supply_ht": supply_ht,
            "network_ht": network_ht,
            "taxes_ht": taxes_ht,
            "other_ht": other_ht,
            "htva": htva,
            "vat_breakdown": vat_breakdown,
            "ttc": ttc,
        },
        "lines": lines,
    }


def _parse_edf_supply_lines(section: str) -> List[Dict]:
    """Parse EDF supply lines (Abonnement + Consommation HP/HC/Pointe)."""
    lines = []

    # Abonnement line: "Abonnement\ndu DD/MM/YYYY au DD/MM/YYYY\nprice/mois\namount\nTVA%"
    m = re.search(
        r"Abonnement\s*\n\s*du\s+(\d{2}/\d{2}/\d{4})\s+au\s+(\d{2}/\d{2}/\d{4})\s*\n\s*([\d\s,.]+)\s*\u20ac/mois\s*\n\s*([\d\s,.]+)\s*\u20ac\s*\n\s*([\d,.]+)\s*%",
        section
    )
    if m:
        lines.append({
            "category": CATEGORY_SUPPLY,
            "subtype": "ABONNEMENT",
            "label_source": "Abonnement",
            "tax_code": None,
            "period_start": parse_fr_date(m.group(1)),
            "period_end": parse_fr_date(m.group(2)),
            "qty": 1,
            "unit": "mois",
            "unit_price": parse_fr_float(m.group(3)),
            "amount_ht": parse_fr_float(m.group(4)),
            "vat_rate": parse_fr_float(m.group(5)),
        })

    # Consumption lines: "Électricité Heures Pleines Été\ndu DD/MM/YYYY au DD/MM/YYYY\nQty kWh\nprice c€/kWh\namount €\nTVA%"
    for m in re.finditer(
        r"(Electricit[eé\xe9]\s+Heures\s+(?:Pleines|Creuses)\s+[EéÉ\xe9]t[eé\xe9])\s*\n\s*du\s+(\d{2}/\d{2}/\d{4})\s+au\s+(\d{2}/\d{2}/\d{4})\s*\n\s*([\d\s,.]+)\s*kWh\s*\n\s*([\d\s,.]+)\s*c\u20ac/kWh\s*\n\s*([\d\s,.]+)\s*\u20ac\s*\n\s*([\d,.]+)\s*%",
        section
    ):
        label = m.group(1).strip()
        subtype = "CONSO_HP" if "Pleines" in label else "CONSO_HC"
        lines.append({
            "category": CATEGORY_SUPPLY,
            "subtype": subtype,
            "label_source": label,
            "tax_code": None,
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": parse_fr_float(m.group(4)),
            "unit": "kWh",
            "unit_price": round(parse_fr_float(m.group(5)) / 100, 6) if parse_fr_float(m.group(5)) else None,  # c€ → €
            "amount_ht": parse_fr_float(m.group(6)),
            "vat_rate": parse_fr_float(m.group(7)),
        })

    return lines


def _parse_edf_network_lines(section: str) -> List[Dict]:
    """Parse EDF network lines (TURPE: gestion, comptage, soutirage, dépassement).

    Handles Reprise (negative), Echu, Echoir patterns.
    """
    lines = []

    # Pattern 1: Reprise lines (negative, no qty/price)
    for m in re.finditer(
        r"(Composante\s+de\s+\w+(?:\s+\w+)*\s*-\s*Reprise)\s*\n\s*du\s+(\d{2}/\d{2}/\d{4})\s+au\s+(\d{2}/\d{2}/\d{4})\s*\n\s*(?:PS[^\n]*\n\s*)?(-?[\d\s,.]+)\s*\u20ac\s*\n\s*([\d,.]+)\s*%",
        section
    ):
        label = m.group(1).strip()
        lines.append({
            "category": CATEGORY_NETWORK,
            "subtype": _turpe_subtype(label),
            "label_source": label,
            "tax_code": None,
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": None,
            "unit": None,
            "unit_price": None,
            "amount_ht": parse_fr_float(m.group(4)),
            "vat_rate": parse_fr_float(m.group(5)),
        })

    # Pattern 2: Echu/Echoir lines (with qty and unit price)
    for m in re.finditer(
        r"(Composante\s+de\s+\w+(?:\s+\w+)*\s*-\s*(?:Echu|Echoir))\s*\n\s*du\s+(\d{2}/\d{2}/\d{4})\s+au\s+(\d{2}/\d{2}/\d{4})\s*\n\s*([\d\s,.]+)\s*(\w+(?:\.\w+)?)\s*\n\s*([\d\s,.]+)\s*c\u20ac/\w+(?:\.\w+)?\s*\n\s*([\d\s,.]+)\s*\u20ac\s*\n\s*([\d,.]+)\s*%",
        section
    ):
        label = m.group(1).strip()
        unit_raw = m.group(5).strip()
        # Map units: c.j → c.j, p.j → p.j, kW → kW, kWh → kWh
        lines.append({
            "category": CATEGORY_NETWORK,
            "subtype": _turpe_subtype(label),
            "label_source": label,
            "tax_code": None,
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": parse_fr_float(m.group(4)),
            "unit": unit_raw,
            "unit_price": round(parse_fr_float(m.group(6)) / 100, 6) if parse_fr_float(m.group(6)) else None,  # c€ → €
            "amount_ht": parse_fr_float(m.group(7)),
            "vat_rate": parse_fr_float(m.group(8)),
        })

    # Pattern 3: Soutirage variable lines (Pointe, HPH, HCH, HPE, HCE)
    for m in re.finditer(
        r"(Composante\s+de\s+soutirage\s+(?:Pointe|Heures\s+(?:Pleines|Creuses)\s+(?:Hiver|[EéÉ\xe9]t[eé\xe9])))\s*\n\s*du\s+(\d{2}/\d{2}/\d{4})\s+au\s+(\d{2}/\d{2}/\d{4})\s*\n\s*([\d\s,.]+)\s*kWh\s*\n\s*([\d\s,.]+)\s*c\u20ac/kWh\s*\n\s*([\d\s,.]+)\s*\u20ac\s*\n\s*([\d,.]+)\s*%",
        section
    ):
        label = m.group(1).strip()
        lines.append({
            "category": CATEGORY_NETWORK,
            "subtype": _turpe_soutirage_subtype(label),
            "label_source": label,
            "tax_code": None,
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": parse_fr_float(m.group(4)),
            "unit": "kWh",
            "unit_price": round(parse_fr_float(m.group(5)) / 100, 6) if parse_fr_float(m.group(5)) else None,
            "amount_ht": parse_fr_float(m.group(6)),
            "vat_rate": parse_fr_float(m.group(7)),
        })

    # Pattern 4: Dépassement
    for m in re.finditer(
        r"(Dur[eé\xe9]e de d[eé\xe9]passement)\s*\n\s*du\s+(\d{2}/\d{2}/\d{4})\s+au\s+(\d{2}/\d{2}/\d{4})\s*\n\s*([\d\s,.]+)\s*h\s*\n\s*([\d\s,.]+)\s*c\u20ac/h\s*\n\s*([\d\s,.]+)\s*\u20ac\s*\n\s*([\d,.]+)\s*%",
        section
    ):
        label = m.group(1).strip()
        lines.append({
            "category": CATEGORY_NETWORK,
            "subtype": "DEPASSEMENT",
            "label_source": label,
            "tax_code": None,
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": parse_fr_float(m.group(4)),
            "unit": "h",
            "unit_price": round(parse_fr_float(m.group(5)) / 100, 6) if parse_fr_float(m.group(5)) else None,
            "amount_ht": parse_fr_float(m.group(6)),
            "vat_rate": parse_fr_float(m.group(7)),
        })

    return lines


def _parse_edf_tax_lines(section: str) -> List[Dict]:
    """Parse EDF tax lines (Accise, CTA)."""
    lines = []

    # Accise sur l'électricité — case-insensitive, handles É/é and various apostrophes
    m = re.search(
        r"(Accise sur l.[eéÉ\xe9\xc9]lectricit[eéÉ\xe9\xc9])\s*\n\s*du\s+(\d{2}/\d{2}/\d{4})\s+au\s+(\d{2}/\d{2}/\d{4})\s*\n\s*([\d\s,.]+)\s*kWh\s*\n\s*([\d\s,.]+)\s*c\u20ac/kWh\s*\n\s*([\d\s,.]+)\s*\u20ac\s*\n\s*([\d,.]+)\s*%",
        section
    )
    if m:
        lines.append({
            "category": CATEGORY_TAX,
            "subtype": "ACCISE_ELEC",
            "label_source": m.group(1).strip(),
            "tax_code": "ACCISE_ELEC",
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": parse_fr_float(m.group(4)),
            "unit": "kWh",
            "unit_price": round(parse_fr_float(m.group(5)) / 100, 6) if parse_fr_float(m.group(5)) else None,
            "amount_ht": parse_fr_float(m.group(6)),
            "vat_rate": parse_fr_float(m.group(7)),
        })

    # CTA
    m = re.search(
        r"(Contribution Tarifaire d.Acheminement)\s*\n\s*du\s+(\d{2}/\d{2}/\d{4})\s+au\s+(\d{2}/\d{2}/\d{4})\s*\n\s*([\d\s,.]+)\s*\n\s*([\d\s,.]+)\s*%\s*\n\s*([\d\s,.]+)\s*\u20ac\s*\n\s*([\d,.]+)\s*%",
        section
    )
    if m:
        lines.append({
            "category": CATEGORY_TAX,
            "subtype": "CTA",
            "label_source": m.group(1).strip(),
            "tax_code": "CTA",
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": parse_fr_float(m.group(4)),
            "unit": "EUR",
            "unit_price": round(parse_fr_float(m.group(5)) / 100, 6) if parse_fr_float(m.group(5)) else None,
            "amount_ht": parse_fr_float(m.group(6)),
            "vat_rate": parse_fr_float(m.group(7)),
        })

    return lines


def _turpe_subtype(label: str) -> str:
    """Map TURPE component label to subtype."""
    lower = label.lower()
    if "gestion" in lower:
        return "TURPE_GESTION"
    if "comptage" in lower:
        return "TURPE_COMPTAGE"
    if "soutirage fixe" in lower:
        return "TURPE_SOUTIRAGE_FIXE"
    if "soutirage" in lower:
        return "TURPE_SOUTIRAGE_VAR"
    return "TURPE_OTHER"


def _turpe_soutirage_subtype(label: str) -> str:
    """Map soutirage variable label to specific subtype."""
    lower = label.lower()
    if "pointe" in lower:
        return "TURPE_SOUTIRAGE_P"
    if "pleines" in lower and "hiver" in lower:
        return "TURPE_SOUTIRAGE_HPH"
    if "creuses" in lower and "hiver" in lower:
        return "TURPE_SOUTIRAGE_HCH"
    if "pleines" in lower:
        return "TURPE_SOUTIRAGE_HPE"
    if "creuses" in lower:
        return "TURPE_SOUTIRAGE_HCE"
    return "TURPE_SOUTIRAGE_VAR"


# ======================================================================
# TotalEnergies Electricity Parser
# ======================================================================


def parse_total_elec(text: str, pages: List[str], source_file: str) -> Dict[str, Any]:
    """Parse TotalEnergies electricity invoice -> normalized JSON."""

    # --- Invoice meta ---
    invoice_id = find_str(text, r"N[°\u00b0]\s*(\d+)")
    pdl = find_str(text, r"PDL\s*:\s*(\d{14})")
    invoice_date_str = find_str(text, r"Date de facture\s*:\s*(\d{2}/\d{2}/\d{2,4})")
    invoice_date_iso = parse_fr_date(invoice_date_str) if invoice_date_str else None
    if not invoice_date_iso:
        # Try "FACTURE D'ELECTRICITE du DD mois YYYY"
        months_fr = {
            "janvier": "01", "f\xe9vrier": "02", "fevrier": "02", "mars": "03",
            "avril": "04", "mai": "05", "juin": "06", "juillet": "07",
            "ao\xfbt": "08", "aout": "08", "septembre": "09", "octobre": "10",
            "novembre": "11", "d\xe9cembre": "12", "decembre": "12",
        }
        m = re.search(r"FACTURE.*du (\d{1,2})\s+(\w+)\s+(\d{4})", text, re.IGNORECASE)
        if m:
            mm = months_fr.get(m.group(2).lower())
            if mm:
                invoice_date_iso = f"{m.group(3)}-{mm}-{m.group(1).zfill(2)}"

    # Period
    period_m = re.search(r"FACTURATION PERIODE DU\s+(\d{2}/\d{2}/\d{4})\s+AU\s+(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    period_start = parse_fr_date(period_m.group(1)) if period_m else None
    period_end = parse_fr_date(period_m.group(2)) if period_m else None

    segment = find_str(text, r"Segment\s*:\s*(\w+)")
    puissance = find_float(text, r"Puissance pond[eé\xe9]r[eé\xe9]e\s*[\n:]\s*([\d,.]+)")
    client = find_str(text, r"Titulaire contrat\s*:\s*(.+)")

    # --- Page 1 totals ---
    supply_ht = find_float(text, r"Fourniture d.[eé\xe9]lectricit[eé\xe9]\s*\n\s*([\d\s,.]+)\s*\u20ac")
    network_ht = find_float(text, r"Transport,?\s*Acheminement\s*\n\s*([\d\s,.]+)\s*\u20ac")
    taxes_ht = find_float(text, r"Taxes et contributions\s*\n\s*([\d\s,.]+)\s*\u20ac")
    if taxes_ht is None:
        taxes_ht = find_float(text, r"Taxes et contributions \(HT\)\s*\n?\s*([\d\s,.]+)\s*\u20ac")
    htva = find_float(text, r"Total hors TVA\s*\n\s*([\d\s,.]+)\s*\u20ac")
    ttc = find_float(text, r"Montant TTC\s*\n\s*([\d\s,.]+)\s*\u20ac")

    vat_breakdown = []
    for vm in re.finditer(r"TVA [àa\xe0]\s*([\d,.]+)\s*%\s+(?:sur le montant de\s+)?([\d\s,.]+)\s*\u20ac\s*\n\s*([\d\s,.]+)\s*\u20ac", text):
        vat_breakdown.append({
            "rate": parse_fr_float(vm.group(1)),
            "base": parse_fr_float(vm.group(2)),
            "amount": parse_fr_float(vm.group(3)),
        })

    # --- Detail lines from page 3 ---
    lines = []
    detail_text = "\n".join(pages[2:]) if len(pages) > 2 else text

    # SUPPLY: Energie active lines (case-insensitive: "hiver" vs "Hiver" varies)
    for m in re.finditer(
        r"(Heures\s+(?:pleines|creuses)\s+(?:Hiver|[EéÉ\xe9\xc9]t[eé\xe9]))\s*\n\s*"
        r"(\d{2}/\d{2}/\d{2,4})\s+(\d{2}/\d{2}/\d{2,4})\s*\n?\s*"
        r"([\d\s,.]+)\s*kWh\s*\n?\s*([\d\s,.]+)\s*kWh\s*\n?\s*"
        r"([\d\s,.]+)\s*\u20ac/kWh\s*\n?\s*([\d\s,.]+)\s*\u20ac\s*\n?\s*(\d+)\s*%",
        detail_text, re.IGNORECASE
    ):
        label = m.group(1).strip()
        subtype = "CONSO_HP" if "pleines" in label.lower() else "CONSO_HC"
        lines.append({
            "category": CATEGORY_SUPPLY,
            "subtype": subtype,
            "label_source": label,
            "tax_code": None,
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": parse_fr_float(m.group(5)),  # facturé qty
            "unit": "kWh",
            "unit_price": parse_fr_float(m.group(6)),
            "amount_ht": parse_fr_float(m.group(7)),
            "vat_rate": parse_fr_float(m.group(8)),
        })

    # SUPPLY: Abonnement lines (Reprise/Echu/Echoir)
    for m in re.finditer(
        r"(Abonnement fournisseur\s+(?:Reprise|Echu|Echoir))\s*\n?\s*"
        r"(\d{2}/\d{2}/\d{2,4})\s+(\d{2}/\d{2}/\d{2,4})\s*\n?\s*"
        r"(?:\s*\n?\s*)*?"
        r"([\d,.]+)\s*\u20ac/an\s*\n?\s*(-?[\d\s,.]+)\s*\u20ac\s*\n?\s*(\d+)\s*%",
        detail_text
    ):
        label = m.group(1).strip()
        lines.append({
            "category": CATEGORY_SUPPLY,
            "subtype": "ABONNEMENT",
            "label_source": label,
            "tax_code": None,
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": 1,
            "unit": "an",
            "unit_price": parse_fr_float(m.group(4)),
            "amount_ht": parse_fr_float(m.group(5)),
            "vat_rate": parse_fr_float(m.group(6)),
        })

    # NETWORK: Composante de soutirage variable lines
    for m in re.finditer(
        r"(Composante de soutirage (?:variable\s+)?(?:Heures\s+(?:Pleines|Creuses)\s+(?:Hiver|[EéÉ\xe9\xc9]t[eé\xe9])))\s*\n?\s*"
        r"(\d{2}/\d{2}/\d{2,4})\s+(\d{2}/\d{2}/\d{2,4})\s*\n?\s*"
        r"([\d\s,.]+)\s*kWh\s*\n?\s*"
        r"([\d\s,.]+)\s*\u20ac/kWh\s*\n?\s*([\d\s,.]+)\s*\u20ac\s*\n?\s*(\d+)\s*%",
        detail_text
    ):
        label = m.group(1).strip()
        lines.append({
            "category": CATEGORY_NETWORK,
            "subtype": _turpe_soutirage_subtype(label),
            "label_source": label,
            "tax_code": None,
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": parse_fr_float(m.group(4)),
            "unit": "kWh",
            "unit_price": parse_fr_float(m.group(5)),
            "amount_ht": parse_fr_float(m.group(6)),
            "vat_rate": parse_fr_float(m.group(7)),
        })

    # NETWORK: Fixed TURPE components (gestion, comptage, soutirage fixe) — Reprise/Echu/Echoir
    for m in re.finditer(
        r"(Composante de (?:gestion|comptage|soutirage fixe)\s*-\s*(?:Reprise|Echu|Echoir))\s*\n?\s*"
        r"(\d{2}/\d{2}/\d{2,4})\s+(\d{2}/\d{2}/\d{2,4})\s*\n?\s*"
        r"(-?[\d\s,.]+)\s*(\w+(?:\.\w+)?)\s*\n?\s*"
        r"([\d\s,.]+)\s*\u20ac/\w+(?:\.\w+)?\s*\n?\s*(-?[\d\s,.]+)\s*\u20ac\s*\n?\s*(\d+)\s*%",
        detail_text
    ):
        label = m.group(1).strip()
        lines.append({
            "category": CATEGORY_NETWORK,
            "subtype": _turpe_subtype(label),
            "label_source": label,
            "tax_code": None,
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": parse_fr_float(m.group(4)),
            "unit": m.group(5).strip(),
            "unit_price": parse_fr_float(m.group(6)),
            "amount_ht": parse_fr_float(m.group(7)),
            "vat_rate": parse_fr_float(m.group(8)),
        })

    # TAX: CTA
    m = re.search(
        r"(Contribution Tarifaire d.Acheminement\s*\(CTA\))\s*\n?\s*"
        r"(\d{2}/\d{2}/\d{2,4})\s+(\d{2}/\d{2}/\d{2,4})\s*\n?\s*"
        r"(?:.*?\n?\s*)*?"
        r"([\d\s,.]+)\s*\u20ac\s*\n?\s*(\d+)\s*%",
        detail_text
    )
    if m:
        lines.append({
            "category": CATEGORY_TAX,
            "subtype": "CTA",
            "label_source": m.group(1).strip(),
            "tax_code": "CTA",
            "period_start": parse_fr_date(m.group(2)),
            "period_end": parse_fr_date(m.group(3)),
            "qty": None,
            "unit": None,
            "unit_price": None,
            "amount_ht": parse_fr_float(m.group(4)),
            "vat_rate": parse_fr_float(m.group(5)),
        })

    # TAX: CSPE (= ACCISE_ELEC)
    for m in re.finditer(
        r"(?:Contribution au Service Public|CSPE)[^\n]*\n?\s*"
        r"(\d{2}/\d{2}/\d{2,4})\s+(\d{2}/\d{2}/\d{2,4})\s*\n?\s*"
        r"([\d\s,.]+)\s*kWh\s*\n?\s*"
        r"([\d\s,.]+)\s*\u20ac/kWh\s*\n?\s*([\d\s,.]+)\s*\u20ac\s*\n?\s*(\d+)\s*%",
        detail_text
    ):
        lines.append({
            "category": CATEGORY_TAX,
            "subtype": "ACCISE_ELEC",
            "label_source": "Contribution au Service Public de l'Electricite (CSPE)",
            "tax_code": "ACCISE_ELEC",
            "period_start": parse_fr_date(m.group(1)),
            "period_end": parse_fr_date(m.group(2)),
            "qty": parse_fr_float(m.group(3)),
            "unit": "kWh",
            "unit_price": parse_fr_float(m.group(4)),
            "amount_ht": parse_fr_float(m.group(5)),
            "vat_rate": parse_fr_float(m.group(6)),
        })

    return {
        "invoice_meta": {
            "supplier": "TOTALENERGIES",
            "invoice_id": invoice_id,
            "pdl": pdl,
            "invoice_date": invoice_date_iso,
            "period_start": period_start,
            "period_end": period_end,
            "segment": segment,
            "puissance_kva": round(puissance) if puissance else None,
            "client": client,
            "source_file": os.path.basename(source_file),
        },
        "totals": {
            "supply_ht": round((supply_ht or 0), 2) if supply_ht else None,
            "network_ht": network_ht,
            "taxes_ht": taxes_ht,
            "htva": htva,
            "vat_breakdown": vat_breakdown,
            "ttc": ttc,
        },
        "lines": lines,
    }


# ======================================================================
# Main
# ======================================================================


def build_golden(pdf_path: str) -> Dict[str, Any]:
    """Extract normalized billing JSON from a PDF."""
    text = extract_text(pdf_path)
    pages = extract_pages(pdf_path)
    supplier = detect_supplier(text)

    if supplier == "ENGIE":
        return parse_engie_elec(text, pages, pdf_path)
    elif supplier == "EDF":
        return parse_edf_elec(text, pages, pdf_path)
    elif supplier == "TOTALENERGIES":
        return parse_total_elec(text, pages, pdf_path)
    else:
        raise ValueError(f"Unknown supplier in PDF: {pdf_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract billing golden JSON from French B2B electricity PDFs")
    parser.add_argument("pdf", nargs="?", help="Path to a single PDF file")
    parser.add_argument("--all", action="store_true", help="Process all PDFs in --pdf-dir")
    parser.add_argument("--pdf-dir", default=".", help="Directory containing PDFs")
    parser.add_argument("--output", "-o", default=".", help="Output directory for JSON files")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.pdf:
        pdf_files = [args.pdf]
    elif args.all:
        pdf_files = sorted(Path(args.pdf_dir).glob("*.pdf"))
    else:
        parser.print_help()
        sys.exit(1)

    for pdf_path in pdf_files:
        pdf_path = str(pdf_path)
        print(f"Processing: {pdf_path}")
        try:
            result = build_golden(pdf_path)
            stem = Path(pdf_path).stem
            out_file = output_dir / f"{stem}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"  => {out_file}")
            # Summary
            totals = result["totals"]
            n_lines = len(result["lines"])
            print(f"  Supplier: {result['invoice_meta']['supplier']}")
            print(f"  Lines: {n_lines}")
            print(f"  HTVA: {totals.get('htva')} | TTC: {totals.get('ttc')}")
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
