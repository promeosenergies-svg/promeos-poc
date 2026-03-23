# PROMEOS — Dictionnaire KPI

> Chaque KPI affiché dans PROMEOS est documenté ici avec sa définition, formule, source, unité et confiance.

## Conformité

| KPI | Définition | Formule | Unité | Source | Confiance |
|-----|-----------|---------|-------|--------|-----------|
| **Score conformité composite** | Score global conformité réglementaire | `(DT×0.45 + BACS×0.30 + APER×0.25) − MIN(20, nb_critiques×5)` | 0-100 | `compliance_score_service.py:143` | high/medium/low selon nb frameworks évalués |
| **Score conformité portfolio** | Score pondéré par surface assujettie | `Σ(score_site × surface_site) / Σ(surface_site)` | 0-100 | `cockpit.py` (V103+) | medium |
| **Risque financier** | Exposition aux pénalités réglementaires | `7500 × nb(NC) + 3750 × nb(AR)` | EUR | `compliance_engine.py:93` | high |
| **Avancement DT** | Progression trajectoire décret tertiaire | `AVG(sites.avancement_decret_pct)` | % | `kpi_service.py:211` | low (statique) |
| **Exposition anomalies** | Risque patrimoine probabilisé | `risque_brut × probability_factor(0.05)` | EUR | `patrimoine_impact.py` (V109+) | medium |

## Facturation

| KPI | Définition | Formule | Unité | Source | Confiance |
|-----|-----------|---------|-------|--------|-----------|
| **Surcoût facture** | Total des écarts détectés par shadow billing | `Σ(insight.estimated_loss_eur)` | EUR | `billing_service.py` → BillingInsight | high (élec C4/C5), n/a (gaz) |
| **Factures impactées** | Nb de factures avec au moins 1 anomalie | `COUNT(DISTINCT invoice_id WHERE insight EXISTS)` | count | BillingInsight | high |
| **Prorata** | Facteur de proportionnalité mensuel | `jours_période / jours_dans_le_mois` | ratio | `billing_shadow_v2.py` (V101+) | high |

## Achat

| KPI | Définition | Formule | Unité | Source | Confiance |
|-----|-----------|---------|-------|--------|-----------|
| **Score offre** | Score global d'une offre fournisseur | `BudgetRisk(30%) + Transparency(25%) + ContractRisk(25%) + DataReadiness(20%)` | 0-100 | `purchase_scoring_service.py:367` | medium |
| **Contrats expirants** | Nb contrats arrivant à échéance dans l'horizon sélectionné | `COUNT(end_date BETWEEN today AND today+horizon)` | count | `contract_radar_service.py` | high |
| **Conso estimée** | Volume annuel pour scénarios | Priorité : MeterReading > Invoice > 500k kWh | kWh/an | `purchase_service.py` | variable |

## Patrimoine

| KPI | Définition | Formule | Unité | Source | Confiance |
|-----|-----------|---------|-------|--------|-----------|
| **Complétude données** | Score de remplissage des champs site | `filled_checks / 8 × 100` | % 0-100 | `patrimoine/_helpers.py:357` | high |
| **Conso annuelle** | Consommation unifiée 12 derniers mois | `Σ(metered kWh par site, dédupliqué par fréquence)` | kWh | `consumption_unified_service.py` | high |
| **Surface totale** | Surface cumulée des sites actifs | `Σ(site.surface_m2)` | m² | Site model | high |
| **Couverture opérationnelle** | Score combiné données + conformité + actions | Composite frontend | % | `dashboardEssentials.js` | medium |

## Qualité Données

| KPI | Définition | Formule | Unité | Source | Confiance |
|-----|-----------|---------|-------|--------|-----------|
| **Score qualité électricité** | Score composite qualité des relevés | `complétude(35%) + gaps(25%) + doublons(15%) + négatifs(15%) + outliers(10%)` | 0-100 | `electric_monitoring/data_quality.py` | high |
| **Fraîcheur** | Ancienneté du dernier relevé | `today − max(reading.timestamp)` | jours | `data_quality_service.py` | high |
| **Couverture** | Mois avec données / 12 | `months_with_data / 12 × 100` | % | `data_quality_service.py` | high |

## Actions

| KPI | Définition | Formule | Unité | Source | Confiance |
|-----|-----------|---------|-------|--------|-----------|
| **Impact estimé total** | Somme des gains attendus | `Σ(action.estimated_gain_eur)` | EUR | ActionItem model | medium |
| **ROI réalisé** | Ratio gains réalisés / estimés | `Σ(realized_gain) / Σ(estimated_gain) × 100` | % | ActionItem model | high (si action terminée) |
| **Avancement actions** | Progression du plan d'actions | `nb_done / nb_total × 100` | % | ActionItem model | high |

## Grades

| Grade | Seuil |
|-------|-------|
| A | ≥ 85/100 |
| B | ≥ 70/100 |
| C | ≥ 50/100 |
| D | ≥ 30/100 |
| F | < 30/100 |

## Niveaux de confiance

| Niveau | Critère |
|--------|---------|
| **high** | 3/3 frameworks évalués, données fraîches, source mesurée |
| **medium** | 2/3 frameworks, ou données partielles |
| **low** | 0-1 framework, données absentes ou estimées |
| **variable** | Dépend du site (mesuré vs estimé) |
