# Ingestion des flux Enedis SGE

> **Module** : `backend/data_ingestion/enedis/`
> **Statut** : POC -- couche de staging brut opérationnelle (SF1 à SF4)
> **Dernière mise à jour** : 2026-03-29

---

## Table des matières

1. [Introduction](#1-introduction)
2. [Vue d'ensemble fonctionnelle](#2-vue-densemble-fonctionnelle)
3. [Source des données : les flux SGE](#3-source-des-données--les-flux-sge)
4. [Types de flux](#4-types-de-flux)
5. [Architecture du module](#5-architecture-du-module)
6. [Flux de données de bout en bout](#6-flux-de-données-de-bout-en-bout)
7. [Décryptage](#7-décryptage)
8. [Parsers XML](#8-parsers-xml)
   - 8.1 [Utilitaires partagés](#81-utilitaires-partagés-_helperspy)
   - 8.2 [R4x -- Courbe de charge C1-C4](#82-r4x--courbe-de-charge-c1-c4)
   - 8.3 [R171 -- Index journalier C2-C4](#83-r171--index-journalier-c2-c4)
   - 8.4 [R50 -- Courbe de charge C5](#84-r50--courbe-de-charge-c5)
   - 8.5 [R151 -- Index et puissance maximale C5](#85-r151--index-et-puissance-maximale-c5)
9. [Pipeline d'ingestion](#9-pipeline-dingestion)
   - 9.1 [Traitement unitaire : `ingest_file()`](#91-traitement-unitaire--ingest_file)
   - 9.2 [Traitement batch : `ingest_directory()`](#92-traitement-batch--ingest_directory)
   - 9.3 [Idempotence](#93-idempotence)
   - 9.4 [Détection des republications](#94-détection-des-republications)
   - 9.5 [Retry et gestion d'erreurs](#95-retry-et-gestion-derreurs)
   - 9.6 [Mode dry-run](#96-mode-dry-run)
10. [Modèle de données](#10-modèle-de-données)
    - 10.1 [`enedis_flux_file`](#101-enedis_flux_file)
    - 10.2 [`enedis_flux_mesure_r4x`](#102-enedis_flux_mesure_r4x)
    - 10.3 [`enedis_flux_mesure_r171`](#103-enedis_flux_mesure_r171)
    - 10.4 [`enedis_flux_mesure_r50`](#104-enedis_flux_mesure_r50)
    - 10.5 [`enedis_flux_mesure_r151`](#105-enedis_flux_mesure_r151)
    - 10.6 [`enedis_flux_file_error`](#106-enedis_flux_file_error)
    - 10.7 [`enedis_ingestion_run`](#107-enedis_ingestion_run)
11. [API REST](#11-api-rest)
12. [Interface CLI](#12-interface-cli)
13. [Configuration](#13-configuration)
14. [Tests](#14-tests)
15. [Cycle de vie d'un fichier (machine à états)](#15-cycle-de-vie-dun-fichier-machine-à-états)
16. [Glossaire](#16-glossaire)

---

## 1. Introduction

Ce document décrit le module d'ingestion des flux Enedis SGE tel qu'implémenté dans le POC Promeos. Il couvre l'intégralité de la chaîne : réception des fichiers chiffrés, décryptage, parsing XML, stockage en base de données, exposition via API REST et CLI.

Le module a été construit en 4 sous-features (SF1 à SF4) :

| SF | Périmètre | Résultat |
|----|-----------|----------|
| SF1 | Décryptage et classification | AES-128-CBC, 3 paires de clés, 91 fichiers décryptés |
| SF2 | Ingestion CDC R4x (C1-C4) | Parser R4H/R4M/R4Q, modèle staging, pipeline mono-fichier |
| SF3 | Ingestion R171 + R50 + R151 | 3 parsers supplémentaires, dispatch multi-flux, `ingest_directory()` |
| SF4 | Opérationnalisation | CLI, API REST (4 endpoints), config externalisée, audit d'erreurs, retry |

**Philosophie fondamentale** : archiver la donnée brute telle que reçue d'Enedis, sans transformation ni conversion de type. Toutes les valeurs sont stockées en tant que chaînes de caractères. La conversion et la normalisation sont réservées à une couche fonctionnelle ultérieure.

---

## 2. Vue d'ensemble fonctionnelle

### Ce que fait le module

Le module ingère les fichiers de flux Enedis SGE (publiés par Enedis via FTP) et les archive dans une couche de staging en base de données. Il assure :

- **Le décryptage** des fichiers AES-128-CBC reçus chiffrés
- **Le parsing** de 6 formats XML distincts (R4H, R4M, R4Q, R171, R50, R151)
- **Le stockage** des mesures brutes dans des tables dédiées par famille de flux
- **L'idempotence** : un fichier identique (même contenu) n'est jamais traité deux fois
- **La détection des republications** : quand Enedis republié un fichier corrigé, les deux versions sont conservées
- **L'audit** : chaque exécution est tracée, les erreurs sont historisées, les fichiers en échec sont retentés automatiquement

### Ce que le module ne fait pas (hors périmètre actuel)

- Pas de conversion des mesures en données fonctionnelles (pas d'écriture dans `Consommation` ou `MeterReading`)
- Pas de matching PRM vers Site
- Pas de déduplication au niveau des mesures individuelles
- Pas d'authentification sur les endpoints API
- Pas d'appel SOAP aux web services Enedis (les fichiers sont déposés via FTP)

---

## 3. Source des données : les flux SGE

Enedis publie les données de comptage via le **Système de Gestion des Échanges (SGE)**. En tant que fournisseur, Promeos reçoit ces flux sous forme de fichiers `.zip` chiffrés déposés sur un serveur FTP.

Chaque fichier contient un document XML structuré selon les XSD Enedis (ADR V70). Le nom du fichier indique le type de flux qu'il contient.

**Segments de comptage concernés :**

| Segment | Description | Flux associés |
|---------|-------------|---------------|
| C1-C4 | Compteurs télérelevés haute fréquence (> 36 kVA) | R4H, R4M, R4Q, R171 |
| C5 | Compteurs Linky basse tension (< 36 kVA) | R50, R151 |

**Volume de référence (POC)** : 91 fichiers en périmètre, 123 846 mesures ingérées.

**Objectif de dimensionnement** : 10 000 PRM sur 2 ans d'historique.

---

## 4. Types de flux

Le module reconnaît 10 types de flux à partir du nom de fichier. 6 sont ingérés, 4 sont hors périmètre.

### Flux ingérés

| Type | Nom complet | Segment | Contenu | Granularité |
|------|-------------|---------|---------|-------------|
| **R4H** | CDC publiée hebdomadairement | C1-C4 | Courbe de charge publiée à la maille hebdomadaire | Points toutes les 5 ou 10 min |
| **R4M** | CDC publiée mensuellement | C1-C4 | Idem, publication mensuelle | Points toutes les 5 ou 10 min |
| **R4Q** | CDC publiée quotidiennement | C1-C4 | Idem, publication quotidienne | Points toutes les 5 ou 10 min |
| **R171** | Index journalier par PRM | C2-C4 | Index de consommation par classe temporelle | 1 valeur par jour et par classe |
| **R50** | Courbe de charge C5 | C5 | Points de courbe sur abonnement | Points toutes les 30 min |
| **R151** | Index + puissance max C5 | C5 | Index par classe temporelle et puissance maximale | 1 relevé par période |

### Fenetres officielles de publication R4x

Ces delais ne changent pas le parsing, mais ils sont importants pour l'exploitation et la future couche de completude:

| Flux | Periode couverte | Delai officiel de publication |
|------|------------------|-------------------------------|
| **R4Q** | Jour D (`00:00-23:50`) | **J+1 calendaire** |
| **R4H** | Semaine (`samedi 00:00` -> `vendredi 23:50`) | **Au plus tard le 3eme jour ouvre apres la fin de semaine, avant minuit** |
| **R4M** | Mois civil (`1er jour 00:00` -> dernier jour `23:50`) | **Au plus tard le 3eme jour ouvre apres la fin du mois, avant minuit** |

Point important pour la suite:
- avant l'expiration de cette fenetre, une publication absente est **attendue mais non echue**
- apres l'expiration de cette fenetre, elle devient **potentiellement en retard / manquante**
- cela doit etre traite separement d'un **trou de donnees a l'interieur d'un fichier effectivement livre**

### Flux hors périmètre (ignorés)

| Type | Raison |
|------|--------|
| **R172** | Réconciliation binaire -- format non XML |
| **X14** | Hors périmètre fonctionnel |
| **HDM** | CSV chiffré PGP -- algorithme différent |
| **UNKNOWN** | Nom de fichier non reconnu |

### Règles de classification

La classification se fait par recherche de sous-chaîne dans le nom de fichier, dans l'ordre de priorité suivant :

| Motif recherché | Type assigné |
|----------------|--------------|
| `_R4H_CDC_` | R4H |
| `_R4M_CDC_` | R4M |
| `_R4Q_CDC_` | R4Q |
| `_R171_` | R171 |
| `_R50_` | R50 |
| `_R151_` | R151 |
| `_R172_` | R172 |
| `_X14_` | X14 |
| `_HDM_` | HDM |
| *(aucun match)* | UNKNOWN |

Exemples de noms de fichiers réels :
```
ENEDIS_23X--130624--EE1_R4H_CDC_20260302.zip
ERDF_R50_23X--130624--EE1_GRD-F121.zip
ENEDIS_23X--130624--EE1_R171_20260301.zip
```

---

## 5. Architecture du module

### Arborescence

```
backend/data_ingestion/enedis/
├── __init__.py
├── enums.py                # Vocabulaire partagé (FluxType, FluxStatus, IngestionRunStatus)
├── config.py               # Configuration externalisée (ENEDIS_FLUX_DIR, MAX_RETRIES)
├── decrypt.py              # Décryptage AES-128-CBC + classification des flux
├── models.py               # 7 modèles SQLAlchemy (staging)
├── pipeline.py             # Orchestrateur (ingest_file, ingest_directory, fonctions de stockage)
├── cli.py                  # Point d'entrée CLI
├── parsers/
│   ├── _helpers.py         # Utilitaires XML tolérants aux namespaces
│   ├── r4.py               # Parser R4H/R4M/R4Q
│   ├── r171.py             # Parser R171
│   ├── r50.py              # Parser R50
│   └── r151.py             # Parser R151
└── scripts/
    ├── decrypt_samples.py  # (déprécié) Script autonome de décryptage vers XML
    └── ingest_real_db.py   # (déprécié) Script autonome d'ingestion
```

### Principes de conception

| Principe | Description |
|----------|-------------|
| **Parsers purs** | Les parsers sont des fonctions pures : bytes en entrée, dataclasses en sortie. Aucun accès DB, aucun effet de bord. |
| **Stockage brut** | Toutes les valeurs sont stockées en `String`, sans conversion (`float`, `datetime`, UTC). Garantie zéro perte de donnée. |
| **Dispatch table** | Le routage flux → parser → stockage est une table de dispatch. Ajouter un nouveau type de flux = 1 parser + 1 entrée dans la table. |
| **Idempotence fichier** | SHA256 du fichier chiffré. Même contenu physique = pas de re-traitement. |
| **Crash recovery** | Conception en 2 phases. Un crash en cours de traitement laisse les fichiers en statut `RECEIVED`, qui seront repris au prochain run. |
| **Base partagée** | Les tables Enedis utilisent le même `Base` SQLAlchemy que le reste de Promeos (même fichier `promeos.db` en dev). |

### Intégration avec le reste du backend

- **Routes** : le routeur FastAPI est enregistré dans `main.py` sous le préfixe `/api/enedis`
- **Base de données** : les tables sont créées au démarrage via `database/migrations.py` (`_create_enedis_tables()`)
- **Session** : l'API utilise `database.get_db()` (injection FastAPI), le CLI utilise `database.SessionLocal()`
- **Aucun lien vers les entités métier** : les tables de staging n'ont pas de FK vers `Compteur`, `Site` ou `Consommation`

---

## 6. Flux de données de bout en bout

```
┌──────────────────┐
│  Fichier .zip    │  Fichier chiffré AES-128-CBC déposé sur le FTP Enedis
│  (ciphertext)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Classification  │  Identification du type de flux via le nom de fichier
│  (classify_flux) │  → FluxType (R4H, R50, UNKNOWN, etc.)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Hash SHA256     │  Calcul de l'empreinte du fichier chiffré
│  (idempotence)   │  → Vérification : déjà traité ?
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Décryptage      │  AES-128-CBC + PKCS7, essai séquentiel des clés
│  (decrypt_file)  │  → Extraction ZIP → Validation XML
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Parsing XML     │  Parser spécifique au type de flux
│  (parse_r4x/...) │  → Dataclasses typées (valeurs brutes string)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Stockage        │  Insertion batch en base (chunks de 1000 lignes)
│  (_store_r4x/..) │  → EnedisFluxFile + mesures dans la table dédiée
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Tables staging  │  enedis_flux_file (registre)
│  (promeos.db)    │  enedis_flux_mesure_r4x / r171 / r50 / r151 (mesures)
└──────────────────┘
```

---

## 7. Décryptage

**Fichier** : `decrypt.py`

### Algorithme

- **Chiffrement** : AES-128-CBC avec padding PKCS7
- **Clés** : jusqu'à 9 paires clé/IV, chargées depuis les variables d'environnement `KEY_1/IV_1` à `KEY_9/IV_9`
- **Format des clés** : hexadécimal (32 caractères hex = 16 octets pour AES-128)
- **Essai séquentiel** : chaque paire est essayée dans l'ordre jusqu'à obtenir un XML valide. Il n'existe pas de correspondance déterministe entre une clé et un type de flux.
- **Nombre de clés en production POC** : 3 paires

### Processus de décryptage (`decrypt_file()`)

1. Lecture du fichier chiffré (ciphertext brut)
2. Pour chaque paire (clé, IV) :
   - Tentative AES-128-CBC + dépadding PKCS7
   - Si le déchiffrement échoue → paire suivante
   - Inspection du résultat :
     - Octets magiques `PK\x03\x04` → c'est un ZIP → extraction du premier fichier contenu
     - Premier caractère `<` → XML direct
     - Autre → paire suivante
   - Validation : le résultat doit être parseable par `xml.etree.ElementTree`
3. Si `archive_dir` est fourni : sauvegarde du XML décrypté sur disque (audit)
4. Si aucune clé ne produit un XML valide → `DecryptError`

### Classification (`classify_flux()`)

Identification du type de flux par recherche de motif dans le nom de fichier (voir section 4).

### Gestion des clés (`load_keys_from_env()`)

- Lecture des variables `KEY_1/IV_1`, `KEY_2/IV_2`, etc. dans l'ordre
- Arrêt au premier indice absent (si `KEY_3` manque, seules les paires 1 et 2 sont chargées)
- Erreur si `KEY_i` est présent sans `IV_i` (ou inversement)
- Erreur si aucune paire n'est trouvée (`MissingKeyError`)

---

## 8. Parsers XML

Chaque parser est une fonction pure : `bytes → dataclass`. Aucun accès base de données, aucun effet de bord. Les valeurs sont toujours conservées en tant que chaînes de caractères brutes telles qu'elles apparaissent dans le XML.

### 8.1 Utilitaires partagés (`_helpers.py`)

Trois fonctions utilisées par tous les parsers pour gérer les variations de namespace XML (ERDF → ENEDIS, namespaces `ns2:`, etc.) :

| Fonction | Rôle |
|----------|------|
| `strip_ns(tag)` | Retire le préfixe namespace d'un tag XML : `{http://...}Tag` → `Tag` |
| `find_child(parent, tag_name)` | Trouve le premier enfant direct correspondant au nom de tag (tolérant aux namespaces) |
| `child_text(parent, tag_name)` | Retourne le contenu texte du premier enfant correspondant, ou `None` |

---

### 8.2 R4x -- Courbe de charge C1-C4

**Fichier** : `parsers/r4.py`
**Flux concernés** : R4H, R4M, R4Q (même structure XML, même parser)
**Fonction** : `parse_r4x(xml_bytes) → ParsedR4xFile`

#### Structure XML

```xml
<Courbe>
  <Entete>
    <Identifiant_Flux>R4x</Identifiant_Flux>
    <Libelle_Flux>...</Libelle_Flux>
    <Identifiant_Emetteur>ENEDIS</Identifiant_Emetteur>
    <Identifiant_Destinataire>...</Identifiant_Destinataire>
    <Date_Creation>...</Date_Creation>
    <Frequence_Publication>H|M|Q</Frequence_Publication>
    <Reference_Demande>...</Reference_Demande>
    <Nature_De_Courbe_Demandee>Brute|Corrigee</Nature_De_Courbe_Demandee>
  </Entete>
  <Corps>
    <Identifiant_PRM>30000210411333</Identifiant_PRM>   <!-- 14 chiffres, 1 par fichier -->
    <Donnees_Courbe>                                      <!-- 1..N par Corps -->
      <Horodatage_Debut>2026-03-01T00:00:00+01:00</Horodatage_Debut>
      <Horodatage_Fin>2026-03-02T00:00:00+01:00</Horodatage_Fin>
      <Granularite>10</Granularite>                       <!-- pas en minutes (5 ou 10) -->
      <Unite_Mesure>kW</Unite_Mesure>                     <!-- kW, kWr, V -->
      <Grandeur_Metier>CONS</Grandeur_Metier>             <!-- CONS ou PROD -->
      <Grandeur_Physique>EA</Grandeur_Physique>           <!-- EA, ERC, ERI, E -->
      <Donnees_Point_Mesure
        Horodatage="2026-03-01T00:10:00+01:00"
        Valeur_Point="1234"
        Statut_Point="R"/>                                <!-- attributs XML -->
      <!-- ... répété pour chaque pas de temps -->
    </Donnees_Courbe>
  </Corps>
</Courbe>
```

#### Champs obligatoires

- Balise racine `<Courbe>`
- `<Entete>` présent
- `<Corps>` présent avec `<Identifiant_PRM>` non vide
- Chaque `<Donnees_Point_Mesure>` doit avoir l'attribut `Horodatage`

#### Champs optionnels (stockés `None` si absents)

- `Valeur_Point`, `Statut_Point` sur les points de mesure
- Tous les champs du bloc `<Donnees_Courbe>` (granularité, unité, etc.)

#### Tolérances

- Préfixe `ERDF_` dans l'émetteur (nom historique d'Enedis)
- `<Donnees_Courbe>` vide (0 points) : liste vide, pas d'erreur

#### Contraintes officielles utiles (guide R4x v2.0.3)

- Les dates R4x sont vehiculees en "heure legale Paris" avec decalage horaire explicite.
- Au passage a l'heure d'hiver, la tranche locale `[02:00 ; 03:00[` apparait deux fois avec deux offsets differents.
- Au passage a l'heure d'ete, la tranche locale `[02:00 ; 03:00[` est absente et ce n'est pas une anomalie de donnees.
- La `Granularite` officielle R4x est `10` avant la date de bascule Enedis et `5` apres. Le module de staging stocke la valeur brute et ne hardcode pas cette date.
- La `Valeur_Point` associee a un `Horodatage=H` represente la valeur moyenne sur la periode suivante, de duree egale a la granularite. En pratique, les donnees R4x doivent donc etre interpretees comme couvrant l'intervalle demi-ouvert `[H ; H + granularite[`, pas comme un echantillon instantane pris a `H`.
- Le guide officiel autorise une archive ZIP contenant un ou plusieurs XML. Les fichiers observes dans le POC etaient mono-XML, et `decrypt_file()` extrait encore uniquement le premier membre de l'archive. Le support multi-XML reste donc un point de durcissement pour SF1-SF4.

#### Données produites

| Champ dataclass | Source XML | Description |
|-----------------|-----------|-------------|
| `header.raw` | Tous les enfants de `<Entete>` | Dictionnaire `{tag: texte}` |
| `header.frequence_publication` | `Frequence_Publication` | H (hebdomadaire), M (mensuel), Q (quotidien) |
| `header.nature_courbe_demandee` | `Nature_De_Courbe_Demandee` | Brute ou Corrigee |
| `header.identifiant_destinataire` | `Identifiant_Destinataire` | Code du destinataire |
| `point_id` | `Identifiant_PRM` | PRM 14 chiffres (1 par fichier) |
| `courbes[].horodatage_debut` | `Horodatage_Debut` | Début de la période du bloc |
| `courbes[].horodatage_fin` | `Horodatage_Fin` | Fin de la période du bloc |
| `courbes[].granularite` | `Granularite` | Pas en minutes ("5" ou "10") |
| `courbes[].unite_mesure` | `Unite_Mesure` | kW, kWr, V |
| `courbes[].grandeur_metier` | `Grandeur_Metier` | CONS ou PROD |
| `courbes[].grandeur_physique` | `Grandeur_Physique` | EA, ERC, ERI, E |
| `courbes[].points[].horodatage` | attribut `Horodatage` | ISO8601 avec timezone, debut de l'intervalle couvert |
| `courbes[].points[].valeur_point` | attribut `Valeur_Point` | Valeur brute string |
| `courbes[].points[].statut_point` | attribut `Statut_Point` | R/H/P/S/T/F/G/E/C/K/D |

---

### 8.3 R171 -- Index journalier C2-C4

**Fichier** : `parsers/r171.py`
**Flux concerné** : R171
**Fonction** : `parse_r171(xml_bytes) → ParsedR171File`

#### Structure XML

```xml
<ns2:R171 xmlns:ns2="http://www.enedis.fr/stm/R171">
  <entete>
    <emetteur>Enedis</emetteur>
    <destinataire>GRD-F121</destinataire>
    <dateHeureCreation>2026-03-01T01:13:01</dateHeureCreation>
    <flux>R171</flux>
    <version>1.0</version>
  </entete>
  <serieMesuresDateesListe>
    <serieMesuresDatees>                              <!-- 1..N, multi-PRM possible -->
      <prmId>30000550506121</prmId>                   <!-- obligatoire -->
      <type>INDEX</type>                              <!-- obligatoire -->
      <grandeurMetier>CONS</grandeurMetier>
      <grandeurPhysique>EA</grandeurPhysique>
      <typeCalendrier>D</typeCalendrier>
      <codeClasseTemporelle>HPH</codeClasseTemporelle>
      <libelleClasseTemporelle>Heures Pleines Hiver</libelleClasseTemporelle>
      <unite>Wh</unite>
      <mesuresDateesListe>
        <mesureDatee>
          <dateFin>2026-03-01T00:51:11</dateFin>      <!-- obligatoire -->
          <valeur>1320</valeur>
        </mesureDatee>
      </mesuresDateesListe>
    </serieMesuresDatees>
  </serieMesuresDateesListe>
</ns2:R171>
```

**Particularités du R171** :
- Noms de balises en camelCase (schéma ADR V70), contrairement aux R4x/R50/R151 en underscore
- Namespace `ns2:` sur la racine (optionnel, géré par `strip_ns`)
- **Multi-PRM** : un fichier peut contenir des séries pour plusieurs PRM différents

#### Champs obligatoires

- Balise racine `<R171>` (avec ou sans namespace)
- `<entete>` et `<serieMesuresDateesListe>` présents
- Chaque `<serieMesuresDatees>` : `<prmId>` et `<type>` non vides
- Chaque `<mesureDatee>` : `<dateFin>` non vide

#### Données produites

| Champ dataclass | Source XML | Description |
|-----------------|-----------|-------------|
| `header.raw` | Enfants de `<entete>` | Dictionnaire `{tag: texte}` |
| `series[].point_id` | `prmId` | PRM 14 chiffres |
| `series[].type_mesure` | `type` | INDEX |
| `series[].grandeur_metier` | `grandeurMetier` | CONS, PROD |
| `series[].grandeur_physique` | `grandeurPhysique` | DD, DQ, EA, ERC, ERI, PMA, TF |
| `series[].type_calendrier` | `typeCalendrier` | D |
| `series[].code_classe_temporelle` | `codeClasseTemporelle` | HPH, HCH, HPE, HCE, P |
| `series[].libelle_classe_temporelle` | `libelleClasseTemporelle` | Texte humain |
| `series[].unite` | `unite` | Wh, VArh, VA, s |
| `series[].mesures[].date_fin` | `dateFin` | ISO8601 sans timezone |
| `series[].mesures[].valeur` | `valeur` | Valeur brute string |

---

### 8.4 R50 -- Courbe de charge C5

**Fichier** : `parsers/r50.py`
**Flux concerné** : R50
**Fonction** : `parse_r50(xml_bytes) → ParsedR50File`

#### Structure XML

```xml
<R50>
  <En_Tete_Flux>
    <Identifiant_Flux>R50</Identifiant_Flux>
    <Libelle_Flux>Courbes de charge des PRM du segment C5 sur abonnement</Libelle_Flux>
    <Version_XSD>1.1.0</Version_XSD>
    <Identifiant_Emetteur>ERDF</Identifiant_Emetteur>     <!-- historique ERDF -->
    <Identifiant_Destinataire>...</Identifiant_Destinataire>
    <Date_Creation>...</Date_Creation>
    <Identifiant_Contrat>...</Identifiant_Contrat>
    <Numero_Abonnement>...</Numero_Abonnement>
    <Pas_Publication>30</Pas_Publication>                   <!-- 30 minutes -->
  </En_Tete_Flux>
  <PRM>                                                     <!-- 1..N -->
    <Id_PRM>30001234567890</Id_PRM>
    <Donnees_Releve>                                        <!-- 1..N par PRM -->
      <Date_Releve>2023-01-02</Date_Releve>
      <Id_Affaire>M041AWXF</Id_Affaire>
      <PDC>                                                 <!-- 0..48 par relevé -->
        <H>2023-01-02T16:30:00+01:00</H>                   <!-- horodatage obligatoire -->
        <V>20710</V>                                        <!-- valeur optionnelle -->
        <IV>0</IV>                                          <!-- indice vraisemblance optionnel -->
      </PDC>
    </Donnees_Releve>
  </PRM>
</R50>
```

**Particularités du R50** :
- Structure à 3 niveaux d'imbrication : fichier → PRM → relevé → PDC
- **Multi-PRM** : un fichier contient les courbes de plusieurs PRM
- Pas de publication de 30 minutes (jusqu'à 48 PDC par relevé pour une journée complète)
- L'émetteur peut être `ERDF` (nom historique)

#### Champs obligatoires

- Balise racine `<R50>`
- `<En_Tete_Flux>` présent
- Chaque `<PRM>` : `<Id_PRM>` non vide
- Chaque `<Donnees_Releve>` : `<Date_Releve>` non vide
- Chaque `<PDC>` : `<H>` non vide

#### Données produites

| Champ dataclass | Source XML | Description |
|-----------------|-----------|-------------|
| `header.raw` | Enfants de `<En_Tete_Flux>` | Dictionnaire `{tag: texte}` |
| `prms[].point_id` | `Id_PRM` | PRM 14 chiffres |
| `prms[].releves[].date_releve` | `Date_Releve` | Date du relevé |
| `prms[].releves[].id_affaire` | `Id_Affaire` | Identifiant d'affaire (optionnel) |
| `prms[].releves[].points[].horodatage` | `H` | ISO8601 avec timezone |
| `prms[].releves[].points[].valeur` | `V` | Valeur brute string |
| `prms[].releves[].points[].indice_vraisemblance` | `IV` | "0" ou "1" |

---

### 8.5 R151 -- Index et puissance maximale C5

**Fichier** : `parsers/r151.py`
**Flux concerné** : R151
**Fonction** : `parse_r151(xml_bytes) → ParsedR151File`

#### Structure XML

```xml
<R151>
  <En_Tete_Flux>
    <Identifiant_Flux>R151</Identifiant_Flux>
    <Libelle_Flux>Puissances maximales et index des PRM du segment C5 sur abonnement</Libelle_Flux>
    <Version_XSD>V1</Version_XSD>
    <Identifiant_Emetteur>ERDF</Identifiant_Emetteur>
    <Identifiant_Destinataire>...</Identifiant_Destinataire>
    <Date_Creation>...</Date_Creation>
    <Identifiant_Contrat>...</Identifiant_Contrat>
    <Numero_Abonnement>...</Numero_Abonnement>
    <Unite_Mesure_Index>Wh</Unite_Mesure_Index>
    <Unite_Mesure_Puissance>VA</Unite_Mesure_Puissance>
  </En_Tete_Flux>
  <PRM>
    <Id_PRM>30001234567890</Id_PRM>
    <Donnees_Releve>
      <Date_Releve>2024-12-17</Date_Releve>
      <Id_Calendrier_Fournisseur>CF001</Id_Calendrier_Fournisseur>
      <Libelle_Calendrier_Fournisseur>Base</Libelle_Calendrier_Fournisseur>
      <Id_Calendrier_Distributeur>CD001</Id_Calendrier_Distributeur>
      <Libelle_Calendrier_Distributeur>4 postes</Libelle_Calendrier_Distributeur>
      <Id_Affaire>...</Id_Affaire>

      <!-- Index grille distributeur -->
      <Classe_Temporelle_Distributeur>
        <Id_Classe_Temporelle>HCB</Id_Classe_Temporelle>
        <Libelle_Classe_Temporelle>Heures Creuses Basses</Libelle_Classe_Temporelle>
        <Rang_Cadran>1</Rang_Cadran>
        <Valeur>83044953</Valeur>
        <Indice_Vraisemblance>0</Indice_Vraisemblance>
      </Classe_Temporelle_Distributeur>

      <!-- Index grille fournisseur -->
      <Classe_Temporelle>
        <Id_Classe_Temporelle>HC</Id_Classe_Temporelle>
        <Libelle_Classe_Temporelle>Heures Creuses</Libelle_Classe_Temporelle>
        <Rang_Cadran>1</Rang_Cadran>
        <Valeur>18047813</Valeur>
        <Indice_Vraisemblance>0</Indice_Vraisemblance>
      </Classe_Temporelle>

      <!-- Puissance maximale -->
      <Puissance_Maximale>
        <Valeur>7452</Valeur>
      </Puissance_Maximale>
    </Donnees_Releve>
  </PRM>
</R151>
```

**Particularités du R151** :
- Structure à 3 niveaux : fichier → PRM → relevé → données
- **3 types de données dans un même relevé**, distingués par le tag XML :
  - `<Classe_Temporelle_Distributeur>` → `type_donnee = "CT_DIST"` (grille distributeur)
  - `<Classe_Temporelle>` → `type_donnee = "CT"` (grille fournisseur)
  - `<Puissance_Maximale>` → `type_donnee = "PMAX"` (puissance maximale atteinte)
- Le discriminant `type_donnee` est **synthétisé par le parser** (il n'existe pas dans le XML)
- Les lignes PMAX n'ont pas de classe temporelle ni d'indice de vraisemblance (stockés `None`)

#### Champs obligatoires

- Balise racine `<R151>`
- `<En_Tete_Flux>` présent
- Chaque `<PRM>` : `<Id_PRM>` non vide
- Chaque `<Donnees_Releve>` : `<Date_Releve>` non vide

#### Données produites

| Champ dataclass | Source XML | Description |
|-----------------|-----------|-------------|
| `header.raw` | Enfants de `<En_Tete_Flux>` | Dictionnaire `{tag: texte}` |
| `prms[].point_id` | `Id_PRM` | PRM 14 chiffres |
| `prms[].releves[].date_releve` | `Date_Releve` | Date du relevé |
| `prms[].releves[].id_calendrier_fournisseur` | `Id_Calendrier_Fournisseur` | Identifiant calendrier |
| `prms[].releves[].libelle_calendrier_fournisseur` | `Libelle_Calendrier_Fournisseur` | Libellé |
| `prms[].releves[].id_calendrier_distributeur` | `Id_Calendrier_Distributeur` | Identifiant calendrier |
| `prms[].releves[].libelle_calendrier_distributeur` | `Libelle_Calendrier_Distributeur` | Libellé |
| `prms[].releves[].id_affaire` | `Id_Affaire` | Identifiant d'affaire |
| `prms[].releves[].donnees[].type_donnee` | *(déduit du tag)* | CT_DIST, CT, ou PMAX |
| `prms[].releves[].donnees[].id_classe_temporelle` | `Id_Classe_Temporelle` | HCB/HCH/HPB/HPH/HC/HP (null pour PMAX) |
| `prms[].releves[].donnees[].libelle_classe_temporelle` | `Libelle_Classe_Temporelle` | Texte humain (null pour PMAX) |
| `prms[].releves[].donnees[].rang_cadran` | `Rang_Cadran` | Numéro de cadran (null pour PMAX) |
| `prms[].releves[].donnees[].valeur` | `Valeur` | Index en Wh ou puissance en VA |
| `prms[].releves[].donnees[].indice_vraisemblance` | `Indice_Vraisemblance` | 0-15 (null pour PMAX) |

---

## 9. Pipeline d'ingestion

**Fichier** : `pipeline.py`

Le pipeline orchestre l'ensemble du processus : classification → hash → décryptage → parsing → stockage. Il fonctionne en deux modes : traitement unitaire (`ingest_file()`) et traitement batch (`ingest_directory()`).

### 9.1 Traitement unitaire : `ingest_file()`

Traite un seul fichier `.zip` et retourne un `FluxStatus`.

**Séquence de traitement :**

```
ingest_file(file_path, session, keys)
│
├── classify_flux(filename) → FluxType
├── SHA256(ciphertext) → file_hash
│
├── VÉRIFICATION IDEMPOTENCE (recherche par file_hash) :
│   ├── Statut PARSED/SKIPPED/NEEDS_REVIEW/PERMANENTLY_FAILED → retour immédiat (no-op)
│   ├── Statut ERROR, nb erreurs >= MAX_RETRIES → archiver erreur, PERMANENTLY_FAILED
│   ├── Statut ERROR, nb erreurs < MAX_RETRIES → archiver erreur, préparer retry
│   └── Statut RECEIVED → reprise après crash
│
├── Type dans {R172, X14, HDM, UNKNOWN} ? → SKIPPED
├── Type absent de la dispatch table ? → SKIPPED
│
├── DÉTECTION REPUBLICATION :
│   └── Même filename + statut PARSED/NEEDS_REVIEW ? → is_republication = true
│
├── decrypt_file() → xml_bytes  (ou ERROR si décryptage impossible)
├── parser_fn() → dataclass     (ou ERROR si parsing impossible)
│
└── STOCKAGE :
    ├── Republication → status=NEEDS_REVIEW, version=N+1, supersedes_file_id=prev.id
    └── Normal → status=PARSED, version=1
    ├── Création/mise à jour EnedisFluxFile + flush (obtention de l'id)
    ├── store_fn() → bulk insert des mesures (chunks de 1000)
    └── commit (ou rollback + ERROR en cas d'exception)
```

### 9.2 Traitement batch : `ingest_directory()`

Traite un répertoire entier de fichiers `.zip` en deux phases.

**Phase 1 -- Scan et enregistrement :**

Pour chaque fichier `.zip` trouvé (glob `*.zip`, optionnellement récursif, trié par nom) :
1. Calcul du SHA256
2. Recherche en base par hash
3. Selon le statut existant :
   - **Pas trouvé** → création d'un enregistrement `EnedisFluxFile` en statut `RECEIVED`
   - **RECEIVED** → fichier périmé d'un run interrompu, ajouté à la file de traitement
   - **ERROR** (< MAX_RETRIES) → ajouté à la file pour retry
   - **ERROR** (>= MAX_RETRIES) → transition vers `PERMANENTLY_FAILED`
   - **PARSED/SKIPPED/NEEDS_REVIEW/PERMANENTLY_FAILED** → comptabilisé comme déjà traité
4. Un seul `commit()` pour tous les enregistrements `RECEIVED` de la phase 1

**Phase 2 -- Traitement :**

Pour chaque fichier de la file :
1. Appel à `ingest_file()` (traitement unitaire)
2. Mise à jour incrémentale des compteurs de l'`IngestionRun` après chaque fichier
3. Si exception non gérée : le fichier `RECEIVED` passe en `ERROR`

**Intérêt de la conception en 2 phases** : si le processus crash pendant la phase 2, les fichiers restent en statut `RECEIVED` et seront automatiquement repris au prochain run.

### Compteurs retournés

| Compteur | Description |
|----------|-------------|
| `received` | Nouveaux fichiers + fichiers RECEIVED périmés |
| `parsed` | Fichiers traités avec succès |
| `needs_review` | Republications ingérées (en attente de review) |
| `skipped` | Flux hors périmètre (R172, X14, HDM, UNKNOWN) |
| `error` | Fichiers en erreur dans ce run |
| `permanently_failed` | Fichiers passés en PERMANENTLY_FAILED dans ce run |
| `already_processed` | Fichiers déjà traités lors d'un run précédent |
| `retried` | Fichiers ERROR retentés dans ce run |
| `max_retries_reached` | Fichiers ayant atteint la limite de retries |

**Invariant** : `received + retried == parsed + needs_review + skipped + error` (en mode non-dry-run).

### 9.3 Idempotence

L'idempotence est assurée à **deux niveaux** :

1. **Niveau fichier (SHA256)** : le hash est calculé sur le fichier **chiffré** (ciphertext brut). La colonne `file_hash` a une contrainte `UNIQUE`. Même contenu physique = skip automatique.

2. **Niveau republication (filename + hash différent)** : si un fichier porte le même nom qu'un fichier déjà traité mais a un contenu différent (hash différent), il est traité comme une republication (voir section 9.4).

Il n'y a **pas d'idempotence au niveau des mesures individuelles**. Si le même PRM/horodatage apparaît dans deux fichiers différents, les deux lignes coexistent dans la table staging.

### 9.4 Détection des republications

Enedis peut republier un fichier avec le même nom mais un contenu corrigé. Le pipeline détecte ce cas :

1. Recherche d'un `EnedisFluxFile` existant avec le même `filename` et un statut `PARSED` ou `NEEDS_REVIEW`
2. Si trouvé : le nouveau fichier est ingéré avec `status = NEEDS_REVIEW`, `version = N+1`, et `supersedes_file_id` pointant vers le fichier précédent
3. Les deux versions (originale et republication) sont conservées en base
4. L'intervenant humain doit ensuite décider quoi faire (d'où le statut `NEEDS_REVIEW`)

### 9.5 Retry et gestion d'erreurs

| Mécanisme | Description |
|-----------|-------------|
| **MAX_RETRIES** | 3 (configurable dans `config.py`), soit 4 tentatives au total (1 initiale + 3 retries) |
| **Historique** | Chaque échec est archivé dans `enedis_flux_file_error` (1 ligne par tentative). Le nombre de lignes sert de compteur de retries. |
| **Escalade** | Après 3 erreurs archivées → le fichier passe en `PERMANENTLY_FAILED` et n'est plus retenté |
| **Recovery** | Les fichiers en `ERROR` (< MAX_RETRIES) sont automatiquement retentés lors du prochain run de `ingest_directory()` |

### 9.6 Mode dry-run

En mode `dry_run=True` :
- La phase 1 (scan) s'exécute mais **aucun enregistrement n'est créé** en base
- La phase 2 (traitement) est **entièrement ignorée**
- Les transitions vers `PERMANENTLY_FAILED` sont aussi ignorées
- Un `IngestionRun` est quand même créé (pour audit), marqué `dry_run=true`
- Le rapport affiche les fichiers qui *seraient* traités

### Table de dispatch

Le routage d'un type de flux vers son parser et sa fonction de stockage est centralisé dans une table de dispatch :

```python
_DISPATCH = {
    FluxType.R4H:  (parse_r4x,  R4xParseError,  _store_r4x),
    FluxType.R4M:  (parse_r4x,  R4xParseError,  _store_r4x),
    FluxType.R4Q:  (parse_r4x,  R4xParseError,  _store_r4x),
    FluxType.R171: (parse_r171, R171ParseError, _store_r171),
    FluxType.R50:  (parse_r50,  R50ParseError,  _store_r50),
    FluxType.R151: (parse_r151, R151ParseError, _store_r151),
}
```

Pour ajouter un nouveau type de flux, il suffit de :
1. Créer un parser (fonction pure `bytes → dataclass`)
2. Créer un modèle SQLAlchemy (table de mesures)
3. Créer une fonction de stockage (`_store_xxx`)
4. Ajouter une entrée dans `_DISPATCH`

---

## 10. Modèle de données

Toutes les tables utilisent le `Base` partagé de SQLAlchemy (`models.base.Base`) et le `TimestampMixin` qui ajoute automatiquement `created_at` et `updated_at`.

Les mesures sont stockées en tant que **chaînes de caractères brutes** (aucune conversion en `float` ou `datetime`).

Les suppressions sont en **cascade** : supprimer un `EnedisFluxFile` supprime automatiquement toutes ses mesures et ses erreurs.

### 10.1 `enedis_flux_file`

Registre central : un enregistrement par fichier ingéré.

| Colonne | Type | Null | Description |
|---------|------|------|-------------|
| `id` | Integer PK | | Identifiant auto-incrémenté |
| `filename` | String(255) | non | Nom du fichier `.zip` original |
| `file_hash` | String(64) | non | SHA256 du fichier chiffré (**UNIQUE**) |
| `flux_type` | String(10) | non | R4H, R4M, R4Q, R171, R50, R151, etc. |
| `status` | String(20) | non | received / parsed / error / skipped / needs_review / permanently_failed |
| `error_message` | Text | oui | Message d'erreur de la dernière tentative |
| `measures_count` | Integer | oui | Nombre de mesures extraites et stockées |
| `version` | Integer | non | 1 = original, 2+ = republication |
| `supersedes_file_id` | Integer FK→self | oui | Pointe vers le fichier remplacé (SET NULL à la suppression) |
| `frequence_publication` | String(5) | oui | H/M/Q -- R4x uniquement |
| `nature_courbe_demandee` | String(20) | oui | Brute/Corrigee -- R4x uniquement |
| `identifiant_destinataire` | String(100) | oui | Code destinataire -- R4x uniquement |
| `header_raw` | Text | oui | En-tête XML complet sérialisé en JSON |
| `created_at` | DateTime | | Horodatage de création |
| `updated_at` | DateTime | | Horodatage de dernière modification |

**Relations** : `mesures_r4x`, `mesures_r171`, `mesures_r50`, `mesures_r151`, `errors` (toutes en cascade delete-orphan).

### 10.2 `enedis_flux_mesure_r4x`

Mesures CDC haute fréquence (C1-C4). Entièrement dénormalisé : chaque ligne porte le contexte de son bloc `<Donnees_Courbe>`.

| Colonne | Type | Null | Description |
|---------|------|------|-------------|
| `id` | Integer PK | | |
| `flux_file_id` | Integer FK | non | FK vers `enedis_flux_file` (CASCADE) |
| `flux_type` | String(10) | non | R4H/R4M/R4Q (dénormalisé) |
| `point_id` | String(14) | non | PRM 14 chiffres |
| `grandeur_physique` | String(10) | oui | EA/ERI/ERC/E |
| `grandeur_metier` | String(10) | oui | CONS/PROD |
| `unite_mesure` | String(10) | oui | kW/kWr/V |
| `granularite` | String(10) | oui | Pas en minutes (5/10) |
| `horodatage_debut` | String(50) | oui | Début de la période du bloc |
| `horodatage_fin` | String(50) | oui | Fin de la période du bloc |
| `horodatage` | String(50) | non | Horodatage du point (ISO8601) |
| `valeur_point` | String(20) | oui | Valeur brute |
| `statut_point` | String(2) | oui | R/H/P/S/T/F/G/E/C/K/D |

**Index** : `(point_id, horodatage)`, `flux_file_id`, `flux_type`

### 10.3 `enedis_flux_mesure_r171`

Index journalier (C2-C4). 1 ligne par `mesureDatee`.

| Colonne | Type | Null | Description |
|---------|------|------|-------------|
| `id` | Integer PK | | |
| `flux_file_id` | Integer FK | non | FK vers `enedis_flux_file` (CASCADE) |
| `flux_type` | String(10) | non | R171 |
| `point_id` | String(14) | non | PRM 14 chiffres |
| `type_mesure` | String(10) | non | INDEX |
| `grandeur_metier` | String(10) | oui | CONS |
| `grandeur_physique` | String(10) | oui | DD/DQ/EA/ERC/ERI/PMA/TF |
| `type_calendrier` | String(5) | oui | D |
| `code_classe_temporelle` | String(10) | oui | HCE/HCH/HPE/HPH/P |
| `libelle_classe_temporelle` | String(100) | oui | Texte humain |
| `unite` | String(10) | oui | Wh/VArh/VA/s |
| `date_fin` | String(50) | non | dateFin (ISO8601) |
| `valeur` | String(20) | oui | Valeur brute |

**Index** : `(point_id, date_fin)`, `flux_file_id`, `flux_type`

### 10.4 `enedis_flux_mesure_r50`

Courbe de charge C5. 1 ligne par PDC (point de courbe, pas de 30 min).

| Colonne | Type | Null | Description |
|---------|------|------|-------------|
| `id` | Integer PK | | |
| `flux_file_id` | Integer FK | non | FK vers `enedis_flux_file` (CASCADE) |
| `flux_type` | String(10) | non | R50 |
| `point_id` | String(14) | non | PRM 14 chiffres |
| `date_releve` | String(20) | non | Date du relevé |
| `id_affaire` | String(20) | oui | Identifiant d'affaire |
| `horodatage` | String(50) | non | Horodatage du PDC (ISO8601+TZ) |
| `valeur` | String(20) | oui | Valeur brute |
| `indice_vraisemblance` | String(5) | oui | 0 ou 1 |

**Index** : `(point_id, horodatage)`, `flux_file_id`, `flux_type`

### 10.5 `enedis_flux_mesure_r151`

Index et puissance maximale C5. 1 ligne par valeur (index par classe temporelle ou puissance max).

| Colonne | Type | Null | Description |
|---------|------|------|-------------|
| `id` | Integer PK | | |
| `flux_file_id` | Integer FK | non | FK vers `enedis_flux_file` (CASCADE) |
| `flux_type` | String(10) | non | R151 |
| `point_id` | String(14) | non | PRM 14 chiffres |
| `date_releve` | String(20) | non | Date du relevé |
| `id_calendrier_fournisseur` | String(20) | oui | |
| `libelle_calendrier_fournisseur` | String(100) | oui | |
| `id_calendrier_distributeur` | String(20) | oui | |
| `libelle_calendrier_distributeur` | String(150) | oui | |
| `id_affaire` | String(20) | oui | |
| `type_donnee` | String(10) | non | CT_DIST / CT / PMAX (déduit du tag XML) |
| `id_classe_temporelle` | String(10) | oui | HCB/HCH/HPB/HPH/HC/HP (null pour PMAX) |
| `libelle_classe_temporelle` | String(100) | oui | Texte humain (null pour PMAX) |
| `rang_cadran` | String(5) | oui | Numéro de cadran (null pour PMAX) |
| `valeur` | String(20) | oui | Index Wh ou puissance VA |
| `indice_vraisemblance` | String(5) | oui | 0-15 (null pour PMAX) |

**Index** : `(point_id, date_releve)`, `flux_file_id`, `flux_type`

### 10.6 `enedis_flux_file_error`

Historique des erreurs de traitement. 1 ligne par tentative échouée.

| Colonne | Type | Null | Description |
|---------|------|------|-------------|
| `id` | Integer PK | | |
| `flux_file_id` | Integer FK | non | FK vers `enedis_flux_file` (CASCADE) |
| `error_message` | Text | non | Message d'erreur de la tentative |
| `created_at` | DateTime | | Horodatage de l'erreur |
| `updated_at` | DateTime | | |

Le nombre de lignes pour un `flux_file_id` donné sert de **compteur de retries** (pas de colonne dédiée).

**Index** : `flux_file_id`

### 10.7 `enedis_ingestion_run`

Audit de chaque exécution du pipeline. Les compteurs sont mis à jour **de manière incrémentale** (après chaque fichier traité), ce qui permet de voir la progression même en cas de crash.

| Colonne | Type | Null | Description |
|---------|------|------|-------------|
| `id` | Integer PK | | |
| `started_at` | DateTime | non | Début du run |
| `finished_at` | DateTime | oui | Fin du run (null si en cours) |
| `directory` | String(500) | non | Répertoire source scanné |
| `recursive` | Boolean | non | Scan récursif |
| `dry_run` | Boolean | non | Mode dry-run |
| `status` | String(20) | non | running / completed / failed |
| `triggered_by` | String(10) | non | cli / api |
| `files_received` | Integer | | Nouveaux fichiers à traiter |
| `files_parsed` | Integer | | Fichiers parsés avec succès |
| `files_skipped` | Integer | | Flux hors périmètre |
| `files_error` | Integer | | Fichiers en erreur |
| `files_needs_review` | Integer | | Republications en attente de review |
| `files_already_processed` | Integer | | Fichiers déjà traités |
| `files_retried` | Integer | | Fichiers ERROR retentés |
| `files_max_retries` | Integer | | Fichiers PERMANENTLY_FAILED |
| `error_message` | Text | oui | Erreur ayant interrompu le run |

---

## 11. API REST

**Fichier** : `backend/routes/enedis.py`
**Préfixe** : `/api/enedis`
**Authentification** : aucune (POC)

### POST /api/enedis/ingest

Déclenche le pipeline d'ingestion de manière **synchrone** (bloquant).

**Corps de la requête** (`IngestRequest`) :

| Champ | Type | Défaut | Description |
|-------|------|--------|-------------|
| `directory` | string (opt.) | null | Override de `ENEDIS_FLUX_DIR` |
| `recursive` | bool | true | Scan récursif |
| `dry_run` | bool | false | Mode simulation |

**Validations préalables** :
1. Résolution du répertoire flux (422 si non configuré ou inexistant)
2. Chargement des clés de décryptage (422 si absentes)
3. Vérification de concurrence : rejet 409 si un run est déjà en cours

**Réponse** (`IngestResponse`) :

| Champ | Type | Description |
|-------|------|-------------|
| `run_id` | int | Identifiant du run |
| `status` | string | completed / failed |
| `dry_run` | bool | |
| `duration_seconds` | float | Durée d'exécution |
| `counters` | dict | Compteurs du pipeline (voir section 9.2) |
| `errors` | list | Fichiers en ERROR/PERMANENTLY_FAILED modifiés pendant ce run |

**Codes retour** : 200 (succès), 409 (run concurrent), 422 (config invalide), 500 (erreur pipeline)

### GET /api/enedis/flux-files

Liste paginée des fichiers flux avec filtres optionnels.

**Paramètres query** :

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `status` | string (opt.) | null | Filtrer par statut (parsed, error, etc.) |
| `flux_type` | string (opt.) | null | Filtrer par type de flux (R4H, R171, etc.) |
| `limit` | int | 24 | Taille de page (1-200) |
| `offset` | int | 0 | Décalage |

**Réponse** (`FluxFileListResponse`) :

| Champ | Type |
|-------|------|
| `total` | int |
| `items` | liste de `FluxFileResponse` (id, filename, file_hash, flux_type, status, error_message, measures_count, version, supersedes_file_id, created_at, updated_at) |
| `limit`, `offset` | int |

### GET /api/enedis/flux-files/{id}

Détail d'un fichier flux avec en-tête XML complet et historique des erreurs.

**Réponse** (`FluxFileDetailResponse`) : tous les champs de `FluxFileResponse` plus :

| Champ | Type | Description |
|-------|------|-------------|
| `header_raw` | dict (opt.) | En-tête XML complet décodé du JSON |
| `frequence_publication` | string (opt.) | H/M/Q (R4x uniquement) |
| `nature_courbe_demandee` | string (opt.) | Brute/Corrigee (R4x uniquement) |
| `identifiant_destinataire` | string (opt.) | Code destinataire (R4x uniquement) |
| `errors_history` | liste | Toutes les tentatives échouées (error_message, created_at) |

**Code retour** : 200 ou 404

### GET /api/enedis/stats

Dashboard agrégé de la couche staging.

**Réponse** (`StatsResponse`) :

```json
{
  "files": {
    "total": 91,
    "by_status": {"parsed": 81, "skipped": 7, "needs_review": 3},
    "by_flux_type": {"R4H": 5, "R4M": 4, "R171": 64, ...}
  },
  "measures": {
    "total": 123846,
    "r4x": 98234,
    "r171": 15432,
    "r50": 8180,
    "r151": 2000
  },
  "prms": {
    "count": 12,
    "identifiers": ["30000210411333", "30000550506121", ...]
  },
  "last_ingestion": {
    "run_id": 5,
    "timestamp": "2026-03-28T14:30:00Z",
    "files_count": 91,
    "triggered_by": "cli"
  }
}
```

La liste des PRM est obtenue par un `UNION DISTINCT` sur les 4 tables de mesures.

---

## 12. Interface CLI

**Fichier** : `cli.py`
**Invocation** : `cd promeos-poc/backend && python -m data_ingestion.enedis.cli ingest [OPTIONS]`

### Commande `ingest`

| Option | Description |
|--------|-------------|
| `--dir PATH` | Override de la variable `ENEDIS_FLUX_DIR` |
| `--dry-run` | Scan et classification sans écriture en base |
| `--no-recursive` | Désactiver le scan récursif (récursif par défaut) |
| `--verbose` | Activer le logging DEBUG |

### Séquence d'exécution

1. Configuration du logging (INFO par défaut, DEBUG avec `--verbose`)
2. Bootstrap des tables (`_ensure_tables` : création des tables + migrations)
3. Résolution du répertoire flux
4. Chargement des clés de décryptage
5. Vérification de concurrence (exit code 1 si un run est déjà en cours)
6. Création de l'`IngestionRun` (statut `RUNNING`)
7. Exécution de `ingest_directory()`
8. Affichage du rapport
9. Exit code 0 (succès) ou 1 (erreur)

### Rapport d'exécution

Le rapport affiche :
- Identifiant et statut du run
- Répertoire source et mode (récursif ou non)
- Durée
- Compteurs par statut (received, parsed, skipped, error, needs_review, retried, max_retries, already_processed)
- **Totaux staging** : nombre de mesures par table (R4x, R171, R50, R151) et total
- **Détail des erreurs** : nom de fichier et message pour chaque fichier en erreur

---

## 13. Configuration

### Variables d'environnement requises

| Variable | Description | Exemple |
|----------|-------------|---------|
| `ENEDIS_FLUX_DIR` | Répertoire contenant les fichiers `.zip` chiffrés | `/data/flux_enedis` |
| `KEY_1` | Clé AES-128 (hex, 32 chars) | `00112233445566778899aabbccddeeff` |
| `IV_1` | Vecteur d'initialisation (hex, 32 chars) | `aabbccddeeff00112233445566778899` |
| `KEY_2`, `IV_2` | 2e paire de clés | |
| `KEY_3`, `IV_3` | 3e paire de clés | |

Les paires de clés sont numérotées de 1 à 9. Le chargement s'arrête au premier indice absent.

### Paramètres internes

| Paramètre | Valeur | Fichier | Description |
|-----------|--------|---------|-------------|
| `MAX_RETRIES` | 3 | `config.py` | Nombre max de retries (4 tentatives au total) |
| `DEFAULT_CHUNK_SIZE` | 1000 | `pipeline.py` | Taille de batch pour l'insertion des mesures |

---

## 14. Tests

**Répertoire** : `backend/data_ingestion/enedis/tests/`

### Organisation

| Fichier | Couverture | Nb de tests |
|---------|-----------|-------------|
| `test_decrypt.py` | Classification, décryptage, gestion des clés | 17 |
| `test_parsers_r4.py` | Parser R4x : header, courbes, points, erreurs | 19 |
| `test_parsers_r171.py` | Parser R171 : séries, mesures, namespaces, erreurs | 22 |
| `test_parsers_r50.py` | Parser R50 : PRMs, relevés, PDC, ERDF | 22 |
| `test_parsers_r151.py` | Parser R151 : CT_DIST/CT/PMAX, calendriers | 26 |
| `test_models.py` | 7 modèles SQLAlchemy, relations, cascades | 45 |
| `test_pipeline.py` | `ingest_file()` : idempotence, retry, republication, erreurs | 41 |
| `test_pipeline_full.py` | `ingest_directory()` : batch, dry-run, compteurs, multi-flux | 23 |
| `test_config.py` | `get_flux_dir()`, MAX_RETRIES | 10 |
| `test_cli.py` | CLI : ingest, dry-run, verbose, concurrence | 9 |
| `test_integration.py` | Intégration avec fichiers réels (skip sans clés) | 2 (paramétrés) |
| `test_e2e_real_files.py` | E2E complet avec fichiers chiffrés réels | 5 |

**Total** : ~265 tests (incluant les tests API dans `backend/tests/test_enedis_api.py`).

### Données de test

- Les tests unitaires utilisent des **XML synthétiques** construits par des fonctions helper dans chaque fichier de test
- Les tests de décryptage utilisent des **clés de test** codées en dur et des fichiers chiffrés générés par `make_encrypted_zip()` (dans `conftest.py`)
- Les tests d'intégration et E2E utilisent des **fichiers réels** situés hors du repo (`flux_enedis/`) et sont **ignorés en CI** (absence de clés)

### Exécution

```bash
# Tous les tests Enedis
cd promeos-poc/backend
./venv/bin/pytest data_ingestion/enedis/tests/ -x -v

# Tests API Enedis
./venv/bin/pytest tests/test_enedis_api.py -x -v
```

---

## 15. Cycle de vie d'un fichier (machine à états)

```
                        ┌──────────┐
   Nouveau fichier ────▶│ RECEIVED │◄──── Reprise après crash
                        └────┬─────┘
                             │
                    ┌────────┼────────────────────┐
                    │        │                     │
                    ▼        ▼                     ▼
              ┌──────────┐ ┌────────┐       ┌──────────┐
              │ SKIPPED  │ │ PARSED │       │  ERROR   │
              │(hors     │ │        │       │          │
              │ scope)   │ └────────┘       └────┬─────┘
              └──────────┘                       │
                                          retry < MAX ?
                                           │         │
                                          oui       non
                                           │         │
                                           ▼         ▼
                                    ┌──────────┐ ┌───────────────────┐
                                    │ RECEIVED │ │PERMANENTLY_FAILED │
                                    │(retry)   │ │                   │
                                    └──────────┘ └───────────────────┘

              ┌──────────────┐
              │ NEEDS_REVIEW │◄──── Republication détectée
              │              │      (même filename, hash différent)
              └──────────────┘
```

| Statut | Signification | Action requise |
|--------|---------------|----------------|
| `received` | Fichier enregistré, en attente de traitement | Aucune (traitement automatique) |
| `parsed` | Ingéré avec succès | Aucune |
| `skipped` | Type de flux hors périmètre (R172, X14, HDM, UNKNOWN) | Aucune |
| `error` | Échec de traitement, retry possible | Retry automatique au prochain run |
| `needs_review` | Republication ingérée, les deux versions coexistent | Revue humaine nécessaire |
| `permanently_failed` | MAX_RETRIES atteint, fichier abandonné | Investigation manuelle |

---

## 16. Glossaire

| Terme | Définition |
|-------|------------|
| **SGE** | Système de Gestion des Échanges -- plateforme Enedis d'échange de données de comptage |
| **PRM** | Point de Référence Mesure -- identifiant unique d'un point de comptage (14 chiffres) |
| **CDC** | Courbe de charge -- série temporelle de mesures de puissance/énergie |
| **C1-C4** | Segments de comptage pour compteurs télérelevés haute fréquence (puissance > 36 kVA) |
| **C5** | Segment de comptage pour compteurs Linky basse tension (puissance <= 36 kVA) |
| **Flux** | Fichier de données publié par Enedis selon un format XML normalisé |
| **Republication** | Nouvelle version d'un fichier déjà publié par Enedis (corrections) |
| **Staging** | Couche de stockage brut -- archive fidèle des données XML sans transformation |
| **ADR** | Accord de Données de Référence -- standard Enedis pour les formats de flux |
| **FTP** | Protocole de transfert de fichiers utilisé pour la publication des flux SGE |
| **Classe temporelle** | Découpage tarifaire de la consommation (HPH, HCH, HPE, HCE, etc.) |
| **Indice de vraisemblance** | Indicateur de qualité de la mesure (0 = réelle, 1+ = estimée) |
| **ERDF** | Ancien nom d'Enedis (Électricité Réseau Distribution France) -- présent dans certains flux |
| **Dry-run** | Mode d'exécution qui simule le traitement sans écrire en base |
