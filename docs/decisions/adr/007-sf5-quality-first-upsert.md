# ADR-007: SF5 — Quality-first UPSERT pour la promotion

**Date**: 2026-04-12
**Statut**: Accepted
**Sprint**: Sprint 3 — SF5 Promotion Pipeline

---

## Contexte

Le pipeline SF5 promeut les donnees brutes Enedis (staging `enedis_flux_mesure_r4x`, `r50`, `r171`, `r151`) vers les tables fonctionnelles (`meter_load_curve`, `meter_energy_index`, `meter_power_peak`).

Enedis republie regulierement des donnees pour le meme (PRM, timestamp) :
- Une mesure initialement estimee (`statut_point=E`, quality=0.60)
- Ensuite corrigee (`statut_point=C`, quality=0.95)
- Finalement reelle (`statut_point=R`, quality=1.00)

Chaque run de promotion peut recevoir une republication qui ameliore ou degrade la qualite d'une row deja promue.

---

## Probleme

Quelle regle appliquer quand une row deja promue recoit une mise a jour ?

- Option A: Toujours ecraser (latest wins) -> perd les donnees R ecrasees par E
- Option B: Ne jamais ecraser (first wins) -> reste bloque sur les estimations initiales
- Option C: Comparer les qualites et choisir la meilleure

---

## Decision

**Option C avec comparateur `>=` (quality-first, latest wins on tie)**

Regle :
```
SI row.quality_score >= existing.quality_score:
    UPDATE existing avec les champs de row
SINON:
    SKIP (garder existing)
```

Le `>=` (pas `>`) est intentionnel : en cas d'egalite de qualite, la row la plus recente gagne, ce qui permet de propager des corrections mineures sans degrader la qualite moyenne.

### Points cles :

1. **Mapping qualite officiel Enedis** (dans `data_staging/quality.py`):
   - R (Reel) : 1.00
   - C (Corrige) : 0.95
   - S/T/F/G (Coupure) : 0.90
   - D (Import manuel) : 0.85
   - H (Reconstitue) : 0.80
   - K (Derive) : 0.75
   - P (Reconstitue + coupure) : 0.70
   - E (Estime) : 0.60
   - Inconnu : 0.50

2. **Preservation des champs null** : si `row.active_power_kw is None`, on ne l'ecrase PAS (fix du bug P0 `or` vs `is not None`).

3. **Zero preservation** : `0.0 kW` est une valeur legitime (site ferme, dimanche matin) et doit etre preservee. C'est pour cela qu'on teste `is not None` et pas `or` :
   ```python
   # FAUX (perd les zeros)
   existing.active_power_kw = row.active_power_kw or existing.active_power_kw
   # CORRECT
   existing.active_power_kw = (
       row.active_power_kw if row.active_power_kw is not None else existing.active_power_kw
   )
   ```

---

## Consequences

### Positives

- Auto-promotion des corrections (E -> R propage automatiquement)
- Pas de regression silencieuse sur des donnees zero
- Compatible avec la republication Enedis sans intervention manuelle
- Deterministe et testable

### Negatives

- Une republication de qualite inferieure est silencieusement ignoree (logguee uniquement)
- La table `promotion_event` ne capture pas encore les skips (spec future)

---

## Implementation

### Batch upsert (Sprint 7)

Pour resoudre le N+1 query initial, l'implementation finale utilise 3 queries par chunk de 1000 rows :

1. `SELECT` batch fetch des rows existantes (1 query via `tuple_(*cols).in_(...)`)
2. `INSERT` batch des nouvelles rows (1 query via `bulk_save_objects`)
3. `UPDATE` batch des rows existantes a ecraser (1 query via `bulk_update_mappings`)

Gain : 3 queries / 1000 rows (vs 2000+ dans la version naive). Sur 100k rows : 300 queries au lieu de 200 000.

### Fichier

`backend/data_staging/engine.py::_upsert_quality_first()`

Testes par :
- `tests/test_sf5_e2e.py::TestE2ESF5Pipeline::test_full_chain_matched_and_promoted` (verifie que la qualite est correctement propagee)
- `tests/test_sf5_e2e.py::TestE2ESF5Pipeline::test_incremental_mode_respects_high_water_mark` (verifie que les re-runs ne creent pas de doublons)

---

## Bugs corriges par ce pattern

1. **P0 `or` vs `is not None`** (Sprint 3 audit) : le `or` perdait les valeurs zero
2. **P0 HWM mode incremental** (Sprint 5 audit) : `_load_last_hwm()` lit depuis le dernier `completed` run, pas depuis `max(id)` courant

---

## References

- Spec SF5 : `docs/specs/feature-enedis-sge-6-data-staging.md` (section D4)
- Doctrine CDC : `.claude/skills/promeos-enedis/references/courbes-charge-doctrine.md`
