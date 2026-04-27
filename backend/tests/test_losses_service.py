"""Sprint 2 Vague B ét7' — Bill-Intel losses_service.

Tests `losses_service.compute_billing_losses_summary` + helpers de format.
Garanties (memory feedback chiffres fiables/vérifiables/simples 27/04) :

  1. **Fiable** : reproductibilité (même DB → même output), pureté
     fonctionnelle (pas de side-effect), edge cases dégradés gracieusement.
  2. **Vérifiable** : provenance complète (source, confidence, sample_size,
     methodology) renvoyée pour les 3 mesures.
  3. **Simple** : format helpers `fmt_payback_human` / `fmt_recovery_rate`
     produisent des sorties intuitives non-sachant.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, EntiteJuridique, Organisation, Portefeuille, Site
from models.billing_models import BillingInsight
from models.enums import InsightStatus
from services.billing.losses_service import (
    BillingLossesSummary,
    LossesProvenance,
    compute_billing_losses_summary,
    fmt_payback_human,
    fmt_recovery_rate,
)


# ── Fixture DB en mémoire ────────────────────────────────────────────


@pytest.fixture
def db():
    """SQLite in-memory pour tests isolés et reproductibles."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def org_with_site(db):
    """Org → EJ → Portefeuille → Site canoniques pour scope billing."""
    org = Organisation(nom="Test Org")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom="Test EJ", siren="123456789", organisation_id=org.id)
    db.add(ej)
    db.flush()
    portefeuille = Portefeuille(nom="Test Portefeuille", entite_juridique_id=ej.id)
    db.add(portefeuille)
    db.flush()
    site = Site(nom="Test Site", type="bureau", portefeuille_id=portefeuille.id)
    db.add(site)
    db.commit()
    return {"org_id": org.id, "site_id": site.id}


def _make_insight(
    db,
    site_id: int,
    *,
    status: InsightStatus,
    loss_eur: float,
    type_: str = "shadow_gap",
    severity: str = "high",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    message: str = "Test insight",
) -> BillingInsight:
    """Helper de création d'insight avec dates contrôlables (payback)."""
    insight = BillingInsight(
        site_id=site_id,
        type=type_,
        severity=severity,
        message=message,
        estimated_loss_eur=loss_eur,
        insight_status=status,
    )
    db.add(insight)
    db.flush()
    if created_at is not None:
        insight.created_at = created_at
    if updated_at is not None:
        insight.updated_at = updated_at
    db.commit()
    return insight


# ── Tests compute_billing_losses_summary ─────────────────────────────


def test_empty_org_returns_zero_summary(db, org_with_site):
    """Edge case : org sans aucun insight — toutes les agrégations à 0."""
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    assert summary.nb_open == 0
    assert summary.nb_ack == 0
    assert summary.nb_resolved == 0
    assert summary.perte_open_eur == 0.0
    assert summary.contestation_eur == 0.0
    assert summary.reclaim_ytd_eur == 0.0
    assert summary.payback_avg_days is None
    assert summary.recovery_rate_pct is None


def test_aggregates_open_insights_correctly(db, org_with_site):
    """3 insights open → somme correcte + nb correct + provenance source."""
    _make_insight(db, org_with_site["site_id"], status=InsightStatus.OPEN, loss_eur=1500.0)
    _make_insight(db, org_with_site["site_id"], status=InsightStatus.OPEN, loss_eur=2500.0)
    _make_insight(db, org_with_site["site_id"], status=InsightStatus.OPEN, loss_eur=1000.0)
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    assert summary.nb_open == 3
    assert summary.perte_open_eur == 5000.0
    assert summary.losses_provenance.source == "Bill-Intel shadow billing v4.2"
    assert summary.losses_provenance.sample_size == 3


def test_payback_avg_days_computed_from_resolved_dates(db, org_with_site):
    """Payback moyen = moyenne arithmétique des délais résolution."""
    now = datetime.now(timezone.utc)
    # 3 insights résolus : 10j, 20j, 30j → moyenne 20j
    for days in (10, 20, 30):
        _make_insight(
            db,
            org_with_site["site_id"],
            status=InsightStatus.RESOLVED,
            loss_eur=1000.0,
            created_at=now - timedelta(days=days),
            updated_at=now,
        )
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    assert summary.nb_resolved == 3
    assert summary.payback_avg_days == pytest.approx(20.0)


def test_payback_confidence_low_when_sample_under_3(db, org_with_site):
    """Règle d'or chiffres : confidence dégradée LOW quand <3 échantillons."""
    now = datetime.now(timezone.utc)
    _make_insight(
        db,
        org_with_site["site_id"],
        status=InsightStatus.RESOLVED,
        loss_eur=500.0,
        created_at=now - timedelta(days=14),
        updated_at=now,
    )
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    assert summary.payback_avg_days == pytest.approx(14.0)
    # 1 sample only → LOW confidence
    assert summary.payback_provenance.confidence == "low"
    assert summary.payback_provenance.sample_size == 1


