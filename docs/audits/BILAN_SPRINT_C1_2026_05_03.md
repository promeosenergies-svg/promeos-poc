# Bilan Sprint C-1 — Doctrine + OPERAT cœur

**Date livraison** : 2026-05-03
**Branche** : `claude/refonte-sol2`
**Audit Phase B référence** : `docs/audits/AUDIT_PATRIMOINE_PHASE_B_2026_05_03.md`
**Matrice cible** : `docs/produit/patrimoine_parametrage_requis_v1.md`

---

## Synthèse

| Phase | Description | Effort réel | Statut | Tests ajoutés | Commit hash |
|---|---|---|---|---|---|
| Phase 0 | Diagnostic état T0 (read-only) | <1 j-h | ✅ | — | — |
| Phase A.0 | Co-commit matrice v1 + audit Phase B | <1 j-h | ✅ | — | `ca231396` |
| Phase 1 | Doctrine `CO2_FACTOR_GNL_KGCO2_PER_KWH=0.238` | <1 j-h | ✅ | 4 | `2e2148c2` |
| Phase 2 | Réparation workflow CI source_guards + hook husky | 1 j-h | ✅ | 5 | `d9ef3cf5` + `adb5f8a3` |
| Phase 3 | Site +18 OPERAT/APER/EFA fields + 6 enums + migration Alembic | 4 j-h | ✅ | 70 | `4f09221b` |
| Phase 4 | OperatValeursAbsoluesService + endpoint `/api/operat/cabs/{site_id}` | 5 j-h | ✅ | 32 | `7a5364c5` |
| Phase 5 | Compliance score V2 adaptatif (wrapper pattern, API publique inchangée) | 4 j-h | ✅ | 25 | `f97dacdb` |
| Phase 6 | Cascade_recompute_service + endpoint `/api/v1/sites/{id}/cascade-impact` | 3 j-h | ✅ | 25 | `fc1221e7` |
| **Total** | | **~17-18 j-h** | ✅ | **161 nouveaux** | |

---

## GAPS audit Phase B comblés

| GAP | Description | Phase comblée |
|---|---|---|
| ✅ R1 | Compliance score V2 adaptatif (0 → N obligations) | Phase 5 (wrapper pattern) |
| ✅ R2 | OperatValeursAbsoluesService (4 lookups en chaîne) | Phase 4 |
| ✅ R3 | Site OPERAT/APER/EFA fields (18 champs) | Phase 3 |
| ✅ R5 | Workflow CI source_guards réparé | Phase 2 |
| ✅ R6 | cascade_recompute_service | Phase 6 |
| ✅ Bonus B1 | `CO2_FACTOR_GNL_KGCO2_PER_KWH=0.238` (arrêté 01/08/2025) | Phase 1 |

**6 GAPS P0 du sprint comblés. 0 régression introduite finale.**

---

## GAPS restants (Sprints C-2+)

| GAP | Description | Sprint cible |
|---|---|---|
| R4 | site_portefeuille_history (temporalité) | Sprint C-2 |
| R7 | Logique kWh/m² FE Patrimoine.jsx (anti-pattern) | Sprint C-2 |
| R8 | Onboarding 3 parcours bifurqués (Wizard/Expert/Bulk) | Sprint C-5 |
| R9 | audit_log_service dédié (table + middleware) | Sprint C-2 (logs structurés MVP livrés Phase 6) |
| R10 | Tooltip traçabilité réglementaire FE | Sprint C-3 |

---

## Tracker dette technique (11 entrées ouvertes + 1 clôturée)

| ID | Priorité | Sprint cible | Synthèse |
|---|---|---|---|
| D-Enedis-Legacy-001 | 🟡 P2 | post-C-7 | 17 tables Enedis legacy sans modèle SQLAlchemy (autogenerate Alembic flag) |
| D-Phase3-Legacy-Zones-001 | 🟡 P2 | C-2/C-4 | 8 occurrences zones H1a-H3 string littéral dans 3 services legacy (allowlist active) |
| D-EMS-Overlay-Org-Scoping-001 | 🟠 P1 | C-2 | `test_overlay_two_sites` pré-existant rouge — org-scoping fragile route EMS |
| D-Phase4-Fuzzy-Mapping-Annexes-001 | 🟡 P2 | C-6 | Coeff DJU non résolus pour sous-cat Annexe I non listées Annexe II |
| ✅ D-Phase4-Encoding-Reunion-001 | — | — | **CLÔTURÉ** : audit confirme JSON utilise "Reunion" sans accent (normalisation correcte) |
| D-Phase5-DtBacsAssujetti-Volatile-001 | 🟡 P2 | C-6 | dt/bacs_assujetti calculés à la volée, dénormalisation différée |
| D-Phase5-Frontend-NonApplicable-001 | 🟠 P1 | C-2 | FE doit gérer `score=null` + `confidence='non_applicable'` (16 fichiers) |
| D-Phase5-Score-None-Propagation-001 | 🟡 P2 | C-2/C-4 | Audit défensif autres callsites pattern `r.score * weight` |
| D-Phase6-Cascade-EJ-Sites-001 | 🟠 P1 | C-2 | Cascade EJ.conso_3y → audit_sme + multi-sites compliance (perf bulk) |
| D-Phase6-Cascade-Org-Consentements-001 | 🟠 P1 | C-3 | Cascade Org.consentement DataConnect/GRDF → DPs |
| D-Phase6-Cascade-DeliveryPoint-Fta-001 | 🟡 P2 | C-3 | Cascade DP.code_fta → profil + Bill Intelligence |
| D-Phase6-Cascade-Contract-Renewal-001 | 🟡 P2 | C-2/C-5 | Cascade Contract.date_fin_validite → alerte 90j |

