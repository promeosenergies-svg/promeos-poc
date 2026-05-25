"""
PROMEOS — Bill Intelligence P1 C1 (2026-05-24) : invariant `is_monetizable`.

Vérifie l'invariant doctrinal sur `BillAnomaly` introduit par la migration
`p38_bill_anomaly_monetizable.py` :

- `is_monetizable=True` → `actual_value` doit être renseigné (sinon
  `BillAnomalyValidationError` + flush rollback)
- `is_monetizable=False` → `non_monetizable_reason` obligatoire (FR clair)

Cf. audit `phase_0bis_exploration_drive_billing_2026_05_24.md` §7.1 et
`audit_brique_bill_intelligence_deep_readonly_2026_05_23.md` P0 §3.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, EntiteJuridique, Organisation, Portefeuille, Site, TypeSite  # noqa: E402
from models.bill_anomaly import (  # noqa: E402
    BillAnomaly,
    BillAnomalyValidationError,
)
from models.billing_models import EnergyInvoice  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _seed_invoice(db):
    org = Organisation(nom="Org C1", siren="111111111", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="111111111")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site C1",
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        actif=True,
    )
    db.add(site)
    db.flush()
    invoice = EnergyInvoice(
        site_id=site.id,
        invoice_number="INV-C1-001",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        issue_date=date(2026, 5, 5),
        total_eur=1234.56,
        energy_kwh=8000,
        source="manual",
    )
    db.add(invoice)
    db.commit()
    return org, site, invoice


# ─── Invariant 1 : valorisable sans actual_value → rejet ────────────────


def test_monetizable_anomaly_without_actual_value_is_rejected(db):
    """Anomalie valorisable (`is_monetizable=True`) sans `actual_value` → rejet."""
    _, _, invoice = _seed_invoice(db)
    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="warning",
        # is_monetizable=True par défaut, actual_value absent → doit lever
    )
    db.add(anomaly)
    with pytest.raises(BillAnomalyValidationError, match="is_monetizable=True \\(défaut\\)"):
        db.flush()


def test_monetizable_anomaly_with_actual_value_is_accepted(db):
    """Anomalie valorisable avec `actual_value` chiffré → acceptée."""
    _, _, invoice = _seed_invoice(db)
    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="warning",
        actual_value=Decimal("42.50"),
        details_json={"vnu_total_eur": 42.50, "vnu_lines_count": 3},
    )
    db.add(anomaly)
    db.flush()  # ne doit pas lever
    db.commit()
    assert anomaly.id is not None
    assert anomaly.is_monetizable is True
    assert anomaly.actual_value == Decimal("42.5000")


# ─── Invariant 2 : non valorisable sans raison → rejet ──────────────────


def test_non_monetizable_anomaly_without_reason_is_rejected(db):
    """Anomalie `is_monetizable=False` sans `non_monetizable_reason` → rejet."""
    _, _, invoice = _seed_invoice(db)
    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code="R017",
        severity="info",
        is_monetizable=False,
        # non_monetizable_reason absent → doit lever
    )
    db.add(anomaly)
    with pytest.raises(BillAnomalyValidationError, match="non_monetizable_reason"):
        db.flush()


def test_non_monetizable_anomaly_with_empty_reason_is_rejected(db):
    """Raison `'   '` (whitespace seulement) → rejet."""
    _, _, invoice = _seed_invoice(db)
    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code="R017",
        severity="info",
        is_monetizable=False,
        non_monetizable_reason="   ",
    )
    db.add(anomaly)
    with pytest.raises(BillAnomalyValidationError, match="non_monetizable_reason"):
        db.flush()


def test_non_monetizable_anomaly_with_reason_is_accepted(db):
    """Anomalie informative avec raison FR claire → acceptée."""
    _, _, invoice = _seed_invoice(db)
    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code="R017",
        severity="info",
        is_monetizable=False,
        non_monetizable_reason="PDL manquant — impact non chiffrable sans rattachement contractuel.",
    )
    db.add(anomaly)
    db.flush()
    db.commit()
    assert anomaly.id is not None
    assert anomaly.is_monetizable is False
    assert anomaly.actual_value is None  # autorisé pour les informatives


# ─── Invariant sur UPDATE ───────────────────────────────────────────────


def test_update_to_monetizable_without_actual_value_is_rejected(db):
    """Anomalie passant `is_monetizable=False → True` sans actual_value → rejet."""
    _, _, invoice = _seed_invoice(db)
    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code="R017",
        severity="info",
        is_monetizable=False,
        non_monetizable_reason="Initialement informative.",
    )
    db.add(anomaly)
    db.commit()

    # Mutation : on rebascule en valorisable sans renseigner actual_value
    anomaly.is_monetizable = True
    with pytest.raises(BillAnomalyValidationError, match="is_monetizable=True"):
        db.flush()
        db.commit()


# ─── KPI VNU : 0 anomalie valorisable sans actual_value ────────────────


def test_kpi_vnu_aggregates_only_monetizable_with_value(db):
    """KPI VNU dormant n'agrège que les anomalies valorisables avec montant fiable."""
    _, _, invoice = _seed_invoice(db)
    db.add(
        BillAnomaly(
            invoice_id=invoice.id,
            code="R19",
            severity="critical",
            actual_value=Decimal("100.00"),
            details_json={"vnu_total_eur": 100.00},
        )
    )
    db.add(
        BillAnomaly(
            invoice_id=invoice.id,
            code="R017",
            severity="info",
            is_monetizable=False,
            non_monetizable_reason="Informative seule.",
        )
    )
    db.commit()

    # Agrégat KPI : ne prend que les is_monetizable=True avec actual_value
    from sqlalchemy import func

    total_reclaim = (
        db.query(func.coalesce(func.sum(BillAnomaly.actual_value), 0))
        .filter(
            BillAnomaly.is_monetizable.is_(True),
            BillAnomaly.actual_value.isnot(None),
        )
        .scalar()
    )
    assert float(total_reclaim) == 100.00, "Seule l'anomalie valorisable doit compter dans le KPI"
