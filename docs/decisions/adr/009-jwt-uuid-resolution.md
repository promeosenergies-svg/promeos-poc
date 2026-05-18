# ADR-009 — Résolution dette JWT int ↔ V4 UUID

**Statut** : ✅ ACCEPTED — décision Amine 2026-05-16 (STOP gate M2-4.0)
**Date** : 2026-05-16
**Date décision** : 2026-05-16
**Sprint** : M2-4
**Décision** : **Option D** — Migration `organisation_id` UUID → Integer FK partagé legacy↔V4
**Amende** : ADR-025 §4.1 + ADR-029 §2 (voir avenant consolidé `docs/dev/ADR-025-029_A1_integer_fk.md`)
**Auteur** : Claude Code (analyse) — décision finale Amine
**Lié à** : `SECURITY.md` §5.1 · M2-3.C `backend/middleware/org_context.py` · `M2-4_AUDIT.md`

---

## 1. Contexte

> **Décision finale : Option D** — `organisation_id` migre de UUID vers Integer FK.
> **§2 et §3 ci-dessous sont la trace historique de l'analyse** (4 options, reco initiale A).
> **Pour la décision et sa justification, aller directement à §5.**

Sprint M2-3.C a livré `BaseRepositoryV4` fail-closed avec un `ContextVar` peuplé
depuis le JWT par `populate_org_context`. **Mismatch découvert** :

- JWT actuel porte `org_id: int` (legacy — `Organisation.id` Integer PK)
- Les 8 models V4 (`backend/models/v4/`) utilisent `organisation_id: UUID`

En production routée, `populate_org_context` set le contexte avec `str(int)`,
mais les queries V4 filtrent sur `UUID`. Résultat : queries renvoient `[]`
(*fail-visible* — pas de wrong data, mais aucune route V4 ne marche end-to-end).

**État audit M2-4.0** (cf. `M2-4_AUDIT.md`) :

- 8 models V4, tous avec `organisation_id: UUID` (0 gap)
- 🔴 Lien legacy↔V4 : **inexistant** (aucune colonne de liaison, aucune table mapping)
- 18 consommateurs JWT `org_id` : **17 legacy** (attendent `int`) + 1 V4
- 🔴 Endpoints V4 réels : **0** (12 à créer ex nihilo en M2-4)
- 🔴 Seed V4 : **inexistant** — les 8 tables V4 sont **vides**

**Fenêtre rare** : les tables V4 étant vides, toute migration de schéma
`organisation_id` serait **sans backfill** — cela débloque l'Option D ci-dessous.

---

## 2. Options évaluées

> ⚠️ **Note historique** : cette section présente les 4 options analysées en
> M2-4.0. La recommandation analyste initiale était l'Option A (mapping). Après
> arbitrage Amine au STOP gate, c'est l'**Option D** qui a été retenue (cf. §5).
> La trace de l'analyse complète est conservée — elle documente *pourquoi* D a
> été préférée, pas seulement *que* D a été choisie.

### Option A — Mapping in `populate_org_context` (recommandée initialement, NON retenue)

**Concept** : `populate_org_context` lit `payload['org_id']: int`, résout l'UUID
V4 via un dict de mapping en code, set le contexte en UUID.

```python
_LEGACY_INT_TO_V4_UUID: dict[int, str] = {
    1: "11111111-1111-1111-1111-111111111111",   # HELIOS demo
    2: "22222222-2222-2222-2222-222222222222",   # MERIDIAN demo
}

async def populate_org_context(payload=Depends(get_jwt_payload)):
    if payload is None:
        yield; return
    legacy_int = payload.get("org_id")
    v4_uuid = _LEGACY_INT_TO_V4_UUID.get(legacy_int)
    if v4_uuid is None:
        raise HTTPException(403, {"code": "ORG_NOT_IN_V4_SCOPE", ...})
    token = set_org_context(v4_uuid)
    try: yield
    finally: reset_org_context(token)
```

