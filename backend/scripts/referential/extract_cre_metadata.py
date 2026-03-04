"""
PROMEOS Referentiel — CRE-specific metadata extractor.
Parses CRE deliberation pages for structured metadata.
"""

import re
from typing import Optional


def extract_cre_metadata(html_content: str) -> dict:
    """
    Parse a CRE deliberation HTML page and extract structured fields:
    - deliberation_number
    - date_document
    - date_mise_en_ligne
    - document_type (Decision, Projet, Avis, Communication)
    - energy (Electricite, Gaz, Multi)
    - pdf_url (if found)
    """
    result: dict = {}

    # Deliberation number: "N° 2025-xxx" patterns
    num_match = re.search(r"(?:N[°o]\s*|numero[:\s]*)(\d{4}-\d{2,4})", html_content, re.IGNORECASE)
    if num_match:
        result["deliberation_number"] = num_match.group(1)

    # Date du document
    date_doc_match = re.search(r"Date\s+du\s+document\s*[:\s]*(\d{1,2}\s+\w+\s+\d{4})", html_content, re.IGNORECASE)
    if date_doc_match:
        result["date_document"] = _normalize_french_date(date_doc_match.group(1))

    # Date de mise en ligne
    date_mel_match = re.search(
        r"(?:Date\s+de\s+mise\s+en\s+ligne|Mise\s+en\s+ligne)\s*[:\s]*(\d{1,2}\s+\w+\s+\d{4})",
        html_content,
        re.IGNORECASE,
    )
    if date_mel_match:
        result["date_mise_en_ligne"] = _normalize_french_date(date_mel_match.group(1))

    # Fallback: date from meta tags or breadcrumb
    if "date_document" not in result:
        iso_match = re.search(
            r'(?:date|datePublished|article:published_time)["\s:=]+(\d{4}-\d{2}-\d{2})', html_content, re.IGNORECASE
        )
        if iso_match:
            result["date_document"] = iso_match.group(1)

    # Document type
    content_lower = html_content.lower()
    if "projet de" in content_lower or "consultation publique" in content_lower:
        result["document_type"] = "Projet"
    elif "décision" in content_lower or "decision" in content_lower:
        result["document_type"] = "Decision"
    elif "avis" in content_lower:
        result["document_type"] = "Avis"
    elif "communication" in content_lower:
        result["document_type"] = "Communication"
    else:
        result["document_type"] = "Autre"

    # Energy type
    if "électricité" in content_lower or "electricite" in content_lower or "turpe" in content_lower:
        if "gaz" in content_lower:
            result["energy_detected"] = "multi"
        else:
            result["energy_detected"] = "electricite"
    elif "gaz" in content_lower:
        result["energy_detected"] = "gaz"
    else:
        result["energy_detected"] = "unknown"

    # PDF link
    pdf_match = re.search(r'href="([^"]+\.pdf[^"]*)"', html_content, re.IGNORECASE)
    if pdf_match:
        pdf_url = pdf_match.group(1)
        if not pdf_url.startswith("http"):
            pdf_url = "https://www.cre.fr" + pdf_url
        result["pdf_url"] = pdf_url

    return result


FRENCH_MONTHS = {
    "janvier": "01",
    "février": "02",
    "fevrier": "02",
    "mars": "03",
    "avril": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "août": "08",
    "aout": "08",
    "septembre": "09",
    "octobre": "10",
    "novembre": "11",
    "décembre": "12",
    "decembre": "12",
}


def _normalize_french_date(raw: str) -> Optional[str]:
    """Convert '16 janvier 2025' -> '2025-01-16'."""
    raw = raw.strip().lower()
    match = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", raw)
    if not match:
        return None
    day, month_str, year = match.groups()
    month = FRENCH_MONTHS.get(month_str)
    if not month:
        return None
    return f"{year}-{month}-{int(day):02d}"
