# SOL_MIGRATION_GUIDE.md

> **Objet** : guide unique pour migrer toutes les pages PROMEOS sur l'esprit maquette `cockpit-sol-v1-adjusted-v2.html`. Référencé par tous les prompts Claude Code de refonte (Lots 1 à 6).
>
> **Audience** : Claude Code exécutant les prompts de refonte, et tout contributeur humain qui ajoute une nouvelle page.

---

## Principes fondateurs (5, inviolables)

1. **La maquette est le wireframe.** Toute page nouvelle ou refondue dérive d'un des 6 patterns documentés ici — jamais d'une invention libre.
2. **Zéro backend modifié.** `git diff --name-only origin/main... | grep -E '^(backend/|.*\.py$|services/api/[^/]+\.js)'` doit retourner vide avant chaque commit.
3. **Zéro calcul frontend.** Les composants Sol et les pages sont de la composition pure ; les presenters (`*_sol_presenters.js`) sont des fonctions pures qui transforment les données API existantes en props d'affichage.
4. **Tous menus/routes/actions préservés.** `NavRegistry`, `QUICK_ACTIONS`, `COMMAND_SHORTCUTS`, `HIDDEN_PAGES` restent intouchés. La refonte habille, elle ne change pas la structure.
5. **Cohérence visuelle stricte.** Les tokens CSS de `ui/sol/tokens.css` sont la seule source de couleurs/typo. Tout hex hardcodé ≠ `#FFFFFF` dans un composant Sol est une régression.

---

## Les 6 patterns

### Pattern A — Dashboard narratif

**Quand l'utiliser** : page d'accueil d'un module, vue synthétique avec 3-5 KPIs + éléments narratifs.

**Structure type** (ordre strict) :
```
┌─ SolPageHeader (kicker mono + titre DM + rightSlot SolLayerToggle)
├─ SolHeadline (phrase narrative Sol contextuelle)
├─ SolSubline (sous-phrase d'explication)
├─ [SolHero conditionnel] (si action Sol proposée)
├─ SolKpiRow (exactement 3 SolKpiCard)
├─ SolSectionHead ("Cette semaine chez vous" · meta freshness)
├─ SolWeekGrid (exactement 3 SolWeekCard : attention / afaire / succes)
├─ SolSectionHead ("Courbe signature" · meta unités/source)
└─ SolLoadCurve ou graphe signature propre au module
```

**Composants Sol utilisés** : tous déjà produits en Phase 1 du prompt initial.

**Presenters requis** : `build{Page}Narrative`, `build{Page}SubNarrative`, `build{Page}WeekCards`, `interpret*` pour chaque KPI.

**Pages concernées** : `/` accueil tableau de bord, `/conformite/aper`, `/monitoring` Performance.

**Variantes autorisées** :
- Remplacer SolLoadCurve par SolBarChart (conso par site) ou SolAreaChart (trajectoire temporelle) — même structure, visualisation adaptée
- Ajouter un 4ᵉ KPI si strictement justifié — sinon rester à 3 (règle "numbers first")
- Omettre SolHero si le module n'a jamais d'action Sol proposée (rare)

