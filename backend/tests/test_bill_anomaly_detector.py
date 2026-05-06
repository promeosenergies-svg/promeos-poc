"""
PROMEOS — Tests Bill Intelligence anomaly_detector (Sprint C-5 Phase 5.1, ADR-013).

Couverture cardinal :
- R19 VNU dormant : détection + skip si usage / seuil YAML / agrégation multi-lignes
- R20 capacité variance : 1 anomaly par poste / matching period_code / no contract / résilience
- Helper _resolve_period_code : 3 priorités (champ direct / meta_json / label)
- Pipeline detect_anomalies_for_invoice : résilience par-action
- Cohérence YAML ↔ runtime (SG cardinal)
"""

from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Fixtures bulk org ─────────────────────────────────────────────────────


@pytest.fixture
def db_session():
    """In-memory SQLite avec schema déployé pour tests Bill Intelligence."""
    from models import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_org_site_meter_contract(db, ps_dict=None):
    """Crée Org → EJ → Pf → Site → Meter → PowerContract pour tests R20."""
    from datetime import date

    from models import (
        EnergyVector,
        EntiteJuridique,
        Meter,
        Organisation,
        Portefeuille,
        PowerContract,
        Site,
        TypeSite,
    )

    org = Organisation(nom="TestOrg", siren="100000001")
    db.add(org)
    db.flush()

    ej = EntiteJuridique(nom="TestEJ", siren="100000001", organisation_id=org.id)
    db.add(ej)
    db.flush()

    pf = Portefeuille(nom="TestPF", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()

    site = Site(
        nom="TestSite",
        type=TypeSite.BUREAU,
        actif=True,
        portefeuille_id=pf.id,
        surface_m2=500,
    )
    db.add(site)
    db.flush()

    meter = Meter(
        meter_id="PRM-TEST-001",
        name="Meter Test",
        site_id=site.id,
        energy_vector=EnergyVector.ELECTRICITY,
        subscribed_power_kva=36,
    )
    db.add(meter)
    db.flush()

    if ps_dict is None:
        ps_dict = {"HPH": 36, "HCH": 36, "HPB": 36, "HCB": 36}

    contract = PowerContract(
        meter_id=meter.id,
        date_debut=date(2026, 1, 1),
        date_fin=None,
        domaine_tension="BT",
        fta_code="BTSUPCU4",
        ps_par_poste_kva=ps_dict,
    )
    db.add(contract)
    db.commit()

    return org, site, meter, contract


def _seed_invoice(db, site, energy_kwh=10000, period_start=None, period_end=None):
    """Crée 1 EnergyInvoice rattachée au site."""
    from datetime import date

    from models import BillingInvoiceStatus, EnergyInvoice

    invoice = EnergyInvoice(
        site_id=site.id,
        invoice_number=f"INV-{site.id}-{energy_kwh}",
        period_start=period_start or date(2026, 4, 1),
        period_end=period_end or date(2026, 4, 30),
        issue_date=date(2026, 5, 5),
        total_eur=1500.0,
        energy_kwh=energy_kwh,
        status=BillingInvoiceStatus.IMPORTED,
        source="test",
    )
    db.add(invoice)
    db.commit()
    return invoice


def _add_line(db, invoice, line_type, label, qty=None, unit=None, amount_eur=None, period_code=None, meta=None):
    from models import EnergyInvoiceLine

    line = EnergyInvoiceLine(
        invoice_id=invoice.id,
        line_type=line_type,
        label=label,
        qty=qty,
        unit=unit,
        amount_eur=amount_eur,
        period_code=period_code,
        meta_json=meta,
    )
    db.add(line)
    db.commit()
    return line


# ─── R19 VNU dormant ────────────────────────────────────────────────────────


def test_detect_r19_vnu_dormant_flags_when_no_usage(db_session):
    """R19 : VNU > seuil + consumption < 100 kWh = anomaly warning."""
    from services.bill_intelligence import detect_r19_vnu_dormant

    _, site, _, _ = _seed_org_site_meter_contract(db_session)
    invoice = _seed_invoice(db_session, site, energy_kwh=50)  # < 100
    _add_line(db_session, invoice, "tax", "VNU - Versement Nucléaire Universel", amount_eur=12.50)

    anomaly = detect_r19_vnu_dormant(invoice, db_session)

    assert anomaly is not None
    assert anomaly.code == "R19"
    assert anomaly.severity == "warning"
    assert float(anomaly.actual_value) == 12.50
    assert anomaly.details_json["consumption_kwh"] == 50.0
    assert anomaly.details_json["vnu_lines_count"] == 1


def test_detect_r19_skips_when_usage_expected(db_session):
    """R19 : VNU > seuil mais consumption > 100 kWh = pas d'anomaly (usage normal)."""
    from services.bill_intelligence import detect_r19_vnu_dormant

    _, site, _, _ = _seed_org_site_meter_contract(db_session)
    invoice = _seed_invoice(db_session, site, energy_kwh=5000)  # usage actif
    _add_line(db_session, invoice, "tax", "VNU", amount_eur=15.0)

    assert detect_r19_vnu_dormant(invoice, db_session) is None


def test_detect_r19_threshold_yaml_respected(db_session):
    """R19 : VNU < seuil YAML (0.01) = pas d'anomaly."""
    from services.bill_intelligence import detect_r19_vnu_dormant

    _, site, _, _ = _seed_org_site_meter_contract(db_session)
    invoice = _seed_invoice(db_session, site, energy_kwh=50)
    _add_line(db_session, invoice, "tax", "VNU", amount_eur=0.005)  # sous-seuil

    assert detect_r19_vnu_dormant(invoice, db_session) is None


def test_detect_r19_aggregates_multiple_vnu_lines(db_session):
    """R19 : Σ amount_eur sur plusieurs lignes VNU agrégé correctement."""
    from services.bill_intelligence import detect_r19_vnu_dormant

    _, site, _, _ = _seed_org_site_meter_contract(db_session)
    invoice = _seed_invoice(db_session, site, energy_kwh=50)
    _add_line(db_session, invoice, "tax", "VNU base", amount_eur=8.0)
    _add_line(db_session, invoice, "tax", "VERSEMENT NUCLEAIRE complément", amount_eur=4.0)

    anomaly = detect_r19_vnu_dormant(invoice, db_session)

    assert anomaly is not None
    assert float(anomaly.actual_value) == 12.0
    assert anomaly.details_json["vnu_lines_count"] == 2


def test_detect_r19_ignores_non_tax_lines(db_session):
    """R19 : ligne ENERGY label VNU = ignorée (ne scanne que TAX)."""
    from services.bill_intelligence import detect_r19_vnu_dormant

    _, site, _, _ = _seed_org_site_meter_contract(db_session)
    invoice = _seed_invoice(db_session, site, energy_kwh=50)
    _add_line(db_session, invoice, "energy", "VNU mention erronée", amount_eur=20.0)

    assert detect_r19_vnu_dormant(invoice, db_session) is None


# ─── R20 Capacité variance ──────────────────────────────────────────────────


def test_detect_r20_capacity_variance_8pct_flags_warning(db_session):
    """R20 : variance 8% (>5% et <10%) = warning."""
    from services.bill_intelligence import detect_r20_capacity_variance

    _, site, _, _ = _seed_org_site_meter_contract(db_session, ps_dict={"HPH": 36, "HCH": 36})
    invoice = _seed_invoice(db_session, site)
    # 39 kVA facturé vs 36 souscrit = variance 8.33%
    _add_line(db_session, invoice, "network", "Capacité HPH", qty=39, unit="kVA", period_code="HPH")

    anomalies = detect_r20_capacity_variance(invoice, db_session)

    assert len(anomalies) == 1
    assert anomalies[0].code == "R20"
    assert anomalies[0].severity == "warning"
    assert anomalies[0].details_json["period_code"] == "HPH"


def test_detect_r20_capacity_variance_15pct_flags_critical(db_session):
    """R20 : variance 25% (>10% = 2x seuil) = critical."""
    from services.bill_intelligence import detect_r20_capacity_variance

    _, site, _, _ = _seed_org_site_meter_contract(db_session, ps_dict={"HPH": 36})
    invoice = _seed_invoice(db_session, site)
    _add_line(db_session, invoice, "network", "Capacité HPH", qty=45, unit="kVA", period_code="HPH")

    anomalies = detect_r20_capacity_variance(invoice, db_session)

    assert len(anomalies) == 1
    assert anomalies[0].severity == "critical"


def test_detect_r20_within_threshold_returns_empty_list(db_session):
    """R20 : variance 2% (<5%) = pas d'anomaly."""
    from services.bill_intelligence import detect_r20_capacity_variance

    _, site, _, _ = _seed_org_site_meter_contract(db_session, ps_dict={"HPH": 36})
    invoice = _seed_invoice(db_session, site)
    _add_line(db_session, invoice, "network", "Capacité HPH", qty=36.5, unit="kVA", period_code="HPH")

    assert detect_r20_capacity_variance(invoice, db_session) == []


def test_detect_r20_no_contract_returns_empty_list(db_session):
    """R20 : pas de PowerContract = pas d'anomaly (skip silencieux)."""
    from datetime import date

    from models import (
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )
    from services.bill_intelligence import detect_r20_capacity_variance

    org = Organisation(nom="O", siren="200000001")
    db_session.add(org)
    db_session.flush()
    ej = EntiteJuridique(nom="EJ", siren="200000001", organisation_id=org.id)
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(nom="PF", entite_juridique_id=ej.id)
    db_session.add(pf)
    db_session.flush()
    site = Site(nom="S", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
    db_session.add(site)
    db_session.commit()
    invoice = _seed_invoice(db_session, site)
    _add_line(db_session, invoice, "network", "kVA", qty=50, unit="kVA", period_code="HPH")

    assert detect_r20_capacity_variance(invoice, db_session) == []


def test_detect_r20_multiple_postes_returns_multiple_anomalies(db_session):
    """R20 CARDINAL : 2 postes en variance = 2 anomalies (1 par poste)."""
    from services.bill_intelligence import detect_r20_capacity_variance

    _, site, _, _ = _seed_org_site_meter_contract(db_session, ps_dict={"HPH": 36, "HCH": 36})
    invoice = _seed_invoice(db_session, site)
    _add_line(db_session, invoice, "network", "HPH", qty=42, unit="kVA", period_code="HPH")  # +16.7%
    _add_line(db_session, invoice, "network", "HCH", qty=40, unit="kVA", period_code="HCH")  # +11.1%

    anomalies = detect_r20_capacity_variance(invoice, db_session)

    assert len(anomalies) == 2
    period_codes = sorted(a.details_json["period_code"] for a in anomalies)
    assert period_codes == ["HCH", "HPH"]


def test_detect_r20_period_code_unknown_skips_silently(db_session):
    """R20 : period_code inconnu (pas dans ps_par_poste_kva) = skip silencieux."""
    from services.bill_intelligence import detect_r20_capacity_variance

    _, site, _, _ = _seed_org_site_meter_contract(db_session, ps_dict={"HPH": 36})
    invoice = _seed_invoice(db_session, site)
    _add_line(db_session, invoice, "network", "POINTE", qty=50, unit="kVA", period_code="POINTE")

    # POINTE absent du contract → skip
    assert detect_r20_capacity_variance(invoice, db_session) == []


def test_detect_r20_period_code_matching_HPH(db_session):
    """R20 CARDINAL Phase 5.1.0 : matching HPH cardinal entre line et ps_dict."""
    from services.bill_intelligence import detect_r20_capacity_variance

    _, site, _, _ = _seed_org_site_meter_contract(db_session, ps_dict={"HPH": 36, "HCH": 24})
    invoice = _seed_invoice(db_session, site)
    # HPH facturé 50 → variance vs 36 = +38.9% critical
    _add_line(db_session, invoice, "network", "HPH", qty=50, unit="kVA", period_code="HPH")

    anomalies = detect_r20_capacity_variance(invoice, db_session)

    assert len(anomalies) == 1
    assert anomalies[0].details_json["period_code"] == "HPH"
    assert anomalies[0].details_json["capacite_souscrite_kva"] == 36


# ─── Helper _resolve_period_code ────────────────────────────────────────────


def test_resolve_period_code_from_direct_field_priority_1(db_session):
    """Priority 1 : champ direct line.period_code prime."""
    from services.bill_intelligence.anomaly_detector import _resolve_period_code

    _, site, _, _ = _seed_org_site_meter_contract(db_session)
    invoice = _seed_invoice(db_session, site)
    line = _add_line(db_session, invoice, "network", "Whatever HCH label", qty=36, unit="kVA", period_code="HPH")

    # Le champ direct HPH doit prévaloir sur le label HCH
    assert _resolve_period_code(line) == "HPH"


def test_resolve_period_code_from_label_fallback(db_session):
    """Priority 3 : extraction depuis label si pas de champ direct."""
    from services.bill_intelligence.anomaly_detector import _resolve_period_code

    _, site, _, _ = _seed_org_site_meter_contract(db_session)
    invoice = _seed_invoice(db_session, site)
    line = _add_line(db_session, invoice, "network", "Capacité tarifaire HCH 36 kVA", qty=36, unit="kVA")

    assert _resolve_period_code(line) == "HCH"


def test_resolve_period_code_returns_none_when_nothing_matches(db_session):
    """Cas dégradé : aucune source résolution = None (skip downstream)."""
    from services.bill_intelligence.anomaly_detector import _resolve_period_code

    _, site, _, _ = _seed_org_site_meter_contract(db_session)
    invoice = _seed_invoice(db_session, site)
    line = _add_line(db_session, invoice, "network", "Capacité abonnement annuel", qty=36, unit="kVA")

    assert _resolve_period_code(line) is None


# ─── Pipeline detect_anomalies_for_invoice ──────────────────────────────────


def test_pipeline_detect_anomalies_for_invoice_aggregates_R19_and_R20(db_session):
    """Pipeline : R19 + R20 simultanés sur même invoice = 2+ anomalies persistées."""
    from models import BillAnomaly
    from services.bill_intelligence import detect_anomalies_for_invoice

    _, site, _, _ = _seed_org_site_meter_contract(db_session, ps_dict={"HPH": 36})
    invoice = _seed_invoice(db_session, site, energy_kwh=50)  # bas usage → R19 attendu
    _add_line(db_session, invoice, "tax", "VNU", amount_eur=10.0)
    _add_line(db_session, invoice, "network", "HPH", qty=42, unit="kVA", period_code="HPH")

    results = detect_anomalies_for_invoice(invoice, db_session)

    assert len(results) == 2
    codes = sorted(a.code for a in results)
    assert codes == ["R19", "R20"]

    # Vérifier persistence
    persisted = db_session.query(BillAnomaly).filter(BillAnomaly.invoice_id == invoice.id).all()
    assert len(persisted) == 2


def test_pipeline_resilience_one_detector_fails_others_continue(db_session, monkeypatch):
    """Pipeline résilience : si R19 lève exception, R20 continue."""
    from services.bill_intelligence import anomaly_detector, detect_anomalies_for_invoice

    _, site, _, _ = _seed_org_site_meter_contract(db_session, ps_dict={"HPH": 36})
    invoice = _seed_invoice(db_session, site, energy_kwh=50)
    _add_line(db_session, invoice, "tax", "VNU", amount_eur=10.0)
    _add_line(db_session, invoice, "network", "HPH", qty=42, unit="kVA", period_code="HPH")

    def _broken_r19(*args, **kwargs):
        raise RuntimeError("R19 simulated failure")

    monkeypatch.setattr(anomaly_detector, "detect_r19_vnu_dormant", _broken_r19)

    results = detect_anomalies_for_invoice(invoice, db_session)

    # R19 a planté mais R20 doit avoir détecté
    assert len(results) == 1
    assert results[0].code == "R20"


# ─── YAML SoT cohérence ─────────────────────────────────────────────────────


def test_yaml_seuils_match_expected_runtime_constants():
    """SG cohérence YAML ↔ runtime : seuils chargés correspondent aux defaults documentés."""
    from config.regulatory_sources_loader import get_term_value, reload_regulatory_sources

    reload_regulatory_sources()

    vnu_threshold = get_term_value("BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR")
    capacity_threshold = get_term_value("BILL_ANOMALY_CAPACITY_VARIANCE_THRESHOLD_PCT")

    assert vnu_threshold == 0.01, f"VNU threshold YAML = {vnu_threshold} (attendu 0.01 EUR)"
    assert capacity_threshold == 5.0, f"Capacity threshold YAML = {capacity_threshold} (attendu 5.0 %)"


def test_yaml_terms_present_in_bill_intelligence_domain():
    """SG : les 2 termes BILL_ANOMALY_* sont dans le domain `bill_intelligence`."""
    from config.regulatory_sources_loader import get_term, reload_regulatory_sources

    reload_regulatory_sources()

    vnu_term = get_term("BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR")
    capacity_term = get_term("BILL_ANOMALY_CAPACITY_VARIANCE_THRESHOLD_PCT")

    assert vnu_term["domain"] == "bill_intelligence"
    assert capacity_term["domain"] == "bill_intelligence"
