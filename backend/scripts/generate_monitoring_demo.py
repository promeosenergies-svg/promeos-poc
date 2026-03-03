"""
PROMEOS - Generate monitoring demo data with power signatures and anomalies.
Creates 2 sites with distinct consumption patterns and embedded anomalies.

Site 1: Bureau standard (office) - 90 days hourly data
  - Clean pattern: day/night variation, weekend dip
  - Anomaly: high night base for 2 weeks (month 2)
  - Anomaly: weekend spike (week 6)

Site 2: Commerce (supermarket) - 90 days hourly data
  - Flat curve (high base load: fridges)
  - Anomaly: power exceedance events (5 spikes above subscribed)
  - Anomaly: 3-day data gap
  - Anomaly: 2 negative readings
"""
import sys
import os
import math
import random
from datetime import datetime, timedelta, timezone

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.connection import SessionLocal
from models import Site, Meter, MeterReading, FrequencyType
from models.energy_models import EnergyVector


def generate():
    db = SessionLocal()
    try:
        _generate_site1(db)
        _generate_site2(db)
        print("Demo monitoring data generated successfully.")
    finally:
        db.close()


def _generate_site1(db):
    """Bureau standard - clean pattern with night base anomaly."""
    # Find or create site 1
    site = db.query(Site).filter_by(id=1).first()
    if not site:
        print("Site 1 not found, skipping site1 generation")
        return

    meter_id_str = "PRM-MON-001"
    meter = db.query(Meter).filter_by(meter_id=meter_id_str).first()
    if not meter:
        meter = Meter(
            meter_id=meter_id_str,
            name="Compteur Monitoring Bureau",
            site_id=site.id,
            energy_vector=EnergyVector.ELECTRICITY,
            subscribed_power_kva=80.0,
            tariff_type="C5"
        )
        db.add(meter)
        db.commit()
        db.refresh(meter)
    else:
        # Clear existing readings for this meter
        db.query(MeterReading).filter_by(meter_id=meter.id).delete()
        db.commit()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=90)
    readings = []
    random.seed(42)

    for day_offset in range(90):
        dt = start + timedelta(days=day_offset)
        day_of_week = dt.weekday()
        is_weekend = day_of_week >= 5
        month_offset = day_offset // 30  # 0, 1, 2

        for hour in range(24):
            ts = dt.replace(hour=hour, minute=0, second=0, microsecond=0)

            # Base office profile
            if is_weekend:
                base_kwh = 5.0  # Low weekend
            elif 8 <= hour <= 18:
                base_kwh = 35.0  # Office hours
            elif 7 <= hour <= 7 or 19 <= hour <= 20:
                base_kwh = 18.0  # Ramp up/down
            else:
                base_kwh = 6.0  # Night base

            # Seasonal (winter = higher)
            seasonal = 1.0 + 0.15 * math.cos(2 * math.pi * (dt.month - 1) / 12.0)
            value = base_kwh * seasonal

            # ANOMALY 1: High night base in month 2 (days 30-44)
            if 30 <= day_offset <= 44 and (hour < 7 or hour > 19) and not is_weekend:
                value *= 2.5  # Stuck HVAC at night

            # ANOMALY 2: Weekend spike in week 6 (days 35-36)
            if day_offset in [35, 36] and is_weekend:
                value = 40.0  # Unexpected weekend consumption

            # Noise
            value *= random.uniform(0.90, 1.10)
            value = max(0.1, round(value, 2))

            readings.append(MeterReading(
                meter_id=meter.id,
                timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=value,
                is_estimated=False
            ))

    db.bulk_save_objects(readings)
    db.commit()
    print(f"  Site 1 (Bureau): {len(readings)} readings generated for meter {meter_id_str}")


def _generate_site2(db):
    """Commerce - flat curve with power exceedance and data issues."""
    site = db.query(Site).filter_by(id=2).first()
    if not site:
        # Try site 1 if no site 2
        site = db.query(Site).filter_by(id=1).first()
        if not site:
            print("No sites found, skipping site2 generation")
            return

    meter_id_str = "PRM-MON-002"
    meter = db.query(Meter).filter_by(meter_id=meter_id_str).first()
    if not meter:
        meter = Meter(
            meter_id=meter_id_str,
            name="Compteur Monitoring Commerce",
            site_id=site.id,
            energy_vector=EnergyVector.ELECTRICITY,
            subscribed_power_kva=60.0,  # Deliberately low for depassement
            tariff_type="C5"
        )
        db.add(meter)
        db.commit()
        db.refresh(meter)
    else:
        db.query(MeterReading).filter_by(meter_id=meter.id).delete()
        db.commit()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=90)
    readings = []
    random.seed(123)

    for day_offset in range(90):
        dt = start + timedelta(days=day_offset)
        day_of_week = dt.weekday()
        is_weekend = day_of_week >= 5

        # ANOMALY: 3-day data gap (days 50-52)
        if 50 <= day_offset <= 52:
            continue

        for hour in range(24):
            ts = dt.replace(hour=hour, minute=0, second=0, microsecond=0)

            # Flat commerce profile (fridges always on)
            base_kwh = 45.0  # High base
            if 8 <= hour <= 20:
                base_kwh = 55.0  # Open hours bump
            if is_weekend and 10 <= hour <= 18:
                base_kwh = 52.0  # Slightly lower weekend

            # ANOMALY: Power spikes that exceed 60 kVA (5 events)
            if (day_offset == 10 and hour == 14) or \
               (day_offset == 25 and hour == 11) or \
               (day_offset == 40 and hour == 15) or \
               (day_offset == 60 and hour == 13) or \
               (day_offset == 75 and hour == 16):
                base_kwh = 85.0  # Way above 60 kVA subscribed

            # ANOMALY: 2 negative readings
            if day_offset == 20 and hour == 3:
                base_kwh = -2.5
            if day_offset == 65 and hour == 2:
                base_kwh = -1.0

            value = base_kwh * random.uniform(0.92, 1.08)
            value = round(value, 2)

            readings.append(MeterReading(
                meter_id=meter.id,
                timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=value,
                is_estimated=False
            ))

    db.bulk_save_objects(readings)
    db.commit()
    print(f"  Site 2 (Commerce): {len(readings)} readings generated for meter {meter_id_str}")


if __name__ == "__main__":
    generate()
