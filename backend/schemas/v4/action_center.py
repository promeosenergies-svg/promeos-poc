"""M2-4.2 — Schemas Pydantic des endpoints /api/v4/action-center/items.

Discipline (anti-patterns V66 intégrés nativement) :
- `response_model` sur chaque endpoint (RC2) — les modèles de réponse vivent ici.
- `extra="forbid"` sur les requests → un payload avec un champ inconnu est
  rejeté en 422 dès la couche schema (defense in depth avec le repo).
- Enums Python V4, jamais de strings magiques.
- `organisation_id` JAMAIS dans un request body : forcé par `BaseRepositoryV4`
  depuis le contexte org. Il est en revanche exposé en réponse (pas dans l'URL,
  donc pas de fuite d'énumération).

Erreurs : format PROMEOS standard `{code, message, hint, correlation_id}` —
cf. `schemas/error.py::APIError`. Les routes lèvent des `HTTPException` dont le
`detail` suit ce dict (pas de modèle d'erreur dédié dupliqué ici).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.v4.enums import BlockerType, ClosureReason, Kind, LifecycleState, PriorityBracket
from models.v4.enums.target_module import TargetModule


# ── Request ──────────────────────────────────────────────────────────


class ActionCenterItemCreate(BaseModel):
    """Body de POST /api/v4/action-center/items.

    `priority_*` et `lifecycle_state` sont absents par design :
    - la priorité est DÉRIVÉE (scoring R1-R6, Sprint M2-5) — pas une saisie user ;
      à la création, la route pose un placeholder + `score_stale=True`.
    - `lifecycle_state` démarre toujours à `new` (server_default).
    """

    model_config = ConfigDict(extra="forbid")

    kind: Kind
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    domain: Optional[str] = Field(None, max_length=30)


# ── Responses ────────────────────────────────────────────────────────


class ActionCenterItemResponse(BaseModel):
    """Réponse d'un item unique (POST / GET by id)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: int  # exposé OK : dérivé du contexte, jamais dans l'URL
    kind: Kind
    title: str
    description: Optional[str]
    domain: Optional[str]
    lifecycle_state: LifecycleState
    priority_bracket: PriorityBracket
    priority_score: float
    score_stale: bool
    # M2-5.11.D — Valeur €/12m du quadrant « à risque » (lue depuis la
    # `@property impact_at_risk_eur` du model, extraite de `impact_payload`).
    # Permet à l'UI d'afficher le montant dans ItemsTable + PriorityQueueCard
    # sans appel /impact unitaire (anti N+1). `None` si l'impact n'est pas
    # encore calculé pour cet item — l'UI rend « — ».
    impact_at_risk_eur: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class ActionCenterItemListResponse(BaseModel):
    """Réponse de GET /api/v4/action-center/items — liste paginée."""

    items: list[ActionCenterItemResponse]
    total: int
    offset: int
    limit: int


# ── Sous-ressources : responses (M2-4.3, lecture seule) ──────────────
#
# Discipline : on expose les métadonnées sémantiquement publiques, on masque
# tout ce qui touche au stockage / à l'implémentation interne.
# - Evidence : `storage_uri` + `validation_payload` JAMAIS exposés (anti-leak).
#   Pas de `download_endpoint` : l'endpoint de download n'existe pas (M2-4.4+) —
#   exposer un champ toujours None serait du bruit ; il sera ajouté avec lui.
# - ActionEventLog : `event_payload` (JSON versionné IE7) non exposé — un read
#   endpoint générique expose les métadonnées, pas la structure interne.


class ActionEventLogResponse(BaseModel):
    """Métadonnées d'un event (audit trail)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_item_id: UUID
    event_type: str
    occurred_at: datetime
    actor_type: str
    actor_id: Optional[UUID]
    actor_name: Optional[str]
    actor_role: Optional[str]
    schema_version: str
    correlation_id: UUID
    source_route: Optional[str]


class ActionEvidenceResponse(BaseModel):
    """Métadonnées d'une evidence.

    SÉCURITÉ : `storage_uri` et `validation_payload` ne sont JAMAIS exposés.
    Le download passera par un endpoint dédié (M2-4.4+) revalidant auth + scope.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_item_id: UUID
    mime_type: str
    file_size_bytes: int
    original_filename: Optional[str]
    description: Optional[str]
    uploaded_at: datetime
    uploaded_by: UUID
    verified_at: Optional[datetime]
    verified_by: Optional[UUID]
    expires_at: Optional[datetime]


class ActionBlockerResponse(BaseModel):
    """Métadonnées d'un blocker (pas de colonne `severity` sur ce modèle)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_id: UUID
    blocker_type: str
    justification: Optional[str]
    added_at: datetime
    added_by: Optional[UUID]
    expected_resolution_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolved_by: Optional[UUID]


class ActionLinkResponse(BaseModel):
    """Métadonnées d'un lien — polymorphe : cible `target_module` + `target_id`."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_id: UUID
    link_type: str
    target_module: str
    target_id: UUID
    relation: str
    created_at: datetime


