# Audit postfix — Sprint S4 Conformité « Mutualisation advanced workflow »

**Branche** : `claude/conformite-s4-mutualisation-advanced-workflow`
**Base** : `claude/refonte-sol2` (HEAD `9640b4c1` post #329 infra Playwright)
**Date** : 2026-05-29
**Phase 0 cross-check** : aucune nouvelle référence Légifrance nécessaire — s'appuie sur le cross-check S3 (`crosscheck_legifrance_mutualisation_art14_2026_05_28.md`) qui a déjà confirmé R.174-31 (31/12/2031/2041/2051) + Article 14 + L.174-1.

---

## 1. Phase 0 audit READ-ONLY (synthèse)

| Question | Réponse retenue |
|---|---|
| Le PDF peut-il réutiliser un moteur existant ? | **Oui** — `services/v4/pdf_export_service.py::_render_with_reportlab()` utilise reportlab + SimpleDocTemplate. Pattern + tokens couleur Sol réutilisés. |
| Où stocker la preuve de validation représentant légal ? | Champ `validation_token_hash` (SHA256 hex, 64 chars) ajouté à `tertiaire_groupe_structures_membre` via migration alembic `s4_mutu_tok`. Calculé applicativement sur `(group_id, efa_id, validator_user_id, validated_at_iso)`. |
| Quel statut afficher côté UI ? | 3 niveaux : groupe (`draft/pending_validation/validated/archived`), RL par EFA (`pending/validated/rejected`), opposabilité globale (oui/non + raison FR). |
| Quels champs Table 1B manquent encore ? | MVP 11 colonnes S3 conservé. PDF ajoute hash SHA256 d'opposabilité. Extension verbatim Annexe IV reportée S5 (lecture ligne par ligne Légifrance dédiée). |
| Comment éviter un workflow trop lourd ? | **Réutiliser** : NBA upsert V4 (S2) pour la création d'action « Demander validation RL » ; pas de système notif backend dédié ; bandeau échéance read-only dans bloc existant. |

---

## 2. Livrables techniques

### 2.1 Backend

| Fichier | Type | Résumé |
|---|---|---|
| `backend/models/tertiaire_mutualisation.py` | edit | Ajout `validation_token_hash: Column(String(64), nullable=True)` à `GroupeStructuresMembre`. |
| `backend/alembic/versions/s4_mutu_validation_token.py` | nouveau | Migration additive `s3_mutu_gs → s4_mutu_tok`. |
| `backend/services/tertiaire_groupe_structures_service.py` | edit | `set_representant_legal_status` calcule SHA256(`group_id\|efa_id\|validator_user_id\|validated_at`) au PASS validated. Reset hash si rejected. |
| `backend/services/tertiaire_mutualisation_pdf.py` | nouveau, 250 l | `generate_table_1b_pdf(db, groupe) → (pdf_bytes, export_hash)` ; reportlab + tokens couleur Sol ; PDF 1 page A4 avec composition + statut RL + source réglementaire + hash. |
| `backend/routes/tertiaire_mutualisation.py` | edit | 3 endpoints S4 : `GET .../export-table-1b.pdf` (header `X-Export-Hash`) · `POST .../members/{efa_id}/request-validation` (délègue upsert NBA V4 idempotent par `external_ref=conformite:rl_validation:{efa_id}:{group_id}`) · `GET .../deadline-status` (R.174-31 31/12/2031/2041/2051). |

### 2.2 Frontend

| Fichier | Type | Résumé |
|---|---|---|
| `frontend/src/services/api/conformite.js` | edit | 3 wrappers ajoutés : `buildExportTable1bPdfUrl(groupId, orgId)`, `requestRlValidation(groupId, efaId, orgId)`, `getMutualisationDeadlineStatus(groupId, orgId)`. |
| `frontend/src/components/conformite/MutualisationSection.jsx` | edit | Composant interne `GroupeDeadlineBanner` (bandeau R.174-31 avec icône CalendarClock) ; bouton PDF Table 1B à côté du CSV (les 2 conditionnels sur `allRlOk`) ; CTA `Demander validation RL pour l'EFA #X` par EFA pending (gère 409 RL_ALREADY_VALIDATED + 409 EXTERNAL_REF_CLOSED). |

### 2.3 Tests

| Fichier | Type | Résumé |
|---|---|---|
| `backend/tests/test_tertiaire_mutualisation_s4.py` | nouveau | 9 tests : `validation_token_hash` set/reset/uniqueness, `compute_export_hash` déterministe, `generate_table_1b_pdf` magic bytes + refus si vide + hash change si composition change. |
| `frontend/src/components/conformite/__tests__/MutualisationSectionS4.test.js` | nouveau | 14 source-guards : PDF (3) + bandeau échéance (4) + CTA demande RL (4) + wrappers API (3) + anti-concurrent (1). |
| `frontend/src/components/conformite/__tests__/MutualisationSectionS3.test.js` | edit | Test `expose un bouton « Exporter Table 1B »` mis à jour (S4 déclinaison CSV + PDF). |
| `backend/tests/source_guards/test_mutualisation_s3_invariants.py` | edit | Idem source-guard BE mis à jour. |

---

## 3. Contrats juridiques respectés

### 3.1 Art. 14 §1 al.1-4 (cross-check S3 conservé)

- **I1** Statuts whitelist : inchangé S3.
- **I2** Validation RL obligatoire avant export opposable : **renforcé S4** — un `validation_token_hash` SHA256 est désormais persisté, recalculable par un contrôleur ADEME pour vérifier l'absence d'altération.
- **I3** 1 EFA = 1 groupe actif max : inchangé S3.
- **I4** Redistribution unique par jalon : inchangé S3.
- **I5** Refus si redistribution > surplus : inchangé S3.

### 3.2 R.174-31 CCH

Le service `deadline-status` matérialise les 3 deadlines (`31/12/2031`, `31/12/2041`, `31/12/2051`) confirmées Phase 0 S3 + génère une `action_recommandee_fr` priorisée (4 cas FR clairs).

### 3.3 Zéro concurrent UI

Source-guards BE + FE restent verts (20/20 + 14/14). Aucune nouvelle string introduite par S4 ne mentionne un éditeur tiers.

### 3.4 Doctrine §6.2 hub unique

- Aucun nouveau menu.
- Aucune nouvelle route React.
- 3 nouveaux endpoints BE tous sous `/api/tertiaire/mutualisation/...`.
- UI insérée dans `MutualisationSection` existante (composant interne `GroupeDeadlineBanner` + boutons inline).

---

## 4. Curl smoke endpoints S4 (live 2026-05-29 07:25 UTC)

```
=== 1/3 deadline-status (pas opposable) ===
  HTTP=200 opposable=False jalon_next=2030 days_remaining=2042
  action: Collectez 1 validation(s) représentant légal manquante(s) (Art. 14 §1 al.2)…
  ✅

=== 2/3 request-validation (création action V4 idempotente) ===
  HTTP=201 status=created external_ref=conformite:rl_validation:6:8
  Re-tenter HTTP=200 status=existing ✅ (idempotence)

=== 3/3 Validation RL puis PDF export ===
  validation RL HTTP=200 rl=validated
  validation_token_hash=c257589f3419b46083cade4addb9ade7… (len=64, SHA256 hex)
  PDF HTTP=200 ct=application/pdf
  X-Export-Hash=0798ddb56eac1287… (64 chars hex)
  Magic bytes %PDF : oui
  Taille : 3 208 bytes
  ✅

=== Re-deadline post-validation ===
  opposable=True
  action: Groupe opposable — surveillez l'ouverture du module OPERAT mutualisation ADEME.
```

---

## 5. Tests automatisés

| Couche | Suite | Verts |
|---|---|---|
| BE pytest | `test_tertiaire_mutualisation_s4` (S4 nouveau) | **9/9** |
| BE pytest | `test_tertiaire_mutualisation_s3` (régression S3) | **25/25** |
| BE pytest | `source_guards/test_mutualisation_s3_invariants` (S3 mis à jour S4) | **15/15** |
| BE pytest | `source_guards/test_no_competitor_in_user_facing_strings` | **20/20** |
| BE pytest | `test_v4_upsert_by_external_ref` (régression S2) | **9/9** |
| BE pytest | `test_dt_progress` (régression S2) | **10/10** |
| FE vitest | `MutualisationSectionS4.test.js` (S4 nouveau) | **14/14** |
| FE vitest | `MutualisationSectionS3.test.js` (S3 mis à jour S4) | **15/15** |
| FE vitest | `conformiteS2SimpliciteMetier` (régression S2) | **19/19** |
| FE vitest | `step21_conformite_messages` (régression S2) | **18/18** |
| FE vitest | `breadcrumb` (régression S2) | **18/18** |
| Playwright | `golden-paths.spec.js` (4 routes + setup) | **5/5** |
| Playwright | `s2-conformite-simplicite-metier.spec.js` | **4/4** |

**Total : 88 BE pytest + 84 FE vitest + 9 Playwright = 181 verts**. 0 régression sur S2/S3/infra Playwright.

---

## 6. Critères d'acceptation

| Critère | État |
|---|---|
| 0 console error | ✅ (Playwright golden path Item 11) |
| 0 network 4xx/5xx golden path | ✅ |
| Aucun nouveau menu | ✅ (composant inséré dans `MutualisationSection` existante) |
| Export CSV toujours OK | ✅ (régression S3 verte, endpoint inchangé) |
| PDF OK ou 501 FR documenté | ✅ **PDF OK** — endpoint actif, magic bytes vérifiés, hash SHA256 retourné en header `X-Export-Hash` |
| Validation RL traçable | ✅ (`validation_token_hash` + `validator_user_id` + `representant_legal_validated_at` persistés ; 3 tests S4) |
| Audit livré | ✅ (ce fichier) |

---

## 7. Limitations connues + reports

- **Email Brevo** : non branché sur `request-validation` côté S4. Le canal canonique est l'action Centre d'Action V4 (idempotente via NBA upsert S2). Branche email = S5+ via `services/email_provider.py::BrevoProvider`.
- **Extension colonnes Table 1B** : MVP 11 colonnes inchangé. Lecture verbatim Annexe IV de l'arrêté à faire en sprint dédié si demandé.
- **Notification calendaire active** : pas de système de push/email automatique sur deadline 31/12/2031. L'endpoint `deadline-status` renvoie l'info que l'UI affiche — l'utilisateur doit la consulter activement.
- **Hash signature serveur** : aujourd'hui déterministe (SHA256 du payload). Pour un vrai « non-répudiation », il faudrait HMAC avec clé serveur ou signature X.509. Considéré hors scope MVP S4 — la reproductibilité par le contrôleur est l'objectif minimal viable.

---

## 8. Verdict

✅ **GO**

- 3 endpoints S4 fonctionnels (PDF, request-validation idempotent, deadline-status).
- 5 invariants juridiques S3 conservés + I2 renforcé avec hash opposable.
- 181 tests verts, 0 régression S2/S3/infra.
- Aucun changement UX cassant (composant existant enrichi, pas de nouvelle page).
- Doctrine respectée : hub unique, zéro concurrent UI, sources Légifrance verbatim, vocabulaire FR.

**Suite suggérée S5+** :
- Branche email Brevo sur `request-validation` (envoi réel à l'adresse RL).
- Extension Table 1B verbatim Annexe IV (sprint Légifrance dédié).
- Notification active 30/60/90 jours avant échéance.
- Signature HMAC du hash export pour non-répudiation forte.
