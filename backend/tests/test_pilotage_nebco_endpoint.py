"""
PROMEOS - Tests endpoint /api/pilotage/nebco-simulation/{site_id} (Vague 2 piste 4).

Couvre :
    1. Site.id numerique avec CDC seedee -> 200 + payload NebcoSimulationResponse.
    2. Site hors scope org -> 404 (defense-in-depth).
    3. Validation Pydantic `period_days` (7-90) -> 422.
    4. Cle DEMO_SITES -> 404 explicite (pas de CDC historique credible).
    5. Schema Pydantic complet conforme (tous champs + types).

Note : l'interface `simulate_nebco_gain` est stable (agent A), mais l'impl
peut ne pas etre presente au moment de ce test -> tests 1 et 5 utilisent
un monkeypatch sur le service pour simuler un resultat deterministe.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from main import app
from middleware.auth import AuthContext, get_optional_auth
from models import (
    Base,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
)
from models.energy_models import FrequencyType, Meter, MeterReading
from models.enums import EnergyVector, TypeSite
from models.market_models import (
    MarketDataSource,
    MarketType,
    MktPrice,
    PriceZone,
    ProductType,
    Resolution,
)


# ---------------------------------------------------------------------------
# Fake service pour decoupler des tests : simulate_nebco_gain peut ne pas
# encore etre implemente par l'agent A au moment de l'execution.
# ---------------------------------------------------------------------------
def _fake_simulate_nebco_gain(*, site, db, period_days: int = 30, now=None) -> dict:
    """
    Simulacre du service `simulate_nebco_gain` -- signature stable, resultat
    deterministe pour les tests d'integration HTTP (cf. interface Agent A).
    """
    periode_fin = (now or datetime.now(timezone.utc)).date()
    periode_debut = periode_fin - timedelta(days=period_days)
    return {
        "site_id": str(site.id),
        "periode_debut": periode_debut.isoformat(),
        "periode_fin": periode_fin.isoformat(),
        "gain_simule_eur": 125.40,
        "kwh_decales_total": 1840.0,
        "n_fenetres_favorables": 12,
        "spread_moyen_eur_mwh": 58.3,
        "composantes": {
            "gain_spread_eur": 179.14,
            "compensation_fournisseur_eur": 53.74,
            "net_eur": 125.40,
        },
        "hypotheses": {
            "taux_decalable": 0.18,
            "compensation_ratio": 0.30,
            "archetype": site.archetype_code or "BUREAU_STANDARD",
            "sources": ["Barometre Flex 2026", "NEBCO 2025"],
        },
        "confiance": "indicative",
        "source": "Barometre Flex 2026 + MktPrice day-ahead FR",
    }


@pytest.fixture
def patch_nebco_service(monkeypatch):
    """
    Monkeypatch `services.pilotage.nebco_simulation.simulate_nebco_gain`.

    Utile tant que l'agent A n'a pas merge l'impl reelle : garantit que
    l'endpoint est testable en isolation. Le parent coordonnera le merge.
    """
    import types

    fake_mod = types.ModuleType("services.pilotage.nebco_simulation")
    fake_mod.simulate_nebco_gain = _fake_simulate_nebco_gain  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "services.pilotage.nebco_simulation", fake_mod)
    return fake_mod


# ---------------------------------------------------------------------------
# Fixtures DB + client
# ---------------------------------------------------------------------------
@pytest.fixture
def db_session():
    """Session DB SQLite in-memory, isolation totale."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def org_with_site_cdc(db_session):
    """
    Org + EntiteJuridique + Portefeuille + Site seede + Meter + 30 MeterReading
    horaires + 30 MktPrice (1 par jour, 12h UTC).

    Represente la base minimale attendue par `simulate_nebco_gain` :
        - Site reel avec archetype + puissance pilotable
        - Meter ELEC avec readings historiques
        - MktPrice day-ahead FR sur la periode
    """
    org = Organisation(nom="Nebco Test Org", siren="987654321")
    db_session.add(org)
    db_session.flush()

    entite = EntiteJuridique(
        nom="Nebco Test Entite",
        siren="987654321",
        organisation_id=org.id,
    )
    db_session.add(entite)
    db_session.flush()

    ptf = Portefeuille(nom="Nebco Test Ptf", entite_juridique_id=entite.id)
    db_session.add(ptf)
    db_session.flush()

    site = Site(
        nom="Bureau Test Nebco",
        type=TypeSite.BUREAU,
        portefeuille_id=ptf.id,
        surface_m2=1800.0,
        actif=True,
        archetype_code="BUREAU_STANDARD",
        puissance_pilotable_kw=120.0,
    )
    db_session.add(site)
    db_session.flush()

    meter = Meter(
        meter_id=f"PRM-NEBCO-{site.id}",
        name="Meter Nebco Test",
        energy_vector=EnergyVector.ELECTRICITY,
        site_id=site.id,
        subscribed_power_kva=144.0,
        is_active=True,
    )
    db_session.add(meter)
    db_session.flush()

    # 30 readings horaires (1 par jour midi UTC sur 30 jours).
    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    readings: list[MeterReading] = []
    prices: list[MktPrice] = []
    for d in range(1, 31):
        ts = now_utc - timedelta(days=d)
        ts_noon = ts.replace(hour=12)
        readings.append(
            MeterReading(
                meter_id=meter.id,
                timestamp=ts_noon.replace(tzinfo=None),
                frequency=FrequencyType.HOURLY,
                value_kwh=50.0,
            )
        )
        prices.append(
            MktPrice(
                source=MarketDataSource.ENTSOE,
                market_type=MarketType.SPOT_DAY_AHEAD,
                product_type=ProductType.HOURLY,
                zone=PriceZone.FR,
                delivery_start=ts_noon,
                delivery_end=ts_noon + timedelta(hours=1),
                price_eur_mwh=-15.0 if d % 3 == 0 else 75.0,
                resolution=Resolution.PT60M,
                fetched_at=now_utc,
            )
        )
    db_session.add_all(readings + prices)
    db_session.commit()

    return {"org": org, "entite": entite, "ptf": ptf, "site": site, "meter": meter}


