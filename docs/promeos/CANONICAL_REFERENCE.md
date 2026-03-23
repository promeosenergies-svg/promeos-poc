# PROMEOS — Référentiel Canonique

> Dernière mise à jour : 2026-03-20 | Version POC : V109+

## 1. Vision Produit

PROMEOS est un **cockpit énergétique B2B post-ARENH** couvrant le cycle complet :
**Patrimoine → Données → Conformité → Facturation → Achat → Actions → Optimisation**

Pas un dashboard isolé. Chaque brique alimente la suivante.

## 2. Architecture Backend

| Domaine | Routes | Services | Modèles |
|---------|--------|----------|---------|
| Conformité | compliance.py, bacs.py, aper.py, tertiaire.py | compliance_engine, compliance_score_service, bacs_engine, aper_service, compliance_rules | RegAssessment, ComplianceFinding, ComplianceScoreHistory |
| Facturation | billing.py | billing_engine, billing_reconcile, billing_shadow_v2 | EnergyInvoice, BillingInsight, ShadowInvoice |
| Achat | purchase.py, contracts_radar.py | purchase_service, purchase_scenarios_service, purchase_scoring_service | PurchaseAssumptionSet, PurchaseScenarioResult |
| Patrimoine | patrimoine/*.py | patrimoine_service, patrimoine_impact, patrimoine_anomalies | Site, Batiment, Compteur, EnergyContract |
| Actions | actions.py | action_plan_engine, action_close_rules | ActionItem, ActionEvent, ActionEvidence |
| Cockpit | cockpit.py | kpi_service, compliance_score_trend | (agrège les autres) |
| Données | data_quality.py, ems.py | data_quality_service, consumption_unified_service | MeterReading, ConsumptionTarget |

**Total** : 58 routes, 90+ services, 56 modèles, 50+ tables.

## 3. Architecture Frontend

| Module | Page principale | Modèle métier |
|--------|----------------|---------------|
| Cockpit | Cockpit.jsx | dashboardEssentials.js |
| Patrimoine | Patrimoine.jsx | normalizeRisk.jsx |
| Conformité | ConformitePage.jsx | guidedModeModel.js, complianceProfileRules.js |
| Facturation | BillIntelPage.jsx | billingHealthModel.js |
| Achat | PurchasePage.jsx | domain/purchase/engine.js |
| Actions | ActionsPage.jsx | actionProofLinkModel.js |

**Layout** : AppShell (h-screen) → Sidebar (NavRail 64px + NavPanel 208px) + Content (header sticky + main scrollable)

## 4. Réglementation Implémentée

### Décret Tertiaire / OPERAT
- Seuil : surface tertiaire ≥ 1 000 m²
- Trajectoire : −40% en 2030, −50% en 2040 vs référence
- Pénalités : 7 500 € (non-déclaration), 1 500 € (non-affichage)
- Source : regs.yaml + decret_tertiaire_operat_v1.yaml

### Décret BACS / GTB-GTC
- Seuil haut : CVC > 290 kW → échéance 01/01/2025
- Seuil bas : 70 < CVC ≤ 290 kW → échéance 01/01/2030
- Putile = MAX(SUM chauffage, SUM climatisation) selon architecture (cascade/indépendant)
- Pénalité : 7 500 € non-conformité
- Source : regs.yaml + decret_bacs_v1.yaml

### Loi APER (Solarisation)
- Parking ≥ 1 500 m² → ombrières PV → échéance 01/07/2026
- Toiture ≥ 500 m² → PV ou végétalisation → échéance 01/01/2028
- Source : regs.yaml + loi_aper_v1.yaml

### CEE
- Mécanisme de financement (pas dans le score conformité composite)
- Workflow dossier avec preuves

## 5. Scoring Conformité Unifié (A.2)

```
Score = (DT × 0.45 + BACS × 0.30 + APER × 0.25) − MIN(20, nb_critiques × 5)
```

- Source unique : `compliance_score_service.py`
- Poids configurables : `regs.yaml > scoring > framework_weights`
- Confiance : high (3/3 fw évalués), medium (2/3), low (0-1)
- Portfolio : pondéré par surface assujettie

## 6. Risque Financier

```
risque = 7 500 × nb(NON_CONFORME) + 3 750 × nb(A_RISQUE)
```

- Source : `compliance_engine.py` → persisté sur `Site.risque_financier_euro`
- Anomalies patrimoine : `probability_factor = 0.05` (V109+)

## 7. Shadow Billing (Facturation Théorique)

- Tarifs supportés : C4 BT (LU/MU/CU), C5 BT (Base/HP-HC)
- Composantes : Fourniture + TURPE (gestion, comptage, soutirage) + Taxes + TVA
- Prorata : `days / calendar.monthrange(year, month)[1]` (V101+)
- Non supporté : C3/C2/C1, Gaz, Réactif, MEOC, CEE

## 8. Achat Énergie

### Estimation conso (priorité)
1. MeterReading 12 derniers mois
2. EnergyInvoice 12 derniers mois
3. Fallback : 500 000 kWh/an

### 3 Scénarios déterministes
| Scénario | Risque | Facteur prix | Indexation |
|----------|--------|-------------|------------|
| A Fixe | Faible | ×1.05 | fixe |
| B Indexé | Modéré | ×0.95 | marché |
| C Spot | Élevé | ×0.88 | spot |

### Scoring 4 axes (V101+)
- BudgetRisk 30% + Transparency 25% + ContractRisk 25% + DataReadiness 20%
- Source : `purchase_scoring_service.py`

## 9. Qualité Données

| Seuil | Valeur |
|-------|--------|
| Fresh | < 45 jours |
| Stale | 45-90 jours |
| Outdated | > 90 jours |
| Couverture attendue | 12 mois |

Score qualité électricité : complétude 35% + gaps 25% + doublons 15% + négatifs 15% + outliers 10%

## 10. Unités & Formatage

| Grandeur | Fonction | Seuils |
|----------|----------|--------|
| Énergie | `fmtKwh(v)` | ≥1M → GWh, ≥1k → MWh, sinon kWh |
| Monnaie | `fmtEur(v)` | ≥1M → M€, ≥1k → k€, sinon € |
| Surface | `fmtArea(v)` | m² avec séparateurs |
| Puissance | `fmtKw(v)` | kW / MW |
| CO₂ | `fmtCo2(kg)` | kg / t CO₂ |

## 11. Seed Démo Canonique

- Pack : HELIOS / taille S
- 5 sites : Paris (3500m²), Lyon (1200m²), Toulouse (6000m²), Nice (4000m²), Marseille (2800m²)
- 9 contrats, 36 factures, 12 actions, 10 notifications
- Conso synchronisée via `consumption_unified_service`
- Login : `promeos@promeos.io` / `promeos2024`
