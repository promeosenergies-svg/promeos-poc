# ADR-009 — Résolution dette JWT int ↔ V4 UUID

**Statut** : 🟡 DRAFT — en attente décision Amine (STOP gate M2-4.0)
**Date** : 2026-05-16
**Sprint** : M2-4
**Auteur** : Claude Code (analyste) — décision finale Amine
**Lié à** : `SECURITY.md` §5.1 · M2-3.C `backend/middleware/org_context.py` · `M2-4_AUDIT.md`

---

## 1. Contexte

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

### Option A — Mapping in `populate_org_context` (recommandée court-terme)

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

## 3. Recommandation analyste

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

## 4. Plan d'implémentation

### Si Option A retenue
- **M2-4.1** : mapping `_LEGACY_INT_TO_V4_UUID` + seed V4 conjoint + tests + invariant seed
- **M2-4.2 → .4** : rollout 12 endpoints V4 (mapping câblé)
- **M2-4.5** : IDOR matrix (utilise le mapping + seed réels)
- **M2-4.7** : MAJ `SECURITY.md` §5.1 — dette résolue court-terme + ticket sortie M3-X

### Si Option D retenue
- **M2-4.1.bis** : avenant ADR-025/029 (`organisation_id` UUID → Integer FK) +
  migration Alembic (alter column, tables vides) + maj 8 models V4 + maj `base_v4.py`
- **M2-4.1** : seed V4 (org_id int aligné legacy)
- **M2-4.2 → .7** : identique (mais `populate_org_context` câblé directement, 0 mapping)

---

## 5. Décision

🟡 **EN ATTENTE** — à acter par Amine au STOP gate M2-4.0.

Options : **A** (recommandée court-terme) · B · C · **D** (révélée par l'audit —
résout la dette mais amende ADR-025/029) · autre · défer.
