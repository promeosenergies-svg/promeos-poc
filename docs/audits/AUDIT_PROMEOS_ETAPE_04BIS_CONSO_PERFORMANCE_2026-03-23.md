# AUDIT PROMEOS — ÉTAPE 4bis : CONSO / PERFORMANCE

> **Date** : 2026-03-23
> **Baseline** : Étapes 0-4
> **Méthode** : 3 agents parallèles (backend/frontend/intégration), cartographie exhaustive
> **Statut** : AUDIT UNIQUEMENT — aucune modification

---

## 1. Résumé exécutif

La brique Conso/Performance est **le 3e asset majeur du POC** (après BACS et Bill Intelligence). C'est une brique **massive, mature et bien architecturée** :

- **73 fichiers frontend** (8 pages, 37 sous-composants, 4 hooks/moteurs, 25+ panels)
- **12 services backend** (monitoring 5 engines, diagnostic 5 détecteurs, timeseries, signature, météo)
- **15 modèles** (MeterReading, MonitoringSnapshot, MonitoringAlert, ConsumptionInsight, Anomaly, Recommendation...)
- **40+ endpoints API** (conso unifié, monitoring, diagnostic, EMS, context, targets, HP/HC, gaz)

**Architecture** : moteur unifié (`useExplorerMotor`) côté frontend, pipeline orchestré (`MonitoringOrchestrator`) côté backend, données versionnées (15min→monthly), multi-source (compteur>facture>estimé), réconciliation metered/billed.

**Intégration** : **réelle** avec cockpit, conformité (trajectoire DT), facture (shadow billing), achat (volume kWh), actions (5 types insights). Bien meilleure que le lien conformité↔facture.

| Aspect | Note | Justification |
| --- | --- | --- |
| Richesse fonctionnelle | **9/10** | 8 pages, 40+ endpoints, 12 types d'alertes, 5 détecteurs diagnostic |
| Architecture backend | **8.5/10** | Pipeline orchestré, multi-engine, quality scoring, réconciliation |
| Architecture frontend | **8.5/10** | Moteur unifié, URL state sync, 4 modes d'affichage, layer system |
| Intégration PROMEOS | **7/10** | Alimente cockpit + conformité + facture + achat + actions. Gap : diagnostic pas auto-déclenché |
| Crédibilité métier | **7.5/10** | KPIs démontrables, sources traçables (ConsoSourceBadge), benchmarks ADEME |
| Données démo réalisme | **8/10** | Profils ADEME par archétype, saisonnalité, anomalies diversifiées |

---

## 2. Cartographie réelle

### Pages frontend (8)

| Page | Route | Lignes | Rôle |
| --- | --- | --- | --- |
| ConsumptionExplorerPage | `/consommations/explorer` | 978 | Analyse multi-sites, 10 panels, 4 modes (agrégé/superposé/empilé/séparé) |
| ConsumptionPortfolioPage | `/consommations/portfolio` | 978 | Vue portefeuille, data_status par site, couverture % |
| ConsommationsPage | `/consommations` | shell | Layout wrapper 4 tabs (Portfolio/Explorer/Import/Memobox) |
| ConsommationsUsages | `/consommations/import` | 1240 | Wizard import 7 étapes |
| MonitoringPage | `/monitoring` | 3112 | Performance élec : 5 KPIs, 4 graphes, signature, heatmap, alertes |
| ConsumptionDiagPage | `/diagnostic-conso` | 1173 | Diagnostic opérationnel : détecter→prouver→agir |
| UsagesDashboardPage | `/usages` | 1203 | Usages : readiness, plan comptage, top UES, baselines |
| ConsumptionContextPage | `/consumption-context` | 130 | Profil conso & anomalies comportementales |

### Services backend (12+)

