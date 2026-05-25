"""
Tests Cockpit P1 (2026-05-25) — cockpit_executive_narrative_service.

Couvre :
1. Structure du payload : executive_summary{kpis:5} + top_priorities (≤ 3).
2. Métadonnées doctrine §8.1 : chaque KPI expose source/formula/unit/period/scope.
3. Comptages cross-briques : surfact total = Σ insights ouverts ; actions
   ouvertes = COUNT(items lifecycle ≠ closed) ; sites = COUNT(périmètre).
4. Filtres : insights closed/false_positive exclus, actions CLOSED exclues.
5. CTA canoniques (doctrine §6.2) : /bill-intel, /conformite, /patrimoine
   uniquement — jamais de nouvelle route inventée.
6. Edge cases : org_id None, org sans données, max 3 priorités cap.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime, timezone

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
from services.executive_narrative_service import (  # noqa: E402
    compute_executive_narrative,
    compute_executive_summary,
    compute_top_priorities,
)


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


def _seed(
    db,
    *,
    n_sites=1,
    insights_open=0,
    insights_closed=0,
    loss_per_insight=100.0,
    actions_open=0,
    actions_closed=0,
):
    """Seed minimal : 1 org + N sites + insights + actions."""
    org = Organisation(nom="Org Exec", siren="222222222", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="222222222")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()

    sites = []
    for i in range(n_sites):
        s = Site(
            portefeuille_id=pf.id,
            nom=f"Site {i}",
            type=TypeSite.BUREAU,
            adresse="x",
            code_postal="75001",
            ville="Paris",
            actif=True,
        )
        db.add(s)
        sites.append(s)
    db.flush()

    if sites:
        ref_site = sites[0]

        def _insight(status, idx):
            contract = EnergyContract(
                site_id=ref_site.id,
                supplier_name="EDF",
                energy_type=BillingEnergyType.ELEC,
                start_date=date(2026, 1, 1),
                end_date=date(2027, 1, 1),
            )
            db.add(contract)
            db.flush()
            invoice = EnergyInvoice(
                site_id=ref_site.id,
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
            db.add(
                BillingInsight(
                    site_id=ref_site.id,
                    invoice_id=invoice.id,
                    type="shadow_gap",
                    severity="high",
                    message=f"Surfacturation {idx}",
                    estimated_loss_eur=loss_per_insight,
                    insight_status=status,
                )
            )

        for i in range(insights_open):
            _insight(InsightStatus.OPEN, f"open-{i}")
        for i in range(insights_closed):
            _insight(InsightStatus.RESOLVED, f"closed-{i}")

    for i in range(actions_open):
        db.add(
            ActionCenterItem(
                id=uuid.uuid4(),
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
    for i in range(actions_closed):
        db.add(
            ActionCenterItem(
                id=uuid.uuid4(),
                organisation_id=org.id,
                kind=Kind.ANOMALY.value,
                domain=Domain.FACTURATION.value,
                title=f"Action close {i}",
                description="x",
                lifecycle_state=LifecycleState.CLOSED.value,
                closed_at=datetime.now(timezone.utc),
                closure_reason=ClosureReason.RESOLVED.value,
                priority_bracket="P2",
                priority_score=50.0,
            )
        )

    db.commit()
    return org, sites


# ─── 1. Structure ──────────────────────────────────────────────────────


class TestStructure:
    def test_narrative_retourne_les_2_blocs(self, db):
        org, _ = _seed(db, n_sites=2, insights_open=1)
        out = compute_executive_narrative(db, org.id)
        assert "executive_summary" in out
        assert "top_priorities" in out
        assert isinstance(out["top_priorities"], list)
        assert isinstance(out["executive_summary"]["kpis"], list)

    def test_executive_summary_a_exactement_5_kpis(self, db):
        org, _ = _seed(db, n_sites=2)
        out = compute_executive_summary(db, org.id)
        assert len(out["kpis"]) == 5
        ids = {k["id"] for k in out["kpis"]}
        assert ids == {
            "score_conformite",
            "risque_financier_a_contester",
            "prochaine_echeance",
            "actions_ouvertes",
            "sites_dans_perimetre",
        }

    def test_chaque_kpi_a_metadata_doctrine_8_1(self, db):
        org, _ = _seed(db, n_sites=1, insights_open=1)
        out = compute_executive_summary(db, org.id)
        for kpi in out["kpis"]:
            assert "id" in kpi
            assert "label_fr" in kpi and kpi["label_fr"]
            assert "value" in kpi  # peut être None ; clé obligatoire
            assert "unit" in kpi and kpi["unit"]
            assert "source" in kpi and kpi["source"]
            assert "formula" in kpi and kpi["formula"]
            assert "period" in kpi and kpi["period"]
            assert "scope" in kpi and kpi["scope"]


# ─── 2. Comptages cross-briques ──────────────────────────────────────────


class TestComptagesCrossBriques:
    def test_sites_dans_perimetre_compte_org_actifs(self, db):
        org, _ = _seed(db, n_sites=4)
        out = compute_executive_summary(db, org.id)
        sites_kpi = next(k for k in out["kpis"] if k["id"] == "sites_dans_perimetre")
        assert sites_kpi["value"] == 4

    def test_surfact_somme_insights_ouverts(self, db):
        org, _ = _seed(db, n_sites=1, insights_open=3, loss_per_insight=420.50)
        out = compute_executive_summary(db, org.id)
        surfact = next(k for k in out["kpis"] if k["id"] == "risque_financier_a_contester")
        assert surfact["value"] == pytest.approx(3 * 420.50, abs=0.01)

    def test_insights_closed_exclus_du_surfact(self, db):
        org, _ = _seed(db, n_sites=1, insights_open=1, insights_closed=5, loss_per_insight=100.0)
        out = compute_executive_summary(db, org.id)
        surfact = next(k for k in out["kpis"] if k["id"] == "risque_financier_a_contester")
        assert surfact["value"] == pytest.approx(100.0, abs=0.01), (
            "Insights RESOLVED ne doivent pas compter dans la surfacturation à contester"
        )

    def test_actions_ouvertes_exclut_closed(self, db):
        org, _ = _seed(db, n_sites=1, actions_open=7, actions_closed=4)
        out = compute_executive_summary(db, org.id)
        actions = next(k for k in out["kpis"] if k["id"] == "actions_ouvertes")
        assert actions["value"] == 7


# ─── 3. Top priorities ──────────────────────────────────────────────────


class TestTopPriorities:
    def test_top_priority_billing_si_insight_ouvert(self, db):
        org, _ = _seed(db, n_sites=1, insights_open=2, loss_per_insight=999.0)
        priorities = compute_top_priorities(db, org.id)
        assert len(priorities) >= 1
        top = priorities[0]
        assert top["priority_rank"] == 1
        assert top["impact"]["unit"] == "€"
        assert top["impact"]["value"] == pytest.approx(999.0, abs=0.01)
        assert top["cta"]["link"].startswith("/bill-intel")
        assert top["why_fr"]  # justification présente

    def test_priorites_capees_a_3(self, db):
        # Même avec beaucoup d'insights/actions, on ne dépasse jamais 3
        org, _ = _seed(db, n_sites=2, insights_open=10, actions_open=20)
        priorities = compute_top_priorities(db, org.id)
        assert len(priorities) <= 3

    def test_priorites_pas_de_billing_si_aucun_insight(self, db):
        # Sans insight ouvert, pas de priorité "Surfacturation à contester"
        # (anti-bruit : on ne fabrique pas une priorité Billing fictive).
        org, _ = _seed(db, n_sites=2, insights_open=0)
        priorities = compute_top_priorities(db, org.id)
        billing_priorities = [p for p in priorities if p["cta"]["link"].startswith("/bill-intel")]
        assert billing_priorities == []

    def test_cta_links_doctrine_6_2_routes_existantes(self, db):
        # Toutes les CTA doivent pointer vers une page hub existante :
        # /bill-intel, /conformite, /patrimoine, /centre-action.
        org, _ = _seed(db, n_sites=1, insights_open=1)
        priorities = compute_top_priorities(db, org.id)
        for p in priorities:
            link = p["cta"]["link"]
            assert any(
                link.startswith(route) for route in ("/bill-intel", "/conformite", "/patrimoine", "/centre-action")
            ), f"CTA link {link} ne pointe pas vers une page hub canonique (doctrine §6.2)"


# ─── 4. Edge cases ──────────────────────────────────────────────────────


class TestEdgeCases:
    def test_org_id_none_retourne_payload_vide_safe(self, db):
        out = compute_executive_narrative(db, None)
        assert out["executive_summary"]["kpis"] == []
        assert out["top_priorities"] == []

    def test_score_conformite_none_si_aucun_site_eval(self, db):
        org, _ = _seed(db, n_sites=0)
        out = compute_executive_summary(db, org.id)
        score = next(k for k in out["kpis"] if k["id"] == "score_conformite")
        # avg_score 0 ou non calculable → value None + sub "non_applicable"
        assert score["value"] is None
        assert "non_applicable" in (score.get("sub_label_fr") or "")


# ─── 5. Cockpit P1.5 polish — Pourquoi cette priorité + ordering ────────


class TestP15PriorityPolish:
    def test_chaque_priorite_expose_source_et_action_recommandee(self, db):
        # Le bloc « Pourquoi cette priorité ? » a besoin de source_fr +
        # action_recommandee_fr sur chaque priorité retournée.
        org, _ = _seed(db, n_sites=1, insights_open=1, loss_per_insight=500.0)
        priorities = compute_top_priorities(db, org.id)
        assert priorities, "Le seed doit produire au moins 1 priorité billing"
        for p in priorities:
            assert "source_fr" in p and p["source_fr"], f"source_fr manquant : {p}"
            assert "action_recommandee_fr" in p and p["action_recommandee_fr"], f"action_recommandee_fr manquant : {p}"
            assert "category" in p and p["category"], f"category manquant : {p}"
            assert "perimetre_fr" in p and p["perimetre_fr"], f"perimetre_fr manquant : {p}"

    def test_ordering_canonique_reglementaire_urgent_avant_billing(self, db):
        # Quand on a billing + compliance urgent simultanément, le compliance
        # urgent (deadline < 30 j) doit ranker avant billing.
        from unittest.mock import patch
        import services.executive_narrative_service as svc

        org, _ = _seed(db, n_sites=1, insights_open=1, loss_per_insight=999.0)
        fake_deadline = {"id": "DT", "label": "OPERAT 2026", "days_remaining": 12, "deadline": "2026-06-06"}
        with patch.object(svc, "_compute_next_deadline", return_value=fake_deadline):
            priorities = compute_top_priorities(db, org.id)
        cats = [p["category"] for p in priorities]
        assert cats[0] == "regulatory_urgent", f"Le compliance urgent (<30j) doit ranker en 1er, got {cats}"
        assert priorities[0]["priority_rank"] == 1

    def test_ordering_canonique_billing_avant_patrimoine(self, db):
        # Sans compliance, billing (€) doit ranker avant patrimoine.
        from unittest.mock import patch
        import services.executive_narrative_service as svc

        org, _ = _seed(db, n_sites=2, insights_open=1, loss_per_insight=500.0)
        with patch.object(svc, "_compute_next_deadline", return_value=None):
            priorities = compute_top_priorities(db, org.id)
        cats = [p["category"] for p in priorities]
        if "billing" in cats and "patrimoine" in cats:
            assert cats.index("billing") < cats.index("patrimoine"), f"Billing doit ranker avant patrimoine, got {cats}"

    def test_priorites_cap_strict_3_meme_si_5_categories_remplies(self, db):
        # Même si on a 1 candidate par catégorie (5 au total), max 3 sortent.
        org, _ = _seed(db, n_sites=2, insights_open=1, actions_open=3, loss_per_insight=100.0)
        priorities = compute_top_priorities(db, org.id)
        assert len(priorities) <= 3
        ranks = [p["priority_rank"] for p in priorities]
        assert ranks == list(range(1, len(ranks) + 1)), f"Ranks doivent être séquentiels 1..N, got {ranks}"
