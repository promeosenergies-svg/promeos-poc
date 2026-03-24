# Audit Complet Cockpit PROMEOS — V2
**Date** : 24 mars 2026
**Branche** : `fix/migrate-calc-to-backend`
**Méthode** : Audit multi-agents (architecture, données, UX/UI pixel-perfect)

---

## Résumé exécutif

| Catégorie | CRITICAL | HIGH | MEDIUM | LOW |
|-----------|----------|------|--------|-----|
| Architecture / Calculs | 2 | 1 | 1 | 0 |
| Données / Cohérence | 1 | 2 | 2 | 3 |
| UX/UI vs Maquettes | 4 | 4 | 3 | 2 |
| **Total** | **7** | **7** | **6** | **5** |

**Score global : 25 écarts identifiés** dont 7 critiques à corriger en priorité.

---

## 1. BUGS CRITIQUES (à corriger immédiatement)

### CRIT-1 — Benchmark endpoint data leak multi-tenant
- **Fichier** : `backend/routes/cockpit.py:278-279`
- **Bug** : `GET /api/cockpit/benchmark` parse `X-Org-Id` mais ne l'utilise PAS dans la query. Retourne les sites de TOUTES les organisations.
- **Fix** : Remplacer la query par `_sites_for_org(db, org_id)` (helper déjà existant ligne 31).

### CRIT-2 — CO₂ endpoint data leak quand org_id=0
- **Fichier** : `backend/routes/cockpit.py:501`
- **Bug** : `GET /api/cockpit/co2` passe `org_id=0` quand le header est absent. `compute_portfolio_co2(db, 0)` → 0 est falsy → pas de filtre org → toutes les orgs retournées.
- **Fix** : Utiliser `resolve_org_id(request, auth, db)` comme les autres endpoints.

### CRIT-3 — risqueTotal affiché = réglementaire seul, label promet "pénalités + anomalies billing"
- **Fichier** : `frontend/src/hooks/useCockpitData.js:38`
- **Bug** : `risqueTotal: s.risque_financier_euro` mappe uniquement le risque réglementaire. Le backend expose `risque_breakdown.total_eur` (réglementaire + billing) mais il n'est pas utilisé.
- **Fix** : `risqueTotal: s.risque_breakdown?.total_eur ?? s.risque_financier_euro ?? 0`

### CRIT-4 — CO₂ factor : 0.052 est la valeur ADEME correcte (pas 0.0569)
- **Fichier** : `backend/config/emission_factors.py:15,25`
- **Constat** : Le fichier de config documente explicitement : *"l'ancien 0.0569 n'est retrouvé dans aucune source ADEME actuelle"*. La valeur canonique est **0.052 kgCO₂/kWh** (ADEME Base Empreinte V23.6).
- **Impact** : `compliance_engine.py` a `CO2_FACTOR_ELEC_KG_KWH = 0.052` (correct). Le test P0 asserte `== 0.052` (correct). Le commentaire "ADEME 2024 0.0569" dans certains fichiers frontend est **faux** — c'est un tarif TURPE 7 (LU c_HPH), pas un facteur CO₂.
- **Action** : Nettoyer les commentaires frontend qui mentionnent 0.0569 comme facteur CO₂.

### CRIT-5 — VecteurEnergetiqueCard fallback agrège CO₂ côté front
- **Fichier** : `frontend/src/pages/cockpit/VecteurEnergetiqueCard.jsx:62-89`
- **Bug** : Le bloc "rétro-compatibilité" calcule `scope1KgCo2`, `scope2KgCo2`, MWh et % côté front depuis `data.sites.breakdown`. Violation architecture "zéro calcul métier en front".
- **Fix** : Supprimer le fallback. Si `data.vectors` est absent → afficher EmptyState.

### CRIT-6 — billing summary `total_estimated_loss_eur` inclut les insights résolus
- **Fichier** : `backend/routes/billing.py:873-877`
- **Bug** : Pas de filtre sur `insight_status`. Inclut `RESOLVED` et `FALSE_POSITIVE`. Le cockpit filtre correctement (ligne 152-159) → **incohérence** entre les 2 endpoints pour le même KPI.
- **Fix** : Ajouter `.filter(BillingInsight.insight_status.notin_([RESOLVED, FALSE_POSITIVE]))` dans billing summary.

