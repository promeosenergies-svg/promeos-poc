"""
Parser pour EuropEnergies Gros Plan (articles de fond).
Format PDF : 1-2 pages, article unique par PDF.
"""

import re
from pathlib import Path

from models.enums import ArticleCategory, ArticleSource
from .base_parser import extract_text_pdftotext, parse_ee_date, compute_content_hash, auto_tag


def parse_gros_plan_pdf(pdf_path: str) -> list[dict]:
    """Parse un PDF Gros Plan EE → un seul article structuré."""
    path = Path(pdf_path)
    text = extract_text_pdftotext(pdf_path)
    if not text.strip():
        return []

    lines = text.strip().split("\n")
    first_line = lines[0]
    source_date = parse_ee_date(first_line)
    if not source_date:
        return []

    body_text = "\n".join(lines[1:]).strip()
    body_text = re.sub(r"\f", "\n", body_text)

    title = ""
    for line in lines[1:]:
        stripped = line.strip()
        if stripped and len(stripped) > 10:
            title = stripped
            break

    if not title:
        title = f"Gros Plan – {source_date.strftime('%d/%m/%Y')}"

    tags = auto_tag(f"{title} {body_text}")
    content_hash = compute_content_hash(title, body_text, source_date.isoformat())

    return [
        {
            "source": ArticleSource.EUROP_ENERGIES,
            "category": ArticleCategory.GROS_PLAN,
            "title": title,
            "body_text": body_text,
            "summary": body_text[:300].rsplit(".", 1)[0] + "." if "." in body_text[:300] else body_text[:300],
            "countries": tags["countries"],
            "topics": tags["topics"],
            "entities": tags["entities"],
            "energy_types": tags["energy_types"],
            "source_file": path.name,
            "source_date": source_date,
            "source_issue": None,
            "content_hash": content_hash,
            "promeos_relevance": tags["promeos_relevance"],
            "promeos_modules": tags["promeos_modules"],
        }
    ]
