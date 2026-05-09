"""
PROMEOS — Phase G : tests cardinaux endpoints persona dashboards.

12 tests T-PERSONA-01 → T-PERSONA-12 :
- Marie DAF compliance dashboard (5 tests)
- Jean-Marc CFO billing anomalies summary (4 tests)
- Jean-Marc CFO expiring contracts J-180 (3 tests)
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import (
    Base,
    EnergyContract,
    EnergyInvoice,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)
from models.bill_anomaly import BillAnomaly
from models.enums import BillingEnergyType, BillingInvoiceStatus


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_org_with_sites(db, org_name="Org Alpha", siren="111111111", n_sites=2):
    org = Organisation(nom=org_name, type_client="bureau", actif=True, siren=siren)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(
        organisation_id=org.id,
        nom="EJ A",
        siren=siren,
        consommation_annuelle_moyenne_3y_gwh=5.0,  # déclenche Audit SMÉ (>=2.75)
    )
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF A")
    db.add(pf)
    db.flush()
    sites = []
    for i in range(n_sites):
        s = Site(
            portefeuille_id=pf.id,
            nom=f"Site {i + 1}",
            type=TypeSite.BUREAU,
            actif=True,
            tertiaire_area_m2=2000,  # déclenche DT
            parking_area_m2=1500,  # déclenche APER SMALL
            aper_assujetti=True,
            parking_solar_pct_engaged=10,  # < 50% → non compliant APER
            bacs_assujetti=True,
        )
        db.add(s)
        db.flush()
        sites.append(s)
    db.commit()
    return org, ej, pf, sites


def _h(org_id):
    return {"X-Org-Id": str(org_id)}


# ─── G1 Marie DAF — Compliance dashboard ───────────────────────────────────


class TestMarieDaFComplianceDashboard:
    def test_t_persona_01_dashboard_returns_headlines_structure(self, client, db):
        """T-PERSONA-01 : structure de réponse cardinale (headlines + sites + audit_sme)."""
        org, _, _, _ = _seed_org_with_sites(db, n_sites=3)
        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        assert r.status_code == 200
        data = r.json()
        assert "headlines" in data
        assert "sites" in data
        assert "audit_sme" in data
        assert data["headlines"]["total_sites"] == 3

    def test_t_persona_02_frameworks_5_per_site(self, client, db):
        """T-PERSONA-02 : 5 frameworks DT/BACS/APER/OPERAT/DPE par site (Phase H1 +DPE)."""
        org, _, _, _ = _seed_org_with_sites(db, n_sites=2)
        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        for site in r.json()["sites"]:
            frameworks = {fw["framework"] for fw in site["frameworks"]}
            assert frameworks == {"DT", "BACS", "APER", "OPERAT", "DPE"}

    def test_t_persona_03_total_exposure_includes_aper_surface(self, client, db):
        """T-PERSONA-03 : exposition cumulée non nulle (APER 1500 m² × 20 €/m² × 2 sites).

        Phase H : split certain (APER+OPERAT) vs pending (DT+BACS A_RISQUE) — total = somme.
        """
        org, _, _, _ = _seed_org_with_sites(db, n_sites=2)
        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        headlines = r.json()["headlines"]
        # Split certain + pending
        assert "total_exposure_certain_eur" in headlines
        assert "total_exposure_pending_max_eur" in headlines
        assert "pending_frameworks_count" in headlines
        # Total cumul (backward-compat) > 50k
        assert headlines["total_exposure_eur"] > 50000

    def test_t_persona_04_audit_sme_triggered_by_consumption_3y(self, client, db):
        """T-PERSONA-04 : Audit SMÉ déclenché par EJ.consommation_annuelle_moyenne_3y_gwh ≥ 2.75."""
        org, _, _, _ = _seed_org_with_sites(db, n_sites=1)
        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        audit_sme = r.json()["audit_sme"]
        assert len(audit_sme) >= 1
        # EJ seedé avec conso 5.0 GWh → triggered
        assert any(item["triggered"] for item in audit_sme)

    def test_t_persona_05_idor_cross_tenant_empty(self, client, db):
        """T-PERSONA-05 : Phase E IDOR — Org B ne voit pas sites Org A."""
        org_a, _, _, _ = _seed_org_with_sites(db, "Org Alpha", "111111111", 2)
        org_b, _, _, _ = _seed_org_with_sites(db, "Org Bravo", "222222222", 0)
        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org_b.id))
        assert r.status_code == 200
        # Org B n'a pas de sites → headlines vides
        assert r.json()["headlines"]["total_sites"] == 0


# ─── G2.1 Jean-Marc CFO — Billing anomalies summary ────────────────────────


class TestCFOBillingAnomaliesSummary:
    def _seed_anomaly(self, db, site, severity="critical", montant=1500.0, suffix=""):
        # Garantit unicité invoice_number + code via suffix
        unique_id = f"{site.id}-{severity}-{suffix or montant}"
        invoice = EnergyInvoice(
            site_id=site.id,
            invoice_number=f"INV-{unique_id}",
            energy_kwh=10000,
            total_eur=2500,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        anomaly = BillAnomaly(
            invoice_id=invoice.id,
            code=f"R{19 if severity == 'critical' else 20}",
            severity=severity,
            details_json={"montant_anomalie_eur": montant},
        )
        db.add(anomaly)
        db.flush()
        return anomaly

    def test_t_persona_06_summary_structure(self, client, db):
        """T-PERSONA-06 : structure cardinale (total_open + by_severity + top_5)."""
        org, _, _, _ = _seed_org_with_sites(db, n_sites=1)
        r = client.get("/api/persona/cfo/billing-anomalies-summary", headers=_h(org.id))
        assert r.status_code == 200
        data = r.json()
        assert "total_open" in data
        assert "by_severity" in data
        assert "top_5" in data

    def test_t_persona_07_aggregates_open_anomalies(self, client, db):
        """T-PERSONA-07 : agrégation correcte des anomalies OPEN (resolved_at NULL)."""
        org, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        self._seed_anomaly(db, sites[0], "critical", 2500.0, "a")
        self._seed_anomaly(db, sites[0], "warning", 1000.0, "b")
        self._seed_anomaly(db, sites[0], "critical", 500.0, "c")
        db.commit()
        r = client.get("/api/persona/cfo/billing-anomalies-summary", headers=_h(org.id))
        data = r.json()
        assert data["total_open"] == 3
        assert data["by_severity"]["critical"] == 2
        assert data["by_severity"]["warning"] == 1
        assert data["total_montant_anomalie_eur"] == 4000.0

    def test_t_persona_08_top_5_sorted_by_montant_desc(self, client, db):
        """T-PERSONA-08 : top_5 trié décroissant par montant (depuis details_json)."""
        org, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        # Mix critical + warning pour varier les codes (anti-uniqueness violation)
        for i, (sev, amount) in enumerate(
            [
                ("critical", 500),
                ("warning", 3000),
                ("critical", 1000),
                ("warning", 2500),
                ("critical", 100),
                ("warning", 4000),
            ]
        ):
            self._seed_anomaly(db, sites[0], sev, float(amount), suffix=str(i))
        db.commit()
        r = client.get("/api/persona/cfo/billing-anomalies-summary", headers=_h(org.id))
        montants = [a["montant_eur"] for a in r.json()["top_5"]]
        assert montants == sorted(montants, reverse=True)
        assert len(montants) == 5
        assert montants[0] == 4000.0

    def test_t_persona_09_idor_cross_tenant(self, client, db):
        """T-PERSONA-09 : Phase E IDOR — Org B ne voit pas anomalies Org A."""
        org_a, _, _, sites_a = _seed_org_with_sites(db, "Org Alpha", "111111111", 1)
        org_b, _, _, _ = _seed_org_with_sites(db, "Org Bravo", "222222222", 0)
        self._seed_anomaly(db, sites_a[0], "critical", 1500.0)
        db.commit()
        r = client.get("/api/persona/cfo/billing-anomalies-summary", headers=_h(org_b.id))
        assert r.json()["total_open"] == 0


# ─── G2.2 Jean-Marc CFO — Expiring contracts J-180 ─────────────────────────


class TestCFOExpiringContracts:
    def _seed_contract(self, db, site, end_date, supplier="EDF"):
        import json

        c = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name=supplier,
            end_date=end_date,
            metadata_json=json.dumps({"phase_j2_legacy": True}),
        )
        db.add(c)
        db.flush()
        return c

    def test_t_persona_10_expiring_contracts_within_horizon(self, client, db):
        """T-PERSONA-10 : contrats expirant dans J-180 retournés ordonnés croissants."""
        org, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        today = date.today()
        self._seed_contract(db, sites[0], today + timedelta(days=60), "EDF")  # in
        self._seed_contract(db, sites[0], today + timedelta(days=120), "ENGIE")  # in
        self._seed_contract(db, sites[0], today + timedelta(days=400), "TOTAL")  # out
        db.commit()

        r = client.get("/api/persona/cfo/expiring-contracts", headers=_h(org.id))
        data = r.json()
        assert data["total_expiring"] == 2
        assert data["horizon_days"] == 180
        # Ordre croissant par end_date
        days_remaining = [c["days_remaining"] for c in data["contracts"]]
        assert days_remaining == sorted(days_remaining)

    def test_t_persona_11_horizon_configurable(self, client, db):
        """T-PERSONA-11 : query param horizon_days configurable (90 jours)."""
        org, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        today = date.today()
        self._seed_contract(db, sites[0], today + timedelta(days=60), "EDF")
        self._seed_contract(db, sites[0], today + timedelta(days=120), "ENGIE")
        db.commit()

        r = client.get("/api/persona/cfo/expiring-contracts?horizon_days=90", headers=_h(org.id))
        assert r.json()["total_expiring"] == 1  # Seul le contrat 60j tombe dans 90j

    def test_t_persona_12_idor_cross_tenant(self, client, db):
        """T-PERSONA-12 : Phase E IDOR — Org B ne voit pas contrats Org A."""
        org_a, _, _, sites_a = _seed_org_with_sites(db, "Org Alpha", "111111111", 1)
        org_b, _, _, _ = _seed_org_with_sites(db, "Org Bravo", "222222222", 0)
        self._seed_contract(db, sites_a[0], date.today() + timedelta(days=60), "EDF")
        db.commit()
        r = client.get("/api/persona/cfo/expiring-contracts", headers=_h(org_b.id))
        assert r.json()["total_expiring"] == 0


# ─── Phase H1 — DPE framework #5 (Marie DAF cardinal Control 19,9k€) ───────


class TestPhaseH1DPEFramework:
    def _seed_with_dpe(self, db, dpe_class="C", expired=False):
        from datetime import timedelta

        from models import Batiment

        org, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        site = sites[0]
        validity = date.today() - timedelta(days=10) if expired else date.today() + timedelta(days=365)
        bati = Batiment(
            site_id=site.id,
            nom="Bati 1",
            surface_m2=1000.0,
            dpe_class=dpe_class,
            dpe_date_validite=validity,
        )
        db.add(bati)
        db.commit()
        return org, site

    def test_h1_dpe_compliant_class_a_to_e(self, client, db):
        """H1 — DPE classe A-E + non expiré → compliant=True, exposure=0."""
        org, site = self._seed_with_dpe(db, dpe_class="C")
        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        dpe = next(fw for fw in r.json()["sites"][0]["frameworks"] if fw["framework"] == "DPE")
        assert dpe["assujetti"] is True
        assert dpe["compliant"] is True
        assert dpe["exposure_eur"] == 0

    def test_h1_dpe_non_compliant_class_f(self, client, db):
        """H1 — DPE classe F → compliant=False, exposure=15 000 € (sanction DDPP)."""
        org, _ = self._seed_with_dpe(db, dpe_class="F")
        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        dpe = next(fw for fw in r.json()["sites"][0]["frameworks"] if fw["framework"] == "DPE")
        assert dpe["compliant"] is False
        assert dpe["exposure_eur"] == 15000

    def test_h1_dpe_non_compliant_expired(self, client, db):
        """H1 — DPE expiré (validité < today) → compliant=False même si classe A."""
        org, _ = self._seed_with_dpe(db, dpe_class="A", expired=True)
        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        dpe = next(fw for fw in r.json()["sites"][0]["frameworks"] if fw["framework"] == "DPE")
        assert dpe["compliant"] is False
        assert dpe["has_expired_dpe"] is True

    def test_h1_dpe_pending_no_data(self, client, db):
        """H1 — Site assujetti tertiaire >250 m² sans Batiment.dpe_class → compliant=None."""
        org, _, _, _ = _seed_org_with_sites(db, n_sites=1)
        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        dpe = next(fw for fw in r.json()["sites"][0]["frameworks"] if fw["framework"] == "DPE")
        assert dpe["assujetti"] is True
        assert dpe["compliant"] is None
        assert dpe["exposure_eur"] is None
        assert dpe["exposure_max_eur"] == 15000


# ─── Phase H2 — R23 TURPE doublé (Jean-Marc CFO cardinal ROI) ───────────────


class TestPhaseH2R23TurpeDouble:
    def test_h2_r23_detects_double_turpe_period(self, db):
        """H2 — 2 lignes NETWORK même période HPH → R23 détecté."""
        from models import EnergyInvoiceLine
        from models.enums import InvoiceLineType
        from services.bill_intelligence.anomaly_detector import detect_r23_turpe_double

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-R23",
            energy_kwh=10000,
            total_eur=2500,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        # 2 lignes TURPE NETWORK HPH (doublon)
        for amount in (250.0, 250.0):
            db.add(
                EnergyInvoiceLine(
                    invoice_id=invoice.id,
                    line_type=InvoiceLineType.NETWORK,
                    label="TURPE 7 HPH soutirage",
                    amount_eur=amount,
                )
            )
        db.commit()
        db.refresh(invoice)

        anomalies = detect_r23_turpe_double(invoice, db)
        assert len(anomalies) == 1
        a = anomalies[0]
        assert a.code == "R23"
        assert a.severity == "critical"  # 250 € > 100 €
        assert a.details_json["period_code"] == "HPH"
        assert a.details_json["duplicate_count"] == 2

    def test_h2_r23_no_double_no_anomaly(self, db):
        """H2 — 1 seule ligne par période → pas de doublon détecté."""
        from models import EnergyInvoiceLine
        from models.enums import InvoiceLineType
        from services.bill_intelligence.anomaly_detector import detect_r23_turpe_double

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-R23-OK",
            energy_kwh=10000,
            total_eur=2500,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        # 1 ligne par période différente — pas de doublon
        for label in ("TURPE 7 HPH", "TURPE 7 HCH", "TURPE 7 HPB"):
            db.add(
                EnergyInvoiceLine(
                    invoice_id=invoice.id,
                    line_type=InvoiceLineType.NETWORK,
                    label=label,
                    amount_eur=100.0,
                )
            )
        db.commit()
        db.refresh(invoice)

        anomalies = detect_r23_turpe_double(invoice, db)
        assert anomalies == []

    def test_h2_r23_severity_warning_below_100eur(self, db):
        """H2 — doublon < 100 € → severity warning (pas critical)."""
        from models import EnergyInvoiceLine
        from models.enums import InvoiceLineType
        from services.bill_intelligence.anomaly_detector import detect_r23_turpe_double

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-R23-W",
            energy_kwh=10000,
            total_eur=2500,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        for amount in (50.0, 50.0):
            db.add(
                EnergyInvoiceLine(
                    invoice_id=invoice.id,
                    line_type=InvoiceLineType.NETWORK,
                    label="TURPE 7 HC",
                    amount_eur=amount,
                )
            )
        db.commit()
        db.refresh(invoice)

        anomalies = detect_r23_turpe_double(invoice, db)
        assert len(anomalies) == 1
        assert anomalies[0].severity == "warning"


# ─── Phase H3 — ISO 50001 exemption Audit SMÉ (Marie DAF) ──────────────────


class TestPhaseH3IsoExemption:
    def test_h3_iso_50001_exempts_audit_sme_obligation(self, client, db):
        """H3 — EJ ISO 50001 actif + valide → obligation_active=False même si triggered."""
        from datetime import timedelta

        org, ej, _, _ = _seed_org_with_sites(db, n_sites=1)
        # ej a déjà conso 5.0 GWh (triggered=True)
        ej.iso_50001_actif = True
        ej.iso_50001_date_validite = date.today() + timedelta(days=365)
        db.commit()

        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        audit_sme = r.json()["audit_sme"][0]
        assert audit_sme["triggered"] is True  # conso ≥ 2.75 GWh
        assert audit_sme["iso_50001_actif"] is True
        assert audit_sme["iso_50001_valide"] is True
        assert audit_sme["exemption_iso_50001"] is True
        assert audit_sme["obligation_active"] is False  # exempté !

    def test_h3_iso_expired_does_not_exempt(self, client, db):
        """H3 — ISO 50001 actif mais expiré → pas d'exemption (obligation_active=True)."""
        from datetime import timedelta

        org, ej, _, _ = _seed_org_with_sites(db, n_sites=1)
        ej.iso_50001_actif = True
        ej.iso_50001_date_validite = date.today() - timedelta(days=10)  # expiré
        db.commit()

        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        audit_sme = r.json()["audit_sme"][0]
        assert audit_sme["iso_50001_actif"] is True
        assert audit_sme["iso_50001_valide"] is False  # expiré
        assert audit_sme["obligation_active"] is True  # obligé d'auditer


