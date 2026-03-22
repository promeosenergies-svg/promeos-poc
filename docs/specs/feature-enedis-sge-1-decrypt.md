# Feature Spec : Déchiffrement et classification des flux SGE Enedis

> **Sub-feature 1/3** — Aucune dépendance. First mover.
> Chaîne : **SF1 (decrypt)** → SF2 (ingestion CDC) → SF3 (ingestion Index)

## Contexte

Promeos reçoit les flux SGE Enedis sous forme de fichiers chiffrés en AES symétrique. Cette sub-feature est la brique fondatrice : elle déchiffre les fichiers, classifie le type de flux, et produit les fixtures XML sanitisées nécessaires aux sub-features suivantes.

### Ce que cette sub-feature doit livrer

Une fonction qui prend un fichier chiffré et retourne `(FluxType, xml_bytes)`.

## Vocabulaire Enedis

| Terme | Signification |
|-------|--------------|
| **PRM** | Point de Référence Mesure — identifiant unique 14 chiffres d'un point de livraison électrique |
| **CDC** | Courbe De Charge — série temporelle de puissance/énergie à pas fin |
| **SGE** | Système de Gestion des Echanges — plateforme Enedis de publication des flux B2B |
| **C1-C4** | Segments de comptage haute puissance (télérelevés, CDC disponible) |
| **C5** | Segment résidentiel/petit tertiaire (index mensuels) |

## Flux concernés par le déchiffrement

| Flux | Segment | Statut dans cette SF |
|------|---------|---------------------|
| **R4H, R4M, R4Q** | C1-C4 | Déchiffrer + classifier |
| **R171** | C1-C4 | Déchiffrer + classifier |
| **R50** | C5 | Déchiffrer + classifier |
| **R151** | C5 | Déchiffrer + classifier |
| **R172** | C1-C4 | Classifier → **skipped** (binaire non-XML) |
| **X14** | C1-C4 | Classifier → **skipped** (hors scope) |
| **HDM CSV** | — | Classifier → **skipped** (chiffré PGP, hors scope) |

## Fichiers d'exemple

Répertoire : `Promeos/flux_enedis/` (~114 fichiers)

```
flux_enedis/
  C1-C4/
    ENEDIS_R171_C_*.zip          # ~57 fichiers — CDC journalière par PRM
    ENEDIS_R172_*.zip            # ~17 fichiers — réconciliation (binaire, hors scope)
    ENEDIS_23X--*_R4H_CDC_*.zip  # R4H horaire
    ENEDIS_23X--*_R4M_CDC_*.zip  # R4M mensuel
    ENEDIS_23X--*_R4Q_CDC_*.zip  # R4Q trimestriel
    X14_*.zip                    # ~3 fichiers (hors scope)
  C5/
    ERDF_R50_*.zip               # ~5 fichiers — index mensuels (préfixe historique ERDF)
    ERDF_R151_*.zip              # ~5 fichiers — relevés trimestriels (préfixe historique ERDF)
    HDM_*.csv                    # ~3 fichiers — CSV chiffrés PGP (hors scope)
```

### Réalité du chiffrement (corrections factuelles)

Les fichiers `.zip` **ne sont pas des archives ZIP**. La commande `file` retourne `"data"`, pas `"Zip archive"`. Ce sont du **ciphertext AES brut**. Les tailles sont des multiples de 16 octets, confirmant un block cipher AES (ECB ou CBC).

**Séquence réelle** : déchiffrement AES → résultat. Le résultat post-décrypt peut être :
- Du XML directement
- Un ZIP contenant du XML

L'agent doit tester les deux cas après déchiffrement et adapter le code en conséquence.

**Il n'y a pas d'étape de "dézip" avant le déchiffrement.**

## Implémentation

### 1. Discovery du mode AES (première étape obligatoire)

L'agent doit déterminer empiriquement le mode AES en testant les fichiers réels de `Promeos/flux_enedis/`. Voici la procédure :

