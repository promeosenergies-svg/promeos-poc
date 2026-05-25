"""
Tests P0 cleanup cockpit (2026-05-25) — billing_kpis_cockpit_service.

Couvre :
1. La fonction retourne un dict avec 4 KPIs canoniques.
2. Chaque KPI expose source/formula/unit/period/scope/link_to (doctrine §8.1).
3. Les liens pointent vers /bill-intel et /centre-action?domain=facturation.
4. Comptages corrects (insights ouverts, anomalies par énergie, actions).
5. Filtres : insights closed/false_positive exclus.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (  # noqa: E402
    Base,
    BillingInsight,
    EnergyContract,
    EnergyInvoice,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)
from models.enums import BillingEnergyType, InsightStatus  # noqa: E402
from models.v4.action_center_items import ActionCenterItem  # noqa: E402
from models.v4.enums import ClosureReason, Domain, Kind, LifecycleState  # noqa: E402
from services.billing_kpis_cockpit_service import compute_billing_kpis_cockpit  # noqa: E402


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


def _seed(db, *, insights_elec_open=0, insights_gaz_open=0, insights_closed=0,
          loss_per_insight=100.0, actions_facturation_open=0, actions_facturation_closed=0):
    """Seed minimal : 1 org + 1 site + N contracts/invoices/insights/actions."""
    org = Organisation(nom="Org Test", siren="111111111", actif=True)
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
        nom="Site Test",
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        actif=True,
    )
    db.add(site)
    db.flush()

    def _make_contract_invoice_insight(energy_type, status, idx):
        contract = EnergyContract(
            site_id=site.id,
            supplier_name="EDF",
            energy_type=energy_type,
            start_date=date(2026, 1, 1),
            end_date=date(2027, 1, 1),
        )
        db.add(contract)
        db.flush()
        invoice = EnergyInvoice(
            site_id=site.id,
            contract_id=contract.id,
            invoice_number=f"INV-{idx}",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            issue_date=date(2026, 5, 5),
            total_eur=1000.0,
            energy_kwh=5000,
            source="manual",
        )
        db.add(invoice)
        db.flush()
        insight = BillingInsight(
            site_id=site.id,
            invoice_id=invoice.id,
            type="shadow_gap",
            severity="high",
            message=f"Insight {idx}",
            estimated_loss_eur=loss_per_insight,
            insight_status=status,
        )
        db.add(insight)
        return insight

    for i in range(insights_elec_open):
        _make_contract_invoice_insight(BillingEnergyType.ELEC, InsightStatus.OPEN, f"elec-{i}")
    for i in range(insights_gaz_open):
        _make_contract_invoice_insight(BillingEnergyType.GAZ, InsightStatus.OPEN, f"gaz-{i}")
    for i in range(insights_closed):
        _make_contract_invoice_insight(BillingEnergyType.ELEC, InsightStatus.RESOLVED, f"closed-{i}")

    # Actions facturation
    import uuid as _uuid

    for i in range(actions_facturation_open):
        db.add(
            ActionCenterItem(
                id=_uuid.uuid4(),
                organisation_id=org.id,
                kind=Kind.ANOMALY.value,
                domain=Domain.FACTURATION.value,
                title=f"Action ouverte {i}",
                description="x",
                lifecycle_state=LifecycleState.NEW.value,
                priority_bracket="P2",
                priority_score=50.0,
            )
        )
    from datetime import datetime, timezone as _tz

    for i in range(actions_facturation_closed):
        db.add(
            ActionCenterItem(
                id=_uuid.uuid4(),
                organisation_id=org.id,
                kind=Kind.ANOMALY.value,
                domain=Domain.FACTURATION.value,
                title=f"Action close {i}",
                description="x",
                lifecycle_state=LifecycleState.CLOSED.value,
                closed_at=datetime.now(_tz.utc),
                closure_reason=ClosureReason.RESOLVED.value,
                priority_bracket="P2",
                priority_score=50.0,
            )
        )

    db.commit()
    return org, site


# ─── 1. Structure du payload ──────────────────────────────────────────


class TestPayloadStructure:
    def test_returns_4_kpis_avec_links(self, db):
        org, _ = _seed(db, insights_elec_open=1)
        result = compute_billing_kpis_cockpit(db, org.id)
        assert "kpis" in result
        assert "links" in result
        assert len(result["kpis"]) == 4
        ids = [k["id"] for k in result["kpis"]]
        assert "surfacturations_a_contester" in ids
        assert "anomalies_ouvertes" in ids
        assert "anomalies_par_energie" in ids
        assert "actions_facturation_ouvertes" in ids

    def test_chaque_kpi_a_metadata_obligatoire(self, db):
        org, _ = _seed(db, insights_elec_open=1)
        result = compute_billing_kpis_cockpit(db, org.id)
        for kpi in result["kpis"]:
            assert "id" in kpi
            assert "label_fr" in kpi and kpi["label_fr"]
            assert "value" in kpi
            assert "unit" in kpi and kpi["unit"]
            assert "source" in kpi and kpi["source"]
            assert "formula" in kpi and kpi["formula"]
            assert "period" in kpi
            assert "scope" in kpi
            assert "link_to" in kpi

    def test_links_canoniques(self, db):
        org, _ = _seed(db)
        result = compute_billing_kpis_cockpit(db, org.id)
        assert result["links"]["bill_intel"] == "/bill-intel"
        assert result["links"]["centre_action_facturation"] == "/centre-action?domain=facturation"


# ─── 2. Comptages ─────────────────────────────────────────────────────


class TestComptages:
    def test_surfacturations_somme_loss_eur(self, db):
        org, _ = _seed(db, insights_elec_open=3, loss_per_insight=250.0)
        result = compute_billing_kpis_cockpit(db, org.id)
        surfact = next(k for k in result["kpis"] if k["id"] == "surfacturations_a_contester")
        assert surfact["value"] == 750.0  # 3 × 250

    def test_anomalies_ouvertes_compte_ack_et_open(self, db):
        org, _ = _seed(db, insights_elec_open=2, insights_gaz_open=3)
        result = compute_billing_kpis_cockpit(db, org.id)
        ano = next(k for k in result["kpis"] if k["id"] == "anomalies_ouvertes")
        assert ano["value"] == 5

    def test_insights_closed_exclus(self, db):
        org, _ = _seed(db, insights_elec_open=1, insights_closed=5)
        result = compute_billing_kpis_cockpit(db, org.id)
        ano = next(k for k in result["kpis"] if k["id"] == "anomalies_ouvertes")
        assert ano["value"] == 1, "Les insights RESOLVED ne doivent pas être comptés"

    def test_anomalies_par_energie_breakdown(self, db):
        org, _ = _seed(db, insights_elec_open=2, insights_gaz_open=3)
        result = compute_billing_kpis_cockpit(db, org.id)
        par_energie = next(k for k in result["kpis"] if k["id"] == "anomalies_par_energie")
        breakdown = par_energie["value"]
        assert breakdown["elec"] == 2
        assert breakdown["gaz"] == 3
        assert breakdown["inconnu"] == 0

    def test_actions_facturation_ouvertes_exclut_closed(self, db):
        org, _ = _seed(db, actions_facturation_open=3, actions_facturation_closed=4)
        result = compute_billing_kpis_cockpit(db, org.id)
        actions = next(k for k in result["kpis"] if k["id"] == "actions_facturation_ouvertes")
        assert actions["value"] == 3, "Les actions CLOSED ne doivent pas être comptées"


# ─── 3. Edge cases ───────────────────────────────────────────────────


class TestEdgeCases:
    def test_org_id_none_retourne_vide(self, db):
        result = compute_billing_kpis_cockpit(db, None)
        assert result["kpis"] == []
        assert result["links"] == {}

    def test_org_sans_donnees_retourne_kpis_a_zero(self, db):
        org, _ = _seed(db)  # aucune donnée billing
        result = compute_billing_kpis_cockpit(db, org.id)
        assert len(result["kpis"]) == 4
        for kpi in result["kpis"]:
            if kpi["id"] == "anomalies_par_energie":
                assert kpi["value"] == {"elec": 0, "gaz": 0, "inconnu": 0}
            elif kpi["unit"] == "EUR":
                assert kpi["value"] == 0.0
            else:
                assert kpi["value"] == 0
