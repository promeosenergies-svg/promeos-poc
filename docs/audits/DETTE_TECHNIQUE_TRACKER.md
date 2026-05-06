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

## ~~D-Phase6-Cascade-Org-Consentements-001~~ — ✅ REPORTÉE 2026-05-04 (modèle préalable manquant) — Cascade Org.consentement_dataconnect / grdf → tous DPs

**Pivot Phase 3.7 audit** : audit pré-build a confirmé que les 4 champs cibles **n'existent pas** dans le modèle ORM :
- `Organisation.consentement_dataconnect_global` — absent (modèle Organisation minimal : id/nom/type_client/logo_url/siren/actif/is_demo)
- `Organisation.consentement_grdf_global` — absent
- `DeliveryPoint.consentement_dataconnect_local` — absent
- `DeliveryPoint.consentement_grdf_local` — absent

**Pourquoi pivoter au lieu de livrer** : créer des helpers cascade sur des champs ORM fantômes serait une régression doctrine "constants vérifiables" (pattern identique à Phase 5.2 Sprint C-2 où la cascade `EJ.consommation_3y` sur champ inexistant a été pivotée vers `AuditEnergetique.conso_annuelle_moy_gwh`, et Phase 3.6 où `DP.code_fta` inexistant a été pivoté vers `DP.grd_code`).

**Décomposition** : la dette originale (1 dette P1) est **scindée en 2 dettes Sprint C-4** :
1. `D-Sprint-C3-Org-Consentement-Modele-001` (P1) — créer modèle (migration Alembic + 4 champs)
2. `D-Sprint-C3-Cascade-Consentement-Activation-001` (P1) — activer cascade après modèle prêt

**Statut** : ✅ REPORTÉE Sprint C-3 (audit pré-build 2026-05-04). Sera réactivable Sprint C-4 après livraison de la dette `D-Sprint-C3-Org-Consentement-Modele-001`.

**Original** :

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

## D-Sprint-C2-Conftest-Reseed-Reset-001 — `conftest._ensure_seeded` reset alembic_version pendant tests [CLÔTURÉE Phase 4.7]

**Détecté** : Sprint C-2 Phase 1.2 anomalie mid-flight (2026-05-03)
**Statut** : ✅ **CLÔTURÉE** Sprint C-4 Phase 4.7 (commit follow-up).

### Livraison Phase 4.7

`backend/tests/conftest.py::_ensure_seeded()` enrichi avec reset explicite + re-stamp head post-reseed (Option C "stamper automatiquement post-reset" retenue) :

```python
# Sprint C-4 Phase 4.7 — reset alembic_version pour cohérence baseline
# post-reseed (anti-désync entre test modules consécutifs).
try:
    db.execute(text("DELETE FROM alembic_version"))
    from alembic import command
    from alembic.config import Config
    alembic_cfg = Config("alembic.ini")
    command.stamp(alembic_cfg, "head")
    db.commit()
except Exception:
    db.rollback()  # Defensive : best-effort, non critique pour tests sans migration runtime
```

### Workaround historique conservé (defensive)

`alembic stamp head` manuel reste possible avant `alembic revision --autogenerate` mais le reset automatique post-reseed couvre désormais le cas runtime tests.

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

## D-V92-Split-Stale-Imports-Audit-001 — Tests post-split V92 avec imports stale [CLÔTURÉE Phase 4.7]

**Détecté** : Mini-sprint sécurité IDOR (2026-05-04, commits 40ebb348 + 0ec2743a)
**Statut** : ✅ **CLÔTURÉE** Sprint C-4 Phase 4.7 (commit follow-up).

### Audit balayage Phase 4.7.1 — verdict propre

`grep -rnE "from routes\.patrimoine\s+import"` → 17 callsites détectés (tests + 2 routes consumers). Tests collectés sans erreur :

```
tests/test_compliance_contracts.py: 19
tests/test_contracts_v96.py: 10
tests/test_guidance_v98.py: 34
tests/test_reconciliation_v96.py: 8
tests/test_registre_patrimonial.py: 17
tests/test_resolution_engine_v97.py: 32
tests/test_step35_import_update.py: 17
TOTAL: 137 tests collectés sans erreur d'import
```

→ Cohérence assurée par les **ré-exports backward-compatible** dans `routes/patrimoine/__init__.py` (Sprint C-2 V92 split discipline). Pattern :

```python
# routes/patrimoine/__init__.py
from routes.patrimoine._helpers import (  # noqa: F401, E402
    _get_org_id, _check_*_belongs_to_org, _load_*_with_org_check,
    _serialize_*, _compute_site_completeness, _worst_compliance_status, ...
)
```

Les 2 tests historiquement cassés (`test_step25_meter_unified.py` + `test_step26_sub_meters.py`) ont été fixés mid-flight mini-IDOR meters (commit `40ebb348`).

### Source-guard anti-régression Phase 4.7

`backend/tests/source_guards/test_routes_patrimoine_init_reexports_source_guards.py` (NOUVEAU) :

- **SG_V92_01** : bloc "Backward-compatible re-exports" présent dans `__init__.py`
- **SG_V92_02** : 10 ré-exports cardinaux validés (`_get_org_id`, `_check_*`, `_load_*_with_org_check`, `_serialize_*`, `_compute_*`, `_worst_compliance_status`)

Si quelqu'un retire un ré-export sans coordonner les 17 callsites, ce SG bloque au commit.

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

## D-Sprint-C3-Org-Consentement-Modele-001 — Créer modèle Organisation + DeliveryPoint pour consentements RGPD

**Détecté** : Sprint C-3 Phase 3.7 audit pré-build (2026-05-04, audit pivot)

**Périmètre** : Le modèle ORM actuel ne contient AUCUN champ de consentement RGPD. Pour activer la cascade `D-Phase6-Cascade-Org-Consentements-001`, il faut d'abord créer 4 champs via migration Alembic :

