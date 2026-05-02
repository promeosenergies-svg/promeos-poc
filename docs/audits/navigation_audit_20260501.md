---
audit: navigation_phase_0
date: 2026-05-01
branch: claude/refonte-sol2
mode: read-only strict
doctrine_ref: docs/vision/promeos_sol_doctrine.md (v1.0.1 — 2026-04-26)
auteur: Claude Code (Opus 4.7)
---

# AUDIT NAVIGATION PROMEOS — Phase 0 read-only

> **Cible doctrinale (Sol v1.1, prompt mission)** : Dual Cockpit (`/cockpit/jour`
> Briefing 30s · `/cockpit/strategique` Synthèse 3min) + Centre d'action comme
> hub. Ordre rail proposé : **Accueil → Énergie → Conformité → Facturation →
> Achat → [séparateur] → Patrimoine**.
>
> **Réalité auditée** : ordre par défaut `cockpit → conformite → energie →
> patrimoine → achat` (5 modules + admin expert), Facturation cachée comme
> sous-item Patrimoine, libellés legacy "Vue exécutive" / "Tableau de bord"
> persistants dans le panel Cockpit.

---

## 1. TL;DR

1. **Rail à 5 modules visibles + 1 expert** ([NavRegistry.js:201-256](frontend/src/layout/NavRegistry.js#L201-L256)). Architecture stable, registre centralisé propre, role-based ordering en place ([NavRegistry.js:813-841](frontend/src/layout/NavRegistry.js#L813-L841)).
2. **❌ Trou MVP P0 — Facturation noyée sous Patrimoine** : `Bill-Intel` est item #3 de la section Patrimoine ([NavRegistry.js:668-682](frontend/src/layout/NavRegistry.js#L668-L682)) alors que la doctrine §4.4 le pose comme pilier autonome ([promeos_sol_doctrine.md:270-276](docs/vision/promeos_sol_doctrine.md#L270-L276)) et §11 lui assigne une intention propre "Facture, anomalie, contestation → Bill-Intel" ([promeos_sol_doctrine.md:214](docs/vision/promeos_sol_doctrine.md#L214)).
3. **❌ Libellés legacy encore au cœur du panel Cockpit** : "Vue exécutive" + "Tableau de bord" subsistent ([NavRegistry.js:529, 536](frontend/src/layout/NavRegistry.js#L529-L536)) — anti-pattern §6.2 (chemin double sans hiérarchie claire) et viole grammaire éditoriale Sol §5 (titres narratifs : "Briefing du jour" / "Synthèse stratégique" devraient être les libellés primaires).
4. **⚠️ Centre d'action absent du rail** — uniquement accessible via cloche header ([AppShell.jsx:328-332](frontend/src/layout/AppShell.jsx#L328-L332)), raccourci Ctrl+Shift+L ([NavRegistry.js:959-965](frontend/src/layout/NavRegistry.js#L959-L965)) ou route directe `/action-center`. Le prompt mission le qualifie de "hub" → discoverability faible (≥ 2 clics + connaissance du raccourci).
5. **✅ Routes legacy `/dashboard` et `/executive` factorisées et redirigées** ([legacyRedirects.js:26-31](frontend/src/routes/legacyRedirects.js#L26-L31)). Couverture test Vitest présente ([phase3_1_routes_cockpit_dual.test.js](frontend/src/__tests__/phase3_1_routes_cockpit_dual.test.js)) mais E2E Playwright absent. Risque régression à la suppression : faible.

---

## 2. Inventaire (8 dimensions)

### Dimension 1 — Inventaire structurel du rail

#### 1.1 Fichiers définissant la navigation

| Fichier | Rôle | Lignes clés |
|---|---|---|
| [frontend/src/layout/NavRegistry.js](frontend/src/layout/NavRegistry.js) | **Source canonique** : 6 modules, route→module map (53 entrées), tint palette, 8 sections, 15 quick actions, 10 command shortcuts, role-based ordering, hidden pages | [1-1023](frontend/src/layout/NavRegistry.js#L1-L1023) |
| [frontend/src/layout/NavRail.jsx](frontend/src/layout/NavRail.jsx) | **Rail icônes** 64px : module-level, badge logic, expert mode, role ordering | [1-91](frontend/src/layout/NavRail.jsx#L1-L91) |
| [frontend/src/layout/NavPanel.jsx](frontend/src/layout/NavPanel.jsx) | **Panel contextuel** 208px : sections module actif, pins, recents, search patrimoine, progress conformité | [1-680](frontend/src/layout/NavPanel.jsx#L1-L680) |
| [frontend/src/layout/Sidebar.jsx](frontend/src/layout/Sidebar.jsx) | **Orchestrateur** : compose NavRail + NavPanel, fetch badges, gère pins, recents, override module | [1-160](frontend/src/layout/Sidebar.jsx#L1-L160) |
| [frontend/src/layout/AppShell.jsx](frontend/src/layout/AppShell.jsx) | **Layout** : header, ActionCenter slideover (cloche), badge actionCenter | [1-570+](frontend/src/layout/AppShell.jsx) |
| [frontend/src/layout/Breadcrumb.jsx](frontend/src/layout/Breadcrumb.jsx) | Breadcrumbs dérivés ROUTE_SECTION_MAP | [1-9](frontend/src/layout/Breadcrumb.jsx#L1-L9) |
| [frontend/src/ui/CommandPalette.jsx](frontend/src/ui/CommandPalette.jsx) | **⌘K palette** : `ALL_MAIN_ITEMS` + `ALL_NAV_ITEMS` + QUICK_ACTIONS + COMMAND_SHORTCUTS | [11, 160-176](frontend/src/ui/CommandPalette.jsx#L11) |
| [frontend/src/routes/legacyRedirects.js](frontend/src/routes/legacyRedirects.js) | **31 redirects legacy** factorisés Phase 3.bis.a | [15-66](frontend/src/routes/legacyRedirects.js#L15-L66) |

**Pas de mobile bottom-nav** détecté (collapsable panel via `toggleCollapsed` [Sidebar.jsx:62-69](frontend/src/layout/Sidebar.jsx#L62-L69) sert de fallback responsive).

#### 1.2 Modules rail (NAV_MODULES)

[NavRegistry.js:201-256](frontend/src/layout/NavRegistry.js#L201-L256) :

| order | key | label | tint | expertOnly | desc |
|---|---|---|---|---|---|
| 1 | `cockpit` | **Accueil** | blue | false | Synthèse & décisions |
| 2 | `conformite` | Conformité | emerald | false | Obligations réglementaires |
| 3 | `energie` | Énergie | indigo | false | Consommations & performance |
| 4 | `patrimoine` | Patrimoine | amber | false | **Sites, contrats & factures** ← Facturation enfouie |
| 5 | `achat` | Achat | violet | false | Échéances & arbitrage énergie |
| 6 | `admin` | Administration | slate | **true** | Import, utilisateurs et système |

#### 1.3 Sections panel (NAV_SECTIONS)

| Module | Items panel | Source |
|---|---|---|
| Accueil | "Vue exécutive" `/cockpit/strategique` · "Tableau de bord" `/cockpit/jour` | [NavRegistry.js:508-541](frontend/src/layout/NavRegistry.js#L508-L541) |
| Conformité | "Conformité" · "Décret Tertiaire / OPERAT" · "Solarisation (APER)" | [NavRegistry.js:544-592](frontend/src/layout/NavRegistry.js#L544-L592) |
| Énergie | "Consommations" · "Performance énergétique" (badgeKey: monitoring) · "Répartition par usage" · "Diagnostics" · "Flex Intelligence" | [NavRegistry.js:596-642](frontend/src/layout/NavRegistry.js#L596-L642) |
| Patrimoine | "Sites & bâtiments" · "Contrats énergie" · **"Facturation" `/bill-intel`** | [NavRegistry.js:646-684](frontend/src/layout/NavRegistry.js#L646-L684) |
| Achat | "Échéances" `/renouvellements` · "Scénarios d'achat" `/achat-energie` | [NavRegistry.js:687-720](frontend/src/layout/NavRegistry.js#L687-L720) |
| Admin (expert) | Import · Utilisateurs · Veille réglementaire · Système | [NavRegistry.js:723-757](frontend/src/layout/NavRegistry.js#L723-L757) |

#### 1.4 Pages cachées du menu mais searchables

[NavRegistry.js:877-930](frontend/src/layout/NavRegistry.js#L877-L930) — `HIDDEN_PAGES` (6 entrées) :
- `/kb` (Mémobox) · `/segmentation` · `/connectors` · `/usages-horaires` · `/compliance/pipeline` · `/anomalies` (Détection automatique)

#### 1.5 Raccourcis clavier

| Raccourci | Action | Fichier |
|---|---|---|
| `Ctrl+K` | CommandPalette | [NavPanel.jsx:342](frontend/src/layout/NavPanel.jsx#L342) |
| `Ctrl+Shift+A` | Créer une action | [NavRegistry.js:947](frontend/src/layout/NavRegistry.js#L947) |
| `Ctrl+Shift+I` | Importer données | [NavRegistry.js:955](frontend/src/layout/NavRegistry.js#L955) |
| `Ctrl+Shift+L` | **Centre d'actions** | [NavRegistry.js:963](frontend/src/layout/NavRegistry.js#L963) |
| `Ctrl+Shift+C` | Aller au cockpit | [NavRegistry.js:971](frontend/src/layout/NavRegistry.js#L971) |
| `Ctrl+Shift+S` | Changer de site | [NavRegistry.js:979](frontend/src/layout/NavRegistry.js#L979) |
| `Ctrl+Shift+E` | Exporter CSV | [NavRegistry.js:987](frontend/src/layout/NavRegistry.js#L987) |
| `Ctrl+Shift+F` | Voir conformité | [NavRegistry.js:995](frontend/src/layout/NavRegistry.js#L995) |
| `Ctrl+Shift+B` | Voir factures | [NavRegistry.js:1003](frontend/src/layout/NavRegistry.js#L1003) |
| `Ctrl+Shift+X` | Toggle expert | [NavRegistry.js:1011](frontend/src/layout/NavRegistry.js#L1011) |
| `F1` | Aide | [NavRegistry.js:1019](frontend/src/layout/NavRegistry.js#L1019) |

#### 1.6 Desktop vs Mobile

| Aspect | Desktop | Mobile |
|---|---|---|
| Rail icônes | 64px sticky gauche | Idem (pas de breakpoint conditionnel) |
| Panel | 208px expandable | Toggle collapsed via [Sidebar.jsx:63](frontend/src/layout/Sidebar.jsx#L63) |
| Bottom-nav | N/A | **❌ ABSENT** |
| Command palette | ⌘K dispo | ⌘K dispo (mais pas de FAB mobile) |

**Constat** : pas de stratégie mobile-first. La nav repose sur le desktop ; mobile = collapse latéral. Hors scope Sol v1.1 mais à noter (audit Marie DAF Phase 13.D rappelait persona terrain).

---

### Dimension 2 — Cartographie des routes

#### 2.1 Source canonique

Routes déclarées dans [App.jsx](frontend/src/App.jsx) (610 lignes) — patrons `<Route path={...} element={...}>`, lazy-loaded via `lazy()` + `<Suspense>`.

#### 2.2 Routes vs entrées rail (alignement)

Total ROUTE_MODULE_MAP : 53 entrées explicites ([NavRegistry.js:65-136](frontend/src/layout/NavRegistry.js#L65-L136)).

| Catégorie | Compte | Exemples |
|---|---|---|
| Routes mappées **et visibles dans NAV_SECTIONS** | 13 | `/cockpit/jour`, `/conformite`, `/consommations`, `/bill-intel`, … |
| Routes mappées **mais cachées** (`HIDDEN_PAGES`) | 6 | `/kb`, `/segmentation`, `/connectors`, `/usages-horaires`, `/compliance/pipeline`, `/anomalies` |
| Routes mappées **mais sans entrée rail** (orphelines) | ~30 | `/notifications`, `/actions`, `/actions/new`, `/actions/:id`, `/onboarding`, `/conformite/dt`, `/conformite/bacs`, `/conformite/audit-sme`, `/regops/:id`, `/payment-rules`, `/portfolio-reconciliation`, `/admin/roles`, `/admin/assignments`, `/admin/audit`, `/activation`, `/status`… |
| Entrées rail **sans route ROUTE_MODULE_MAP** | 0 (audit Vitest [NavRegistry.test.js:344](frontend/src/layout/__tests__/NavRegistry.test.js#L344)) | — |

#### 2.3 Doublons sémantiques `/dashboard` ↔ `/executive` ↔ `/cockpit/*`

[legacyRedirects.js:26-31](frontend/src/routes/legacyRedirects.js#L26-L31) :

```js
['/cockpit', '/cockpit/strategique'],
['/synthese', '/cockpit/strategique'],
['/executive', '/cockpit/strategique'],
['/dashboard', '/cockpit/strategique'],
['/dashboard-legacy', '/'],
['/tableau-de-bord', '/cockpit/jour'],
```

→ **`/dashboard`, `/executive`, `/synthese`, `/cockpit` redirigent tous vers `/cockpit/strategique`** (Vue exécutive 3min CFO). Cohabitation propre via redirects ; aucune route source vivante en parallèle.

#### 2.4 Grep occurrences libellés/routes

| Chaîne | Volume estimé `frontend/src` | Top fichiers |
|---|---|---|
| "Tableau de bord" / "Dashboard" | ~1 035 (large bruit incluant docstrings + tests) | [NavRegistry.js:536](frontend/src/layout/NavRegistry.js#L536), [App.jsx](frontend/src/App.jsx) imports lazy, [Cockpit.jsx](frontend/src/pages/Cockpit.jsx), tests phase3 |
| `/cockpit/*` | ~194 occurrences | App.jsx (routes), NavRegistry.js (mapping), legacyRedirects, tests |
| "Vue exécutive" | ~15 | [NavRegistry.js:529](frontend/src/layout/NavRegistry.js#L529), [Breadcrumb.jsx](frontend/src/layout/Breadcrumb.jsx), tests |
| "Briefing" | ~30 | Composants Sol (`SolBriefingHead.jsx`, `SolBriefingFooter.jsx`), pages Cockpit |
| "Synthèse stratégique" | ~20 | `SolKickerWithSwitch.jsx`, `CockpitDecision.jsx`, `TrajectoryDT.jsx` |
| "Centre d'action(s)" | ~25 | AppShell, ActionCenterSlideOver, COMMAND_SHORTCUTS |
| `/dashboard` | ~5 (redirects, tests) | legacyRedirects, phase3_1 test |
| `/executive` | ~5 | idem |

→ **Verdict** : les chaînes legacy "Tableau de bord" / "Vue exécutive" sont vivantes au cœur du panel Accueil ([NavRegistry.js:529, 536](frontend/src/layout/NavRegistry.js#L529-L536)) — incohérence avec doctrine §11.3 (libellés canoniques = "Briefing du jour" / "Synthèse stratégique") et §5 grammaire éditoriale.

---

### Dimension 3 — Badges, règle de calcul

#### 3.1 Architecture actuelle

[Sidebar.jsx:86-116](frontend/src/layout/Sidebar.jsx#L86-L116) :

```js
const [alertBadge, setAlertBadge] = useState(0);
const [monitoringBadge, setMonitoringBadge] = useState(0);

useEffect(() => {
  getNotificationsSummary().then(s => setAlertBadge(s.new_critical + s.new_warn));
  getMonitoringAlerts(null, 'open', 200).then(alerts => setMonitoringBadge(alerts.length));
}, []);
// + setInterval 2 minutes
```

[NavRail.jsx:12-15](frontend/src/layout/NavRail.jsx#L12-L15) :

```js
const MODULE_BADGE_KEY = {
  conformite: 'alerts',
  energie: 'monitoring',
};
```

#### 3.2 Tableau des badges

| Badge | Source | Calcul FE/BE | Endpoint(s) | Fichier:ligne |
|---|---|---|---|---|
| **conformite** (rail) | Notifications globales | **FE** : `s.new_critical + s.new_warn` (somme triviale) | `getNotificationsSummary()` | [Sidebar.jsx:96](frontend/src/layout/Sidebar.jsx#L96) |
| **energie** (rail) | Monitoring alerts | **FE** : `alerts.length` (count trivial) | `getMonitoringAlerts(null, 'open', 200)` | [Sidebar.jsx:101](frontend/src/layout/Sidebar.jsx#L101) |
| **conformiteDt / Bacs / Aper** (panel progress bars) | Score % | **FE** : `Math.min/max` cosmétique | **Source non câblée** : `badges.conformiteDt` n'est jamais peuplé par Sidebar ([Sidebar.jsx:113-116](frontend/src/layout/Sidebar.jsx#L113-L116) ne contient que `alerts` et `monitoring`) | [NavPanel.jsx:362-398](frontend/src/layout/NavPanel.jsx#L362-L398) |
| **monitoring** (item Performance énergétique) | idem energie | FE comptage | idem | [NavRegistry.js:615](frontend/src/layout/NavRegistry.js#L615) |
| **actionCenterBadge** (cloche header) | `computeActionCenterBadge(summary, notif)` | **FE** mais composé via util dédié | `getActionCenterActionsSummary()` + `getActionCenterNotifications()` | [AppShell.jsx:219-235](frontend/src/layout/AppShell.jsx#L219-L235) |

#### 3.3 Constats

- **✅ Pas de violation règle d'or** : les calculs FE sont triviaux (somme et count) — pas de business logic.
- **⚠️ Pas d'endpoint agrégé** `/api/v1/navigation/badges`. Coût : 2 appels REST en mount Sidebar + N selon refetch (toutes les 2 min). N+1 potentiel si Cockpit refetch les mêmes endpoints.
- **❌ Trois badges déclarés mais jamais peuplés** : `conformiteDt`, `conformiteBacs`, `conformiteAper` sont consommés par [NavPanel.jsx:362-398](frontend/src/layout/NavPanel.jsx#L362-L398) mais Sidebar ne les fournit pas. → Bloc de progression conformité **silencieusement masqué** (condition `!= null` toujours fausse).
- **⚠️ Sémantique flottante** : "Conformité 9+" affiche **alertes notifications globales**, pas "obligations en retard" ni "échéances proches". Incohérent avec doctrine §11 (intention "Régulation, conformité, échéances").
- **❌ Cockpit, Patrimoine, Achat, Admin sans badge** : pas de signal "événement à traiter" au niveau rail, alors que doctrine §6 "Le produit pousse, ne tire pas" exige proactivité.

---

### Dimension 4 — Cohérence doctrinale Sol v1.1

#### 4.1 Grammaire éditoriale §5 ([promeos_sol_doctrine.md:304-344](docs/vision/promeos_sol_doctrine.md#L304-L344))

| Élément doctrinal | Implémentation rail/panel | Statut |
|---|---|---|
| Kicker contextuel | `[KICKER]` SolKickerWithSwitch présent dans pages Cockpit | ✅ Hors rail |
| Titre narratif | "Briefing du jour" / "Synthèse stratégique" | **❌ Rail panel** affiche "Vue exécutive" / "Tableau de bord" ([NavRegistry.js:529, 536](frontend/src/layout/NavRegistry.js#L529-L536)) |
| Libellés courts ≤ 3 mots rail | `Accueil`, `Conformité`, `Énergie`, `Patrimoine`, `Achat` | ✅ |

#### 4.2 Anti-patterns navigation §6.2 ([promeos_sol_doctrine.md:361-368](docs/vision/promeos_sol_doctrine.md#L361-L368))

| Anti-pattern | Présent ? | Preuve |
|---|---|---|
| Menus à 4 niveaux ou plus | ❌ Non — max 3 (Module → Section → Item) | — |
| Sous-pages cachées accessibles uniquement par URL directe | ⚠️ Oui : `HIDDEN_PAGES` 6 entrées dont `/anomalies` (Détection automatique) | [NavRegistry.js:877-930](frontend/src/layout/NavRegistry.js#L877-L930) |
| Chemins multiples vers la même information | ⚠️ Oui : `/cockpit/strategique` accessible via "Vue exécutive" panel + Ctrl+Shift+C + `/cockpit` redirect | [legacyRedirects.js:26](frontend/src/routes/legacyRedirects.js#L26), [NavRegistry.js:967-973](frontend/src/layout/NavRegistry.js#L967-L973) |
| Item nav qui mène à page vide ou en chantier | ⚠️ À vérifier : 14 pages "Sol non encore actives" listées dans backlog Sprint 2 ([promeos_sol_doctrine.md:494-498](docs/vision/promeos_sol_doctrine.md)) | hors scope Phase 0 |
| Item nav redondant entre 2 modules | ❌ Non visible | — |
| Routes `-legacy` maintenues sans plan désactivation | ⚠️ Oui : 31 redirects sans date de retrait ([legacyRedirects.js](frontend/src/routes/legacyRedirects.js)) | — |

#### 4.3 Principe 11 §198-222 — Le bon endroit pour chaque brique

[promeos_sol_doctrine.md:211-218](docs/vision/promeos_sol_doctrine.md#L211-L218) — table d'intentions :

| L'utilisateur pense à... | Doctrine | Réalité actuelle | Écart |
|---|---|---|---|
| Régulation, conformité, échéances | Conformité | Module rail #2 ✅ | OK |
| **Facture, anomalie, contestation** | **Bill-Intel** | **Item #3 sous Patrimoine** | ❌ Bill-Intel n'est pas un module |
| Contrat, achat, négociation | Achat | Module rail #5 ✅ | OK |
| Mes sites, bâtiments, compteurs | Patrimoine | Module rail #4 ✅ | OK |
| Aujourd'hui, semaine, vue d'ensemble | Cockpit | Module rail #1 (label "Accueil") ✅ | OK |
| Effacement, revenus flexibilité | Flex | Item dans Énergie ([NavRegistry.js:633-641](frontend/src/layout/NavRegistry.js#L633-L641)) | ⚠️ Pilier doctrinal §4.6 mais pas module rail (cohérent avec wedge MVP : flex sous Énergie) |

#### 4.4 Centre d'action discoverability

| Surface | Présence | Détails |
|---|---|---|
| Module rail | ❌ Non | Routes `/action-center`, `/actions`, `/anomalies` mappées à `cockpit` ([NavRegistry.js:75-80](frontend/src/layout/NavRegistry.js#L75-L80)) |
| Header cloche | ✅ Oui | [AppShell.jsx:328-332](frontend/src/layout/AppShell.jsx#L328-L332) — slideover |
| Section Accueil | ❌ Non | Items panel = uniquement les 2 cockpit ([NavRegistry.js:516-540](frontend/src/layout/NavRegistry.js#L516-L540)) |
| Quick actions | ✅ "Détection automatique" → `/anomalies` | [NavRegistry.js:396-402](frontend/src/layout/NavRegistry.js#L396-L402) |
| Command shortcut | ✅ Ctrl+Shift+L | [NavRegistry.js:959-965](frontend/src/layout/NavRegistry.js#L959-L965) |

→ Discoverability : **2 clics minimum** depuis l'Accueil (cloche header) ou connaissance du raccourci. Pas d'item visible dans le panel — incohérent avec qualification "hub" du prompt.

#### 4.5 Wedge MVP représenté ?

| Brique MVP doctrine §4 | Module/section rail | Statut |
|---|---|---|
| 4.1 Patrimoine | Module #4 | ✅ |
| 4.2 EMS / Énergie | Module #3 | ✅ |
| 4.3 Conformité | Module #2 | ✅ |
| 4.4 **Bill Intelligence** | Item #3 sous Patrimoine | **❌ pas module** |
| 4.5 Achat | Module #5 | ✅ |
| 4.6 Flex | Item sous Énergie | ⚠️ Conscient (wedge énergie) |
| 4.7 Cockpit | Module #1 (Accueil) | ✅ |

→ **Bill Intelligence non visible au rail = trou doctrinal P0**. Le pilier §4.4 « shadow billing transparent » est un différenciant business stratégique ([promeos_sol_doctrine.md:554](docs/vision/promeos_sol_doctrine.md#L554) : "Bill intelligence intégrée — Oui (shadow v4.2)" vs concurrents Non), il mérite un emplacement first-class.

---

### Dimension 5 — Persona × fréquence d'usage

#### 5.1 Ordre actuel par persona

[NavRegistry.js:813-827](frontend/src/layout/NavRegistry.js#L813-L827) :

| Persona / role | Ordre rail (5 modules visibles) |
|---|---|
| `default` | cockpit, conformite, energie, patrimoine, achat |
| `dg_owner` (DG) | cockpit, achat, conformite, patrimoine, energie |
| `daf` (DAF) | cockpit, patrimoine, achat, conformite, energie |
| `acheteur` | cockpit, achat, patrimoine, conformite, energie |
| `energy_manager` | **cockpit, energie, conformite, patrimoine, achat** |
| `resp_conformite` | cockpit, conformite, patrimoine, energie, achat |
| `resp_immobilier` | cockpit, patrimoine, conformite, energie, achat |
| `resp_site` | cockpit, patrimoine, energie, conformite, achat |

#### 5.2 Cible prompt vs réalité

Cible prompt : **Accueil → Énergie → Conformité → Facturation → Achat → [séparateur] → Patrimoine** (1 ordre unique pour persona dominant).

| Position cible | Cible | Default actuel | Energy Manager actuel | DAF actuel |
|---|---|---|---|---|
| 1 | Accueil | cockpit ✅ | cockpit ✅ | cockpit ✅ |
| 2 | Énergie | conformite ❌ | **energie ✅** | patrimoine ❌ |
| 3 | Conformité | energie ❌ | conformite ✅ | achat ❌ |
| 4 | **Facturation** | patrimoine ❌ | patrimoine ❌ | conformite ❌ |
| 5 | Achat | achat ✅ | achat ✅ | energie ❌ |
| 6 (séparateur) | Patrimoine | — (4ème) | — (4ème) | — (2ème) |

→ **L'ordre `energy_manager` est le plus proche de la cible** (positions 1,2,3 alignées) mais Facturation manquante et Patrimoine pas relégué.

#### 5.3 Estimation fréquence d'usage théorique

| Persona | Cockpit | Énergie | Conformité | Facturation | Achat | Patrimoine |
|---|---|---|---|---|---|---|
| Energy Manager | quotidien | **quotidien** | hebdo | hebdo | mensuel | one-shot |
| DAF | quotidien | hebdo | hebdo | **hebdo** | mensuel | one-shot |
| RegOps | hebdo | hebdo | **quotidien** | mensuel | rare | one-shot |
| Direction Achat | mensuel | mensuel | rare | mensuel | **mensuel/quotidien** | one-shot |
| DG | mensuel | mensuel | mensuel | mensuel | mensuel | rare |
| Patrimoine/Onboarding | rare | rare | one-shot | rare | rare | **one-shot setup** |

→ **Patrimoine relégué sous séparateur cohérent avec usage one-shot.** Mais l'ordre actuel `default` met Patrimoine en #4 (avant Achat) — pas aligné.

#### 5.4 Score d'alignement persona dominant (Energy Manager)

| Critère | Cible | EM actuel | Score |
|---|---|---|---|
| Position #1 | Accueil | cockpit | 1/1 |
| Position #2 | Énergie | energie | 1/1 |
| Position #3 | Conformité | conformite | 1/1 |
| Position #4 | Facturation | patrimoine | 0/1 |
| Position #5 | Achat | achat (5ème) | 1/1 |
| Position #6 (séparateur) | Patrimoine | patrimoine en #4, pas séparé | 0/1 |
| **Total** | | | **4/6 = 67 %** |

---

### Dimension 6 — Cohérence transverse

#### 6.1 Source unique des libellés

| Libellé | Source | Utilisé dans |
|---|---|---|
| `Accueil` | [NavRegistry.js:204](frontend/src/layout/NavRegistry.js#L204) | NavRail (label module), NavPanel header, Breadcrumb |
| `Conformité`, `Énergie`, `Patrimoine`, `Achat` | NAV_MODULES | idem |
| `Vue exécutive`, `Tableau de bord` | [NavRegistry.js:529, 536](frontend/src/layout/NavRegistry.js#L529-L536) | NavPanel items, Breadcrumb (via ROUTE_SECTION_MAP/ALL_NAV_ITEMS) |
| `Facturation` | [NavRegistry.js:671](frontend/src/layout/NavRegistry.js#L671) | NavPanel item Patrimoine, Command shortcut Ctrl+Shift+B |

→ **✅ Single source of truth = NAV_MODULES + NAV_SECTIONS.** Breadcrumb dérive ([Breadcrumb.jsx:9](frontend/src/layout/Breadcrumb.jsx#L9)). Pas de divergence détectée.

#### 6.2 Calculs dupliqués entre rail et page

- [Sidebar.jsx:99](frontend/src/layout/Sidebar.jsx#L99) appelle `getMonitoringAlerts(null, 'open', 200)` toutes les 2 min.
- Si la page Cockpit / Monitoring fait le même appel sans dédupage, **N+1 réseau**.
- D'après audit existant [docs/audits/AUDIT_VUE_EXECUTIVE_SOL2_BILAN.md](docs/audits/AUDIT_VUE_EXECUTIVE_SOL2_BILAN.md) (constat 5 : "131 req/mount"), problème déjà identifié sur Cockpit Pilotage.

#### 6.3 Cohérence inter-libellés

- "Vue exécutive" (panel) ≠ "Synthèse stratégique" (page CockpitDecision title) → **incohérence visuelle utilisateur**. Doctrine §11.3 fixe libellé canonique = "Synthèse stratégique".
- "Tableau de bord" (panel) ≠ "Briefing du jour" (page CockpitPilotage title) → idem.

→ Le commit `0fcfff03` (Phase 15.bis) a corrigé l'inversion sidebar (Tableau de bord ↔ Vue exécutive) mais **n'a pas remplacé** ces libellés par les libellés narratifs canoniques.

---

### Dimension 7 — Couverture tests

#### 7.1 Tests Vitest navigation

| Fichier | LOC | Cas | Scope |
|---|---|---|---|
| [NavRegistry.test.js](frontend/src/layout/__tests__/NavRegistry.test.js) | ~600 | ~30 | Modules ordre, sections, ROUTE_MODULE_MAP, getOrderedModules, ALL_NAV_ITEMS unicité paths/labels |
| [navRefactorV114.test.js](frontend/src/__tests__/navRefactorV114.test.js) | ~200 | ~10 | Refactor Phase 13.D, ordre cockpit, libellés canoniques |
| [phase3_1_routes_cockpit_dual.test.js](frontend/src/__tests__/phase3_1_routes_cockpit_dual.test.js) | 149 | ~12 | Routes dual cockpit, redirects legacy `/dashboard`, `/executive`, no business logic FE |
| [nav_patrimoine_contextual.test.js](frontend/src/__tests__/nav_patrimoine_contextual.test.js) | ~80 | ~5 | Site search, active site context |
| [routeHelpers.test.js](frontend/src/__tests__/routeHelpers.test.js) | ~150 | ~10 | matchRouteToModule pattern matching |
| [nav_v7_parity.test.js](frontend/src/__tests__/nav_v7_parity.test.js) | ~100 | ~6 | Parity NavRail v7 |
| [phase1_site360_nav_unified.test.js](frontend/src/__tests__/phase1_site360_nav_unified.test.js) | ~80 | ~4 | Site360 nav tree |
| [step24b_nav_clean.test.js](frontend/src/__tests__/step24b_nav_clean.test.js) | ~150 | ~8 | NavRail modules V7 cleanup |
| [recents.test.js](frontend/src/layout/__tests__/recents.test.js) | ~120 | ~6 | Recents tracking |
| [ux-hardening.test.js](frontend/src/__tests__/ux-hardening.test.js) | ~300 | ~15 | NavRail label text, accessibility |
| **Total** | ~1 930 | ~106 | |

#### 7.2 Tests Playwright nav

Inventaire `tools/playwright/` :

| Fichier | Type | Scope nav |
|---|---|---|
| [audit_phase17_all_routes.mjs](tools/playwright/audit_phase17_all_routes.mjs) | Script audit | Capture 16 routes (dont `/cockpit/strategique`, `/cockpit/jour`) |
| [audit-vue-executive-sol2.mjs](tools/playwright/audit-vue-executive-sol2.mjs) | Script audit | Vue exécutive Sol2 (Phase 0) |
| [audit_phase13_complet_capture.mjs](tools/playwright/audit_phase13_complet_capture.mjs) | Script audit | Phase 13 nav démo CFO |
| [_audit_cockpit_maquette_gap.mjs](tools/playwright/_audit_cockpit_maquette_gap.mjs) | Script audit | Gap maquette ↔ implémentation |

→ **❌ Aucune suite Playwright `.spec.ts` formelle structurée.** Tous les fichiers sont des scripts d'audit en `.mjs` (capture screenshots, report markdown). Pas d'assertions automatisées sur les redirects legacy `/dashboard` → `/cockpit/strategique`.

#### 7.3 Source-guards backend

[backend/tests/source_guards/](backend/tests/) (4 fichiers, ~600 LOC) :

| Fichier | Scope |
|---|---|
| `test_doctrine_sol_source_guards.py` (252 LOC) | Invariants doctrine, anti-patterns acronymes §6.3, no FE business logic §8.1 |
| `test_conformite_source_guards.py` (150 LOC) | Conformité scoring univoque |
| `test_billing_source_guards.py` (101 LOC) | Billing constantes |
| `test_consumption_source_guard.py` (94 LOC) | Consumption SoT |

→ **❌ Aucun source-guard nav.** Pas de garde `test_no_legacy_routes_in_nav.py` qui vérifierait l'absence de réintroduction `/dashboard`, `/executive` dans NAV_MODULES/NAV_SECTIONS.

#### 7.4 Endpoints backend de navigation

| Endpoint | Fichier:ligne | Usage rail |
|---|---|---|
| `GET /api/notifications/summary` | (consommé via `getNotificationsSummary` [Sidebar.jsx:94](frontend/src/layout/Sidebar.jsx#L94)) | badge `alerts` rail Conformité |
| `GET /api/monitoring/alerts` | `backend/api/monitoring.py:378` | badge `monitoring` rail Énergie |
| `GET /api/action-center/executive-summary` | `backend/api/action_center.py:416` | badge cloche header AppShell |
| `GET /api/cockpit/executive-v2` | `backend/api/cockpit_v2.py:56` | données page Cockpit (pas rail direct) |
| `GET /api/v1/navigation/badges` | **❌ ABSENT** | — |

---

### Dimension 8 — Risques de régression

#### 8.1 Routes legacy : où elles vivent

| Route legacy | Fichier:ligne | Type | Action si suppression |
|---|---|---|---|
| `/dashboard` | [legacyRedirects.js:29](frontend/src/routes/legacyRedirects.js#L29) | Redirect FE | safe — redirect transitif |
| `/dashboard` | [phase3_1_routes_cockpit_dual.test.js](frontend/src/__tests__/phase3_1_routes_cockpit_dual.test.js) | Test FE assert redirect | **mettre à jour** test si suppression |
| `/executive` | [legacyRedirects.js:28](frontend/src/routes/legacyRedirects.js#L28) | Redirect FE | safe |
| `/executive` | tests phase3_1 | Test FE | mettre à jour |
| `/dashboard-legacy` | [legacyRedirects.js:30](frontend/src/routes/legacyRedirects.js#L30) | Redirect FE | safe |
| `/synthese` | [legacyRedirects.js:27](frontend/src/routes/legacyRedirects.js#L27) | Redirect FE | safe |
| `/tableau-de-bord` | [legacyRedirects.js:31](frontend/src/routes/legacyRedirects.js#L31) | Redirect FE | safe |

#### 8.2 Composants / models orphelins

| Item | Fichier | Statut |
|---|---|---|
| `Dashboard.jsx` | [frontend/src/pages/Dashboard.jsx](frontend/src/pages/Dashboard.jsx) | Page legacy non routée (redirects avant render). Suppression possible. |
| `dashboardEssentials.js` (856 LOC) | [frontend/src/models/dashboardEssentials.js](frontend/src/models/dashboardEssentials.js) | **Pure model** réutilisé Cockpit/CommandCenter (`buildExecutiveKpis`, `buildExecutiveSummary`) — NE PAS supprimer |
| `useExecutiveV2` | [frontend/src/hooks/useExecutiveV2.js](frontend/src/hooks/useExecutiveV2.js) | Hook fetch `/api/cockpit/executive-v2` — vivant |
| `Cockpit.jsx` (55 KB) | [frontend/src/pages/Cockpit.jsx](frontend/src/pages/Cockpit.jsx) | Page V1 legacy, rattachée à `/command-center`. À traiter ADR-001 trajectoire dashboardEssentials backend S2.5. |

#### 8.3 Documentation

| Référence | Fichier | Impact |
|---|---|---|
| Routes canoniques | [docs/vision/promeos_sol_doctrine.md:11.3](docs/vision/promeos_sol_doctrine.md) | À jour |
| Bilan audit existant | [docs/audits/AUDIT_VUE_EXECUTIVE_SOL2_BILAN.md](docs/audits/AUDIT_VUE_EXECUTIVE_SOL2_BILAN.md) | 10 findings Phase 0 (constats 595 MWh, drop -43 %, leak retail-001, 131 req/mount, 10 KPI vs ≤ 3) |
| Sprint cockpit dual | [docs/sprints/SPRINT_RETRO_COCKPIT_DUAL_SOL2/](docs/sprints/SPRINT_RETRO_COCKPIT_DUAL_SOL2/) | 139 commits Phases 0-24 documentés |

#### 8.4 Seeds démo

→ Aucune référence `/dashboard` ou `/executive` dans `backend/services/demo_seed/` (vérifié par grep agent B).

#### 8.5 Tableau impact × probabilité

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Suppression `/dashboard` casse bookmark utilisateur | Faible | Faible | Garder redirect indefinitely |
| Renommage "Vue exécutive" → "Synthèse stratégique" casse search palette | Faible | Faible | Mettre à jour `keywords` [NavRegistry.js:531](frontend/src/layout/NavRegistry.js#L531) |
| Promotion Bill-Intel module rail casse 50+ deep-links existants vers `/bill-intel` | Très faible | Faible | Routes inchangées, seul module-mapping change [NavRegistry.js:116](frontend/src/layout/NavRegistry.js#L116) |
| Réorganisation ordre rail casse muscle memory utilisateurs internes | Moyenne | Moyenne | Communication sprint + mode override role-based préservé |
| Ajout module Facturation rompt couverture tests | Haute | Faible | Mettre à jour `step24b_nav_clean.test.js`, `nav_v7_parity.test.js`, `NavRegistry.test.js` |
| N+1 refetch badges Sidebar + Cockpit | Haute | Moyenne | Dédupe via React Query cache (déjà identifié AUDIT_VUE_EXECUTIVE_SOL2_BILAN) |

---

## 3. Constats consolidés

### ✅ Points forts

1. **Registre navigation centralisé propre** ([NavRegistry.js](frontend/src/layout/NavRegistry.js)) — single source of truth, role-based ordering, séparation Module/Section/Item correcte.
2. **Routes legacy factorisées** ([legacyRedirects.js](frontend/src/routes/legacyRedirects.js)) — Phase 3.bis.a (29/04/2026) a supprimé 31 redirects dispersés.
3. **Cockpit dual câblé** — `/cockpit/jour` + `/cockpit/strategique` actifs, redirects propres.
4. **Couverture Vitest nav** ~1 930 LOC / ~106 cas — bonne densité tests structurels.
5. **Calculs FE des badges triviaux** (somme + count) — pas de violation règle d'or.
6. **Documentation à jour** — doctrine v1.0.1 (26/04), audit existant Phase 0 Vue Exécutive (27/04), sprint retro dual sol2 (30/04).

### ⚠️ Points moyens

1. **Anti-pattern "chemins multiples"** : `/cockpit/strategique` accessible via 4 surfaces (panel "Vue exécutive", `/cockpit` redirect, Ctrl+Shift+C, palette).
2. **Redirects legacy sans plan retrait** ([legacyRedirects.js](frontend/src/routes/legacyRedirects.js)) — 31 entrées sans date de désactivation.
3. **Pas d'endpoint agrégé badges** — 2 calls REST mount Sidebar, refetch 2 min, N+1 potentiel avec Cockpit.
4. **Sémantique badges flottante** — "Conformité" badge = notifications globales, pas obligations en retard.
5. **Pas de stratégie mobile-first** — pas de bottom-nav, panel collapse seul fallback responsive.
6. **Source-guards nav absents** côté backend.

### ❌ Trous P0

1. **Bill Intelligence non visible au rail** ([NavRegistry.js:668-682](frontend/src/layout/NavRegistry.js#L668-L682)) — pilier doctrinal §4.4 enfoui sous Patrimoine. **Trou MVP.**
2. **Libellés panel Cockpit non canoniques** ([NavRegistry.js:529, 536](frontend/src/layout/NavRegistry.js#L529-L536)) — "Vue exécutive" / "Tableau de bord" au lieu de "Synthèse stratégique" / "Briefing du jour" (doctrine §11.3 + §5).
3. **Centre d'action absent du rail/panel** — qualifié "hub" prompt, accessible uniquement via cloche header (≥ 2 clics) ou raccourci Ctrl+Shift+L.
4. **Badges progress conformité morts** ([NavPanel.jsx:362-398](frontend/src/layout/NavPanel.jsx#L362-L398)) — bloc rendu conditionnel jamais déclenché car Sidebar ne fournit pas `conformiteDt/Bacs/Aper`.

---

## 4. Matrice d'écart vs cible Sol v1.1

| Aspect | Cible Sol v1.1 (prompt) | Réalité actuelle | Écart |
|---|---|---|---|
| Module #1 | Accueil | cockpit (label "Accueil") | ✅ aligné |
| Module #2 | Énergie | conformite (default) / energie (energy_manager) | ⚠️ Dépend role |
| Module #3 | Conformité | energie (default) / conformite (energy_manager) | ⚠️ Dépend role |
| Module #4 | **Facturation** | patrimoine (Facturation = sous-item) | ❌ **module manquant** |
| Module #5 | Achat | achat | ✅ aligné |
| Module #6 (séparé) | **Patrimoine** | patrimoine (#4 sans séparateur) | ❌ position + UI |
| Centre d'action | Hub | cloche header + raccourci | ❌ pas hub visible |
| Cockpit dual | Briefing 30s + Synthèse 3min | `/cockpit/jour` + `/cockpit/strategique` actifs | ✅ routes OK |
| Libellés Cockpit panel | "Briefing du jour" + "Synthèse stratégique" | "Tableau de bord" + "Vue exécutive" | ❌ libellés legacy |
| Séparateur visuel | Avant Patrimoine | Aucun | ❌ |
| Persona dominant | Energy Manager (cible Sol §2) | Default order ≠ EM order | ⚠️ |
| Badges sémantiques | Événement à traiter | Compteurs notifications globales | ⚠️ |

---

## 5. Plan recommandé P0/P1/P2

> **Read-only — pas d'implémentation ici. Estimations en commits atomiques sur format `fix(nav-pN): Phase X.Y — description`.**

### P0 — Trous doctrinaux (3-5 commits)

| # | Commit | Fichiers concernés | Estim. |
|---|---|---|---|
| P0.1 | `feat(nav-p0): promote Bill Intelligence to top-level rail module` | NavRegistry.js (NAV_MODULES, NAV_SECTIONS, ROUTE_MODULE_MAP, ROLE_MODULE_ORDER), NavPanel.jsx (icon Receipt déjà présent), tests NavRegistry | 1 commit |
| P0.2 | `fix(nav-p0): rename panel cockpit items to canonical Sol §11.3` ("Vue exécutive" → "Synthèse stratégique", "Tableau de bord" → "Briefing du jour") | NavRegistry.js:526-540, tests phase3_1, navRefactorV114, ux-hardening | 1 commit |
| P0.3 | `feat(nav-p0): expose Centre d'action in Accueil panel` (item dédié `/anomalies` ou `/action-center` dans section Accueil) | NavRegistry.js NAV_SECTIONS cockpit, tests | 1 commit |
| P0.4 | `fix(nav-p0): wire conformiteDt/Bacs/Aper badges` (Sidebar fetch endpoints scoring + propagation, ou retirer le bloc dead-code NavPanel:362-398) | Sidebar.jsx, NavPanel.jsx, services/api.js | 1-2 commits |
| P0.5 | `feat(nav-p0): adopt cible rail order Accueil→Énergie→Conformité→Facturation→Achat→[sep]→Patrimoine` (réordonner ROLE_MODULE_ORDER.default + ajouter séparateur visuel rail) | NavRegistry.js, NavRail.jsx | 1 commit |

### P1 — Hygiène doctrinale (3-4 commits)

| # | Commit | Fichiers |
|---|---|---|
| P1.1 | `chore(nav-p1): document legacy redirects retirement plan` (commentaires + dates dans legacyRedirects.js) | legacyRedirects.js |
| P1.2 | `feat(nav-p1): aggregate /api/v1/navigation/badges endpoint` (backend) — supprimer 2 calls Sidebar | backend/api/navigation.py (nouveau), Sidebar.jsx |
| P1.3 | `test(nav-p1): backend source-guard prevent legacy routes in NAV_MODULES` | backend/tests/source_guards/test_nav_source_guards.py |
| P1.4 | `test(nav-p1): playwright e2e legacy redirects assertions` | tools/playwright/nav_redirects.spec.ts |

### P2 — Polish (2-3 commits)

| # | Commit | Fichiers |
|---|---|---|
| P2.1 | `fix(nav-p2): align badge semantics — alerts vs notifications` | NavRail.jsx MODULE_BADGE_KEY + Sidebar.jsx (rebrand + filtres scope) |
| P2.2 | `feat(nav-p2): mobile bottom-nav 5 modules` | NavBottomBar.jsx (nouveau), AppShell.jsx breakpoint |
| P2.3 | `chore(nav-p2): cleanup HIDDEN_PAGES — retire /anomalies double` (déjà item Centre d'action panel post-P0.3) | NavRegistry.js |

**Total estimé** : **8-12 commits atomiques** sur 1-2 sprints.

---

## 6. Risques de régression — synthèse

| Action | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Promotion Bill-Intel module rail | Tests à mettre à jour | Faible UX (deep-links inchangés) | Mettre à jour tests Vitest |
| Renommage libellés Cockpit panel | Search palette keywords | Faible | Étendre `keywords` [NavRegistry.js:531, 538](frontend/src/layout/NavRegistry.js#L531-L538) avec ancien libellé |
| Réordonnancement ROLE_MODULE_ORDER | Muscle memory utilisateurs | Moyen | Communication interne, conserver overrides personas |
| Suppression libellé "Vue exécutive" | Doc/screenshots datés | Faible | Conserver redirect routes, mettre à jour breadcrumb + ALL_NAV_ITEMS |
| Endpoint agrégé badges | Breaking change consomateurs | Très faible | Nouveau endpoint, pas de remplacement |

---

## 7. Questions ouvertes (max 5)

1. **Bill Intelligence module #4 ou item top-level distinct ?** — Promouvoir Bill-Intel à module rail dédié (option recommandée P0.1) ou créer un module composite "Facturation & Achat" ? Doctrine §4.4 + §4.5 sont 2 piliers distincts → **module Bill-Intel séparé semble cohérent**, mais cela porte le rail à 6 modules visibles + admin.

2. **Centre d'action : item Accueil ou module à part ?** — Le prompt qualifie "hub". Item dans section Accueil (P0.3) suffit pour discoverability, ou faut-il un 7ème module dédié ? Si module → conflit avec §6.2 anti-pattern "Cockpit doit être briefing, pas inbox".

3. **ROLE_MODULE_ORDER : on garde le multi-persona ou on aligne tous les rôles sur cible unique ?** — Le prompt cible un ordre unique. Faut-il supprimer la matrice 8 rôles ([NavRegistry.js:813-827](frontend/src/layout/NavRegistry.js#L813-L827)) ou aligner uniquement le `default` ? Conserver multi-persona = différenciation B2B forte mais complexité maintenance.

4. **Patrimoine séparé visuellement comment ?** — Séparateur graphique vertical dans NavRail (espace + ligne) ou groupement sémantique "Configuration" qui hébergerait Patrimoine + Admin ? Impact tint palette + a11y `aria-label`.

5. **Libellés panel Cockpit : adoption immédiate ou phase soft (cohabitation 1 sprint) ?** — Renommer "Vue exécutive" → "Synthèse stratégique" + "Tableau de bord" → "Briefing du jour" en hard cut (P0.2) impacte 50+ tests + screenshots audit. Phase soft = libellé hybride (`Synthèse stratégique` + small caption `ex Vue exécutive`) pendant 1 sprint, puis hard cut.

---

## 8. STOP — Hard Gate Phase 0

**Phase 0 read-only terminée.** Aucune modification de code, config ou test (vérification : seuls fichiers modifiés sont ceux pré-existants au lancement de la session — `docs/audit/agent_sessions.jsonl`, `docs/sprints/SPRINT_RETRO_COCKPIT_DUAL_SOL2/outputs/` — non-liés à cet audit).

**Livrable unique** : `audit/navigation_audit_20260501.md` ([ce fichier](audit/navigation_audit_20260501.md)).

**Attente** : validation explicite utilisateur sur :
- les 4 trous P0 prioritaires
- les 5 questions ouvertes §7
- le séquencement P0 → P1 → P2

→ **Aucune Phase 1 lancée tant que GO non donné.**

---

## Annexes

### A. Doctrine v1.0.1 (citations clés)

- §4.4 Bill Intelligence pilier autonome : [promeos_sol_doctrine.md:270-276](docs/vision/promeos_sol_doctrine.md#L270-L276)
- §6.2 Anti-patterns navigation : [promeos_sol_doctrine.md:361-368](docs/vision/promeos_sol_doctrine.md#L361-L368)
- §11 Le bon endroit pour chaque brique : [promeos_sol_doctrine.md:198-222](docs/vision/promeos_sol_doctrine.md#L198-L222)
- §11.3 Routes canoniques cockpit dual (cité par NavRegistry.js commentaire) : doctrine + commit `6992988d` Phase 3.1

### B. Commits récents nav (top 10)

```
afcab0a9 fix(cockpit-sol2): Phase 20.bis — corrections audit triple pre-Phase 21
232ba8e2 fix(cockpit-sol2): Phase 18 — fixes nav doublon + harmonisation glossaires
b99a1a6f fix(cockpit-sol2): Phase 17.bis — fixes P0 audits 16 routes
0fcfff03 fix(cockpit-sol2): Phase 15.bis — login redirige sur Vue exécutive
d12e6829 feat(cockpit-sol2): Phase 13.D — nav démo CFO + footer signaux moat
bbccee40 feat(cockpit-sol2): Refonte WOW Étape 2 — CockpitDecision page
d8ce9578 fix(cockpit-sol2): NavRegistry — résolution inversion sidebar
708b1b6e feat(cockpit-sol2): Refonte WOW Étape 1 — CockpitPilotage
731efb9f refactor(cockpit-sol2): Phase 3.bis.a — factorisation 31 redirects legacy
6992988d feat(cockpit-sol2): Phase 3.1 — routes /cockpit/jour | /strategique
```

### C. Paramètres audit

- **Branche** : `claude/refonte-sol2`
- **Date** : 2026-05-01
- **Mode** : read-only strict (zéro modification code/test/config)
- **Outil** : Claude Code Opus 4.7 (1M context)
- **Délégations** : 2 sous-agents Explore (cartographie nav frontend + cartographie risques régression)
- **MCP requis prompt** : Context7, code-review, simplify (non utilisés en Phase 0 read-only — réservés Phase 1+)
