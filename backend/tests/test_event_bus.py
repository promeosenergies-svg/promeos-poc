"""Sprint 2 Vague C ét11 — chantier α moteur événements MVP.

Tests `services.event_bus.compute_events` + détecteur pilote
`compliance_deadline_detector`. Garanties (doctrine v1.1 §10 + §14 Test 6) :

1. **Schéma §10** : chaque event respecte la dataclass `SolEventCard`
   (event_type / severity / impact / source / action / linked_assets).
2. **Test §14 T6 J vs J+1** : si l'état DB change (non_conformes 0→1),
   `compute_events` retourne un événement nouveau (vs version statique
   qui restait identique J et J+1).
3. **Test §6 P6 produit pousse** : critical avant warning avant info
   dans le tri résultat.
4. **Source canonique constants** : `DT_PENALTY_EUR=7500` consommée
   depuis `backend/doctrine/constants.py` (test sentinel rappel).
5. **Conversion rétro-compat** : `to_narrative_week_cards` mappe
   correctement severity → type (critical/warning → todo, watch → watch,
   info → good_news) + impact € → impact_eur.
"""

from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from doctrine.constants import DT_PENALTY_AT_RISK_EUR, DT_PENALTY_EUR
from models import (
    Base,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
)
from models.enums import StatutConformite
from services.event_bus import (
    SolEventCard,
    compute_events,
    to_narrative_week_cards,
)
from services.event_bus.detectors import compliance_deadline_detector
from services.event_bus.types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventMitigation,
    EventSource,
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
def org_with_sites(db):
    """Org avec 3 sites : 1 conforme, 1 non-conforme, 1 à risque."""
    org = Organisation(nom="Test Org")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom="Test EJ", siren="123456789", organisation_id=org.id)
    db.add(ej)
    db.flush()
    portefeuille = Portefeuille(nom="Test Portefeuille", entite_juridique_id=ej.id)
    db.add(portefeuille)
    db.flush()

    sites = [
        Site(
            nom=f"Site {i}",
            type="bureau",
            portefeuille_id=portefeuille.id,
            statut_decret_tertiaire=statut,
        )
        for i, statut in enumerate(
            [
                StatutConformite.CONFORME,
                StatutConformite.NON_CONFORME,
                StatutConformite.A_RISQUE,
            ]
        )
    ]
    db.add_all(sites)
    db.commit()
    return {"org_id": org.id}


# ── Tests SolEventCard schema (§10) ─────────────────────────────────


def test_sol_event_card_is_frozen():
    """SolEventCard est une frozen dataclass — pas de mutation post-création."""
    from datetime import datetime, timezone

    event = SolEventCard(
        id="test:1",
        event_type="compliance_deadline",
        severity="critical",
        title="Test",
        narrative="Test narrative",
        impact=EventImpact(value=1000.0, unit="€", period="year"),
        source=EventSource(
            system="RegOps",
            last_updated_at=datetime.now(timezone.utc),
            confidence="high",
        ),
        action=EventAction(label="Voir", route="/test", owner_role="DAF"),
        linked_assets=EventLinkedAssets(org_id=1),
    )
    with pytest.raises((AttributeError, Exception)):
        event.severity = "info"  # type: ignore[misc]


def test_sol_event_card_to_dict_serialises_datetime():
    """to_dict() convertit datetime en ISO string (JSON-safe)."""
    from datetime import datetime, timezone

    now = datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc)
    event = SolEventCard(
        id="test:1",
        event_type="compliance_deadline",
        severity="info",
        title="Test",
        narrative="Test",
        impact=EventImpact(value=None, unit="€", period="year"),
        source=EventSource(system="RegOps", last_updated_at=now, confidence="high"),
        action=EventAction(label="Voir", route="/test"),
        linked_assets=EventLinkedAssets(org_id=1),
    )
    d = event.to_dict()
    assert d["source"]["last_updated_at"] == "2026-04-27T12:00:00+00:00"
    assert d["impact"]["value"] is None  # value=None autorisé §6 P13


# ── Tests détecteur compliance_deadline (§10 + constants doctrine) ───


