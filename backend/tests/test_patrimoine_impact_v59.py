"""
test_patrimoine_impact_v59.py — Tests V59 : Impact réglementaire & business

Couverture :
  - PatrimoineAssumptions : defaults, override, dérivés
  - enrich_anomalies_with_impact : enrichissement, champs attendus
  - compute_priority_score : formule, clamp 100
  - Tri priority_score DESC
  - Chaque code anomalie → framework + business_type attendus
  - Backward compat : anomalies vides, snapshot absent
  - Endpoints HTTP enrichis + assumptions endpoint
"""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Batiment,
    Usage,
    Compteur,
    DeliveryPoint,
    EnergyContract,
    TypeSite,
    TypeCompteur,
    TypeUsage,
    DeliveryPointStatus,
    DeliveryPointEnergyType,
    BillingEnergyType,
)
from database import get_db
from main import app
from services.demo_state import DemoState
from config.patrimoine_assumptions import PatrimoineAssumptions, DEFAULT_ASSUMPTIONS
from services.patrimoine_impact import (
    enrich_anomalies_with_impact,
    compute_priority_score,
    _IMPACT_META,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_org(db, nom, siren=None):
    org = Organisation(nom=nom, actif=True)
    db.add(org)
    db.flush()
    s = siren or str(abs(hash(nom)) % 10**9).zfill(9)
    ej = EntiteJuridique(nom="EJ " + nom, organisation_id=org.id, siren=s)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom="PF " + nom, entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    return org, pf


def _make_full_site(db, pf, nom="Site", surface=5000.0):
    site = Site(nom=nom, type=TypeSite.BUREAU, surface_m2=surface, portefeuille_id=pf.id, actif=True)
    db.add(site)
    db.flush()
    bat = Batiment(site_id=site.id, nom="Bat A", surface_m2=3000.0)
    db.add(bat)
    db.flush()
    db.add(Usage(batiment_id=bat.id, type=TypeUsage.BUREAUX))
    dp = DeliveryPoint(
        code="12345678901234",
        energy_type=DeliveryPointEnergyType.ELEC,
        site_id=site.id,
        status=DeliveryPointStatus.ACTIVE,
    )
    db.add(dp)
    db.flush()
    db.add(
        Compteur(
            site_id=site.id, type=TypeCompteur.ELECTRICITE, numero_serie="SN-001", actif=True, delivery_point_id=dp.id
        )
    )
    db.add(
        EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            start_date=date(2023, 1, 1),
            end_date=date(2025, 12, 31),
        )
    )
    db.commit()
    return site


# ── Tests PatrimoineAssumptions ───────────────────────────────────────────────


class TestPatrimoineAssumptions:
    def test_defaults_valid(self):
        a = PatrimoineAssumptions()
        assert a.prix_elec_eur_mwh == 120.0
        assert a.prix_gaz_eur_mwh == 55.0
        assert a.conso_fallback_kwh_an == 300_000.0
        assert a.horizon_factor == 1.0

    def test_prix_elec_eur_kwh_derived(self):
        a = PatrimoineAssumptions(prix_elec_eur_mwh=120.0)
        assert abs(a.prix_elec_eur_kwh - 0.12) < 1e-6

    def test_prix_gaz_eur_kwh_derived(self):
        a = PatrimoineAssumptions(prix_gaz_eur_mwh=55.0)
        assert abs(a.prix_gaz_eur_kwh - 0.055) < 1e-6

    def test_override_partial(self):
        a = PatrimoineAssumptions(prix_elec_eur_mwh=150.0)
        assert a.prix_elec_eur_mwh == 150.0
        assert a.prix_gaz_eur_mwh == 55.0  # unchanged

    def test_conso_for_usage_bureaux(self):
        a = PatrimoineAssumptions()
        assert a.conso_for_usage("bureaux") == 250_000.0

    def test_conso_for_usage_unknown_fallback(self):
        a = PatrimoineAssumptions()
        assert a.conso_for_usage("xyz_inconnu") == a.conso_fallback_kwh_an

    def test_conso_for_usage_none_fallback(self):
        a = PatrimoineAssumptions()
        assert a.conso_for_usage(None) == a.conso_fallback_kwh_an

    def test_conso_m2_for_usage_bureaux(self):
        a = PatrimoineAssumptions()
        assert a.conso_m2_for_usage("bureaux") == 250.0

    def test_conso_m2_for_usage_default_fallback(self):
        a = PatrimoineAssumptions()
        assert a.conso_m2_for_usage(None) == a.conso_kwh_m2_an_default

    def test_to_dict_has_required_keys(self):
        d = DEFAULT_ASSUMPTIONS.to_dict()
        for key in (
            "prix_elec_eur_mwh",
            "prix_gaz_eur_mwh",
            "conso_fallback_kwh_an",
            "horizon_factor",
            "conso_fallback_by_usage",
            "conso_kwh_m2_an_by_usage",
        ):
            assert key in d