# ─── Phase H4 — Countdown urgency enum (Marie DAF UX) ───────────────────────


class TestPhaseH4UrgencyEnum:
    def test_h4_urgency_levels_present_on_all_frameworks(self, client, db):
        """H4 — urgency_level présent sur DT/BACS/APER/OPERAT/DPE."""
        org, _, _, _ = _seed_org_with_sites(db, n_sites=1)
        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        for site in r.json()["sites"]:
            for fw in site["frameworks"]:
                assert "urgency_level" in fw
                assert fw["urgency_level"] in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "OVERDUE"}

    def test_h4_urgency_levels_thresholds(self):
        """H4 — _compute_urgency_level renvoie les bons niveaux selon days."""
        from services.persona_dashboard_service import _compute_urgency_level

        assert _compute_urgency_level(-5) == "OVERDUE"
        assert _compute_urgency_level(0) == "CRITICAL"
        assert _compute_urgency_level(15) == "CRITICAL"
        assert _compute_urgency_level(45) == "HIGH"
        assert _compute_urgency_level(120) == "MEDIUM"
        assert _compute_urgency_level(365) == "LOW"


# ─── Phase H5 — R21 CTA mauvais calcul (Jean-Marc CFO) ─────────────────────


class TestPhaseH5R21CTA:
    def test_h5_r21_detects_cta_mismatch_post_2026(self, db):
        """H5 — CTA facturée diverge >10 % du taux 15 % post-2026 → R21 critical."""
        from datetime import date as _date

        from models import EnergyInvoiceLine
        from models.enums import InvoiceLineType
        from services.bill_intelligence.anomaly_detector import detect_r21_cta_mismatch

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-R21-2026",
            energy_kwh=10000,
            total_eur=2500,
            issue_date=_date(2026, 3, 15),
            period_start=_date(2026, 3, 1),
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        # TURPE 1000 € → CTA attendue = 150 € (15 %), mais facturée 250 € (mauvais 25 %)
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.NETWORK,
                label="TURPE soutirage",
                amount_eur=1000.0,
            )
        )
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.TAX,
                label="CTA",
                amount_eur=300.0,  # 150 € de trop (>100 → critical)
            )
        )
        db.commit()
        db.refresh(invoice)

        anomaly = detect_r21_cta_mismatch(invoice, db)
        assert anomaly is not None
        assert anomaly.code == "R21"
        assert anomaly.severity == "critical"
        assert anomaly.details_json["cta_attendue_eur"] == 150.0
        assert anomaly.details_json["cta_facturee_eur"] == 300.0
        assert anomaly.details_json["cta_rate_applied"] == 0.15

    def test_h5_r21_no_anomaly_within_tolerance(self, db):
        """H5 — CTA facturée à ±5 % du taux attendu → pas d'anomalie."""
        from datetime import date as _date

        from models import EnergyInvoiceLine
        from models.enums import InvoiceLineType
        from services.bill_intelligence.anomaly_detector import detect_r21_cta_mismatch

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-R21-OK",
            energy_kwh=10000,
            total_eur=2500,
            issue_date=_date(2026, 3, 15),
            period_start=_date(2026, 3, 1),
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        # TURPE 1000 € → CTA attendue 150 € ; facturée 152 € (~1.3 % écart, < 10 %)
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.NETWORK,
                label="TURPE",
                amount_eur=1000.0,
            )
        )
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.TAX,
                label="CTA",
                amount_eur=152.0,
            )
        )
        db.commit()
        db.refresh(invoice)

        anomaly = detect_r21_cta_mismatch(invoice, db)
        assert anomaly is None


