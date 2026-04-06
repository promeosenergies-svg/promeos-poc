# Feature Spec : Ingestion des flux Courbe De Charge (CDC) — R4x

> **Sub-feature 2/3** — **COMPLÉTÉE le 2026-03-23**
> Branche : `feat/enedis-sge-2-ingestion-cdc`
> Chaîne : SF1 (decrypt) ✅ → **SF2 (ingestion CDC R4x)** ✅ → SF3 (R171 + Index)

---

## Résultat de l'implémentation

### Scope réel vs spec

**Le R171 a été différé à SF3.** L'implémentation SF2 couvre uniquement les flux R4x (R4H, R4M, R4Q). Le R171 a une structure XML fondamentalement différente (namespace `ns2:R171`, schéma `serieMesuresDatees` au lieu de `<Courbe>`) et a été regroupé avec SF3 pour cohérence.

### Ce qui a été livré

| Livrable | Statut | Détail |
|----------|--------|--------|
| Modèle SQLAlchemy `EnedisFluxFile` | ✅ | Registre des fichiers ingérés, header brut en JSON |
| Modèle SQLAlchemy `EnedisFluxMesure` | ✅ | Mesures CDC brutes, fully denormalized |
| Parser `parse_r4x()` | ✅ | Pure function, typed dataclasses, zero side effects |
| Pipeline `ingest_file()` | ✅ | classify → hash → idempotence → decrypt → parse → store → commit |
| Enum `FluxStatus` | ✅ | received, parsed, error, skipped |
| Migration `_create_enedis_tables()` | ✅ | Intégré dans `database/migrations.py` |
| Tests unitaires | ✅ | 49 tests (12 models + 19 parsers + 10 pipeline + 8 integration) |
| Shared Base integration | ✅ | Tables créées dans `promeos.db` (pas de base séparée) |

### Écarts entre le spec et l'implémentation

| Spec original | Réalité implémentée | Raison |
|--------------|---------------------|--------|
| R4 + R171 dans SF2 | **R4x uniquement**, R171 différé à SF3 | R171 a un XML très différent (namespace, structure), regroupé avec R50/R151 |
| BaseParser ABC + ParsedMesure dataclass | **Pas de classe abstraite**, pure function `parse_r4x()` retourne `ParsedR4xFile` | YAGNI — le R4x parser est self-contained, pas besoin d'héritage pour 1 parser |
| `NatureMesure`, `CadenceMesure` enums | **Non implémentés** — valeurs stockées comme strings brutes du XML | Philosophie "archiver sans manipuler" — les codes Enedis (`R`, `H`, `P`...) sont stockés tels quels |
| Contrainte unique sur mesures `(point_id, horodatage, flux_type)` | **Pas de contrainte unique sur les mesures** | Décision utilisateur : Enedis peut republier des corrections, les deux versions doivent être archivées. Dedup différée à une couche staging/normalisation future |
| `INSERT OR IGNORE` pour doublons | **Pas nécessaire** (pas de contrainte unique) | Conséquence directe de l'archivage sans manipulation |
| `point_id="AGGREGATE"` sentinelle pour R4 | **`point_id` = PRM réel** du `<Identifiant_PRM>` | Les R4x contiennent bien un PRM dans le XML (identifiant du périmètre fournisseur) |
| Colonnes `valeur` Float, `horodatage` DateTime | **Tout en String** : `valeur_point` String(20), `horodatage` String(50) | Zero data loss — pas de conversion ni normalisation |
| `extra_data` JSON fourre-tout | **Colonnes dédiées** pour chaque champ XML (grandeur_physique, unite_mesure, etc.) + `header_raw` JSON pour l'entête complet | Plus queryable, plus fidèle |
| Base séparée `EnedisBase` | **Shared `Base`** from `models.base` | POC — tout centralisé dans `promeos.db`. Production pourra migrer vers time-series DB |
| Fichier retry (status=error → delete + reprocess) | ✅ Implémenté | Conforme au spec |

### Architecture des données

#### Philosophie : archivage brut sans manipulation

> "Nous devons absolument tout archiver sans manipuler la donnée"

- **Toutes les valeurs sont des strings** — pas de conversion float/datetime
- **Pas de contrainte unique sur les mesures** — Enedis peut republier des corrections, les deux versions sont conservées
- **Idempotence au niveau fichier uniquement** — SHA256 du ciphertext
- **Deduplication différée** — une future couche staging/normalisation s'en chargera

