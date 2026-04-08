"""
Routes API Market Intelligence.
Endpoints sous /api/market-intelligence/*.
"""

import os
from typing import Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from models.market_article import MarketArticle
from models.market_indicator import MarketIndicator
from models.enums import ArticleCategory

router = APIRouter(prefix="/api/market-intelligence", tags=["Market Intelligence"])


@router.get("/articles")
def list_articles(
    category: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste des articles de veille marché avec filtres."""
    q = db.query(MarketArticle)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    q = q.filter(MarketArticle.source_date >= cutoff)

    if category:
        q = q.filter(MarketArticle.category == category)
    if topic:
        q = q.filter(MarketArticle.topics.contains(topic))
    if module:
        q = q.filter(MarketArticle.promeos_modules.contains(module))

    total = q.count()
    articles = q.order_by(desc(MarketArticle.source_date)).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "articles": [_serialize_article(a) for a in articles],
    }


@router.get("/articles/{article_id}")
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détail d'un article (inclut body_text complet)."""
    article = db.query(MarketArticle).filter(MarketArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article non trouvé")
    return _serialize_article_full(article)


@router.get("/search")
def search_articles(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Recherche full-text dans les articles (titre + body)."""
    pattern = f"%{q}%"
    articles = (
        db.query(MarketArticle)
        .filter(or_(MarketArticle.title.ilike(pattern), MarketArticle.body_text.ilike(pattern)))
        .order_by(desc(MarketArticle.source_date))
        .limit(limit)
        .all()
    )
    return {
        "query": q,
        "count": len(articles),
        "results": [_serialize_article(a) for a in articles],
    }


@router.get("/indicators/latest")
def get_latest_indicators(
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Derniers indicateurs marché par indicator_name."""
    subq = (
        db.query(
            MarketIndicator.indicator_name,
            func.max(MarketIndicator.period_start).label("max_date"),
        )
        .group_by(MarketIndicator.indicator_name)
        .subquery()
    )

    indicators = (
        db.query(MarketIndicator)
        .join(
            subq,
            (MarketIndicator.indicator_name == subq.c.indicator_name)
            & (MarketIndicator.period_start == subq.c.max_date),
        )
        .all()
    )

    return {
        "count": len(indicators),
        "indicators": [_serialize_indicator(i) for i in indicators],
    }


@router.get("/indicators/history")
def get_indicator_history(
    name: str = Query(...),
    limit: int = Query(12, ge=1, le=60),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Historique d'un indicateur."""
    indicators = (
        db.query(MarketIndicator)
        .filter(MarketIndicator.indicator_name == name)
        .order_by(desc(MarketIndicator.period_start))
        .limit(limit)
        .all()
    )
    return {
        "indicator": name,
        "count": len(indicators),
        "history": [_serialize_indicator(i) for i in indicators],
    }


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Statistiques de la base Market Intelligence."""
    total_articles = db.query(MarketArticle).count()
    total_indicators = db.query(MarketIndicator).count()

    latest = db.query(MarketArticle).order_by(desc(MarketArticle.source_date)).first()
    earliest = db.query(MarketArticle).order_by(MarketArticle.source_date).first()

    categories = dict(db.query(MarketArticle.category, func.count()).group_by(MarketArticle.category).all())

    return {
        "total_articles": total_articles,
        "total_indicators": total_indicators,
        "date_range": {
            "earliest": earliest.source_date.isoformat() if earliest else None,
            "latest": latest.source_date.isoformat() if latest else None,
        },
        "categories": {k.value if hasattr(k, "value") else str(k): v for k, v in categories.items()},
    }


@router.post("/ingest")
def trigger_ingestion(
    db: Session = Depends(get_db),
    _admin: None = Depends(get_optional_auth),
):
    """Déclenche l'ingestion EuropEnergies."""
    base_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs", "base_documentaire", "EuropEnergies"
    )
    from market_intelligence.ingestion.ingest_ee_directory import ingest_ee_directory

    return ingest_ee_directory(db, base_dir)


# ── Serializers ──


def _serialize_article(a: MarketArticle) -> dict:
    return {
        "id": a.id,
        "category": a.category.value if a.category else None,
        "title": a.title,
        "summary": a.summary,
        "source_date": a.source_date.isoformat() if a.source_date else None,
        "source": a.source.value if a.source else None,
        "source_issue": a.source_issue,
        "countries": a.countries,
        "topics": a.topics,
        "entities": a.entities,
        "energy_types": a.energy_types,
        "promeos_relevance": a.promeos_relevance,
        "promeos_modules": a.promeos_modules,
    }


def _serialize_article_full(a: MarketArticle) -> dict:
    d = _serialize_article(a)
    d["body_text"] = a.body_text
    d["source_file"] = a.source_file
    return d


def _serialize_indicator(i: MarketIndicator) -> dict:
    return {
        "name": i.indicator_name,
        "period": i.period_label,
        "value": i.value_eur_mwh,
        "low": i.value_low,
        "high": i.value_high,
        "close": i.value_close,
        "variation_pct": i.variation_pct,
        "unit": i.unit,
        "source_issue": i.source_issue,
    }
