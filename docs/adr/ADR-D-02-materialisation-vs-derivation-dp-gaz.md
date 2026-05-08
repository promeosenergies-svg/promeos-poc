# ADR-D-02 — Matérialisation vs dérivation runtime DP gaz (5 P0 §4.6.C)

**Statut** : ✅ ACCEPTED — implémenté Phase D-4 Tier 1 (commit `2268e90d`)
**Date** : 2026-05-08
**Sprint** : Phase D-4 Tier 1 candidat
**Décideurs** : à figer post-revue (architect-helios + bill-intelligence + regulatory-expert)

## Contexte

Audit écarts matrice v1 (commit Phase 0 cardinal `AUDIT_ECARTS_MATRICE_V1_2026_05_07.md`) révèle 5 P0 cardinaux §4.6.C DP gaz **déductibles via regex/grd_code mais non matérialisés** :

- `pce_format` (Enum DISTRIBUTION_14/DISTRIBUTION_GI/TRANSPORT_PIR) — déductible via regex `code`
- `type_reseau` (Enum DISTRIBUTION/TRANSPORT) — déductible via grd_code
- `referentiel_tarifaire` (Enum ATRD/ATRT) — déductible via type_reseau
- `est_profile` (bool) — déductible via atrd_option (T1/T2/T3 = profilé)
- `mode_releve` (Enum MM/MJ/JJ/MH) — non déductible, requiert saisie

Validators regex Phase D-3 Tier 2 garantissent la cohérence du `code` mais ne matérialisent pas le format en colonne explicite.

## Options

### Option A — Matérialiser colonnes physiques + validators cohérence

- **Pour** : traçabilité audit, perf query (filtrage `WHERE type_reseau='TRANSPORT'`), cohérence Phase D-3 cardinal
- **Contre** : migration Alembic 16e + risque divergence si validators incomplets

### Option B — `@property` derived runtime

- **Pour** : pas de migration, pas de risque divergence (single source of truth = `code`)
- **Contre** : impossible filtrage SQL direct, perf dégradée, pas de traçabilité audit

### Option C — Hybride (matériel + cache invalidation)

- **Pour** : meilleur des deux mondes
- **Contre** : complexité accrue, risque cache stale

## Décision (à figer Phase D-4 Tier 1)

**Recommandation cardinal** : Option A (matérialiser).

Justification :
1. Pattern Pilier 1 ADR-016 (SoT runtime) : matérialisation aligne avec doctrine
2. Audit traçabilité CNIL Article 5(2) accountability — colonnes physiques cardinaux
3. Perf query billing : filtrage `type_reseau` direct vs JOIN runtime

## Conséquences

- Migration Alembic 16e (anti-DROP discipline 16e épisode)
- Validators cohérence cross-FK (pce_format ↔ code regex)
- Cascade `cascade_recompute_service` si `code` modifié → recalcul format

## Effort estimé

**4-6h** : migration + validators + tests + cascade.

## Liens

- [`AUDIT_ECARTS_MATRICE_V1_2026_05_07.md`](../audits/AUDIT_ECARTS_MATRICE_V1_2026_05_07.md) §3 P0-MATV1-006/007/008
- [`AUDIT_CODES_FTA_TURPE7_2026_05_07.md`](../audits/AUDIT_CODES_FTA_TURPE7_2026_05_07.md) (Pilier 9 ADR-016 connexe)
- Matrice v1 : [`docs/produit/patrimoine_parametrage_requis_v1.md`](../produit/patrimoine_parametrage_requis_v1.md) §4.6.C
