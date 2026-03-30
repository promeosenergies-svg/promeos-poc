# RAPPORT D'AUDIT PATRIMOINE — Phase 0

> **Date** : 2026-03-29 | **Mode** : Read-only | **Statut** : En attente validation

---

## 1. Inventaire

### Backend — 23 endpoints patrimoine + 7 legacy

| Fichier | Lignes | Rôle |
|---------|--------|------|
| `routes/patrimoine/sites.py` | 937 | 23 endpoints (CRUD, anomalies, snapshot, portfolio) |
| `routes/sites.py` | 493 | 7 endpoints legacy (doublons partiels) |
| `services/patrimoine_service.py` | 1429 | Service principal (staging, quality, import, lineage) |
| `routes/patrimoine/_helpers.py` | ~650 | Helpers + `SiteUpdateRequest` (sans `extra="forbid"`) |
| `models/site.py` | 122 | Modèle SQLAlchemy Site |
| `models/compteur.py` | 59 | Modèle Compteur (`meter_id` = String logique, pas FK) |
| `schemas/patrimoine_schemas.py` | 136 | Schemas Pydantic existants (partiels) |

**Doublons identifiés** : `GET /api/sites` et `GET /api/sites/{id}` existent dans les deux modules (patrimoine + legacy).

### Frontend — 21 composants, 0 stubs, ~6800 lignes

| Composant | Lignes | Statut |
|-----------|--------|--------|
| `Patrimoine.jsx` | 2243 | Page principale + `SiteDrawerContent` inline |
| `Site360.jsx` | 1620 | 7 onglets, **tous câblés** (aucun TabStub) |
| `PatrimoineHeatmap.jsx` | 373 | N appels API (`Promise.all`, max 10 sites) |
| `TabConsoSite.jsx` | 202 | Câblé à `getEmsTimeseries()` |
| `TabActionsSite.jsx` | 210 | Câblé à `getActionsList()` |
| `SiteAnomalyPanel.jsx` | 316 | Câblé à `getPatrimoineAnomalies()` |
| `PatrimoinePortfolioHealthBar.jsx` | 375 | 5 sous-composants, états complets |
| `PatrimoineRiskDistributionBar.jsx` | 116 | Standalone, pas d'état loading |
| `PatrimoineWizard.jsx` | 1163 | Import CSV multi-step |

### Tests — 186 passed patrimoine, 3616 passed frontend

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| Backend patrimoine (10 fichiers) | **186** | 0 | 0 |
| Backend impact (1 fichier) | 0 | **1** | 0 |
| Frontend (145 fichiers) | **3616** | 0 | 2 |
| E2E | 2 journeys (cockpit + drill-down patrimoine) | — | — |

**Test en échec** : `test_patrimoine_impact_v59.py::test_defaults_valid` — attend `prix_elec_eur_mwh=180.0`, valeur réelle = `68.0`.

---

## 2. Constats classés

### P0 — Bloquants crédibilité démo

| # | Constat | Fichier | Impact |
|---|---------|---------|--------|
| P0-1 | **PATCH sans `extra="forbid"`** — `SiteUpdateRequest` accepte champs inconnus. Pas de validation SIRET, code_postal, surface > 0 | `_helpers.py:470` | Données corrompues possibles |
| P0-2 | **Heatmap N+1 API** — `Promise.all` de N appels `getPatrimoineAnomalies(siteId)` (max 10) | `Patrimoine.jsx:322` | Perf dégradée, timeout possible |
| P0-3 | **Favoris non scopés par org** — clé `promeos_fav_sites` globale dans localStorage | `Patrimoine.jsx:204` | Favoris mélangés entre orgs |
| P0-4 | **Test impact désynchronisé** — `prix_elec_eur_mwh` test=180 vs config=68 | `test_patrimoine_impact_v59.py:131` | CI rouge |

### P1 — Crédibilité B2B

| # | Constat | Fichier | Impact |
|---|---------|---------|--------|
| P1-1 | **Pas de contrainte `tertiaire_area_m2 ≤ surface_m2`** | Schemas + modèle | Données incohérentes acceptées |
| P1-2 | **`response_model` manquant** sur delivery-points, kpis, meters | `routes/patrimoine/sites.py` | Swagger incomplet |
| P1-3 | **Compteur.meter_id = lien logique** (String 14 vs 50), pas de FK SQL, dual-write non atomique | `models/compteur.py` | Intégrité référentielle non garantie |
| P1-4 | **Pas de helper `resolve_naf_code()`** — `EntiteJuridique.naf_code` jamais consulté en fallback | Backend global | NAF divergent EJ/Site |
| P1-5 | **Routes `/api/sites` non dépréciées** — doublons actifs avec `/api/patrimoine/sites` | `routes/sites.py` | Confusion API consommateurs |
| P1-6 | **Anomalies O(N) queries** — charge tous les sites, compute en boucle, tri Python | `sites.py:637-699` | Timeout > 50 sites |

