# Audit UX/UI — Cockpit World-Class vs Maquettes Cibles

**Date** : 2026-03-23
**Branche** : `feat/cockpit-world-class` (8 commits)
**Methode** : Analyse code source vs 3 maquettes cibles fournies

---

## Legende

| Icone | Statut |
|-------|--------|
| OK | Implemente et conforme |
| PARTIEL | Implemente mais incomplet |
| MANQUANT | Absent du code |

---

## 1. VUE EXECUTIVE (/cockpit) — Maquettes 1 & 2

### 1.1 En-tete page

| Element | Maquette | Code actuel | Statut |
|---------|----------|-------------|--------|
| Titre "Cockpit executif" | Affiche avec EPEX + CO2 badges | PageShell title "Vue executive" | OK |
| Tabs "Vue executive / Tableau de bord" | 2 onglets cliquables | Pas de tabs — pages separees | MANQUANT |
| Bouton "Rapport COMEX" | En haut a droite | Non implemente | MANQUANT |

**Pour y arriver** :
- Ajouter un composant `CockpitTabs` en haut du layout avec 2 onglets qui naviguent entre `/cockpit` et `/`
- Ajouter un bouton "Rapport COMEX" dans le header de `PageShell` (utiliser le slot `actions` du PageShell existant)

### 1.2 CockpitHero — Bloc hero 4 KPIs

| Element | Maquette | Code actuel | Statut |
|---------|----------|-------------|--------|
| Gauge score sante (73) | Demi-cercle + "Satisfaisant" | Implemente (SVG gauge) | OK |
| Sous-texte gauge "DT 45% BACS 30% APER 25%" | Breakdown ponderation | Absent — affiche seulement date + source | MANQUANT |
| KPI "Risque financier 142 kEUR" | Bloc amber a droite | Implemente (risque breakdown) | OK |
| KPI "Reduction DT cumulee -18%" | Valeur + objectif | Implemente | OK |
| KPI "Actions en cours 8/23" | Compteur + "+38 kEUR/an potentiel" | ABSENT — remplace par "Intensite energetique" (placeholder) | MANQUANT |
| Sous-label "penalites + anomalies billing" | Contextualise le risque | Absent | MANQUANT |
| Sous-label "Objectif 2026: -25% billing retard" | Contextualise la reduction | Affiche "Objectif 2026 : -25 %" sans "billing retard" | PARTIEL |

**Pour y arriver** :
- Remplacer le KPI "Intensite energetique" (card 2, placeholder '—') par **"Actions en cours"** avec `actions.enCours` / `actions.total` + `fmtEur(actions.potentielEur)` en sous-texte
- Garder "CO2 evite" en card 3 (placeholder OK pour maintenant)
- Ajouter sous le gauge : `DT ${complianceMeta?.framework_weights?.tertiaire_operat*100 ?? 45}% · BACS ${...bacs*100 ?? 30}% · APER ${...aper*100 ?? 25}%` — les poids viennent de `complianceMeta` (deja importe dans Cockpit.jsx via `useComplianceMeta`)
- Enrichir le sous-label risque avec "penalites + anomalies billing"

### 1.3 Banniere retard trajectoire

| Element | Maquette | Code actuel | Statut |
|---------|----------|-------------|--------|
| Banniere amber "Trajectoire DT 2026 en retard" | Texte + "76 kEUR si non rattrape" + CTA | Implemente (banniere conditionnelle) | PARTIEL |
| Montant penalite affiche | "76 kEUR si non rattrape" | Absent — affiche uniquement % | MANQUANT |
| Texte "Actions P0 a lancer avant le 30 avril" | Deadline actionnable | Absent | MANQUANT |

**Pour y arriver** :
- Enrichir le texte de la banniere avec `fmtEur(cockpitKpis.risqueBreakdown?.reglementaire_eur)` + "si non rattrape"
- Ajouter la date butoir (hardcode "30 avril" ou calculer depuis `trajectoire.jalons[0].annee`)

### 1.4 Sections manquantes /cockpit