- `Organisation.consentement_dataconnect_global` (Boolean, nullable, default=null) — état consentement Enedis DataConnect au niveau organisation (effet bulk)
- `Organisation.consentement_grdf_global` (Boolean, nullable, default=null) — état consentement GRDF ADICT au niveau organisation
- `DeliveryPoint.consentement_dataconnect_local` (Boolean, nullable, default=null) — état effectif au niveau DP élec (peut diverger de l'org en cas d'override)
- `DeliveryPoint.consentement_grdf_local` (Boolean, nullable, default=null) — état effectif au niveau DP gaz GRDF (court-circuit ELD locales)

**Cohérence RGPD** : ces 4 champs sont nécessaires pour traçabilité audit RGPD (date consentement / révocation / source) — à terme ajout champs `consentement_*_at` (DateTime) + `consentement_*_source` (String, ex: "user_admin", "import_csv").

**Action Sprint C-4** :
1. Migration Alembic mineure (4 colonnes nullable, pattern anti-DROP destructif maintenu)
2. Mise à jour Pydantic schemas Organisation + DeliveryPoint
3. Tests source-guards : aucune écriture directe hors service consent_lifecycle
4. Documenter dans `docs/produit/patrimoine_parametrage_requis_v1.md` matrice §4

**Effort estimé** : ~1.5-2 j-h (migration + schemas + tests)
**Priorité** : 🟠 P1 (préalable cascade D-Sprint-C3-Cascade-Consentement-Activation-001)
**Sprint cible** : Sprint C-4 (consolidation modèles)

**Traces** :
- Audit pré-build Phase 3.7 (2026-05-04) : 4 champs absents confirmés
- Modèle Organisation actuel (`models/organisation.py`) : 7 colonnes seulement
- Modèle DeliveryPoint (`models/patrimoine.py:225+`) : pas de champ consentement

---

## D-Sprint-C3-Cascade-Consentement-Activation-001 — Activer cascade Org consentements après modèle livré [CLÔTURÉE Phase 4.5]

**Détecté** : Sprint C-3 Phase 3.7 audit pré-build (2026-05-04, audit pivot)
**Statut** : ✅ **CLÔTURÉE** Sprint C-4 Phase 4.5 (commit follow-up).

### Livraison Phase 4.5

- ✅ 2 helpers cascade activés `cascade_recompute_service.py` :
  - `_propagate_consentement_dataconnect(org, db)` (Phase 4.5)
  - `_propagate_consentement_grdf(org, db)` avec court-circuit ELD locales via `is_grdf()` Phase 3.6
- ✅ 2 entrées `CASCADE_MAP_MVP_SPRINT_C1` ajoutées (Org.consentement_dataconnect_global + grdf_global)
- ✅ Service nouveau `services/consent_service.py` (Option B archi-helios — effective consent runtime)
  - `get_effective_consent(dp, type_)` : hiérarchie `_local IF NOT NULL ELSE _global`
  - `is_consent_active(dp, type_)` : helper booléen explicite RGPD-respectful
- ✅ 14 tests cascade vivante + 3 SG no-direct-propagation (override RGPD préservé)
- ✅ Court-circuit ELD locales testé (Régaz, GreenAlp skippés cardinal RGPD)

