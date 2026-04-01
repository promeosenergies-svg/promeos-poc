# Audit Usages Énergétiques — Phase 0

> **Date** : 2026-04-01
> **Auteur** : Claude Code (audit lecture seule)
> **Objectif** : Cartographie complète de la page Usages, vérification des calculs, identification des bugs et gaps.

---

## 1. Architecture

### Fichiers

| Couche | Fichier | Lignes | Rôle |
|--------|---------|--------|------|
| Page frontend | `frontend/src/pages/UsagesDashboardPage.jsx` | 1 203 | Page principale — 9 sections, 12 sous-composants inline |
| Import wizard | `frontend/src/pages/ConsommationsUsages.jsx` | 1 240 | Import wizard 7 étapes + KB Admin panel |
| API wrapper | `frontend/src/services/api/energy.js` | 366 | 7 endpoints usages, tous en `cachedGet()` |
| Navigation | `frontend/src/layout/NavRegistry.js` | 977 | Registre menu, module Énergie |
| Routes | `frontend/src/App.jsx` | ~450 | Route `/usages` lazy-loaded |
| Route backend | `backend/routes/usages.py` | 152 | 10 endpoints GET |
| Route KB | `backend/routes/kb_usages.py` | 500+ | Search, archetypes, rules, recommendations |
| Service | `backend/services/usage_service.py` | 1 000+ | Readiness, baselines, IPE, coûts, compliance |
| Modèle Usage | `backend/models/usage.py` | 85 | `Usage` + `UsageBaseline` ORM |
| Modèle Meter | `backend/models/energy_models.py` | 534+ | `Meter` (self-ref parent/sub), `MeterReading` |
| Enums | `backend/models/enums.py` | 300+ | `TypeUsage` (12 types / 6 familles), `DataSourceType` |
| Prix défaut | `backend/config/default_prices.py` | 27 | Fallback 0.068 EUR/kWh (EPEX Spot 2025) |
| Seed master | `backend/services/demo_seed/gen_master.py` | 400+ | Usages par profil (office, hotel, warehouse...) |
| Seed readings | `backend/services/demo_seed/gen_readings.py` | 300+ | 365j × 15 min, profils thermiques/occupancy |
| Seed packs | `backend/services/demo_seed/packs.py` | 500+ | Définition HELIOS : 5 sites, 7 bâtiments |

### Endpoints

| Méthode | URL | Params | Retour | Utilisé par |
|---------|-----|--------|--------|-------------|
| GET | `/api/usages/dashboard/{site_id}` | site_id | Agrégat complet (readiness + plan + UES + drifts + costs + compliance + billing) | `UsagesDashboardPage` |
| GET | `/api/usages/readiness/{site_id}` | site_id | `{score, level, details, recommendations}` | KPI row |
| GET | `/api/usages/metering-plan/{site_id}` | site_id | Arbre compteurs + couverture | Section Plan de comptage |
| GET | `/api/usages/top-ues/{site_id}` | site_id, limit=5 | Top UES par kWh | Section UES |
| GET | `/api/usages/baselines/{site_id}` | site_id | Baseline N-1 vs N par usage | Section Baseline |
| GET | `/api/usages/compliance/{site_id}` | site_id | BACS score + couverture + risques | Section Conformité |
| GET | `/api/usages/cost-breakdown/{site_id}` | site_id, days=365 | Coût par usage + non couvert | Section Coût |
| GET | `/api/usages/billing-links/{site_id}` | site_id | Prix ref + contrat + factures | Section Facture/Achat |
| GET | `/api/usages/taxonomy` | — | Familles + types + labels FR | Import wizard |
| GET | `/api/usages/site/{site_id}` | site_id | Liste usages déclarés du site | Divers |

### Navigation

