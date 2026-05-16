# Plan rollout M2-4 — RÉVISÉ Option D (2026-05-16)

> **Statut** : draft — sera supprimé en fin de sprint M2-4 (commit M2-4.7).
> **Mise à jour M2-4.0.bis** : décision Option D actée (ADR-009 §5) → sprint passe
> à **10 commits**. Avenant ADR-025/029 rédigé. `organisation_id` UUID → Integer FK.
> **Source** : `M2-4_AUDIT.md` (audit Phase 1) + `docs/decisions/adr/009-jwt-uuid-resolution.md`.

---

## Décision pivot — Option D

`organisation_id` migre de UUID vers **Integer FK `organisations(id)`** sur les
8 models V4. Le JWT `org_id: int` câble directement au `ContextVar` V4 — 0 mapping.
Dette JWT/UUID **supprimée à la racine**. Détails : ADR-009 §5 + avenant
`docs/dev/ADR-025-029_A1_integer_fk.md`.

---

## Endpoints V4 prévus (12 — ADR-027 §9 · audit §5)

⚠️ **Aucun n'existe** — tous à créer ex nihilo (pas de "migration").

| # | Endpoint | Méthode | Type | Repo V4 | Sprint |
|---|---|---|---|---|---|
| 1 | `/api/v4/action-center/pilotage` | GET | read | ActionCenterItemRepo | M2-4.2 (template) |
| 2 | `/api/v4/action-center/items/{id}` | GET | read | ActionCenterItemRepo | M2-4.3 |
| 3 | `/api/v4/action-center/items/{id}/audit-trail` | GET | read | ActionEventLogRepo | M2-4.3 |
| 4 | `/api/v4/action-center/impact` | GET | read | ActionCenterItemRepo | M2-4.3 |
| 5 | `/api/v4/action-center/items` | POST | write | ActionCenterItemRepo | M2-4.4 |
| 6 | `/api/v4/action-center/items/{id}/lifecycle` | PATCH | write | ActionCenterItemRepo | M2-4.4 |
| 7 | `/api/v4/action-center/items/{id}/owner` | PATCH | write | ActionCenterItemRepo | M2-4.4 |
| 8 | `/api/v4/action-center/items/{id}/blockers` | PATCH | write | ActionBlockerRepo | M2-4.4 |
| 9 | `/api/v4/action-center/items/{id}/close` | POST | write | ActionCenterItemRepo | M2-4.4 |
| 10 | `/api/v4/action-center/items/{id}/correct-kind` | PATCH | admin | ActionCenterItemRepo | M2-4.4 |
| 11 | `/api/v4/action-center/items/{id}/evidence` | POST | write | EvidenceRepo | M2-4.4 |
| 12 | `/api/v4/action-center/items/{id}/scenarios/{sid}/select` | POST | write | ActionScenarioRepo | M2-4.4 |

Répartition : **4 read** (M2-4.3) · **8 write/admin** (M2-4.4).
Repos V4 : `ActionCenterItemRepository` ✅ livré M2-3.C · 4 autres triviaux à créer
(héritent `BaseRepositoryV4`, 3 lignes chacun) — en M2-4.1.

---

## Séquence commits (10)

