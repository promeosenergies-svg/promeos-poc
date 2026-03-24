"""
PROMEOS — Tests purchase_actions_engine.py (Sprint QA XS)
Couvre les 5 types d'actions : renewal_urgent, renewal_soon, renewal_plan, strategy_switch, accept_reco.
Vérifie priorités, filtres, sévérités et gain potentiel.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    EnergyContract,
    PurchaseAssumptionSet,
    PurchaseScenarioResult,
    PurchaseStrategy,
    PurchaseRecoStatus,
    BillingEnergyType,
    TypeSite,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed org → entite → portefeuille → site
    org = Organisation(nom="Test Org", siren="123456789")
    session.add(org)
    session.flush()
    ej = EntiteJuridique(nom="Test EJ", organisation_id=org.id, siren="987654321")
    session.add(ej)
    session.flush()
    pf = Portefeuille(nom="Test PF", entite_juridique_id=ej.id)
    session.add(pf)
    session.flush()
    site = Site(
        nom="Site Test",
        type=TypeSite.BUREAU,
        surface_m2=2000,
        portefeuille_id=pf.id,
        actif=True,
    )
    session.add(site)
    session.flush()

    yield session
    session.close()


class TestRenewalActions:
    """Tests des 3 types d'actions renouvellement contrat."""

    def test_renewal_urgent_past_notice(self, db_session):
        """Contrat dont la deadline de préavis est passée → renewal_urgent (red)."""
        from services.purchase_actions_engine import compute_purchase_actions

        site = db_session.query(Site).first()
        # Contrat expirant dans 30 jours, préavis 90 jours → notice passée de 60 jours
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            end_date=date.today() + timedelta(days=30),
            notice_period_days=90,
        )
        db_session.add(contract)
        db_session.flush()

        result = compute_purchase_actions(db_session)

        assert result["total_actions"] >= 1
        urgent = [a for a in result["actions"] if a["type"] == "renewal_urgent"]
        assert len(urgent) == 1
        assert urgent[0]["severity"] == "red"
        assert urgent[0]["priority"] == 100
        assert urgent[0]["supplier"] == "EDF"
        assert urgent[0]["site_id"] == site.id

    def test_renewal_soon_within_60_days(self, db_session):
        """Contrat dont le préavis est dans 31-60 jours → renewal_soon (orange)."""
        from services.purchase_actions_engine import compute_purchase_actions

        site = db_session.query(Site).first()
        # Notice deadline dans 45 jours → renewal_soon
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Engie",
            end_date=date.today() + timedelta(days=135),  # 135 - 90 = 45 jours de notice
            notice_period_days=90,
        )
        db_session.add(contract)
        db_session.flush()

        result = compute_purchase_actions(db_session)

        soon = [a for a in result["actions"] if a["type"] == "renewal_soon"]
        assert len(soon) == 1
        assert soon[0]["severity"] == "orange"
        assert soon[0]["priority"] == 70

    def test_renewal_plan_within_90_days(self, db_session):
        """Contrat dont le préavis est dans 61-90 jours → renewal_plan (yellow)."""
        from services.purchase_actions_engine import compute_purchase_actions

        site = db_session.query(Site).first()
        # Notice deadline dans 75 jours → renewal_plan
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Total",
            end_date=date.today() + timedelta(days=165),  # 165 - 90 = 75 jours
            notice_period_days=90,
        )
        db_session.add(contract)
        db_session.flush()

        result = compute_purchase_actions(db_session)

        plan = [a for a in result["actions"] if a["type"] == "renewal_plan"]
        assert len(plan) == 1
        assert plan[0]["severity"] == "yellow"
        assert plan[0]["priority"] == 40

    def test_no_action_if_notice_far(self, db_session):
        """Contrat dont le préavis est dans > 90 jours → aucune action."""
        from services.purchase_actions_engine import compute_purchase_actions

        site = db_session.query(Site).first()
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Alpiq",
            end_date=date.today() + timedelta(days=365),
            notice_period_days=90,
        )
        db_session.add(contract)
        db_session.flush()

        result = compute_purchase_actions(db_session)

        assert result["total_actions"] == 0

    def test_expired_contract_skipped(self, db_session):
        """Contrat déjà expiré → ignoré (pas d'action)."""
        from services.purchase_actions_engine import compute_purchase_actions

        site = db_session.query(Site).first()
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Expired Corp",
            end_date=date.today() - timedelta(days=10),
            notice_period_days=90,
        )
        db_session.add(contract)
        db_session.flush()

        result = compute_purchase_actions(db_session)

        assert result["total_actions"] == 0