| Service | Lignes | Rôle |
| --- | --- | --- |
| `consumption_unified_service.py` | 377 | Source unifiée metered/billed/reconciled |
| `consumption_diagnostic.py` | 939 | 5 détecteurs (hors_horaires, base_load, pointe, dérive, data_gap) |
| `consumption_context_service.py` | ~300 | Profil comportemental, behavior_score 0-100 |
| `electric_monitoring/kpi_engine.py` | 9.3K | Pmax, P95, P99, load_factor, profils horaires |
| `electric_monitoring/power_engine.py` | 6.4K | Risk score puissance 0-100 (4 composantes pondérées) |
| `electric_monitoring/climate_engine.py` | 4.3K | Signature énergétique (corrélation T°) |
| `electric_monitoring/alert_engine.py` | 19K | 12 types d'alertes Tier-1 |
| `electric_monitoring/monitoring_orchestrator.py` | 13K | Pipeline : readings→KPIs→quality→power→alerts→snapshot |
| `electric_monitoring/data_quality.py` | 9.7K | Gaps, doublons, DST, valeurs négatives |
| `ems/timeseries_service.py` | 751 | Aggrégation SQL 15min→monthly, max 5000 pts |
| `ems/signature_service.py` | 5.4K | Régression piecewise change-point (BIC) |
| `ems/weather_service.py` | 5.6K | Cache météo + génération démo |

### Modèles (15)

| Modèle | Fichier | Rôle |
| --- | --- | --- |
| MeterReading | energy_models.py | Données time-series (timestamp, value_kwh, quality_score) |
| Meter | energy_models.py | Compteur maître (hiérarchie sub-meters) |
| MonitoringSnapshot | energy_models.py | KPIs agrégés par période (JSON) |
| MonitoringAlert | energy_models.py | 12 types alertes avec lifecycle |
| ConsumptionInsight | consumption_insight.py | Diagnostics (5 types, severity, recommended_actions) |
| ConsumptionTarget | consumption_target.py | Objectifs mensuels/annuels kWh/EUR/CO2e |
| Anomaly | energy_models.py | Anomalies détectées (confidence, deviation) |
| Recommendation | energy_models.py | Actions recommandées (ICE scoring) |
| DataPoint | datapoint.py | Métriques génériques avec lineage |
| DataImportJob | energy_models.py | Suivi import (SHA256 dedup, status, rows) |
| UsageProfile | energy_models.py | Archétype + features extraites |
| EmsWeatherCache | ems_models.py | Cache météo journalier |
| EmsSavedView | ems_models.py | Vues sauvegardées |
| EmsCollection | ems_models.py | Paniers de sites |
| Consommation | consommation.py | Legacy simple readings |

---

## 3. Ce qui est réellement implémenté

### 3.1 Pipeline Monitoring complet — IMPLÉMENTÉ

```text
MeterReading (15min/hourly/daily)
    ↓
MonitoringOrchestrator.run()
    ├── KPIEngine → Pmax, P95, P99, load_factor, profils 24h
    ├── PowerEngine → risk_score 0-100 (P95/souscrite, dépassements, volatilité, concentration)
    ├── DataQualityEngine → quality_score, gaps, doublons, DST
    ├── ClimateEngine → corrélation T°, signature, balance_point
    └── AlertEngine → 12 alertes Tier-1
    ↓
MonitoringSnapshot + MonitoringAlert (persistés)
```

**Tag** : IMPLÉMENTÉ — Pipeline professionnel, multi-engine, avec quality scoring

### 3.2 Diagnostic 5 détecteurs — IMPLÉMENTÉ

| Détecteur | Méthode | Seuil | Output |
| --- | --- | --- | --- |
| hors_horaires | Schedule-aware (SiteOperatingSchedule) | kWh hors heures / kWh total | ConsumptionInsight |
| base_load | Q10 des readings jour vs médiane | Statistique robuste | ConsumptionInsight |
| pointe | Médiane + 3×MAD sur conso journalière | Outlier résistant | ConsumptionInsight |
| dérive | Régression linéaire 30j (fallback sem1/sem4) | Pente significative | ConsumptionInsight |
| data_gap | Détection lectures manquantes | Coverage < seuil | ConsumptionInsight |

**Tag** : IMPLÉMENTÉ — Statistiques robustes (médiane, MAD, Q10), pas de seuils arbitraires

### 3.3 Signature énergétique — IMPLÉMENTÉ

