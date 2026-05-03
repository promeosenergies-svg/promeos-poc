"""Events query service — couche d'adaptation REST sur event_bus (Voie C, Phase 1.A).

Sprint α-fin Phase 1.A — endpoint REST `/api/v1/events/upcoming`.
Sprint α-push Phase 2.A — orchestrateur multi-org `refresh_all_active_orgs`
appelé par cron `.github/workflows/digest-daily.yml` à 7h45 Paris.

Principe : `event_bus/` reste strictement intact (réutilisation pure de
`compute_events`). Cette couche query applique les filtres requis par
l'API REST (persona, page_key, horizon_days) + pagination cursor MVP
sur la liste retournée.

Aucune logique métier de détection ici — seulement filtrage, pagination
et orchestration multi-org sur la sortie de `compute_events`.

Réf : docs/audits/sprint_alpha_phase0_audit_20260502.md (Voie C),
docs/adr/ADR-002-chantier-alpha-moteur-evenements.md.
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from services.event_bus.event_service import compute_events
from services.event_bus.types import SolEventCard

# ── Constantes mapping (alignées convention repo) ───────────────────

# Mapping persona → owner_role(s) tolérés.
# Aligné sur valeurs réelles des détecteurs `event_bus/detectors/*.py` :
#   - DAF : compliance_deadline, asset_registry_issue, billing_anomaly,
#           contract_renewal, market_window
#   - Energy Manager : flex_opportunity, data_quality_issue,
#                      consumption_drift, action_overdue (cas EM)
#   - Site Manager : action_overdue (cas Site)
PERSONA_TO_OWNER_ROLES: dict[str, list[str]] = {
    "energy_manager": ["Energy Manager", "Site Manager"],
    "daf": ["DAF"],
    "admin": ["Admin"],
    "operator": ["Operator"],
}

# Mapping page_key → event_types.
# Aligné sur PageKey Literal canonique défini dans
# `services/narrative/narrative_generator.py` (10 valeurs).
PAGE_KEY_TO_EVENT_TYPES: dict[str, list[str]] = {
    "cockpit_daily": [
        "compliance_deadline",
        "consumption_drift",
        "billing_anomaly",
        "flex_opportunity",
        "data_quality_issue",
    ],
    "cockpit_comex": ["compliance_deadline", "contract_renewal", "market_window"],
    "patrimoine": ["data_quality_issue", "asset_registry_issue"],
    "conformite": ["compliance_deadline"],
    "bill_intel": ["billing_anomaly"],
    "achat_energie": ["contract_renewal", "market_window"],
    "monitoring": ["consumption_drift"],
    "diagnostic": ["consumption_drift", "data_quality_issue"],
    "anomalies": ["billing_anomaly", "data_quality_issue"],
    "flex": ["flex_opportunity"],
}

DEFAULT_LIMIT = 20
DEFAULT_HORIZON_DAYS = 30


# ── Public API ──────────────────────────────────────────────────────


def get_upcoming_events(
    db: Session,
    org_id: int,
    persona: Optional[str] = None,
    page_key: Optional[str] = None,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    cursor: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> dict:
    """Query layer over event_bus.compute_events.

    Pure adaptation pour endpoint REST :
    - applique 3 filtres optionnels (persona / page_key / horizon_days)
    - pagine via cursor base64-encoded offset (MVP)

    Aucune mutation de event_bus/. Aucune détection métier ici.

    Parameters
    ----------
    db : Session
    org_id : int
    persona : Optional[str]
        Si fourni, filtre sur action.owner_role via PERSONA_TO_OWNER_ROLES.
        Persona inconnu → aucun filtre persona appliqué.
    page_key : Optional[str]
        Si fourni, filtre sur event_type via PAGE_KEY_TO_EVENT_TYPES.
        Page_key inconnu → aucun filtre page_key appliqué.
    horizon_days : int
        Borne supérieure de fenêtre temporelle (défaut 30j).
    cursor : Optional[str]
        Curseur base64 opaque (offset entier encodé). Curseur invalide → page 0.
    limit : int
        Nombre max d'events par page (défaut 20).

    Returns
    -------
    dict
        {
          'events': list[SolEventCard],  # page courante
          'next_cursor': Optional[str],   # None si dernière page
          'total': int,                    # taille totale post-filtres
        }
    """
    raw = compute_events(db, org_id)
    filtered = _apply_persona_filter(raw, persona)
    filtered = _apply_page_key_filter(filtered, page_key)
    filtered = _apply_horizon_filter(filtered, horizon_days)
    paginated, next_cursor = _paginate(filtered, cursor, limit)
    return {
        "events": paginated,
        "next_cursor": next_cursor,
        "total": len(filtered),
    }


# ── Filtres internes ────────────────────────────────────────────────


def _apply_persona_filter(events: list[SolEventCard], persona: Optional[str]) -> list[SolEventCard]:
    """Filtre sur action.owner_role via PERSONA_TO_OWNER_ROLES.

    Persona = None ou inconnu → no-op (retourne events inchangés).
    """
    if not persona or persona not in PERSONA_TO_OWNER_ROLES:
        return events
    allowed_roles = PERSONA_TO_OWNER_ROLES[persona]
    return [e for e in events if e.action.owner_role in allowed_roles]


def _apply_page_key_filter(events: list[SolEventCard], page_key: Optional[str]) -> list[SolEventCard]:
    """Filtre sur event_type via PAGE_KEY_TO_EVENT_TYPES.

    Page_key = None ou inconnu → no-op.
    """
    if not page_key or page_key not in PAGE_KEY_TO_EVENT_TYPES:
        return events
    allowed_types = PAGE_KEY_TO_EVENT_TYPES[page_key]
    return [e for e in events if e.event_type in allowed_types]


def _apply_horizon_filter(events: list[SolEventCard], horizon_days: int) -> list[SolEventCard]:
    """Filtre fenêtre temporelle.

    Règle :
    - event avec impact.period='deadline' et impact.value (jours) ≤ horizon_days
      → inclus
    - event avec source.last_updated_at dans la fenêtre (cutoff = now - horizon_days)
      → inclus
    - sinon → inclus par défaut (l'absence de signal temporel ne doit pas exclure
      les events structurels comme flex_opportunity sans deadline explicite)
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=horizon_days)

    def in_horizon(e: SolEventCard) -> bool:
        if e.impact.period == "deadline" and e.impact.value is not None:
            return e.impact.value <= horizon_days
        if e.source.last_updated_at is not None:
            updated = e.source.last_updated_at
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            if updated >= cutoff:
                return True
        return True

    return [e for e in events if in_horizon(e)]


