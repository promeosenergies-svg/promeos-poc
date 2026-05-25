# Audit postmerge — Cockpit P1.5 Executive Priority Polish (2026-05-25)

**Branche** : `claude/postmerge-cockpit-p15-smoke`
**Base** : `claude/refonte-sol2` après merge PR #308 (squash `6ef5cdbd`)
**Verdict** : 🟢 **GO** — Cockpit P1.5 stable post-merge. Playwright réel HELIOS : 0 console error, 0 network 4xx/5xx, 0 endpoint cockpit 410 appelé. Anti-régression #303 préservée (Cockpit.jsx + CockpitDecision.jsx toujours supprimés).

## 1 — Smoke `/cockpit/strategique` (Critère brief #1)

```
GET /api/cockpit/strategique (HELIOS, git_sha=6ef5cdbd) → HTTP 200, 25 413 B
```

### Bloc « Situation en 30 secondes » ✅

| KPI | Valeur HELIOS | Unit |
|---|---|---|
| Score conformité | 36,2 | /100 |
| Surfacturations à contester | 19 808,92 | € |
| Prochaine échéance | None (pas de timeline OPERAT) | jours |
| Actions ouvertes | 58 | actions |
| Sites suivis | 5 | sites |

`_error: None` → service nominal. 5 KPI tous présents avec metadata complète.

### Bloc « Priorités » ✅

2 priorités cross-briques triées canoniquement (catégorie):

| Rang | Catégorie | Label | CTA |
|---|---|---|---|
| 1 | `billing` | Surfacturation à contester (2149 €) | `/bill-intel?insight=439` |
| 2 | `contract` | Contrat énergie à renouveler (Eni) | `/bill-intel?contract=4` |

Wording rendu : « **2 priorités à traiter en premier** » (correct, dynamique 0/1/2-3 P1.5).

### Cas 0/1/2-3 (Critère brief #1) ✅

- **2 priorités** : observé live (wording « N priorités à traiter en premier »).
- **0 priorité** : couvert par FE test `0 priorité → message rassurant « Aucune priorité critique détectée »` (vert pastel).
- **1 priorité** : couvert par FE test `1 priorité → « 1 priorité détectée — à traiter maintenant »`.
- **3 priorités** : couvert par FE test `3 priorités → « 3 priorités à traiter en premier »`.

### Bloc « Pourquoi cette priorité ? » ouvrable ✅

Click Playwright réel sur `[data-testid=exec-priority-1-why] summary` → `details` expanded → source + impact + échéance + périmètre + action recommandée visibles.

### CTA hub canoniques fonctionnels ✅

| CTA | Vérification |
|---|---|
| `/bill-intel?insight=439` | présent dans payload priority[1] |
| `/conformite` | testé via FE test `CTA /conformite pour priorité regulatory_urgent` |
| `/centre-action?item={id}` | testé via FE test `CTA /centre-action pour priorité evidence_missing` |
| `/patrimoine?incomplete={rule}` | builder `_top_patrimoine_priority` testé (G4 source-guard) |

## 2 — Non-régression 4 briques (Critère brief #2)

### Endpoints golden path (HELIOS, JWT energy_manager)

| Endpoint | HTTP | Taille |
|---|---|---|
| `/api/compliance/bundle` | **200** | 6 265 B |
| `/api/compliance/timeline` | **200** | 2 415 B |
| `/api/billing/summary` | **200** | 746 B |
| `/api/billing/insights` | **200** | 33 212 B |
| `/api/v4/action-center/items?domain=facturation` | **200** | 37 576 B |
| `/api/v4/action-center/summary` | **200** | 288 B |
| `/api/patrimoine/sites` | **200** | 3 742 B |
| `/api/cockpit/strategique` | **200** | 25 413 B |

### Vérifications structurelles