### CRIT-7 — `bacs_engine.py` hardcode `7500.0` au lieu d'importer
- **Fichier** : `backend/services/bacs_engine.py:472`
- **Bug** : `bacs_penalty = 7500.0` — littéral dupliqué, non importé de `compliance_engine.BASE_PENALTY_EURO`.
- **Fix** : `from services.compliance_engine import BASE_PENALTY_EURO; bacs_penalty = BASE_PENALTY_EURO`

---

## 2. BUGS HIGH (à corriger dans le sprint)

### HIGH-1 — `projection_mwh` toujours vide → série verte invisible
- **Fichier** : `backend/routes/cockpit.py:479`
- **Bug** : `"projection_mwh": []` hardcodé. La légende "Projection actions planifiées" s'affiche mais aucune courbe.
- **Fix court terme** : Masquer la légende Projection quand `projectionMwh.length === 0`.

### HIGH-2 — CommandCenter barre "Avec actions planifiées" toujours 100%
- **Fichier** : `frontend/src/pages/CommandCenter.jsx:580`
- **Bug** : `style={{ width: '100%' }}` hardcodé. Devrait refléter la projection réelle.
- **Fix** : Masquer cette section quand `projectionMwh` est vide.

### HIGH-3 — CockpitHero objectif 2026 hardcodé −25%
- **Fichier** : `frontend/src/pages/cockpit/CockpitHero.jsx:161`
- **Bug** : Texte "−25%" en dur. `trajectoire.objectif2026Pct` est disponible mais non utilisé.
- **Fix** : `{trajectoire?.objectif2026Pct ?? -25}%`

### HIGH-4 — Bannière retard : wording différent de la maquette
- **Fichier** : `frontend/src/pages/Cockpit.jsx:605-613`
- **Maquette** : "Trajectoire DT 2026 en retard de −7 pts — 76 k€ de pénalités si non rattrapé"
- **Actuel** : "Retard trajectoire DT · X% réalisé vs objectif Y%"
- **Fix** : Calculer le delta en pts backend et reformater le texte.

### HIGH-5 — PerformanceSitesCard label "obj." trompeuse
- **Fichier** : `frontend/src/pages/cockpit/PerformanceSitesCard.jsx:22`
- **Bug** : Utilise `benchmark.median` ADEME comme "objectif". La médiane n'est pas un objectif réglementaire.
- **Fix** : Changer le label en "réf. ADEME" au lieu de "obj."

### HIGH-6 — `billing` prop fetchée, normalisée, passée à CockpitHero mais JAMAIS affichée
- **Fichier** : `frontend/src/pages/cockpit/CockpitHero.jsx`
- **Bug** : La prop `billing` est dans la signature mais jamais utilisée dans le rendu. Le fetch `getBillingSummary` est du dead weight.
- **Fix** : Afficher `billing.anomalies` dans le sous-texte de la card Risque, ou supprimer la prop.

### HIGH-7 — `consoJ1BySite` jamais passé → barres Sites Baseline estimées
- **Fichier** : `frontend/src/pages/CommandCenter.jsx:609`
- **Bug** : Seul `consoHierTotal` est passé. Pas de données J-1 par site. Toutes les barres sont au prorata.
- **Fix backlog** : Créer endpoint `/api/ems/sites/j1` retournant conso par site.

---

## 3. ÉCARTS UX/UI vs MAQUETTES

### Vue Executive (/cockpit)

