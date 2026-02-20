# PROMEOS Performance Budget

## Vue d'ensemble

Ce document definit les budgets de performance pour l'application PROMEOS.
Ces budgets sont **mesure-only** : ils produisent des warnings et des echecs
de tests mais ne bloquent pas les requetes et n'optimisent pas le code.

## Backend

### Slow Request Warning

Le `RequestContextMiddleware` log un warning `"slow_request"` pour toute
requete HTTP depassant le seuil.

| Parametre | Defaut | Env Var | Fichier |
| --- | --- | --- | --- |
| Seuil requete lente | 300 ms | `PROMEOS_SLOW_REQUEST_MS` | `backend/perf_config.py` |

Format du log :

```json
{
  "level": "warning",
  "message": "slow_request",
  "method": "GET",
  "path": "/api/cockpit",
  "duration_ms": 412.3,
  "threshold_ms": 300.0
}
```

### Tests de performance endpoints

Trois endpoints critiques sont testes avec un budget de temps de reponse.
Les tests utilisent SQLite in-memory avec des donnees demo seedees.

| Endpoint | Budget | Env Var |
| --- | --- | --- |
| `GET /api/cockpit` | 500 ms | `PROMEOS_PERF_COCKPIT_MS` |
| `GET /api/dashboard/2min` | 500 ms | `PROMEOS_PERF_DASHBOARD_MS` |
| `GET /api/sites` | 300 ms | `PROMEOS_PERF_SITES_MS` |

Lancer les tests :

```bash
cd backend
venv/Scripts/python -m pytest tests/test_perf_budget.py -v
```

Les tests mesurent le best-of-3 apres un warm-up. Les seuils sont calibres
pour SQLite in-memory. En CI sur une base reelle, augmenter les seuils
via les variables d'environnement.

## Frontend

### Bundle Size

Le script `scripts/check-bundle-size.js` lit `dist/assets/` apres un build
Vite et compare les tailles totales JS/CSS aux budgets. Aucune dependance
npm supplementaire.

| Asset | Budget | Env Var |
| --- | --- | --- |
| Total JS | 1500 KB | `PROMEOS_BUNDLE_JS_KB` |
| Total CSS | 100 KB | `PROMEOS_BUNDLE_CSS_KB` |

Lancer le check :

```bash
cd frontend
npm run build:check
```

Le script affiche les 5 plus gros chunks JS pour identifier les cibles
d'optimisation futures.

### Dashboard Render Timing (dev-only)

Le hook `useRenderTiming` mesure le temps mount-to-paint des composants
instrumentes. Les resultats sont visibles dans le DevPanel (onglet Perf,
accessible via `?debug` dans l'URL).

| Composant | Warning | Emplacement |
| --- | --- | --- |
| Cockpit | > 100 ms | `src/hooks/useRenderTiming.js` |

Ce hook est tree-shake en production (`import.meta.env.DEV` guard).
Les rendus depassant 100 ms produisent un `console.warn`.

## Ajouter un nouveau budget

1. **Nouvel endpoint backend** : ajouter un seuil dans `backend/perf_config.py`
   et un test dans `backend/tests/test_perf_budget.py`.

2. **Nouveau composant frontend** : ajouter `useRenderTiming('NomComposant')`
   en premiere ligne du composant.

3. **Mettre a jour ce document** avec la nouvelle entree.

## Rationale des seuils

- **300 ms** pour les endpoints de liste paginee (sites) : requetes avec
  joins simples, les utilisateurs attendent une reponse quasi-instantanee.

- **500 ms** pour les dashboards agreges (cockpit, 2min) : queries multiples
  avec aggregations. Acceptable pour des vues de type tableau de bord.

- **1500 KB JS** : build Vite avec React 18 + Recharts + 25+ routes lazy.
  Calibre sur la taille actuelle (~1460 KB) avec ~3% de marge.

- **100 KB CSS** : Tailwind v4 avec purge. Calibre sur la taille actuelle
  (~87 KB) avec marge pour la croissance.

- **100 ms render** : Cockpit a 7+ useMemo computations. Sous 100 ms
  l'UI reste fluide.

## Fichiers cles

| Fichier | Role |
| --- | --- |
| `backend/perf_config.py` | Seuils centraux backend |
| `backend/middleware/request_context.py` | Slow request warning |
| `backend/services/json_logger.py` | Extra field `threshold_ms` |
| `backend/tests/test_perf_budget.py` | Tests perf 3 endpoints |
| `frontend/scripts/check-bundle-size.js` | Check bundle post-build |
| `frontend/src/hooks/useRenderTiming.js` | Hook render timing dev-only |
| `frontend/src/pages/Cockpit.jsx` | Instrument Cockpit render |
| `frontend/src/layout/DevPanel.jsx` | Onglet Perf dans DevPanel |
