# Chasse-bugs Tour 4 — `/bill-intel`

**Date** : 2026-05-29
**Branche** : `claude/chasse-bugs-bill-intel-2026-05-29`
**Base** : `claude/refonte-sol2` HEAD `21bcc6c7` (post #339 Tour 3 a11y action-center-v4)
**Skill** : `chasse-bugs-promeos` (4e tour, cycle 1)

## Périmètre audité

- `frontend/src/pages/BillIntelPage.jsx` (1 541 lignes)
- `frontend/src/components/BillingTimeline.jsx`
- `frontend/src/components/BillingCompareChart.jsx`
- `frontend/src/components/SiteBillingMini.jsx`
- `frontend/src/components/billing/ShadowBreakdownCard.jsx`
- `frontend/src/components/analytics/BillingVentilationCard.jsx`

**Contexte produit** : Bill Intelligence est le wedge cardinal PROMEOS (Vision Consolidée v1.3 — wedge facture + conformité + consommation). Code mature, doctrine bien appliquée.

## Findings par catégorie

### Cat 1 — Boutons/liens inactifs : 0 finding

`navigate()` cibles toutes valides : `/achat-energie`, `/consommations/import`, `/contrats`, `/billing`. Aucun bouton sans handler.

### Cat 2 — Routes mortes : 0 finding

### Cat 3 — Jargon technique exposé : 0 finding

Tous acronymes sensibles (TURPE, accise, CTA, TVA, shadow_billing, reconciliation_auto) wrappés `<Explain term>`. Aucun nom de concurrent. Aucun `rule_id` / `correlation_id` / `efa_id` / `[object Object]` / `undefined` / `NaN`.

### Cat 4 — Texte non-FR : 0 finding

Entièrement FR. `toLocaleString('fr-FR')`, `toLocaleDateString('fr-FR')`, pluriels cohérents (`anomalie`/`anomalies`), espace insécable `&euro;` + ` ` corrects.

### Cat 5 — « ? » indicatifs morts : 0 finding

`<Tooltip>` et `title=` natifs utilisés systématiquement sur éléments interactifs.

### Cat 6 — Calculs faux ou incohérents : 2 findings ⚠️ reportés (non-triviaux)

**[MAJEUR]** `frontend/src/pages/BillIntelPage.jsx:284-302` — filtrage par période en FE :
```jsx
new Date(now.getFullYear(), now.getMonth() - 3, 1)
```
Logique métier (date cutoff) calculée côté navigateur. **Violation doctrine §8.1 ZERO biz FE**.

**Fix** : ajouter param `period_preset=last_3m|last_6m|...` à l'endpoint `/api/bill-intel/*`, retirer le filter FE. Touche : service BE + Pydantic + 1 hook FE. Estimé **~½ j/h**. **Reporté sprint BE Bill-Intel** (owner : agent `bill-intelligence`).

**[MINEUR]** `frontend/src/components/analytics/BillingVentilationCard.jsx:114-116` — transformation `archetype_code` :
```jsx
data.archetype_code?.replace(/_/g, ' ').toLowerCase()
```
Display transformation, mais reste un calcul FE qui devrait venir du backend. **Reporté** : backend doit fournir `archetype_label` formaté. **Estimé ~2h**, low priority.

### Cat 7 — KPI mensongers : 0 finding

`fmtEur(0)` retourne `'—'` (cf. utils/format.js doctrine) → pas d'affichage `'0 €'` mensonger. `estimated_loss_eur > 0` guards respectés (ligne 1183). Tooltips source/formule/période présents (ligne 920).

### Cat 8 — Console errors : pas testé ce tour

Reporté tour Playwright dédié.

### Cat 9 — Network 4xx/5xx : pas testé ce tour

ErrorState + catch/toast présents. Vérification runtime reportée.

### Cat 10 — Dette technique : 1 finding **MINEUR** ✅ fixé

**[MINEUR]** `frontend/src/pages/BillIntelPage.jsx:36` — import `Term` jamais utilisé dans la page :
```jsx
import { DecisionEvidenceCard, Term } from '../components/grammar';
```

**Fix appliqué** : retrait du symbole `Term` de la destructure (1 ligne nette).

Note : test `V15Scope.test.js` fail toujours pré-existant (déjà reporté Tour 2, owner #335 P1.S4). Test `EnergyProvenanceCoverage.test.jsx` apparaît occasionnellement en flaky (passe en isolé, peut échouer en full run — probable race FS). À investiguer hors-scope chasse-bugs.

## Décisions appliquées ce tour

| Finding | Sévérité | Décision | Fichier |
|---|---|---|---|
| Cat 10 import `Term` inutilisé | MINEUR | **Fixer** | BillIntelPage.jsx (1 ligne) |
| Cat 6 filtrage période FE | MAJEUR | **Reporter** sprint BE Bill-Intel | BillIntelPage.jsx:284-302 |
| Cat 6 `archetype_code` transform FE | MINEUR | **Reporter** sprint BE (low priority) | BillingVentilationCard.jsx:114-116 |

## Tests

- `vitest run` full : 5 538 pass / 3 skipped / 1 fail pré-existant V15Scope — **0 régression**
- Test `EnergyProvenanceCoverage.test.jsx` passe en isolé (16/16) mais flaky en full run

## Verdict tour 4

✅ **GO** — 1 finding MINEUR fixé, 2 findings MAJEUR/MINEUR Cat 6 explicitement reportés au sprint BE Bill-Intel avec owner identifié, page `/bill-intel` cohérente. Périmètre wedge produit confirmé **architecturalement sain** (sauf brèche doctrine §8.1 à corriger backend).

## Suite (tour 5 selon skill)

`/patrimoine` + composants.
