# Integrity Patrimoine → Conformite — Chaine reparee

> Date : 2026-03-16
> Commit : `a7aa57d`
> Statut : Implemente, teste, pushe

---

## Corrections apportees

| Fail critique | Avant | Apres |
|---|---|---|
| Site archive → EFA/BACS orphelins | Pas de cascade | cascade_site_archive() archive EFA + BACS |
| BacsAsset non archivable | Pas de SoftDeleteMixin | SoftDeleteMixin ajoute |
| Surface EfaBuilding desynchronisee | Snapshot a la creation, jamais synchro | flag_efa_desync_on_surface_change() synchro auto |
| CVC modifie → BACS obsolete | Recalcul manuel uniquement | auto_recompute_bacs() sur add/update/delete CVC |
| Aucune detection orphelins | Pas de mecanisme | detect_orphans() + endpoint /orphans |

---

## Service patrimoine_conformite_sync.py

| Fonction | Role |
|----------|------|
| cascade_site_archive(db, site_id) | Archive EFA + BACS quand site archive |
| flag_efa_desync_on_surface_change(db, site_id) | Synchro surface EfaBuilding avec batiment reel |
| auto_recompute_bacs(db, site_id) | Recalcul BACS apres modif CVC |
| detect_orphans(db) | Detecte EFA/BACS avec site archive |

---

## Points de branchement

| Route | Modification | Sync declenche |
|-------|-------------|---------------|
| POST /sites/{id}/archive | Apres soft_delete | cascade_site_archive |
| DELETE /patrimoine/crud/sites/{id} | Apres soft_delete | cascade_site_archive |
| PATCH /patrimoine/sites/{id} | Si surface/type/NAF modifie | flag_efa_desync_on_surface_change |
| POST /bacs/asset/{id}/system | Apres ajout CVC | auto_recompute_bacs |
| PUT /bacs/system/{id} | Apres modif CVC | auto_recompute_bacs |
| DELETE /bacs/system/{id} | Apres suppression CVC | auto_recompute_bacs |

---

## Tests (8 passes)

| Test | Verifie |
|------|---------|
| archive_site_cascades_efa | EFA archivee quand site archive |
| archive_site_cascades_bacs | BacsAsset archive quand site archive |
| efa_not_visible_after_cascade | not_deleted filtre correctement |
| surface_change_syncs | EfaBuilding.surface_m2 mis a jour |
| no_sync_if_same | Pas de synchro inutile |
| detects_efa_orphan | EFA orpheline detectee |
| detects_bacs_orphan | BACS orphelin detecte |
| no_orphan_when_clean | Zero faux positif |

---

## Avant / apres

| Scenario | Avant (40/100) | Apres |
|----------|---------------|-------|
| Archive site | EFA/BACS visibles | Archives automatiquement |
| Modif surface | EfaBuilding diverge | Synchro auto |
| Ajout CVC | BACS obsolete | Recalcul auto |
| Orphelins | Pas detectes | Endpoint /orphans |
| BacsAsset supprime | Hard delete seul | Soft delete possible |

---

## Limites restantes

| Limite | Effort |
|--------|--------|
| Badge UI "a recalculer / desynchronise" | S |
| Auto-creation EFA/BACS a la provision site | L |
| Job coherence periodique | M |
| Re-evaluation eligibilite si usage change | M |
