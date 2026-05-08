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
        c = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name=supplier,
            end_date=end_date,
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