def _override_db_factory(db_session):
    def _gen():
        yield db_session

    return _gen


# ---------------------------------------------------------------------------
# Test 1 : Site.id numerique + CDC seedee -> 200 + payload valide
# ---------------------------------------------------------------------------
def test_endpoint_site_reel_numerique(db_session, org_with_site_cdc, patch_nebco_service):
    """Un Site.id numerique avec CDC seedee -> 200 + payload NebcoSimulationResponse."""
    site = org_with_site_cdc["site"]

    app.dependency_overrides[get_db] = _override_db_factory(db_session)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(f"/api/pilotage/nebco-simulation/{site.id}")
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
        data = r.json()
        assert data["site_id"] == str(site.id)
        assert data["gain_simule_eur"] == pytest.approx(125.40)
        assert data["n_fenetres_favorables"] == 12
        assert data["confiance"] == "indicative"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 2 : Site hors scope org -> 404 (defense-in-depth)
# ---------------------------------------------------------------------------
def test_endpoint_site_hors_scope_404(db_session, org_with_site_cdc, patch_nebco_service):
    """Auth avec org_id different du site -> 404 via `_scoped_site_query`."""
    site = org_with_site_cdc["site"]
    fake_auth = AuthContext(
        user=None,
        user_org_role=None,
        org_id=9999,  # pas l'org du site
        role=None,
        site_ids=[site.id],
    )

    app.dependency_overrides[get_db] = _override_db_factory(db_session)
    app.dependency_overrides[get_optional_auth] = lambda: fake_auth
    try:
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(f"/api/pilotage/nebco-simulation/{site.id}")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 3 : period_days hors [7, 90] -> 422
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("period_days", [0, 3, 6, 91, 200])
def test_endpoint_period_days_validation(db_session, org_with_site_cdc, patch_nebco_service, period_days):
    """Pydantic Query validation rejette period_days hors [7, 90] -> 422."""
    site = org_with_site_cdc["site"]

    app.dependency_overrides[get_db] = _override_db_factory(db_session)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/api/pilotage/nebco-simulation/{site.id}",
            params={"period_days": period_days},
        )
        assert r.status_code == 422, f"period_days={period_days} devait etre refuse, got {r.status_code}"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 4 : cle DEMO_SITES -> 404 explicite (pas de CDC credible)
# ---------------------------------------------------------------------------
def test_endpoint_demo_site_404_explicite(db_session, patch_nebco_service):
    """`/nebco-simulation/retail-001` -> 404 avec message clair (pas de CDC seedee)."""
    app.dependency_overrides[get_db] = _override_db_factory(db_session)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/pilotage/nebco-simulation/retail-001")
        assert r.status_code == 404
        payload = r.json()
        # Le middleware d'erreur PROMEOS wrappe HTTPException.detail dans
        # `message` (code/message/hint/correlation_id) ; en fallback, certains
        # endpoints retournent encore `detail` brut -> on accepte les deux.
        detail = payload.get("message") or payload.get("detail", "")
        assert "DEMO" in detail or "demo" in detail.lower() or "CDC" in detail, (
            f"Message 404 devrait mentionner DEMO/CDC : {detail!r}"
        )
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 5 : schema Pydantic complet conforme (champs + types)
# ---------------------------------------------------------------------------
def test_endpoint_schema_conforme(db_session, org_with_site_cdc, patch_nebco_service):
    """Le payload respecte integralement NebcoSimulationResponse (champs + types)."""
    site = org_with_site_cdc["site"]

    app.dependency_overrides[get_db] = _override_db_factory(db_session)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(f"/api/pilotage/nebco-simulation/{site.id}?period_days=30")
        assert r.status_code == 200
        data = r.json()

        # Champs racine obligatoires
        expected_keys = {
            "site_id",
            "periode_debut",
            "periode_fin",
            "gain_simule_eur",
            "kwh_decales_total",
            "n_fenetres_favorables",
            "spread_moyen_eur_mwh",
            "composantes",
            "hypotheses",
            "confiance",
            "source",
        }
        missing = expected_keys - set(data.keys())
        assert not missing, f"Champs manquants : {missing}"

        # Types
        assert isinstance(data["site_id"], str)
        assert isinstance(data["periode_debut"], str)
        assert isinstance(data["periode_fin"], str)
        assert isinstance(data["gain_simule_eur"], (int, float))
        assert isinstance(data["kwh_decales_total"], (int, float))
        assert isinstance(data["n_fenetres_favorables"], int)
        assert data["n_fenetres_favorables"] >= 0
        assert isinstance(data["spread_moyen_eur_mwh"], (int, float))
        assert isinstance(data["hypotheses"], dict)
        assert isinstance(data["source"], str)
        assert data["confiance"] == "indicative"

        # Composantes : 3 champs additifs
        comp = data["composantes"]
        assert set(comp.keys()) == {
            "gain_spread_eur",
            "compensation_fournisseur_eur",
            "net_eur",
        }
        for k, v in comp.items():
            assert isinstance(v, (int, float)), f"composantes.{k} pas numerique"

        # ISO date parse OK
        datetime.fromisoformat(data["periode_debut"])
        datetime.fromisoformat(data["periode_fin"])
    finally:
        app.dependency_overrides.clear()