#### Table `enedis_flux_file`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `filename` | String(255) | Nom du fichier .zip original |
| `file_hash` | String(64), **UNIQUE** | SHA256 du fichier chiffré (idempotence) |
| `flux_type` | String(10) | R4H, R4M, R4Q, etc. |
| `status` | String(20) | received/parsed/error/skipped |
| `error_message` | Text, nullable | Message d'erreur si status=error |
| `measures_count` | Integer | Nombre de mesures extraites |
| `frequence_publication` | String(5), nullable | H/M/Q — de l'Entête XML |
| `nature_courbe_demandee` | String(20), nullable | Brute/Corrigee |
| `identifiant_destinataire` | String(100), nullable | Code destinataire du flux |
| `header_raw` | Text, nullable | Entête XML complet en JSON (fidélité totale) |
| `created_at` / `updated_at` | DateTime | TimestampMixin |

#### Table `enedis_flux_mesure`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `flux_file_id` | FK → enedis_flux_file (CASCADE) | Fichier source |
| `flux_type` | String(10) | Dénormalisé pour les requêtes |
| `point_id` | String(14) | Identifiant_PRM |
| `grandeur_physique` | String(10), nullable | EA/ERI/ERC/E — brut XML |
| `grandeur_metier` | String(10), nullable | CONS/PROD — brut XML |
| `unite_mesure` | String(10), nullable | kW/kWr/V — brut XML |
| `granularite` | String(10), nullable | Pas en minutes — brut XML |
| `horodatage_debut` | String(50), nullable | Début période du bloc Donnees_Courbe |
| `horodatage_fin` | String(50), nullable | Fin période du bloc Donnees_Courbe |
| `horodatage` | String(50) | Horodatage du point — brut ISO8601 |
| `valeur_point` | String(20), nullable | Valeur brute — string, pas float |
| `statut_point` | String(2), nullable | R/H/P/S/T/F/G/E/C/K/D — brut XML |
| `created_at` / `updated_at` | DateTime | TimestampMixin |

Index de performance :
- `ix_enedis_mesure_point_horodatage` — `(point_id, horodatage)`
- `ix_enedis_mesure_flux_file` — `(flux_file_id)`
- `ix_enedis_mesure_flux_type` — `(flux_type)`

### Parser R4x — dataclasses de sortie

```python
from data_ingestion.enedis.parsers.r4 import (
    parse_r4x,          # (xml_bytes: bytes) -> ParsedR4xFile
    R4xParseError,      # raised on structural XML error
    ParsedR4xFile,      # header + point_id + courbes[]
    ParsedR4xHeader,    # raw dict + extracted queryable fields
    ParsedCourbe,       # Donnees_Courbe context + points[]
    ParsedPoint,        # horodatage, valeur_point, statut_point
)
```

### Pipeline API

```python
from data_ingestion.enedis.pipeline import ingest_file

# ingest_file commits on success, rolls back on unhandled error
status = ingest_file(
    file_path=Path("flux.zip"),
    session=session,
    keys=keys,               # from load_keys_from_env()
    chunk_size=1000,          # batch insert size (default)
    archive_dir=None,         # optional XML archiving
)
# Returns FluxStatus: PARSED, SKIPPED, or ERROR
```

**Important** : `ingest_file()` commits the session internally. The caller should NOT commit separately.

### DB integration

Les models Enedis utilisent le `Base` partagé de `models.base` (pas de `declarative_base()` séparé). Conséquences :

1. **`database/migrations.py`** : `_create_enedis_tables(engine)` ajouté à `run_migrations()` — crée les tables si absentes
2. **`scripts/init_database.py`** : importe `data_ingestion.enedis.models` avant `Base.metadata.create_all()` pour enregistrer les tables
3. **`models/__init__.py`** : **NON modifié** — l'import Enedis ici cause une circular import (`data_ingestion.enedis.models` → `models.base` → `models.__init__` → `data_ingestion.enedis.models`)
4. **Tests** : la fixture `db()` dans `conftest.py` importe `data_ingestion.enedis.models` puis fait `Base.metadata.create_all()` sur un SQLite in-memory

