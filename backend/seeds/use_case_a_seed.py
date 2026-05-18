"""Seed Use Case A — 6 actions HELIOS pour la démo pilote V4 (Sprint M2-5.7).

Closure du sprint M2-5 (frontend Centre d'Action V4). Le code FE M2-5.0→.6 est
fonctionnel mais ne sert à rien si `/action-center-v4` affiche « Aucune action ».
Ce seed transforme le parcours technique en démo crédible : un Energy Manager
HELIOS ouvre l'app et voit immédiatement un panorama d'actions réalistes.

Les 6 actions couvrent l'éventail Energy Manager B2B tertiaire :
  1. anomalie `new`            — vedette démo vierge (parcours live pilote)
  2. échéance `in_progress`    — riche : 2 preuves + 1 blocage + 1 lien
  3. échéance `triaged`        — simple (vu, pas planifié)
  4. décision `planned`        — projet engagé
  5. recommandation `closed`   — résolue + preuve vérifiée + lien
  6. action `closed`           — écartée (`not_applicable`)

Étend le seed minimal M2-4.1.bis (`seeds/v4_seed.py`) sans le modifier. Même
doctrine d'idempotence (D3) : chaque entité porte une PK UUID5 déterministe ;
une action déjà présente est ignorée (avec tous ses enfants). Deux runs
consécutifs ⇒ COUNT identique, 0 doublon. Pas de `_reset_demo` par DELETE :
`action_event_log` est en FK ON DELETE RESTRICT, un DELETE de l'item échouerait.

Org-scoping (D1/D5) — le seed NE crée PAS d'organisation. Il exige que l'org
cible (HELIOS, id=1) existe, sinon `SeedError`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_DNS, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.organisation import Organisation
from models.v4.action_blockers import ActionBlocker
from models.v4.action_center_items import ActionCenterItem
from models.v4.action_event_log import ActionEventLog
from models.v4.action_links import ActionLink
from models.v4.evidences import Evidence
from seeds.v4_seed import SeedError
from seeds.v4_seed_constants import SEED_ORG_ID

# ─────────────────────────────────────────────────────────────────────
# Identité déterministe (idempotence D3)
# ─────────────────────────────────────────────────────────────────────

# Namespace dédié, distinct de celui du seed minimal M2-4.1.bis → aucune
# collision de PK entre les 3 items minimaux et les 6 items Use Case A.
_NS: UUID = uuid5(NAMESPACE_DNS, "promeos.seed.v4.use_case_a")


def _item_uuid(slug: str) -> UUID:
    """PK déterministe d'une action Use Case A."""
    return uuid5(_NS, f"item:{slug}")


def _child_uuid(table: str, item_slug: str, child_slug: str) -> UUID:
    """PK déterministe d'une entité fille (event / evidence / blocker / link)."""
    return uuid5(_NS, f"{table}:{item_slug}:{child_slug}")


def _correlation_uuid(item_slug: str) -> UUID:
    """correlation_id partagé par tous les events d'une action (IS9)."""
    return uuid5(_NS, f"correlation:{item_slug}")


# actor_id Marie Dupont — UUID fictif déterministe (aucune FK `users` côté V4 ;
# `actor_id` est une colonne UUID nue, cf. ADR-009 / M3-JWT-USER-UUID).
_MARIE_ACTOR_ID: UUID = uuid5(_NS, "actor:marie.dupont")

# Acteurs des events. `chk_actor_consistency` : actor_type='user' ⇒ actor_id
# NOT NULL ; actor_type='system' ⇒ actor_id NULL.
_ACTORS: dict[str, dict] = {
    "marie": {
        "actor_type": "user",
        "actor_id": _MARIE_ACTOR_ID,
        "actor_name": "Marie Dupont",
        "actor_role": "energy_manager",
    },
    "copilot": {
        "actor_type": "system",
        "actor_id": None,
        "actor_name": "Copilot PROMEOS",
        "actor_role": None,
    },
}

_SOURCE_ROUTE = "seed:use_case_a"
_EVIDENCE_RETENTION_DAYS = 90  # IE6 : expires_at = verified_at + 90 jours