**Anti-patterns** :
- ❌ Plus de 5 KPIs (ça devient un dashboard BI, pas une page narrative)
- ❌ Pas de SolHeadline narrative (casse l'esprit journal)
- ❌ Week-cards génériques sans tag coloré (casse la hiérarchie émotionnelle)

---

### Pattern B — Liste drillable

**Quand l'utiliser** : page qui affiche une collection d'entités (factures, contrats, anomalies, utilisateurs, etc.) avec filtres et drill-down.

**Structure type** :
```
┌─ SolPageHeader (kicker + titre + rightSlot actions primaires)
├─ SolHeadline (phrase contextuelle avec count + impact chiffré)
├─ SolExpertToolbar (filtres mono + sélection + bouton action de masse)
├─ SolExpertGrid (table 4-7 colonnes sortable + status pills)
├─ SolPagination (mono, discrète)
└─ [SolDrawer ouvert au clic sur une ligne → mode détail]
```

**Composants Sol à produire en Phase 1 du Lot 2** :
- `SolListPage.jsx` — wrapper qui compose toolbar + grid + pagination
- `SolExpertToolbar.jsx` — filtres mono pills + action primaire droite
- `SolExpertGridFull.jsx` — extension de `SolExpertGrid` (sort + select + row click)
- `SolPagination.jsx` — mono discrète

**Presenters requis** : `buildListHeadline(count, contestable, potentialRecovery)`, `buildListRows(data)` (shape par type d'entité), `buildFilterPills(activeFilters)`.

**Pages concernées** : `/contrats`, `/renouvellements`, `/anomalies`, `/usages`, `/usages-horaires`, `/watchers`, `/admin/users`, `/admin/roles`, `/admin/assignments`, `/admin/audit`.

**Variantes autorisées** :
- Ajouter un bloc SolKpiRow (3 KPIs) au-dessus de la table si valeur agrégée utile — ex : pour `/anomalies`, montrer "12 anomalies · 7 contestables · 12 847 € potentiel" même en résumé narratif puis le détail en table
- Drawer détail peut ouvrir un mode Inspect (prose éditoriale Fraunces) au lieu d'un simple side panel

**Anti-patterns** :
- ❌ Table sans filtres (personne n'utilise 500 lignes sans filtrer)
- ❌ Sélection multiple sans action de masse (ou l'inverse)
- ❌ Drawer qui recharge la page (doit être instantané, données déjà en mémoire)

---

### Pattern C — Fiche détail

**Quand l'utiliser** : page d'une entité unique (un site, un dossier de conformité, une anomalie de facture, un diagnostic).

**Structure type** :
```
┌─ SolBreadcrumb (kicker mono avec chemin + retour)
├─ SolPageHeader (titre = nom entité + rightSlot status pill)
├─ SolHeadline (phrase narrative contextuelle sur l'entité)
├─ SolKpiRow (3 KPIs contextuels à l'entité)
├─ SolLayerToggle (Surface / Inspect / Expert) — optionnel selon page
├─ [mode Surface] SolSectionHead + contenu principal
│   └─ soit graphe, soit timeline, soit sections thématiques
├─ [mode Inspect] SolInspectDoc (prose éditoriale 760px Fraunces)
└─ [mode Expert] SolExpertGrid (historique actions/événements sur l'entité)
```

**Composants Sol à produire en Phase 1 du Lot 3** :
- `SolDetailPage.jsx` — wrapper avec breadcrumb
- `SolBreadcrumb.jsx` — chemin kicker avec retour
- `SolTimeline.jsx` — timeline verticale d'événements (append-only visual)
- `SolEntityCard.jsx` — card latérale avec infos statiques (PDL, surface, etc.)

**Presenters requis** : `buildEntityNarrative(entity)`, `buildEntityKpis(entity)`, `buildEntityTimeline(events)`.

**Pages concernées** : `/sites/:id` (Site360), `/regops/:id`, `/conformite/tertiaire/efa/:id`, `/diagnostic-conso`.

**Variantes autorisées** :
- Si l'entité a peu de dimensions : omettre SolLayerToggle, rester en Surface seule
- Si l'entité a une carte/plan : ajouter un bloc cartographique avant les KPIs

**Anti-patterns** :
- ❌ Pas de breadcrumb (l'utilisateur ne sait pas d'où il vient)
- ❌ KPIs génériques (doivent être contextuels à l'entité, pas les mêmes que la page parent)

---

**✅ Statut Lot 3 (v2.2-lot3-fiches, avril 2026)** :

4 composants Pattern C livrés et stabilisés — tous commités dans
[frontend/src/ui/sol/](../../frontend/src/ui/sol/) (commit `be11dd02`) :
`SolDetailPage`, `SolBreadcrumb`, `SolEntityCard`, `SolTimeline`.
Extension `SolTrajectoryChart.verticalMarkers` backward-compat
(commit `b8d1017c`).

3 pages migrées en Pattern C :
- [`/sites/:id`](../../frontend/src/pages/Site360Sol.jsx) — onglet Résumé only (scope-cut, legacy 8 onglets préservés) — commit `b85f7f60`
- [`/regops/:id`](../../frontend/src/pages/RegOpsSol.jsx) — commit `b38674b1` (bonus : AI endpoints non-bloquants)
- [`/conformite/tertiaire/efa/:id`](../../frontend/src/pages/EfaSol.jsx) — commit `b8d1017c` (3 jalons DT 2030/2040/2050)

1 page migrée en Pattern A hybride (exception Pattern C) :
- [`/diagnostic-conso`](../../frontend/src/pages/DiagnosticConsoSol.jsx) — commit `b0313cf4` + polish `cea98719`. **Cas d'usage Pattern A** plutôt que C : pas de `:id` dans la route, page multi-sites avec scope optionnel, sélecteur de période (usePeriodParams 90 j), comportement dashboard. Pattern C aurait forcé une sémantique métier cassée. Legacy body + EvidenceDrawer 4 tabs inline **intégralement préservés** (asset lourd hors scope Lot 3).

Cumul Sol : **25 composants** (Pattern C inclus), **12 pages migrées** (Phase 2+Lot 1+Lot 3), **~37 termes glossaire**, **~37 entrées business_errors**, **58 presenters purs**. Voir [BILAN_LOT_3.md](BILAN_LOT_3.md) pour détail complet.

Registre [REFONTE_FEATURES_PARKED.md](../REFONTE_FEATURES_PARKED.md) : 3 features EFA temporairement parkées (Export Mémobox UI + précheck + controls) — ré-intégration post-pilote si signal utilisateur.

---

### Pattern D — Wizard / Import

**Quand l'utiliser** : flux multi-étapes guidé (onboarding Sirene, import factures, création entité).

**Structure type** :
```
┌─ SolPageHeader (kicker + titre + rightSlot nombre d'étapes)
├─ SolStepper (horizontal, étape courante mise en avant)
├─ SolHeadline (phrase explicative de l'étape courante)
├─ [contenu étape : form / upload / preview]
├─ SolHero ou SolPreviewBox (preview de ce qui va se passer)
├─ SolLawList (garanties d'exécution — réversibilité, délai, audit)
└─ SolStepperFooter (précédent / suivant / valider)
```

**Composants Sol à produire en Phase 1 du Lot 4** :
- `SolWizardPage.jsx` — wrapper stepper
- `SolStepper.jsx` — horizontal, étapes numérotées
- `SolPreviewBox.jsx` — bg-canvas, Fraunces 14.5px, whitespace-preserve
- `SolLawList.jsx` — liste numérotée avec icônes garanties

**Presenters requis** : pas ou peu (logique dans la page, c'est du form).

**Pages concernées** : `/import`, `/onboarding/sirene` (+ toute future page wizard).

**Variantes autorisées** :
- Preview peut être un `<SolDrawer>` latéral au lieu d'un bloc inline si l'étape est simple
- Stepper peut être vertical si > 6 étapes (rare)

**Anti-patterns** :
- ❌ Submit irréversible sans SolLawList explicite (casse la loi 2 Sol : réversible ou délai de grâce)
- ❌ Pas de preview avant validation (casse la loi 1 : prévisualisation intégrale)

---

### Pattern E — Admin utilitaire

**Quand l'utiliser** : pages techniques (status système, connecteurs, métriques internes, dashboards admin).

**Structure type** :
```
┌─ SolPageHeader (kicker + titre + rightSlot actions admin)
├─ SolKpiRow (3 KPIs techniques : uptime, latency, error rate, etc.)
├─ SolSectionHead ("État des systèmes" · meta refresh interval)
├─ SolStatusGrid (cards avec status pill + mono details + dernière exécution)
├─ SolSectionHead ("Logs récents")
└─ SolLogTable (mono dense, scrollable, export CSV)
```

**Composants Sol à produire en Phase 1 du Lot 5** :
- `SolAdminPage.jsx` — wrapper
- `SolStatusGrid.jsx` — grid de status cards
- `SolStatusCard.jsx` — card individuelle (nom service + status pill + mono metrics + last run)
- `SolLogTable.jsx` — table mono dense avec highlighting de niveau (info/warn/error)

**Presenters requis** : `buildStatusCards(services)`, `buildLogRows(logs)`.

**Pages concernées** : `/status`, `/connectors`, `/admin/kb-metrics`, `/admin/cx-dashboard`, `/admin/enedis-health`.

**Variantes autorisées** :
- Remplacer SolLogTable par SolChart si la page est plus analytique (kb-metrics peut avoir un chart qualité)
- Ajouter actions admin directes (reset, refresh, seed) dans rightSlot du header

**Anti-patterns** :
- ❌ Copier le style narrative Sol (pas de kpi headline humain ici, on est en technique)
- ❌ Présenter les logs comme des week-cards (casse le registre)

---

### Pattern F — Explorer / KB

**Quand l'utiliser** : pages de recherche/exploration longform (base de connaissance, segmentation, règles métier).

**Structure type** :
```
┌─ SolPageHeader (kicker + titre + rightSlot search input)
├─ SolFacetPanel (latéral gauche, filtres à facettes)
├─ [résultat principal]
│   ├─ si liste : SolResultList (cards avec titre serif + body + source + tags)
│   └─ si détail : SolInspectDoc (prose éditoriale 760px Fraunces 15/1.7)
└─ SolSourceFootnote (sources en bas avec numérotation)
```

**Composants Sol à produire en Phase 1 du Lot 6** :
- `SolExplorerPage.jsx` — layout 2 colonnes facettes + contenu
- `SolFacetPanel.jsx` — panel latéral (sous le panel Sol) avec facettes checkbox/range
- `SolResultList.jsx` — liste de résultats avec tri
- `SolResultCard.jsx` — card de résultat (titre + extrait + source)
- `SolSearchInput.jsx` — input mono avec icône loupe, shortcut ⌘K

**Presenters requis** : `buildFacets(data)`, `buildResultCards(data)`.

**Pages concernées** : `/kb`, `/segmentation`, `/compliance/pipeline`, `/conformite/tertiaire` (hidden).

**Variantes autorisées** :
- Pas de facettes si la page est purement textuelle (alors Pattern C avec mode Inspect suffit)
- Mode Expert avec table dense des règles si la KB a une dimension relationnelle

**Anti-patterns** :
- ❌ Recherche qui reload la page (doit être instantanée côté client avec Fuse.js ou similaire déjà en place)
- ❌ Pas de sources/citations (casse la crédibilité B2B)

---

## Checklist par page (méthode Phase 0)

À exécuter pour chaque page individuelle, avant de la migrer.

1. **Identifier le pattern** (A/B/C/D/E/F) — si ambiguë, demander à Amine
2. **Lister les API calls** de la page main :
   ```bash
   grep -rn "import.*services/api\|useQuery\|useMutation" frontend/src/pages/<XxxPage>.jsx
   ```
3. **Lister les drawers/modales** existants et leur source :
   ```bash
   grep -rn "Drawer\|Modal\|SlideOver" frontend/src/pages/<XxxPage>.jsx
   ```
4. **Lister les filtres/tabs/segmented** actifs
5. **Écrire le mapping** zone maquette ↔ donnée API dans `docs/design/SOL_WIREFRAME_SPEC.md` section `<Page>`
6. **Créer `<Xxx>Sol.jsx`** à côté de `<Xxx>.jsx` existant (ne pas remplacer)
7. **Créer le presenter** `frontend/src/pages/<xxx>/sol_presenters.js`
8. **Router temporaire** : `/xxx` → `XxxSol.jsx` dans le worktree refonte · `/xxx-legacy` → `Xxx.jsx` pour comparaison
9. **Source-guards** auto avant commit
10. **Screenshots A/B obligatoires** dans `docs/design/screenshots/` avec nomenclature stricte :
    - `<page>_main_before.png` + `<page>_main_before_fold.png` (port 5173, legacy)
    - `<page>_refonte_after.png` + `<page>_refonte_after_fold.png` (port 5175, refonte)
    - Capturés via **Playwright headless** avec login réel `promeos@promeos.io` / `promeos2024`
    - Viewport **1440×900**, full page + fold (au-dessus du pli)
    - Utiliser l'helper `captureABPair(pageName, routePath)` de `tools/playwright/sol_refonte_helper.mjs`
    - Attendre 3 500 ms après navigation pour stabilisation des fetches parallèles
    - Dismisser `OnboardingOverlay` si présent avant screenshot

---

## Checklist transverse "zéro issue"

Avant chaque STOP GATE, vérifier :

- [ ] Tous menus `NavRegistry` visibles et fonctionnels
- [ ] Tous `QUICK_ACTIONS` (15) accessibles via Ctrl+K et sidebar
- [ ] Tous `COMMAND_SHORTCUTS` (10) fonctionnels
- [ ] `HIDDEN_PAGES` (7) accessibles uniquement via Ctrl+K
- [ ] Rôles (dg_owner, daf, acheteur, etc.) : ordre des modules dans le rail adapté via `getOrderedModules(role, isExpert)`
- [ ] Mode expert : 4 items admin apparaissent, Ctrl+Shift+X toggle fonctionnel
- [ ] Breadcrumb correct sur routes dynamiques (Site360, RegOps, EFA)
- [ ] Drawers existants (Evidence, Detail, ActionCenterSlideOver, CommandPalette) ouvrent et ferment correctement
- [ ] `OnboardingOverlay` et `ToastProvider` toujours montés
- [ ] ScopeContext appliqué : changement de scope recharge les données
- [ ] Espaces fines insécables U+202F partout (nombres, %, °, h, €)
- [ ] Guillemets chevrons « » jamais ""
- [ ] Source chip sur chaque KPI / graphe / tableau
- [ ] Build prod `npm run build` ne génère pas de warning au-dessus de baseline
- [ ] Tests Vitest + source-guards verts
- [ ] Port 5174 rendu conforme à la maquette · port 5173 (main) continue à vivre normalement

---

## Incohérences NavRegistry à remonter (PR séparé post-refonte)

À traiter après la refonte, dans un PR dédié sur main :

1. **`/sites-legacy/:id`** non mappé dans `ROUTE_MODULE_MAP` → tombe sur défaut cockpit. Ajouter à la map ou décider de supprimer cette route.
2. **6 routes admin étendues** (`/admin/audit`, `/admin/roles`, `/admin/assignments`, `/admin/kb-metrics`, `/admin/cx-dashboard`, `/admin/enedis-health`) non mappées explicitement → fonctionnent par prefix fallback mais fragile. Les ajouter à `ROUTE_MODULE_MAP`.
3. **`/diagnostic-conso`** mappé à Énergie mais ambigu selon contexte → trancher une fois pour toutes (probablement Énergie OK, mais vérifier que le header reflète ce module quand on arrive depuis Conformité).
4. **`/kb`, `/connectors`, `/segmentation`** mappés à admin mais accessibles via Ctrl+K à tout utilisateur → léger mismatch, l'utilisateur non-expert voit le rail admin s'activer. À décider : soit cacher le rail actif pour ces routes, soit mapper à un module plus neutre.

Ces corrections ne sont **pas** du scope refonte — elles sont des corrections de logique NavRegistry qui doivent vivre dans main pour ne pas diverger.

---

## Ordre d'exécution recommandé

| Étape | Livrable | Durée | Dépend de |
|---|---|---|---|
| 0 | Prompt Sprint 1-2 Cockpit + 5 pages flagship (en cours) | 2-3 j | — |
| 1 | Prompt **Lot 1 Dashboards** (3 pages : /, /conformite/aper, /monitoring) | 1 j | Étape 0 validée |
| 2 | Prompt **Lot 2 Listes** (10 pages) | 2 j | Étape 1 validée, composants Sol Pattern B produits |
| 3 | Prompt **Lot 3 Fiches détail** (4 pages) | 1,5 j | Étape 2 validée, composants Pattern C produits |
| 4 | Prompt **Lot 4 Wizards** (2 pages) | 0,5 j | Étape 3 validée |
| 5 | Prompt **Lot 5 Admin** (5 pages) | 1 j | Étape 4 validée |
| 6 | Prompt **Lot 6 Explorer/KB** (4 pages) | 1 j | Étape 5 validée |
| 7 | PR incohérences NavRegistry sur main | 0,5 j | Refonte mergée ou validée |
| 8 | Polish final + tag `v2.1-refonte-complete` | 0,5 j | Étape 6 validée |

**Total refonte complète : ~10 jours effectifs après le prompt en cours.**

---

## Définition d'une page "migrée OK"

Une page est considérée migrée si **toutes** ces conditions sont remplies :

1. Son `<Xxx>Sol.jsx` existe et fonctionne sur port 5174
2. Elle utilise uniquement des composants `ui/sol/*` (pas de composant V1 résiduel)
3. Aucun hex hardcodé, aucun fetch direct, aucun calcul métier dans la page
4. Son `sol_presenters.js` est testé par source-guards (pas d'appel API)
5. Les drawers/modales existants sont intégrés et fonctionnels
6. La grammaire française est respectée (espaces fines, chevrons, vouvoiement)
7. Les source chips sont présents sur tous les KPIs/graphes/tableaux
8. Screenshots avant/après existent dans `docs/design/screenshots/`
9. Tests verts, source-guards verts, build prod clean
10. Validation Amine au STOP GATE de la page

Une page qui ne remplit pas ces 10 conditions n'est **pas** migrée — peu importe qu'elle s'affiche correctement.
