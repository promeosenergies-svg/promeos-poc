# V62 — Portfolio Trend réel (in-memory cache)

**Date :** 2026-02-23
**Auteurs :** équipe PROMEOS
**Statut :** Livré

---

## Objectif

Fournir un indicateur de tendance **réel** sur le bandeau Cockpit Patrimoine :
`↑ Hausse` / `↓ Baisse` / `— Stable` en comparant le snapshot courant au
snapshot précédent calculé pour la même organisation.

En V61 le champ `trend` était toujours `null`. En V62 il devient non-null
dès le deuxième appel à `GET /api/patrimoine/portfolio-summary`.

---

## Architecture

### Principe

```
1er appel  → aucun snapshot précédent
             → trend = null
             → stocker {computed_at, risk_eur, sites_count} en cache

2ème appel → lire snapshot précédent
             → calculer delta_risk = risk_courant - risk_précédent
             → direction = "up" si delta > 1€, "down" si delta < -1€, "stable" sinon
             → trend = { risk_eur_delta, sites_count_delta, direction, vs_computed_at }
             → mettre à jour le cache avec snapshot courant
```

### Module cache

**`backend/services/patrimoine_portfolio_cache.py`**

- Dictionnaire global `_cache: Dict[int, Dict]` — clé = `org_id`
- Protégé par `threading.Lock()` (safe Uvicorn multi-thread)
- API : `get_prev_snapshot(org_id)`, `set_snapshot(org_id, snap)`,
  `clear_snapshot(org_id)`, `clear_all()`
- Snapshot minimal stocké : `{ computed_at, total_estimated_risk_eur, sites_count }`

### Règles de mise en cache

| Condition | Cache mis à jour ? | Trend calculé ? |
|-----------|-------------------|-----------------|
| Scope global (pas de filtre) | ✅ OUI | ✅ OUI (dès 2ème appel) |
| Filtre `site_id` présent | ❌ NON | ❌ trend=null |
| Filtre `portefeuille_id` présent | ❌ NON | ❌ trend=null |
| Scope vide (`sites_count == 0`) | ❌ NON | ❌ trend=null |

**Justification :** Ne mettre en cache que le scope global évite de polluer
la baseline du portfolio entier avec une vue partielle.

### EPS anti-bruit

`EPS = 1.0 €` — en dessous de ce seuil de delta absolu, la direction est
`"stable"`. Évite les faux signaux dus aux arrondis.

### Invalidation

- **Demo reset** (`POST /api/demo/reset-pack`) : appel `clear_all()` après le
  reset. Le prochain appel portfolio repartira sans historique.
- **Restart serveur** : cache perdu (in-memory). Le premier appel post-restart
  retourne `trend=null` — comportement attendu et documenté.

---

## Payload V62

```json
{
  "trend": {
    "risk_eur_delta": -4500.0,
    "sites_count_delta": 0,
    "direction": "down",
    "vs_computed_at": "2026-02-23T14:32:00Z"
  }
}
```

`trend` peut être `null` si :
- Premier appel (pas d'historique)
- Filtre actif (site_id ou portefeuille_id)
- Scope vide

---

## Fichiers modifiés / créés

| Fichier | Type | Description |
|---------|------|-------------|
| `backend/services/patrimoine_portfolio_cache.py` | NEW | Module cache in-memory |
| `backend/routes/patrimoine.py` | MODIFIÉ | Import + logique trend + set_snapshot |
| `backend/routes/demo.py` | MODIFIÉ | clear_all() après reset-pack |
| `backend/tests/test_portfolio_trend_v62.py` | NEW | 22 tests (unit + intégration) |
| `backend/tests/conftest.py` | MODIFIÉ | autouse fixture clear_all() |

---

## Tests

```
tests/test_portfolio_trend_v62.py — 22 tests
  TestPortfolioCacheUnit       (8) — get/set/clear/overwrite/None org
  TestPortfolioTrendV62       (14) — None 1er appel, non-None 2ème,
                                     stable/up/down, vs_computed_at,
                                     filtre site/pf → None, multi-org isolé,
                                     backward compat V61, scope vide
```

Suite complète V60 + V61 + V62 : **53/53 passed**.

---

## Limites acceptées

- **Single-process uniquement** : `threading.Lock()` ne protège pas contre
  les race conditions entre plusieurs *processus* Gunicorn. En prod multi-worker,
  migrer vers Redis (V64+).
- **Pas de TTL** : un snapshot survit jusqu'au prochain appel ou reset.
  Si le serveur redémarre sans reset, le premier appel retourne `trend=null`.
- **Scope global uniquement** : les vues filtrées (portefeuille, site) ne
  contribuent pas à la baseline. Si l'usage filtre systématiquement, trend
  reste `null` — à documenter dans l'UI (V63).

---

## Évolutions futures

- **V63** : Exposer `trend` dans l'UI sur le `TrendBadge` (déjà null-safe).
- **V64** : Remplacer dict in-memory par Redis pour prod multi-worker.
- **V65** : Historique complet (liste de snapshots) pour graphique de tendance.
