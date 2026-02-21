# V48 — Action-Proof Persistence

## FAITS

1. **V47 (URL-only)** : Le lien Action → Preuve passait par des query-params dans l'URL (`/kb?action_id=X`). Un refresh ou un autre navigateur perdait le contexte.
2. **KB SQLite** : La base KB (`kb.db`) utilise SQLite avec `CREATE TABLE IF NOT EXISTS` (pas d'Alembic). Le schéma est dans `app/kb/models.py`.
3. **Deux bases** : Les actions sont en SQLAlchemy ORM (`promeos.db`), les documents KB sont en SQLite (`kb.db`). Le lien action↔doc doit vivre côté KB.
4. **Upload dedup** : `POST /api/kb/upload` retourne `already_exists` si le SHA256 du fichier est identique. Le lien action doit être créé même dans ce cas.

## HYPOTHESES

1. Un `action_id` est un entier stable (clé primaire SQLAlchemy). Le lien `(action_id, kb_doc_id)` est unique.
2. La table `action_proof_link` dans KB SQLite est suffisante pour la persistance (pas besoin de colonne action_id dans la table kb_docs).
3. Le fallback vers les preuves EFA (`getTertiaireEfaProofs`) reste nécessaire tant que toutes les preuves ne sont pas migrées vers le système persistant.

## DECISIONS

| # | Decision | Justification |
|---|----------|---------------|
| D1 | Table `action_proof_link` dans KB SQLite | Même DB que les docs, pas de cross-DB FK, idempotent via `CREATE TABLE IF NOT EXISTS` |
| D2 | UNIQUE(action_id, kb_doc_id) pour dedup | Un même doc ne peut être lié qu'une fois à une action |
| D3 | `proof_type TEXT` nullable | Permet de typer la preuve (ex: `attestation_conso`) sans rendre le champ obligatoire |
| D4 | Auto-link sur upload quand `action_id` est fourni | Le backend crée le lien automatiquement, le frontend n'a qu'à passer le param |
| D5 | Endpoints sur `/actions/{id}/proofs` | GET pour lister, POST pour lier — logique REST sous le router actions |
| D6 | Frontend: persistent API first, EFA fallback | `getActionProofs` est appelé en premier, `getTertiaireEfaProofs` en fallback |
| D7 | DocCard "Lier à l'action" button | Permet de lier un doc existant à une action depuis la Mémobox |

## Schema

```sql
CREATE TABLE IF NOT EXISTS action_proof_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id INTEGER NOT NULL,
    kb_doc_id TEXT NOT NULL,
    proof_type TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(action_id, kb_doc_id)
);
CREATE INDEX IF NOT EXISTS idx_apl_action ON action_proof_link(action_id);
CREATE INDEX IF NOT EXISTS idx_apl_doc ON action_proof_link(kb_doc_id);
```

## Fichiers modifies

| Fichier | Action |
|---------|--------|
| `backend/app/kb/models.py` | +migration table `action_proof_link` |
| `backend/app/kb/store.py` | +`link_doc_to_action`, `list_action_proofs`, `unlink_doc_from_action` |
| `backend/app/kb/router.py` | +`action_id` param sur `POST /upload` + auto-link |
| `backend/routes/actions.py` | +`GET /{id}/proofs`, `POST /{id}/proofs/{doc_id}` |
| `backend/tests/test_action_proofs_v48.py` | 8 tests CRUD + dedup + JOIN |
| `frontend/src/services/api.js` | +`getActionProofs`, `linkProofToAction`, `uploadKBDoc` + `actionId` |
| `frontend/src/components/ActionDetailDrawer.jsx` | Persistent fetch + EFA fallback |
| `frontend/src/pages/KBExplorerPage.jsx` | Upload avec `action_id`, bouton "Lier à l'action" |
| `frontend/src/pages/__tests__/actionProofPersistenceV48.test.js` | 25 source guards |
