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

## ~~D-Phase4-2-Operat-Surfaces-3-Distinct-001~~ — ✅ CLÔTURÉE Sprint C-7 Phase 7.1

**Détecté** : Sprint C-2 Phase 4 audit regulatory-expert (2026-05-04)
**Clôturée** : Sprint C-7 Phase 7.1 (2026-05-06, commit `<hash-phase-7-1>`, migration Alembic 11e `f5df8bc45f8b`)

**Source légale** : Arrêté 10/04/2020 art. 2-j (NOR LOGL2005904A, version 15/03/2024) — « *La surface de consommations énergétiques [S_CE], la surface sur laquelle l'ensemble des consommations énergétiques sont prises en compte, **intégrant notamment les surfaces de stationnement intérieur et de locaux techniques** de l'entité fonctionnelle, **au contraire de la surface de plancher** [SDP]* ».

**Livrables Phase 7.1** (~1 h vs 2-3 j-h estimé = gain -85%) :

- **Migration Alembic 11e propre** (`f5df8bc45f8b_phase_7_1_*.py`) — `Site.s_ce_m2 Float nullable` ajouté, anti-DROP discipline 11e épisode (63 drop_table autogenerate retirés)
- **`backend/models/site.py`** — col `s_ce_m2` ajoutée avec docstring cardinal référençant les 3 surfaces distinctes (SDP / tertiaire_area_m2 / S_CE)
- **Tests** : `tests/test_site_s_ce_m2_phase71.py` — 7 tests CRUD (default NULL + set + 3 surfaces distinct cardinal + précision décimale + optionnel + post-creation)
- **Source-guards** : `tests/source_guards/test_site_3_surfaces_structure_source_guards.py` — 3 SG (3 cols présentes + Float type + nullable)

**Scope MVP retenu** : 1 col ajoutée (`s_ce_m2`) — `surface_de_plancher_sdp_m2` reportée Sprint C-7+ (`D-Phase1-4-Batiment-SDP-Proxy-001`). `intensity_kwh_m2_tertiaire` reste calculé sur `tertiaire_area_m2` (assujettie) — pas de migration logique métier MVP, dette `D-Phase4-2-Operat-Intensity-DJU-Adjustment-001` couvre l'ajustement DJU pour métrique réglementaire OPERAT officielle.

**Cumul Phase C+ : 11 migrations propres / 0 destructive** (Phase 7.1 = 11e épisode anti-DROP).

**Priorité** : ✅ CLÔTURÉE
**Sprint cible** : Sprint C-7 ✅

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
| 2026-05-06 (Sprint C-5 Phase 5.3 — ADR-007 ext consentement_by + cgu_version — 1 clôture P2 RGPD audit trail complet) | 28 | 1 | 12 | 15 |
| 2026-05-06 (Sprint C-5 Phase 5.4 — Polish 4 dettes (P1 SG TraceTooltip + P1 SG YAML constants reclassif P2 + 2 P1 ADR-008/009 audit qualité)) | 25 | 1 | 9 | 15 |
| 2026-05-06 (Sprint C-5 Phase 5.5 — Fix audit 4 bloquants : VNU terminologie + multi-meter filter + 4 tests intégration endpoint + 1 P0 nouvelle DEMO_MODE) | 26 | 2 | 9 | 15 |
| 2026-05-06 (Sprint C-5 Phase 5.6 — Fix 4 P0 audit deep multi-agents : F1 PRAGMA FK + F2 R19 NULL + F3 Capacité 3.15→3150 + F4 SG tolerance 1500→1.5 + 23 dettes C-7 tracées) | 49 | 4 | 18 | 27 |
| 2026-05-06 (Sprint C-5 Phase 5.8 — Fix 6 P0 audit transversal : G1 cascade Org PATCH wiring + G2 R20 NULL + G3 BillAnomaly UNIQUE + G4 ADR-015 warning + G5 IDOR stepper + G6 operat_export NULL DT compliance) | 43 | 1 | 18 | 24 |
| 2026-05-06 (Sprint C-7 Phase 7.1 — Site +1 col s_ce_m2 Surface CE Décret Tertiaire — clôture P0 historique D-Phase4-2-Operat-Surfaces-3-Distinct + migration Alembic 11e propre) | 42 | 0 | 18 | 24 |
| 2026-05-06 (Sprint C-7 Phase 7.2 — DEMO_MODE bypass scope_utils fix ADR-017 Option B — clôture P0 SEC-2026-012, surface attaque ~25 endpoints éliminée) | 41 | 0 | 18 | 23 |
| 2026-05-06 (Sprint C-7 Phase 7.3 — PATCH endpoints consentement Org/DP ADR-019 — clôture P0 RGPD D-Sprint-C7-PATCH-Consentement-Endpoint-001) | 40 | 0 | 18 | 22 |
| 2026-05-06 (Sprint C-7 Phase 7.4 — log_consent_change helper RGPD CNIL — clôture P0 D-Sprint-C7-AuditLog-Wiring-RGPD-Consent-Change-001 + CLÔTURE PATTERN DOCTRINAL 5/5 "Déclaration sans enforcement runtime") | 39 | 0 | 18 | 21 |
| 2026-05-06 (Sprint C-7 Phase 7.5 — `audit_external_api_call` décorateur ADR-018 + wiring 4 connecteurs cardinaux DataConnect/GRDF/Sirene — clôture P0 D-Sprint-C7-External-Connectors-Audit-Trail-001 → **0 P0 résiduel Sprint C-7 → PRÉ-PILOTE-READY tactique**) | 38 | 0 | 18 | 20 |
| 2026-05-06 (Sprint C-7 Phase 7.6 — ADR-016 Math+Runtime+Cross-Module Enforcement Doctrine implémenté + 3 pre-commit hooks systémiques (anti-DROP + anti-PRAGMA + anti-arithmétique) + CI workflow — POLISH DOCTRINAL CARDINAL Phase D+ filet de sécurité automatisé) | 38 | 0 | 18 | 20 |
| 2026-05-06 (Sprint C-7 Phase 7.7 Lot A — Bill Anomaly enrichissements 4 P1 + 3 P2 (HPE/HCE/PM HTA + PII sanitization SIREN/PRM + word-boundary regex + decoupling commit + UNIQUE Phase 5.8 G3 anti-régression + YAML legal_reference enrichi) — commit 6408a25b) | 31 | 0 | 14 | 17 |
| 2026-05-06 (Sprint C-7 Phase 7.7 Lot B — REGOPS Weights AUDIT_APPLICABLE SG + Accise SG coverage + invariants 100% (3 P1 + 1 P2) — commit 2713ab4b) | 27 | 0 | 11 | 16 |
| 2026-05-06 (Sprint C-7 Phase 7.7 Lot C — EnergyInvoice +1 col tva_rate Numeric(5,4) + 12e migration Alembic propre + VNU terminologie cardinale 6 callsites (1 P1 + 1 P2) — commit c5ace813) | 25 | 0 | 10 | 15 |
| 2026-05-06 (Sprint C-7 Phase 7.7 Lot D — Bill Intelligence endpoint Literal validation + pagination + KPI total_economie_potentielle_eur (3 P2) → **Phase 7.7 totale : 8 P1 + 9 P2 = 17 dettes clôturées**) | 22 | 0 | 10 | 12 |
| 2026-05-06 (Sprint C-7 AUDIT COMPLET PHASE 7 multi-agents SDK 6 parallèles — 24 findings nouveaux détectés (6 P0 + 10 P1 + 8 P2) → **PRÉ-PILOTE-READY ASSERTION RÉVISÉE**) | 46 | 6 | 20 | 20 |
| 2026-05-06 (Sprint C-7 Phase 7.8 — 6 P0 fixes critiques audit deep clôturés : IDOR DataConnect 5 endpoints + IDOR GRDF 2 endpoints + IDOR org_id_override + audit RGPD commit immédiat + Article 5(2)+30 RGPD + TURPE 7 vs TURPE 6 codes — **PRÉ-PILOTE-READY RÉEL atteint**) | 40 | 0 | 20 | 20 |
| 2026-05-07 (Sprint C-8 Phase 8.1 Lot REGOPS — 3 P1 fixes : Scoring OPERAT migration s_ce_m2 ADR-020 Option C + CGU référentiel central + KPI mutation cardinal canonique cross-vues) | 37 | 0 | 17 | 20 |
| 2026-05-07 (Sprint C-8 Phase 8.2 Lot SEC+CI — 3 P1 fixes : PII étendue email/téléphone FR/IBAN FR + CI bloquant quality-gate.yml + import lazy fix top-level guard) | 34 | 0 | 14 | 20 |
| 2026-05-07 (Sprint C-8 Phase 8.3 Lot CR+REG polish — 4 P1 fixes : dead-code comments rgpd_consent + Organisation.actif.is_(True) idiomatique + VNU tarifs YAML L.336-2 + _is_hash_key('code') exact match strict) | 30 | 0 | 10 | 20 |
| 2026-05-07 (Sprint C-8 AUDIT COMPLET multi-agents SDK 6 parallèles — Pilier 6 ADR-016 reproduit — 26 findings nouveaux (3 P0 + 13 P1 + 10 P2) → **PILOTE EXTERNE READY ASSERTION RÉVISÉE**) | 56 | 3 | 23 | 30 |
| 2026-05-07 (Sprint C-8 Phase 8.4 Lot 1 — 3 P0 hotfix audit deep : VNU L.336-2 ligne 560 + CGU archives rejected runtime CNIL Article 7 + Helper ADR-020 wiré generate_operat_csv) | 53 | 0 | 23 | 30 |
| 2026-05-07 (Sprint C-8 Phase 8.4 Lot 2 — 4 P1 SEC+REG : address allowlist ip_address + CGU reload doc admin-only + contenu_sha256 field + dates archive_test_only clarif) | 49 | 0 | 19 | 30 |
| 2026-05-07 (Sprint C-8 Phase 8.4 Lot 3 — 5 P1 CR+QA+BI : hash_key dedup + URL placeholder JORFTEXT fix + BILAN drift lendemain + BILAN comptage SG + KPI renommage `kpi_vnu_dormant_reclaim_eur`) | 44 | 0 | 14 | 30 |
| 2026-05-07 (Phase D-0 hotfix Patrimoine — 3 P0 audit Sprint Patrimoine v1 : D6 SousCompteur self-FK + Bâtiment 5 champs RNB/DPE/rénovation + Site categorie_operat + mode_propriete — 13e migration Alembic propre) | 41 | 0 | 14 | 27 |
| 2026-05-07 (Phase D-1 hotfix Patrimoine — 4 P1 audits cumulés : DP TURPE 7 explicite (5 champs) + Org enrichi entreprise (6 champs) + PII patterns ordre + retrait `\d{10}` + CGU sha256 helper integrity — 14e migration Alembic propre) | 37 | 0 | 10 | 27 |
| 2026-05-07 (AUDIT COMPLET PHASE D-0+D-1 multi-agents SDK 6 parallèles — Pilier 6 ADR-016 reproduit Sprint C-7→C-8→D — 25 findings nouveaux (3 P0 + 12 P1 + 10 P2) → **PILOTE EXTERNE READY ASSERTION RÉVISÉE** (Tier 1 ~3-4h obligatoire avant démo investisseur)) | 62 | 3 | 22 | 37 |
| 2026-05-07 (Sprint D1-B Validators cross-FK Top 20 contraintes matrice v1 §8.3 — 5 validators DP TURPE 7+gaz + 3 contraintes DB (C50+C60+C85+C108) + 15e migration Alembic propre + script audit pré-migration) | 62 | 3 | 22 | 37 |
| 2026-05-07 (Phase D-2 hotfix Tier 1 — 3 P0 cardinaux audit Phase D : TURPE 7 dates 1/02/2025 + codes FTA canoniques CRE + ADR-D-01 Compteur/Meter dualité bridge léger Option C — 3 docs audits livrés via 6 agents SDK Pilier 6 ADR-016 4e cycle) | 59 | 0 | 22 | 37 |
| 2026-05-07 (Phase D-2.2 ajustée — Enum FtaCode strict canonique + ADR-016 v3 Pilier 9 (validator permissif transitoire → Enum strict) + 3 P1 code-reviewer fixés (anti-cycle + org-scoping + tests négatifs)) | 56 | 0 | 19 | 37 |
| 2026-05-07 (Sprint Audit Réglementaire Cardinal pré Phase D-3 — 17 catégories réglementaires auditées via 3 agents SDK + cross-check KB — 10 P0 + 10 P1 + 25 à vérifier identifiés. Toutes sources externes WebFetch bloquées 403/503 → rapport escalade humaine livré (17 sources à figer Phase D-4 ~3h navigateur direct)) | 76 | 10 | 29 | 37 |
| 2026-05-07 (Phase D-3 Tier 0 RÉGLEMENTAIRE — 5 P0 actionnables fixés : APER échéance 01/07/2026 LARGE parkings + APER LARGE surface 10000m² + APER solar ratio 50% + OPERAT 426 sous-cat constante + BACS 70 kW 2030 exposé + VNU 4 constantes mécanisme — mirroring constants.py↔sources_reglementaires.yaml) | 71 | 5 | 29 | 37 |