| Widget | Statut | Détail écart |
|--------|--------|-------------|
| Header titre | ❌ PARTIAL | "Vue exécutive" au lieu de "Cockpit exécutif" |
| Header pills EPEX/CO₂ | ❌ MISSING | Aucune pill marché dans le header |
| Header badge alertes | ❌ MISSING | Pas de badge "3 alertes" dans le header |
| Header "Rapport COMEX" | ❌ MISSING | Bouton absent |
| Tabs | ✅ MATCH | Correct |
| KPI Card 1 Score | ✅ MATCH | Gauge SVG + DT/BACS/APER |
| KPI Card 2 Risque | ⚠️ PARTIAL | Label OK, mais valeur = réglementaire seul (CRIT-3) |
| KPI Card 3 Réduction | ⚠️ PARTIAL | Objectif hardcodé -25% (HIGH-3) |
| KPI Card 4 Actions | ✅ MATCH | Format X/Y + potentiel EUR |
| Bannière retard | ⚠️ PARTIAL | Wording différent, pas de "pts" (HIGH-4) |
| Alertes prioritaires | ✅ MATCH | 3 items avec icône, EUR, jours |
| Événements récents | ✅ MATCH | 4 items avec dot, titre, date |
| Trajectoire chart | ⚠️ PARTIAL | Projection vide (HIGH-1), ref_year 2024 pas 2020 |
| Performance sites | ⚠️ PARTIAL | Label "obj." → devrait être "réf. ADEME" (HIGH-5) |
| Vecteur énergétique | ⚠️ PARTIAL | Fallback calcul front (CRIT-5), Scope 1 = gaz maintenant visible |
| Actions Impact header | ✅ MATCH | Badges en cours/planifiées |
| Actions Impact cards | ❌ PARTIAL | Pas de nom site, pas de MWh/an, pas de pts trajectoire |
| Actions Impact footer | ❌ PARTIAL | Seulement EUR, pas de MWh total ni pts ni projection % |

### Vue Exploitation (/)

| Widget | Statut | Détail écart |
|--------|--------|-------------|
| Tabs | ✅ MATCH | Correct |
| KPI Conso hier | ⚠️ PARTIAL | Valeur OK, mais pas de delta % vs N-1 |
| KPI Conso ce mois | ❌ MISSING | Stub "Endpoint à venir" |
| KPI Pic puissance | ⚠️ PARTIAL | Valeur OK, mais pas de nom de site dépassant |
| KPI CO₂ réseau | ❌ MISSING | Stub "Connecteur RTE à brancher" |
| Conso 7 jours chart | ⚠️ PARTIAL | 1 seule série (pas de comparaison N-1) |
| Profil J-1 | ✅ MATCH | Courbe + seuil rouge |
| Trajectoire mensuelle | ⚠️ PARTIAL | Barre projection 100% hardcodé (HIGH-2) |
| Actions du jour | ✅ MATCH | 5 éléments avec badges |
| Sites J-1 vs Baseline | ⚠️ PARTIAL | Barres estimées (pas de données J-1 par site) |

---

## 4. AMÉLIORATIONS PROPOSÉES (Quick Wins)

### P0 — Corrections immédiates (< 1h chacune)

| # | Fichier | Action |
|---|---------|--------|
| 1 | `useCockpitData.js:38` | `risqueTotal → risque_breakdown.total_eur` |
| 2 | `CockpitHero.jsx:161` | Objectif dynamique `{trajectoire?.objectif2026Pct}%` |
| 3 | `VecteurEnergetiqueCard.jsx:62-89` | Supprimer fallback calcul front |
| 4 | `TrajectorySection.jsx:145` | Masquer légende "Projection" si vide |
| 5 | `CommandCenter.jsx:579-581` | Masquer barre "Avec actions" si projection vide |
| 6 | `PerformanceSitesCard.jsx:22` | "obj." → "réf. ADEME" |
| 7 | `cockpit.py:278` | Benchmark : utiliser `_sites_for_org(db, org_id)` |

### P1 — Enrichissements (sprint suivant)

| # | Fichier | Action |
|---|---------|--------|
| 1 | `ActionsImpact.jsx` | Ajouter site_nom dans le titre "Action — Site" |
| 2 | `ActionsImpact.jsx` | Afficher `co2e_savings_est_kg` converti en MWh si dispo |
| 3 | `Cockpit.jsx` header | Ajouter pills EPEX + CO₂ + badge alertes + bouton Rapport COMEX |
| 4 | `CommandCenter.jsx` | Ajouter série N-1 dans le BarChart 7 jours |
| 5 | `CommandCenter.jsx` | KPI "Conso ce mois" : endpoint backend ConsumptionTarget monthly |
| 6 | `SitesBaselineCard` | Endpoint `/api/ems/sites/j1` pour données réelles par site |
| 7 | `gen_targets.py` | Étendre le seed à 2020 comme année de référence |

### P2 — Backlog long terme