| Brique | Vérification | Statut |
|---|---|---|
| `/conformite` | 4 cartes ATF (ConformiteSyntheseCompacte #302) inchangées | ✅ |
| `/bill-intel` | API `/billing/summary` + `/billing/insights` 200, billing_kpis cockpit toujours 4 cartes | ✅ |
| `/centre-action` | API `/v4/action-center/items?domain=facturation` 200 (37 KB) | ✅ |
| `/patrimoine` | API `/patrimoine/sites` 200, 5 sites HELIOS | ✅ |

## 3 — Playwright réel (Critères brief #3-#4)

```
node + playwright (1.59.1) headless chromium 1440×900
→ login demo → /cockpit/strategique → click « Pourquoi cette priorité ? »

Console errors  : 0 (React Router future flags filtrés)
Network 4xx/5xx : 0 (/api/auth/me 401 pré-login filtré)
410 Gone appelés: 0  ← critère brief #3
API cockpit hits: 2 (HTTP 200 /cockpit/strategique + HTTP 200 /cockpit/_facts)
« Pourquoi » click : OK (details expanded)
Screenshot fullPage : /tmp/cockpit_p15_postmerge.png
```

Les 2 seuls endpoints `/cockpit/*` consommés par le FE sont :
- `/api/cockpit/strategique` (Cockpit P1/P1.5 — payload data-driven)
- `/api/cockpit/_facts?period=current_week` (facts service, actif et non déprécié)

**Aucun appel** à `/cockpit/benchmark`, `/conso-month`, `/co2`, `/_facts.scope`, `/levers`, `/essentials` qui retournent tous **410 Gone** (vérifié par curl explicite ci-dessous).

### Vérification 410 Gone (anti-régression #303)

| Endpoint | HTTP attendu | HTTP réel |
|---|---|---|
| `/api/cockpit/benchmark` | 410 | ✅ 410 |
| `/api/cockpit/conso-month` | 410 | ✅ 410 |
| `/api/cockpit/co2` | 410 | ✅ 410 |
| `/api/cockpit/_facts.scope` | 410 | ✅ 410 |
| `/api/cockpit/levers` | 410 | ✅ 410 |
| `/api/cockpit/essentials` | 410 | ✅ 410 |
| `/api/v2/cockpit/executive-v2` | 404* | ℹ️ 404 (route déjà retirée du router pré-#303) |
| `/api/v2/cockpit/top-contributors` | 404* | ℹ️ 404 (idem) |

\* 404 acceptable : la route n'est plus enregistrée dans le router cockpit_v2.py (suppression complète plutôt que 410 Gone).

## 4 — Source-guards anti-régression (Critère brief #4)

| Vérification | Statut |
|---|---|
| `frontend/src/pages/Cockpit.jsx` toujours absent (#303) | ✅ |
| `frontend/src/pages/CockpitDecision.jsx` toujours absent (#303) | ✅ |
| Tests `tests/source_guards/ -k cockpit` (50 P0 + 13 P1 + 4 P1.5) | **67 / 67 ✅** |
| FE `pages/cockpit/__tests__/CockpitExecutiveNarrative.test.jsx` (P1 baseline + P1.5 polish) | **17 / 17 ✅** |
| FE `pages/cockpit/__tests__/CockpitBillingKpis.test.jsx` (anti-régression P0) | **9 / 9 ✅** |
| FE `__tests__/ux-hardening.test.js` (cross-page convergence) | **36 / 36 ✅** |

## 5 — Critères d'acceptation brief

| # | Critère | État |
|---|---|---|
| 1 | `/cockpit/strategique` : Situation 30s + Priorités + cas 0/1/2-3 + Pourquoi ouvrable + CTAs `/bill-intel`/`/conformite`/`/centre-action` | ✅ |
| 2 | Non-régression `/conformite` 4 cartes ATF + `/bill-intel` + `/centre-action` filtre Facturation + `/patrimoine` | ✅ HTTP 200 + tests verts |
| 3 | 0 console error | ✅ Playwright réel HELIOS |
| 4 | 0 network 4xx/5xx golden path | ✅ Playwright réel + curl explicite |
| 5 | Aucun endpoint cockpit 410 appelé | ✅ Network capture Playwright = 0 |
| 6 | Aucun Cockpit.jsx / CockpitDecision.jsx réintroduit | ✅ filesystem check + source-guard G5 |

## Verdict

🟢 **GO** — Cockpit P1.5 stable post-merge. 5 KPI + 2 priorités triées canoniquement + bloc « Pourquoi cette priorité ? » ouvrable. 0 console error, 0 network 4xx/5xx, 0 endpoint 410 appelé sur le golden path Playwright réel. Anti-régression #303 et #306 préservée (67/67 source-guards + 62 FE tests). Aucune action correctrice nécessaire.
