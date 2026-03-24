# Plan d'implémentation SF3 — Ingestion R171 + Index (R50/R151)

> **Date** : 2026-03-24
> **Branche source** : `feat/enedis-sge-2-ingestion-cdc` (contient SF1 + SF2)
> **Spec** : [`feature-enedis-sge-3-ingestion-index.md`](feature-enedis-sge-3-ingestion-index.md)
> **Review** : [`feature-enedis-implementation-review.md`](feature-enedis-implementation-review.md)
> **Note** : issue #156 (republication versioning) est traitée indépendamment

---

## Vue d'ensemble

SF3 est découpée en **2 sous-parties** :

```
 SF3-A : Tables + Parsers + Pipeline dispatch (single-file)
     │
     ▼
 SF3-B : Ingestion répertoire + statut RECEIVED
```

---

## SF3-A : Tables + Parsers + Pipeline dispatch

> **Branche** : `feat/enedis-sge-3a-tables-parsers`

### Étape 1 — Analyse XML des vrais fichiers

**Objectif** : Déterminer la structure exacte des XML R171, R50 et R151 pour définir les colonnes de chaque nouvelle table.

**Actions** :
1. Déchiffrer 1 fichier de chaque type avec `decrypt_file()` + les vraies clés `.env` :
   - Un R171 depuis `flux_enedis/C1-C4/`
   - Un R50 depuis `flux_enedis/C5/`
   - Un R151 depuis `flux_enedis/C5/`
2. Documenter chaque élément/attribut XML, leur cardinalité, et les mapper vers des colonnes SQLAlchemy
3. Rédiger un ADR (`docs/specs/adr-sf3-xml-structures.md`) avec le mapping XML → colonnes définitif pour chaque type

**Livrable** : ADR validé avant toute écriture de code.

**Pourquoi cette étape d'abord** : Les colonnes des tables et les dataclasses des parsers dépendent directement de ce que contiennent les XML réels. Coder avant cette analyse reviendrait à deviner.

### Étape 2 — 3 nouvelles tables staging + migrations

**Objectif** : Créer les tables `enedis_flux_mesure_r171`, `enedis_flux_mesure_r50`, `enedis_flux_mesure_r151` avec les colonnes identifiées en Étape 1.

**Fichiers impactés** :
- `data_ingestion/enedis/models.py` — 3 nouveaux modèles + ajout de relationships sur `EnedisFluxFile`
- `database/migrations.py` — import des nouveaux modèles dans `_create_enedis_tables()`
- `scripts/init_database.py` — import des nouveaux modèles

**Décisions d'architecture** :

| Décision | Choix | Rationale |
|----------|-------|-----------|
| 1 table par type de flux (pas de table partagée) | **Oui** | Stocker brut, fidèle au XML. Unification en couche fonctionnelle ultérieure |
| Toutes les valeurs sont des strings | **Oui** | Cohérent avec SF2 — archiver sans manipuler |
| Pas de contrainte unique sur les mesures | **Oui** | Cohérent avec SF2 — republications archivées |
| FK vers `enedis_flux_file` avec CASCADE | **Oui** | Même pattern que R4x — `EnedisFluxFile` reste le registre centralisé |
| `EnedisFluxFile` reste partagé | **Oui** | Table de contrôle centralisée. Colonnes R4x-spécifiques nullable pour non-R4x. `header_raw` JSON garantit la fidélité complète. Viabilité à valider pendant l'implémentation |
| Rename `mesures` → `mesures_r4x` | **Oui** | Clarté. Ajouter `mesures_r171`, `mesures_r50`, `mesures_r151`. Vérifier par grep qu'aucun code externe ne référence `flux_file.mesures` |

**Critères d'acceptation** :
- Les 3 tables sont créées en base (test de création)
- Le cascade delete fonctionne (supprimer un FluxFile → mesures associées supprimées)
- Aucune régression sur les 75 tests SF1+SF2

### Étape 3 — Extraction des helpers XML communs

**Objectif** : Mutualiser `_strip_ns()`, `_find_child()`, `_child_text()` actuellement dans `parsers/r4.py`.

**Fichiers impactés** :
- `parsers/_helpers.py` — nouveau, contient les 3 fonctions
- `parsers/r4.py` — importe depuis `_helpers.py` au lieu de définir localement

