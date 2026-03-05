# Audit Cohérence KPI — PROMEOS V117+

> Généré le 2026-03-05 — Playbook Phase 0, Prompt 0.3

---

## 1. KPI "Consommation totale kWh"

### Sources identifiées

| Module | Fichier:Ligne | Source données | Formule | Période défaut |
|--------|--------------|----------------|---------|----------------|
| Cockpit | `cockpit.py` | N/A | **Pas de conso affichée** — affiche avancement_decret_pct + risque_financier | N/A |
| Consumption Context | `consumption_context_service.py:227` | `MeterReading` (physique) | `hp_kwh + hc_kwh` via `tou_service.py:395` | 30 jours |
| Monitoring KPI | `kpi_engine.py:66,117` | `MeterReading` (physique) | `sum(value_kwh)` — sélection freq 15min > horaire | 90 jours |
| Billing Summary | `billing_service.py:810,885` | `EnergyInvoice` (commercial) | `sum(i.energy_kwh or 0)` | **Toutes factures** (pas de filtre temporel) |
| Patrimoine | `patrimoine.py:1223` | `Site.annual_kwh_total` (statique) | Champ pré-rempli manuellement | Annuelle |
| Gas Summary | `consumption_diagnostic.py:864-882` | `MeterReading` (GAS) | `sum(daily[day].kwh)` | N derniers jours |

### Incohérences détectées

| # | Problème | Sévérité | Impact |
|---|----------|----------|--------|
| 1 | **Deux sources incompatibles** : MeterReading (physique) vs EnergyInvoice (commercial) — peuvent diverger 5-15% | MAJEUR | Confusion utilisateur entre "conso mesurée" et "conso facturée" |
| 2 | **Plages temporelles différentes** : Context=30j, Monitoring=90j, Billing=tout, Patrimoine=statique | MAJEUR | KPIs non comparables entre vues |
| 3 | **Fréquences filtrées différemment** : Monitoring exclut DAILY/MONTHLY, Gas Summary inclut tout | MINEUR | Agrégation potentiellement incorrecte si lectures mixtes |
| 4 | **`Site.annual_kwh_total` jamais mis à jour** automatiquement | MINEUR | Donnée patrimoniale obsolète |
| 5 | **Pas de rapprochement** MeterReading vs EnergyInvoice | MOYEN | Écarts non détectés |

### Verdict : **6/10** — Deux systèmes parallèles sans réconciliation

### Recommandation
- Créer `get_consumption_summary(db, site_id, source="metered"|"billed"|"all")` comme source unique
- Normaliser les plages temporelles (paramètre `period_start/period_end` partout)
- Ajouter règle de rapprochement automatique `|metered - billed| < X%`

---

## 2. KPI "Risque financier (EUR)"

### Sources identifiées

| Module | Fichier:Ligne | Input | Formule | Cache |
|--------|--------------|-------|---------|-------|
| Compliance Engine | `compliance_engine.py:85-88` | Obligations | `7500 × COUNT(NON_CONFORME)` — **A_RISQUE ignoré** | Aucun |
| Site Snapshot | `compliance_engine.py:177-198` | Obligations + Evidences | `7500 × COUNT(NON_CONFORME)` — **A_RISQUE ignoré** | Persisté dans `Site.risque_financier_euro` |
| Migration Backfill | `migrations.py:778-779` | SQL direct | `7500 × NON_CONFORME + 3750 × A_RISQUE` | BDD |
| Demo Seed | `orchestrator.py:644-648` | Obligations loop | `7500 × NON_CONFORME + 3750 × A_RISQUE` | BDD |
| Cockpit | `cockpit.py:89` | `Site.risque_financier_euro` | `SUM(site.risque_financier_euro)` | Lit snapshot |
| Patrimoine | `patrimoine.py:1180` | `Site.risque_financier_euro` | `SUM(site.risque_financier_euro)` | Lit snapshot |
| KPI Service | `kpi_service.py:114` | `Site.risque_financier_euro` | `SUM(site.risque_financier_euro)` | Cache TTL 5min |
| Patrimoine Impact | `patrimoine_impact.py:138-261` | Anomalies data quality | Formules par type anomalie (15% surface, 20% meter...) | Aucun |

### Incohérences détectées

