# M2-4 AUDIT — État V4 réel (Phase 1 lecture seule)

> **Date** : 2026-05-16
> **Branche** : `feat/m2-4-rollout`
> **Méthode** : audit lecture seule (cf. M2-4.0_audit_adr_jwt_uuid.md)
> **Pivot** : conditionne la forme des commits M2-4.1 → M2-4.7.

---

## 1. Models V4 totaux

**8 models V4** dans `backend/models/v4/` :

| Model | `organisation_id` ? | Type |
|---|---|---|
| `action_center_items` | ✅ | `UUID(as_uuid=True)` NOT NULL |
| `action_event_log` | ✅ | `UUID(as_uuid=True)` NOT NULL |
| `evidences` (→ `action_evidences`) | ✅ | `UUID(as_uuid=True)` NOT NULL |
| `action_links` | ✅ | `UUID(as_uuid=True)` NOT NULL |
| `action_blockers` | ✅ | `UUID(as_uuid=True)` NOT NULL |
| `action_scenarios` | ✅ | `UUID(as_uuid=True)` NOT NULL |
| `duplicate_groups` | ✅ | `UUID(as_uuid=True)` NOT NULL |
| `recurrence_groups` | ✅ | `UUID(as_uuid=True)` NOT NULL |

**Verdict** : 8/8 models ont `organisation_id` — **0 gap**. Type uniforme `UUID(as_uuid=True)` NOT NULL (IS1 cardinal). Aucun model V4 sans scope.

---

## 2. Type `organisation_id`

**Confirmé : UUID** sur les 8 models (`Column(UUID(as_uuid=True), nullable=False)`).

Contraste : le legacy `Organisation.id` est **Integer** PK (`backend/models/organisation.py:18`).

---

## 3. Lien legacy ↔ V4

Recherche des 3 hypothèses de liaison :

| Hypothèse | Recherche | Résultat |
|---|---|---|
| H1 — colonne `v4_uuid` sur `Organisation` legacy | `grep v4_uuid` dans `iam.py` + `organisation.py` | ❌ Vide |
| H2 — colonne `legacy_id` sur model V4 | `grep legacy_id` dans `models/v4/` | ❌ Vide |
| H3 — table de mapping dédiée | `grep OrgMapping\|organisation_mapping` | ❌ Vide |

**Verdict cardinal** : 🔴 **AUCUN lien legacy↔V4 n'existe** (Hypothèse 4 — entités séparées sans liaison).

→ Conséquence : Option A (mapping in `populate_org_context`) nécessite un **dict de mapping créé en code** — il n'y a aucun lien BDD à exploiter.

---

## 4. Consommateurs JWT `org_id`

**18 occurrences** hors test (impact direct sur Option B) :

| Fichier | Occurrences | Nature |
|---|---|---|
| `backend/middleware/auth.py` | 3 | Legacy core (`get_current_user`, `get_current_user_role`, `get_optional_auth`) — `int(payload.get("org_id"))` |
| `backend/routes/admin_users.py` | 7 | Legacy admin — `int(_admin.get("org_id"))` |
| `backend/routes/auth.py` | 2 | Legacy auth — `int(payload.get("org_id"))` |
| `backend/routes/demo.py` | 3 | Seed/demo |
| `backend/services/audit_log_service.py` | 1 | Legacy audit |
| `backend/services/narrative/typology_resolver.py` | 1 | Legacy narrative |
| `backend/middleware/org_context.py` | 1 | **V4** (M2-3.C — prend la valeur brute) |

**Verdict** : **17 consommateurs legacy** (tous attendent `int`) + **1 consommateur V4**.

→ Impact Option B (JWT en UUID natif) : **17 callsites legacy à migrer** + invalidation sessions. Confirme que Option B sort du scope M2-4 (orienté V4, pas refactor legacy).

---

## 5. Routes V4 prévues

| Élément | État |
|---|---|
| `backend/api/action_center/` | Scaffold — uniquement `__init__.py` (0 endpoint réel) |
| `backend/routes/action_center.py` | **Legacy** — ~20 endpoints (`/issues`, `/summary`, `/actions`, `/recommendations/*`) agrégateur in-memory, **ne touche PAS `models/v4/`** |
| Repository V4 (M2-3.C) | ✅ `base_v4.py` + `action_center_item_v4_repository.py` livrés |

**Verdict** : 🔴 **Aucun endpoint V4 réel n'existe.** Les **12 endpoints `/api/action-center/*`** (cf. ADR-027 §9 + L7 §6 IDOR matrix) sont à **créer ex nihilo** en M2-4 — pas à "migrer".

12 endpoints V4 cible (ADR-027 §9) :
1. `GET /pilotage` · 2. `GET /items/{id}` · 3. `POST /items` · 4. `PATCH /items/{id}/lifecycle`
5. `PATCH /items/{id}/owner` · 6. `PATCH /items/{id}/blockers` · 7. `POST /items/{id}/close`
8. `PATCH /items/{id}/correct-kind` · 9. `GET /items/{id}/audit-trail` · 10. `GET /impact`
11. `POST /items/{id}/evidence` · 12. `POST /items/{id}/scenarios/{sid}/select`

---

## 6. Seed V4 état

Recherche `ActionCenterItem` / `action_center_items` dans `backend/scripts/` + `backend/services/demo_seed/` :

**Verdict** : 🔴 **Aucun seed V4 n'existe.** Les 8 tables V4 sont créées (migration `m2s2v4`) mais **jamais peuplées**.

→ **Prérequis bloquant pour IDOR matrix M2-4.5** (surprise #5 du prompt confirmée). Le seed V4 doit être créé en M2-4.1.bis avant le rollout des endpoints + avant les tests d'intégration cross-org.

---

## Synthèse exécutive

| Question | Réponse |
|---|---|
| Models V4 totaux | 8, tous avec `organisation_id` UUID — 0 gap |
| Type `organisation_id` | UUID (legacy `Organisation.id` = Integer) |
| Lien legacy ↔ V4 | 🔴 **Inexistant** (H1/H2/H3 toutes vides) |
| Consommateurs JWT `org_id` | 18 (17 legacy `int` + 1 V4) |
| Endpoints V4 réels | 🔴 **0** — 12 à créer ex nihilo |
| Seed V4 | 🔴 **Inexistant** — prérequis bloquant IDOR M2-4.5 |

**3 cas bloquants découverts** (à traiter avant rollout) :
1. Aucun lien legacy↔V4 → Option A doit créer un dict de mapping en code.
2. Aucun endpoint V4 → M2-4 crée 12 endpoints (pas de "migration").
3. Aucun seed V4 → M2-4.1.bis doit créer le seed avant IDOR matrix.

**Fenêtre rare détectée** : les 8 tables V4 étant **vides**, une migration de colonne `organisation_id` (UUID → autre type) serait **sans backfill** — ce qui débloque une Option D non envisagée par le prompt (cf. ADR-009 §2 Option D).
