# Feature Spec : Ingestion des flux R171 + C5 — R171, R50 et R151

> **Sub-feature 3/3** — Dépend de SF1 (déchiffrement) et SF2 (modèle + pipeline R4x).
> Chaîne : SF1 (decrypt) ✅ → SF2 (ingestion CDC R4x) ✅ → **SF3 (R171 + Index)**

## Prérequis SF1 + SF2 — Ce qui a été livré (2026-03-23)

> **IMPORTANT pour l'agent** : lire cette section ET les specs SF1/SF2 avant toute exploration.
> - SF1 : [`feature-enedis-sge-1-decrypt.md`](feature-enedis-sge-1-decrypt.md)
> - SF2 : [`feature-enedis-sge-2-ingestion-cdc.md`](feature-enedis-sge-2-ingestion-cdc.md)

### SF1 — Déchiffrement (PR #148)

- Module : `backend/data_ingestion/enedis/`
- API : `decrypt_file()`, `classify_flux()`, `load_keys_from_env()`, `SKIP_FLUX_TYPES`
- Clés : `KEY_1/IV_1`..`KEY_3/IV_3` dans `backend/.env` (pas `ENEDIS_DECRYPT_KEY`)
- Fixtures XML : **non commitées** — utiliser les vrais fichiers avec skip, ou créer des fixtures synthétiques

### SF2 — Modèle + Pipeline R4x

SF2 a livré :
- **2 tables SQLAlchemy** : `EnedisFluxFile` (registre fichiers) + `EnedisFluxMesure` (mesures brutes)
- **Parser** : `parse_r4x()` — pure function pour R4H/R4M/R4Q uniquement
- **Pipeline** : `ingest_file()` — classify → hash → idempotence → decrypt → parse → store
- **Enums** : `FluxStatus` (received, parsed, error, skipped)
- **DB integration** : shared `Base` from `models.base`, tables dans `promeos.db`
- **Migration** : `_create_enedis_tables()` dans `database/migrations.py`
- **Tests** : 49 tests (models 12, parsers 19, pipeline 10, integration 8)

**Scope SF2 = R4x uniquement.** Le pipeline `ingest_file()` skip les types non-R4x avec `FluxStatus.SKIPPED` :
```python
# pipeline.py line 95-99
if flux_type not in R4X_FLUX_TYPES:
    logger.info("Skipping %s (flux type %s not in R4x scope)", filename, flux_type.value)
    _record_file(session, filename, file_hash, flux_type.value, FluxStatus.SKIPPED)
    session.commit()
    return FluxStatus.SKIPPED
```

### Pourquoi R171 a été différé de SF2 à SF3

Le R171 a une structure XML fondamentalement différente des R4x :
- **R4x** : racine `<Courbe>`, pas de namespace, éléments `<Entete>`, `<Corps>`, `<Donnees_Courbe>`, `<Donnees_Point_Mesure>`
- **R171** : racine `<ns2:R171 xmlns:ns2="http://www.enedis.fr/stm/R171">`, éléments `<entete>`, `<serieMesuresDateesListe>`, `<serieMesuresDatees>`, `<prmId>`

Un parser R171 nécessite un parser dédié (pas de réutilisation de `parse_r4x()`). Il est regroupé avec R50/R151 dans SF3 car tous trois nécessitent un nouveau parser chacun.

### Architecture des données (décisions critiques de SF2)

> **"Nous devons absolument tout archiver sans manipuler la donnée"**

- **Toutes les valeurs sont des strings brutes** — pas de conversion float/datetime
- **Pas de contrainte unique sur les mesures** — Enedis peut republier des corrections, les deux versions sont archivées
- **Pas de `INSERT OR IGNORE`** — conséquence directe (pas de contrainte unique)
- **Idempotence au niveau fichier uniquement** — SHA256 du ciphertext
- **Deduplication différée** à une future couche staging/normalisation
- **Colonnes dédiées** (pas de `extra_data` JSON fourre-tout) — chaque champ XML a sa colonne

### API disponible de SF2

```python
from data_ingestion.enedis.enums import FluxType, FluxStatus
from data_ingestion.enedis.decrypt import (
    decrypt_file, classify_flux, load_keys_from_env,
    SKIP_FLUX_TYPES, DecryptError, MissingKeyError,
)
from data_ingestion.enedis.models import EnedisFluxFile, EnedisFluxMesure
from data_ingestion.enedis.pipeline import ingest_file
from data_ingestion.enedis.parsers.r4 import parse_r4x, R4xParseError
```