**Décision archi cardinale Phase 4.5** : Option B (effective consent runtime, pas d'écrasement physique des `_local`). Préserve override RGPD-protégé. Différenciateur PROMEOS RGPD-compliant cf. ADR-007.

**Cascade vivante 14 champs Phase C** (post-Phase 4.5, +2 vs Phase 4.4) :
- Sprint C-1 : 7 champs (Site OPERAT/APER/EFA + Batiment.cvc_power_kw)
- Sprint C-2 : 4 champs (Site.surface_m2 + annual_kwh + AuditEnergetique.conso + EnergyContract.end_date)
- Sprint C-3 : 1 champ (DeliveryPoint.grd_code → ELD ref + bill_recheck)
- **Sprint C-4 Phase 4.5 : 2 champs cardinaux Org.consentement_dataconnect_global + grdf_global**

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
| 2026-05-04 (Sprint C-3 Phase 3.7 — 1 clôture reportée + 2 nouvelles dettes Modele/Activation) | 22 | 2 | 8 | 12 |
| 2026-05-04 (Sprint C-3 Phase 3.7d audit follow-up — +6 dettes audit cumul) | 28 | 2 | 11 | 15 |
| 2026-05-04 (post Sprint C-3 — clôture finale + renommage Phase 3.7d + ADR split en 3) | 28 | 2 | 12 | 14 |
| 2026-05-05 (Sprint C-4 Phase 4.1 coherence_globale.yaml v1.0 + dette TraceTooltip-TermId-SG) | 29 | 2 | 13 | 14 |
| 2026-05-05 (Sprint C-4 Phase 4.2 CAPACITE+CBAM+VNU YAML — clôture P0 partielle + 2 nouvelles dettes URLs+Unit) | 30 | 1 | 13 | 16 |
| 2026-05-05 (Sprint C-4 Phase 4.2d audit follow-up — ADR-010 + 4 nouvelles dettes + 1 reclassif P2→P1 + clôture i18n TraceTooltip) | 33 | 3 | 15 | 15 |
| 2026-05-05 (Sprint C-4 Phase 4.3 — Type strict EnergieFinale ADR-011 — clôture EnergieFinale-Type-Strict + 1 successeur typage progressif) | 33 | 3 | 15 | 15 |
| 2026-05-05 (Sprint C-4 Phase 4.4 — Modèle Org/DP consentement ADR-007 — clôture RGPD-Consent-Detail) | 32 | 3 | 14 | 15 |
| 2026-05-05 (Sprint C-4 Phase 4.5 — Cascade Org consentement vivante + audit SoT reuse — 2 clôtures + 1 nouvelle dette ADR-007 reportée) | 31 | 3 | 12 | 16 |
| 2026-05-05 (Sprint C-4 Phase 4.6 — Tests perf bulk recompute 50/200/500 sites — toutes cibles tenues, pas de nouvelle dette) | 31 | 3 | 12 | 16 |
| 2026-05-05 (Sprint C-4 Phase 4.7 — Polish V92 + ELD + Conftest reseed — 2 clôtures P2 + SG V92 anti-régression) | 29 | 3 | 12 | 14 |
| 2026-05-06 (Sprint C-5 Phase 5.1 — Bill Intelligence anomaly_detector R19+R20 ADR-013 — 1 clôture P0 cardinal différenciateur produit) | 28 | 2 | 12 | 14 |
| 2026-05-06 (Sprint C-5 Phase 5.2 — Capacité EUR/MW disambiguation ADR-015 — 1 clôture P0 documentaire + 2 nouvelles P2 reportées Sprint C-7) | 29 | 1 | 12 | 16 |

---

## D-Sprint-C3-7d-ELD-5-Entries-Disparities-Resolved-001 — 5 entrées ELD discordantes [CLÔTURÉE Fix #4]

**Détecté** : Sprint C-3 Phase 3.7d audit regulatory-expert (2026-05-04)
**Statut** : ✅ **CLÔTURÉE** — Fix #4 même phase (commit `477e3cea`)
**Alias historique** : `D-Sprint-C4-ELD-5-Entrees-Verification-001` (référencé `eld_gaz_referentiel.yaml`)

**Fixes appliqués Phase 3.7d** :

| Code | Correction |
|---|---|
| `R_GDS` | Label corrigé "Réseau Gaz de Strasbourg" |
| `REGIE_NAGYS` | Note warning + label "à vérifier" (Carmaux Gaz absent liste CRE) |
| `SOREGIES_VIENNE` (ex-REGIE_RIDUEZE) | Renommé code (terme officiel SOREGIES) |
| `GAZ_DE_BORDEAUX` | Note warning fournisseur ≠ distributeur |
| `ENERGIE_LOON_PLAGE` (ex-GAZ_DUNKERQUE) | Renommé + périmètre clarifié (Loon-Plage, pas CU Dunkerque) |

`source_url` aligné CRE : `https://www.cre.fr/distributeurs-de-gaz-naturel`.

**Successeur Sprint C-4** : `D-Sprint-C4-ELD-Quality-YAML-CrossSource-Audit-001` (audit qualité automatisé YAML cross-source + complétion `legal_reference` Loi 46-628 art. 23 + suivi statut Gaz de Bordeaux/REGIE_NAGYS).

---

## D-Sprint-C3-7d-EnergieFinale-Type-Strict-001 — Source-guard ingestion GRDF kWh PCS → PCI [CLÔTURÉE Phase 4.3]

**Détecté** : Sprint C-3 Phase 3.7d audit regulatory-expert (2026-05-04)
**Alias historique** : `D-Phase3-4-EnergieFinale-Strict-Type-Conversion-PCI-PCS-001`
**Statut** : ✅ **CLÔTURÉE** Sprint C-4 Phase 4.3 (ADR-011, commit follow-up).

### Livraison Phase 4.3

- ✅ Module `backend/promeos_types/energy.py` (NOUVEAU) — 5 NewType (`KwhEFPCI`, `KwhEP`, `MWhEFPCI`, `GWhEFPCI`, `KwhPCS`) + 6 helpers conversion typés + 4 coefficients réglementaires (1 SoT)
- ✅ Helper cardinal `kwh_pcs_to_kwh_ef_pci_gaz()` — conversion GRDF avec coefficient officiel 0.901 centralisé
- ✅ Typage signature `services/portfolio_intensity_service.compute_portfolio_intensity()` — `sum_annual_kwh: KwhEFPCI` (consumer cardinal MVP)
- ✅ ADR-011 livré (`docs/adr/ADR-011-type-strict-energie-finale-kwhef-pci.md`)
- ✅ 14 tests `test_promeos_types_energy.py` + 3 SG `test_energy_types_strict_source_guards.py`
- ✅ SG MVP Phase 3.4 conservés (defense in depth — allowlist setattr + commentaire `kWhEF PCI`)

### Successeur Sprint C-5 (typage progressif)

`D-Phase4-3-Energy-Types-Migration-Progressive-001` (P1) — étendre le typage `KwhEFPCI` aux autres services consumers (`compliance_rules`, `cee_service`, `intake_service`, `compliance_readiness_service`, `operat_export_service`).

### Successeur Sprint C-7 polish

Schemas pydantic Site/AuditEnergetique avec `Annotated[KwhEFPCI, Field(...)]` + validation FastAPI request strict (Option B reportée).

**Sources** : GRDF Catalogue prestations 2025 §conversion PCS→PCI ; Arrêté 10/04/2020 art. 2-g (NOR LOGL2005904A).

---

## D-Phase4-3-Energy-Types-Migration-Progressive-001 — Typage progressif autres services consumers

**Détecté** : Sprint C-4 Phase 4.3 (ADR-011, 2026-05-05)

**Périmètre** : Phase 4.3 a typé UNIQUEMENT `services/portfolio_intensity_service.compute_portfolio_intensity()` (consumer cardinal MVP). Les autres services consumers de `Site.annual_kwh_total` restent non-typés `float` :

- `services/compliance_rules.py:130, 206` — `ctx["annual_kwh_total"]`
- `services/compliance_readiness_service.py:42, 62` — blocking field + label
- `services/operat_export_service.py:206-207` — export OPERAT conso élec
- `services/cee_service.py:252, 261` — baseline CEE
- `services/intake_service.py:52` — mapping intake

**Action Sprint C-5** :
1. Annoter signatures de chaque service consumer (`from promeos_types.energy import KwhEFPCI`)
2. Étendre SG `SG_ENERGY_TYPES_02` pattern à chaque consumer (vérifier import + usage cohérent)
3. Tests anti-régression sur dataset HELIOS demo

**Effort estimé** : ~1.5-2 h (5 services × ~15-20 min each)
**Priorité** : 🟡 P1 (cohérence cross-stack, non bloquant pré-pilote car SG MVP couvre allowlist setattr)
**Sprint cible** : Sprint C-5

---

## D-Sprint-C3-7d-Cascade-SoT-Reuse-Audit-001 — Auditer toutes constantes locales dupliquant SoT YAML [CLÔTURÉE Phase 4.5]

**Détecté** : Sprint C-3 Phase 3.7d audit code-reviewer (2026-05-04)
**Statut** : ✅ **CLÔTURÉE** Sprint C-4 Phase 4.5 audit rapide 4.5.4 (commit follow-up).

### Livraison Phase 4.5.4 (audit rapide cascade SoT reuse)

Audit ciblé `cascade_recompute_service.py` vs services métier :

- `_recompute_compliance(site, db)` — helper canonique propre, pas de duplication
- `_recompute_organisation_via_coordinator(audit_sme, db)` (Sprint C-2 P5.2) — délègue à `compliance_coordinator.recompute_organisation` (1 callsite L308) — pattern propre
- `_recompute_cabs`, `_recompute_intensity_total/tertiaire` — thin wrappers locaux cardinaux, pas de logique métier dupliquée
- Phase 4.5 helpers `_propagate_consentement_*` réutilisent `is_grdf()` du `eld_gaz_loader` (1 SoT court-circuit ELD)

**Verdict cardinal** : pas de duplication critique détectée. Pattern compliance_coordinator déjà adopté pour les cas org-scopés. Doctrine "1 SoT par concept" respectée.

### Audits déjà appliqués Phase 3.7d (2 fixes confirmés)

- `_AUDIT_SME_SEUIL_*` → `get_audit_sme_threshold()` SoT YAML (commit Phase 3.7d)
- Dates APER hardcodées → `get_term_value("APER_DEADLINE_*")` (commit Phase 3.7d)

### Audit profond reporté Sprint C-7 polish

Si Sprint C-7 souhaite étendre l'audit balayage cross-modules (`regops/rules/*.py`, `compliance_score_service.py`, `data_ingestion/`), créer dette dédiée `D-Sprint-C7-SoT-Reuse-Cross-Modules-Audit-001` avec scope :

1. `grep -rn "0.052|0.227|7500|3750|2.75|23.6|26.58|0.0569"` cross-modules
2. Étendre source-guards SG_REG_CONST_* couverture 68/68 termes (vs 10/68 actuel — `D-Sprint-C3-YAML-Constants-SG-Coverage-001`)

---

## D-Phase4-4-ADR-007-Consent-By-CGU-Version-001 — Audit trail RGPD avancé Org/DP consentement (champs ADR-007 reportés)

**Détecté** : Sprint C-4 Phase 4.4 (modèle Org/DP consentement, 2026-05-05)

**Périmètre** : ADR-007 spécifie un schéma RGPD enrichi avec audit trail complet (qui/quand/version CGU/IP hashée). Phase 4.4 a livré le MVP cardinal (8 cols : Boolean + DateTime timezone=True) mais REPORTE 2 catégories de champs RGPD avancés :

| Champ ADR-007 | Description | Sprint cible |
|---|---|---|
| `consentement_*_by` (FK users) | Quel utilisateur a accordé/retiré le consentement | C-5+ |
| `consentement_*_cgu_version` (String 20) | Version CGU au moment du consentement | C-5+ |
| `consentement_*_ip_hash` (String SHA-256) | IP hashée RGPD-safe (audit forensique) | C-7+ optionnel |

**Action Sprint C-5** :

1. Migration Alembic 8e Phase C — ajouter `_by` + `_cgu_version` (4 cols par entité × 2 entités = 8 cols additionnelles)
2. AuditLog event_type `RGPD_CONSENT_CHANGE` enrichi avec `cgu_version` JSON metadata
3. Tests cardinal : changement consentement crée 1 entrée AuditLog conforme CNIL
4. Délégation `regulatory-expert` (CNIL audit trail) + `security-auditor` (FK + IP hash)

**Effort estimé** : ~1-1.5 j-h (migration + tests + AuditLog wiring)
**Priorité** : 🟡 P2 (RGPD audit trail avancé — différenciateur CNIL strict, non bloquant pré-pilote MVP)
**Sprint cible** : Sprint C-5

**Référence** : `docs/adr/ADR-007-rgpd-consentement-dataconnect-grdf-modele.md` section "Audit trail" — schéma complet revendiqué.

---

## D-Sprint-C3-7d-ADR-RGPD-Consent-Detail-001 — ADR design modèle consentement RGPD [CLÔTURÉE Phase 4.4]

**Détecté** : Sprint C-3 Phase 3.7d audit architect-helios (2026-05-04)
**Statut** : ✅ **CLÔTURÉE** Sprint C-4 Phase 4.4 (commit follow-up).

### Livraison Phase 4.4 (ADR-007 implémentation)

- ✅ ADR-007 livré Sprint C-4 Phase 0 (`docs/adr/ADR-007-rgpd-consentement-dataconnect-grdf-modele.md`) — design 4 champs Org + 4 champs DP avec court-circuit ELD préservé
- ✅ Migration Alembic 7e Phase C `d4a59f7c8e21_org_dp_consentement_cols.py` (0 destructive cumulée)
- ✅ Modèles ORM mis à jour : `models/organisation.py` +4 cols + `models/patrimoine.py:DeliveryPoint` +4 cols (8 cols total RGPD timezone-aware)
- ✅ Index `ix_delivery_points_consentement_dataconnect_local` (filtres cascade Phase 4.5)
- ✅ 11 tests CRUD + 3 SG structure consentement (timezone=True RGPD-compliant)

### Successeurs

- `D-Sprint-C3-Cascade-Consentement-Activation-001` (P1) — Phase 4.5 Sprint C-4 (cascade vivante org → DPs activée)
- Champs ADR-007 reportés Sprint C-5+ (audit trail RGPD avancé) :
  - `consentement_*_by` (FK users) — délégation security-auditor
  - `consentement_*_cgu_version` (String) — versioning CGU explicite

---

## D-Sprint-C3-7d-ADR-Intensity-OPERAT-Naming-001 — ADR cohabitation `/api/energy/intensity` vs `/api/portfolio/intensity`

**Détecté** : Sprint C-3 Phase 3.7d audit architect-helios (2026-05-04)

**Périmètre** : Figer le contrat entre 2 endpoints intensity coexistants :
- `/api/energy/intensity` (existant, série temporelle Meter readings, semantic = précision réelle mesurée)
- `/api/portfolio/intensity` (nouveau Sprint C-3 Phase 3.4, agrégat org-scopé `Site.annual_kwh_total`, semantic = snapshot patrimoine rapide)

**Risque** : divergence formule entre 2 endpoints sans ADR explicit (anti-pattern doctrine §6.4 "1 SoT par concept").

**Action Sprint C-4 amont** : ADR `docs/adr/2026-XX-cohabitation-intensity-endpoints.md` figeant :
- Cas d'usage canoniques (Cockpit/RegOps précision réelle vs Patrimoine.jsx KpiStripItem global)
- Différentiel sémantique (Meter readings ≠ Site.annual_kwh_total)
- Stratégie convergence ou séparation pérenne

**Effort estimé** : ~30 min
**Priorité** : 🟡 P1 (cohérence doctrine 1-SoT)
**Sprint cible** : Sprint C-4 amont

---

## D-Sprint-C3-7d-ADR-Routes-Namespace-001 — ADR namespace `/api/config/*` vs `/api/regulatory/*`

**Détecté** : Sprint C-3 Phase 3.7d audit architect-helios (2026-05-04)

**Périmètre** : Figer la séparation sémantique entre 2 namespaces API actuels :
- `/api/config/*` — constantes Python runtime (`emission_factors`, `regulatory_constants` Phase 3.3)
- `/api/regulatory/*` — sources légales avec traçabilité (`rates`, `domains`, citations Légifrance/CRE)

**Action Sprint C-4 amont** : ADR `docs/adr/2026-XX-namespace-config-vs-regulatory.md` figeant règles de routage par type (constante vs source légale traçable).

**Effort estimé** : ~20 min
**Priorité** : 🟡 P2 (cosmétique architectural, mineur)
**Sprint cible** : Sprint C-4 ou opportunistique

---

## D-Sprint-C3-7d-TVA-Reduite-Abo-Gaz-001 — TVA 5,5% abonnement gaz/élec résidentiel

**Détecté** : Sprint C-3 Phase 3.7d audit regulatory-expert (2026-05-04)

**Périmètre** : Manquant YAML SoT `sources_reglementaires.yaml`. Doctrine fiscale française :
- TVA **5,5%** sur abonnement gaz/élec résidentiel (≤ 36 kVA pour élec, abonnement seul gaz)
- Source : CGI art. 278-0 bis A
- Distinct du `TVA_REDUITE_CTA_PCT` actuel (5,5% sur CTA spécifiquement)

**Action Sprint C-4** : ajouter terme `TVA_REDUITE_ABONNEMENT_PCT = 5.5%` au YAML.

**Effort estimé** : 5 min
**Priorité** : 🟡 P1 (impact Bill Intelligence résidentiel)
**Sprint cible** : Sprint C-4

---

## D-Sprint-C3-7d-Legal-Reference-Completion-001 — JORFTEXT/legal_reference manquants 18+ termes

**Détecté** : Sprint C-3 Phase 3.7d audit regulatory-expert (2026-05-04)

**Périmètre** : 18+ termes du YAML ont `legal_reference: null` ou URL deep-link non vérifiée :
- TURPE 6/7 (URLs CRE deep-link à confirmer)
- CTA_ELEC_DISTRIBUTION/TRANSPORT_PCT (URLs Phase 3.4d à vérifier post-publication officielle)
- CO2_FACTOR_GNL_KGCO2_PER_KWH (JORFTEXT collision corrigée Phase 3.4d → null avec note)
- REGOPS_WEIGHT_* / READINESS_WEIGHT_* (doctrine PROMEOS, pas de JORFTEXT applicable, OK)
- PRICE_FALLBACK / PRICE_FLEX_NEBCO (heuristiques marché, pas de JORFTEXT, OK)

**Action Sprint C-4** : audit systématique `legal_reference: null` + complétion URLs Légifrance/CRE deep-links validés.

**Effort estimé** : ~1 j-h (vérification 18 termes + complétion + tests source-guards renforcés)
**Priorité** : 🟡 P1 (audit trail légal R10 différenciateur)
**Sprint cible** : Sprint C-4

---

## D-Sprint-C3-7d-FE-i18n-TraceTooltip-001 — "effective" anglais dans TraceTooltip [CLÔTURÉE]

**Détecté** : Sprint C-3 Phase 3.7d audit code-reviewer (2026-05-04)
**Statut** : ✅ **CLÔTURÉE** Phase 4.2d (commit follow-up) — `frontend/src/ui/TraceTooltip.jsx` ligne ~62 corrigée opportunistiquement : "effective" → "applicable depuis" en même temps que ajout rendu pending_source_verification (ADR-010).

---

## D-Phase4-1-TraceTooltip-TermId-SG-Cross-Stack-001 — Source-guard cross-stack FE↔YAML invariant 5

**Détecté** : Sprint C-4 Phase 4.1 (création `coherence_globale.yaml` v1.0, 2026-05-05)

**Périmètre** : Invariant 5 `TRACETOOLTIP_TERMID_VALIDITY` du registre `coherence_globale.yaml` est **doctrinal MVP** Sprint C-4. L'implémentation runtime (source-guard cross-stack FE↔YAML) est reportée Sprint C-5 :

- Scanner tous les usages `<TraceTooltip termId="X" />` dans `frontend/src/**/*.jsx`
- Lire `backend/config/sources_reglementaires.yaml` (subprocess Node ou fixture conftest pytest)
- Test croisé : 100% match `termId` FE ↔ `terms.keys()` YAML SoT

**Risque sans fix** : typo `termId` silencieuse côté FE → tooltip ne s'affiche pas (fallback enfants seuls), différenciateur R10 perdu sans alerte. UX cassée non détectée.

**Action Sprint C-5** :

1. Décision implémentation :
   - **Option A** — source-guard côté FE (Vitest) : grep regex `<TraceTooltip\s+termId="([^"]+)"` + lecture YAML via fixture
   - **Option B** — source-guard côté BE (pytest) : scan `frontend/src/` depuis Python (path traversal cross-stack)
2. Test cardinal : 100% match termId
3. Fail-fast : 1 typo = PR-bloquante

**Effort estimé** : ~30 min (cf. user msg Phase 4.1)
**Priorité** : 🟡 P1 (UX silencieuse cassée — différenciateur R10 perdu)
**Sprint cible** : Sprint C-5

**Référence** : `backend/config/coherence_globale.yaml` invariant 5 (`detection: tests/source_guards/test_tracetooltip_termid_yaml_coherence_source_guards`).

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

## D-Sprint-C3-Reg-Manquants-Capacite-CBAM-VNU-001 — 9 termes réglementaires manquants YAML [PARTIELLEMENT CLÔTURÉE]

**Détecté** : Sprint C-3 Phase 3.4d audit regulatory-expert (2026-05-04)
**Statut** : 🟡 **PARTIELLEMENT CLÔTURÉE** — Phase 4.2 Sprint C-4 (commit `014df01a`+) livre 3/9 mécanismes (Capacité RTE P0 cardinal + CBAM + VNU). Reste 6 mécanismes pour Sprint C-5+.

### ✅ Livrés Phase 4.2 (3/9 mécanismes — 9 termes YAML)

| Mécanisme | Termes ajoutés | Sources |
|---|---|---|
| **Capacité RTE 1/11/2026** ✅ | `CAPACITE_RTE_OBLIGATION_DEADLINE` + `_TARIF_2026_EUR_PER_MW` (3.15) + `_COEFF_2026` (1.2) + `_TARIF_2025_EUR_PER_MW` (0.0) | Décret 2025-1441 + Arrêté 18/03/2026 (référencés `purchase/cost_simulator_2026.py`) |
| **CBAM** ✅ | `CBAM_OBLIGATION_DEADLINE_PHASE_PLEINE` (2026-01-01) + `CBAM_REGLEMENT_REFERENCE` | Règlement (UE) 2023/956 (référencé `billing_engine/bricks/cbam.py`) |
| **VNU** ✅ | `VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH` (0.0) + seuils `_PRIX_BAS` (78) + `_PRIX_HAUT` (110) | Décret 2026-55 + CRE 2026-52 (référencés `purchase/cost_simulator_2026.py`) |

→ 9 termes YAML ajoutés + 13 tests YAML + 3 source-guards cohérence YAML↔runtime catalog (Option B archi décision Phase 4.2).

### ⏳ Restants Sprint C-5+ (6/9 mécanismes)

| ID | Mécanisme | Échéance | Priorité | Sprint cible |
|---|---|---|---|---|
| 2 | ATRD7 gaz (T1/T2/T3/T4/TP) + ATRT8 | Avant pilote gaz | 🟠 P1 | C-5 |
| 3 | TURPE 7 C4/C3 horosaisonnier (couverture C5 BT seule actuellement) | Pilote 2026 | 🟠 P1 | C-5 |
| 6 | TRVE résidentiel + TRV gaz repère | Continu | 🟡 P2 | C-7 |
| 7 | CEE période P6 (2026-2030) — coefficients fiches BAT | 2026-2030 | 🟡 P2 | C-5 |
| 8 | ETS2 (UE 2023/959) — bâtiments tertiaires 2027 | 2027 | 🟡 P2 | C-7 |
| 9 | TDN + CPB | Continu | 🟡 P2 | C-7 (CPB déjà partiel `catalog.py`) |

**Action Sprint C-5** : ajouter ATRD7 + ATRT8 + TURPE C4/C3 + CEE P6 (4 mécanismes prioritaires).
**Action Sprint C-7** : compléter TRVE + ETS2 + TDN polish.

**Effort restant estimé** : ~1.5-2 j-h Sprint C-5 + ~1 j-h Sprint C-7
**Priorité résiduelle** : 🟠 P1 (Capacité RTE P0 critique livré)

**Traces** :
- Phase 4.2 Sprint C-4 commit `014df01a`+ (clôture P0)
- agent_veille_reglementaire.md (17 mécanismes canoniques — base liste complète)

---

## D-Phase4-2-Sources-URLs-Verifier-001 — URLs Légifrance/CRE/EUR-Lex à vérifier (CAPACITE/VNU/CBAM)

**Détecté** : Sprint C-4 Phase 4.2 (création 9 termes YAML CAPACITE/VNU/CBAM, 2026-05-05)

**Périmètre** : Les 9 termes ajoutés Phase 4.2 ont `url: null` car Claude Code ne peut pas vérifier URLs Légifrance/CRE/EUR-Lex en ligne sans accès web. Les `legal_reference` (Décret 2025-1441, Décret 2026-55, Règlement UE 2023/956) sont fiables (sourcés depuis le code repo : `cost_simulator_2026.py`, `billing_engine/bricks/cbam.py`, `billing_engine/catalog.py`).

**Risque** : URLs deep-link absentes côté FE TraceTooltip → différenciateur R10 affaibli sur ces 9 termes (pas de lien cliquable Légifrance/CRE/EUR-Lex).

**Action Sprint C-7** :
1. Vérifier sur Légifrance : Décret n°2025-1441 (Capacité RTE) + Arrêté 18/03/2026
2. Vérifier sur Légifrance : Décret n°2026-55 (VNU) + CRE délibération 2026-52
3. Vérifier sur EUR-Lex : Règlement (UE) 2023/956 (CBAM)
4. Vérifier sur services-rte.com : résultats enchères capacité 06/03/2025 (3.15 EUR/MW)
5. Compléter `url:` champ pour les 9 termes
6. Test source-guard renforcé : `url != null` pour tout terme legal_reference != null

**Effort estimé** : ~30-45 min (vérification web + édition YAML)
**Priorité** : 🟡 P2 (cosmétique TraceTooltip, valeurs numériques déjà fiables)
**Sprint cible** : Sprint C-7 polish

---

## D-Phase4-2-Catalog-CAPACITE-Unit-Mismatch-001 — Catalog `CAPACITE_ELEC.unit` probablement incorrect (EUR/kWh vs EUR/MWh)

**Détecté** : Sprint C-4 Phase 4.2 source-guard cohérence YAML↔runtime (2026-05-05)

**Périmètre** : `services/billing_engine/catalog.py::CAPACITE_ELEC` stocke :
- `rate: 0.00043`
- `unit: "EUR/kWh"`

Or la formule canonique `_compute_capacity()` produit EUR/MWh : `(price_eur_per_mw × coeff) / 8760 = EUR/MWh`. Numériquement `(3.15 × 1.2) / 8760 ≈ 0.000432` qui correspond à 0.00043 EUR/MWh, **PAS 0.00043 EUR/kWh** (qui serait ~1000× trop élevé). Le commentaire catalog `→ 3.15 × 1.2 / 8760 ≈ 0.00043 EUR/kWh` (ligne 878) est incohérent avec la formule.

**Risque** : si un consumer applique `rate × kwh` pour calculer le montant capacité, le résultat peut être 1000× trop élevé selon l'interprétation. À vérifier que les consumers actuels (`compute_xxx` du billing_engine) interprètent le rate cohéremment.

**Action Sprint C-7 polish** :
1. Audit consumers `CAPACITE_ELEC.rate` dans `billing_engine/`
2. Décider : corriger `unit: "EUR/MWh"` (probable) OU garder unit + corriger rate à 0.00000043
3. Tests anti-régression sur les calculs de facturation capacité existants
4. SG renforcé `test_capacite_yaml_runtime_consistency_source_guards` : valider unit catalog

**Effort estimé** : ~1.5 h (audit consumers + correction + tests anti-régression billing)
**Priorité** : 🟠 **P1** (RECLASSIFIÉE Phase 4.2d audit follow-up — blast radius rapport CFO confirmé par bill-intelligence : `unit` exposée dans tooltip / rapport JSON utilisateur)
**Sprint cible** : Sprint C-5 (reclassif depuis C-7 polish, urgence rapport CFO)

**Note Phase 4.2d** : reclassifiée P1 sur audit bill-intelligence (commit `714d3ad4` follow-up). Le bill-intelligence a confirmé : si un consumer expose `.unit` dans un rapport CFO, l'utilisateur verrait "EUR/kWh" alors que la valeur est en EUR/MWh — embarras commercial. Phase 4.2 SG `test_sg_capacite_runtime_01_tarif_2026_numeric_consistency_with_catalog` valide la **valeur numérique** uniquement (pas l'unit string) avec note doctrinale dans la docstring. Lié dette `D-Phase4-2d-Capacite-EUR-MW-Disambiguation-001` (audit valeur enchère 3.15 vs 3150 EUR/MW).