def test_payback_confidence_medium_3_to_9_samples(db, org_with_site):
    """3 ≤ sample < 10 → MEDIUM confidence."""
    now = datetime.now(timezone.utc)
    for _ in range(5):
        _make_insight(
            db,
            org_with_site["site_id"],
            status=InsightStatus.RESOLVED,
            loss_eur=500.0,
            created_at=now - timedelta(days=14),
            updated_at=now,
        )
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    assert summary.payback_provenance.confidence == "medium"
    assert summary.payback_provenance.sample_size == 5


def test_payback_confidence_high_when_10_plus_samples(db, org_with_site):
    """≥10 samples → HIGH confidence."""
    now = datetime.now(timezone.utc)
    for _ in range(12):
        _make_insight(
            db,
            org_with_site["site_id"],
            status=InsightStatus.RESOLVED,
            loss_eur=500.0,
            created_at=now - timedelta(days=14),
            updated_at=now,
        )
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    assert summary.payback_provenance.confidence == "high"


def test_recovery_rate_computed_correctly(db, org_with_site):
    """Recovery rate = reclaim_ytd / (reclaim_ytd + open + ack) × 100."""
    now = datetime.now(timezone.utc)
    # 2000 € récupérés YTD
    _make_insight(
        db,
        org_with_site["site_id"],
        status=InsightStatus.RESOLVED,
        loss_eur=2000.0,
        created_at=now - timedelta(days=30),
        updated_at=now - timedelta(days=10),
    )
    # 3000 € encore ouverts
    _make_insight(db, org_with_site["site_id"], status=InsightStatus.OPEN, loss_eur=3000.0)
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    assert summary.recovery_rate_pct == pytest.approx(40.0)  # 2000 / 5000


def test_recovery_rate_includes_ack_in_denominator(db, org_with_site):
    """ack (contestation en cours) inclus dans le dénominateur (P2 /simplify ét7').

    Méthodologie : le taux de récupération mesure le succès du processus
    complet — open + ack + resolved sont toutes des anomalies actionnées.
    Exclure ack diluerait le ratio "succès".
    """
    now = datetime.now(timezone.utc)
    _make_insight(
        db,
        org_with_site["site_id"],
        status=InsightStatus.RESOLVED,
        loss_eur=1000.0,
        created_at=now - timedelta(days=20),
        updated_at=now - timedelta(days=5),
    )
    _make_insight(db, org_with_site["site_id"], status=InsightStatus.OPEN, loss_eur=2000.0)
    _make_insight(db, org_with_site["site_id"], status=InsightStatus.ACK, loss_eur=2000.0)
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    # 1000 / (1000 + 2000 + 2000) = 20%
    assert summary.recovery_rate_pct == pytest.approx(20.0)


def test_recovery_rate_none_when_no_data(db, org_with_site):
    """Recovery rate = None si dénominateur zéro (anti-division/0)."""
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    assert summary.recovery_rate_pct is None


def test_resolved_outside_ytd_not_counted_in_reclaim(db, org_with_site):
    """Insight résolu l'an passé ne compte PAS dans reclaim_ytd_eur."""
    now = datetime.now(timezone.utc)
    last_year_dec = datetime(now.year - 1, 12, 15, tzinfo=timezone.utc)
    _make_insight(
        db,
        org_with_site["site_id"],
        status=InsightStatus.RESOLVED,
        loss_eur=999.0,
        created_at=last_year_dec - timedelta(days=20),
        updated_at=last_year_dec,
    )
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    assert summary.reclaim_ytd_eur == 0.0


def test_reproducibility_same_db_same_output(db, org_with_site):
    """Règle d'or : même état DB → même résultat (déterminisme)."""
    now = datetime.now(timezone.utc)
    _make_insight(db, org_with_site["site_id"], status=InsightStatus.OPEN, loss_eur=1234.56)
    _make_insight(
        db,
        org_with_site["site_id"],
        status=InsightStatus.RESOLVED,
        loss_eur=789.12,
        created_at=now - timedelta(days=15),
        updated_at=now,
    )
    s1 = compute_billing_losses_summary(db, org_with_site["org_id"])
    s2 = compute_billing_losses_summary(db, org_with_site["org_id"])
    assert s1.perte_open_eur == s2.perte_open_eur
    assert s1.reclaim_ytd_eur == s2.reclaim_ytd_eur
    assert s1.payback_avg_days == s2.payback_avg_days
    assert s1.recovery_rate_pct == s2.recovery_rate_pct