- **Route** : `/usages`
- **Module parent** : Énergie (tint indigo)
- **Position sidebar** : 3e sur 4 dans Énergie
- **Ordre menu** : Consommations → Performance → **Usages** → Facturation
- **Icon** : BarChart3
- **Keywords recherche** : `usages`, `energetiques`, `plan comptage`, `readiness`, `ues`, `baseline`, `sous-compteur`
- **Lazy loading** : Oui (code-split)
- **Breadcrumb** : PROMEOS > Énergie > Usages

---

## 2. Données démo

### Sous-compteurs HELIOS

| Site | Surface site | Bâtiments | Sous-compteurs | Couverture |
|------|-------------|-----------|----------------|------------|
| Siège Paris | 3 500 m² | A (2000 m²), B (1500 m²) | CVC 35%, Éclairage 20%, IT 15% | 70% |
| Bureau Lyon | 1 200 m² | Principal (1200 m²) | Chauffage 35%, Éclairage 25% | 60% |
| Usine Toulouse | 6 000 m² | Industriel (6000 m²) | Process 30%, Éclairage 20%, Ventilation 10% | 60% |
| Hôtel Nice | 4 000 m² | Hôtel (4000 m²) | Climatisation 40%, Cuisine 25%, Communs 15% | 80% |
| École Marseille | 2 800 m² | Principal (2000 m²), Gymnase (800 m²) | Aucun sous-compteur | 0% |

### Usages par profil (seed)

| Profil | Chauffage | Clim | Éclairage | IT | Ventilation | Autres | UES |
|--------|-----------|------|-----------|-----|-------------|--------|-----|
| Office | 35% ✓ | 15% ✓ | 20% ✓ | 15% | 8% | 7% | 3 UES |
| Hotel | 25% | 15% | 15% | 15% | - | 30% (cuisine/linge) | - |
| Warehouse | 25% | - | 20% | 8% | 10% | 37% (process) | - |
| School | 45% | - | 20% | 10% | 10% | 15% | - |

### Consommation annuelle seedée

| Site | Annual kWh | Benchmark ADEME |
|------|-----------|-----------------|
| Siège Paris | 800 000 | bureau 170 kWh/m² → 595 000 (seed > bench) |
| Bureau Lyon | 350 000 | bureau 170 kWh/m² → 204 000 (seed > bench) |
| Usine Toulouse | 2 500 000 | warehouse 120 kWh/m² → 720 000 (seed >> bench) |
| Hôtel Nice | 1 200 000 | hotel 280 kWh/m² → 1 120 000 (cohérent) |
| École Marseille | 600 000 | school ~100 kWh/m² → 280 000 (seed > bench) |

---

## 3. Bugs identifiés

### P0 — Valeurs fausses

| # | Bug | Localisation | Impact | Cause probable |
|---|-----|-------------|--------|----------------|
| 1 | **IPE Chauffage 647 kWh/m² absurde pour bureau** | `usage_service.py:710-712` | Crédibilité zéro pour un pilote | L'IPE est calculé sur la surface du **bâtiment**, pas du site. Si Bât A = 2000 m² et seul ce bâtiment a le chauffage rattaché, alors 970 804 / 2000 = 485 kWh/m². Mais si surface_m2 Usage = None, fallback sur batiment.surface_m2 = 1500 m² → 970 804 / 1500 ≈ 647. **Le fallback surface est probablement incorrect.** Benchmark ADEME bureau chauffage : ~90-120 kWh/m². |
| 2 | **Coût surconsommation incohérent** | `usage_service.py` + `default_prices.py` | Erreur financière visible | 490 333 kWh × 0.237 €/kWh (prix affiché) = 116 209 €, mais affiché 88 260 €. Si prix = 0.18 €/kWh → 88 260 € (ancien fallback). **Le calcul de coût utilise peut-être le prix contrat (0.145 €/kWh) ou une cascade différente du prix KPI strip.** |
| 3 | **Simulation aléatoire masquée** | `usage_service.py:703-704` | Valeurs fictives présentées comme réelles | Quand pas de readings mais baseline stockée : `kwh_current = kwh_baseline * random.uniform(0.88, 1.08)`. Pas de marqueur "estimé" visible côté UI. |

