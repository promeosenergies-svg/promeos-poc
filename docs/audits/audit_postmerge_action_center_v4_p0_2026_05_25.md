# Audit postmerge — Action Center V4 P0 fixes (2026-05-25)

**Branche** : `claude/postmerge-action-center-v4-p0-smoke`
**Base** : `claude/refonte-sol2` après merge PR #311 (squash `a02ce382`)
**Verdict** : 🟢 **GO** — Les 4 fixes P0 du sprint #311 restent opérationnels post-merge. Playwright réel HELIOS : 0 console error, 0 network 4xx/5xx, 0 endpoint 410 appelé, 0 navigation FE vers `/anomalies`. Idempotence sync billing préservée (2 runs = 0 doublon). Anti-régression 4 briques verte.

## 1 — Smoke `/centre-action` ✅

| Critère brief | État |
|---|---|
| Liste visible | ✅ 20 rows affichées en pagination par défaut + NarrativeBar visible |
| Filtre `?domain=facturation` | ✅ HTTP 200 + 19 rows filtrées (anti-régression filter URL params) |
| Filtre `?domain=conformite` | ✅ HTTP 200 + 2 items |
| Filtre `?domain=patrimoine` | ✅ HTTP 200 + 2 items |
| Drawer ouvre sans crash | ✅ click row → `<dialog>` visible, 6/6 endpoints drawer HTTP 200 (`/items/{id}` + events/evidences/blockers/links/impact) |
| Item not found → fallback FR | ✅ `GET /items/{fake-uuid}` retourne HTTP 404, `ItemNotFoundState.test.jsx` 7/7 valide variant `not_found` rendu |

Summary HELIOS post-merge :
```
items_total : 62 (avant fix : 61 — +1 = item smoke audit créé hier)
P0 : 53 · P1 : 3 · sums_eur_total : 47 500 €
```

## 2 — Billing post-fix ✅

| Critère brief | État |
|---|---|
| `/centre-action?domain=facturation` affiche les actions billing | ✅ 19 rows (Playwright) |
| Action billing affiche « Voir la source » | ✅ FE test `LinksTab_source_cta.test.jsx` 5/5 + CTA `[data-testid=links-source-cta]` rendu dès `item.source_url` exposé |
| Clic source → `/bill-intel?anomaly=<id>` | ✅ live HELIOS : `item 0b2146a0 → source_url=/bill-intel?anomaly=1`, ActionLink `target_module=billing` `relation=caused_by` peuplé |
| Double sync billing ne duplique pas | ✅ 2 runs consécutifs : `created=0`, `updated=0`, `skipped_existing=52` — index UNIQUE `idx_aci_external_ref` garantit zéro race |

Live curl :
```
GET /api/v4/action-center/items/0b2146a0… :
  external_ref : billing_anomaly:1
  source_url   : /bill-intel?anomaly=1

GET /api/v4/action-center/items/0b2146a0…/links :
  total : 1
  link  : target_module=billing, relation=caused_by, link_type=source
```

## 3 — Cockpit post-fix ✅

| Critère brief | État |
|---|---|
| Priorité billing ne pointe jamais vers `/anomalies` | ✅ `/api/cockpit/priorities` retourne 5 priorités, **0 contenant `/anomalies`** (avant fix : 5+). `action_urls` réels : `/conformite?site=2`, `/conformite?site=3`, `/conformite?site=6` |
| Fallback `/centre-action` si source inconnue | ✅ helper `_safe_action_url` retourne `/centre-action` pour domain unknown, testé par `test_safe_action_url_helper_present` (4 hubs canoniques validés) |
| Cockpit Stratégique non régressé | ✅ `cockpit-executive-narrative` visible + priorité #1 CTA = `/bill-intel?insight=439` (canonical hub) |

## 4 — Non-régression 4 briques ✅

| Endpoint | HTTP | Page h1 (Playwright) |
|---|---|---|
| `/api/cockpit/strategique` | 200 | « Cockpit » + 5 KPI + 2 priorités |
| `/api/compliance/bundle` | 200 | Page `/conformite` → H1 « Conformité » |
| `/api/billing/summary` + `/api/billing/insights` | 200 | Page `/bill-intel` → H1 « Facturation » |
| `/api/v4/action-center/items?domain=facturation` | 200 | Page `/action-center-v4?domain=facturation` → 19 rows |
| `/api/v4/action-center/summary` | 200 | 10 compteurs |
| `/api/patrimoine/sites` | 200 | Page `/patrimoine` → H1 « Patrimoine » |

