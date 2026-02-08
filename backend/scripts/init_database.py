import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base
from database import engine, DATABASE_URL

def init_database():
    print("🔥 PROMEOS - Initialisation de la base de données")
    print(f"📁 Fichier DB : {DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées :", list(Base.metadata.tables.keys()))

if __name__ == "__main__":
    init_database()