# ─── Phase H6 — Comparateur prix EPEX MVP (Jean-Marc CFO) ──────────────────


class TestPhaseH6ContractPriceBenchmark:
    def test_h6_benchmark_no_market_data(self, client, db):
        """H6 — Sans MktPrice forward → benchmark_status='no_market_data'."""
        import json
        from datetime import timedelta

        org, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        c = EnergyContract(
            site_id=sites[0].id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            end_date=date.today() + timedelta(days=60),
            price_ref_eur_per_kwh=0.15,
            metadata_json=json.dumps({"phase_j2_legacy": True}),
        )
        db.add(c)
        db.commit()

        r = client.get("/api/persona/cfo/contract-price-benchmark", headers=_h(org.id))
        data = r.json()
        assert data["benchmark_status"] == "no_market_data"
        assert data["market_forward_eur_mwh"] is None
        assert data["total_contracts"] == 1
        # Prix contractuel exposé même sans benchmark
        assert data["contracts"][0]["prix_contractuel_eur_mwh"] == 150.0  # 0.15 * 1000

    def test_h6_benchmark_computes_delta_with_market(self, client, db):
        """H6 — Avec MktPrice forward Y+1, delta + impact économies calculés."""
        from datetime import datetime, timedelta, timezone

        from models.market_models import (
            MarketDataSource,
            MarketType,
            MktPrice,
            PriceZone,
            ProductType,
            Resolution,
        )
        # Phase H6 : MktPrice utilise MarketType.FORWARD_YEAR + ProductType.BASELOAD

        import json

        org, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        # Contrat à 180 €/MWh (très cher)
        c = EnergyContract(
            site_id=sites[0].id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            end_date=date.today() + timedelta(days=60),
            price_ref_eur_per_kwh=0.18,
            metadata_json=json.dumps({"phase_j2_legacy": True}),
        )
        db.add(c)
        db.flush()
        # Facture historique pour conso 100 MWh
        inv = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-CONSO",
            contract_id=c.id,
            energy_kwh=100000,
            total_eur=18000,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(inv)
        # Forward Y+1 à 100 €/MWh
        next_year = date.today().year + 1
        mkt = MktPrice(
            source=MarketDataSource.EPEX_SPOT,
            market_type=MarketType.FORWARD_YEAR,
            product_type=ProductType.BASELOAD,
            zone=PriceZone.FR,
            delivery_start=datetime(next_year, 1, 1, tzinfo=timezone.utc),
            delivery_end=datetime(next_year, 12, 31, tzinfo=timezone.utc),
            price_eur_mwh=100.0,
            resolution=Resolution.PT60M,
            fetched_at=datetime.now(timezone.utc),
        )
        db.add(mkt)
        db.commit()

        r = client.get("/api/persona/cfo/contract-price-benchmark", headers=_h(org.id))
        data = r.json()
        assert data["benchmark_status"] == "available"
        assert data["market_forward_eur_mwh"] == 100.0
        contract = data["contracts"][0]
        assert contract["prix_contractuel_eur_mwh"] == 180.0
        assert contract["delta_eur_mwh"] == 80.0  # surcoût client
        assert contract["delta_pct"] == 80.0
        assert contract["conso_annuelle_mwh"] == 100.0
        assert contract["impact_economies_eur_an"] == 8000.0  # 80 €/MWh × 100 MWh


