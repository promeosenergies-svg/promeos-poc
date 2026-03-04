"""
PROMEOS - Tests DIAMANT: Patrimoine Wizard (staging pipeline, quality gate, activation, N-N links).
~25 tests covering: N-N links, staging pipeline, quality rules, corrections, activation, demo, lineage.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Compteur,
    OrgEntiteLink,
    PortfolioEntiteLink,
    StagingBatch,
    StagingSite,
    StagingCompteur,
    QualityFinding,
    StagingStatus,
    ImportSourceType,
    QualityRuleSeverity,
    TypeSite,
    TypeCompteur,
    EnergyVector,
)
from database import get_db
from main import app
from services.patrimoine_service import (
    create_staging_batch,
    import_csv_to_staging,
    import_invoices_to_staging,
    get_staging_summary,
    run_quality_gate,
    apply_fix,
    activate_batch,
    get_diff_plan,
    compute_content_hash,
    abandon_batch,
)
from services.quality_rules import (
    check_duplicate_sites,
    check_duplicate_meters,
    check_orphan_meters,
    check_incomplete_sites,
    check_missing_entity,
    run_all_rules,
)


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def db_session():
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
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_org(db_session):
    """Create minimal org hierarchy for testing."""
    org = Organisation(nom="Test Org", type_client="bureau", actif=True, siren="123456789")
    db_session.add(org)
    db_session.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="Test EJ", siren="123456789")
    db_session.add(ej)
    db_session.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF Test", description="Test")
    db_session.add(pf)
    db_session.flush()

    return org, ej, pf


def _create_batch_with_data(db_session, org_id=None):
    """Create a staging batch with 2 sites and 3 compteurs."""
    batch = create_staging_batch(
        db_session,
        org_id=org_id,
        user_id=None,
        source_type=ImportSourceType.CSV,
        mode="import",
    )

    s1 = StagingSite(
        batch_id=batch.id,
        row_number=2,
        nom="Site Alpha",
        adresse="10 rue de la Paix",
        code_postal="75001",
        ville="Paris",
        surface_m2=1200,
    )
    s2 = StagingSite(
        batch_id=batch.id,
        row_number=3,
        nom="Site Beta",
        adresse="20 avenue des Champs",
        code_postal="75008",
        ville="Paris",
        surface_m2=800,
    )
    db_session.add_all([s1, s2])
    db_session.flush()

    c1 = StagingCompteur(
        batch_id=batch.id,
        staging_site_id=s1.id,
        numero_serie="PRM-001",
        meter_id="12345678901234",
        type_compteur="electricite",
        puissance_kw=60,
    )
    c2 = StagingCompteur(batch_id=batch.id, staging_site_id=s1.id, numero_serie="PRM-002", type_compteur="gaz")
    c3 = StagingCompteur(
        batch_id=batch.id, staging_site_id=s2.id, numero_serie="PRM-003", type_compteur="electricite", puissance_kw=36
    )
    db_session.add_all([c1, c2, c3])
    db_session.flush()

    return batch, [s1, s2], [c1, c2, c3]


# ========================================
# TestNNLinks (4 tests)
# ========================================


class TestNNLinks:
    def test_create_org_entite_link(self, db_session):
        org, ej, _ = _create_org(db_session)
        link = OrgEntiteLink(organisation_id=org.id, entite_juridique_id=ej.id, role="proprietaire", confidence=1.0)
        db_session.add(link)
        db_session.flush()
        assert link.id is not None
        assert link.role == "proprietaire"

    def test_unique_constraint_org_entite(self, db_session):
        org, ej, _ = _create_org(db_session)
        link1 = OrgEntiteLink(organisation_id=org.id, entite_juridique_id=ej.id, role="a")
        db_session.add(link1)
        db_session.flush()
        link2 = OrgEntiteLink(organisation_id=org.id, entite_juridique_id=ej.id, role="b")
        db_session.add(link2)
        with pytest.raises(Exception):
            db_session.flush()
        db_session.rollback()

    def test_portfolio_entite_link(self, db_session):
        org, ej, pf = _create_org(db_session)
        link = PortfolioEntiteLink(portefeuille_id=pf.id, entite_juridique_id=ej.id, role="gestionnaire")
        db_session.add(link)
        db_session.flush()
        assert link.id is not None

    def test_nn_link_with_role_and_dates(self, db_session):
        from datetime import date

        org, ej, _ = _create_org(db_session)
        link = OrgEntiteLink(
            organisation_id=org.id,
            entite_juridique_id=ej.id,
            role="locataire",
            confidence=0.8,
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            source_ref="contrat-2024-001",
        )
        db_session.add(link)
        db_session.flush()
        assert link.start_date == date(2024, 1, 1)
        assert link.source_ref == "contrat-2024-001"


# ========================================
# TestStagingPipeline (6 tests)
# ========================================


class TestStagingPipeline:
    def test_create_batch(self, db_session):
        batch = create_staging_batch(
            db_session,
            org_id=None,
            user_id=None,
            source_type=ImportSourceType.CSV,
            mode="import",
        )
        assert batch.id is not None
        assert batch.status == StagingStatus.DRAFT

    def test_import_csv_to_staging(self, db_session):
        batch = create_staging_batch(
            db_session,
            org_id=None,
            user_id=None,
            source_type=ImportSourceType.CSV,
            mode="import",
        )
        csv_content = (
            "nom,adresse,code_postal,ville,surface_m2,type,numero_serie,type_compteur,puissance_kw\n"
            "Bureau Paris,10 rue Paix,75002,Paris,1200,bureau,PRM-100,electricite,60\n"
            "Hotel Nice,Promenade,06000,Nice,800,,PRM-200,gaz,\n"
        ).encode("utf-8")

        result = import_csv_to_staging(db_session, batch.id, csv_content)
        assert result["sites_count"] == 2
        assert result["compteurs_count"] == 2
        assert len(result["parse_errors"]) == 0

    def test_staging_summary(self, db_session):
        batch, sites, compteurs = _create_batch_with_data(db_session)
        summary = get_staging_summary(db_session, batch.id)
        assert summary["sites"] == 2
        assert summary["compteurs"] == 3
        assert summary["batch_id"] == batch.id

    def test_activate_creates_final_entities(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch, sites, compteurs = _create_batch_with_data(db_session, org.id)

        # Run quality gate (should pass clean)
        run_quality_gate(db_session, batch.id)

        result = activate_batch(db_session, batch.id, pf.id)
        assert result["sites_created"] == 2
        assert result["compteurs_created"] == 3
        assert result["batiments"] == 2
        assert batch.status == StagingStatus.APPLIED

        # Verify real sites exist
        real_sites = db_session.query(Site).filter(Site.portefeuille_id == pf.id).all()
        assert len(real_sites) == 2

    def test_activate_idempotent(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch, _, _ = _create_batch_with_data(db_session, org.id)
        run_quality_gate(db_session, batch.id)
        activate_batch(db_session, batch.id, pf.id)

        # Second activation — idempotent, returns cached ActivationLog result
        result = activate_batch(db_session, batch.id, pf.id)
        assert "already applied" in result["detail"].lower()
        assert "activation_log_id" in result

    def test_abandoned_batch(self, db_session):
        batch = create_staging_batch(
            db_session,
            org_id=None,
            user_id=None,
            source_type=ImportSourceType.CSV,
            mode="import",
        )
        result = abandon_batch(db_session, batch.id)
        assert result["applied"] is True
        assert batch.status == StagingStatus.ABANDONED


# ========================================
# TestQualityRules (5 tests)
# ========================================


class TestQualityRules:
    def test_duplicate_site_detected(self, db_session):
        batch = create_staging_batch(
            db_session,
            org_id=None,
            user_id=None,
            source_type=ImportSourceType.CSV,
            mode="import",
        )
        # Two sites at same address
        s1 = StagingSite(batch_id=batch.id, nom="Bureau A", adresse="10 rue de la Paix", code_postal="75001")
        s2 = StagingSite(batch_id=batch.id, nom="Bureau B", adresse="10 rue de la Paix", code_postal="75001")
        db_session.add_all([s1, s2])
        db_session.flush()

        findings = check_duplicate_sites(db_session, batch.id)
        assert len(findings) >= 1
        assert findings[0]["rule_id"] == "dup_site_address"

    def test_duplicate_meter_detected(self, db_session):
        batch = create_staging_batch(
            db_session,
            org_id=None,
            user_id=None,
            source_type=ImportSourceType.CSV,
            mode="import",
        )
        s1 = StagingSite(batch_id=batch.id, nom="Site X")
        db_session.add(s1)
        db_session.flush()

        c1 = StagingCompteur(batch_id=batch.id, staging_site_id=s1.id, numero_serie="PRM-SAME")
        c2 = StagingCompteur(batch_id=batch.id, staging_site_id=s1.id, numero_serie="PRM-SAME")
        db_session.add_all([c1, c2])
        db_session.flush()

        findings = check_duplicate_meters(db_session, batch.id)
        assert len(findings) >= 1
        assert findings[0]["rule_id"] == "dup_meter"
        assert findings[0]["severity"] == QualityRuleSeverity.BLOCKING

    def test_orphan_meter_detected(self, db_session):
        batch = create_staging_batch(
            db_session,
            org_id=None,
            user_id=None,
            source_type=ImportSourceType.CSV,
            mode="import",
        )
        # Compteur without site
        c = StagingCompteur(batch_id=batch.id, numero_serie="PRM-ORPHAN")
        db_session.add(c)
        db_session.flush()

        findings = check_orphan_meters(db_session, batch.id)
        assert len(findings) == 1
        assert findings[0]["rule_id"] == "orphan_meter"

    def test_incomplete_site_warning(self, db_session):
        batch = create_staging_batch(
            db_session,
            org_id=None,
            user_id=None,
            source_type=ImportSourceType.CSV,
            mode="import",
        )
        s = StagingSite(batch_id=batch.id, nom="Missing Address")
        db_session.add(s)
        db_session.flush()

        findings = check_incomplete_sites(db_session, batch.id)
        assert len(findings) == 1
        assert findings[0]["severity"] == QualityRuleSeverity.WARNING

    def test_no_findings_clean_data(self, db_session):
        batch, sites, compteurs = _create_batch_with_data(db_session)
        findings = run_all_rules(db_session, batch.id)
        # Clean data should have no orphans, no exact dup meters, some warnings at most
        blocking = [f for f in findings if f["severity"] == QualityRuleSeverity.BLOCKING]
        assert len(blocking) == 0


# ========================================
# TestQualityFixes (3 tests)
# ========================================


class TestQualityFixes:
    def test_skip_row(self, db_session):
        batch, sites, _ = _create_batch_with_data(db_session)
        result = apply_fix(db_session, batch.id, "skip", {"staging_site_id": sites[0].id})
        assert result["applied"] is True
        assert sites[0].skip is True

    def test_merge_sites(self, db_session):
        org, ej, pf = _create_org(db_session)
        # Create an existing real site
        real_site = Site(portefeuille_id=pf.id, nom="Existing", type=TypeSite.BUREAU, surface_m2=1000, actif=True)
        db_session.add(real_site)
        db_session.flush()

        batch, sites, compteurs = _create_batch_with_data(db_session, org.id)
        result = apply_fix(
            db_session,
            batch.id,
            "merge_sites",
            {
                "staging_site_id": sites[0].id,
                "target_site_id": real_site.id,
            },
        )
        assert result["applied"] is True
        assert sites[0].skip is True
        assert sites[0].target_site_id == real_site.id

    def test_remap_compteur(self, db_session):
        batch, sites, compteurs = _create_batch_with_data(db_session)
        # Remap c3 (on site beta) to site alpha
        result = apply_fix(
            db_session,
            batch.id,
            "remap",
            {
                "staging_compteur_id": compteurs[2].id,
                "target_staging_site_id": sites[0].id,
            },
        )
        assert result["applied"] is True
        assert compteurs[2].staging_site_id == sites[0].id


# ========================================
# TestDemoLoad (3 tests)
# ========================================


class TestDemoLoad:
    def test_demo_load_creates_data(self, db_session):
        from scripts.seed_data import seed_patrimoine_demo

        # Need a minimal base for onboarding_service dependencies
        result = seed_patrimoine_demo(db_session)
        db_session.commit()
        assert result["status"] == "created"
        assert result["sites"] == 10
        assert result["compteurs"] == 13

    def test_demo_load_idempotent(self, db_session):
        from scripts.seed_data import seed_patrimoine_demo

        seed_patrimoine_demo(db_session)
        db_session.commit()

        result2 = seed_patrimoine_demo(db_session)
        assert result2["status"] == "already_exists"

    def test_demo_data_has_nn_links(self, db_session):
        from scripts.seed_data import seed_patrimoine_demo

        seed_patrimoine_demo(db_session)
        db_session.commit()

        links = db_session.query(OrgEntiteLink).all()
        assert len(links) >= 2  # org->mairie + org->ccas

        pf_links = db_session.query(PortfolioEntiteLink).all()
        assert len(pf_links) >= 2  # medico->ccas + medico->mairie


# ========================================
# TestIncrementalSync (2 tests)
# ========================================


class TestIncrementalSync:
    def test_diff_plan_detects_new(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch, _, _ = _create_batch_with_data(db_session, org.id)

        diff = get_diff_plan(db_session, pf.id, batch.id)
        # No existing sites, all should be "to_create"
        assert len(diff["to_create"]) == 2
        assert len(diff["to_update"]) == 0
        assert len(diff["to_merge"]) == 0

    def test_diff_plan_detects_existing(self, db_session):
        org, ej, pf = _create_org(db_session)

        # Create an existing site matching staging
        existing = Site(
            portefeuille_id=pf.id,
            nom="Site Alpha",
            type=TypeSite.BUREAU,
            code_postal="75001",
            surface_m2=1200,
            actif=True,
        )
        db_session.add(existing)
        db_session.flush()

        batch, _, _ = _create_batch_with_data(db_session, org.id)
        diff = get_diff_plan(db_session, pf.id, batch.id)

        # "Site Alpha" should be in to_update or to_merge, "Site Beta" in to_create
        assert len(diff["to_create"]) == 1
        assert diff["to_create"][0]["name"] == "Site Beta"


# ========================================
# TestLineage (2 tests)
# ========================================


class TestLineage:
    def test_activated_site_has_lineage(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch, _, _ = _create_batch_with_data(db_session, org.id)
        run_quality_gate(db_session, batch.id)
        activate_batch(db_session, batch.id, pf.id)

        real_sites = db_session.query(Site).filter(Site.portefeuille_id == pf.id).all()
        for s in real_sites:
            assert s.data_source == "csv"
            assert s.data_source_ref == f"batch:{batch.id}"
            assert s.imported_at is not None

    def test_activated_compteur_has_lineage(self, db_session):
        org, ej, pf = _create_org(db_session)
        batch, _, _ = _create_batch_with_data(db_session, org.id)
        run_quality_gate(db_session, batch.id)
        activate_batch(db_session, batch.id, pf.id)

        real_compteurs = db_session.query(Compteur).all()
        assert len(real_compteurs) >= 3
        for c in real_compteurs:
            assert c.data_source == "csv"
            assert c.data_source_ref == f"batch:{batch.id}"


# ========================================
# TestContentHash (1 test)
# ========================================


class TestContentHash:
    def test_compute_content_hash(self):
        content = b"nom,adresse\nSite A,10 rue"
        h = compute_content_hash(content)
        assert len(h) == 64  # SHA-256 hex
        assert h == compute_content_hash(content)  # Deterministic


# ========================================
# TestInvoiceImport (1 test)
# ========================================


class TestInvoiceImport:
    def test_import_invoices_to_staging(self, db_session):
        batch = create_staging_batch(
            db_session,
            org_id=None,
            user_id=None,
            source_type=ImportSourceType.INVOICE,
            mode="assiste",
        )
        metadata = {
            "invoices": [
                {
                    "site_name": "Bureau Paris",
                    "meter_id": "PRM111",
                    "address": "10 rue test",
                    "postal_code": "75001",
                    "city": "Paris",
                    "energy_type": "electricite",
                },
                {"site_name": "Bureau Paris", "meter_id": "PRM222", "energy_type": "gaz"},
                {"site_name": "Hotel Nice", "meter_id": "PRM333"},
            ]
        }
        result = import_invoices_to_staging(db_session, batch.id, metadata)
        assert result["sites_detected"] == 2
        assert result["compteurs_detected"] == 3


# ========================================
# TestAPIEndpoints (2 tests)
# ========================================


class TestAPIEndpoints:
    def test_staging_import_endpoint(self, client, db_session):
        # Create org for the route
        org = Organisation(nom="API Test Org", type_client="bureau", actif=True)
        db_session.add(org)
        db_session.commit()

        csv_content = "nom,adresse,code_postal,ville\nSite Test,1 rue Test,75001,Paris\n"
        response = client.post(
            "/api/patrimoine/staging/import",
            files={"file": ("test.csv", csv_content.encode(), "text/csv")},
            params={"mode": "express"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] is not None
        assert data["sites_count"] == 1

    def test_demo_load_endpoint(self, client, db_session):
        response = client.post("/api/patrimoine/demo/load")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ok", "created")
        assert data["sites"] == 10
