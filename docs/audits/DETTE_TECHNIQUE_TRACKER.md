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

## ~~D-Phase5-Frontend-NonApplicable-001~~ — ✅ CLÔTURÉ 2026-05-04 — Frontend doit gérer score=null + confidence="non_applicable"

**Clôture** : Sprint C-2 Phase 4.5a-c (commits b2e4cf25 + 325c64c9 + 75c09204 + 8553ac99 follow-up)
- Composant `frontend/src/components/NonApplicableLabel.jsx` créé (3 variants + a11y) — Phase 4.5a
- 3 fixes ciblés ConformitePage / ComplianceScoreHeader / RegOps — Phase 4.5b
- Revue 18 fichiers consommateurs + propagation `compliance_score_confidence` BE→FE — Phase 4.5c
- 2 fixes audit follow-up (PerformanceSitesCard + duplication intra-Phase header) — Phase 4.5d

**Original** :

**Détecté** : Sprint C-1 Phase 5 livraison (2026-05-03)

**Comportement actuel** :
- API `compute_site_compliance_score` retourne désormais `score=None` + `confidence="non_applicable"`
  quand site sans obligation active
- Format breakdown : `[{framework, score, weight, available, source}]` (inchangé V1)

**Impact frontend** (16 fichiers identifiés Phase 5.1) :
- `ScoreBreakdownPanel.jsx` : peut crasher sur `null.toFixed()` ou similaire
- `ScoreCircle` : assume `score: Number`
- `ConformitePage`, `RegOps`, `BacsWizard`, `ComplianceScoreHeader`, `SitesMap`, `useCockpitData` :
  assume confidence ∈ {high, medium, low}

**Action Sprint C-2** :
- Audit défensif des 16 consommateurs
- Affichage label "Non applicable" pour cas `score=null`
- Confidence `non_applicable` → état UI dédié (pas erreur)
- Tests E2E couvrant les 2 cas (avec/sans obligation)

**Effort estimé** : 4-6 h (audit + fix + tests E2E)
**Priorité** : 🟠 P1 (régression UX possible avant fix)
**Sprint cible** : Sprint C-2 (FE cleanup) en P0 — bloquant si site démo HELIOS sans obligation

---

## D-Phase5-Score-None-Propagation-001 — Audit callsites pattern `r.score * weight` autres

**Détecté** : Sprint C-1 Phase 5 régression mid-flight (2026-05-03)

**Symptôme corrigé** : `compute_portfolio_compliance:377` crashait sur `r.score * weight`
pour sites V2 NON_APPLICABLE (`score=None`). Fix : filtre `scorable_results` avant agrégation.

**Suspicion** : d'autres callsites du même pattern peuvent crasher dans des cas
non couverts par les tests existants (notamment dashboards aggregations).

**Action** :
- `grep -rn "score\s*\*\|\*\s*r\.score\|score.*weight\|weighted.*score" backend/`
- Identifier callsites suspects
- Pour chacun : vérifier gestion `None` propagation
- Ajouter tests d'intégration multi-sites mix V2-applicable / V2-non_applicable

**Effort estimé** : 2-3 h
**Priorité** : 🟡 P2 (defensive — pas de bug connu actuellement)
**Sprint cible** : Sprint C-2 ou C-4

---

## ~~D-Phase6-Cascade-EJ-Sites-001~~ — ✅ CLÔTURÉ 2026-05-04 (pivoté + renommé) — Cascade EJ.consommation_3y → audit_sme + compliance multi-sites

**Détecté** : Sprint C-1 Phase 6.1 audit pré-build (2026-05-03)
**Pivot** : Sprint C-2 Phase 5.1 audit pré-build (2026-05-04) — découverte modèle

**Découverte critique Phase 5.1** : `EntiteJuridique.consommation_annuelle_moyenne_3y_gwh` **n'existe pas** dans le modèle ORM. Le champ canonique est `AuditEnergetique.conso_annuelle_moy_gwh` qui est **org-scoped** (FK `organisation_id`), pas EJ-scoped. La cascade originale ciblait un champ inexistant.

**Pivot Option A acté** (2026-05-04) : cascade depuis `AuditEnergetique.conso_annuelle_moy_gwh` (SoT canonique) vers `recompute_organisation(db, organisation_id)`. Voir nouvelle entrée `D-Phase6-Cascade-AuditSme-Org-Sites-001` qui clôture le périmètre.

**Périmètre original (pour mémoire)** : Modification `EntiteJuridique.consommation_annuelle_moyenne_3y_gwh` devait cascade vers :
- `audit_energetique.obligation` (recalcul AUCUNE / AUDIT_4ANS / SME_ISO50001 selon seuils 2.75 / 23.6 GWh)
- Compliance score TOUS sites de l'EJ (impact dimensions AUDIT_SME / ISO_50001)

**Statut** : ✅ **CLÔTURÉ 2026-05-04 sous nouveau nom** `D-Phase6-Cascade-AuditSme-Org-Sites-001` (Phase 5.2 commit). Le pivot vers org-scoped est plus cohérent avec l'architecture existante (audit_sme.organisation_id). Si à terme une EJ unique est nécessaire (cas multi-EJ par org), une dette plus fine pourra être créée Sprint C-7 polish.

**Note matrice v1 §6** : si `EntiteJuridique.consommation_annuelle_moyenne_3y_gwh` y figure encore comme champ attendu, à corriger Sprint C-7 polish (champ dérivé via AuditEnergetique org-scoped, pas champ direct EJ).

---

## ~~D-Phase6-Cascade-AuditSme-Org-Sites-001~~ — ✅ CLÔTURÉ 2026-05-04 — Cascade AuditEnergetique.conso → obligation + recompute_organisation

