"""T6 — Doctrine canonical test : event engine reacts to time J → J+1.

Doctrine v1.1 §6 P6 « le produit pousse, ne tire pas » + §14 Test 6 :
si le temps avance, **au moins un événement** doit refléter ce changement.

Ce test cristallise la dimension temporelle du moteur événements de
manière permanente. Verrou contre l'anti-pattern §6.4 « page identique
J vs J+1 ». Survit aux refactorings event_bus internes : tant que
`compute_events` produit des événements deadline-driven, ce test passe.

Mécanique :
1. Snapshot J : `compute_events(db, org_id)` avec horloge réelle.
2. Mock `datetime.now()` à J+1 dans les 3 détecteurs deadline-driven
   (`compliance_deadline_detector`, `contract_renewal_detector`,
   `market_window_detector`) — ceux dont l'impact dépend de
   `(deadline - today)`.
3. Snapshot J+1 : `compute_events(db, org_id)` avec horloge mockée.
4. Assert ≥ 1 différence (severity / impact.value / appearance).

Réf : docs/adr/ADR-002-chantier-alpha-moteur-evenements.md §Tests,
docs/audits/sprint_alpha_phase0_audit_20260502.md §7 Q5 (c)
(doublon assumé avec test_event_bus.py — ce fichier est la SoT
doctrinale, test_event_bus.py reste le test de non-régression Vague C).
"""

from __future__ import annotations

import os
import sys
from contextlib import ExitStack
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# Détecteurs qui utilisent `datetime.now()` ou `date.today()` pour
# calculer un impact dépendant du temps (deadline restant). Mocker ces
# modules suffit à garantir un changement J → J+1.
_DEADLINE_DRIVEN_DETECTORS = (
    "services.event_bus.detectors.compliance_deadline_detector",
    "services.event_bus.detectors.contract_renewal_detector",
    "services.event_bus.detectors.market_window_detector",
)


class _FrozenDatetime(datetime):
    """Sous-classe de datetime qui fige `.now()` à une valeur cible.

    Utilisée comme remplacement du symbole `datetime` importé par les
    détecteurs (`from datetime import datetime`). Hérite de la vraie
    datetime → `isinstance(x, datetime)` reste correct + opérations
    arithmétiques (timedelta) préservées.
    """

    _frozen_value: datetime | None = None

    @classmethod
    def freeze(cls, target: datetime) -> None:
        cls._frozen_value = target

    @classmethod
    def unfreeze(cls) -> None:
        cls._frozen_value = None

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        if cls._frozen_value is None:
            return datetime.now(tz)
        if tz is None:
            return cls._frozen_value
        return cls._frozen_value.astimezone(tz)

    @classmethod
    def utcnow(cls):  # type: ignore[override]
        if cls._frozen_value is None:
            return datetime.utcnow()
        v = cls._frozen_value
        return v.replace(tzinfo=None) if v.tzinfo else v


class _FrozenDate(date):
    """Sous-classe de date qui fige `.today()` à une valeur cible.

    Le détecteur `contract_renewal_detector` + `market_window_detector`
    utilisent `date.today()` (cf. discovery Phase 1.E). Sans ce mock,
    leurs events ne changeraient pas avec datetime mocké seul.
    """

    _frozen_value: date | None = None

    @classmethod
    def freeze(cls, target: date) -> None:
        cls._frozen_value = target

    @classmethod
    def unfreeze(cls) -> None:
        cls._frozen_value = None

    @classmethod
    def today(cls):  # type: ignore[override]
        if cls._frozen_value is None:
            return date.today()
        return cls._frozen_value


def _snapshot_at(target_datetime: datetime, org_id: int) -> list:
    """Capture les events produits à `target_datetime`.

    Mocke `datetime` et `date` dans les 3 détecteurs deadline-driven.
    Les 6 autres détecteurs (data_quality, asset_registry, etc.) ne
    dépendent pas du temps écoulé — ils restent fonctionnels avec
    l'horloge réelle, ce qui n'invalide pas l'assertion T6 (qui exige
    seulement ≥ 1 changement parmi les 9 EventTypes).
    """
    from database import SessionLocal

    from services.event_bus.event_service import compute_events

    target_date_obj = target_datetime.date()
    _FrozenDatetime.freeze(target_datetime)
    _FrozenDate.freeze(target_date_obj)

    stack = ExitStack()
    try:
        for mod_path in _DEADLINE_DRIVEN_DETECTORS:
            stack.enter_context(patch(f"{mod_path}.datetime", _FrozenDatetime))
            # `date` n'est importé que dans contract_renewal et market_window
            # (cf. discovery Phase 1.E). On utilise create=True pour ne pas
            # planter sur les modules qui ne l'importent pas.
            stack.enter_context(patch(f"{mod_path}.date", _FrozenDate, create=True))

        with stack:
            db = SessionLocal()
            try:
                events = compute_events(db, org_id)
                # Force évaluation hors mock (les events sont des
                # frozen dataclasses, pas de SQL lazy).
                return list(events)
            finally:
                db.close()
    finally:
        _FrozenDatetime.unfreeze()
        _FrozenDate.unfreeze()