def test_detector_emits_critical_for_non_conforme(db, org_with_sites):
    """1 site non-conforme → 1 événement critical avec impact = DT_PENALTY_EUR."""
    events = compliance_deadline_detector.detect(db, org_with_sites["org_id"])
    critical = [e for e in events if e.severity == "critical"]
    assert len(critical) == 1
    assert critical[0].event_type == "compliance_deadline"
    assert critical[0].impact.value == float(DT_PENALTY_EUR)  # = 7500
    assert critical[0].impact.unit == "€"
    assert critical[0].source.system == "RegOps"
    assert critical[0].source.confidence == "high"
    assert critical[0].action.route == "/conformite"
    assert critical[0].action.owner_role == "DAF"


def test_detector_emits_warning_for_a_risque(db, org_with_sites):
    """1 site à risque → 1 événement warning avec impact = DT_PENALTY_AT_RISK_EUR."""
    events = compliance_deadline_detector.detect(db, org_with_sites["org_id"])
    warning = [e for e in events if e.severity == "warning"]
    assert len(warning) == 1
    assert warning[0].impact.value == float(DT_PENALTY_AT_RISK_EUR)  # = 3750


def test_detector_linked_assets_filtered_by_statut(db, org_with_sites):
    """Doctrine §10 « quel périmètre est concerné ? » — linked_assets.site_ids
    contient SEULEMENT les sites du statut concerné (pas tous les sites org).

    P1 fix /simplify ét11 : avant, le critical citait TOUS les sites org
    (incluant conformes) → violation §10. Désormais filtré par statut réel.
    """
    events = compliance_deadline_detector.detect(db, org_with_sites["org_id"])
    critical = next(e for e in events if e.severity == "critical")
    warning = next(e for e in events if e.severity == "warning")
    # Org_with_sites a 3 sites : 1 conforme + 1 non-conforme + 1 à risque
    # critical doit citer 1 seul site (le non-conforme), pas 3
    assert len(critical.linked_assets.site_ids) == 1
    # warning doit citer 1 seul site (le à risque), pas 3
    assert len(warning.linked_assets.site_ids) == 1
    # Les 2 sites cités sont distincts (statuts différents)
    assert critical.linked_assets.site_ids != warning.linked_assets.site_ids


def test_detector_uses_constants_canonical(db, org_with_sites):
    """Vérifie que la pénalité provient de constants.py (pas hardcoded)."""
    events = compliance_deadline_detector.detect(db, org_with_sites["org_id"])
    critical = next(e for e in events if e.severity == "critical")
    # Si DT_PENALTY_EUR change, ce test casse — preuve que la source est canonique.
    assert critical.impact.value == DT_PENALTY_EUR
    # P1 fix /simplify ét11 : utiliser str(DT_PENALTY_EUR) brut au lieu d'un
    # format avec séparateur millier (locale-dependent : "7,500" en C/EN,
    # "7 500" en fr_FR). Le test devient indépendant de la locale CI.
    assert str(DT_PENALTY_EUR) in critical.narrative or "7 500" in critical.narrative


def test_detector_emits_nothing_when_all_conforme(db):
    """Org sans site non-conforme ni à risque → liste vide ou seul info."""
    org = Organisation(nom="Conforme Org")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom="EJ", siren="111111111", organisation_id=org.id)
    db.add(ej)
    db.flush()
    p = Portefeuille(nom="P", entite_juridique_id=ej.id)
    db.add(p)
    db.flush()
    db.add(Site(nom="S", type="bureau", portefeuille_id=p.id, statut_decret_tertiaire=StatutConformite.CONFORME))
    db.commit()

    events = compliance_deadline_detector.detect(db, org.id)
    # Pas de critical/warning — au plus un info (good_news) ou rien
    assert all(e.severity in ("info",) for e in events)


# ── Test §14 T6 J vs J+1 (cardinal doctrine v1.1) ───────────────────