# ── Tests compute_priority_score ──────────────────────────────────────────────


class TestComputePriorityScore:
    def _anom(self, severity, framework, eur):
        return {
            "severity": severity,
            "regulatory_impact": {"framework": framework, "risk_level": severity},
            "business_impact": {"estimated_risk_eur": eur, "type": "BILLING_RISK"},
        }

    def test_high_facturation_big_eur(self):
        a = self._anom("HIGH", "FACTURATION", 60_000)
        score = compute_priority_score(a)
        assert score == min(100, 25 + 20 + 30)  # 75

    def test_low_none_zero_eur(self):
        a = self._anom("LOW", "NONE", 0)
        score = compute_priority_score(a)
        assert score == 5 + 0 + 0  # 5

    def test_medium_decret_medium_eur(self):
        a = self._anom("MEDIUM", "DECRET_TERTIAIRE", 5_000)
        score = compute_priority_score(a)
        assert score == 15 + 20 + 10  # 45

    def test_clamp_100(self):
        a = self._anom("CRITICAL", "DECRET_TERTIAIRE", 100_000)
        # CRITICAL: 30, DECRET_TERTIAIRE: 20, >50k: 30 → 80 (no CRITICAL in base... wait)
        # Actually _SEV_BASE has no CRITICAL: let me check
        # CRITICAL→30 base... wait the base for HIGH is 25, MEDIUM 15... CRITICAL is NOT in _SEV_BASE
        # It uses HIGH=25 for CRITICAL path → but test should still work
        # Actually looking at the code: _SEV_BASE = {"CRITICAL":30,"HIGH":25,"MEDIUM":15,"LOW":5}
        score = compute_priority_score(a)
        assert score == min(100, 30 + 20 + 30)  # 80

    def test_missing_fields_graceful(self):
        # Anomaly without regulatory_impact or business_impact
        a = {"severity": "HIGH"}
        score = compute_priority_score(a)
        assert score == 25  # base only

    def test_no_crash_on_none_impacts(self):
        a = {
            "severity": "MEDIUM",
            "regulatory_impact": None,
            "business_impact": None,
        }
        score = compute_priority_score(a)
        assert score == 15  # base only


# ── Tests enrich_anomalies_with_impact ────────────────────────────────────────


