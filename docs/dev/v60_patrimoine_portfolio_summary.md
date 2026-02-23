# V60 — Patrimoine Portfolio Summary : contrat API & performance

## Endpoint

```
GET /api/patrimoine/portfolio-summary
```

### Paramètres query

| Paramètre        | Type    | Défaut | Description                                        |
|-----------------|---------|--------|----------------------------------------------------|
| `portefeuille_id` | int   | null   | Filtre résultat au portefeuille indiqué            |
| `site_id`         | int   | null   | Filtre résultat à un site unique                   |
| `top_n`           | int   | 3      | Nombre de top sites retournés (1..10)              |

### Payload de réponse

```json
{
  "scope": {
    "org_id": 1,
    "portefeuille_id": null,
    "site_id": null
  },
  "total_estimated_risk_eur": 43200.0,
  "sites_count": 3,
  "sites_at_risk": {
    "critical": 0,
    "high": 2,
    "medium": 1,
    "low": 0
  },
  "framework_breakdown": [
    { "framework": "DECRET_TERTIAIRE", "risk_eur": 21600.0, "anomalies_count": 2 },
    { "framework": "FACTURATION",      "risk_eur": 7200.0,  "anomalies_count": 1 }
  ],
  "top_sites": [
    {
      "site_id": 12,
      "site_nom": "Tour Coface",
      "risk_eur": 21600.0,
      "anomalies_count": 3,
      "top_framework": "DECRET_TERTIAIRE"
    }
  ],
  "computed_at": "2026-02-23T14:32:00Z"
}
```

### Sémantique des champs

| Champ                      | Sémantique                                                            |
|---------------------------|-----------------------------------------------------------------------|
| `total_estimated_risk_eur` | Somme de `business_impact.estimated_risk_eur` sur toutes anomalies enrichies |
| `sites_at_risk`            | Distribution par sévérité *la pire* du site (1 bucket par site)      |
| `framework_breakdown`      | Agrégat risk + count par framework réglementaire (NONE exclu), trié risk DESC |
| `top_sites`                | Les `top_n` sites avec le risque € le plus élevé, triés DESC         |
| `top_framework`            | Framework de l'anomalie à `priority_score` le plus élevé du site     |

---

## Architecture de calcul

```
GET /portfolio-summary
    │
    ├── resolve_org_id()           # scope org — jamais Organisation.first()
    ├── SQL: Site JOIN Portefeuille JOIN EntiteJuridique WHERE org_id = ?
    │         [ + filtre optionnel portefeuille_id / site_id ]
    │
    └── for site in all_sites:
            compute_site_anomalies(site.id, db)       # V58 — 8 règles P0
            enrich_anomalies_with_impact(anomalies)   # V59 — regulatory + business + priority_score
            → aggregate: total_risk, sites_at_risk, framework_totals, site_summaries
    │
    └── Sort top_sites DESC by risk_eur → slice [:top_n]
        Sort framework_breakdown DESC by risk_eur
```

**Zéro N+1 SQL** : une seule requête SQL pour récupérer les sites (avec JOINs). Les appels à `compute_site_anomalies()` font chacun leurs propres requêtes batchées (pas de N+1 interne — voir `patrimoine_anomalies.py`).

**Zéro accès DB dans l'enrichissement** : `enrich_anomalies_with_impact()` est une pure function qui opère sur des dicts en mémoire.

---

## Performance

| Scenario           | Sites | Anomalies/site | Temps estimé |
|-------------------|-------|----------------|--------------|
| Petit portefeuille | 10    | 2–4            | ~50 ms       |
| Moyen             | 50    | 2–4            | ~250 ms      |
| Grand             | 200   | 2–4            | ~1 s         |

**Optimisations actives :**
- `_cachedGet` côté frontend (TTL 5s) : pas de double fetch au StrictMode double-mount
- `top_n` limité à 10 : payload garanti petit
- Agrégation 100 % backend : pas de boucle frontend sur tous les sites

**Si le portefeuille dépasse ~500 sites** : envisager un endpoint dédié avec pagination ou un job de précalcul (voir ADR V60).

---

## Contrats de compatibilité

- **Backward compat V59** : endpoint additionnel, aucun modèle existant modifié.
- **Multi-org safe** : `org_id` résolu via `resolve_org_id()` — aucun `Organisation.first()`.
- **Scope vide → 0** : si aucune org ou aucun site, retourne zeros + listes vides.
- **top_framework = null** si le site n'a que des anomalies framework=NONE.

---

## Tests

```bash
# Backend
pytest tests/test_patrimoine_portfolio_v60.py -v

# Frontend source guards
npx vitest run src/pages/__tests__/patrimoineV60.test.js
```

Couverture tests backend :
- `TestPortfolioSummaryEmpty` : scope vide, no org, zeros garantis
- `TestPortfolioSummaryNominal` : risk > 0, top_sites, framework_breakdown, sort DESC
- `TestPortfolioSummarySiteFilter` : filtre site_id, top_n, multi-org isolation
