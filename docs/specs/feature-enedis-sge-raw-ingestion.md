# [ARCHIVÉ] Feature Spec : Ingestion des flux SGE Enedis — Structure de données brute

> **Ce spec est archivé.** Il a été scindé en 3 sub-features ciblées après corrections factuelles.
>
> Consulter les specs actifs :
> 1. [`feature-enedis-sge-1-decrypt.md`](feature-enedis-sge-1-decrypt.md) — Déchiffrement et classification
> 2. [`feature-enedis-sge-2-ingestion-cdc.md`](feature-enedis-sge-2-ingestion-cdc.md) — Ingestion CDC (R4 + R171)
> 3. [`feature-enedis-sge-3-ingestion-index.md`](feature-enedis-sge-3-ingestion-index.md) — Ingestion Index (R50 + R151)
>
> **Corrections factuelles principales** :
> - Les `.zip` sont du ciphertext AES brut (pas des archives ZIP)
> - La séquence est déchiffrement AES → XML (pas dézip → déchiffrement)
> - `cryptography` n'est pas installé dans le venv malgré `requirements.lock.txt`
> - Décompte réel : ~98 C1-C4, 10 C5, 3 X14, 3 HDM CSV (pas 114 fichiers homogènes)
> - X14 et HDM CSV existent mais n'étaient pas mentionnés
> - R172 contient du binaire illisible (pas dézippable)

---

## Contexte (original)

Promeos fonctionne avec des données de consommation synthétiques (seed). Pour passer en production, la plateforme doit ingérer les **flux réels Enedis SGE** (Système de Gestion des Echanges) qui sont la source de vérité pour toute la chaîne : analytics, anomalies, monitoring, facturation.

En tant que fournisseur d'énergie, Promeos a accès aux flux SGE publiés par Enedis en FTP. Cette feature est la **première brique** d'un pipeline plus large. Elle se concentre exclusivement sur : déchiffrer les fichiers, parser le XML, et stocker les données brutes dans un modèle dédié.

## Vocabulaire Enedis

| Terme | Signification |
|-------|--------------|
| **PRM** | Point de Référence Mesure — identifiant unique 14 chiffres d'un point de livraison électrique |
| **CDC** | Courbe De Charge — série temporelle de puissance/énergie à pas fin (10min, 30min, horaire) |
| **SGE** | Système de Gestion des Echanges — plateforme Enedis de publication des flux B2B |
| **C1-C4** | Segments de comptage haute puissance (télérelevés, CDC disponible) |
| **C5** | Segment résidentiel/petit tertiaire (index mensuels, pas de CDC native) |

## Flux en scope

| Flux | Contenu | Segment | Cadence | Format déchiffré |
|------|---------|---------|---------|-----------------|
| **R4H** | CDC horaire agrégée (ensemble du périmètre fournisseur) | C1-C4 | Quotidien | XML |
| **R4M** | CDC mensuelle agrégée | C1-C4 | Mensuel | XML |
| **R4Q** | CDC trimestrielle agrégée | C1-C4 | Trimestriel | XML |
| **R171** | CDC journalière par PRM individuel | C1-C4 | Quotidien | XML |
| **R50** | Index de consommation mensuel | C5 | Mensuel | XML |
| **R151** | Relevés trimestriels | C5 | Trimestriel | XML |

**Hors scope de cette feature :**
- SGE HDM (exports CSV portail) → feature séparée
- Puissance souscrite → feature séparée
- Historique 36 mois (backfill) → feature séparée
- WS SOAP (appels webservice temps réel) → évolution future
- Normalisation des données brutes vers MeterReading → feature séparée (Feature 3)
- Import automatisé FTP / orchestration de jobs → feature séparée (Feature 2)
- Frontend / affichage → hors scope

## Fichiers d'exemple

Répertoire : `Promeos/flux_enedis/` (114 fichiers)

```
flux_enedis/
  C1-C4/
    ENEDIS_R171_C_*.zip          # 57 fichiers — CDC journalière par PRM
    ENEDIS_R172_*.zip            # 17 fichiers — réconciliation (hors scope parsing, mais dézippable)
    ENEDIS_23X--*_R4H_CDC_*.zip  # R4H horaire
    ENEDIS_23X--*_R4M_CDC_*.zip  # R4M mensuel
    ENEDIS_23X--*_R4Q_CDC_*.zip  # R4Q trimestriel
  C5/
    ERDF_R50_*.zip               # 5 fichiers — index mensuels
    ERDF_R151_*.zip              # 5 fichiers — relevés trimestriels
```

**Chiffrement** : Les fichiers ZIP contiennent des données chiffrées en **AES symétrique**. La clé de déchiffrement est fournie via la variable d'environnement `ENEDIS_DECRYPT_KEY`.

**Important** : Le mode AES exact (CBC, ECB, GCM), le format de la clé (hex, base64, raw), et la présence éventuelle d'un IV/nonce sont à identifier en déchiffrant un premier fichier. C'est la première étape de l'implémentation.

## Ce que cette feature doit produire

### 1. Module de déchiffrement (`decrypt`)
- Input : chemin vers un fichier `.zip` Enedis
- Output : contenu XML déchiffré
- Étapes : dézip (gérer les zips imbriqués) → déchiffrement AES → XML brut
- Le XML déchiffré doit aussi être archivé dans un répertoire configurable (`ENEDIS_ARCHIVE_DIR` env var) pour audit et re-processing

