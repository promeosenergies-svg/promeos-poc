"""
PROMEOS — V27: Product Invariant Guard Tests
10 invariants metier critiques — tests fonctionnels (pas techniques).

INV-1:  cockpit total_sites == db count
INV-2:  risque_financier == SUM(sites.risque)
INV-3:  conformite hierarchy NOK > A_RISQUE > OK
INV-5:  cockpit scoped to org (no cross-org leakage)
INV-7:  facture total = sum(lignes) (R8, 2% tolerance)
INV-8:  shadow billing = kwh * prix_ref
INV-9:  compteur requires site_id (FK NOT NULL)
INV-10: staging activation blocked by critical findings
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Compteur,
    Obligation,
    Alerte,
    EnergyInvoice,
    EnergyInvoiceLine,
    EnergyContract,
    StagingBatch,
    StagingSite,
    StagingCompteur,
    QualityFinding,
    StatutConformite,
    TypeObligation,
    TypeCompteur,
    TypeSite,
    SeveriteAlerte,
    StagingStatus,
    ImportSourceType,
    QualityRuleSeverity,
    BillingEnergyType,
    InvoiceLineType,
    not_deleted,
)


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════


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


_siren_counter = 0


def _make_org(db, nom="Org Test"):
    global _siren_counter
    _siren_counter += 1
    org = Organisation(nom=nom, type_client="tertiaire_prive")
    db.add(org)
    db.flush()
    siren = f"{100000000 + _siren_counter}"
    ej = EntiteJuridique(nom=f"EJ {nom}", organisation_id=org.id, siren=siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom=f"PF {nom}", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    return org, ej, pf


def _make_site(db, pf, nom="Site Test", risque=0, actif=True):
    site = Site(
        nom=nom,
        type=TypeSite.BUREAU,
        portefeuille_id=pf.id,
        actif=actif,
        risque_financier_euro=risque,
    )
    db.add(site)
    db.flush()
    return site


# ══════════════════════════════════════════════════════════════════════════════
# INV-1: cockpit total_sites == actual db count
# ══════════════════════════════════════════════════════════════════════════════


class TestInv1TotalSites:
    def test_total_matches_db_count(self, db):
        """total_sites from cockpit logic must equal real DB count for org."""
        org, ej, pf = _make_org(db)
        for i in range(5):
            _make_site(db, pf, nom=f"Site {i}")
        db.commit()

        # Reproduce cockpit's _sites_for_org logic
        q = (
            not_deleted(db.query(Site), Site)
            .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
            .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
            .filter(EntiteJuridique.organisation_id == org.id)
        )
        total_sites = q.count()
        assert total_sites == 5

    def test_soft_deleted_excluded(self, db):
        """Soft-deleted sites must NOT be counted."""
        from datetime import datetime, timezone

        org, ej, pf = _make_org(db)
        s1 = _make_site(db, pf, nom="Active")
        s2 = _make_site(db, pf, nom="Deleted")
        s2.deleted_at = datetime.now(timezone.utc)
        db.commit()

        q = (
            not_deleted(db.query(Site), Site)
            .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
            .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
            .filter(EntiteJuridique.organisation_id == org.id)
        )
        assert q.count() == 1


# ══════════════════════════════════════════════════════════════════════════════
# INV-2: risque_financier == SUM(sites.risque_financier_euro)
# ══════════════════════════════════════════════════════════════════════════════


class TestInv2RisqueFinancier:
    def test_risque_is_sum(self, db):
        """risque_financier_euro must equal SUM of all site risks for org."""
        from sqlalchemy import func

        org, ej, pf = _make_org(db)
        _make_site(db, pf, nom="S1", risque=5000)
        _make_site(db, pf, nom="S2", risque=12000)
        _make_site(db, pf, nom="S3", risque=3000)
        db.commit()

        q = (
            not_deleted(db.query(Site), Site)
            .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
            .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
            .filter(EntiteJuridique.organisation_id == org.id)
        )
        total_risque = q.with_entities(func.sum(Site.risque_financier_euro)).scalar() or 0
        assert total_risque == 20000


# ══════════════════════════════════════════════════════════════════════════════
# INV-3: conformite hierarchy NOK > A_RISQUE > OK
# ══════════════════════════════════════════════════════════════════════════════


class TestInv3ConformiteHierarchy:
    def _compute_conformite(self, db, org_id, site_ids):
        """Reproduce dashboard_2min conformite logic."""
        obligations = db.query(Obligation).filter(Obligation.site_id.in_(site_ids)).all() if site_ids else []
        if not obligations:
            return {"label": "A evaluer", "color": "gray"}

        nb_conforme = sum(1 for o in obligations if o.statut == StatutConformite.CONFORME)
        nb_non_conforme = sum(1 for o in obligations if o.statut == StatutConformite.NON_CONFORME)
        nb_a_risque = sum(1 for o in obligations if o.statut == StatutConformite.A_RISQUE)
        total_obl = len(obligations)

        if nb_non_conforme > 0:
            return {"label": "Non conforme", "color": "red"}
        elif nb_a_risque > 0:
            return {"label": "A risque", "color": "orange"}
        elif nb_conforme == total_obl:
            return {"label": "Conforme", "color": "green"}
        else:
            return {"label": "En cours", "color": "blue"}

    def test_red_if_any_non_conforme(self, db):
        org, ej, pf = _make_org(db)
        s1 = _make_site(db, pf, nom="OK")
        s2 = _make_site(db, pf, nom="NOK")
        db.add(Obligation(site_id=s1.id, type=TypeObligation.DECRET_TERTIAIRE, statut=StatutConformite.CONFORME))
        db.add(Obligation(site_id=s2.id, type=TypeObligation.DECRET_TERTIAIRE, statut=StatutConformite.NON_CONFORME))
        db.commit()

        result = self._compute_conformite(db, org.id, [s1.id, s2.id])
        assert result["label"] == "Non conforme"
        assert result["color"] == "red"

    def test_orange_if_a_risque_no_nok(self, db):
        org, ej, pf = _make_org(db)
        s1 = _make_site(db, pf, nom="OK")
        s2 = _make_site(db, pf, nom="RISK")
        db.add(Obligation(site_id=s1.id, type=TypeObligation.DECRET_TERTIAIRE, statut=StatutConformite.CONFORME))
        db.add(Obligation(site_id=s2.id, type=TypeObligation.DECRET_TERTIAIRE, statut=StatutConformite.A_RISQUE))
        db.commit()

        result = self._compute_conformite(db, org.id, [s1.id, s2.id])
        assert result["label"] == "A risque"
        assert result["color"] == "orange"

    def test_green_if_all_conforme(self, db):
        org, ej, pf = _make_org(db)
        s1 = _make_site(db, pf, nom="OK1")
        s2 = _make_site(db, pf, nom="OK2")
        db.add(Obligation(site_id=s1.id, type=TypeObligation.DECRET_TERTIAIRE, statut=StatutConformite.CONFORME))
        db.add(Obligation(site_id=s2.id, type=TypeObligation.BACS, statut=StatutConformite.CONFORME))
        db.commit()

        result = self._compute_conformite(db, org.id, [s1.id, s2.id])
        assert result["label"] == "Conforme"
        assert result["color"] == "green"


# ══════════════════════════════════════════════════════════════════════════════
# INV-5: cockpit scoped to org — no cross-org data
# ══════════════════════════════════════════════════════════════════════════════


class TestInv5OrgScoping:
    def test_sites_only_from_target_org(self, db):
        """Sites from org2 must NEVER appear in org1's cockpit query."""
        org1, ej1, pf1 = _make_org(db, nom="Org1")
        org2, ej2, pf2 = _make_org(db, nom="Org2")
        _make_site(db, pf1, nom="Site Org1")
        _make_site(db, pf2, nom="Site Org2")
        db.commit()

        q = (
            not_deleted(db.query(Site), Site)
            .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
            .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
            .filter(EntiteJuridique.organisation_id == org1.id)
        )
        sites = q.all()
        assert len(sites) == 1
        assert sites[0].nom == "Site Org1"

    def test_alertes_scoped_to_org_sites(self, db):
        """Alertes from other org's sites must not be counted."""
        org1, ej1, pf1 = _make_org(db, nom="Org1")
        org2, ej2, pf2 = _make_org(db, nom="Org2")
        s1 = _make_site(db, pf1, nom="S1")
        s2 = _make_site(db, pf2, nom="S2")
        from datetime import datetime, timezone

        db.add(
            Alerte(
                site_id=s1.id,
                titre="Alert org1",
                description="Detail",
                resolue=False,
                severite=SeveriteAlerte.WARNING,
                timestamp=datetime.now(timezone.utc),
            )
        )
        db.add(
            Alerte(
                site_id=s2.id,
                titre="Alert org2",
                description="Detail",
                resolue=False,
                severite=SeveriteAlerte.CRITICAL,
                timestamp=datetime.now(timezone.utc),
            )
        )
        db.commit()

        # Cockpit query: alertes for org1 only
        site_ids_org1 = [
            s.id
            for s in not_deleted(db.query(Site), Site)
            .join(Portefeuille)
            .join(EntiteJuridique)
            .filter(EntiteJuridique.organisation_id == org1.id)
            .with_entities(Site.id)
            .all()
        ]
        alertes = (
            db.query(Alerte)
            .filter(
                Alerte.resolue == False,
                Alerte.site_id.in_(site_ids_org1),
            )
            .count()
        )
        assert alertes == 1


