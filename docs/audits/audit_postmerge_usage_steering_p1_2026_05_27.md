# Audit postmerge — Usage Steering P1 4ᵉ onglet (2026-05-27)

**Branche** : `claude/postmerge-usage-steering-p1-smoke`
**Base** : `claude/refonte-sol2` après merge PR #318 (squash `36b8939d`)
**Verdict** : 🟢 **GO** — Le 4ᵉ onglet « Pilotage des usages » reste opérationnel post-merge. Playwright HELIOS : **0 console error · 0 network 4xx/5xx · 0 navigation vers `/usage-steering`**. Action idempotente confirmée (1er run 201 / 2e run 200 même `item_id` / 3e run après clôture = HTTP 409 ACTION_CLOSED non ressuscitée). ActionLink source vers `/usages?tab=pilotage&site=42` peuplée.

---

## 1 — Smoke `/usages?tab=pilotage` ✅

| Critère brief | Statut |
|---|---|
| Onglet visible | ✅ `pilotage-tab` testid visible |
| 3 cartes max above-the-fold | ✅ Playwright = 3 `article[data-testid^=pilotage-card-]` (BE expose 5 candidates, FE limite à `top3`) |
| Banner data-gap si applicable | ✅ `pilotage-tab-data-gap` testid visible (8 insights HELIOS tous data_gap) |
| EmptyState si aucun insight | ✅ couvert par test FE `pilotage-tab-empty` (non déclenché sur HELIOS car insights présents) |
| Détails expert repliés | ✅ `<details>` « Détails expert (source, période, confiance) » présent en `closed` par défaut |

---

## 2 — Action Center V4 — Création + idempotence + clôture

### 2.1 Création (1er POST)

```
POST /api/usages/pilotage/sync-action
  payload : { insight_type: "hors_horaires", site_id: 42,
              external_ref: "pilotage:hors_horaires:site:42-postmerge", ... }
  → HTTP 201
  → { created: true, item_id: "b9246a96-...", domain: "optimisation",
      kind: "recommendation", priority_bracket: "P2" }
```

### 2.2 Idempotence (2e POST identique)

```
POST /api/usages/pilotage/sync-action (même payload)
  → HTTP 200
  → { created: false, item_id: "b9246a96-..." (même item) }
```

### 2.3 Action visible dans le Centre d'Action V4

```
GET /api/v4/action-center/items/b9246a96-...
  title        : Postmerge smoke test
  domain       : optimisation
  external_ref : pilotage:hors_horaires:site:42-postmerge
  source_url   : /usages?tab=pilotage&site=42
  lifecycle    : new
```

### 2.4 ActionLink source

```
GET /api/v4/action-center/items/b9246a96-.../links
  total : 1
  link  : target_module=energie, relation=caused_by, link_type=source
```

Drawer V4 LinksTab rendra le CTA « Voir la source » → `/usages?tab=pilotage&site=42` (back-link canonique).

### 2.5 Action CLOSED — non ressuscitée (brief P1 C3)

```
PATCH /items/b9246a96-.../lifecycle  { new_state: "closed", closure_reason: "resolved" }
  → HTTP 200, lifecycle_state = closed

POST /api/usages/pilotage/sync-action (même external_ref)
  → HTTP 409
  → { code: "ACTION_CLOSED", lifecycle_state: "closed" }
```

L'item reste `closed` ; aucune nouvelle création ; UX FE rend un message « Action clôturée — non recréée. » (testid `result.status === 'closed'`).

---

## 3 — Non-régression

### 3.1 Anti-régression `/usage-steering`

| Vérification | Statut |
|---|---|
| 0 occurrence `/usage-steering` dans FE (sources + tests) | ✅ source-guards G1 P0 + P1 verts |
| 0 navigation Playwright vers `/usage-steering` | ✅ `framenavigated` capture = 0 |

### 3.2 Anti-régression menu sidebar

| Vérification | Statut |
|---|---|
| Aucun nouveau menu « Pilotage des usages » dans NAV_SECTIONS | ✅ source-guard G2 P1 |
| Sidebar Énergie = 4 items inchangés (Consommations / Performance / Répartition par usage / Diagnostics) | ✅ (Playwright non-régression visuelle) |
| Aucun « Flex Intelligence » visible client | ✅ source-guard G5 P1 |

### 3.3 Anti-régression tabs `/usages`

