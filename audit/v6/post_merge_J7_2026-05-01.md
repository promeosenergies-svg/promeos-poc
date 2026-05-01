# Audit J+7 post-merge PR #264 — PROMEOS
**Date** : 2026-05-01 · **Auditeur** : Claude Code (automatisé)
**Branche auditée** : `claude/refonte-visuelle-sol` · **HEAD** : `7309165c`

---

## 1. État de la PR #264

| Champ | Valeur |
|---|---|
| Numéro | #264 |
| Titre | fix(p0-demo-ready): 6 P0 démo blockers → 36/36 routes clean |
| État | **MERGED** |
| Date de merge | 2026-04-25T09:13:34Z (J+0) |
| Branche source | `claude/fix-p0-demo-ready` |
| Branche cible | `claude/refonte-visuelle-sol` |
| Commit de merge | `7309165c` |
| Auteur merge | promeosenergies-svg |

## 2. Commits intervenus depuis le merge de PR #264

```
7309165c fix(p0-demo-ready): 6 P0 démo blockers → 36/36 routes clean (#264)  ← merge J+0
babc4b4c docs(CLAUDE): sources veille canoniques — regle obligatoire 24/04       ← pré-merge
261e3a2e feat(yaml): biométhane + stockage + coef A transport + ...              ← pré-merge
fdbf3a8b feat(yaml): ATRD7 GRDF grille 1/07/2026 (Z=+5,87% avec péréquation)   ← pré-merge
```

**Aucun commit après le merge de PR #264.** Le HEAD de `claude/refonte-visuelle-sol` est le commit de merge lui-même. La fenêtre J+0 → J+7 ne contient aucun changement de code extérieur.

## 3. Environnement d'audit

| Composant | Valeur |
|---|---|
| Backend | FastAPI · port 8001 · git_sha `7309165c` |
| Frontend | Vite 5.4.21 · port 5173 |
| Seed | HELIOS S · 5 sites · 4 utilisateurs |
| Playwright | 1.56+ (global `/opt/node22/bin/playwright`) |
| Script audit | `audit/v6/audit-console-network-J7.mjs` (créé pour cet audit — `tools/playwright/audit-console-network.mjs` absent du repo) |
| Baseline de référence | `audit/v5/console-network-p0-absolute-final/` · **ABSENT du repo** (référencé dans la mission mais non commité) |

### Obstacles infra rencontrés

| Obstacle | Résolution |
|---|---|
| `frontend/node_modules` = symlink cassé pointant `/Users/amine/...` | Supprimé + réinstallation |
| `PROMEOS_JWT_SECRET` absent → backend crash | `.env` créé depuis `.env.example` |
| `audit-console-network.mjs` absent | Script équivalent créé dans `audit/v6/` |
| Baseline `audit/v5/` absent | Analyse qualitative + logs backend substitués |

## 4. Résultats de l'audit — 36 routes

### Tableau complet