# ══════════════════════════════════════════════════════════════════════════════
# INV-7: facture total = sum(lignes) — R8 rule with 2% tolerance
# ══════════════════════════════════════════════════════════════════════════════


class TestInv7InvoiceLinesSum:
    def test_mismatch_detected_above_2pct(self, db):
        """R8 must detect when lines sum diverges > 2% from invoice total."""
        from services.billing_service import _rule_lines_sum_mismatch

        org, ej, pf = _make_org(db)
        site = _make_site(db, pf)
        invoice = EnergyInvoice(
            site_id=site.id,
            total_eur=1000.0,
            energy_kwh=5000,
            invoice_number="F-001",
        )
        db.add(invoice)
        db.flush()

        # Lines sum = 800 → 20% off → should trigger
        lines = [
            EnergyInvoiceLine(
                invoice_id=invoice.id, label="Energie", amount_eur=500.0, line_type=InvoiceLineType.ENERGY
            ),
            EnergyInvoiceLine(
                invoice_id=invoice.id, label="Reseau", amount_eur=300.0, line_type=InvoiceLineType.NETWORK
            ),
        ]
        db.add_all(lines)
        db.commit()

        result = _rule_lines_sum_mismatch(invoice, None, lines)
        assert result is not None
        assert result["type"] == "lines_sum_mismatch"
        assert result["severity"] == "high"  # > 10%

    def test_within_tolerance_ok(self, db):
        """R8 must NOT trigger when lines sum is within 2% of total."""
        from services.billing_service import _rule_lines_sum_mismatch

        org, ej, pf = _make_org(db)
        site = _make_site(db, pf)
        invoice = EnergyInvoice(
            site_id=site.id,
            total_eur=1000.0,
            energy_kwh=5000,
            invoice_number="F-002",
        )
        db.add(invoice)
        db.flush()

        # Lines sum = 990 → 1% off → within tolerance
        lines = [
            EnergyInvoiceLine(
                invoice_id=invoice.id, label="Energie", amount_eur=600.0, line_type=InvoiceLineType.ENERGY
            ),
            EnergyInvoiceLine(
                invoice_id=invoice.id, label="Reseau", amount_eur=390.0, line_type=InvoiceLineType.NETWORK
            ),
        ]
        db.add_all(lines)
        db.commit()

        result = _rule_lines_sum_mismatch(invoice, None, lines)
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# INV-8: shadow billing = kwh * prix_ref
# ══════════════════════════════════════════════════════════════════════════════