1. Lire la clé depuis `ENEDIS_DECRYPT_KEY` (tester les formats : hex string, base64, raw bytes)
2. Tester les modes AES dans cet ordre de probabilité :
   - **AES-CBC** avec IV = premiers 16 octets du fichier
   - **AES-ECB** (pas d'IV)
   - **AES-CBC** avec IV zéro
   - **AES-CBC** avec IV dérivé de la clé
3. Après déchiffrement, vérifier :
   - Le résultat commence par `<?xml` ou `PK` (signature ZIP)
   - Si `PK` : extraire le ZIP en mémoire, puis obtenir le XML
   - Si `<?xml` : utiliser tel quel
4. Valider sur au moins un fichier de **chaque** type de flux (R4H, R4M, R4Q, R171, R50, R151)
5. Documenter le mode trouvé dans un commentaire en tête de `decrypt.py`

**Critère de succès** : TOUS les fichiers d'un type donné déchiffrent avec succès, pas "au moins 1". Si certains fichiers d'un même type échouent, investiguer la raison (variante de format, fichier corrompu, etc.).

### 2. Module de déchiffrement (`decrypt.py`)

```python
def decrypt_file(file_path: Path, key: bytes) -> bytes:
    """Déchiffre un fichier SGE Enedis.

    Returns: contenu déchiffré (XML bytes ou ZIP bytes)
    Raises: DecryptError si le déchiffrement échoue
    """
```

- Lire la clé depuis l'env var `ENEDIS_DECRYPT_KEY`
- Appliquer le mode AES découvert en étape 1
- Gérer le padding PKCS7 (standard pour AES-CBC) ou absence de padding (ECB)
- Si le résultat post-décrypt est un ZIP → extraire le XML en mémoire
- **Validation post-décrypt** : vérifier que le contenu final est du XML valide (commence par `<?xml` ou `<` et est parsable). Si non → lever `DecryptError`

### 3. Classification des flux (`classify.py` ou dans `decrypt.py`)

```python
def classify_flux(filename: str) -> FluxType:
    """Identifie le type de flux à partir du nom de fichier."""
```

Règles de classification basées sur le nom de fichier :

| Pattern dans le nom | FluxType |
|---------------------|----------|
| `_R4H_CDC_` | `R4H` |
| `_R4M_CDC_` | `R4M` |
| `_R4Q_CDC_` | `R4Q` |
| `_R171_` ou `R171_C_` | `R171` |
| `_R50_` | `R50` |
| `_R151_` | `R151` |
| `_R172_` | `R172` (→ skipped) |
| `X14_` | `X14` (→ skipped) |
| `HDM_` | `HDM` (→ skipped) |
| Aucun match | `UNKNOWN` (→ skipped) |

Les types R172, X14, HDM et UNKNOWN sont des flux reconnus mais hors scope de parsing. Le pipeline les classifie sans tenter de les déchiffrer ni de les parser.

### 4. Archivage optionnel du XML déchiffré

Si la variable d'environnement `ENEDIS_ARCHIVE_DIR` est définie :
- Écrire le XML déchiffré dans ce répertoire
- Nom du fichier : même nom que l'original, extension remplacée par `.xml`
- Si `ENEDIS_ARCHIVE_DIR` est absente → pas d'archivage (comportement par défaut)

### 5. Production de fixtures XML

**Livrable critique pour les sub-features suivantes** : l'agent doit produire des fixtures XML déchiffrées et sanitisées (PRM anonymisés si nécessaire) pour chaque type de flux en scope. Ces fixtures seront commitées dans le repo pour servir de base aux tests des SF2 et SF3.

Emplacement : `backend/enedis/tests/fixtures/`

Fixtures attendues :
- `r4h_sample.xml`
- `r4m_sample.xml`
- `r4q_sample.xml`
- `r171_sample.xml`
- `r50_sample.xml`
- `r151_sample.xml`

### 6. Enums

```python
# backend/enedis/enums.py

class FluxType(str, Enum):
    R4H = "R4H"
    R4M = "R4M"
    R4Q = "R4Q"
    R171 = "R171"
    R50 = "R50"
    R151 = "R151"
    R172 = "R172"      # hors scope parsing
    X14 = "X14"        # hors scope parsing
    HDM = "HDM"        # hors scope parsing
    UNKNOWN = "UNKNOWN" # non reconnu
```

## Variables d'environnement

| Variable | Obligatoire | Description |
|----------|------------|-------------|
| `ENEDIS_DECRYPT_KEY` | Oui | Clé AES de déchiffrement. Format à déterminer lors de la discovery (hex, base64, raw) |
| `ENEDIS_ARCHIVE_DIR` | Non | Répertoire d'archivage des XML déchiffrés. Si absent, pas d'archivage |

## Dépendances Python

Le package `cryptography` est référencé dans `requirements.lock.txt` mais **n'est pas installé** dans le venv. L'agent doit :
1. Vérifier avec `pip list | grep cryptography`
2. Si absent : `pip install cryptography` et s'assurer qu'il est dans les requirements

## Matrice d'erreurs

| Scénario | Comportement | Status |
|----------|-------------|--------|
| Fichier introuvable | Lever `FileNotFoundError` (laisser l'appelant gérer) | n/a |
| `ENEDIS_DECRYPT_KEY` absente | Lever une exception claire (`MissingKeyError` ou `ValueError`) | n/a |
| Mauvaise clé (garbage post-décrypt) | Lever `DecryptError` | n/a |
| XML invalide après décrypt | Lever `DecryptError` | n/a |
| Type de flux R172 / X14 / HDM / UNKNOWN | Retourner le type, ne pas tenter de déchiffrer | skipped |

## Arborescence cible

```
backend/
  enedis/
    __init__.py
    enums.py           # FluxType (+ placeholder pour les enums des SF suivantes)
    decrypt.py         # decrypt_file(), classify_flux()
    tests/
      __init__.py
      test_decrypt.py
      conftest.py      # Fixtures : clé de test, fichiers chiffrés de test
      fixtures/
        r4h_sample.xml
        r4m_sample.xml
        r4q_sample.xml
        r171_sample.xml
        r50_sample.xml
        r151_sample.xml
```

## Tests

### Tests unitaires (`test_decrypt.py`)

1. **Test decrypt avec clé de test connue** : créer une fixture chiffrée avec une clé de test, vérifier que `decrypt_file` retourne le XML attendu
2. **Test classify_flux** : vérifier chaque pattern de nom de fichier → bon FluxType
3. **Test fichier corrompu** : contenu aléatoire → `DecryptError`
4. **Test mauvaise clé** : chiffrer avec clé A, déchiffrer avec clé B → `DecryptError`
5. **Test archivage** : avec `ENEDIS_ARCHIVE_DIR` défini, vérifier que le XML est écrit au bon endroit
6. **Test sans archivage** : sans `ENEDIS_ARCHIVE_DIR`, vérifier qu'aucun fichier n'est écrit

### Tests d'intégration (fichiers réels)

```python
@pytest.mark.skipif(not os.environ.get("ENEDIS_DECRYPT_KEY"), reason="No decrypt key")
def test_decrypt_real_files():
    """Déchiffre les fichiers réels de flux_enedis/ et vérifie le résultat."""
```

- Tester sur au moins un fichier de chaque type
- Vérifier que le résultat est du XML valide (parsable par `xml.etree.ElementTree`)

## Contraintes d'architecture

1. **Isolation totale** : nouveau module `backend/enedis/` — aucune dépendance ni modification des modèles existants
2. **Pas de routes API** dans cette feature
3. **Pas de modèle SQLAlchemy** dans cette sub-feature (introduit en SF2)
4. **Les tests existants du POC ne doivent pas casser** : `pytest backend/tests/ -x`

## Challenges intégrés

| Pattern | Point de vigilance |
|---------|-------------------|
| **Metric Validity** | Le critère est "TOUS les fichiers d'un type déchiffrent", pas "au moins 1". Si un R171 sur 57 échoue, investiguer pourquoi |
| **Misuse Surface** | Toujours valider que le contenu déchiffré est du XML avant de le retourner. Ne jamais passer du garbage aux parsers |
| **Boundary Behavior** | Un fichier R172 ou X14 ne doit pas provoquer d'erreur — il est classifié et ignoré proprement |
