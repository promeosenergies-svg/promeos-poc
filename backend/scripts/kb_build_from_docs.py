"""
PROMEOS KB - Build from Base Documentaire
Parse HTML canonical source → Generate YAML items with full provenance
Usage: python backend/scripts/kb_build_from_docs.py [--doc-id USAGES_ENERGETIQUES_B2B_v1] [--output-dir docs/kb/items/usages]
"""

import sys
import json
import hashlib
import re
from pathlib import Path
from html.parser import HTMLParser
from typing import Dict, List, Any, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class HTMLContentExtractor(HTMLParser):
    """Lightweight HTML parser - no BeautifulSoup dependency"""

    def __init__(self):
        super().__init__()
        self.sections = {}
        self.current_section_id = None
        self.current_tag = None
        self.current_content = []
        self.capture = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Track sections by ID
        if "id" in attrs_dict:
            section_id = attrs_dict["id"]
            if section_id.startswith(("archetype-", "anomalie-", "reco-", "taxonomie-", "mappings-")):
                self.current_section_id = section_id
                self.sections[section_id] = {"content": [], "tag": tag, "class": attrs_dict.get("class", "")}
                self.capture = True

        self.current_tag = tag

    def handle_endtag(self, tag):
        if self.capture and self.current_section_id:
            if tag in ("section", "div") and self.current_tag == tag:
                self.capture = False
                self.current_section_id = None
        self.current_tag = None

    def handle_data(self, data):
        if self.capture and self.current_section_id:
            clean_data = data.strip()
            if clean_data:
                self.sections[self.current_section_id]["content"].append(clean_data)


