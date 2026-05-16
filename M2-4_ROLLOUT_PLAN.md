# Plan rollout M2-4

> **Statut** : draft — sera supprimé en fin de sprint M2-4.
> **Source** : `M2-4_AUDIT.md` (Phase 1) + ADR-009 (option JWT/UUID à acter).
> **Dépend de** : décision Amine au STOP gate M2-4.0 (Option A vs D conditionne M2-4.1).

---

## Endpoints V4 prévus (12 — ADR-027 §9 · audit §5)

⚠️ **Aucun n'existe** — tous à créer ex nihilo (pas de "migration").

| # | Endpoint | Méthode | Type | Repo V4 | Sprint | Effort |
|---|---|---|---|---|---|---|
| 1 | `/api/v4/action-center/pilotage` | GET | read | ActionCenterItemRepo | M2-4.2 (template) | 1h |
| 2 | `/api/v4/action-center/items/{id}` | GET | read | ActionCenterItemRepo | M2-4.3 | 30min |
| 3 | `/api/v4/action-center/items` | POST | write | ActionCenterItemRepo | M2-4.4 | 45min |
| 4 | `/api/v4/action-center/items/{id}/lifecycle` | PATCH | write | ActionCenterItemRepo | M2-4.4 | 45min |
| 5 | `/api/v4/action-center/items/{id}/owner` | PATCH | write | ActionCenterItemRepo | M2-4.4 | 45min |
| 6 | `/api/v4/action-center/items/{id}/blockers` | PATCH | write | ActionBlockerRepo | M2-4.4 | 45min |
| 7 | `/api/v4/action-center/items/{id}/close` | POST | write | ActionCenterItemRepo | M2-4.4 | 45min |
| 8 | `/api/v4/action-center/items/{id}/correct-kind` | PATCH | admin | ActionCenterItemRepo | M2-4.4 | 45min |
| 9 | `/api/v4/action-center/items/{id}/audit-trail` | GET | read | ActionEventLogRepo | M2-4.3 | 30min |
| 10 | `/api/v4/action-center/impact` | GET | read | ActionCenterItemRepo | M2-4.3 | 30min |
| 11 | `/api/v4/action-center/items/{id}/evidence` | POST | write | EvidenceRepo | M2-4.4 | 45min |
| 12 | `/api/v4/action-center/items/{id}/scenarios/{sid}/select` | POST | write | ActionScenarioRepo | M2-4.4 | 45min |

Répartition : **4 read** (M2-4.3) · **8 write/admin** (M2-4.4).

Repos V4 nécessaires : `ActionCenterItemRepository` ✅ livré M2-3.C · 4 autres à créer
(`ActionBlockerRepository`, `ActionEventLogRepository`, `EvidenceRepository`,
`ActionScenarioRepository`) — triviaux (3 lignes chacun, héritent `BaseRepositoryV4`).

---

## Séquencement M2-4 (7 commits)

| Commit | Objet | Effort | Dépend de |
|---|---|---|---|
| M2-4.0 | Audit + ADR-009 + ce plan (doc) | 45min | — (ce commit) |
| M2-4.1 | Résolution JWT/UUID (option actée) + **seed V4** + 4 repos concrets | 2-3h | STOP gate |
| M2-4.2 | 1er endpoint template (`GET /pilotage`) + pattern de référence | 1h | M2-4.1 |
| M2-4.3 | Rollout 4 endpoints read | 2h | M2-4.2 |
| M2-4.4 | Rollout 8 endpoints write/admin | 5-6h | M2-4.3 |
| M2-4.5 | IDOR matrix (12 routes × rôles × 2 orgs) | 1-2h | M2-4.3 + M2-4.4 + seed |
| M2-4.6 | Rate limiting `@limiter` sur routes V4 sensibles | 1h | indépendant |
| M2-4.7 | Doc closure — MAJ SECURITY.md §5.1, suppression plans | 30min | tous |

**Total estimé** : **15-18h** (sprint lourd — proche de la borne haute prompt).

---

## Estimation par sous-commit

- M2-4.1 (JWT/UUID + seed V4 + 4 repos) : 2-3h
  - Option A : mapping dict + lru_cache + test invariant seed (~1.5h) + seed V4 (~1h)
  - Option D : avenant ADR-025/029 + migration Alembic + maj 8 models (~2h) + seed V4 (~1h)
- M2-4.2 (endpoint template) : 1h
- M2-4.3 (4 read × ~30min) : 2h
- M2-4.4 (8 write × ~45min) : 5-6h
- M2-4.5 (IDOR matrix) : 1-2h
- M2-4.6 (rate limiting) : 1h
- M2-4.7 (doc) : 30min

---

## Dépendances internes

- **M2-4.1 bloque tout** : ni endpoint ni IDOR sans résolution JWT/UUID + seed.
- M2-4.2 (template) doit précéder M2-4.3/.4 — sert de pattern de référence.
- M2-4.3 + M2-4.4 doivent précéder M2-4.5 (IDOR teste les routes existantes).
- M2-4.6 (rate limiting) indépendant — avançable ou retardable sans impact.

---

## Points de vigilance (issus audit Phase 1)

| # | Vigilance | Mitigation |
|---|---|---|
| 1 | 🔴 **Seed V4 inexistant** — bloque IDOR M2-4.5 | Créer le seed V4 **en M2-4.1** (conjoint au mapping/migration) |
| 2 | 🔴 Aucun lien legacy↔V4 — Option A = dict en code | Test invariant `test_legacy_to_v4_mapping_matches_seed()` anti-désync |
| 3 | Models V4 sans `organisation_id` | ✅ Aucun — 8/8 ont le champ |
| 4 | Endpoints cross-table V4 (ex: audit-trail lit `action_event_log`) | Pattern multi-repo à valider en M2-4.2 template |
| 5 | Idempotence POST (anti-pattern V66 RC4) | `idempotency_key` natif prévu sur les 8 endpoints write M2-4.4 |
| 6 | `response_model` Pydantic obligatoire (anti-pattern V66 RC2) | Schémas Pydantic V4 sur les 12 endpoints — pas de `dict` brut |
| 7 | 12 endpoints = borne haute prompt (>15 = split M2-4/M2-5) | 12 ≤ 15 → reste 1 seul sprint M2-4 |

---

## Re-séquencement conditionnel

- **Si Amine retient Option D** : insérer M2-4.1.bis (avenant ADR-025/029 +
  migration Alembic) avant M2-4.1 — sprint passe à 8 commits.
- **Si IDOR matrix trop lourde** : M2-4.5 peut être splitté (sample 30 cellules
  en M2-4.5, matrice complète 288 en M2-5).