def test_accepts_pre_loaded_insights_skips_query(db, org_with_site):
    """P1 fix /simplify ét7' : si insights est fourni, pas de 2ᵉ query SQL.

    Le caller (narrative_generator) a déjà la liste pour les week-cards.
    On vérifie que le résultat est identique (même org, même data) quand
    on passe ou non `insights`.
    """
    now = datetime.now(timezone.utc)
    _make_insight(db, org_with_site["site_id"], status=InsightStatus.OPEN, loss_eur=1500.0)
    _make_insight(
        db,
        org_with_site["site_id"],
        status=InsightStatus.RESOLVED,
        loss_eur=2000.0,
        created_at=now - timedelta(days=10),
        updated_at=now,
    )
    # Sans insights : query interne
    s1 = compute_billing_losses_summary(db, org_with_site["org_id"])
    # Avec insights : skip query, reuse pré-chargé
    from models.billing_models import BillingInsight

    pre_loaded = db.query(BillingInsight).all()
    s2 = compute_billing_losses_summary(db, org_with_site["org_id"], insights=pre_loaded)
    assert s1.perte_open_eur == s2.perte_open_eur
    assert s1.reclaim_ytd_eur == s2.reclaim_ytd_eur
    assert s1.payback_avg_days == s2.payback_avg_days
    assert s1.recovery_rate_pct == s2.recovery_rate_pct
    assert s1.nb_open == s2.nb_open
    assert s1.nb_resolved == s2.nb_resolved


def test_org_isolation_no_cross_leak(db):
    """Multi-org : l'agrégation d'org A ne voit pas les insights d'org B."""
    org_a = Organisation(nom="Org A")
    org_b = Organisation(nom="Org B")
    db.add_all([org_a, org_b])
    db.flush()
    ej_a = EntiteJuridique(nom="EJ A", siren="111111111", organisation_id=org_a.id)
    ej_b = EntiteJuridique(nom="EJ B", siren="222222222", organisation_id=org_b.id)
    db.add_all([ej_a, ej_b])
    db.flush()
    p_a = Portefeuille(nom="P A", entite_juridique_id=ej_a.id)
    p_b = Portefeuille(nom="P B", entite_juridique_id=ej_b.id)
    db.add_all([p_a, p_b])
    db.flush()
    s_a = Site(nom="S A", type="bureau", portefeuille_id=p_a.id)
    s_b = Site(nom="S B", type="bureau", portefeuille_id=p_b.id)
    db.add_all([s_a, s_b])
    db.commit()
    _make_insight(db, s_a.id, status=InsightStatus.OPEN, loss_eur=1000.0)
    _make_insight(db, s_b.id, status=InsightStatus.OPEN, loss_eur=9999.0)
    summary_a = compute_billing_losses_summary(db, org_a.id)
    summary_b = compute_billing_losses_summary(db, org_b.id)
    assert summary_a.perte_open_eur == 1000.0
    assert summary_b.perte_open_eur == 9999.0
    assert summary_a.nb_open == 1
    assert summary_b.nb_open == 1


def test_provenance_methodology_explains_calculation(db, org_with_site):
    """Règle d'or vérifiable : methodology décrit la formule au non-sachant."""
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    assert "estimated_loss_eur" in summary.losses_provenance.methodology
    assert "Moyenne" in summary.payback_provenance.methodology
    assert "Reclaim YTD" in summary.recovery_provenance.methodology
    # computed_at est toujours renseigné
    assert isinstance(summary.losses_provenance.computed_at, datetime)


def test_returned_dataclass_is_frozen(db, org_with_site):
    """Pureté : BillingLossesSummary frozen → impossible à muter accidentellement."""
    summary = compute_billing_losses_summary(db, org_with_site["org_id"])
    with pytest.raises((AttributeError, Exception)):
        summary.nb_open = 999  # type: ignore[misc]


# ── Tests format helpers (règle d'or simple à comprendre) ───────────


@pytest.mark.parametrize(
    "days, expected",
    [
        (None, "—"),
        (0, "—"),
        (-5, "—"),
        (1, "1 jour"),  # singulier (P1 fix /simplify ét7')
        (2, "2 jours"),
        (15, "15 jours"),
        (29, "29 jours"),
        (30, "1.0 mois"),  # = exactement 1 mois → 1.0 (1 décimale, < 2 mois)
        (45, "1.5 mois"),  # 45/30 = 1.5
        (60, "2 mois"),  # ≥ 2 mois → entier
        (90, "3 mois"),
        (365, "1.0 an"),  # 365/30/12 ≈ 1.01 → 1.0 an (singulier)
        (730, "2.0 ans"),  # 2 ans → pluriel
    ],
)
def test_fmt_payback_human(days, expected):
    assert fmt_payback_human(days) == expected


@pytest.mark.parametrize(
    "rate, expected",
    [
        (None, "—"),
        (0, "0.0 %"),
        (5.4, "5.4 %"),  # < 10 → 1 décimale
        (9.99, "10.0 %"),  # arrondi avant comparaison < 10 → reste 1 décimale
        (10.0, "10 %"),  # ≥ 10 → entier
        (42.0, "42 %"),
        (99.5, "100 %"),  # arrondi standard
    ],
)
def test_fmt_recovery_rate(rate, expected):
    assert fmt_recovery_rate(rate) == expected


# ── Tests dataclass LossesProvenance ────────────────────────────────


def test_losses_provenance_is_frozen():
    p = LossesProvenance(
        source="test",
        confidence="high",
        sample_size=5,
        computed_at=datetime.now(timezone.utc),
        methodology="test",
    )
    with pytest.raises((AttributeError, Exception)):
        p.confidence = "low"  # type: ignore[misc]