class KBBuilder:
    """Build KB YAML items from canonical HTML source"""

    def __init__(self, base_doc_dir: Path):
        self.base_doc_dir = base_doc_dir
        self.manifest_path = base_doc_dir / "manifest.json"
        self.manifest = None
        self.source_html = None
        self.source_sha256 = None

    def load_manifest(self) -> Dict[str, Any]:
        """Load and validate manifest.json"""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)

        print(f"[OK] Loaded manifest: {self.manifest['doc_id']} v{self.manifest['version']}")
        return self.manifest

    def verify_source(self) -> bool:
        """Verify SHA256 hash of source HTML"""
        source_path = self.base_doc_dir / self.manifest["source_path"]

        if not source_path.exists():
            raise FileNotFoundError(f"Source HTML not found: {source_path}")

        with open(source_path, "rb") as f:
            content = f.read()
            computed_hash = hashlib.sha256(content).hexdigest()

        expected_hash = self.manifest["sha256"]

        if computed_hash != expected_hash:
            raise ValueError(
                f"SHA256 mismatch!\n"
                f"  Expected: {expected_hash}\n"
                f"  Computed: {computed_hash}\n"
                f"  Source may have been modified!"
            )

        self.source_html = content.decode("utf-8")
        self.source_sha256 = computed_hash

        print(f"[OK] Source verified: SHA256 {computed_hash[:16]}...")
        return True

    def parse_html(self) -> Dict[str, Dict]:
        """Parse HTML and extract sections"""
        parser = HTMLContentExtractor()
        parser.feed(self.source_html)

        print(f"[OK] Parsed HTML: {len(parser.sections)} sections extracted")
        return parser.sections

    def extract_archetypes(self, sections: Dict) -> List[Dict]:
        """Extract archetype YAML items from sections"""
        archetypes = []

        # Get archetype metadata from manifest
        archetype_section = next((s for s in self.manifest["sections"] if s["id"] == "archetypes"), None)

        if not archetype_section:
            print("⚠️  No archetype section in manifest")
            return []

        for arch_meta in archetype_section.get("archetypes", []):
            section_id = arch_meta["id"]

            if section_id not in sections:
                print(f"[WARN] Section {section_id} not found in HTML")
                continue

            section_content = sections[section_id]
            content_text = " ".join(section_content["content"])

            # Extract key information using regex patterns
            code = arch_meta["code"]

            # Extract consumption range
            kwh_match = re.search(r"(\d+)\s*-\s*(\d+)\s*kWh/m²/an", content_text)
            kwh_min = int(kwh_match.group(1)) if kwh_match else None
            kwh_max = int(kwh_match.group(2)) if kwh_match else None

            # Extract description (first sentence)
            desc_match = re.search(r"^([^.]+\.)", content_text)
            description = desc_match.group(1).strip() if desc_match else f"Archétype {code}"

            # Build YAML item
            item = {
                "id": f"ARCHETYPE-{code}",
                "type": "knowledge",
                "domain": "usages",
                "title": f"Archétype {code.replace('_', ' ').title()}",
                "summary": description[:200] if len(description) > 200 else description,
                "tags": {
                    "energy": ["elec"],
                    "segment": self._infer_segment(code),
                    "asset": self._infer_assets(content_text),
                    "reg": [],
                    "granularity": ["mensuel", "horaire"],
                },
                "scope": {"archetype": code, "naf_codes": arch_meta.get("naf_codes", [])},
                "content_md": self._format_archetype_content(content_text, code, kwh_min, kwh_max),
                "logic": None,  # Archetypes don't have logic - they're reference data
                "sources": [
                    {
                        "doc_id": self.manifest["doc_id"],
                        "label": f"{self.manifest['doc_id']} - Section Archétypes",
                        "section": section_id,
                        "anchor": f"#{section_id}",
                        "excerpt_short": description[:150],
                    }
                ],
                "provenance": {
                    "source_path": self.manifest["source_path"],
                    "source_sha256": self.source_sha256,
                    "source_section": section_id,
                    "extracted_at": self.manifest["date"],
                },
                "updated_at": self.manifest["date"],
                "confidence": "high",  # Canonical source = high confidence
                "status": "validated",
                "priority": 2,
            }

            archetypes.append(item)

        print(f"[OK] Extracted {len(archetypes)} archetypes")
        return archetypes

    def extract_anomaly_rules(self, sections: Dict) -> List[Dict]:
        """Extract anomaly detection rules"""
        rules = []

        # Get rules metadata from manifest
        anomaly_section = next((s for s in self.manifest["sections"] if s["id"] == "anomalies"), None)

        if not anomaly_section:
            return []

        for rule_meta in anomaly_section.get("rules", []):
            section_id = rule_meta["id"]

            if section_id not in sections:
                continue

            section_content = sections[section_id]
            content_text = " ".join(section_content["content"])

            code = rule_meta["code"]

            # Extract description
            desc_match = re.search(r"Description\s*:?\s*([^.]+\.)", content_text, re.IGNORECASE)
            description = desc_match.group(1).strip() if desc_match else f"Règle {code}"

            # Determine severity
            severity = "medium"
            if "CRITICAL" in content_text or "CRITIQUE" in content_text.upper():
                severity = "high"
            elif "WARNING" in content_text or "AVERTISSEMENT" in content_text.upper():
                severity = "medium"

            # Build YAML item with logic
            item = {
                "id": f"RULE-{code}",
                "type": "rule",
                "domain": "usages",
                "title": f"Détection {code.replace('_', ' ').title()}",
                "summary": description[:200],
                "tags": {
                    "energy": ["elec"],
                    "segment": ["tertiaire_multisite", "industrie"],
                    "asset": self._infer_assets_from_rule(code),
                    "reg": [],
                    "granularity": ["horaire", "journalier"],
                },
                "scope": {},
                "content_md": self._format_rule_content(content_text, code),
                "logic": {
                    "when": self._extract_rule_logic(code, content_text),
                    "then": {
                        "outputs": [
                            {
                                "type": "anomaly",
                                "label": f"Anomalie détectée: {code}",
                                "severity": severity,
                                "confidence": "medium",
                            }
                        ]
                    },
                },
                "sources": [
                    {
                        "doc_id": self.manifest["doc_id"],
                        "label": f"{self.manifest['doc_id']} - Règles Anomalies",
                        "section": section_id,
                        "anchor": f"#{section_id}",
                        "excerpt_short": description[:150],
                    }
                ],
                "provenance": {
                    "source_path": self.manifest["source_path"],
                    "source_sha256": self.source_sha256,
                    "source_section": section_id,
                    "extracted_at": self.manifest["date"],
                },
                "updated_at": self.manifest["date"],
                "confidence": "high",
                "status": "validated",
                "priority": 2,
            }

            rules.append(item)

        print(f"[OK] Extracted {len(rules)} anomaly rules")
        return rules

    def extract_recommendations(self, sections: Dict) -> List[Dict]:
        """Extract recommendation playbooks"""
        recommendations = []

        # Get reco metadata from manifest
        reco_section = next((s for s in self.manifest["sections"] if s["id"] == "recommandations"), None)

        if not reco_section:
            return []

        for reco_meta in reco_section.get("playbooks", []):
            section_id = reco_meta["id"]

            if section_id not in sections:
                continue

            section_content = sections[section_id]
            content_text = " ".join(section_content["content"])

            code = reco_meta["code"]

            # Extract key info
            desc_match = re.search(r"Action\s*:?\s*([^.]+\.)", content_text, re.IGNORECASE)
            description = desc_match.group(1).strip() if desc_match else f"Recommandation {code}"

            # Extract savings range
            savings_match = re.search(r"(\d+)\s*-\s*(\d+)%", content_text)
            savings_min = int(savings_match.group(1)) if savings_match else 5
            savings_max = int(savings_match.group(2)) if savings_match else 15

            item = {
                "id": f"RECO-{code}",
                "type": "knowledge",
                "domain": "usages",
                "title": f"Recommandation {code.replace('_', ' ').title()}",
                "summary": description[:200],
                "tags": {
                    "energy": ["elec"],
                    "segment": ["tertiaire_multisite"],
                    "asset": self._infer_assets_from_reco(code),
                    "reg": [],
                    "granularity": ["action"],
                },
                "scope": {},
                "content_md": self._format_reco_content(content_text, code, savings_min, savings_max),
                "logic": None,  # Recommendations are templates, not conditional
                "sources": [
                    {
                        "doc_id": self.manifest["doc_id"],
                        "label": f"{self.manifest['doc_id']} - Playbooks Recommandations",
                        "section": section_id,
                        "anchor": f"#{section_id}",
                        "excerpt_short": description[:150],
                    }
                ],
                "provenance": {
                    "source_path": self.manifest["source_path"],
                    "source_sha256": self.source_sha256,
                    "source_section": section_id,
                    "extracted_at": self.manifest["date"],
                },
                "updated_at": self.manifest["date"],
                "confidence": "high",
                "status": "validated",
                "priority": 3,
            }

            recommendations.append(item)

        print(f"[OK] Extracted {len(recommendations)} recommendations")
        return recommendations

    def _infer_segment(self, code: str) -> List[str]:
        """Infer segment tags from archetype code"""
        if "BUREAU" in code or "COMMERCE" in code or "RESTAURATION" in code:
            return ["tertiaire_multisite"]
        elif "HOPITAL" in code:
            return ["collectivite"]
        elif "INDUSTRIE" in code or "LOGISTIQUE" in code:
            return ["industrie"]
        return ["tertiaire_multisite"]

    def _infer_assets(self, content: str) -> List[str]:
        """Infer asset tags from content"""
        assets = []
        content_upper = content.upper()

        if "HVAC" in content_upper or "CVC" in content_upper or "CHAUFFAGE" in content_upper or "CLIM" in content_upper:
            assets.append("hvac")
        if "ÉCLAIRAGE" in content_upper or "LED" in content_upper:
            assets.append("eclairage")
        if "FROID" in content_upper or "RÉFRIGÉRATION" in content_upper:
            assets.append("froid")
        if "IT" in content_upper or "BUREAUTIQUE" in content_upper or "SERVEUR" in content_upper:
            assets.append("it")

        return assets if assets else ["hvac"]  # Default

    def _infer_assets_from_rule(self, code: str) -> List[str]:
        """Infer assets from rule code"""
        if "BASE_NUIT" in code or "WEEKEND" in code:
            return ["hvac", "eclairage", "it"]
        elif "PUISSANCE" in code:
            return ["hvac"]
        elif "GAZ" in code:
            return ["hvac"]
        return ["hvac"]

    def _infer_assets_from_reco(self, code: str) -> List[str]:
        """Infer assets from recommendation code"""
        if "THERMIQUE" in code or "REGULATION" in code:
            return ["hvac"]
        elif "ECLAIRAGE" in code or "LED" in code:
            return ["eclairage"]
        elif "FROID" in code:
            return ["froid"]
        elif "AIR_COMPRIME" in code:
            return ["it"]
        return ["hvac"]

    def _extract_rule_logic(self, code: str, content: str) -> Dict:
        """Extract conditional logic from rule description"""
        # Simplified logic extraction - real implementation would parse thresholds
        # For now, create placeholder conditions that will need manual refinement

        return {
            "all": [
                {
                    "field": "metrics.computed",
                    "op": "=",
                    "value": True,
                    "comment": f"Rule {code} - requires manual threshold configuration",
                }
            ]
        }

    def _format_archetype_content(self, content: str, code: str, kwh_min: Optional[int], kwh_max: Optional[int]) -> str:
        """Format archetype content as markdown"""
        md = f"## Archétype {code.replace('_', ' ').title()}\n\n"

        if kwh_min and kwh_max:
            md += f"### Consommation typique\n"
            md += f"- **Fourchette**: {kwh_min}-{kwh_max} kWh/m²/an\n\n"

        md += "### Caractéristiques\n"
        md += "(Extrait du document source - voir provenance)\n\n"
        md += content[:500] + "...\n"

        return md

    def _format_rule_content(self, content: str, code: str) -> str:
        """Format rule content as markdown"""
        md = f"## Règle de Détection: {code.replace('_', ' ').title()}\n\n"
        md += "### Description\n"
        md += "(Extrait du document source)\n\n"
        md += content[:400] + "...\n"
        return md

    def _format_reco_content(self, content: str, code: str, savings_min: int, savings_max: int) -> str:
        """Format recommendation content as markdown"""
        md = f"## Recommandation: {code.replace('_', ' ').title()}\n\n"
        md += f"### Impact estimé\n"
        md += f"- **Économies potentielles**: {savings_min}-{savings_max}%\n\n"
        md += "### Détails\n"
        md += content[:400] + "...\n"
        return md

    def save_yaml_items(self, items: List[Dict], output_dir: Path):
        """Save YAML items to output directory"""
        import yaml

        output_dir.mkdir(parents=True, exist_ok=True)

        saved_count = 0
        for item in items:
            filename = f"{item['id']}.yaml"
            filepath = output_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(item, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

            saved_count += 1

        print(f"[OK] Saved {saved_count} YAML files to {output_dir}")

    def build(self, output_dir: Path) -> Dict[str, Any]:
        """Main build pipeline"""
        print(f"\n{'=' * 60}")
        print("KB BUILD FROM BASE DOCUMENTAIRE")
        print(f"{'=' * 60}\n")

        # 1. Load manifest
        self.load_manifest()

        # 2. Verify source integrity
        self.verify_source()

        # 3. Parse HTML
        sections = self.parse_html()

        # 4. Extract knowledge items
        archetypes = self.extract_archetypes(sections)
        anomaly_rules = self.extract_anomaly_rules(sections)
        recommendations = self.extract_recommendations(sections)

        all_items = archetypes + anomaly_rules + recommendations

        # 5. Save YAML files
        if all_items:
            self.save_yaml_items(all_items, output_dir)

        # 6. Report
        report = {
            "doc_id": self.manifest["doc_id"],
            "version": self.manifest["version"],
            "source_sha256": self.source_sha256,
            "extracted_at": self.manifest["date"],
            "items_generated": len(all_items),
            "breakdown": {
                "archetypes": len(archetypes),
                "anomaly_rules": len(anomaly_rules),
                "recommendations": len(recommendations),
            },
        }

        print(f"\n{'=' * 60}")
        print("BUILD COMPLETE")
        print(f"{'=' * 60}")
        print(f"Document:       {report['doc_id']} v{report['version']}")
        print(f"Source SHA256:  {report['source_sha256'][:16]}...")
        print(f"Items generated: {report['items_generated']}")
        print(f"  - Archetypes:         {report['breakdown']['archetypes']}")
        print(f"  - Anomaly rules:      {report['breakdown']['anomaly_rules']}")
        print(f"  - Recommendations:    {report['breakdown']['recommendations']}")
        print(f"{'=' * 60}\n")

        return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Build KB YAML items from canonical base documentaire")
    parser.add_argument(
        "--doc-id",
        default="USAGES_ENERGETIQUES_B2B_v1",
        help="Base documentaire ID (default: USAGES_ENERGETIQUES_B2B_v1)",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/kb/items/usages",
        help="Output directory for YAML files (default: docs/kb/items/usages)",
    )

    args = parser.parse_args()

    # Resolve paths
    base_doc_dir = Path(f"docs/base_documentaire/usages_energetiques_b2b")
    output_dir = Path(args.output_dir)

    if not base_doc_dir.exists():
        print(f"[ERROR] Base documentaire directory not found: {base_doc_dir}")
        sys.exit(1)

    # Build
    builder = KBBuilder(base_doc_dir)

    try:
        report = builder.build(output_dir)

        # Success
        print("[OK] KB build successful!")
        sys.exit(0)

    except Exception as e:
        print(f"\n[ERROR] BUILD FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
