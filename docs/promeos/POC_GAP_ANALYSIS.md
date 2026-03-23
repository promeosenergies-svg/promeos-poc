# PROMEOS — Gap Analysis POC vs Référentiel

> Date : 2026-03-20 | Version POC : V109+ (post Pilote Contrôlé)

## État actuel

| Métrique | Valeur |
|----------|--------|
| Frontend tests | 5659 passed, 0 failed |
| Backend tests ciblés | 260+ passed |
| E2E Playwright | 17 scénarios (dont 17 audit visuel) |
| Audit cross-views | 60 checks, 0 issues |
| Build | OK (22s) |

## Top 20 Actions Priorisées

### P0 — Bloquants crédibilité

| # | Gap | Impact | Fichiers concernés | Effort |
|---|-----|--------|---------------------|--------|
| 1 | **Gaz non supporté en shadow billing** | Seule l'élec est facturée théoriquement. 40% du parc a du gaz | `billing_engine/engine.py` | L |
| 2 | **Tarifs C3/HTA non supportés** | Exclut les sites industriels > 250 kVA | `billing_engine/engine.py`, `billing_engine/turpe.py` | L |
| 3 | **Aucun calcul CO₂** réel | `fmtCo2` existe mais aucune donnée CO₂ n'est produite | Nouveau service + modèle | M |
| 4 | **Trajectoire DT non calculée** dynamiquement | `avancement_decret_pct` est un champ statique, pas calculé depuis les consos réelles | `tertiaire_service.py`, `compliance_engine.py` | M |
| 5 | **TURPE V2 (2025)** non intégré | Les tarifs TURPE datent de 2024, pas de mécanisme de mise à jour | `billing_engine/turpe.py` | S |

### P1 — Crédibilité métier

| # | Gap | Impact | Fichiers concernés | Effort |
|---|-----|--------|---------------------|--------|
| 6 | **Capacité/MEOC** non modélisé | Composante significative des gros sites (5-15% de la facture) | `billing_engine/engine.py` | M |
| 7 | **Énergie réactive** non modélisée | Pénalité tan(φ) > 0.4 non détectée | Nouveau module | M |
| 8 | **CEE dans le ROI actions** | Le financement CEE n'est pas intégré dans le calcul de ROI des actions d'efficacité | `action_plan_engine.py` | S |
| 9 | **Profil de charge** simpliste | Facteurs plats (0.85/1.25/1.0) vs courbe de charge réelle | `purchase_service.py` | M |
| 10 | **Benchmark ADEME** non exploité | Les benchmarks kWh/m²/an existent dans `gen_meter_readings.py` mais ne sont pas exposés en UI | `patrimoine_assumptions.py`, nouveau composant | S |
| 11 | **PVGIS non branché** dans APER | `aper_service.py` a un placeholder mais pas d'appel réel PVGIS | `aper_service.py` | S |
| 12 | **DPE non modélisé** | Pas de lien avec le Diagnostic de Performance Énergétique | Nouveau modèle | M |
| 13 | **Multi-fluides incomplet** | Eau, vapeur, froid réseau non modélisés | `models/energy_models.py` | L |

### P2 — Niveau leader marché

| # | Gap | Impact | Fichiers concernés | Effort |
|---|-----|--------|---------------------|--------|
| 14 | **Autoconsommation / PV** | Pas de simulation d'autoconsommation solaire | Nouveau service | L |
| 15 | **Flexibilité / effacement** | `flex_mini.py` est un placeholder, pas de calcul réel | `flex_mini.py` | L |
| 16 | **Stockage batterie** | Aucune modélisation stockage | Nouveau service | L |
| 17 | **Multi-fournisseur / market making** | Comparaison d'offres limitée à 3 scénarios fixes | `purchase_scenarios_service.py` | L |
| 18 | **Weather normalization** automatique | `operat_normalization.py` existe mais DJU manuels | `weather_provider.py` | M |
| 19 | **Prédiction conso** (ML) | Aucun modèle prédictif | Nouveau service | L |
| 20 | **API marché temps réel** | Prix EPEX seedés, pas de flux live | `market_service.py` | M |

