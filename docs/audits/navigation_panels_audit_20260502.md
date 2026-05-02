---
audit: navigation_phase_0_bis
date: 2026-05-02
branch: claude/refonte-sol2
mode: read-only strict
doctrine_ref: docs/vision/promeos_sol_doctrine.md (v1.0.1 — 2026-04-26)
phase_0_ref: docs/audits/navigation_audit_20260501.md
auteur: Claude Code (Opus 4.7)
---

# AUDIT NAVIGATION PROMEOS — Phase 0.bis read-only

> **Cible** : audit doctrinal des **sections panel internes** + **disposition fine**
> (ordre intra-section, items cachés, mobile, Command Palette). Le Phase 0
> initial avait couvert la couche modules rail ; cette Phase 0.bis cible la
> couche 2 (items panel) qui n'avait pas été auditée doctrinalement.
>
> **Sprint nav clos** au 2026-05-02 : 12 commits livrés depuis l'audit Phase 0
> (P0.1 → P0.5 + P1.0 + P1.2 + P1.2.bis + P1.3). 5/5 trous P0 résolus,
> baseline tests +79, 0 régression.

---

## 1. TL;DR

1. **Architecture sections panel saine post-sprint** ([NavRegistry.js:NAV_SECTIONS](frontend/src/layout/NavRegistry.js)) — 7 sections, 20 items visibles + 4 expert. 100 % des piliers doctrinaux §4 ont au moins un item rail. Aucun doublon pathologique anti-pattern §6.2 (toutes les redondances rail/quick/shortcut sont contextes distincts).
2. **❌ Trou doctrinal P0 — Conformité §4.3 incomplète** : doctrine cite **DT, BACS, APER, Audit SMÉ, OPERAT**. Items rail actuels = 3 (Conformité parent / Tertiaire-OPERAT / APER). **BACS et Audit SMÉ absents en items dédiés** alors que ROUTE_MODULE_MAP mappe `/conformite/bacs` et `/conformite/audit-sme` ([NavRegistry.js:84-87](frontend/src/layout/NavRegistry.js#L84)). Persona Energy Manager (BACS = bâtiments tertiaires >290 kW) et RegOps (Audit SMÉ = obligation périodique) servis par mots-clés keyword search uniquement.
3. **⚠️ Patrimoine §4.1 — promesse "benchmarks ADEME + mutualisation DT" non rendue en panel** : 2 items génériques (Sites & bâtiments, Contrats énergie). La doctrine évoque "benchmarks ADEME ODP 2024 + simulation mutualisation DT (-23k€)" comme différenciants. À arbitrer : page dédiée vs vue intégrée Site360.
4. **⚠️ HIDDEN_PAGES — 6 entrées dont 2 à clarifier** : `/anomalies` (Détection automatique) est désormais redondant avec l'item panel "Centre d'action" Phase 1.C (deux portes vers même fonction). `/compliance/pipeline` reste utile pour RegOps mais flotte sans rattachement explicite à la section Conformité du panel.
5. **⚠️ Mobile P1 toujours ouvert** — pas de bottom-nav, pas de stratégie responsive distincte (drawer overlay seul à <768px). Persona terrain (Marc EM, Yannick chargé site) non servi sur mobile en MVP. Audit Phase 0 §1.6 toujours en l'état.

---

## 2. Inventaire détaillé par module (7 sections)

### 2.1 Cockpit / Accueil (blue) — 3 items

| Pos | Route | Label | Icon | Badge | Source |
|---|---|---|---|---|---|
| 1 | `/cockpit/jour` | Briefing du jour | LayoutDashboard | — | [NavRegistry.js:540-555](frontend/src/layout/NavRegistry.js) |
| 2 | `/cockpit/strategique` | Synthèse stratégique | BarChart3 | — | [NavRegistry.js:557-573](frontend/src/layout/NavRegistry.js) |
| 3 | `/action-center` | Centre d'action | Inbox | actionCenter | [NavRegistry.js:582-601](frontend/src/layout/NavRegistry.js) |

Phase doc : P0.2 hard-cut libellés (Sol §11.3) + P0.3 ajout Centre d'action + ordre EM-first (Briefing → Synthèse).

### 2.2 Conformité (emerald) — 3 items

| Pos | Route | Label | Icon | Badge | Source |
|---|---|---|---|---|---|
| 1 | `/conformite` | Conformité | ShieldCheck | — | [NavRegistry.js:606-628](frontend/src/layout/NavRegistry.js) |
| 2 | `/conformite/tertiaire` | Décret Tertiaire / OPERAT | Building2 | — | [NavRegistry.js:629-636](frontend/src/layout/NavRegistry.js) |
| 3 | `/conformite/aper` | Solarisation (APER) | Sun | — | [NavRegistry.js:637-643](frontend/src/layout/NavRegistry.js) |

Phase doc : Tertiaire/OPERAT promu de HIDDEN à visible (Phase 17.bis.C, persona Marie DAF). Item parent `/conformite` couvre BACS + Audit SMÉ via keywords mais sans landing page dédiée.

### 2.3 Énergie (indigo) — 5 items

| Pos | Route | Label | Icon | Badge | Source |
|---|---|---|---|---|---|
| 1 | `/consommations` | Consommations | Activity | — | [NavRegistry.js:651-657](frontend/src/layout/NavRegistry.js) |
| 2 | `/monitoring` | Performance énergétique | TrendingUp | monitoring | [NavRegistry.js:658-665](frontend/src/layout/NavRegistry.js) |
| 3 | `/usages` | Répartition par usage | PieChart | — | [NavRegistry.js:666-672](frontend/src/layout/NavRegistry.js) |
| 4 | `/diagnostic-conso` | Diagnostics | SearchCheck | — | [NavRegistry.js:673-678](frontend/src/layout/NavRegistry.js) |
| 5 | `/flex` | Flex Intelligence | Zap | — | [NavRegistry.js:684-690](frontend/src/layout/NavRegistry.js) |

Phase doc : Flex rattaché module Énergie (Phase 17.bis.B). Usages sorti HIDDEN. Section la plus dense (5 items, max recommandé Sol §6.2).

### 2.4 Patrimoine (amber) — 2 items

| Pos | Route | Label | Icon | Badge | Source |
|---|---|---|---|---|---|
| 1 | `/patrimoine` | Sites & bâtiments | MapPin | — | [NavRegistry.js:698-705](frontend/src/layout/NavRegistry.js) |
| 2 | `/contrats` | Contrats énergie | FileText | — | [NavRegistry.js:706-712](frontend/src/layout/NavRegistry.js) |

Phase doc : Facturation extraite vers module dédié (Phase 1.D — P0.1). Patrimoine désormais 2 items "asset registry" pure.

### 2.5 Facturation (cyan) — 1 item · Phase 1.D — P0.1

| Pos | Route | Label | Icon | Badge | Source |
|---|---|---|---|---|---|
| 1 | `/bill-intel` | Vue d'ensemble | Receipt | facturation | [NavRegistry.js:723-741](frontend/src/layout/NavRegistry.js) |

Phase doc : Bill Intelligence promotion module rail dédié (P0.1). 1 seul item — variantes via query-string `?filter=...`.

### 2.6 Achat (violet) — 2 items

| Pos | Route | Label | Icon | Badge | Source |
|---|---|---|---|---|---|
| 1 | `/renouvellements` | Échéances | CalendarRange | achat | [NavRegistry.js:749-754](frontend/src/layout/NavRegistry.js) |
| 2 | `/achat-energie` | Scénarios d'achat | Calculator | — | [NavRegistry.js:755-770](frontend/src/layout/NavRegistry.js) |

Phase doc : Achat visible mode normal V7. Ordre Échéances → Scénarios (signal urgent → outil simulation).

### 2.7 Admin — Données (slate, expertOnly) — 4 items

| Pos | Route | Label | Icon | Badge | Source |
|---|---|---|---|---|---|
| 1 | `/import` | Import données | Upload | — | [NavRegistry.js:780-784](frontend/src/layout/NavRegistry.js) |
| 2 | `/admin/users` | Utilisateurs | Users | — | [NavRegistry.js:786-790](frontend/src/layout/NavRegistry.js) |
| 3 | `/watchers` | Veille réglementaire | Eye | — | [NavRegistry.js:792-796](frontend/src/layout/NavRegistry.js) |
| 4 | `/status` | Système | Settings | — | [NavRegistry.js:798-802](frontend/src/layout/NavRegistry.js) |

Phase doc : Admin = expertOnly, hors comptage `ALL_NAV_ITEMS`. 4 items administrateur stables.

---

## 3. Constats par module (✅ / ⚠️ / ❌)

### 3.1 Cockpit ✅

- ✅ 3/3 items canoniques (Briefing, Synthèse, Centre d'action) — couverture doctrine §4.7
- ✅ Ordre EM-first cohérent (briefing 30s → synthèse 3min → action center)
- ⚠️ **Chantier α non livré** (moteur événements proactif) — la promesse "briefing éditorial vivant qui se réécrit chaque jour" ([promeos_sol_doctrine.md:294-300](docs/vision/promeos_sol_doctrine.md#L294-L300)) reste un chantier backlog. Hors scope nav, mais conditionne le test 6 doctrine ("test du jour J vs J+1").

### 3.2 Conformité ❌

- ❌ **Items BACS et Audit SMÉ manquants** ([promeos_sol_doctrine.md:264](docs/vision/promeos_sol_doctrine.md#L264)) — doctrine §4.3 cite "Décret Tertiaire, BACS, APER, Audit SMÉ, OPERAT" comme 5 piliers réglementaires. Items panel actuels n'exposent que 3 (parent + Tertiaire + APER).
- ⚠️ **Routes mappées mais sans landing visible** : `/conformite/bacs` et `/conformite/audit-sme` sont dans `ROUTE_MODULE_MAP` ([NavRegistry.js:84-87](frontend/src/layout/NavRegistry.js#L84-L87)) → existent côté routing mais inaccessibles depuis le panel.
- ⚠️ **Persona impacté** : Energy Manager (BACS = bâtiments >290 kW décret 2020-887, échéance BACS 25 k 2026 / 100 k 2030) et RegOps (Audit SMÉ obligatoire >250 ETP) cherchent ces items en navigation directe.

### 3.3 Énergie ✅

- ✅ 5/5 items couvrant les sous-axes (consommation, performance, usages, diagnostics, flex)
- ✅ Flex Intelligence intégré (Phase 17.bis.B) — différenciant produit majeur
- ⚠️ **Densité maximale** : 5 items = limite haute recommandée Sol §6.2 (anti-pattern menu surchargé). Si on ajoute une 6e item (ex: forecasting), il faudra arbitrer regroupement.

### 3.4 Patrimoine ⚠️

- ✅ 2 items registry purs (Sites, Contrats) — séparation asset/contrat claire
- ⚠️ **Promesse §4.1 "benchmarks ADEME + simulation mutualisation DT"** non rendue en panel ([promeos_sol_doctrine.md:250-252](docs/vision/promeos_sol_doctrine.md#L250-L252)). Ces fonctions vivent embed dans `/patrimoine` ou `/sites/:id` mais ne sont pas annoncées par le rail. Risque doctrine §1 (Mission "récit lisible") non rendue.
- ⚠️ Position rail = 6e (avec séparateur) cohérent avec usage one-shot setup, mais cela "cache" la richesse fonctionnelle.

### 3.5 Facturation ✅

- ✅ Module rail dédié (Phase 1.D — P0.1) — pilier §4.4 servi
- ✅ 1 item "Vue d'ensemble" comme entry point clair (variantes via query-string conformes pattern Sol §11.3)
- ✅ Couverture COMMAND_SHORTCUT Ctrl+Shift+B + Quick Action "Anomalies factures"

### 3.6 Achat ✅

- ✅ 2 items aligned wedge §4.5 (Échéances + Scénarios)
- ✅ Ordre signal urgent → outil simulation
- ⚠️ Pas de COMMAND_SHORTCUT dédié Achat — persona Direction Achat (mensuel/quotidien) bénéficierait d'un raccourci type Ctrl+Shift+P (purchase). Mineur.

### 3.7 Admin ✅

- ✅ 4 items administrateurs stables
- ✅ ExpertOnly correctement filtré ([NavRegistry.js:251-253](frontend/src/layout/NavRegistry.js))
- ⚠️ Pas de groupage logique (Import + Veille = "Données" / Utilisateurs + Système = "Plateforme") — actuellement liste plate. Mineur.

---

## 4. Matrice trous doctrinaux

| Item attendu doctrine | Présent panel ? | Module suggéré | Sévérité | Réf doctrine |
|---|---|---|---|---|
| **BACS — Pilotage bâtiment** | ❌ | Conformité (3e pos après Tertiaire) | **P0** | §4.3 |
| **Audit SMÉ** | ❌ | Conformité (4e pos) | **P0** | §4.3 |
| Benchmarks ADEME ODP 2024 | ⚠️ embed Site360 | Patrimoine (3e pos) ou page dédiée | P1 | §4.1 |
| Simulation mutualisation DT (-23k€) | ⚠️ embed Tertiaire | Conformité Tertiaire (sub-page) ou Patrimoine | P1 | §4.1 |
| Moteur événements proactif Cockpit | ⚠️ Chantier α | hors scope nav | P1 backlog | §4.7 + §6 |
| Forecasting énergie | ⚠️ embed Monitoring | Énergie ? (densité 5→6) | P2 | §4.2 |
| Mobile bottom-nav 5 modules | ❌ | nouveau composant | P1 | §1.6 audit Phase 0 |
| Hedging post-ARENH | ⚠️ embed Achat | Achat (sub-page Scénarios) | P2 | §4.5 |
| Bridge agrégateur Flex | ⚠️ embed Flex | Énergie/Flex (sub-page) | P2 | §4.6 |

**Synthèse** : 2 trous **P0 doctrinaux** (BACS + Audit SMÉ), 3 P1 fonctionnels (benchmarks, mutualisation, mobile), 4 P2 backlog (forecasting, hedging, bridge, événements).

---

## 5. Items cachés (HIDDEN_PAGES) — Décisions à arbitrer

| Route | Label | Statut actuel | Recommandation | Justification doctrinale |
|---|---|---|---|---|
| `/kb` | Mémobox | CommandPalette only | **Keep hidden** | Doc/référence — search adapté, doctrine §11.1 "moins de noise rail" |
| `/segmentation` | Segmentation | CommandPalette only | **Keep hidden** | Outil interne marketing/produit — pas exposé persona client |
| `/connectors` | Connecteurs | CommandPalette only | **Keep hidden** | Setup/admin technique — accédé par admin uniquement |
| `/usages-horaires` | Usages & Horaires | CommandPalette only | **Keep hidden** | Variante sub-page de `/usages` (item visible) — doublon pathologique sinon |
| `/compliance/pipeline` | Pipeline conformité | CommandPalette only | **⚠️ À arbitrer** | Workflow RegOps utile mais sans rattachement panel. Promotion = item Conformité ou keep hidden ? |
| `/anomalies` | Détection automatique | CommandPalette + Quick Action | **⚠️ À reconsidérer** | Phase 1.C ajouté Centre d'action panel → redondance fonctionnelle. Quick Action "Détection automatique" pointe sur `/anomalies` alors que Centre d'action couvre l'intent. |

**Note** : `/anomalies` quick action ([NavRegistry.js:452-458](frontend/src/layout/NavRegistry.js#L452-L458)) a été ajoutée AVANT P0.3 (Centre d'action). Avec le Centre d'action désormais en panel, la Quick Action duplique le canal. À arbitrer : (a) supprimer Quick Action ; (b) garder Quick Action mais retargeter vers `/action-center` ; (c) garder pour rétro-compat search.

---

## 6. Conformité §4.3 — Trou BACS + Audit SMÉ détaillé

### 6.1 État actuel

```
Section panel "Conformité" (3 items) :
  1. Conformité (parent) — keywords: bacs, gtb, gtc, audit, sme [...]
  2. Décret Tertiaire / OPERAT (sub-page tertiaire)
  3. Solarisation (APER) (sub-page aper)
```

Routes mappées non exposées en panel :
- `/conformite/bacs` → mappée module 'conformite' ([NavRegistry.js:85](frontend/src/layout/NavRegistry.js#L85)) mais pas dans `NAV_SECTIONS`
- `/conformite/audit-sme` → idem ([NavRegistry.js:87](frontend/src/layout/NavRegistry.js#L87))

### 6.2 Pourquoi c'est un trou P0

- **Doctrine §4.3** énonce "DT, BACS, APER, Audit SMÉ, OPERAT" comme 5 piliers réglementaires. La nav rend 3/5 (DT, OPERAT via Tertiaire, APER).
- **Persona EM (Marc)** consulte BACS quotidiennement post-2026 (échéance BACS bâtiments tertiaires 25 kW puis 70 kW selon décret 2020-887).
- **Persona RegOps** consulte Audit SMÉ annuellement (obligation ISO 50001 pour entreprises >250 ETP).
- **Wedge MVP** → la conformité est le trafic le plus fort (audit Phase 0 §5.4 score persona EM 4/6) ; un trou ici impacte le test doctrine §11 (intention "Régulation, conformité, échéances → Conformité").

### 6.3 Options d'arbitrage

| Option | Description | Pro | Contra |
|---|---|---|---|
| **A** | Ajouter 2 items panel : BACS + Audit SMÉ | Couverture doctrine 5/5. Discoverability max. | Section passe de 3 à 5 items (densité limite §6.2) |
| **B** | Promouvoir BACS uniquement (Audit SMÉ rare → keep hidden) | Cohérent fréquence persona | Doctrine §4.3 partiellement servie |
| **C** | Sub-tabs dans `/conformite` parent (DT/BACS/APER/SMÉ tabs) | Densité panel inchangée | Anti-pattern §6.2 sub-pages cachées par défaut |

---

## 7. Disposition mobile

### 7.1 État actuel

- Breakpoint : `useMediaQuery('(min-width: 768px)')` ([AppShell.jsx:202](frontend/src/layout/AppShell.jsx#L202))
- ≥768px : Sidebar persistante (rail 64px + panel 208px)
- <768px : Drawer overlay (`<Drawer side="left">` activé par hamburger header)
- Auto-close sur route change ([AppShell.jsx:206-208](frontend/src/layout/AppShell.jsx#L206-L208))
- Pas de bottom-nav, pas de MobileNav distinct, pas de skeleton mobile

### 7.2 Constats

- ✅ Drawer mobile fonctionne (UX MVP acceptable)
- ⚠️ Persona terrain (Marc EM site, Yannick chargé site) servi par drawer overlay = friction (1 clic hamburger + 1 clic item = 2 clics nav)
- ⚠️ Pas de quick access aux 3 actions les plus fréquentes (Briefing / Centre d'action / Conformité) en mobile
- ⚠️ Pas de breakpoints intermédiaires (tablette portrait) — drawer sur tout <768px

### 7.3 Recommandation P1 (audit Phase 0 §5)

Bottom-nav 5 modules cible Sol v1.1 (Accueil → Énergie → Conformité → Facturation → Achat) avec drawer overlay pour Patrimoine/Admin. Hors scope sprint nav actuel — à séquencer P1.

---

## 8. Command Palette ⌘K — Couverture

### 8.1 Métriques

| Métrique | Compte | Source |
|---|---|---|
| `ALL_NAV_ITEMS` (panel non-admin) | 19 | [NavRegistry.js:919-921](frontend/src/layout/NavRegistry.js) |
| `HIDDEN_PAGES` | 6 | [NavRegistry.js:1040-1089](frontend/src/layout/NavRegistry.js) |
| `ALL_MAIN_ITEMS` (= panel + hidden) | 25 | [NavRegistry.js:1094-1099](frontend/src/layout/NavRegistry.js) |
| `QUICK_ACTIONS` | 15 | [NavRegistry.js:445-557](frontend/src/layout/NavRegistry.js) |
| `COMMAND_SHORTCUTS` | 10 | [NavRegistry.js:1104-1186](frontend/src/layout/NavRegistry.js) |
| **Total surfaces ⌘K** | **50 entrées** indexables | — |

### 8.2 Constats

- ✅ Aucun item nav inaccessible search (couverture 100 % via panel + hidden + quick + shortcut)
- ✅ Keywords étendus pour rétro-compat (Phase 1.A : "vue exécutive" / "tableau de bord" → routes canoniques)
- ⚠️ **Doublon `/anomalies`** : Quick Action "Détection automatique" + HIDDEN_PAGE "Détection automatique" (même libellé, même route) — double match en search
- ⚠️ **Pas de keywords pour BACS/Audit SMÉ items** (puisque les items eux-mêmes manquent) — search "bacs" tombe sur item parent `/conformite` (keywords contiennent 'bacs'), mais l'utilisateur attend une page BACS

---

## 9. Plan recommandé P0/P1/P2

### P0 — Trous doctrinaux Conformité (1-2 commits)

| # | Commit | Fichiers | Estim. |
|---|---|---|---|
| P0.6 | `feat(nav-p0): add BACS + Audit SMÉ items to Conformité section (doctrine §4.3 completeness)` | NavRegistry.js (+2 items NAV_SECTIONS conformite), tests NavRegistry.test.js + nav_v7_parity.test.js (compteurs +2) | 1 commit |

**Note conditionnelle** : si Option B retenue (BACS only), ce commit ajoute 1 item (compteur +1). Si Option C (tabs), aucun ajout item mais réorg parent `/conformite` → hors scope panel.

### P1 — Cohérence + mobile + cleanup (3-4 commits)

| # | Commit | Fichiers |
|---|---|---|
| P1.4 | `feat(nav-p1): mobile bottom-nav 5 modules` (Sol v1.1 cible) | NavBottomBar.jsx (NEW), AppShell.jsx breakpoint, tests |
| P1.5 | `chore(nav-p1): retire QuickAction /anomalies redundant with Centre d'action panel` | NavRegistry.js QUICK_ACTIONS, tests compteurs |
| P1.6 | `feat(nav-p1): expose /compliance/pipeline as item Conformité (RegOps workflow)` | NavRegistry.js NAV_SECTIONS conformite (+1) ou keep hidden + decision logged |
| P1.7 | `feat(nav-p1): Patrimoine — benchmarks/mutualisation landing page` | NavRegistry.js (+1 item Patrimoine ou nouveau composant) |

### P2 — Backlog (post-MVP)

| # | Commit | Fichiers |
|---|---|---|
| P2.1 | Cockpit — Chantier α moteur événements proactif | hors scope nav (backlog produit) |
| P2.2 | Énergie — Forecasting item (si densité 6 acceptée) | NavRegistry.js |
| P2.3 | Achat — COMMAND_SHORTCUT Ctrl+Shift+P (purchase) | NavRegistry.js COMMAND_SHORTCUTS |
| P2.4 | Admin — groupage logique "Données / Plateforme" | NavRegistry.js sections admin |

**Total estimé** : **6-9 commits atomiques** sur 1-2 sprints.

---

## 10. Risques de régression

| Action | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Ajout BACS item Conformité | Tests compteurs à mettre à jour (3→4) | Faible | nav_v7_parity, NavRegistry.test compteurs +2 |
| Ajout Audit SMÉ item Conformité | idem (4→5, atteint densité limite) | Faible | tests + revue UX longueur panel |
| Retrait QuickAction `/anomalies` | Search palette utilisateur perd 1 hit | Très faible | Centre d'action panel + HIDDEN_PAGE le couvrent toujours |
| Promotion `/compliance/pipeline` | Compteur ALL_NAV_ITEMS +1 (16→17) | Faible | Cascade tests existants |
| Bottom-nav mobile | Risque scope creep responsive | Moyen | Itération scope strict 5 modules cible |
| Page benchmarks Patrimoine | Possible doublon avec Site360 EUI | Moyen | Décision arbitrée avant action |

---

## 11. Questions ouvertes (max 5)

1. **BACS / Audit SMÉ : Option A (2 items), B (BACS seul), ou C (tabs sur `/conformite` parent) ?** Densité panel Conformité actuel = 3, target Option A = 5 (limite haute §6.2). Quel arbitrage doctrinal vs UX ?

2. **`/anomalies` Quick Action : retirer (Option α), retargeter vers `/action-center` (Option β), ou conserver (Option γ) ?** Phase 1.C a fait du Centre d'action le hub — la Quick Action vers `/anomalies` brut devient sémantiquement incohérente. Mais retirer = perdre 1 entrée search (même si les keywords du Centre d'action couvrent).

3. **`/compliance/pipeline` : promouvoir item Conformité (Option A) ou laisser HIDDEN_PAGES (Option B) ?** Workflow RegOps utile mais audience persona limitée. Test doctrine §11 "feature critique invisible faute de surcharger" applicable ici ?

4. **Patrimoine §4.1 benchmarks/mutualisation : page panel dédiée (Option A) ou enrichissement Site360 (Option B) ?** Option A coûte 1 item rail Patrimoine (3e pos après séparateur), Option B garde le rail léger mais doctrine §4.1 promesse moins discoverable.

5. **Mobile bottom-nav : prioriser P1.4 maintenant (Option α) ou laisser au sprint mobile dédié (Option β) ?** Le sprint nav est clos côté desktop. Lancer mobile sans avoir mesuré impact perso terrain = risque scope creep.

---

## 12. STOP — Hard Gate Phase 0.bis

**Phase 0.bis read-only terminée.** Aucune modification de code, config ou test (vérification : modifs `M` initiales `migrations.py` + `docs/sprints/SPRINT_RETRO_COCKPIT_DUAL_SOL2/outputs/*` préexistantes, hors scope audit).

**Livrable unique** : [docs/audits/navigation_panels_audit_20260502.md](docs/audits/navigation_panels_audit_20260502.md) (ce fichier).

**Attente** : validation explicite utilisateur sur :
- les 2 trous P0 doctrinaux (BACS + Audit SMÉ)
- les 5 questions ouvertes §11
- le séquencement P0.6 → P1.4-P1.7

→ **Aucune Phase suivante lancée tant que GO non donné.**

---

## Annexes

### A. Récap sprint nav cumulé (12 commits)

| Phase | SHA | Description |
|---|---|---|
| Phase 0 | (audit livrable) | Audit Phase 0 read-only |
| 1.A P0.2 | `b14af2b6` + `3e4e311a` | Libellés Cockpit canoniques §11.3 |
| 1.B P0.4 | `eff5778d` | Retrait dead-code badges progress |
| 1.C P0.3 | `86fdad8e` | Centre d'action en 3e item Accueil |
| 1.D P0.1 | `ca2caf3a` | Bill Intelligence module rail dédié |
| 1.E P0.5 | `b7e25880` | Ordre cible rail Sol v1.1 |
| 1.F P1.0 | `51aeb291` | Stabilisation captures + smoke spec |
| 2.A P1.2 | `6c4cc362` | Endpoint backend agrégé `/api/v1/navigation/badges` |
| 2.B P1.2.bis | `f036a99e` | NavigationBadgesContext — 1 fetch unique FE |
| 2.C P1.3 | `447f24c3` | Source-guards FE anti-régression |

### B. Doctrine — Citations clés

- §4.3 Conformité piliers : [promeos_sol_doctrine.md:264](docs/vision/promeos_sol_doctrine.md#L264) — "DT, BACS, APER, Audit SMÉ, OPERAT"
- §4.1 Patrimoine promesse : [promeos_sol_doctrine.md:250-252](docs/vision/promeos_sol_doctrine.md#L250-L252)
- §4.7 Cockpit promesse : [promeos_sol_doctrine.md:294-300](docs/vision/promeos_sol_doctrine.md#L294-L300)
- §6.2 anti-patterns navigation : [promeos_sol_doctrine.md:361-368](docs/vision/promeos_sol_doctrine.md#L361-L368)
- §11 le bon endroit : [promeos_sol_doctrine.md:198-222](docs/vision/promeos_sol_doctrine.md#L198-L222)

### C. Paramètres audit

- **Branche** : `claude/refonte-sol2`
- **Date** : 2026-05-02
- **Mode** : read-only strict
- **Outil** : Claude Code Opus 4.7 (1M context)
- **Délégation** : 1 sous-agent Explore (cartographie sections + HIDDEN_PAGES + mobile + ALL_NAV_ITEMS + doctrine §4/§11)
