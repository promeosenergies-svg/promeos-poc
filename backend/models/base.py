"""
PROMEOS - Base SQLAlchemy
Configuration de base pour tous les modèles de données
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime
from datetime import datetime

# Base commune pour tous les modèles
Base = declarative_base()

class TimestampMixin:
    """
    Mixin pour ajouter automatiquement les timestamps
    à tous les modèles PROMEOS
    
    Attributs:
        created_at: Date de création (auto)
        updated_at: Date de dernière modification (auto)
    """
    created_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False,
        comment="Date de création"
    )
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False,
        comment="Date de dernière modification"
    )