Modèle piecewise change-point :
```
kWh_jour = base + a × max(0, T_balance_chaud − T) + b × max(0, T − T_balance_froid)
```
- Grid search T_balance ∈ [10°, 20.5°] × [18°, 28.5°] (pas 0.5°)
- Sélection modèle par BIC (chauffe seule, froid seul, complet)
- Output : base, a, b, T_balance_chaud, T_balance_froid, R², n_points

**Tag** : IMPLÉMENTÉ — Algorithme de référence en audit énergétique

### 3.4 Explorer multi-sites — IMPLÉMENTÉ

- **4 modes** : agrégé, superposé, empilé, séparé
- **3 unités** : kWh, kW, EUR
- **Layers composables** : Tunnel (P10-P90), Signature, Météo, Talon, Objectifs
- **URL state sync** : deep-linkable, bookmarkable
- **Max 5 sites** par vue (bascule auto en mode portfolio au-delà)
- **Granularité auto** : 15min ≤3j, hourly ≤90j, daily ≤4000j, monthly >4000j

**Tag** : IMPLÉMENTÉ — Outil d'analyse professionnel

### 3.5 Source badge et réconciliation — IMPLÉMENTÉ

- `ConsoSourceBadge` : vert (compteur), bleu (facture), orange (estimé)
- `reconcile_metered_billed()` : alerte si delta > 10%
- `ConsumptionSource` enum : METERED | BILLED | RECONCILED
- Coverage tracking : préfère metered si couverture ≥ 80%

**Tag** : IMPLÉMENTÉ — Traçabilité source crédible

---

## 4. Ce qui est partiel

### 4.1 Diagnostic pas auto-déclenché — PARTIEL

`run_diagnostic()` n'est appelé que via :
- `POST /api/consumption/diagnose` (API manuelle)
- Demo seed (`gen_monitoring.py`)

Pas d'auto-déclenchement après import de données ou à intervalle régulier.

**Tag** : PARTIEL — Le moteur existe mais ne tourne pas automatiquement

### 4.2 Site.annual_kwh_total pas auto-mis à jour — PARTIEL

Ce champ clé (utilisé par DT trajectory, cockpit, purchase) n'est pas automatiquement recalculé depuis les MeterReading. Il est alimenté par :
- Import/intake_service (manuel)
- Demo seed
- EFA declaration

Mais PAS par un recalcul automatique type "somme 12 derniers mois metered".

**Tag** : PARTIEL — Source de vérité conso existe mais pas de rafraîchissement automatique

### 4.3 Gaz = Beta — PARTIEL

`GasPanel.jsx` marqué "Beta". Les services gaz existent (`getGasSummary`, `getGasWeatherNormalized`) mais la décomposition base/chauffage et la normalisation DJU sont simplifiées.

**Tag** : PARTIEL — Fonctionnel mais annoncé beta

### 4.4 Actions conso : pas de gain calculé automatiquement — PARTIEL

`build_actions_from_consumption()` dans `action_hub_service.py:125-170` extrait `estimated_loss_eur` depuis `ConsumptionInsight`. Mais cette valeur dépend d'un prix unitaire (DEFAULT_PRICE_ELEC_EUR_KWH) car pas de lien direct au contrat du site.

**Tag** : PARTIEL — Gain estimé mais prix approximatif

---

## 5. Ce qui est trompeur ou fragile

### 5.1 Données = 100% seed en mode démo

Toutes les MeterReading sont générées par `gen_readings.py` avec des profils ADEME par archétype. Les données sont réalistes (saisonnalité, anomalies diversifiées, CVC cycling) mais synthétiques. En démo, l'utilisateur pourrait croire à des données réelles si aucun signal ne l'indique.

**ConsoSourceBadge** affiche "Compteur" (vert) même pour des données seed — car `is_estimated=False` dans gen_readings.

**Tag** : À RISQUE CRÉDIBILITÉ — Données seed non distinguées visuellement

### 5.2 12 alertes mais seuils non configurables par site

Les 12 alertes Tier-1 utilisent des seuils globaux (ex: night base > X%, weekend ratio > Y%). Ces seuils ne sont pas ajustables par type de site (un hôtel 24/7 vs un bureau 8h-18h).

