"""
Parser pour EuropEnergies Garanties d'Origine (enchères GO).
"""

from pathlib import Path

from models.enums import ArticleCategory, ArticleSource
from .base_parser import extract_text_pdftotext, parse_ee_date, compute_content_hash, auto_tag


def parse_go_pdf(pdf_path: str) -> list[dict]:
    """Parse un PDF GO → un article structuré."""
    path = Path(pdf_path)
    text = extract_text_pdftotext(pdf_path)
    if not text.strip():
        return []

    first_line = text.split("\n")[0]
    source_date = parse_ee_date(first_line)
    if not source_date:
        return []

    title = first_line.strip()
    body = text.strip()
    tags = auto_tag(body)
    if "GO" not in tags["topics"]:
        tags["topics"].append("GO")

    return [
        {
            "source": ArticleSource.EUROP_ENERGIES,
            "category": ArticleCategory.GO_AUCTION,
            "title": title,
            "body_text": body,
            "summary": body[:300].rsplit(".", 1)[0] + "." if "." in body[:300] else body[:300],
            "countries": tags["countries"],
            "topics": tags["topics"],
            "entities": tags["entities"],
            "energy_types": ["ELEC"],
            "source_file": path.name,
            "source_date": source_date,
            "content_hash": compute_content_hash(title, body, source_date.isoformat()),
            "promeos_relevance": 0.7,
            "promeos_modules": ["achat"],
        }
    ]