### P1 — Crédibilité

| # | Issue | Localisation | Impact |
|---|-------|-------------|--------|
| 4 | **0 lien entrant vers /usages** | Autres pages frontend | Page isolée — aucun CTA "Voir les usages" depuis Consommations, Diagnostic, ou Conformité |
| 5 | **École sans sous-compteur** | `packs.py:261-286` | Score readiness = 0/30 pour couverture, pas de UES mesurés |
| 6 | **Delta "Non affecté" sans explication** | `UsagesDashboardPage.jsx` | Le delta principal - sous-compteurs (30-40%) n'est pas expliqué ni actionnable |
| 7 | **Export = window.print()** | `UsagesDashboardPage.jsx` | Pas de PDF structuré, pas d'export Excel |

### P2 — Best-in-world

| # | Gap | Benchmark | Effort |
|---|-----|-----------|--------|
| 8 | Pas de granularité temporelle (mensuel, hebdo, horaire) | Engie NEXT, Deepki → time series par usage | M |
| 9 | Pas de comparaison inter-sites | DGO, ista → ranking sites par IPE/usage | S |
| 10 | Pas de cible réglementaire sur le graphe (DT -40%, BACS Class A) | Plateformes ISO 50001 → target lines | S |
| 11 | Pas de drill-down usage → sous-compteur → relevé | Schneider EcoStruxure → 3 niveaux | L |
| 12 | Pas d'alerte proactive si dérive > seuil | Energisme → push notifications | M |

---

## 4. Calculs vérifiés

### IPE (kWh/m²)

- **Formule** : `kwh / batiment.surface_m2` (fallback `usage.surface_m2`)
- **Fichier** : `backend/services/usage_service.py:710-712`
- **Dénominateur** : Surface du **bâtiment** rattaché à l'usage (via `Usage.batiment`), PAS la surface du site
- **Bug** : Si un usage couvre plusieurs bâtiments ou si le rattachement bâtiment est incorrect, l'IPE est faux. Pour le chauffage d'un bureau, l'IPE attendu est 90-120 kWh/m²/an (ADEME). Les 647 kWh/m² affichés sont 5-7× trop élevés → **P0 confirmé**
- **Cause racine probable** : Le seed assigne les usages aux bâtiments individuels (2000 m² ou 1500 m²), mais le chauffage kWh inclut tout le site (800 000 × 35% = 280 000 kWh). Avec 1500 m² : 280 000 / 1500 = 186 kWh/m². Avec usage.surface_m2 calculé comme `bat_surface * pct / 100` = 1500 × 35% = 525 m² → 280 000 / 525 = **533 kWh/m²**. Ni l'un ni l'autre ne correspond au benchmark.

### Score readiness (/100)

- **Formule** : `usage_service.py:38-158`
  - 30 pts : usages déclarés / attendus (min 3)
  - 30 pts : couverture sous-comptage (sub_kwh / principal_kwh × 100) → plafonné à 30
  - 20 pts : qualité données (avg `quality_score` × 20)
  - 20 pts : ancienneté (min(1.0, jours_données / 365) × 20)
- **Seuils** : GREEN ≥ 75, AMBER 40-74, RED < 40
- **Explain dans l'UI** : Oui — le backend retourne `details{}` avec chaque composant (score, max, count/pct/avg/days) + `recommendations[]` (texte FR). Le frontend affiche les recommandations si score < 100.
- **Verdict** : Calcul solide, bien décomposé, pas de violation arch. **OK**

### Coût surconsommation (€)

