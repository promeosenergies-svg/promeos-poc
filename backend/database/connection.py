"""
PROMEOS - Configuration de la base de données
Connexion SQLite pour gestion des 120 sites
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Chemin vers la base SQLite
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "promeos.db")

# Créer le dossier data s'il n'existe pas
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# URL de connexion SQLite
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

print(f"[DB] Base de donnees PROMEOS : {DATABASE_PATH}")

# Engine SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Nécessaire pour SQLite
    echo=False  # Mettre True pour voir les requêtes SQL en dev
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency pour FastAPI
def get_db():
    """
    Générateur de session de base de données
    À utiliser comme dépendance FastAPI
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