| Avantages | Inconvénients |
|---|---|
| ✅ Aucune migration BDD | ⚠️ Mapping à maintenir (dict en code) |
| ✅ JWT inchangé → 17 consommateurs legacy intacts | ⚠️ Désync mapping↔seed → 403 ou fuite |
| ✅ Rapide (~1-1.5h) · rollback trivial | ⚠️ Dette structurelle préservée |
| ✅ Le mapping et le seed V4 se créent ensemble | ⚠️ Lookup par requête (mitigeable `lru_cache`) |

**Effort** : ~1-1.5h · **Risque** : faible · **Sortie "vraie" résolution** : ticket M3-X.

### Option B — JWT en UUID natif

**Concept** : modifier `iam_service.create_access_token` pour émettre
`org_id: UUID`. Tous les consommateurs JWT mis à jour.

| Avantages | Inconvénients |
|---|---|
| ✅ Source de vérité unique | 🔴 **17 callsites legacy** `int(payload.get("org_id"))` à migrer |
| ✅ Pas de mapping | 🔴 Sessions existantes invalidées → re-login forcé |
| ✅ Cohérent V4 natif | 🔴 Risque régression élevé sur le legacy |

**Effort** : ~2-3h · **Risque** : 🔴 élevé (régression legacy).

### Option C — Colonne `legacy_int_id` sur models V4

**Concept** : ajouter `legacy_int_id: int (indexed)` sur les 8 models V4.
`BaseRepositoryV4._apply_scope` filtre sur `legacy_int_id`. JWT inchangé.

| Avantages | Inconvénients |
|---|---|
| ✅ JWT inchangé | 🔴 Migration BDD sur 8 models + tous les futurs |
| ✅ Performance native (index) | 🔴 Double identifiant V4 = anti-pattern |
| | 🔴 `_apply_scope` filtre une clé secondaire, pas la vraie clé — incohérent fail-closed |

**Effort** : ~2-3h · **Risque** : moyen · dette **déplacée, pas résolue**.

### Option D — Migration `organisation_id` UUID → Integer FK (révélée par l'audit)

**Concept** : puisque les 8 tables V4 sont **vides** (audit §6), migrer la colonne
`organisation_id` de `UUID` vers `Integer` FK `organisations.id`. V4 utiliserait
alors le **même org_id int que le legacy** — le JWT marche directement, 0 mapping.

| Avantages | Inconvénients |
|---|---|
| ✅ Résout la dette **à la racine** (1 seul type org partout) | 🔴 Amende ADR-025 §4.1 + ADR-029 §2 (Accepted) — `organisation_id` UUID était un **choix PG-ready délibéré** (anti-collision multi-shard, anti-énumération séquentielle) |
| ✅ Migration **sans backfill** (tables vides — fenêtre rare) | 🔴 Lourdeur doctrinale : 2 ADR Accepted à amender via avenant |
| ✅ JWT inchangé · 17 consommateurs legacy intacts | 🔴 Perd l'acquis UUID (IS1 a été pensé UUID dans ADR-027) |
| ✅ `_apply_scope` filtre la vraie clé | |

**Effort** : ~2h (migration Alembic + maj 8 models + avenant ADR-025/029).
**Risque** : moyen — techniquement sûr (tables vides), mais **coût doctrinal**
(toucher 2 ADR de la série Mois 1 figée).

---

## 3. Recommandation analyste initiale (NON retenue — trace historique)

> Cette section documente la recommandation faite par l'analyste au STOP gate.
> Amine a tranché différemment (Option D). Conservée pour traçabilité du
> raisonnement — un lecteur futur doit comprendre que D a été choisie *contre*
> une recommandation A, et pourquoi.

**Option A (mapping in `populate_org_context`)** — résolution court-terme.

Justification (mise à jour post-audit, peut diverger du pré-écrit) :