def test_j_vs_j1_events_change_when_data_change(db, org_with_sites):
    """Doctrine §14 T6 — si l'état change, l'écran change.

    Si on rend un site supplémentaire non-conforme, le nouveau compute_events
    doit refléter le changement (impact différent). Ancien comportement
    statique pré-α : impact identique J et J+1 quel que soit l'état réel.
    """
    org_id = org_with_sites["org_id"]
    events_before = compute_events(db, org_id)
    critical_before = next(e for e in events_before if e.severity == "critical")
    impact_before = critical_before.impact.value

    # Rend un site supplémentaire non-conforme (le 1er site était CONFORME)
    site_to_flip = db.query(Site).filter(Site.statut_decret_tertiaire == StatutConformite.CONFORME).first()
    site_to_flip.statut_decret_tertiaire = StatutConformite.NON_CONFORME
    db.commit()

    events_after = compute_events(db, org_id)
    critical_after = next(e for e in events_after if e.severity == "critical")
    impact_after = critical_after.impact.value

    # T6 PASS : nouveau état → nouveau impact (vs ancienne behaviour statique)
    assert impact_after == 2 * impact_before  # 2 sites non-conformes vs 1


# ── Test §6 P6 tri severity (critical d'abord) ──────────────────────


def test_compute_events_sorts_by_severity_critical_first(db, org_with_sites):
    """Tri stable : critical → warning → watch → info."""
    events = compute_events(db, org_with_sites["org_id"])
    severities = [e.severity for e in events]
    # Au minimum critical avant warning
    if "critical" in severities and "warning" in severities:
        assert severities.index("critical") < severities.index("warning")


# ── Test rétro-compat to_narrative_week_cards ───────────────────────


def test_to_narrative_week_cards_maps_severity_to_type(db, org_with_sites):
    """Mapping : critical/warning → todo, watch → watch, info → good_news."""
    events = compute_events(db, org_with_sites["org_id"])
    cards = to_narrative_week_cards(events)
    # Au moins 1 critical → todo + 1 warning → todo
    types = [c.type for c in cards]
    assert types.count("todo") >= 2  # 1 critical + 1 warning


def test_to_narrative_week_cards_preserves_eur_impact(db, org_with_sites):
    """impact.value (unit=€) → impact_eur dans NarrativeWeekCard."""
    events = compute_events(db, org_with_sites["org_id"])
    cards = to_narrative_week_cards(events)
    # Le critical a impact_eur = DT_PENALTY_EUR
    todo_card = next(c for c in cards if c.type == "todo")
    assert todo_card.impact_eur is not None
    assert todo_card.impact_eur >= DT_PENALTY_AT_RISK_EUR  # au moins 3750


def test_to_narrative_week_cards_preserves_route(db, org_with_sites):
    """action.route → cta_path."""
    events = compute_events(db, org_with_sites["org_id"])
    cards = to_narrative_week_cards(events)
    routes = {c.cta_path for c in cards if c.cta_path}
    assert "/conformite" in routes


# ── Test isolation org ──────────────────────────────────────────────


# ── Sprint 2 Vague C ét11bis : Protocol + freshness + mitigation ────


def test_detector_module_satisfies_event_detector_protocol():
    """Vérifie que les modules détecteurs respectent le Protocol structurel."""
    from services.event_bus.detectors import DETECTORS, EventDetector

    assert len(DETECTORS) >= 1
    for detector in DETECTORS:
        assert isinstance(detector, EventDetector), (
            f"Détecteur {detector} ne respecte pas le Protocol EventDetector "
            "— vérifier signature `detect(db, org_id) -> list[SolEventCard]`."
        )


def test_event_source_freshness_status_default_fresh():
    """EventSource.freshness_status défaut = 'fresh' pour rétro-compat ét11."""
    from datetime import datetime, timezone

    src = EventSource(
        system="RegOps",
        last_updated_at=datetime.now(timezone.utc),
        confidence="high",
    )
    # Pas de freshness_status passé → défaut 'fresh'
    assert src.freshness_status == "fresh"


def test_event_source_freshness_status_demo_seed():
    """Doctrine §7.2 : statut 'demo' pour données seed (badge UI obligatoire)."""
    from datetime import datetime, timezone

    src = EventSource(
        system="manual",
        last_updated_at=datetime.now(timezone.utc),
        confidence="low",
        freshness_status="demo",
    )
    assert src.freshness_status == "demo"


def test_event_impact_mitigation_optional():
    """EventImpact.mitigation optionnel — backward-compat ét11."""
    impact = EventImpact(value=10000.0, unit="€", period="year")
    assert impact.mitigation is None


