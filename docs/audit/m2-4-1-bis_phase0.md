# M2-4.1.bis — Phase 0 audit READ-ONLY (STOP GATE)

> Sprint : seed V4 idempotent · Branche `feat/m2-4-rollout` (hash courant `6423d40d`).
> Phase 0 = lecture seule. Aucun fichier code/test/migration modifié. Ce rapport
> est le seul artefact produit.

---

## 1. Synthèse (5 lignes)

1. **Aucun seed V4 préexistant** — `test_v4_seed_endpoints.py` teste le pattern RBAC
   M2-3 (`require_v4_role` + `require_non_prod_env`), PAS le seed des 8 tables V4.
   Créer un nouveau module seed est donc correct, sans risque de duplication.
2. **DB de dev (`data/promeos.db`) est à `p37bilan`** — la migration `m2s2v4`
   n'y est PAS appliquée → **les 8 tables V4 n'existent pas** (≠ vides : absentes).
3. **1 seule organisation** en DB : HELIOS `id=1` (Integer, `is_demo=1`). `id=42`
   (proposé D1) n'existe pas.
4. **`PRAGMA foreign_keys=ON` est déjà garanti** par un listener `connect` dans
   `database/connection.py` → C2 satisfait, Phase 2 §3.1 (ajout listener) inutile.
5. **Org-scoping cardinal** : un item V4 sous une org ≠ org du JWT démo (HELIOS=1)
   serait **invisible** dans la démo → `id=42` produirait des données orphelines.

---

## 2. §1.1 — Fichiers seed existants

`demo_seed` est un **package** (`services/demo_seed/`), pas un fichier unique.

| Catégorie | Fichiers | Mentionne `org`/`org_id` |
|---|---|---|
| Orchestrateur | `services/demo_seed/orchestrator.py` (`SeedOrchestrator.seed(pack,size,…)`) | oui — pilote HELIOS/CASINO |
| Générateurs pack | `services/demo_seed/gen_*.py` (≈25 fichiers) | `gen_actions.py` seede `action_items` **legacy** |
| Seeds domaine | `services/billing_seed.py`, `bacs_seed.py`, `purchase_seed.py`… | `seed_purchase_demo(db, org_id=1)` |
| Script | `scripts/seed_data.py` (génère Org→Site→Compteur legacy) | oui |
| Endpoints | `routes/demo.py` (`seed_demo_pack`, `seed_demo`) | oui |
| Tests | `tests/test_seed_idempotence.py`, `test_demo_seed*.py` | pattern count-before/after |

**Convention repo** : `def seed_X_demo(db: Session, org_id: int = 1) -> dict`.
**`grep V4 / action_center` sur `orchestrator.py` + `packs.py` → 0 résultat** :
le pipeline de seed actuel ignore totalement les tables V4.

## 3. §1.3 — État des 8 tables V4

| Vérif | Résultat |
|---|---|
| `data/promeos.db` révision Alembic | **`p37bilan`** (= `down_revision` de `m2s2v4`) |
| 8 tables V4 (`action_center_items`, …) | **`no such table`** — absentes (migration non appliquée) |

⚠️ **F1 (P0 — prérequis opérationnel, pas un bug code)** : avant tout run du seed
V4 sur la DB de dev, il faut `alembic upgrade m2s2v4`. Le sprint doit inclure
cette étape (ou la documenter comme précondition). Les tests isolés (in-memory)
ne sont pas concernés — ils créent les tables via `Base.metadata.create_all`.

## 4. §1.4 — PRAGMA foreign_keys

**Déjà actif.** `database/connection.py` lignes 50-60 :

```python
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA foreign_keys=ON")   # Sprint C-5 Phase 5.6 F1
```

→ Toute session issue de `SessionLocal` / `get_db()` a `foreign_keys=ON`.
**C2 satisfait.** Phase 2 §3.1 (ajouter un listener) devient **un simple test de
non-régression** vérifiant que le PRAGMA est bien actif — pas un ajout de code.

## 5. §1.6 — Modèle `ActionCenterItem` (champs requis seed minimal)

NOT NULL **sans** default → à fournir : `organisation_id` (Integer FK),
`kind` (7 valeurs), `title`, `priority_bracket` (P0-P3), `priority_score` (0-100).
`id` auto (`default=uuid4`). `lifecycle_state` `server_default='new'`.