### Structures XML (découvertes lors de SF1)

| Flux | Racine XML | Namespace | Taille typique |
|------|-----------|-----------|---------------|
| R4H/R4M/R4Q | `<Courbe>` | Aucun | 25 Ko – 700 Ko |
| R171 | `<ns2:R171>` | `http://www.enedis.fr/stm/R171` | ~58 Ko |
| R50 | `<R50>` | `xmlns:xsi` | ~668 Ko |
| R151 | `<R151>` | `xmlns:xsi` | ~3 Ko |

**R171** : `<ns2:R171 xmlns:ns2="http://www.enedis.fr/stm/R171"><entete>...</entete><serieMesuresDateesListe><serieMesuresDatees><prmId>...</prmId>...</serieMesuresDatees></serieMesuresDateesListe></ns2:R171>`

**R50** : `<R50 xmlns:xsi="..."><En_Tete_Flux><Identifiant_Flux>R50</Identifiant_Flux>...</En_Tete_Flux>...</R50>`

**R151** : `<R151 xmlns:xsi="..."><En_Tete_Flux><Identifiant_Flux>R151</Identifiant_Flux>...</En_Tete_Flux>...</R151>`

Note : les fichiers C5 utilisent le préfixe historique `ERDF_` (pas `ENEDIS_`) dans les noms de fichier. La classification SF1 gère déjà cela.

### Branching

```bash
git checkout feat/enedis-sge-2-ingestion-cdc && git pull  # contient SF1 + SF2
git checkout -b feat/enedis-sge-3-ingestion-index
```

---

## Contexte

Les SF1 et SF2 ont livré le module de déchiffrement, le modèle de données staging (2 tables), le parser R4x, et le pipeline d'ingestion. Cette sub-feature étend le pipeline pour supporter les **3 types de flux restants** : R171 (CDC par PRM), R50 (courbe de charge C5), et R151 (relevés trimestriels C5).

### Ce que cette sub-feature doit livrer

- **Parser R171** pour les CDC journalières par PRM (C1-C4)
- **Parser R50** pour la courbe de charge C5 et **parser R151** pour les releves/index C5
- **Extension du pipeline** `ingest_file()` pour dispatcher vers les 3 nouveaux parsers
- **Extension du modèle** si la structure XML diverge trop de `EnedisFluxMesure` (voir décision Option A/B ci-dessous)
- **Fonction `ingest_directory()`** pour traitement batch d'un répertoire complet
- Tests d'intégration couvrant **tous** les types de flux (R4x + R171 + R50 + R151) dans un même batch

## Vocabulaire Enedis

| Terme | Signification |
|-------|--------------|
| **C1-C4** | Segments de comptage haute puissance (télérelevés, CDC disponible) |
| **C5** | Segment résidentiel/petit tertiaire — comptage par index (pas de CDC native) |
| **R171** | CDC journalière **par PRM individuel** (C1-C4) — différé de SF2 car XML très différent des R4x |
| **R50** | Courbe de charge des PRM C5 sur abonnement (pas 30 min, publication quotidienne ou mensuelle) |
| **R151** | Relevés trimestriels par PRM (C5) |
| **Index** | Valeur cumulée du compteur à un instant donné (en kWh) — contrairement à la CDC qui donne la puissance/énergie par intervalle |
| **ERDF** | Ancien nom d'Enedis — les flux C5 utilisent le préfixe historique `ERDF_` dans les noms de fichier |

## Flux en scope

| Flux | Contenu | Granularité | Cadence | Préfixe fichier |
|------|---------|-------------|---------|-----------------|
| **R171** | CDC journalière par PRM | Par PRM (14 chiffres) | Quotidien | `ENEDIS_R171_` |
| **R50** | Courbe de charge C5 | Par PRM | Quotidien ou mensuel | `ERDF_R50_` |
| **R151** | Relevés trimestriels | Par PRM | Trimestriel | `ERDF_R151_` |

### Particularités des flux

- **R171** : CDC par PRM individuel. Structure XML avec namespace `ns2`, éléments `serieMesuresDatees`, `prmId`. Totalement différent de la structure R4x `<Courbe>`.
- **Préfixe historique** : les fichiers C5 utilisent `ERDF_` (pas `ENEDIS_`). La classification (SF1) gère déjà cela, mais les parsers XML doivent aussi tolérer les deux préfixes/namespaces dans le contenu XML.
- **Structure différente de la CDC** : les index ne sont pas des séries temporelles à pas régulier. Un index est une valeur cumulée à un instant donné. Le modèle `EnedisFluxMesure` de SF2 peut nécessiter une adaptation (colonne `type_mesure` : "index" vs "cdc", ou table séparée si la structure diverge trop).

