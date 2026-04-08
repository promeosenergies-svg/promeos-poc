"""
PROMEOS — Ingestion pipeline EuropEnergies.
Scanne docs/base_documentaire/EuropEnergies/ → parse → upsert DB.
Idempotent : content_hash empêche les doublons.
"""

import logging
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.market_article import MarketArticle
from models.market_indicator import MarketIndicator

from market_intelligence.parsers.ee_flash_parser import parse_flash_pdf
from market_intelligence.parsers.ee_gros_plan_parser import parse_gros_plan_pdf
from market_intelligence.parsers.ee_monthly_parser import parse_monthly_pdf
from market_intelligence.parsers.ee_go_parser import parse_go_pdf

logger = logging.getLogger(__name__)


def classify_ee_file(filename: str) -> str | None:
    """Classifie un fichier EE par son type."""
    name = filename.lower()
    if name.endswith(".pptx") or name.endswith(".docx.pdf"):
        return None
    if "flash" in name:
        return "flash"
    elif name.startswith("ee_gp"):
        return "gros_plan"
    elif name.startswith("ee-n"):
        return "monthly"
    elif name.startswith("ee_go"):
        return "go"
    return None


def ingest_ee_directory(db: Session, base_dir: str) -> dict:
    """Ingestion complète du dossier EE. Retourne un bilan."""
    base_path = Path(base_dir)
    if not base_path.exists():
        logger.error(f"Directory not found: {base_dir}")
        return {"error": f"Directory not found: {base_dir}"}

    stats = {
        "total_files": 0,
        "parsed": 0,
        "skipped": 0,
        "duplicates": 0,
        "articles_inserted": 0,
        "indicators_inserted": 0,
        "errors": [],
    }

    # Dédupliquer les fichiers (certains ont des "(1)" "(2)" en double)
    seen_files = set()
    pdf_files = []
    for f in sorted(base_path.glob("*.pdf")):
        normalized = f.stem.split(" (")[0] + f.suffix
        if normalized not in seen_files:
            seen_files.add(normalized)
            pdf_files.append(f)
        else:
            stats["skipped"] += 1

    stats["total_files"] = len(pdf_files) + stats["skipped"]

    for pdf_path in pdf_files:
        file_type = classify_ee_file(pdf_path.name)
        if not file_type:
            stats["skipped"] += 1
            continue

        try:
            if file_type == "flash":
                articles_data = parse_flash_pdf(str(pdf_path))
                _insert_articles(db, articles_data, stats)

            elif file_type == "gros_plan":
                articles_data = parse_gros_plan_pdf(str(pdf_path))
                _insert_articles(db, articles_data, stats)

            elif file_type == "monthly":
                result = parse_monthly_pdf(str(pdf_path))
                _insert_articles(db, result["articles"], stats)
                _insert_indicators(db, result["indicators"], stats)

            elif file_type == "go":
                articles_data = parse_go_pdf(str(pdf_path))
                _insert_articles(db, articles_data, stats)

            stats["parsed"] += 1

        except Exception as e:
            stats["errors"].append(f"{pdf_path.name}: {str(e)}")
            logger.error(f"Error parsing {pdf_path.name}: {e}", exc_info=True)

    db.commit()

    logger.info(
        f"EE ingestion complete: {stats['parsed']} parsed, "
        f"{stats['articles_inserted']} articles, "
        f"{stats['indicators_inserted']} indicators, "
        f"{len(stats['errors'])} errors"
    )
    return stats


def _insert_articles(db: Session, articles_data: list[dict], stats: dict):
    """Insert articles avec gestion des doublons par content_hash."""
    for data in articles_data:
        existing = db.query(MarketArticle).filter(MarketArticle.content_hash == data["content_hash"]).first()
        if existing:
            stats["duplicates"] += 1
            continue
        article = MarketArticle(**data)
        db.add(article)
        db.flush()
        stats["articles_inserted"] += 1


def _insert_indicators(db: Session, indicators_data: list[dict], stats: dict):
    """Insert indicators avec gestion des doublons."""
    for data in indicators_data:
        try:
            indicator = MarketIndicator(**data)
            db.add(indicator)
            db.flush()
            stats["indicators_inserted"] += 1
        except IntegrityError:
            db.rollback()
            stats["duplicates"] += 1