def test_event_impact_mitigation_full():
    """EventMitigation : capex + payback + npv pour CFO arbitrage."""
    mitigation = EventMitigation(
        capex_eur=50000.0,
        payback_months=18,
        npv_eur=120000.0,
        npv_horizon_year=2030,
    )
    impact = EventImpact(
        value=15000.0,
        unit="€",
        period="year",
        mitigation=mitigation,
    )
    assert impact.mitigation.capex_eur == 50000.0
    assert impact.mitigation.payback_months == 18


def test_compute_events_uses_detectors_registry(db, org_with_sites):
    """compute_events itère sur DETECTORS registry (ét11bis Architecture P0)."""
    from services.event_bus.detectors import DETECTORS

    # Simulation : si on retire le détecteur du registry, compute_events
    # doit retourner une liste vide.
    original_detectors = DETECTORS.copy()
    DETECTORS.clear()
    try:
        events = compute_events(db, org_with_sites["org_id"])
        assert events == []
    finally:
        DETECTORS.extend(original_detectors)


# ── Sprint 2 Vague C ét12b : consumption_drift_detector ───────────


def _seed_consumption_insight(db, site_id, *, type_="hors_horaires", loss_eur=3000, severity="high", delta_pct=None):
    """Helper : crée un ConsumptionInsight."""
    import json

    from models.consumption_insight import ConsumptionInsight

    metrics = {"delta_pct": delta_pct} if delta_pct is not None else None
    ci = ConsumptionInsight(
        site_id=site_id,
        type=type_,
        severity=severity,
        message=f"Test insight {type_}",
        estimated_loss_eur=loss_eur,
        estimated_loss_kwh=loss_eur * 5,  # arbitrary ratio
        metrics_json=json.dumps(metrics) if metrics else None,
    )
    db.add(ci)
    db.commit()


def test_consumption_drift_detector_emits_critical_above_5k(db, org_with_sites):
    """Perte ≥ 5 k€ → événement critical consumption_drift."""
    from services.event_bus.detectors import consumption_drift_detector

    site_id = db.query(Site).first().id
    _seed_consumption_insight(db, site_id, loss_eur=8_000, type_="derive")
    events = consumption_drift_detector.detect(db, org_with_sites["org_id"])
    critical = [e for e in events if e.severity == "critical"]
    assert len(critical) >= 1
    assert critical[0].event_type == "consumption_drift"
    assert critical[0].action.owner_role == "Energy Manager"


def test_consumption_drift_detector_top_2_only(db, org_with_sites):
    """Détecteur garde top 2 insights par perte décroissante (focus CFO €)."""
    from services.event_bus.detectors import consumption_drift_detector

    site_id = db.query(Site).first().id
    for loss in [500, 1500, 8000, 12000]:
        _seed_consumption_insight(db, site_id, loss_eur=loss, type_="hors_horaires")
    events = consumption_drift_detector.detect(db, org_with_sites["org_id"])
    drift_events = [e for e in events if e.event_type == "consumption_drift"]
    assert len(drift_events) == 2
    # Top 2 = 12000 et 8000
    values = sorted([e.impact.value for e in drift_events], reverse=True)
    assert values == [12_000.0, 8_000.0]


def test_consumption_drift_detector_uses_diagnostic_sot(db, org_with_sites):
    """Détecteur consomme consumption_diagnostic.get_insights_summary (SoT)."""
    import inspect

    from services.event_bus.detectors import consumption_drift_detector

    src = inspect.getsource(consumption_drift_detector.detect)
    assert "get_insights_summary" in src
    # Pas de query DB directe sur ConsumptionInsight
    assert "db.query(ConsumptionInsight" not in src


def test_consumption_drift_detector_includes_amplitude_when_available(db, org_with_sites):
    """Si delta_pct présent dans metrics, narrative l'expose (compromis EM levé)."""
    from services.event_bus.detectors import consumption_drift_detector

    site_id = db.query(Site).first().id
    _seed_consumption_insight(db, site_id, loss_eur=3000, type_="derive", delta_pct=23.4)
    events = consumption_drift_detector.detect(db, org_with_sites["org_id"])
    drift = next(e for e in events if e.event_type == "consumption_drift")
    assert "+23.4%" in drift.narrative or "23.4" in drift.narrative


