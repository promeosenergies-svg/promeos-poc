# Feature Spec : Ingestion des flux Index (C5) — R50 et R151

> **Sub-feature 3/3** — Dépend de SF1 (déchiffrement) et SF2 (modèle + pipeline CDC).
> Chaîne : SF1 (decrypt) → SF2 (ingestion CDC) → **SF3 (ingestion Index)**

## Contexte

Les SF1 et SF2 ont livré le module de déchiffrement, le modèle de données staging, les parsers CDC, et le pipeline d'ingestion. Cette sub-feature étend le pipeline pour supporter les flux C5 (index de consommation) : R50 et R151.

### Ce que cette sub-feature doit livrer

- Parsers XML pour R50 et R151
- Extension du pipeline pour traiter les flux C5
- Extension du modèle si la structure XML C5 diffère significativement de CDC
- Tests d'intégration couvrant **tous** les types de flux (CDC + Index) dans un même batch

## Vocabulaire Enedis

| Terme | Signification |
|-------|--------------|
| **C5** | Segment résidentiel/petit tertiaire — comptage par index (pas de CDC native) |
| **R50** | Index de consommation mensuels par PRM |
| **R151** | Relevés trimestriels par PRM |
| **Index** | Valeur cumulée du compteur à un instant donné (en kWh) — contrairement à la CDC qui donne la puissance/énergie par intervalle |
| **ERDF** | Ancien nom d'Enedis — les flux C5 utilisent le préfixe historique `ERDF_` dans les noms de fichier |

## Flux en scope

| Flux | Contenu | Granularité | Cadence | Préfixe fichier |
|------|---------|-------------|---------|-----------------|
| **R50** | Index mensuels | Par PRM | Mensuel | `ERDF_R50_` |
| **R151** | Relevés trimestriels | Par PRM | Trimestriel | `ERDF_R151_` |

### Particularités des flux C5

- **Préfixe historique** : les fichiers C5 utilisent `ERDF_` (pas `ENEDIS_`). La classification (SF1) gère déjà cela, mais les parsers XML doivent aussi tolérer les deux préfixes/namespaces dans le contenu XML.
- **Structure différente de la CDC** : les index ne sont pas des séries temporelles à pas régulier. Un index est une valeur cumulée à un instant donné. Le modèle `EnedisFluxMesure` de SF2 peut nécessiter une adaptation (colonne `type_mesure` : "index" vs "cdc", ou table séparée si la structure diverge trop).

## Extension du modèle de données

### Décision à prendre par l'agent

Après analyse des fixtures XML `r50_sample.xml` et `r151_sample.xml` (produites par SF1), l'agent doit décider :

**Option A** — Réutiliser `EnedisFluxMesure` tel quel :
- Si les champs existants (`point_id`, `horodatage`, `valeur`, `unite`, `nature`, `cadence`, `extra_data`) suffisent à stocker les index C5 sans perte d'information
- Ajouter une colonne discriminante si nécessaire (ex: `type_mesure`)

**Option B** — Créer une table `EnedisFluxIndex` dédiée :
- Si la structure XML C5 est fondamentalement différente (ex: multiples index par PRM par relevé, cadres tarifaires, etc.)
- La table partage la FK vers `enedis_flux_file`

**Critère de décision** : la fidélité. L'option qui conserve le plus d'information brute sans forçage est la bonne.

### Contrainte d'unicité pour les flux C5

Les flux C5 sont par PRM individuel. La contrainte d'unicité utilise la colonne `flux_type` dénormalisée sur `enedis_flux_mesure` (introduite en SF2) :
- `(point_id, horodatage, flux_type)` — même contrainte composite que R171
- Même logique que R171 (par PRM), contrairement aux R4 (agrégés, `point_id="AGGREGATE"`)

## Parsers XML

### Parsers à implémenter

| Parser | Fichier | Flux | Particularité |
|--------|---------|------|---------------|
| `R50Parser` | `parsers/r50.py` | R50 | Index mensuels par PRM |
| `R151Parser` | `parsers/r151.py` | R151 | Relevés trimestriels par PRM |

Les parsers doivent :
- Utiliser `xml.etree.ElementTree` (stdlib)
- Être tolérants aux namespaces `ERDF` et `ENEDIS` dans le contenu XML
- Extraire **tous** les champs présents dans le XML (les non-mappés vont dans `extra_data`)
- Retourner `[]` (liste vide) si le XML est valide mais ne contient aucune mesure — **pas d'exception**

### Tolérance aux préfixes historiques

Les flux C5 utilisent systématiquement `ERDF_` dans les noms de fichier. Le contenu XML peut aussi utiliser des namespaces ou des noms d'éléments avec le préfixe ERDF. Les parsers doivent gérer les deux variantes sans distinction.

## Extension du pipeline

Le pipeline `ingest_file()` de SF2 doit être étendu pour :