**Détecté** : Sprint C-1 Phase 6.1 (originellement EJ-Sites-001), pivoté Sprint C-2 Phase 5.1 (2026-05-04)

**Périmètre** : Modification `AuditEnergetique.conso_annuelle_moy_gwh` cascade vers :
- `AuditEnergetique.obligation` recalculée selon seuils loi 30/04/2025 (≥23.6 GWh → SME_ISO50001 ; ≥2.75 GWh → AUDIT_4ANS ; <2.75 → AUCUNE)
- `compliance_coordinator.recompute_organisation(db, audit_sme.organisation_id)` → bulk recompute compliance score TOUS sites de l'organisation

**Action Phase 5.2** :
- Ajouter entrée `CASCADE_MAP_MVP_SPRINT_C1["AuditEnergetique.conso_annuelle_moy_gwh"]`
- 2 helpers `_recompute_audit_sme_obligation` + `_recompute_organisation_via_coordinator`
- Tests : 3 obligations × seuils + 2 limites + résilience + perf 50 sites

**Effort estimé** : ~2 h (vs 3-4 h estimé avant pivot, simplifié grâce à existence `recompute_organisation`)
**Priorité** : 🟠 P1 (déclencheur Audit SMÉ deadline 11/10/2026 critique)
**Sprint cible** : Sprint C-2 Phase 5.2 — **clôturée par commit Phase 5.2**

---

## D-Phase6-Cascade-Org-Consentements-001 — Cascade Org.consentement_dataconnect / grdf → tous DPs

**Détecté** : Sprint C-1 Phase 6.1 audit pré-build (2026-05-03)

**Périmètre** : Modification `Organisation.consentement_dataconnect_global` ou `Organisation.consentement_grdf_global` doit cascade vers tous DeliveryPoints élec/gaz de l'Org (avec court-circuit `gestionnaire_reseau != GRDF` pour ADICT).

**Pourquoi reporté** : Touche modules Bill Intelligence + DataConnect connector (Phase 4 connector live = stub `sync()` returns []). Cascade nécessite intégration avec consent lifecycle automatisé (Sprint C-3).

**Action** :
- Ajouter entrées CASCADE_MAP[Organisation.consentement_*]
- Wiring avec DataConnect token revocation/rotation
- Audit RGPD : trace cascade dans audit_log_service

**Effort estimé** : 4-6 h
**Priorité** : 🟠 P1 (cascade RGPD critique)
**Sprint cible** : Sprint C-3 (Sources + traçabilité, contexte consents)

---

## ~~D-Phase6-Cascade-DeliveryPoint-Fta-001~~ — ✅ CLÔTURÉ 2026-05-04 (pivoté DP.grd_code) — Cascade DeliveryPoint.code_fta → profil + Bill Intelligence

**Pivot Phase 3.6 audit** : `DeliveryPoint.code_fta` n'existe pas (audit pré-build a confirmé que le FTA est sur `PowerContract.fta_code`, modèle distinct). Pivot vers `DeliveryPoint.grd_code` (champ existant, ENEDIS/GRDF/ELD_*/RTE) qui est plus pertinent pour la cascade ELD ref.

**Clôture** : Sprint C-3 Phase 3.6 (commit à venir)
- Cascade `DeliveryPoint.grd_code` → `_recompute_eld_metadata_from_grd_code` + `_trigger_bill_recheck`
- Référentiel YAML 21 ELD (GRDF + 20 ELD locales) + `eld_gaz_loader.py`
- 24 tests : 12 loader + 7 cascade + 5 source-guards structure

**Cascade `PowerContract.fta_code`** : reportée Sprint C-4 sous nouvelle dette `D-Phase3-6-Cascade-PowerContract-FTA-001`.

**Original** :

**Détecté** : Sprint C-1 Phase 6.1 audit pré-build (2026-05-03)

**Périmètre** : Modification `DeliveryPoint.code_fta` doit cascade vers :
- `profil_tarifaire` (mapping FTA → BT_RESIDENTIEL / BT_PROFESSIONNEL / etc.)
- Bill Intelligence A6 recheck (cohérence Σ conso compteurs ↔ Σ conso contrats, tolérance 1%)

**Pourquoi reporté** : Touche module Bill Intelligence (A6 1% tolérance) — pas encore implémenté Sprint C-1.

**Action** :
- Mapping FTA TURPE 7 → profil tarifaire (15 valeurs FTA)
- Endpoint `/api/billing/recheck-coherence/{site_id}`
- Tests intégration bill engine

**Effort estimé** : 3-4 h
**Priorité** : 🟡 P2 (Bill Intelligence module Sprint C-3)
**Sprint cible** : Sprint C-3 (Sources + traçabilité)

---

## ~~D-Phase6-Cascade-Contract-Renewal-001~~ — ✅ CLÔTURÉ MVP 2026-05-04 — Cascade Contract.date_fin_validite → alerte 90j

**Détecté** : Sprint C-1 Phase 6.1 audit pré-build (2026-05-03)
**Clôturé MVP** : Sprint C-2 Phase 5.3 (2026-05-04, commit Phase 5.3)

**Périmètre original** : Modification `Contract.date_fin_validite` doit cascade vers création alerte 90j dans Centre d'action.

**Pivot Phase 5.1** : `Contract.date_fin_validite` n'existe pas (champ canonique = `EnergyContract.end_date`). Cascade pivotée sans changement sémantique.

**Solution MVP livrée Phase 5.3 (Cas B — modèle Alert absent)** :
- Migration Alembic mineure 2e78ecc6040c (6e épisode discipline anti-DROP) :
  `EnergyContract.alerte_renouvellement_logged_at: DateTime nullable`