def test_consumption_drift_detector_links_site(db, org_with_sites):
    """linked_assets.site_ids contient le site concerné (granularité §10)."""
    from services.event_bus.detectors import consumption_drift_detector

    site_id = db.query(Site).first().id
    _seed_consumption_insight(db, site_id, loss_eur=3000)
    events = consumption_drift_detector.detect(db, org_with_sites["org_id"])
    drift = next(e for e in events if e.event_type == "consumption_drift")
    assert drift.linked_assets.site_ids == [site_id]


# ── Sprint 2 Vague C ét12a : billing_anomaly_detector ──────────────


def _seed_billing_insights(db, site_id, *, open_eur, resolved_eur=0, resolved_payback_days=0):
    """Helper : crée des BillingInsight avec montants paramétrables."""
    from datetime import datetime, timedelta, timezone

    from models.billing_models import BillingInsight
    from models.enums import InsightStatus

    now = datetime.now(timezone.utc)
    if open_eur > 0:
        b1 = BillingInsight(
            site_id=site_id,
            type="shadow_gap",
            severity="high",
            message="Test open",
            estimated_loss_eur=open_eur,
            insight_status=InsightStatus.OPEN,
        )
        db.add(b1)
    if resolved_eur > 0:
        b2 = BillingInsight(
            site_id=site_id,
            type="shadow_gap",
            severity="high",
            message="Test resolved",
            estimated_loss_eur=resolved_eur,
            insight_status=InsightStatus.RESOLVED,
        )
        db.add(b2)
        db.flush()
        b2.created_at = now - timedelta(days=resolved_payback_days)
        b2.updated_at = now
    db.commit()


def test_billing_detector_emits_critical_above_10k(db, org_with_sites):
    """Pertes ouvertes ≥ 10 k€ → événement critical billing_anomaly."""
    from services.event_bus.detectors import billing_anomaly_detector

    site_id = db.query(Site).first().id
    _seed_billing_insights(db, site_id, open_eur=15_000)
    events = billing_anomaly_detector.detect(db, org_with_sites["org_id"])
    critical = [e for e in events if e.severity == "critical" and e.event_type == "billing_anomaly"]
    assert len(critical) == 1
    assert critical[0].impact.value == 15_000
    assert critical[0].impact.unit == "€"
    assert critical[0].action.route == "/bill-intel"
    assert critical[0].source.system == "invoice"


def test_billing_detector_emits_warning_2k_to_10k(db, org_with_sites):
    """Pertes ouvertes 2-10 k€ → warning billing_anomaly."""
    from services.event_bus.detectors import billing_anomaly_detector

    site_id = db.query(Site).first().id
    _seed_billing_insights(db, site_id, open_eur=5_000)
    events = billing_anomaly_detector.detect(db, org_with_sites["org_id"])
    warning = [e for e in events if e.severity == "warning"]
    assert len(warning) == 1


def test_billing_detector_emits_nothing_below_500(db, org_with_sites):
    """Pertes ouvertes < 500 € → aucun événement billing (densification fallback)."""
    from services.event_bus.detectors import billing_anomaly_detector

    site_id = db.query(Site).first().id
    _seed_billing_insights(db, site_id, open_eur=200)
    events = billing_anomaly_detector.detect(db, org_with_sites["org_id"])
    assert all(e.event_type != "billing_anomaly" or e.severity == "info" for e in events)


def test_billing_detector_emits_info_for_reclaim_ytd(db, org_with_sites):
    """Reclaim YTD ≥ 500 € → événement info (good_news : récupérations validées)."""
    from datetime import datetime, timedelta, timezone

    from services.event_bus.detectors import billing_anomaly_detector

    site_id = db.query(Site).first().id
    _seed_billing_insights(db, site_id, open_eur=0, resolved_eur=3_000, resolved_payback_days=10)
    events = billing_anomaly_detector.detect(db, org_with_sites["org_id"])
    info = [e for e in events if e.severity == "info" and e.event_type == "billing_anomaly"]
    assert len(info) == 1
    assert info[0].impact.value == 3_000