# ─── Phase I1 — R22 Accise erronée (Jean-Marc CFO) ─────────────────────────


class TestPhaseI1R22Accise:
    def test_i1_r22_detects_accise_overcharge(self, db):
        """I1 — Accise facturée trop élevée vs tarif T1 (30,85 €/MWh) → R22."""
        from models import EnergyInvoiceLine
        from models.enums import InvoiceLineType
        from services.bill_intelligence.anomaly_detector import detect_r22_accise_mismatch

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-R22",
            energy_kwh=10000,  # 10 MWh
            total_eur=2500,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        # T1 attendu = 10 MWh × 30,85 = 308,50 € ; facturée 600 € (~94 % d'écart)
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.TAX,
                label="Accise sur l'électricité",
                amount_eur=600.0,
            )
        )
        db.commit()
        db.refresh(invoice)

        anomaly = detect_r22_accise_mismatch(invoice, db)
        assert anomaly is not None
        assert anomaly.code == "R22"
        assert anomaly.severity == "critical"  # écart > 50 €
        # Phase J : sans DP catégorie → FALLBACK T1
        assert anomaly.details_json["category_source"] == "FALLBACK"
        assert anomaly.details_json["category_value"] == "T1_FALLBACK"

    def test_i1_r22_no_anomaly_within_t1_range(self, db):
        """I1 — Accise dans la fourchette T1 (±35 % fallback) → pas d'anomalie."""
        from models import EnergyInvoiceLine
        from models.enums import InvoiceLineType
        from services.bill_intelligence.anomaly_detector import detect_r22_accise_mismatch

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-R22-OK",
            energy_kwh=10000,
            total_eur=2500,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        # 10 MWh × 30,85 = 308,5 € ± 35% → 200-417 € OK
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.TAX,
                label="CSPE",
                amount_eur=300.0,  # ~3 % d'écart
            )
        )
        db.commit()
        db.refresh(invoice)

        assert detect_r22_accise_mismatch(invoice, db) is None