### 2. Parsers XML (un par type de flux)
- Input : contenu XML déchiffré
- Output : données structurées (liste de points de mesure avec leurs valeurs)
- Un parser par famille de flux : R4 (R4H/R4M/R4Q), R171, R50, R151
- Les parsers doivent être tolérants aux variantes de schemas Enedis (namespaces, versions)
- Extraction minimale requise pour chaque mesure :
  - **PRM** (identifiant du point)
  - **Horodatage** (datetime, timezone-aware)
  - **Valeur** (float, en kW ou kWh selon le flux)
  - **Unité** (kW, kWh)
  - **Nature** de la donnée (réelle, estimée, corrigée, absente)
  - **Cadence** de mesure (10min, 30min, horaire, journalier, mensuel)

### 3. Modèle de données brut (tables SQLAlchemy)

**Principe directeur** : Le modèle de staging doit stocker l'information brute des flux Enedis **le plus fidèlement possible**, sans transformation ni perte. L'objectif est de conserver une copie structurée du contenu XML pour pouvoir la travailler, normaliser et enrichir dans des features ultérieures.

**Le modèle exact (nombre de tables, champs, relations) doit être conçu par les agents après avoir déchiffré et analysé la structure XML réelle des fichiers d'exemple.** Le cadrage ne prescrit pas un schéma figé.

**Exigences pour guider la conception :**
- **Fidélité** : ne pas jeter d'information présente dans le XML — si un champ existe dans le flux, il doit être stocké (en colonne typée ou en JSON)
- **Traçabilité** : chaque donnée doit pouvoir remonter au fichier source (quel flux, quel fichier, quelle date de réception)
- **Dedup** : identifier les fichiers déjà traités (hash SHA256) pour garantir l'idempotence
- **Lifecycle** : suivre le statut de traitement de chaque fichier (reçu → déchiffré → parsé → erreur)
- **Performance** : supporter ~480 000 mesures/jour à terme (10 000 PRM × 48 points/jour). Prévoir les index appropriés
- **Unicité des mesures** : empêcher les doublons au niveau des valeurs individuelles (un même PRM + horodatage ne doit pas apparaître deux fois)
- **Pas de normalisation** : les données sont stockées telles qu'Enedis les envoie (unités, codes qualité, natures) — la transformation viendra dans une feature ultérieure

### 4. Pipeline orchestrateur
- Fonction unique qui prend un chemin de fichier et exécute : dézip → déchiffrement → identification du type de flux → parsing → stockage
- Idempotent : si le `file_hash` existe déjà en base avec status=parsed → skip (no-op)
- Résilient : fichier corrompu ou format inattendu → status=error avec message, pas de crash
- Batch insert performant pour les mesures (chunks)

### 5. Tests
- Tests unitaires pour chaque parser avec les fichiers d'exemple de `flux_enedis/`
- Test du pipeline complet (fichier → base)
- Test d'idempotence (double import = 0 doublon)
- Test de résilience (fichier corrompu → error propre)

## Contraintes d'architecture

1. **Isolation totale** : nouveau module `backend/enedis/` — aucune dépendance ni modification des modèles existants (Meter, MeterReading, Consommation, Compteur)
2. **Pas de routes API** dans cette feature — le pipeline est appelable programmatiquement (la Feature 2 ajoutera les routes)
3. **SQLAlchemy** pour les modèles, cohérent avec le reste du backend
4. **Les tables staging sont permanentes** — ce ne sont pas des tables temporaires, elles sont la trace audit des flux reçus
5. **Scalabilité** : le modèle doit supporter 10 000 PRM × 48 mesures/jour (30min) = ~480 000 inserts/jour. Index composites sur `(point_id, horodatage)` et `(flux_id)`.

## Arborescence cible

```
backend/
  enedis/
    __init__.py
    models.py          # FluxSGE, FluxSGEPointDeMesure, FluxSGEMesure
    enums.py           # FluxType, FluxStatus, NatureMesure, CadenceMesure, SourceFlux
    pipeline.py        # Orchestrateur : fichier → déchiffrement → parse → store
    decrypt.py         # Dézip + déchiffrement AES
    parsers/
      __init__.py
      base.py          # Interface/classe de base parser
      r4.py            # Parser R4H/R4M/R4Q (même structure XML, cadence différente)
      r171.py          # Parser R171
      r50.py           # Parser R50
      r151.py          # Parser R151
    tests/
      __init__.py
      test_decrypt.py
      test_parsers.py
      test_pipeline.py
      conftest.py      # Fixtures avec fichiers d'exemple de flux_enedis/
```

## Critères d'acceptation

1. **Déchiffrement OK** : au moins un fichier de chaque type (R4H, R171, R50, R151) est déchiffré avec succès → XML valide
2. **Parsing OK** : chaque parser extrait correctement PRM, horodatages, valeurs, nature depuis les fichiers d'exemple
3. **Stockage OK** : les données parsées sont en base, requêtables par PRM et plage de dates
4. **Idempotence** : relancer le pipeline sur le même fichier → 0 nouvelle ligne en base
5. **Résilience** : fichier corrompu → status=error, message informatif, pas d'exception non gérée
6. **Isolation** : aucun test existant du POC ne casse (`pytest backend/tests/ -x`)
7. **Tests propres** : `pytest backend/enedis/tests/ -x -v` passe à 100%

## Risques identifiés

- **Chiffrement** : le mode AES exact est inconnu → première tâche = déchiffrer un fichier d'exemple
- **Schemas XML** : les flux Enedis ont évolué au fil des années (ex: préfixe ERDF → ENEDIS). Les parsers doivent gérer les deux
- **Fichiers R172** : présents dans les exemples mais non listés dans le scope initial. À ignorer pour cette feature, mais le pipeline ne doit pas crasher dessus