# ── Pagination ──────────────────────────────────────────────────────


def _paginate(
    events: list[SolEventCard], cursor: Optional[str], limit: int
) -> tuple[list[SolEventCard], Optional[str]]:
    """Pagination MVP via cursor base64(offset).

    Cursor invalide ou absent → offset=0 (page 0).
    Last page → next_cursor=None.
    """
    offset = _decode_cursor(cursor)
    page = events[offset : offset + limit]
    next_cursor: Optional[str] = None
    if offset + limit < len(events):
        next_cursor = _encode_cursor(offset + limit)
    return page, next_cursor


def _decode_cursor(cursor: Optional[str]) -> int:
    """Décode un cursor base64 en offset entier. Invalide → 0."""
    if not cursor:
        return 0
    try:
        decoded = base64.b64decode(cursor.encode("utf-8")).decode("utf-8")
        offset = int(decoded)
        if offset < 0:
            return 0
        return offset
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return 0


def _encode_cursor(offset: int) -> str:
    """Encode un offset entier en cursor base64."""
    return base64.b64encode(str(offset).encode("utf-8")).decode("utf-8")


# ── Orchestration multi-org (Sprint α-push Phase 2.A) ───────────────


def refresh_all_active_orgs(db: Session) -> dict:
    """Recalcule `compute_events` pour toutes les orgs actives.

    Appelé par l'endpoint admin `POST /api/v1/events/refresh` qui est
    déclenché par le workflow GitHub Actions cron quotidien 7h45 Paris.

    Erreurs par org sont capturées (pas de propagation) — une org en
    échec n'empêche pas les suivantes d'être rafraîchies. Réponse
    structurée pour traçabilité GHA Actions log.

    Idempotent : `compute_events` est stateless (détection à la volée
    sur l'état DB courant), pas d'effet de bord en table `events`
    (Phase 1.B/2.D introduiront le store si besoin audit régulatoire).

    Returns
    -------
    dict
        {
          'refreshed_orgs': int,
          'total_events': int,
          'errors': list[{'org_id': int, 'error': str}],
          'computed_at': str (ISO 8601 UTC),
        }
    """
    from models import Organisation

    refreshed_orgs = 0
    total_events = 0
    errors: list[dict] = []

    active_orgs = db.query(Organisation).filter(Organisation.actif.is_(True)).all()

    for org in active_orgs:
        try:
            events = compute_events(db, org.id)
            total_events += len(events)
            refreshed_orgs += 1
        except Exception as exc:
            errors.append({"org_id": org.id, "error": str(exc)})

    return {
        "refreshed_orgs": refreshed_orgs,
        "total_events": total_events,
        "errors": errors,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
