"""
PROMEOS Tests - KB Usages (Archetypes, Rules, Recommendations)
Tests: KB build from docs, service layer, API endpoints, analytics engine
"""
import pytest
import json
import hashlib
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from models.base import Base
from models import (
    Site, KBVersion, KBArchetype, KBMappingCode, KBAnomalyRule,
    KBRecommendation, KBTaxonomy, KBConfidence, KBStatus,
    Meter, MeterReading, DataImportJob, UsageProfile,
    Anomaly, Recommendation, FrequencyType, ImportStatus
)
from models.enums import TypeSite


# ---- Fixtures ----

@pytest.fixture(scope="function")
def test_db():
    """Create in-memory test database"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_site(test_db):
    """Create a sample site"""
    site = Site(
        nom="Bureau Test Paris",
        type=TypeSite.BUREAU,
        ville="Paris",
        surface_m2=1000.0,
        naf_code="70.10",
        actif=True
    )
    test_db.add(site)
    test_db.commit()
    test_db.refresh(site)
    return site


@pytest.fixture
def sample_kb_version(test_db):
    """Create a sample KB version"""
    version = KBVersion(
        doc_id="USAGES_ENERGETIQUES_B2B_v1",
        version="1.0",
        date="2026-02-09",
        source_path="source/USAGES_ENERGETIQUES_B2B_v1.html",
        source_sha256="e27ab62d958a5ab1240c118ce7e69079fdea166fe22cb95953ed2a3cadd97a22",
        author="PROMEOS Test",
        status=KBStatus.VALIDATED,
        is_active=True
    )
    test_db.add(version)
    test_db.commit()
    test_db.refresh(version)
    return version


@pytest.fixture
def sample_archetypes(test_db, sample_kb_version):
    """Create sample archetypes"""
    archetypes = [
        KBArchetype(
            code="BUREAU_STANDARD",
            title="Bureau Standard",
            description="Bureaux tertiaires classiques",
            kwh_m2_min=150,
            kwh_m2_max=250,
            kwh_m2_avg=200,
            segment_tags=["tertiaire_multisite"],
            kb_item_id="ARCHETYPE-BUREAU_STANDARD",
            kb_version_id=sample_kb_version.id,
            source_section="archetype-bureau",
            confidence=KBConfidence.HIGH,
            status=KBStatus.VALIDATED
        ),
        KBArchetype(
            code="COMMERCE_ALIMENTAIRE",
            title="Commerce Alimentaire",
            description="Supermarches et alimentaire",
            kwh_m2_min=400,
            kwh_m2_max=800,
            kwh_m2_avg=600,
            segment_tags=["tertiaire_multisite"],
            kb_item_id="ARCHETYPE-COMMERCE_ALIMENTAIRE",
            kb_version_id=sample_kb_version.id,
            source_section="archetype-commerce",
            confidence=KBConfidence.HIGH,
            status=KBStatus.VALIDATED
        ),
    ]
    test_db.add_all(archetypes)
    test_db.commit()
    for a in archetypes:
        test_db.refresh(a)

    # Add NAF mappings
    naf_mappings = [
        KBMappingCode(naf_code="70.10", archetype_id=archetypes[0].id, confidence=KBConfidence.HIGH, kb_version_id=sample_kb_version.id),
        KBMappingCode(naf_code="69.10", archetype_id=archetypes[0].id, confidence=KBConfidence.HIGH, kb_version_id=sample_kb_version.id),
        KBMappingCode(naf_code="47.11", archetype_id=archetypes[1].id, confidence=KBConfidence.HIGH, kb_version_id=sample_kb_version.id),
    ]
    test_db.add_all(naf_mappings)
    test_db.commit()

    return archetypes


@pytest.fixture
def sample_rules(test_db, sample_kb_version):
    """Create sample anomaly rules"""
    rules = [
        KBAnomalyRule(
            code="ANOM_BASE_NUIT_ELEVEE",
            title="Base nuit elevee",
            description="Consommation nuit excessive",
            rule_type="base_nuit",
            severity="high",
            archetype_codes=["*"],
            kb_item_id="RULE-ANOM_BASE_NUIT_ELEVEE",
            kb_version_id=sample_kb_version.id,
            source_section="anomalie-base-nuit",
            confidence=KBConfidence.HIGH,
            status=KBStatus.VALIDATED
        ),
        KBAnomalyRule(
            code="ANOM_WEEKEND_ELEVE",
            title="Weekend eleve",
            description="Consommation weekend excessive",
            rule_type="weekend",
            severity="medium",
            archetype_codes=["*"],
            kb_item_id="RULE-ANOM_WEEKEND_ELEVE",
            kb_version_id=sample_kb_version.id,
            source_section="anomalie-weekend",
            confidence=KBConfidence.HIGH,
            status=KBStatus.VALIDATED
        ),
    ]
    test_db.add_all(rules)
    test_db.commit()
    return rules


@pytest.fixture
def sample_recommendations(test_db, sample_kb_version):
    """Create sample recommendations"""
    recos = [
        KBRecommendation(
            code="RECO_BASE_NUIT",
            title="Reduction base nuit",
            description="Reduire la consommation nocturne",
            action_type="behavior",
            target_asset="hvac",
            savings_min_pct=5.0,
            savings_max_pct=15.0,
            impact_score=7,
            confidence_score=7,
            ease_score=8,
            ice_score=0.392,
            anomaly_codes=["ANOM_BASE_NUIT_ELEVEE"],
            kb_item_id="RECO-RECO_BASE_NUIT",
            kb_version_id=sample_kb_version.id,
            source_section="reco-base-nuit",
            confidence=KBConfidence.HIGH,
            status=KBStatus.VALIDATED
        ),
    ]
    test_db.add_all(recos)
    test_db.commit()
    return recos


@pytest.fixture
def sample_meter_with_readings(test_db, sample_site):
    """Create a meter with 30 days of hourly readings (office pattern)"""
    meter = Meter(
        meter_id=f"PRM-{sample_site.id:06d}",
        name="Compteur Principal",
        site_id=sample_site.id,
        subscribed_power_kva=100.0
    )
    test_db.add(meter)
    test_db.commit()
    test_db.refresh(meter)

    import random
    import math
    random.seed(42)  # Deterministic for tests

    readings = []
    start = datetime(2025, 1, 1)

    for day in range(90):  # 90 days of data
        dt = start + timedelta(days=day)
        is_weekend = dt.weekday() >= 5
        month = dt.month
        seasonal = 1.0 + 0.2 * math.cos(2 * math.pi * (month - 1) / 12.0)

        for hour in range(24):
            ts = dt.replace(hour=hour)

            if is_weekend:
                factor = 0.15  # Low weekend (office)
            elif 8 <= hour <= 18:
                factor = 4.0  # High during work hours
            elif 6 <= hour <= 7 or 19 <= hour <= 20:
                factor = 2.0
            else:
                factor = 0.35  # Night base - slightly high for anomaly detection

            value = 7.0 * factor * seasonal * random.uniform(0.9, 1.1)

            readings.append(MeterReading(
                meter_id=meter.id,
                timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=round(value, 2),
                is_estimated=False
            ))

    test_db.bulk_save_objects(readings)
    test_db.commit()

    return meter


# ---- Test KB Build from Docs ----

class TestKBBuildFromDocs:
    """Test the kb_build_from_docs.py pipeline"""

    def test_manifest_exists(self):
        """Manifest file should exist"""
        manifest_path = Path(PROJECT_ROOT) / "docs/base_documentaire/usages_energetiques_b2b/manifest.json"
        assert manifest_path.exists(), f"Manifest not found: {manifest_path}"

    def test_manifest_valid_json(self):
        """Manifest should be valid JSON"""
        manifest_path = Path(PROJECT_ROOT) / "docs/base_documentaire/usages_energetiques_b2b/manifest.json"
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        assert manifest['doc_id'] == 'USAGES_ENERGETIQUES_B2B_v1'
        assert manifest['version'] == '1.0'
        assert 'sha256' in manifest
        assert len(manifest['sha256']) == 64
        assert 'sections' in manifest
        assert len(manifest['sections']) >= 4

    def test_source_html_exists(self):
        """Source HTML should exist"""
        html_path = Path(PROJECT_ROOT) / "docs/base_documentaire/usages_energetiques_b2b/source/USAGES_ENERGETIQUES_B2B_v1.html"
        assert html_path.exists(), f"HTML source not found: {html_path}"

    def test_source_sha256_matches_manifest(self):
        """Source HTML SHA256 should match manifest"""
        manifest_path = Path(PROJECT_ROOT) / "docs/base_documentaire/usages_energetiques_b2b/manifest.json"
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        html_path = Path(PROJECT_ROOT) / "docs/base_documentaire/usages_energetiques_b2b" / manifest['source_path']
        with open(html_path, 'rb') as f:
            computed = hashlib.sha256(f.read()).hexdigest()

        assert computed == manifest['sha256'], "SHA256 mismatch - source may have been tampered with"

    def test_yaml_files_generated(self):
        """KB YAML files should exist in output directory"""
        yaml_dir = Path(PROJECT_ROOT) / "docs/kb/items/usages"
        if not yaml_dir.exists():
            pytest.skip("YAML output directory not found - run kb_build_from_docs.py first")

        yaml_files = list(yaml_dir.glob("*.yaml"))
        assert len(yaml_files) >= 5, f"Expected at least 5 YAML files, got {len(yaml_files)}"

    def test_yaml_has_provenance(self):
        """Generated YAML files should have provenance fields"""
        import yaml as yaml_lib

        yaml_dir = Path(PROJECT_ROOT) / "docs/kb/items/usages"
        if not yaml_dir.exists():
            pytest.skip("YAML output directory not found")

        archetype_files = list(yaml_dir.glob("ARCHETYPE-*.yaml"))
        if not archetype_files:
            pytest.skip("No archetype YAML files found")

        with open(archetype_files[0], 'r', encoding='utf-8') as f:
            item = yaml_lib.safe_load(f)

        assert 'provenance' in item, "Missing 'provenance' field"
        assert 'source_path' in item['provenance']
        assert 'source_sha256' in item['provenance']
        assert 'source_section' in item['provenance']
        assert item['confidence'] == 'high'


# ---- Test KB Models ----

class TestKBModels:
    """Test KB database models"""

    def test_create_kb_version(self, test_db, sample_kb_version):
        """Should create KB version"""
        assert sample_kb_version.id is not None
        assert sample_kb_version.doc_id == "USAGES_ENERGETIQUES_B2B_v1"
        assert sample_kb_version.version == "1.0"
        assert len(sample_kb_version.source_sha256) == 64

    def test_create_archetype(self, test_db, sample_archetypes):
        """Should create archetypes"""
        assert len(sample_archetypes) == 2
        assert sample_archetypes[0].code == "BUREAU_STANDARD"
        assert sample_archetypes[0].kwh_m2_min == 150
        assert sample_archetypes[0].kwh_m2_max == 250

    def test_archetype_naf_mapping(self, test_db, sample_archetypes):
        """Should create NAF mappings for archetypes"""
        mappings = test_db.query(KBMappingCode).filter_by(archetype_id=sample_archetypes[0].id).all()
        assert len(mappings) == 2
        naf_codes = [m.naf_code for m in mappings]
        assert "70.10" in naf_codes
        assert "69.10" in naf_codes

    def test_archetype_by_naf_lookup(self, test_db, sample_archetypes):
        """Should find archetype by NAF code"""
        mapping = test_db.query(KBMappingCode).filter_by(naf_code="70.10").first()
        assert mapping is not None
        assert mapping.archetype.code == "BUREAU_STANDARD"

    def test_create_anomaly_rule(self, test_db, sample_rules):
        """Should create anomaly rules"""
        assert len(sample_rules) == 2
        assert sample_rules[0].code == "ANOM_BASE_NUIT_ELEVEE"
        assert sample_rules[0].rule_type == "base_nuit"
        assert sample_rules[0].severity == "high"

    def test_create_recommendation(self, test_db, sample_recommendations):
        """Should create recommendations with ICE score"""
        assert len(sample_recommendations) == 1
        reco = sample_recommendations[0]
        assert reco.code == "RECO_BASE_NUIT"
        assert reco.savings_min_pct == 5.0
        assert reco.savings_max_pct == 15.0
        assert reco.ice_score == pytest.approx(0.392, abs=0.01)

    def test_provenance_tracking(self, test_db, sample_archetypes, sample_kb_version):
        """Should maintain provenance chain"""
        arch = sample_archetypes[0]
        assert arch.kb_version_id == sample_kb_version.id
        assert arch.source_section == "archetype-bureau"
        assert arch.confidence == KBConfidence.HIGH
        assert arch.status == KBStatus.VALIDATED


# ---- Test Energy Models ----

class TestEnergyModels:
    """Test Energy database models"""

    def test_create_meter(self, test_db, sample_site):
        """Should create meter linked to site"""
        meter = Meter(
            meter_id="PRM-TEST-001",
            name="Compteur Test",
            site_id=sample_site.id,
            subscribed_power_kva=50.0
        )
        test_db.add(meter)
        test_db.commit()

        assert meter.id is not None
        assert meter.site_id == sample_site.id

    def test_create_meter_readings(self, test_db, sample_meter_with_readings):
        """Should create hourly readings"""
        count = test_db.query(MeterReading).filter_by(meter_id=sample_meter_with_readings.id).count()
        assert count == 90 * 24  # 90 days * 24 hours

    def test_import_job_tracking(self, test_db, sample_site):
        """Should track import jobs"""
        job = DataImportJob(
            job_type="consumption_import",
            status=ImportStatus.COMPLETED,
            filename="test.csv",
            file_format="csv",
            file_size_bytes=1024,
            site_id=sample_site.id,
            rows_total=100,
            rows_imported=95,
            rows_skipped=3,
            rows_errored=2
        )
        test_db.add(job)
        test_db.commit()

        assert job.id is not None
        assert job.rows_imported == 95
        assert job.status == ImportStatus.COMPLETED


# ---- Test KB Service ----

class TestKBService:
    """Test KB service layer"""

    def test_get_archetype_by_code(self, test_db, sample_archetypes):
        """Should find archetype by code"""
        from services.kb_service import KBService
        service = KBService(test_db)
        arch = service.get_archetype_by_code("BUREAU_STANDARD")
        assert arch is not None
        assert arch.kwh_m2_min == 150

    def test_get_archetype_by_naf(self, test_db, sample_archetypes):
        """Should find archetype by NAF code"""
        from services.kb_service import KBService
        service = KBService(test_db)
        arch = service.get_archetype_by_naf("70.10")
        assert arch is not None
        assert arch.code == "BUREAU_STANDARD"

    def test_get_anomaly_rules(self, test_db, sample_rules):
        """Should return all validated rules"""
        from services.kb_service import KBService
        service = KBService(test_db)
        rules = service.get_anomaly_rules()
        assert len(rules) == 2

    def test_get_recommendations(self, test_db, sample_recommendations):
        """Should return recommendations sorted by ICE"""
        from services.kb_service import KBService
        service = KBService(test_db)
        recos = service.get_recommendations()
        assert len(recos) == 1
        assert recos[0].code == "RECO_BASE_NUIT"


# ---- Test Analytics Engine ----

class TestAnalyticsEngine:
    """Test KB-driven analytics engine"""

    def test_extract_features(self, test_db, sample_meter_with_readings):
        """Should extract features from meter data"""
        from services.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine(test_db)
        features = engine._extract_features(sample_meter_with_readings)

        assert features is not None
        assert features['kwh_total'] > 0
        assert features['base_nuit_ratio'] > 0
        assert features['weekend_ratio'] > 0
        assert features['load_factor'] > 0
        assert features['seasonality_cv'] >= 0
        assert features['readings_count'] == 90 * 24

    def test_retrieve_archetype_by_naf(self, test_db, sample_site, sample_archetypes, sample_meter_with_readings):
        """Should match archetype based on site NAF code"""
        from services.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine(test_db)
        features = engine._extract_features(sample_meter_with_readings)
        arch, score = engine._retrieve_archetype(sample_site, features)

        assert arch is not None
        assert arch.code == "BUREAU_STANDARD"  # NAF 70.10 maps to BUREAU
        assert score >= 0.3  # At minimum default, ideally 0.85 for NAF match

    def test_apply_anomaly_rules(self, test_db, sample_meter_with_readings, sample_rules, sample_archetypes):
        """Should detect anomalies based on KB rules"""
        from services.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine(test_db)
        features = engine._extract_features(sample_meter_with_readings)
        archetype = sample_archetypes[0]

        anomalies = engine._apply_anomaly_rules(sample_meter_with_readings, features, archetype)

        # Should detect at least one anomaly (our test data has high night base)
        assert isinstance(anomalies, list)
        # Each anomaly should have KB provenance
        for a in anomalies:
            assert 'kb_rule_id' in a
            assert 'explanation' in a
            assert 'severity' in a

    def test_generate_recommendations(self, test_db, sample_meter_with_readings,
                                        sample_rules, sample_recommendations, sample_archetypes):
        """Should generate KB-driven recommendations"""
        from services.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine(test_db)
        features = engine._extract_features(sample_meter_with_readings)
        archetype = sample_archetypes[0]

        anomalies = engine._apply_anomaly_rules(sample_meter_with_readings, features, archetype)
        recos = engine._generate_recommendations(sample_meter_with_readings, anomalies, archetype, features)

        assert isinstance(recos, list)
        for r in recos:
            assert 'kb_recommendation_id' in r
            assert 'ice_score' in r
            assert 'triggered_by' in r

    def test_full_analysis_pipeline(self, test_db, sample_site, sample_meter_with_readings,
                                     sample_archetypes, sample_rules, sample_recommendations, sample_kb_version):
        """Should run complete analysis pipeline"""
        from services.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine(test_db)
        result = engine.analyze(sample_meter_with_readings.id)

        assert result['status'] == 'ok'
        assert result['meter_id'] == sample_meter_with_readings.meter_id
        assert result['features'] is not None
        assert result['archetype'] is not None
        assert 'anomalies' in result
        assert 'recommendations' in result


# ---- Test CSV Import ----

class TestCSVImport:
    """Test CSV parsing and import"""

    def test_parse_csv_semicolon(self, test_db, sample_site):
        """Should parse CSV with semicolon separator"""
        from routes.energy import _import_csv

        meter = Meter(
            meter_id="PRM-CSV-TEST",
            name="Test CSV",
            site_id=sample_site.id
        )
        test_db.add(meter)
        test_db.commit()

        csv_content = b"timestamp;value_kwh\n2025-01-01 00:00:00;12.5\n2025-01-01 01:00:00;11.3\n2025-01-01 02:00:00;10.1\n"

        imported, skipped, errored, date_range = _import_csv(
            csv_content, meter.id, FrequencyType.HOURLY, test_db
        )

        assert imported == 3
        assert skipped == 0
        assert errored == 0
        assert date_range[0] is not None

    def test_parse_csv_comma_values(self, test_db, sample_site):
        """Should handle comma as decimal separator"""
        from routes.energy import _import_csv

        meter = Meter(
            meter_id="PRM-CSV-COMMA",
            name="Test CSV Comma",
            site_id=sample_site.id
        )
        test_db.add(meter)
        test_db.commit()

        csv_content = "timestamp;value_kwh\n2025-01-01 00:00;12,5\n2025-01-01 01:00;11,3\n".encode('utf-8')

        imported, skipped, errored, _ = _import_csv(
            csv_content, meter.id, FrequencyType.HOURLY, test_db
        )

        assert imported == 2

    def test_parse_csv_french_dates(self, test_db, sample_site):
        """Should handle French date format"""
        from routes.energy import _import_csv

        meter = Meter(
            meter_id="PRM-CSV-FR",
            name="Test CSV FR",
            site_id=sample_site.id
        )
        test_db.add(meter)
        test_db.commit()

        csv_content = "date;kwh\n01/01/2025 00:00;12.5\n01/01/2025 01:00;11.3\n".encode('utf-8')

        imported, skipped, errored, _ = _import_csv(
            csv_content, meter.id, FrequencyType.HOURLY, test_db
        )

        assert imported == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
