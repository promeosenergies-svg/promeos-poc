# Ingestion des flux Enedis SGE

> **Module** : `backend/data_ingestion/enedis/`
> **Statut** : POC -- archive brute opérationnelle SF1 à SF5, isolée dans `flux_data.db`
> **Dernière mise à jour** : 2026-04-26

---

## Table des matières

1. [Introduction](#1-introduction)
2. [Vue d'ensemble fonctionnelle](#2-vue-densemble-fonctionnelle)
3. [Source des données : les flux SGE](#3-source-des-données--les-flux-sge)
4. [Types de flux et classification](#4-types-de-flux-et-classification)
5. [Architecture du module](#5-architecture-du-module)
6. [Flux de données de bout en bout](#6-flux-de-données-de-bout-en-bout)
7. [Décryptage et transport](#7-décryptage-et-transport)
8. [Parsers](#8-parsers)
9. [Pipeline d'ingestion](#9-pipeline-dingestion)
10. [Modèle de données](#10-modèle-de-données)
11. [Migrations et séparation des bases](#11-migrations-et-séparation-des-bases)
12. [API REST](#12-api-rest)
13. [Interface CLI](#13-interface-cli)
14. [Configuration](#14-configuration)
15. [Tests](#15-tests)
16. [Cycle de vie d'un fichier](#16-cycle-de-vie-dun-fichier)
17. [Limites connues](#17-limites-connues)
18. [Glossaire](#18-glossaire)

---

## 1. Introduction

Ce document décrit l'implémentation actuelle du module d'ingestion brute des flux Enedis SGE dans le POC Promeos. Il sert de référence pour comprendre ce que la couche raw archive stocke, ce qu'elle expose aux opérateurs, et ce qu'elle laisse volontairement à des couches ultérieures.

Fonctionnellement, le module prend des fichiers Enedis reçus par dépôt fichier, les identifie, les ouvre selon leur transport, parse leur contenu, puis archive les données brutes dans des tables dédiées. Pour l'utilisateur, cela veut dire qu'un seul run d'ingestion peut traiter un répertoire mixte contenant à la fois les anciens flux XML chiffrés et les nouveaux flux SF5 en ZIP direct ou chiffré.

Le module a été construit par vagues :

| Vague | Périmètre | Résultat actuel |
|-------|-----------|-----------------|
| SF1 | Décryptage et classification initiale | AES-128-CBC, clés `KEY_n/IV_n`, classification legacy |
| SF2 | Courbes R4x C1-C4 | Parser R4H/R4M/R4Q, table raw R4x |
| SF3 | Index et courbes complémentaires | Parsers R171, R50, R151, dispatch multi-flux |
| SF4 | Opérationnalisation | Retry, audit d'erreurs, CLI, API REST, dry-run |
| SGE4.5 | Séparation des bases | Raw Enedis dans `flux_data.db`, pas dans `promeos.db` |
| SF5 | R6X + C68 raw ingestion | R63, R64, C68 JSON/CSV, ZIP direct ou AES, tables raw dédiées |

Le principe central n'a pas changé depuis SF1 : **archiver la donnée brute telle qu'Enedis l'a publiée, sans conversion métier**. Les valeurs de mesure restent des chaînes. Les dates ne sont pas converties en UTC. Les doublons de mesure ne sont pas supprimés. La normalisation, le matching PRM vers site et la promotion vers les tables produit appartiennent à la couche suivante.

Exemple concret : si Enedis publie deux fichiers portant le même nom mais avec un contenu différent, Promeos conserve les deux versions. La nouvelle version passe en `needs_review` afin qu'un humain ou une future couche de promotion décide comment l'utiliser.

---

## 2. Vue d'ensemble fonctionnelle

### Ce que fait le module

Le module ingère des flux Enedis SGE et les archive dans une base raw dédiée. Il assure :

- **La classification** des fichiers à partir de leur nomenclature.
- **Le transport** : fichiers legacy AES/XML, fichiers SF5 ZIP directs, ou fichiers SF5 AES qui se déchiffrent en ZIP.
- **Le parsing** de 9 familles ingérées : `R4H`, `R4M`, `R4Q`, `R171`, `R50`, `R151`, `R63`, `R64`, `C68`.
- **Le stockage brut** dans `flux_data.db`, avec une table de registre et des tables de mesures/snapshots par famille.
- **L'idempotence fichier** : un fichier physique identique n'est pas retraité.
- **La gestion des republications** : même nom de fichier, hash différent, nouvelle version conservée en `needs_review`.
- **Le retry** : les erreurs sont historisées et les fichiers en échec sont retentés jusqu'à `MAX_RETRIES`.
- **L'observabilité opérationnelle** : CLI, API REST, compteurs par statut, compteurs par flux et liste des erreurs.

Ce que cela signifie pour l'utilisateur : l'opérateur n'a pas besoin de choisir un outil différent selon que le dépôt contient un ancien R50 XML chiffré, un R63 ZIP direct, ou une archive C68 imbriquée. Il lance la même ingestion, puis consulte les mêmes compteurs et statuts.

### Ce que le module ne fait pas

Le module ne fait pas :

- de conversion en tables métier (`Consommation`, `MeterReading`, `meter_load_curve`, etc.) ;
- de matching PRM vers `Site`, `Compteur` ou contrat Promeos ;
- de déduplication au niveau des mesures individuelles ;
- d'interprétation tarifaire ou qualité avancée ;
- de réconciliation du compte rendu `CR.M023` ;
- d'appel SOAP aux services Enedis ;
- d'authentification propre sur les endpoints d'ingestion du POC.

Ces choix sont volontaires. La couche d'ingestion brute doit rester une archive fidèle et réexploitable. Par exemple, si un parser C68 s'améliore plus tard pour extraire une nouvelle colonne, le `payload_raw` stocké permet de recalculer cette colonne sans redemander le fichier à Enedis.

---

## 3. Source des données : les flux SGE

Enedis publie des données de comptage via le **Système de Gestion des Échanges (SGE)**. Promeos reçoit ces flux sous forme de fichiers portant une nomenclature Enedis. Selon la famille et le canal, le fichier reçu peut être :

- un ciphertext AES qui contient un XML ou un ZIP contenant un XML ;
- un ZIP directement ouvrable contenant un JSON ou un CSV ;
- un ciphertext AES qui, une fois déchiffré, contient un ZIP SF5.

Les segments actuellement couverts sont :

| Segment / famille | Description | Flux ingérés |
|-------------------|-------------|--------------|
| C1-C4 legacy | Compteurs télérelevés haute fréquence | `R4H`, `R4M`, `R4Q`, `R171` |
| C5 legacy | Compteurs Linky basse tension | `R50`, `R151` |
| R6X ponctuel | Mesures demandées via M023 | `R63`, `R64` |
| ITC ponctuel | Informations techniques et contractuelles | `C68` |

Les fichiers historiques SF1-SF4 étaient principalement des XML chiffrés. SF5 ajoute des payloads JSON/CSV et des règles de conteneur ZIP plus riches.

---

## 4. Types de flux et classification

### Flux ingérés

| Type | Nom fonctionnel | Contenu archivé | Format payload | Granularité raw |
|------|-----------------|-----------------|----------------|-----------------|
| `R4H` | Courbe de charge hebdomadaire C1-C4 | Points de courbe R4x | XML | 5 ou 10 min selon Enedis |
| `R4M` | Courbe de charge mensuelle C1-C4 | Points de courbe R4x | XML | 5 ou 10 min selon Enedis |
| `R4Q` | Courbe de charge quotidienne C1-C4 | Points de courbe R4x | XML | 5 ou 10 min selon Enedis |
| `R171` | Mesures datées quotidiennes C2-C4 | Index / grandeurs par classe temporelle | XML | 1..n valeurs datées par série |
| `R50` | Courbe de charge C5 | Points de courbe C5 | XML | 30 min |
| `R151` | Index et puissance maximale C5 | Index fournisseur/distributeur et PMAX | XML | 1 relevé par période |
| `R63` | Courbe de charge R6X ponctuelle | Points de courbe infrajournaliers | JSON ou CSV | Pas brut `PT5M`, `PT10M`, `PT15M`, `PT30M`, `PT60M`, etc. |
| `R64` | Index R6X ponctuels | Index cumulés avec contexte de relève, calendrier et classe temporelle | JSON ou CSV | Valeurs d'index datées |
| `C68` | Informations techniques et contractuelles | Snapshot ITC par PRM | JSON ou CSV | 1 ligne/snapshot par PRM |

### Flux reconnus mais ignorés

Ces flux sont connus de la classification mais restent hors périmètre de parsing. Ils sont enregistrés en `skipped`, pas en `error`, car leur présence n'est pas une panne d'ingestion.

| Type | Raison |
|------|--------|
| `R172` | Réconciliation binaire legacy, non XML |
| `X14` | Hors périmètre fonctionnel |
| `HDM` | CSV chiffré PGP, transport différent |
| `R63A`, `R63B` | R6X récurrent, reconnu mais non supporté SF5 |
| `R64A`, `R64B` | R6X récurrent, reconnu mais non supporté SF5 |
| `R65`, `R66`, `R66B`, `R67` | Flux R6X adjacents hors périmètre SF5 |
| `CR_M023` | Compte rendu M023 reconnu mais non réconcilié |
| `UNKNOWN` | Nom non reconnu |

### Règles de classification legacy

Les flux SF1-SF4 sont détectés par motifs dans le nom de fichier :

| Motif | Type |
|-------|------|
| `_R4H_CDC_` | `R4H` |
| `_R4M_CDC_` | `R4M` |
| `_R4Q_CDC_` | `R4Q` |
| `_R171_` | `R171` |
| `_R50_` | `R50` |
| `_R151_` | `R151` |
| `_R172_` | `R172` |
| `_X14_` | `X14` |
| `_HDM_` | `HDM` |

### Règles de classification SF5

SF5 lit un segment explicite de code flux plutôt qu'une simple sous-chaîne large. Cette prudence évite de confondre `R63A` avec `R63`, ou `R64B` avec `R64`.

Nomenclatures supportées :

```text
ENEDIS_<codeFlux>_<modePublication>_<typeDonnee>_<idDemande>_<numSequence>_<horodate>.<extension>
ENEDIS_<codeFlux>_<modePublication>_<typeDonnee>_<idDemande>_<codeContratOrSiren>_<numSequence>_<horodate>.<extension>
```

Métadonnées extraites quand le fichier est réellement parsé :

| Métadonnée | Exemple | Utilisation |
|------------|---------|-------------|
| `code_flux` | `R63`, `C68` | Code source Enedis |
| `mode_publication` | `P`, `Q`, `H`, `M` | Rythme ou mode de publication |
| `type_donnee` | `CdC`, `INDEX`, `ITC` | Famille de donnée publiée |
| `id_demande` | `M053Q0D3` | Identifiant de demande M023 |
| `num_sequence` | `00001` | Numéro de séquence brut |
| `publication_horodatage` | `20230918161101` | Horodatage de publication brut |
| `siren_publication` | `123456789` | Segment extra si forme SIREN |
| `code_contrat_publication` | `GRD-F345` | Segment extra si non-SIREN |
| `payload_format` | `JSON`, `CSV` | Format SF5 effectivement parsé ; les flux legacy XML le laissent actuellement nul |
| `archive_members_count` | `1`, `2`, ... | Nombre de membres ouverts au niveau pertinent |

Exemples :

```text
ENEDIS_23X--130624--EE1_R4H_CDC_20260302.zip
ERDF_R50_23X--130624--EE1_GRD-F121.zip
ENEDIS_R171_C_00000099895595_GRDF_23X--130624--EE1_20260301024107.zip
ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip
ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip
ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip
ENEDIS_R63A_R_CDC_M01ABCDE_GRD-F345_00001_20230918161101.zip
```

### Fenêtres de publication utiles à l'exploitation

Ces délais n'influencent pas le parsing, mais ils évitent de confondre un fichier pas encore attendu avec un retard.

| Flux | Période couverte | Délai de publication |
|------|------------------|----------------------|
| `R4Q` | Jour D | J+1 calendaire |
| `R4H` | Semaine samedi 00:00 à vendredi 23:50 | Au plus tard le 3e jour ouvré après fin de semaine |
| `R4M` | Mois civil | Au plus tard le 3e jour ouvré après fin de mois |
| `R50` quotidien | Jour J | Nuit de J+1 à J+2 |
| `R50` mensuel | Abonnement mensuel, pas forcément mois civil | Au plus tard le 3e jour ouvré après le dernier jour de collecte |

Point important : l'ingestion brute ne produit pas encore d'état de complétude. Une absence de fichier avant échéance, un retard de publication, et un trou à l'intérieur d'un fichier livré sont trois problèmes différents.

---

## 5. Architecture du module

### Arborescence

```text
backend/data_ingestion/enedis/
├── __init__.py
├── base.py                 # FluxDataBase, base SQLAlchemy dédiée raw Enedis
├── enums.py                # FluxType, FluxStatus, IngestionRunStatus
├── config.py               # ENEDIS_FLUX_DIR, MAX_RETRIES
├── decrypt.py              # AES legacy + classification générale
├── filename.py             # Classification/parsing de nomenclature SF5
├── transport.py            # Résolution direct ZIP/XML ou AES vers payload attendu
├── containers.py           # Validation des archives R6X et C68
├── models.py               # Modèles SQLAlchemy raw
├── migrations.py           # Bootstrap/migrations flux_data.db
├── pipeline.py             # Orchestrateur ingest_file / ingest_directory
├── cli.py                  # Point d'entrée CLI
├── parsers/
│   ├── _helpers.py         # Utilitaires XML tolérants aux namespaces
│   ├── r4.py               # R4H/R4M/R4Q XML
│   ├── r171.py             # R171 XML
│   ├── r50.py              # R50 XML
│   ├── r151.py             # R151 XML
│   ├── r63.py              # R63 JSON/CSV
│   ├── r64.py              # R64 JSON/CSV
│   └── c68.py              # C68 JSON/CSV
└── scripts/
    ├── backfill_c68_payload_raw.py
    ├── decrypt_samples.py
    └── ingest_real_db.py
```

### Principes de conception

| Principe | Implémentation |
|----------|----------------|
| Archive brute | Valeurs stockées comme chaînes, pas de conversion numérique ou temporelle |
| Base raw dédiée | Modèles rattachés à `FluxDataBase`, stockage dans `flux_data.db` |
| Parsers purs | Les parsers transforment des bytes en dataclasses, sans accès DB |
| Transport séparé du parsing | SF5 résout d'abord direct ZIP ou AES, puis valide le conteneur, puis parse le payload |
| Dispatch explicite | Legacy XML via `_DISPATCH`, SF5 via handlers dédiés R6X/C68 |
| Idempotence fichier | SHA256 du fichier physique reçu |
| Pas de déduplication mesure | Les doublons restent en raw ; la décision est repoussée à la promotion |
| Crash recovery | Scan en deux phases avec statut `received` repris au run suivant |
| Audit | Runs, erreurs par tentative et statuts fichier conservés |

### Intégration backend

- **Routes** : `backend/routes/enedis.py`, préfixe `/api/enedis`.
- **Session API** : `database.get_flux_data_db()`.
- **Session CLI** : `database.FluxDataSessionLocal()`.
- **Migrations raw** : `data_ingestion/enedis/migrations.py::run_flux_data_migrations()`.
- **Séparation produit/raw** : les tables `enedis_flux_*` ne sont pas créées dans `promeos.db`.
- **Aucune FK métier** : pas de relation vers `Site`, `Compteur`, `Consommation` ou les tables de promotion.

---

## 6. Flux de données de bout en bout

### Chemin legacy XML (`R4H`, `R4M`, `R4Q`, `R171`, `R50`, `R151`)

```text
Fichier reçu
  │
  ├─ classify_flux(filename)
  │
  ├─ SHA256 du fichier physique
  │
  ├─ vérification idempotence / retry / republication
  │
  ├─ decrypt_file()
  │    ├─ AES-128-CBC + PKCS7
  │    ├─ ZIP post-décryptage : extraction du premier membre
  │    └─ validation XML
  │
  ├─ parser XML spécifique
  │
  ├─ _create_flux_file()
  │
  └─ _store_r4x/_store_r171/_store_r50/_store_r151()
       └─ insertions batch dans flux_data.db
```

Ce que cela veut dire pour un R50 : le fichier est déchiffré, le XML est lu, chaque `PDC` devient une ligne dans `enedis_flux_mesure_r50`, et le registre `enedis_flux_file` porte le statut final et le nombre de points stockés.

### Chemin SF5 R6X (`R63`, `R64`)

```text
Fichier ENEDIS_R63/R64_*.zip
  │
  ├─ classification SF5 par segment codeFlux
  │
  ├─ SHA256 du fichier physique
  │
  ├─ resolve_payload(expected="zip")
  │    ├─ si ZIP direct : utilisé tel quel
  │    └─ sinon : tentative AES avec les clés disponibles
  │
  ├─ extract_r6x_payload()
  │    ├─ archive ZIP avec exactement 1 membre
  │    ├─ membre JSON ou CSV
  │    └─ cohérence nomenclature archive ↔ payload
  │
  ├─ parse_r63_payload() ou parse_r64_payload()
  │
  └─ stockage dans enedis_flux_mesure_r63 ou enedis_flux_index_r64
```

Exemple : `ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip` doit contenir un seul payload `ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.json` ou `.csv`. Si le payload annonce `00002` alors que l'archive annonce `00001`, le fichier passe en `error` sans insert partiel.

### Chemin SF5 C68

```text
Fichier ENEDIS_C68_*.zip (archive primaire)
  │
  ├─ classification C68
  │
  ├─ SHA256 du fichier physique
  │
  ├─ resolve_payload(expected="zip")
  │
  ├─ extract_c68_payloads()
  │    ├─ archive primaire : séquence 00001 obligatoire
  │    ├─ 1 à 10 archives secondaires
  │    ├─ chaque secondaire contient exactement 1 JSON ou CSV
  │    ├─ séquences secondaires contiguës 00001..N
  │    └─ pas de mélange JSON/CSV dans une même primaire
  │
  ├─ parse_c68_payload() pour chaque payload secondaire
  │
  └─ stockage dans enedis_flux_itc_c68
```

Ce que cela veut dire pour l'utilisateur : une demande ITC C68 livrée en deux archives secondaires est stockée comme un seul fichier de registre avec `archive_members_count=2`, puis une ligne raw par PRM dans `enedis_flux_itc_c68`.

---

## 7. Décryptage et transport

### Décryptage legacy (`decrypt.py`)

Le décryptage legacy est utilisé pour les flux XML SF1-SF4.

| Élément | Détail |
|---------|--------|
| Chiffrement | AES-128-CBC |
| Padding | PKCS7 |
| Clés | `KEY_1/IV_1` à `KEY_9/IV_9` |
| Format clé/IV | Hexadécimal, 32 caractères pour 16 octets |
| Stratégie | Essai séquentiel des paires disponibles |
| Sortie attendue | XML direct ou ZIP contenant un XML |

`decrypt_file()` valide que le résultat est parseable en XML. Si un ZIP est produit, l'implémentation actuelle extrait uniquement le premier membre.

### Chargement des clés

`load_keys_from_env()` :

- parcourt les indices `1..9` et charge chaque paire `KEY_n/IV_n` présente ;
- échoue si une clé existe sans IV, ou inversement ;
- échoue si aucune paire n'est trouvée.

La CLI et l'API attrapent `MissingKeyError` et continuent avec `keys=[]`. Cela permet d'ingérer des fichiers SF5 directement ouvrables même quand les clés ne sont pas configurées. En revanche, un flux legacy chiffré ou un SF5 chiffré passera en `error` si aucune clé n'est disponible pour l'ouvrir.

### Transport SF5 (`transport.py`)

SF5 utilise `resolve_payload()` au lieu de `decrypt_file()` :

1. Lire les bytes du fichier reçu.
2. Vérifier si ces bytes correspondent déjà au type attendu (`zip` pour R63/R64/C68).
3. Si oui, transport `direct`.
4. Sinon, tenter `aes_unwrap_bytes()` avec les clés disponibles.
5. Valider que le plaintext obtenu correspond au type attendu.

Le transport ne parse pas le contenu métier. Il répond seulement à la question : "ai-je maintenant un ZIP exploitable ?"

---

## 8. Parsers

Chaque parser est volontairement limité à la transformation bytes → dataclasses. Le stockage en base est fait dans `pipeline.py`.

### 8.1 Utilitaires XML partagés

`parsers/_helpers.py` fournit :

| Fonction | Rôle |
|----------|------|
| `strip_ns(tag)` | Supprime le namespace XML d'un tag |
| `find_child(parent, tag_name)` | Trouve un enfant direct en ignorant les namespaces |
| `child_text(parent, tag_name)` | Retourne le texte d'un enfant, ou `None` |

Ces helpers permettent d'accepter des XML avec préfixes `ns2:` ou anciennes mentions `ERDF`.

### 8.2 R4x -- Courbe de charge C1-C4

**Fichier** : `parsers/r4.py`

Flux concernés : `R4H`, `R4M`, `R4Q`.

Le parser lit un XML `<Courbe>` et produit une ligne raw par `<Donnees_Point_Mesure>`.

| Champ raw | Source | Sens fonctionnel |
|-----------|--------|------------------|
| `point_id` | `Identifiant_PRM` | PRM du fichier |
| `horodatage_debut` / `horodatage_fin` | Bloc `Donnees_Courbe` | Fenêtre couverte par le bloc |
| `granularite` | `Granularite` | Pas en minutes, stocké brut |
| `unite_mesure` | `Unite_Mesure` | Unité Enedis brute |
| `grandeur_metier` | `Grandeur_Metier` | `CONS`, `PROD`, etc. |
| `grandeur_physique` | `Grandeur_Physique` | `EA`, `ERC`, `ERI`, etc. |
| `horodatage` | attribut `Horodatage` | Début de l'intervalle couvert |
| `valeur_point` | attribut `Valeur_Point` | Valeur brute |
| `statut_point` | attribut `Statut_Point` | Qualité/statut Enedis brut |

Point métier important : la valeur R4x associée à `Horodatage=H` représente l'intervalle `[H ; H + granularité[`. Les passages heure d'été/hiver doivent être interprétés plus tard à partir des offsets fournis par Enedis.

### 8.3 R171 -- Mesures datées quotidiennes C2-C4

**Fichier** : `parsers/r171.py`

Le parser lit un XML `<R171>` et produit une ligne par `mesureDatee`.

| Champ raw | Source | Sens fonctionnel |
|-----------|--------|------------------|
| `point_id` | `prmId` | PRM |
| `type_mesure` | `type` | Observé : `INDEX` |
| `grandeur_metier` | `grandeurMetier` | `CONS`, `PROD` |
| `grandeur_physique` | `grandeurPhysique` | `EA`, `PMA`, `DD`, etc. |
| `type_calendrier` | `typeCalendrier` | Grille distributeur/fournisseur |
| `code_classe_temporelle` | `codeClasseTemporelle` | HPH, HCH, P, etc. |
| `unite` | `unite` | Wh, W, s, VA, VArh |
| `date_fin` | `dateFin` | Horodatage de lecture |
| `valeur` | `valeur` | Valeur brute |

Le fichier peut contenir plusieurs PRM et plusieurs séries. Le parser est plus tolérant que la XSD sur certains champs optionnels afin de préserver l'archive brute.

### 8.4 R50 -- Courbe de charge C5

**Fichier** : `parsers/r50.py`

Le parser lit un XML `<R50>` et produit une ligne par `PDC`.

| Champ raw | Source | Sens fonctionnel |
|-----------|--------|------------------|
| `point_id` | `Id_PRM` | PRM |
| `date_releve` | `Date_Releve` | Date du relevé |
| `id_affaire` | `Id_Affaire` | Affaire Enedis |
| `horodatage` | `H` | Fin de l'intervalle de 30 minutes |
| `valeur` | `V` | Puissance moyenne brute en W |
| `indice_vraisemblance` | `IV` | Qualité brute, `1` = valeur sujette à caution |

Exemple : un point `H=2023-01-02T00:30:00+01:00` porte la puissance moyenne des 30 minutes précédentes, pas une mesure instantanée prise à 00:30.

### 8.5 R151 -- Index et puissance maximale C5

**Fichier** : `parsers/r151.py`

Le parser lit un XML `<R151>` et produit une ligne par valeur d'index ou de puissance maximale.

| Type synthétisé | Source XML | Sens |
|-----------------|------------|------|
| `CT_DIST` | `Classe_Temporelle_Distributeur` | Index grille distributeur |
| `CT` | `Classe_Temporelle` | Index grille fournisseur |
| `PMAX` | `Puissance_Maximale` | Puissance maximale |

Le champ `type_donnee` n'existe pas dans le XML : il est synthétisé par le parser pour rendre la table raw interrogeable.

### 8.6 R63 -- Courbe de charge R6X ponctuelle

**Fichier** : `parsers/r63.py`

Le parser accepte `JSON` et `CSV`.

Structure JSON attendue :

```text
header
mesures[]
  idPrm
  etapeMetier
  modeCalcul
  periode.dateDebut/dateFin
  grandeur[]
    grandeurMetier
    grandeurPhysique
    unite
    points[]
      d, v, p, n, tc, iv, ec
```

Colonnes CSV reconnues par alias normalisés :

| Champ dataclass | Exemples d'en-tête CSV |
|-----------------|------------------------|
| `point_id` | `Identifiant PRM` |
| `periode_date_debut` | `Date de début` |
| `periode_date_fin` | `Date de fin` |
| `grandeur_physique` | `Grandeur physique` |
| `grandeur_metier` | `Grandeur métier` |
| `etape_metier` | `Etape métier` |
| `unite` | `Unité` |
| `horodatage` | `Horodate` |
| `valeur` | `Valeur` |
| `nature_point` | `Nature` |
| `pas` | `Pas` |
| `type_correction` | `Type correction`, `tc` |
| `indice_vraisemblance` | `Indice de vraisemblance`, `iv` |
| `etat_complementaire` | `Etat complémentaire`, `ec` |

Chaque point devient une ligne `enedis_flux_mesure_r63`. Les clés JSON inconnues sont enregistrées comme warnings dans `header_raw`.

### 8.7 R64 -- Index R6X ponctuels

**Fichier** : `parsers/r64.py`

Le parser accepte `JSON` et `CSV`.

Structure JSON attendue :

```text
header
mesures[]
  idPrm
  periode.dateDebut/dateFin
  contexte[]
    etapeMetier
    contexteReleve
    typeReleve
    motifReleve
    grandeur[]
      grandeurMetier
      grandeurPhysique
      unite
      calendrier[].classeTemporelle[].valeur[]
      cadranTotalisateur.valeur[]
```

Le parser aplatit les feuilles `valeur[]` en lignes `enedis_flux_index_r64`, en conservant le contexte de relève, la grandeur, le calendrier, la classe temporelle et le cadran quand ils existent.

Pour l'utilisateur métier, cela signifie qu'un index R64 ne perd pas son contexte tarifaire brut : un même PRM peut avoir des valeurs rattachées à une grille fournisseur, une grille distributeur ou un cadran totalisateur.

### 8.8 C68 -- Informations techniques et contractuelles

**Fichier** : `parsers/c68.py`

Le parser accepte `JSON` et `CSV`, après validation de l'archive C68 par `containers.py`.

Granularité : une ligne `enedis_flux_itc_c68` par PRM snapshot.

| Élément | Comportement |
|---------|--------------|
| `payload_raw` | JSON complet de l'objet PRM ou de la ligne CSV, sérialisé en texte |
| Colonnes extraites | Allowlist de champs utiles pour requête rapide |
| JSON nested | Recherche récursive pour certains champs techniques |
| CSV | Mapping par noms d'en-têtes normalisés, pas par position |
| Situations contractuelles multiples | Sélection de la plus récente si non ambiguë, sinon warning et colonnes contractuelles prudentes |
| Puissance souscrite CSV | `36 kVA` est séparé en valeur `36` et unité `kVA` |

Colonnes extraites principales :

| Colonne | Sens |
|---------|------|
| `point_id` | PRM |
| `contractual_situation_count` | Nombre de situations contractuelles JSON |
| `date_debut_situation_contractuelle` | Date de début retenue si disponible |
| `segment` | Segment contractuel |
| `etat_contractuel` | État contractuel |
| `formule_tarifaire_acheminement` | FTA ou code/libellé associé |
| `code_tarif_acheminement` | Code tarif brut |
| `siret`, `siren` | Identifiants client final |
| `domaine_tension`, `tension_livraison` | Données techniques de tension |
| `type_comptage`, `mode_releve`, `media_comptage`, `periodicite_releve` | Informations de comptage/relevé |
| `puissance_*_valeur`, `puissance_*_unite` | Puissances contractuelles/techniques |
| `type_injection`, `borne_fixe`, `refus_pose_linky`, `date_refus_pose_linky` | Champs C68 récents/observés |

Le parser C68 ne normalise pas les branches riches comme `rattachements` ou `optionsContractuelles` dans des tables dédiées. Elles restent disponibles dans `payload_raw`.

---

## 9. Pipeline d'ingestion

**Fichier** : `pipeline.py`

### 9.1 Traitement unitaire : `ingest_file()`

`ingest_file(file_path, session, keys, ...)` traite un fichier et retourne un `FluxStatus`.

Séquence commune :

1. Vérifier que le fichier existe.
2. Classifier le type de flux.
3. Calculer ou recevoir le SHA256 du fichier physique.
4. Chercher un fichier existant par hash.
5. Appliquer idempotence, retry ou reprise `received`.
6. Skip immédiat si type dans `SKIP_FLUX_TYPES`.
7. Détecter une republication par même filename et hash différent.
8. Ouvrir le payload selon la famille.
9. Parser.
10. Créer ou mettre à jour `enedis_flux_file`.
11. Insérer les lignes raw par batch de `DEFAULT_CHUNK_SIZE=1000`.
12. Commit, ou rollback + statut `error` en cas d'échec.

### 9.2 Traitement batch : `ingest_directory()`

`ingest_directory()` fonctionne en deux phases.

**Phase 1 -- scan et enregistrement**

- Scanne les fichiers selon `pattern="*.zip"`.
- Utilise `directory.rglob()` si `recursive=True`, sinon `directory.glob()`.
- Trie les fichiers par nom.
- Crée les nouveaux registres en `received`.
- Reprend les anciens `received`.
- Retente les anciens `error` si le compteur d'erreurs est inférieur à `MAX_RETRIES`.
- Passe les erreurs épuisées en `permanently_failed`.

**Phase 2 -- traitement**

- Appelle `ingest_file()` pour chaque fichier à traiter.
- Met à jour les compteurs du run après chaque fichier.
- En cas d'exception non gérée, le fichier pré-enregistré passe en `error`.

Ce design rend les crashs récupérables : si le processus s'arrête après le scan mais avant la fin du traitement, les fichiers restés en `received` seront repris au prochain run.

### 9.3 Compteurs

| Compteur | Description |
|----------|-------------|
| `received` | Nouveaux fichiers + anciens `received` repris |
| `parsed` | Fichiers ingérés avec succès |
| `needs_review` | Republications ingérées et à examiner |
| `skipped` | Flux connus hors périmètre ou inconnus |
| `error` | Fichiers en erreur dans ce run |
| `permanently_failed` | Fichiers passés en échec définitif pendant ce run |
| `already_processed` | Fichiers déjà finalisés avant ce run |
| `retried` | Fichiers `error` retentés |
| `max_retries_reached` | Fichiers déjà ou nouvellement au plafond de retries |

En non-dry-run, l'invariant attendu est :

```text
received + retried == parsed + needs_review + skipped + error
```

### 9.4 Idempotence

L'idempotence est au niveau fichier :

- `file_hash` = SHA256 des bytes du fichier reçu.
- `file_hash` est unique.
- Même fichier physique = no-op si statut déjà finalisé.

Ce détail est important depuis SF5 : pour un fichier ZIP direct, le hash est celui du ZIP direct ; pour un fichier chiffré, le hash est celui du ciphertext reçu.

Il n'y a pas d'idempotence au niveau mesure. Exemple : si deux fichiers différents contiennent le même PRM et le même horodatage, les deux lignes restent en raw.

### 9.5 Republications

Une republication est détectée quand :

- le `filename` existe déjà avec statut `parsed` ou `needs_review` ;
- le nouveau fichier a un `file_hash` différent.

Le nouveau registre reçoit :

- `status = needs_review` ;
- `version = previous.version + 1` ;
- `supersedes_file_id = previous.id`.

Les deux versions restent consultables. La couche raw ne choisit pas laquelle est "bonne".

### 9.6 Retry et erreurs

| Mécanisme | Comportement |
|-----------|--------------|
| `MAX_RETRIES` | `3` erreurs historisées avant échec définitif |
| Historique | Une ligne `enedis_flux_file_error` par tentative échouée archivée avant retry |
| Dernière erreur | `enedis_flux_file.error_message` porte l'erreur courante |
| Escalade | Après le plafond, statut `permanently_failed`, `error_message` remis à `None` |
| Reprise | Les fichiers `error` sous le plafond sont retentés automatiquement au prochain batch |

### 9.7 Dry-run

En `dry_run=True` :

- un `IngestionRun` est créé pour audit ;
- le répertoire est scanné ;
- aucun `EnedisFluxFile` ni aucune mesure ne sont créés ;
- la phase de parsing/stockage est ignorée ;
- les transitions `permanently_failed` sont simulées dans le rapport.

### 9.8 Routage parser/stockage

Legacy XML via `_DISPATCH` :

```python
_DISPATCH = {
    FluxType.R4H:  (parse_r4x,  R4xParseError,  _store_r4x),
    FluxType.R4M:  (parse_r4x,  R4xParseError,  _store_r4x),
    FluxType.R4Q:  (parse_r4x,  R4xParseError,  _store_r4x),
    FluxType.R171: (parse_r171, R171ParseError, _store_r171),
    FluxType.R50:  (parse_r50,  R50ParseError, _store_r50),
    FluxType.R151: (parse_r151, R151ParseError, _store_r151),
}
```

SF5 utilise des handlers dédiés :

| Flux | Handler | Parser | Store |
|------|---------|--------|-------|
| `R63` | `_ingest_r6x_file()` | `parse_r63_payload()` | `_store_r63()` |
| `R64` | `_ingest_r6x_file()` | `parse_r64_payload()` | `_store_r64()` |
| `C68` | `_ingest_c68_file()` | `parse_c68_payload()` | `_store_c68()` |

---

## 10. Modèle de données

Toutes les tables Enedis raw héritent de `data_ingestion.enedis.base.FluxDataBase`. Elles sont créées dans `flux_data.db`. Elles utilisent aussi `TimestampMixin`, qui ajoute `created_at` et `updated_at`.

Les suppressions sont en cascade : supprimer une ligne `enedis_flux_file` supprime ses mesures/snapshots et ses erreurs.

### 10.1 `enedis_flux_file`

Registre central : une ligne par fichier reçu.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Identifiant |
| `filename` | String(255) | Nom du fichier original |
| `file_hash` | String(64), unique | SHA256 du fichier physique |
| `flux_type` | String(10) | Type Promeos/Enedis : `R4H`, `R63`, `C68`, etc. |
| `status` | String(20) | `received`, `parsed`, `error`, `skipped`, `needs_review`, `permanently_failed` |
| `error_message` | Text | Dernière erreur courante |
| `measures_count` | Integer | Nombre de lignes raw insérées |
| `version` | Integer | `1` original, `2+` republication |
| `supersedes_file_id` | FK self | Version précédente remplacée |
| `frequence_publication` | String(5) | R4x uniquement |
| `nature_courbe_demandee` | String(20) | R4x uniquement |
| `identifiant_destinataire` | String(100) | R4x uniquement |
| `code_flux` | String(20) | SF5 : code flux du nom |
| `type_donnee` | String(20) | SF5 : `CdC`, `INDEX`, `ITC`, etc. |
| `id_demande` | String(20) | SF5 : demande M023 |
| `mode_publication` | String(5) | SF5 : `P`, `Q`, `H`, `M` |
| `payload_format` | String(10) | SF5 : `JSON` ou `CSV`; legacy XML actuellement nul |
| `num_sequence` | String(10) | Séquence brute |
| `siren_publication` | String(20) | Segment extra SIREN si présent |
| `code_contrat_publication` | String(50) | Segment extra non-SIREN si présent |
| `publication_horodatage` | String(20) | Horodatage publication brut |
| `archive_members_count` | Integer | Nombre de membres utiles au niveau archive |
| `header_raw` | Text | JSON brut d'en-tête / manifeste / warnings |

Relations : `mesures_r4x`, `mesures_r171`, `mesures_r50`, `mesures_r151`, `mesures_r63`, `indexes_r64`, `itc_c68`, `errors`.

### 10.2 `enedis_flux_mesure_r4x`

Une ligne par point R4x.

| Colonne | Description |
|---------|-------------|
| `flux_file_id` | FK vers `enedis_flux_file` |
| `flux_type` | `R4H`, `R4M` ou `R4Q` |
| `point_id` | PRM |
| `grandeur_physique`, `grandeur_metier`, `unite_mesure`, `granularite` | Contexte du bloc courbe |
| `horodatage_debut`, `horodatage_fin` | Fenêtre du bloc |
| `horodatage` | Horodatage du point |
| `valeur_point` | Valeur brute |
| `statut_point` | Statut brut |

Index : `(point_id, horodatage)`, `flux_file_id`, `flux_type`.

### 10.3 `enedis_flux_mesure_r171`

Une ligne par `mesureDatee`.

| Colonne | Description |
|---------|-------------|
| `flux_file_id` | FK |
| `flux_type` | `R171` |
| `point_id` | PRM |
| `type_mesure` | Type brut, observé `INDEX` |
| `grandeur_metier`, `grandeur_physique` | Grandeurs |
| `type_calendrier` | Grille |
| `code_classe_temporelle`, `libelle_classe_temporelle` | Classe temporelle |
| `unite` | Unité |
| `date_fin` | Horodatage de lecture |
| `valeur` | Valeur brute |

Index : `(point_id, date_fin)`, `flux_file_id`, `flux_type`.

### 10.4 `enedis_flux_mesure_r50`

Une ligne par `PDC`.

| Colonne | Description |
|---------|-------------|
| `flux_file_id` | FK |
| `flux_type` | `R50` |
| `point_id` | PRM |
| `date_releve` | Date du relevé |
| `id_affaire` | Affaire Enedis |
| `horodatage` | Fin de l'intervalle 30 min |
| `valeur` | Puissance moyenne brute |
| `indice_vraisemblance` | Qualité brute |

Index : `(point_id, horodatage)`, `flux_file_id`, `flux_type`.

### 10.5 `enedis_flux_mesure_r151`

Une ligne par index ou puissance maximale.

| Colonne | Description |
|---------|-------------|
| `flux_file_id` | FK |
| `flux_type` | `R151` |
| `point_id` | PRM |
| `date_releve` | Date du relevé |
| `id_calendrier_fournisseur`, `libelle_calendrier_fournisseur` | Calendrier fournisseur |
| `id_calendrier_distributeur`, `libelle_calendrier_distributeur` | Calendrier distributeur |
| `id_affaire` | Affaire |
| `type_donnee` | `CT_DIST`, `CT`, `PMAX` |
| `id_classe_temporelle`, `libelle_classe_temporelle`, `rang_cadran` | Contexte tarifaire |
| `valeur` | Valeur brute |
| `indice_vraisemblance` | Qualité brute |

Index : `(point_id, date_releve)`, `flux_file_id`, `flux_type`.

### 10.6 `enedis_flux_mesure_r63`

Une ligne par point R63.

| Colonne | Description |
|---------|-------------|
| `flux_file_id` | FK |
| `flux_type` | `R63` |
| `source_format` | `JSON` ou `CSV` |
| `archive_member_name` | Nom du payload dans l'archive |
| `point_id` | PRM |
| `periode_date_debut`, `periode_date_fin` | Période de publication brute |
| `etape_metier`, `mode_calcul` | Contexte R6X |
| `grandeur_metier`, `grandeur_physique`, `unite` | Grandeur |
| `horodatage` | Horodatage du point |
| `pas` | Pas brut |
| `nature_point` | Nature du point |
| `type_correction` | Type de correction |
| `valeur` | Valeur brute |
| `indice_vraisemblance` | Qualité brute |
| `etat_complementaire` | État complémentaire |

Index : `(point_id, horodatage)`, `flux_file_id`, `(point_id, grandeur_physique)`.

### 10.7 `enedis_flux_index_r64`

Une ligne par valeur d'index R64.

| Colonne | Description |
|---------|-------------|
| `flux_file_id` | FK |
| `flux_type` | `R64` |
| `source_format` | `JSON` ou `CSV` |
| `archive_member_name` | Payload |
| `point_id` | PRM |
| `periode_date_debut`, `periode_date_fin` | Période brute |
| `etape_metier` | Étape métier |
| `contexte_releve`, `type_releve`, `motif_releve` | Contexte de relève |
| `grandeur_metier`, `grandeur_physique`, `unite` | Grandeur |
| `horodatage` | Horodatage de l'index |
| `valeur` | Index brut |
| `indice_vraisemblance` | Qualité brute |
| `code_grille` | Grille brute si CSV |
| `id_calendrier`, `libelle_calendrier`, `libelle_grille` | Calendrier/grille |
| `id_classe_temporelle`, `libelle_classe_temporelle` | Classe temporelle |
| `code_cadran` | Cadran |

Index : `(point_id, horodatage)`, `flux_file_id`, `(point_id, grandeur_physique)`, `(point_id, id_calendrier, id_classe_temporelle)`.

### 10.8 `enedis_flux_itc_c68`

Une ligne par snapshot PRM C68.

| Colonne | Description |
|---------|-------------|
| `flux_file_id` | FK |
| `source_format` | `JSON` ou `CSV` |
| `secondary_archive_name` | Archive secondaire C68 |
| `payload_member_name` | Payload JSON/CSV |
| `point_id` | PRM |
| `payload_raw` | Objet PRM ou ligne CSV complète sérialisée JSON |
| `contractual_situation_count` | Nombre de situations contractuelles |
| `date_debut_situation_contractuelle` | Date retenue si non ambiguë |
| `segment`, `etat_contractuel` | Résumé contractuel |
| `formule_tarifaire_acheminement`, `code_tarif_acheminement` | Tarification brute |
| `siret`, `siren` | Identifiants client |
| `domaine_tension`, `tension_livraison` | Données techniques |
| `type_comptage`, `mode_releve`, `media_comptage`, `periodicite_releve` | Données de comptage |
| `puissance_souscrite_*` | Puissance souscrite |
| `puissance_limite_soutirage_*` | Puissance limite soutirage |
| `puissance_raccordement_soutirage_*` | Puissance raccordement soutirage |
| `puissance_raccordement_injection_*` | Puissance raccordement injection |
| `type_injection`, `borne_fixe`, `refus_pose_linky`, `date_refus_pose_linky` | Champs ITC complémentaires |

Index : `point_id`, `flux_file_id`, `(point_id, flux_file_id)`, `siret`, `siren`.

### 10.9 `enedis_flux_file_error`

Historique des erreurs.

| Colonne | Description |
|---------|-------------|
| `flux_file_id` | FK |
| `error_message` | Message de la tentative échouée |
| `created_at`, `updated_at` | Audit |

Le nombre de lignes par fichier sert de compteur de retry.

### 10.10 `enedis_ingestion_run`

Audit de chaque exécution.

| Colonne | Description |
|---------|-------------|
| `started_at`, `finished_at` | Début/fin |
| `directory` | Répertoire scanné |
| `recursive` | Scan récursif |
| `dry_run` | Simulation |
| `status` | `running`, `completed`, `failed` |
| `triggered_by` | `cli` ou `api` |
| `files_received`, `files_parsed`, `files_skipped`, `files_error`, `files_needs_review` | Compteurs principaux |
| `files_already_processed`, `files_retried`, `files_max_retries` | Compteurs opérationnels |
| `error_message` | Erreur run-level |

Une contrainte d'unicité partielle empêche deux runs `running` simultanés.

---

## 11. Migrations et séparation des bases

`run_flux_data_migrations(engine)` gère le bootstrap de `flux_data.db`.

Étapes :

1. Renommer l'ancien `enedis_flux_mesure` en `enedis_flux_mesure_r4x` si nécessaire.
2. Créer les tables raw listées dans `ENEDIS_RAW_TABLES`.
3. Ajouter les colonnes évolutives sur `enedis_flux_file`.
4. Ajouter les colonnes C68 évolutives si nécessaire.
5. Migrer une ancienne table physique `enedis_flux_mesure_r6x` vers les tables canoniques split.
6. Créer la vue de compatibilité `enedis_flux_mesure_r6x`.

Tables canoniques raw :

```text
enedis_flux_file
enedis_flux_mesure_r4x
enedis_flux_mesure_r171
enedis_flux_mesure_r50
enedis_flux_mesure_r151
enedis_flux_mesure_r63
enedis_flux_index_r64
enedis_flux_itc_c68
enedis_flux_file_error
enedis_ingestion_run
```

`enedis_flux_mesure_r6x` n'est pas une table canonique. C'est une vue read-only de compatibilité qui agrège `R63` et `R64`.

Ce que cela signifie pour le produit : l'application principale peut évoluer sans embarquer les tables volumineuses de staging Enedis dans `promeos.db`.

---

## 12. API REST

**Fichier** : `backend/routes/enedis.py`
**Préfixe** : `/api/enedis`

### POST `/api/enedis/ingest`

Déclenche l'ingestion synchrone.

Corps :

| Champ | Type | Défaut | Description |
|-------|------|--------|-------------|
| `recursive` | bool | `true` | Scan récursif |
| `dry_run` | bool | `false` | Simulation sans mutation de fichiers raw |

Le répertoire vient de `ENEDIS_FLUX_DIR`. Contrairement à la CLI, l'API ne prend pas d'override `directory`.

Pré-vol :

- résolution de `ENEDIS_FLUX_DIR` ;
- chargement des clés si présentes, sinon continuation avec `keys=[]` ;
- garde de concurrence via un run `running` unique.

Réponse :

| Champ | Description |
|-------|-------------|
| `run_id` | Identifiant du run |
| `status` | Statut final |
| `dry_run` | Mode simulation |
| `duration_seconds` | Durée |
| `counters` | Compteurs du pipeline |
| `errors` | Fichiers en `error` ou `permanently_failed` modifiés pendant ce run |

Codes principaux : `200`, `409` si run concurrent, `422` si répertoire invalide, `500` si interruption pipeline.

### GET `/api/enedis/flux-files`

Liste paginée des fichiers.

Paramètres :

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `status` | aucun | Filtre par statut |
| `flux_type` | aucun | Filtre par type |
| `limit` | `24` | 1 à 200 |
| `offset` | `0` | Décalage |

Chaque item expose les champs de registre, y compris les métadonnées SF5 (`code_flux`, `id_demande`, `payload_format`, `archive_members_count`, etc.).

### GET `/api/enedis/flux-files/{id}`

Détail d'un fichier :

- champs de liste ;
- `header_raw` décodé ;
- champs R4x dédiés ;
- historique complet `errors_history`.

### GET `/api/enedis/stats`

Retourne :

```json
{
  "files": {
    "total": 123,
    "by_status": {"parsed": 100, "skipped": 10, "error": 13},
    "by_flux_type": {"R4H": 5, "R63": 20, "C68": 3}
  },
  "measures": {
    "total": 456789,
    "r4x": 1000,
    "r171": 200,
    "r50": 300,
    "r151": 40,
    "r63": 400000,
    "r64": 50000,
    "r6x": 450000,
    "c68": 249
  },
  "prms": {
    "count": 42,
    "identifiers": ["30000000000001"]
  },
  "last_ingestion": {
    "run_id": 12,
    "timestamp": "2026-04-26T10:00:00",
    "files_count": 33,
    "triggered_by": "cli"
  }
}
```

Les mesures sont agrégées depuis `enedis_flux_file.measures_count` pour les statuts `parsed` et `needs_review`. Les PRM sont calculés par `UNION DISTINCT` sur les tables raw R4x, R171, R50, R151, R63, R64 et C68.

---

## 13. Interface CLI

Invocation :

```bash
cd promeos-poc/backend
python -m data_ingestion.enedis.cli ingest [OPTIONS]
```

Options :

| Option | Description |
|--------|-------------|
| `--dir PATH` | Override de `ENEDIS_FLUX_DIR` |
| `--dry-run` | Scan sans création de fichiers raw ni mesures |
| `--no-recursive` | Désactive le scan récursif |
| `--verbose` | Logging DEBUG |

Séquence :

1. Configurer le logging.
2. Créer/migrer les tables raw via `run_flux_data_migrations()`.
3. Résoudre le répertoire source.
4. Charger les clés si disponibles ; continuer avec un warning si absentes.
5. Créer le run avec garde de concurrence.
6. Appeler `ingest_directory()`.
7. Afficher le rapport.

Le rapport non dry-run affiche :

- compteurs fichiers ;
- retries et échecs définitifs ;
- totaux staging par table : R4x, R171, R50, R151, R63, R64, R6X agrégé, C68 ;
- détail des erreurs récentes.

---

## 14. Configuration

Variables :

| Variable | Usage |
|----------|-------|
| `ENEDIS_FLUX_DIR` | Répertoire scanné par CLI/API |
| `KEY_1` / `IV_1` ... `KEY_9` / `IV_9` | Paires AES-128-CBC en hex |

Paramètres internes :

| Paramètre | Valeur actuelle | Fichier |
|-----------|-----------------|---------|
| `MAX_RETRIES` | `3` | `config.py` |
| `DEFAULT_CHUNK_SIZE` | `1000` | `pipeline.py` |
| Pattern batch | `*.zip` | `pipeline.py` |

Les clés sont optionnelles pour les fichiers SF5 ZIP directs, mais restent nécessaires pour :

- les flux legacy XML chiffrés ;
- les fichiers SF5 reçus chiffrés selon le canal Enedis.

---

## 15. Tests

Répertoires principaux :

- `backend/data_ingestion/enedis/tests/`
- `backend/tests/test_enedis_api.py`
- `backend/tests/test_flux_data_split.py`
- `backend/tests/test_sf5_e2e.py`

Couverture notable :

| Fichier | Couverture |
|---------|------------|
| `test_decrypt.py` | Décryptage et classification legacy |
| `test_filename_sf5.py` | Classification et parsing des noms SF5 |
| `test_transport_sf5.py` | ZIP direct, AES vers ZIP, clés absentes |
| `test_containers_sf5.py` | Contraintes d'archives R6X/C68 |
| `test_parsers_r4.py`, `r171.py`, `r50.py`, `r151.py` | Parsers XML legacy |
| `test_parsers_r63.py`, `r64.py`, `c68.py` | Parsers JSON/CSV SF5 |
| `test_models.py` | Modèles, relations, cascades, doublons raw |
| `test_pipeline.py`, `test_pipeline_full.py`, `test_pipeline_sf5.py` | Idempotence, batch, retry, republications, SF5 |
| `test_cli.py` | CLI, dry-run, rapport |
| `test_enedis_api.py` | API ingestion, liste, détail, stats |
| `test_flux_data_split.py` | Garantie `flux_data.db` vs `promeos.db` |

Les tests réels SF5 sont opt-in via `PROMEOS_RUN_REAL_SF5_TESTS=1`, car les payloads locaux ne sont pas versionnés dans le repo.

Commandes utiles :

```bash
cd promeos-poc/backend
./venv/bin/pytest data_ingestion/enedis/tests/ -x -v
./venv/bin/pytest tests/test_enedis_api.py tests/test_flux_data_split.py -x -v
```

---

## 16. Cycle de vie d'un fichier

```text
                       nouveau fichier
                             │
                             ▼
                       ┌──────────┐
                       │ RECEIVED │◄──── reprise après crash
                       └────┬─────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
   ┌─────────┐        ┌──────────┐        ┌────────┐
   │ PARSED  │        │ SKIPPED  │        │ ERROR  │
   └─────────┘        └──────────┘        └───┬────┘
        │                                     │
        │ republication                       │ retry < MAX_RETRIES
        ▼                                     │
 ┌──────────────┐                             ▼
 │ NEEDS_REVIEW │                       ┌──────────┐
 └──────────────┘                       │ RECEIVED │
                                        └──────────┘
                                             │
                                             │ retry épuisé
                                             ▼
                                  ┌────────────────────┐
                                  │ PERMANENTLY_FAILED │
                                  └────────────────────┘
```

| Statut | Signification | Action |
|--------|---------------|--------|
| `received` | Fichier enregistré, pas encore finalisé | Repris automatiquement |
| `parsed` | Données raw insérées | Aucune |
| `skipped` | Flux hors périmètre ou inconnu | Aucune |
| `error` | Échec avec retry possible | Retry automatique |
| `needs_review` | Republication stockée | Revue humaine/future promotion |
| `permanently_failed` | Retry épuisé | Investigation manuelle |

---

## 17. Limites connues

- Les archives legacy XML post-décryptage peuvent officiellement contenir plusieurs XML, mais `decrypt_file()` extrait encore seulement le premier membre.
- Les endpoints d'ingestion du POC ne portent pas encore une auth opérationnelle dédiée.
- `CR_M023` est reconnu mais non réconcilié avec les données C68/R6X.
- Les flux R6X récurrents `R63A/B` et `R64A/B` sont reconnus mais non parsés.
- La complétude temporelle des publications n'est pas calculée par cette couche.
- Les warnings parser sont stockés dans `header_raw`, mais il n'existe pas encore de surface dédiée pour les filtrer.
- `enedis_flux_mesure_r6x` est une vue de compatibilité, pas une cible d'écriture.

---

## 18. Glossaire

| Terme | Définition |
|-------|------------|
| **SGE** | Système de Gestion des Échanges Enedis |
| **PRM** | Point de Référence Mesure, identifiant de point de comptage |
| **CDC** | Courbe de charge |
| **R6X** | Famille Enedis de publications de mesures demandées, incluant R63/R64 |
| **M023** | Demande ponctuelle à l'origine de certains flux R6X/C68 |
| **ITC** | Informations techniques et contractuelles |
| **C1-C4** | Segments de comptage haute puissance/télérelevés |
| **C5** | Segment Linky basse tension |
| **Raw archive** | Stockage brut fidèle aux fichiers source |
| **Promotion** | Transformation ultérieure raw → tables fonctionnelles |
| **Republication** | Nouveau fichier avec même nom mais contenu différent |
| **Idempotence** | Garantie qu'un même fichier physique n'est pas traité deux fois |
| **Payload** | Fichier métier contenu dans une archive |
| **Archive primaire C68** | ZIP C68 de premier niveau |
| **Archive secondaire C68** | ZIP contenu dans la primaire, portant un JSON/CSV |
| **Dry-run** | Simulation sans insertion de fichiers raw ni mesures |
| **ERDF** | Ancien nom d'Enedis, encore présent dans certains flux |