## Extension du modèle de données

### Modèle existant (SF2)

Le modèle SF2 utilise des **colonnes string dédiées** (pas de `extra_data` JSON, pas de Float/DateTime) :

| Colonne clé | Utilisation R4x | Applicable à R171/R50/R151 ? |
|-------------|----------------|------------------------------|
| `point_id` String(14) | PRM du périmètre fournisseur | R171: PRM individuel, R50/R151: PRM individuel |
| `grandeur_physique` String(10) | EA/ERI/ERC/E | R171: à vérifier dans le XML |
| `grandeur_metier` String(10) | CONS/PROD | R171: à vérifier |
| `unite_mesure` String(10) | kW/kWr/V | R50: non (la valeur est en W dans `<V>`), R151: n/a |
| `granularite` String(10) | Pas en minutes | R171: oui, R50: non (pas fixe via `Pas_Publication`), R151: n/a |
| `horodatage` String(50) | ISO8601 du point | Tous: horodatage de la mesure/index |
| `valeur_point` String(20) | Valeur brute | Tous: valeur brute |
| `statut_point` String(2) | R/H/P/S/T/F/G/E/C/K/D | R171: probablement, R50/R151: à vérifier |
| `horodatage_debut/fin` String(50) | Période du bloc | R171: à vérifier, R50/R151: à vérifier |

### Décision à prendre par l'agent

Après analyse des XML R171, R50 et R151 déchiffrés (utiliser `decrypt_file()` de SF1 pour les inspecter), l'agent doit décider :

**Option A** — Réutiliser `EnedisFluxMesure` tel quel :
- Si les colonnes existantes suffisent à stocker R171, R50, et R151 sans perte d'information
- Ajouter des colonnes si nécessaire (ex: `type_mesure` discriminant "cdc" vs "index")
- **Avantage** : requêtes cross-flux simples, pas de migration additionnelle

**Option B** — Créer une ou plusieurs tables dédiées :
- Si la structure XML est fondamentalement incompatible (ex: multiples index par PRM par relevé, cadres tarifaires, etc.)
- La table partage la FK vers `enedis_flux_file`
- **Avantage** : fidélité maximale si les structures divergent

**Critère de décision** : la fidélité. L'option qui conserve le plus d'information brute sans forçage est la bonne. **Pas de contrainte unique sur les mesures** — même philosophie que SF2 (archiver tout, dedup différée).

### Rappel — pas de contrainte unique sur les mesures

SF2 a explicitement choisi de ne PAS avoir de contrainte unique sur `EnedisFluxMesure`. Enedis peut republier des corrections pour le même PRM/timestamp. Les deux versions sont archivées. Cette décision s'applique aussi aux flux R171, R50, R151.

## Parsers XML

### Parsers à implémenter

| Parser | Fichier | Flux | Particularité |
|--------|---------|------|---------------|
| `parse_r171()` | `parsers/r171.py` | R171 | CDC journalière par PRM individuel, namespace `ns2` |
| `parse_r50()` | `parsers/r50.py` | R50 | Courbe de charge C5 (points 30 min) |
| `parse_r151()` | `parsers/r151.py` | R151 | Relevés trimestriels par PRM |

### Convention SF2 pour les parsers

SF2 a établi un pattern pour les parsers. Le suivre pour cohérence :
- **Pure function** (pas de classe ABC) : `parse_r171(xml_bytes: bytes) -> ParsedR171File`
- **Typed dataclasses** pour le résultat (pas de dicts)
- **Toutes les valeurs en strings** — pas de conversion float/datetime
- **Custom exception** : `R171ParseError`, `R50ParseError`, `R151ParseError`
- Utiliser `xml.etree.ElementTree` (stdlib)
- Helpers namespace-tolerant : voir `_strip_ns()`, `_find_child()`, `_child_text()` dans `parsers/r4.py`
- Être tolérants aux namespaces `ERDF` et `ENEDIS` dans le contenu XML
- **Pas de `extra_data` dict** — créer des colonnes dédiées pour chaque champ XML

### Tolérance aux préfixes historiques

