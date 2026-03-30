# ADR V70 — SF3 : Structures XML R171, R50, R151 et mapping colonnes

> Date : 2026-03-24
> Contexte : SF3-A Etape 1 — Analyse des fichiers XML reels avant toute ecriture de code
> Source : Dechiffrement de fichiers reels avec `decrypt_file()` + croisement specs Enedis

---

## Contexte

SF3 etend le pipeline d'ingestion pour supporter 3 nouveaux types de flux :
- **R171** : Index journalier C2-C4 (64 fichiers dans `flux_enedis/C1-C4/`)
- **R50** : Courbe de charge C5 (5 fichiers dans `flux_enedis/C5/`)
- **R151** : Index + Puissance maximale C5 (5 fichiers dans `flux_enedis/C5/`)

Cette ADR documente la structure XML exacte observee dans les fichiers reels et definit le mapping vers des colonnes SQLAlchemy pour chaque type.

---

## Decouverte importante : R171 != R17

Le guide Enedis `Enedis-R17.pdf` decrit le flux R17 avec une racine XML `<Index_C2_C3_C4>` et une structure profondement imbriquee (Corps_PRM > Donnees_Releve > Donnees_Par_Type_Mesure > Index_Par_Classe_Temporelle > Index).

**Les fichiers R171 reels utilisent un schema completement different** : racine `<ns2:R171 xmlns:ns2="http://www.enedis.fr/stm/R171">` avec une structure plate de series. Aucun champ du spec R17 n'est "manquant" — ce sont deux schemas distincts.

Pour R50 et R151, aucune spec formelle XML n'est disponible dans notre base documentaire. Le guide R6X couvre R63/R64 (formats JSON/CSV du portail Client Entreprise), qui portent des donnees similaires mais avec des schemas differents. L'analyse repose sur les fichiers reels.

---

## R171 — Index journalier C2-C4

### Metadonnees fichier

| Propriete | Valeur observee |
|-----------|----------------|
| Racine XML | `<ns2:R171 xmlns:ns2="http://www.enedis.fr/stm/R171">` |
| Prefixe fichier | `ENEDIS_R171_C_` |
| PRMs par fichier | Multiple (9-14 observes sur 10 fichiers) |
| Taille typique | ~58-189 Ko |

### Structure XML

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
    <serieMesuresDatees>              <!-- N series, une par PRM+grandeur+classe -->
      <prmId>30000550506121</prmId>
      <type>INDEX</type>
      <grandeurMetier>CONS</grandeurMetier>
      <grandeurPhysique>EA</grandeurPhysique>
      <typeCalendrier>D</typeCalendrier>
      <codeClasseTemporelle>HPH</codeClasseTemporelle>
      <libelleClasseTemporelle>Heures Pleines Hiver / Saison Haute</libelleClasseTemporelle>
      <unite>Wh</unite>
      <mesuresDateesListe>
        <mesureDatee>                 <!-- 1 mesure par serie (100% des cas observes) -->
          <dateFin>2026-03-01T00:51:11</dateFin>
          <valeur>1320</valeur>
        </mesureDatee>
      </mesuresDateesListe>
    </serieMesuresDatees>
  </serieMesuresDateesListe>