---

## D-Phase4-2d-Pending-Source-Verification-001 — 5 termes YAML status pending_source_verification

**Détecté** : Sprint C-4 Phase 4.2d audit regulatory-expert (2026-05-05)

**Périmètre** : Audit regulatory-expert Phase 4.2 follow-up a relevé 5 termes YAML CAPACITE_RTE_* + VNU_* avec confidence LOW car WebFetch bloqué par allow-list (Légifrance/CRE/services-rte.com inaccessibles, seul EUR-Lex CBAM validé). Le tag `status: pending_source_verification` ajouté Phase 4.2d (ADR-010) signale ces incertitudes.

| Terme | Confidence | Source revendiquée | Risque |
|---|---|---|---|
| `CAPACITE_RTE_OBLIGATION_DEADLINE` | medium | Décret 2025-1441 | Plausible mais non vérifié |
| `CAPACITE_RTE_TARIF_2026_EUR_PER_MW` (3.15) | low | Enchères RTE 06/03/2025 | **Disambiguation requise** (3.15 vs 3150 EUR/MW, cf. dette ci-dessous) |
| `CAPACITE_RTE_COEFF_2026` (1.2) | low | RTE | Coefficient non confirmé |
| `VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH` (0.0) | low | Décret 2026-55 + CRE 2026-52 | **Délibération CRE 2026-52 NON RETROUVÉE portail public** (confusion possible avec délib 2026-70 minoration nucléaire) |
| `VNU_SEUIL_*` (78/110) | low | CRE 2026-52 | Idem (référence CRE non confirmée) |