- 2 helpers cascade_recompute_service.py :
  - `_trigger_renewal_alert(contract, db)` — log structuré "RENEWAL_ALERT_90D" + flag set
  - `_reset_renewal_alert_flag(contract, db)` — reset flag à None
- 1 entrée `CASCADE_MAP_MVP_SPRINT_C1["EnergyContract.end_date"]` (2 actions ordonnées : reset PUIS trigger)
- Idempotence anti-spam : log skipped si dernier log <30j (`_RENEWAL_ALERT_REPLAY_COOLDOWN_DAYS`)
- Fenêtre 90j stricte : `_RENEWAL_ALERT_WINDOW_DAYS = 90`
- 10 tests verts (fenêtre + idempotence + reset flag + extension/raccourcissement contrat)

**Reste à faire — version Premium Sprint C-5** :
- Modèle `Alert` générique (type, deadline, priorité, action_url, recipient)
- Endpoint `/api/alerts` CRUD + dispatch UI Centre d'action
- Notif email via outbox (cf. ADR Postgres+TimescaleDB+outbox HMAC)
- Migration logs MVP → records Alert dédiés

**Effort réel MVP** : ~1.5 h (vs 4-6 h estimé Premium)
**Priorité** : 🟡 P2 (MVP couvre besoin opérationnel ; Premium polish UI Sprint C-5)
**Sprint cible MVP** : Sprint C-2 ✅ — **Sprint C-5 pour version Premium**

**Traces** :
- Phase 5.1 audit (2026-05-04) : décision Cas B
- Phase 5.3 commit : implémentation MVP + tests + migration

---

## D-Phase1-Audit-Log-Legacy-Callsites-001 — 7-9 callsites legacy AuditLog directs

**Détecté** : Sprint C-2 Phase 1.1 audit pré-build (2026-05-03)

**Périmètre** : N callsites legacy créent des AuditLog directement (pas via audit_log_service.py).

**Fichiers concernés** :
- `middleware/cx_logger.py:252` (CX events — refactor lourd, garder)
- `services/intake_service.py:485` (Intake — refactor moyen)
- `services/operat_export_service.py:270` (OPERAT export — refactor faisable)
- `services/copilot_engine.py:443, 494` (Copilot — refactor moyen)
- `services/iam_service.py:504` (IAM — refactor faisable)
- (potentiellement) `routes/patrimoine/sites.py:508, 554` (si non migrés Phase 1.2)

**Action** : refactor progressif vers `audit_log_service.log_*()` méthodes appropriées.

**Allowlist active** : `backend/tests/source_guards/test_audit_log_no_direct_writes_source_guards.py::_LEGACY_CALLSITES_GRANDFATHERED`

**Effort estimé** : 30 min × 7 fichiers ≈ 3-4 h cumulés
**Priorité** : 🟡 P2 (fonctionnel, cohérence cosmétique)
**Sprint cible** : Sprint C-4 (Tests + observabilité, contexte cleanup audit)

---

## D-Sprint-C2-Conftest-Reseed-Reset-001 — `conftest._ensure_seeded` reset alembic_version pendant tests

**Détecté** : Sprint C-2 Phase 1.2 anomalie mid-flight (2026-05-03)

**Symptôme** : DB locale revenue à un revision Alembic antérieur (`2f83c6bebc57`) après run de tests, alors que HEAD migration attendu était `c8f1246522f9` (Phase 3 Sprint C-1). Probablement `conftest.py::_ensure_seeded` autouse module-scoped qui reset la DB pendant les tests Phase 4-6 Sprint C-1.

**Impact** : avant chaque `alembic revision --autogenerate`, il faut `alembic stamp head` pour aligner DB sur HEAD migration. Sinon autogenerate produit du diff erroné (re-création colonnes déjà présentes, dépendances cassées, ou drops non-désirés sur tables Enedis legacy).

**Workaround actuel** : `alembic stamp head` avant chaque autogenerate (côté dev manuel).

**Action durable** :
- Investiguer `conftest._ensure_seeded` scope et logique reset
- Restreindre scope (function-level uniquement, pas module-level autouse)
- OU isolation DB de test vs DB dev (fixture pytest dédiée tmp_path)
- OU stamper automatiquement post-reset dans `_ensure_seeded`

**Effort estimé** : 1-2 h
**Priorité** : 🟡 P2 (workaround connu, pas bloquant mais friction récurrente)
**Sprint cible** : Sprint C-4 (Tests + observabilité, contexte qualité tests)

**Traces** :
- Sprint C-1 Phase 3 (test_site_migration_alembic.py) : approche statique AST adoptée à cause de ce comportement
- Sprint C-2 Phase 1.2 : `alembic stamp head` exécuté manuellement avant `alembic revision --autogenerate`

---

## D-Phase1-4-Batiment-SDP-Proxy-001 — Modèle Batiment minimal (6/23 champs matrice v1 §4.5)

**Détecté** : Sprint C-2 Phase 1.4 (2026-05-03)

**Périmètre** : Modèle `Batiment` actuel = 6 champs (`id`, `site_id`, `nom`, `surface_m2`, `annee_construction`, `cvc_power_kw`). Matrice v1 §4.5 cible 23 champs incluant : `surface_de_plancher_sdp_m2`, `categorie_operat_batiment`, `rnb_id`, `dpe_*`, `efa_id`, `etage_count`, `parties_communes_pct`, etc.

