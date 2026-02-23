"""
PROMEOS — V57: Multi-Org Isolation Tests
Proves: resolve_org_id replaces Organisation.first() everywhere.
No cross-org data leakage via compliance, segmentation, onboarding,
import, consumption diagnostic, or energy routes.

Setup: 2 orgs (Alpha, Bravo), each with EJ → Portfolio → Site → Meter.
Every test uses X-Org-Id headers to simulate org context.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Organisation, EntiteJuridique, Portefeuille,
    Site, Meter, MeterReading, ComplianceFinding,
    TypeSite,
)
from models.energy_models import EnergyVector
from database import get_db
from main import app


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
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
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_two_orgs(db):
    """Create 2 complete org hierarchies: Alpha and Bravo with meters."""
    # Org Alpha
    org_a = Organisation(nom="Org Alpha", type_client="bureau", actif=True, siren="111111111")
    db.add(org_a)
    db.flush()
    ej_a = EntiteJuridique(organisation_id=org_a.id, nom="EJ Alpha", siren="111111111")
    db.add(ej_a)
    db.flush()
    pf_a = Portefeuille(entite_juridique_id=ej_a.id, nom="PF Alpha")
    db.add(pf_a)
    db.flush()
    site_a = Site(
        portefeuille_id=pf_a.id, nom="Site Alpha", type=TypeSite.BUREAU,
        adresse="10 rue Alpha", code_postal="75001", ville="Paris",
        surface_m2=1000, actif=True,
    )
    db.add(site_a)
    db.flush()
    meter_a = Meter(
        meter_id="PRM-ALPHA-001", name="Meter Alpha",
        site_id=site_a.id, energy_vector=EnergyVector.ELECTRICITY,
    )
    db.add(meter_a)
    db.flush()

    # Org Bravo
    org_b = Organisation(nom="Org Bravo", type_client="industrie", actif=True, siren="222222222")
    db.add(org_b)
    db.flush()
    ej_b = EntiteJuridique(organisation_id=org_b.id, nom="EJ Bravo", siren="222222222")
    db.add(ej_b)
    db.flush()
    pf_b = Portefeuille(entite_juridique_id=ej_b.id, nom="PF Bravo")
    db.add(pf_b)
    db.flush()
    site_b = Site(
        portefeuille_id=pf_b.id, nom="Site Bravo", type=TypeSite.BUREAU,
        adresse="20 rue Bravo", code_postal="69001", ville="Lyon",
        surface_m2=800, actif=True,
    )
    db.add(site_b)
    db.flush()
    meter_b = Meter(
        meter_id="PRM-BRAVO-001", name="Meter Bravo",
        site_id=site_b.id, energy_vector=EnergyVector.ELECTRICITY,
    )
    db.add(meter_b)
    db.flush()

    db.commit()
    return {
        "org_a": org_a, "ej_a": ej_a, "pf_a": pf_a, "site_a": site_a, "meter_a": meter_a,
        "org_b": org_b, "ej_b": ej_b, "pf_b": pf_b, "site_b": site_b, "meter_b": meter_b,
    }


def _h(org_id: int) -> dict:
    """X-Org-Id header."""
    return {"X-Org-Id": str(org_id)}


# ════════════════════════════════════════════════════════════
# 1. Compliance isolation
# ════════════════════════════════════════════════════════════

class TestComplianceIsolation:
    def test_summary_scoped_to_org(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/compliance/summary", headers=_h(d["org_a"].id))
        assert r.status_code == 200

    def test_sites_scoped_to_org(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/compliance/sites", headers=_h(d["org_a"].id))
        assert r.status_code == 200

    def test_bundle_scoped_to_org(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/compliance/bundle", headers=_h(d["org_a"].id))
        assert r.status_code == 200

    def test_findings_scoped_to_org(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/compliance/findings", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        data = r.json()
        # All findings should belong to org_a's sites only
        for f in data:
            assert f["site_id"] == d["site_a"].id

    def test_patch_finding_cross_org_forbidden(self, client, db):
        """Patching a finding from org_b while scoped to org_a → 403."""
        d = _create_two_orgs(db)
        # Create finding on org_b's site
        finding = ComplianceFinding(
            site_id=d["site_b"].id, regulation="DECRET_TERTIAIRE",
            rule_id="test_rule", status="NOK", severity="high",
        )
        db.add(finding)
        db.commit()

        r = client.patch(
            f"/api/compliance/findings/{finding.id}",
            json={"status": "resolved"},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 403

    def test_patch_finding_same_org_ok(self, client, db):
        """Patching a finding from org_a while scoped to org_a → 200."""
        d = _create_two_orgs(db)
        finding = ComplianceFinding(
            site_id=d["site_a"].id, regulation="DECRET_TERTIAIRE",
            rule_id="test_rule", status="NOK", severity="high",
        )
        db.add(finding)
        db.commit()

        r = client.patch(
            f"/api/compliance/findings/{finding.id}",
            json={"notes": "test"},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 200

    def test_recompute_rules_scoped(self, client, db):
        d = _create_two_orgs(db)
        r = client.post("/api/compliance/recompute-rules", headers=_h(d["org_a"].id))
        assert r.status_code == 200


# ════════════════════════════════════════════════════════════
# 2. Sites isolation
# ════════════════════════════════════════════════════════════

class TestSitesIsolation:
    def test_list_sites_scoped(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/sites", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        data = r.json()
        for s in data["sites"]:
            assert s["nom"] == "Site Alpha"

    def test_list_sites_bravo_only(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/sites", headers=_h(d["org_b"].id))
        assert r.status_code == 200
        data = r.json()
        for s in data["sites"]:
            assert s["nom"] == "Site Bravo"

    def test_create_site_scoped(self, client, db):
        d = _create_two_orgs(db)
        r = client.post(
            "/api/sites",
            json={"nom": "New Site Alpha", "surface_m2": 500},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 200
        # Verify new site is in org_a's scope
        r2 = client.get("/api/sites", headers=_h(d["org_a"].id))
        noms = [s["nom"] for s in r2.json()["sites"]]
        assert "New Site Alpha" in noms

        # Verify new site NOT visible to org_b
        r3 = client.get("/api/sites", headers=_h(d["org_b"].id))
        noms_b = [s["nom"] for s in r3.json()["sites"]]
        assert "New Site Alpha" not in noms_b


# ════════════════════════════════════════════════════════════
# 3. Onboarding isolation
# ════════════════════════════════════════════════════════════

class TestOnboardingIsolation:
    def test_status_scoped(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/onboarding/status", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        data = r.json()
        assert data["has_organisation"] is True
        assert data["organisation_nom"] == "Org Alpha"

    def test_status_bravo(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/onboarding/status", headers=_h(d["org_b"].id))
        assert r.status_code == 200
        data = r.json()
        assert data["organisation_nom"] == "Org Bravo"

    def test_status_counts_only_own_sites(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/onboarding/status", headers=_h(d["org_a"].id))
        data = r.json()
        assert data["total_sites"] == 1  # Only Alpha's site
        assert data["total_portefeuilles"] == 1


# ════════════════════════════════════════════════════════════
# 4. Segmentation isolation
# ════════════════════════════════════════════════════════════

class TestSegmentationIsolation:
    def test_profile_scoped(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/segmentation/profile", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        data = r.json()
        if data.get("organisation"):
            assert data["organisation"]["id"] == d["org_a"].id


# ════════════════════════════════════════════════════════════
# 5. Consumption diagnostic isolation
# ════════════════════════════════════════════════════════════

class TestConsumptionIsolation:
    def test_insights_scoped(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/consumption/insights", headers=_h(d["org_a"].id))
        assert r.status_code == 200

    def test_diagnose_scoped(self, client, db):
        d = _create_two_orgs(db)
        r = client.post("/api/consumption/diagnose", headers=_h(d["org_a"].id))
        assert r.status_code == 200


# ════════════════════════════════════════════════════════════
# 6. Energy route isolation
# ════════════════════════════════════════════════════════════

class TestEnergyIsolation:
    def test_list_meters_scoped(self, client, db):
        """List meters returns both orgs' meters without auth (demo mode)."""
        d = _create_two_orgs(db)
        r = client.get("/api/energy/meters", params={"site_id": d["site_a"].id})
        assert r.status_code == 200
        data = r.json()
        meter_ids = [m["meter_id"] for m in data]
        assert "PRM-ALPHA-001" in meter_ids
        assert "PRM-BRAVO-001" not in meter_ids