| # | Problème | Sévérité | Impact |
|---|----------|----------|--------|
| 1 | **A_RISQUE traité différemment** : compliance_engine=0€, migration=3750€, seed=3750€ | CRITIQUE | Même site : 7500€ vs 11250€ selon initialisation |
| 2 | **Deux métriques "risque" confusantes** : `Site.risque_financier_euro` (pénalité réglementaire) vs `estimated_risk_eur` (risque data quality) | MAJEUR | Métriques incomparables portant des noms similaires |
| 3 | **Constante SQL hard-codée** : `7500.0` dans migrations.py au lieu d'importer `BASE_PENALTY_EURO` | MINEUR | Maintenance difficile |
| 4 | **Cache stale** : cockpit lit `Site.risque_financier_euro` qui dépend de `recompute_site()` | MOYEN | Données potentiellement périmées |

### Exemple concret de divergence

```
Site avec 2 NON_CONFORME + 1 A_RISQUE :
- Via compliance_engine.compute_risque_financier() : 15 000 €
- Via demo_seed._sync_site_compliance_statuses() : 18 750 €
- Écart : +3 750 € (25%)
```

### Verdict : **5/10** — Incohérence critique sur A_RISQUE entre formule officielle et seed/migration

### Recommandation
- Aligner migration + seed sur la formule officielle (A_RISQUE = 0€)
- Ou décider produit que A_RISQUE = 50% et modifier compliance_engine
- Centraliser : importer `BASE_PENALTY_EURO` dans tous les fichiers (pas de SQL hard-codé)

---

## 3. KPI "Score conformité"

### Systèmes identifiés

| Système | Fichier:Ligne | Formule | Range | Cache |
|---------|--------------|---------|-------|-------|
| **Snapshot Site** | `compliance_engine.py:409-436` | `reg_risk = min(100, NOK×30 + A_RISQUE×15 + NOK_findings×10)` | 0-100 (higher=worse) | Aucun |
| **RegOps Scoring** | `regops/scoring.py:118-208` | Weighted penalties + urgency + dedup | 0-100 (higher=better) | `RegAssessment` table |
| **Cockpit** | `cockpit.py:60-85` | Count `NON_CONFORME` + `A_RISQUE` sites | Count (pas un score) | `Site.*` snapshot fields |

### Incohérences détectées

| # | Problème | Sévérité | Impact |
|---|----------|----------|--------|
| 1 | **Trois formules distinctes** pour "score conformité" | CRITIQUE | Même site peut avoir 3 scores différents |
| 2 | **Échelles inversées** : Snapshot reg_risk 0-100 (higher=worse), RegOps compliance_score 0-100 (higher=better) | CRITIQUE | Confusion complète si comparés |
| 3 | **Inputs différents** : Snapshot utilise Obligations, RegOps utilise Findings YAML | MAJEUR | Données source incompatibles |
| 4 | **RegOps applique urgency**, Snapshot non | MOYEN | Pondération temporelle incohérente |
| 5 | **Dedup explicite** en RegOps, implicite en Snapshot | MINEUR | Double-counting possible |
| 6 | **Caches séparés** : Site fields (manual recompute) vs RegAssessment (stale flag) vs V68 (toujours frais) | MOYEN | Freshness incohérente |

### Exemple concret de divergence

```
Site avec 2 findings NON_CONFORME (deadline imminente) :
- Snapshot reg_risk : min(100, 2×30) = 60 (higher = worse)
- RegOps compliance_score : 100 - weighted(urgency×severity) ≈ 30 (higher = better)
- Cockpit : "2 sites non conformes" (count, pas score)
→ Trois représentations incomparables
```

### Verdict : **4/10** — Trois systèmes indépendants sans unification

### Recommandation
- Unifier vers RegOps (le plus mature, avec urgency + dedup + profil configurable)
- Migrer cockpit vers `RegAssessment.compliance_score` au lieu de counts
- Créer un score composite : `compliance_composite = weighted_avg(regops, bacs, tertiaire)`

---

## 4. Unités & formatage frontend

### Formatter centralisé : `frontend/src/utils/format.js`

| Fonction | Conversion | Seuils | Locale |
|----------|-----------|--------|--------|
| `fmtEur(v)` | € → k€ → M€ | ≥1k → k€, ≥1M → M€ | `fr-FR` ✓ |
| `fmtEurFull(v)` | Toujours en € | Séparateur milliers | `fr-FR` ✓ |
| `fmtKwh(v)` | kWh → k kWh → GWh | ≥1k → k kWh, ≥1M → GWh | `fr-FR` ✓ |
| `formatPercentFR(v)` | % | 0 décimales | `Intl.NumberFormat` ✓ |