Les flux C5 utilisent systématiquement `ERDF_` dans les noms de fichier. Le contenu XML peut aussi utiliser des namespaces ou des noms d'éléments avec le préfixe ERDF. Les parsers doivent gérer les deux variantes sans distinction. Le R171 utilise le namespace `http://www.enedis.fr/stm/R171`.

## Extension du pipeline

Le pipeline `ingest_file()` de SF2 doit être étendu pour :

1. **Supprimer le guard R4x-only** (pipeline.py lignes 95-99) qui skip tout non-R4x
2. **Reconnaître R171, R50 et R151** dans le dispatch des parsers
3. **Sélectionner le bon parser** selon le `FluxType` (R4x → `parse_r4x()`, R171 → `parse_r171()`, etc.)
4. **Insérer les mesures** dans la bonne table (si Option B) ou avec le bon discriminant (si Option A)
5. **`ingest_file()` doit continuer à commit la session** — même pattern que SF2

### Traitement batch d'un répertoire complet

Ajouter une fonction de traitement batch :

```python
def ingest_directory(dir_path: Path, session: Session) -> dict[str, int]:
    """Traite tous les fichiers d'un répertoire.

    Gère un mix de fichiers CDC, Index, et hors-scope.

    Returns: {"parsed": N, "skipped": N, "error": N, "already_processed": N}
    """
```

- Itérer sur tous les fichiers du répertoire
- Appeler `ingest_file()` pour chaque fichier
- Agréger les résultats
- Un fichier en erreur ne bloque pas le reste du batch
- Les fichiers hors-scope (R172, X14, HDM) sont classifiés et skipped

## Variables d'environnement

Mêmes que SF1 et SF2, aucune nouvelle variable.

| Variable | Obligatoire | Description |
|----------|------------|-------------|
| `KEY_1`..`KEY_3` / `IV_1`..`IV_3` | Oui | 3 paires clé/IV AES (hex-encoded) |
| `ENEDIS_ARCHIVE_DIR` | Non | Archivage XML (via SF1) |

## Matrice d'erreurs

| Scénario | Comportement | Status |
|----------|-------------|--------|
| Fichier introuvable | Lever `FileNotFoundError` | n/a |
| Clés absentes | Lever `MissingKeyError` (via SF1) | n/a |
| Mauvaise clé (garbage post-décrypt) | Enregistrer fichier avec erreur | error |
| XML invalide après décrypt | Enregistrer fichier avec erreur | error |
| Type de flux inconnu (R172, X14, HDM) | Enregistrer fichier avec status skipped | skipped |
| Fichier déjà traité (même hash, status=parsed) | No-op | inchangé |
| Fichier déjà connu (même hash, status=error) | Retry : supprimer l'ancien enregistrement et retraiter | selon résultat |
| Fichier valide, 0 mesures | Enregistrer fichier, measures_count=0 | parsed |
| Erreur DB pendant l'insert | Rollback, enregistrer fichier avec erreur | error |
| Doublon de mesure (même PRM+horodatage) | `INSERT OR IGNORE` — silencieux | parsed |

## Arborescence cible (état final après SF3)

```
backend/
  data_ingestion/
    __init__.py
    enedis/
      __init__.py
      enums.py               # FluxType (SF1), FluxStatus (SF2) — étendre si nécessaire
      decrypt.py             # (SF1 — ne pas modifier)
      models.py              # EnedisFluxFile, EnedisFluxMesure (shared Base) — étendre si Option B
      pipeline.py            # ingest_file() (SF2, étendu SF3), ingest_directory() (SF3)
      parsers/
        __init__.py
        r4.py                # parse_r4x() — pure function (SF2 — ne pas modifier)
        r171.py              # parse_r171() (SF3)
        r50.py               # parse_r50() (SF3)
        r151.py              # parse_r151() (SF3)
      tests/
        __init__.py
        conftest.py           # Fixtures AES + DB in-memory (SF1+SF2 — étendre si besoin)
        test_decrypt.py       # 26 tests (SF1 — ne pas modifier)
        test_integration.py   # 8 tests (SF1 — ne pas modifier)
        test_models.py        # 12 tests (SF2 — étendre si Option B)
        test_parsers_r4.py    # 19 tests (SF2 — ne pas modifier)
        test_parsers_r171.py  # (SF3)
        test_parsers_index.py # (SF3) — R50 + R151
        test_pipeline.py      # 10 tests (SF2 — étendre ou create test_pipeline_full.py)
        test_pipeline_full.py # (SF3) — tous les types de flux + ingest_directory()
  database/
    migrations.py            # _create_enedis_tables() (SF2) — étendre si nouvelles tables
  scripts/
    init_database.py         # import enedis models (SF2 — inchangé si pas de nouvelles tables)
```

