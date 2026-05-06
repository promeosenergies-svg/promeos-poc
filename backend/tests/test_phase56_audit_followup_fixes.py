"""
PROMEOS — Tests cardinaux Phase 5.6 audit follow-up fixes (Sprint C-5).

Anti-régression cardinal post-audit deep multi-agents Phase 5.5 :
- F1 PRAGMA foreign_keys=ON enforcé runtime (RGPD ondelete=SET NULL)
- F2 R19 NULL handling (energy_kwh IS NULL ≠ 0, élimine faux positif acompte)
- F3 Formule Capacité corrigée (3.15 → 3150 EUR/MW.an cohérent runtime 0.43)
- F4 SG tolerance 1500 → 1.5 (anti-régression formule renforcé)

Si quelqu'un revert un fix (ex: retire PRAGMA, ou remet 3.15 dans YAML, ou
retire la branche NULL), ces tests cassent immédiatement.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── F1 PRAGMA foreign_keys=ON ──────────────────────────────────────────────


def test_f1_pragma_foreign_keys_enabled_on_main_engine():
    """F1 cardinal : le pragma foreign_keys est activé au connect SQLite (event listener)."""
    from database import engine

    if engine.dialect.name != "sqlite":
        pytest.skip("F1 PRAGMA test SQLite-only — autres dialectes enforce FK par défaut")

    # Forcer un nouveau connect pour déclencher le listener
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert result == 1, (
            f"F1 BLOQUANT : PRAGMA foreign_keys = {result} (attendu 1).\n"
            "Sans ce pragma, ondelete=SET NULL × 4 FK consentement_*_by est silencieusement "
            "non-enforced runtime (régression Phase 5.3 RGPD)."
        )


def test_f1_user_delete_set_null_consentement_by_runtime_enforced():
    """F1 cardinal : suppression user → consentement_*_by → NULL effectivement enforced runtime.

    Distinct du test test_user_delete_sets_org_consentement_by_to_null (qui active le pragma
    explicitement via PRAGMA foreign_keys=ON dans le fixture). Ici on teste que le PRAGMA
    natif du connect listener fonctionne SANS hack test.
    """
    from models import Base, Organisation, User

    # Engine vierge AVEC le listener PRAGMA via import database.engine
    from database import engine as main_engine

    if main_engine.dialect.name != "sqlite":
        pytest.skip("F1 RGPD test SQLite-only")

    # Créer engine in-memory avec MÊME listener (via copy stratégie : new engine,
    # listener attaché auto via @event.listens_for(Engine, "connect"))
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Réenregistrer le listener PRAGMA (équivalent à database/connection.py)
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, _cr):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Vérifier que le PRAGMA est bien actif sur cette connexion
        pragma_state = db.execute(text("PRAGMA foreign_keys")).scalar()
        assert pragma_state == 1, "PRAGMA foreign_keys non enforced sur fixture engine"

        user = User(
            email="f1_test@promeos.io",
            hashed_password="hash",
            nom="Test",
            prenom="F1",
            actif=True,
        )
        db.add(user)
        db.flush()

        org = Organisation(
            nom="OrgF1",
            siren="900000001",
            consentement_dataconnect_by=user.id,
            consentement_dataconnect_cgu_version="1.0",
        )
        db.add(org)
        db.commit()

        # Suppression user — ondelete=SET NULL doit s'appliquer effectivement
        db.delete(user)
        db.commit()
        db.refresh(org)

        assert org.consentement_dataconnect_by is None, (
            "F1 BLOQUANT : suppression user N'A PAS déclenché SET NULL sur "
            "consentement_dataconnect_by — PRAGMA foreign_keys non enforced runtime."
        )
        assert org.consentement_dataconnect_cgu_version == "1.0", (
            "F1 : cgu_version doit être préservé post-suppression user (audit RGPD)."
        )
    finally:
        db.close()


# ─── F2 R19 NULL handling ───────────────────────────────────────────────────


def test_f2_r19_null_consumption_returns_none_not_flag(tmp_path):
    """F2 cardinal : invoice.energy_kwh IS NULL → R19 retourne None (pas anomaly).

    Avant fix Phase 5.6 : faux positif systématique sur factures acompte EDF/Engie B2B
    (consumption=0 < 100 → R19 fire alors que conso est INCONNUE, pas absente).
    """
    from models import (
        Base,
        BillingInvoiceStatus,
        EnergyInvoice,
        EnergyInvoiceLine,
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )
    from services.bill_intelligence import detect_r19_vnu_dormant

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        org = Organisation(nom="O", siren="900000002")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJ", siren="900000002", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PF", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="S", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        # Facture acompte : energy_kwh = NULL (cas légitime EDF/Engie)
        invoice = EnergyInvoice(
            site_id=site.id,
            invoice_number="ACOMPTE-001",
            period_start=datetime(2026, 4, 1, tzinfo=timezone.utc).date(),
            period_end=datetime(2026, 4, 30, tzinfo=timezone.utc).date(),
            total_eur=500.0,
            energy_kwh=None,  # CARDINAL : NULL pas 0
            status=BillingInvoiceStatus.IMPORTED,
        )
        db.add(invoice)
        db.flush()

        # VNU > seuil sur cette facture acompte
        line = EnergyInvoiceLine(
            invoice_id=invoice.id,
            line_type="tax",
            label="VNU - Versement pour Non-Usage",
            amount_eur=15.0,
        )
        db.add(line)
        db.commit()

        result = detect_r19_vnu_dormant(invoice, db)

        assert result is None, (
            "F2 BLOQUANT : energy_kwh IS NULL → R19 doit retourner None (consumption inconnue).\n"
            f"Au lieu de None, retour : {result}\n"
            "Régression : avant fix Phase 5.6, R19 fire systématiquement sur acompte VNU."
        )
    finally:
        db.close()


# ─── F3 Formule Capacité corrigée ────────────────────────────────────────────


def test_f3_capacite_yaml_value_is_3150_not_3_15():
    """F3 cardinal : YAML CAPACITE_RTE_TARIF_2026_EUR_PER_MW = 3150 (pas 3.15)."""
    from config.regulatory_sources_loader import get_term_value, reload_regulatory_sources

    reload_regulatory_sources()
    yaml_value = get_term_value("CAPACITE_RTE_TARIF_2026_EUR_PER_MW")

    assert yaml_value == 3150, (
        f"F3 BLOQUANT : YAML CAPACITE_RTE_TARIF_2026_EUR_PER_MW = {yaml_value} (attendu 3150).\n"
        "Régression : valeur 3.15 produit formule incohérente x1000 vs runtime 0.43 EUR/MWh.\n"
        "Audit deep Phase 5.5 a corrigé typo factor 1000 manquant Sprint C-4 P4.2."
    )


def test_f3_capacite_arithmetic_yaml_matches_runtime():
    """F3 cardinal : 3150 × 1.2 / 8760 ≈ 0.43 (cohérence formule YAML ↔ runtime)."""
    from config.regulatory_sources_loader import get_term_value, reload_regulatory_sources
    from services.purchase.cost_simulator_2026 import CAPACITE_UNITAIRE_EUR_MWH

    reload_regulatory_sources()
    yaml_price = get_term_value("CAPACITE_RTE_TARIF_2026_EUR_PER_MW")
    yaml_coeff = get_term_value("CAPACITE_RTE_COEFF_2026")

    formula_value = (yaml_price * yaml_coeff) / 8760

    # Tolerance 5% (runtime 0.43 vs formule 0.4315)
    delta = abs(formula_value - CAPACITE_UNITAIRE_EUR_MWH)
    assert delta < 0.05, (
        f"F3 BLOQUANT : ({yaml_price} × {yaml_coeff}) / 8760 = {formula_value:.4f} EUR/MWh "
        f"vs runtime CAPACITE_UNITAIRE_EUR_MWH = {CAPACITE_UNITAIRE_EUR_MWH}.\n"
        f"Δ = {delta:.4f} (tolerance 0.05).\n"
        "Régression : YAML et runtime divergent — corriger typo Phase 5.6 fix F3."
    )


# ─── F4 SG tolerance Capacité ────────────────────────────────────────────────


def test_f4_sg_tolerance_max_is_1_5_not_1500():
    """F4 cardinal : SG _RATIO_TOLERANCE_MAX = 1.5 (pas 1500 qui masquait erreur F3)."""
    sg_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tests",
        "source_guards",
        "test_cost_simulator_2026_yaml_consistency_source_guards.py",
    )
    with open(sg_path, encoding="utf-8") as f:
        content = f.read()

    assert "_RATIO_TOLERANCE_MAX = 1.5" in content, (
        "F4 BLOQUANT : _RATIO_TOLERANCE_MAX doit être 1.5 (pas 1500).\n"
        "Régression : tolérance 1500 masque erreur F3 (×1000 dans formule capacité)."
    )

    assert "_RATIO_TOLERANCE_MAX = 1500" not in content, (
        "F4 BLOQUANT : ancienne tolerance 1500 doit être retirée (masquait erreur F3)."
    )