**Pourquoi maintenant** : Les 3 nouveaux parsers auront besoin de ces mêmes helpers. Les extraire avant de coder les parsers évite la duplication.

**Critères d'acceptation** :
- `r4.py` utilise les helpers importés
- Tous les tests parser R4x passent sans modification

### Étapes 4, 5, 6 — Parsers R171, R50, R151

> Ces 3 étapes sont **indépendantes** et peuvent être développées en parallèle.

**Objectif** : Un parser par type de flux, suivant le pattern établi par `parse_r4x()` en SF2.

**Un fichier par parser** : `parsers/r171.py`, `parsers/r50.py`, `parsers/r151.py`

**Pattern à suivre** (établi par SF2, voir `parsers/r4.py`) :
- Pure function, pas de classe ABC
- Typed dataclasses pour le résultat (pas de dicts)
- Toutes les valeurs en strings brutes
- Custom exception par parser
- `xml.etree.ElementTree` (stdlib)
- Helpers depuis `_helpers.py`
- Tolérance aux namespaces ERDF/ENEDIS

**Particularités connues** :

| Parser | Particularité |
|--------|---------------|
| R171 | Namespace `ns2` (`http://www.enedis.fr/stm/R171`). Peut contenir **plusieurs PRM** par fichier (`serieMesuresDateesListe` → N `serieMesuresDatees` avec `prmId`), contrairement aux R4x (1 PRM/fichier) |
| R50 | Préfixe `ERDF_` dans les noms de fichier (classification déjà gérée par SF1). Namespace `xmlns:xsi`. Index = valeur cumulée, pas une série temporelle à pas régulier |
| R151 | Similaire au R50 en principe. Structure exacte à confirmer par l'Étape 1 |

**Tests par parser** (fichier dédié par parser ou regroupé R50+R151) :

| Test | Description |
|------|-------------|
| Parsing nominal | XML synthétique → extraction correcte de tous les champs |
| Multiple PRM (R171) | Plusieurs séries → mesures pour chaque PRM |
| Tolérance namespace | Avec et sans namespace → même résultat |
| XML vide (0 mesures) | Structure vide, pas d'exception |
| Champs requis manquants | → ParseError |
| Namespace ERDF (R50/R151) | Préfixe historique → parsing OK |

### Étape 7 — Extension du pipeline dispatch

**Objectif** : `ingest_file()` accepte et traite R171, R50, R151 en plus des R4x.

**Fichier principal** : `pipeline.py`

**Modifications** :

1. **Supprimer le guard R4x-only** (lignes 99-104) qui skip tout non-R4x
2. **Dispatch parsing** : table de correspondance `FluxType → (parser_fn, exception_class)` remplaçant le branchement codé en dur
3. **Dispatch stockage** : une fonction `_store_*` par famille de flux. Le stockage R4x actuel (inline dans `ingest_file()`) est extrait dans `_store_r4x()`. Chaque `_store_*` crée les objets du bon modèle et les bulk-insère
4. **Adaptation header** : pour les flux non-R4x, `header_raw` JSON est toujours alimenté ; les colonnes R4x-spécifiques restent NULL

**Critères d'acceptation** :

| Test | Description |
|------|-------------|
| Pipeline R171 end-to-end | Fixture chiffrée → `ingest_file()` → mesures R171 en base |
| Pipeline R50 end-to-end | Idem avec R50 |
| Pipeline R151 end-to-end | Idem avec R151 |
| Idempotence R171/R50/R151 | Même fichier 2 fois → pas de doublon |
| Fichier corrompu non-R4x | → status ERROR, error_message renseigné |
| 0 mesures valide | → status PARSED, measures_count=0 |
| Non-régression R4x | Tous les tests SF2 pipeline passent sans modification |

---

## SF3-B : Ingestion répertoire + statut RECEIVED

> **Branche** : `feat/enedis-sge-3b-ingest-directory`
> **Base** : SF3-A mergé

### Étape 1 — `ingest_directory()` + statut RECEIVED (#154)

**Objectif** : Traiter un répertoire complet de fichiers flux mixtes en batch.

**Fichier** : `pipeline.py`

