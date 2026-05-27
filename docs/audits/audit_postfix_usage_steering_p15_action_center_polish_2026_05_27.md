# Audit postfix — Usage Steering P1.5 Action Center polish (2026-05-27)

**Branche** : `claude/usage-steering-p15-action-center-polish`
**Base** : `claude/refonte-sol2` après merge PR #319 (squash `2ee600d4`)
**Verdict** : 🟢 **GO MERGE** — boucle complète Pilotage → Centre d'Action V4 → retour source. Composant `PilotageSourceBackLink` livré (équivalent `BillingAnomalyBackLink` pour `domain=optimisation`). Mise en évidence site auto au retour. Playwright HELIOS : 0 console error, 0 network 4xx/5xx, boucle complète validée live.

---

## 1 — Phase 0 audit (avant code)

| Vérif | État | Action |
|---|---|---|
| Filtre BE `domain=optimisation` fonctionne | ✅ live HELIOS = 3 items | rien à faire |
| `DOMAIN_LABELS.optimisation = 'Optimisation énergétique'` | ✅ déjà OK | rien à faire |
| `ListFilterBar` dropdown inclut `optimisation` via `domainOrder` | ✅ déjà OK | rien à faire |
| Drawer affiche `<DomainChip>` | ✅ déjà OK | rien à faire |
| Composant back-link pour `domain=optimisation` | ❌ inexistant | **C2 à créer** |
| Auto-bascule scope au retour `?site=X` | ❌ inexistant | **C3 à ajouter** |

Phase 0 a permis d'éviter de reconstruire ce qui existe déjà (filtres, libellés). Le polish s'est concentré sur les 2 gaps réels.

---

## 2 — Livrables par chantier

### C1 — Vérification filtres + libellés (rien à modifier)

| Élément | Statut |
|---|---|
| BE `/api/v4/action-center/items?domain=optimisation` | ✅ HTTP 200, 3 items HELIOS |
| FE `DOMAIN_LABELS.optimisation = 'Optimisation énergétique'` | ✅ `constants/classification.js` |
| FE `ListFilterBar` dropdown domain | ✅ `domainOrder` inclut `optimisation`, label « Optimisation énergétique » |
| Aucune confusion avec Facturation / Conformité | ✅ 3 domains distincts dans dropdown |

Aucun code modifié pour C1 — fonctionnalité préexistante depuis P2-B C1.

### C2 — `PilotageSourceBackLink.jsx` (NEW)

**Fichier NEW** : `frontend/src/pages/action-center-v4/components/drawer/PilotageSourceBackLink.jsx` (66 lignes)

Pattern strictement aligné sur `BillingAnomalyBackLink` (P2-B C3) :
- Filter strict `item.domain === 'optimisation'` (anti-collision facturation/conformite).
- Regex `_PILOTAGE_REF_RE = /^pilotage:([a-z_]+):site:(\d+)/` extrait `insight_type` + `site_id` depuis `item.external_ref`.
- Mapping FR `_INSIGHT_LABEL_FR` pour rendre les 5 types insight en label client clair.
- `<Link to={item.source_url || /usages?tab=pilotage&site={id}}>` (fallback construction si BE absent).
- Style Sol success (émeraude pastel, cohérent avec sémantique « optimisation »).
- `data-testid="pilotage-source-back-link"`.

Affichage live : « Source : Pilotage des usages — site #42 · Consommation hors horaires ».

**Câblage** : `ItemDetailDrawer.jsx:200` ajoute `<PilotageSourceBackLink item={item} />` juste après `<BillingAnomalyBackLink item={item} />`, dans le body wrappé par `DrawerErrorBoundary`.

### C3 — Auto-bascule scope au retour `?site=X`

**Fichier** : `frontend/src/pages/UsagesDashboardPage.jsx:53-79`

```js
const { selectedSiteId, scopedSites, scope, setSite } = useScope();
const siteFromUrl = searchParams.get('site');

useEffect(() => {
  if (!siteFromUrl) return;
  const targetSiteId = Number(siteFromUrl);
  if (Number.isFinite(targetSiteId) && targetSiteId !== selectedSiteId) {
    setSite(targetSiteId);
  }
  // deps: [siteFromUrl] — pas de loop
}, [siteFromUrl]);
```

Au retour depuis `PilotageSourceBackLink`, l'URL contient `?tab=pilotage&site=X` → `useEffect` détecte `siteFromUrl` ≠ `selectedSiteId` → appel `setSite(X)`. ScopeBar (multi-niveaux) reflète automatiquement la sélection du site, et le `PilotageTab` re-fetch `getPilotageSummary({siteId: X})` filtré sur ce site.

---

## 3 — Smoke live HELIOS

```
GET /api/v4/action-center/items?domain=optimisation&limit=3 (HTTP 200)
  3 items dont 2 avec external_ref `pilotage:*`
```

### Playwright réel HELIOS

```
node + playwright (1.59.1) headless chromium 1440×900
→ login demo → boucle complète :

1. /action-center-v4?domain=optimisation
   rows filtre optimisation : 2

2. Drawer item optimisation (clic 1ère row)
   drawer ouvert                     : true
   PilotageSourceBackLink visible    : true
   href                              : /usages?tab=pilotage&site=42
   texte                             : "Source : Pilotage des usages — site #42 · Consommation hors horaires"

3. Clic back-link → /usages?tab=pilotage&site=42
   URL après clic                   : /usages?tab=pilotage&site=42
   pilotage-tab actif après retour  : true ✅

Console errors  : 0
Network 4xx/5xx : 0
```