class TestScenarioActions:
    """Tests des actions strategy_switch et accept_reco."""

    def _seed_scenario(self, db_session, savings_pct):
        site = db_session.query(Site).first()
        assumption = PurchaseAssumptionSet(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            volume_kwh_an=500000,
        )
        db_session.add(assumption)
        db_session.flush()

        result = PurchaseScenarioResult(
            run_id="test-run-1",
            assumption_set_id=assumption.id,
            strategy=PurchaseStrategy.FIXE,
            price_eur_per_kwh=0.15,
            total_annual_eur=75000,
            risk_score=20,
            savings_vs_current_pct=savings_pct,
            is_recommended=True,
            reco_status=PurchaseRecoStatus.DRAFT,
        )
        db_session.add(result)
        db_session.flush()
        return result

    def test_strategy_switch_if_savings_above_5pct(self, db_session):
        """Scénario recommandé avec > 5% d'économie → strategy_switch (blue)."""
        from services.purchase_actions_engine import compute_purchase_actions

        self._seed_scenario(db_session, savings_pct=12.0)

        result = compute_purchase_actions(db_session)

        switch = [a for a in result["actions"] if a["type"] == "strategy_switch"]
        assert len(switch) == 1
        assert switch[0]["severity"] == "blue"
        assert switch[0]["priority"] == 60
        assert "12" in switch[0]["label"]  # savings_pct dans le label

    def test_accept_reco_if_savings_below_5pct(self, db_session):
        """Scénario recommandé avec <= 5% → accept_reco (blue)."""
        from services.purchase_actions_engine import compute_purchase_actions

        self._seed_scenario(db_session, savings_pct=3.0)

        result = compute_purchase_actions(db_session)

        accept = [a for a in result["actions"] if a["type"] == "accept_reco"]
        assert len(accept) == 1
        assert accept[0]["severity"] == "blue"
        assert accept[0]["priority"] == 50

    def test_gain_potentiel_computed(self, db_session):
        """Le gain potentiel EUR est calculé correctement."""
        from services.purchase_actions_engine import compute_purchase_actions

        self._seed_scenario(db_session, savings_pct=10.0)

        result = compute_purchase_actions(db_session)

        # total_annual_eur=75000, savings=10% → current_cost=75000/(1-0.10)=83333, gain=8333
        assert result["gain_potentiel_eur"] > 0
        assert result["gain_potentiel_eur"] == pytest.approx(8333.33, abs=1)


class TestPriorityAndOrdering:
    """Tests de tri et structure de sortie."""

    def test_actions_sorted_by_priority_desc(self, db_session):
        """Les actions sont triées par priorité décroissante."""
        from services.purchase_actions_engine import compute_purchase_actions

        site = db_session.query(Site).first()

        # Créer 2 contrats : un urgent (prio 100) + un plan (prio 40)
        db_session.add(EnergyContract(
            site_id=site.id, energy_type=BillingEnergyType.ELEC,
            supplier_name="Urgent", end_date=date.today() + timedelta(days=30),
            notice_period_days=90,
        ))
        db_session.add(EnergyContract(
            site_id=site.id, energy_type=BillingEnergyType.ELEC,
            supplier_name="Plan", end_date=date.today() + timedelta(days=165),
            notice_period_days=90,
        ))
        db_session.flush()

        result = compute_purchase_actions(db_session)

        assert result["total_actions"] == 2
        assert result["actions"][0]["priority"] >= result["actions"][1]["priority"]
        assert result["actions"][0]["rank"] == 1
        assert result["actions"][1]["rank"] == 2

    def test_empty_org_returns_empty(self, db_session):
        """Org sans sites → aucune action."""
        from services.purchase_actions_engine import compute_purchase_actions

        result = compute_purchase_actions(db_session, org_id=99999)

        assert result["total_actions"] == 0
        assert result["actions"] == []
        assert result["gain_potentiel_eur"] == 0