1. **Pourquoi pas B** : 17 consommateurs JWT legacy `int` à migrer = sortir du
   scope M2-4 (orienté V4, pas refactor legacy) + invalidation sessions.

2. **Pourquoi pas C** : double identifiant = anti-pattern. `_apply_scope` qui
   filtre une clé secondaire casse la cohérence fail-closed de M2-3.C.

3. **Pourquoi pas D, malgré sa séduction** : l'audit révèle que D est
   *techniquement triviale* (tables vides → 0 backfill). MAIS `organisation_id`
   UUID est un **choix d'architecture délibéré d'ADR-025 §4.1 + ADR-029**
   (PG-ready : UUID évite collisions multi-shard + énumération séquentielle des
   ressources). Reverter ce choix = amender 2 ADR Accepted de la série Mois 1
   figée — coût doctrinal disproportionné pour M2-4. **Si Amine juge que la
   dette JWT/UUID est plus grave que l'acquis UUID, D devient le meilleur choix
   et c'est un arbitrage légitime** — mais ça relève d'un avenant doctrinal, pas
   d'un sprint d'implémentation.

**Recommandation conditionnelle** :
- **Si priorité = vélocité M2-4 + préserver les ADR** → **Option A**.
- **Si priorité = supprimer la dette définitivement, ADR amendables** → **Option D**
  (la fenêtre "tables vides" ne se représentera pas — une fois le seed V4 créé,
  D coûte un backfill).

Mapping Option A à mitiger :
- `_LEGACY_INT_TO_V4_UUID` en **code** (pas BDD) — versionné, auditable.
- `functools.lru_cache` sur la résolution (O(1) après warmup).
- `legacy_int` absent du mapping → `HTTPException(403, ORG_NOT_IN_V4_SCOPE)` (fail-visible).
- **Test invariant** `test_legacy_to_v4_mapping_matches_seed()` : scanne le seed
  V4 et vérifie que chaque org legacy seedée a son UUID dans la table (anti-désync).

---

## 4. Plan d'implémentation — Option D actée

Sprint M2-4 séquence (10 commits — cf. `M2-4_ROLLOUT_PLAN.md`) :

| # | Commit | Objectif |
|---|---|---|
| M2-4.0 ✅ | Audit + ADR-009 DRAFT + rollout plan | livré |
| M2-4.0.bis ⏳ | ADR-009 FINAL Option D + avenant ADR-025/029 + plan révisé | ce commit |
| M2-4.1 | Migration Alembic `organisation_id` UUID → Integer FK (8 tables V4 vides, 0 backfill) + maj 8 models V4 + maj `base_v4.py` + adaptation tests M2-3.C | |
| M2-4.1.bis | Seed V4 minimal (prérequis IDOR — 2 orgs + items V4) | |
| M2-4.2 | Endpoint V4 template (`GET /pilotage`) + `response_model` Pydantic + idempotence | |
| M2-4.3 | Rollout 4 endpoints read | |
| M2-4.4 | Rollout 8 endpoints write/admin | |
| M2-4.5 | IDOR matrix (12 routes × rôles × 2 orgs) | |
| M2-4.6 | `@limiter` rate limiting sur routes V4 | |
| M2-4.7 | Doc closure — `SECURITY.md` §5.1 dette **supprimée** (plus différée) | |

`populate_org_context` est câblé directement (0 mapping) : le JWT `org_id: int`
alimente le `ContextVar`, `BaseRepositoryV4._apply_scope` filtre sur la colonne
`organisation_id` Integer — le type matche de bout en bout.

---

## 5. Décision — Option D retenue

**Décision** (Amine, STOP gate M2-4.0, 2026-05-16) : migrer `organisation_id` de
`UUID` vers `Integer FK organisations(id)` sur les 8 models V4. Le JWT existant
(`org_id: int`) câble naturellement au contexte V4 via `populate_org_context`
sans transformation. **Dette JWT/UUID supprimée à la racine.**

### 5.1 — Pourquoi pas Option A (mapping)