| Section | Maquette | Code actuel | Statut |
|---------|----------|-------------|--------|
| **ALERTES PRIORITAIRES** | 3 items : OPERAT Q1, Factures anomalies, Contrat EDF | Aucun composant | MANQUANT |
| **EVENEMENTS RECENTS** | 4 items avec dots colores + timestamps | Aucun composant | MANQUANT |
| **PERFORMANCE PAR SITE — KWH/M2** | 5 barres horizontales avec objectifs | SiteBar existe dans TrajectorySection mais pas de section standalone | PARTIEL |
| **REPARTITION PAR VECTEUR ENERGETIQUE** | Electricite/Gaz/Autres barres + CO2 total/scope2/scope1 | Aucun composant | MANQUANT |

**Pour y arriver** :

#### Alertes Prioritaires
- Creer `frontend/src/pages/cockpit/AlertesPrioritaires.jsx`
- Source de donnees : combiner `getNotificationsSummary()` (deja importe dans Cockpit.jsx) + actions P0 ouvertes
- 3 items max avec : icone source (DT/Billing/Achat), titre, sous-texte (delai, montant), badge jours restants
- Pattern : similaire a `TodayActionsCard` dans CommandCenter

#### Evenements Recents
- Creer `frontend/src/pages/cockpit/EvenementsRecents.jsx`
- Source : `getNotificationsList({ limit: 4 })` (existe dans `api/cockpit.js`)
- 4 items avec dot colore (severity), texte, date relative
- Pattern : similaire a `buildWatchlist()` dans dashboardEssentials

#### Performance par Site (standalone)
- Le composant `SiteBar` existe dans TrajectorySection — l'extraire en composant reutilisable
- Creer `frontend/src/pages/cockpit/PerformanceSitesCard.jsx`
- Source : `scopedSites` (deja dans useScope) avec `conso_kwh_an` et `surface_m2`
- Afficher kWh/m2 reel vs objectif (benchmark ADEME disponible via `/api/cockpit/benchmark`)

#### Repartition par Vecteur Energetique
- Creer `frontend/src/pages/cockpit/VecteurEnergetiqueCard.jsx`
- Source : `/api/cockpit/co2` (existe deja dans `backend/routes/cockpit.py:305`)
- Afficher : Electricite (MWh, %), Gaz naturel (MWh, %), Autres (MWh, %)
- Sous-section CO2 : Total tCO2eq + Scope 2 (elec) + Scope 1 (gaz)

### 1.5 TrajectorySection

| Element | Maquette | Code actuel | Statut |
|---------|----------|-------------|--------|
| Toggle KWH / % REDUCTION | 2 boutons pills | Implemente | OK |
| Legende "Reel HELIOS (5 sites)" | Avec metadata | Legende generique "Reel" | PARTIEL |
| Courbe 3 series | Bleu/rouge pointille/vert | Implemente | OK |
| Jalons texte | 2026 -25% etc. | Implemente | OK |
| "Ref. 2020 Surface : 8 780 m2" | En bas a droite | Implemente | OK |

**Pour y arriver** :
- Enrichir les labels legende : "Reel" → `Reel HELIOS (${scopedSites.length} sites)` et "Objectif DT" → `Objectif DT (−40% 2030)`
- Passer `scopedSites.length` en prop ou via le hook

### 1.6 ActionsImpact

| Element | Maquette | Code actuel | Statut |
|---------|----------|-------------|--------|
| Badge P0/P1 | Cercle colore | Implemente | OK |
| Titre + description 2 lignes | Titre + sous-texte detaille | Titre seul (truncate) | PARTIEL |
| Savings MWh/an a droite | "-42 MWh/an" | Affiche EUR uniquement | PARTIEL |
| "+X pts trajectoire" | Sous-texte bleu | Absent (champ backend manquant) | MANQUANT |
| Footer aggregate | "121 MWh/an +7,3 pts trajectoire Atteindrait -25,3% fin 2026" | Footer simplifie (EUR seulement) | PARTIEL |
| Lien "Voir toutes les actions" | CTA en bas | Implemente | OK |