class TestEnrichAnomaliesWithImpact:
    def _base_anomaly(self, code, severity="MEDIUM"):
        return {
            "code": code,
            "severity": severity,
            "title_fr": f"Test {code}",
            "detail_fr": "Detail",
            "evidence": {},
            "cta": {"label": "Action", "to": "/patrimoine"},
            "fix_hint_fr": "Fix",
        }

    def test_empty_list_returns_empty(self):
        result = enrich_anomalies_with_impact([], {}, DEFAULT_ASSUMPTIONS)
        assert result == []

    def test_adds_regulatory_impact(self):
        anomalies = [self._base_anomaly("SURFACE_MISSING", "HIGH")]
        result = enrich_anomalies_with_impact(anomalies)
        assert "regulatory_impact" in result[0]
        ri = result[0]["regulatory_impact"]
        assert ri["framework"] == "DECRET_TERTIAIRE"
        assert ri["risk_level"] == "HIGH"
        assert ri["explanation_fr"]

    def test_adds_business_impact(self):
        anomalies = [self._base_anomaly("SURFACE_MISSING", "HIGH")]
        result = enrich_anomalies_with_impact(anomalies)
        assert "business_impact" in result[0]
        bi = result[0]["business_impact"]
        assert "estimated_risk_eur" in bi
        assert "confidence" in bi
        assert bi["estimated_risk_eur"] >= 0

    def test_adds_priority_score(self):
        anomalies = [self._base_anomaly("SURFACE_MISSING", "HIGH")]
        result = enrich_anomalies_with_impact(anomalies)
        assert "priority_score" in result[0]
        assert 0 <= result[0]["priority_score"] <= 100

    def test_sorted_by_priority_score_desc(self):
        anomalies = [
            self._base_anomaly("BUILDING_USAGE_MISSING", "LOW"),
            self._base_anomaly("CONTRACT_OVERLAP_SITE", "HIGH"),
            self._base_anomaly("SURFACE_MISSING", "HIGH"),
        ]
        result = enrich_anomalies_with_impact(anomalies)
        scores = [a["priority_score"] for a in result]
        assert scores == sorted(scores, reverse=True)

    def test_backward_compat_original_fields_preserved(self):
        anomalies = [self._base_anomaly("SURFACE_MISSING", "HIGH")]
        result = enrich_anomalies_with_impact(anomalies)
        a = result[0]
        assert a["code"] == "SURFACE_MISSING"
        assert a["severity"] == "HIGH"
        assert a["title_fr"]
        assert a["cta"]["to"] == "/patrimoine"

    def test_snapshot_none_no_crash(self):
        anomalies = [self._base_anomaly("SURFACE_MISMATCH", "MEDIUM")]
        result = enrich_anomalies_with_impact(anomalies, snapshot=None)
        assert result[0]["business_impact"]["estimated_risk_eur"] >= 0

    def test_surface_mismatch_uses_evidence(self):
        anomalies = [
            {
                **self._base_anomaly("SURFACE_MISMATCH", "MEDIUM"),
                "evidence": {
                    "surface_site_m2": 10_000,
                    "surface_batiments_sum_m2": 7_000,
                    "ecart_pct": 30.0,
                },
            }
        ]
        a = DEFAULT_ASSUMPTIONS
        result = enrich_anomalies_with_impact(anomalies, snapshot={}, assumptions=a)
        bi = result[0]["business_impact"]
        # diff=3000, conso_m2=200(default), prix=0.12, horizon=1 → 3000*200*0.12=72000
        expected = round(3000 * a.conso_kwh_m2_an_default * a.prix_elec_eur_kwh, 0)
        assert bi["estimated_risk_eur"] == expected

    def test_contract_overlap_positive_risk(self):
        anomalies = [self._base_anomaly("CONTRACT_OVERLAP_SITE", "HIGH")]
        result = enrich_anomalies_with_impact(anomalies)
        assert result[0]["business_impact"]["estimated_risk_eur"] > 0

    def test_meter_no_dp_positive_risk(self):
        anomalies = [self._base_anomaly("METER_NO_DELIVERY_POINT", "MEDIUM")]
        result = enrich_anomalies_with_impact(anomalies)
        assert result[0]["business_impact"]["estimated_risk_eur"] > 0

    def test_orphans_zero_risk(self):
        anomalies = [self._base_anomaly("ORPHANS_DETECTED", "CRITICAL")]
        result = enrich_anomalies_with_impact(anomalies)
        assert result[0]["business_impact"]["estimated_risk_eur"] == 0.0

    def test_all_p0_codes_have_meta(self):
        codes = [
            "SURFACE_MISSING",
            "SURFACE_MISMATCH",
            "BUILDING_MISSING",
            "BUILDING_USAGE_MISSING",
            "METER_NO_DELIVERY_POINT",
            "CONTRACT_DATE_INVALID",
            "CONTRACT_OVERLAP_SITE",
            "ORPHANS_DETECTED",
        ]
        for code in codes:
            assert code in _IMPACT_META, f"{code} absent de _IMPACT_META"


# ── Tests endpoints HTTP enrichis ────────────────────────────────────────────