Option A préservait la dette via un dict `_LEGACY_INT_TO_V4_UUID` à maintenir et
un ticket de sortie M3-X à 6 mois. Coût total cumulé (maintenance mapping +
risque désync + résolution différée) supérieur au coût Option D, alors que la
fenêtre d'exécution Option D (8 tables V4 vides → 0 backfill) **ne se
représentera plus** une fois le seed V4 actif. Décision : **payer la dette
maintenant plutôt que la financer**.

### 5.2 — Justifications historiques UUID — réévaluation

ADR-025 §4.1 et ADR-029 §2 retenaient UUID pour 3 raisons. Réévaluation au regard
de l'état réel du projet (audit M2-4.0) :

| Justification originale | Statut 2026-05 | Raison |
|---|---|---|
| Multi-shard PostgreSQL | ⏸️ Différée 12-18 mois min | Aucun signal de besoin avant cette échéance (suppose >10M lignes/table ou >1000 orgs). Si re-besoin, Integer FK reste shardable via clé composée `(shard_id, id)`. |
| Anti-énumération URL | ✅ Mitigée autrement | Le fail-closed `BaseRepositoryV4` (M2-3.C) bloque l'exploitation cross-org : URL devinable mais inexploitable. Trade-off §5.3. |
| PG-ready | ✅ Maintenue | Integer FK est aussi PG-ready, avec index B-tree plus compact (4-8 octets vs 16). Aucune dégradation. |

### 5.3 — Trade-off accepté : URL énumérable côté pattern

> ⚠️ **NOTE RECTIFICATIVE (M2-4.7 — 2026-05-18)** — ce §5.3 est **caduc**.
> L'analyse ci-dessous supposait que la migration `organisation_id` UUID→Integer
> rendait séquentielles les **clés primaires des entités V4**. C'est faux :
> **seule** la colonne `organisation_id` (clé étrangère) est devenue `Integer`.
> Les PK des 8 tables V4 — `action_center_items.id`, `evidences.id`, etc. —
> sont **restées `UUID(as_uuid=True)` avec `default=uuid4`** (vérifié à
> l'implémentation M2-4.1). Les URL `/api/v4/action-center/items/{id}` portent
> donc un UUID v4 non séquentiel → **non énumérables**. Le trade-off décrit
> ci-dessous n'existe pas.
> Le texte original est conservé sans modification pour la traçabilité du
> raisonnement tenu au STOP gate M2-4.0 — ce sont ses **conclusions** qui sont
> caduques, pas la trace de l'analyse.

Integer PK séquentielle rend les URL `/api/v4/action-center/items/{id}`
énumérables par incrément. Conséquences explicitement acceptées :

- **Exploitation cross-org** : bloquée par fail-closed `BaseRepositoryV4`. Une
  URL devinée par un user d'org A pour un item d'org B retourne `404` (cf.
  `test_get_blocks_cross_org_access` — M2-3.C).
- **Énumération intra-org** : un user peut deviner les IDs de ses propres items.
  Acceptable — il y a déjà accès légitime par définition.
- **Inférence de volume via fuite log** : un attaquant qui obtient un ID via une
  fuite log peut inférer la taille de la table. Mitigation : nettoyage logs
  (chantier M2-6+, déjà tracé).

Trade-off documenté dans `SECURITY.md` §4 (table de garanties).

### 5.4 — Conditions de re-bascule UUID

Ré-ouvrir cet ADR si l'un de ces signaux se matérialise :

- Besoin réel multi-shard PG (>10M lignes sur une table V4, ou >1000 orgs).
- Exposition API publique **non-authentifiée** d'URL V4 (changement de modèle
  de menace — l'énumération deviendrait exploitable).
- Audit externe identifiant l'énumération séquentielle comme P0/P1.
- Migration de stack DB hors PostgreSQL (contraintes Integer FK différentes).

Tant qu'aucun signal n'apparaît, Integer FK reste la décision active.
