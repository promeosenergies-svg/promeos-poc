# V50 — OPERAT Proof Catalog V2 + Templates (issue → preuves attendues)

## FAITS

- V45 avait un `PROOF_CATALOG` basique (6 types, labels simples) dans `tertiaire_proofs.py`
- Les `CONTROL_RULES` (V40) définissent 8 codes d'issue avec `proof_required` structuré
- La KB store (V48) expose `upsert_doc()` pour créer des documents et `link_doc_to_action()` pour les lier aux actions
- Le frontend (V47-V49) affiche un bloc "Preuves OPERAT" dans le drawer d'action avec compteurs et CTAs

## HYPOTHESES

- **Mapping issue→preuves** : les associations issue_code → proof_types sont basées sur la pratique courante OPERAT
  - `confidence: "high"` = confirmé par textes réglementaires (Décret tertiaire, arrêté OPERAT)
  - `confidence: "medium"` = déduit de la pratique courante (bail, multi-occupation)
  - `confidence: "low"` = V1 à confirmer — TODO vérification réglementaire
- **Templates draft** : les modèles générés sont des brouillons (status="draft") destinés à être remplacés par les preuves réelles

## DECISIONS

### D1 — Catalogue enrichi séparé (tertiaire_proof_catalog.py)
- Nouveau module `services/tertiaire_proof_catalog.py` distinct de `tertiaire_proofs.py` (V45)
- `PROOF_TYPES` : 6 types avec title_fr, description_fr, examples_fr[], template_kind
- `ISSUE_PROOF_MAPPING` : 8 codes d'issue → proof_types + rationale_fr + confidence
- 3 fonctions API : `get_proof_types()`, `get_issue_proof_mapping()`, `get_proofs_for_issue(issue_code)`

### D2 — Génération de templates Mémobox (tertiaire_proof_templates.py)
- `render_template_md(proof_type, context)` → (filename, content_md, display_name)
- `generate_proof_templates(efa_id, year, issue_code, proof_types, action_id?)` :
  - Crée des docs KB draft via `KBStore.upsert_doc()`
  - Dedup par doc_id déterministe : `operat_template:{efa_id}:{year}:{proof_type}`
  - Auto-link vers action via `KBStore.link_doc_to_action()` si action_id fourni
  - source_type = "md" (respecte CHECK constraint KB)

### D3 — 4 nouveaux endpoints
- `GET /api/tertiaire/proofs/catalog` — catalogue enrichi V50
- `GET /api/tertiaire/proofs/issue-mapping` — mapping complet
- `GET /api/tertiaire/issues/{issue_code}/proofs` — preuves pour une anomalie
- `POST /api/tertiaire/efa/{efa_id}/proofs/templates?year=YYYY` — génération templates

### D4 — Frontend : preuves attendues + CTA templates
- Nouveau bloc "Preuves attendues" dans le drawer d'action (data-testid="v50-expected-proofs")
- Affiche title_fr, description_fr, examples_fr, confidence badge, rationale_fr
- CTA "Créer les modèles dans la Mémobox" (data-testid="v50-generate-templates-cta")
- Feedback toast après génération

### D5 — Fix pre-existing JSX tag mismatch (TertiaireAnomaliesPage)
- Corrigé un `</div>` manquant qui cassait le build (erreur pré-existante, pas V50)

## FICHIERS MODIFIES

| Fichier | Action | Lignes |
|---------|--------|--------|
| `backend/services/tertiaire_proof_catalog.py` | NEW | ~207 |
| `backend/services/tertiaire_proof_templates.py` | NEW | ~160 |
| `backend/routes/tertiaire.py` | MODIFY | +import V50, +4 endpoints |
| `backend/tests/test_proof_catalog_v50.py` | NEW | 36 tests |
| `frontend/src/services/api.js` | MODIFY | +3 exports V50 |
| `frontend/src/components/ActionDetailDrawer.jsx` | MODIFY | +expected proofs bloc, +template CTA |
| `frontend/src/pages/tertiaire/TertiaireAnomaliesPage.jsx` | FIX | JSX tag mismatch |
| `frontend/src/pages/__tests__/proofCatalogV50.test.js` | NEW | 39 guards |

## TESTS

- Backend : 36 tests V50 + 102 total (0 régression)
- Frontend : 39 guards V50 + 106 total (0 régression)
- Build : OK
