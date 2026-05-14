# BRIEF ADR-028 · Lifecycle states Centre d'Action V4

> **Statut** : `Proposed` → à acter par Amine avant production L5
> **Version** : v0.1
> **Date** : 2026-05-14
> **Branche cible** : `claude/refonte-sol2`
> **Doctrine source** : `docs/doctrine/doctrine_v4_classement_priorisation.md` v0.2
> **ADR amont** : ADR-022 · ADR-025 · ADR-026 · ADR-027
> **Auteurs** : Amine + Claude (cadrage session 2026-05-14)

---

## 0. TL;DR exécutif

**ADR-028 = manuel de comportement de l'item.** Fige la state machine `ActionCenterItem` : 5 lifecycle states + 10 transitions strictes + 6 closure_reasons révisés + hooks Python explicites + protections cardinales sur clôture.

**11 invariants lifecycle non négociables (IL1-IL11)** :

| # | Invariant |
|---|---|
| IL1 | Toutes transitions invalides → **HTTP 409 Conflict** avec payload `{code, message, hint}` |
| IL2 | `closed → new` **impossible** (terminal pour le flow user) |
| IL3 | `closed → triaged` uniquement **admin + fresh token (<5min) + justification non vide** |
| IL4 | `expired` **interdit sur conformité/facturation P0/P1** (escalade prioritaire) |
| IL5 | `merged_duplicate` **interdit si** `recurrence_group_id` existe sans `duplicate_group_id` |
| IL6 | Auto-close récurrence **exige** `recurrence_group.status = resolved` |
| IL7 | Auto-close récurrence **P0/P1 exige preuve ou justification** |
| IL8 | Chaque transition écrit dans `action_event_log` (cohérent ADR-029) |
| IL9 | Chaque transition déclenche `score_stale = TRUE` (cohérent ADR-025 §4.4) |
| IL10 | Frontend attend réponse serveur avant d'afficher le nouvel état (wait-for-server) |
| IL11 | Réouverture admin trace event `reopened` avec `justification` non vide dans payload |

**7 arbitrages techniques Q33-Q39 actés** :