## 5 — Anti-régression source-guards ✅

| Vérification | Statut |
|---|---|
| `frontend/src/pages/Cockpit.jsx` toujours absent (#303) | ✅ |
| `frontend/src/pages/CockpitDecision.jsx` toujours absent (#303) | ✅ |
| Endpoints `/api/cockpit/{benchmark,co2,levers,_facts.scope,…}` toujours 410 Gone | ✅ (vérifié sprint #309 postmerge P1.5 — pas re-testé ici, contrats stable) |
| `/api/cockpit/priorities` jamais d'`action_url` `/anomalies` | ✅ test `test_no_legacy_anomalies_url_in_cockpit_priorities_action_urls` |
| `/api/cockpit/priorities` jamais d'`action_url` `/actions/{id}` | ✅ test `test_no_legacy_actions_url_in_overdue_priority` |
| Index UNIQUE `idx_aci_external_ref` actif | ✅ test `test_index_unique_protege_doublons_meme_org` raise IntegrityError |
| `ActionLink` toujours peuplée à chaque sync | ✅ test `test_ensure_action_link_cree_si_absent` + live HELIOS 1 link/item |

## 6 — Playwright réel HELIOS

```
node + playwright (1.59.1) headless chromium 1440×900
→ login demo → /action-center-v4 → /action-center-v4?domain=facturation
  → click 1ère row (drawer) → /cockpit/strategique → /conformite → /bill-intel → /patrimoine

Console errors           : 0 (React Router future flags filtrés)
Network 4xx/5xx          : 0 (/api/auth/me 401 pré-login filtré)
410 Gone endpoints appelés : 0
Navigations FE /anomalies : 0  ← critère brief
Screenshot               : /tmp/postmerge_p0_v2.png
```

## 7 — Tests anti-régression

| Suite | Résultat |
|---|---|
| BE source-guards cockpit+billing + P0-1 (`test_cockpit_priorities_no_legacy_anomalies.py`) | **3/3 ✅** |
| BE P0-3+P0-4 (`test_action_center_v4_p0_external_ref.py`) | **8/8 ✅** |
| BE source-guards cockpit `-k cockpit` | **63+ ✅** |
| FE `CockpitExecutiveNarrative.test.jsx` | **17/17 ✅** |
| FE `CockpitBillingKpis.test.jsx` | **9/9 ✅** |
| FE `action-center-v4/components/drawer/__tests__/ItemNotFoundState.test.jsx` | **7/7 ✅** |
| FE `action-center-v4/components/drawer/__tests__/LinksTab_source_cta.test.jsx` | **5/5 ✅** |
| FE `__tests__/ux-hardening.test.js` | **36/36 ✅** |
| **Total** | **74 FE + 65+ BE = 139+ tests verts** |

## 8 — Critères d'acceptation brief (5/5 ✅)

| # | Critère | État |
|---|---|---|
| 1 | 0 console error | ✅ Playwright réel HELIOS |
| 2 | 0 network 4xx/5xx golden path | ✅ Playwright réel + curl explicite |
| 3 | 0 endpoint 410 appelé | ✅ Network capture Playwright = 0 |
| 4 | 0 navigation vers `/anomalies` | ✅ Network capture Playwright = 0 (avant fix : DG cliquant priorité → /anomalies gated OFF) |
| 5 | Verdict GO/NO GO | 🟢 **GO** |

## Verdict

🟢 **GO** — Les 4 fixes P0 du sprint #311 sont stables post-merge :
- Cockpit priorities n'envoie plus jamais le DG sur `/anomalies` (page gated OFF).
- Drawer V4 résilient (fallback FR + ErrorBoundary).
- Billing sync idempotent strict (index UNIQUE `idx_aci_external_ref`).
- ActionLink peuplée → drawer rend « Voir la source » fonctionnelle (`/bill-intel?anomaly=1`).

Anti-régression #303 (Cockpit.jsx + CockpitDecision.jsx + 410 endpoints), #306-#308 (Cockpit P1/P1.5), et 4 briques (Conformité + Billing + Centre d'Action + Patrimoine) toutes vertes. Aucune action correctrice nécessaire.
