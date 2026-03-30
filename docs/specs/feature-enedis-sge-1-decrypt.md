# Feature Spec : Déchiffrement et classification des flux SGE Enedis

> **Sub-feature 1/3** — **COMPLÉTÉE le 2026-03-23**
> PR : [#148](https://github.com/promeosenergies-svg/promeos-poc/pull/148) (`feat/enedis-sge-1-decrypt` → `feat/enedis-sge-ingestion`)
> Chaîne : **SF1 (decrypt)** ✅ → SF2 (ingestion CDC) → SF3 (ingestion Index)

---

## Résultat de l'implémentation

### Ce qui a été livré

| Livrable | Statut | Détail |
|----------|--------|--------|
| Module `backend/data_ingestion/enedis/` | ✅ | Nouveau module isolé sous `data_ingestion/` (pas `backend/enedis/` comme le spec initial proposait) |
| `decrypt_file()` | ✅ | AES-128-CBC + PKCS7, essai séquentiel de 3 paires KEY/IV |
| `classify_flux()` | ✅ | Pattern matching sur le nom de fichier → `FluxType` |
| `load_keys_from_env()` | ✅ | Chargement KEY_1/IV_1..KEY_3/IV_3 avec validation paires partielles |
| `FluxType` enum | ✅ | 10 valeurs (6 in-scope + 4 skip) |
| Tests unitaires | ✅ | 26 tests avec fixtures AES synthétiques |
| Tests intégration | ✅ | 8 tests sur les 91 vrais fichiers (skip si pas de clés) |
| Fixtures XML commitées | ❌ | **Décision utilisateur** : ne pas committer les fichiers déchiffrés. Les tests d'intégration utilisent les vrais fichiers avec skip si non disponibles. |

### Discovery AES (2026-03-23)

| Propriété | Valeur trouvée |
|-----------|---------------|
| Algorithme | **AES-128-CBC** avec padding **PKCS7** |
| Clés | **3 paires KEY/IV** (hex-encoded, 16 bytes chacune) |
| Post-decrypt | **Toujours un ZIP** contenant un seul XML (jamais du XML direct dans les fichiers réels) |
| Mapping clé→flux | **Non déterministe** — R4Q utilise KEY_2 ou KEY_3 selon le fichier. Le code essaie les 3 clés séquentiellement. |
| Taux de succès | **91/91 fichiers** in-scope (100%) |

Mapping observé (non garanti stable) :

| Clé | Flux types |
|-----|-----------|
| KEY_1 / IV_1 | R151 |
| KEY_2 / IV_2 | R4Q (4/8), R50 |
| KEY_3 / IV_3 | R4H, R4M, R4Q (4/8), R171 |

### Variables d'environnement (réalité vs spec)

Le spec initial prévoyait une seule `ENEDIS_DECRYPT_KEY`. La réalité est **6 variables** :

| Variable | Format | Description |
|----------|--------|-------------|
| `KEY_1` | hex 32 chars | Clé AES #1 |
| `IV_1` | hex 32 chars | IV #1 |
| `KEY_2` | hex 32 chars | Clé AES #2 |
| `IV_2` | hex 32 chars | IV #2 |
| `KEY_3` | hex 32 chars | Clé AES #3 |
| `IV_3` | hex 32 chars | IV #3 |
| `ENEDIS_ARCHIVE_DIR` | chemin (optionnel) | Répertoire d'archivage XML |

Les clés sont dans `backend/.env` (non committées, `.gitignore`).

### Comptage réel des fichiers

```
flux_enedis/
  C1-C4/  (98 fichiers)
    R4H:   5 fichiers
    R4M:   4 fichiers
    R4Q:   8 fichiers
    R171: 64 fichiers
    R172: 15 fichiers (skip — binaire)
  C5/     (10 fichiers)
    R50:   5 fichiers
    R151:  5 fichiers
  (root)  (6 fichiers)
    X14:   3 fichiers (skip)
    HDM:   3 fichiers CSV (skip — PGP)
```

### Structure XML découverte

| Flux | Racine XML | Namespace | Taille typique |
|------|-----------|-----------|---------------|
| R4H/R4M/R4Q | `<Courbe>` | Aucun | 25 Ko – 700 Ko |
| R171 | `<ns2:R171>` | `http://www.enedis.fr/stm/R171` | ~58 Ko |
| R50 | `<R50>` | xsi schema | ~668 Ko |
| R151 | `<R151>` | xsi schema | ~3 Ko |

### Arborescence livrée

```
backend/
  data_ingestion/
    __init__.py
    enedis/
      __init__.py
      enums.py             # FluxType (10 valeurs)
      decrypt.py           # decrypt_file(), classify_flux(), load_keys_from_env()
                           # + DecryptError, MissingKeyError, SKIP_FLUX_TYPES
      tests/
        __init__.py
        conftest.py        # Fixtures AES synthétiques, load_dotenv
        test_decrypt.py    # 26 tests unitaires
        test_integration.py # 8 tests intégration (vrais fichiers)
```

### API publique pour SF2/SF3

```python
from data_ingestion.enedis.enums import FluxType
from data_ingestion.enedis.decrypt import (
    decrypt_file,       # (Path, keys: list[tuple[bytes,bytes]], archive_dir?) -> bytes (XML)
    classify_flux,      # (filename: str) -> FluxType
    load_keys_from_env, # () -> list[tuple[bytes,bytes]]  (lève MissingKeyError)
    SKIP_FLUX_TYPES,    # frozenset{R172, X14, HDM, UNKNOWN}
    DecryptError,       # déchiffrement échoué
    MissingKeyError,    # clés absentes ou invalides
)
```

### Commandes de test

```bash
# Tests SF1 uniquement (unitaires + intégration)
cd promeos-poc && ./backend/venv/bin/pytest backend/data_ingestion/ -x -v

# Vérifier non-régression backend existant
cd promeos-poc && ./backend/venv/bin/pytest backend/tests/ -x
```

### Dépendances ajoutées

- `cryptography>=42.0.0` ajouté dans `backend/requirements.txt`
- `data_ingestion` ajouté dans `known-first-party` de `pyproject.toml`

---

## Spec original (pour référence)

Le reste du document ci-dessous est le spec original tel qu'il a été rédigé avant implémentation. Les sections marquées `[CORRIGÉ]` indiquent les écarts avec la réalité.

### Contexte

Promeos reçoit les flux SGE Enedis sous forme de fichiers chiffrés en AES symétrique. Cette sub-feature est la brique fondatrice : elle déchiffre les fichiers, classifie le type de flux, et produit les fixtures XML sanitisées nécessaires aux sub-features suivantes.

### Écarts entre le spec et l'implémentation

| Spec original | Réalité |
|--------------|---------|
| Module dans `backend/enedis/` | `backend/data_ingestion/enedis/` (préparation pour d'autres sources futures) |
| Une seule clé `ENEDIS_DECRYPT_KEY` | 3 paires KEY_1/IV_1..KEY_3/IV_3 |
| Mode AES à découvrir (ECB, CBC...) | AES-128-CBC confirmé |
| Fichiers séparés `decrypt.py` + `classify.py` + `exceptions.py` | Tout dans `decrypt.py` (YAGNI) |
| Fixtures XML commitées dans le repo | Non commitées (décision utilisateur — fichiers sensibles) |
| Post-decrypt peut être XML direct ou ZIP | Toujours ZIP dans les vrais fichiers (mais le code gère les deux cas) |
