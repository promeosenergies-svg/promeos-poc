"""
PROMEOS KB Service - Knowledge Base Operations
Load KB from YAML files, query archetypes, rules, recommendations
"""

import yaml
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models import (
    KBVersion,
    KBArchetype,
    KBMappingCode,
    KBAnomalyRule,
    KBRecommendation,
    KBTaxonomy,
    KBConfidence,
    KBStatus,
)


class KBService:
    """Service for Knowledge Base operations"""

    def __init__(self, db: Session):
        self.db = db

    def load_kb_version_from_manifest(self, manifest_path: Path) -> Optional[KBVersion]:
        """Load KB version from manifest.json"""
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Check if version already loaded
        existing = self.db.query(KBVersion).filter_by(doc_id=manifest["doc_id"]).first()

        if existing and existing.source_sha256 == manifest["sha256"]:
            print(f"[KB] Version {manifest['doc_id']} already loaded (SHA256 match)")
            return existing

        # Create/update version
        kb_version = KBVersion(
            doc_id=manifest["doc_id"],
            version=manifest["version"],
            date=manifest["date"],
            source_path=manifest["source_path"],
            source_sha256=manifest["sha256"],
            author=manifest.get("author"),
            description=manifest.get("description"),
            status=KBStatus.VALIDATED,
            is_active=True,
        )

        if existing:
            existing.version = kb_version.version
            existing.source_sha256 = kb_version.source_sha256
            existing.date = kb_version.date
            existing.updated_at = datetime.now(timezone.utc)
            kb_version = existing
        else:
            self.db.add(kb_version)

        self.db.commit()
        self.db.refresh(kb_version)

        print(f"[KB] Loaded version {kb_version.doc_id} v{kb_version.version}")
        return kb_version

    def load_archetypes_from_yaml(self, yaml_dir: Path, kb_version_id: int) -> int:
        """Load archetypes from YAML files"""
        yaml_files = list(yaml_dir.glob("ARCHETYPE-*.yaml"))

        loaded_count = 0

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    item = yaml.safe_load(f)

                # Extract code from ID
                code = item["id"].replace("ARCHETYPE-", "")

                # Check if exists
                existing = self.db.query(KBArchetype).filter_by(code=code).first()

                # Parse consumption range
                content_md = item.get("content_md", "")
                kwh_min, kwh_max = self._extract_kwh_range(content_md)

                archetype_data = {
                    "code": code,
                    "title": item["title"],
                    "description": item["summary"],
                    "kwh_m2_min": kwh_min,
                    "kwh_m2_max": kwh_max,
                    "kwh_m2_avg": int((kwh_min + kwh_max) / 2) if kwh_min and kwh_max else None,
                    "usage_breakdown_json": self._extract_usage_breakdown(content_md),
                    "temporal_signature_json": None,  # TODO: Extract if available
                    "segment_tags": item["tags"].get("segment", []),
                    "kb_item_id": item["id"],
                    "kb_version_id": kb_version_id,
                    "source_section": item["provenance"]["source_section"],
                    "confidence": KBConfidence(item["confidence"]),
                    "status": KBStatus(item.get("status", "validated")),
                }

                if existing:
                    for key, value in archetype_data.items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.now(timezone.utc)
                    archetype = existing
                else:
                    archetype = KBArchetype(**archetype_data)
                    self.db.add(archetype)

                self.db.flush()

                # Load NAF mappings
                naf_codes = item.get("scope", {}).get("naf_codes", [])
                self._load_naf_mappings(archetype.id, naf_codes, kb_version_id)

                loaded_count += 1

            except Exception as e:
                print(f"[WARN] Failed to load {yaml_file.name}: {e}")

        self.db.commit()
        print(f"[KB] Loaded {loaded_count} archetypes")
        return loaded_count

    def load_anomaly_rules_from_yaml(self, yaml_dir: Path, kb_version_id: int) -> int:
        """Load anomaly rules from YAML files"""
        yaml_files = list(yaml_dir.glob("RULE-*.yaml"))

        loaded_count = 0

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    item = yaml.safe_load(f)

                code = item["id"].replace("RULE-", "")

                existing = self.db.query(KBAnomalyRule).filter_by(code=code).first()

                # Determine rule type and severity from code/content
                rule_type = self._infer_rule_type(code)
                severity = self._extract_severity(item)

                rule_data = {
                    "code": code,
                    "title": item["title"],
                    "description": item["summary"],
                    "rule_type": rule_type,
                    "severity": severity,
                    "thresholds_json": self._extract_thresholds(item.get("content_md", "")),
                    "conditions_json": item.get("logic", {}),
                    "archetype_codes": item.get("scope", {}).get("archetypes", ["*"]),
                    "kb_item_id": item["id"],
                    "kb_version_id": kb_version_id,
                    "source_section": item["provenance"]["source_section"],
                    "confidence": KBConfidence(item["confidence"]),
                    "status": KBStatus(item.get("status", "validated")),
                }

                if existing:
                    for key, value in rule_data.items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    rule = KBAnomalyRule(**rule_data)
                    self.db.add(rule)

                loaded_count += 1

            except Exception as e:
                print(f"[WARN] Failed to load {yaml_file.name}: {e}")

        self.db.commit()
        print(f"[KB] Loaded {loaded_count} anomaly rules")
        return loaded_count

    def load_recommendations_from_yaml(self, yaml_dir: Path, kb_version_id: int) -> int:
        """Load recommendations from YAML files"""
        yaml_files = list(yaml_dir.glob("RECO-*.yaml"))

        loaded_count = 0

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    item = yaml.safe_load(f)

                code = item["id"].replace("RECO-", "")

                existing = self.db.query(KBRecommendation).filter_by(code=code).first()

                # Extract savings and ICE scores
                savings_min, savings_max = self._extract_savings_range(item.get("content_md", ""))

                reco_data = {
                    "code": code,
                    "title": item["title"],
                    "description": item["summary"],
                    "action_type": self._infer_action_type(code),
                    "target_asset": item["tags"].get("asset", ["hvac"])[0] if item["tags"].get("asset") else "hvac",
                    "savings_min_pct": savings_min,
                    "savings_max_pct": savings_max,
                    "impact_score": self._estimate_impact(savings_min, savings_max),
                    "confidence_score": 7,  # Default medium confidence
                    "ease_score": 5,  # Default medium ease
                    "ice_score": None,  # Will be computed
                    "implementation_steps_json": None,  # TODO: Extract if available
                    "prerequisites_json": None,
                    "archetype_codes": item.get("scope", {}).get("archetypes", ["*"]),
                    "anomaly_codes": self._infer_trigger_anomalies(code),
                    "kb_item_id": item["id"],
                    "kb_version_id": kb_version_id,
                    "source_section": item["provenance"]["source_section"],
                    "confidence": KBConfidence(item["confidence"]),
                    "status": KBStatus(item.get("status", "validated")),
                }

                # Compute ICE score
                if reco_data["impact_score"] and reco_data["confidence_score"] and reco_data["ease_score"]:
                    reco_data["ice_score"] = (
                        reco_data["impact_score"] * reco_data["confidence_score"] * reco_data["ease_score"]
                    ) / 1000.0

                if existing:
                    for key, value in reco_data.items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    reco = KBRecommendation(**reco_data)
                    self.db.add(reco)

                loaded_count += 1

            except Exception as e:
                print(f"[WARN] Failed to load {yaml_file.name}: {e}")

        self.db.commit()
        print(f"[KB] Loaded {loaded_count} recommendations")
        return loaded_count

    def _load_naf_mappings(self, archetype_id: int, naf_codes: List[str], kb_version_id: int):
        """Load NAF code mappings for an archetype"""
        # Delete existing mappings for this archetype
        self.db.query(KBMappingCode).filter_by(archetype_id=archetype_id).delete()

        for naf_code in naf_codes:
            mapping = KBMappingCode(
                naf_code=naf_code,
                archetype_id=archetype_id,
                confidence=KBConfidence.HIGH,
                priority=1,
                kb_version_id=kb_version_id,
            )
            self.db.add(mapping)

    def get_archetype_by_code(self, code: str) -> Optional[KBArchetype]:
        """Get archetype by code"""
        return self.db.query(KBArchetype).filter_by(code=code, status=KBStatus.VALIDATED).first()

    def get_archetype_by_naf(self, naf_code: str) -> Optional[KBArchetype]:
        """Get archetype by NAF code"""
        mapping = (
            self.db.query(KBMappingCode).filter_by(naf_code=naf_code).order_by(KBMappingCode.priority.desc()).first()
        )

        if mapping:
            return mapping.archetype

        return None

    def search_archetypes(self, segment: Optional[str] = None, kwh_range: Optional[tuple] = None) -> List[KBArchetype]:
        """Search archetypes by criteria"""
        query = self.db.query(KBArchetype).filter_by(status=KBStatus.VALIDATED)

        if segment:
            # JSON contains search (requires SQL function)
            query = query.filter(KBArchetype.segment_tags.contains([segment]))

        if kwh_range:
            kwh_min, kwh_max = kwh_range
            query = query.filter(and_(KBArchetype.kwh_m2_min <= kwh_max, KBArchetype.kwh_m2_max >= kwh_min))

        return query.all()

    def get_anomaly_rules(self, archetype_code: Optional[str] = None) -> List[KBAnomalyRule]:
        """Get applicable anomaly rules"""
        query = self.db.query(KBAnomalyRule).filter_by(status=KBStatus.VALIDATED)

        if archetype_code:
            # Filter rules that apply to this archetype or all ("*")
            query = query.filter(
                or_(
                    KBAnomalyRule.archetype_codes.contains([archetype_code]),
                    KBAnomalyRule.archetype_codes.contains(["*"]),
                )
            )

        return query.all()

    def get_recommendations(
        self, archetype_code: Optional[str] = None, anomaly_code: Optional[str] = None
    ) -> List[KBRecommendation]:
        """Get applicable recommendations"""
        query = self.db.query(KBRecommendation).filter_by(status=KBStatus.VALIDATED)

        if archetype_code:
            query = query.filter(
                or_(
                    KBRecommendation.archetype_codes.contains([archetype_code]),
                    KBRecommendation.archetype_codes.contains(["*"]),
                )
            )

        if anomaly_code:
            query = query.filter(KBRecommendation.anomaly_codes.contains([anomaly_code]))

        return query.order_by(KBRecommendation.ice_score.desc()).all()

    # Helper methods for extraction

    def _extract_kwh_range(self, content: str) -> tuple:
        """Extract kWh/m²/an range from content"""
        import re

        match = re.search(r"(\d+)-(\d+)\s*kWh/m²/an", content)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None, None

    def _extract_usage_breakdown(self, content: str) -> Optional[Dict]:
        """Extract usage breakdown from content"""
        # Simplified extraction - would need more sophisticated parsing
        return None

    def _extract_severity(self, item: Dict) -> str:
        """Extract severity from item"""
        # Check logic outputs for severity
        outputs = item.get("logic", {}).get("then", {}).get("outputs", [])
        if outputs:
            return outputs[0].get("severity", "medium")
        return "medium"

    def _extract_thresholds(self, content: str) -> Optional[Dict]:
        """Extract thresholds from content"""
        # Would need sophisticated parsing
        return {}

    def _extract_savings_range(self, content: str) -> tuple:
        """Extract savings percentage range"""
        import re

        match = re.search(r"(\d+)-(\d+)%", content)
        if match:
            return float(match.group(1)), float(match.group(2))
        return None, None

    def _estimate_impact(self, savings_min: Optional[float], savings_max: Optional[float]) -> int:
        """Estimate impact score (1-10) from savings range"""
        if savings_min is None or savings_max is None:
            return 5  # Default

        avg_savings = (savings_min + savings_max) / 2

        if avg_savings >= 30:
            return 9
        elif avg_savings >= 20:
            return 7
        elif avg_savings >= 10:
            return 5
        else:
            return 3

    def _infer_rule_type(self, code: str) -> str:
        """Infer rule type from code"""
        if "BASE_NUIT" in code:
            return "base_nuit"
        elif "WEEKEND" in code:
            return "weekend"
        elif "PUISSANCE" in code:
            return "puissance"
        elif "SAISON" in code:
            return "saisonnalite"
        elif "RATIO_M2" in code:
            return "ratio_m2"
        elif "GAZ" in code:
            return "gaz_ete"
        return "general"

    def _infer_action_type(self, code: str) -> str:
        """Infer action type from code"""
        if "REGULATION" in code or "THERMIQUE" in code:
            return "regulation"
        elif "ECLAIRAGE" in code or "LED" in code:
            return "equipment"
        elif "PUISSANCE" in code:
            return "subscription"
        elif "FROID" in code:
            return "equipment"
        elif "AIR_COMPRIME" in code:
            return "maintenance"
        return "behavior"

    def _infer_trigger_anomalies(self, code: str) -> List[str]:
        """Infer which anomalies trigger this recommendation"""
        if "BASE_NUIT" in code:
            return ["ANOM_BASE_NUIT_ELEVEE"]
        elif "PUISSANCE" in code:
            return ["ANOM_PUISSANCE_POINTE"]
        elif "THERMIQUE" in code or "REGULATION" in code:
            return ["ANOM_PAS_SAISONNALITE", "ANOM_WEEKEND_ELEVE"]
        elif "FROID" in code:
            return ["ANOM_WEEKEND_ELEVE"]
        elif "GAZ" in code:
            return ["ANOM_GAZ_ETE"]
        return []