**Workarounds actuels** :
- `is_site_production_ready` Check 3 : utilise `Batiment.surface_m2` comme proxy SDP
- `is_site_production_ready` Check 3 : fallback `Site.operat_sous_categorie_id` au lieu de `Batiment.categorie_operat_batiment`
- `OperatValeursAbsoluesService.compute_cabs_2030` Phase 4 : même fallback pattern
- `cascade_recompute_service._recompute_cabs` Phase 6 : utilise `Site.tertiaire_area_m2` ou `Site.surface_m2` au lieu d'une agrégation Bâtiment

**Action** : enrichir modèle Batiment avec les 17 champs manquants (RNB ID, DPE classes, EFA ID, parties communes, etage_count, etc.). Migration Alembic dédiée + Pydantic schemas Bâtiment + tests.

**Effort estimé** : 4-6 j-h (migration Alembic + Pydantic schemas + service + tests)
**Priorité** : 🟡 P2 (workarounds fonctionnels, pas bloquant)
**Sprint cible** : Sprint C-6 (Modèles enrichis + EFA — déjà planifié plan Phase B)

**Traces** :
- Site_readiness_service Phase 1.4 : check 3 documente l'adaptation
- Operat_cabs_service Phase 4 : `compute_cabs_2030` n'agrège pas multi-bâtiments
- Compute_cabs Phase 6 : utilise sous-cat unique site

---

## ~~D-Phase4-3-Portfolio-Intensity-Backend-001~~ — ✅ CLÔTURÉ 2026-05-04 — Agrégat portfolio kWh/m² calculé côté FE

**Clôture** : Sprint C-3 Phase 3.4 (commit 85b6502c)
- backend/services/portfolio_intensity_service.py — formule canonique Σ kWh / Σ surface
- backend/routes/portfolio_intensity.py — GET /api/portfolio/intensity org-scopé
- 9 tests (4 unit MagicMock + 5 integration TestClient) verts

**Original** :

**Détecté** : Sprint C-2 Phase 4.3 (2026-05-04)

**Périmètre** : `frontend/src/pages/Patrimoine.jsx:822-831` (KpiStripItem global "Consommation"). Le sub-label `"X kWh/m² moy."` est calculé côté FE par `Σ(annual_kwh) / Σ(surface)` (moyenne pondérée). Reste un calcul FE sur des données pré-agrégées car la moyenne arithmétique des `site.intensity_kwh_m2_total` (moyenne des ratios) ≠ ratio des sommes (intensité globale réelle du portfolio).

**Justification scope-out Phase 4.3** :
- L1525-1531 (ligne par site) reste l'anti-pattern principal cible R7 audit Phase B → corrigé Phase 4.3 par lecture directe `site.intensity_kwh_m2_total`.
- L825-830 (agrégat portfolio) est une agrégation de données déjà côté FE (somme conso, somme surface). Pas un calcul métier sur 1 entité.
- Décision Option D pragmatique : préserver le scope Phase 4.3 sans recréer endpoint backend agrégé.

**Risque résiduel** :
- Doctrine PROMEOS "zero business logic frontend" légèrement violée pour 1 sub-label.
- Si `surface` ou `annual_kwh` filtrage scope inconsistant entre BE/FE → divergence d'affichage possible.
- Sentinelle facile à grep : `Math.round(.*conso_kwh.*\/.*surface)` dans Patrimoine.jsx.

**Action Sprint C-3** :
1. Créer endpoint `GET /api/portfolio/intensity?scope=...` agrégé côté backend (somme conso / somme surface, avec filtres scope EJ/Portefeuille/Site cohérents avec `_get_org_id`).
2. Exposer 2 valeurs : `intensity_kwh_m2_total_portfolio`, `intensity_kwh_m2_tertiaire_portfolio`.
3. FE consomme via hook (cohérent avec `useElecCo2Factor` Phase 4.4 pattern).
4. Retirer la moyenne pondérée FE Patrimoine.jsx L827-828.
5. Ajouter source-guard FE (no `Math.round.*conso.*\/.*surface`).

**Effort estimé** : ~1 j-h (endpoint backend + hook FE + remplacement Patrimoine.jsx + tests)
**Priorité** : 🟡 P2 (workaround fonctionnel, divergence affichage faible probabilité, pas bloquant)
**Sprint cible** : Sprint C-3 (TraceTooltip + sources canoniques agrégés)

**Traces** :
- Patrimoine.jsx:822-831 commentaire inline référence cette dette
- Phase 4.3 commit (atomic) trace la décision Option D

---

## D-Phase4-2-Operat-Surfaces-3-Distinct-001 — Distinguer SDP / tertiaire_area_m2 / S_CE OPERAT

**Détecté** : Sprint C-2 Phase 4 audit regulatory-expert (2026-05-04)

**Source légale** : Arrêté 10/04/2020 art. 2-j (NOR LOGL2005904A, version 15/03/2024) — « *La surface de consommations énergétiques [S_CE], la surface sur laquelle l'ensemble des consommations énergétiques sont prises en compte, **intégrant notamment les surfaces de stationnement intérieur et de locaux techniques** de l'entité fonctionnelle, **au contraire de la surface de plancher** [SDP]* ».

**Périmètre** : Phase 4.2 a ajouté `Site.intensity_kwh_m2_tertiaire = annual_kwh_total / tertiaire_area_m2`. Or `tertiaire_area_m2` est commenté "Surface tertiaire assujettie (m2)" — sémantique floue. Réglementairement il faut distinguer 3 surfaces :
- **SDP** (Surface De Plancher) — code construction, exclut parking + locaux techniques
- **tertiaire_area_m2** — part assujettie OPERAT (≥ 1 000 m² cumulés EFA, R.174-22 CCH)
- **S_CE** — surface OPERAT pour reporting kWh/m², INCLUT parking intérieur + locaux techniques (typiquement > SDP)

