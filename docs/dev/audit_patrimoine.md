# Audit Patrimoine — FAITS / PROBLEMES / DECISIONS / FIXES

## Date : 2026-02-22 (V51-V52)

## FAITS

### Inventaire complet
- **Backend** : 35+ endpoints dans `routes/patrimoine.py` (1450 lignes)
- **Service** : `patrimoine_service.py` (992 lignes, pipeline DIAMANT)
- **Models** : Site, Batiment, Compteur, DeliveryPoint, StagingBatch, StagingSite, StagingCompteur, QualityFinding, ActivationLog, EnergyContract
- **Frontend** : Patrimoine.jsx, Site360.jsx, SiteDetail.jsx, PatrimoineWizard.jsx
- **API** : 35 fonctions frontend alignees avec les endpoints backend

### Routage
- 25/25 checks PASS : zero route cassee, zero CTA dead-end
- Routes : `/patrimoine`, `/sites/:id`, `/sites-legacy/:id`
- CTAs depuis : CommandCenter, Cockpit, ImpactDecisionPanel, TertiaireDashboard, TertiaireWizard, Site360

### API Contract
- 35/35 fonctions frontend matchent un endpoint backend
- Staging (11), Sites CRUD (7), Compteurs (4), Contrats (4), Autres (9)

### Chaine de valeur
- Zero orphan creation dans aucun module
- Tous les modules consomment le patrimoine via FK (site_id, building_id)
- EFA Wizard : selectionne des batiments existants, CTA si 0 batiment

## PROBLEMES IDENTIFIES

1. **3 wrappers API manquants** (V51) : `stagingExportReport`, `patrimoineDeliveryPoints`, `patrimoineKpis` — CORRIGE
2. **1 doublon API** : `getImportTemplate` declare 2 fois dans api.js — CORRIGE (doublon supprime)
3. **Demo seed : EFA sans building_id reel** : `gen_tertiaire.py` creait des `TertiaireEfaBuilding` avec `building_id=None` — CORRIGE en V52 (buildings_map)
4. **Demo Casino/Tertiaire ne couvrent pas tous les modules E2E** — CORRIGE en V52 (pack HELIOS)

## DECISIONS

1. Patrimoine = source de verite unique. Pas de modification au modele.
2. 4 wrappers API ajoutes + 1 doublon supprime (V51)
3. 64 source guards tests couvrant Router, NavRegistry, API, CTAs, Wizard, Pages, Backend
4. Nouvelle demo E2E "Groupe HELIOS" (V52) couvrant tous les modules
5. EFA buildings lies aux vrais batiments dans la demo HELIOS

## FIXES APPLIQUES

| Version | Fix | Fichiers |
|---------|-----|----------|
| V51 | +4 wrappers API | `frontend/src/services/api.js` |
| V51 | -1 doublon getImportTemplate | `frontend/src/services/api.js` |
| V51 | +64 source guards | `frontend/src/pages/__tests__/patrimoineAuditV51.test.js` |
| V52 | Pack HELIOS E2E | `backend/services/demo_seed/packs.py` + generators |
| V52 | buildings_map dans gen_tertiaire | `backend/services/demo_seed/gen_tertiaire.py` |

## PARCOURS E2E ATTENDU

1. Utilisateur charge la demo HELIOS
2. Patrimoine : 5 sites, 7 batiments, compteurs, contrats visibles
3. Conformite : site-signals qualifie 4 sites assujettis, 1 non concerne
4. OPERAT : CTA "Creer EFA" mene au wizard prerempli avec batiments existants
5. Factures : factures visibles pour chaque site, anomalies detectees
6. Achats : contrat expirant declenche lever "Renouveler"
7. Actions : actions OPERAT visibles avec preuves attendues
8. Memobox : preuves et templates accessibles