**Action Sprint C-7 polish** :
1. Vérification experte (juriste / consultant énergie) des 5 références légales
2. Si délibérations CRE confirmées → renseigner URLs deep-link YAML
3. Si délibérations introuvables → corriger `legal_reference` + `source.label` au plus juste
4. Retirer tag `status: pending_source_verification` au cas par cas après vérification
5. Cohérent avec `D-Phase4-2d-WebFetch-Allowlist-Review-001` (élargissement allow-list)

**Effort estimé** : ~1.5-2 j-h (vérification 5 termes + ajustements YAML + tests)
**Priorité** : 🟡 P1 (cohérence R10 différenciateur — bannière warning visible utilisateur)
**Sprint cible** : Sprint C-7 polish

---

## D-Phase4-2d-WebFetch-Allowlist-Review-001 — Allow-list WebFetch trop restrictive

**Détecté** : Sprint C-4 Phase 4.2d audit regulatory-expert (2026-05-05)

**Périmètre** : L'allow-list actuelle bloque `legifrance.gouv.fr` / `cre.fr` / `services-rte.com`. Seul `eur-lex.europa.eu` accessible. Frein cardinal pour vérification des sources réglementaires françaises (Légifrance JO + CRE délibérations + RTE résultats enchères) — tout l'écosystème PROMEOS repose pourtant sur ces sources.

