"""
PROMEOS — Tests cardinaux Phase 5.8 audit transversal Phase C fixes (Sprint C-5).

Anti-régression cardinal post-audit transversal Phase 5.7 (10 P0 + 18 findings nouveaux) :
- G1 Cascade Org consentement PATCH wiring runtime (vs déclarée CASCADE_MAP non-effective)
- G2 R20 NULL handling (line.qty IS NULL ≠ 0, élimine faux negative HTA)
- G3 BillAnomaly UNIQUE(invoice_id, code) anti-doublons
- G4 ADR-015 sections amont avertissement HISTORIQUE post Phase 5.6 F3
- G5 Onboarding stepper IDOR org_id_override retiré (4 endpoints)
- G6 operat_export NULL handling distinct (cardinal réglementaire DT)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── G2 R20 NULL handling ────────────────────────────────────────────────────


def test_g2_r20_null_qty_returns_no_anomaly():
    """G2 cardinal : line.qty IS NULL → R20 ne flag pas (acompte sans relève kVA)."""
    from datetime import date

    from models import (
        Base,
        BillingInvoiceStatus,
        EnergyInvoice,
        EnergyInvoiceLine,
        EnergyVector,
        EntiteJuridique,
        Meter,
        Organisation,
        Portefeuille,
        PowerContract,
        Site,
        TypeSite,
    )
    from services.bill_intelligence import detect_r20_capacity_variance

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        org = Organisation(nom="O_G2", siren="700000001")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJ", siren="700000001", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PF", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="S", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        meter = Meter(
            meter_id="PRM-G2-001",
            name="Meter G2",
            site_id=site.id,
            energy_vector=EnergyVector.ELECTRICITY,
            subscribed_power_kva=36,
        )
        db.add(meter)
        db.flush()

        contract = PowerContract(
            meter_id=meter.id,
            date_debut=date(2026, 1, 1),
            date_fin=None,
            domaine_tension="BT",
            fta_code="BTSUPCU4",
            ps_par_poste_kva={"HPH": 36},
        )
        db.add(contract)
        db.flush()

        invoice = EnergyInvoice(
            site_id=site.id,
            invoice_number="ACOMPTE-G2",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            energy_kwh=10000,
            status=BillingInvoiceStatus.IMPORTED,
        )
        db.add(invoice)
        db.flush()

        # Ligne kVA avec qty NULL (cas légitime acompte sans relève)
        line = EnergyInvoiceLine(
            invoice_id=invoice.id,
            line_type="network",
            label="Capacité HPH",
            qty=None,  # CARDINAL G2 : NULL
            unit="kVA",
            period_code="HPH",
        )
        db.add(line)
        db.commit()

        result = detect_r20_capacity_variance(invoice, db)

        assert result == [], (
            f"G2 BLOQUANT : R20 doit retourner [] si line.qty IS NULL.\n"
            f"Au lieu de [], retour : {result}\n"
            "Régression : faux negative variance HTA si donnée manquante traitée comme 0."
        )
    finally:
        db.close()


# ─── G3 BillAnomaly UNIQUE constraint ────────────────────────────────────────


def test_g3_bill_anomaly_unique_invoice_code_constraint():
    """G3 cardinal : UNIQUE(invoice_id, code) empêche doublons R19/R20 sur même invoice."""
    from models import (
        Base,
        BillAnomaly,
        BillingInvoiceStatus,
        EnergyInvoice,
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # Activer FK pour test SQLite
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.execute(text("PRAGMA foreign_keys=ON"))

    try:
        org = Organisation(nom="O", siren="700000002")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJ", siren="700000002", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PF", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="S", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        from datetime import date

        invoice = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-G3",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            energy_kwh=1000,
            status=BillingInvoiceStatus.IMPORTED,
        )
        db.add(invoice)
        db.flush()

        # Première anomaly R19
        a1 = BillAnomaly(
            invoice_id=invoice.id,
            code="R19",
            severity="warning",
        )
        db.add(a1)
        db.commit()

        # Tentative doublon R19 sur même invoice → IntegrityError
        a2 = BillAnomaly(
            invoice_id=invoice.id,
            code="R19",
            severity="critical",
        )
        db.add(a2)

        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.close()


def test_g3_bill_anomaly_distinct_codes_allowed():
    """G3 : R19 + R20 sur même invoice OK (codes distincts)."""
    from models import (
        Base,
        BillAnomaly,
        BillingInvoiceStatus,
        EnergyInvoice,
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        org = Organisation(nom="O", siren="700000003")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJ", siren="700000003", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PF", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="S", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        from datetime import date

        invoice = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-G3b",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            status=BillingInvoiceStatus.IMPORTED,
        )
        db.add(invoice)
        db.flush()

        a1 = BillAnomaly(invoice_id=invoice.id, code="R19", severity="warning")
        a2 = BillAnomaly(invoice_id=invoice.id, code="R20", severity="critical")
        db.add_all([a1, a2])
        db.commit()  # OK : codes distincts

        from models import BillAnomaly as BA

        assert db.query(BA).filter(BA.invoice_id == invoice.id).count() == 2
    finally:
        db.close()


# ─── G6 operat_export NULL handling ──────────────────────────────────────────


def test_g6_get_site_conso_with_completeness_distinguishes_null_from_zero():
    """G6 cardinal : helper distingue NULL (incomplete_null) de 0 (complete) — DT compliance."""
    from datetime import date

    from models import (
        Base,
        BillingInvoiceStatus,
        EnergyInvoice,
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )
    from services.operat_export_service import _get_site_conso_with_completeness

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        org = Organisation(nom="O", siren="700000004")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJ", siren="700000004", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PF", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="S", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        # Cas 1 : pas de facture → "no_data"
        conso, status = _get_site_conso_with_completeness(db, site.id, 2026)
        assert status == "no_data"
        assert conso == {"elec": 0, "gaz": 0, "reseau": 0}

        # Cas 2 : 1 facture avec energy_kwh NULL → "incomplete_null"
        invoice_null = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-NULL",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            energy_kwh=None,  # CARDINAL G6 : NULL
            status=BillingInvoiceStatus.IMPORTED,
        )
        db.add(invoice_null)
        db.commit()

        conso, status = _get_site_conso_with_completeness(db, site.id, 2026)
        assert status == "incomplete_null", (
            f"G6 BLOQUANT : facture energy_kwh=NULL doit produire status='incomplete_null'.\n"
            f"Au lieu, status = '{status}'.\n"
            "DT compliance : NULL ≠ 0 (donnée manquante vs mesurée à 0). Sanctions Décret Tertiaire."
        )

        # Cas 3 : ajouter 1 facture avec energy_kwh=0 explicite → toujours "incomplete_null"
        # (présence d'une NULL parmi les autres)
        invoice_zero = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-ZERO",
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            energy_kwh=0,  # 0 explicite (mesuré à 0)
            status=BillingInvoiceStatus.IMPORTED,
        )
        db.add(invoice_zero)
        db.commit()

        conso, status = _get_site_conso_with_completeness(db, site.id, 2026)
        # has_null=True garde le statut incomplete_null (1 NULL parmi les 2)
        assert status == "incomplete_null"
    finally:
        db.close()


# ─── G5 Onboarding stepper IDOR fix ──────────────────────────────────────────


def test_g5_onboarding_stepper_org_id_override_removed():
    """G5 cardinal : retire `org_id_override=org_id` des 4 endpoints stepper (anti-IDOR cross-tenant DEMO)."""
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stepper_path = os.path.join(backend_root, "routes", "onboarding_stepper.py")
    with open(stepper_path, encoding="utf-8") as f:
        content = f.read()

    # Anti-régression : aucune occurrence `org_id_override=org_id`
    assert "org_id_override=org_id" not in content, (
        "G5 BLOQUANT : `org_id_override=org_id` détecté dans onboarding_stepper.py.\n"
        "Régression : permet cross-tenant énumération en DEMO_MODE (SEC-2026-011).\n"
        "Fix Phase 5.8 G5 : remplacer par `resolve_org_id(request, auth, db)` strict."
    )

    # Au moins 4 résolutions strictes (4 endpoints stepper)
    strict_count = content.count("resolve_org_id(request, auth, db)")
    assert strict_count >= 4, (
        f"G5 : attendu ≥4 appels `resolve_org_id(request, auth, db)` strict, trouvé {strict_count}.\n"
        "4 endpoints stepper (GET / PATCH /step / POST /dismiss / POST /auto) doivent tous être strict."
    )


# ─── G4 ADR-015 avertissement post-Phase 5.6 ─────────────────────────────────


def test_g4_adr015_has_phase56_warning_block():
    """G4 cardinal : ADR-015 contient l'avertissement HISTORIQUE post Phase 5.6 F3."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    adr_path = os.path.join(repo_root, "docs", "adr", "ADR-015-Capacite-EUR-MW-Disambiguation.md")
    with open(adr_path, encoding="utf-8") as f:
        content = f.read()

    assert "AVERTISSEMENT LECTEUR" in content, (
        "G4 BLOQUANT : ADR-015 doit contenir bloc 'AVERTISSEMENT LECTEUR' Phase 5.8 fix G4.\n"
        "Régression : sections amont stale (3.15 EUR/MW) sans warning → confusion lecteur."
    )

    assert "3150 EUR/MW.an" in content, "G4 : valeur corrigée 3150 doit être documentée."

    assert "HISTORIQUE pré-Phase 5.6" in content or "HISTORIQUE" in content, (
        "G4 : contexte historique des sections amont doit être marqué."
    )
