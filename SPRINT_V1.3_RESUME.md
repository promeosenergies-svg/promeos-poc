# RÉSUMÉ SPRINT V1.3 — Questionnaire + Correctifs UX/Bugs

**Date** : 2026-03-14
**Scope** : V1.3 Questionnaire + 6 correctifs UX/bugs
**Tests** : 5 585/5 585 ALL PASSED

---

## A. QUESTIONNAIRE V1.3 — 5 actions

| # | Action | Statut |
|---|--------|--------|
| Q1 | Titre modal : "Personnalisez votre cockpit énergie" + sous-titre adapté | **FAIT** |
| Q2 | Nouvelle question `q_surface_seuil` (seuil 1000 m² Décret Tertiaire) | **FAIT** |
| Q3 | Message de confirmation visible après validation (icône + texte + auto-close 3s) | **FAIT** |
| Q4 | Badge "Adapté à votre profil" sur page Conformité | **FAIT** |
| Q5 | Bandeau "Secteur détecté : {label}" pré-rempli depuis patrimoine | **FAIT** |

### Fichiers modifiés
- `frontend/src/components/SegmentationQuestionnaireModal.jsx` — réécriture V1.3 complète
- `backend/services/segmentation_service.py` — ajout question q_surface_seuil
- `frontend/src/pages/ConformitePage.jsx` — import segProfile + badge "Adapté"

---

## B. CORRECTIFS UX/BUGS — 6 actions

| # | Problème | Cause | Fix | Statut |
|---|----------|-------|-----|--------|
| B1 | CEE visible partout | Sections CEE dans 4 pages | Masqué (code conservé, désactivé) | **FAIT** |
| B2 | Sparkline confus (trait vert) | Petit graphe sans contexte ni légende | Retiré, texte tendance conservé | **FAIT** |
| B3 | Trend "42→59" mais score = 54 | Dernier snapshot historique ≠ score live | Utilise `kpi.rawValue` (score live) comme dernier point | **FAIT** |
| B4 | 500% Couverture contrats | `sitesWithContract / totalSites` sans cap | Ajout `Math.min(100, ...)` | **FAIT** |
| B5 | Tabs Consommations : Explorer en 1er | Ordre historique | Portefeuille en 1er, redirections mises à jour | **FAIT** |
| B6 | "Voir anomalies" ne fonctionne pas | Site pas dans `scopedSites` → toast erreur | Fallback : navigate vers `/compliance/sites/{id}` | **FAIT** |

### Fichiers modifiés
- `frontend/src/ui/evidence.fixtures.js` — CEE retiré
- `frontend/src/pages/ConformitePage.jsx` — CEE masqué
- `frontend/src/pages/RegOps.jsx` — CEE masqué
- `frontend/src/pages/SiteCompliancePage.jsx` — CEE badge/kanban retirés
- `frontend/src/pages/cockpit/ExecutiveKpiRow.jsx` — sparkline retiré, trend utilise score live
- `frontend/src/models/purchaseSignalsContract.js` — cap 100% couverture
- `frontend/src/pages/ConsommationsPage.jsx` — Portefeuille en 1er tab
- `frontend/src/App.jsx` — redirections `/consommations` → portfolio
- `frontend/src/pages/Patrimoine.jsx` — "Voir anomalies" fallback navigation
- `frontend/src/__tests__/step33_sparkline_guard.test.js` — tests adaptés

---

## C. PROCHAINES ÉTAPES

| # | Action | Priorité |
|---|--------|----------|
| 1 | Audit complet parcours B2B France (Organisation → Entité → Portefeuille → Site → Bâtiment → Compteurs → Conformité) | P0 |
| 2 | Connecter q_surface_seuil → filtrage conformité (masquer DT si < 1000 m²) | P1 |
| 3 | KPI cards tooltips (détails en bulle info) | P2 |
| 4 | Filtrage réglementations par profil utilisateur | P1 |
| 5 | Push GitHub | P0 |
