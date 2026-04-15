# FIX PROMEOS — Sprint UX XS — 24 mars 2026

## 1. Résumé exécutif

5 corrections UX appliquées. Le 6e point (demo gating) était déjà correct.

| # | Correction | Fichiers | Effort |
|---|---|---|---|
| 1 | Badge aliases `success`→`ok`, `warning`→`warn` + 5 appelants | Badge.jsx + 5 pages | XS |
| 2 | Risque financier qualifié "risque théorique max." | CockpitHero.jsx | XS |
| 3 | Toggle cockpit "Plus de détails" | Cockpit.jsx | XS |
| 4 | GuidedModeBandeau visible pour tous | ConformitePage.jsx | XS |
| 5 | FreshnessIndicator composant dans BillIntelPage | BillIntelPage.jsx | XS |
| 6 | Demo gating | *(déjà correct — isExpert/isDemo/!hasData)* | 0 |

## 2. Modifications réalisées

### Fix 1 — Badge aliases + nettoyage appelants

**Badge.jsx** : ajout `success` et `warning` comme aliases dans le mapping `styles` pour backward-compat. Les badges `success` et `warning` qui tombaient en fallback `neutral` (gris) sont maintenant correctement colorés.

**5 appelants corrigés** pour utiliser les noms canoniques :
- `ConnectorsPage.jsx:147` : `"warning"` → `"warn"`
- `ImportPage.jsx:350` : `"success"` → `"ok"`
- `Dashboard.jsx:107` : `"warning"` → `"warn"`
- `Dashboard.jsx:182` : `"success"` → `"ok"`
- `Patrimoine.jsx:1018` : `"warning"` → `"warn"`

### Fix 2 — Risque financier qualifié

`CockpitHero.jsx:147` : sous-libellé changé de "pénalités + anomalies billing" → "risque théorique max. (pénalités réglementaires + anomalies facture)".

Un DAF comprend maintenant que le montant est un maximum théorique, pas un montant certain.

### Fix 3 — Toggle cockpit

`Cockpit.jsx:721` : "Analyse détaillée" → "Plus de détails". Plus accessible pour un non-expert.

### Fix 4 — GuidedMode pour tous

`ConformitePage.jsx:642` : condition `!isExpert &&` retirée. Le bandeau guidé (5 étapes) est maintenant visible pour tous les utilisateurs, pas uniquement les non-experts.

### Fix 5 — FreshnessIndicator

`BillIntelPage.jsx:799-801` : le span texte plat "Dernière maj : ..." remplacé par le composant `<FreshnessIndicator>` avec calcul dynamique du statut (fresh < 45j, recent < 90j, stale < 365j, expired).

### Fix 6 — Demo gating (aucune modification)

Vérifié : les 3 pages sont déjà correctement gatées.
- BillIntelPage : boutons seed gatés `!hasData && isExpert` (L514) et `isExpert` en empty state (L818)
- PurchasePage : bloc "Datasets demo" gaté `isExpert` (L1458)
- PurchaseAssistantPage : badge "MODE DEMO" conditionnel sur `isDemo` flag API (L489)

## 3. Fichiers touchés

| Fichier | Modification |
|---|---|
| `ui/Badge.jsx` | Aliases success→ok, warning→warn |
| `pages/ConnectorsPage.jsx` | warning→warn |
| `pages/ImportPage.jsx` | success→ok |
| `pages/Dashboard.jsx` | warning→warn, success→ok |
| `pages/Patrimoine.jsx` | warning→warn |
| `pages/cockpit/CockpitHero.jsx` | Sous-libellé risque qualifié |
| `pages/Cockpit.jsx` | Toggle "Plus de détails" |
| `pages/ConformitePage.jsx` | GuidedMode pour tous |
| `pages/BillIntelPage.jsx` | Import + FreshnessIndicator |

## 4. Tests

| Suite | Résultat |
|---|---|
| `step4_co2_guard.test.js` | 9/9 ✅ |

## 5. Risques de régression

| Risque | Probabilité | Mitigation |
|---|---|---|
| Badge aliases cassent des tests qui vérifient les classes CSS | Nulle | Les classes sont identiques (alias = même style) |
| GuidedMode visible en expert crée du bruit | Faible | Le bandeau est compact et informatif pour tous |
| FreshnessIndicator ne reçoit pas `last_updated` | Faible | Fallback `no_data` géré dans le calcul |

## 6. Points non traités

| Point | Raison |
|---|---|
| ErrorState sur 26 pages | Effort S, hors sprint XS |
| Unification KpiCard/MetricCard/UnifiedKpiCard | Effort M, migration progressive |
| Accessibilité sr-only/ARIA | Effort M |
| TrustBadge sur ConformitePage/PurchasePage | Effort S |

## 7. Definition of Done

- [x] Badge `success`/`warning` ne tombent plus en fallback gris
- [x] 5 appelants utilisent les noms canoniques
- [x] Risque financier = "risque théorique max."
- [x] Toggle cockpit = "Plus de détails"
- [x] GuidedModeBandeau visible pour tous
- [x] FreshnessIndicator composant dans BillIntelPage
- [x] Demo gating vérifié (déjà correct)
- [x] 9 tests frontend passent
- [x] 0 fichier Yannick touché