---

## 📊 AUDIT COMPLET PHASE D-0 + D-1 — 25 NOUVELLES DETTES (2026-05-07)

**Méthode** : 6 agents SDK parallèles (code-reviewer + security-auditor + qa-guardian + regulatory-expert + bill-intelligence + architect-helios) — Pilier 6 ADR-016 reproduit Sprint C-7 → C-8 → **D** (3e cycle stable, ROI ×7 méthodologique vs séquentiel).

**Périmètre** : 4 commits Phase D (`50ef8766` audit Onboarding + `f738f1d0` audit Sprint Patrimoine v1 + `55f8afa2` Phase D-0 hotfix D6+Bâtiment+Site + `2726c77b` Phase D-1 hotfix DP TURPE 7+Org+PII+CGU sha256).

**Référence** : [`AUDIT_PHASE_D_COMPLET_2026_05_07.md`](AUDIT_PHASE_D_COMPLET_2026_05_07.md)

### 🔴 3 P0 BLOQUANTS PILOTE EXTERNE (Tier 1 ~3-4h)

- **D-Audit-D-TURPE7-Date-Application-001** P0 REG — `models/patrimoine.py:294-305` commentaire cite "JO 14/05/2025" comme date application TURPE 7, MAIS date application réelle = **01/08/2025** (CRE délibération 2025-78 — JO ≠ application). Fix commentaire 5 min. confidence: high.
- **D-Audit-D-CodeFta-Nomenclature-Inventee-002** P0 REG+BI — `code_fta` exemple `"BT_HCH_PRO"` (tests Phase D-1) **non canonique**. Nomenclature officielle Enedis TURPE 7 = `BTINFCU4` / `BTINFMU4` / `BTSUP` / `HTACU5` / `HTALU5` (5 segments × 4 options). Risque KeyError silencieux R13 mismatch + faux positif/négatif systématique sites C4. Fix : Enum exhaustif ~12 combinaisons OU regex `r'^(C[1-5]|BT|HTA|HTB)_'` + cross-FK avec `TariffSegmentEnum`/`TariffOptionEnum`. ~30 min.
- **D-Audit-D-Compteur-Meter-Dualite-003** P0 ARCH — D6 SousCompteur self-FK ajouté Phase D-0 sur `Compteur` MAIS `consumption_unified_service.py` SoT consommation utilise **exclusivement `Meter`** (cf. `timeseries_service.py:60-75` `get_site_meter_ids` dédoublonne via `parent_meter_id`). Sub-meters CVC/IT déclarés sur `Compteur.sub_meter_of_id` resteront **orphelins runtime** → différenciateur "pilotage CVC/IT" annoncé sans chaîne d'exploitation. Fix : ADR-D-01 trancher dualité (deprecate Compteur OU wirer consumption_unified_service les deux). ~2-3h.

### 🟠 12 P1 AVANT PILOTE EXTERNE (~8-10h)

Sécurité (3, préexistants pré-D — surface étendue par nouveaux champs) :