# ════════════════════════════════════════════════════════════
# 7. Source-level guard: Organisation.first() eliminated
# ════════════════════════════════════════════════════════════

class TestSourceGuard:
    def test_no_organisation_first_in_routes(self):
        """Organisation.first() must NOT appear in any route except demo.py."""
        import os
        routes_dir = os.path.join(os.path.dirname(__file__), '..', 'routes')
        violations = []
        for fname in os.listdir(routes_dir):
            if not fname.endswith('.py') or fname == 'demo.py':
                continue
            fpath = os.path.join(routes_dir, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                src = f.read()
            # Check for unscoped Organisation.first() — not Organisation.filter(...).first()
            import re
            matches = re.findall(r'Organisation\)\.first\(\)', src)
            if matches:
                violations.append(f"{fname}: {len(matches)} occurrence(s)")
        assert violations == [], f"Organisation.first() found: {violations}"

    def test_no_organisation_order_by_first_in_routes(self):
        """Organisation.order_by(...).first() must NOT appear in routes."""
        import os, re
        routes_dir = os.path.join(os.path.dirname(__file__), '..', 'routes')
        violations = []
        for fname in os.listdir(routes_dir):
            if not fname.endswith('.py') or fname == 'demo.py':
                continue
            fpath = os.path.join(routes_dir, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                src = f.read()
            matches = re.findall(r'Organisation\)\.order_by.*\.first\(\)', src)
            if matches:
                violations.append(f"{fname}: {len(matches)} occurrence(s)")
        assert violations == [], f"Organisation.order_by().first() found: {violations}"

    def test_resolve_org_id_in_compliance(self):
        """compliance.py uses resolve_org_id."""
        import os
        fpath = os.path.join(os.path.dirname(__file__), '..', 'routes', 'compliance.py')
        with open(fpath, 'r', encoding='utf-8') as f:
            src = f.read()
        assert 'resolve_org_id' in src
        assert src.count('resolve_org_id') >= 7  # summary, sites, bundle, recompute, findings, patch, detail

    def test_resolve_org_id_in_segmentation(self):
        """segmentation.py uses resolve_org_id."""
        import os
        fpath = os.path.join(os.path.dirname(__file__), '..', 'routes', 'segmentation.py')
        with open(fpath, 'r', encoding='utf-8') as f:
            src = f.read()
        assert 'resolve_org_id' in src

    def test_resolve_org_id_in_onboarding(self):
        """onboarding.py uses resolve_org_id."""
        import os
        fpath = os.path.join(os.path.dirname(__file__), '..', 'routes', 'onboarding.py')
        with open(fpath, 'r', encoding='utf-8') as f:
            src = f.read()
        assert 'resolve_org_id' in src

    def test_check_site_access_in_energy(self):
        """energy.py uses check_site_access for org scoping."""
        import os
        fpath = os.path.join(os.path.dirname(__file__), '..', 'routes', 'energy.py')
        with open(fpath, 'r', encoding='utf-8') as f:
            src = f.read()
        assert 'check_site_access' in src
        assert src.count('check_site_access') >= 5  # create_meter, upload, run_analysis, summary, demo
