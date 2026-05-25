# Audit postmerge — Cockpit P1 Executive Narrative (2026-05-25)

**Branche** : `claude/cockpit-p1-postmerge-smoke`
**Base** : `claude/refonte-sol2` après merge PR #306 (squash `650312b2`)
**Verdict** : 🟢 **GO** — Cockpit P1 reste cohérent post-merge avec Conformité, Bill Intelligence, Centre d'Action et Patrimoine. Wording dynamique « 1 priorité détectée » ajouté pour éviter l'effet « Top 3 trompeur ».

## 1 — Smoke `/cockpit/strategique`

```
GET /api/cockpit/strategique (HELIOS, git_sha=650312b2) → HTTP 200, 24 702 B
```

### Bloc « Situation en 30 secondes » (5 KPI) ✅

| KPI | Valeur HELIOS | Attendu brief | Status |
|---|---|---|---|
| Score conformité | **36,2 /100** | 36.2/100 | ✅ |
| Surfacturations à contester | **19 808,92 €** | 19 808.92 € | ✅ |
| Prochaine échéance | None (pas de timeline OPERAT sur HELIOS) | — | ✅ |
| Actions ouvertes | **58 actions** | 58 | ✅ |
| Sites suivis | **5 sites** | 5 | ✅ |

Chaque KPI expose `source` + `formula` + `unit` + `period` + `scope` (doctrine §8.1).

### Bloc « Top priorités » (cross-briques) ✅

```
top_priorities = 1 entrée
  [1] Surfacturation à contester (2149 €)
      why = "Montant à contester"
      impact = { value: 2148.64, unit: "€" }
      cta = "Voir la facture" → /bill-intel?insight=439
```

Priorité surfacturation **visible** comme attendu. CTA pointe vers une page hub canonique (doctrine §6.2).

### Bloc « Pourquoi c'est important » ✅

Rendu côté FE en `<details>` collapsable, 4 entrées statiques (Risque réglementaire / Montant à contester / Donnée manquante / Action en attente). Vérifié par test FE `cockpit-executive-narrative` testid + 9 tests `CockpitExecutiveNarrative.test.jsx`.

### Bloc « KPIs Billing » (intégré ci-dessous) ✅

```
billing_kpis.kpis = 4 entrées
  - Surfacturations à contester     = 19 808,92 €   → /bill-intel
  - Anomalies factures ouvertes     = 109            → /bill-intel
  - Anomalies par énergie           = 29 élec · 49 gaz · 31 ? → /bill-intel
  - Actions facturation ouvertes    = 52             → /centre-action?domain=facturation

links.bill_intel                   = /bill-intel
links.centre_action_facturation    = /centre-action?domain=facturation
```

Liens canoniques **présents et conformes** au brief.

## 2 — Cas « moins de 3 priorités » ✅ (correction livrée)

Avant ce sprint : header `Top 1 priorité — à traiter maintenant` → effet « Top 3 » trompeur quand le service ne remonte qu'une priorité.

**Correctif** dans `frontend/src/pages/cockpit/CockpitExecutiveNarrative.jsx` :

```jsx
{priorities.length === 1
  ? '1 priorité détectée — à traiter maintenant'
  : `Top ${priorities.length} priorités — à traiter maintenant`}
```

Tests FE ajoutés (`CockpitExecutiveNarrative.test.jsx`) :
- `wording « 1 priorité détectée » quand une seule priorité (anti-Top 3 trompeur)` ✅
- `wording « Top N priorités » quand N ≥ 2` ✅

**Aucun trou visuel** : la grille `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` ne crée pas de cellules vides — CSS Grid n'occupe que les cellules présentes.

## 3 — Non-régression 4 briques

### Golden path endpoints (HELIOS, JWT energy_manager)

| Endpoint | HTTP | Taille | Status |
|---|---|---|---|
| `GET /api/compliance/bundle` | **200** | 6 265 B | ✅ |
| `GET /api/compliance/timeline` | **200** | 2 415 B | ✅ |
| `GET /api/billing/summary` | **200** | 746 B | ✅ |
| `GET /api/v4/action-center/items?domain=facturation` | **200** | 37 576 B | ✅ |
| `GET /api/v4/action-center/summary` | **200** | 288 B | ✅ |
| `GET /api/patrimoine/sites` | **200** | 3 742 B | ✅ |
| `GET /api/cockpit/strategique` | **200** | 24 702 B | ✅ |

