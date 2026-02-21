# V49 — Action Close Rules + Proof Workflow (OPERAT)

## FAITS

1. **V47 (frontend-only)** : La clôturabilité OPERAT était évaluée uniquement côté frontend (`isActionClosable`). Un appel API direct pouvait clôturer sans preuve.
2. **V48 (persistence)** : Le lien action ↔ preuve est persisté en KB SQLite (`action_proof_link`). Le backend peut maintenant vérifier les preuves liées.
3. **PATCH route** : `PATCH /api/actions/{id}` acceptait tout changement de statut sans vérification côté serveur.
4. **Modèle ActionItem** : Aucun champ `closure_justification` n'existait pour stocker une justification de clôture.

## HYPOTHESES

1. Une « preuve validée » signifie un doc KB lié avec `status ∈ {validated, decisional}`.
2. Une justification de clôture de ≥ 10 caractères est un fallback acceptable quand aucune preuve n'est disponible.
3. Le service `action_close_rules.py` est la source de vérité unique (pas le frontend).
4. Les actions non-OPERAT ne sont pas concernées par ces règles (clôture libre).

## DECISIONS

| # | Decision | Justification |
|---|----------|---------------|
| D1 | Service `action_close_rules.py` | Source de vérité unique pour la closabilité. Séparation responsabilité. |
| D2 | `closure_justification TEXT` dans ActionItem | Colonne nullable, additive, auto-migrée par le système existant. |
| D3 | PATCH `status=done` → HTTP 400 si non closable | Enforcement serveur. Le frontend ne peut pas contourner. |
| D4 | `GET /{id}/closeability` endpoint | Pre-check avant tentative de clôture (UX optimiste). |
| D5 | Guided close form frontend | Textarea justification apparaît si le pré-check échoue. Min 10 chars. |
| D6 | Gestion HTTP 400 dans handleStatusChange | Le drawer affiche le message d'erreur backend au lieu d'un toast générique. |
| D7 | Aide FR mise à jour (V49 rules) | Texte reflète les nouvelles règles (justification au lieu de `[justifié]`). |

## Schema

```sql
-- Additive column on action_items (main ORM DB)
ALTER TABLE action_items ADD COLUMN closure_justification TEXT;
```

## Fichiers modifies

| Fichier | Action |
|---------|--------|
| `backend/models/action_item.py` | +colonne `closure_justification` |
| `backend/services/action_close_rules.py` | **NEW** — `is_operat_action`, `check_closable` |
| `backend/routes/actions.py` | +import close rules, +enforcement PATCH, +`GET /closeability`, +serialize |
| `backend/tests/test_action_close_rules_v49.py` | 19 tests: service + endpoint + source guards |
| `frontend/src/services/api.js` | +`checkActionCloseability` |
| `frontend/src/components/ActionDetailDrawer.jsx` | Guided close form, justification textarea, HTTP 400 handling |
| `frontend/src/pages/KBExplorerPage.jsx` | +close rule hint dans le banner action |
| `frontend/src/pages/__tests__/actionCloseRulesV49.test.js` | 29 source guards |
| `frontend/src/pages/__tests__/operatProofLoopV47.test.js` | Mise à jour aide FR guard (V49 compat) |

## Test results

- Backend: 39/39 (V48 + V49 + tertiaire) — 0 fail
- Frontend: 1843/1843 — 0 fail, 0 regression