### Arborescence livrée (état après SF2)

```
backend/
  data_ingestion/
    __init__.py
    enedis/
      __init__.py
      enums.py               # FluxType (10 valeurs, SF1) + FluxStatus (SF2)
      decrypt.py             # (SF1 — inchangé)
      models.py              # EnedisFluxFile, EnedisFluxMesure (shared Base)
      pipeline.py            # ingest_file() — R4x only
      parsers/
        __init__.py
        r4.py                # parse_r4x() — pure function, typed dataclasses
      tests/
        __init__.py
        conftest.py          # Fixtures AES + DB in-memory (shared Base)
        test_decrypt.py      # 26 tests (SF1 — inchangé)
        test_integration.py  # 8 tests (SF1 — inchangé)
        test_models.py       # 12 tests (SF2)
        test_parsers_r4.py   # 19 tests (SF2)
        test_pipeline.py     # 10 tests (SF2)
  database/
    migrations.py            # _create_enedis_tables() ajouté (SF2)
  scripts/
    init_database.py         # import enedis models ajouté (SF2)
```

### Commandes de test

```bash
# Tests SF1 + SF2 (75 tests, ~5s)
cd promeos-poc && ./backend/venv/bin/pytest backend/data_ingestion/ -x -v

# Vérifier non-régression backend existant
cd promeos-poc && ./backend/venv/bin/pytest backend/tests/ -x
```

---

## Spec original (pour référence)

Le reste du document ci-dessous est le spec original tel qu'il a été rédigé avant implémentation. Les sections marquées `[ÉCART]` indiquent les écarts avec la réalité. Pour l'état réel de l'implémentation, **se référer à la section "Résultat de l'implémentation" ci-dessus**.

---

## Prérequis SF1 — Ce qui a été livré (2026-03-23)

> **IMPORTANT pour l'agent** : lire cette section avant toute exploration. Elle documente l'API réelle de SF1.

### Module path

Le code vit dans `backend/data_ingestion/enedis/` (**pas** `backend/enedis/`).

### API disponible

```python
from data_ingestion.enedis.enums import FluxType
from data_ingestion.enedis.decrypt import (
    decrypt_file,       # (Path, keys: list[tuple[bytes,bytes]], archive_dir?: Path) -> bytes
    classify_flux,      # (filename: str) -> FluxType
    load_keys_from_env, # () -> list[tuple[bytes,bytes]]
    SKIP_FLUX_TYPES,    # frozenset{R172, X14, HDM, UNKNOWN}
    DecryptError,       # déchiffrement échoué
    MissingKeyError,    # clés absentes ou invalides
)
```

### Variables d'environnement (clés)

**Le spec original mentionnait `ENEDIS_DECRYPT_KEY` — cette variable n'existe pas.** Les clés sont :

| Variable | Format |
|----------|--------|
| `KEY_1` / `IV_1` | hex 32 chars (16 bytes) |
| `KEY_2` / `IV_2` | hex 32 chars (16 bytes) |
| `KEY_3` / `IV_3` | hex 32 chars (16 bytes) |

Elles sont dans `backend/.env` (non commitées).

### Fixtures XML

**Les fixtures XML ne sont PAS commitées dans le repo** (décision utilisateur). Pour les tests :
- Les **tests unitaires** doivent utiliser des fixtures XML synthétiques (créées en code)
- Les **tests d'intégration** utilisent les vrais fichiers de `Promeos/flux_enedis/` avec `@pytest.mark.skipif` si les clés/fichiers ne sont pas disponibles

Les XML déchiffrés peuvent être générés localement pour inspection :
```python
decrypt_file(path, keys, archive_dir=Path("/tmp/enedis_xml"))
```

### Structures XML réelles (découvertes lors de SF1)

| Flux | Racine XML | Namespace | Taille typique |
|------|-----------|-----------|---------------|
| R4H/R4M/R4Q | `<Courbe>` | Aucun | 25 Ko – 700 Ko |
| R171 | `<ns2:R171>` | `http://www.enedis.fr/stm/R171` | ~58 Ko |

**R4x** : `<Courbe><Entete><Identifiant_Flux>R4x</Identifiant_Flux><Frequence_Publication>H|M|Q</Frequence_Publication>...</Entete><Corps>...</Corps></Courbe>`