### Conversions énergétiques : 100% correctes

Toutes les conversions kWh→MWh (÷1000) et €/MWh→€/kWh (÷1000) sont correctes. Aucune inversion détectée.

### Problèmes détectés

| # | Fichier:Ligne | Problème | Sévérité |
|---|--------------|----------|----------|
| 1 | `PurchaseAssistantPage.jsx:1307` | **`Math.min(...[])` = Infinity** si tableau vide → affiche "Infinity EUR/MWh" | BUG CRITIQUE |
| 2 | `PatrimoineHealthCard.jsx:83` | Pas `.toLocaleString()` → "1234 €" au lieu de "1 234 €" | BUG FORMATAGE |
| 3 | `PatrimoineRiskDistributionBar.jsx:17` | Pas `.toLocaleString()` → montants sans séparateurs | BUG FORMATAGE |
| 4 | `PatrimoinePortfolioHealthBar.jsx:56` | Pas `.toLocaleString()` → montants sans séparateurs | BUG FORMATAGE |
| 5 | `SiteAnomalyPanel.jsx:91` | Pas `.toLocaleString()` → montants sans séparateurs | BUG FORMATAGE |
| 6 | `AnomaliesPage.jsx:43-48` | `fmtEur` locale avec préfixe `~` + pas `.toLocaleString()` | DIVERGENT |
| 7 | `ROISummaryBar.jsx:9` | `EUR` au lieu de `€`, pas compaction k€/M€ | DIVERGENT |
| 8 | `SitePicker.jsx:270` | `(s.conso_kwh_an / 1000).toFixed(0)}k kWh` — pas d'espace insécable | COSMÉTIQUE |
| 9 | `impactDecisionModel.js:126` | `_fmtEurSimple()` duplique `fmtEur()` avec retour `'0 €'` vs `'—'` | DUPLIQUÉ |

### Adoption des formatters centralisés

- **5 fichiers** importent les formatters sur **378 fichiers** = taux d'adoption très faible
- La majorité des pages utilisent du formatage inline — fonctionnellement correct mais non uniforme

### Verdict : **7/10** — Conversions correctes, formatage dupliqué, 1 bug Infinity

### Recommandation
- Fix immédiat : guard `scoredOffers.length > 0` dans PurchaseAssistantPage
- Ajouter `.toLocaleString('fr-FR')` dans les 4 composants Patrimoine
- Migration progressive vers `fmtEur`/`fmtKwh` centralisés

---

## 5. Tableau récapitulatif

| KPI | Cohérent ? | Score | Problème principal |
|-----|-----------|-------|--------------------|
| Consommation kWh | NON | 6/10 | Deux sources incompatibles (metered vs billed) sans réconciliation |
| Risque financier € | NON | 5/10 | A_RISQUE traité à 0€ (engine) vs 3750€ (seed/migration) |
| Score conformité | NON | 4/10 | Trois formules indépendantes, échelles inversées |
| Unités & formatage | OUI (partiel) | 7/10 | 1 bug Infinity, 4 composants sans toLocaleString, formatters sous-utilisés |

### **Score cohérence KPI global : 55/100**

---

## 6. Plan d'action recommandé

### Priorité 1 — Bugs critiques (immédiat)
1. **Fix A_RISQUE** : aligner `migrations.py` et `orchestrator.py` sur la formule officielle (A_RISQUE = 0€), ou décision produit inverse
2. **Fix Infinity** : `PurchaseAssistantPage.jsx:1307` — guard `.length > 0`
3. **Fix toLocaleString** : 4 composants Patrimoine (PatrimoineHealthCard, RiskDistributionBar, PortfolioHealthBar, SiteAnomalyPanel)

### Priorité 2 — Unification (sprint suivant)
4. **Score conformité unique** : migrer cockpit vers RegAssessment, créer `compliance_composite_score`
5. **Consommation unifiée** : créer `get_consumption_summary(source="metered"|"billed"|"all")`
6. **Formatters centralisés** : migration progressive vers `fmtEur`/`fmtKwh`

### Priorité 3 — Qualité long terme
7. **Rapprochement auto** : règle `|metered - billed| > 10%` → alerte
8. **Cache cohérent** : event-driven invalidation de `Site.risque_financier_euro`
9. **Tests de cohérence** : `test_kpi_coherence.py` vérifiant cockpit === sum(sites)

---

*Rapport généré par Playbook Phase 0.3 — Cohérence KPI cross-briques*