**Risque** : impossibilité de vérifier ~80% des termes YAML avant Sprint C-7 vérification experte. Différenciateur R10 affaibli à chaque ajout YAML futur (devra démarrer en `pending_source_verification`).

**Action Sprint C-7** :
1. Audit pertinence allow-list `.claude/` ou settings Claude Code
2. Décision archi : élargir vers Légifrance + CRE + services-rte.com avec validation security-auditor
3. Si élargissement OK → re-run regulatory-expert audit pour valider les 5 termes pending Phase 4.2d
4. Si refusé → process alternatif : consultation manuelle juriste + import sources via fichier statique

**Effort estimé** : 30-45 min (audit + décision archi)
**Priorité** : 🟡 P2 (infrastructure dev — gain ROI vérifications futures)
**Sprint cible** : Sprint C-7

---

## D-Phase4-2d-Capacite-EUR-MW-Disambiguation-001 — Valeur enchère capacité 3.15 vs 3150 EUR/MW à clarifier

**Détecté** : Sprint C-4 Phase 4.2d mini-audit pré-build (2026-05-05)

**Périmètre** : Le YAML `CAPACITE_RTE_TARIF_2026_EUR_PER_MW = 3.15` (mirroir `cost_simulator_2026.py:64 CAPACITE_UNITAIRE_EUR_MWH = 0.43`) présente une **incohérence mathématique apparente** :