class TestInv8ShadowBilling:
    def test_shadow_formula(self, db):
        """shadow_total = energy_kwh * price_ref (default 0.18 for elec)."""
        from services.billing_service import shadow_billing_simple

        org, ej, pf = _make_org(db)
        site = _make_site(db, pf)
        invoice = EnergyInvoice(
            site_id=site.id,
            total_eur=200.0,
            energy_kwh=1000,
            invoice_number="F-003",
        )
        db.add(invoice)
        db.commit()

        from services.billing_service import DEFAULT_PRICE_ELEC

        result = shadow_billing_simple(invoice)
        assert result["method"] == "simple"
        expected_shadow = 1000 * DEFAULT_PRICE_ELEC
        assert result["shadow_total_eur"] == expected_shadow
        assert result["delta_eur"] == 200.0 - expected_shadow
        assert result["energy_kwh"] == 1000

    def test_contract_price_takes_priority(self, db):
        """When contract exists with price_ref, use contract price over default."""
        from services.billing_service import shadow_billing_simple

        org, ej, pf = _make_org(db)
        site = _make_site(db, pf)
        contract = EnergyContract(
            site_id=site.id,
            supplier_name="EDF",
            energy_type=BillingEnergyType.ELEC,
            price_ref_eur_per_kwh=0.22,
        )
        db.add(contract)
        invoice = EnergyInvoice(
            site_id=site.id,
            total_eur=250.0,
            energy_kwh=1000,
            invoice_number="F-004",
            contract_id=None,
        )
        db.add(invoice)
        db.commit()

        result = shadow_billing_simple(invoice, contract=contract)
        assert result["shadow_total_eur"] == 220.0  # 1000 * 0.22
        assert result["ref_price_source"] == f"contract:{contract.id}"

    def test_skip_when_no_kwh(self, db):
        """shadow_billing must skip when energy_kwh is 0 or None."""
        from services.billing_service import shadow_billing_simple

        org, ej, pf = _make_org(db)
        site = _make_site(db, pf)
        invoice = EnergyInvoice(
            site_id=site.id,
            total_eur=100.0,
            energy_kwh=0,
            invoice_number="F-005",
        )
        db.add(invoice)
        db.commit()

        result = shadow_billing_simple(invoice)
        assert result["method"] == "skip"


