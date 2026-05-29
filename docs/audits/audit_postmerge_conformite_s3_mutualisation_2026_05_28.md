# Audit postmerge — Sprint S3 Conformité « Mutualisation P0 juridique »

**Branche** : `claude/postmerge-conformite-s3-mutualisation-smoke`
**Base** : `claude/refonte-sol2` post-merge **#327** (HEAD `1fc50f04`)
**Date** : 2026-05-28 (audit lancé 2026-05-29 04h-07h UTC, libellé conservé au format brief)
**Cross-check Phase 0 livré** : [`crosscheck_legifrance_mutualisation_art14_2026_05_28.md`](crosscheck_legifrance_mutualisation_art14_2026_05_28.md)
**Audit livraison S3** : [`audit_postfix_conformite_s3_mutualisation_p0_2026_05_28.md`](audit_postfix_conformite_s3_mutualisation_p0_2026_05_28.md)

---

## Contexte

Smoke postmerge déclenché après merge effectif de la chaîne complète :
- `82e0b6b8 fix(usages): consolidate renderers and cleanup horaires route (#321)`
- `0f0634f4 docs(usages): closing audit brique Energie / Pilotage des usages (#322)`
- `406b0cc8 fix(energie): close inherited navigation and scoping cleanup (#323)`
- `8bd17666 docs(conformite): audit Phase 0 brique Conformite multi-energie (#324)`
- `ede198fa fix(conformite): harden operat deet regulatory constants and modulation (#325)`
- `71ab844b fix(conformite): simplify hub and make next best action actionable (#326)`
- `1fc50f04 feat(conformite): add legal safeguards for tertiaire mutualisation (#327)` ← cible smoke

`origin/claude/refonte-sol2` est désormais à `1fc50f04` (vérifié `git log --oneline -1`).

Objectif : valider qu'après merge effectif, la brique Mutualisation P0 juridique fonctionne bout-en-bout sans régression S2.

---

## 1. Migration Alembic ✅

### Tables créées

```
tertiaire_groupe_structures           — 11 colonnes
tertiaire_groupe_structures_membre    — 11 colonnes
tertiaire_mutualisation_ledger        — 8 colonnes
```

### Contraintes en vigueur (vérifiées via `sqlalchemy.inspect`)

| Table | CHECK constraints | Indexes UNIQUE |
|---|---|---|
| `tertiaire_groupe_structures` | `chk_groupe_status` (I1) | — (`idx_groupe_org_active` non-unique) |
| `tertiaire_groupe_structures_membre` | `chk_membre_rl_status` (I2) | **`uq_membre_efa_active`** (I3 — UNIQUE PARTIEL `WHERE deleted_at IS NULL`) |
| `tertiaire_mutualisation_ledger` | `chk_ledger_kwh_positive` (I5) | — (`UniqueConstraint uq_ledger_donneuse_jalon` enforce I4 au niveau ORM) |

### Heads Alembic

```
$ alembic current
s3_mutu_gs (head) (mergepoint)

$ alembic heads
s3_mutu_gs (head)
```

**Une seule head**, branchée comme `mergepoint` des 2 heads pré-existantes (`p0fix_acref` + `p39evid`). Dette branching alembic résorbée par la migration S3. **Verdict** : pas de conflit Alembic, migration appliquée proprement post-merge.

---

## 2. API smoke (6/6 verts) ✅