| Route | Statut | Erreurs console (réelles) | Fails API | Crash |
|---|---|---|---|---|
| `/` | ❌ **KO** | 1 error + 1 warning (500 peer-comparison) | 1 (HTTP 500) | Non |
| `/cockpit` | ✅ OK* | 0 | 0 | Non |
| `/conformite` | ✅ OK* | 0 | 0 | Non |
| `/bill-intel` | ✅ OK* | 0 | 0 | Non |
| `/billing` | ✅ OK* | 0 | 0 | Non |
| `/achat-energie` | ✅ OK* | 0 | 0 | Non |
| `/monitoring` | ✅ OK* | 0 | 0 | Non |
| `/import` | ✅ OK* | 0 | 0 | Non |
| `/connectors` | ✅ OK* | 0 | 0 | Non |
| `/kb` | ✅ OK* | 0 | 0 | Non |
| `/notifications` | ✅ OK* | 0 | 0 | Non |
| `/watchers` | ✅ OK* | 0 | 0 | Non |
| `/patrimoine` | ✅ OK* | 0 | 0 | Non |
| `/sites` | ✅ OK* | 0 | 0 | Non |
| `/activation` | ✅ OK* | 0 | 0 | Non |
| `/actions` | ✅ OK* | 0 | 0 | Non |
| `/admin/users` | ✅ OK* | 0 | 0 | Non |
| `/admin/roles` | ✅ OK* | 0 | 0 | Non |
| `/admin/assignments` | ✅ OK* | 0 | 0 | Non |
| `/admin/audit` | ✅ OK* | 0 | 0 | Non |
| `/profile` | ✅ OK* | 0 | 0 | Non |
| `/settings` | ✅ OK* | 0 | 0 | Non |
| `/help` | ✅ OK* | 0 | 0 | Non |
| `/energy-copilot` | ✅ OK* | 0 | 0 | Non (redirect → /cockpit ✓) |
| `/consommations` | ✅ OK* | 0 | 0 | Non |
| `/consommations/portfolio` | ✅ OK* | 0 | 0 | Non |
| `/conformite/aper` | ✅ OK* | 0 | 0 | Non |
| `/conformite/bacs` | ✅ OK* | 0 | 0 | Non |
| `/conformite/audit` | ✅ OK* | 0 | 0 | Non |
| `/pilotage` | ✅ OK* | 0 | 0 | Non |
| `/sites/1` | ✅ OK* | 0 | 0 | Non |
| `/kb/items` | ✅ OK* | 0 | 0 | Non |
| `/page-qui-nexiste-pas` | ✅ OK* | 0 | 0 | Non |
| `/import/upload` | ✅ OK* | 0 | 0 | Non |
| `/billing/invoices` | ✅ OK* | 0 | 0 | Non |
| `/admin/kb-metrics` | ✅ OK* | 0 | 0 | Non |

> **Note** : Les routes marquées OK* présentent uniquement des warnings React Router Future Flag (v7 compatibility) et des warnings Recharts `width(-1)/height(-1)` (rendu headless). Ces deux types de bruit sont des avertissements framework non-applicatifs, ignorés dans cette analyse.

### Synthèse quantitative (après filtrage du bruit framework)

| Métrique | Valeur | Baseline v3 |
|---|---|---|
| Routes OK | **35/36** | N/A (v5 absente) |
| Routes KO | **1/36** | N/A |
| Nouvelles erreurs console applicatives | **2** (1 error + 1 warning) | N/A |
| Nouveaux API fails 4xx/5xx | **1** (HTTP 500) | N/A |
| Crashes React (ErrorBoundary) | **0** | 0 |

## 5. Détail de la régression détectée

### R-001 · `GET /api/sol/peer-comparison` → HTTP 500

**Gravité** : P1 (non-bloquant UI, dégradation gracieuse — `PeerComparisonCard` affiche un placeholder)

**Route affectée** : `/` (home — `CommandCenterSol.jsx`)

**Erreur backend** (log `/tmp/be.log`) :
```
OperationalError: (sqlite3.OperationalError) no such column: total_kwh
[SQL:
    SELECT
        COALESCE(SUM(total_eur), 0) AS total_eur,
        COALESCE(SUM(total_kwh), 0) AS total_kwh
    FROM energy_invoices
    WHERE site_id IN (1,2,3,4,5)
      AND total_kwh > 0
]
```

**Cause exacte** : `backend/app/sol/service.py:532` — la query SQL référence la colonne `total_kwh` qui n'existe pas dans `energy_invoices`. La colonne réelle est `energy_kwh` (`billing_models.py:351`).

**Fichier fautif** : `backend/app/sol/service.py` · lignes 532, 535, 539-544

**Fix minimal** (2 min) :
```python
# Ligne 532 — remplacer :
COALESCE(SUM(total_kwh), 0) AS total_kwh
# par :
COALESCE(SUM(energy_kwh), 0) AS total_kwh

# Ligne 535 :
AND total_kwh > 0
# par :
AND energy_kwh > 0
```

