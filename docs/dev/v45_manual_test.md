# V45 — Controles V2 + Preuves actionnables — Test manuel

## Pre-requis

- Backend demarre (`python main.py`)
- Frontend demarre (`npm run dev`)
- Au moins 1 EFA creee (via wizard ou API)

---

## 1. Proof Catalog (backend)

| # | Action | Resultat attendu |
|---|--------|-----------------|
| 1.1 | `GET /api/tertiaire/proof-catalog` | 200, `proofs` array >= 6, chaque entry a `type`, `label_fr`, `owner_role` |
| 1.2 | Verifier `attestation_operat` present | `label_fr` contient "Attestation" |
| 1.3 | Verifier `bail_titre_propriete` present | `label_fr` contient "Bail" ou "titre" |

## 2. Proofs Status (backend)

| # | Action | Resultat attendu |
|---|--------|-----------------|
| 2.1 | `GET /api/tertiaire/efa/{id}/proofs` | 200, `expected_count` >= 2, `deposited_count` = 0, `coverage_pct` = 0 |
| 2.2 | `GET /api/tertiaire/efa/99999/proofs` | 404 |
| 2.3 | Verifier `expected` contient `attestation_operat` et `bail_titre_propriete` | Les 2 types presents |

## 3. Proof Link (backend)

| # | Action | Resultat attendu |
|---|--------|-----------------|
| 3.1 | `POST /api/tertiaire/efa/{id}/proofs/link` avec `{"kb_doc_id":"test","proof_type":"attestation_operat"}` | 201, `status: "linked"` |
| 3.2 | Refaire le meme POST | 201, `status: "already_linked"` |
| 3.3 | `GET /api/tertiaire/efa/{id}/proofs` apres link | `deposited_count` = 1, `coverage_pct` > 0 |

## 4. Controls V2 (backend)

| # | Action | Resultat attendu |
|---|--------|-----------------|
| 4.1 | `POST /api/tertiaire/efa/{id}/controls` | 200, chaque issue a `title_fr`, `proof_required` (ou null), `proof_links` (array) |
| 4.2 | Verifier TERTIAIRE_NO_BUILDING | `severity: "critical"`, `title_fr` non vide |
| 4.3 | Verifier TERTIAIRE_NO_RESPONSIBILITY | `proof_required.type = "bail_titre_propriete"`, `proof_links` contient `context=proof` |
| 4.4 | Lancer 2x controles sur meme EFA | Resultats identiques (determinisme) |

## 5. EFA Detail Page (frontend)

| # | Action | Resultat attendu |
|---|--------|-----------------|
| 5.1 | Ouvrir `/conformite/tertiaire/efa/{id}` | Page charge, status card visible |
| 5.2 | Verifier bloc "Statut des preuves" | 3 compteurs: Attendues (>= 2), Deposees, Validees. Barre de couverture visible |
| 5.3 | Bouton "Voir dans la Memobox" | Navigue vers `/kb?context=proof&efa_id={id}` |
| 5.4 | Cliquer "Controles" | Anomalies s'affichent |
| 5.5 | Verifier une issue avec `proof_required` | Bloc indigo "Preuve attendue" avec label + responsable + deadline |
| 5.6 | Bouton "Deposer la preuve" sur une issue | Navigue vers Memobox avec `proof_type` et `efa_id` dans l'URL |

## 6. Anomalies Page (frontend)

| # | Action | Resultat attendu |
|---|--------|-----------------|
| 6.1 | Ouvrir `/conformite/tertiaire/anomalies` | Page charge, filtres visibles |
| 6.2 | Verifier une issue avec `title_fr` | Titre en gras au-dessus du message |
| 6.3 | Verifier une issue avec `proof_required` | Bloc indigo "Preuve attendue" visible |
| 6.4 | Bouton "Deposer la preuve" (deep-link) | Navigue vers Memobox avec `proof_type` dans l'URL |
| 6.5 | Issue sans `proof_links` | Fallback vers ProofDepositCTA generique |

## 7. Memobox — Proof Prefilter (frontend)

| # | Action | Resultat attendu |
|---|--------|-----------------|
| 7.1 | Ouvrir `/kb?context=proof&domain=conformite/tertiaire-operat&proof_type=attestation_operat&efa_id=1` | Tab Documents active, banner preuve visible |
| 7.2 | Verifier banner | "Preuve attendue", domaine "Conformite / Tertiaire OPERAT", type "attestation operat", "EFA #1" |
| 7.3 | Bouton "Effacer filtres" | Banner disparait, retour a l'onglet Items |
| 7.4 | Sur un document, bouton "Lier a l'EFA" | Appel API, message "Preuve liee a l'EFA #1" |
| 7.5 | Relancer "Lier a l'EFA" sur le meme doc | Message "Preuve deja liee a cette EFA" |

---

## Suites de tests automatisees

```bash
# Backend (31 tests V45 + 62 regression)
cd backend && venv/Scripts/python -m pytest tests/test_v45_controls_v2.py tests/test_v45_proof_catalog.py tests/test_v44_patrimoine_operat.py tests/test_v42_site_signals.py tests/test_v41_efa_patrimoine.py tests/test_router_mount_tertiaire.py tests/test_export_memobox_v40.py -v -p no:warnings

# Frontend (40 tests V45 + 1623 regression)
cd frontend && npx vitest run
```

Criteres de validation : 0 fail, 0 regression, UI 100% FR.