### P2 — Best-in-world

| # | Constat | Impact |
|---|---------|--------|
| P2-1 | Favoris backend-synced (table `user_site_favorites`) | Persistance cross-device |
| P2-2 | Heatmap label "Top 15" mais cap à 10 (`HEATMAP_MAX_TILES=10`) | Incohérence visuelle |
| P2-3 | Carte Leaflet (lat/lng existent dans le modèle) | Visualisation géo |
| P2-4 | Audit trail PATCH patrimoine (before/after diff) | Traçabilité |
| P2-5 | Cache anomalies dénormalisé avec TTL | Performance |

---

## 3. Écarts doc vs implémentation

| Ce que le plan d'audit prévoyait | Réalité dans le code |
|---|---|
| Tab Consommation = stub (`TabStub`) | **Faux** — `TabConsoSite.jsx` câblé à `getEmsTimeseries()` |
| Tab Actions = stub | **Faux** — `TabActionsSite.jsx` câblé à `getActionsList()` |
| `SiteDetail.jsx` legacy encore utilisé | **Faux** — fichier inexistant, `Site360.jsx` seul |
| `anomalies_count` = snapshot statique | **Faux** — dynamique via `compute_site_anomalies()` |
| Pas d'endpoint batch anomalies | **Partiellement faux** — `/anomalies` org-wide existe, mais pas de batch par `site_ids` |
| Tab Compteurs du Drawer = stub | **Faux** — `SiteMetersTab` câblé |
| PATCH sans validation Pydantic | **Partiellement vrai** — `SiteUpdateRequest` existe mais sans `extra="forbid"` ni validateurs |

---

## 4. Cohérence inter-modules

| Vérification | Résultat | Sévérité |
|---|---|---|
| Surface `tertiaire ≤ totale` | **Aucune contrainte** | MOYEN |
| NAF code cascade EJ → Site | **Pas de `resolve_naf_code()`** — Site.naf_code seul utilisé | FAIBLE |
| `completude_score` vs `compliance_score` | **Distincts, rôles clairs** — patrimoine vs réglementaire | OK |
| Badge anomalies Drawer vs SiteAnomalyPanel | **Même source** (`compute_site_anomalies`) | OK |
| Billing bridge org_id | **Centralisé** via `_org_sites_query()` (jointure 3 niveaux) | OK |

---

## 5. Résumé exécutif

```
Backend    : 23 endpoints patrimoine, 7 legacy, 1429 lignes service
Frontend   : 21 composants, 0 stubs, architecture modulaire solide
Tests      : 186 passed patrimoine, 3616 passed frontend, 1 failed (impact)
Sécurité   : PATCH sans extra="forbid", meter_id sans FK SQL
Performance: Heatmap N+1, anomalies O(N) queries
Qualité    : Favoris non scopés org, pas de contrainte surface cross-field
```

### Priorisation Phase 1

Les fixes P0 du plan initial sont **révisés** au vu de l'audit :

| Fix planifié | Statut | Action |
|---|---|---|
| P0-1 : Validation PATCH `extra="forbid"` | **Confirmé** | À implémenter |
| P0-2 : Endpoint batch anomalies (Heatmap) | **Confirmé** | À implémenter |
| P0-3 : Réconcilier `anomalies_count` | **Déjà résolu** — source unique dynamique | Skip |
| P0-4 : Tab Consommation Site360 (stub) | **Déjà résolu** — `TabConsoSite` câblé | Skip |
| **Nouveau** : Fix test impact désynchronisé | **À ajouter** | Aligner test sur config réelle |
| **Nouveau** : Favoris scopés par org | **À ajouter** | Clé localStorage par org_id |

### Hypothèses

1. L'erreur "database is locked" (`test_action_close_rules_v49.py`) est un problème de concurrence SQLite hors périmètre patrimoine.
2. `prix_elec_eur_mwh=68.0` est la valeur correcte actuelle — le test doit s'aligner.
3. Les tabs Site360 étant câblés, 2 fixes P0 du plan initial sont retirés.

---

**En attente de validation avant Phase 1.**
