"""
PROMEOS Connectors - Contract definitions and mapping validator.
Defines required fields, sanity ranges, and validation logic.
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConnectorMeta:
    name: str
    version: str
    capabilities: list[str] = field(default_factory=list)


@dataclass
class MappingReport:
    connector: str
    mapped_fields: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    valid: bool = True


# Required fields per object_type
REQUIRED_FIELDS = {
    "site": ["metric", "value", "unit", "ts_start"],
    "meter": ["metric", "value", "unit", "ts_start"],
}

# Sanity ranges for known metrics
SANITY_RANGES = {
    "grid_co2_intensity": (0, 2000),       # gCO2/kWh
    "pv_prod_estimate_kwh": (0, 100000),   # kWh/month
    "temperature": (-50, 60),              # Celsius
    "wind_speed": (0, 200),                # km/h
    "consumption_kwh": (0, 10000000),      # kWh
    "solar_irradiance": (0, 1500),         # W/m2
}


def validate_mapping(object_type: str, records: list[dict], connector_name: str = "") -> MappingReport:
    """
    Validate connector output records against contract.

    1. Check required fields present in each record
    2. Type checks (value is numeric, ts_start is datetime-like)
    3. Range sanity checks for known metrics
    """
    required = REQUIRED_FIELDS.get(object_type, REQUIRED_FIELDS.get("site", []))

    report = MappingReport(connector=connector_name)
    all_fields_seen = set()

    for i, record in enumerate(records):
        if not isinstance(record, dict):
            report.warnings.append(f"Record {i}: not a dict")
            report.valid = False
            continue

        all_fields_seen.update(record.keys())

        # Required fields check
        for f in required:
            if f not in record:
                if f not in report.missing_fields:
                    report.missing_fields.append(f)
                report.valid = False

        # Type checks
        if "value" in record:
            val = record["value"]
            if val is not None and not isinstance(val, (int, float)):
                report.warnings.append(f"Record {i}: value is not numeric ({type(val).__name__})")
                report.valid = False

        if "ts_start" in record:
            ts = record["ts_start"]
            if ts is not None and not isinstance(ts, (str, datetime)):
                report.warnings.append(f"Record {i}: ts_start is not datetime/str ({type(ts).__name__})")

        # Range sanity
        metric = record.get("metric", "")
        value = record.get("value")
        if metric in SANITY_RANGES and value is not None and isinstance(value, (int, float)):
            lo, hi = SANITY_RANGES[metric]
            if value < lo or value > hi:
                report.warnings.append(
                    f"Record {i}: {metric}={value} out of range [{lo}, {hi}]"
                )

    report.mapped_fields = sorted(all_fields_seen)
    return report