Mitigation : le diagnostic `consumption_diagnostic.py` est schedule-aware (utilise `SiteOperatingSchedule`). Mais `alert_engine.py` ne l'est pas systématiquement.

**Tag** : IMPLICITE MAIS NON FIABILISÉ

### 5.3 CO2e factor hardcodé

`ConsoKpiHeader.jsx` utilise `CO2E_FACTOR_KG_PER_KWH = 0.052` (ADEME 2024 location-based). Ce facteur est correct mais :
- Non configurable par site (pas de facteur market-based pour GO renouvelables)
- Pas de distinction gaz (0.227 kg/kWh) vs élec (0.052)

**Tag** : IMPLICITE MAIS NON FIABILISÉ — Correct pour élec, incorrect pour gaz

---

## 6. Intégration avec les autres briques

| Brique | Lien avec Conso | Statut | Fichier:preuve |
| --- | --- | --- | --- |
| **Cockpit** | `conso_kwh_total`, `conso_confidence`, `conso_sites_with_data` + trajectory | **IMPLÉMENTÉ** | `cockpit.py:131-144` |
| **Conformité DT** | `dt_trajectory_service` consomme `get_portfolio_consumption()` pour conso actuelle | **IMPLÉMENTÉ** | `dt_trajectory_service.py:117` |
| **Facture** | `billing_service` utilise `EnergyInvoice.energy_kwh` (pas MeterReading directement) | **PARTIEL** | `billing_service.py:162` |
| **Achat** | `purchase_service.estimate_consumption()` utilise MeterReading (P1) puis Invoice (P2) | **IMPLÉMENTÉ** | `purchase_service.py:46-96` |
| **Actions** | `build_actions_from_consumption()` convertit ConsumptionInsight en ActionItem | **IMPLÉMENTÉ** | `action_hub_service.py:125-170` |
| **Patrimoine** | Site.annual_kwh_total alimenté par intake, pas auto-refresh | **PARTIEL** | — |

### Chaîne conso dans le fil conducteur

```text
patrimoine → [MeterReading/Consommation] → KPI/Monitoring
                                                ↓
                                    ConsumptionInsight (diagnostic)
                                                ↓
                                    ActionItem (via action_hub)

                        ← cockpit ← conso_kwh_total
                        ← conformité ← dt_trajectory (avancement)
                        ← facture ← EnergyInvoice.energy_kwh
                        ← achat ← estimate_consumption()
```

**Tag** : La conso est **le liant le plus naturel** entre les briques. Elle alimente toutes les autres.

---

## 7. Risques de crédibilité

### Top 5 points vulnérables en démo

| # | Risque | Impact | Mitigation existante |
| --- | --- | --- | --- |
| 1 | **Données seed indistinguables** — ConsoSourceBadge affiche "Compteur" pour du seed | Un expert demande d'où viennent les données | ConsoSourceBadge existe mais `is_estimated=False` pour seed |
| 2 | **Diagnostic pas auto-déclenché** — Il faut un appel API manuel pour obtenir les insights | Le centre d'actions semble vide côté conso si personne ne lance le diagnostic | Bouton "Diagnostiquer" dans ConsumptionDiagPage |
| 3 | **CO2e uniquement élec** — 0.052 kg/kWh pour tout, même le gaz | Un energy manager vérifie le facteur CO2 gaz (devrait être 0.227) | Aucune |
| 4 | **annual_kwh_total stale** — Pas de recalcul auto depuis les compteurs | L'avancement DT peut rester figé malgré des données récentes | `update_site_avancement()` existe mais pas câblé (étape 1 P0-1) |
| 5 | **Signature énergétique démo** — Le scatter T°/kWh est cohérent mais avec météo démo | Si quelqu'un compare avec Météo-France réel | Weather cache peut être réel (API Météo-France intégrable) |

### Ce qui est solide