**Synthèse** : 11 ouvertes (0 P0 / 4 P1 / 7 P2) — 1 clôturée Phase 5. Toutes tracées avec sprint cible et effort estimé.

---

## Baseline non-régression

| Étape | Tests collected | Δ |
|---|---|---|
| **Pré-Sprint C-1** | **7 202** | — |
| Post-Phase 1 (CO2_GNL) | 7 206 | +4 |
| Post-Phase 2 (source_guards CI) | 7 211 | +5 |
| Post-Phase 3 (Site fields) | 7 281 | +70 |
| Post-Phase 4 (OperatCabs) | 7 313 | +32 |
| Post-Phase 5 (Compliance V2) | 7 338 | +25 |
| **Post-Phase 6 (Cascade)** | **7 363** | **+25** |
| **Total Sprint C-1** | **+161 tests** | **0 régression finale** |

### Anomalies détectées et résolues mid-flight

1. **Phase 3 — Test migration Alembic conftest perturbé** : `conftest.py::_ensure_seeded` autouse module-scoped re-seed la DB et empêche un test exécutif fiable. Solution : test statique parser AST du fichier de migration. Preuve fonctionnelle = exécution manuelle étapes 1-10.
2. **Phase 3 — Autogenerate Alembic 17 drop_table destructifs** : retirés manuellement, backup `.original-autogenerate` conservé local. Tracker D-Enedis-Legacy-001.
3. **Phase 5 — Régression `compute_portfolio_compliance` ligne 377** : `r.score * w` crashait sur sites V2 NON_APPLICABLE (`score=None`). Fix : filtre `scorable_results` avant agrégation. Test `test_navigation_badges::test_returns_200_authenticated` redevenu vert.
4. **Phase 6 — Bug dry-run preview** : `sync_site_unified_score` appelle `db.flush()` qui pollue la session ORM même avec `persist=False`. Fix : encapsulation dans `db.begin_nested()` (SAVEPOINT) + rollback en finally.

### Anomalies pré-existantes identifiées

- `tests/test_ems_overlay.py::test_overlay_two_sites` : déjà rouge sur HEAD `claude/refonte-sol2` pré-Phase 3 (vérifié au stash). Pas une régression Phase 3. Tracée en D-EMS-Overlay-Org-Scoping-001.

---

## Source-guards activés Sprint C-1

| Fichier | Phase | Patterns interdits |
|---|---|---|
| `test_doctrine_co2_constants_completeness.py` | 1 | 3 facteurs CO₂ canoniques + `0.238` hors doctrine/config |
| `test_workflow_ci_active.py` | 2 | Dossier `tests/source_guards/` existe + workflow yaml pointe correct |
| `test_operat_aper_enums_no_string_literal_source_guards.py` | 3 | Zones H1a-H3, DOM, APER taille, modulation motifs en strings (allowlist 4 fichiers) |
| `test_operat_cabs_no_hardcoded_values_source_guards.py` | 4 | CVCi/Cabs/Coeff DJU hardcodés hors service |
| `test_compliance_score_v2_adaptive_source_guards.py` | 5 | Pondération 45/30/25 figée hors V1 legacy + helpers V2 exposés |
| `test_cascade_recompute_no_direct_field_modification_source_guards.py` | 6 | `site.cabs_kwh_m2_an =` ou `site.operat_zone/palier =` hors orchestrateur |

**Total** : 6 nouveaux fichiers source-guards + workflow CI désormais actif (vs cassé silencieusement avant Phase 2).

---

## Architecture livrée Sprint C-1

