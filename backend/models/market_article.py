"""
PROMEOS — MarketArticle model
Articles de veille marché structurés (EuropEnergies, CRE, etc.).
Source de vérité pour l'intelligence marché contextuelle.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    JSON,
    Index,
    Enum as SAEnum,
)

from models.base import Base, TimestampMixin
from models.enums import ArticleCategory, ArticleSource


class MarketArticle(TimestampMixin, Base):
    """Article de veille marché structuré, parsé depuis PDFs EuropEnergies ou autres sources."""

    __tablename__ = "market_articles"

    id = Column(Integer, primary_key=True)
    source = Column(SAEnum(ArticleSource), nullable=False, default=ArticleSource.EUROP_ENERGIES, index=True)
    category = Column(SAEnum(ArticleCategory), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    body_text = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)

    # Tagging structuré
    countries = Column(JSON, default=list)
    topics = Column(JSON, default=list)
    entities = Column(JSON, default=list)
    energy_types = Column(JSON, default=list)

    # Source & provenance
    source_file = Column(String(200), nullable=False)
    source_date = Column(DateTime(timezone=True), nullable=False, index=True)
    source_issue = Column(String(50), nullable=True)
    source_page = Column(Integer, nullable=True)

    # Déduplication
    content_hash = Column(String(64), unique=True, nullable=False, index=True)

    # Pertinence PROMEOS
    promeos_relevance = Column(Float, default=0.5)
    promeos_modules = Column(JSON, default=list)

    __table_args__ = (
        Index("ix_article_date_cat", "source_date", "category"),
        Index("ix_article_source_date", "source", "source_date"),
    )

    def __repr__(self):
        return f"<MarketArticle(id={self.id}, cat={self.category}, date={self.source_date}, title={self.title[:50]})>"
