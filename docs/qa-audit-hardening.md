# QA SCRIPT — Parcours de Navigation PROMEOS

> Post-audit hardening — 2026-02-18
> Pre-requis : `npm run build` clean, `npx vitest run` >= 935 tests green

---

## Commandes de validation rapide

```bash
# 1. Tests unitaires (doit afficher 0 failed)
cd frontend && npx vitest run

# 2. Build production (doit afficher "built in" sans erreur)
npm run build

# 3. Guard tests specifiques (anti-regression audit)
npx vitest run src/pages/__tests__/RoutingSmoke.test.js

# 4. Tests NavRegistry
npx vitest run src/layout/__tests__/NavRegistry.test.js

# 5. Tests Cockpit V2
npx vitest run src/pages/__tests__/DashboardV2.test.js src/pages/__tests__/CockpitV2.test.js
```

---

## Parcours de navigation manuelle

### 1. Cockpit — Tableau de bord (route `/`)

- [ ] Page charge sans spinner infini
- [ ] Titre "Tableau de bord" visible dans le header
- [ ] BriefingHeroCard affiche un message contextuel
- [ ] 3 MetricCards (conformite, actions, alertes) avec valeurs numeriques
- [ ] EssentialsRow present (badges couverture donnees / perimetre)
- [ ] Bouton "Vue executive" navigue vers `/cockpit`
- [ ] ModuleLaunchers (4-5 cartes modules) cliquables

### 2. Cockpit — Vue executive (route `/cockpit`)

- [ ] Page charge sans spinner infini
- [ ] Titre "Vue executive" visible
- [ ] ExecutiveSummaryCard avec texte genere
- [ ] ExecutiveKpiRow (4 KPIs en ligne)
- [ ] BriefingHeroCard + ConsistencyBanner
- [ ] WatchlistCard + OpportunitiesCard
- [ ] EssentialsRow en bas de page

### 3. Redirect `/cockpit-2min`

- [ ] Naviguer vers `/cockpit-2min` dans la barre d'adresse
- [ ] Redirect automatique vers `/cockpit` (pas de 404)

### 4. Operations — Conformite (route `/conformite`)

- [ ] Page charge, titre "Conformite" visible
- [ ] Scanner des decrets/articles avec detail panel
- [ ] Sidebar highlight sur module "Operations" (teinte emerald)

### 5. Operations — Plan d'actions (route `/actions`)

- [ ] Liste des actions avec statut
- [ ] Creation d'action possible

### 6. Analyse — Consommations (route `/consommations`)

- [ ] Tabs: Courbes, Tunnel, Objectifs, HPHC, Gaz
- [ ] Tab Courbes : graphe Recharts avec donnees
- [ ] Tab Gaz : EmptyState avec CTA si pas de donnees gaz
- [ ] Barre de filtres sticky avec selecteur de granularite

### 7. Analyse — Performance (route `/monitoring`)

- [ ] KPI cards en haut
- [ ] Lien "Explorer" navigue vers `/consommations/explorer` (PAS `/consumption-explorer`)
- [ ] Graphes de performance

### 8. Analyse — Diagnostic (route `/diagnostic-conso`)

- [ ] Selection de site filtre les insights
- [ ] Pas de crash (normalizeId fonctionne)

### 9. Marche — Facturation (route `/bill-intel`)

- [ ] Page charge (mode expert requis)
- [ ] Teinte amber dans le sidebar

### 10. Marche — Achats energie (route `/achat-energie`)

- [ ] Label "Achats energie" avec accent dans la nav
- [ ] Page charge avec onglets

### 11. Admin — Patrimoine (route `/patrimoine`)

- [ ] Liste de sites
- [ ] Clic sur site → detail sans crash
- [ ] Message "non trouve" avec accent si site inexistant

### 12. Admin — Utilisateurs (route `/admin/users`)

- [ ] Titre "Utilisateurs" (pas "Users")
- [ ] Requiert admin

### 13. Admin — Roles (route `/admin/roles`)

- [ ] Titre "Roles & Permissions" avec accent
- [ ] "11 roles systeme" avec accents
- [ ] Acces refuse si non-admin → message "Acces refuse" avec accents

### 14. Admin — Affectations (route `/admin/assignments`)

- [ ] Titre "Affectations" (pas "Assignments")
- [ ] Stepper : Utilisateur / Perimetre / Role / Confirmer
- [ ] Bouton "Assigner un role" avec accent

### 15. Admin — Veille (route `/watchers`)

- [ ] Page charge avec watchers actifs
- [ ] Modal revision : titre "Reviser l'evenement" avec accents

### 16. Login (route `/login`)

- [ ] "Cockpit energetique" avec accent
- [ ] "Demo : sophie@atlas.demo" avec accent et espace

---

## Verification z-index

- [ ] Ouvrir sidebar (z-30) → ne couvre pas le header (z-10 mais au-dessus visuellement par position)
- [ ] Ouvrir un modal (z-50) → couvre sidebar et header
- [ ] Tooltip sur un graphe (z-9999) → visible au-dessus du modal si present
- [ ] Dropdown de filtre (z-40) → au-dessus du contenu, sous les modals

---

## Verification scope

- [ ] Changer de perimetre dans le ScopeContext (selecteur organisation)
- [ ] Tableau de bord : KPIs se rafraichissent avec les sites du perimetre
- [ ] Consommations : donnees filtrées par perimetre
- [ ] Conformite : articles filtres par perimetre

---

## Points de vigilance (P2 non corriges)

| Point | Impact | Ou verifier |
|-------|--------|-------------|
| `ConsommationsUsages.jsx` ImportWizard scope | Donnees hors perimetre dans import | Import de conso → assistant → liste de sites |
| Couleurs hex charts | Visuel incoherent si theme change | Graphes Recharts (MonitoringPage, Explorer) |
| Route `/status` orpheline | Page accessible mais invisible | Taper `/status` dans la barre d'adresse |

---

## Criteres de validation

| Critere | Seuil | Commande |
|---------|-------|----------|
| Tests verts | >= 935 | `npx vitest run` |
| Build clean | 0 erreurs | `npm run build` |
| Guard tests | 5/5 green | `npx vitest run RoutingSmoke` |
| Labels FR | 0 anglais dans nav | Guard test blacklist |
| Routes valides | 0 route cassee | Guard test coverage |