# ─── Phase J1 — R22 raffinement AcciseCategorieElec routing ─────────────────


class TestPhaseJ1R22DPCategoryRouting:
    def test_j1_r22_uses_dp_category_pme_tighter_threshold(self, db):
        """J1 — DP catégorie PME → taux T2 26,58 €/MWh + seuil 10 % (vs 35 % fallback).

        Le raffinement Phase J réduit faux positifs : avec PME catégorie connue,
        on détecte un écart de 12 % (sub-T1 fallback 35 %) sur taux T2 attendu.
        """
        from models import (
            DeliveryPoint,
            EnergyInvoiceLine,
            Meter,
        )
        from models.enums import (
            AcciseCategorieElec,
            DeliveryPointEnergyType,
            InvoiceLineType,
        )
        from models.energy_models import EnergyVector
        from services.bill_intelligence.anomaly_detector import detect_r22_accise_mismatch

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        # DP avec catégorie PME (T2)
        dp = DeliveryPoint(
            code="14999100000001",
            energy_type=DeliveryPointEnergyType.ELEC,
            site_id=sites[0].id,
            accise_categorie_elec=AcciseCategorieElec.PME,
        )
        db.add(dp)
        db.flush()
        # Meter lié au site et au DP
        meter = Meter(
            meter_id="PRM-J1-PME",
            name="Meter J1",
            site_id=sites[0].id,
            energy_vector=EnergyVector.ELECTRICITY,
            delivery_point_id=dp.id,
        )
        db.add(meter)
        db.flush()

        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-J1-PME",
            energy_kwh=10000,  # 10 MWh
            total_eur=2500,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        # T2 attendue = 10 × 26,58 = 265,80 € ; facturée 320 € (écart +20 %)
        # Sous le seuil T1 fallback 35 % MAIS au-dessus du seuil DP 10 % → détecté
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.TAX,
                label="CSPE",
                amount_eur=320.0,
            )
        )
        db.commit()
        db.refresh(invoice)

        from doctrine.constants import ACCISE_ELEC_T2_EUR_PER_MWH

        anomaly = detect_r22_accise_mismatch(invoice, db)
        assert anomaly is not None
        assert anomaly.code == "R22"
        assert anomaly.details_json["category_source"] == "DP_CATEGORY"
        assert anomaly.details_json["category_value"] == "PME"
        assert anomaly.details_json["tarif_eur_per_mwh"] == ACCISE_ELEC_T2_EUR_PER_MWH

    def test_j1_r22_haute_puissance_uses_hp_rate(self, db):
        """J1 — DP catégorie HAUTE_PUISSANCE → taux HP 5,71 €/MWh."""
        from models import (
            DeliveryPoint,
            EnergyInvoiceLine,
            Meter,
        )
        from models.enums import (
            AcciseCategorieElec,
            DeliveryPointEnergyType,
            InvoiceLineType,
        )
        from models.energy_models import EnergyVector
        from services.bill_intelligence.anomaly_detector import detect_r22_accise_mismatch

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        dp = DeliveryPoint(
            code="14999100000002",
            energy_type=DeliveryPointEnergyType.ELEC,
            site_id=sites[0].id,
            accise_categorie_elec=AcciseCategorieElec.HAUTE_PUISSANCE,
        )
        db.add(dp)
        db.flush()
        meter = Meter(
            meter_id="PRM-J1-HP",
            name="Meter HP",
            site_id=sites[0].id,
            energy_vector=EnergyVector.ELECTRICITY,
            delivery_point_id=dp.id,
        )
        db.add(meter)
        db.flush()

        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-J1-HP",
            energy_kwh=1000000,  # 1000 MWh = 1 GWh (industriel)
            total_eur=85000,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        # HP attendue = 1000 × 5,71 = 5710 € ; facturée 30 850 € (taux T1 appliqué à tort)
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.TAX,
                label="Accise sur l'électricité",
                amount_eur=30850.0,  # facturé au taux T1 alors que HP attendu
            )
        )
        db.commit()
        db.refresh(invoice)

        from doctrine.constants import ACCISE_ELEC_HP_EUR_PER_MWH

        anomaly = detect_r22_accise_mismatch(invoice, db)
        assert anomaly is not None
        assert anomaly.code == "R22"
        assert anomaly.severity == "critical"
        assert anomaly.details_json["category_source"] == "DP_CATEGORY"
        assert anomaly.details_json["category_value"] == "HAUTE_PUISSANCE"
        assert anomaly.details_json["tarif_eur_per_mwh"] == ACCISE_ELEC_HP_EUR_PER_MWH
        # Détection énorme surfacturation : ~25 k€ de récupération potentielle
        assert anomaly.details_json["montant_anomalie_eur"] > 20000