`POST /api/billing/audit-all` retourne 405 sur un GET — comportement normal (méthode HTTP attendue : POST). Pas un 4xx d'erreur applicative.

### Conformité — 4 cartes ATF ✅

`ConformiteSyntheseCompacte.jsx` (P2-A #302) rend toujours 4 `<Card>` au-dessus de la fold (vérifié par grep). Bundle backend expose `findings_by_regulation` pour 3 frameworks actifs (bacs, decret_tertiaire_operat, aper) + 1 carte synthèse → **4 cartes ATF maintenues**. Score conformité bundle = **36,2/100** ⇄ cohérent avec le KPI cockpit (même SoT `compute_portfolio_compliance`).

### Bill Intelligence ✅

`/api/billing/summary` + `/api/billing/insights` 200 ; les 4 KPI billing du cockpit consomment la même SoT que `/bill-intel` (BillingInsight.estimated_loss_eur + InsightStatus). Aucune divergence.

### Centre d'Action filtre Facturation ✅

`/api/v4/action-center/items?domain=facturation` retourne 37 KB → liste complète des items domain=FACTURATION. CTA cockpit `Actions facturation ouvertes = 52` cohérent avec le filtre.

### Patrimoine ✅

`/api/patrimoine/sites` retourne les 5 sites HELIOS → cohérent avec KPI cockpit « Sites suivis = 5 ».

## 4 — Tests anti-régression

| Suite | Résultat |
|---|---|
| BE source-guards cockpit (-k cockpit, 50 tests + 13 service) | **63 / 63 ✅** |
| FE `pages/cockpit/__tests__/CockpitExecutiveNarrative.test.jsx` (11 tests : 9 P1 + 2 wording dynamique) | **11 / 11 ✅** |
| FE `pages/cockpit/__tests__/CockpitBillingKpis.test.jsx` (anti-régression P0) | **9 / 9 ✅** |
| FE `__tests__/ux-hardening.test.js` (anti-régression cross-page) | **36 / 36 ✅** |

## 5 — Critères d'acceptation (brief postmerge)

| # | Critère | État |
|---|---|---|
| 1 | `/cockpit/strategique` : Situation 30s + Top priorités + Pourquoi + KPIs Billing + liens `/bill-intel` & `/centre-action?domain=facturation` | ✅ |
| 2 | Cas HELIOS : score 36.2, surfact 19 808.92 €, 58 actions, 5 sites, priorité surfacturation visible | ✅ |
| 3 | Cas « < 3 priorités » : wording `1 priorité détectée`, aucun trou visuel, pas de `Top 3` trompeur | ✅ (correctif livré) |
| 4 | Non-régression `/conformite` 4 cartes ATF + `/bill-intel` + `/centre-action` filtre Facturation + `/patrimoine` | ✅ HTTP 200 + tests verts |
| 5 | 0 console error en golden path | ⚠️ Vérification API + tests unitaires OK ; check browser ↓ |
| 6 | 0 network 4xx/5xx golden path | ✅ tous endpoints 200 (POST attendu en 405 non bloquant) |
| 7 | Liens fonctionnels (`/bill-intel?insight=439`, `/conformite`, `/centre-action`, `/patrimoine`) | ✅ tous présents dans payload + guards FE |

⚠️ **Réserve méthodologique sur le critère 5** : la vérification « 0 console error » nécessite un browser réel (Playwright ou inspection manuelle). Le harness actuel a validé :
- 0 erreur dans la réponse API (`_error: None` sur `executive_summary`)
- 0 erreur de runtime dans les tests FE (56/56 passent)
- 0 warning ESLint sur le nouveau composant après fix whitespace

Pour clôturer formellement le critère, lancer en local :
```bash
cd frontend && npm run dev  # → :5173, BE déjà :8001
# Ouvrir /cockpit/strategique en DevTools Console, screenshot le panel Console
```

## Verdict

🟢 **GO** — Cockpit P1 stable post-merge, wording dynamique correct, 4 briques voisines OK. Aucune régression détectée sur 119 tests (BE 63 + FE 56). La PR #306 peut rester telle quelle ; le seul ajout livré ici (`1 priorité détectée`) reste à committer dans la branche `claude/cockpit-p1-postmerge-smoke` puis à mergerdans `refonte-sol2`.