**Note** : les noms de fichiers de test SF2 sont `test_parsers_r4.py` et `test_pipeline.py` (pas `test_parsers_cdc.py` ni `test_pipeline_cdc.py` comme le spec SF2 original proposait).

## Tests

### Tests unitaires — Parser R171 (`test_parsers_r171.py`)

1. **parse_r171** : fixture synthétique XML avec namespace `ns2`, vérifier PRM, horodatage, valeur brute (string)
2. **R171 multiple PRM** : XML avec plusieurs `serieMesuresDatees` → mesures pour chaque PRM
3. **R171 namespace tolerant** : tester avec et sans namespace
4. **R171 XML vide** : XML valide sans mesures → structure vide, pas d'exception
5. **R171 missing required fields** : → `R171ParseError`

### Tests unitaires — Parsers Index (`test_parsers_index.py`)

1. **parse_r50** : fixture synthétique, vérifier PRM, horodatage, puissance moyenne brute (string), qualité
2. **parse_r151** : fixture synthétique, vérifier extraction correcte
3. **Parser namespace ERDF** : vérifier que les parsers fonctionnent avec les namespaces `ERDF` historiques
4. **Parser XML vide** : XML valide sans mesures → structure vide, pas d'exception

### Tests d'intégration — Pipeline complet (`test_pipeline_full.py`)

1. **Pipeline complet R171** : fixture chiffrée (clé de test) → `ingest_file` → mesures CDC en base
2. **Pipeline complet R50** : fixture chiffrée (clé de test) → `ingest_file` → mesures index en base
3. **Pipeline complet R151** : idem
4. **Batch mixte** : répertoire contenant des fichiers R4H, R171, R50, R151, R172 → tous traités correctement, R172 skipped
5. **Idempotence batch** : exécuter `ingest_directory` × 2 sur le même répertoire → 0 nouvelle mesure
6. **Résilience globale** : mix de fichiers valides, corrompus, et hors-scope → les valides sont parsed, les corrompus sont error, les hors-scope sont skipped. Aucun crash.
7. **Requête cross-flux** : après ingestion de tous les types, vérifier qu'on peut requêter par PRM sur les données R171 + R50 + R151

### Test de non-régression

```bash
# Tous les tests SF1 + SF2 doivent continuer à passer (75 tests actuels)
cd promeos-poc && ./backend/venv/bin/pytest backend/data_ingestion/ -x -v

# Les tests existants du POC ne doivent pas casser
cd promeos-poc && ./backend/venv/bin/pytest backend/tests/ -x
```

## Contraintes d'architecture

1. **Isolation totale** : module `backend/data_ingestion/enedis/` — aucune dépendance ni modification des modèles existants
2. **Pas de routes API** dans cette feature
3. **SQLAlchemy** pour les modèles, cohérent avec le reste du backend
4. **Les tables staging sont permanentes**
5. **Les tests existants ne doivent pas casser** : `pytest backend/tests/ -x` ET `pytest backend/data_ingestion/ -x`

## Challenges intégrés

| Pattern | Point de vigilance |
|---------|-------------------|
| **Metric Validity** | Les tests d'intégration doivent couvrir TOUS les types de flux (R4H, R4M, R4Q, R171, R50, R151), pas seulement les nouveaux |
| **Silent Self-Defeat** | L'idempotence fichier (hash SHA256) doit fonctionner pour R171, R50, R151. Pas de contrainte unique mesure (décision SF2) |
| **Boundary Behavior** | `ingest_directory` avec un répertoire contenant uniquement des fichiers hors-scope → retourne `{"parsed": 0, "skipped": N}`, pas d'erreur |
| **Misuse Surface** | Le préfixe `ERDF_` ne doit pas être traité comme un format inconnu — les parsers et la classification doivent le supporter nativement |
| **Archivage brut** | Comme SF2, **toutes les valeurs doivent rester des strings** — pas de conversion float, datetime, ou enum. Stocker exactement ce que le XML contient |
| **Circular Import** | Ne PAS importer les modèles Enedis dans `models/__init__.py` — cela cause une circular import. Les importer dans `migrations.py` et `init_database.py` uniquement |