- **D-Audit-D-IDOR-Patrimoine-Crud-004** P1 SEC (Critical pré-D) — 6 endpoints `patrimoine_crud.py:101-616` sans `resolve_org_id`. ~1h fix.
- **D-Audit-D-IDOR-GET-Compteurs-005** P1 SEC (High pré-D) — `GET /api/compteurs/{id}` sans auth ni org-scoping. ~30 min fix.
- **D-Audit-D-Path-Traversal-CGU-Sha256-006** P1 SEC — `compute_cgu_pdf_sha256(pdf_path)` Phase D-1 sans restriction → oracle hash fichiers système. Allowlist `docs/cgu/*` requise. ~15 min fix.

String vs Enum systémique (5 — régression doctrinale post-Sprint C-7 ADR-016) :

- **D-Audit-D-Version-Turpe-String-007** P1 CR — `version_turpe` String(10) → Enum strict (couvre P0-001 cardinal billing).
- **D-Audit-D-Mode-Propriete-String-008** P1 CR — `mode_propriete` String(20) → réutiliser `EfaRole` existant (PROPRIETAIRE/LOCATAIRE/MANDATAIRE).
- **D-Audit-D-Secteur-String-009** P1 CR — `secteur` Org String(50) → réutiliser `Typologie` existant (TERTIAIRE_PRIVE/INDUSTRIE/COMMERCE_RETAIL).
- **D-Audit-D-Sub-Meter-Usage-String-010** P1 CR — `sub_meter_usage` String(50) → Enum (CVC/IT/ECLAIRAGE/AUTRES) ou réutiliser `UsageFamily`.
- **D-Audit-D-Dpe-Class-String-011** P1 CR — `dpe_class` String(1) → réutiliser `DpeClasseEnergie` existant (A-G + VIERGE).

Architecture / cross-pillar (3) :

- **D-Audit-D-Anti-Cycle-D6-012** P1 ARCH+QA — `Compteur.sub_meter_of_id` self-FK sans garde anti-cycle A→B→A. Aucun validator. Fix : SQLAlchemy event listener + test cycle 3 niveaux. ~1h.
- **D-Audit-D-NAF-Org-Site-Duplication-013** P1 ARCH — `code_naf_principal` Org + `Site.naf_code` sans arbitrage doctrinal. Étendre `resolve_naf_code()` chain fallback Site→Org. ~30 min.
- **D-Audit-D-PII-Sanitizer-2-SoT-014** P1 ARCH — `_SENSITIVE_KEY_PATTERNS` (`audit_log_service`) vs `_PII_PATTERNS` (`anomaly_detector`) 2 SoT distinctes. Extraire `services/security/pii_sanitizer.py` SoT unique. ~1.5h.

Bill Intelligence (2) :

- **D-Audit-D-R13-Reseau-Mismatch-Code-Fta-015** P1 BI — R13 fallback C5 BT ne consomme pas `code_fta` Phase D-1. Faux positif/négatif systématique sites C4 (~35% écart variable). Fix : intégrer `code_fta` chain résolution. ~1h.
- **D-Audit-D-PCE-Legacy-10-Chiffres-016** P1 BI — labels VNU 2024-2025 exposent PCE 10 chiffres post retrait `\b\d{10}\b` runtime. Pattern contextualisé `PCE\s*[:\-]?\s*\d{10}` requis. ~30 min.

CGU + Org (2) :

- **D-Audit-D-CGU-Helper-Non-Cable-017** P1 QA — `compute_cgu_pdf_sha256` livré Phase D-1 mais NON câblé endpoint admin → `contenu_sha256` reste `null` indéfiniment pré-pilote. Récidive anti-pattern "Helper orphelin" Phase 8.1. Fix : endpoint admin POST `/admin/cgu/{version}/compute-sha256`. ~45 min.
- **D-Audit-D-Tva-Intra-Format-018** P1 QA+REG — `tva_intra` String sans validation regex `^FR\d{11}$`. Fix : Pydantic field validator. ~15 min.

### 🟡 10 P2 SPRINT E BACKLOG (~5-7h)

- **D-Audit-D-Categorie-Operat-Doublon-019** P2 CR — `categorie_operat_principale` doublon `usage_principal` Enum existant.
- **D-Audit-D-Imports-Lazy-CGU-Sha256-020** P2 CR — `compute_cgu_pdf_sha256` imports lazy `hashlib` + `pathlib` → top-level.
- **D-Audit-D-Chiffre-Affaires-Cleartext-021** P2 SEC — `chiffre_affaires_eur` cleartext + audit log mutations financières manquant.
- **D-Audit-D-Code-Fta-XSS-022** P2 SEC — `code_fta` String non-Enum permet `<script>` injection si reflété frontend sans escape (XSS storage low risk).
- **D-Audit-D-Db-None-Bypass-023** P2 SEC — backward-compat `db=None` bypass `scope_utils` legacy callers (déjà contraint Phase 7.2 mais résidu signal).
- **D-Audit-D-RNB-V9-Mention-024** P2 REG — RNB V9.0 mentionné Phase D-0 non vérifiable (retirer ou citer source officielle IGN/CSTB).
- **D-Audit-D-NAF-Rev3-Migration-025** P2 REG — `code_naf` NAF Rev. 2 → Rev. 3 transition janvier 2027 (migration roadmap Phase E+).
- **D-Audit-D-Audit-SME-Logique-026** P2 REG — Audit SMÉ Décret 2024-1304 logique service-level absent (champs Org `effectif_total`/`chiffre_affaires_eur` présents seulement, pas de scoring assujettissement).
- **D-Audit-D-Mode-Traitement-Allowlist-027** P2 REG — `mode_traitement` allowlist `{smart, traditionnel, telereleve, manuel}` non normative CRE — vocabulaire interne PROMEOS à documenter.
- **D-Audit-D-Bill-Anomaly-R21-R23-028** P2 BI — 3 candidats détecteurs Bill Anomaly identifiés (R21 FTA mismatch + R22 Audit SMÉ assujettissement + R23 sub-meter consistency portfolio).

### Patterns émergents Phase D candidats Pilier ADR-016

- **Pilier 8 candidat** — Hiérarchies internes via self-FK (`sub_meter_of_id` + backref + ondelete=SET NULL). Transposable EntiteJuridique parent/filiale, Action workflow parent/sub.
- **Pilier 9 candidat** — Preuve d'origine forte SHA-256 (`compute_<doc>_sha256` + `verify_<doc>_integrity`). Réutilisable CGV/charte RGPD/OPERAT export PDF/facture PDF.
- **Anti-pattern détecté** — String prematuré là où Enum existant (5 occurrences Phase D-0/D-1). Codifier dans ADR-016 : "consulter `enums.py` AVANT créer `String` pour domaine fini".

### Verdict révisé pilote

| Pilote | Pré audit Phase D | Post audit Phase D |
| --- | --- | --- |
| Interne | ✅ READY | ✅ READY |
| Investisseur démo | ✅ READY | 🟠 **CORRECTIONS Tier 1** (3 P0 ~3-4h) |
| Externe complet | 🟠 P1 résiduels | 🔴 **BLOCK Tier 1+2** (3 P0 + 8 P1 critiques ~10-15h) |

**Confidence verdict** : `high` (consensus 6 agents indépendants sur 3 P0 cardinaux REG + ARCH).

---

## 📊 AUDIT COMPLET SPRINT C-8 — 26 NOUVELLES DETTES (2026-05-07)

**Méthode** : 6 agents SDK parallèles (code-reviewer + security-auditor + qa-guardian + regulatory-expert + bill-intelligence + architect-helios) — Pilier 6 ADR-016 reproduit avec succès post Sprint C-7 audit deep.

**Référence** : [`AUDIT_SPRINT_C8_COMPLET_2026_05_07.md`](AUDIT_SPRINT_C8_COMPLET_2026_05_07.md)

### 🔴 3 P0 BLOQUANTS PILOTE EXTERNE (Tier 1 ~1h)

