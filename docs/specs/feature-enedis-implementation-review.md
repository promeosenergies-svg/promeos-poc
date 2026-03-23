# Revue critique SF1 + SF2 — Enedis SGE Ingestion

> **Date** : 2026-03-23
> **Branche** : `feat/enedis-sge-2-ingestion-cdc`
> **Commits** : `82c5095` (SF1) + `74e2351` (SF2) + `1dc013a` (docs)
> **Tests** : 75/75 passent (26 decrypt + 8 integration + 12 models + 19 parsers + 10 pipeline)

---

## Verdict global

L'implementation est **solide et bien structuree**. Code propre, bonne separation des concerns, bon ratio tests/code. Mais j'ai identifie un vrai bug, quelques edge cases non traites, et des decisions a confirmer avant SF3.

---

## BUG : Pas de try/except autour de la phase de stockage DB

**Fichier** : `pipeline.py:121-166`

Le spec exige : *"Erreur DB pendant l'insert -> Rollback, enregistrer fichier avec erreur -> status=error"*. Ce n'est **pas implemente**.

Si `session.flush()` (ligne 133) ou `session.bulk_save_objects()` (ligne 157) leve une exception (disque plein, erreur SQLAlchemy), le pipeline crashe sans :
- faire de rollback
- enregistrer le fichier avec `status=error`

La session est laissee dans un etat dirty. Le caller doit gerer lui-meme, ce qui contredit le contrat documente ("rolls back on unhandled error").