</ns2:R171>
```

### Analyse exhaustive (10 fichiers, 1624 series)

| Champ | Cardinalite | Valeurs observees |
|-------|------------|-------------------|
| `prmId` | 1 par serie | 14 PRMs distincts |
| `type` | 1 par serie | `INDEX` (100%) |
| `grandeurMetier` | 1 par serie | `CONS` (100%) |
| `grandeurPhysique` | 1 par serie | `DD`, `DQ`, `EA`, `ERC`, `ERI`, `PMA`, `TF` |
| `typeCalendrier` | 1 par serie | `D` (100%) |
| `codeClasseTemporelle` | 1 par serie | `HCE`, `HCH`, `HPE`, `HPH`, `P` |
| `libelleClasseTemporelle` | 1 par serie | Libelle humain de la classe |
| `unite` | 1 par serie | `Wh`, `VArh`, `VA`, `s` |
| `dateFin` | 1 par mesure | ISO8601 sans timezone |
| `valeur` | 1 par mesure | Entier (string brute) |

**Note** : `mesuresDateesListe` contient toujours exactement 1 `mesureDatee` dans nos donnees. Le parser doit supporter N mesures par serie au cas ou, mais le stockage est 1 row par mesure.

### Champs potentiellement absents

Le R171 ne contient PAS de `dateDebut` (seulement `dateFin`). Pas de `statutMesure`, `natureMesure`, ou `motifRectif` (presents dans le R17 spec mais qui est un schema different). Le schema R171 est complet tel qu'observe.

### Entete — champs pour `header_raw`

| Champ | Exemple |
|-------|---------|
| `emetteur` | Enedis |
| `destinataire` | GRD-F121 |
| `dateHeureCreation` | 2026-03-01T01:13:01 |
| `flux` | R171 |
| `version` | 1.0 |

---

## R50 — Courbe de charge C5

### Metadonnees fichier

| Propriete | Valeur observee |
|-----------|----------------|
| Racine XML | `<R50 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">` |
| Prefixe fichier | `ERDF_R50_` (prefixe historique) |
| PRMs par fichier | Multiple (7 observes, constant sur 5 fichiers) |
| Taille typique | ~41 Ko |
| Pas de publication | 30 minutes |

**Correction par rapport au spec SF3** : le R50 est une **courbe de charge** (CDC) a pas de 30 minutes, PAS un "index mensuel". Le `Libelle_Flux` confirme : "Courbes de charge des PRM du segment C5 sur abonnement".

### Structure XML

```xml
<R50 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <En_Tete_Flux>
    <Identifiant_Flux>R50</Identifiant_Flux>
    <Libelle_Flux>Courbes de charge des PRM du segment C5 sur abonnement</Libelle_Flux>
    <Version_XSD>1.1.0</Version_XSD>
    <Identifiant_Emetteur>ERDF</Identifiant_Emetteur>
    <Identifiant_Destinataire>23X--130624--EE1</Identifiant_Destinataire>
    <Date_Creation>2023-01-06T19:02:30+01:00</Date_Creation>
    <Identifiant_Contrat>GRD-F121</Identifiant_Contrat>
    <Numero_Abonnement>3363068</Numero_Abonnement>
    <Pas_Publication>30</Pas_Publication>
  </En_Tete_Flux>
  <PRM>                                <!-- N PRM par fichier -->
    <Id_PRM>01445441288824</Id_PRM>
    <Donnees_Releve>                   <!-- 1..N releves par PRM (1 par jour) -->
      <Date_Releve>2023-01-02</Date_Releve>
      <Id_Affaire>M041AWXF</Id_Affaire>
      <PDC>                            <!-- 48 PDC par jour (30 min * 24h) -->
        <H>2023-01-02T16:30:00+01:00</H>
        <V>20710</V>                   <!-- optionnel : absent si pas de donnee -->
        <IV>0</IV>                     <!-- optionnel : absent si pas de donnee -->
      </PDC>
    </Donnees_Releve>
  </PRM>
</R50>
```

### Analyse exhaustive (5 fichiers)

| Champ | Cardinalite | Valeurs observees |
|-------|------------|-------------------|
| `Id_PRM` | 1 par PRM | 7 PRMs distincts (14 chiffres) |
| `Date_Releve` | 1 par releve | Date ISO (2023-01-02) |
| `Id_Affaire` | 1 par releve | Code affaire (M041AWXF) |
| `H` (horodatage) | 1 par PDC | ISO8601 avec timezone (+01:00) |
| `V` (valeur) | 0..1 par PDC | Entier (string brute), absent si pas de mesure |
| `IV` (indice vraisemblance) | 0..1 par PDC | `0` ou `1` (absent si V absent) |

**Points PDC sans valeur** : 32 PDC sur 96 n'ont que `<H>` (pas de `<V>` ni `<IV>`). Cela correspond aux creneaux sans mesure (compteur pas encore actif ou absence de donnee).

### Entete — champs specifiques R50

Le R50 a des champs d'entete supplementaires par rapport au R4x :
- `Numero_Abonnement` : identifiant de l'abonnement a la publication
- `Pas_Publication` : pas en minutes (30)

### Champs potentiellement absents

Le guide R6X (R63 CDC JSON) inclut des champs supplementaires par point : `p` (pas), `n` (nature), `tc` (type correction), `ec` (etat complementaire). Le format XML R50 ne les contient PAS — c'est un format legacy plus simple. Seuls H, V, IV sont presents par PDC.

