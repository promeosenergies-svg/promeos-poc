# V45 — Contrôles V2 + Preuves actionnables : Audit Flash

## FAITS

1. **CONTROL_RULES** : 6 règles V1 dans `tertiaire_service.py:81-148`, dont seulement 2 portent `proof_required` (NO_RESPONSIBILITY + SURFACE_COHERENCE)
2. **proof_required_json** : format `{"label": "...", "owner": "..."}` — très basique, pas de type structuré, pas de deadline, pas de domain KB
3. **TertiaireProofArtifact** : modèle existant (`tertiaire.py:108-122`) avec `type`, `kb_doc_id`, `owner_role`, `valid_from/to`, `tags_json` — bridge EFA↔KB fonctionnel
4. **TertiaireDataQualityIssue** : modèle existant (`tertiaire.py:125-142`) avec severity (critical/high/medium/low), status (open/ack/resolved/false_positive), proof_required_json, proof_owner_role
5. **generate_operat_pack** : crée un ProofArtifact de type `operat_export_pack` + KB doc avec domain `conformite/tertiaire-operat` + status `review`
6. **KBExplorerPage** : gère `context=proof`, `domain`, `status`, `hint` en query params → bandeau proof context + filtres auto
7. **ProofDepositCTA** : composant existant, utilise `buildProofLink` → `/kb?context=proof&domain=...&hint=...`
8. **EFA detail page** : affiche `open_issues`, section preuves avec ProofDepositCTA, mais aucun compteur preuves attendues/déposées/validées
9. **Anomalies page** : liste issues avec severity/status filters, ProofDepositCTA par issue, transitions status (open→ack→resolved)
10. **KB docs** : colonnes `status` (draft/review/validated/decisional), `domain`, `meta_json` — peuvent stocker proof_type + efa_id

## HYPOTHÈSES

1. Le proof_required_json actuel est trop pauvre pour V45 — besoin d'un catalogue structuré
2. Le compteur preuves (attendues/déposées/validées) peut se baser sur ProofArtifact existant + KB doc status
3. Le lien proof→issue peut se faire via `tags_json` sur ProofArtifact (ex: `{"issue_code": "...", "year": ...}`)
4. Pas besoin d'un nouveau modèle — enrichir les existants suffit

## DÉCISIONS

| # | Décision | Justification |
|---|----------|---------------|
| D1 | **PROOF_CATALOG** dans `tertiaire_proofs.py` | Catalogue typé avec label_fr, owner_role, exemple_fichiers, deadline_hint, kb_domain |
| D2 | **Enrichir CONTROL_RULES V2** : 8-10 règles avec proof_required structuré | Chaque issue embarque proof_required complet (type + label + owner + deadline + deeplink) |
| D3 | **GET /efa/{id}/proofs?year=** endpoint | Retourne expected/deposited/validated avec counts |
| D4 | **POST /efa/{id}/proofs/link** endpoint | Lie un KB doc à une EFA comme preuve (crée ProofArtifact) |
| D5 | **Frontend : bloc "Preuves" + "Contrôles V2"** sur EFA detail | Compteurs + issues enrichies + CTA deep-link Mémobox |
| D6 | **KBExplorerPage** : enrichir bandeau proof avec proof_type | Afficher type preuve attendue si fourni en query param |

## FICHIERS MODIFIÉS/CRÉÉS

| Fichier | Action |
|---------|--------|
| `backend/services/tertiaire_proofs.py` | NEW — proof catalog + helpers |
| `backend/services/tertiaire_service.py` | MODIFY — CONTROL_RULES V2 |
| `backend/routes/tertiaire.py` | MODIFY — nouveaux endpoints proofs |
| `frontend/src/pages/tertiaire/TertiaireEfaDetailPage.jsx` | MODIFY — bloc preuves + contrôles V2 |
| `frontend/src/pages/tertiaire/TertiaireAnomaliesPage.jsx` | MODIFY — CTA proof enrichi |
| `frontend/src/pages/KBExplorerPage.jsx` | MODIFY — proof_type prefilter |
| `backend/tests/test_v45_*.py` | NEW — tests |
| `frontend/src/pages/__tests__/operatControlsV45.test.js` | NEW — tests |