# ── Sous-ressources : wrappers de liste paginée ──────────────────────


class ActionEventLogListResponse(BaseModel):
    items: list[ActionEventLogResponse]
    total: int
    offset: int
    limit: int


class ActionEvidenceListResponse(BaseModel):
    items: list[ActionEvidenceResponse]
    total: int
    offset: int
    limit: int


class ActionBlockerListResponse(BaseModel):
    items: list[ActionBlockerResponse]
    total: int
    offset: int
    limit: int


class ActionLinkListResponse(BaseModel):
    items: list[ActionLinkResponse]
    total: int
    offset: int
    limit: int


# ── Impact financier (M2-5.10.C — maquette §8.5 / detail_drawer §8.4) ──
#
# 4 dimensions strictes par item (cf. maquette `centre_action_v4_detail_drawer
# _v02.html` lignes 853-885) :
#   - estimated   : gain attendu si l'action est exécutée selon le scénario reco
#   - at_risk     : montant non sécurisé (pénalité, sanction) si non-traitement
#   - secured     : montant prêt à activer (action démarrée, preuve disponible)
#   - realized    : gain constaté après clôture avec preuves vérifiées
#
# MV3 : les valeurs sont lues depuis `ActionCenterItem.impact_payload` (JSONB)
# si présentes — un futur engine de scoring économique (M3+) les calculera.
# Côté UI, une dimension `null` est rendue « — » (pas « 0 € » qui mentirait).


class ImpactDimension(BaseModel):
    """Une dimension d'impact (Estimated / AtRisk / Secured / Realized).

    `value_eur` peut être `None` : la dimension est rendue « — » côté UI
    (cardinal : ne jamais afficher 0 € quand le montant est inconnu).
    """

    model_config = ConfigDict(extra="forbid")

    value_eur: Optional[float] = None
    detail: Optional[str] = Field(None, max_length=200)
    formula: Optional[str] = Field(None, max_length=200)
    source: Optional[str] = Field(None, max_length=120)