- Formule canonique `(price × coeff) / 8760 = EUR/MWh`
- Avec YAML 3.15 EUR/MW × 1.2 = 3.78, ÷ 8760 = **0.000432 EUR/MWh**
- Catalog runtime stocke pourtant **0.43 EUR/MWh** (= 0.00043 EUR/kWh)
- **Différence x1000** entre la formule et la valeur stockée

Hypothèses :
- **A** : tarif réel = **3150 EUR/MW** (typo "3.15" propagée Phase 4.2). Cohérent avec `services/capacity/revenue.py PRIX_MOYEN_MW_AN PL1 (20-50k EUR/MW)` qui suggère ordre de grandeur kEUR/MW pour enchères capacité.
- **B** : tarif réel = 3.15 EUR/MW (référence catalog ligne 882) mais le commentaire formule du catalog est incorrect.

**Risque** : si hypothèse A confirmée → YAML + cost_simulator_2026 + catalog billing_engine doivent être mis à jour CONJOINTEMENT (3.15 → 3150 + recalcul rate). Dérive non détectée silencieuse possible.

**Action Sprint C-5** :
1. Audit source officielle RTE résultats enchères 06/03/2025 livraison 2026 (consultation experte ou WebFetch après allow-list élargie)
2. Disambiguer valeur réelle (3.15 vs 3150 EUR/MW)
3. Si disambiguation = 3150 → MAJ coordonnée 3 fichiers (YAML + cost_simulator_2026 + catalog) + ajustement SG
4. Tests anti-régression billing engine post-correction