def _resolve_helios_org_id() -> int:
    """Récupère l'org HELIOS S seedée par conftest autouse parent."""
    from database import SessionLocal
    from models import Organisation

    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.actif.is_(True)).first()
        assert org is not None, (
            "T6 setup invariant violated: aucune Organisation active en DB. "
            "Le conftest autouse `ensure_demo_data` devrait avoir seedé HELIOS S."
        )
        return org.id
    finally:
        db.close()


# ── Comparaison events J vs J+1 ─────────────────────────────────────


def _diff_events(events_j: list, events_j1: list) -> list[tuple]:
    """Calcule les changements entre 2 snapshots events.

    Retourne une liste de tuples typés :
      ('appeared', event_id)
      ('disappeared', event_id)
      ('severity_changed', event_id, sev_j, sev_j1)
      ('impact_value_changed', event_id, val_j, val_j1)
      ('narrative_changed', event_id)
    """
    j_by_id = {e.id: e for e in events_j}
    j1_by_id = {e.id: e for e in events_j1}

    changes: list[tuple] = []
    all_ids = set(j_by_id.keys()) | set(j1_by_id.keys())

    for event_id in all_ids:
        e_j = j_by_id.get(event_id)
        e_j1 = j1_by_id.get(event_id)

        if e_j is None and e_j1 is not None:
            changes.append(("appeared", event_id))
        elif e_j is not None and e_j1 is None:
            changes.append(("disappeared", event_id))
        elif e_j is not None and e_j1 is not None:
            if e_j.severity != e_j1.severity:
                changes.append(("severity_changed", event_id, e_j.severity, e_j1.severity))
            if e_j.impact.value != e_j1.impact.value:
                changes.append(("impact_value_changed", event_id, e_j.impact.value, e_j1.impact.value))
            if e_j.narrative != e_j1.narrative:
                changes.append(("narrative_changed", event_id))

    return changes


# ── Test canonique T6 ───────────────────────────────────────────────


def test_t6_event_cards_evolve_between_j_and_j_plus_1():
    """Doctrine §14 T6 — si le temps avance, ≥ 1 event card change.

    Verrou permanent contre l'anti-pattern §6.4 « page identique J vs J+1 ».
    Si ce test échoue, le moteur événements ne réagit plus au temps —
    régression doctrinale critique.
    """
    org_id = _resolve_helios_org_id()

    # Date pivot fixe : 17 jours avant la deadline capacité 2026-11-01.
    # Zone narrative "dans N jours" (≤ 30j) → décrement N → N-1 garantit
    # un changement narrative dans market_window_detector entre J et J+1.
    # Cohérence reproductibilité : pas de today() réel utilisé.
    j = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)
    j_plus_1 = j + timedelta(days=1)

    events_j = _snapshot_at(j, org_id)
    events_j1 = _snapshot_at(j_plus_1, org_id)

    # Sanity check : le seed HELIOS S doit produire au moins 1 event
    # côté snapshot J (sinon T6 n'a pas de matière à comparer).
    assert len(events_j) > 0 or len(events_j1) > 0, (
        "T6 setup invariant violated: aucun event produit ni en J ni en J+1. "
        "Le seed HELIOS S devrait déclencher au moins compliance_deadline_detector "
        "ou data_quality_issue_detector. Vérifier `services.demo_seed.SeedOrchestrator`."
    )

    changes = _diff_events(events_j, events_j1)

    # Doctrine assertion : moteur réagit au temps
    assert len(changes) >= 1, (
        f"T6 doctrine violation: aucun event card n'a changé entre J et J+1. "
        f"Events J: {len(events_j)}, Events J+1: {len(events_j1)}. "
        f"Doctrine §6 P6 + §14 Test 6 exigent une réactivité temporelle. "
        f"Si tous les détecteurs deadline-driven (compliance / contract / "
        f"market) sont stateless ou bypassés, ce test devient une régression "
        f"doctrinale critique. Voir ADR-002 + audit Phase 0 α."
    )


def test_t6_helios_seed_produces_compliance_deadline_event():
    """T6 setup invariant — HELIOS S doit produire ≥ 1 compliance_deadline.

    Garde-fou amont : si le seed change et ne produit plus de
    compliance_deadline events, le test T6 principal pourrait passer
    par hasard via d'autres détecteurs. Cette assertion isole le
    pilote MVP doctrinal (compliance_deadline_detector ét11).
    """
    org_id = _resolve_helios_org_id()

    j = datetime(2026, 5, 2, 12, 0, 0, tzinfo=timezone.utc)
    events_j = _snapshot_at(j, org_id)

    compliance_events = [e for e in events_j if e.event_type == "compliance_deadline"]
    assert len(compliance_events) >= 1, (
        "Setup HELIOS S a perdu ses compliance_deadline events. "
        "Vérifier que le seed produit toujours ≥ 1 site `non_conforme` ou "
        "`a_risque` (cf. compliance_deadline_detector.detect logique)."
    )