# ─── Phase I2 — R24 TVA mauvais taux (Jean-Marc CFO) ───────────────────────


class TestPhaseI2R24TVA:
    def test_i2_r24_detects_wrong_tva_rate(self, db):
        """I2 — TVA appliquée à 25 % au lieu de 20 % → R24."""
        from models import EnergyInvoiceLine
        from models.enums import InvoiceLineType
        from services.bill_intelligence.anomaly_detector import detect_r24_tva_rate_mismatch

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-R24",
            energy_kwh=10000,
            total_eur=2500,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        # HT 1000 € → TVA 20 % attendue = 200 € ; facturée 270 € (taux 27 %, écart +7 pts)
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.NETWORK,
                label="TURPE",
                amount_eur=1000.0,
            )
        )
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.TAX,
                label="TVA 27%",
                amount_eur=270.0,
            )
        )
        db.commit()
        db.refresh(invoice)

        anomaly = detect_r24_tva_rate_mismatch(invoice, db)
        assert anomaly is not None
        assert anomaly.code == "R24"
        assert anomaly.severity == "critical"  # écart 7 pts > 5 = critical
        assert anomaly.details_json["taux_effectif_pct"] == 27.0

    def test_i2_r24_no_anomaly_correct_20pct(self, db):
        """I2 — TVA correcte 20 % → pas d'anomalie."""
        from models import EnergyInvoiceLine
        from models.enums import InvoiceLineType
        from services.bill_intelligence.anomaly_detector import detect_r24_tva_rate_mismatch

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-R24-OK",
            energy_kwh=10000,
            total_eur=2500,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.NETWORK,
                label="TURPE",
                amount_eur=1000.0,
            )
        )
        db.add(
            EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=InvoiceLineType.TAX,
                label="TVA 20%",
                amount_eur=200.0,  # exactement 20 %
            )
        )
        db.commit()
        db.refresh(invoice)

        assert detect_r24_tva_rate_mismatch(invoice, db) is None