| # | Force | Pourquoi |
| --- | --- | --- |
| 1 | Pipeline monitoring multi-engine | 5 engines orchestrés, KPIs professionnels, quality scoring |
| 2 | Signature énergétique piecewise | Algorithme de référence en audit énergie (BIC model selection) |
| 3 | 12 alertes Tier-1 avec lifecycle | Couvre les cas classiques energy management |
| 4 | Explorer 4 modes + URL sync | Outil d'analyse compétitif (comparable à platforms commerciales) |
| 5 | Réconciliation metered/billed | Source traçable, seuil 10%, coverage tracking |

---

## 8. Risques de conflit / non-régression

### RÈGLE ABSOLUE — PÉRIMÈTRE YANNICK

> **On ne touche PAS aux données et au travail de Yannick. On les exploite et on les prend en considération.**
>
> Les fichiers ci-dessous sont des **inputs en lecture seule** pour l'audit et les correctifs PROMEOS. Toute modification dans ces zones est **interdite** sans coordination explicite.

| Zone (lecture seule) | Raison |
| --- | --- |
| `MonitoringPage.jsx` (3112L) | Page la plus grosse du POC, travail en cours |
| `useExplorerMotor.js` | Moteur central, tout changement cascaderait sur 10 panels |
| `electric_monitoring/` (5 engines) | Pipeline interdépendant, périmètre Yannick |
| `consumption_diagnostic.py` (939L) | Statistiques robustes, ne pas toucher |
| `gen_readings.py` | Seed data = base de tous les tests/demos |
| `ems/timeseries_service.py` | Service EMS core |
| `ems/signature_service.py` | Algorithme signature énergétique |
| `ems/weather_service.py` | Cache météo |
| `consumption_unified_service.py` | Source unifiée conso |
| `consumption_context_service.py` | Profil comportemental |
| Tout fichier `frontend/src/pages/consumption/` | Panels conso |

### Ce qu'on PEUT faire (sans toucher au périmètre)

| Action autorisée | Exemple |
| --- | --- |
| **Lire** les données conso pour alimenter d'autres briques | Cockpit, conformité, facture, achat, actions |
| **Consommer** les endpoints API existants | `GET /api/ems/timeseries`, `GET /api/monitoring/kpis` |
| **Afficher** les KPIs conso dans d'autres pages | Bandeau conso dans ConformitePage ou BillIntelPage |
| **Ajouter** des CTA vers les pages conso | Lien "Voir la consommation" depuis d'autres pages |
| **Ne PAS modifier** les services, modèles, composants ou seed conso | Interdit |

**Tag** : À RISQUE RÉGRESSION — Brique complexe, périmètre Yannick = lecture seule

---

## 8b. Conflits et mismatchs détectés

### CONFLIT C1 : CO2 — 0.052 vs 0.0569 (écart 9%)

| Source | Facteur élec | Fichier |
| --- | --- | --- |
| `config/emission_factors.py` (source canonique) | **0.0569** kgCO₂e/kWh | ADEME Base Carbone 2024 |
| `compliance_engine.py:60` | **0.0569** | Cohérent |
| `demo_seed/gen_targets.py` | **0.0569** | Cohérent |
| `co2_service.py:27` | **0.052** | **MISMATCH** — arrondi divergent |
| `frontend/src/pages/consumption/constants.js:13` | **0.052** | **MISMATCH** — copié depuis co2_service |

**Impact** : Le frontend sous-estime le CO₂ de ~9% par rapport au compliance engine. Un site affichant 520 tCO₂ au cockpit conso montrerait 569 tCO₂ si recalculé côté conformité.

**Périmètre** : `co2_service.py` et `constants.js` sont dans le périmètre Yannick → signaler le mismatch, ne pas corriger.

**Tag** : À RISQUE CRÉDIBILITÉ — Deux chiffres CO₂ différents selon la page consultée

### CONFLIT C2 : Compteur (legacy) vs Meter (nouveau) — double-comptage potentiel

5 services accèdent encore directement au modèle `Compteur` legacy au lieu de passer par `meter_unified_service` :
- `co2_service.py:80`
- `compliance_engine.py:286`
- `onboarding_service.py`
- `patrimoine_anomalies.py`
- `iam_service.py` (3 queries)

