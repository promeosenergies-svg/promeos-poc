# PROMEOS Performance Benchmarks — Sprint C-4 Phase 4.6

**Date** : 2026-05-05
**Sprint** : C-4 Phase 4.6
**Hardware référence** : macOS dev (M-series Apple Silicon, Python 3.11.9, SQLite in-memory)
**Tests fichier** : `backend/tests/test_bulk_recompute_perf.py`
**Marker pytest** : `@pytest.mark.perf` (exécution manuelle `venv/bin/python -m pytest -m perf`)

---

## Résultats benchmarks Phase 4.6 (5/5 cibles ✅)

| Scénario | Cible | Mesuré | Marge | Statut |
|---|---|---|---|---|
| `recompute_organisation` 50 sites | < 2 sec | **0.10s** | x20 | ✅ |
| `recompute_organisation` 200 sites | < 8 sec | **0.28s** | x29 | ✅ |
| `recompute_organisation` 500 sites | < 25 sec | **0.68s** | x37 | ✅ |
| `get_effective_consent` x50 DPs (Phase 4.5) | < 500ms | **0.01s** | x50 | ✅ |
| Cascade GRDF court-circuit ELD x500 DPs | < 3 sec | **0.04s** | x75 | ✅ |

**Verdict** : Toutes cibles **largement tenues** avec marges x20 à x75. Pas de goulot d'étranglement détecté MVP Sprint C-4.

---

## Méthodologie

### Fixtures bulk

Factory pattern `_create_org_with_n_sites(db, n)` génère in-memory :

- 1 Organisation + 1 EntiteJuridique + 1 Portefeuille
- N Sites avec `surface_m2`, `annual_kwh_total` populés
- 2 DPs par site : 1 ENEDIS élec + 1 GRDF gaz

**Volumétrie totale 500 sites** : 1 Org + 1 EJ + 1 PF + 500 sites + 1000 DPs (500 élec + 500 gaz GRDF). Permet test bulk + cascade GRDF court-circuit ELD à grande échelle.

### Pattern test perf

```python
@pytest.mark.perf
def test_recompute_organisation_50_sites_under_2sec(db_session, org_with_50_sites):
    from services.compliance_coordinator import recompute_organisation

    start = time.time()
    result = recompute_organisation(db_session, org_with_50_sites.id)
    duration = time.time() - start

    assert result["sites_recomputed"] == 50
    assert duration < 2.0, f"50 sites recompute took {duration:.2f}s (cible <2s)"
```

---

## Limites de l'environnement de test

⚠️ **Mesures sur SQLite in-memory + macOS dev**. En production (PostgreSQL + latence réseau + concurrence I/O), les chiffres seront **plus élevés** mais conservent une marge de sécurité confortable :

| Facteur | Impact estimé prod vs dev |
|---|---|
| PostgreSQL vs SQLite in-memory | ×3 à ×5 (latence connexion + parse SQL) |
| Latence réseau prod | +50-200ms par batch |
| Concurrence multi-tenant | ×1.5 à ×2 selon load |

**Estimation prod x10 dégradation conservative** :

| Scénario | Mesuré dev | Estimation prod | Cible | Marge prod |
|---|---|---|---|---|
| 50 sites | 0.10s | ~1s | <2s | x2 |
| 200 sites | 0.28s | ~3s | <8s | x2.7 |
| 500 sites | 0.68s | ~7s | <25s | x3.6 |

→ Marges prod **suffisantes** pour pilote pré-prod sans optimisation cardinale Sprint C-7.

---

## Optimisations possibles (Sprint C-7 polish, si besoin réel post-pilote)

Si métriques prod réelles montrent dégradation > x10 vs dev, opportunités :

1. **Bulk SELECT** pour DPs (1 query JOIN vs N+1 lazy load FK chains)
   - Actuel : `dp.site.portefeuille.entite_juridique.organisation` lazy load N+1 dans `get_effective_consent`
   - Optim : `joinedload` SQLAlchemy ou eager loading dans le helper bulk
2. **Lazy compliance_score** (skip recompute si pas de changement input détecté)
   - Actuel : `_bulk_recompute(db, sites)` recompute tous les sites systématiquement
   - Optim : delta-based recompute (cache dirty bits)
3. **Cache Redis 5 min** pour intermédiaires (`Cabs OPERAT`, `compliance_score`)
   - Actuel : recalcul à chaque cascade trigger
   - Optim : invalidation cache uniquement sur input change détecté
4. **Pagination bulk** pour orgs > 1000 sites
   - Actuel : single query `.all()` charge tout en mémoire
   - Optim : `.yield_per(100)` SQLAlchemy streaming

**Aucune de ces optims n'est nécessaire MVP** Phase C — métriques dev <1s pour 500 sites laissent ample marge pour pilote.

---

## Notes méthodologiques

### Tests perf vs CI standard

Les tests `@pytest.mark.perf` sont **exclus de la CI standard** (déclarés dans `pyproject.toml` markers section). Exécution :

- **Manuelle** : `venv/bin/python -m pytest -m perf` (commande développeur)
- **Hebdomadaire** : workflow CI dédié optionnel Sprint C-7+ (`schedule: '0 2 * * 0'` cron dimanche nuit)

### Pas de tests perf en CI standard

Justification : les tests perf incluent fixtures bulk creation (500 sites + 1000 DPs en in-memory) qui prennent ~0.24s setup chacun. En CI exécutant `pytest tests/` complet, ces tests ralentiraient la pipeline dev cycle. Discipline "tests rapides en CI, perf en dédié" cohérente avec marker `fast` Sprint C-1.

### Re-run benchmarks

Pour ré-exécuter les benchmarks (post-changement archi cardinal) :

```bash
cd backend
venv/bin/python -m pytest tests/test_bulk_recompute_perf.py -m perf --durations=0
```

Le flag `--durations=0` affiche le temps précis de chaque test (call + setup) pour mise à jour de cette doc.

---

## Tracker dette

**Phase 4.6 résultat** : pas de nouvelle dette ouverte (toutes cibles tenues largement).

Si métriques prod post-pilote dégradent > x10 vs dev, ouvrir dette `D-Sprint-C7-Bulk-Recompute-Perf-Optim-001` P1 avec scope optimisation cardinale (option 1-4 ci-dessus selon profiling).

---

**Référence implémentation** : Phase 4.6 commit (à insérer hash post-commit).