class JournalEventResponse(BaseModel):
    """M2-5.10.E — Event enrichi du titre de l'item parent (vue org-wide).

    Calqué sur `ActionEventLogResponse` (sous-ressource item-scoped) avec en
    plus `action_item_title` joint au repo — évite N+1 côté UI quand on
    affiche la timeline cross-items du journal.

    Discipline : on n'expose pas `event_payload` (IE7 versionné — détail
    interne) ni `correlation_id` / `source_route` (peu pertinents pour la
    vue user). L'UI dérive le label affiché depuis `event_type` (cf.
    EVENT_TYPE_LABELS) et l'acteur via `actor_name` / `actor_role`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_item_id: UUID
    action_item_title: str
    event_type: str
    actor_type: str
    actor_id: Optional[UUID] = None
    actor_role: Optional[str] = None
    actor_name: Optional[str] = None
    occurred_at: datetime


class PilotageJournalResponse(BaseModel):
    """M2-5.10.E — Réponse de GET /api/v4/action-center/pilotage/journal.

    Timeline org-wide des N derniers jours (maquette §8.2). `since_days`
    est la fenêtre demandée (cap 30j MV3) ; `total` est le compte non
    plafonné par `limit` (utile pour le badge filtre / narrative bar).
    """

    model_config = ConfigDict(extra="forbid")

    items: list[JournalEventResponse]
    total: int
    since_days: int
    limit: int


class PilotageFilePrioritaireResponse(BaseModel):
    """M2-5.10.D — Réponse de GET /api/v4/action-center/pilotage/file-prioritaire.

    Top N items P0/P1 actifs (lifecycle != closed), triés priority_score
    DESC. `limit` est la taille demandée (≤ 20 — file cardinale, pas une
    liste exhaustive). Pas de pagination : la file est par définition
    courte. Pour la liste exhaustive, l'UI renvoie vers le référentiel.
    """

    model_config = ConfigDict(extra="forbid")

    items: list[ActionCenterItemResponse]
    limit: int


class ItemImpactResponse(BaseModel):
    """Réponse de GET /api/v4/action-center/items/{id}/impact.

    Les 4 dimensions sont toujours présentes (UI rend des cards Sol fixes),
    avec valeurs `null` si le payload backend ne les expose pas encore.
    """

    model_config = ConfigDict(extra="forbid")

    item_id: UUID
    period: str = Field("12m", max_length=10, description="Période d'évaluation (cohérent maquette '12 mois')")
    estimated: ImpactDimension
    at_risk: ImpactDimension
    secured: ImpactDimension
    realized: ImpactDimension
    # `dimension` legacy : la dimension dominante actuellement enregistrée
    # dans `impact_dimension` (un seul champ legacy, sera décommissionné M3+).
    dominant_dimension: Optional[str] = Field(None, max_length=20)
    # `has_data` : false si toutes les dimensions sont null → l'UI affiche un
    # empty state explicite « Impact non encore calculé pour cet item ».
    has_data: bool


class ActionCenterSummaryResponse(BaseModel):
    """M2-5.11.C — Réponse de GET /api/v4/action-center/summary.

    5 compteurs agrégés org-scopés alimentant la `NarrativeBar` Sol posée au
    sommet des pages Référentiel + Pilotage (vue CFO « combien d'urgence,
    combien de risque, combien de preuve »).

    Définitions canoniques (toutes restreintes au scope `organisation_id`
    courant via `_apply_scope`, fail-closed) :

    - `count_p0` / `count_p1` : items actifs (lifecycle ≠ closed) au bracket
      P0 / P1 (axe dérivé `priority_bracket`, doctrine v0.3 §4.2).
    - `count_without_owner` : items actifs sans assignee. Le champ
      `owner_id` existe sur le model (M2-4.2) mais l'endpoint d'assignation
      arrive en M2-5.11.E ; ce compteur est utilisable dès maintenant pour
      mesurer la dette d'attribution.
    - `count_at_risk` : items actifs avec ≥ 1 blocker non-résolu
      (`resolved_at IS NULL`). Le pan « in_progress > 14j » de la doctrine
      est reporté M2-5.11.F (exige scan event_log, hors V1).
    - `count_secured` : items actifs avec ≥ 1 evidence vérifiée
      (`verified_at IS NOT NULL`) — preuve auditée disponible.
    """

    model_config = ConfigDict(extra="forbid")

    count_p0: int = Field(..., ge=0)
    count_p1: int = Field(..., ge=0)
    count_without_owner: int = Field(..., ge=0)
    count_at_risk: int = Field(..., ge=0)
    count_secured: int = Field(..., ge=0)


# ── Requests write (M2-4.4) ──────────────────────────────────────────
#
# Tous `extra="forbid"`. Les champs serveur-gérés / dérivés ne sont jamais
# acceptés en body (organisation_id forcé par le repo ; priority_* dérivée M2-5 ;
# lifecycle_state via PATCH /lifecycle ; kind via endpoint admin dédié — IS5).


class ActionCenterItemUpdate(BaseModel):
    """Body PATCH /items/{id} — update partiel des champs cosmétiques SEULEMENT.

    Hors périmètre (endpoints dédiés) : `kind` (IS5 admin-sensible),
    `lifecycle_state`/`closure_reason` (PATCH /lifecycle), `priority_*`/`score_*`
    (axe dérivé M2-5), `organisation_id` (forcé par le repo).
    """

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    domain: Optional[str] = Field(None, max_length=30)


class LifecycleTransitionRequest(BaseModel):
    """Body PATCH /items/{id}/lifecycle.

    `closure_reason` : requise SSI `new_state == closed` ; refusée sinon ;
    les valeurs system-only sont rejetées en 422 (cf. lifecycle_validator).
    `comment` → metadata de l'event `state_changed` (pas de colonne dédiée).
    """

    model_config = ConfigDict(extra="forbid")

    new_state: LifecycleState
    closure_reason: Optional[ClosureReason] = None
    comment: Optional[str] = Field(None, max_length=500)


class EvidenceVerifyRequest(BaseModel):
    """Body PATCH /evidences/{id}/verify.

    ADR-029 : pas d'enum `status`. Sémantique portée par `verified_at` +
    `verified_by` + `expires_at`. `expires_at` optionnel → défaut verified_at+90j.
    `comment` → metadata de l'event (pas de colonne sur Evidence).
    """

    model_config = ConfigDict(extra="forbid")

    expires_at: Optional[datetime] = None
    comment: Optional[str] = Field(None, max_length=500)


class BlockerCreate(BaseModel):
    """Body POST /items/{id}/blockers. `justification` = motif (colonne modèle)."""

    model_config = ConfigDict(extra="forbid")

    blocker_type: BlockerType
    justification: str = Field(..., min_length=3, max_length=2000)
    expected_resolution_at: Optional[datetime] = None


class BlockerResolveRequest(BaseModel):
    """Body PATCH /blockers/{id}/resolve.

    `resolution_comment` → metadata de l'event `blocker_removed` (le modèle
    ActionBlocker n'a pas de colonne dédiée).
    """

    model_config = ConfigDict(extra="forbid")

    resolution_comment: Optional[str] = Field(None, max_length=500)


class ActionLinkCreate(BaseModel):
    """Body POST /items/{id}/links — cible polymorphe.

    `target_module` : enum strict (7 valeurs, 1 implémentée, 6 → 501).
    `target_id` : vérifié côté serveur comme appartenant au scope org courant.
    `link_type` et `relation` sont NOT NULL au niveau modèle → requis.
    """

    model_config = ConfigDict(extra="forbid")

    target_module: TargetModule
    target_id: UUID
    link_type: str = Field(..., min_length=2, max_length=40)
    relation: str = Field(..., min_length=2, max_length=40)
