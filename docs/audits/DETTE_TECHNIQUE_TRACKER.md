# Tracker dette technique PROMEOS

> Document interne — référencé par les commits, source-guards, et issues.
> À revue trimestrielle (ou plus fréquente si dette > 5 entrées).

## Légende criticité
- 🔴 **P0** : bloquant production / sécurité
- 🟠 **P1** : crédibilité B2B / différenciateur perdu
- 🟡 **P2** : polish / dette technique non bloquante

---

## D-Enedis-Legacy-001 — Tables Enedis legacy sans modèle SQLAlchemy

**Détecté** : Sprint C-1 Phase 3 étape 5 (autogenerate Alembic, 2026-05-03)

**Tables concernées** (17) :
- annotations, annotator_profiles
- meter_load_curve, meter_energy_index, meter_power_peak
- enedis_opendata_conso_inf36, enedis_opendata_conso_sup36
- enedis_flux_mesure_r151, enedis_flux_mesure_r171, enedis_flux_mesure_r4x, enedis_flux_mesure_r50
- enedis_flux_file, enedis_flux_file_error, enedis_ingestion_run
- unmatched_prm, promotion_run, promotion_event

**Hypothèse** : vestiges archi pré-`data_ingestion/` actuel. Anciens modèles supprimés sans migration de drop.

**Symptôme** : `alembic revision --autogenerate` détecte les tables comme "à dropper" parce qu'elles n'ont plus de modèle SQLAlchemy correspondant. Le fichier de migration `c8f1246522f9_*.py` a été nettoyé manuellement Phase 3 pour retirer ces 17 `op.drop_table()`.

**Action** :
- Audit data lineage Enedis (sprint séparé, post C-1)
- Identifier table par table : drop ou rétablir modèle
- Migration ad-hoc séparée pour les drops confirmés

**Effort estimé** : 1-2 j-h
**Priorité** : 🟡 P2 (pas bloquant Phase C)
**Sprint cible** : à planifier post Sprint C-7