## Matrice Couverture Fonctionnelle

| Brique | Implémenté | Partiel | Manquant |
|--------|-----------|---------|----------|
| **Patrimoine** | Sites, bâtiments, compteurs, contrats, anomalies, qualité données | Segmentation (basique) | DPE, multi-fluides |
| **Conformité DT** | Score, findings, timeline, OPERAT EFA | Trajectoire (statique) | Calcul dynamique trajectoire |
| **Conformité BACS** | Putile, seuils, inspections, preuves | Plan remédiation | Attestation workflow complet |
| **APER** | Éligibilité parking/toiture | Estimation PV (placeholder) | PVGIS réel, simulation financière |
| **Facturation** | Shadow billing C4/C5, reconciliation, insights | Prorata corrigé V101 | Gaz, C3/HTA, MEOC, réactif |
| **Achat** | 3 scénarios, scoring 4 axes, RéFlex, radar contrats | Monte Carlo (backend V101) | Offres réelles, multi-fournisseur |
| **Actions** | CRUD, priorités, ROI, preuves, close rules | Insight→Action→ROI | CEE dans ROI |
| **Cockpit** | KPIs unifiés, priorités, compliance history, export PDF | Pondération surface V103 | Prédictif, alertes proactives |
| **Données** | Qualité, complétude, freshness, confiance | Sync conso V109 | Prédiction gaps |

## Cohérence Cross-Views (audité V109+)

| Vérification | Statut |
|-------------|--------|
| Conso cockpit = conso patrimoine | ✅ (sync V109) |
| Risque cockpit = Σ risque sites | ✅ |
| Compliance portfolio = pondéré surface | ✅ (V103) |
| Monosite = portfolio 1 site | ✅ (7 tests parité) |
| Export PDF = écran | ✅ (jsPDF V106) |
| Filtres radar contrats | ✅ (fix V109) |
| Compteurs dans drawer | ✅ (fix V109) |
| NaN flex | ✅ (fix V109) |
| Banner empty state | ✅ (fix V109) |

## Risques Résiduels

| Risque | Gravité | Mitigation |
|--------|---------|------------|
| SQLite en prod | Élevée | Migrer PostgreSQL avant pilote réel |
| Pas d'auth production-grade | Élevée | JWT basique, pas de refresh token, pas de MFA |
| Pas de multi-tenant réel | Moyenne | Org-scoped mais pas d'isolation forte |
| Pas de backup automatisé | Élevée | Scripts manuels seulement |
| TURPE pas à jour | Moyenne | Tarifs 2024, besoin mise à jour annuelle |
| Pas de monitoring production | Moyenne | Logs JSON + perf audit light |

## Sprint Recommandé : V110 "Crédibilité Métier"

### Objectifs
1. Shadow billing gaz (P0.1)
2. Trajectoire DT dynamique depuis consos réelles (P0.4)
3. TURPE V2 2025 (P0.5)
4. Benchmark ADEME visible en UI (P1.10)
5. CEE dans le calcul ROI actions (P1.8)

### Fichiers à toucher
- `backend/services/billing_engine/engine.py` — ajout gaz
- `backend/services/billing_engine/turpe.py` — mise à jour tarifs
- `backend/services/tertiaire_service.py` — trajectoire dynamique
- `backend/services/compliance_engine.py` — avancement calculé
- `backend/services/action_plan_engine.py` — ROI avec CEE
- `frontend/src/pages/consumption/BenchmarkPanel.jsx` — ADEME visible

### Tests à écrire
- `test_shadow_billing_gas.py` — billing gaz déterministe
- `test_trajectoire_dt_dynamic.py` — -40% calculé vs réel
- `test_turpe_v2.py` — nouveaux tarifs
- `test_roi_with_cee.py` — ROI incluant CEE
- Playwright : audit visuel benchmark ADEME

### Filets de sécurité
- `scripts/audit_cross_views.py` — 60 checks existants
- `e2e/audit-visual.spec.js` — 17 scénarios Playwright
- `test_monosite_portfolio_parity.py` — 7 assertions parité
- Build + vitest avant chaque push