def test_billing_detector_includes_mitigation_with_payback(db, org_with_sites):
    """Si payback observé, EventMitigation rempli pour CFO arbitrage."""
    from services.event_bus.detectors import billing_anomaly_detector

    site_id = db.query(Site).first().id
    _seed_billing_insights(db, site_id, open_eur=15_000, resolved_eur=2_000, resolved_payback_days=14)
    events = billing_anomaly_detector.detect(db, org_with_sites["org_id"])
    critical = next(e for e in events if e.severity == "critical")
    assert critical.impact.mitigation is not None
    # 14 jours / 30 ≈ 0.46 mois → max(1, round(0.46)) = 1 mois
    assert critical.impact.mitigation.payback_months == 1
    assert critical.impact.mitigation.npv_eur == 15_000


def test_billing_detector_uses_losses_service_sot(db, org_with_sites):
    """Détecteur consomme losses_service (SoT canonique) — pas de SQL inline."""
    import inspect

    from services.event_bus.detectors import billing_anomaly_detector

    src = inspect.getsource(billing_anomaly_detector.detect)
    # Doit appeler compute_billing_losses_summary — pas de query directe BillingInsight
    assert "compute_billing_losses_summary" in src
    assert "db.query(BillingInsight" not in src


def test_org_isolation_no_cross_leak(db):
    """Multi-tenant : org A ne voit pas les événements d'org B."""
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
    db.add(
        Site(nom="S A", type="bureau", portefeuille_id=p_a.id, statut_decret_tertiaire=StatutConformite.NON_CONFORME)
    )
    db.add(Site(nom="S B", type="bureau", portefeuille_id=p_b.id, statut_decret_tertiaire=StatutConformite.CONFORME))
    db.commit()

    events_a = compute_events(db, org_a.id)
    events_b = compute_events(db, org_b.id)

    # Org A a un site non-conforme → critical
    assert any(e.severity == "critical" for e in events_a)
    # Org B n'a aucun site non-conforme/à risque → pas de critical/warning
    assert not any(e.severity in ("critical", "warning") for e in events_b)


# ── Vague C ét12c — Narrative expose events natifs §10 SolEventCard ───


def test_narrative_exposes_events_for_frontend(db, org_with_sites):
    """Vague C ét12c : `Narrative.events` est peuplé pour <SolEventCard> natif.

    Le frontend (Cockpit pilot) lit `briefing.events` pour rendre
    <SolEventStream> avec source/confidence/owner_role/mitigation visibles.
    Sans ce champ, Marie reste bloquée sur les week-cards condensées.
    """
    from services.narrative.narrative_generator import _build_cockpit_daily

    org_id = org_with_sites["org_id"]
    narr = _build_cockpit_daily(db, org_id, org_name="Org Test", sites_count=2)

    # Le champ existe et est un tuple (frozen — cohérent week_cards)
    assert hasattr(narr, "events")
    assert isinstance(narr.events, tuple)

    # to_dict() sérialise events[] avec le schéma JSON §10 attendu
    payload = narr.to_dict()
    assert "events" in payload
    assert isinstance(payload["events"], list)

    # Si au moins un événement est produit, vérifier la pile §10 complète
    if payload["events"]:
        first = payload["events"][0]
        assert {
            "id",
            "event_type",
            "severity",
            "title",
            "narrative",
            "impact",
            "source",
            "action",
            "linked_assets",
        }.issubset(first.keys())
        # source.last_updated_at sérialisé en ISO (cf SolEventCard.to_dict)
        assert isinstance(first["source"]["last_updated_at"], str)
        assert "T" in first["source"]["last_updated_at"]  # marker ISO datetime
        # freshness_status présent (défaut "fresh") — §7.2 statuts data
        assert first["source"]["freshness_status"] in ("fresh", "stale", "estimated", "incomplete", "demo")


# ── Vague C ét12d — corrections P0 audit ──────────────────────────────


