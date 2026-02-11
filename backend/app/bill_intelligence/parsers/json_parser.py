"""
PROMEOS Bill Intelligence — JSON Invoice Parser
Parse demo JSON invoices into canonical Invoice objects.
"""
import json
import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from ..domain import (
    Invoice, InvoiceComponent, EnergyType, InvoiceStatus,
    ShadowLevel, ComponentType,
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
