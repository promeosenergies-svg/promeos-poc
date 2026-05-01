# Phase 25 — Comparaison audit dev vs preview prod

> Phase 25 livrée : remplacement `npm run dev` (Vite dev) par
> `vite build && vite preview` pour les audits Playwright. Élimine
> la recompilation lazy per-route qui saturait l'IPC.
>
> Date : 2026-05-01 · Branche : `claude/refonte-sol2`

## Couverture audit Playwright

| Métrique | Dev (5175) | Preview prod (5176) | Δ |
|---|---:|---:|---|
| Routes hydratées | 3/16 | **16/16** | **+13** ✅ |
| Latency moyenne `page.goto` | timeout 25s sur 13 routes | **~860 ms** sur 16 | -97 % |
| `<main>` rempli >120 chars | 3/16 | 16/16 | +13 |
| Status HTTP 200 | 3/16 | 16/16 | +13 |

## Métriques mount /cockpit/strategique

| Métrique | Dev | Preview prod | Δ | Cible |
|---|---:|---:|---|---:|
| Total requêtes | 128 | **37** | **−71 %** | ≤ 50 ✅ |
| Bundles JS Vite servis comme `/api/*.js` | 21 | 0 | −21 ✅ | 0 |
| Endpoints REST métier réels | ~4 | **19** | +15 (mesure réelle) | < 10 ❌ |
| Total endpoints uniques | 21 | 19 | quasi-identique | — |

**Découverte critique** : la mesure dev sous-estimait massivement les
endpoints REST réels parce que le mode dev ne mountait pas certains
composants au mount initial (ex: `BillingHealthBadge`, `MonitoringAlertsCard`,
`ActionCenterSummary`). En mode prod, **tous les composants au-dessus
du fold montent simultanément** → 19 endpoints au lieu de 4.

## Métriques mount /cockpit/jour

| Métrique | Dev | Preview prod | Δ |
|---|---:|---:|---|
| Total requêtes | 128 | **35** | **−73 %** |
| Endpoints REST métier réels | ~4 | **17** | +13 |

## ⚠️ Endpoints REST découverts (à arbitrer Phase 26)

19 endpoints au mount `/cockpit/strategique` — bien au-dessus de la
cible ≤ 10. Liste complète :

```
/api/config/price-references
/api/config/emission-factors
/api/demo/status
/api/sites
/api/auth/me
/api/notifications/summary
/api/monitoring/alerts
/api/billing/summary          ← ⚠️ doctrine Phase 1.3 disait remplacé par _facts
/api/purchase/renewals
/api/patrimoine/contracts
/api/tertiaire/dashboard
/api/connectors/list
/api/action-templates
/api/action-center/actions/summary
/api/action-center/notifications
/api/cockpit/_facts            ← canonique
/api/cockpit/decisions/top3
/api/cockpit/trajectory
/api/purchase/cost-simulation/portfolio/1
```

### Bug réel détecté : `/api/billing/summary` appelé 2× au mount

La revue Claude (instance externe) avait suspecté :

> Si la deuxième vérification montre que /api/billing/summary est
> encore appelé 7 fois (le bug initial du bilan d'audit), Phase 1.3
> n'a pas tenu sa promesse.

Vérif #2 précédente avait répondu "0 occurrence" — **faux négatif** dû
au mode dev qui ne montait pas tous les composants. Mesure prod réelle :
**`/api/billing/summary` est appelé 2× au mount /cockpit/strategique**.

Pas 7×, mais pas 0 non plus. **Phase 1.3 n'a pas complètement éliminé
cet endpoint au profit de `_facts`**. À traiter Phase 26.

## Bilan validation pré-merge

| Critère | Statut |
|---|---|
| Audit Playwright 16/16 routes hydratées | ✅ atteint via preview prod |
| Total requêtes mount ≤ 50 | ✅ 37 (−71 % vs dev) |
| Bundles Vite servis comme APIs | ✅ 0 (vs 21 en dev) |
| `/api/cockpit/_facts` appelé 1× au mount | ✅ confirmé canonique |
| `/api/billing/summary` éliminé | ❌ **2× au mount Vue exécutive** |
| Endpoints REST métier ≤ 10 au mount | ❌ 19 (à réduire Phase 26) |

## Recommandations Phase 26

1. **Audit du chunk `index.js`** (459 KB gzipped 138 KB) : trop de
   composants montés à l'initial render. Identifier les badges/cards
   qui devraient être chargés au scroll.
2. **Migrer `/api/billing/summary` → `_facts.billing` ou `_facts.monthly_vs_n1`** :
   compléter le travail Phase 1.3 (la Vue exécutive ne devrait jamais
   appeler billing/summary directement).
3. **Endpoints "summary" potentiellement consolidables** :
   - `notifications/summary` + `action-center/notifications` (duplicate ?)
   - `monitoring/alerts` + `action-center/actions/summary` (duplicate ?)
   - **Cible** : un seul `/api/cockpit/_inbox` qui consolide tous les
     "compteurs" non urgents en un seul appel.
4. **`/api/auth/me` + `/api/sites`** : essentiels mais à mémoiser via
   ScopeContext pour éviter le re-fetch à chaque navigation.

## Outils livrés

- `tools/playwright/audit_via_preview.sh` : script bash réutilisable
  (build + preview + audit + cleanup en 1 commande)
- `tools/playwright/audit_phase17_all_routes.mjs` modifié : accepte
  `FRONT_URL` + `OUT_DIR` env vars pour réutiliser sur preview prod
- `tools/playwright/captures/phase25_prod/` : 16 PNG + manifest
- `outputs/network_count_strategique_prod.json` + `_jour_prod.json`