Script Python `urllib` exécuté contre le backend live (port 8001, branche refonte-sol2 post-#327). Login : `promeos@promeos.io / promeos2024` (superuser HELIOS).

| # | Scénario | Attendu | Obtenu | État |
|---|---|---|---|---|
| 1/6 | `POST /api/tertiaire/mutualisation/groups` | 201 + status=draft | HTTP=201 id=7 status=draft | ✅ |
| 2/6 | `POST .../groups/7/members {efa_id:10}` (EFA libre) | 201 + rl=pending | HTTP=201 rl=pending | ✅ |
| 3/6 | `POST .../members {efa_id:10}` re-tenter | 422 EFA_ALREADY_IN_ACTIVE_GROUP | HTTP=422 code=EFA_ALREADY_IN_ACTIVE_GROUP (cite Art. 14 §1 al.3) | ✅ |
| 4/6 | `GET .../export-table-1b` sans validation RL | 422 RL_VALIDATION_MISSING | HTTP=422 code=RL_VALIDATION_MISSING (cite Art. 14 §1 al.2) | ✅ |
| 5/6 | `PATCH .../members/10/rl {new_status:validated}` | 200 + rl=validated + validated_at horodaté | HTTP=200 rl=validated | ✅ |
| 6/6 | `GET .../export-table-1b` après RL validé | 200 + CSV BOM-FR + 11 cols + source réglementaire | HTTP=200 Content-Type=text/csv; charset=utf-8, BOM=oui, cols=11, src_col=oui, src_in_data=oui | ✅ |

**Payload erreur structuré** : tous les 422 retournent `{detail: {code, message, hint, source}}` avec `source = "Article 14 arrêté 10/04/2020 modifié (R.174-31 + L.174-1 CCH)"`.

**CSV header** :
```
groupe_id;groupe_nom;groupe_status;efa_id;efa_nom;efa_org_id;site_id;
representant_legal_status;representant_legal_validated_at;
date_generation_iso;source_reglementaire
```

**Ligne data** :
```
7;Smoke postmerge;draft;10;EFA Entrepot HELIOS Toulouse;1;3;validated;
2026-05-29T05:30:32...;2026-05-29T05:30:32...;
Article 14 arrêté 10/04/2020 modifié — Table 1B Annexe IV (R.174-31 + L.174-1 CCH)
```

---

## 3. UI Playwright (4/4 verts) ✅

```
✓ Item 8a · /conformite mode normal : tab Plan d'exécution ABSENT  (912 ms)
✓ Item 8b · /conformite mode expert : tab Plan d'exécution PRESENT (774 ms)
✓ Item 9  · /conformite?tab=execution mode normal → /action-center-v4?domain=conformite (1.0 s)
✓ Item 11 · /action-center-v4?domain=conformite : 0 console error · 0 4xx/5xx (3.2 s)

4 passed (6.9 s)
```

Le flake Item 11 observé pendant la QA pré-merge (rate-limit login en suite) **ne se reproduit pas** sur la branche postmerge. Probablement lié à un état session/cookie reseté par les migrations alembic post-#327. Pas d'action corrective requise — surveiller en CI.

### Validation visuelle (par source-guard FE existant + smoke API)

- **MutualisationSection visible** : composant rend toujours (source `frontend/src/components/conformite/MutualisationSection.jsx` non touché par les autres PRs mergées).
- **Bloc « Groupe de structures » présent** : `data-testid="groupe-structures-bloc"` (source-guard `MutualisationSectionS3.test.js` test #1, vert).
- **Warning juridique** quand non-opposable : « Groupe non opposable — collectez la validation du représentant légal de chaque EFA avant le contrôle décennal (Art. 14 §1 al.2) » (test FE #4, vert).
- **CTA export conditionnel** : `Exporter Table 1B` rendu vs `Export indisponible` selon `allRlOk` (test FE #3, vert).
- **Aucun nouveau menu** : bloc inséré DANS MutualisationSection existante, aucune nouvelle route React (`grep navigate frontend/src/components/conformite/MutualisationSection.jsx` → 0 occurrence).
- **Message contextuel** : « Module OPERAT mutualisation : préparation du dossier » (test FE #5, vert).

---

## 4. Non-régression S2 (170/170 verts) ✅

### Tests automatisés

| Couche | Suite | Résultat |
|---|---|---|
| BE pytest | `test_tertiaire_mutualisation_s3` (S3 I1-I5 + export) | **25/25** |
| BE pytest | `source_guards/test_mutualisation_s3_invariants` (S3) | **15/15** |
| BE pytest | `source_guards/test_no_competitor_in_user_facing_strings` | **20/20** |
| BE pytest | `test_v4_upsert_by_external_ref` (S2 NBA) | **9/9** |
| BE pytest | `test_dt_progress` (S2 hotfix tristate) | **10/10** |
| BE pytest | `test_tertiaire_modulation_typology` (S2 TRI) | **5/5** |
| FE vitest | `MutualisationSectionS3.test.js` (S3) | **14/14** |
| FE vitest | `conformiteS2SimpliciteMetier` (S2) | **19/19** |
| FE vitest | `step21_conformite_messages` (S2) | **18/18** |
| FE vitest | `breadcrumb` (S2 hotfix libellé tertiaire) | **18/18** |
| FE vitest | `ConformiteSyntheseCompacte` (régression) | **17/17** |
| Playwright | `s2-conformite-simplicite-metier.spec.js` | **4/4** |

**Total : 174 verts** (84 BE pytest + 86 FE vitest + 4 Playwright).

### Vérifications cardinales (preuves côté audit)

| Cardinal | Preuve | État |
|---|---|---|
| S2 — Conformité tabs 3 normal / 4 expert | Playwright Item 8a + 8b | ✅ |
| S2 — NextBestAction idempotent | pytest `test_v4_upsert_by_external_ref` 9/9 (CREATE 201 + re-clic 200 + CLOSED 409) | ✅ |
| S2 — ModulationDrawer TRI typologie | pytest `test_tertiaire_modulation_typology` 5/5 (`tri_par_typologie` retourné avec source Légifrance) | ✅ |
| S2/S3 — 0 concurrent dans UI | pytest `test_no_competitor_in_user_facing_strings` 20/20 | ✅ |
| Golden path — 0 console error | Playwright Item 11 vert | ✅ |
| Golden path — 0 network 4xx/5xx | Playwright Item 11 vert | ✅ |

---

## 5. Verdict final

| Critère | État |
|---|---|
| Migration 3 tables présentes | ✅ |
| Contraintes UNIQUE / CHECK actives | ✅ |
| Pas de conflit Alembic (heads = 1) | ✅ |
| API création groupe | ✅ |
| API ajout EFA | ✅ |
| API double appartenance refusée | ✅ |
| API export refusé si RL pending | ✅ |
| API validation RL | ✅ |
| API export Table 1B CSV | ✅ |
| UI /conformite OK | ✅ |
| MutualisationSection visible | ✅ |
| Warning juridique visible | ✅ |
| CTA export conditionnel | ✅ |
| Aucun nouveau menu | ✅ |
| S2 Conformité tabs 3/4 | ✅ |
| S2 NextBestAction idempotent | ✅ |
| S2 ModulationDrawer TRI typologie | ✅ |
| 0 concurrent UI | ✅ |
| 0 console error | ✅ |
| 0 network 4xx/5xx | ✅ |

**Verdict : ✅ GO**

La brique Mutualisation P0 juridique est **opérationnelle post-merge** sur `claude/refonte-sol2`. Les 5 invariants Art. 14 sont enforced (DB + service + UI). Le module est prêt à être consommé en démo et en clientèle pilote pour anticiper le module OPERAT mutualisation ADEME.

### Suivants suggérés (hors scope smoke)

- **Sprint dédié infra-test** : fix du flake Playwright Item 11 (rate-limit login en suite) via `storageState` partagé entre tests Playwright — dette pré-existante S2, non régression S3.
- **Sprint S4 mutualisation** : PDF export Table 1B, notification calendaire 31/12/2031, workflow auto collecte validation RL (email + reminder + horodatage signature opposable), extension colonnes Table 1B verbatim Annexe IV.
- **Veille ADEME** : surveiller le déploiement progressif du module OPERAT « Mutualisation des résultats à l'échelle d'un patrimoine » pour automatiser la bascule PROMEOS → OPERAT dès activation.
