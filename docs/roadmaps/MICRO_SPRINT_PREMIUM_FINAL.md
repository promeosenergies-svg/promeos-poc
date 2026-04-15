# COMPTE-RENDU FINAL — Micro-Sprint Premium Usages V1.2 → V1.2+

**Date** : 2026-03-14
**Scope** : 5 actions premium + 2 bugs correctifs
**Verdict** : **TOUS CORRIGÉS — PREMIUM PRÊT DÉMO**

---

## 1. ACTIONS RÉALISÉES

### ACTION 1 : Cohérence Header / Plan de comptage / Badges

**Problème** : Le header affichait "Sous-compteurs" mais le nombre ne correspondait pas au plan de comptage. Les badges "Mesuré"/"Estimé" n'étaient pas cohérents avec la source réelle des données.

**Fix** :
- `usage_service.py` : `get_usages_dashboard()` enrichi avec `principals_count`, `measured_ues`, `estimated_ues`, `metering_coverage_pct`
- `UsagesDashboardPage.jsx` : KPI header remplacé — card "Readiness" → card "UES mesurés" avec split mesuré/estimé
- `usage_service.py` : `compute_baselines()` retourne `data_source` précis (`mesure_directe`, `estimation_prorata`, `baseline_stockee`)
- Frontend : mapping `dataSourceLabel()` ajouté pour les 3 sources

**Preuve** : Header KPI affiche "X mesurés · Y estimés" cohérent avec le plan de comptage

### ACTION 2 : Déduplication UES (Top Usages)

**Problème** : Un site multi-bâtiments affichait "Chauffage ×2", "Éclairage ×2" car les usages étaient listés par `usage_id` au lieu d'être groupés par `TypeUsage`. De plus, les % dépassaient 100% (228% → puis 182% → puis 112%).

**Fix** : Réécriture complète de `get_top_ues()` en 3 phases :
1. **Phase 1** : Collecter kWh par usage_id depuis les sous-compteurs réels + tracker les `measured_types`
2. **Phase 2** : Fallback `pct_of_total` uniquement pour les types NON déjà couverts par sous-compteurs
3. **Phase 3** : Groupement par `TypeUsage` (merge multi-bâtiments) + normalisation si `raw_sum > total_kwh`

**3 bugs corrigés en cascade** :
| Bug | Cause | Fix |
|-----|-------|-----|
| Doublons UES | Listing par usage_id | Groupement par TypeUsage |
| % > 100% (228%) | Compteurs principaux inclus dans query | Filtre `parent_meter_id.isnot(None)` |
| % > 100% (112%) | Estimé + mesuré pour même type | Skip fallback si type déjà mesuré + normalisation |

**Preuve** :
```
Chauffage:        34,7%  (mesuré)
Éclairage:        19,8%  (mesuré)
Climatisation:    15,3%  (mesuré)
IT & Bureautique: 14,9%  (mesuré)
Ventilation:       8,1%  (estimé)
Autres:            7,1%  (estimé)
TOTAL:            99,9%
```

### ACTION 3 : Bloc "Impact facture & achat" non ambigu

**Problème** : Le bloc affichait des prix sans indiquer leur source. "Explorer le contrat" affiché même sans contrat. Aucune distinction entre "prix contrat", "prix facture", "prix par défaut".

**Fix** : Réécriture de `BillingLinksWidget` dans `UsagesDashboardPage.jsx` :
- Message contextuel source prix : "Prix du contrat actif" / "Prix moyen issu des factures" / "Prix par défaut (aucune facture ni contrat)"
- CTA conditionnel : "Rattacher un contrat" si aucun contrat, "Explorer le contrat" sinon
- Sous-message contextuel : "Import factures disponible" si factures existent mais pas de contrat

**Preuve** : Bloc affiche source de prix + CTA approprié au contexte

### ACTION 4 : Résumé exécutif Baseline avant/après

**Problème** : La section baseline montrait un tableau technique sans synthèse. Un DG ne pouvait pas comprendre en 10 secondes si la situation s'améliore ou se dégrade.

**Fix** : Nouveau composant `BaselineSummary` dans `UsagesDashboardPage.jsx` :
- Bandeau coloré (vert/rouge/gris) selon tendance dominante
- Compteurs : "X en amélioration · Y en dégradation"
- Total écart kWh/an + estimation EUR (×0,18 EUR/kWh)
- Messages :
  - Amélioration : "Tendance favorable — {N} usages en amélioration, économie estimée ~{EUR} EUR/an"
  - Dégradation : "Attention — {N} usages en dégradation, surcoût estimé ~{EUR} EUR/an"
  - Stable : "Stable — aucune dérive significative détectée"

**Preuve** : Bandeau résumé visible au-dessus du tableau baseline

### ACTION 5 : Brief V1.3 produit

