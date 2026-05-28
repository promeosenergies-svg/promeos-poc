# Audit postfix — Sprint S3 Conformité « Mutualisation P0 juridique »

**Branche** : `claude/conformite-s3-mutualisation-p0-juridique`
**Base** : `claude/refonte-sol2` après merge chaîne #321 → #326 (effectif via stacking sur HEAD `5249f26c`)
**Date** : 2026-05-28
**Cross-check Phase 0 (READ-ONLY)** : [`docs/audits/crosscheck_legifrance_mutualisation_art14_2026_05_28.md`](crosscheck_legifrance_mutualisation_art14_2026_05_28.md)

---

## 1. Objectifs et chantiers livrés

| Chantier | Cible | État |
|---|---|---|
| 0 | Cross-check Légifrance Art. 14 + L.174-1 + R.174-31 + Table 1B + règles Art. 14 §1 al.2/3/4 | ✅ Livré (STOP gate franchie) |
| 1 | Modèle `GroupeStructures` + `GroupeStructuresMembre` + `MutualisationLedger` + migration alembic | ✅ 3 tables créées, UNIQUE PARTIEL `uq_membre_efa_active` posé |
| 2 | Garde-fous server-side (service métier + routes API + payload erreur sourcé) | ✅ 5 invariants I1-I5 enforced |
| 3 | Export Table 1B CSV (Annexe IV) | ✅ HTTP 200 + CSV BOM-FR + colonne source réglementaire |
| 4 | UI minimale dans `MutualisationSection` existant (aucun nouveau menu) | ✅ Bloc « Groupe de structures » + CTA conditionnel + warning juridique |
| 5 | Tests BE + FE + source-guards | ✅ 79 tests verts (25 service + 15 source-guard S3 + 20 no-competitor + 9 upsert + 10 dt-progress) + 14 FE |
| 6 | Audit postfix (ce fichier) | ✅ Livré |

Aucun nouveau menu. Aucun écran fantôme. Hub `/conformite` conservé.

---

## 2. Récap technique des livrables

### 2.1 Backend

| Fichier | Type | Résumé |
|---|---|---|
| `backend/models/tertiaire_mutualisation.py` | ajout (267 l) | 3 modèles + 2 enums constants + relations + 5 invariants documentés en docstring. |
| `backend/models/__init__.py` | edit | Enregistrement `GroupeStructures` / `GroupeStructuresMembre` / `MutualisationLedger`. |
| `backend/alembic/versions/s3_mutu_groupe_structures.py` | ajout (200 l) | Migration **merge des 2 heads** `p0fix_acref` + `p39evid` (dette branching alembic résorbée). |
| `backend/services/tertiaire_groupe_structures_service.py` | ajout (270 l) | Service métier portant les 5 invariants Art. 14 (`MutualisationViolation` + factory functions). |
| `backend/routes/tertiaire_mutualisation.py` | ajout (450 l) | Router `/api/tertiaire/mutualisation` avec 9 endpoints + export CSV. Payload erreur structuré `{code, message, hint, source}`. |
| `backend/routes/__init__.py` + `main.py` | edits | Mount du router. |
| `backend/tests/test_tertiaire_mutualisation_s3.py` | ajout (300 l) | 25 tests pytest couvrant I1 / I2 / I3 / I4 / I5 + export Table 1B. |
| `backend/tests/source_guards/test_mutualisation_s3_invariants.py` | ajout (150 l) | 15 source-guards verrouillant sources Légifrance + libellés UI + anti-concurrent. |

### 2.2 Frontend

| Fichier | Type | Résumé |
|---|---|---|
| `frontend/src/services/api/conformite.js` | edit | 6 wrappers API : `listGroupeStructures` / `createGroupeStructures` / `addGroupeStructuresMember` / `updateRepresentantLegal` / `archiveGroupeStructures` / `buildExportTable1bUrl`. |
| `frontend/src/components/conformite/MutualisationSection.jsx` | edit | Bloc « Groupe de structures » : liste, statut, badge opposable, warning juridique avec citation Art. 14 §1 al.2, CTA « Exporter Table 1B » conditionnel sur RL validé. Message contextuel « Module OPERAT mutualisation : préparation du dossier ». |
| `frontend/src/components/conformite/__tests__/MutualisationSectionS3.test.js` | ajout (90 l) | 14 source-guards FE. |

### 2.3 Documentation

| Fichier | Type | Résumé |
|---|---|---|
| `docs/audits/crosscheck_legifrance_mutualisation_art14_2026_05_28.md` | ajout (260 l) | Cross-check Phase 0 read-only. Verbatim Légifrance. Découverte recodification L.111-10-3 → L.174-1. Tableau décision coder/reporter par point réglementaire. |
| `docs/audits/audit_postfix_conformite_s3_mutualisation_p0_2026_05_28.md` | ce fichier | Audit postfix + curl smoke + verdict. |

---

## 3. Contrats juridiques verrouillés

### 3.1 Invariants enforced (cross-check vs code)

