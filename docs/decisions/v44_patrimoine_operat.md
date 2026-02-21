# V44 — Patrimoine → OPERAT : Audit Flash

## FAITS

1. **TertiaireEfa.site_id** existe déjà (FK nullable, `backend/models/tertiaire.py:23`) — le lien Patrimoine→EFA est en place
2. **Surface READ-ONLY** dans le wizard — calculée depuis `selectedBuildings`, jamais saisie manuellement
3. **site_id inféré** depuis le premier bâtiment si non fourni (`routes/tertiaire.py:186-194`)
4. **Surface snapshotée** depuis `Batiment.surface_m2` à la création EFA (`routes/tertiaire.py:214`)
5. **usage_label** initialisé vide (`''`) lors du prefill site_id — l'utilisateur doit le choisir manuellement
6. **Lever ctaPath** ne porte PAS le `site_id` — `'/conformite/tertiaire'` sans paramètre (gap critique)
7. **`/site-signals`** (V42+V43) retourne déjà : signal, is_covered, recommended_cta, reasons_fr — suffisant comme endpoint "sites à traiter"
8. **`/catalog`** retourne sites + bâtiments (id, nom, surface_m2, annee_construction) pour le wizard
9. **Aucune protection** contre la création de doublons EFA pour un même site
10. **EFA nom** n'est PAS pré-rempli lors du prefill `?site_id=X`

## HYPOTHESES

1. Pas besoin d'un nouvel endpoint `/sites-to-process` — `/site-signals` couvre le besoin
2. Le wizard peut pré-remplir le nom EFA depuis le nom du site (catalog)
3. Un warning (non bloquant) suffit pour la dédup EFA/site

## DECISIONS

| # | Décision | Justification |
|---|----------|---------------|
| D1 | **Pas de nouvel endpoint** — `/site-signals` suffit | Déjà en place V42+V43, contient signal + CTA + reasons |
| D2 | **Wizard : pré-remplir nom EFA** depuis site_nom quand `?site_id` | Zéro saisie manuelle, l'utilisateur peut modifier |
| D3 | **Lever deep-link : ajouter `site_id`** au ctaPath create-efa | Navigation directe wizard→site pré-rempli |
| D4 | **Backend : warning dedup** dans POST /efa si site a déjà une EFA | Non bloquant, info utilisateur |
| D5 | **Dashboard : aucun changement** — V43 est complet | "Sites à traiter" + drawer + filtres déjà fonctionnels |
| D6 | **Surface : confirmer RO** — aucune modification du wizard | Déjà en lecture seule, snapshot backend |

## FICHIERS MODIFIES (estimés)

| Fichier | Action | Détail |
|---------|--------|--------|
| `frontend/src/pages/tertiaire/TertiaireWizardPage.jsx` | MODIFY | Pré-remplir nom EFA depuis site_nom |
| `frontend/src/models/leverEngineModel.js` | MODIFY | Ajouter site_id au ctaPath create-efa |
| `backend/routes/tertiaire.py` | MODIFY | Warning dedup dans POST /efa |
| `frontend/src/pages/__tests__/patrimoineOperatV44.test.js` | NEW | Source guards V44 |
| `backend/tests/test_v44_patrimoine_operat.py` | NEW | Tests backend V44 |