Boucle complète **Centre d'Action V4 (filtré optimisation) → drawer → back-link → /usages?tab=pilotage&site=42 → onglet Pilotage actif** — **0 console error, 0 network 4xx/5xx, 0 navigation `/usage-steering`**.

---

## 4 — Tests anti-régression

| Suite | Résultat |
|---|---|
| BE `tests/source_guards/test_usage_steering_p15_polish_source_guards.py` (G1-G6) | **8/8 ✅** (nouveau) |
| BE source-guards cumul `-k "cockpit or billing or energie or usage_steering"` + endpoint sync-action + monitoring clamp | **103+ verts ✅** |
| FE `pages/cockpit/__tests__/` + `pages/action-center-v4/components/drawer/__tests__/` + `__tests__/ux-hardening.test.js` | **74/74 ✅** |
| **Total cumul** | **103+ BE + 74 FE = 177 tests verts** |

### Détail source-guards G1-G6

| ID | Vérification | Test |
|---|---|---|
| G1 | `DOMAIN_LABELS.optimisation = 'Optimisation énergétique'` + Facturation/Conformité distincts | `test_g1_domain_labels_optimisation_label_clair` |
| G2 | `ListFilterBar.domainOrder` inclut `optimisation` + import `DOMAIN_LABELS` | `test_g2_list_filter_bar_includes_optimisation` |
| G3 | `PilotageSourceBackLink.jsx` existe + regex `pilotage:*` + filter `domain === 'optimisation'` + testid + 5 mappings FR insight | `test_g3_pilotage_back_link_component_exists` + `test_g3_pilotage_back_link_shows_site_and_insight` |
| G4 | `ItemDetailDrawer` importe + rend `<PilotageSourceBackLink item={item} />` | `test_g4_drawer_imports_and_renders_pilotage_back_link` |
| G5 | `UsagesDashboardPage` lit `searchParams.get('site')` + appelle `setSite()` | `test_g5_usages_page_sets_site_from_url_param` |
| G6 | 0 `/usage-steering` dans back-link + 0 jargon `NEBCO`/`AOFD`/`Flex Intelligence` | `test_g6_no_usage_steering_in_back_link` + `test_g6_no_flex_jargon_in_back_link` |

---

## 5 — Critères d'acceptation brief (6/6 ✅)

| # | Critère | État |
|---|---|---|
| 1 | 0 console error | ✅ Playwright HELIOS (boucle complète) |
| 2 | 0 network 4xx/5xx golden path | ✅ Playwright + curl |
| 3 | Action visible dans Centre d'Action | ✅ `/action-center-v4?domain=optimisation` filtre 2 items pilotage |
| 4 | Retour source OK | ✅ Back-link rendu + clic → `/usages?tab=pilotage&site=42` + onglet Pilotage actif + scope auto-sélectionné |
| 5 | Aucun nouveau menu | ✅ G2 source-guard (NavRegistry inchangé) + composant interne `PilotageSourceBackLink` rendu dans drawer existant |
| 6 | Aucun écran fantôme | ✅ aucune nouvelle page créée — re-navigation vers `/usages?tab=pilotage` existant |

---

## 6 — Décisions clés

1. **Pattern aligné sur `BillingAnomalyBackLink`** : même style Sol pastel (émeraude pour optimisation vs ambre pour billing), même testid pattern (`pilotage-source-back-link`), même mécanique parser-extract-link. Cohérence cross-brique cardinale.
2. **Filter strict `domain === 'optimisation'`** : empêche le composant de s'afficher sur des items billing/conformite qui contiendraient accidentellement `pilotage:` dans `external_ref` (anti-collision défensive).
3. **`source_url` BE prioritaire** : si le BE expose `item.source_url` (post P0 #317), on l'utilise tel quel. Fallback construction `/usages?tab=pilotage&site={id}` si absent. Pattern strict « lecture pure » brief P0 §C2.
4. **`useEffect` deps = `[siteFromUrl]`** : évite la boucle infinie (`setSite` modifie `selectedSiteId` qui re-déclencherait le useEffect si listed in deps). Pattern « one-shot au mount + sur changement URL ».
5. **`Number.isFinite` + cast** : protection contre `?site=abc` ou `?site=` (cas dégénérés). Pas de `setSite(NaN)` silencieux.
6. **0 fichier modifié pour C1** : le filtre BE `domain=optimisation` + le libellé FR « Optimisation énergétique » + le dropdown existaient déjà depuis P2-B C1 et P0. Phase 0 audit a évité du travail redondant.

---

## 7 — Dette résiduelle

Aucune nouvelle dette créée. Dette héritée préservée :
- Audit menu Énergie #313 P1 (renommer label `/usages`, fusion `/usages-horaires`, IS11 audit)
- Audit Usage Steering P0 #317 dette résiduelle (Recharts sites homonymes seed HELIOS)

---

## Verdict

🟢 **GO MERGE** — Boucle Pilotage des usages → Centre d'Action V4 → retour source **complète et opérationnelle live HELIOS** :
- Filtre `domain=optimisation` fonctionnel + libellé « Optimisation énergétique » sans confusion
- Drawer expose le back-link « Source : Pilotage des usages — site #X · {insight_type FR} »
- Clic back-link → `/usages?tab=pilotage&site=X` avec auto-bascule scope sur le site cible
- 0 console error, 0 network 4xx/5xx, 0 nouveau menu, 0 écran fantôme
- 177 tests cumulés verts (103 BE + 74 FE)

Le sprint suivant (P2 — renderers partagés `<Heatmap7x24/>` + `<ProfileChart/>` + cleanup `/usages-horaires`) peut démarrer.
