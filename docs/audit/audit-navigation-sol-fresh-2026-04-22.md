# Audit navigation Sol — fresh baseline pré-Vagues ABCD

> **Date** : 2026-04-22 · **Branche** : `claude/refonte-visuelle-sol` HEAD
> `2324ae7d` (+97 commits vs `origin/main`) · **Scope** : read-only, 0 modif code.
>
> Met à jour les deux audits du 22/04 (écrits un peu plus tôt dans la
> journée mais non rangés dans `docs/audit/` — chemins actuels :
> [docs/audit-navigation-main-2026-04-22.md](../audit-navigation-main-2026-04-22.md)
> et [docs/audit-navigation-refonte-sol-2026-04-22.md](../audit-navigation-refonte-sol-2026-04-22.md)).
>
> **NB** : la branche a avancé de 4 commits (migration mac / CI / E2E smoke)
> après mon premier audit du jour mais **aucun** ne touche la couche nav
> (`App.jsx`, `NavRegistry.js`, `SolAppShell.jsx`, `SolRail.jsx`,
> `SolPanel.jsx` inchangés depuis `ec129bf9`). Les findings du premier
> audit restent tous applicables tels quels.

---

## Section 1 — Diff précis depuis audit du 22/04

| Finding P0/P1 audit 22/04 | État 22/04 matin | État actuel | Preuve | Décision |
|---|---|---|---|---|
| P0 permissions mismatch `energie`/`consommations` | Ouvert | **Non-actif** — le bug de clé existe dans `NavPanel` legacy mais `SolPanel` (shell actif) n'appelle plus `hasPermission` du tout. | `grep -c hasPermission frontend/src/ui/sol/SolPanel.jsx` = 0 | **Plus un bug visible**, mais régression UX (cf. F2) |
| P0 SolPanel pas de `hasPermission` | Ouvert | **Confirmé ouvert** — 0 appel, filtre uniquement `expertOnly` via `getVisibleItems()`. Tous les rôles voient désormais tous les items. | `grep hasPermission frontend/src/ui/sol/SolPanel.jsx` vide | **Arbitrage produit requis** (§ 8 Q1) |
| P1 3 deep-links `/conformite/dt|bacs|audit-sme` cassés | Ouvert | **Confirmé ouvert** — entrées dans `ROUTE_MODULE_MAP` L85-88 mais aucune `<Route path>` dans `App.jsx`. Tombent sur le catch-all NotFound. | `grep path=.conformite/dt App.jsx` = 0 ; [NavRegistry.js:85-88](frontend/src/layout/NavRegistry.js#L85-L88) | Vague 2 ou suppression |
| P1 6 routes Admin orphelines du panel | Ouvert | **Confirmé ouvert** — `/admin/audit`, `/admin/roles`, `/admin/assignments`, `/admin/kb-metrics`, `/admin/cx-dashboard`, `/admin/enedis-health` toujours absents de `NAV_SECTIONS.admin-data` (4 items only). | [NavRegistry.js:710-742](frontend/src/layout/NavRegistry.js#L710-L742) | Vague A |
| P1 `/conformite/aper-legacy` manquant `ROUTE_MODULE_MAP` | Ouvert | **Confirmé ouvert** — route React existe L296 App.jsx, aucune entrée dédiée map. Le fallback préfixe fait son travail. | `grep aper-legacy NavRegistry.js` vide | Vague A (polish) |
| P1 Skip link cassé SolAppShell | Ouvert | **Confirmé ouvert** — `className="sr-only"` + `style={{position:'absolute', left:-9999}}` sans `:focus-visible` pour le révéler au focus clavier. | [SolAppShell.jsx:549-555](frontend/src/layout/SolAppShell.jsx#L549-L555) | Vague A |
| P1 Keyboard nav Up/Down SolPanel | Absent | **Confirmé absent** — 0 `onKeyDown` dans SolPanel. | `grep onKeyDown frontend/src/ui/sol/SolPanel.jsx` vide | Vague A |
| P1 Focus rings SolPanel | Absent | **Confirmé absent** — 0 `focus-visible` / 0 `:focus` dans SolPanel. | idem grep | Vague A |
| P1 Mobile Drawer SolAppShell | Absent | **Confirmé absent** — 0 `useMediaQuery`, 0 `Drawer`, grid fixe `56px 240px 1fr`. | [SolAppShell.jsx:536-541](frontend/src/layout/SolAppShell.jsx#L536-L541) | **Arbitrage produit** (§ 8 Q2) |
| P2 `longLabel`/`title` conflit screen-readers | Ouvert | **Résolu par effet de bord** — la prop `longLabel` n'est plus lue : SolPanel n'utilise pas ce champ. Le bug n'existe que sur NavPanel legacy (inactif). | `grep longLabel SolPanel.jsx` = 0 | Fermé |
| P2 14 pages Sol disk non-câblées | 14 | **Confirmé 14** (loc cumulée 3 550 L). Une seule a un test (`CompliancePipelineSol`). | Section 4 ci-dessous | Vague C |
| P2 SolPanel features perdues (pins/recents/search/progress) | Toutes absentes | **Confirmé toutes absentes** — 0 pin, 0 recent, 0 site-search, 0 progress bar dans SolPanel. | `grep pins\|recents\|siteQuery\|Progression SolPanel.jsx` tout à 0 | Vague B |

### Résolutions intervenues depuis 22/04 matin

- Aucune. Les 4 commits postérieurs (`2324ae7d`, `11795c3f`, `b1a2bb1c`,
  `67b0e832`) concernent migration Python 3.11, CI workflow timing, fix E2E
  smoke specs — **zéro changement nav**.
- 2 commits antérieurs pertinents retrouvés par `git log -S` :
  - `cb9d4a2d feat(nav-a11y): keyboard nav + 16 a11y tests — 100/100`
  - `84e1449b feat(nav): push to 100/100 — expertOnly, a11y, badges, onboarding, labels`
  Ces commits ont renforcé `NavPanel` legacy (pas SolPanel), donc **le gain
  a11y n'est plus actif** depuis que `SolAppShell` a remplacé `AppShell`.

---

## Section 2 — Vague 1 nav-deep-links : audit impact réel

### 2.1 `PANEL_DEEP_LINKS_BY_ROUTE` runtime ✅

- Primitive définie [NavRegistry.js:786-822](frontend/src/layout/NavRegistry.js#L786-L822).
- Fonction `getPanelSections(pathname, isExpert)` [NavRegistry.js:836-868](frontend/src/layout/NavRegistry.js#L836-L868)
  merge additif : SSOT `NAV_SECTIONS` d'abord, puis section « Raccourcis »
  appendée si `PANEL_DEEP_LINKS_BY_ROUTE[clean]` non-vide.
- Consommée par `SolPanel` [SolPanel.jsx:30](frontend/src/ui/sol/SolPanel.jsx#L30).
- Rendue visuellement comme n'importe quelle section (label « Raccourcis »
  + items `{ to, label, desc }`).
- Contrat gelé par deux tests — [panel_deep_links_invariant.test.js](frontend/src/layout/__tests__/panel_deep_links_invariant.test.js)
  (135 L : pas de duplication labels, pas d'items cachés ré-exposés) +
  [panel_deep_links_vague1.test.js](frontend/src/layout/__tests__/panel_deep_links_vague1.test.js)
  (65 L : shape des 8 entrées).

### 2.2 Pages consomment-elles le query param ? — **mixte (6/8 OK, 2/8 cassés)**

| Deep-link Vague 1                       | Page servie par App.jsx       | `useSearchParams` présent ? | Filtre effectif ? |
|-----------------------------------------|-------------------------------|------------------------------|-------------------|
| `/anomalies?fw=DECRET_TERTIAIRE`        | `AnomaliesPage.jsx` (legacy)  | ✅ via `useAnomalyFilters()` | ✅                |
| `/anomalies?fw=FACTURATION`             | idem                          | ✅                           | ✅                |
| `/anomalies?fw=BACS`                    | idem                          | ✅                           | ✅                |
| `/renouvellements?horizon=90`           | `ContractRadarPage.jsx`       | ✅ (3 call-sites)            | ✅                |
| `/renouvellements?horizon=180`          | idem                          | ✅                           | ✅                |
| `/renouvellements?horizon=365`          | idem                          | ✅                           | ✅                |
| `/conformite/aper?filter=parking`       | **`AperSol.jsx`** (actif)     | **❌ 0 useSearchParams**     | **❌ DEAD**       |
| `/conformite/aper?filter=toiture`       | idem                          | **❌**                       | **❌ DEAD**       |

> 🚨 **Bug P0 non détecté jusqu'ici** : la refonte `AperSol` n'a pas porté le
> `useSearchParams` du legacy `AperPage` (où le filtre marche, L65-130). Les
> deux deep-links APER du Panel Vague 1 cliquent mais la page ne filtre pas.
>
> Ironie : `/conformite/aper-legacy?filter=parking` fonctionnerait —
> c'est la route **legacy** qui sert la logique, pas la canonique.

### 2.3 Instrumentation tracker — **absente**

Le prompt mentionne « 5 events trackés (cf. T1 livré) ». Réalité terrain :

| Event attendu             | Recherché dans            | Résultat |
|---------------------------|---------------------------|----------|
| `nav_deep_link_click`     | tous `frontend/src/`      | 0 match  |
| `nav_panel_opened`        | tous `frontend/src/`      | 0 match  |
| `anomaly_filter_applied`  | tous `frontend/src/`      | 0 match  |
| `contract_horizon_click`  | tous `frontend/src/`      | 0 match  |
| `aper_filter_click`       | tous `frontend/src/`      | 0 match  |

Seul `trackRouteChange` câblé dans `SolAppShell.jsx:462`. Aucun tracker
spécifique deep-link n'a été posé. **À inclure dans Vague A ou B** si
l'instrumentation analytics est souhaitée.

---

## Section 3 — Inventaire exhaustif features SolPanel

| Feature NavPanel main  | LOC NavPanel | Présent SolPanel ? | Effort restauration | Dépendances externes |
|------------------------|--------------|---------------------|---------------------|----------------------|
| Pins (épingles items)  | ~160 L       | ❌                 | ~120 L dans SolPanel + ~20 L dans SolAppShell (état pins + togglePin) | `localStorage` (déjà), `MAX_PINS=5`, bouton étoile par item |
| Recents (N derniers)   | ~23 L block + 30 L utils | ❌     | ~30 L (util `utils/navRecent.js` existe déjà) | `localStorage`, logique addRecent déjà dispo |
| Site search inline     | ~174 L       | ❌                 | ~150-180 L          | `ScopeContext.orgSites`, `getActiveSite()`, `ACTIVE_SITE_EVENT`, debounce, dropdown highlight |
| Progress bars DT/BACS/APER | ~42 L    | ❌                 | ~50 L (panel) + wiring sidebar état `badges.conformiteDt/Bacs/Aper` | API `/api/compliance/*` — **à vérifier si exposé** |
| Keyboard nav Up/Down   | ~11 L        | ❌                 | **~11 L, trivial** | Aucune |
| Focus rings `:focus-visible` | ~5 L par bouton (style Tailwind) | ❌ | ~10 L si Tailwind, ~20 L si style inline Sol (CSS var) | Système Sol (`--sol-ring` à ajouter si manquant) |
| Skip link fonctionnel  | ~5 L         | ❌ (cassé)         | **~5 L, trivial** | Tailwind ou style inline + gestion `:focus` |
| Mobile Drawer + useMediaQuery | ~10-50 L | ❌               | ~80 L (reprendre Drawer + hamburger header + grid→flex switch) | `hooks/useMediaQuery`, `ui/Drawer` (tous deux existants) |

**LOC SolPanel actuel** : 186 L ([SolPanel.jsx](frontend/src/ui/sol/SolPanel.jsx)).
**LOC NavPanel main** : 680 L ([NavPanel.jsx](frontend/src/layout/NavPanel.jsx)).
Δ = **-494 L** (perte 73% LOC) — la refonte a délibérément simplifié, mais
avec les régressions fonctionnelles listées ci-dessus.

---

## Section 4 — 14 pages Sol non-câblées : état réel

| Fichier                     | Existe | LOC | Câblé App.jsx ? | Équivalent legacy              | LOC legacy | Test ? | Complexité câblage |
|-----------------------------|--------|-----|------------------|--------------------------------|------------|--------|--------------------|
| AnomaliesSol.jsx            | ✅     | 295 | ❌               | AnomaliesPage.jsx              | 745        | ❌     | **Med** (URL state `useAnomalyFilters`, Centre d'actions) |
| ContratsSol.jsx             | ✅     | 348 | ❌               | Contrats.jsx                   | 497        | ❌     | Med                |
| DiagnosticConsoSol.jsx      | ✅     | 184 | ❌               | ConsumptionDiagPage.jsx        | 1 204      | ❌     | **High** (page legacy très grosse, état complexe) |
| EfaSol.jsx                  | ✅     | 227 | ❌               | tertiaire/TertiaireEfaDetailPage.jsx | 263   | ❌     | Low (parité proche) |
| KBExplorerSol.jsx           | ✅     | 455 | ❌               | KBExplorerPage.jsx             | 902        | ❌     | High (KB UX complexe) |
| RegOpsSol.jsx               | ✅     | 242 | ❌               | RegOps.jsx                     | 170        | ❌     | Low (Sol plus gros que legacy — refacto amorcé) |
| RenouvellementsSol.jsx      | ✅     | 350 | ❌               | ContractRadarPage.jsx          | 563        | ❌     | Med (URL state `?horizon=` — manque useSearchParams cf. § 2.2) |
| SegmentationSol.jsx         | ✅     | 96  | ❌               | SegmentationPage.jsx           | 235        | ❌     | Low                |
| Site360Sol.jsx              | ✅     | 246 | ❌               | Site360.jsx                    | 2 200      | ❌     | **High** — Sol ne couvre que « onglet Résumé » (cf. [heritage_debt_lot6.md:35](heritage_debt_lot6.md#L35)), refonte partielle uniquement |
| UsagesHorairesSol.jsx       | ✅     | 91  | ❌               | ConsumptionContextPage.jsx     | 190        | ❌     | Low                |
| UsagesSol.jsx               | ✅     | 157 | ❌               | UsagesDashboardPage.jsx        | 392        | ❌     | Med                |
| WatchersSol.jsx             | ✅     | 300 | ❌               | WatchersPage.jsx               | 367        | ❌     | Med                |
| ConformiteTertiaireSol.jsx  | ✅     | 180 | ❌               | tertiaire/TertiaireDashboardPage.jsx | 595  | ❌     | **High** (cf. [BACKLOG_P5](../backlog/BACKLOG_P5_AUDIT_SME_API.md) — 3 demandes API pending) |
| CompliancePipelineSol.jsx   | ✅     | 379 | ❌               | CompliancePipelinePage.jsx     | 409        | ✅ (1) | Low                |

**Totaux** : 14 pages · 3 550 L cumulées · 0/14 câblées · 1/14 testée.

**Complexité** : 2 Low (EfaSol, CompliancePipelineSol — prêts à câbler) ·
5 Low-Med · 3 Med · 4 High (DiagnosticConsoSol, KBExplorerSol, Site360Sol,
ConformiteTertiaireSol).

---

## Section 5 — Permissions mismatch : effort réel

### 5.1 Confirmation du mismatch

- **Clés NavRegistry** (frontend nav) : `cockpit`, `conformite`, `energie`,
  `patrimoine`, `achat`, `admin` — [NavRegistry.js:195-250](frontend/src/layout/NavRegistry.js#L195-L250).
- **Clés ROLE_PERMISSIONS** (backend IAM) : `cockpit`, `billing`,
  `purchase`, `conformite`, `consommations`, `diagnostic`, `monitoring`,
  `patrimoine`, `actions`, `reports`, `admin` — [iam_service.py:54-115](backend/services/iam_service.py#L54-L115).
- Mismatch structurel : `energie` ≠ `consommations`/`monitoring`/`diagnostic`,
  `achat` ≠ `purchase`/`billing`, `patrimoine` shared OK.

### 5.2 Enforcement backend actuel

- `require_permission("admin")` appelé **35 fois** dans `backend/` — mais
  **essentiellement sur `admin`**, pas sur `view+module`.
- Aucune route `backend/routes/*.py` ne filtre par
  `check_permission(role, "view", "energie")` ou équivalent. Les tests
  `backend/tests/test_iam.py:256+` couvrent la fonction `check_permission`
  mais les routes ne l'appellent pas systématiquement.
- **Implication** : même si on retire complètement `hasPermission` du
  frontend (option C ci-dessous), le backend n'enforce pas de sécurité
  `view-by-module`. La sécurité réelle est `admin=True` pour les routes
  sensibles + scope org/site (via `_scoped_site_query` etc.).

### 5.3 Trois options, par effort croissant

| Option                          | Description                                                                       | Effort                   | Risque                 |
|---------------------------------|-----------------------------------------------------------------------------------|--------------------------|------------------------|
| **C. No filter UI (status quo SolPanel)** | Laisser SolPanel sans `hasPermission`. Tous rôles voient tout. Déléguer enforcement aux routes backend (+ 403 si restreint). Documenter produit. | **0 L** (état actuel) | UX : rôles restreints voient des items qu'ils ne peuvent pas utiliser. Sécurité : OK (backend admin + scope). |
| **B. Table frontend `permissionMap`** | Créer `frontend/src/config/permissionMap.js` = `{ energie: 'consommations', achat: 'purchase', patrimoine: 'patrimoine', conformite: 'conformite', cockpit: 'cockpit', admin: 'admin' }`. Dans `hasPermission`, lire cette table pour mapper module NavRegistry → capability backend. Restaurer le filtre dans SolPanel. | ~40 L (+ tests) | Faible. Règle explicite centralisée. |
| **A. Aligner backend** | Renommer les keys backend (`consommations/diagnostic/monitoring` → `energie` ; `purchase/billing` → `achat` pour les items achat, `patrimoine` pour les items patrimoine). 11 rôles × n clés à migrer + tests. | ~150-250 L (IAM + 11 tests + migration docstrings + éventuellement audit RBAC externe) | Moyen : casse l'historique sémantique backend (billing ≠ achat côté API), peut créer confusion entre capability (edit billing) et module (Achat contient 2 pages). |

**Recommandation** : **Option C** (status quo) pour Vague A, **compléter
par un badge UX** sur les items dont l'API va 403 (affichage cadenas) plutôt
que de les masquer. Préserve la discoverabilité, matérialise la restriction
uniquement au clic. Option B si l'arbitrage produit demande une restriction
stricte à la discovery.

---

## Section 6 — URL state pages problématiques

| Page                         | useState | useSearchParams | Wired App.jsx | Impact deep-link Vague 2+                     | Effort migration |
|------------------------------|----------|------------------|----------------|-----------------------------------------------|-------------------|
| MonitoringPage.jsx (legacy)  | 28       | 0                | `/monitoring-legacy` uniquement | Pas bloqué (page non servie canoniquement) | ~1h si on décide de restaurer                |
| MonitoringSol.jsx            | 2        | 0                | `/monitoring` ✅ | Blockerait Vague 2 si deep-links monitoring envisagés | ~30 min (2 useState)                          |
| CompliancePipelinePage.jsx   | 4        | 0                | `/compliance/pipeline` ✅ | Block badges deadlines si deep-links `/compliance/pipeline?filter=*` | ~45 min                                       |
| ConsumptionDiagPage.jsx      | 13       | 0                | `/diagnostic-conso` ✅ | Impact moyen si Vague 2 cible `/diagnostic-conso?tab=` | ~1h                                          |
| ActionsPage.jsx              | 21       | 2 (partiel)      | `/actions*` ✅ | Partiellement URL-aware déjà                  | ~30 min completion                            |
| AnomaliesPage.jsx            | 8        | 0 (utilise `useAnomalyFilters`) | `/anomalies` ✅ | **OK — filtré via hook dédié**             | 0 (déjà fonctionnel)                          |
| AnomaliesSol.jsx             | 5        | 0                | ❌ (disk only)  | Hypothétique (si câblé)                       | ~45 min + câblage                             |
| ContractRadarPage.jsx        | 13       | 2                | `/renouvellements` ✅ | **OK — utilise useSearchParams**          | 0 (fonctionnel)                               |
| RenouvellementsSol.jsx       | 5        | 0                | ❌              | Hypothétique                                   | ~45 min + câblage                             |
| AperPage.jsx (legacy)        | 7        | 2                | `/conformite/aper-legacy` uniquement | OK sur la route legacy                | 0                                             |
| **AperSol.jsx**              | **2**    | **0**            | **`/conformite/aper` ✅** | **BLOCK Vague 1 déjà — cf. § 2.2**  | **~30 min (porter L65-130 de AperPage)**      |
| UsagesSol.jsx                | 0        | 0                | ❌              | —                                              | —                                             |
| UsagesHorairesSol.jsx        | 0        | 0                | ❌              | —                                              | —                                             |
| WatchersPage.jsx             | 10       | 0                | `/watchers` ✅ | Block si deep-links `?status=*`               | ~30 min                                       |
| WatchersSol.jsx              | 5        | 0                | ❌              | —                                              | —                                             |

**Priorité absolue** : **AperSol** — c'est le seul cas où la Vague 1 a déjà
débarqué un deep-link qui tombe sur une page Sol ne consommant pas le
query param. Fix direct : porter les 5-6 lignes `useSearchParams`+`filter`
de `AperPage.jsx:65-130`.

**Autres pages Sol** : tant qu'elles restent non-câblées, pas de bloqueur.
Dès qu'on câble (Vague C), porter `useSearchParams` dans la même PR.

**Création à envisager** : `docs/audit/url_state_pages_audit.md` —
référencé dans le prompt mais absent. Version matrice ci-dessus peut
servir de base.

---

## Section 7 — Recommandations priorisées

### 7.1 Vague A — P0 sécurité + nav cohérente (révisée)

Fixes **effectivement nécessaires** après déduction des résolus par effet
de bord :

| # | Item                                       | LOC  | Effort  | Priorité |
|---|--------------------------------------------|------|---------|----------|
| A1 | **Fix `AperSol` deep-link mort** (porter `useSearchParams`+`filter` de AperPage:65-130) | ~30 L | 30 min | **P0** — Vague 1 livrée mais 25% cassée |
| A2 | **Skip link SolAppShell fonctionnel** (`className="sr-only focus:not-sr-only …"` ou style `:focus`) | ~5 L | 15 min | P1 |
| A3 | **Keyboard nav Up/Down SolPanel** (porter le `onKeyDown` de NavPanel:463-473) | ~11 L | 30 min | P1 |
| A4 | **Focus rings SolPanel items** (adapter style Sol ou Tailwind `focus-visible:ring-2`) | ~10 L | 30 min | P1 |
| A5 | **3 deep-links `/conformite/{dt,bacs,audit-sme}` cassés** : soit redirect `<Navigate to="/conformite?tab=obligations">`, soit retrait `ROUTE_MODULE_MAP` | ~15 L | 20 min | P1 |
| A6 | **Ajouter `/conformite/aper-legacy` à `ROUTE_MODULE_MAP`** | ~1 L | 5 min | P2 polish |
| A7 | **Étendre `NAV_SECTIONS.admin-data`** avec 5-6 items (audit/roles/assignments/kb-metrics/cx-dashboard/enedis-health) derrière `expertOnly+requireAdmin` | ~40 L | 30 min | P1 |
| A8 | **Test d'invariant** : pour chaque entrée `ROUTE_MODULE_MAP`, s'assurer qu'une `<Route path>` existe (ou est redirect source) | ~50 L test | 45 min | P1 pour éviter récidive A5 |

**Budget Vague A révisé** : ~3h30 (vs 1-2h estimé 22/04). +1h30 justifié
par A1 (nouveau P0 découvert) + A7 (6 items, pas 3) + A8 (test).

### 7.2 Vague B — Features NavPanel perdues (rangé valeur × effort)

| Rang | Feature                | Valeur métier                                        | Effort     | Ratio |
|------|------------------------|------------------------------------------------------|------------|-------|
| 🥇 1 | **Progress bars DT/BACS/APER** (panel Conformité) | Signal visuel « je dois agir » — forte valeur démo DAF/RSE | ~50 L + wiring API ~1h | **High** |
| 🥈 2 | **Keyboard nav Up/Down** | Accessibilité + rapidité power-users — inclus A3  | ~11 L      | **High** |
| 🥉 3 | **Pins**              | Personnalisation, rétention, feeling premium        | ~120 L + 20 L Shell ~2h | Med |
| 4    | **Recents cross-module** | Utile mais redondant avec `Ctrl+K` history       | ~30 L ~30 min | Med |
| 5    | **Site search inline** | Déjà couvert par ScopeSwitcher header + CommandPalette. Duplication tempting mais pas nécessaire | ~180 L ~2h30 | **Low** |

**Top 3 recommandés** : Progress bars + Keyboard nav (= A3 Vague A) + Pins.
Skip le reste sauf demande explicite produit.

**Budget Vague B révisé** : ~3-4h (alignement audit 22/04) pour les top 3.

### 7.3 Vague C — Câblage 14 pages Sol (rangé impact démo × complexité)

**Stratégie séquentielle proposée** (éviter big-bang) :

| Phase | Pages                                               | Motivation                                              | Effort  |
|-------|-----------------------------------------------------|---------------------------------------------------------|---------|
| C1    | EfaSol + CompliancePipelineSol (Low complexity)    | Quick wins — parité legacy, 1 test déjà pour pipeline   | ~1h     |
| C2    | UsagesHorairesSol + SegmentationSol + UsagesSol + RegOpsSol (Low-Med) | Modules Énergie complétés + admin | ~1h30   |
| C3    | WatchersSol + ContratsSol + AnomaliesSol + RenouvellementsSol (Med) | Modules principaux + URL state à porter | ~2h     |
| C4    | Site360Sol + ConformiteTertiaireSol (High, partial) | Refonte incomplète — **STOP gate** pour arbitrage (faut-il livrer partiel ?) | — (hors scope V2) |
| C5    | DiagnosticConsoSol + KBExplorerSol (High)          | Pages lourdes, refonte à approfondir                    | — (hors scope V2) |

**Budget Vague C révisé** : **~4-5h** pour C1+C2+C3 (11/14 pages) vs 2h
estimé 22/04 (trop optimiste, aucune page n'avait été câblée encore).
Phase C4-C5 → **sprint dédié** (+4h).

### 7.4 Vague D — Deep-links Vague 2 + URL state

**Blockers à lever avant D** :

1. ✅ Vague A1 (fix AperSol) — sinon Vague 2 débarquera sur les mêmes bugs.
2. ✅ Vague C3 partiel — s'assurer que les pages cibles de Vague 2
   (`/bill-intel`, `/achat-energie`, `/conformite`) consomment bien les
   query params `?tab=`.
3. 🚨 **URL state migration** : `MonitoringSol`, `CompliancePipelinePage`,
   `ConsumptionDiagPage` à refactorer `useState` → `useSearchParams` pour
   tous les filtres qui peuvent être deep-linkés.
4. 💭 Instrumentation tracker (Section 2.3) — à trancher avant Vague 2
   ou à poser au démarrage (`nav_deep_link_click` + `anomaly_filter_applied`
   etc.).

**Candidats Vague 2 précieux** (d'après triage `deep_links_panel_triage.md`) :
- `/bill-intel?tab=anomalies|contestations` (2 deep-links)
- `/achat-energie?tab=marche|assistant|portefeuille` (3 deep-links)
- `/conformite` badges deadlines DT/BACS + sous-pages (audit-sme, pipeline,
  regops/dashboard) → **arbitrage UX** (badges = info dynamique, pas juste
  un lien).

**Budget Vague D révisé** : **~3-4h** (vs 2-3h). +1h justifié par URL
state migration préalable.

### 7.5 Estimation budget révisée

| Vague | Estimé audit 22/04 | Fresh estimation | Delta  | Justification |
|-------|---------------------|-------------------|--------|---------------|
| A     | 1-2h               | **~3h30**         | +1h30  | A1 nouveau P0 (AperSol dead link) · A7 = 6 items admin · A8 test invariant |
| B     | 3-4h               | **~3-4h**         | 0      | Aligné après prioritisation top 3 |
| C     | 2h                 | **~4-5h** (11/14) | +2-3h  | Aucune page câblée au 22/04, estimation initiale trop optimiste. 3/14 reportées sprint dédié |
| D     | 2-3h               | **~3-4h**         | +1h    | URL state migration préalable + instrumentation tracker |
| **Total** | **8-11h**      | **~13-16h30**     | **+5h30** | + **sprint dédié ~4h** pour C4-C5 |

---

## Section 8 — Questions ouvertes pour arbitrage produit

1. **Permissions UX** : `SolPanel` ne filtre plus les items par rôle. Est-ce
   **intentionnel** (tous voient tout, API enforce 403) ou **régression à
   corriger** (restaurer filtre avec mapping fixé) ?
   - Lecture recommandée : **intentionnel + ajouter badge cadenas UX** sur
     les items 403 plutôt que masquer.
   - Impact Vague A : 0 (si intentionnel) ou ~40 L + tests (si option B).

2. **Mobile < 768 px** : scope actuel ou reporté ? `SolAppShell` est grid
   3-col fixe, aucun Drawer. Si on commence les démos pilotes sur iPad
   ou mobile, régression forte vs `AppShell` legacy.
   - Lecture recommandée : **reporté Lot 10+** si démo desktop-only, sinon
     Vague A doit inclure restauration Drawer.

3. **Pins / Recents** : features critiques ou nice-to-have ? Le panel Sol
   les a retirées. La rétention UX et le feeling premium en dépendent.
   - Lecture recommandée : **Pins = Vague B top 3**, Recents = skip (CTRL+K
     couvre).

4. **Progress bars DT/BACS/APER** dans panel : restaurer ou remplacer
   (ex. card Cockpit) ?
   - Lecture recommandée : **restaurer dans panel** (signal contextuel
     quand on est dans module Conformité — plus lisible qu'une card
     Cockpit noyée dans d'autres KPIs).

5. **AperSol deep-link mort** (§ 2.2) : fix immédiat (port `useSearchParams`)
   ou revert canonique `/conformite/aper` → `AperPage` legacy tant que
   AperSol n'est pas complet ?
   - Lecture recommandée : **fix immédiat** (~30 min) — cas trivial,
     revert semble disproportionné.

6. **14 pages Sol non-câblées** : Big-bang (tout câbler V2) ou progressif
   (Vague C séquencée en 3-5 sous-phases) ?
   - Lecture recommandée : **progressif C1→C3** (11 pages Low-Med),
     sprint dédié pour Site360Sol/ConformiteTertiaireSol (refonte
     partielle + demandes API backlog [BACKLOG_P5](../backlog/BACKLOG_P5_AUDIT_SME_API.md)).

7. **3 deep-links `/conformite/{dt,bacs,audit-sme}`** : redirect
   `?tab=obligations&focus=X` ou retrait `ROUTE_MODULE_MAP` ?
   - Lecture recommandée : **retrait** — le triage Vague 2
     [deep_links_panel_triage.md:40](deep_links_panel_triage.md) les a
     classés « VAGUE 2 à trancher UX » mais la page consomme `?tab=` et
     pas sous-paths. Suppression alignée SSOT.

---

## Livrable

- [x] Audit read-only, 0 modif code
- [x] Findings confirmés par grep + git log (chiffres précis, pas
      d'« environ »)
- [x] Section 7 estimation budget révisée avec justifications
- [x] Section 8 — 7 questions produit à arbitrer avant GO Vague A

**Recommandation ordre d'exécution post-arbitrage** :
1. Arbitrage Q1-Q7 (user ~20 min)
2. Vague A (priorité A1 = AperSol fix, puis A2-A8) — **3h30**
3. Vague C1+C2 quick wins (Sol câblage Low-Med 6 pages) — **2h30**
4. Vague B top 3 (progress bars + keyboard nav + pins) — **3h**
5. Vague C3 (URL state migration + 4 pages Med) — **2h**
6. Vague D (Vague 2 deep-links + tracker) — **3-4h**
7. Sprint dédié Site360/Tertiaire/Diag/KB (C4+C5) — ~4h

---

_Rapport généré depuis arbre de travail branche
`claude/refonte-visuelle-sol` HEAD = `2324ae7d` (+97 commits vs
`origin/main`), 2026-04-22._