**Fix propose** : wrapper le bloc store dans un try/except qui fait rollback + enregistre le fichier en erreur.
**Décision Utilisateur** : Fix convenable qui apporte de la sécurité. A implémenter.
**Statut** : Resolu — PR fix/issue-149-db-storage-try-except (#149).

---

## Index duplique sur `flux_file_id`

**Fichier** : `models.py:79` + `models.py:87`

```python
# Ligne 79 — sur la colonne
flux_file_id = Column(..., index=True, ...)

# Ligne 87 — dans __table_args__
Index("ix_enedis_mesure_flux_file", "flux_file_id"),
```

Les deux creent le **meme index**. Double cout en espace et en ecriture, zero benefice. Supprimer l'un des deux (garder celui nomme dans `__table_args__` pour la coherence avec les autres index).
**Décision Utilisateur** : OK. Analyser impact et faire l'optimisation.
**Statut** : Résolu — PR fix/issue-150-duplicate-index-flux-file-id (#160).

---

## Edge cases non traites

### 1. Concurrence sur l'idempotence (`pipeline.py:77-87`)

Si deux workers traitent le meme fichier simultanement :
- Tous deux lisent `existing is None`
- Tous deux tentent l'insert avec le meme `file_hash`
- Le second leve `IntegrityError`

La contrainte `unique=True` protege contre les doublons, mais l'exception n'est pas catchee. Pour le POC mono-processus c'est OK, mais pour SF3 avec `ingest_directory()` si on envisage du parallelisme, il faudra le gerer.

**Décision Utilisateur** : Overkill pour le POC. Cependant ouvrir in feature détaillé dans Github pour un développement en phases ultérieures.

### 2. `_hash_file` lit tout le fichier en memoire (`pipeline.py:178-180`)

`file_path.read_bytes()` charge tout en RAM. Avec les fichiers actuels (25 Ko - 700 Ko) c'est fin. Si les R4Q trimestriels grossissent en production, utiliser un hash par chunks serait plus safe. Pas bloquant pour le POC.

**Décision Utilisateur** : Overkill pour le POC. Cependant ouvrir in feature détaillé dans Github pour un développement en phases ultérieures lorsque le scaleup sera d'actualité.


### 3. `FileNotFoundError` message peu clair

`_hash_file(file_path)` est appele **avant** `decrypt_file()`. Si le fichier n'existe pas, l'erreur vient de `Path.read_bytes()` (message generique) plutot que du message custom de `decrypt_file` ("File not found: ..."). Mineur.

**Décision Utilisateur** : La clarté dans le traitement et les causes d'erreurs est essentielle. Ouvrir une issue github et faire le fix.


---

## Enum `RECEIVED` defini mais jamais utilise

`FluxStatus.RECEIVED = "received"` existe dans `enums.py` mais n'est assigne nulle part dans le pipeline. Le cycle de vie implemente saute directement de "pas en base" a PARSED/ERROR/SKIPPED. Le `DECRYPTED` du spec original a aussi ete elimine.

**Question** : on supprime `RECEIVED` pour eviter la confusion, ou on le garde pour un futur usage (e.g., pipeline asynchrone ou le fichier est recu avant d'etre traite) ?
**Décision Utilisateur** : Le status received permet de stocker en base de données tous les fichiers reçus, avant meme de tenter leur ingestion. Important de l'avoir pour une gestion de pipeline solide. Vérifier si cela est prévu en SF3, car c'est plus logique lorsque nous traiterons des directory plutôt que des files uniques.


---

## Docstring `EnedisFluxMesure` trop restrictive

La docstring dit : *"Raw measurement point from an Enedis R4x CDC flux"*. Or SF3 va utiliser cette meme table pour R171, R50, R151. Elle devrait dire simplement "Raw measurement from an Enedis flux".

**Décision Utilisateur** : Je ne pense pas que ça soit une bonne idée de stocker tous les flux, qui ont des structures différentes, dans une meme table. Trop de compromis et de confusion. Audit difficile. Implémentation Data à revoir. A mon avis c'est consistant d'avoir une table centralisée de suivi des flux traités, mais les contenus devraient être dans des tables spécialisées. La normalisation et/ou fusion dans une table fonctionnelle se fera en étapes ultérieures hors du scope de ce feature.


---

## Decisions de design a confirmer avant SF3

### 1. Pas de contrainte unique sur les mesures

L'implementation a deliberement devie du spec (qui voulait `UNIQUE(point_id, horodatage, flux_type)` + `INSERT OR IGNORE`). Le rationale documente est : *"Enedis peut republier des corrections, les deux versions sont archivees"*.

**Impact** : si le meme fichier R4H est publie deux fois avec des hash differents (e.g., re-genere par Enedis), les mesures sont dupliquees en base. Il n'y a **aucune protection contre les doublons semantiques**, uniquement contre le re-processing du meme fichier physique.

**Question** : est-ce le comportement souhaite ? En production avec des milliers de fichiers, la table grossira vite. La dedup future devra distinguer original vs correction vs vrai doublon.

**Décision Utilisateur** : Nous devrions être capables de détecter ce edge case. Charger les données en spécifiant que c'est, par exemple, une v2 du meme fichier (donnant la compréhension qu'il y a eu republication du meme fichier avec données différentes et obligeant en staging à une analyse et décision du data manager). Gestion donc à dévelloper avant d'attaquer SF3.


### 2. Toutes les valeurs en strings

`valeur_point` est String(20), `horodatage` est String(50). Aucune requete SQL de type `WHERE valeur_point > 500` ou `WHERE horodatage BETWEEN ...` ne fonctionnera sur la table staging.

C'est coherent avec la philosophie "zero manipulation", mais ca signifie que **toute exploitation analytique necessite la couche de normalisation**. L'approche est correcte pour le staging, juste confirmer qu'on n'a pas besoin de requetes directes sur ces donnees brutes.

**Décision Utilisateur** : Cette approche est volontaire. Nous la maintenons.


### 3. Colonnes R4x-specifiques sur `EnedisFluxMesure`

Les colonnes `grandeur_physique`, `grandeur_metier`, `unite_mesure`, `granularite`, `horodatage_debut`, `horodatage_fin` sont specifiques a la structure `<Donnees_Courbe>` des R4x.

Pour R171 (structure `serieMesuresDatees`), certaines colonnes pourraient etre reutilisees (les noms des champs XML different mais le concept est similaire). Pour R50/R151 (index, pas CDC), la structure est fondamentalement differente.

**Options pour SF3** :
- **Option A** : reutiliser `EnedisFluxMesure`, mapper les champs R171/R50/R151 vers les colonnes existantes (certaines seront NULL). Simple.
- **Option B** : table dediee par famille de flux (e.g., `enedis_flux_index` pour R50/R151). Plus fidele mais plus de complexite.

**Recommandation** : Option A pour R171 (meme concept CDC, champs mappables) + Option B pour R50/R151 (index != CDC, structure trop differente). Mais c'est a confirmer.

**Décision Utilisateur** : Voir décision antérieure. Nous sommes en phase d'ingestion brute. Il serait préférable d'avoir des tables dédiées par flux. La fusion/normalisation se faisant en phases postérieures. Analysez les best practices et confirmez cette décision.

### 4. `point_id` String(14) — suffisant pour tous les flux ?

Les PRM francais font toujours 14 chiffres. Mais est-ce que R50/R151 utilisent bien un PRM ou un identifiant de format different ? A verifier en dechiffrant un fichier R50.
**Décision Utilisateur** : En principe c'est fixe chez Enedis. Doute sur d'autres ELDs. Ne rien faire pour l'instant, nous le gardons en point d'attention (ouvrir un issue de type question)

### 5. Colonnes header R4x-specifiques sur `EnedisFluxFile`

`frequence_publication`, `nature_courbe_demandee`, `identifiant_destinataire` sont specifiques aux entetes R4x. Pour R171/R50/R151, ces colonnes seront NULL. Le `header_raw` JSON reste la source de verite complete.

**Question** : est-ce acceptable d'avoir ces colonnes toujours NULL pour les flux non-R4x, ou faut-il les renommer en quelque chose de plus generique ?

**Décision Utilisateur** : Sujet devraie être résolu en ayant en phase d'ingestion brute des tables dédiées par flux.

### 6. La migration `_create_enedis_tables` ne gere pas les ALTER TABLE

Si SF3 ajoute de nouvelles colonnes aux tables existantes, `_create_enedis_tables` fait `has_table()` -> `return` (skip). Il faudra une logique de migration complementaire (comme les `_add_*_columns` patterns existants dans `migrations.py`).
**Décision Utilisateur** : Ceci doit être régle en code ou en processus lors de l'implémentation de nouvelles colonnes?

---

## Points positifs

- Parser en pure function + dataclasses typees : excellent pattern, facile a tester
- `header_raw` JSON pour la fidelite complete : bonne decision
- Idempotence fichier par hash SHA256 : robuste
- Cascade delete file -> mesures : cleanup propre
- Tolerance whitespace et attributs optionnels dans le parser
- Les tests couvrent bien les cas limites (0 mesures, fichier corrompu, retry, dual courbes)

---

## Resume des actions

| # | Type | Sujet | Severite | Action |
|---|------|-------|----------|--------|
| 1 | Bug | Pas de try/except autour du stockage DB | **Haute** | ~~Fix necessaire~~ Resolu — **#149** |
| 2 | Bug | Index duplique sur `flux_file_id` | Basse | ~~Fix simple~~ Résolu — **#150** |
| 3 | Edge case | Concurrence sur idempotence | Basse (POC) | A traiter si parallelisme — **#152** |
| 4 | Edge case | `_hash_file` lit tout en memoire | Basse (POC) | Note pour production — **#153** |
| 5 | Edge case | `FileNotFoundError` message peu clair | Basse | Amelioration mineure — **#151** |
| 6 | Cleanup | Enum `RECEIVED` inutilise | Basse | Conserver, implémenter en SF3 — **#154** |
| 7 | Cleanup | Docstring `EnedisFluxMesure` restrictive | Basse | Résolu par tables dédiées — **#155** |
| 8 | Decision | Pas de contrainte unique mesures | -- | Versioning republications avant SF3 — **#156** |
| 9 | Decision | Toutes les valeurs en strings | -- | Confirmé — ADR `v69_enedis_staging_strings.md` |
| 10 | Decision | Colonnes R4x-specifiques sur mesures | -- | Tables dédiées par flux — **#155** |
| 11 | Decision | `point_id` String(14) suffisant ? | -- | Point d'attention — **#157** |
| 12 | Decision | Colonnes header R4x-specifiques | -- | Résolu par tables dédiées — **#155** |
| 13 | Decision | Migration ne gere pas ALTER TABLE | -- | A traiter dans SF3 — **#158** |
