"""
PROMEOS Bill Intelligence — JSON Invoice Parser
Parse demo JSON invoices into canonical Invoice objects.
"""
import json
import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

import re

from ..domain import (
    Invoice, InvoiceComponent, EnergyType, InvoiceStatus,
    ShadowLevel, ComponentType, BillingConcept, ConceptAllocation,
)


def _parse_date(val: Optional[str]) -> Optional[date]:
    """Parse YYYY-MM-DD string to date."""
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _parse_component_type(val: str) -> ComponentType:
    """Map string to ComponentType enum (with fallback)."""
    try:
        return ComponentType(val)
    except ValueError:
        return ComponentType.AUTRE


# ========================================
# Concept Allocation: ComponentType -> BillingConcept
# ========================================

_COMPONENT_CONCEPT_MAP: Dict[ComponentType, str] = {
    # Fourniture (energie)
    ComponentType.CONSO_HP: BillingConcept.FOURNITURE.value,
    ComponentType.CONSO_HC: BillingConcept.FOURNITURE.value,
    ComponentType.CONSO_BASE: BillingConcept.FOURNITURE.value,
    ComponentType.CONSO_POINTE: BillingConcept.FOURNITURE.value,
    ComponentType.CONSO_HPH: BillingConcept.FOURNITURE.value,
    ComponentType.CONSO_HCH: BillingConcept.FOURNITURE.value,
    ComponentType.CONSO_HPE: BillingConcept.FOURNITURE.value,
    ComponentType.CONSO_HCE: BillingConcept.FOURNITURE.value,
    ComponentType.TERME_VARIABLE: BillingConcept.FOURNITURE.value,
    # Acheminement (reseau)
    ComponentType.TURPE_FIXE: BillingConcept.ACHEMINEMENT.value,
    ComponentType.TURPE_PUISSANCE: BillingConcept.ACHEMINEMENT.value,
    ComponentType.TURPE_ENERGIE: BillingConcept.ACHEMINEMENT.value,
    # Abonnement
    ComponentType.ABONNEMENT: BillingConcept.ABONNEMENT.value,
    ComponentType.TERME_FIXE: BillingConcept.ABONNEMENT.value,
    # Taxes & contributions
    ComponentType.CTA: BillingConcept.TAXES_CONTRIBUTIONS.value,
    ComponentType.ACCISE: BillingConcept.TAXES_CONTRIBUTIONS.value,
    ComponentType.CEE: BillingConcept.TAXES_CONTRIBUTIONS.value,
    # TVA
    ComponentType.TVA_REDUITE: BillingConcept.TVA.value,
    ComponentType.TVA_NORMALE: BillingConcept.TVA.value,
    # Capacite / depassement
    ComponentType.DEPASSEMENT_PUISSANCE: BillingConcept.CAPACITE.value,
    ComponentType.REACTIVE: BillingConcept.CAPACITE.value,
    # Ajustement
    ComponentType.PRORATA: BillingConcept.AJUSTEMENT.value,
    ComponentType.REGULARISATION: BillingConcept.AJUSTEMENT.value,
    ComponentType.REMISE: BillingConcept.AJUSTEMENT.value,
    # Penalite
    ComponentType.PENALITE: BillingConcept.PENALITE.value,
}

# Regex fallback rules for label-based allocation (used when component_type is AUTRE)
_LABEL_CONCEPT_RULES: list = [
    (re.compile(r"abonnement|prime\s+fixe|souscri", re.IGNORECASE), BillingConcept.ABONNEMENT.value, 0.85),
    (re.compile(r"consommation|energie|kwh|heure|hp\b|hc\b|base|pointe", re.IGNORECASE), BillingConcept.FOURNITURE.value, 0.80),
    (re.compile(r"turpe|acheminement|soutirage|gestion|atrd|reseau", re.IGNORECASE), BillingConcept.ACHEMINEMENT.value, 0.85),
    (re.compile(r"accise|cspe|ticfe|ticgn|taxe|cta|contribution", re.IGNORECASE), BillingConcept.TAXES_CONTRIBUTIONS.value, 0.85),
    (re.compile(r"tva", re.IGNORECASE), BillingConcept.TVA.value, 0.90),
    (re.compile(r"depassement|reactive|capacit", re.IGNORECASE), BillingConcept.CAPACITE.value, 0.80),
    (re.compile(r"regularis|prorata|ajust|remise|avoir", re.IGNORECASE), BillingConcept.AJUSTEMENT.value, 0.75),
    (re.compile(r"penalite|indemnit|retard", re.IGNORECASE), BillingConcept.PENALITE.value, 0.80),
    (re.compile(r"cee|certificat|economie", re.IGNORECASE), BillingConcept.TAXES_CONTRIBUTIONS.value, 0.70),
]