**Risque** : Si un site a BOTH `Compteur` + `Meter` pour la même énergie, les calculs pourraient agréger les deux.

**Mitigation existante** : `consumption_diagnostic.py` utilise correctement `get_site_meter_ids()` (Meter only, exclut sub-meters).

**Périmètre** : `meter_unified_service.py` est dans le périmètre Yannick. Les services legacy (`compliance_engine`, `onboarding_service`) sont modifiables.

**Tag** : IMPLICITE MAIS NON FIABILISÉ — Pas de garde explicite contre le double-comptage

### CONFLIT C3 : 3 moteurs de data quality parallèles

| Moteur | Fichier | Input | Score | Signification |
| --- | --- | --- | --- | --- |
| ElectricMonitoring DQ | `electric_monitoring/data_quality.py` | MeterReading | 0-100 | Complétude, gaps, doublons, DST, négatifs |
| Legacy DQ Service | `data_quality_service.py` | MeterReading + invoices | % coverage | 6 causes (no_meter, sparse, stale...) |
| RegOps Gate | `regops/data_quality.py` | Evidence fields + bâtiments | 0-100 confidence | Complétude champs par réglementation |

**Impact** : Même site → 3 scores DQ différents → utilisateur confus ("ma qualité de données est-elle 95% ou 60% ?").

**Périmètre** : `electric_monitoring/data_quality.py` est périmètre Yannick. `data_quality_service.py` et `regops/data_quality.py` sont modifiables.

**Tag** : À RISQUE UX — Trois vérités parallèles, aucune arbitration

### CONFLIT C4 : ConsumptionInsight vs MonitoringAlert — même détecteur, deux modèles

Le détecteur `hors_horaires` peut générer à la fois :
- Un `ConsumptionInsight` (via `consumption_diagnostic.py`)
- Un `MonitoringAlert` type `HORS_HORAIRES` (via `alert_engine.py`)

Les deux ont des champs similaires (severity, evidence, recommended_actions) mais nommés différemment (`estimated_loss_eur` vs `estimated_impact_eur`).

**Impact** : Un même événement peut créer 2 actions via l'Action Hub (une source CONSUMPTION, une source INSIGHT) → pas de dédup cross-source.

**Périmètre** : Les deux moteurs sont périmètre Yannick. Action Hub (`action_hub_service.py`) est modifiable.

**Tag** : IMPLICITE MAIS NON FIABILISÉ — Dédup cross-source absent

### CONFLIT C5 : alert_engine ne lit pas SiteOperatingSchedule

`consumption_diagnostic.py` lit correctement `SiteOperatingSchedule` pour le détecteur `hors_horaires`. Mais `alert_engine.py` a un type `HORS_HORAIRES` qui ne semble pas lire ce schedule → alertes potentiellement faussement positives pour un hôtel 24/7.

**Périmètre** : `alert_engine.py` est périmètre Yannick.

**Tag** : IMPLICITE MAIS NON FIABILISÉ

### CONFLIT C6 : ConsumptionSource enum incomplète

Backend retourne `source_used: "estimated"` en fallback mais l'enum `ConsumptionSource` ne contient que `METERED | BILLED | RECONCILED`. Le frontend `ConsoSourceBadge` gère `estimated` dans son config — ça marche en pratique mais l'enum backend est incomplète.

**Tag** : IMPLICITE MAIS NON FIABILISÉ — Fonctionne par accident

### Résumé des conflits

| # | Conflit | Sévérité | Corrigeable sans toucher Yannick ? |
| --- | --- | --- | --- |
| C1 | CO₂ 0.052 vs 0.0569 | **HIGH** | NON — `co2_service.py` et `constants.js` sont périmètre Yannick. Signaler uniquement |
| C2 | Compteur vs Meter double-comptage | **HIGH** | PARTIEL — peut migrer `compliance_engine`, `onboarding_service` vers `meter_unified_service` |
| C3 | 3 moteurs DQ parallèles | **MEDIUM** | PARTIEL — peut ajouter une vue unifiée qui agrège les 3 |
| C4 | Insight + Alert = 2 actions pour 1 événement | **MEDIUM** | OUI — dédup cross-source dans `action_hub_service.py` |
| C5 | alert_engine sans schedule | **LOW** | NON — périmètre Yannick |
| C6 | Enum ConsumptionSource incomplète | **LOW** | OUI — ajouter `ESTIMATED` à l'enum |

