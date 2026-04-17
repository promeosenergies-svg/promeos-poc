"""
PROMEOS - Tests endpoint Flex Ready (R) NF EN IEC 62746-4.

Couvre :
    1. Conformite schema (5 signaux + metadata)
    2. Site inconnu -> 404
    3. 5 champs standardises presents
    4. Timestamp ISO 8601 avec fuseau horaire
"""

from __future__ import annotations

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app
from models import Base
from database import get_db


@pytest.fixture
def client():
    """TestClient avec DB SQLite in-memory -- isolation totale."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def _override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    c = TestClient(app, raise_server_exceptions=False)
    yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 1 : conformite schema
# ---------------------------------------------------------------------------
def test_flex_ready_schema_conformite(client):
    """Le payload expose la norme NF EN IEC 62746-4 et le flag de conformite."""
    r = client.get("/api/pilotage/flex-ready-signals/retail-001")
    assert r.status_code == 200
    data = r.json()

    assert data["site_id"] == "retail-001"
    assert data["norme"] == "NF EN IEC 62746-4"
    assert data["conformite_flex_ready"] is True
    # Pas 15 min minimum (exigence Flex Ready)
    assert data["clock_resolution_min"] == 15


# ---------------------------------------------------------------------------
# Test 2 : site inconnu -> 404
# ---------------------------------------------------------------------------
def test_flex_ready_site_inconnu_404(client):
    """Un site_id hors DEMO_SITES doit renvoyer 404 avec message explicite."""
    r = client.get("/api/pilotage/flex-ready-signals/inexistant-999")
    assert r.status_code == 404
    payload = r.json()
    # PROMEOS global error handler wraps HTTPException.detail into APIError.message
    # (cf. middleware/error_handler.py). On tolere les deux formats.
    msg = payload.get("detail") or payload.get("message") or ""
    assert "inexistant-999" in msg, f"Payload 404 inattendu : {payload!r}"


# ---------------------------------------------------------------------------
# Test 3 : les 5 champs standardises sont presents et bien types
# ---------------------------------------------------------------------------
def test_flex_ready_cinq_signaux_presents(client):
    """
    Les 5 donnees du standard Flex Ready (R) doivent etre presentes :
        1. Horloge (timestamp + clock_resolution_min)
        2. Puissance max instantanee (kW)
        3. Prix (EUR/kWh)
        4. Puissance souscrite (kVA)
        5. Empreinte carbone (kgCO2e/kWh)
    """
    r = client.get("/api/pilotage/flex-ready-signals/retail-001")
    assert r.status_code == 200
    data = r.json()

    # 1. Horloge
    assert "timestamp" in data
    assert "clock_resolution_min" in data
    assert isinstance(data["clock_resolution_min"], int)

    # 2. Puissance max instantanee
    assert "puissance_max_instantanee_kw" in data
    assert isinstance(data["puissance_max_instantanee_kw"], (int, float))
    assert data["puissance_max_instantanee_kw"] > 0

    # 3. Prix
    assert "prix_eur_kwh" in data
    assert isinstance(data["prix_eur_kwh"], (int, float))
    assert data["prix_eur_kwh"] > 0
    assert "prix_source" in data  # trace : fournisseur_tarif_base ou entsoe_day_ahead

    # 4. Puissance souscrite
    assert "puissance_souscrite_kva" in data
    assert isinstance(data["puissance_souscrite_kva"], int)
    assert data["puissance_souscrite_kva"] > 0

    # 5. Empreinte carbone
    assert "empreinte_carbone_kg_co2e_kwh" in data
    assert isinstance(data["empreinte_carbone_kg_co2e_kwh"], (int, float))
    assert data["empreinte_carbone_kg_co2e_kwh"] > 0
    assert "empreinte_source" in data


# ---------------------------------------------------------------------------
# Test 4 : timestamp ISO 8601 avec fuseau horaire
# ---------------------------------------------------------------------------
def test_flex_ready_timestamp_iso_avec_tz(client):
    """Le timestamp doit etre ISO 8601 ET porter un fuseau horaire (+01:00 / +02:00)."""
    r = client.get("/api/pilotage/flex-ready-signals/retail-001")
    assert r.status_code == 200
    data = r.json()

    ts = data["timestamp"]
    assert isinstance(ts, str)

    # datetime.fromisoformat accepte les offsets +HH:MM depuis Python 3.7+
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None, f"Timestamp sans fuseau horaire : {ts!r}"

    # Bonus : offset Europe/Paris doit etre +01:00 (hiver) ou +02:00 (ete)
    offset = parsed.utcoffset()
    assert offset is not None
    hours = offset.total_seconds() / 3600
    assert hours in (1, 2), f"Offset inattendu pour Europe/Paris : {hours}h"