---

## R151 — Index + Puissance maximale C5

### Metadonnees fichier

| Propriete | Valeur observee |
|-----------|----------------|
| Racine XML | `<R151 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">` |
| Prefixe fichier | `ERDF_R151_` (prefixe historique) |
| PRMs par fichier | 1 (observe sur 5 fichiers) |
| Taille typique | ~3 Ko |

### Structure XML

```xml
<R151 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <En_Tete_Flux>
    <Identifiant_Flux>R151</Identifiant_Flux>
    <Libelle_Flux>Puissances maximales et index des PRM du segment C5 sur abonnement</Libelle_Flux>
    <Version_XSD>V1</Version_XSD>
    <Identifiant_Emetteur>ERDF</Identifiant_Emetteur>
    <Identifiant_Destinataire>23X--130624--EE1</Identifiant_Destinataire>
    <Date_Creation>2024-12-19T03:06:52+01:00</Date_Creation>
    <Identifiant_Contrat>GRD-F121</Identifiant_Contrat>
    <Numero_Abonnement>3363155</Numero_Abonnement>
    <Unite_Mesure_Index>Wh</Unite_Mesure_Index>
    <Unite_Mesure_Puissance>VA</Unite_Mesure_Puissance>
  </En_Tete_Flux>
  <PRM>
    <Id_PRM>17745151915440</Id_PRM>
    <Donnees_Releve>
      <Date_Releve>2024-12-17</Date_Releve>
      <Id_Calendrier_Fournisseur>FC020831</Id_Calendrier_Fournisseur>
      <Libelle_Calendrier_Fournisseur>Heures Pleines/Creuses</Libelle_Calendrier_Fournisseur>
      <Id_Calendrier_Distributeur>DI000003</Id_Calendrier_Distributeur>
      <Libelle_Calendrier_Distributeur>Avec differenciation temporelle...</Libelle_Calendrier_Distributeur>
      <Id_Affaire>M07E7D2I</Id_Affaire>

      <!-- Index par classe temporelle de la grille distributeur (0..N) -->
      <Classe_Temporelle_Distributeur>
        <Id_Classe_Temporelle>HCB</Id_Classe_Temporelle>
        <Libelle_Classe_Temporelle>Heures Creuses Saison Basse</Libelle_Classe_Temporelle>
        <Rang_Cadran>1</Rang_Cadran>
        <Valeur>83044953</Valeur>
        <Indice_Vraisemblance>0</Indice_Vraisemblance>
      </Classe_Temporelle_Distributeur>

      <!-- Index par classe temporelle de la grille fournisseur (0..N) -->
      <Classe_Temporelle>
        <Id_Classe_Temporelle>HC</Id_Classe_Temporelle>
        <Libelle_Classe_Temporelle>Heures Creuses</Libelle_Classe_Temporelle>
        <Rang_Cadran>1</Rang_Cadran>
        <Valeur>18047813</Valeur>
        <Indice_Vraisemblance>0</Indice_Vraisemblance>
      </Classe_Temporelle>

      <!-- Puissance maximale (0..1) -->
      <Puissance_Maximale>
        <Valeur>7452</Valeur>
      </Puissance_Maximale>
    </Donnees_Releve>
  </PRM>
</R151>
```

### Analyse exhaustive (5 fichiers)

| Bloc | Cardinalite par Donnees_Releve | Champs |
|------|-------------------------------|--------|
| `Classe_Temporelle_Distributeur` | 4 (constant) | Id_Classe_Temporelle, Libelle, Rang_Cadran, Valeur, Indice_Vraisemblance |
| `Classe_Temporelle` (fournisseur) | 2 (constant) | Memes champs |
| `Puissance_Maximale` | 1 (constant) | Valeur uniquement |

Valeurs Classe_Temporelle_Distributeur : HCB, HCH, HPB, HPH
Valeurs Classe_Temporelle (fournisseur) : HC, HP
Indice_Vraisemblance observe : `0` uniquement (mais spec R6X definit 0-15)

### Entete — champs specifiques R151

- `Numero_Abonnement` : identifiant de l'abonnement
- `Unite_Mesure_Index` : Wh
- `Unite_Mesure_Puissance` : VA

---

## Decision : 1 table par type de flux