**Livrable** : `BRIEF_USAGES_V1.3.md` — 5 chantiers priorisés :
1. Export preuve PDF/CSV (2-3j, impact critique audit)
2. Couverture globale pondérée + par vecteur (1j)
3. Zones fonctionnelles modèle + lien (2j)
4. Usage ↔ sources + confidence (1-2j)
5. Vue portfolio multi-sites (2-3j)

---

## 2. BUGS CORRECTIFS SUPPLÉMENTAIRES

### BUG-1 : "Aucune facture importée" alors que 7 factures existent

**Cause** : `useDataReadiness.js` lisait `billingSummary?.distinct_months` mais l'API `/api/billing/summary` retourne `coverage_months`. Le champ était toujours `undefined` → 0 → "Aucune facture".

**Fix** : `useDataReadiness.js` ligne 42 :
```javascript
// Avant: billingMonthCount: billingSummary?.distinct_months ?? 0,
billingMonthCount: billingSummary?.coverage_months ?? billingSummary?.distinct_months ?? 0,
```

**Preuve** : Popup readiness affiche le bon nombre de mois de couverture

### BUG-2 : KPI Cards texte tronqué (cockpit)

**Cause** : `ExecutiveKpiRow.jsx` utilisait `truncate` (Tailwind — `text-overflow: ellipsis` sur 1 ligne). Le sous-titre `kpi.sub` était coupé.

**Fix** : `ExecutiveKpiRow.jsx` ligne 78 :
```javascript
// Avant: <p className="text-xs text-gray-500 mt-0.5 truncate">{kpi.sub}</p>
{kpi.sub && <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{kpi.sub}</p>}
```

**Preuve** : KPI cards affichent le sous-titre complet (max 2 lignes)

---

## 3. FICHIERS TOUCHÉS

### Backend

| Fichier | Modification |
|---------|-------------|
| `services/usage_service.py` | Réécriture `get_top_ues()` (groupement TypeUsage + normalisation), fix `compute_baselines()` data_source, enrichissement `get_usages_dashboard()` summary |

### Frontend

| Fichier | Modification |
|---------|-------------|
| `src/pages/UsagesDashboardPage.jsx` | KPI header cohérent, `dataSourceLabel()`, `BaselineSummary`, `BillingLinksWidget` contextuel |
| `src/hooks/useDataReadiness.js` | Fix `coverage_months` vs `distinct_months` |
| `src/pages/cockpit/ExecutiveKpiRow.jsx` | `truncate` → `line-clamp-2` |

### Documentation

| Fichier | Contenu |
|---------|---------|
| `BRIEF_USAGES_V1.3.md` | Brief produit V1.3 (5 chantiers) |
| `AUDIT_QUESTIONNAIRE_PROFIL_ENERGIE.md` | Audit sévère questionnaire + proposition V1.3 |

---

## 4. TESTS

| Suite | Résultat |
|-------|----------|
| Frontend (Vitest) | **5 587 tests — 190 fichiers — ALL PASSED** |
| Backend import | OK (zéro erreur) |
| API /usages/dashboard/1 | 200 OK, données cohérentes |
| API /billing/summary | 200 OK, `coverage_months` correct |

---

## 5. COMMITS

| Hash | Message |
|------|---------|
| `9297c42` | V1.2 Premium — Usages finition métier + fix readiness billing |
| `2df7a6d` | fix: KPI cards truncated text → line-clamp-2 + readiness billing field name |
| `df00530` | docs: audit questionnaire profil énergie + brief usages V1.3 |

---

## 6. TABLEAU FINAL

| # | Item | Statut | Avant | Après | Type |
|---|------|--------|-------|-------|------|
| A1 | Cohérence header/plan/badges | **FAIT** | Incohérent | Mesuré/Estimé aligné | Front+Back |
| A2 | Déduplication UES | **FAIT** | 228% · doublons | 99,9% · types uniques | Back |
| A3 | Bloc facture non ambigu | **FAIT** | Source prix invisible | Source + CTA contextuels | Front |
| A4 | Résumé exécutif baseline | **FAIT** | Tableau technique seul | Bandeau tendance + EUR | Front |
| A5 | Brief V1.3 | **FAIT** | — | Document livré | Doc |
| BUG-1 | Readiness "0 factures" | **FAIT** | "Aucune facture" | Mois corrects | Front |
| BUG-2 | KPI cards tronqués | **FAIT** | Texte coupé | line-clamp-2 | Front |

---

## 7. PROCHAINES ÉTAPES SUGGÉRÉES

1. **Push GitHub** — 3 commits locaux à pousser
2. **Questionnaire V1.3 quick wins** — renommer titre modal, ajouter q_surface_seuil, message confirmation
3. **KPI cards tooltips** — détails en bulle info au lieu d'inline
4. **Filtrage réglementation** — KPI conformité filtré par profil utilisateur (q_typologie)
5. **Export preuve PDF** — premier chantier du brief V1.3