**R171** : `<ns2:R171 xmlns:ns2="http://www.enedis.fr/stm/R171"><entete>...</entete><serieMesuresDateesListe><serieMesuresDatees><prmId>...</prmId>...</serieMesuresDatees></serieMesuresDateesListe></ns2:R171>`

### Tests SF1

```bash
# Lancer les tests SF1 (ne pas modifier ces fichiers)
cd promeos-poc && ./backend/venv/bin/pytest backend/data_ingestion/ -x -v
```

Tests existants : `test_decrypt.py` (26 unitaires) + `test_integration.py` (8 intégration).

### Branching

Créer la branche SF2 **depuis `feat/enedis-sge-ingestion`** (qui contiendra SF1 une fois mergée) :
```bash
git checkout feat/enedis-sge-ingestion && git pull
git checkout -b feat/enedis-sge-2-ingestion-cdc
```

---

## Contexte

La SF1 a produit le module de déchiffrement. Cette sub-feature construit le modèle de données staging, les parsers XML pour les flux CDC, et le pipeline d'ingestion.

### Ce que cette sub-feature doit livrer

- Modèle de données staging (tables SQLAlchemy) pour les fichiers ingérés et les mesures CDC brutes
- Parsers XML pour R4H, R4M, R4Q et R171
- Pipeline d'ingestion : decrypt → parse → store

## Vocabulaire Enedis

| Terme | Signification |
|-------|--------------|
| **PRM** | Point de Référence Mesure — identifiant unique 14 chiffres d'un point de livraison |
| **CDC** | Courbe De Charge — série temporelle de puissance/énergie à pas fin (10min, 30min, horaire) |
| **C1-C4** | Segments de comptage haute puissance (télérelevés, CDC disponible) |
| **R4H/R4M/R4Q** | CDC **agrégées** sur l'ensemble du périmètre fournisseur (pas par PRM individuel) — cadence horaire/mensuelle/trimestrielle |
| **R171** | CDC journalière **par PRM individuel** |

## Flux en scope

| Flux | Contenu | Granularité | Cadence |
|------|---------|-------------|---------|
| **R4H** | CDC horaire agrégée (périmètre fournisseur) | Pas de PRM individuel | Quotidien |
| **R4M** | CDC mensuelle agrégée | Pas de PRM individuel | Mensuel |
| **R4Q** | CDC trimestrielle agrégée | Pas de PRM individuel | Trimestriel |
| **R171** | CDC journalière par PRM | Par PRM (14 chiffres) | Quotidien |

**Point critique** : Les R4H/R4M/R4Q sont des flux **agrégés** au niveau du périmètre fournisseur. Ils ne contiennent pas de PRM individuel. Le modèle de données et les contraintes d'unicité doivent refléter cette réalité.

## Modèle de données staging (SQLAlchemy)

### Principe directeur

Stocker l'information brute des flux Enedis **le plus fidèlement possible**, sans transformation ni perte. Le modèle exact (champs, relations) doit être conçu après analyse de la structure XML réelle (l'agent doit déchiffrer les fichiers localement pour inspecter le XML).

### Exigences pour guider la conception

- **Fidélité** : ne pas jeter d'information présente dans le XML — si un champ existe dans le flux, il doit être stocké (en colonne typée ou en JSON `extra_data`)
- **Traçabilité** : chaque donnée doit pouvoir remonter au fichier source (quel flux, quel fichier, quelle date de réception)
- **Pas de normalisation** : les données sont stockées telles qu'Enedis les envoie (unités, codes qualité, natures)

### Tables attendues (indicatif — adapter après analyse du XML)

#### `enedis_flux_file` — Registre des fichiers traités

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `filename` | String | Nom du fichier original |
| `file_hash` | String(64) | SHA256 du fichier chiffré (pour idempotence) |
| `flux_type` | Enum(FluxType) | R4H, R4M, R4Q, R171, R50, R151, R172, etc. |
| `status` | Enum(FluxStatus) | received, decrypted, parsed, error, skipped |
| `error_message` | Text, nullable | Message d'erreur si status=error |
| `measures_count` | Integer | Nombre de mesures extraites |
| `received_at` | DateTime | Date de réception/traitement |
| `created_at` | DateTime | Timestamp de création en base |