| # | Commit | État | Objectif | Effort | Risque |
|---|---|---|---|---|---|
| 0 | M2-4.0 | ✅ | Audit V4 + ADR-009 DRAFT + rollout plan | 45min | — |
| 0.bis | M2-4.0.bis | ⏳ ce commit | ADR-009 FINAL Option D + avenant ADR-025/029 + plan révisé | 1h | — |
| 1 | M2-4.1 | 🔜 | Migration Alembic `organisation_id` UUID→Integer FK (8 tables) + maj 8 models V4 + maj `base_v4.py` + 4 repos concrets + adaptation tests M2-3.C | 1.5-2h | 🟡 BDD (0 backfill — tables vides) |
| 1.bis | M2-4.1.bis | 🔜 | Seed V4 minimal (2 orgs + items V4 — prérequis IDOR) | 1h | 🟢 |
| 2 | M2-4.2 | 🔜 | Endpoint V4 template (`GET /pilotage`) + `response_model` Pydantic + idempotence | 1h | 🟢 |
| 3 | M2-4.3 | 🔜 | Rollout 4 endpoints read | 2h | 🟢 |
| 4 | M2-4.4 | 🔜 | Rollout 8 endpoints write/admin | 3h | 🟡 idempotence write |
| 5 | M2-4.5 | 🔜 | IDOR matrix (12 routes × rôles × 2 orgs) | 1.5-2h | 🟢 |
| 6 | M2-4.6 | 🔜 | `@limiter` rate limiting sur 12 routes V4 | 1h | 🟢 |
| 7 | M2-4.7 | 🔜 | Doc closure — `SECURITY.md` §5.1 dette **supprimée** (plus différée) | 30min | — |

**Total estimé** : **~12-14h sur 10 commits**.

> Note : l'effort total est **inférieur** au plan initial (15-18h sur 7 commits)
> malgré 3 commits de plus — Option D supprime le mapping (gagne ~1.5h sur M2-4.1)
> et simplifie les tests d'intégration (gagne ~1h sur M2-4.5 — pas de couche de
> traduction à mocker).

---

## Dépendances internes

```
M2-4.0 ──> M2-4.0.bis ──> M2-4.1 ──> M2-4.1.bis ──> M2-4.2 ──> M2-4.3 ──┐
                                                                        │
          ┌─────────────────────────────────────────────────────────────┘
          └──> M2-4.4 ──> M2-4.5 ──> M2-4.7
                          M2-4.6 (indépendant — parallélisable avec M2-4.5)
```

- **M2-4.1 bloque tout** : ni endpoint ni IDOR sans la migration Integer FK.
- M2-4.2 (template) précède M2-4.3/.4 — sert de pattern de référence.
- M2-4.3 + M2-4.4 précèdent M2-4.5 (IDOR teste les routes existantes).
- M2-4.6 (`@limiter`) indépendant — avançable/retardable sans impact.

---

## Points de vigilance

| # | Vigilance | Mitigation |
|---|---|---|
| **C1** | 🔴 Migration BDD : confirmer **0 ligne** sur les 8 tables V4 avant `ALTER TABLE` | Garde-fou pré-commit M2-4.1 : `SELECT COUNT(*)` sur les 8 tables → toutes à 0, sinon STOP + backfill (cf. avenant §5) |
| **C2** | Avenant ADR-025/029 rédigé | ✅ Fait — `docs/dev/ADR-025-029_A1_integer_fk.md` (ce commit) |
| **C3** | Trade-off URL énumérable documenté | ✅ ADR-009 §5.3 + avenant §3.2 + à reporter SECURITY.md §4 (M2-4.7) |
| **C4** | 🔴 Seed V4 inexistant — bloque IDOR M2-4.5 | M2-4.1.bis crée le seed minimal (2 orgs + items V4 dans chaque) |
| C5 | Endpoints cross-table (audit-trail lit `action_event_log`) | Pattern multi-repo validé en M2-4.2 template |
| C6 | Idempotence POST (anti-pattern V66 RC4) | `idempotency_key` natif sur les 8 endpoints write — M2-4.2 template |
| C7 | `response_model` Pydantic obligatoire (anti-pattern V66 RC2) | Schémas Pydantic V4 sur les 12 endpoints — pas de `dict` brut |
| C8 | adaptation tests M2-3.C (`test_base_v4.py` FakeEntity `organisation_id` String) | M2-4.1 : aligner le type FakeEntity sur Integer ou laisser String (test isolé — décision au commit) |

---

## Re-séquencement conditionnel

- Si la migration M2-4.1 révèle des lignes V4 (tables non vides) → insérer
  M2-4.1.pre (backfill int↔UUID) — sprint passe à 11 commits.
- Si IDOR matrix M2-4.5 trop lourde → splitter (sample 30 cellules M2-4.5,
  matrice complète 288 reportée M2-5).