Les trois formats XML sont **structurellement incompatibles** :
- R171 : series plates (prmId + contexte + mesure)
- R50 : CDC a pas regulier (PRM > releves journaliers > points 30 min)
- R151 : index par classe temporelle (PRM > releve > classes dist + fourn + puissance max)

| Decision | Choix | Rationale |
|----------|-------|-----------|
| Nombre de tables | 3 tables separees | Structures XML incompatibles — une table partagee forcerait trop de colonnes nullables et perdrait la semantique |
| Nommage | `enedis_flux_mesure_r171`, `_r50`, `_r151` | Coherent avec `enedis_flux_mesure_r4x` |
| Valeurs brutes strings | Oui | Coherent avec V69 — zero transformation en staging |
| FK vers `enedis_flux_file` | Oui, CASCADE | Meme pattern que R4x |
| Pas de contrainte unique | Oui | Coherent avec SF2 — archiver sans dedup |

---

## Mapping XML vers colonnes SQLAlchemy

### `enedis_flux_mesure_r171`

Granularite : **1 row par mesureDatee** (= 1 row par serie dans les donnees observees).

| Colonne | Source XML | Type SQLAlchemy | Nullable | Commentaire |
|---------|-----------|----------------|----------|-------------|
| `id` | auto | `Integer, PK` | No | |
| `flux_file_id` | FK | `Integer, FK(enedis_flux_file.id, CASCADE)` | No | |
| `flux_type` | "R171" | `String(10)` | No | Denormalise pour requetes |
| `point_id` | `prmId` | `String(14)` | No | PRM |
| `type_mesure` | `type` | `String(10)` | No | INDEX (toujours) |
| `grandeur_metier` | `grandeurMetier` | `String(10)` | Yes | CONS |
| `grandeur_physique` | `grandeurPhysique` | `String(10)` | Yes | DD/DQ/EA/ERC/ERI/PMA/TF |
| `type_calendrier` | `typeCalendrier` | `String(5)` | Yes | D |
| `code_classe_temporelle` | `codeClasseTemporelle` | `String(10)` | Yes | HCE/HCH/HPE/HPH/P |
| `libelle_classe_temporelle` | `libelleClasseTemporelle` | `String(100)` | Yes | Libelle humain |
| `unite` | `unite` | `String(10)` | Yes | Wh/VArh/VA/s |
| `date_fin` | `dateFin` | `String(50)` | No | ISO8601 brut |
| `valeur` | `valeur` | `String(20)` | Yes | Entier brut |

**Index** : `(point_id, date_fin)`, `flux_file_id`, `flux_type`

### `enedis_flux_mesure_r50`

Granularite : **1 row par PDC** (point de courbe de charge).

| Colonne | Source XML | Type SQLAlchemy | Nullable | Commentaire |
|---------|-----------|----------------|----------|-------------|
| `id` | auto | `Integer, PK` | No | |
| `flux_file_id` | FK | `Integer, FK(enedis_flux_file.id, CASCADE)` | No | |
| `flux_type` | "R50" | `String(10)` | No | Denormalise pour requetes |
| `point_id` | `PRM/Id_PRM` | `String(14)` | No | PRM |
| `date_releve` | `Date_Releve` | `String(20)` | No | Date ISO du releve |
| `id_affaire` | `Id_Affaire` | `String(20)` | Yes | Code affaire |
| `horodatage` | `PDC/H` | `String(50)` | No | ISO8601+TZ brut |
| `valeur` | `PDC/V` | `String(20)` | Yes | Absent si pas de mesure |
| `indice_vraisemblance` | `PDC/IV` | `String(5)` | Yes | 0/1, absent si V absent |

**Index** : `(point_id, horodatage)`, `flux_file_id`, `flux_type`

### `enedis_flux_mesure_r151`

Granularite : **1 row par valeur** (index par classe temporelle OU puissance maximale). Le champ `type_donnee` distingue les 3 categories de donnees presentes dans un releve.