`lifecycle_state` ∈ `{new, triaged, planned, in_progress, closed}` — **il n'existe
pas de valeur "ouvert/en_cours/résolu"**. CHECK `chk_closure_consistency` (IL10) :
`lifecycle_state='closed'` ⇒ `closed_at` ET `closure_reason` NOT NULL ;
`!= 'closed'` ⇒ `closed_at` IS NULL.

---

## 6. Confirmation des décisions D1-D6

| # | Prompt (défaut proposé) | Recommandation Phase 0 | Justification |
|---|---|---|---|
| **D1** | org seed `id=42` | **`org_id=1` (HELIOS)** ⚠️ change le défaut | Le JWT démo porte org HELIOS=1 ; en `DEMO_MODE` le contexte org doit être set explicitement sur l'org démo. Un item sous `id=42` est **invisible** (org-scoping `BaseRepositoryV4`). `id=42` dans `TestRealJwtPath` est une valeur JWT synthétique, jamais en DB → ne contraint rien. |
| **D2** | nom `"PROMEOS Demo Org"` | **Sans objet** | Avec D1=1, le seed V4 ne crée pas d'org : HELIOS la possède déjà. |
| **D3** | `INSERT OR IGNORE`, pas `OR REPLACE` | **Confirmé** | + PK `action_center_items` = UUID5 déterministe (`uuid5(NAMESPACE_DNS, "promeos-seed-v4-{n}")`) → idempotence sans lookup. |
| **D4** | org + 3 `action_center_items` | **Confirmé, statuts re-mappés** | "ouvert"→`new`, "en_cours"→`in_progress`, "résolu"→`closed` (+`closed_at`+`closure_reason='resolved'` sinon CHECK IL10 échoue). 7 autres tables V4 non seedées. |
| **D5** | réutiliser HELIOS si compatible | **OUI — réutiliser HELIOS `id=1`** | Integer, existe, cohérent. Le seed V4 **exige** que l'org existe (sinon `SeedError` explicite) ; il ne crée pas d'org (séparation : la création d'org appartient au seed HELIOS — respecte C5). |
| **D6** | test FK RESTRICT obligatoire | **Confirmé** | Test sur DB isolée in-memory : crée org + 1 item, `DELETE FROM organisations` → attend `IntegrityError`. N'utilise PAS l'org de dev. |

### Conséquence design si D1=1 / D5=oui (recommandé)
Le module `v4_seed.py` a **une seule responsabilité** : seeder `action_center_items`.
`_seed_organisation` de la spec §3.3 devient `_require_org(db, org_id)` :
- org absente → `raise SeedError("org {id} introuvable — lancer le seed HELIOS d'abord")`.
- org présente → continuer.
Pour les tests isolés, la fixture crée elle-même l'`Organisation(id=1)` avant le seed.

> Variante B (si tu préfères l'auto-suffisance du prompt) : org dédiée `id=42`
> créée par le seed. **Coût** : données invisibles dans la démo tant que le JWT
> démo n'est pas repointé sur `42` (changement hors périmètre M2-4.1.bis).

---

## 7. Hypothèses prudentes (≤3)

1. La DB de dev sera amenée à `m2s2v4` (`alembic upgrade`) avant exécution du seed
   réel — étape ajoutée au sprint (F1).
2. Les endpoints V4 (`POST/GET /api/actions`) n'existent pas encore (M2-4.2+) →
   le test §4.3 "e2e" devient un test **repo/model** (`BaseRepositoryV4` + contexte
   org), pas un test HTTP. Conforme à la clause de repli du prompt.
3. Le seed V4 reste **opt-in** : non branché dans l'orchestrateur HELIOS par défaut
   (C5) — exposé via CLI dédiée + flag `--with-v4`.

## 8. Questions bloquantes (≤3)

1. **D1 — org cible** : `org_id=1` (HELIOS, recommandé, données visibles en démo)
   ou org dédiée `id=42` (auto-suffisant mais invisible) ? *Décision requise.*
2. **F1 — upgrade DB dev** : autorises-tu le sprint à exécuter `alembic upgrade
   m2s2v4` sur `data/promeos.db` (additif, réversible, Q13-B) ? Sinon le seed ne
   tournera qu'en test in-memory.
3. **Module cible** : `backend/seeds/v4_seed.py` (nouveau dossier, conforme prompt)
   ou `backend/services/demo_seed/gen_v4.py` (cohérent avec le package seed
   existant) ? Le prompt impose `seeds/` — je confirme sauf objection.

---

➡️ **STOP GATE — en attente de validation explicite avant Phase 1.**
Merci de trancher D1 + Q2 (F1) + Q3, et de confirmer D3/D4/D6.
