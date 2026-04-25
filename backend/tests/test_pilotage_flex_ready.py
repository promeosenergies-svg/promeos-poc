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


# ---------------------------------------------------------------------------
# Test 5 : fallback prix stale (> 36h) -> tarif contractuel
# ---------------------------------------------------------------------------
def test_flex_ready_spot_stale_fallback(monkeypatch):
    """Un prix spot > 36h doit basculer sur le tarif contractuel (prix_age_hours=None)."""
    from datetime import datetime, timedelta, timezone
    from services.pilotage import flex_ready

    def fake_stale_spot(db, zone=None, as_of=None):
        return (100.0, datetime.now(timezone.utc) - timedelta(hours=48))

    monkeypatch.setattr(
        "services.pilotage.connectors.entsoe_day_ahead.get_latest_day_ahead_with_timestamp",
        fake_stale_spot,
    )

    result = flex_ready.build_flex_ready_signals(
        site_id="retail-001",
        demo_site={
            "puissance_max_instantanee_kw": 180.0,
            "prix_eur_kwh": 0.185,
            "puissance_souscrite_kva": 250,
            "energy_vector": "ELEC",
        },
        db=object(),  # dummy, fake_stale_spot ignore le db
    )
    assert result["prix_source"] == "fournisseur_tarif_base"
    assert result["prix_age_hours"] is None
    assert result["prix_eur_kwh"] == 0.185