def test_freshness_helper_demo_mode_overrides_ttl(monkeypatch):
    """ét12d P0-3 : DEMO_MODE=true → freshness_status='demo' quel que soit TTL."""
    from datetime import datetime, timezone

    from services.event_bus.freshness import compute_freshness

    monkeypatch.setenv("PROMEOS_DEMO_MODE", "true")
    # Donnée vieille de 1 an mais demo mode → "demo"
    old = datetime(2025, 1, 1, tzinfo=timezone.utc)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert compute_freshness("Enedis", old, now=now) == "demo"


def test_freshness_helper_ttl_thresholds(monkeypatch):
    """ét12d P0-3 : âge ≤ TTL → fresh, TTL < âge ≤ 3×TTL → stale, > 3×TTL → incomplete."""
    from datetime import datetime, timedelta, timezone

    from services.event_bus.freshness import compute_freshness

    monkeypatch.setenv("PROMEOS_DEMO_MODE", "false")
    now = datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc)

    # Enedis TTL = 24h : fresh à 12h, stale à 48h, incomplete à 80h
    assert compute_freshness("Enedis", now - timedelta(hours=12), now=now) == "fresh"
    assert compute_freshness("Enedis", now - timedelta(hours=48), now=now) == "stale"
    assert compute_freshness("Enedis", now - timedelta(hours=80), now=now) == "incomplete"

    # IoT TTL = 1h
    assert compute_freshness("IoT", now - timedelta(minutes=30), now=now) == "fresh"
    assert compute_freshness("IoT", now - timedelta(hours=2), now=now) == "stale"


def test_freshness_helper_estimated_short_circuits(monkeypatch):
    """ét12d P0-3 : is_estimated=True → 'estimated' indépendamment du TTL.

    Demo mode désactivé explicitement (sinon override prioritaire — comportement voulu).
    """
    from datetime import datetime, timezone

    from services.event_bus.freshness import compute_freshness

    monkeypatch.setenv("PROMEOS_DEMO_MODE", "false")
    now = datetime.now(timezone.utc)
    assert compute_freshness("Enedis", now, now=now, is_estimated=True) == "estimated"


def test_compliance_detector_includes_mitigation(db, org_with_sites):
    """ét12d P0-4 (CFO) : compliance_deadline events portent EventMitigation."""
    org_id = org_with_sites["org_id"]
    events = compliance_deadline_detector.detect(db, org_id)
    # Au moins un événement critical/warning attendu (fixture org_with_sites
    # crée des sites NON_CONFORME / A_RISQUE).
    risk_events = [e for e in events if e.severity in ("critical", "warning")]
    assert risk_events, "Fixture org_with_sites doit produire au moins un risque DT"
    for e in risk_events:
        assert e.impact.mitigation is not None, f"{e.id} sans mitigation"
        assert e.impact.mitigation.capex_eur is not None
        assert e.impact.mitigation.payback_months is not None
        assert e.impact.mitigation.npv_eur is not None
        assert e.impact.mitigation.npv_horizon_year == 2030


def test_billing_detector_emits_site_ids_granularity(db, org_with_sites):
    """ét12d P0-5 (EM) : billing_anomaly events exposent linked_assets.site_ids."""
    from services.event_bus.detectors import billing_anomaly_detector

    org_id = org_with_sites["org_id"]
    events = billing_anomaly_detector.detect(db, org_id)
    # Si pertes ouvertes → site_ids non vide ; si reclaims YTD → site_ids non vide
    for e in events:
        # site_ids peut être [] si zéro insight (cas trivial), mais le champ
        # doit toujours exister (linked_assets.site_ids: list, jamais None).
        assert hasattr(e.linked_assets, "site_ids")
        assert isinstance(e.linked_assets.site_ids, list)


# ── Vague C ét12e — corrections P0 résiduels (NPV actualisé + YAML + methodology + σ) ──


