import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base
from database import engine, DATABASE_URL

def init_database():
    print("[INIT] PROMEOS - Initialisation de la base de donnees")
    print(f"[DB] Fichier DB : {DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    print("[OK] Tables creees :", list(Base.metadata.tables.keys()))

if __name__ == "__main__":
    init_database()