| Q | Décision finale |
|---|---|
| Q33-B | Enum `LifecycleState` + dict `VALID_TRANSITIONS` manuel (zéro dépendance) |
| Q34-A | HTTP 409 Conflict avec payload `{code, message, hint, correlation_id}` |
| Q35-A | Méthodes Python explicites `_before_transition` / `_after_transition` |
| Q36-C+ | Réouverture admin + `admin_only_with_fresh_token` + `justification` obligatoire |
| Q37-A+ | Auto-close récurrence avec `closure_reason=resolved_via_recurrence` (≠ `merged_duplicate`) |
| Q38-B | Lifecycle events dans `action_event_log` métier, séparé de `security_audit_log` |
| Q39-B | Frontend wait-for-server (pas d'optimistic UI) |

**5 états doctrinaux figés** : `new` → `triaged` → `planned` → `in_progress` → `closed`

**10 transitions strictes** (no-ops `closed → closed` et `triaged → triaged` exclus).

**6 closure_reasons révisés** : `resolved` · `dismissed` · `not_applicable` · `merged_duplicate` · `resolved_via_recurrence` · `expired` (avec IL4).

---

## 1. Périmètre et hors-scope

### 1.1 Périmètre ADR-028

L'ADR couvre :

- Définition formelle des 5 lifecycle states (enum)
- Matrice 10 transitions strictes avec rôle, hooks, closure_reason autorisés
- Service `LifecycleStateMachine` Python (code complet)
- Hooks pré-transition (`_before_transition`) et post-transition (`_after_transition`)
- 6 closure_reasons révisés avec sémantique stats
- Auto-close récurrence (Q37-A+) avec garde-fous P0/P1
- Réouverture admin (Q36-C+) avec justification obligatoire
- Interdiction `expired` sur P0/P1 conformité/facturation (IL4)
- Endpoint API `PATCH /lifecycle` + `PATCH /reopen` (admin)
- Frontend wait-for-server (IL10)
- 60+ tests générés (matrice complète × roles × closure_reasons)

### 1.2 Hors-scope ADR-028

- **ADR-025** : schéma DB (déjà acté, CHECK constraints cardinaux)
- **ADR-026** : migration data (déjà acté)
- **ADR-027** : sécurité org-scoping + `admin_only_with_fresh_token` (déjà acté)
- **ADR-029 Evidence + audit trail** : rétention `action_event_log` par event_type, formats evidence
- **Notifications utilisateur** : email/Slack/in-app (couvert par ADR-030 ou skill notifications)
- **Workflows d'escalade SLA dépassé** : couvert par sprint Phase 3.5 + ADR-022 priorisation

---

## 2. State machine — 5 états doctrinaux

### 2.1 Enum `LifecycleState`

```python
# backend/models/enums/lifecycle.py
from enum import Enum

class LifecycleState(str, Enum):
    """5 lifecycle states doctrine v0.2 §7.1."""
    NEW = "new"
    TRIAGED = "triaged"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

class ClosureReason(str, Enum):
    """6 closure_reasons révisés (cf. §4)."""
    RESOLVED = "resolved"                              # Problème résolu + preuve vérifiée
    DISMISSED = "dismissed"                            # Item écarté
    NOT_APPLICABLE = "not_applicable"                  # Réglementation non-applicable
    MERGED_DUPLICATE = "merged_duplicate"              # Q9-B duplicate_group only
    RESOLVED_VIA_RECURRENCE = "resolved_via_recurrence" # Auto-close cascade Q37-A+
    EXPIRED = "expired"                                # SLA dépassé · IL4 P0/P1 interdit
```

### 2.2 Sémantique des 5 états

| État | Sémantique | Affichage UI | Couleur doctrine |
|---|---|---|---|
| `new` | Détecté · non encore qualifié | "Nouveau" | gris attention |
| `triaged` | Qualifié · prioritaire identifié | "Qualifié" | calme |
| `planned` | Plan d'action défini · owner assigné | "Planifié" | calme |
| `in_progress` | Action en cours · awaiting closure | "En cours" | calme accent |
| `closed` | Terminé · closure_reason + preuve | "Clôturé" | succès |

---

## 3. Matrice 10 transitions strictes

### 3.1 Tableau complet

```
SOURCE        ACTION              TARGET           ROLE AUTORISÉ              CLOSURE_REASON ACCEPTÉS   HOOKS CARDINAUX
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
new           qualify             triaged          user, admin                —                         verify_kind_set + verify_priority_calculated
new           qualify_system      triaged          system                     —                         from regulatory_applicability_service Q4-A
new           dismiss             closed           user, admin                dismissed                 require_justification (non-empty)
triaged       plan                planned          user, admin                —                         verify_has_owner
triaged       start               in_progress      user, admin                —                         verify_has_owner + verify_no_active_blocker
triaged       close               closed           user, admin                {resolved, not_applicable, merged_duplicate, dismissed}  closure_workflow
planned       start               in_progress      user, admin                —                         verify_no_active_blocker
planned       close               closed           user, admin                {resolved, not_applicable, dismissed}                    closure_workflow
in_progress   close               closed           user, admin                {resolved, dismissed, expired*}                          closure_workflow + *IL4 check
closed        reopen              triaged          ADMIN ONLY + fresh + just  —                         event="reopened" + IL11 justification
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Total : 10 transitions strictes

* expired interdit si domain ∈ {conformite, facturation} ET priority_bracket ∈ {P0, P1} (IL4)
```

### 3.2 Implémentation Q33-B (enum + dict)

```python
# backend/services/lifecycle/state_machine.py

from typing import Optional
from uuid import UUID

VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.NEW: {
        LifecycleState.TRIAGED,
        LifecycleState.CLOSED,
    },
    LifecycleState.TRIAGED: {
        LifecycleState.PLANNED,
        LifecycleState.IN_PROGRESS,
        LifecycleState.CLOSED,
    },
    LifecycleState.PLANNED: {
        LifecycleState.IN_PROGRESS,
        LifecycleState.CLOSED,
    },
    LifecycleState.IN_PROGRESS: {
        LifecycleState.CLOSED,
    },
    LifecycleState.CLOSED: {
        LifecycleState.TRIAGED,  # IL3 : admin + fresh token + justification only
    },
}


# Matrice closure_reasons autorisés par état source
CLOSURE_REASONS_BY_SOURCE: dict[LifecycleState, set[ClosureReason]] = {
    LifecycleState.NEW: {ClosureReason.DISMISSED},
    LifecycleState.TRIAGED: {
        ClosureReason.RESOLVED,
        ClosureReason.NOT_APPLICABLE,
        ClosureReason.MERGED_DUPLICATE,
        ClosureReason.DISMISSED,
    },
    LifecycleState.PLANNED: {
        ClosureReason.RESOLVED,
        ClosureReason.NOT_APPLICABLE,
        ClosureReason.DISMISSED,
    },
    LifecycleState.IN_PROGRESS: {
        ClosureReason.RESOLVED,
        ClosureReason.DISMISSED,
        ClosureReason.EXPIRED,  # IL4 check supplémentaire
    },
}
```

### 3.3 Hooks par transition

```python
# backend/services/lifecycle/hooks.py

# Map transition (source, target) → liste de hooks pré-transition
PRE_TRANSITION_HOOKS: dict[tuple[LifecycleState, LifecycleState], list[str]] = {
    (LifecycleState.NEW, LifecycleState.TRIAGED): [
        "verify_kind_set",
        "verify_priority_calculated",
    ],
    (LifecycleState.NEW, LifecycleState.CLOSED): [
        "require_justification",
    ],
    (LifecycleState.TRIAGED, LifecycleState.PLANNED): [
        "verify_has_owner",
    ],
    (LifecycleState.TRIAGED, LifecycleState.IN_PROGRESS): [
        "verify_has_owner",
        "verify_no_active_blocker",
    ],
    (LifecycleState.PLANNED, LifecycleState.IN_PROGRESS): [
        "verify_no_active_blocker",
    ],
    (LifecycleState.CLOSED, LifecycleState.TRIAGED): [
        "verify_admin_role",          # IS5 ADR-027
        "verify_fresh_token",          # IS5 ADR-027
        "require_justification",       # IL11
    ],
    # close from any state
    ("*", LifecycleState.CLOSED): [
        "verify_closure_reason_valid",  # IL4 check P0/P1 expired
    ],
}

POST_TRANSITION_HOOKS_ALL: list[str] = [
    "write_action_event_log",       # IL8
    "invalidate_score_stale",       # IL9
    "trigger_notifications",        # async, hors-scope ADR-028
]

POST_TRANSITION_HOOKS_BY_TARGET: dict[LifecycleState, list[str]] = {
    LifecycleState.CLOSED: [
        "handle_evidence_finalization",     # cohérent ADR-029
        "update_recurrence_group_stats",    # if recurrence_group_id
        "trigger_compliance_dossier_update", # if domain=conformite
    ],
    LifecycleState.TRIAGED: [
        # post-réouverture
        "log_reopen_audit_trail",
    ],
}
```

---

## 4. Closure reasons révisés (6 valeurs)

### 4.1 Tableau sémantique + impact stats

| Closure reason | Quand l'utiliser | Impact stats M4 | Garde-fous IL |
|---|---|---|---|
| `resolved` | Problème résolu **avec preuve vérifiée** | Compte dans "Réalisé" · ROI positif | Evidence obligatoire si domain=conformite |
| `dismissed` | Item écarté (faux positif, doublon manuel sans groupe, hors-scope) | Compte dans "Perdu" · pas dans ROI | `require_justification` IL3-like |
| `not_applicable` | Réglementation non-applicable (site fermé, seuil changé) | Neutre · pas dans ROI | Verify `regulatory_applicability_service` Q4-A |
| `merged_duplicate` | Item fusionné dans `duplicate_group` (Q9-B doublons stricts) | Neutre · gain visibilité dans groupe | IL5 interdit si `recurrence_group_id` |
| `resolved_via_recurrence` | Auto-fermé car `recurrence_group.status = resolved` | Compte dans "Réalisé" · attribué au groupe | IL6 + IL7 (P0/P1 exige preuve) |
| `expired` | SLA dépassé sans action | Compte dans "Perdu" | **IL4 interdit P0/P1 conformite/facturation** |

### 4.2 Code de validation `expired`

```python
def verify_closure_reason_valid(item: ActionCenterItem, closure_reason: ClosureReason, actor):
    """
    IL4 : expired interdit sur P0/P1 conformité/facturation.
    IL5 : merged_duplicate interdit si recurrence_group sans duplicate_group.
    """
    if closure_reason == ClosureReason.EXPIRED:
        if item.domain in ["conformite", "facturation"] and item.priority_bracket in ["P0", "P1"]:
            raise InvalidClosureError(
                code="EXPIRED_FORBIDDEN_ON_ACTIVE_PRIORITY",
                message=f"Cannot mark P0/P1 {item.domain} item as expired",
                hint="Active compliance/billing risks must be escalated, not silently expired. "
                     "Use the escalation workflow or reassign owner."
            )

    if closure_reason == ClosureReason.MERGED_DUPLICATE:
        if item.recurrence_group_id is not None and item.duplicate_group_id is None:
            raise InvalidClosureError(
                code="MERGED_DUPLICATE_FORBIDDEN_ON_RECURRENCE",
                message="Cannot use merged_duplicate for a recurrence_group item",
                hint="Recurrence ≠ duplicate (Q9-B). Use resolved_via_recurrence "
                     "(auto-triggered when recurrence_group resolves) instead."
            )

    return True
```

### 4.3 Auto-close récurrence (Q37-A+ · IL6 · IL7)

```python
# backend/services/lifecycle/recurrence_cascade.py

def on_recurrence_group_resolved(group: RecurrenceGroup, actor: User):
    """
    Q37-A+ : auto-close cascade avec garde-fous IL6 + IL7.

    IL6 : exige group.status = resolved
    IL7 : P0/P1 exigent preuve OU justification
    """
    if group.status != RecurrenceGroupStatus.RESOLVED:
        raise InvalidCascadeError(
            code="RECURRENCE_CASCADE_REQUIRES_RESOLVED_GROUP",
            message="Cannot cascade auto-close without group.status=resolved"
        )

    active_items = repo.list_items_by_recurrence_group(
        group.id,
        statuses_excluded=[LifecycleState.CLOSED]
    )

    skipped_p0_p1 = []
    for item in active_items:
        # IL7 : P0/P1 exigent preuve ou justification
        if item.priority_bracket in ["P0", "P1"]:
            has_evidence = repo.has_verified_evidence(item.id)
            has_justification = group.resolution_justification is not None and len(group.resolution_justification) > 10
            if not (has_evidence or has_justification):
                skipped_p0_p1.append(item.id)
                log_security_event(
                    event_type="auto_close.recurrence.skipped",
                    item_id=item.id,
                    severity="warning",
                    reason="P0/P1 without evidence or justification (IL7)"
                )
                continue

        machine.transition(
            item,
            target=LifecycleState.CLOSED,
            actor=actor,
            closure_reason=ClosureReason.RESOLVED_VIA_RECURRENCE,
            extra_payload={
                "auto_closed_by_group_id": str(group.id),
                "group_resolution_date": group.resolved_at.isoformat(),
                "group_resolution_justification": group.resolution_justification,
                "trigger": "system.recurrence.cascade"
            }
        )

    if skipped_p0_p1:
        # Trigger workflow : ces items P0/P1 doivent être traités manuellement
        log_audit("recurrence.cascade.partial", skipped=skipped_p0_p1, group_id=group.id)
```

---

## 5. Service `LifecycleStateMachine` complet (Q35-A)

```python
# backend/services/lifecycle/state_machine.py

from typing import Optional
from uuid import UUID

class LifecycleStateMachine:
    """
    State machine des items Centre d'Action.
    Q35-A : méthodes Python explicites (pas de signals magiques).
    """

    def __init__(self, repository: ActionCenterRepository, event_log: ActionEventLogRepository):
        self.repo = repository
        self.event_log = event_log

    def transition(
        self,
        item: ActionCenterItem,
        target: LifecycleState,
        actor: User,
        closure_reason: Optional[ClosureReason] = None,
        justification: Optional[str] = None,
        extra_payload: Optional[dict] = None,
    ) -> ActionCenterItem:
        """
        Transition unique avec hooks pré/post.

        Raises:
            InvalidTransitionError : si transition non autorisée (IL1 → HTTP 409)
            InvalidClosureError : si closure_reason invalide (IL4, IL5)
        """
        # ─── Pre-transition checks ───
        self._before_transition(item, target, actor, closure_reason, justification)

        # ─── State change atomique ───
        old_state = item.lifecycle_state
        item.lifecycle_state = target

        if target == LifecycleState.CLOSED:
            item.closed_at = datetime.utcnow()
            item.closure_reason = closure_reason
            item.closure_payload = {
                "justification": justification,
                "actor_id": str(actor.id),
                **(extra_payload or {}),
            }

        # ─── Post-transition effects ───
        self._after_transition(item, old_state, target, actor, closure_reason, justification, extra_payload)

        return item

    def _before_transition(
        self,
        item: ActionCenterItem,
        target: LifecycleState,
        actor: User,
        closure_reason: Optional[ClosureReason],
        justification: Optional[str],
    ):
        # IL1 : check transition valide
        if target not in VALID_TRANSITIONS[item.lifecycle_state]:
            raise InvalidTransitionError(
                source=item.lifecycle_state,
                target=target,
                valid_targets=list(VALID_TRANSITIONS[item.lifecycle_state])
            )

        # Réouverture admin (IL3 · IL11)
        if item.lifecycle_state == LifecycleState.CLOSED and target == LifecycleState.TRIAGED:
            self._verify_admin_role(actor)
            self._verify_fresh_token(actor)  # < 5min (IS5 ADR-027)
            self._require_justification(justification)

        # Transitions vers closed
        if target == LifecycleState.CLOSED:
            if closure_reason is None:
                raise InvalidClosureError(
                    code="CLOSURE_REASON_REQUIRED",
                    message="Closing an item requires a closure_reason",
                    hint=f"Valid closure_reasons: {CLOSURE_REASONS_BY_SOURCE[item.lifecycle_state]}"
                )

            # IL4 + IL5 checks
            verify_closure_reason_valid(item, closure_reason, actor)

            # Closure reason autorisé pour cet état source
            if closure_reason not in CLOSURE_REASONS_BY_SOURCE.get(item.lifecycle_state, set()):
                # Exception : RESOLVED_VIA_RECURRENCE est autorisé depuis tous les états (system trigger)
                if closure_reason != ClosureReason.RESOLVED_VIA_RECURRENCE:
                    raise InvalidClosureError(
                        code="CLOSURE_REASON_INVALID_FOR_SOURCE",
                        message=f"Cannot close from {item.lifecycle_state} with reason {closure_reason}",
                        hint=f"Valid reasons from {item.lifecycle_state}: {CLOSURE_REASONS_BY_SOURCE[item.lifecycle_state]}"
                    )

        # Hooks spécifiques (verify_has_owner, verify_no_blocker, etc.)
        hook_names = PRE_TRANSITION_HOOKS.get((item.lifecycle_state, target), [])
        for hook_name in hook_names:
            getattr(self, hook_name)(item, actor, justification)

    def _after_transition(
        self,
        item: ActionCenterItem,
        old_state: LifecycleState,
        new_state: LifecycleState,
        actor: User,
        closure_reason: Optional[ClosureReason],
        justification: Optional[str],
        extra_payload: Optional[dict],
    ):
        # IL8 : audit trail
        self.event_log.write(
            item_id=item.id,
            organisation_id=item.organisation_id,
            event_type="state_changed",
            actor_type="user" if not actor.is_system else "system",
            actor_id=actor.id if not actor.is_system else None,
            actor_name=actor.name,
            event_payload={
                "from": old_state.value,
                "to": new_state.value,
                "closure_reason": closure_reason.value if closure_reason else None,
                "justification": justification,
                **(extra_payload or {}),
            },
        )

        # IL9 : score invalidation
        item.score_stale = True

        # Hooks post par target
        hook_names = POST_TRANSITION_HOOKS_BY_TARGET.get(new_state, [])
        for hook_name in hook_names:
            getattr(self, hook_name)(item, old_state, actor)

        # Persistence
        self.repo.save(item)

    # ─── Hooks ───────────────────────────────────────────────

    def _verify_admin_role(self, actor: User):
        if actor.role != "admin":
            raise InvalidTransitionError(
                code="REOPEN_REQUIRES_ADMIN",
                message="Only admins can reopen closed items"
            )

    def _verify_fresh_token(self, actor: User):
        # Fresh token < 5min (IS5 ADR-027)
        if actor.token_age_seconds > 300:
            raise InvalidTransitionError(
                code="REOPEN_REQUIRES_FRESH_TOKEN",
                message="Reopening requires a token issued < 5 minutes ago",
                hint="Re-authenticate to perform admin actions"
            )

    def _require_justification(self, justification: Optional[str]):
        # IL3, IL11
        if not justification or len(justification.strip()) < 10:
            raise InvalidTransitionError(
                code="REOPEN_REQUIRES_JUSTIFICATION",
                message="Reopening requires a justification (min 10 characters)"
            )

    def verify_kind_set(self, item, actor, justification):
        if item.kind is None:
            raise InvalidTransitionError(...)

    def verify_priority_calculated(self, item, actor, justification):
        if item.priority_score is None:
            raise InvalidTransitionError(...)

    def verify_has_owner(self, item, actor, justification):
        if item.owner_id is None:
            raise InvalidTransitionError(
                code="MISSING_OWNER",
                message="This transition requires an assigned owner",
                hint="Assign an owner first"
            )

    def verify_no_active_blocker(self, item, actor, justification):
        blockers = self.repo.list_active_blockers(item.id)
        if blockers:
            raise InvalidTransitionError(
                code="ACTIVE_BLOCKER_PRESENT",
                message=f"Cannot proceed: {len(blockers)} active blocker(s)",
                hint=f"Resolve blockers first: {[b.blocker_type for b in blockers]}"
            )


class InvalidTransitionError(Exception):
    """Mappé à HTTP 409 Conflict (IL1)."""
    def __init__(self, source=None, target=None, valid_targets=None, code=None, message=None, hint=None):
        self.source = source
        self.target = target
        self.valid_targets = valid_targets
        self.code = code or "INVALID_LIFECYCLE_TRANSITION"
        self.message = message or f"Cannot transition from {source} to {target}"
        self.hint = hint or f"Valid transitions from {source}: {valid_targets}"


class InvalidClosureError(Exception):
    """Mappé à HTTP 409 Conflict (IL1)."""
    def __init__(self, code, message, hint=None):
        self.code = code
        self.message = message
        self.hint = hint
```

---

## 6. API endpoints

### 6.1 `PATCH /api/action-center/items/{id}/lifecycle`

```python
# backend/api/action_center/lifecycle.py

from backend.decorators import org_scoped
from backend.services.lifecycle import LifecycleStateMachine

class PatchLifecycleRequest(BaseModel):
    target_state: LifecycleState
    closure_reason: Optional[ClosureReason] = None
    justification: Optional[str] = None
    extra_payload: Optional[dict] = None


@router.patch("/api/action-center/items/{item_id}/lifecycle")
@org_scoped(allowed_roles=["admin", "user"])  # IS4 viewer = 403
async def patch_lifecycle(
    item_id: UUID,
    payload: PatchLifecycleRequest,
    request: Request,
    repo: ActionCenterRepository = Depends(get_repo),
    machine: LifecycleStateMachine = Depends(get_machine),
):
    item = repo.get_by_id(item_id, organisation_id=request.state.organisation_id)
    if not item:
        raise HTTPException(404)  # IS3 anti-énumération

    try:
        actor = build_actor(request)
        updated = machine.transition(
            item,
            target=payload.target_state,
            actor=actor,
            closure_reason=payload.closure_reason,
            justification=payload.justification,
            extra_payload=payload.extra_payload,
        )
        return updated
    except (InvalidTransitionError, InvalidClosureError) as e:
        # IL1 : HTTP 409 Conflict
        raise HTTPException(
            status_code=409,
            detail={
                "code": e.code,
                "message": e.message,
                "hint": e.hint,
                "correlation_id": request.state.correlation_id,
            }
        )
```

### 6.2 `PATCH /api/action-center/items/{id}/reopen` (admin)

```python
class ReopenRequest(BaseModel):
    justification: str  # IL11 obligatoire, validated min 10 chars


@router.patch("/api/action-center/items/{item_id}/reopen")
@admin_only_with_fresh_token  # IS5 ADR-027 · IL3
async def reopen_item(
    item_id: UUID,
    payload: ReopenRequest,
    request: Request,
    repo: ActionCenterRepository = Depends(get_repo),
    machine: LifecycleStateMachine = Depends(get_machine),
):
    item = repo.get_by_id(item_id, organisation_id=request.state.organisation_id)
    if not item or item.lifecycle_state != LifecycleState.CLOSED:
        raise HTTPException(404)

    try:
        actor = build_actor(request)
        updated = machine.transition(
            item,
            target=LifecycleState.TRIAGED,
            actor=actor,
            justification=payload.justification,
        )
        return updated
    except InvalidTransitionError as e:
        raise HTTPException(409, ...)
```

---

## 7. Frontend wait-for-server (Q39-B · IL10)

```typescript
// frontend/src/services/lifecycle.ts

export async function transitionLifecycle(
  itemId: string,
  targetState: LifecycleState,
  closureReason?: ClosureReason,
  justification?: string,
): Promise<ActionCenterItem> {
  // IL10 : ne PAS faire optimistic update
  // Le bouton doit montrer un loader pendant l'appel
  const response = await api.patch(
    `/api/action-center/items/${itemId}/lifecycle`,
    {
      target_state: targetState,
      closure_reason: closureReason,
      justification,
    }
  );

  // Apply server response only on success
  return response.data;
}


// frontend/src/components/LifecycleActionButton.tsx
export function LifecycleActionButton({ item, action }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await transitionLifecycle(item.id, action.targetState);
      onSuccess(updated);
    } catch (err) {
      if (err.response?.status === 409) {
        // IL1 : transition interdite
        setError(err.response.data.detail.message);
        // Optionnel : afficher hint pour l'utilisateur
        showToast(err.response.data.detail.hint);
      } else {
        setError("Erreur réseau, réessayez");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <button onClick={handleClick} disabled={loading}>
      {loading ? <Spinner /> : action.label}
    </button>
  );
}
```

**Budget perf** : transition < 150ms (cohérent ADR-025 §9). 150ms loader est acceptable UX.

---

## 8. Tests générés (60+ unit + intégration)

### 8.1 Matrice transitions (50 tests générés)

```python
# tests/unit/lifecycle/test_transitions_matrix.py

import pytest
from itertools import product

ALL_STATES = list(LifecycleState)
ALL_TRANSITIONS = list(product(ALL_STATES, ALL_STATES))

@pytest.mark.parametrize("source,target", ALL_TRANSITIONS)
def test_transition_matrix(source, target):
    item = make_item(state=source)
    machine = LifecycleStateMachine(...)

    if target in VALID_TRANSITIONS[source]:
        # Devrait réussir (avec hooks satisfaits)
        result = machine.transition(item, target, actor=admin_user_with_fresh_token, ...)
        assert result.lifecycle_state == target
    else:
        # Devrait échouer avec InvalidTransitionError → HTTP 409
        with pytest.raises(InvalidTransitionError):
            machine.transition(item, target, actor=admin_user_with_fresh_token)
```

5 × 5 = 25 cellules. 10 valides + 15 invalides → 25 tests générés.

### 8.2 Closure reasons par état (20 tests générés)

```python
@pytest.mark.parametrize("source", [LifecycleState.TRIAGED, LifecycleState.PLANNED, LifecycleState.IN_PROGRESS])
@pytest.mark.parametrize("closure_reason", list(ClosureReason))
def test_closure_reason_validity(source, closure_reason):
    item = make_item(state=source)
    if closure_reason in CLOSURE_REASONS_BY_SOURCE.get(source, set()):
        # Devrait réussir
        machine.transition(item, LifecycleState.CLOSED, closure_reason=closure_reason, ...)
    else:
        with pytest.raises(InvalidClosureError):
            machine.transition(...)
```

### 8.3 Tests cardinaux (10 tests métier)

```python
def test_IL1_invalid_transition_returns_409():
    item = make_item(state=LifecycleState.CLOSED)
    response = client.patch(f"/api/action-center/items/{item.id}/lifecycle",
                            json={"target_state": "new"})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "INVALID_LIFECYCLE_TRANSITION"

def test_IL2_closed_to_new_impossible():
    # Aucun chemin ne mène à NEW depuis CLOSED
    item = make_item(state=LifecycleState.CLOSED)
    with pytest.raises(InvalidTransitionError):
        machine.transition(item, LifecycleState.NEW, actor=admin)

def test_IL3_reopen_requires_admin_fresh_token_justification():
    item = make_item(state=LifecycleState.CLOSED)
    # Non-admin → 403
    response = client.patch(f"/api/action-center/items/{item.id}/reopen",
                            json={"justification": "Erreur de clôture"},
                            headers={"Authorization": user_token})
    assert response.status_code == 403

    # Admin + token vieux → 403
    response = client.patch(...,
                            headers={"Authorization": admin_old_token})
    assert response.status_code == 403

    # Admin + fresh + sans justification → 409
    response = client.patch(...,
                            json={"justification": ""},
                            headers={"Authorization": admin_fresh_token})
    assert response.status_code == 409

    # Admin + fresh + justification → 200
    response = client.patch(...,
                            json={"justification": "Erreur opérateur, à corriger"},
                            headers={"Authorization": admin_fresh_token})
    assert response.status_code == 200

def test_IL4_expired_forbidden_on_p0_compliance():
    item = make_item(
        state=LifecycleState.IN_PROGRESS,
        domain="conformite",
        priority_bracket="P0"
    )
    with pytest.raises(InvalidClosureError) as exc:
        machine.transition(item, LifecycleState.CLOSED, closure_reason=ClosureReason.EXPIRED)
    assert exc.value.code == "EXPIRED_FORBIDDEN_ON_ACTIVE_PRIORITY"

def test_IL5_merged_duplicate_forbidden_on_recurrence_only():
    item = make_item(
        state=LifecycleState.TRIAGED,
        recurrence_group_id=uuid4(),
        duplicate_group_id=None
    )
    with pytest.raises(InvalidClosureError) as exc:
        machine.transition(item, LifecycleState.CLOSED, closure_reason=ClosureReason.MERGED_DUPLICATE)
    assert exc.value.code == "MERGED_DUPLICATE_FORBIDDEN_ON_RECURRENCE"

def test_IL6_auto_close_recurrence_requires_resolved_group():
    group = make_recurrence_group(status="active")  # not resolved
    with pytest.raises(InvalidCascadeError):
        on_recurrence_group_resolved(group, actor=system)

def test_IL7_auto_close_p0_recurrence_requires_evidence_or_justification():
    group = make_recurrence_group(status="resolved", resolution_justification=None)
    p0_item = make_item(priority_bracket="P0", recurrence_group_id=group.id)
    on_recurrence_group_resolved(group, actor=system)
    # p0_item devrait être SKIPPED
    assert p0_item.lifecycle_state != LifecycleState.CLOSED

def test_IL8_every_transition_writes_event_log():
    item = make_item(state=LifecycleState.NEW)
    machine.transition(item, LifecycleState.TRIAGED, actor=user)
    events = event_log_repo.list_by_item(item.id)
    assert any(e.event_type == "state_changed" for e in events)

def test_IL9_every_transition_invalidates_score():
    item = make_item(state=LifecycleState.NEW, score_stale=False)
    machine.transition(item, LifecycleState.TRIAGED, actor=user)
    assert item.score_stale is True

def test_IL10_frontend_waits_for_server():
    # Vérification UI : pas d'optimistic update
    # Test e2e Playwright (cf. ADR-025 §8.4)
    pass

def test_IL11_reopen_event_has_justification():
    item = make_item(state=LifecycleState.CLOSED)
    machine.transition(item, LifecycleState.TRIAGED,
                       actor=admin_fresh,
                       justification="Erreur opérateur lors du sprint X")
    events = event_log_repo.list_by_item(item.id)
    reopen_event = next(e for e in events if e.event_type == "state_changed"
                        and e.event_payload["to"] == "triaged")
    assert reopen_event.event_payload["justification"] == "Erreur opérateur lors du sprint X"
```

**Total tests ADR-028** : 25 matrice transitions + 20 closure_reasons + 11 invariants IL1-IL11 = **56 tests minimum**.

---

## 9. Effets de bord système (pas des transitions)

### 9.1 Tableau

```
EFFET                                  DÉCLENCHEUR                                  COMPORTEMENT
──────────────────────────────────────────────────────────────────────────────────────────────
auto_close_via_recurrence_resolved     RecurrenceGroup.status → resolved            Cascade close avec resolved_via_recurrence
                                                                                     (skip P0/P1 sans preuve, IL7)

merge_into_duplicate_group             Action manuelle "Fusionner" sur duplicate_group  Close items du groupe avec merged_duplicate
                                                                                     (Q9-B duplicate only, IL5)

escalation_on_sla_overdue              SLA dépassé sur P0/P1                        PAS de transition automatique
                                                                                     Trigger workflow d'escalade (notification manager,
                                                                                     slack alert, log audit)
                                                                                     L'item RESTE in_progress jusqu'à action manuelle

system_dismiss_on_not_applicable       regulatory_applicability_service Q4-A          Auto-close avec not_applicable
                                       déclare règle non-applicable                  Si owner_id == None : auto sans validation
                                                                                     Si owner_id != None : notification only
```

---

## 10. Mapping libellés FR mode standard (cohérent doctrine §7.1)

| event_type API | Libellé FR mode standard |
|---|---|
| `state_changed` (new → triaged) | "Qualifié" |
| `state_changed` (triaged → planned) | "Planifié" |
| `state_changed` (planned → in_progress) | "En cours" |
| `state_changed` (any → closed) | "Clôturé" |
| `state_changed` (closed → triaged) | "Réouvert" |
| `closure_reason=resolved` | "Résolu" |
| `closure_reason=dismissed` | "Écarté" |
| `closure_reason=not_applicable` | "Non applicable" |
| `closure_reason=merged_duplicate` | "Fusionné (doublon)" |
| `closure_reason=resolved_via_recurrence` | "Résolu via récurrence" |
| `closure_reason=expired` | "Expiré" |

---

## 11. Renvois ADR amont/aval

- **ADR-022** : composantes du score (R6 plancher P1 conformité, etc.)
- **ADR-025** : schéma DB (`lifecycle_state` CHECK constraint, `closure_consistency` constraint)
- **ADR-026** : migration data (lifecycle_state legacy → V4)
- **ADR-027** : sécurité (IS5 admin + fresh token = IL3, HTTP 409 = IL1)
- **ADR-029 Evidence + audit trail** : rétention `action_event_log` 5 ans (IL8)

---

## 12. Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Réouverture admin abusée | Faible | Moyen | IL3 fresh token + IL11 justification + audit trail (admin role + log) |
| Auto-close récurrence mal-déclenche P0 critique | Moyen | Élevé | IL7 P0/P1 exigent preuve OU justification + IL6 group.resolved required |
| `expired` masque un risque conformité actif | Moyen | **Élevé (RGPD/réglementaire)** | IL4 interdiction P0/P1 conformite/facturation |
| Confusion merged_duplicate vs resolved_via_recurrence | Élevé (UX) | Faible | IL5 garde-fou code + libellés FR distincts + closure_reason explicit |
| Frontend optimistic UI réintroduit | Moyen | Moyen | IL10 source-guard + tests e2e |
| Hook oublié sur nouvelle transition | Moyen | Élevé | Map `PRE/POST_TRANSITION_HOOKS` explicite + source-guard CI |
| Cascade récurrence infinie | Faible | Élevé | Garde-fou : groupe ne peut pas être réouvert (terminal) |

---

## 13. Critères de validation finale ADR-028

### 13.1 11 invariants vérifiés

- [ ] **IL1** Transitions invalides → HTTP 409 — §5 InvalidTransitionError + §6 endpoint
- [ ] **IL2** `closed → new` impossible — §3.1 matrice + §8.3 test
- [ ] **IL3** Réouverture admin + fresh + justification — §6.2 + §8.3 test
- [ ] **IL4** `expired` interdit P0/P1 conformite/facturation — §4.2 + §8.3 test
- [ ] **IL5** `merged_duplicate` interdit si recurrence sans duplicate — §4.2 + §8.3 test
- [ ] **IL6** Auto-close récurrence exige group.resolved — §4.3 + §8.3 test
- [ ] **IL7** Auto-close récurrence P0/P1 exige preuve ou justification — §4.3 + §8.3 test
- [ ] **IL8** Chaque transition écrit `action_event_log` — §5 `_after_transition` + §8.3 test
- [ ] **IL9** Chaque transition met `score_stale=true` — §5 + §8.3 test
- [ ] **IL10** Frontend wait-for-server — §7 + e2e test
- [ ] **IL11** Réouverture trace event avec justification — §6.2 + §8.3 test

### 13.2 Cohérence cross-documents

- [ ] Cohérence ADR-025 (CHECK constraint `lifecycle_state`, `closure_consistency`)
- [ ] Cohérence ADR-027 (IS5 admin + fresh = IL3, HTTP 409 cohérent §4 ADR-027)
- [ ] Cohérence doctrine v0.2 (5 états + libellés FR + Q9-B recurrence ≠ duplicate)
- [ ] Cohérence L1 (transitions legacy → V4, 6 vocabulaires statuts → 5 + 6 closure_reasons)
- [ ] Cohérence maquettes M1-M5 (boutons "Planifier"/"Réassigner"/"Clôturer" mappés aux transitions)

### 13.3 Conformité Q6-A

- [ ] Aucun code Python/TypeScript modifié
- [ ] Aucune table DB modifiée
- [ ] Aucun script créé sur disque (documentés DANS l'ADR uniquement)

---

## 14. Métadonnées ADR

```yaml
adr_number: 028
title: Lifecycle states Centre d'Action V4
version: v0.1
status: Proposed
date: 2026-05-14
authors:
  - Amine (PROMEOS founder)
  - Claude (architecture co-pilot)
arbitrages_q33_q39:
  Q33: B    # enum + dict transitions manuel
  Q34: A    # HTTP 409 Conflict
  Q35: A    # méthodes Python explicites
  Q36: C+   # réouverture admin + fresh + justification
  Q37: A+   # auto-close avec resolved_via_recurrence (jamais merged)
  Q38: B    # action_event_log métier séparé de security_audit_log
  Q39: B    # wait-for-server
invariants_lifecycle:
  IL1: "Transitions invalides → HTTP 409"
  IL2: "closed → new impossible"
  IL3: "Réouverture admin + fresh token + justification"
  IL4: "expired interdit P0/P1 conformite/facturation"
  IL5: "merged_duplicate interdit si recurrence sans duplicate"
  IL6: "Auto-close récurrence exige group.resolved"
  IL7: "Auto-close récurrence P0/P1 exige preuve ou justification"
  IL8: "Chaque transition écrit action_event_log"
  IL9: "Chaque transition met score_stale=true"
  IL10: "Frontend wait-for-server"
  IL11: "Réouverture trace event avec justification non vide"
states: ["new", "triaged", "planned", "in_progress", "closed"]
transitions_count: 10
closure_reasons:
  - resolved
  - dismissed
  - not_applicable
  - merged_duplicate
  - resolved_via_recurrence
  - expired  # IL4 P0/P1 interdit
tests_planned: 56
next_adr: ADR-029 Evidence + audit trail
```

---

**Statut** : `Proposed`. À acter par Amine avant L5 production.

Une fois acté, ADR-028 devient **le manuel de comportement des items V4** pour Mois 2-6.
