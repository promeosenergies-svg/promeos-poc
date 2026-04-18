"""
PROMEOS — Tests endpoint GET /api/purchase/cost-simulation/{site_id}.

Découplé du service `simulate_annual_cost_2026` (testé dans
`test_achat_cost_simulator_2026.py`) via monkeypatch sur sys.modules.
Pattern repris de `test_pilotage_nebco_endpoint.py` (Vague 2).
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from middleware.auth import AuthContext, get_optional_auth
from models import Base


# ───────────────────────── Fixtures ─────────────────────────


@pytest.fixture
def _fake_cost_simulation():
    """Payload retourné par le service — reflète le schéma Pydantic exact.

    Toute modification de `CostHypotheses` / `Baseline2024` doit être
    répercutée ici pour éviter une dérive contrat service↔endpoint.
    """
    return {
        "site_id": "42",
        "year": 2026,
        "facture_totale_eur": 950_000.0,
        "energie_annuelle_mwh": 12500.0,
        "composantes": {
            "fourniture_eur": 750000.0,
            "turpe_eur": 80000.0,
            "vnu_eur": 0.0,
            "capacite_eur": 5375.0,
            "cbam_scope": 0.0,
            "accise_cta_tva_eur": 114625.0,
        },
        "hypotheses": {
            "prix_forward_y1_eur_mwh": 60.0,
            "facteur_forme": 0.30,
            "peakload_multiplier": 1.105,
            "peak_premium_ratio": 0.15,
            "capacite_unitaire_eur_mwh": 0.43,
            "capacite_source_ref": "billing_engine/catalog.py::CAPACITE_ELEC (0.43 EUR/MWh)",
            "vnu_statut": "dormant",
            "vnu_seuil_active_eur_mwh": 78.0,
            "vnu_source_ref": None,
            "vnu_note": "VNU = taxe redistributive sur EDF, pas sur le consommateur final.",
            "vnu_risque_upside_eur_mwh": 0.0,
            "archetype": "BUREAU_STANDARD",
            "turpe_segment": "C4_BT",
            "turpe_energie_eur_kwh": 0.0390,
            "turpe_gestion_eur_mois": 30.60,
            "turpe_comptage_eur_an": 283.27,
            "turpe_soutirage_eur_an": 1725.0,
            "p_souscrite_kva_estimee": 115.0,
            "accise_code_resolu": "ACCISE_ELEC",
            "accise_eur_kwh": 0.02658,
            "cta_rate": 0.15,
            "tva_rate": 0.20,
            "baseline_2024_eur_mwh": 80.0,
            "comparabilite_baseline": "delta cadré HT énergie pure.",
            "annual_kwh_resolu": 12_500_000.0,
            "cbam_note": "CBAM non applicable à la conso électrique directe.",
            "source_calibration": [],
        },
        "baseline_2024": {
            "fourniture_ht_eur": 1_000_000.0,
            "prix_moyen_pondere_eur_mwh": 80.0,
            "methode": "ARENH 42 EUR/MWh × 50 % + complément spot moyen 2024 — MVP.",
            "delta_fourniture_ht_pct": -25.0,
        },
        "delta_vs_2024_pct": -25.0,
        "confiance": "indicative",
        "source": ("Post-ARENH 01/01/2026 + TURPE 7 + VNU CRE + RTE capacité PL-4/PL-1 Nov 2026"),
    }


@pytest.fixture
def _site_org_factory():
    """
    Factory : retourne `(client, db, site, auth_override)` prêt à tester.
    SQLite in-memory + 1 Site rattaché à une Organisation.
    """

    def _build(org_id: int = 1, other_org_id: int | None = None):
        from models import EntiteJuridique, Organisation, Portefeuille, Site
        from models.enums import TypeSite

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        org = Organisation(nom=f"Org {org_id}", siren=f"{1000000 + org_id}")
        db.add(org)
        db.flush()
        entite = EntiteJuridique(nom="E", siren=f"{1000000 + org_id}", organisation_id=org.id)
        db.add(entite)
        db.flush()
        ptf = Portefeuille(nom="P", entite_juridique_id=entite.id)
        db.add(ptf)
        db.flush()
        site = Site(
            nom="Site Achat Test",
            type=TypeSite.BUREAU,
            portefeuille_id=ptf.id,
            actif=True,
            annual_kwh_total=12_500_000,
        )
        db.add(site)
        db.flush()

        def _override_db():
            yield db

        app.dependency_overrides[get_db] = _override_db

        # Auth factice : org_id = other_org_id si fourni (cas hors scope), sinon org.id
        effective_auth = AuthContext(
            user=None,
            user_org_role=None,
            org_id=(other_org_id if other_org_id is not None else org.id),
            role=None,
            site_ids=[site.id],
        )
        app.dependency_overrides[get_optional_auth] = lambda: effective_auth

        client = TestClient(app, raise_server_exceptions=False)
        return client, db, site, org

    yield _build

    app.dependency_overrides.clear()


# ───────────────────────── Tests ─────────────────────────


def test_endpoint_site_reel_numerique_200(_site_org_factory, _fake_cost_simulation):
    """Site.id numérique scope correct + mock service → 200 + payload complet."""
    client, _, site, _ = _site_org_factory()
    _fake_cost_simulation["site_id"] = str(site.id)

    # Stub le service appelé à l'intérieur du handler (import tardif)
    import services.purchase.cost_simulator_2026 as cost_mod

    with patch.object(cost_mod, "simulate_annual_cost_2026", return_value=_fake_cost_simulation):
        r = client.get(f"/api/purchase/cost-simulation/{site.id}?year=2026")

    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    data = r.json()
    assert data["site_id"] == str(site.id)
    assert data["year"] == 2026
    assert "fourniture_eur" in data["composantes"]
    assert data["composantes"]["fourniture_eur"] == 750000.0
    assert data["hypotheses"]["capacite_unitaire_eur_mwh"] == 0.43
    assert "billing_engine/catalog" in data["hypotheses"]["capacite_source_ref"]
    assert "prix_forward_y1_eur_mwh" in data["hypotheses"]
    assert data["confiance"] == "indicative"
    assert "Post-ARENH" in data["source"]


def test_endpoint_site_hors_scope_404(_site_org_factory, _fake_cost_simulation):
    """Auth org_id différent du site → 404 (anti-énumération, pas 403)."""
    # Org 9999 demande un site appartenant à Org 1
    client, _, site, _ = _site_org_factory(org_id=1, other_org_id=9999)

    r = client.get(f"/api/purchase/cost-simulation/{site.id}")
    assert r.status_code == 404
    payload = r.json()
    msg = payload.get("detail") or payload.get("message") or ""
    assert "introuvable" in msg.lower() or "hors scope" in msg.lower(), f"Message 404 inattendu : {payload!r}"


@pytest.mark.parametrize("bad_year", [2020, 2025, 2031, 2100])
def test_endpoint_year_validation_422(_site_org_factory, bad_year):
    """Pydantic Query ge=2026 le=2030 → 422 sur années hors bornes."""
    client, _, site, _ = _site_org_factory()
    r = client.get(f"/api/purchase/cost-simulation/{site.id}?year={bad_year}")
    assert r.status_code == 422


@pytest.mark.parametrize("good_year", [2026, 2028, 2030])
def test_endpoint_year_acceptees(_site_org_factory, _fake_cost_simulation, good_year):
    """Années 2026, 2028, 2030 acceptées (bornes ge=2026, le=2030)."""
    client, _, site, _ = _site_org_factory()
    _fake_cost_simulation["year"] = good_year

    import services.purchase.cost_simulator_2026 as cost_mod

    with patch.object(cost_mod, "simulate_annual_cost_2026", return_value=_fake_cost_simulation):
        r = client.get(f"/api/purchase/cost-simulation/{site.id}?year={good_year}")
    assert r.status_code == 200
    assert r.json()["year"] == good_year


def test_endpoint_demo_site_key_404_explicite(_site_org_factory):
    """
    Doctrine : les clés DEMO_SITES (non numériques) ne sont pas supportées car
    le chiffrage dépend d'annual_kwh réel. 404 explicite avec message guide.
    """
    client, _, _, _ = _site_org_factory()
    r = client.get("/api/purchase/cost-simulation/retail-001")
    assert r.status_code == 404
    payload = r.json()
    msg = payload.get("detail") or payload.get("message") or ""
    # Le message doit guider l'utilisateur vers la bonne utilisation
    assert "réel" in msg.lower() or "annual_kwh" in msg.lower() or "DEMO" in msg, (
        f"Message 404 non-pédagogique : {payload!r}"
    )


def test_endpoint_schema_pydantic_exhaustif(_site_org_factory, _fake_cost_simulation):
    """Valide la structure complète du payload (tous champs requis présents)."""
    client, _, site, _ = _site_org_factory()
    _fake_cost_simulation["site_id"] = str(site.id)

    import services.purchase.cost_simulator_2026 as cost_mod

    with patch.object(cost_mod, "simulate_annual_cost_2026", return_value=_fake_cost_simulation):
        r = client.get(f"/api/purchase/cost-simulation/{site.id}")

    data = r.json()
    # Top-level
    for key in (
        "site_id",
        "year",
        "facture_totale_eur",
        "energie_annuelle_mwh",
        "composantes",
        "hypotheses",
        "baseline_2024",
        "delta_vs_2024_pct",
        "confiance",
        "source",
    ):
        assert key in data, f"champ top-level manquant : {key}"

    # Composantes : les 6 catégories réglementaires 2026+
    for key in (
        "fourniture_eur",
        "turpe_eur",
        "vnu_eur",
        "capacite_eur",
        "cbam_scope",
        "accise_cta_tva_eur",
    ):
        assert key in data["composantes"], f"composante manquante : {key}"
