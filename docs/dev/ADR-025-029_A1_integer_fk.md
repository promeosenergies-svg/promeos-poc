# Avenant A1 — ADR-025 §4.1 + ADR-029 §2 : `organisation_id` Integer FK (au lieu de UUID)

**Statut** : ✅ ACCEPTED
**Date** : 2026-05-16
**Sprint** : M2-4 (commit M2-4.0.bis)
**Amende** : ADR-025 §4.1 (schéma DB V4 — colonne `organisation_id`) · ADR-029 §2 (schéma `evidences`/`action_evidences`)
**Décidé par** : ADR-009 §5 (`docs/decisions/adr/009-jwt-uuid-resolution.md` — Option D)
**Auteur** : Claude Code (rédaction) — décision Amine

> **Avenant consolidé** : ADR-025 §4.1 et ADR-029 §2 retenaient tous deux
> `organisation_id` UUID sur les models V4 — même sujet, même justification.
> Un avenant unique amende les deux (évite 2 fichiers quasi-identiques).
>
> Convention PROMEOS : la doctrine v0.3 a amendé inline (doctrine §11 Historique).
> Les ADR-025/029 n'ayant pas de section Historique interne, l'avenant est un
> fichier séparé dans `docs/dev/` (où vivent les ADR amendés), avec une note de
> renvoi ajoutée en tête de L2_ADR-025 et L6_ADR-029.

---

## 1. Contexte

ADR-025 §4.1 (commit `b7208022`, Mois 1) a posé le schéma DB V4 avec
`organisation_id UUID NOT NULL` sur la table cardinale `action_center_items`.
ADR-029 §2 (commit `15711df4`) a repris ce choix pour la table `evidences`
(devenue `action_evidences` — M2-2 commit 3/5). Les 8 models V4 utilisent
`organisation_id` UUID.

UUID était retenu pour 3 raisons : (1) compatibilité multi-shard PostgreSQL
future, (2) anti-énumération séquentielle des URL, (3) PG-ready par construction.

Sprint M2-3.C a livré `BaseRepositoryV4` fail-closed avec un `ContextVar` peuplé
depuis le JWT par `populate_org_context`. **Mismatch découvert** : le JWT porte
`org_id: int` (legacy — `Organisation.id` Integer PK), les models V4 attendent
`organisation_id: UUID`. La chaîne JWT → repo V4 ne match pas en type.

L'audit M2-4.0 (`M2-4_AUDIT.md`) a analysé 4 options de résolution
(`docs/decisions/adr/009-jwt-uuid-resolution.md`). Décision Amine : **Option D**.

---

## 2. Amendement

`organisation_id` sur les **8 models V4** (`backend/models/v4/`) passe de :

- **AVANT** : `Column(UUID(as_uuid=True), nullable=False)` — PK source `gen_random_uuid()`
- **APRÈS** : `Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)`

L'identifiant org est désormais **partagé** entre legacy et V4 (Integer PK
`organisations.id`). Les 8 tables concernées : `action_center_items`,
`action_event_log`, `action_evidences`, `action_links`, `action_blockers`,
`action_scenarios`, `duplicate_groups`, `recurrence_groups`.

Le `BaseRepositoryV4._scope_column` reste `"organisation_id"` (le nom de colonne
ne change pas — seul le type change). `_apply_scope` filtre désormais sur un
Integer, ce qui matche le JWT `org_id: int` sans transformation.

---

## 3. Justification

### 3.1 — Multi-shard PostgreSQL (différé 12-18 mois min)

Aucun signal de besoin avant cette échéance. Le besoin multi-shard suppose
>10M lignes sur une table V4 ou >1000 orgs — non prévu à cet horizon pour
PROMEOS (POC → pilotes Y1). Si re-besoin futur, Integer FK reste shardable via
clé composée `(shard_id, id)`. Le choix UUID était une anticipation prématurée.

### 3.2 — Anti-énumération (mitigée autrement)

`BaseRepositoryV4.get(id)` retourne `None` si l'objet appartient à une autre org
→ `404` côté API. Un attaquant qui devine `/api/v4/action-center/items/{id}` ne
peut pas distinguer "n'existe pas" de "existe mais autre org" — l'énumération
**cross-org** est neutralisée au niveau applicatif (fail-closed M2-3.C).

L'énumération **intra-org** reste possible (un user devine les IDs de ses propres
items) mais sans gain — il a déjà accès légitime. Trade-off détaillé : ADR-009 §5.3.

Tests preuve : `test_get_blocks_cross_org_access`, `test_list_all_filters_by_current_org`
(`backend/tests/repositories/test_base_v4.py`).

### 3.3 — PG-ready (maintenue)

Integer FK est nativement PostgreSQL. Index B-tree plus compact (4-8 octets vs
16 pour UUID), jointures plus rapides. Aucune dégradation — légère amélioration.

---

## 4. Conséquences

### Positives

- Dette JWT/UUID **supprimée à la racine** — pas de dict de mapping à maintenir,
  pas de ticket de sortie différé.
- Performance : Integer FK + index B-tree natif (vs UUID 16 octets).
- Cohérence single-source-of-truth pour `org_id` (legacy + V4 partagent `organisations.id`).
- `populate_org_context` simplifié — pas de transformation de type.

### Négatives

- URL `/api/v4/action-center/items/{id}` énumérables par incrément (mitigée — §3.2).
- Ré-ouverture nécessaire si un signal de re-bascule UUID se matérialise
  (cf. ADR-009 §5.4 — besoin multi-shard, exposition API publique non-auth,
  audit externe P0/P1, migration hors PostgreSQL).

### Neutres

- Migration BDD requise (M2-4.1) — réalisable **sans backfill** car les 8 tables
  V4 sont vides au moment de l'amendement (cf. §5).

---

## 5. Condition de fenêtre d'exécution

Cet amendement n'est applicable **sans backfill que** parce que les 8 tables V4
sont **vides** au moment de la décision (audit M2-4.0 §6 — aucun seed V4 n'existe).

⚠️ **Garde-fou M2-4.1** : avant tout `ALTER TABLE`, vérifier explicitement que
les 8 tables retournent `COUNT(*) = 0`. Si une seule ligne existe (test local,
fork, staging), un backfill préalable (mapping int↔UUID des rows existantes) est
requis. Cette vérification est intégrée au prompt M2-4.1.

---

## 6. Conditions de re-bascule UUID

Référence centralisée : `docs/decisions/adr/009-jwt-uuid-resolution.md` §5.4.

En résumé — ré-ouvrir ADR-009 + cet avenant si : besoin réel multi-shard PG ·
exposition API publique non-authentifiée d'URL V4 · audit externe identifiant
l'énumération comme P0/P1 · migration de stack DB hors PostgreSQL.