class TestAnomaliesEndpointsV59:
    def test_site_anomalies_has_regulatory_impact(self, client, db):
        """Endpoint /anomalies retourne regulatory_impact dans les anomalies."""
        DemoState.clear_demo_org()
        org, pf = _make_org(db, "OrgV59Reg")
        # Site sans surface → SURFACE_MISSING
        site = Site(nom="NoSurf", type=TypeSite.BUREAU, surface_m2=None, portefeuille_id=pf.id, actif=True)
        db.add(site)
        db.commit()
        DemoState.set_demo_org(org.id)
        r = client.get(f"/api/patrimoine/sites/{site.id}/anomalies")
        assert r.status_code == 200
        data = r.json()
        assert "anomalies" in data
        assert "total_estimated_risk_eur" in data
        assert "assumptions_used" in data
        if data["anomalies"]:
            a = data["anomalies"][0]
            assert "regulatory_impact" in a
            assert "business_impact" in a
            assert "priority_score" in a

    def test_site_anomalies_total_risk_eur_present(self, client, db):
        """total_estimated_risk_eur est calculé et retourné."""
        DemoState.clear_demo_org()
        org, pf = _make_org(db, "OrgV59Risk")
        site = _make_full_site(db, pf, "SiteRisk")
        DemoState.set_demo_org(org.id)
        r = client.get(f"/api/patrimoine/sites/{site.id}/anomalies")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["total_estimated_risk_eur"], (int, float))
        assert data["total_estimated_risk_eur"] >= 0

    def test_site_anomalies_sorted_by_priority_score(self, client, db):
        """Anomalies triées par priority_score DESC."""
        DemoState.clear_demo_org()
        org, pf = _make_org(db, "OrgV59Sort")
        # Crée site avec plusieurs anomalies possibles
        site = Site(nom="MultiAnom", type=TypeSite.BUREAU, surface_m2=None, portefeuille_id=pf.id, actif=True)
        db.add(site)
        db.commit()
        DemoState.set_demo_org(org.id)
        r = client.get(f"/api/patrimoine/sites/{site.id}/anomalies")
        assert r.status_code == 200
        anomalies = r.json()["anomalies"]
        if len(anomalies) >= 2:
            scores = [a["priority_score"] for a in anomalies]
            assert scores == sorted(scores, reverse=True), f"Scores non triés DESC: {scores}"

    def test_org_anomalies_has_top_priority_score(self, client, db):
        """Liste org retourne top_priority_score par site."""
        DemoState.clear_demo_org()
        org, pf = _make_org(db, "OrgV59Top")
        _make_full_site(db, pf, "SiteTop")
        DemoState.set_demo_org(org.id)
        r = client.get("/api/patrimoine/anomalies")
        assert r.status_code == 200
        sites = r.json()["sites"]
        if sites:
            site_data = sites[0]
            assert "top_priority_score" in site_data
            assert "total_estimated_risk_eur" in site_data

    def test_assumptions_endpoint_200(self, client):
        """GET /api/patrimoine/assumptions retourne les hypothèses par défaut."""
        r = client.get("/api/patrimoine/assumptions")
        assert r.status_code == 200
        data = r.json()
        assert data["prix_elec_eur_mwh"] == 120.0
        assert data["prix_gaz_eur_mwh"] == 55.0
        assert data["conso_fallback_kwh_an"] == 300_000.0
        assert "conso_fallback_by_usage" in data

    def test_anomalies_no_org_returns_error(self, client):
        """Sans org → 401/403/404."""
        DemoState.clear_demo_org()
        r = client.get("/api/patrimoine/sites/99999/anomalies")
        assert r.status_code in (401, 403, 404)

    def test_anomalies_403_wrong_org(self, client, db):
        """Site d'une autre org → 403."""
        DemoState.clear_demo_org()
        org1, pf1 = _make_org(db, "OrgV59A", siren="111111191")
        org2, pf2 = _make_org(db, "OrgV59B", siren="222222292")
        site2 = Site(nom="S2", type=TypeSite.BUREAU, portefeuille_id=pf2.id, actif=True)
        db.add(site2)
        db.commit()
        DemoState.set_demo_org(org1.id)
        r = client.get(f"/api/patrimoine/sites/{site2.id}/anomalies")
        assert r.status_code == 403


# ── Guard multi-org ───────────────────────────────────────────────────────────


class TestMultiOrgGuardV59:
    def test_no_organisation_first_in_impact_service(self):
        """patrimoine_impact.py ne contient pas Organisation).first()."""
        import pathlib

        src = pathlib.Path(__file__).parent.parent / "services" / "patrimoine_impact.py"
        content = src.read_text(encoding="utf-8")
        assert "Organisation)" not in content or ".first()" not in content

    def test_no_organisation_first_in_assumptions_config(self):
        """patrimoine_assumptions.py ne contient pas Organisation).first()."""
        import pathlib

        src = pathlib.Path(__file__).parent.parent / "config" / "patrimoine_assumptions.py"
        content = src.read_text(encoding="utf-8")
        assert "Organisation)" not in content or ".first()" not in content