- **Formule** : `ecart_kwh × prix_reference`
- **Prix — cascade** (`default_prices.py` + `usage_service.py`) :
  1. Contrat actif : `EnergyContract.price_ref_eur_per_kwh` (ex: 0.145 €/kWh pour Siège Paris)
  2. Moyenne factures 12 mois : `sum(EUR) / sum(kWh)`
  3. Défaut : **0.068 EUR/kWh** (EPEX Spot 2025)
- **Ancien fallback** : 0.18 EUR/kWh (retiré, commentaire en `default_prices.py:16`)
- **Incohérence captures** :
  - KPI strip affiche 23.7 c€/kWh = 0.237 €/kWh (prix spot marché ?)
  - Calcul coût affiche 88 260 € = 490 333 × 0.18 (ancien fallback ?)
  - Mais cascade actuelle donnerait : contrat 0.145 → 490 333 × 0.145 = 71 098 €
  - **Aucun des 3 prix ne donne 88 260 € de manière cohérente** → Bug P0

### UES (critère significatif)

- **Seuil** : `Usage.is_significant = True` (booléen, fixé au seed ou manuellement)
- **Pas de seuil % automatique** : Le champ est déclaratif, pas calculé (pas de "si > 5% du total → UES")
- **Conformité ISO 50001** : `concerned_by_iso50001 = is_significant`
- **Seed office** : Chauffage, Climatisation, Éclairage marqués `is_significant=True`
- **Ventilation (8%)** : Marquée `is_significant=False` dans le seed office. Le badge UES ne s'affiche pas.
- **Gap** : En ISO 50001, le critère UES est dynamique (% conso + potentiel d'amélioration). Ici c'est statique.

---

## 5. Placement navigation

### Actuel

- **Section** : Énergie (module indigo)
- **URL** : `/usages`
- **Position sidebar** : 3e sur 4 → Consommations > Performance > **Usages** > Facturation
- **Breadcrumb** : PROMEOS > Énergie > Usages
- **Accessible depuis** : Sidebar, breadcrumb, URL directe, recherche rapide (7 keywords)
- **Lazy loading** : Oui

### Recommandation

- **Position actuelle OK** — logiquement placée entre Performance (vue macro) et Facturation (vue financière)
- **Manque** : Liens entrants depuis les pages voisines (Consommations, Performance, Diagnostic) → les ajouter pour créer un parcours fluide

---

## 6. Liens cross-briques

### Depuis Usages →

| # | Vers | URL | CTA | Fonctionne ? |
|---|------|-----|-----|-------------|
| 1 | Diagnostic Conso | `/diagnostic-conso` | Dérives → "Traiter →" | Oui (navigate) |
| 2 | Conformité Tertiaire | `/conformite/tertiaire` | Compliance → "Voir la conformité détaillée →" | Oui |
| 3 | Bill-Intel | `/bill-intel` | Billing → "Voir les factures →" | Oui |
| 4 | Contrats Radar | `/contrats-radar` | Billing → "Rattacher un contrat →" | Oui |
| 5 | Achat Énergie | `/achat-energie` | Billing → "Scénarios d'achat →" | Oui |
| 6 | Diagnostic Conso | `/diagnostic-conso` | Footer → bouton Diagnostic | Oui |
| 7 | Conformité | `/conformite/tertiaire` | Footer → bouton Conformité | Oui |
| 8 | Factures | `/bill-intel` | Footer → bouton Factures | Oui |
| 9 | Actions | `/actions` | Footer → bouton Actions | Oui |
| 10 | Patrimoine | `/patrimoine` | Footer → bouton Patrimoine | Oui |

### Vers Usages ←

| # | Depuis | CTA | Existe ? |
|---|--------|-----|----------|
| 1 | Consommations | "Voir les usages →" | **NON** |
| 2 | Performance | "Détail par usage →" | **NON** |
| 3 | Diagnostic Conso | "Voir les usages du site →" | **NON** |
| 4 | Conformité | "Voir les UES →" | **NON** |
| 5 | Patrimoine | "Usages du bâtiment →" | **NON** |

**Verdict** : 10 CTAs sortants, **0 entrants**. La page est un hub mais personne ne pointe vers elle.

---

## 7. Score par axe

| Axe | Score /10 | Justification |
|-----|-----------|---------------|
| Données & calculs | **4/10** | IPE faux (P0), coût incohérent (P0), simulation aléatoire masquée. Score readiness OK. |
| UX/UI | **7/10** | Page riche (9 sections), KPI strip, print-friendly. Manque granularité temporelle, drill-down. |
| Cohérence inter-briques | **5/10** | 10 CTAs sortants excellents, mais 0 entrants. Page isolée dans le parcours utilisateur. |
| Complétude réglementaire | **6/10** | BACS, DT, ISO 50001 liés. Manque : UES dynamique (ISO 50001), cibles DT sur graphe, CEE. |
| Architecture code | **8/10** | Zéro calcul frontend (tout backend), lazy loading, cache API, code propre. `random.uniform` à retirer. |
| Navigation & placement | **7/10** | Bien placée dans sidebar. Breadcrumb OK. Manque liens entrants depuis pages voisines. |
| Seed démo | **5/10** | 5 sites variés, sous-compteurs crédibles. Mais surfaces/conso incohérentes avec ADEME, 1 site sans sous-compteur, annual_kwh >> benchmark. |
| **GLOBAL** | **6/10** | Bonne architecture, page riche, mais P0 calculs (IPE, coûts) et isolation navigation à corriger avant pilote. |

---

## 8. Résumé exécutif — 3 questions bloquantes résolues

### Q1 — Dénominateur IPE : **Surface du bâtiment**
> `usage_service.py:710` : `kwh / batiment.surface_m2` avec fallback `usage.surface_m2`.
> Le problème : le seed divise la surface du bâtiment par le % de l'usage (ex: 1500 m² × 35% = 525 m²), ce qui donne des IPE aberrants (280 000 / 525 = 533 kWh/m²). **La formule backend est correcte en principe mais les données seed créent des incohérences.**

### Q2 — Score readiness : **Backend, composite /100**
> `usage_service.py:38-158` : 30 pts (usages) + 30 pts (couverture) + 20 pts (qualité) + 20 pts (ancienneté).
> Explain fourni via `details{}` + `recommendations[]`. **Pas de violation arch. OK.**

### Q3 — Route : **`/usages`, 3e dans Énergie, sidebar OK**
> `NavRegistry.js:494` : Position 3/4 dans section Énergie (Conso > Perf > **Usages** > Factu).
> Breadcrumb OK. Lazy loaded. **Mais 0 liens entrants depuis d'autres pages.**

---

## 9. Roadmap recommandée

### Sprint P0 (immédiat — avant pilote)
1. **Corriger IPE** : Utiliser surface site (pas bâtiment/usage proportionnel) comme dénominateur, ou bien normaliser pour le chauffage global
2. **Aligner prix coût surconsommation** : S'assurer que le prix utilisé pour le coût = le prix affiché dans le KPI strip
3. **Marquer les estimations** : Ajouter badge "Estimé" quand `kwh_current` vient de `random.uniform` (ou supprimer cette simulation)
4. **Ajouter liens entrants** : CTA "Voir les usages" depuis Consommations, Performance, Diagnostic

### Sprint P1 (crédibilité pilote)
5. Calibrer données seed HELIOS sur benchmarks ADEME réalistes
6. Ajouter sous-compteurs à l'école Marseille
7. Rendre UES dynamique (seuil % configurable au lieu de booléen statique)
8. Ajouter cibles réglementaires (DT -40%) sur le tableau baseline

### Sprint P2 (best-in-world)
9. Granularité temporelle (mensuel/hebdo) par usage
10. Comparaison inter-sites (ranking IPE)
11. Drill-down usage → sous-compteur → relevé
12. Export PDF structuré (jsPDF) + Excel
