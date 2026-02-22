# V51 — Patrimoine : checklist de test manuel

## Pre-requis

- Backend demarre (`uvicorn main:app`)
- Frontend demarre (`npm run dev`)
- Donnees demo chargees (POST `/api/patrimoine/demo/load`)

---

## 1. Navigation

- [ ] Cliquer "Patrimoine" dans le menu lateral → arrive sur `/patrimoine`
- [ ] La page affiche le titre, les KPIs, le tableau des sites
- [ ] Cliquer sur un site dans le tableau → arrive sur `/sites/{id}`
- [ ] Sur Site360, cliquer le bouton retour → revient a `/patrimoine`

## 2. Filtres et recherche

- [ ] Les filtres URL-synced fonctionnent (`?search=xxx`, `?statut=xxx`)
- [ ] La recherche filtre les sites en temps reel
- [ ] Les KPIs se mettent a jour avec les filtres

## 3. Import Wizard (PatrimoineWizard)

- [ ] Ouvrir le wizard d'import depuis la page Patrimoine
- [ ] Etape 1 (Mode) : choix Normal / Express / Demo
- [ ] Mode Demo : les donnees se chargent sans upload
- [ ] Mode Normal : upload d'un fichier CSV/XLSX
- [ ] Etape 2 (Preview) : lignes importees visibles
- [ ] Etape 3 (Corrections) : issues qualite affichees, fix possible
- [ ] Etape 4 (Validation) : quality gate passe/echoue
- [ ] Etape 5 (Activation) : batch active dans production
- [ ] Etape 6 (Resultat) : resume de l'import

## 4. Sites CRUD

- [ ] Voir le detail d'un site (GET `/sites/{id}`)
- [ ] Modifier un champ (PATCH) → sauvegarde OK
- [ ] Archiver un site → disparait de la liste active
- [ ] Restaurer un site archive → reapparait

## 5. Compteurs

- [ ] Voir les compteurs d'un site
- [ ] Modifier un compteur
- [ ] Deplacer un compteur vers un autre site
- [ ] Detacher un compteur

## 6. Contrats

- [ ] Lister les contrats
- [ ] Creer un contrat energie
- [ ] Modifier un contrat
- [ ] Supprimer un contrat
- [ ] Verifier le controle de chevauchement (overlap)

## 7. CTAs cross-modules

- [ ] CommandCenter → bouton "Patrimoine" → `/patrimoine`
- [ ] CommandCenter → clic site → `/sites/{id}`
- [ ] ImpactDecisionPanel → CTA patrimoine → `/patrimoine`
- [ ] TertiaireDashboard → lien patrimoine → `/patrimoine`
- [ ] Cockpit → clic site → `/sites/{id}`

## 8. Exports

- [ ] Export CSV des sites (`/patrimoine/sites/export.csv`)
- [ ] Export rapport staging (`/patrimoine/staging/{id}/export/report.csv`)
- [ ] Template d'import (`/patrimoine/import/template`)

## 9. API Swagger

- [ ] Ouvrir `/docs` → section Patrimoine visible
- [ ] Tester GET `/api/patrimoine/sites` → 200 + JSON
- [ ] Tester GET `/api/patrimoine/kpis` → 200 + JSON

---

## Resultat attendu

- Zero erreur console (frontend)
- Zero 500 (backend)
- UI 100% en francais
- Toutes les navigations fonctionnent sans impasse