Contraintes :
- **Unique** sur `file_hash` (idempotence fichier)
- Index sur `flux_type`, `status`

#### `enedis_flux_mesure` — Mesures brutes

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `flux_file_id` | FK → enedis_flux_file | Fichier source |
| `point_id` | String, nullable | PRM 14 chiffres (R171) ou identifiant agrégé (R4) ou NULL si absent |
| `horodatage` | DateTime (timezone-aware) | Timestamp de la mesure |
| `valeur` | Float | Valeur mesurée |
| `unite` | String | kW, kWh, etc. — tel que dans le XML |
| `nature` | String | Nature de la donnée (réelle, estimée, corrigée, absente) — tel que dans le XML |
| `cadence` | String | Pas de mesure (10min, 30min, horaire, etc.) — tel que dans le XML |
| `flux_type` | Enum(FluxType) | Type de flux (dénormalisé depuis `enedis_flux_file` pour simplifier les contraintes d'unicité et les requêtes) |
| `extra_data` | JSON, nullable | Tout champ XML non mappé en colonne |
| `created_at` | DateTime | Timestamp de création |

**Colonne `flux_type` dénormalisée** : bien que `flux_type` soit aussi sur `enedis_flux_file`, il est dupliqué sur `enedis_flux_mesure` car il est nécessaire dans les contraintes d'unicité et les requêtes analytiques. L'agent doit s'assurer que la valeur est cohérente avec celle du fichier parent.

Contraintes d'unicité — **adapter selon le type de flux** :
- **R171** (par PRM) : unique sur `(point_id, horodatage, flux_type)`
- **R4** (agrégé, sans PRM) : unique sur `(horodatage, flux_type)` — car il n'y a qu'une valeur agrégée par timestamp et par type de flux

Stratégie d'implémentation pour gérer les deux cas :
- Contrainte unique composite sur `(point_id, horodatage, flux_type)` — pour R4, `point_id` sera une valeur sentinelle fixe (ex: `"AGGREGATE"`) plutôt que NULL (les NULL ne sont pas comparables dans les contraintes unique en SQL)
- `INSERT OR IGNORE` / `ON CONFLICT DO NOTHING` pour gérer les doublons silencieusement

**L'objectif est double** : pas de doublon si on ré-importe le même fichier, ET pas de doublon si Enedis re-publie les mêmes données dans un fichier différent.

### Enums

```python
# backend/data_ingestion/enedis/enums.py (étendre les enums de SF1)

class FluxStatus(str, Enum):
    RECEIVED = "received"
    DECRYPTED = "decrypted"
    PARSED = "parsed"
    ERROR = "error"
    SKIPPED = "skipped"

class NatureMesure(str, Enum):
    """Valeurs possibles — à compléter après analyse du XML réel."""
    REELLE = "reelle"
    ESTIMEE = "estimee"
    CORRIGEE = "corrigee"
    ABSENTE = "absente"
    # Ajouter d'autres valeurs découvertes dans le XML

class CadenceMesure(str, Enum):
    MIN10 = "10min"
    MIN30 = "30min"
    HORAIRE = "horaire"
    JOURNALIER = "journalier"
    MENSUEL = "mensuel"
```

**Note** : Les valeurs exactes des enums `NatureMesure` et `CadenceMesure` doivent être alignées sur ce que le XML contient réellement. L'agent doit inspecter les XML déchiffrés et adapter les enums en conséquence. Si les valeurs XML sont des codes Enedis (ex: `"RE"`, `"ES"`), stocker les codes bruts et documenter la correspondance.

## Parsers XML

### Architecture des parsers

```python
# backend/data_ingestion/enedis/parsers/base.py

@dataclass
class ParsedMesure:
    point_id: str | None     # PRM ou None pour les flux agrégés
    horodatage: datetime     # timezone-aware
    valeur: float
    unite: str
    nature: str
    cadence: str
    extra_data: dict | None  # Champs XML non mappés

class BaseParser(ABC):
    @abstractmethod
    def parse(self, xml_content: bytes) -> list[ParsedMesure]:
        """Parse le XML et retourne la liste des mesures.

        Retourne une liste vide (pas d'exception) si le XML est valide mais ne contient aucune mesure.
        """
```

### Parsers à implémenter

| Parser | Fichier | Flux | Particularité |
|--------|---------|------|---------------|
| `R4Parser` | `parsers/r4.py` | R4H, R4M, R4Q | Même structure XML, cadence différente. Flux **agrégé** (pas de PRM) |
| `R171Parser` | `parsers/r171.py` | R171 | CDC par **PRM individuel** |

Les parsers doivent :
- Utiliser `xml.etree.ElementTree` (stdlib, pas de dépendance externe)
- Être tolérants aux variantes de namespaces Enedis
- Extraire **tous** les champs présents dans le XML (les non-mappés vont dans `extra_data`)
- Retourner `[]` (liste vide) si le XML est valide mais ne contient aucune mesure — **pas d'exception**

### Tolérance aux préfixes historiques

Certains flux utilisent le préfixe `ERDF_` au lieu de `ENEDIS_` (héritage historique). Les parsers doivent tolérer les deux sans erreur.

## Pipeline d'ingestion CDC

```python
# backend/data_ingestion/enedis/pipeline.py

def ingest_file(file_path: Path, session: Session) -> FluxStatus:
    """Pipeline complet : fichier chiffré → base de données.

    1. Classifier le flux (nom de fichier)
    2. Vérifier idempotence (hash SHA256)
    3. Déchiffrer (via decrypt.py de SF1)
    4. Vérifier que le résultat est du XML valide
    5. Sélectionner le parser approprié
    6. Parser le XML → liste de ParsedMesure
    7. Insérer en base (batch insert, chunks)
    8. Mettre à jour le status du fichier

    Returns: FluxStatus final (parsed, error, skipped)
    """
```

### Idempotence (double protection)

1. **Niveau fichier** : hash SHA256 du fichier chiffré.
   - Si `file_hash` existe déjà en base avec `status=parsed` → skip immédiat (no-op)
   - Si `file_hash` existe avec `status=error` → **retry** : supprimer l'ancien enregistrement (et ses mesures éventuelles) et retraiter le fichier depuis le début. Un fichier en erreur peut être corrigé par une mise à jour de clé ou de code.
   - Si `file_hash` existe avec `status=skipped` → skip (le type de flux n'a pas changé)
2. **Niveau mesure** : contrainte d'unicité en base. Si Enedis re-publie les mêmes données dans un fichier différent (hash différent), les mesures en doublon sont ignorées via `INSERT OR IGNORE` / `ON CONFLICT DO NOTHING`

### Performance

- Batch insert des mesures par chunks (taille configurable, défaut ~1000)
- Target : supporter ~480 000 mesures/jour à terme (10 000 PRM × 48 points/jour)
- Index composites sur `(point_id, horodatage)` et `(flux_file_id)`

## Variables d'environnement

| Variable | Obligatoire | Description |
|----------|------------|-------------|
| `KEY_1`..`KEY_3` / `IV_1`..`IV_3` | Oui | 3 paires clé/IV AES (hex-encoded) — chargées via `load_keys_from_env()` |
| `ENEDIS_ARCHIVE_DIR` | Non | Archivage XML (via SF1) |

## Matrice d'erreurs

| Scénario | Comportement | Status |
|----------|-------------|--------|
| Fichier introuvable | Lever `FileNotFoundError` | n/a |
| Clés absentes | Lever `MissingKeyError` (via SF1) | n/a |
| Mauvaise clé (garbage post-décrypt) | Enregistrer fichier avec erreur | error |
| XML invalide après décrypt | Enregistrer fichier avec erreur | error |
| Type de flux inconnu (R172, X14, HDM) | Enregistrer fichier avec status skipped | skipped |
| Fichier déjà traité (même hash, status=parsed) | No-op, ne pas ré-enregistrer | inchangé |
| Fichier déjà connu (même hash, status=error) | Retry : supprimer l'ancien enregistrement et retraiter | selon résultat |
| Fichier valide, 0 mesures | Enregistrer fichier avec status parsed, measures_count=0 | parsed |
| Erreur DB pendant l'insert | Rollback, enregistrer fichier avec erreur | error |
| Doublon de mesure (même PRM+horodatage) | `INSERT OR IGNORE` — silencieux | parsed |

## Arborescence cible

```
backend/
  data_ingestion/
    __init__.py              # (SF1 — ne pas modifier)
    enedis/
      __init__.py            # (SF1 — ne pas modifier)
      enums.py               # FluxType (SF1) + FluxStatus, NatureMesure, CadenceMesure (SF2)
      decrypt.py             # (SF1 — ne pas modifier)
      models.py              # EnedisFluxFile, EnedisFluxMesure
      pipeline.py            # ingest_file()
      parsers/
        __init__.py
        base.py              # BaseParser, ParsedMesure
        r4.py                # R4Parser (R4H/R4M/R4Q)
        r171.py              # R171Parser
      tests/
        __init__.py          # (SF1 — ne pas modifier)
        conftest.py          # (SF1 — étendre avec fixtures DB)
        test_decrypt.py      # (SF1 — ne pas modifier)
        test_integration.py  # (SF1 — ne pas modifier)
        test_parsers_cdc.py  # (SF2)
        test_pipeline_cdc.py # (SF2)
        test_models.py       # (SF2)
```

## Tests

### Tests unitaires — Parsers (`test_parsers_cdc.py`)

1. **R4Parser** : déchiffrer un fichier R4H réel (ou fixture synthétique), vérifier que les mesures extraites ont les bons champs (pas de PRM, valeur, horodatage, unité, nature)
2. **R4Parser cadences** : vérifier que R4H, R4M, R4Q sont correctement différenciés
3. **R171Parser** : déchiffrer un fichier R171, vérifier PRM présent, mesures correctes
4. **Parser XML vide** : XML valide sans mesures → `[]` (pas d'exception)
5. **Parser namespace variants** : tester avec et sans namespace XML

### Tests unitaires — Modèle (`test_models.py`)

1. **Création de fichier** : insérer un `EnedisFluxFile`, vérifier les champs
2. **Contrainte hash unique** : insérer deux fichiers avec le même hash → erreur d'intégrité
3. **Contrainte unicité mesure** : insérer deux mesures identiques → une seule en base

### Tests d'intégration — Pipeline (`test_pipeline_cdc.py`)

1. **Pipeline complet R171** : fixture chiffrée (clé de test) → `ingest_file` → mesures en base
2. **Pipeline complet R4H** : idem pour flux agrégé
3. **Idempotence fichier** : `ingest_file` × 2 sur le même fichier → 0 nouvelle mesure
4. **Idempotence mesure** : même donnée dans deux fichiers différents → pas de doublon
5. **Fichier corrompu** : → status=error, message informatif
6. **Fichier R172** : → status=skipped, 0 mesure
7. **Fichier valide, 0 mesures** : → status=parsed, measures_count=0

## Contraintes d'architecture

1. **Isolation totale** : module `backend/data_ingestion/enedis/` — aucune dépendance ni modification des modèles existants (Meter, MeterReading, Consommation, Compteur)
2. **Pas de routes API** dans cette feature — le pipeline est appelable programmatiquement
3. **SQLAlchemy** pour les modèles, cohérent avec le reste du backend
4. **Les tables staging sont permanentes** — ce ne sont pas des tables temporaires, elles sont la trace audit des flux reçus
5. **Scalabilité** : index composites sur `(point_id, horodatage)` et `(flux_file_id)`
6. **Les tests existants ne doivent pas casser** : `pytest backend/tests/ -x` ET `pytest backend/data_ingestion/ -x`

## Challenges intégrés

| Pattern | Point de vigilance |
|---------|-------------------|
| **Threshold Fairness** | Les flux R4 sont agrégés (pas de PRM individuel). La contrainte d'unicité doit en tenir compte — on ne peut pas utiliser `(point_id, horodatage)` si `point_id` est NULL pour tous les R4 |
| **Silent Self-Defeat** | Double idempotence obligatoire : hash fichier + contrainte unique mesure. Si Enedis re-publie les mêmes données dans un fichier différent, on ne duplique pas les mesures |
| **Boundary Behavior** | 0 mesures = parsed, pas error. Le parser retourne une liste vide sans exception. Le pipeline enregistre le fichier avec `measures_count=0` et `status=parsed` |
| **Misuse Surface** | Vérifier que le contenu déchiffré est du XML valide **avant** de le passer aux parsers. Ne jamais passer du garbage aux parsers |
| **Metric Validity** | Les tests doivent couvrir tous les types de flux CDC, pas seulement R171 |
