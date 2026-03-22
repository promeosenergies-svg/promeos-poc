# Feature Spec : Ingestion des flux Courbe De Charge (CDC) — R4 et R171

> **Sub-feature 2/3** — Dépend de SF1 (déchiffrement).
> Chaîne : SF1 (decrypt) → **SF2 (ingestion CDC)** → SF3 (ingestion Index)

## Contexte

La SF1 a produit le module de déchiffrement et les fixtures XML sanitisées. Cette sub-feature construit le modèle de données staging, les parsers XML pour les flux CDC, et le pipeline d'ingestion.

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

Stocker l'information brute des flux Enedis **le plus fidèlement possible**, sans transformation ni perte. Le modèle exact (champs, relations) doit être conçu après analyse de la structure XML réelle des fixtures produites par SF1.

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
# backend/enedis/enums.py (étendre les enums de SF1)

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

**Note** : Les valeurs exactes des enums `NatureMesure` et `CadenceMesure` doivent être alignées sur ce que le XML contient réellement. L'agent doit inspecter les fixtures XML de SF1 et adapter les enums en conséquence. Si les valeurs XML sont des codes Enedis (ex: `"RE"`, `"ES"`), stocker les codes bruts et documenter la correspondance.

## Parsers XML

### Architecture des parsers

```python
# backend/enedis/parsers/base.py

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
# backend/enedis/pipeline.py

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
| `ENEDIS_DECRYPT_KEY` | Oui | Clé AES (via SF1) |
| `ENEDIS_ARCHIVE_DIR` | Non | Archivage XML (via SF1) |

## Matrice d'erreurs

| Scénario | Comportement | Status |
|----------|-------------|--------|
| Fichier introuvable | Lever `FileNotFoundError` | n/a |
| `ENEDIS_DECRYPT_KEY` absente | Lever exception claire | n/a |
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
  enedis/
    __init__.py
    enums.py           # FluxType (SF1) + FluxStatus, NatureMesure, CadenceMesure (SF2)
    decrypt.py         # (SF1 — ne pas modifier)
    models.py          # EnedisFluxFile, EnedisFluxMesure
    pipeline.py        # ingest_file()
    parsers/
      __init__.py
      base.py          # BaseParser, ParsedMesure
      r4.py            # R4Parser (R4H/R4M/R4Q)
      r171.py          # R171Parser
    tests/
      __init__.py
      test_decrypt.py  # (SF1 — ne pas modifier)
      test_parsers_cdc.py
      test_pipeline_cdc.py
      test_models.py
      conftest.py      # Étendre avec fixtures DB
      fixtures/
        r4h_sample.xml   # (SF1)
        r4m_sample.xml   # (SF1)
        r4q_sample.xml   # (SF1)
        r171_sample.xml  # (SF1)
        r50_sample.xml   # (SF1 — pour SF3)
        r151_sample.xml  # (SF1 — pour SF3)
```

## Tests

### Tests unitaires — Parsers (`test_parsers_cdc.py`)

1. **R4Parser** : charger `r4h_sample.xml`, vérifier que les mesures extraites ont les bons champs (pas de PRM, valeur, horodatage, unité, nature)
2. **R4Parser cadences** : vérifier que R4H, R4M, R4Q sont correctement différenciés
3. **R171Parser** : charger `r171_sample.xml`, vérifier PRM présent, mesures correctes
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

1. **Isolation totale** : module `backend/enedis/` — aucune dépendance ni modification des modèles existants (Meter, MeterReading, Consommation, Compteur)
2. **Pas de routes API** dans cette feature — le pipeline est appelable programmatiquement
3. **SQLAlchemy** pour les modèles, cohérent avec le reste du backend
4. **Les tables staging sont permanentes** — ce ne sont pas des tables temporaires, elles sont la trace audit des flux reçus
5. **Scalabilité** : index composites sur `(point_id, horodatage)` et `(flux_file_id)`
6. **Les tests existants du POC ne doivent pas casser** : `pytest backend/tests/ -x`

## Challenges intégrés

| Pattern | Point de vigilance |
|---------|-------------------|
| **Threshold Fairness** | Les flux R4 sont agrégés (pas de PRM individuel). La contrainte d'unicité doit en tenir compte — on ne peut pas utiliser `(point_id, horodatage)` si `point_id` est NULL pour tous les R4 |
| **Silent Self-Defeat** | Double idempotence obligatoire : hash fichier + contrainte unique mesure. Si Enedis re-publie les mêmes données dans un fichier différent, on ne duplique pas les mesures |
| **Boundary Behavior** | 0 mesures = parsed, pas error. Le parser retourne une liste vide sans exception. Le pipeline enregistre le fichier avec `measures_count=0` et `status=parsed` |
| **Misuse Surface** | Vérifier que le contenu déchiffré est du XML valide **avant** de le passer aux parsers. Ne jamais passer du garbage aux parsers |
| **Metric Validity** | Les tests doivent couvrir tous les types de flux CDC, pas seulement R171 |