**Risque** : `intensity_kwh_m2_tertiaire` actuellement calculé sur surface assujettie peut **diverger** de l'intensité officielle OPERAT calculée sur S_CE → risque de non-conformité reporting si exposé comme métrique réglementaire (ex: Cockpit RegOps, exports DT).

**Action Sprint C-3 / C-6** :
1. Ajouter colonne `Site.surface_consommations_energetiques_m2` (S_CE) distincte
2. Ajouter colonne `Site.surface_de_plancher_sdp_m2` (cf. dette D-Phase1-4-Batiment-SDP-Proxy-001)
3. Renommer ou documenter `intensity_kwh_m2_tertiaire` comme intensité **assujettie** (pas OPERAT officielle)
4. Source-guard : interdire l'export OPERAT depuis `intensity_kwh_m2_tertiaire` tant que `surface_consommations_energetiques_m2` n'est pas peuplé

**Effort estimé** : ~2-3 j-h (3 colonnes + migration + source-guard + tests + documentation)
**Priorité** : 🟠 **P0** (risque non-conformité reporting OPERAT si exposé en l'état)
**Sprint cible** : Sprint C-6 (Modèles enrichis matrice §4.5) — corrélé à D-Phase1-4-Batiment-SDP-Proxy-001

**Traces** :
- Audit regulatory-expert Phase 4 (2026-05-04) finding D1
- Légifrance arrêté 10/04/2020 art. 2-j

---

## D-Phase4-2-Operat-Intensity-DJU-Adjustment-001 — intensity_kwh_m2_tertiaire non ajusté DJU

**Détecté** : Sprint C-2 Phase 4 audit regulatory-expert (2026-05-04)

**Source légale** : Arrêté 10/04/2020 art. 5 + Annexe II ATDL2430864A (Coeff DJU par groupe).

**Périmètre** : `intensity_kwh_m2_tertiaire` est exposé brut (annual_kwh_total / tertiaire_area_m2) sans ajustement DJU. Pour comparaison à `Cabs` ou `Crelat` (cibles OPERAT 2030), l'arrêté 10/04/2020 art. 5 impose un ajustement par Coeff DJU annuel (rapport DJU année / DJU référence).

**Risque** : si le ratio `intensity_kwh_m2_tertiaire / cabs_kwh_m2_an` est utilisé comme "% progression DT" affiché à l'utilisateur sans ajustement, l'écart peut être faussé de ±15 % selon climatologie annuelle.

**Action Sprint C-3 / C-4** :
1. Ajouter `Site.intensity_kwh_m2_tertiaire_dju_adjusted` (intensité après normalisation Coeff DJU)
2. Calculer via `regops/services/operat_dju_service.py` (réutiliser annexe II Coeff DJU)
3. Documenter inline tooltip "Intensité brute non ajustée DJU" sur Cockpit / RegOps display

**Effort estimé** : ~1-2 j-h (service + colonne + cascade trigger sur DJU update)
**Priorité** : 🟡 P1 (proxy fonctionnel, écart ±15% acceptable MVP)
**Sprint cible** : Sprint C-4 (Compliance V3 ajustements climatiques)

**Traces** :
- Audit regulatory-expert Phase 4 (2026-05-04) finding D2
- Légifrance arrêté 10/04/2020 art. 5

---

## ~~D-Phase4-2-EnergieFinale-Source-Guard-001~~ — ✅ CLÔTURÉ 2026-05-04 — annual_kwh_total doit être kWhEF PCI

**Clôture** : Sprint C-3 Phase 3.4 (commit 85b6502c) + audit follow-up Phase 3.4d
- backend/tests/source_guards/test_annual_kwh_total_kwhef_pci_source_guards.py
- SG_KWHEF_01 : allowlist writers Site.annual_kwh_total
- SG_KWHEF_02 : commentaire "kWhEF PCI" requis dans chaque writer
- Phase 3.4d : regex étendue couvre `setattr()` (false negative corrigé)

**Original** :

**Détecté** : Sprint C-2 Phase 4 audit regulatory-expert (2026-05-04)

**Source légale** : Arrêté 10/04/2020 art. 2-g — « *L'énergie finale, l'énergie délivrée au consommateur final.* » Reporting OPERAT exclusivement en kWhEF PCI.

**Périmètre** : Aucun source-guard backend ne vérifie que `Site.annual_kwh_total` agrège uniquement des kWh **énergie finale PCI**. Si à terme un service ingère du kWhEP (énergie primaire, conversion x2.3 réseau de chaleur) ou du kWh PCS (PCI×1.11 gaz), le calcul `intensity_kwh_m2_*` devient non-conforme OPERAT.

**Action Sprint C-3** :
1. Source-guard `backend/tests/source_guards/annual_kwh_energie_finale_source_guards.py` qui scanne les services écrivant `Site.annual_kwh_total` et exige un commentaire "EF PCI" ou usage d'un helper canonique `to_kwh_ef_pci()`.
2. Documenter dans `consumption_unified_service.py` (SoT consommation) que la valeur retournée est kWhEF PCI.

**Effort estimé** : ~30 min (1 source-guard + 1 docstring)
**Priorité** : 🟡 P1 (préventif, pas de fuite EF/EP/PCS détectée actuellement)
**Sprint cible** : Sprint C-3 (TraceTooltip + sources canoniques)

**Traces** :
- Audit regulatory-expert Phase 4 (2026-05-04) finding D3
- Légifrance arrêté 10/04/2020 art. 2-g

---

## D-ObligationsTab-Heuristics-Inline-001 — estHvacKw / estParkingM2 hardcodés FE (pré-existant)

**Détecté** : Sprint C-2 Phase 4 audit code-reviewer (2026-05-04, code pré-existant 03/2026)

**Périmètre** : `frontend/src/pages/conformite-tabs/ObligationsTab.jsx:159-163` :
```js
const estHvacKw = Math.round(maxSurface * 0.1);     // HVAC = 10% surface
const estParkingM2 = largeSites[0].surface_m2 * 0.6; // parking = 60% du plus grand site
```

Constantes heuristiques métier (10%, 60%) hardcodées dans un composant FE — violation doctrine PROMEOS "zero business logic frontend". Transmis ensuite à `/api/kb/apply` comme contexte site.

**Action Sprint C-4 / C-5** :
1. Endpoint backend `GET /api/kb/site-context-defaults?site_id=X` retournant `{ hvac_kw_estimate, parking_m2_estimate }` calculés via heuristiques BE (config YAML).
2. Retirer les 2 calculs inline ObligationsTab.jsx.
3. Source-guard FE : pas de `Math.round.*surface_m2 \* 0\.\d` dans `pages/`.

**Effort estimé** : ~2-3 h (endpoint + config YAML + retrait inline + source-guard)
**Priorité** : 🟡 P1 (impact = précision moindre KB context si scope FE diverge backend)
**Sprint cible** : Sprint C-4 (consolidation contexte KB)

**Traces** :
- Audit code-reviewer Phase 4 (2026-05-04) finding P1 (1)
- Code introduit en mars 2026 par le précédent contributeur (hors scope Phase 4 audit pour fix immédiat)

---

## D-V92-Split-Stale-Imports-Audit-001 — Tests post-split V92 avec imports stale

**Détecté** : Mini-sprint sécurité IDOR (2026-05-04, commits 40ebb348 + 0ec2743a)

**Périmètre** : Le split V92 (`routes/patrimoine.py` éclaté en `routes/patrimoine/sites.py + autres`) avait laissé 2 tests pointant sur `routes/patrimoine.py` (fichier vide depuis le split). Détectés et corrigés mid-flight mini-sprint IDOR :
- `test_step25_meter_unified.py::TestSourceGuard` (2 assertions)
- `test_step26_sub_meters.py::TestSourceGuards` (2 assertions)

Tous lisaient le fichier vide → `'<pattern>' in ''` retournait False → tests verts par accident OU rouges silencieusement.

**Risque résiduel** : possibilité d'autres tests scope V92 avec imports stale (silencieusement cassés ou trompeurs). Audit complémentaire nécessaire.

**Action Sprint C-4** :
1. `grep -rn "routes/patrimoine\.py\b" backend/tests/` — trouver toutes les références au fichier post-split
2. Vérifier chaque référence : si fichier vide, patcher vers le sous-fichier correct (`routes/patrimoine/sites.py`, `routes/patrimoine/_helpers.py`, `routes/patrimoine/staging.py`, etc.)
3. Source-guard préventif : interdire `_read("routes/patrimoine.py")` (fichier vide) dans tests

**Effort estimé** : 30-60 min (audit balayage + patches + source-guard préventif)
**Priorité** : 🟡 P2 (pas bloquant, polish qualité tests)
**Sprint cible** : Sprint C-4 (Tests + observabilité)

**Traces** :
- Mini-sprint IDOR commit `40ebb348` (Closes #275)
- 2 tests adaptés directement Sprint C-2.5 (extension scope acceptable)

---

## D-Compteur-Vs-Meter-Coexistence-001 — 2 modèles meter coexistent (Compteur legacy + Meter moderne)

**Détecté** : Mini-sprint sécurité IDOR (2026-05-04, audit pré-build helper)

**Périmètre** : Le repo a 2 modèles parallèles pour représenter un compteur :

| Modèle | Fichier | Usage actuel | Helper org-scoping |
|---|---|---|---|
| **Compteur** (legacy) | `models/compteur.py` | Routes legacy (older endpoints) | `_load_compteur_with_org_check` |
| **Meter** (moderne) | `models/energy_models.py` | Routes modernes + `meter_unified_service` | `_load_meter_with_org_check` (Mini-sprint IDOR) |

Pattern actuel : parallèle propre, pas de conflit. Le `meter_unified_service` (existant) est censé abstraire les 2 modèles (`Meter` source primaire, `Compteur` fallback legacy).

**Question architecturale** :
- **Option A — Unification vers Meter** : migrer toutes les routes/services Compteur → Meter, drop modèle legacy. Gain : 1 SoT, 1 helper. Coût : 4-6 j-h migration data + tests + impacts éventuels (`patrimoine_service.py`, anciens tests).
- **Option B — Maintien parallèle avec doctrine claire** : documenter qui utilise Meter (Cockpit, breakdown, sub-meters) vs Compteur (legacy patrimoine_crud, anciens flux import). Gain : zéro migration. Coût : 2 helpers + ambiguïté future.

**Action Sprint C-6/C-7** :
1. Audit usage : `grep -rn "from models.compteur import\|Compteur\b" backend/services backend/routes` — inventaire callsites
2. ADR archi pour arbitrer A vs B (délégation `architect-helios`)
3. Si Option A : roadmap migration progressive (Compteur deprecated → Meter unique)
4. Si Option B : ADR + section dans `helios_architecture` skill documentant la frontière

**Effort estimé** :
- Décision archi (Option A vs B) : ~1 j-h (audit + ADR)
- Si Option A retenue : +4-6 j-h migration + tests
- Si Option B retenue : +0.5 j-h documentation

**Priorité** : 🟡 P2 (pas bloquant, décision architecturale différée)
**Sprint cible** : Sprint C-6 (Modèles enrichis) ou Sprint C-7 (polish + ADR)

**Traces** :
- Mini-sprint IDOR audit pré-build (2026-05-04) : helper distinct créé pour `Meter` (le modèle legacy `Compteur` n'était pas concerné par l'IDOR meters endpoints)
- `meter_unified_service.py:21` documente la cohabitation : *"Source primaire : Meter. Fallback : Compteur legacy"*

---

## D-Phase3-6-Cascade-PowerContract-FTA-001 — Cascade PowerContract.fta_code → profil tarifaire

**Détecté** : Sprint C-3 Phase 3.6 audit pré-build (2026-05-04, audit pivot)

**Périmètre** : La dette originale `D-Phase6-Cascade-DeliveryPoint-Fta-001` ciblait `DeliveryPoint.code_fta`. Audit pré-build Phase 3.6 a confirmé que le champ FTA n'existe pas sur `DeliveryPoint` mais sur `PowerContract.fta_code` (modèle distinct, FTA TURPE 7 — 18 valeurs définies dans `models/power.py::FTA_SEGMENTS`).

**Action Sprint C-4** :
- Ajouter cascade `PowerContract.fta_code` dans `CASCADE_MAP_MVP_SPRINT_C1`
- Helper : `_derive_profile_from_fta(power_contract, db)` mapping 18 FTA → profil tarifaire (BTSUPCU4 → "BT_PRO_SUP_36KVA_CU", HTACU5 → "HTA_INDUSTRIEL_CU", etc.)
- Trigger Bill Intelligence recheck (cohérent avec Phase 3.6)
- Tests : 6-8 cascade FTA + résilience

**Effort estimé** : ~1.5-2 j-h (mapping 18 FTA + helper + tests)
**Priorité** : 🟡 P2 (extension utile mais Phase 3.6 a déjà couvert le cas dominant via DP.grd_code)
**Sprint cible** : Sprint C-4 (consolidation cascade + Bill Intelligence)

**Traces** :
- Audit pré-build Phase 3.6 (2026-05-04) : pivot DP.code_fta → DP.grd_code
- `models/power.py::FTA_SEGMENTS` (18 valeurs TURPE 7 + historiques)

---

## Métriques tracker

| Date | Nb dettes ouvertes | Nb dettes P0 | Nb dettes P1 | Nb dettes P2 |
|---|---|---|---|---|
| 2026-05-03 | 11 | 0 | 4 | 7 |
| 2026-05-03 | 12 | 0 | 4 | 8 |
| 2026-05-03 | 13 | 0 | 4 | 9 |
| 2026-05-03 | 14 | 0 | 4 | 10 |
| 2026-05-04 | 15 | 0 | 4 | 11 |
| 2026-05-04 | 19 | 1 | 7 | 11 |
| 2026-05-04 (Phase 5 clôtures Sprint C-2) | 16 | 1 | 5 | 10 |
| 2026-05-04 (post mini-sprint IDOR + 2 dettes) | 18 | 1 | 5 | 12 |
| 2026-05-04 (Sprint C-3 Phase 3.4 — 2 clôtures) | 16 | 1 | 4 | 11 |
| 2026-05-04 (Sprint C-3 Phase 3.4d audit follow-up — +5 dettes) | 21 | 2 | 6 | 13 |
| 2026-05-04 (Sprint C-3 Phase 3.6 — 1 clôture pivotée + 1 nouvelle PowerContract) | 21 | 2 | 6 | 13 |

---

## D-Sprint-C3-Portfolio-Consumption-OrgScope-001 — `/api/portfolio/consumption/*` sans org-scoping (PRÉ-EXISTANT)

**Détecté** : Sprint C-3 Phase 3.4d audit security-auditor (2026-05-04)

**Périmètre** : `backend/routes/portfolio.py:251` (GET /api/portfolio/consumption/summary) et L366 (GET /api/portfolio/consumption/sites). Filtre `Site.actif == True` SANS join `EntiteJuridique.organisation_id == org_id`. Tout utilisateur authentifié (même cross-org) peut voir les KPIs agrégés et top-sites de TOUTES les organisations.

**Code pré-existant** (hors range Sprint C-3 commits cd87bf36^..85b6502c). Détection bonus audit follow-up.

**Action Sprint C-4** :
1. Ajouter `_get_org_id` + join `EntiteJuridique.organisation_id == org_id` dans la query principale L251 et L366
2. Pattern à reproduire : `_build_sites_query` dans `routes/patrimoine/_helpers.py`
3. Tests cross-org → 403/404 (un par endpoint)

**Effort estimé** : 1-2 j-h
**Priorité** : 🔴 **P0** (CWE-284, sécurité, équivalent IDOR meters CWE-639 fixé mini-sprint 2026-05-04)
**Sprint cible** : Sprint C-4 (priorité absolue avant pilote)

**Traces** :
- Audit security-auditor Phase 3.4d (PROMEOS-SEC-2026-001 + 002)
- Symétrique au pattern fixé sur endpoints meters (commit 0ec2743a)

---

## D-Sprint-C3-YAML-Constants-SG-Coverage-001 — Source-guard cohérence YAML↔constants couvre 10/68 termes

**Détecté** : Sprint C-3 Phase 3.4d audit code-reviewer (2026-05-04)

**Périmètre** : `backend/tests/source_guards/test_regulatory_sources_yaml_consistency_with_constants_source_guards.py` couvre actuellement 10 termes (CO2 ×2, DT penalty ×3, audit_sme ×1, DT milestones ×3, EP coef ×2). Sur les 68 termes du YAML, **58 ne sont pas croisés** avec les constantes Python runtime.

**Risque** : drift silencieux si LFI 2027 (ou autre) modifie un taux côté YAML mais oublie côté Python (ou inversement).

**Termes prioritaires à ajouter** :
- ACCISE_ELEC_T1/T2/GAZ (3 termes — accises ↔ doctrine.constants.py)
- PRICE_FALLBACK / PRICE_FLEX_NEBCO / PRICE_ELEC_ETI_2026 (3 termes prix marché)
- NEBCO_THRESHOLD_KW_PER_STEP (1 terme RTE)
- FLEX_HEURISTIC_EUR_PER_SITE_PER_YEAR (1 terme heuristique)
- APER_PENALTY_EUR_PER_M2_PER_YEAR (1 terme APER)
- REGOPS_WEIGHT_* / READINESS_WEIGHT_* (6 termes pondérations doctrine)

**Effort estimé** : ~30 min (étendre les patterns SG_REG_CONST_* avec ~12 nouvelles assertions)
**Priorité** : 🟡 P1 (anti-drift réglementaire, traçabilité audit légal)
**Sprint cible** : Sprint C-4 (consolidation source-guards)

---

## D-Sprint-C3-Reg-Manquants-Capacite-CBAM-VNU-001 — 9 termes réglementaires manquants YAML

**Détecté** : Sprint C-3 Phase 3.4d audit regulatory-expert (2026-05-04)

**Périmètre** : Le YAML 68 termes (Phase 3.2) couvre les domaines coeur (DT, BACS, APER, audit SMÉ, OPERAT, CO2, accises, TVA, TURPE 6/7 partiel). **9 mécanismes réglementaires importants ABSENTS** :

| ID | Mécanisme | Échéance critique | Priorité |
|---|---|---|---|
| 1 | **Capacité RTE 1/11/2026** | Échéance critique 6 mois | 🔴 P0 |
| 2 | ATRD7 gaz (T1/T2/T3/T4/TP) + ATRT8 | Avant pilote gaz | 🟠 P1 |
| 3 | TURPE 7 C4/C3 horosaisonnier (couverture C5 BT seule actuellement) | Pilote 2026 | 🟠 P1 |
| 4 | CBAM règlement UE 2023/956 (déclaration trimestrielle) | 2026 trimestriel | 🟠 P1 |
| 5 | VNU post-ARENH (loi 2025) | 2026 | 🟠 P1 |
| 6 | TRVE résidentiel + TRV gaz repère | Continu | 🟡 P2 |
| 7 | CEE période P6 (2026-2030) — coefficients fiches BAT | 2026-2030 | 🟡 P2 |
| 8 | ETS2 (UE 2023/959) — bâtiments tertiaires 2027 | 2027 | 🟡 P2 |
| 9 | TDN + CPB | Continu | 🟡 P2 |

**Action Sprint C-4** : ajouter les 9 mécanismes au YAML + helpers typés + 9 tests loader.

**Effort estimé** : ~2-3 j-h (structuration YAML + helpers + tests)
**Priorité** : 🔴 **P0 pour Capacité RTE** (échéance 1/11/2026, fenêtre 6 mois) + 🟠 P1 pour ATRD/CBAM/VNU
**Sprint cible** : Sprint C-4 (priorité Capacité RTE) + Sprint C-5 (CBAM/VNU/CEE)

**Traces** :
- Audit regulatory-expert Phase 3.4d findings
- agent_veille_reglementaire.md (17 mécanismes canoniques — base liste complète)

---

## D-Sprint-C3-CRE-CTA-URLs-Verifier-001 — URLs CTA 2026 deep-link à vérifier

**Détecté** : Sprint C-3 Phase 3.4d audit regulatory-expert (2026-05-04)

**Périmètre** : `sources_reglementaires.yaml` lignes 245-268 (CTA_ELEC_DISTRIBUTION_PCT + CTA_ELEC_TRANSPORT_PCT). URL deep-link CRE délibération 2026-14 a été reconstruite Phase 3.4d (`https://www.cre.fr/documents/Deliberations/Decision/deliberation-2026-14-cta-distribution`) mais **non vérifiée** sur cre.fr en live (URL plausible mais pas confirmée disponible).

**Action Sprint C-4** : vérifier les 2 URLs CRE 2026-14 sont bien accessibles + corriger si différentes du pattern reconstruit.

**Effort estimé** : 15 min (vérification live + maj YAML)
**Priorité** : 🟡 P2 (URLs plausibles fonctionnent encore via redirection cre.fr/, mais audit légal préfère deep-link confirmé)
**Sprint cible** : Sprint C-4 ou opportunistique

---

## D-Sprint-C3-CO2-GNL-JORFTEXT-Verifier-001 — JORFTEXT GNL à reconfirmer

**Détecté** : Sprint C-3 Phase 3.4d audit regulatory-expert (2026-05-04)

**Périmètre** : `sources_reglementaires.yaml` ligne 53-64 (CO2_FACTOR_GNL_KGCO2_PER_KWH). Le JORFTEXT initialement utilisé (`JORFTEXT000051956481`) entrait en collision avec le JORFTEXT de la Loi 2025-391 audit SMÉ (lignes 613-642). **Phase 3.4d a corrigé** : `legal_reference: null` + URL fallback recherche Légifrance + note explicite.

**Action Sprint C-4** : retrouver le JORFTEXT correct de l'arrêté 01/08/2025 GNL sur Légifrance + restaurer `legal_reference` + URL deep-link.

**Effort estimé** : 10 min (recherche Légifrance + maj YAML)
**Priorité** : 🟡 P2 (la valeur 0.238 reste correcte ADEME ; seul le JORFTEXT de référence est temporairement incomplet)
**Sprint cible** : Sprint C-4

---

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