| Colonne | Source XML | Type SQLAlchemy | Nullable | Commentaire |
|---------|-----------|----------------|----------|-------------|
| `id` | auto | `Integer, PK` | No | |
| `flux_file_id` | FK | `Integer, FK(enedis_flux_file.id, CASCADE)` | No | |
| `flux_type` | "R151" | `String(10)` | No | Denormalise pour requetes |
| `point_id` | `PRM/Id_PRM` | `String(14)` | No | PRM |
| `date_releve` | `Date_Releve` | `String(20)` | No | Date ISO du releve |
| `id_calendrier_fournisseur` | `Id_Calendrier_Fournisseur` | `String(20)` | Yes | Code calendrier |
| `libelle_calendrier_fournisseur` | `Libelle_Calendrier_Fournisseur` | `String(100)` | Yes | |
| `id_calendrier_distributeur` | `Id_Calendrier_Distributeur` | `String(20)` | Yes | Code calendrier |
| `libelle_calendrier_distributeur` | `Libelle_Calendrier_Distributeur` | `String(150)` | Yes | |
| `id_affaire` | `Id_Affaire` | `String(20)` | Yes | Code affaire |
| `type_donnee` | derive de la structure | `String(10)` | No | `CT_DIST` / `CT` / `PMAX` |
| `id_classe_temporelle` | `Id_Classe_Temporelle` | `String(10)` | Yes | HCB/HCH/HPB/HPH/HC/HP, NULL pour PMAX |
| `libelle_classe_temporelle` | `Libelle_Classe_Temporelle` | `String(100)` | Yes | NULL pour PMAX |
| `rang_cadran` | `Rang_Cadran` | `String(5)` | Yes | NULL pour PMAX |
| `valeur` | `Valeur` | `String(20)` | Yes | Index cumule (Wh) ou puissance max (VA) |
| `indice_vraisemblance` | `Indice_Vraisemblance` | `String(5)` | Yes | 0-15 (spec R6X), NULL pour PMAX |

`type_donnee` values :
- `CT_DIST` : Classe_Temporelle_Distributeur (index grille distributeur)
- `CT` : Classe_Temporelle (index grille fournisseur)
- `PMAX` : Puissance_Maximale

**Index** : `(point_id, date_releve)`, `flux_file_id`, `flux_type`

---

## Impact sur `EnedisFluxFile`

`EnedisFluxFile` reste la table registre partagee. Adaptations :

| Point | Decision |
|-------|----------|
| `header_raw` JSON | Toujours alimente — fidelite complete de l'entete quel que soit le type |
| Colonnes R4x-specifiques (`frequence_publication`, `nature_courbe_demandee`, `identifiant_destinataire`) | Restent NULL pour R171/R50/R151 — pas de colonnes supplementaires queryables pour le moment |
| Rename `mesures` relationship | `mesures` -> `mesures_r4x`. Ajouter `mesures_r171`, `mesures_r50`, `mesures_r151` |
| Viabilite | Confirmee. `header_raw` JSON garantit la fidelite. Les 3 colonnes R4x nullable ne posent pas de probleme |

---

## Risques identifies

| Risque | Mitigation |
|--------|-----------|
| R171 pourrait avoir N mesures par serie (et pas seulement 1) | Le parser itere `mesuresDateesListe` sans limiter a 1. Le stockage est 1 row par mesure |
| R50 PDC sans V ni IV (creneaux vides) | Stocker quand meme (1 row par PDC, V et IV nullable). Permet de detecter les trous |
| R151 pourrait avoir N Donnees_Releve par PRM | Structure observee : 1, mais le parser doit iterer sans limiter |
| Encodage UTF-8 corrompu dans R151 (`Ã©` au lieu de `e`) | Stocker brut — c'est le contenu du fichier, pas une erreur de parsing |
| `type_donnee` dans R151 est un champ derive (pas present dans le XML) | Acceptable : il distingue des blocs XML structurellement differents au sein du meme releve. Alternative (3 sous-tables) serait du sur-engineering |

---

## Fichiers analyses

| Type | Fichier | Taille XML |
|------|---------|-----------|
| R171 | `ENEDIS_R171_C_00000099895595_GRDF_23X--130624--EE1_20260301024107.zip` + 9 autres | 189 Ko |
| R50 | `ERDF_R50_23X--130624--EE1_GRD-F121_3363068_00001_M_00001_00001_20230106190230.zip` + 4 autres | 41 Ko |
| R151 | `ERDF_R151_23X--130624--EE1_GRD-F121_3363155_00001_Q_00001_00001_20241219030652.zip` + 4 autres | 3 Ko |