def allocate_concept(comp: InvoiceComponent) -> ConceptAllocation:
    """
    Allocate a billing concept to a component.
    Strategy: component_type mapping first (confidence=1.0),
    then regex on label as fallback (confidence 0.70-0.90).
    """
    # 1. Direct mapping from component_type
    if comp.component_type in _COMPONENT_CONCEPT_MAP:
        return ConceptAllocation(
            concept_id=_COMPONENT_CONCEPT_MAP[comp.component_type],
            confidence=1.0,
            matched_rules=[f"type:{comp.component_type.value}"],
        )

    # 2. Regex fallback on label
    label = comp.label or ""
    for pattern, concept_id, confidence in _LABEL_CONCEPT_RULES:
        if pattern.search(label):
            return ConceptAllocation(
                concept_id=concept_id,
                confidence=confidence,
                matched_rules=[f"label_regex:{pattern.pattern[:40]}"],
            )

    # 3. Unmatched → autre
    return ConceptAllocation(
        concept_id=BillingConcept.AUTRE.value,
        confidence=0.5,
        matched_rules=["fallback:unmatched"],
    )


def _compute_input_hash(raw: str) -> str:
    """SHA-256 of raw input for reproducibility."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def parse_json_invoice(raw_json: str, source_file: Optional[str] = None) -> Invoice:
    """
    Parse a JSON string into a canonical Invoice.
    Validates structure and sets shadow_level = L0.
    """
    data = json.loads(raw_json)
    return _build_invoice(data, raw_json, source_file)


def parse_json_file(file_path: str) -> Invoice:
    """Parse a JSON file into a canonical Invoice."""
    path = Path(file_path)
    raw = path.read_text(encoding="utf-8")
    return parse_json_invoice(raw, source_file=str(path.name))


def _build_invoice(data: Dict[str, Any], raw_json: str, source_file: Optional[str]) -> Invoice:
    """Build Invoice from parsed dict."""
    # Parse components
    components = []
    for comp_data in data.get("components", []):
        comp = InvoiceComponent(
            component_type=_parse_component_type(comp_data.get("component_type", "autre")),
            label=comp_data.get("label", ""),
            quantity=comp_data.get("quantity"),
            unit=comp_data.get("unit"),
            unit_price=comp_data.get("unit_price"),
            amount_ht=comp_data.get("amount_ht"),
            amount_ttc=comp_data.get("amount_ttc"),
            tva_rate=comp_data.get("tva_rate"),
            tva_amount=comp_data.get("tva_amount"),
            period_start=_parse_date(comp_data.get("period_start")),
            period_end=_parse_date(comp_data.get("period_end")),
            metadata={k: v for k, v in comp_data.items() if k.startswith("_")},
        )
        comp.allocation = allocate_concept(comp)
        components.append(comp)

    invoice = Invoice(
        invoice_id=data.get("invoice_id", "UNKNOWN"),
        energy_type=EnergyType(data.get("energy_type", "elec")),
        supplier=data.get("supplier", "UNKNOWN"),
        contract_ref=data.get("contract_ref"),
        pdl_pce=data.get("pdl_pce"),
        site_id=data.get("site_id"),
        invoice_date=_parse_date(data.get("invoice_date")),
        due_date=_parse_date(data.get("due_date")),
        period_start=_parse_date(data.get("period_start")),
        period_end=_parse_date(data.get("period_end")),
        total_ht=data.get("total_ht"),
        total_tva=data.get("total_tva"),
        total_ttc=data.get("total_ttc"),
        conso_kwh=data.get("conso_kwh"),
        puissance_souscrite_kva=data.get("puissance_souscrite_kva"),
        components=components,
        status=InvoiceStatus.PARSED,
        source_file=source_file,
        source_format=data.get("source_format", "json"),
        import_timestamp=datetime.now(timezone.utc).isoformat(),
        parsing_confidence=1.0,  # JSON = deterministic parsing
        shadow_level=ShadowLevel.L0_READ,
        input_hash=_compute_input_hash(raw_json),
    )

    return invoice


def list_demo_invoices() -> list:
    """List all demo invoice files."""
    demo_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "invoices" / "demo"
    if not demo_dir.exists():
        return []
    return sorted([f.name for f in demo_dir.glob("*.json")])


def load_all_demo_invoices() -> list:
    """Load and parse all demo invoices."""
    demo_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "invoices" / "demo"
    if not demo_dir.exists():
        return []

    invoices = []
    for f in sorted(demo_dir.glob("*.json")):
        try:
            inv = parse_json_file(str(f))
            invoices.append(inv)
        except Exception as e:
            print(f"Error parsing {f.name}: {e}")
    return invoices