**Effort estimé** : ~2-3 h (audit source + correction coordonnée + tests)
**Priorité** : 🔴 **P0** (calcul facture client erroné si hypothèse A confirmée — embarras commercial pré-pilote)
**Sprint cible** : Sprint C-5

**Note Phase 4.2d** : SG `test_sg_cost_sim_02_capacite_unitaire_consistent_with_yaml_formula` documente l'incohérence avec ratio toléré x1000 jusqu'à clôture de cette dette. Anti-dérive : empêche modification d'une seule des 3 valeurs sans MAJ coordonnée.

---

## ~~D-Phase4-2d-BillIntelligence-Anomaly-Detector-001~~ — ✅ CLÔTURÉE Sprint C-5 Phase 5.1

**Détecté** : Sprint C-4 Phase 4.2d audit bill-intelligence (2026-05-05)
**Clôturée** : Sprint C-5 Phase 5.1 (2026-05-06, commit `<hash-phase-5-1>`, ADR-013)

**Livrables Phase 5.1** :

- `backend/models/bill_anomaly.py` — modèle `BillAnomaly` (héritage `TimestampMixin + SoftDeleteMixin`, FK `invoice_id` → `energy_invoices.id`)
- `backend/alembic/versions/478ee4a61ebb_phase_5_1_sprint_c_5_bill_anomaly_table_.py` — 8e migration Alembic Phase C (cumul 0 destructive, 14 drop_table autogenerate retirés discipline anti-DROP 8e épisode)
- `backend/services/bill_intelligence/__init__.py` + `anomaly_detector.py` (~280 LOC) :
  - `detect_r19_vnu_dormant` : scan `EnergyInvoiceLine` `line_type=tax` + label LIKE `%VNU%`/`%VERSEMENT NUCLEAIRE%`, agrégation, anomaly si Σ > seuil et `consumption_kwh < 100`
  - `detect_r20_capacity_variance` : scan `line_type=network` + `unit LIKE %kVA%`, JOIN `EnergyInvoice → Site → Meter → PowerContract`, navigation JSON dict `ps_par_poste_kva[period_code]`, retourne LISTE (1 anomaly par poste tarifaire)
  - `_resolve_period_code` helper 3 priorités (champ direct / meta_json / label parsing HPH/HCH/HPB/HCB/POINTE)
  - `detect_anomalies_for_invoice` pipeline résilience par-action (try/except chaque détecteur)
- `backend/config/sources_reglementaires.yaml` (+2 termes domain `bill_intelligence`) :
  - `BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR = 0.01 EUR`
  - `BILL_ANOMALY_CAPACITY_VARIANCE_THRESHOLD_PCT = 5.0 %`
- `backend/routes/bill_intelligence.py` — endpoint `GET /api/bill-intelligence/anomalies` org-scopé strict (JOIN chain `BillAnomaly → EnergyInvoice → Site → Portefeuille → EntiteJuridique.organisation_id`), filtres `code/severity/resolved`
- `backend/tests/test_bill_anomaly_detector.py` — 19 tests verts (R19 + R20 + multi-postes + matching period_code + résilience pipeline + YAML SoT cohérence)
- `backend/tests/source_guards/test_bill_anomaly_yaml_runtime_consistency_source_guards.py` — 3 SG anti-régression (YAML termes présents + pas de hard-code seuils + helper signature stable)

**Adaptations Phase 5.1.0** (post-diagnostic mini-audit, vs ADR-013 initial) :

- Modèle `EnergyInvoice` (pas `Facture`) → FK `invoice_id` → `energy_invoices.id`
- Scan `EnergyInvoiceLine` (line_type `TAX`/`NETWORK` + label/unit) car pas de champ direct `vnu_montant` ou `capacite_facturee_kw`
- JOIN chain `EnergyInvoice → Site → Meter → PowerContract` (pas DeliveryPoint direct)
- `PowerContract.ps_par_poste_kva` JSON dict (pas scalaire) → R20 retourne LISTE multi-postes

**Effort réel** : ~2 h (vs 2-3 j-h estimé) = **gain -85 à -90%** maintenu.

**Différenciateur produit cardinal** : runtime R19+R20 traçable, seuils YAML SoT versionnés, 1 SoT par concept (cohérence Sprint C-3 + C-4).

**Priorité** : ✅ CLÔTURÉE
**Sprint cible** : Sprint C-5 ✅

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