# ══════════════════════════════════════════════════════════════════════════════
# INV-9: compteur requires site_id (FK NOT NULL)
# ══════════════════════════════════════════════════════════════════════════════


class TestInv9CompteurSiteFk:
    def test_compteur_without_site_raises(self, db):
        """Creating a compteur without site_id must raise IntegrityError."""
        compteur = Compteur(
            type=TypeCompteur.ELECTRICITE,
            numero_serie="ORPHAN-001",
            site_id=None,
        )
        db.add(compteur)
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_compteur_with_site_ok(self, db):
        """Creating a compteur with valid site_id must succeed."""
        org, ej, pf = _make_org(db)
        site = _make_site(db, pf)
        compteur = Compteur(
            type=TypeCompteur.ELECTRICITE,
            numero_serie="VALID-001",
            site_id=site.id,
        )
        db.add(compteur)
        db.commit()
        assert compteur.id is not None
        assert compteur.site_id == site.id


# ══════════════════════════════════════════════════════════════════════════════
# INV-10: staging activation blocked by unresolved critical findings
# ══════════════════════════════════════════════════════════════════════════════


class TestInv10StagingQualityGate:
    def test_activation_blocked_by_critical_finding(self, db):
        """_pre_activation_checks must raise if unresolved CRITICAL findings exist."""
        from services.patrimoine_service import _pre_activation_checks

        org, ej, pf = _make_org(db)
        batch = StagingBatch(org_id=org.id, status=StagingStatus.VALIDATED, source_type=ImportSourceType.CSV)
        db.add(batch)
        db.flush()

        finding = QualityFinding(
            batch_id=batch.id,
            rule_id="dup_meter",
            severity=QualityRuleSeverity.CRITICAL,
            resolved=False,
        )
        db.add(finding)
        db.commit()

        with pytest.raises(ValueError, match="unresolved blocking/critical"):
            _pre_activation_checks(db, batch.id)

    def test_activation_blocked_by_blocking_finding(self, db):
        """_pre_activation_checks must raise if unresolved BLOCKING findings exist."""
        from services.patrimoine_service import _pre_activation_checks

        org, ej, pf = _make_org(db)
        batch = StagingBatch(org_id=org.id, status=StagingStatus.VALIDATED, source_type=ImportSourceType.CSV)
        db.add(batch)
        db.flush()

        finding = QualityFinding(
            batch_id=batch.id,
            rule_id="dup_site",
            severity=QualityRuleSeverity.BLOCKING,
            resolved=False,
        )
        db.add(finding)
        db.commit()

        with pytest.raises(ValueError, match="unresolved blocking/critical"):
            _pre_activation_checks(db, batch.id)

    def test_activation_ok_after_resolving(self, db):
        """_pre_activation_checks must pass when all critical findings are resolved."""
        from services.patrimoine_service import _pre_activation_checks

        org, ej, pf = _make_org(db)
        batch = StagingBatch(org_id=org.id, status=StagingStatus.VALIDATED, source_type=ImportSourceType.CSV)
        db.add(batch)
        db.flush()

        finding = QualityFinding(
            batch_id=batch.id,
            rule_id="dup_meter",
            severity=QualityRuleSeverity.CRITICAL,
            resolved=True,
            resolution="merged",
        )
        db.add(finding)
        db.commit()

        # Should not raise
        _pre_activation_checks(db, batch.id)