**Design** :
- Scan plat par défaut (`*.zip`, non-récursif), avec paramètres optionnels pour récursion et pattern
- Tri par nom de fichier (donne l'ordre chronologique pour les fichiers Enedis car les noms contiennent des timestamps)
- Un fichier en erreur ne bloque pas le reste du batch
- Les fichiers hors-scope sont classifiés et skipped

**Cycle de vie RECEIVED** (issue #154) :
- RECEIVED est implémenté dans `ingest_directory()` uniquement (pas dans `ingest_file()` qui est atomique)
- Phase 1 : scanner le répertoire, enregistrer chaque fichier avec `status=RECEIVED` (un seul commit)
- Phase 2 : traiter chaque fichier RECEIVED via `ingest_file()` → transition vers PARSED/ERROR/SKIPPED
- Un fichier resté en RECEIVED après un crash = anomalie détectable au prochain cycle
- Adapter `ingest_file()` pour traiter un fichier déjà enregistré avec `status=RECEIVED` (au lieu de le skip)

**Valeur de retour** : dict de compteurs `{"received": N, "parsed": N, "skipped": N, "error": N, "already_processed": N}`

**Edge cases** :
- Répertoire vide → compteurs à 0, pas d'erreur
- Uniquement des fichiers hors-scope → `{"skipped": N}`
- Fichiers non-`.zip` → ignorés par le glob
- Fichier RECEIVED stale (crash précédent) → re-traité

### Étape 2 — Tests SF3-B

**Fichier** : `tests/test_pipeline_full.py`

| Test | Description |
|------|-------------|
| Batch mixte | Répertoire avec R4H + R171 + R50 + R151 + R172 → tous traités correctement |
| Idempotence batch | Exécuter 2 fois → 0 nouvelle mesure, tous `already_processed` |
| Résilience | Mix valides + corrompus + hors-scope → pas de crash, counters corrects |
| Répertoire vide | Compteurs à 0, pas d'erreur |
| Tout skipped | Uniquement R172 → `{"skipped": N}` |
| Lifecycle RECEIVED | Après scan : fichiers en RECEIVED. Après processing : PARSED/ERROR/SKIPPED |
| RECEIVED stale | Crash simulé → re-traité au prochain appel |
| Requête cross-flux | Après ingestion tous types, requête par PRM sur les 4 tables de mesures |

**Non-régression finale** : `pytest backend/data_ingestion/ -x -v` + `pytest backend/tests/ -x`

---

## Séquence de PRs recommandée

```
PR 1  — Étape 1 : ADR XML structures (doc only, pas de code)
PR 2  — Étapes 2+3 : tables + migrations + extraction helpers
PR 3  — Étape 4 : parser R171 + tests          ┐
PR 4  — Étape 5 : parser R50 + tests           ├─ parallélisables
PR 5  — Étape 6 : parser R151 + tests          ┘
PR 6  — Étape 7 : pipeline dispatch + tests
PR 7  — SF3-B : ingest_directory() + RECEIVED + tests
```

- PR 3, 4, 5 sont indépendants et parallélisables
- PR 6 dépend de PR 3+4+5 (les parsers doivent exister)
- PR 7 dépend de PR 6 (pipeline dispatch doit être en place)
- Chaque PR doit passer `pytest backend/data_ingestion/ -x -v` + `pytest backend/tests/ -x`

---

## Risques et points d'attention

| Risque | Mitigation |
|--------|-----------|
| Structure XML R171/R50/R151 plus complexe que prévu | L'ADR (Étape 1) est la première action — ajuster le plan si nécessaire |
| R50/R151 ont des champs inattendus (cadres tarifaires, etc.) | Colonnes dédiées pour chaque champ XML — pas de `extra_data` JSON |
| Rename `mesures` → `mesures_r4x` casse du code | Module isolé. Vérifier par grep avant le rename |
| Circular import avec les nouveaux modèles | Ne PAS importer dans `models/__init__.py` — uniquement `migrations.py` et `init_database.py` |
| `EnedisFluxFile` partagé pas viable pour les headers non-R4x | `header_raw` JSON est le filet de sécurité. Évaluer pendant l'implémentation si des colonnes queryables supplémentaires sont nécessaires |
| R171 multi-PRM complexifie le stockage | Contrairement aux R4x (1 PRM/fichier), R171 peut en contenir plusieurs. Le `_store_r171` doit itérer sur les séries |