def _dt(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    """datetime UTC concis pour les specs littérales."""
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


# ─────────────────────────────────────────────────────────────────────
# Specs littérales — 6 actions HELIOS (aucune logique métier, cf. C4)
# ─────────────────────────────────────────────────────────────────────

USE_CASE_A_SPECS: tuple[dict, ...] = (
    # ── 1. VEDETTE DÉMO — anomalie vierge, traitée live par le pilote ──
    {
        "slug": "paris-hphc-q3",
        "kind": "anomaly",
        "domain": "optimisation",
        "title": "Vérifier consommation HP/HC Q3 — Paris Bureaux",
        "description": (
            "Anomalie détectée par Copilot PROMEOS : pic de consommation en "
            "Heures Pleines au Q3 2025 (+18 % vs baseline ajustée DJU). "
            "Vérifier la facture Engie et les courbes de charge Enedis."
        ),
        "lifecycle_state": "new",
        "priority_bracket": "P1",
        "priority_score": 62.0,
        "source_module": "copilot",
        "owner": False,
        "created_at": _dt(2026, 5, 17, 9, 30),
        "updated_at": _dt(2026, 5, 17, 9, 30),
        "events": [
            {
                "slug": "created",
                "type": "created",
                "actor": "copilot",
                "at": _dt(2026, 5, 17, 9, 30),
                "payload": {"to_state": "new", "detection": "automatique", "ecart_pct": 18},
            },
        ],
    },
    # ── 2. RICHE — toutes les mécaniques V4 visibles ──
    {
        "slug": "operat-2025",
        "kind": "deadline",
        "domain": "conformite",
        "title": "Déclaration OPERAT 2025 — Échéance 30/09/2026",
        "description": (
            "Récolter les consommations 2025 des 5 sites HELIOS et préparer la "
            "déclaration OPERAT. Périmètre : Paris Bureaux (3 500 m²), Lyon "
            "Bureaux (1 200 m²), Marseille École (2 800 m²), Nice Hôtel "
            "(4 000 m²), Toulouse Entrepôt (6 000 m²)."
        ),
        "lifecycle_state": "in_progress",
        "priority_bracket": "P1",
        "priority_score": 78.0,
        "source_module": "conformite",
        "owner": True,
        "business_due_date": _dt(2026, 9, 30),
        "created_at": _dt(2026, 3, 1, 14, 0),
        "updated_at": _dt(2026, 5, 15, 10, 0),
        "events": [
            {
                "slug": "created",
                "type": "created",
                "actor": "marie",
                "at": _dt(2026, 3, 1, 14, 0),
                "payload": {"to_state": "new"},
            },
            {
                "slug": "to-triaged",
                "type": "state_changed",
                "actor": "marie",
                "at": _dt(2026, 3, 2, 14, 0),
                "payload": {"from_state": "new", "to_state": "triaged"},
            },
            {
                "slug": "to-planned",
                "type": "state_changed",
                "actor": "marie",
                "at": _dt(2026, 3, 4, 14, 0),
                "payload": {"from_state": "triaged", "to_state": "planned"},
            },
            {
                "slug": "to-in-progress",
                "type": "state_changed",
                "actor": "marie",
                "at": _dt(2026, 3, 11, 14, 0),
                "payload": {"from_state": "planned", "to_state": "in_progress"},
            },
            {
                "slug": "ev-paris-added",
                "type": "evidence_added",
                "actor": "marie",
                "at": _dt(2026, 4, 10, 11, 0),
                "ref": ("evidence", "conso-paris"),
                "payload": {},
            },
            {
                "slug": "ev-paris-verified",
                "type": "evidence_verified",
                "actor": "marie",
                "at": _dt(2026, 4, 15, 16, 0),
                "ref": ("evidence", "conso-paris"),
                "payload": {},
            },
            {
                "slug": "ev-lyon-added",
                "type": "evidence_added",
                "actor": "marie",
                "at": _dt(2026, 5, 10, 9, 30),
                "ref": ("evidence", "conso-lyon"),
                "payload": {},
            },
            {
                "slug": "bl-toulouse-added",
                "type": "blocker_added",
                "actor": "marie",
                "at": _dt(2026, 5, 15, 10, 0),
                "ref": ("blocker", "conso-toulouse"),
                "payload": {"blocker_type": "waiting_data"},
            },
        ],
        "evidences": [
            {
                "slug": "conso-paris",
                "filename": "Conso_2025_Paris_Bureaux.pdf",
                "mime_type": "application/pdf",
                "file_size_mb": 1.2,
                "uploaded_at": _dt(2026, 4, 10, 11, 0),
                "description": "Consommations électricité + gaz Paris Bureaux 2025 (12 mois)",
                "verified_at": _dt(2026, 4, 15, 16, 0),
            },
            {
                "slug": "conso-lyon",
                "filename": "Conso_2025_Lyon_Bureaux.pdf",
                "mime_type": "application/pdf",
                "file_size_mb": 0.9,
                "uploaded_at": _dt(2026, 5, 10, 9, 30),
                "description": "Consommations Lyon Bureaux 2025",
                "verified_at": None,
            },
        ],
        "blockers": [
            {
                "slug": "conso-toulouse",
                "blocker_type": "waiting_data",
                "justification": (
                    "Consommation Toulouse Entrepôt manquante. Relance du compteur "
                    "Enedis envoyée le 15/05/2026, retour attendu sous 7 jours."
                ),
                "added_at": _dt(2026, 5, 15, 10, 0),
                "expected_resolution_at": _dt(2026, 5, 22, 10, 0),
            },
        ],
        "links": [
            {
                "slug": "operat-obligation",
                "link_type": "regulatory_anchor",
                "target_module": "regulatory_obligation",
                "relation": "fulfills",
                "created_at": _dt(2026, 3, 1, 14, 0),
            },
        ],
    },
    # ── 3. SIMPLE — état triaged ──
    {
        "slug": "audit-sme-nice",
        "kind": "deadline",
        "domain": "conformite",
        "title": "Audit SMÉ obligatoire — Nice Hôtel",
        "description": (
            "Site dépassant le seuil de 2,75 GWh/an (estimé 3,1 GWh sur 2025). "
            "Audit énergétique réglementaire à programmer avant le 11/10/2026."
        ),
        "lifecycle_state": "triaged",
        "priority_bracket": "P1",
        "priority_score": 68.0,
        "source_module": "conformite",
        "owner": True,
        "business_due_date": _dt(2026, 10, 11),
        "created_at": _dt(2026, 5, 10, 14, 0),
        "updated_at": _dt(2026, 5, 11, 14, 0),
        "events": [
            {
                "slug": "created",
                "type": "created",
                "actor": "marie",
                "at": _dt(2026, 5, 10, 14, 0),
                "payload": {"to_state": "new"},
            },
            {
                "slug": "to-triaged",
                "type": "state_changed",
                "actor": "marie",
                "at": _dt(2026, 5, 11, 14, 0),
                "payload": {"from_state": "new", "to_state": "triaged"},
            },
        ],
    },
    # ── 4. PLANNED — projet engagé ──
    {
        "slug": "renouvellement-contrat",
        "kind": "decision",
        "domain": "purchase",
        "title": "Renouvellement contrat fourniture électricité — 5 sites",
        "description": (
            "Contrat Engie arrivant à échéance le 31/12/2026. Comparer 3 "
            "fournisseurs (EDF / TotalEnergies / Alpiq) sur le prix de fourniture "
            "et les indexations 2026, dans le contexte du TURPE 7. Volume annuel "
            "HELIOS : ~4,2 GWh."
        ),
        "lifecycle_state": "planned",
        "priority_bracket": "P2",
        "priority_score": 54.0,
        "source_module": "purchase",
        "owner": True,
        "business_due_date": _dt(2026, 12, 31),
        "created_at": _dt(2026, 4, 1, 10, 0),
        "updated_at": _dt(2026, 4, 15, 11, 0),
        "events": [
            {
                "slug": "created",
                "type": "created",
                "actor": "marie",
                "at": _dt(2026, 4, 1, 10, 0),
                "payload": {"to_state": "new"},
            },
            {
                "slug": "to-triaged",
                "type": "state_changed",
                "actor": "marie",
                "at": _dt(2026, 4, 4, 10, 0),
                "payload": {"from_state": "new", "to_state": "triaged"},
            },
            {
                "slug": "to-planned",
                "type": "state_changed",
                "actor": "marie",
                "at": _dt(2026, 4, 15, 10, 0),
                "payload": {"from_state": "triaged", "to_state": "planned"},
            },
        ],
    },
    # ── 5. CLOSED resolved — action terminée avec preuve ──
    {
        "slug": "optim-hphc-marseille",
        "kind": "recommendation",
        "domain": "optimisation",
        "title": "Optimisation HP/HC — Marseille École",
        "description": (
            "Reprogrammation des thermostats de l'école pour basculer la chauffe "
            "principale en Heures Creuses (5 h–7 h). Économies attendues : ~7 % "
            "sur la consommation de chauffage."
        ),
        "lifecycle_state": "closed",
        "priority_bracket": "P3",
        "priority_score": 32.0,
        "source_module": "ems",
        "owner": True,
        "closure_reason": "resolved",
        "closed_at": _dt(2026, 3, 10, 8, 0),
        "created_at": _dt(2026, 2, 15, 8, 0),
        "updated_at": _dt(2026, 3, 10, 17, 0),
        "events": [
            {
                "slug": "created",
                "type": "created",
                "actor": "marie",
                "at": _dt(2026, 2, 15, 8, 0),
                "payload": {"to_state": "new"},
            },
            {
                "slug": "to-triaged",
                "type": "state_changed",
                "actor": "marie",
                "at": _dt(2026, 2, 17, 8, 0),
                "payload": {"from_state": "new", "to_state": "triaged"},
            },
            {
                "slug": "to-planned",
                "type": "state_changed",
                "actor": "marie",
                "at": _dt(2026, 2, 20, 8, 0),
                "payload": {"from_state": "triaged", "to_state": "planned"},
            },
            {
                "slug": "to-in-progress",
                "type": "state_changed",
                "actor": "marie",
                "at": _dt(2026, 2, 25, 8, 0),
                "payload": {"from_state": "planned", "to_state": "in_progress"},
            },
            {
                "slug": "ev-added",
                "type": "evidence_added",
                "actor": "marie",
                "at": _dt(2026, 3, 2, 14, 0),
                "ref": ("evidence", "rapport-optim"),
                "payload": {},
            },
            {
                "slug": "ev-verified",
                "type": "evidence_verified",
                "actor": "marie",
                "at": _dt(2026, 3, 5, 10, 0),
                "ref": ("evidence", "rapport-optim"),
                "payload": {},
            },
            {
                "slug": "to-closed",
                "type": "state_changed",
                "actor": "marie",
                "at": _dt(2026, 3, 10, 8, 0),
                "payload": {
                    "from_state": "in_progress",
                    "to_state": "closed",
                    "closure_reason": "resolved",
                },
            },
        ],
        "evidences": [
            {
                "slug": "rapport-optim",
                "filename": "Rapport_optimisation_HC_Marseille.pdf",
                "mime_type": "application/pdf",
                "file_size_mb": 2.4,
                "uploaded_at": _dt(2026, 3, 2, 14, 0),
                "description": "Rapport d'optimisation HP/HC école Marseille (mars 2026)",
                "verified_at": _dt(2026, 3, 5, 10, 0),
            },
        ],
        "links": [
            {
                "slug": "site-marseille",
                "link_type": "site_reference",
                "target_module": "site",
                "relation": "concerns",
                "created_at": _dt(2026, 2, 15, 8, 0),
            },
        ],
    },
    # ── 6. CLOSED not_applicable — action écartée ──
    {
        "slug": "bacs-lyon",
        "kind": "action",
        "domain": "conformite",
        "title": "Vérification décret BACS — Lyon Bureaux",
        "description": (
            "Vérification de l'applicabilité du décret BACS (décret n° 2020-887 "
            "du 20 juillet 2020, modifié par le décret n° 2023-259) au bâtiment "
            "de bureaux Lyon. Conclusion : puissance installée < 70 kW, site non "
            "concerné par l'obligation d'automatisation."
        ),
        "lifecycle_state": "closed",
        "priority_bracket": "P3",
        "priority_score": 20.0,
        "source_module": "conformite",
        "owner": False,
        "closure_reason": "not_applicable",
        "closed_at": _dt(2026, 4, 7, 9, 0),
        "created_at": _dt(2026, 4, 5, 9, 0),
        "updated_at": _dt(2026, 4, 7, 9, 0),
        "events": [
            {
                "slug": "created",
                "type": "created",
                "actor": "marie",
                "at": _dt(2026, 4, 5, 9, 0),
                "payload": {"to_state": "new"},
            },
            {
                "slug": "to-closed",
                "type": "state_changed",
                "actor": "marie",
                "at": _dt(2026, 4, 7, 9, 0),
                "payload": {
                    "from_state": "new",
                    "to_state": "closed",
                    "closure_reason": "not_applicable",
                },
            },
        ],
    },
)


# ─────────────────────────────────────────────────────────────────────
# Rapport de run
# ─────────────────────────────────────────────────────────────────────


@dataclass
class UseCaseASeedReport:
    """Résultat d'un run du seed Use Case A."""

    org_id: int
    actions_created: int
    actions_skipped: int
    events_created: int
    evidences_created: int
    blockers_created: int
    links_created: int

    def __str__(self) -> str:
        return (
            f"seed Use Case A — org_id={self.org_id} · "
            f"actions créées={self.actions_created} · "
            f"ignorées (déjà présentes)={self.actions_skipped} · "
            f"events={self.events_created} · evidences={self.evidences_created} · "
            f"blockers={self.blockers_created} · links={self.links_created}"
        )


# ─────────────────────────────────────────────────────────────────────
# Matérialisation
# ─────────────────────────────────────────────────────────────────────


def _require_org(db: Session, org_id: int) -> None:
    """Vérifie que l'organisation cible existe. Lève `SeedError` sinon."""
    if db.scalar(select(Organisation.id).where(Organisation.id == org_id)) is None:
        raise SeedError(
            f"Organisation id={org_id} introuvable — le seed Use Case A ne crée "
            f"pas d'organisation. Lancer le seed HELIOS d'abord "
            f"(python -m services.demo_seed --pack helios --size S)."
        )


def _build_evidence(spec: dict, item_slug: str, item_id: UUID, org_id: int) -> Evidence:
    """Construit une Evidence depuis sa spec.

    `storage_uri` est NOT NULL côté modèle (IE1) : on pose une URI `fs://`
    fictive. Elle reste interne au backend — le frontend ne l'expose jamais
    (doctrine M2-5.5, schéma de réponse sans cette colonne).
    `expires_at` est dérivé `verified_at + 90 j` (IE6).
    """
    verified_at = spec["verified_at"]
    expires_at = verified_at + timedelta(days=_EVIDENCE_RETENTION_DAYS) if verified_at else None
    return Evidence(
        id=_child_uuid("evidence", item_slug, spec["slug"]),
        organisation_id=org_id,
        action_item_id=item_id,
        mime_type=spec["mime_type"],
        file_size_bytes=int(spec["file_size_mb"] * 1024 * 1024),
        storage_uri=f"fs://seed/use-case-a/{item_slug}/{spec['filename']}",
        original_filename=spec["filename"],
        description=spec["description"],
        uploaded_at=spec["uploaded_at"],
        uploaded_by=_MARIE_ACTOR_ID,
        verified_at=verified_at,
        verified_by=_MARIE_ACTOR_ID if verified_at else None,
        expires_at=expires_at,
    )


def _seed_one_action(db: Session, org_id: int, spec: dict) -> dict[str, int]:
    """Matérialise une action et toutes ses entités filles. Idempotent.

    Returns:
        compteurs {events, evidences, blockers, links} (0 partout si l'action
        existait déjà — l'idempotence se joue sur la PK de l'item).
    """
    item_slug = spec["slug"]
    item_id = _item_uuid(item_slug)
    counts = {"events": 0, "evidences": 0, "blockers": 0, "links": 0}

    if db.get(ActionCenterItem, item_id) is not None:
        return counts  # déjà seedé — skip action + enfants

    item = ActionCenterItem(
        id=item_id,
        organisation_id=org_id,
        kind=spec["kind"],
        domain=spec["domain"],
        title=spec["title"],
        description=spec["description"],
        source_module=spec.get("source_module"),
        lifecycle_state=spec["lifecycle_state"],
        priority_bracket=spec["priority_bracket"],
        priority_score=spec["priority_score"],
        detected_at=spec["created_at"],
        business_due_date=spec.get("business_due_date"),
        created_at=spec["created_at"],
        updated_at=spec["updated_at"],
    )
    if spec.get("owner"):
        item.owner_id = _MARIE_ACTOR_ID
        item.owner_role = "energy_manager"
        item.assigned_at = spec["created_at"]
    # IL10 (chk_closure_consistency) : closed ⇒ closed_at + closure_reason NOT NULL.
    if spec["lifecycle_state"] == "closed":
        item.closed_at = spec["closed_at"]
        item.closure_reason = spec["closure_reason"]
    db.add(item)
    db.flush()  # isole une éventuelle violation CHECK sur cette action

    correlation_id = _correlation_uuid(item_slug)

    for ev in spec.get("evidences", []):
        db.add(_build_evidence(ev, item_slug, item_id, org_id))
        counts["evidences"] += 1

    for bl in spec.get("blockers", []):
        db.add(
            ActionBlocker(
                id=_child_uuid("blocker", item_slug, bl["slug"]),
                organisation_id=org_id,
                item_id=item_id,
                blocker_type=bl["blocker_type"],
                justification=bl["justification"],
                added_by=_MARIE_ACTOR_ID,
                added_at=bl["added_at"],
                expected_resolution_at=bl.get("expected_resolution_at"),
            )
        )
        counts["blockers"] += 1

    for lk in spec.get("links", []):
        db.add(
            ActionLink(
                id=_child_uuid("link", item_slug, lk["slug"]),
                organisation_id=org_id,
                item_id=item_id,
                link_type=lk["link_type"],
                target_module=lk["target_module"],
                target_id=_child_uuid("link_target", item_slug, lk["slug"]),
                relation=lk["relation"],
                created_at=lk["created_at"],
            )
        )
        counts["links"] += 1

    for ev in spec.get("events", []):
        payload = dict(ev.get("payload", {}))
        ref = ev.get("ref")
        if ref is not None:
            ref_table, ref_slug = ref
            payload[f"{ref_table}_id"] = str(_child_uuid(ref_table, item_slug, ref_slug))
        actor = _ACTORS[ev["actor"]]
        db.add(
            ActionEventLog(
                id=_child_uuid("event", item_slug, ev["slug"]),
                organisation_id=org_id,
                action_item_id=item_id,
                event_type=ev["type"],
                occurred_at=ev["at"],
                actor_type=actor["actor_type"],
                actor_id=actor["actor_id"],
                actor_name=actor["actor_name"],
                actor_role=actor["actor_role"],
                event_payload=payload,
                correlation_id=correlation_id,
                source_route=_SOURCE_ROUTE,
            )
        )
        counts["events"] += 1

    db.flush()
    return counts


def seed_use_case_a_actions(db: Session, *, org_id: int = SEED_ORG_ID) -> UseCaseASeedReport:
    """Seede les 6 actions HELIOS du Use Case A. Idempotent (skip par PK).

    Args:
        db: session SQLAlchemy. `PRAGMA foreign_keys=ON` doit être actif (garanti
            par `database/connection.py` pour toute session de production).
        org_id: organisation cible (défaut `SEED_ORG_ID`=1, HELIOS). Doit exister.

    Returns:
        UseCaseASeedReport (compteurs par type d'entité).

    Raises:
        SeedError: si l'organisation cible n'existe pas.
    """
    _require_org(db, org_id)

    created = skipped = 0
    totals = {"events": 0, "evidences": 0, "blockers": 0, "links": 0}
    for spec in USE_CASE_A_SPECS:
        if db.get(ActionCenterItem, _item_uuid(spec["slug"])) is not None:
            skipped += 1
            continue
        counts = _seed_one_action(db, org_id, spec)
        created += 1
        for key, value in counts.items():
            totals[key] += value

    db.commit()
    return UseCaseASeedReport(
        org_id=org_id,
        actions_created=created,
        actions_skipped=skipped,
        events_created=totals["events"],
        evidences_created=totals["evidences"],
        blockers_created=totals["blockers"],
        links_created=totals["links"],
    )


def main() -> None:
    """Point d'entrée CLI : `python -m seeds.use_case_a_seed [--org-id N]`.

    Utilise `SessionLocal` de production (`PRAGMA foreign_keys=ON` garanti).
    """
    import argparse
    import sys

    from database.connection import SessionLocal

    parser = argparse.ArgumentParser(
        prog="python -m seeds.use_case_a_seed",
        description="Seed Use Case A — 6 actions HELIOS pour la démo pilote V4.",
    )
    parser.add_argument(
        "--org-id",
        type=int,
        default=SEED_ORG_ID,
        help=f"organisation cible (défaut {SEED_ORG_ID}, HELIOS). Doit exister.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = seed_use_case_a_actions(db, org_id=args.org_id)
    except SeedError as exc:
        print(f"ERREUR seed Use Case A : {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()
    print(report)


if __name__ == "__main__":
    main()
