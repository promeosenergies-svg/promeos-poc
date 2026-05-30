# Chasse-bugs Tour 2 — `/usages`

**Date** : 2026-05-29
**Branche** : `claude/chasse-bugs-usages-2026-05-29`
**Base** : `claude/refonte-sol2` HEAD `d7522ba6` (post #335 P1.S4 semaine type)
**Skill** : `chasse-bugs-promeos` (2e tour, cycle 1)

## Périmètre audité

- `frontend/src/pages/UsagesDashboardPage.jsx`
- `frontend/src/pages/usages/WeekProfileTab.jsx`
- `frontend/src/components/usages/*.jsx` (17 composants)
- `frontend/src/components/pilotage/*.jsx` (4 composants)

Cross-check routes : `grep "path=" frontend/src/App.jsx` (lignes 206, 214, 228, 272, 522, 530, 544, 548, 564).

## Findings par catégorie

### Cat 1 — Boutons / liens inactifs : 0 finding

Tous les `navigate()` du périmètre ciblent des routes existantes (`/sites/:id`, `/conformite/tertiaire`, `/diagnostic-conso`, `/bill-intel`, `/achat-energie`, `/actions`, `/patrimoine`). `FooterLinks` navigue uniquement vers des cibles vérifiées.

### Cat 2 — Routes mortes / breadcrumb trompeur : 0 finding

### Cat 3 — Jargon technique exposé : 1 finding **CRITIQUE** ✅ fixé

**[CRITIQUE]** `frontend/src/pages/usages/WeekProfileTab.jsx:55-58` — affichage du label brut `correlation_id:` dans le bandeau d'erreur (jargon backend exposé à l'utilisateur final). Le `code:` brut souffrait du même biais.

**Fix appliqué** :
- `code: {code}` → `Code : {code}` (libellé FR avec espace insécable typo)
- `correlation_id: {correlationId}` → `Réf. : {correlationId}` (vocabulaire FR, hash reste copyable pour support)
- Commentaire de référence ajouté avec lien vers cet audit
- Tests existants (`WeekProfileTab.test.jsx` Critère 5) restent verts car ils n'assertent que sur la valeur via `data-testid`, pas sur le libellé.

### Cat 4 — Texte non-FR ou mixte : 1 finding **MINEUR** ✅ fixé

**[MINEUR]** `frontend/src/components/usages/FooterLinks.jsx:98` — chip KPI factures rend `'OK'` (anglais) quand `invoiceCount > 0 && uncoveredPct ≤ 5`.

**Fix appliqué** : `'OK'` → `'Conforme'` (cohérent avec vocabulaire de la carte « Conformité » adjacente).

### Cat 5 — « ? » indicatifs morts : 0 finding

Aucune icône `<Info>` / `<HelpCircle>` orpheline détectée dans le périmètre.

### Cat 6 — Calculs faux ou incohérents : 1 finding **MAJEUR** ⚠️ reporté

**[MAJEUR]** `frontend/src/components/usages/CostCard.jsx:30-42` — calcul `pct_of_total` côté FE pour l'item synthétique « Autres / non ventilé » :

```jsx
pct_of_total: totalEurAll > 0 ? Math.round((uncoveredEur / totalEurAll) * 100) : 0,
```

**Pourquoi ce n'est pas trivial** :
- Doctrine §8.1 ZERO calcul métier FE. La valeur doit venir du backend.
- Fixer correctement = ajouter `pct_of_total` au contrat API `/api/usages/cost` côté backend (compute_cost_breakdown service) + tests + migration possible des consumers existants.
- Touche : service `backend/services/cost_usage_service.py` (ou équivalent), schéma Pydantic `CostUsageItem`, test BE, test FE.

**Décision** : reporté à un sprint backend dédié (~½ j/h estimé). Tracker dans `project_promeos_brique_pilotage_usages.md` comme tâche P1.

### Cat 7 — KPI mensongers : 0 finding

`KpiStrip.jsx:30-37` et `UsageSignalCard.jsx:74` utilisent correctement `?? null` puis rendent `'—'` quand null. Aucun `'0 €'` mensonger détecté.

### Cat 8 — Console errors : pas testé ce tour

Reporté à un tour Playwright dédié (cf. `feedback_audit_sprint_visuel_fonctionnel`).

### Cat 9 — Network 4xx/5xx : pas testé ce tour

Idem (Playwright dédié).

### Cat 10 — Dette technique : 1 finding **MAJEUR** ⚠️ reporté

**[MAJEUR]** `frontend/src/pages/__tests__/V15Scope.test.js:94` — test `computeSummaryFromInsights > computes correct totals for 4 insights` échoue **sur `claude/refonte-sol2` tip (`d7522ba6`)** :

```
expected 65 to be close to 64.5, received difference is 0.5, but expected 0.005
```

**Origine** : régression introduite par PR #335 (P1.S4 semaine type) — un facteur tarifaire a probablement changé sans mise à jour du test. **Pré-existait à cette branche** (vérifié via `git stash` + run du test sur HEAD nu).

**Décision** : reporté à un hotfix dédié. Le fix est trivial (1 ligne) mais hors scope `/usages` direct — doit être traité par l'auteur de #335 (équipe énergie P1).

## Décisions appliquées ce tour

| Finding | Sévérité | Décision | Fichiers |
|---|---|---|---|
| Cat 3 jargon `correlation_id` | CRITIQUE | **Fixer** | WeekProfileTab.jsx (3 lignes) |
| Cat 4 `'OK'` anglais | MINEUR | **Fixer** | FooterLinks.jsx (1 ligne) |
| Cat 6 calcul `pct_of_total` FE | MAJEUR | **Reporter** sprint BE | CostCard.jsx — voir BE service |
| Cat 10 test V15Scope.test.js fail | MAJEUR | **Reporter** hotfix #335 owner | V15Scope.test.js (1 ligne) |

## Tests

- `vitest WeekProfileTab.test.jsx` : 13/13 ✅
- `vitest run` full : 5 399 pass / 3 skipped / **1 fail pré-existant (V15Scope, cf. Cat 10)** — **0 régression de mes edits**

## Verdict tour 2

✅ **GO** — 2 findings (CRITIQUE + MINEUR) fixés, 2 findings (MAJEUR Cat 6 + MAJEUR Cat 10) explicitement reportés avec owner identifié, hub `/usages` cohérent.

## Suite (tour 3 selon skill)

`/action-center-v4` + composants.
