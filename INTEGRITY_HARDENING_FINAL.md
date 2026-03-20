# Integrity Hardening Final — Chaine patrimoine → conformite surveillee

> Date : 2026-03-16
> Commit : `e6421c8`
> Statut : Implemente, teste, pushe

---

## Corrections apportees

### Reevaluation usage/type/NAF
- Si `type` ou `naf_code` modifie sur un site :
  - EFA `trajectory_status` → `review_required`
  - BACS `bacs_scope_status` → `review_required`
  - `not_applicable` et `potentially_in_scope` non flagges (garde-fou)

### Job coherence periodique
- `run_coherence_check()` detecte 3 types d'anomalies :
  - **Orphelins** : EFA/BACS avec site archive
  - **Surface desync** : EfaBuilding ≠ batiment reel
  - **BACS stale** : assessment > 30 jours
- Retourne `status: clean | issues_detected` + `total_issues`

### Endpoint
- `GET /api/regops/bacs/coherence` — verification complete

---

## Tests (8 passes)

| Test | Verifie |
|------|---------|
| usage_change_flags_efa | EFA → review_required |
| usage_change_flags_bacs | BACS → review_required |
| not_applicable_not_flagged | Garde-fou |
| clean_state_with_assessment | Status clean si tout OK |
| detects_surface_desync | Surface divergente detectee |
| detects_orphan | Orphelin dans coherence |
| recompute_true | Recalcul BACS fonctionne |
| recompute_false_no_asset | Retourne false sans asset |

---

## Bilan integrity complet

| Commit | Correction | Tests |
|--------|-----------|-------|
| `a7aa57d` | Cascade archive + surface sync + orphelins | 8 |
| `e6421c8` | Reevaluation usage + coherence + recalcul | 8 |
| **Total integrity** | **2 commits** | **16 tests** |

---

## Bilan conformite complet session

| Zone | Commits | Tests |
|------|---------|-------|
| OPERAT | 8 | 96 |
| BACS | 8 | 61 |
| Integrity | 2 | 16 |
| Audit fixes | 2 | 0 |
| **Total** | **20** | **173** |

---

## Chaine patrimoine → conformite : etat final

```
Patrimoine modifie
    │
    ├── Surface change → EfaBuilding synchro auto
    ├── Usage/type change → EFA + BACS flag review_required
    ├── CVC modifie → BACS recalcul auto
    ├── Site archive → EFA + BACS cascade archive
    │
    └── Job coherence
         ├── Orphelins detectes
         ├── Surface desync detectees
         └── BACS stale detectes
```

**Plus de desynchronisation silencieuse.**