**Pour y arriver** :
- Ajouter `action.description` ou `action.rationale` en 2e ligne sous le titre (champ existe dans API)
- Afficher `action.co2e_savings_est_kg` converti en MWh (si dispo) a cote de l'EUR — mais **attention** : la conversion CO2→MWh est un calcul metier interdit cote front. Il faut que le backend fournisse `impact_kwh_an` directement
- Pour "+X pts trajectoire" : necessite un champ backend `trajectoire_contribution_pct` sur ActionItem (backlog P2)
- Footer : enrichir avec le total `impact_kwh_an` agrege quand le backend le fournira

---

## 2. VUE EXPLOITATION (/) — Maquette 3

### 2.1 KPIs J-1 (4 cards)

| KPI | Maquette | Code actuel | Statut |
|-----|----------|-------------|--------|
| "Conso hier (J-1) 2,4 MWh" | Valeur + "-8% vs J-1 N-1 5 sites" | Valeur affichee, sous-texte simplifie | PARTIEL |
| "Conso ce mois (mars) 54,2 MWh" | Valeur + "-6% vs mars N-1" | Hardcode "—" + "Endpoint a venir" | MANQUANT |
| "Pic puissance J-1 42 kW" | Amber si seuil depasse + "Lyon Bureaux" | Accent warn si >40, pas de nom site | PARTIEL |
| "Intensite CO2 reseau 62 gCO2/kWh" | Valeur + "RTE J-1 Nuit favorable" | Affiche "—" + "Connecteur RTE a brancher" | MANQUANT |

**Pour y arriver** :

#### KPI 1 — Comparaison J-1 N-1
- Le hook `useCommandCenterData` doit fetcher les donnees de J-1 de l'annee precedente
- Ajouter un appel `getEmsTimeseries` supplementaire avec `date_from/date_to` decale de 365 jours
- Calculer le delta % **cote backend** (creer endpoint) ou accepter une transformation de presentation locale

#### KPI 2 — Conso ce mois
- Backend : creer `GET /api/cockpit/conso-mensuelle` ou enrichir `/api/cockpit` avec `conso_mois_kwh`
- Source : `SUM(MeterReading.value_kwh)` pour le mois courant, filtre freq granulaires
- Front : afficher avec `fmtKwh()`

