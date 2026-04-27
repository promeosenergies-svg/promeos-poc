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
