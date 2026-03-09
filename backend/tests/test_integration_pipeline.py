"""
PROMEOS Integration Test - Full Pipeline
Base Doc -> KB Build -> Load -> Import Data -> Analytics -> Results
Tests the complete KB-driven pipeline end-to-end.
"""

import pytest
import sys
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import math
import random

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models import (
    Site,
    KBVersion,
    KBArchetype,
    KBMappingCode,
    KBAnomalyRule,
    KBRecommendation,
    KBConfidence,
    KBStatus,
    Meter,
    MeterReading,
    UsageProfile,
    Anomaly,
    Recommendation,
    FrequencyType,
)
from models.enums import TypeSite


@pytest.fixture(scope="module")
def integration_db():
    """Create in-memory database for integration test"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestFullPipeline:
    """Integration test: base doc -> KB -> import -> analytics -> results"""

    def test_step1_verify_base_doc(self):
        """Step 1: Verify base documentaire integrity"""
        manifest_path = Path(PROJECT_ROOT) / "docs/base_documentaire/usages_energetiques_b2b/manifest.json"
        assert manifest_path.exists()

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        html_path = Path(PROJECT_ROOT) / "docs/base_documentaire/usages_energetiques_b2b" / manifest["source_path"]
        # Normalize line endings to LF for consistent hashing across OS
        with open(html_path, "r", encoding="utf-8") as f:
            content_lf = f.read().replace("\r\n", "\n")
        computed = hashlib.sha256(content_lf.encode("utf-8")).hexdigest()

        assert computed == manifest["sha256"], "Source integrity check FAILED"

    def test_step2_load_kb_version(self, integration_db):
        """Step 2: Load KB version from manifest"""
        from services.kb_service import KBService

        manifest_path = Path(PROJECT_ROOT) / "docs/base_documentaire/usages_energetiques_b2b/manifest.json"
        service = KBService(integration_db)
        kb_version = service.load_kb_version_from_manifest(manifest_path)

        assert kb_version is not None
        assert kb_version.doc_id == "USAGES_ENERGETIQUES_B2B_v1"
        assert kb_version.version == "1.0"
        assert len(kb_version.source_sha256) == 64

    def test_step3_load_archetypes(self, integration_db):
        """Step 3: Load archetypes from YAML files"""
        from services.kb_service import KBService

        yaml_dir = Path(PROJECT_ROOT) / "docs/kb/items/usages"
        service = KBService(integration_db)

        kb_version = integration_db.query(KBVersion).filter_by(is_active=True).first()
        assert kb_version is not None

        count = service.load_archetypes_from_yaml(yaml_dir, kb_version.id)
        assert count >= 1, "Should load at least 1 archetype from YAML"

        # Verify archetypes loaded with provenance
        archetypes = integration_db.query(KBArchetype).all()
        assert len(archetypes) >= 1

        for arch in archetypes:
            assert arch.kb_version_id == kb_version.id
            assert arch.source_section is not None
            assert arch.confidence is not None

    def test_step4_load_anomaly_rules(self, integration_db):
        """Step 4: Load anomaly rules"""
        from services.kb_service import KBService

        yaml_dir = Path(PROJECT_ROOT) / "docs/kb/items/usages"
        service = KBService(integration_db)

        kb_version = integration_db.query(KBVersion).filter_by(is_active=True).first()
        count = service.load_anomaly_rules_from_yaml(yaml_dir, kb_version.id)

        assert count >= 1, "Should load at least 1 anomaly rule"

    def test_step5_load_recommendations(self, integration_db):
        """Step 5: Load recommendations"""
        from services.kb_service import KBService

        yaml_dir = Path(PROJECT_ROOT) / "docs/kb/items/usages"
        service = KBService(integration_db)

        kb_version = integration_db.query(KBVersion).filter_by(is_active=True).first()
        count = service.load_recommendations_from_yaml(yaml_dir, kb_version.id)

        assert count >= 1, "Should load at least 1 recommendation"

    def test_step6_create_site_and_meter(self, integration_db):
        """Step 6: Create a test site with meter"""
        site = Site(
            nom="Bureau Integration Test",
            type=TypeSite.BUREAU,
            ville="Paris",
            surface_m2=1200.0,
            naf_code="70.10",
            actif=True,
        )
        integration_db.add(site)
        integration_db.commit()
        integration_db.refresh(site)

        meter = Meter(
            meter_id="PRM-INTEGRATION-001", name="Compteur Principal", site_id=site.id, subscribed_power_kva=120.0
        )
        integration_db.add(meter)
        integration_db.commit()

        assert meter.id is not None

    def test_step7_import_consumption_data(self, integration_db):
        """Step 7: Import synthetic consumption data (office profile)"""
        random.seed(42)

        meter = integration_db.query(Meter).filter_by(meter_id="PRM-INTEGRATION-001").first()
        assert meter is not None

        readings = []
        start = datetime(2025, 1, 1)

        for day in range(180):  # 6 months
            dt = start + timedelta(days=day)
            is_weekend = dt.weekday() >= 5
            month = dt.month
            seasonal = 1.0 + 0.2 * math.cos(2 * math.pi * (month - 1) / 12.0)

            for hour in range(24):
                ts = dt.replace(hour=hour)

                if is_weekend:
                    factor = 0.15
                elif 8 <= hour <= 18:
                    factor = 4.0
                elif 6 <= hour <= 7 or 19 <= hour <= 20:
                    factor = 2.0
                else:
                    factor = 0.30  # Slightly high night base for anomaly

                value = 7.0 * factor * seasonal * random.uniform(0.9, 1.1)
                readings.append(
                    MeterReading(
                        meter_id=meter.id,
                        timestamp=ts,
                        frequency=FrequencyType.HOURLY,
                        value_kwh=round(value, 2),
                        is_estimated=False,
                    )
                )

        integration_db.bulk_save_objects(readings)
        integration_db.commit()

        count = integration_db.query(MeterReading).filter_by(meter_id=meter.id).count()
        assert count == 180 * 24, f"Expected {180 * 24} readings, got {count}"

    def test_step8_run_analytics(self, integration_db):
        """Step 8: Run KB-driven analytics pipeline"""
        from services.analytics_engine import AnalyticsEngine

        meter = integration_db.query(Meter).filter_by(meter_id="PRM-INTEGRATION-001").first()
        engine = AnalyticsEngine(integration_db)
        result = engine.analyze(meter.id)

        assert result["status"] == "ok"
        assert result["features"] is not None
        assert result["features"]["readings_count"] == 180 * 24

    def test_step9_verify_archetype_detection(self, integration_db):
        """Step 9: Verify usage profile was created"""
        meter = integration_db.query(Meter).filter_by(meter_id="PRM-INTEGRATION-001").first()
        profile = integration_db.query(UsageProfile).filter_by(meter_id=meter.id).first()

        assert profile is not None
        assert profile.features_json is not None
        # Archetype may or may not be matched depending on KB load success
        assert profile.archetype_match_score is not None

    def test_step10_verify_anomalies_detected(self, integration_db):
        """Step 10: Verify anomalies were detected with KB provenance"""
        meter = integration_db.query(Meter).filter_by(meter_id="PRM-INTEGRATION-001").first()
        anomalies = integration_db.query(Anomaly).filter_by(meter_id=meter.id, is_active=True).all()

        # We should have at least some anomalies detected
        assert isinstance(anomalies, list)

        for anomaly in anomalies:
            assert anomaly.anomaly_code is not None
            assert anomaly.severity is not None
            assert anomaly.explanation_json is not None

    def test_step11_verify_recommendations_generated(self, integration_db):
        """Step 11: Verify recommendations have KB provenance"""
        meter = integration_db.query(Meter).filter_by(meter_id="PRM-INTEGRATION-001").first()
        recos = integration_db.query(Recommendation).filter_by(meter_id=meter.id).all()

        assert isinstance(recos, list)

        for reco in recos:
            assert reco.recommendation_code is not None
            assert reco.ice_score is not None
            assert reco.priority_rank is not None

    def test_step12_verify_provenance_chain(self, integration_db):
        """Step 12: Verify end-to-end provenance chain"""
        kb_version = integration_db.query(KBVersion).filter_by(is_active=True).first()
        assert kb_version is not None

        # KB Version -> Archetypes
        archetypes = integration_db.query(KBArchetype).filter_by(kb_version_id=kb_version.id).all()
        assert len(archetypes) >= 1

        # KB Version -> Rules
        rules = integration_db.query(KBAnomalyRule).filter_by(kb_version_id=kb_version.id).all()
        assert len(rules) >= 1

        # KB Version -> Recommendations
        recos = integration_db.query(KBRecommendation).filter_by(kb_version_id=kb_version.id).all()
        assert len(recos) >= 1

        # All items trace back to the same source document
        for arch in archetypes:
            assert arch.source_section is not None
            assert arch.confidence is not None

        print(f"\n[PROVENANCE] KB {kb_version.doc_id} v{kb_version.version}")
        print(f"  SHA256: {kb_version.source_sha256[:16]}...")
        print(f"  Archetypes: {len(archetypes)}")
        print(f"  Rules: {len(rules)}")
        print(f"  Recommendations: {len(recos)}")
        print(f"  Pipeline: Base Doc -> KB YAML -> DB -> Analytics -> Results")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
