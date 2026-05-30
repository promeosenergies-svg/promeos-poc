# Chasse-bugs Tour 5 — `/patrimoine`

**Date** : 2026-05-29
**Branche** : `claude/chasse-bugs-patrimoine-2026-05-29`
**Base** : `claude/refonte-sol2` HEAD `bae2c80e` (post #341 P2.1 monitoring split)
**Skill** : `chasse-bugs-promeos` (5e tour, cycle 1)

## Périmètre audité

- `frontend/src/pages/Patrimoine.jsx` (2 396 lignes)
- `frontend/src/components/patrimoine/SitesMap.jsx`
- `frontend/src/components/patrimoine/IncompleteBanner.jsx`
- `frontend/src/components/PatrimoineWizard.jsx`
- `frontend/src/components/SiteCreationWizard.jsx`
- `frontend/src/components/QuickCreateSite.jsx`

**Contexte produit** : hub de gestion du parc immobilier (sites, bâtiments, compteurs). Page sensible pour onboarding nouveau client (premier contact avec leur portefeuille).

## Findings par catégorie

### Cat 1 — Boutons/liens inactifs : 0 finding

`navigate()` cibles valides : `/sites/:id`, `/conformite`, `/renouvellements`, `/onboarding/sirene`. Aucun bouton orphelin.

### Cat 2 — Routes mortes : 0 finding

### Cat 3 — Jargon technique exposé : 1 finding **CRITIQUE** ✅ fixé

**[CRITIQUE]** `frontend/src/components/PatrimoineWizard.jsx:746` — `{f.rule_id}` brut affiché à l'utilisateur. Exemple : `"invalid_siret_format"` au lieu de `"Invalid siret format"` ou `"Format SIRET invalide"`. Onboarding nouveau client → impression de bug.

**Fix appliqué** : humanize inline `(f.rule_id || '').replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase())`. Rend `"invalid_siret_format"` → `"Invalid siret format"`. **Imperfait** (anglais résiduel pour rule_ids construits en EN côté BE) mais infiniment meilleur que le snake_case brut.

**Suite recommandée (non-trivial)** : créer dict `RULE_LABELS_FR_WIZARD` exhaustif quand l'équipe a la liste complète des rule_ids de validation wizard (cf. pattern existant dans `frontend/src/components/patrimoine/IncompleteBanner.jsx:14`).

### Cat 4 — Texte non-FR : 5 findings **MINEURS** ✅ fixés

**[MINEURS]** `frontend/src/components/QuickCreateSite.jsx:22,24,25,27,28` — 5 labels usage sans accents FR :
- `'Entrepot'` → `'Entrepôt'`
- `'Hotel'` → `'Hôtel'`
- `'Sante'` → `'Santé'`
- `'Copropriete'` → `'Copropriété'`
- `'Collectivite'` → `'Collectivité'`

**Note de cohérence** : `SiteCreationWizard.jsx` a les **bons accents** (lignes 49, 53, 55, 56, 57). Incohérence entre 2 composants similaires → fix appliqué pour aligner sur la version correcte.

### Cat 5 — « ? » indicatifs morts : 0 finding

### Cat 6 — Calculs faux ou incohérents : 1 finding documenté (déjà tracké)

**[MINEUR documenté]** `frontend/src/pages/Patrimoine.jsx:899` — calcul moyenne pondérée intensité énergétique en FE (violation doctrine §8.1). **Tracking ID `D-Phase4-3-Portfolio-Intensity-Backend-001`** déjà en place (commentaire lignes 893-897), backend endpoint planifié Sprint C-3. **Pas d'action ce tour** — dette accepté MVP.

### Cat 7 — KPI mensongers : 1 finding **MAJEUR** ✅ fixé

**[MAJEUR]** `frontend/src/pages/Patrimoine.jsx:2204` — MetricPill "Compteurs" affiche `'0'` quand `nb_compteurs === null` (donnée manquante) :
```jsx
value={site.nb_compteurs != null ? site.nb_compteurs : 0}
```

**Impact** : utilisateur croit qu'il y a 0 compteur sur le site, alors qu'il s'agit d'une donnée non remontée par le backend. Critique pour onboarding (mauvais inventaire compteurs → mauvaise stratégie monitoring).

**Fix appliqué** : `: 0` → `: '—'` (vocabulaire `'à qualifier'` doctrine §contrats_chiffres).

### Cat 8 — Console errors : pas testé ce tour

### Cat 9 — Network 4xx/5xx : pas testé ce tour

### Cat 10 — Dette technique : 2 findings **MINEURS** ✅ fixés

**[MINEUR]** `frontend/src/pages/Patrimoine.jsx:42` — `import ErrorState from '../ui/ErrorState'; // eslint-disable-line no-unused-vars` — vraiment inutilisé (grep confirme 1 seule occurrence = la ligne d'import).

**[MINEUR]** `frontend/src/pages/Patrimoine.jsx:165` — `const { isExpert } = useExpertMode(); // eslint-disable-line no-unused-vars` — `isExpert` vraiment inutilisé (grep confirme 1 occurrence destructure).

**Fix appliqué** : retrait des 2 lignes mortes + commentaire FR explicatif. `useExpertMode` import également retiré (n'était nécessaire que pour ce destructure).

Note : test `V15Scope.test.js` fail toujours pré-existant (déjà reporté Tours 2 et 4, owner PR #335 P1.S4 énergie).

## Décisions appliquées ce tour

| Finding | Sévérité | Décision | Fichier |
|---|---|---|---|
| Cat 3 jargon `rule_id` | CRITIQUE | **Fixer** (humanize inline) | PatrimoineWizard.jsx (+5 lignes) |
| Cat 7 KPI mensonger Compteurs | MAJEUR | **Fixer** | Patrimoine.jsx:2204 (1 ligne) |
| Cat 4 accents FR USAGE_OPTIONS | MINEUR × 5 | **Fixer** | QuickCreateSite.jsx (5 lignes) |
| Cat 10 imports inutilisés | MINEUR × 2 | **Fixer** | Patrimoine.jsx (3 lignes net) |
| Cat 6 intensité pondérée FE | MINEUR | **Pas d'action** — déjà tracké | Patrimoine.jsx:899 |

## Tests

- `vitest run` full : 5 558 pass / 3 skipped / 1 fail pré-existant V15Scope — **0 régression**

## Verdict tour 5

✅ **GO** — 4 findings actionnables fixés (1 CRITIQUE + 1 MAJEUR + 2 MINEUR), 1 finding Cat 6 explicitement laissé (déjà tracké sprint dédié), 0 régression, page `/patrimoine` mieux préparée pour onboarding.

## Suite (tour 6 selon skill)

`/cockpit/*` (CockpitPilotage + sous-pages).