```
backend/
├── alembic/versions/c8f1246522f9_site_operat_aper_efa_fields_18cols.py  [Phase 3]
├── doctrine/constants.py  [Phase 1 — +CO2_FACTOR_GNL]
├── models/
│   ├── enums.py  [Phase 3 — +6 enums OPERAT/APER]
│   └── site.py  [Phase 3 — +18 colonnes]
├── regops/services/  [Phase 4 — package créé]
│   ├── operat_cabs_service.py  [Phase 4 — 4 lookups en chaîne]
│   └── cascade_recompute_service.py  [Phase 6 — orchestrateur 7 champs]
├── routes/
│   ├── operat.py  [Phase 4 — endpoint /api/operat/cabs/{site_id}]
│   └── cascade.py  [Phase 6 — endpoint /api/v1/sites/{id}/cascade-impact]
├── schemas/
│   ├── patrimoine_crud.py  [Phase 3 — SiteCreate/Update +18 fields Optional]
│   └── patrimoine_schemas.py  [Phase 3 — SiteUpdateRequest +18 fields]
└── services/
    └── compliance_score_service.py  [Phase 5 — wrapper V1/V2 adaptatif]

backend/tests/
├── source_guards/  [Phase 2 — dossier créé + 15 fichiers migrés]
└── test_*.py  [+161 nouveaux tests Sprint C-1]

docs/
├── audits/
│   ├── AUDIT_PATRIMOINE_PHASE_B_2026_05_03.md  [Phase A.0 co-commit]
│   ├── DETTE_TECHNIQUE_TRACKER.md  [Sprint C-1 — 11 entrées + 1 clôturée]
│   └── BILAN_SPRINT_C1_2026_05_03.md  [Ce document]
└── produit/patrimoine_parametrage_requis_v1.md  [Phase A.0 co-commit]

.github/workflows/source_guards.yml  [Phase 2 — pointage corrigé backend/tests/source_guards/]
.husky/pre-commit  [Phase 2 — PATH backend/venv/bin auto-exposé]
```

---

## Décisions archi cardinales validées

| Phase | Décision | Justification |
|---|---|---|
| Phase 3 | Migration Alembic nettoyée des 17 drop_table autogenerate | Préserver tables Enedis legacy (D-Enedis-Legacy-001 reportée audit dédié) |
| Phase 3 | sa.Enum(native_enum=False) sur SQLite | Compat PostgreSQL roadmap sans cassure (CHECK constraint sur SQLite, type ENUM natif sur PG) |
| Phase 3 | Test migration Alembic statique AST + preuve manuelle exécutive | conftest.py autouse perturbe DB pour test exécutif fiable |
| Phase 4 | Normalisation "Réunion" / "Reunion" → "Reunion" (encodage Annexe I JSON) | JSON utilise sans accent (audit D-Phase4-Encoding-Reunion-001 clôturé) |
| Phase 4 | Org-scoping cascade hiérarchique Site → Portefeuille → EJ → Org | Pas de Site.organisation_id direct, jointure obligatoire |
| Phase 5 | Wrapper pattern V2 + V1 deprecated avec env var rollback | API publique inchangée → 0 callsite à migrer + A/B testing snapshots |
| Phase 5 | Calcul à la volée dt_assujetti / bacs_assujetti (Option A) | Évite scope creep migration ; dénormalisation différée Sprint C-6 |
| Phase 5 | Exclusion mutuelle AUDIT_SME ↔ ISO_50001 enforced | Loi DDADUE 2025-391 art. L.233-1 — un seul des deux selon obligation |
| Phase 6 | Architecture mince : délègue à services Phase 4 + 5 | Pas de duplication de logique métier |
| Phase 6 | SAVEPOINT pour dry-run preview | Anti-pollution session ORM lors de db.flush() interne sub-services |
| Phase 6 | Endpoint cascade-impact dry-run only (pas dual mode) | Séparation REST GET=lecture / PATCH=écriture (wiring PATCH = Sprint C-2) |
| Phase 6 | Scope MVP 7 champs (vs 10 prévus) | 5 cascades reportées tracées en dette pour scope OPERAT/compliance Sprint C-1 |

---

## Prochaine étape — Sprint C-2

**Périmètre** : Temporalité + FE cleanup (estimé 14-18 j-h selon plan Phase B).

| Priorité | Sujet | Référence |
|---|---|---|
| P0 | `site_portefeuille_history` (temporalité) | R4 audit Phase B |
| P0 | Frontend gestion `score=null` + `confidence='non_applicable'` | D-Phase5-Frontend-NonApplicable-001 |
| P0 | Retrait calculs `kWh/m²` inline `Patrimoine.jsx` (lignes 828, 1528) | R7 audit Phase B |
| P0 | Audit défensif callsites `r.score * weight` autres | D-Phase5-Score-None-Propagation-001 |
| P0 | Wiring PATCH `/api/sites/{id}` → `cascade_recompute_on_change(persist=True)` | Phase 6 préparation |
| P1 | `audit_log_service` table dédiée (logs structurés MVP livrés Phase 6) | R9 audit Phase B |
| P1 | Investigation `test_overlay_two_sites` org-scoping fragile | D-EMS-Overlay-Org-Scoping-001 |
| P1 | Cascade EJ.consommation_3y → multi-sites bulk | D-Phase6-Cascade-EJ-Sites-001 |
| P1 | Endpoint `/api/v1/sites/{id}/production-ready-status` | Section 9 matrice |
| P2 | Refactor 3 fichiers legacy zones (cee_p6, weather_provider, aper_service) | D-Phase3-Legacy-Zones-001 |
| P2 | Duplications CO2 frontend (`consumption/constants.js`) | R7 audit Phase B |

---

**Fin Sprint C-1** — 6 phases livrées + 8 commits atomiques + 161 tests + 0 régression finale + 11 dettes tracées + 6 GAPS P0 audit Phase B comblés.

🚦 **STOP gate finale Sprint C-1** — attente validation utilisateur avant Sprint C-2.
