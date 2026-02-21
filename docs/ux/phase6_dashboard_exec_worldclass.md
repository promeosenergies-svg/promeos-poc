# Phase 6 — Dashboard & Executive World-Class

## Objectif
Trouver le juste milieu couleur: plus vivant que "hopital blanc", mais sans saturation.
Modele "neutral-first + accents maitrises".

## Audit (avant)

### CommandCenter.jsx
- 3 MetricCards blanches identiques, seul signal = tiny StatusDot
- Carte priorite: fond blanc, icone grise, aucune mise en avant
- Couverture donnees masquee (expert only)
- Pas d'etat "tout va bien"
- EUR sans locale FR

### Cockpit.jsx
- Pas de hero band pour les actions prioritaires
- Maturite ring tout gris
- Pas de mode 1 site (meme layout pour 1 ou 36 sites)
- Table hover neutre

### NotificationsPage.jsx
- Filtres scrollent hors de l'ecran
- Pas de meta synchro visible
- Densite table un peu large
- Hover basic sur les lignes

## Palette (contrainte respectee)

| Role             | Couleur      | Usage                                |
|------------------|-------------|--------------------------------------|
| Accent principal | Blue (primary) | Conformite, Sites, Maturite       |
| Accent secondaire| Indigo       | Alertes, Executive CTA               |
| Accent tertiaire | Amber        | Risque, attention, montants EUR      |
| Rouge/Vert       | Micro-signals| StatusDot uniquement, jamais en aplat|

## Tokens UI (colorTokens.js)

- `KPI_ACCENTS`: conformite, risque, alertes, sites, maturite, neutral
  - Chaque entree: accent, iconBg, iconText, border, tintBg, tintText, ringClass
- `SEVERITY_TINT`: critical, high, warn, medium, info, low, neutral
  - Chaque entree: dot, chipBg, chipText, chipBorder, label (FR)
- `ACCENT_BAR`: primary, amber, indigo, gray
- `HERO_ACCENTS`: priority, success, executive

## MetricCard v3

- Prop `accent`: cle dans KPI_ACCENTS -> barre laterale 3px + icon pill teinte
- Prop `icon`: composant Lucide affiche dans le pill
- Backward-compatible: sans accent/icon, rendu identique a v2

## Changements par page

### CommandCenter
1. Header: trust signals compacts (heure synchro + couverture %) dans les actions
2. KPI Row: 3 MetricCards avec accents (conformite=blue, risque=amber, alertes=indigo)
3. Priority #1: carte premium avec ring/bg subtle (HERO_ACCENTS.priority)
4. "Tout sous controle": carte emeraude quand isAllClear (100% + 0 risk + 0 alerts)
5. normalizeDashboardModel(): empeche contradictions KPI
6. Severity chips FR (tint-only, pas de badges pleins)
7. Table sites: hover bg-blue-50/40, risque en text-amber-700

### Cockpit
1. KPIs avec accents (sites=blue, conformite=blue, risque=amber) + Maturite barre bleue
2. Hero band indigo: "N sites non conformes" + CTA "Plan d'action"
3. Mode 1 site: 3 cartes insights (statut, risque, conso), pas de table sites
4. Ring maturite: couleur blue au lieu de gray
5. Table: hover accent, risque amber

### NotificationsPage
1. Filtres sticky (top-0 z-10 bg-white/95 backdrop-blur)
2. Sync meta: heure + nombre de sources a cote du bouton
3. KPI summary avec accents (risque=amber, alertes=indigo, conformite=blue)
4. Table: hover bg-blue-50/40, new rows bg-blue-50/30
5. Impact EUR en text-amber-700, message en line-clamp-1
6. Boutons action: hover blue (pas gray)

## Coherence donnees

`normalizeDashboardModel({ kpis, topActions, alertsCount })`:
- Si pctConf=100 -> force risque=0, nonConformes=0, aRisque=0
- Si 0 sites a risque -> force risque=0
- Si isAllClear -> topActions=[] (pas d'actions fantomes)

## Tests (13 nouveaux)

### CommandCenter.test.js
- normalizeDashboardModel: 6 tests (allClear, alerts, risk, force risque, force sites, preserve alerts)
- colorTokens integrity: 7 tests (keys, fields, severity FR labels, accent bar, hero)

## QA

- `npm run build`: 0 errors
- `npx vitest run`: 195 passed (8 files)
- Pas de console.error
- Backward-compatible (MetricCard v3 sans accent = identique a v2)

## DoD

- [x] Juste milieu atteint: accent bars + icon pills + hero bands, pas de saturation
- [x] Couleurs stables et semantiques via colorTokens.js
- [x] Zero incoherence KPI/priorites/listes (normalizeDashboardModel)
- [x] Build + tests OK
- [x] Doc redigee