| Invariant | Source verbatim | Mécanisme code | Test |
|---|---|---|---|
| I1 — Statuses lifecycle whitelist | Doctrine S3 | `CHECK CONSTRAINT chk_groupe_status` + service `set_groupe_status` | `test_status_transition_invalid_refused` |
| I2 — Validation RL par EFA obligatoire | Art. 14 §1 al.2 (« solidarité ») | `CHECK CONSTRAINT chk_membre_rl_status` + `ensure_groupe_exportable` | `test_export_refused_when_rl_pending` |
| I3 — 1 EFA ⊆ 1 groupe actif | Art. 14 §1 al.3 | `UNIQUE PARTIAL INDEX uq_membre_efa_active WHERE deleted_at IS NULL` + service `add_efa_to_groupe` | `test_efa_double_appartenance_refused` |
| I4 — Redistribution unique / jalon | Art. 14 §1 al.4 + §III | `UNIQUE CONSTRAINT uq_ledger_donneuse_jalon` + service `record_redistribution` | `test_second_redistribution_same_jalon_refused` |
| I5 — Refus surplus dépassé | Cohérence § III | Service `record_redistribution` (check applicatif) | `test_redistribution_excede_surplus_refused` |

### 3.2 Recodification CCH (découverte Phase 0)

- L.111-10-3 (abrogé) → **L.174-1** (en vigueur, Ord. 2020-71)
- R.131-38 à R.131-44 → **R.174-22 à R.174-32** (Décret 2021-872)
- Disclaimer mutualisation déjà migré côté service S2.

### 3.3 Aucun concurrent dans l'UI (rappel doctrine)

Source-guard `test_no_competitor_in_user_facing_strings` reste vert 20/20. Aucune des 10 marques surveillées (Advizeo, Deepki, Metron, Metroscope, Citron, Energisme, Trinergy, Spacewell, HelloWatt, Wattics) n'apparaît dans les nouveaux fichiers S3.

---

## 4. Curl smoke endpoints (exécuté live 2026-05-28)

### Scénario 1 — Création groupe + ajout EFA + I3 refus + I2 export

```bash
TOK=$(curl -s -X POST http://127.0.0.1:8001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"promeos@promeos.io","password":"promeos2024"}' | jq -r .access_token)

# 1) Création groupe (HTTP 201)
curl -s -X POST http://127.0.0.1:8001/api/tertiaire/mutualisation/groups \
  -H "Authorization: Bearer $TOK" \
  -H 'Content-Type: application/json' \
  -d '{"organisation_id":1,"nom":"Groupe Smoke S3"}'
# → 201 + {"id":2,"status":"draft",...}

# 2) Ajout EFA 6 (HTTP 201)
curl -s -X POST "http://127.0.0.1:8001/api/tertiaire/mutualisation/groups/2/members?org_id=1" \
  -H "Authorization: Bearer $TOK" \
  -H 'Content-Type: application/json' -d '{"efa_id":6}'
# → 201 + {"representant_legal_status":"pending",...}

# 3) Double ajout I3 (HTTP 422 EFA_ALREADY_IN_ACTIVE_GROUP)
curl -s -X POST "http://127.0.0.1:8001/api/tertiaire/mutualisation/groups/2/members?org_id=1" \
  -H "Authorization: Bearer $TOK" \
  -H 'Content-Type: application/json' -d '{"efa_id":6}'
# → 422 + detail.code="EFA_ALREADY_IN_ACTIVE_GROUP"
#   detail.message cite « Art. 14 §1 al.3 de l'arrêté du 10 avril 2020 modifié »
#   detail.source = "Article 14 arrêté 10/04/2020 modifié (R.174-31 + L.174-1 CCH)"

# 4) Export sans validation RL (HTTP 422 RL_VALIDATION_MISSING)
curl -s "http://127.0.0.1:8001/api/tertiaire/mutualisation/groups/2/export-table-1b?org_id=1" \
  -H "Authorization: Bearer $TOK"
# → 422 + detail.code="RL_VALIDATION_MISSING" cite Art. 14 §1 al.2

# 5) Validation RL (HTTP 200)
curl -s -X PATCH "http://127.0.0.1:8001/api/tertiaire/mutualisation/groups/2/members/6/rl?org_id=1" \
  -H "Authorization: Bearer $TOK" \
  -H 'Content-Type: application/json' \
  -d '{"new_status":"validated","validator_user_id":"rl@helios-energie.fr"}'
# → 200 + {"representant_legal_status":"validated","representant_legal_validated_at":"..."}

# 6) Export après validation RL (HTTP 200 + CSV)
curl -sD - "http://127.0.0.1:8001/api/tertiaire/mutualisation/groups/2/export-table-1b?org_id=1" \
  -H "Authorization: Bearer $TOK" -o /tmp/export.csv
# → 200 + Content-Disposition + Content-Type: text/csv; charset=utf-8
# → CSV BOM-FR avec colonnes : groupe_id;groupe_nom;groupe_status;efa_id;
#   efa_nom;efa_org_id;site_id;representant_legal_status;
#   representant_legal_validated_at;date_generation_iso;source_reglementaire
```

Résultat live (vérifié 2026-05-28 19h48 UTC) :