---

## 9. Top P0 / P1 / P2

### P0 — Aucun bloquant

La brique conso/performance est fonctionnelle. Pas de P0 spécifique à cette brique.

### P1 — Crédibilité

| # | Problème | Impact | Correctif | Effort | Risque régression |
| --- | --- | --- | --- | --- | --- |
| P1-1 | Données seed affichées comme "Compteur" | Expert détecte la fraude en < 1 min | Badge "Données démo" si source = seed (comme MarketContextBanner) | S | Faible |
| P1-2 | Diagnostic pas auto-déclenché | Insights conso vides sans action manuelle | Auto-diagnostic après import ou à l'ouverture de ConsumptionDiagPage | S | Moyen — ne pas surcharger le backend |
| P1-3 | CO2e factor unique 0.052 (élec seul) | Faux pour gaz | Distinguer facteur par energy_vector (0.052 élec, 0.227 gaz) | XS | Faible |

### P2 — Premium

| # | Problème | Impact | Correctif | Effort |
| --- | --- | --- | --- | --- |
| P2-1 | annual_kwh_total pas auto-refresh | Avancement DT stale | Auto-recalculer après import metered (12 mois glissants) | M |
| P2-2 | Seuils alertes non configurables par site | Faux positifs hôtels/datacenters | Ajouter schedule-aware filtering dans alert_engine | M |
| P2-3 | Pas de feed Météo-France réel | Signature énergétique sur données démo | Intégrer API MF ou Synop (endpoint weather_service prêt) | L |
| P2-4 | Gaz beta | Couverture fonctionnelle incomplète | Finaliser normalisation DJU + décomposition base/chauffage | M |

---

## 10. Plan de correction priorisé

### Immédiat (1-2 jours) — XS/S, sans risque régression

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 1 | Badge "Données démo" dans ConsoSourceBadge si MeterReading vient de seed | `ConsoSourceBadge.jsx`, `gen_readings.py` (ajouter `source="seed"`) | S |
| 2 | Facteur CO2e par energy_vector (0.052 élec, 0.227 gaz) | `ConsoKpiHeader.jsx`, `constants.js` | XS |

### Court terme (1 semaine) — S, coordination recommandée

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 3 | Auto-diagnostic au mount de ConsumptionDiagPage (1×/session) | `ConsumptionDiagPage.jsx` | S |
| 4 | Auto-refresh annual_kwh_total après import metered réussi | `DataImportJob` handler, `Site` model | M |

### Moyen terme — Coordonner avec Yannick

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 5 | Seuils alertes configurables par archétype | `alert_engine.py` | M |
| 6 | Feed météo réel | `weather_service.py` | L |

---

## 11. Definition of Done

| Critère | Statut |
| --- | --- |
| Pages conso cartographiées (8) | FAIT |
| Services backend cartographiés (12+) | FAIT |
| Modèles cartographiés (15) | FAIT |
| Intégration avec cockpit vérifiée | FAIT — IMPLÉMENTÉ |
| Intégration avec conformité vérifiée | FAIT — IMPLÉMENTÉ (DT trajectory) |
| Intégration avec facture vérifiée | FAIT — PARTIEL (EnergyInvoice.energy_kwh, pas MeterReading direct) |
| Intégration avec achat vérifiée | FAIT — IMPLÉMENTÉ (MeterReading P1, Invoice P2) |
| Intégration avec actions vérifiée | FAIT — IMPLÉMENTÉ (ConsumptionInsight → ActionItem) |
| Risques de crédibilité identifiés (5) | FAIT |
| Risques de régression identifiés (6 zones) | FAIT |
| P1/P2 priorisés avec effort | FAIT |

---

*Audit étape 4bis réalisé le 2026-03-23. La brique conso est le 3e asset majeur du POC — riche, bien architecturée, et mieux intégrée que le lien conformité↔facture.*