1. **Reconnaître R50 et R151** dans le dispatch des parsers
2. **Sélectionner le bon parser** selon le `FluxType`
3. **Insérer les mesures** dans la bonne table (si Option B) ou avec le bon discriminant (si Option A)

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
| Fichier déjà traité (même hash, status=parsed) | No-op | inchangé |
| Fichier déjà connu (même hash, status=error) | Retry : supprimer l'ancien enregistrement et retraiter | selon résultat |
| Fichier valide, 0 mesures | Enregistrer fichier, measures_count=0 | parsed |
| Erreur DB pendant l'insert | Rollback, enregistrer fichier avec erreur | error |
| Doublon de mesure (même PRM+horodatage) | `INSERT OR IGNORE` — silencieux | parsed |

## Arborescence cible (état final après SF3)

```
backend/
  enedis/
    __init__.py
    enums.py           # FluxType, FluxStatus, NatureMesure, CadenceMesure
    decrypt.py         # (SF1)
    models.py          # EnedisFluxFile, EnedisFluxMesure (+ EnedisFluxIndex si Option B)
    pipeline.py        # ingest_file(), ingest_directory()
    parsers/
      __init__.py
      base.py          # BaseParser, ParsedMesure (SF2)
      r4.py            # R4Parser (SF2)
      r171.py          # R171Parser (SF2)
      r50.py           # R50Parser (SF3)
      r151.py          # R151Parser (SF3)
    tests/
      __init__.py
      test_decrypt.py       # (SF1)
      test_parsers_cdc.py   # (SF2)
      test_parsers_index.py # (SF3)
      test_pipeline_cdc.py  # (SF2)
      test_pipeline_full.py # (SF3) — tous les types de flux
      test_models.py        # (SF2, étendu en SF3)
      conftest.py
      fixtures/
        r4h_sample.xml     # (SF1)
        r4m_sample.xml     # (SF1)
        r4q_sample.xml     # (SF1)
        r171_sample.xml    # (SF1)
        r50_sample.xml     # (SF1)
        r151_sample.xml    # (SF1)
```

## Tests

### Tests unitaires — Parsers (`test_parsers_index.py`)

1. **R50Parser** : charger `r50_sample.xml`, vérifier que les mesures extraites ont PRM, horodatage, valeur index, unité
2. **R151Parser** : charger `r151_sample.xml`, vérifier extraction correcte
3. **Parser namespace ERDF** : vérifier que les parsers fonctionnent avec les namespaces `ERDF` historiques
4. **Parser XML vide** : XML valide sans mesures → `[]` (pas d'exception)

### Tests d'intégration — Pipeline complet (`test_pipeline_full.py`)

1. **Batch mixte** : répertoire contenant des fichiers R4H, R171, R50, R151, R172 → tous traités correctement, R172 skipped
2. **Idempotence batch** : exécuter `ingest_directory` × 2 sur le même répertoire → 0 nouvelle mesure
3. **Résilience globale** : mix de fichiers valides, corrompus, et hors-scope → les valides sont parsed, les corrompus sont error, les hors-scope sont skipped. Aucun crash.
4. **Pipeline complet R50** : fixture chiffrée (clé de test) → `ingest_file` → mesures index en base
5. **Pipeline complet R151** : idem
6. **Requête cross-flux** : après ingestion de tous les types, vérifier qu'on peut requêter par PRM sur les données R171 + R50 + R151

### Test de non-régression

- **Tous les tests SF1 et SF2 doivent continuer à passer**
- **Les tests existants du POC ne doivent pas casser** : `pytest backend/tests/ -x`

## Contraintes d'architecture

1. **Isolation totale** : module `backend/enedis/` — aucune dépendance ni modification des modèles existants
2. **Pas de routes API** dans cette feature
3. **SQLAlchemy** pour les modèles, cohérent avec le reste du backend
4. **Les tables staging sont permanentes**
5. **Les tests existants du POC ne doivent pas casser** : `pytest backend/tests/ -x`
6. **Les tests SF1 et SF2 ne doivent pas casser** : `pytest backend/enedis/tests/ -x`

## Challenges intégrés

| Pattern | Point de vigilance |
|---------|-------------------|
| **Metric Validity** | Les tests d'intégration doivent couvrir TOUS les types de flux (R4H, R4M, R4Q, R171, R50, R151), pas seulement les nouveaux |
| **Threshold Fairness** | Les flux C5 sont par PRM (comme R171), contrairement aux R4 agrégés. La contrainte d'unicité doit être cohérente |
| **Silent Self-Defeat** | La double idempotence (hash + unicité mesure) doit fonctionner aussi pour les flux C5 |
| **Boundary Behavior** | `ingest_directory` avec un répertoire contenant uniquement des fichiers hors-scope → retourne `{"parsed": 0, "skipped": N}`, pas d'erreur |
| **Misuse Surface** | Le préfixe `ERDF_` ne doit pas être traité comme un format inconnu — les parsers et la classification doivent le supporter nativement |