#### KPI 3 — Nom du site en depassement
- Le hook doit identifier quel site a le pic max (si mode multi-site)
- Enrichir `kpisJ1` avec `picSiteNom` depuis les series EMS (la serie par site, pas l'agregat)

#### KPI 4 — CO2 reseau
- Necessite l'integration du connecteur RTE eco2mix
- API : `GET /api/ems/co2-reseau` qui appelle l'API RTE
- Fallback : afficher "—" (actuel, correct)

### 2.2 Graphiques

| Element | Maquette | Code actuel | Statut |
|---------|----------|-------------|--------|
| Conso 7j — barres "Cette semaine" vs "Semaine N-1" | 2 series barres | 1 serie AreaChart | PARTIEL |
| Profil J-1 — courbe + seuil rouge | Area + ReferenceLine | Implemente | OK |

**Pour y arriver** :
- Transformer l'AreaChart 7j en **BarChart** avec 2 series (cette semaine + N-1)
- Fetcher les donnees N-1 en parallele (appel EMS supplementaire decale de 7 jours)
- Utiliser `recharts.BarChart` avec `<Bar>` au lieu de `<AreaChart>` + `<Area>`

### 2.3 Sections supplementaires

| Section | Maquette | Code actuel | Statut |
|---------|----------|-------------|--------|
| "ACTIONS DU JOUR 3 URGENTES" | Card avec 3 actions detaillees | TodayActionsCard (existant) | PARTIEL |
| "SITES — CONSO J-1 VS BASELINE (KWH/J)" | 5 barres avec % vs baseline | Table "Sites a risque" (different) | MANQUANT |

**Pour y arriver** :

#### Sites J-1 vs Baseline
- Creer `frontend/src/pages/cockpit/SitesBaselineCard.jsx`
- Source : combiner `weekSeries` par site (fetcher en mode `superpose` au lieu d'`aggregate`) + `ConsumptionTargets` mensuels
- Afficher : nom site, barre coloree (vert si < baseline, amber si > baseline), valeur kWh + "% vs baseline"
- La baseline journaliere = `target_kwh_mensuel / nb_jours_mois` (transformation de presentation documentee)

---

## 3. TABLEAU RECAPITULATIF DES ECARTS

### Priorite P0 — Bloquants pour la demo

| # | Ecart | Composant a creer/modifier | Source backend |
|---|-------|---------------------------|----------------|
| 1 | KPI "Actions en cours 8/23" absent du Hero | Modifier `CockpitHero.jsx` card 2 | `useCockpitData().actions` (existe) |
| 2 | Sous-texte gauge "DT 45% BACS 30% APER 25%" | Modifier `CockpitHero.jsx` | `complianceMeta` (existe dans Cockpit.jsx) |
| 3 | Banniere retard — montant penalite | Modifier `Cockpit.jsx` banniere | `risqueBreakdown.reglementaire_eur` (existe) |

### Priorite P1 — Sections manquantes

| # | Ecart | Composant a creer | Source backend |
|---|-------|-------------------|----------------|
| 4 | Alertes Prioritaires | `AlertesPrioritaires.jsx` | `getNotificationsList` + actions P0 |
| 5 | Evenements Recents | `EvenementsRecents.jsx` | `getNotificationsList({ limit: 4 })` |
| 6 | Repartition Vecteur Energetique + CO2 | `VecteurEnergetiqueCard.jsx` | `/api/cockpit/co2` (existe backend) |
| 7 | Performance Sites standalone | `PerformanceSitesCard.jsx` | `/api/cockpit/benchmark` (existe backend) |
| 8 | Sites J-1 vs Baseline | `SitesBaselineCard.jsx` | EMS timeseries + ConsumptionTargets |
| 9 | Conso 7j barres comparatives N-1 | Modifier `CommandCenter.jsx` | EMS timeseries N-1 |
| 10 | Conso ce mois KPI | Backend + hook enrichi | Nouvel endpoint ou enrichir /cockpit |

### Priorite P2 — Enrichissements

| # | Ecart | Action | Prerequis |
|---|-------|--------|-----------|
| 11 | ActionsImpact — description 2 lignes | Afficher `rationale` sous titre | Champ existe dans API |
| 12 | ActionsImpact — MWh/an + pts trajectoire | Ajouter `impact_kwh_an` au modele | Backend model change |
| 13 | ActionsImpact — footer agrege | Enrichir footer avec MWh total | Depend de #12 |
| 14 | TrajectorySection — legende enrichie | Ajouter "(5 sites)" et "(-40% 2030)" | Passer count en prop |
| 15 | KPIs J-1 — comparaison N-1 | Fetcher donnees N-1 | Appel EMS supplementaire |
| 16 | KPIs J-1 — nom site pic | Identifier site max | EMS mode superpose |
| 17 | Tabs Vue executive / Tableau de bord | Creer `CockpitTabs.jsx` | Navigation |
| 18 | Bouton "Rapport COMEX" | Ajouter dans header | PDF export existant |
| 19 | CO2 reseau RTE | Connecteur RTE eco2mix | API externe |

---

## 4. ORDRE D'EXECUTION RECOMMANDE

### Sprint immediat (P0 — 1h)
1. Modifier `CockpitHero.jsx` : remplacer card "Intensite" par "Actions en cours"
2. Modifier `CockpitHero.jsx` : ajouter sous-texte gauge avec poids DT/BACS/APER
3. Modifier `Cockpit.jsx` banniere : ajouter montant penalite

### Sprint suivant (P1 — 4h)
4. Creer `AlertesPrioritaires.jsx` + `EvenementsRecents.jsx`
5. Creer `VecteurEnergetiqueCard.jsx` (endpoint `/api/cockpit/co2` existe)
6. Creer `PerformanceSitesCard.jsx` (endpoint `/api/cockpit/benchmark` existe)
7. Creer `SitesBaselineCard.jsx` pour CommandCenter
8. Enrichir Conso 7j avec barres comparatives N-1
9. Backend : endpoint `conso_mois_kwh`

### Sprint ulterieur (P2)
10-19. Enrichissements detail actions, legende, comparaisons N-1, tabs, COMEX, RTE