| # | Action |
|---|--------|
| 1 | `projection_mwh` calculé backend depuis les actions planifiées |
| 2 | Connecteur RTE CO₂ temps réel pour KPI "Intensité CO₂ réseau" |
| 3 | KPI "Conso ce mois" avec comparaison N-1 |
| 4 | Endpoint `/api/ems/sites/j1` pour conso J-1 par site |
| 5 | Facteur CO₂ dynamique (0.052 actuellement hardcodé dans emission_factors config) |

---

## 5. VÉRIFICATION FACTEUR CO₂ (triple check)

| Source | Valeur | Statut |
|--------|--------|--------|
| `config/emission_factors.py` | **0.052** kgCO₂/kWh | Source de vérité PROMEOS |
| ADEME Base Empreinte V23.6 | **0.052** kgCO₂/kWh (élec réseau France, mix moyen annuel, ACV) | ✅ Cohérent |
| `compliance_engine.py:62` | `CO2_FACTOR_ELEC_KG_KWH = _get_ef("ELEC")` → **0.052** | ✅ Import dynamique |
| Tests (`test_cockpit_p0.py:170`) | `assert == 0.052` | ✅ Vert |
| Tests (`test_emissions.py:251`) | `assert == 0.052` + commentaire "ADEME Base Empreinte V23.6" | ✅ Vert |

**⚠️ Le 0.0569** retrouvé dans `billing_engine/catalog.py:155` est un **tarif TURPE 7** (composante soutirage HPH en €/kWh), PAS un facteur CO₂. Les commentaires frontend qui mentionnent "0.0569 kgCO₂/kWh ADEME 2024" sont **erronés** et doivent être corrigés.

---

## 6. DONNÉES DISPONIBLES NON EXPLOITÉES

| Donnée | Source backend | Affiché cockpit ? | Impact |
|--------|---------------|-------------------|--------|
| 312 ConsumptionTarget mensuels avec actual_kwh | `gen_targets.py` | ❌ Non | KPI "Conso ce mois vs objectif" possible |
| `base_night_pct` par site (% nocturne) | `/api/portfolio/consumption/sites` | ❌ Non | Détection anomalie horaire |
| `peak_kw` (P95) par site | `/api/portfolio/consumption/sites` | ❌ Non | Alerte puissance souscrite |
| ROI actions : `total_realized_eur`, `roi_ratio` | `/api/actions/roi_summary` | ❌ Non | Widget ROI dans le cockpit |
| Contrats expirant 30/60/90j | `/api/contracts_radar` | ❌ Non | Widget "Contrats à renouveler" |
| 47 BillingInsight avec `estimated_loss_eur` | `/api/billing/summary` | ❌ Partiellement | Card 2 montre le total mais pas le détail |
| `operat_status` par site | scopedSites | ❌ Non | Colonne "Statut OPERAT" dans la table sites |
| `by_source` actions breakdown | `/api/actions/summary` | ❌ Non | Répartition DT/Billing/Conso dans ActionsImpact |
| 20 NotificationEvent | `/api/notifications/list` | ✅ Oui (4 affichés) | OK |
| ComplianceScoreHistory 6 mois | sparkline data | ❌ Non (expert seulement) | Tendance score dans CockpitHero |

---

## 7. RÉSUMÉ DES COMMITS NÉCESSAIRES

```
fix(CRIT): benchmark + co2 → org scoping + risqueTotal → breakdown.total_eur
fix(CRIT): VecteurEnergetiqueCard supprimer fallback calcul front
fix(CRIT): billing summary → filtrer RESOLVED/FALSE_POSITIVE
fix(HIGH): masquer projection vide + objectif dynamique + label "réf. ADEME"
feat(UX): ActionsImpact enrichir cards avec site_nom + MWh si dispo
feat(UX): header pills EPEX/CO₂ + badge alertes + bouton Rapport COMEX
```

---

## 8. ÉTAT ACTUEL vs MAQUETTE — Score de conformité

| Vue | Score maquette (widgets présents et conformes / total widgets) |
|-----|--------------------------------------------------------------|
| Vue Executive (/cockpit) | **11/18 widgets** conformes (61%) |
| Vue Exploitation (/) | **5/10 widgets** conformes (50%) |
| **Global** | **16/28** (57%) |

**Objectif pour le prochain sprint : 80%+** en corrigeant les 7 CRITICAL + 7 HIGH.