- **D-Audit-C8-VNU-L336-Source-Field-001** P0 REG — `tarifs_reglementaires.yaml:560` cite `L.336-1` (vs L.336-2 corrigé header Phase 8.3) — fix 1-ligne (5 min). Phase 8.3 fix incomplet.
- **D-Audit-C8-CGU-Archives-Accepted-002** P0 SEC (High) — `is_valid_cgu_version()` accepte versions `statut: archive` postérieures à `actuel` → CNIL Article 7 violé (preuve d'origine forte invalidée). Fix : filtrer `statut='actuel'` PATCH runtime + chronologie YAML (~30 min).
- **D-Audit-C8-Helper-OPERAT-Orphan-003** P0 CR — `resolve_surface_for_operat_export()` Phase 8.1 livré mais NON wiré dans `operat_export_service.py:324 generate_operat_csv`. ADR-020 Pilier 2 partiel — helper orphelin = dead-code fonctionnel. Fix : wiring (~30 min).

### 🟠 13 P1 AVANT PRODUCTION SCALING (~5-6h)

Sécurité (3) :
- **D-Audit-C8-CGU-Cache-Reload-Auth-004** P1 SEC — LRU cache + `reload_cgu_referentiel()` sans guard auth (path traversal risk).
- **D-Audit-C8-Address-Substring-Match-005** P1 SEC — `address` substring → `ip_address` sur-redacted (perte traçabilité CNIL article 5(2)).
- **D-Audit-C8-PII-Patterns-Order-006** P1 SEC — chevauchement `\b\d{14}\b` + `\b\d{10}\b` + `\b\d{9}\b` ordre causal labels EDF/Engie.

Réglementaire (2) :
- **D-Audit-C8-CGU-Pdf-Hash-007** P1 REG — `cgu_referentiel.yaml` 4 versions `contenu_pdf: null` → preuve CNIL article 7 non opposable.
- **D-Audit-C8-CGU-Dates-Versionning-008** P1 REG — dates publication CGU rétro-actives suspectes + saut 1.0→2.0 inexpliqué.

Code review / QA (4) :
- **D-Audit-C8-Hash-Key-Siret-Redundant-009** P1 CR — `_is_hash_key('siret')` redondance `pattern == lk OR pattern in lk` + risque sur `siret_etablissement`.
- **D-Audit-C8-OPERAT-VA-URL-Placeholder-010** P1 CR — `operat_valeurs_absolues.yaml:59` URL placeholder `JORFTEXT000052113xxx` commité.
- **D-Audit-C8-Bilan-Lendemain-Drift-011** P1 QA — Bilan claim "Phase 8.3 reportée lendemain" mais timestamps git = 11 min même journée.
- **D-Audit-C8-Bilan-Comptage-SG-012** P1 QA — Bilan revendique "4 SG Phase 8.1" → réel 3 + "139 tests" non réconciliable (réel ~134).

Bill Intelligence (2) :
- **D-Audit-C8-KPI-Semantic-Renaming-013** P1 BI — `kpi_total_economie_potentielle_eur` ambigu CFO → renommer `kpi_vnu_dormant_reclaim_eur`.
- **D-Audit-C8-KPI-Cockpit-Wiring-014** P1 BI — KPI Phase 8.1 endpoint orphelin (PAS consommé CockpitDecision/useCockpitFacts/BillIntelPage).

Architecture (1) :
- **D-Audit-C8-KPI-Canonical-Pilier-015** P1 ARCH — KPI canonique cross-vues non documenté Pilier ADR-016 (cardinal `feedback_kpi_tracabilite_obligatoire.md`).

### 🟡 10 P2 SPRINT D BACKLOG

- **D-Audit-C8-CI-Suites-Continue-On-Error-016** P2 — 3 suites Contracts V2/Power/Flex masquent 148 tests (consensus CR + QA + SEC).
- **D-Audit-C8-E2E-Smoke-Bug-017** P2 — Playwright bug `__dirname` ESM continue-on-error.
- **D-Audit-C8-KPI-Window-Disclosure-018** P2 — KPI sans `kpi_window` réponse JSON.
- **D-Audit-C8-ADR020-Version-URL-019** P2 — ADR-020 cite "v15/03/2024" sans URL versionnée.
- **D-Audit-C8-Helper-Reference-Version-020** P2 — `operat_export_helpers.py:21` perd mention version.
- **D-Audit-C8-Decret-2026-55-URL-021** P2 — décret 2026-55 cité sans URL Légifrance.
- **D-Audit-C8-VNU-Patterns-TotalEnergies-022** P2 BI — patterns "VERS. NUC."/"CONTRIB. NUCL." absents détecteur R19.
- **D-Audit-C8-VNU-Patterns-Eni-023** P2 BI — patterns "VNU 2026"/"VNU HIST" millésimés.
- **D-Audit-C8-S-CE-M2-Consistency-024** P2 ARCH — schisme silencieux scoring/export `s_ce_m2` vs `tertiaire_area_m2` (>10% écart sans warning).
- **D-Audit-C8-Cross-Pillar-EMS-Flex-Achat-025** P2 ARCH — Sprint C-8 = 0 impact EMS/Flex/Achat (décrochage roadmap stratégique Q2-Q3).
- **D-Audit-C8-Wrappers-CachedGet-Backlog-026** P2 — 20 wrappers `cachedGet` sans `.then((r) => r.data)` (memory `reference_api_wrapper_unwrap_pattern.md`).

---

---

## 📊 AUDIT COMPLET PHASE 7 — 24 NOUVELLES DETTES (2026-05-06)

**Méthode** : 6 agents SDK parallèles (code-reviewer + security-auditor + qa-guardian + regulatory-expert + bill-intelligence + architect-helios) sur 10 commits Phase 7.1 à 7.7.

**Référence** : [`AUDIT_PHASE_7_COMPLET_2026_05_06.md`](AUDIT_PHASE_7_COMPLET_2026_05_06.md)

### 🔴 P0 BLOQUANTS PRÉ-PILOTE (6 dettes — Tier 1+2 corrections cumulées ~5-6h)

- **D-Sprint-C7-IDOR-DataConnect-Connectors-001** P0 — 5 endpoints `/api/dataconnect/*` (authorize/callback/consent/sync/tokens) sans `resolve_org_id`. CWE-639 + CWE-862. Lecture/écriture cross-tenant PRM. Fix : ajouter resolve_org_id + JOIN chain Meter→Site→Portefeuille→EJ. ~2h.
- **D-Sprint-C7-IDOR-GRDF-Endpoints-001** P0 — 2 endpoints `/api/grdf/pce/{pce}/*` sans org-scoping. Identique DataConnect. ~1h.
- **D-Sprint-C7-IDOR-OrgIdOverride-Bypass-001** P0 — `scope_utils.py:170` `if org_id_override: return org_id_override` sans validation DB ni JWT cross-check. Bypass DEMO_MODE via query param. ~30 min.
- **D-Sprint-C7-Audit-RGPD-Transaction-Decoupling-001** P0 CNIL — `rgpd_consent.py:113` log_consent_changes_batch dans transaction principale → rollback efface AuditLog → CWE-778 perte preuve CNIL article 7. Fix : session DB dédiée pattern Phase 7.5. ~30 min.
- **D-Sprint-C7-RGPD-Article-6-vs-5-2-Mislabel-001** P0 REG — `audit_log_service.py:414` `rgpd_article: "Article 6 RGPD"` juridiquement inadéquat (Article 6 = bases légales, traçabilité = Article 5(2) accountability + Article 30 registre). Fix : remplacer texte. ~15 min.
- **D-Sprint-C7-TURPE-7-Codes-HTA-Mismatch-001** P0 REG — `anomaly_detector.py:54-66` ajout HPE/HCE/PM annoncé "TURPE 7" mais codes TURPE 6 obsolètes (TURPE 7 utilise P/HPH/HCH/HPB/HCB). Fix : commenter rétro-compat OU retirer. ~30 min.

### 🟠 P1 AVANT PRODUCTION SCALING (10 dettes — ~6-8h)

- **D-Sprint-C7-PII-Sanitization-Email-IBAN-001** P1 SEC — `_sanitize_pii_label` manque email/téléphone/IBAN/RIB. Étendre `_PII_PATTERNS`. ~30 min.
- **D-Sprint-C7-Hash-Key-Code-Overmatch-001** P1 SEC — `_is_hash_key('code')` matche `period_code`/`error_code`. Fix word-boundary `lk == 'code'`. ~15 min.
- **D-Sprint-C7-PKCE-Pending-Auth-InMemory-001** P1 SEC — `_pending_auth: dict[str, str]` non borné, multi-worker incompatible. Fix : DB/Redis TTL. ~1h.
- **D-Sprint-C7-Audit-External-Positional-Args-001** P1 SEC — `audit_external_api_call` extrait org_id via `kwargs.get()` only. Fix : inspecter args[1:]. ~30 min.
- **D-Sprint-C7-RGPD-Consent-Dead-Comments-001** P1 CR — `rgpd_consent.py:147` + `:250` commentaires résidus "Phase 7.4 préparation" obsolètes. ~5 min.
- **D-Sprint-C7-Audit-Service-Import-Lazy-001** P1 CR — `audit_log_service.py:418` `from database import SessionLocal` dans fonction → silencieusement swallowed BLE001. Fix : import top-level. ~15 min.
- **D-Sprint-C7-Bill-KPI-Filter-Mutation-001** P1 CR — `bill_intelligence.py:113` KPI muté par filtres user (`code=R20` → KPI R19=0). Fix : query indépendante OR documenter `kpi_scope: 'filtered'`. ~30 min.
- **D-Sprint-C7-Org-Actif-Idiomatic-001** P1 CR — `scope_utils.py:187` `Organisation.actif == True` non-idiomatique vs `.is_(True)` ligne 90 du même fichier. ~5 min.
- **D-Sprint-C7-VNU-L336-Article-Inconsistency-001** P1 REG — VNU YAML ligne 550 `L.336-1` vs brief Lot C `L.336-2` incohérence. Trancher manuellement Légifrance. ~30 min.
- **D-Sprint-C7-TURPE-7-BT-Gestion-Unit-Mismatch-001** P1 REG — YAML `gestion_eur_mois: 18.48` (= 221.76 €/an) vs `catalog.py:194 TURPE_GESTION_C5: 16.80 EUR/an` facteur ~13×. Audit unité YAML. ~30 min.
- **D-Sprint-C7-Accise-T1-T2-Inverted-Brief-001** P1 REG — Brief Lot B `ACCISE_ELEC_T2_C5_MENAGE = 25.09` incohérent (T1=30.85 ménage, T2=26.58 PME). Terminologie inversée. ~15 min.
- **D-Sprint-C7-Scoring-OPERAT-S-CE-M2-Migration-001** P1 ARCH — `backend/regops/scoring.py` pas migré sur `s_ce_m2` Phase 7.1. Risque divergence SoT silencieuse. ~1h.
- **D-Sprint-C7-CI-Pytest-Continue-On-Error-001** P1 QA — `quality-gate.yml:106` `continue-on-error: true` rend claim "0 régression" non-vérifiable CI. Fix : retirer continue-on-error principal. ~15 min.
- **D-Sprint-C7-Alembic-Drift-Initial-001** P1 QA — Migration `2f83c6bebc57` "massively out of sync" — `alembic upgrade head` produit état divergent. Fix : migration catch-up Sprint C-8. ~2h.

### 🟡 P2 SPRINT C-8 BACKLOG (8 dettes — ~3-5h)

- **D-Sprint-C7-Logger-Lazy-Format-001** P2 — f-string logger `anomaly_detector.py:338` au lieu `%s`.
- **D-Sprint-C7-Hook-Math-X-Token-001** P2 — Regex hook math `[*×x]` token `x` minuscule risque faux positifs.
- **D-Sprint-C7-TVA-Rate-CheckConstraint-001** P2 — `Numeric(5,4)` sans CheckConstraint valeurs admises {0.055, 0.10, 0.20}.
- **D-Sprint-C7-Audit-Response-Hash-Canonical-001** P2 — `response_hash` non-canonique pour objets ORM.
- **D-Sprint-C7-Hook-Math-Yaml-Coverage-001** P2 — `.pre-commit-config.yaml:42` exclut `operat_valeurs_absolues.yaml`.
- **D-Sprint-C7-DataConnect-PRM-Error-Leak-001** P2 SEC — PRM/PCE bruts dans messages d'erreur 404.
- **D-Sprint-C7-Hooks-Project-Dir-001** P2 QA — Hooks pré-commit sans `$CLAUDE_PROJECT_DIR` (CLAUDE.md règle 10).
- **D-Sprint-C7-External-Audit-Flex-Generalization-001** P2 ARCH — Décorateur `audit_external_api_call` non généralisé Flex (NEBCO/AOFD).
- **D-Sprint-C7-ADR-Index-Canonical-001** P2 ARCH — Pas d'ADR-000 index canonique.
- **D-Sprint-C7-CRE-URL-Deep-Link-Stable-001** P2 BI — URL CRE TURPE 7 deep-link instable.
- **D-Sprint-C7-Bill-Codes-HPS-HCS-PTE-001** P2 BI — Codes TURPE 7 manquants HPS/HCS, PTE alias.

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

## ~~D-Phase4-4-ADR-007-Consent-By-CGU-Version-001~~ — ✅ CLÔTURÉE Sprint C-5 Phase 5.3

**Détecté** : Sprint C-4 Phase 4.4 (modèle Org/DP consentement, 2026-05-05)
**Clôturée** : Sprint C-5 Phase 5.3 (2026-05-06, commit `f3849751`, ADR-007 ext)

**Livrables Phase 5.3** :

- **Migration Alembic 9e propre** (`b86d01f19001_phase_5_3_sprint_c_5_org_dp_.py`) — 63 drop_table/drop_index autogenerate retirés discipline anti-DROP 9e épisode (cumul Phase C : 0 destructive)
- **8 cols ajoutés** :
  - `organisations` +4 : `consentement_dataconnect_by` (FK users.id ON DELETE SET NULL) + `consentement_dataconnect_cgu_version` (String 20) + `consentement_grdf_by` + `consentement_grdf_cgu_version`
  - `delivery_points` +4 : `consentement_dataconnect_local_by` + `consentement_dataconnect_local_cgu_version` + `consentement_grdf_local_by` + `consentement_grdf_local_cgu_version`
- **`ondelete=SET NULL` cardinal** : suppression user (RGPD droit oubli art. 17) préserve l'historique de consentement (la trace persiste, la référence personnelle disparaît)
- **Helper enrichi** `services/consent_service.py:get_effective_consent_with_audit(dp, type_) -> dict` — retourne dict 5 clés stable : `active + by_user_id + cgu_version + at + scope` (local/global/none)
- **Tests** : 13 tests `test_org_dp_consentement_by_cgu_version.py` (CRUD Org/DP + ondelete SET NULL + helper 3 scopes + sérialisation contrat) — 13/13 verts
- **Source-guards** : 4 SG `test_consent_audit_trail_structure_source_guards.py` (Org 4 cols + DP 4 cols + ondelete=SET NULL × 4 + helper signature stable) — 4/4 verts

**Champs ADR-007 reportés Sprint C-7+** (audit trail forensique optionnel) :

- `consentement_*_ip_hash` (String SHA-256) — IP hashée RGPD-safe pour audit forensique (non bloquant MVP, dette `D-Sprint-C7-Consent-IP-Hash-Audit-001` P2 à créer si besoin réel détecté pré-pilote)

**Effort réel** : ~1.5 h (vs 1-1.5 j-h estimé) = **gain -85 à -90% maintenu**.

**Différenciateur produit** : audit RGPD officiel "preuve d'origine + valeur" complet (qui + quelle CGU + quand + scope) pour cas d'usage cardinaux :

- Audit RGPD CNIL ("prouvez que tel utilisateur a accepté tel jour la version X")
- Cockpit RGPD UI Sprint C-5+ — affichage trace complète par PRM/PCE
- Export RGPD droit d'accès personnel (article 15 RGPD)

**Priorité** : ✅ CLÔTURÉE
**Sprint cible** : Sprint C-5 ✅

**Référence** : `docs/adr/ADR-007-rgpd-consentement-dataconnect-grdf-modele.md` section "Implémentation Phase 5.3 actée".

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

## ~~D-Sprint-C3-7d-ADR-Intensity-OPERAT-Naming-001~~ — ✅ CLÔTURÉE Sprint C-4 Phase 0

**Détecté** : Sprint C-3 Phase 3.7d audit architect-helios (2026-05-04)
**Clôturée** : Sprint C-4 Phase 0 (commit `76a57f7a`, ADR-008)

**Audit qualité tracker Phase 5.4** (2026-05-06) : la dette ciblait l'absence d'ADR figeant la cohabitation 2 endpoints intensity. **ADR-008 a effectivement été livré** Sprint C-4 Phase 0 (`docs/adr/ADR-008-cohabitation-endpoints-intensity-energy-vs-portfolio.md`) couvrant intégralement le périmètre :

- Cas d'usage canoniques (Cockpit/RegOps précision réelle vs Patrimoine.jsx KpiStripItem global)
- Différentiel sémantique (Meter readings ≠ Site.annual_kwh_total)
- Stratégie séparation pérenne (pas de convergence MVP)

Dette `D-Phase4-1-TraceTooltip-TermId-SG-Cross-Stack-001` adresse l'invariant 5 doctrinal lié (TraceTooltip termId validity), désormais livré Sprint C-5 Phase 5.4.

**Priorité** : ✅ CLÔTURÉE
**Sprint cible** : Sprint C-4 amont ✅ (livré ADR-008)

---

## ~~D-Sprint-C3-7d-ADR-Routes-Namespace-001~~ — ✅ CLÔTURÉE Sprint C-4 Phase 0

**Détecté** : Sprint C-3 Phase 3.7d audit architect-helios (2026-05-04)
**Clôturée** : Sprint C-4 Phase 0 (commit `76a57f7a`, ADR-009)

**Audit qualité tracker Phase 5.4** (2026-05-06) : la dette ciblait l'absence d'ADR figeant la séparation sémantique 2 namespaces. **ADR-009 a effectivement été livré** Sprint C-4 Phase 0 (`docs/adr/ADR-009-namespace-api-config-vs-regulatory.md`) couvrant intégralement le périmètre :

- Règles routage par type (constante Python vs source légale traçable)
- Cohérence pattern Sprint C-3 Phase 3.3 `/api/regulatory/rates`
- Migration `regulatory_constants` reportée Sprint C-7 (pas urgent MVP)

**Priorité** : ✅ CLÔTURÉE
**Sprint cible** : Sprint C-4 amont ✅ (livré ADR-009)

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

## ~~D-Phase4-1-TraceTooltip-TermId-SG-Cross-Stack-001~~ — ✅ CLÔTURÉE Sprint C-5 Phase 5.4

**Détecté** : Sprint C-4 Phase 4.1 (création `coherence_globale.yaml` v1.0, 2026-05-05)
**Clôturée** : Sprint C-5 Phase 5.4 (2026-05-06, commit `041c0faa`)

**Livrables Phase 5.4** :

- **SG cross-stack** `tests/source_guards/test_tracetooltip_termid_yaml_coherence_source_guards.py` (Option B BE pytest retenue) :
  - SG_TRACETOOLTIP_01 : scan `frontend/src/**/*.{jsx,js}` (regex `<TraceTooltip\b[^>]*\btermId="([^"]+)"`), validation 100% termId FE ⊆ `terms.keys()` YAML SoT
  - SG_TRACETOOLTIP_02 : au moins 1 usage statique TraceTooltip déployé (anti-régression suppression silencieuse R10)
  - Diagnostic riche en cas de fail (liste fichiers FE concernés par termId manquant)
- **Skip __tests__** : fixtures avec termIds factices ignorés (allowlist explicite tests dossier)
- **Test exec actuel** : 6 termIds FE validés (`COMPLIANCE_DT_PENALTY_EUR`, `OPERAT_SURFACE_CONSO_DEFINITION`, `REGOPS_WEIGHT_DT_DEFAULT`, `READINESS_WEIGHT_CONFORMITY_PCT`, `REGOPS_WEIGHT_BACS_DEFAULT`, `REGOPS_WEIGHT_APER_DEFAULT`) — 100% présents YAML

Effort réel : ~30 min (cible tenue exactement). 2 SG verts.

**Différenciateur R10 protégé** : typo `termId` silencieuse FE détectée fail-fast à la collection pytest (vs UX cassée silencieusement non détectée).

**Priorité** : ✅ CLÔTURÉE
**Sprint cible** : Sprint C-5 ✅

**Référence** : `backend/config/coherence_globale.yaml` invariant 5 `TRACETOOLTIP_TERMID_VALIDITY` désormais runtime-enforced.

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
**Statut** : 🟡 **PARTIELLEMENT CLÔTURÉE** Sprint C-5 Phase 5.4 (2026-05-06, commit `041c0faa`).

**Livrables Phase 5.4** (extension de 10 → 18 termes couverts SG cohérence YAML↔constants) :

- ✅ ACCISE_ELEC_T1_EUR_PER_MWH (SG_REG_CONST_06)
- ✅ ACCISE_ELEC_T2_EUR_PER_MWH (SG_REG_CONST_06)
- ✅ REGOPS_WEIGHT_DT_DEFAULT (SG_REG_CONST_07)
- ✅ REGOPS_WEIGHT_BACS_DEFAULT (SG_REG_CONST_07)
- ✅ REGOPS_WEIGHT_APER_DEFAULT (SG_REG_CONST_07)
- ✅ READINESS_WEIGHT_DATA_PCT (SG_REG_CONST_08, conversion décimal × 100 = pct)
- ✅ READINESS_WEIGHT_CONFORMITY_PCT (SG_REG_CONST_08)
- ✅ READINESS_WEIGHT_ACTIONS_PCT (SG_REG_CONST_08)

**Effort réel** : ~20 min (vs 30 min estimé). 8 nouvelles assertions (SG_REG_CONST_06/07/08), 18/18 verts.

**Termes restants reportés Sprint C-7 polish** (50/68, hors scope Phase 5.4) :

- ACCISE_GAZ (1 terme)
- PRICE_FALLBACK / PRICE_FLEX_NEBCO / PRICE_ELEC_ETI_2026 (3 termes prix marché)
- NEBCO_THRESHOLD_KW_PER_STEP (1 terme RTE)
- FLEX_HEURISTIC_EUR_PER_SITE_PER_YEAR (1 terme heuristique)
- APER_PENALTY_EUR_PER_M2_PER_YEAR (1 terme APER)
- BILL_ANOMALY_* / CAPACITE_RTE_* / VNU_* / CBAM_* / etc. (~43 termes pas tous nécessaires SG)

**Priorité résiduelle** : 🟡 P2 (extension cardinaux livrée — pondérations doctrine + accises + readiness)
**Sprint cible** : Sprint C-7 polish (extension complète 50 termes restants)

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

## ~~D-Phase4-2d-Capacite-EUR-MW-Disambiguation-001~~ — ✅ CLÔTURÉE Sprint C-5 Phase 5.2

**Détecté** : Sprint C-4 Phase 4.2d mini-audit pré-build (2026-05-05)
**Clôturée** : Sprint C-5 Phase 5.2 (2026-05-06, commit `cdbb9e21`, ADR-015)

**Note Phase 5.5 audit qualité** : barré ajouté rétroactivement (cohérence formelle avec autres dettes barrées Sprint C-5). Hypothèse B confirmée Phase 5.2 (3.15 EUR/MW unitaire enchère, calcul 0.43 EUR/MWh correct). 3 dimensions distinctes documentées ADR-015 (3.15 EUR/MW certificat / 0.43 EUR/MWh client TURPE / 20-50 k€/MW.an revenu producteur).

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
**Clôturée** : Sprint C-5 Phase 5.1 (2026-05-06, commit `be7fd8f0`, ADR-013)

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

## D-Sprint-C7-Demo-Mode-Org-Validation-001 — DEMO_MODE X-Org-Id sans validation DB (IDOR pré-existant)

**Détecté** : Sprint C-5 Phase 5.5 audit security-auditor (2026-05-06) — finding `PROMEOS-SEC-2026-001` HIGH

**Périmètre** : `backend/services/scope_utils.py:get_scope_org_id` accepte le header `X-Org-Id` brut en mode `DEMO_MODE=true` sans vérifier que l'organisation existe en DB ni qu'elle appartient à l'utilisateur. Un attaquant peut envoyer un entier arbitraire (`1`, `2`, `999`...) et obtenir les données de toute organisation cross-tenant.

**Code pré-existant** : ce risque IDOR est antérieur à Sprint C-5 (la fonction `get_scope_org_id` existe depuis Sprint C-2/C-3). Détecté en bonus par audit Sprint C-5 Phase 5.5 sur l'endpoint `/api/bill-intelligence/anomalies` (Phase 5.1) qui consomme `resolve_org_id`.

**Risque** :

- En production avec auth activée : protégé par chaîne JWT → `auth.org_id`
- En DEMO_MODE (POC, démo investisseur, pilote pré-prod si DEMO_MODE oublié) : tout utilisateur peut accéder à toute organisation
- Cardinal pré-pilote prod : doit être bloqué avant tout déploiement non-DEMO

**Action Sprint C-7** :

1. Modifier `services/scope_utils.py:get_scope_org_id` pour ajouter check DB :
   ```python
   if raw_org_id := request.headers.get("X-Org-Id"):
       org = db.query(Organisation).filter_by(id=int(raw_org_id), actif=True).first()
       if org is None:
           raise HTTPException(403, "Organisation introuvable ou inactive")
   ```

2. Tests intégration : org_id inexistant (`X-Org-Id: 99999`) → 403, pas 200

3. Cohérent avec mini-sprint IDOR meters (commit `40ebb348`) + IDOR Portfolio (commit `32d88c85`) — pattern PROMEOS-SEC-XXX

**Effort estimé** : ~15-20 min (modif scope_utils + 2 tests intégration)
**Priorité** : 🔴 **P0** (sécurité, bloquant pré-prod, pré-existant détecté audit Sprint C-5 Phase 5.5)
**Sprint cible** : Sprint C-7 polish (ou ticket dédié hors-sprint)

**Référence interne** : `PROMEOS-SEC-2026-001` (audit security-auditor Sprint C-5 Phase 5.5).

> **Alias tracker post Phase C clôture** : ce ticket est aussi référencé `D-Sprint-C7-DEMO-MODE-Bypass-Scope-Utils-001` dans la liste des 5 P0 résiduels pré-pilote (cf. `BILAN_PHASE_C_7_7_LIVRES_2026_05_06.md`).

> ✅ **CLÔTURÉE Sprint C-7 Phase 7.2** (2026-05-06, commit `<hash-phase-7-2>`, ADR-017 Option B).
>
> **Livrables** :
>
> - `backend/services/scope_utils.py` : `get_scope_org_id` étend signature `db: Optional[Session] = None`, ajoute validation DB stricte X-Org-Id (Organisation existence + actif + soft-delete check)
> - `backend/services/scope_utils.py:resolve_org_id` propage `db` à `get_scope_org_id` (fix runtime cardinal)
> - 10 tests cardinaux SEC-2026-012 : `tests/test_demo_mode_org_validation_phase72.py`
>   * Existant + actif → accepté ✓
>   * Inexistant DB → REJETÉ (anti-IDOR énumération)
>   * `actif=False` → REJETÉ
>   * Soft-deleted → REJETÉ
>   * Format invalide ('abc', injection-like) → REJETÉ
>   * JWT priorité préservée (anti-régression)
>   * Backward-compat `db=None` legacy callers
>   * Audit log security warning sur tentatives IDOR
> - 4 SG anti-régression : `tests/source_guards/test_demo_mode_no_bypass_scope_utils_source_guards.py`
> - Surface attaque ~25 endpoints éliminée (1 fix scope_utils protège tous endpoints `resolve_org_id`)
> - Démo investisseur préservée (DEMO_MODE actif, fallback DemoState après rejet X-Org-Id invalide)
> - 29/29 tests anti-régression Phase 5.5/5.6/5.8 endpoint Bill Intelligence + RGPD ext non régressés
>
> **Effort réel** : ~1.5 h (vs 3-4 h estimé Sprint C-7 = gain -50%).

## D-Sprint-C7-External-Connectors-Audit-Trail-001 — Connecteurs externes sans AuditLog (CNIL preuve d'extraction)

> ✅ **CLÔTURÉE Sprint C-7 Phase 7.5** (2026-05-06, ADR-018).
>
> **Livrables** :
>
> - `backend/services/audit_log_service.py` : décorateur `audit_external_api_call(provider, endpoint, method)` ajouté avec `_record_external_api_event` (session DB dédiée découplée caller, résilience exception logging) + `_sanitize_kwargs` (redact Authorization/Bearer/client_secret/token/code_verifier ; hash sha256[:16] PRM/PCE/SIREN/SIRET/usage_point_id/code)
> - `backend/connectors/enedis_dataconnect.py` : 2 wirings (`exchange_code` POST /oauth2/v3/token + `_api_get` lambda dynamic endpoint) — couvre fetch_daily/load_curve/check_consent transitivement
> - `backend/connectors/grdf_adict.py` : 1 wiring (`_api_get` lambda dynamic endpoint) — couvre fetch_informative/published transitivement
> - `backend/services/sirene_hydrate.py` : 1 wiring (`hydrate_siren_from_api` GET /search)
> - 13 tests cardinaux : `tests/test_audit_external_api_call_phase75.py`
>   * Décorateur succès → AuditLog `connector.api_call` créé
>   * Décorateur exception → AuditLog success=False + reraise + error_class
>   * Sanitisation Authorization/Bearer/client_secret/token redacted
>   * Hashing PRM/PCE/SIREN sha256:[16chars] (raw absent du detail_json)
>   * Session SQLAlchemy non sérialisée (pas dans args_summary)
>   * `functools.wraps` préserve `__name__`/`__doc__`
>   * Endpoint dynamique callable(*args, **kwargs)
>   * request_hash deterministic same-input
>   * Découplage transactionnel (audit DB down → caller continue)
> - 4 SG anti-régression : `tests/source_guards/test_external_connector_audit_trail_source_guards.py` (décorateur présent + 4 wirings + sentinelles redaction + action="connector.api_call" dot-snake)
>
> **CNIL article 6** : preuve d'extraction = qui (user_id si dispo) + quand (created_at) + où (provider+endpoint) + quoi (request_hash + response_hash) + résultat (success/error).
>
> **Effort réel** : ~2 h (vs 2-3 h estimé Sprint C-7 = dans la fourchette).
>
> **CARDINAL** : clôture **dernier P0 résiduel Sprint C-7** → 0 P0 résiduel → **PRÉ-PILOTE-READY tactique**.

**Détecté** : Sprint C-5 Phase 5.7 audit transversal AXE 5 (2026-05-06)

**Périmètre** : 3 connecteurs externes Phase C n'écrivent **aucun event AuditLog** lors des appels API tiers consommant des données à caractère personnel (PRM/PCE/SIREN — art. 4 RGPD) :

- `backend/connectors/enedis_dataconnect.py` — appels DataConnect Enedis (PRM élec, consentement client requis)
- `backend/connectors/grdf_adict.py` — appels ADICT GRDF (PCE gaz, consentement client requis)
- `backend/services/sirene_hydrate.py` — appels Sirene `recherche-entreprises.api.gouv.fr` (SIREN/SIRET, donnée publique mais traçabilité prospect/lead requise)

`sirene_hydrate.py:153` ne fait que `logger.info` stdout (volatile, non requêtable, non scopé org).

**Risque CNIL** : "preuve d'extraction" PRM/PCE/SIREN impossible à reconstituer post-incident. Audit RGPD CNIL ne peut pas trace "qui a consulté quoi quand pour quel client".

**Action Sprint C-7** :

1. Créer wrapper décorateur `@audit_external_api_call(provider, endpoint)` dans `backend/services/audit_log_service.py` :
   - Capture `correlation_id` (header `X-Correlation-ID` déjà supporté ligne 550 `routes/patrimoine/sites.py`)
   - Log : `provider`, `endpoint`, `status_code`, `payload_hash` (SHA256 sans secrets), `duration_ms`, `org_id`, `user_id`
   - 3 nouveaux event types `AuditLog.action` : `API_CALL_DATACONNECT`, `API_CALL_GRDF`, `API_CALL_SIRENE`
2. Wrapper `httpx.get/post` Sirene/DataConnect/GRDF dans 3 connecteurs
3. Tests cardinaux : 1 appel DataConnect réussi → 1 entrée AuditLog avec correlation_id
4. Source-guard : grep `httpx.get|httpx.post` dans `backend/connectors/` + `backend/services/sirene_*` doit être ≤ 0 hors wrapper

**Effort estimé** : ~2-3 h (wrapper + 3 wirings + 3 tests cardinaux + 1 source-guard)
**Priorité** : 🔴 **P0** (CNIL preuve d'extraction PRM/PCE/SIREN)
**Sprint cible** : Sprint C-7

**Référence** : audit transversal Phase 5.7 AXE 5 P0 finding C2 (`AUDIT_TRANSVERSAL_PHASE_C_2026_05_06.md`).

---

## Dettes Sprint C-7 polish — issues audit deep multi-agents Phase 5.5/5.6 (15 nouvelles)

**Détecté** : Sprint C-5 Phase 5.5 + 5.6 audit deep multi-agents (2026-05-06)
**Contexte** : 4 P0 cardinaux fix Phase 5.6 (F1+F2+F3+F4). Findings P1/P2 résiduels reportés Sprint C-7 polish.

### Bill Intelligence (Phase 5.1 audit)

- **D-Sprint-C7-BillAnomaly-Unique-Constraint-001** P1 — `UNIQUE(invoice_id, code)` pour anti-doublons concurrents (bill-intelligence finding B2). Migration Alembic 10e ~15 min.
- **D-Sprint-C7-BillAnomaly-Decoupling-Commit-001** P2 — retirer `db.commit()` interne `detect_anomalies_for_invoice` (couplage caller, code-reviewer A5). 5 min.
- **D-Sprint-C7-BillAnomaly-Thresholds-Source-001** P1 — sources affirmées seuils 0.01 EUR + 5% (regulatory-expert A2 + bill-intelligence A1). YAML `legal_reference` à enrichir, ~30 min.
- **D-Sprint-C7-BillIntelligence-KPI-Aggregate-001** P2 — KPI `total_economie_potentielle_eur` agrégé endpoint `/api/bill-intelligence/anomalies` (general-purpose D2). 1 h.
- **D-Sprint-C7-BillAnomaly-PII-Vnu-Labels-Sanitization-001** P1 — sanitizer regex SIREN/PRM dans `details_json.vnu_labels` (security-auditor SEC-002). 30 min.
- **D-Sprint-C7-BillAnomaly-Endpoint-Enum-Validation-001** P2 — `Literal["R19", "R20"]` query params (security-auditor SEC-003). 15 min.
- **D-Sprint-C7-BillAnomaly-Endpoint-Pagination-001** P2 — pagination + filtre date period_start/end. 30 min.
- **D-Sprint-C7-BillAnomaly-Multi-Postes-HTA-001** P1 — ajouter HPE/HCE/PM dans `_PERIOD_CODES_KNOWN` (TURPE 7 HTA). 10 min.
- **D-Sprint-C7-BillAnomaly-Word-Boundary-Regex-001** P2 — `_resolve_period_code` regex `\b<code>\b` (vs substring) anti-faux-positifs. 15 min.
- **D-Sprint-C7-BillAnomaly-VNU-Patterns-Fournisseurs-001** P2 — patterns "VERS. NUC.", "VNU 2026" (TotalEnergies/Eni/Vattenfall). 30 min.
- **D-Sprint-C7-BillAnomaly-Aggregate-By-Contract-001** P2 — agrégation R20 par contract_id pour éviter saturation cockpit (general-purpose A3). 1 h.

### Capacité (Phase 5.2 audit)

- **D-Sprint-C7-Capacite-FE-TraceTooltip-001** P1 — usage `<TraceTooltip termId="CAPACITE_RTE_TARIF_2026_EUR_PER_MW">` Cockpit Decision/CFO (différenciateur R10 inactif). 30 min.
- **D-Sprint-C7-Capacite-Coefficient-1.2-Source-001** P1 — source CRE/RTE coefficient obligation 1.2 (general-purpose Phase 5.2 #4). Web search RTE. 30 min.
- **D-Sprint-C7-Capacite-Revenue-Refactor-Yaml-001** P2 — refactor `services/capacity/revenue.py` PRIX_MOYEN_MW_AN consomme YAML loader. 1 h.
- **D-Sprint-C7-Capacite-Loader-Refactor-001** P2 — refactor `cost_simulator_2026.py` + `catalog.py` vers `capacite_loader.py` pattern Sprint C-3. 1.5 h.

### RGPD ext (Phase 5.3 audit)

- **D-Sprint-C7-CGU-Referentiel-Central-001** P1 — table `cgu_versions` (id, version, effective_from/to, hash_sha256) vs String(20) libre (general-purpose Phase 5.3 A1). Migration + endpoint admin. 1.5 h.
- ~~**D-Sprint-C7-PATCH-Consentement-Endpoint-001**~~ ✅ **CLÔTURÉE Sprint C-7 Phase 7.3** (2026-05-06, commit `<hash-phase-7-3>`). 2 endpoints PATCH dédiés livrés (`PATCH /api/organisations/{id}/consentement` + `PATCH /api/delivery_points/{id}/consentement-local`) avec validation pydantic stricte cgu_version (CNIL article 7), org-scoping ADR-017, cascade trigger préservé Phase 5.8 G1. Cockpit RGPD UI Sprint C-6+ débloqué. Effort réel ~2 h vs 1 h estimé.
- **D-Sprint-C7-Consent-Helper-Deduplication-001** P2 — factoriser `_resolve_consent_scope(dp, type_)` partagé `get_effective_consent` + `_with_audit` (general-purpose Phase 5.3 A2 + code-reviewer). 30 min.
- ~~**D-Sprint-C7-AuditLog-Wiring-RGPD-Consent-Change-001**~~ ✅ **CLÔTURÉE Sprint C-7 Phase 7.4** (2026-05-06, commit `<hash-phase-7-4>`). Helper `log_consent_change` + `log_consent_changes_batch` ajoutés à `audit_log_service.py` (action `rgpd.consent_change` cohérent dot-snake). Wiring 2 endpoints PATCH Phase 7.3 (org + dp local) automatique. CNIL article 7 "preuve d'origine forte" complète : qui + quand + valeur + CGU + scope. **CLÔTURE PATTERN DOCTRINAL "Déclaration sans enforcement runtime" 5/5 cardinal Phase C+** (PRAGMA + cascade Org + UNIQUE BillAnomaly + DEMO_MODE + RGPD audit_log). Effort réel ~1.5 h vs 1 h estimé.
- **D-Sprint-C7-Consent-TypedDict-001** P2 — `ConsentAuditResult(TypedDict)` retour helper. 15 min.

### Polish + invariants (Phase 5.4 audit)

- **D-Sprint-C7-REGOPS-Weights-Audit-Applicable-SG-001** P1 — SG `REGOPS_WEIGHTS_AUDIT_APPLICABLE` (0.39/0.28/0.17/0.16) protégé YAML (general-purpose Phase 5.4 B2). 20 min.
- **D-Sprint-C7-Accise-SG-Coverage-001** P1 — SG `ACCISE_GAZ_EUR_PER_MWH` + `ACCISE_ELEC_T2_C5_MENAGE_EUR_PER_MWH` (general-purpose Phase 5.4 B1). 15 min.
- **D-Sprint-C7-Weights-Sum-100pct-Invariant-001** P2 — `assert sum(REGOPS_WEIGHTS_DEFAULT.values()) == 1.0` + READINESS sum=100%. 15 min.
- **D-Sprint-C7-FE-TraceTooltip-Coverage-Expansion-001** P1 — couverture FE 6/68 (8.8%) → ≥30 termes exposés (CO2 factors, TURPE, CTA, OPERAT seuils). 2-3 h.
- **D-Sprint-C7-Tracker-Quality-Audit-Script-001** P2 — script `verify_dette_resolved.py` détecte automatiquement dettes déjà résolues mais pas barrées. 1 h.

### Pré-existants Phase C détectés bonus

- **D-Sprint-C7-EnergyInvoice-TVA-Rate-Field-001** P1 — colonne `tva_rate Numeric(5,4)` (bloque R0X TVA futurs). Migration Alembic + tests. 30 min.
- **D-Sprint-C7-Anomaly-SoT-Consumption-Unified-001** P2 — option `use_measured_consumption` cross-check via `consumption_unified_service` (anomaly_detector). 1 h.
- **D-Sprint-C7-VNU-Terminologie-Cleanup-001** P2 — corriger 3 callsites pré-existants "Versement Nucléaire Universel" → "Versement pour Non-Usage" (`demo_seed/orchestrator.py`, `gen_seed_completion.py`, `market_window_detector.py`). 10 min.

**Effort estimé total Sprint C-7 polish** : ~18-22 h (~3 j-h dense).
**Priorités cumul** : 2 P0 + 9 P1 + 12 P2 = 23 nouvelles dettes Sprint C-7.

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
