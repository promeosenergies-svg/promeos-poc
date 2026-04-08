"""
Parser pour EuropEnergies Flashes (brèves quotidiennes).
Format PDF : 1-2 pages, articles séparés par titres géographiques/thématiques.
"""

import re
from pathlib import Path

from models.enums import ArticleCategory, ArticleSource
from .base_parser import extract_text_pdftotext, parse_ee_date, compute_content_hash, auto_tag


def parse_flash_pdf(pdf_path: str) -> list[dict]:
    """Parse un PDF Flash EE → liste de dicts prêts à insérer en MarketArticle."""
    path = Path(pdf_path)
    text = extract_text_pdftotext(pdf_path)
    if not text.strip():
        return []

    first_line = text.split("\n")[0]
    source_date = parse_ee_date(first_line)
    if not source_date:
        return []

    # Nettoyer le footer
    text = re.sub(r"Suppl.ment au mensuel EUROP.ENERGIES", "", text)
    text = re.sub(r"\f", "\n", text)

    articles = _split_flash_articles(text, first_line)

    results = []
    for art in articles:
        title = art["title"].strip()
        body = art["body"].strip()
        if len(body) < 30:
            continue

        tags = auto_tag(f"{title} {body}")
        content_hash = compute_content_hash(title, body, source_date.isoformat())

        results.append(
            {
                "source": ArticleSource.EUROP_ENERGIES,
                "category": ArticleCategory.FLASH,
                "title": title,
                "body_text": body,
                "summary": _generate_summary(body),
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
        )

    return results


def _split_flash_articles(text: str, first_line: str) -> list[dict]:
    """Sépare le texte d'un flash en articles individuels."""
    text = text.replace(first_line, "", 1).strip()

    title_pattern = re.compile(
        r"^(?:(?:France|UE|Allemagne|Belgique|Espagne|Italie|Royaume-Uni|"
        r"Europe|Crise|Nomination|Nucl.aire|Gaz|P.trole|Renouvelables|"
        r"R.seaux|Stockage|Chaleur|Flexibilit.|Capacit.|Tarif|En Bref|"
        r"Futurs .nerg.tiques|Autoconsommation|Prix|March.|Comp.tition|"
        r"Offres|Fournisseurs|G.opolitique|Iran|Moyen.Orient)"
        r"[\s]*:?\s*.+)",
        re.MULTILINE,
    )

    matches = list(title_pattern.finditer(text))

    if not matches:
        return [{"title": "Flash EuropEnergies", "body": text}]

    articles = []
    for i, match in enumerate(matches):
        title_line = match.group(0).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        title = title_line.split("\n")[0].strip()
        articles.append({"title": title, "body": f"{title_line}\n{body}"})

    return articles


def _generate_summary(body: str, max_chars: int = 300) -> str:
    """Résumé = premières phrases jusqu'à max_chars."""
    sentences = re.split(r"(?<=[.!?])\s+", body)
    summary = ""
    for s in sentences:
        if len(summary) + len(s) > max_chars:
            break
        summary += s + " "
    return summary.strip() or body[:max_chars]