# ---------------------------------------------------------------------------
# Test 6 : module entsoe_day_ahead indisponible -> fallback gracieux + log
# ---------------------------------------------------------------------------
def test_flex_ready_entsoe_module_indisponible(monkeypatch, caplog):
    """Si le module ENTSO-E crash a l'import, fallback tarif + warning log."""
    import logging
    from services.pilotage import flex_ready

    def raise_import_error(db, zone=None, as_of=None):
        raise ImportError("ENTSO-E connector manquant")

    monkeypatch.setattr(
        "services.pilotage.connectors.entsoe_day_ahead.get_latest_day_ahead_with_timestamp",
        raise_import_error,
    )

    with caplog.at_level(logging.WARNING, logger="services.pilotage.flex_ready"):
        result = flex_ready.build_flex_ready_signals(
            site_id="retail-001",
            demo_site={
                "puissance_max_instantanee_kw": 180.0,
                "prix_eur_kwh": 0.185,
                "puissance_souscrite_kva": 250,
                "energy_vector": "ELEC",
            },
            db=object(),
        )

    assert result["prix_source"] == "fournisseur_tarif_base"
    assert result["prix_age_hours"] is None
    # Verifie que l'erreur a ete loggee (pas avalee silencieusement)
    assert any("ENTSO-E" in rec.message or "spot" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# Tests Option C : harmonisation Site.id numerique + scope org
# ---------------------------------------------------------------------------
@pytest.fixture
def org_with_site_and_contract():
    """Cree Org + Entite + Portefeuille + Site + DeliveryPoint + EnergyContract."""
    from datetime import date

    from middleware.auth import AuthContext, get_optional_auth
    from models import EntiteJuridique, Organisation, Portefeuille, Site
    from models.billing_models import EnergyContract
    from models.enums import BillingEnergyType, TypeSite
    from models.patrimoine import DeliveryPoint

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    org = Organisation(nom="Test Org", siren="123456789")
    db.add(org)
    db.flush()

    entite = EntiteJuridique(nom="Test Entite", siren="123456789", organisation_id=org.id)
    db.add(entite)
    db.flush()

    ptf = Portefeuille(nom="Test Ptf", entite_juridique_id=entite.id)
    db.add(ptf)
    db.flush()

    site = Site(
        nom="Hypermarche Test",
        type=TypeSite.MAGASIN,
        portefeuille_id=ptf.id,
        surface_m2=2500.0,
        actif=True,
        archetype_code="COMMERCE_ALIMENTAIRE",
        puissance_pilotable_kw=220.0,
    )
    db.add(site)
    db.flush()

    dp = DeliveryPoint(
        code="12345678901234",
        site_id=site.id,
        puissance_souscrite_kva=250.0,
    )
    db.add(dp)

    contract = EnergyContract(
        site_id=site.id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF",
        start_date=date(2025, 1, 1),
        price_ref_eur_per_kwh=0.198,
    )
    db.add(contract)
    db.flush()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    c = TestClient(app, raise_server_exceptions=False)
    yield {
        "client": c,
        "db": db,
        "site": site,
        "org": org,
        "AuthContext": AuthContext,
        "get_optional_auth": get_optional_auth,
    }
    app.dependency_overrides.clear()
    db.close()


def test_flex_ready_accepte_site_id_numerique(org_with_site_and_contract):
    """Un Site.id numerique doit resoudre en DB et produire une payload valide."""
    ctx = org_with_site_and_contract
    site = ctx["site"]
    r = ctx["client"].get(f"/api/pilotage/flex-ready-signals/{site.id}")
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
    data = r.json()
    assert data["site_id"] == str(site.id)
    assert data["puissance_max_instantanee_kw"] == 220.0
    assert data["puissance_souscrite_kva"] == 250
    # Prix derive du contrat (0.198) via fallback fournisseur_tarif_base (pas de spot dispo en DB vierge)
    assert data["prix_eur_kwh"] == 0.198
    assert data["prix_source"] == "contrat_fournisseur"
    assert data["norme"] == "NF EN IEC 62746-4"
    assert data["conformite_flex_ready"] is True


def test_flex_ready_site_hors_scope_org_404(org_with_site_and_contract):
    """Un Site.id hors scope de l'org authentifiee doit renvoyer 404."""
    ctx = org_with_site_and_contract
    site = ctx["site"]
    AuthContext = ctx["AuthContext"]
    get_optional_auth = ctx["get_optional_auth"]

    fake_auth = AuthContext(
        user=None,
        user_org_role=None,
        org_id=9999,  # org differente
        role=None,
        site_ids=[site.id],
    )
    app.dependency_overrides[get_optional_auth] = lambda: fake_auth
    try:
        r = ctx["client"].get(f"/api/pilotage/flex-ready-signals/{site.id}")
        assert r.status_code == 404
    finally:
        # Ne pas clear toutes les overrides : le fixture s'en charge
        app.dependency_overrides.pop(get_optional_auth, None)


def test_flex_ready_site_sans_contrat_fallback(org_with_site_and_contract):
    """Un Site reel sans EnergyContract elec -> tarif fallback + trace explicite."""
    from models.billing_models import EnergyContract

    ctx = org_with_site_and_contract
    db = ctx["db"]
    site = ctx["site"]

    # Supprimer le contrat pour forcer le fallback
    db.query(EnergyContract).filter(EnergyContract.site_id == site.id).delete()
    db.flush()

    r = ctx["client"].get(f"/api/pilotage/flex-ready-signals/{site.id}")
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
    data = r.json()
    assert data["prix_source"] == "site_sans_contrat_fallback"
    assert data["prix_eur_kwh"] == 0.175  # _TARIF_BASE_FALLBACK_EUR_KWH
    assert data["conformite_flex_ready"] is True


def test_flex_ready_demo_sites_toujours_supportes(client):
    """Regression : les cles DEMO_SITES historiques restent supportees."""
    r = client.get("/api/pilotage/flex-ready-signals/bureau-001")
    assert r.status_code == 200
    data = r.json()
    assert data["site_id"] == "bureau-001"
    assert data["puissance_souscrite_kva"] == 144
    assert data["puissance_max_instantanee_kw"] == 95.0


def test_flex_ready_contrat_resilie_exclu(org_with_site_and_contract):
    """
    Fix review PR #231 : un contrat avec `end_date` anterieure a aujourd'hui
    ne doit PAS etre retenu. On ajoute un contrat 'legacy' resilie avec un
    start_date plus recent que l'actif, puis on verifie que c'est l'actif
    (end_date=None) qui gagne.
    """
    from datetime import date, timedelta

    from models.billing_models import EnergyContract
    from models.enums import BillingEnergyType

    ctx = org_with_site_and_contract
    db = ctx["db"]
    site = ctx["site"]

    # Ajout d'un contrat resilie recent (start_date 2026-03-01, end_date 2026-03-15 PASSE)
    resilie = EnergyContract(
        site_id=site.id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="ANCIEN_FOURNISSEUR",
        start_date=date(2026, 3, 1),
        end_date=date.today() - timedelta(days=10),
        price_ref_eur_per_kwh=0.999,
    )
    db.add(resilie)
    db.flush()

    r = ctx["client"].get(f"/api/pilotage/flex-ready-signals/{site.id}")
    assert r.status_code == 200
    data = r.json()
    # Doit rester sur le contrat ACTIF (0.198) pas le resilie (0.999)
    assert data["prix_eur_kwh"] == 0.198, f"Contrat resilie a ete retenu a tort : prix={data['prix_eur_kwh']}"
    assert data["prix_source"] == "contrat_fournisseur"


def test_flex_ready_conformite_false_sans_deliverypoint(org_with_site_and_contract):
    """
    Fix P1-1 audit PR #231 : un Site sans DeliveryPoint tombe sur le sentinel
    `puissance_souscrite_kva=0` via `_load_flex_ready_ctx`. La regle de
    conformite doit exclure les sentinels 0 (vs `is not None` naif) et
    flagger `conformite_flex_ready=False`.
    """
    from models.patrimoine import DeliveryPoint

    ctx = org_with_site_and_contract
    db = ctx["db"]
    site = ctx["site"]

    # Supprimer le DeliveryPoint pour forcer le sentinel 0 kVA
    db.query(DeliveryPoint).filter(DeliveryPoint.site_id == site.id).delete()
    db.flush()

    r = ctx["client"].get(f"/api/pilotage/flex-ready-signals/{site.id}")
    assert r.status_code == 200
    data = r.json()
    assert data["puissance_souscrite_kva"] == 0
    # Sentinel 0 -> conformite NF EN IEC 62746-4 NON atteinte
    assert data["conformite_flex_ready"] is False