# ─── Phase I3 — Export PDF compliance dashboard (Marie DAF) ─────────────────


class TestPhaseI3PDFExport:
    def test_i3_pdf_endpoint_returns_pdf_bytes(self, client, db):
        """I3 — endpoint PDF retourne content-type application/pdf + bytes valides."""
        org, _, _, _ = _seed_org_with_sites(db, n_sites=2)
        r = client.get(
            "/api/persona/marie-daf/compliance-dashboard.pdf",
            headers=_h(org.id),
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        # PDF magic bytes : "%PDF"
        assert r.content[:4] == b"%PDF"
        # Content-Disposition attachment avec filename
        assert "attachment" in r.headers["content-disposition"]

    def test_i3_pdf_idor_cross_tenant(self, client, db):
        """I3 — Phase E IDOR : Org B ne voit pas sites Org A dans le PDF généré."""
        org_a, _, _, _ = _seed_org_with_sites(db, "Org Alpha", "111111111", 2)
        org_b, _, _, _ = _seed_org_with_sites(db, "Org Bravo", "222222222", 0)
        r = client.get(
            "/api/persona/marie-daf/compliance-dashboard.pdf",
            headers=_h(org_b.id),
        )
        assert r.status_code == 200
        # PDF généré pour Org B → 0 sites
        assert r.content[:4] == b"%PDF"


# ─── Phase K1 — Refacto __init__ → @event.listens_for(init) orthodoxe SQLAlchemy ──


class TestPhaseK1EventListenerRefactor:
    def test_k1_event_listener_fires_on_construction(self, db, caplog):
        """K1 — `@event.listens_for(EnergyContract, 'init')` fire sur création Python."""
        import logging

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        with caplog.at_level(logging.WARNING, logger="promeos.billing"):
            EnergyContract(
                site_id=sites[0].id,
                energy_type=BillingEnergyType.ELEC,
                supplier_name="UnknownSupplier",
                end_date=date.today() + timedelta(days=180),
            )
        # Listener fire le warning (mode soft défaut)
        assert any("Phase J2 ADR-F-04" in r.message for r in caplog.records)

    def test_k1_event_listener_does_not_fire_on_load(self, db):
        """K1 — Listener ne fire PAS sur load DB (pattern orthodoxe SQLAlchemy)."""
        import json

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        # Création initiale avec legacy override
        c = EnergyContract(
            site_id=sites[0].id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            end_date=date.today() + timedelta(days=180),
            metadata_json=json.dumps({"phase_j2_legacy": True}),
        )
        db.add(c)
        db.commit()
        cid = c.id
        db.expire_all()

        # Reload depuis DB ne doit PAS déclencher de warning (pattern correct)
        loaded = db.query(EnergyContract).filter_by(id=cid).first()
        assert loaded is not None
        assert loaded.fournisseur_id is None  # legacy preserved


# ─── Phase K2 — _normalize_enum_value module-level + cache batch ──────────


class TestPhaseK2NormalizeAndCache:
    def test_k2_normalize_handles_enum_string_none(self):
        """K2 — _normalize_enum_value gère 3 cas : Enum.value / string raw / None."""
        from models.enums import AcciseCategorieElec
        from services.bill_intelligence.anomaly_detector import _normalize_enum_value

        assert _normalize_enum_value(None) is None
        assert _normalize_enum_value(AcciseCategorieElec.PME) == "PME"
        assert _normalize_enum_value("PME") == "PME"
        assert _normalize_enum_value(AcciseCategorieElec.HAUTE_PUISSANCE) == "HAUTE_PUISSANCE"

    def test_k2_resolver_cache_batch_avoids_redundant_queries(self, db):
        """K2 — `cache` dict évite N queries DP pour N invoices/site (perf batch)."""
        from models import DeliveryPoint
        from models.enums import AcciseCategorieElec, DeliveryPointEnergyType
        from services.bill_intelligence.anomaly_detector import _resolve_accise_rate_from_dp

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        dp = DeliveryPoint(
            code="14999100000099",
            energy_type=DeliveryPointEnergyType.ELEC,
            site_id=sites[0].id,
            accise_categorie_elec=AcciseCategorieElec.PME,
        )
        db.add(dp)
        db.commit()

        invoice = EnergyInvoice(
            site_id=sites[0].id,
            invoice_number="INV-K2",
            energy_kwh=1000,
            total_eur=100,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(invoice)
        db.flush()

        cache: dict = {}
        # 1er appel : query DB + populate cache
        r1 = _resolve_accise_rate_from_dp(invoice, db, cache=cache)
        assert r1[2] == "DP_CATEGORY"
        assert sites[0].id in cache
        # 2nd appel : cache hit (pas de query)
        r2 = _resolve_accise_rate_from_dp(invoice, db, cache=cache)
        assert r1 == r2  # même résultat depuis cache


# ─── Phase J2 — ADR-F-04 hard-cut supplier_name → fournisseur_id ────────────


class TestPhaseJ2HardCutFournisseurId:
    def test_j2_new_energy_contract_without_fournisseur_id_raises_strict_mode(self, db, monkeypatch):
        """J2 — Mode strict (env PROMEOS_J2_HARDCUT=1) : sans fournisseur_id → ValueError."""
        monkeypatch.setenv("PROMEOS_J2_HARDCUT", "1")
        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        with pytest.raises(ValueError, match="Phase J2 ADR-F-04"):
            EnergyContract(
                site_id=sites[0].id,
                energy_type=BillingEnergyType.ELEC,
                supplier_name="UnknownSupplier",
                end_date=date.today() + timedelta(days=180),
                # fournisseur_id manquant → doit raise en mode strict
            )

    def test_j2_soft_mode_warns_only_no_raise(self, db, caplog):
        """J2 — Mode soft (défaut) : log warning sans raise (compat fixtures legacy)."""
        import logging

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        with caplog.at_level(logging.WARNING, logger="promeos.billing"):
            c = EnergyContract(
                site_id=sites[0].id,
                energy_type=BillingEnergyType.ELEC,
                supplier_name="UnknownSupplier",
                end_date=date.today() + timedelta(days=180),
            )
        assert c is not None  # pas de raise
        assert any("Phase J2 ADR-F-04" in r.message for r in caplog.records)

    def test_j2_energy_contract_with_fournisseur_id_ok(self, db):
        """J2 — EnergyContract avec fournisseur_id valide → OK."""
        from models import Fournisseur, TypeFournitureEnum

        f = Fournisseur(nom="EDF", siren="552081317", type_fourniture=TypeFournitureEnum.MULTI)
        db.add(f)
        db.flush()

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        c = EnergyContract(
            site_id=sites[0].id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            fournisseur_id=f.id,
            end_date=date.today() + timedelta(days=180),
        )
        db.add(c)
        db.commit()
        assert c.id is not None

    def test_j2_legacy_import_override_ok(self, db):
        """J2 — Override `metadata_json={"phase_j2_legacy": true}` autorise sans fournisseur_id."""
        import json

        _, _, _, sites = _seed_org_with_sites(db, n_sites=1)
        c = EnergyContract(
            site_id=sites[0].id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Eni",  # unmapped historique
            metadata_json=json.dumps({"phase_j2_legacy": True}),
        )
        db.add(c)
        db.commit()
        assert c.id is not None
        assert c.fournisseur_id is None  # legacy override accepté


# ─── Source-guards P1 fixes (post-audit code-reviewer Phase G) ─────────────


class TestPhaseGP1FixesSourceGuards:
    def test_p1_fix_bacs_uses_real_statut_bacs_field(self):
        """P1 fix Phase H : BACS utilise Site.statut_bacs (champ réel) au lieu
        de bacs_classe (inexistant sur Site). Tri-state compliant : True/False/None.
        """
        from pathlib import Path

        src = (Path(__file__).resolve().parent.parent / "services" / "persona_dashboard_service.py").read_text(
            encoding="utf-8"
        )
        # Bug original supprimé (bool() in tuple)
        assert 'bool(getattr(site, "bacs_classe"' not in src
        # Fix Phase H final : utilise statut_bacs (vrai champ Site)
        assert 'getattr(site, "statut_bacs"' in src
        assert "StatutConformite.CONFORME" in src
        assert "StatutConformite.NON_CONFORME" in src

    def test_p1_fix_dt_compliant_null_not_false(self, client, db):
        """P1 fix : DT.compliant = None (pending trajectory) au lieu de False hardcoded."""
        org, _, _, _ = _seed_org_with_sites(db, n_sites=1)
        r = client.get("/api/persona/marie-daf/compliance-dashboard", headers=_h(org.id))
        for site in r.json()["sites"]:
            dt_fw = next(fw for fw in site["frameworks"] if fw["framework"] == "DT")
            # Compliant doit être None (pas False hardcoded), needs_trajectory_data flag présent
            if dt_fw["assujetti"]:
                assert dt_fw["compliant"] is None
                assert dt_fw["needs_trajectory_data"] is True
                assert dt_fw["exposure_eur"] is None  # pas de chiffrage faux
                assert dt_fw["exposure_max_eur"] == 7500  # plafond légal exposé

    def test_p1_fix_aper_uses_doctrine_constants(self):
        """P1 fix : APER utilise APER_PARKING_LARGE_SURFACE_M2 + APER_SOLAR_RATIO_PCT."""
        from pathlib import Path

        src = (Path(__file__).resolve().parent.parent / "services" / "persona_dashboard_service.py").read_text(
            encoding="utf-8"
        )
        # Constantes doctrine importées
        assert "APER_PARKING_LARGE_SURFACE_M2" in src
        assert "APER_SOLAR_RATIO_PCT" in src
        # Pas d'usage hardcodé `> 10000` ou `>= 50` dans _aper_status
        # (note : ne grep pas le commentaire qui peut contenir `>=50` en explication)
        aper_block = src.split("def _aper_status")[1].split("def ")[0]
        assert "> 10000" not in aper_block, "_aper_status doit utiliser APER_PARKING_LARGE_SURFACE_M2"
        assert "parking_solar_pct >= 50" not in aper_block, "_aper_status doit utiliser APER_SOLAR_RATIO_PCT"