def test_npv_actualized_lower_than_nominal():
    """ét12e P0 #1 (CFO) : NPV actualisé < NPV nominal sur 5+ ans (>10% écart).

    Avant ét12e : NPV = annual_flow × années - capex (nominal, surévaluation
    35-40% sur 5 ans). Le CFO se faisait corriger en CODIR. Ce test garantit
    que la formule actualisée évite la surévaluation.
    """
    from config.mitigation_loader import compute_npv_actualized

    annual_flow = 30_000.0
    horizon = 2030
    capex = 8_000.0
    current = 2026  # 4 ans à actualiser

    npv_actualized = compute_npv_actualized(
        annual_flow_eur=annual_flow,
        horizon_year=horizon,
        capex_eur=capex,
        current_year=current,
    )
    npv_nominal = annual_flow * (horizon - current) - capex

    # NPV actualisé strictement inférieur au nominal (taux > 0)
    assert npv_actualized < npv_nominal, "NPV actualisé doit être < NPV nominal"
    # Écart > 5% sur 4 ans à 4% (~7-8% attendu)
    diff_pct = (npv_nominal - npv_actualized) / abs(npv_nominal) * 100
    assert diff_pct > 5.0, f"Écart actualisé/nominal trop faible : {diff_pct:.1f}%"


def test_npv_actualized_zero_horizon_returns_negative_capex():
    """ét12e P0 #1 : si horizon == année courante, NPV = -CAPEX (pas de flux)."""
    from config.mitigation_loader import compute_npv_actualized

    npv = compute_npv_actualized(
        annual_flow_eur=10_000.0,
        horizon_year=2026,
        capex_eur=5_000.0,
        current_year=2026,
    )
    assert npv == -5_000.0


def test_mitigation_yaml_loader_returns_typed_defaults():
    """ét12e P0 #4 : `mitigation_loader` charge YAML versionné avec sources citées."""
    from config.mitigation_loader import (
        get_consumption_drift_defaults,
        get_discount_rate,
        get_dt_compliance_defaults,
        reload,
    )

    reload()  # reset cache

    # Discount rate (pas magic, lu depuis YAML)
    rate = get_discount_rate()
    assert 0 < rate < 0.20, f"Taux d'actualisation hors plage raisonnable : {rate}"

    # DT defaults
    dt = get_dt_compliance_defaults()
    assert dt.capex_per_site_eur > 0
    assert dt.payback_months > 0
    assert dt.npv_horizon_year >= 2026
    assert "ADEME" in dt.capex_source or "marketplace" in dt.capex_source.lower()
    assert "Décret" in dt.npv_horizon_source

    # Consumption drift defaults
    drift = get_consumption_drift_defaults()
    assert drift.capex_eur is None  # action comportementale
    assert drift.payback_months >= 1


def test_compliance_event_exposes_methodology_for_drill_down(db, org_with_sites):
    """ét12e P0 #2/CFO drill-down : `EventSource.methodology` exposé pour tooltip frontend."""
    org_id = org_with_sites["org_id"]
    events = compliance_deadline_detector.detect(db, org_id)
    risk_events = [e for e in events if e.severity in ("critical", "warning")]
    assert risk_events, "Fixture doit produire au moins un risque DT"
    for e in risk_events:
        assert e.source.methodology is not None, f"{e.id} sans methodology"
        # methodology doit citer la source réglementaire
        assert "Décret" in e.source.methodology or "ADEME" in e.source.methodology
        # phrase explicite, pas un mot
        assert len(e.source.methodology) > 50


def test_consumption_drift_exposes_z_score_when_metrics_present(monkeypatch):
    """ét12e P0 #3 (EM) : si metrics.z_score présent, narrative inclut « Z-score ±X.Xσ »."""
    from datetime import datetime, timezone

    from services.event_bus.detectors import consumption_drift_detector

    # Stub get_insights_summary pour fournir un insight avec z_score
    fake_insight = {
        "type": "derive",
        "site_id": 42,
        "site_label": "Site Test",
        "estimated_loss_eur": 1500.0,
        "severity": "high",
        "message": "Dérive détectée",
        "metrics": {"delta_pct": 23.5, "z_score": 3.2, "sigma_baseline_kwh": 250},
        "updated_at": datetime.now(timezone.utc),
    }

    def fake_summary(db, org_id):
        return {"insights": [fake_insight]}

    monkeypatch.setattr(
        "services.consumption_diagnostic.get_insights_summary",
        fake_summary,
    )

    events = consumption_drift_detector.detect(db=None, org_id=1)
    assert events, "Détecteur doit émettre un événement avec ce stub"
    e = events[0]
    assert "Z-score" in e.narrative or "Z-score" in (e.title or "")
    assert "+3.2" in e.narrative or "3.2" in e.narrative