| Tab | URL | État |
|---|---|---|
| Évolution (timeline) | `/usages?tab=timeline` | ✅ OK |
| Baseline | `/usages?tab=baseline` | ✅ OK |
| Comptage | `/usages?tab=comptage` | ✅ OK |
| **Pilotage des usages** | `/usages?tab=pilotage` | ✅ NEW |

### 3.4 Anti-régression tests cumulatifs

| Suite | Résultat |
|---|---|
| BE source-guards cumul `-k "cockpit or billing or energie or usage_steering"` + tests P0 monitoring + endpoint sync-action | **95+ verts ✅** |
| FE `pages/cockpit/__tests__/` + `pages/action-center-v4/components/drawer/__tests__/` + `__tests__/ux-hardening.test.js` | **74/74 ✅** |

---

## 4 — Playwright réel HELIOS

```
node + playwright (1.59.1) headless chromium 1440×900
→ login demo → /usages?tab=pilotage :

  pilotage-tab visible : true
  Cards article rendues : 3 (brief: max 3 above-the-fold)
  data-gap banner       : true
  Expert details (replié) : true (1 <details>)

  CTA « Créer l'action » visible : true
  Feedback après clic (toast/inline) : true

  Tab timeline URL OK   : true
  Tab baseline URL OK   : true
  Tab comptage URL OK   : true

  Console errors  : 0
  Network 4xx/5xx : 0
  Navigations vers /usage-steering : 0
```

Screenshot : `/tmp/postmerge_p1.png` — 4 onglets visibles dans /usages, 3 cards Lacune données avec impact `—` (BE None-safe), badges « À fiabiliser », CTA « Créer l'action » + lien « Voir la source », banner amber « Données à compléter », `<details>` expert replié en bas.

---

## 5 — Critères d'acceptation brief (6/6 ✅)

| # | Critère | État |
|---|---|---|
| 1 | 0 console error | ✅ Playwright HELIOS |
| 2 | 0 network 4xx/5xx golden path | ✅ Playwright + curl |
| 3 | 0 navigation vers `/usage-steering` | ✅ `framenavigated` capture vide |
| 4 | Action idempotente | ✅ POST × 2 = 201 puis 200 même `item_id` ; POST × 3 après CLOSED = HTTP 409 ACTION_CLOSED |
| 5 | Retour source OK | ✅ ActionLink `target_module=energie` + `source_url=/usages?tab=pilotage&site=42` exposés ; drawer V4 LinksTab rendra le CTA « Voir la source » |
| 6 | Verdict GO/NO GO | 🟢 **GO** |

---

## 6 — Observations

1. **Dédup BE confirmée** : `pilotage-summary` retourne 5 `action_candidates` uniques (8 insights bruts sur HELIOS dont 3 doublons type/site → agrégés en 5). Tous external_refs distincts (`dédup OK : True`).
2. **CTA fonctionnel** : le clic « Créer l'action » dans PilotageTab déclenche le POST + affiche le feedback inline (« Action créée » / « Cette action existe déjà »).
3. **Vocabulaire client préservé** : aucune mention NEBCO / AOFD / « Flex Intelligence » dans la surface PilotageTab (G5 P1 verrouille).
4. **Bonus livré** : le PATCH lifecycle utilise `new_state` (pas `target_state`) — vérifié contractuellement live.
5. **Anti-régression P0/P1 préservée** : source-guards des sprints précédents (cockpit P1.5 / action center V4 P0 / energie P0a/P0b / usage steering P0) tous verts (95+ BE cumul).

---

## Verdict

🟢 **GO** — Le 4ᵉ onglet « Pilotage des usages » est stable post-merge :
- Live HELIOS : 5 action_candidates uniques, 3 cards above-the-fold, banner data-gap, EmptyState couvert par tests
- POST sync-action idempotent strict (201 → 200 → 409 selon état)
- ActionLink source peuplée + source_url pointant vers `/usages?tab=pilotage&site=X`
- Action clôturée non ressuscitée (HTTP 409 ACTION_CLOSED)
- 0 console error, 0 network 4xx/5xx, 0 navigation vers `/usage-steering`
- Non-régression complète : 95 BE + 74 FE tests verts

Aucune action correctrice nécessaire. Le sprint suivant (P2 — renderers partagés `<Heatmap7x24/>` + `<ProfileChart/>` + fusion `/usages-horaires`) peut démarrer.