**Impact côté frontend** :
```jsx
// PeerComparisonCard.jsx:31
getPeerComparison()
  .then(setData)
  .catch(() => setData(null))   // ← swallow silencieux du 500
  .finally(() => setLoading(false));
```
La card affiche "Comparaison vs pairs sectoriels — calcul en cours · benchmark OID/CEREN par archétype NAF" au lieu des données réelles.

**Commit introduisant la régression** : `7309165c` (le commit de merge lui-même)
— `backend/app/sol/service.py` (+596 lignes) ajouté dans ce commit avec le mauvais nom de colonne.

**Présence en J+0 vs J+7** : La régression était déjà présente dès J+0 (le commit de merge). Elle n'a pas été détectée par l'audit initial car le frontend la masque et l'audit PR utilisait probablement un filtrage différent des erreurs console.

## 6. Fixes P0 de la PR #264 — Vérification de non-régression

| Fix | Route cible | Statut J+7 |
|---|---|---|
| M-01 : modale onboarding désactivée | Toutes | ✅ Confirmé — aucune modale bloquante |
| M-02 : NEBCO fallback site `'1'` | `/cockpit` | ✅ OK — 0 erreur |
| M-02bis : EMS timeseries dates | `/cockpit` | ✅ OK — 0 fail API |
| M-03 : KB search fallback GET | `/kb` | ✅ OK — 0 erreur |
| M-05 : `/energy-copilot` → redirect `/cockpit` | `/energy-copilot` | ✅ Redirect fonctionnel |

## 7. Analyse baseline J+24h (branche `claude/audit-refonte-j24h-2026-04-26`)

L'audit J+24h avait audité commit `1ecc04eb` (branche supprimée/orpheline) et signalé :

> **RÉGRESSION P0** : `7309165c` avait introduit une erreur JSX dans App.jsx (`<Route>` hors `<Routes>`)

**Vérification à J+7** : L'inspection de `frontend/src/App.jsx` sur HEAD `7309165c` montre que la syntaxe JSX est valide — `<Routes>` se ferme correctement à la ligne 740, et le bloc `{showUpgradeWizard && (...)}` suit correctement. Vite 5.4.21 démarre sans erreur de build. La régression JSX **n'est pas reproductible** à J+7.

Hypothèse : le J+24h audit comparait `1ecc04eb` (pré-merge refonte vues `/` et `/cockpit`) au HEAD `7309165c`, et la différence de ligne dans le diff était interprétée à tort comme une erreur JSX. Le build Vite actuel le confirme.

## 8. Conclusion

```
VERDICT J+7 : RÉGRESSION PARTIELLE (1/36 routes)
```

| Critère | Résultat |
|---|---|
| Aucun nouveau commit depuis merge | ✅ Confirmé (0 commit post-merge) |
| Fixes P0 PR #264 maintenus | ✅ 5/5 fixes opérationnels |
| Crashes React | ✅ 0 |
| Erreur JSX App.jsx (J+24h) | ✅ Non reproductible — Vite build OK |
| `GET /api/sol/peer-comparison` | ❌ HTTP 500 (R-001 — présent depuis J+0) |
| UI dégradée (placeholder) | ⚠️ Home page → PeerComparisonCard affiche placeholder |

La régression R-001 était **présente dès le merge de PR #264** (commit `7309165c`), non détectée par l'audit initial. Elle n'a pas été introduite par un commit postérieur.

**Action recommandée** : Corriger `backend/app/sol/service.py:532,535` (`total_kwh` → `energy_kwh`) en priorité P1, dans un commit atomique dédié sur une branche `claude/fix-sol-peer-comparison-column`.

---

*Audit automatisé Claude Code · 2026-05-01 · Branch: `claude/refonte-visuelle-sol` · SHA: `7309165c`*
*Script: `audit/v6/audit-console-network-J7.mjs` · Playwright 1.56.1 · Node 22.22.2*