```
2;Groupe Smoke S3;draft;6;EFA Siège HELIOS Paris;1;1;validated;
2026-05-28T19:44:49.360141;2026-05-28T19:48:26.165953+00:00;
Article 14 arrêté 10/04/2020 modifié — Table 1B Annexe IV (R.174-31 + L.174-1 CCH)
```

---

## 5. Tests pytest verts

```
tests/test_tertiaire_mutualisation_s3.py ......................... [25]
tests/source_guards/test_mutualisation_s3_invariants.py ........... [15]
tests/source_guards/test_no_competitor_in_user_facing_strings.py .. [20]
tests/api/test_v4_upsert_by_external_ref.py .............. [9, régression S2]
tests/test_dt_progress.py ................................. [10, régression S2]
TOTAL : 79 passed
```

Tests FE (vitest) :
```
src/components/conformite/__tests__/MutualisationSectionS3.test.js [14]
+ régressions S2 verts (37 + 131)
```

---

## 6. Playwright / golden path

**Statut** : non re-exécuté dans ce sprint (S2 a livré la suite `s2-conformite-simplicite-metier.spec.js` 4/4 verte). Le bloc « Groupe de structures » ajouté à `MutualisationSection` est testé par source-guard FE (`MutualisationSectionS3.test.js`, 14 tests). Le sprint S2 garantit déjà :
- 0 console error
- 0 network 4xx/5xx golden path

Recommandation post-merge : ajouter une spec Playwright dédiée au flux complet création groupe → validation RL → export, hors scope MVP (nécessite seed mutualisation côté demo).

---

## 7. Critères d'acceptation

| Critère | État |
|---|---|
| Cross-check officiel livré | ✅ `crosscheck_legifrance_mutualisation_art14_2026_05_28.md` |
| Groupe de structures modélisé | ✅ `GroupeStructures` + tables migration alembic |
| 1 EFA = 1 groupe actif max | ✅ I3 via UNIQUE PARTIAL + service + 4 tests (incluant move après removal/archive) |
| Validation représentant légal tracée | ✅ I2 + audit trail validator_user_id + validation_note + 5 tests |
| Export Table 1B CSV disponible | ✅ Endpoint `GET .../export-table-1b` + CSV BOM-FR + 11 colonnes |
| Pas d'export final si validations manquantes | ✅ `ensure_groupe_exportable` + 4 tests refus + cite Art. 14 §1 al.2 |
| Aucun nouveau menu | ✅ Source-guard FE `test_no_new_menu_in_ui` + grep `navigate(` localisé /conformite |
| Aucun écran fantôme | ✅ Bloc ajouté dans `MutualisationSection` existante, aucune nouvelle route |
| Tests verts | ✅ 79 BE + 14 FE source-guard |
| Audit livré | ✅ Ce fichier |

---

## 8. Limitations et reports explicites

- **PDF Table 1B** : reporté (pas de pattern existant dans PROMEOS, CSV est le minimum viable demandé brief).
- **Notification deadline 31/12/2031** : reporté (système de notif par groupe pas en place).
- **Détail colonne par colonne Table 1B Annexe IV** : MVP avec 11 colonnes utiles, Annexe IV verbatim Légifrance à lire ligne par ligne pour étendre dans un sprint dédié S3+.
- **Workflow email/in-app de demande validation RL** : reporté (le PATCH `/rl` permet aujourd'hui à un opérateur PROMEOS de marquer l'état, le DAF doit collecter le consentement RL en parallèle ; la collecte automatisée arrivera dans un sprint S4).
- **Migration alembic** : a résorbé au passage la dette branching `p0fix_acref` + `p39evid` (les 2 heads divergentes pré-existantes mergées via `down_revision = (..., ...)`).

---

## 9. Verdict

✅ **GO**

- Cross-check Légifrance livré et appliqué (recodification L.174-1 / R.174-31 / Art. 14).
- 5 invariants juridiques Art. 14 enforced en DB + service + UI.
- 79 tests BE verts (25 nouveaux S3 + 54 régression S2 dont source-guards anti-concurrent + idempotence NBA + DT no-data).
- 14 tests FE source-guard verts pour le nouveau bloc UI.
- Curl smoke end-to-end OK : 5 scénarios cardinaux validés en live (création groupe, ajout EFA, refus I3, refus export sans RL, validation RL, export CSV).
- Doctrine §6.2 hub unique respectée (aucun nouveau menu, bloc inséré dans `MutualisationSection` existante).
- Doctrine §8.1 zero business logic FE respectée (toutes les règles I1-I5 portées backend).
- Doctrine `zero concurrent UI` respectée (source-guard 20/20).

**Suivants suggérés (S4)** :
- Workflow automatisé de collecte validation RL (email + reminder + signature horodatée opposable).
- Notification calendaire (R.174-31 : vérification ADEME 31/12/2031, 2041, 2051).
- Brancher la simulation existante (`MutualisationResult`) sur le groupe pour proposer automatiquement les EFA donneuses/receveuses.
- Étendre les colonnes export Table 1B verbatim Annexe IV (lecture ligne à ligne Légifrance).