**Traces** :
- Commit Phase 3 nettoyage migration : `c8f1246522f9` (retire 17 drop_table de l'autogenerate)
- Backup migration originale : `backend/alembic/versions/c8f1246522f9_*.py.original-autogenerate`

---

## D-Phase3-Legacy-Zones-001 — Zones OPERAT (H1a..H3) en string littéral dans 3 services

**Détecté** : Sprint C-1 Phase 3 étape 9 (source-guard, 2026-05-03)

**Fichiers concernés (8 occurrences)** :

| Fichier:ligne | Snippet | Contexte |
|---|---|---|
| `backend/regops/rules/cee_p6.py:97` | `zone = "H2b"` | CEE P6 calculs zone-spécifiques |
| `backend/services/weather_provider.py:16` | `"H3": 1600` | Lookup table altitude |
| `backend/services/weather_provider.py:98` | `"H3" for d in [...]` | Mapping département → zone |
| `backend/services/aper_service.py:136-148` | `"Occitanie": "H3", "H3": [5,6,...]` | Mapping régions → zones (DJU mensuel) |
| `backend/services/aper_service.py:220` | `{"H1": 1050, "H2": 1150, "H3": 1350}` | Hours équiv production solaire |

**Cause** : code legacy pré-Phase 3, écrit avant la création de `OperatZoneClimatiqueEnum`.

**Risque** :
- 🟡 P2 : pas de bug fonctionnel — strings et `enums.value` sont équivalents au runtime
- ⚠️ Fragilité : si l'enum change ses values (ex : rename "H3" → "H_3"), ces 3 fichiers ne suivront pas
- 🔧 Cohérence doctrinale : viole "single source of truth" pour les zones

**Action** :
- Refactor 3 fichiers : remplacer strings par `OperatZoneClimatiqueEnum.X.value` ou `.X` selon contexte
- Garder les tests métier existants verts (CEE, weather, aper)
- Ajouter test paramétré pour valider migration sans régression

**Effort estimé** : 30-60 min par fichier × 3 = 1.5-3 h ⋍ 0.5 j-h

**Priorité** : 🟡 P2 (allowlist temporaire dans source-guard, pas bloquant Phase C)

**Sprint cible** : Sprint C-4 (Tests + observabilité) ou Sprint C-2 (FE cleanup) selon disponibilité

**Allowlist active** : `backend/tests/source_guards/test_operat_aper_enums_no_string_literal_source_guards.py::_LEGACY_FILES_GRANDFATHERED`

**Traces** :
- Source-guard avec allowlist : commit Phase 3 (sprint C-1)
- DeprecationWarning émis à chaque exécution du source-guard (visibilité continue)

---

## D-EMS-Overlay-Org-Scoping-001 — `test_overlay_two_sites` pré-existant rouge

**Détecté** : Sprint C-1 Phase 3 baseline check (2026-05-03)

**Test concerné** : `tests/test_ems_overlay.py::TestOverlayMode::test_overlay_two_sites`

**Symptôme** : 403 "Organisation non résolue" (route `/api/ems/timeseries`)

**Vérification** : test rouge déjà sur HEAD `claude/refonte-sol2` pré-Phase 3 — confirmé via `git stash` + re-test.

**Suspicion** : org-scoping fragile sur route `/api/ems/timeseries`

**Action** :
- Investigation org-scoping route `/api/ems/timeseries`
- Vérifier helper `_get_org_id` ou équivalent
- Diagnostiquer : test factory cassée OU route mal scopée OU les deux

**Effort estimé** : 1-2 j-h
**Priorité** : 🟠 P1 (test rouge persistant = signal observabilité fragile)
**Sprint cible** : Sprint C-2 (FE cleanup + temporalité, contexte org-scoping multi-tenant)

**Traces** :
- Bilan Sprint C-1 Phase 3 (ce sprint)
- Ce test n'est PAS une régression Phase 3 (vérifié au stash)

---

## D-Phase4-Fuzzy-Mapping-Annexes-001 — Coeff DJU non résolus pour sous-cat Annexe I non listées Annexe II

**Détecté** : Sprint C-1 Phase 4 (2026-05-03)

**Comportement actuel** :
- `OperatValeursAbsoluesService.get_coeff_dju()` retourne `None` si sous-catégorie
  Annexe I non listée dans `Annexe II.categories_couvertes`
- `compute_cabs_2030()` skip proprement l'ajustement DJU dans ce cas
- Cabs résultant = CVC étalon + USE étalon (pas d'ajustement climat DJU)

**Risque** : Cabs imprécis pour les sous-cat sans Coeff DJU. Pas faux mathématiquement, mais pas optimal pour les sites réels avec données météo non-étalon.

**Action** :
- Audit complet Annexe I (426 sous-cat) vs Annexe II (13 groupes G1-G13)
- Identifier les sous-cat orphelines (sans groupe Coeff DJU)
- Décider : (a) mapping fuzzy "best-match" via similarité texte, (b) defaults par catégorie parent, (c) tracker explicite côté Site (`coeff_dju_status` enum : RESOLVED/MISSING/DEFAULTED)

**Effort estimé** : 2-3 j-h (audit + impl + tests)
**Priorité** : 🟡 P2 (MVP fonctionnel, optimisation différée)
**Sprint cible** : Sprint C-6 (Modèles enrichis) ou sprint séparé "OPERAT precision"

**Traces** :
- Test : `tests/test_operat_cabs_service.py::test_get_coeff_dju_returns_none_when_not_mapped`
- Service : `backend/regops/services/operat_cabs_service.py::OperatValeursAbsoluesService.get_coeff_dju`

---

## ✅ CLÔTURÉ 2026-05-03 — D-Phase4-Encoding-Reunion-001 (Annexe I utilise bien "Reunion" sans accent)

**Détecté** : Sprint C-1 Phase 4 normalisation zones DOM (2026-05-03)

**Investigation** : Audit du fichier `backend/config/operat_annexe_i_sous_categories.json` :
- `zones_order` contient bien `"Reunion"` (sans accent) — 1 occurrence
- 0 occurrence de `"Réunion"` (avec accent) ou `"La Réunion"` dans le JSON

**Conclusion** : la normalisation `_normalize_zone_for_annexe_i()` du service est cohérente
avec l'encodage du JSON. Aucune action corrective requise. La normalisation accepte aussi
les formats UI ("Réunion", "La Réunion") avec mapping vers la forme JSON.

**Action** : ❌ AUCUNE — comportement actuel correct.

**Statut** : ✅ Clôturé Sprint C-1 Phase 5 (avant build, audit en passant).

---

## D-Phase5-DtBacsAssujetti-Volatile-001 — `dt_assujetti` / `bacs_assujetti` calculés à la volée

**Détecté** : Sprint C-1 Phase 5.1 (2026-05-03)

**Comportement actuel** :
- `dt_assujetti` calculé à la volée via `_is_dt_assujetti(site)` = `site.tertiaire_area_m2 >= 1000`
- `bacs_assujetti` calculé à la volée via `_is_bacs_assujetti(site)` = `sum(b.cvc_power_kw for b in site.batiments) >= 70`
- `aper_assujetti` est stocké en colonne DB (ajouté Phase 3)

**Décision Phase 5** : ne pas dénormaliser ces 2 champs maintenant pour ne pas scope creep migration (Option A retenue).

**Action** :
- Phase 6 (cascade_recompute_service) : si performance OK avec calcul à la volée, peut rester
- OU Sprint C-6 (Modèles enrichis) : dénormalisation en colonnes stockées avec recalcul cascade
- Décision finale : à arbitrer en Phase 6 ou C-6 selon impact perf observé

**Effort estimé** : 1-2 j-h (migration Alembic + cascade trigger)
**Priorité** : 🟡 P2 (fonctionnel sans dénorm)
**Sprint cible** : Phase 6 ou Sprint C-6 (à arbitrer)

**Traces** :
- Service : `backend/services/compliance_score_service.py::_is_dt_assujetti` / `_is_bacs_assujetti`

---

## Métriques tracker

| Date | Nb dettes ouvertes | Nb dettes P0 | Nb dettes P1 | Nb dettes P2 |
|---|---|---|---|---|
| 2026-05-03 | 5 | 0 | 1 | 4 |

---

## Procédure d'ouverture / clôture d'entrée

**Pour ouvrir une nouvelle entrée** :
1. Identifier un code unique : `D-<sprint/contexte>-<topic>-<NNN>` (ex : `D-C2-FE-Patrimoine-001`)
2. Documenter : détection, fichiers, cause, risque, action, effort, priorité, sprint cible
3. Ajouter une référence dans le commit qui détecte la dette
4. Si grandfathering nécessaire (allowlist source-guard, exclusion test) : référencer l'entrée dans le code

**Pour clôturer une entrée** :
1. Une fois la dette résorbée : barrer l'entrée avec `~~D-...~~` et préfixer "✅ CLÔTURÉ <date>"
2. Lien vers le commit/PR qui résout
3. Mettre à jour la table métriques
4. Conserver l'historique pour traçabilité (ne pas supprimer)
