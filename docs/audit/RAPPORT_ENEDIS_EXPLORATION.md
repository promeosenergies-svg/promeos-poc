# Rapport d'exploration -- Dossier Enedis PROMEOS

> **Date** : 2026-03-28
> **Mode** : Lecture seule -- aucun fichier modifié
> **Périmètre** : `docs/`, `backend/`, `frontend/`, `.env*`, tests

---

## 1. Inventaire des fichiers

### 1a. Spécifications fonctionnelles (`docs/specs/`)

| # | Chemin | Type | Taille | Contenu |
|---|--------|------|--------|---------|
| 1 | `docs/specs/feature-enedis-sge-raw-ingestion.md` | MD | 11 KB | Spec originale ARCHIVÉE -- scindée en 3 sous-features |
| 2 | `docs/specs/feature-enedis-sge-1-decrypt.md` | MD | 11 KB | SF1 : Décryptage AES + classification flux |
| 3 | `docs/specs/feature-enedis-sge-2-ingestion-cdc.md` | MD | 15 KB | SF2 : Ingestion CDC (R4H/R4M/R4Q, R171) |
| 4 | `docs/specs/feature-enedis-sge-3-ingestion-index.md` | MD | 11 KB | SF3 : Ingestion index C5 (R50, R151) |

### 1b. Base documentaire (`docs/base_documentaire/enedis/`) -- ~21 MB

#### PDFs (13 fichiers, ~16.8 MB)

| # | Fichier | Taille | Sujet |
|---|---------|--------|-------|
| 5 | `Enedis-MOP-CF_094E.pdf` | 2.3 MB | Mode opératoire contractuel |
| 6 | `Enedis-NMO-CPT_002E.pdf` | 1.7 MB | Nomenclature comptage |
| 7 | `Enedis-R17.pdf` | 1.6 MB | Flux R17 (CDC per-PRM) |
| 8 | `Enedis-R4X.pdf` | 706 KB | Flux R4X (CDC agrégé) |
| 9 | `Enedis-R6X.pdf` | 1.5 MB | Flux R6X (nouveau format JSON) |
| 10 | `Enedis SGE GUI 0300 Flux C15_v5.1.3.pdf` | 1.8 MB | Guide flux C15 |
| 11 | `Enedis.SGE.GUI.0124.Flux F12_v1.14.2.pdf` | 2.3 MB | Guide flux F12 (facturation) |
| 12 | `Enedis.SGE.GUI.0129.Flux C12_v1.12.4.pdf` | 1.4 MB | Guide flux C12 |
| 13 | `Enedis.SGE.GUI.0131.Flux R17_v1.11.4.pdf` | 911 KB | Guide flux R17 |
| 14 | `Enedis.SGE.GUI.0298.Flux F15_v4.1.3.pdf` | 1.7 MB | Guide flux F15 |
| 15 | `Enedis.SGE.GUI.0503.Flux.R6X_v1.5.2.pdf` | 1.5 MB | Guide flux R6X |
| 16 | `Enedis.SGE.GUI.0504.Flux_C68_v1.2.0/...pdf` | ~1 MB | Guide flux C68 (données techniques PRM) |
| 17 | `Enedis_Flux F15_Releve residuel TURPE7_...pdf` | 443 KB | Principes facturation F15 TURPE 7 |

#### XSD -- Schémas XML F12/C12/R17/F15/C15 (10 fichiers, ~168 KB)

| # | Fichier | Lignes | Sujet |
|---|---------|--------|-------|
| 18 | `Enedis.SGE.XSD.0125.F12_Donnees_Generales_1.10.4.xsd` | 1032 | F12 : en-tête facture, montants HT/TTC/TVA, CSPE, données bancaires |
| 19 | `Enedis.SGE.XSD.0126.F12_Donnees_Detail_1.10.4.xsd` | 648 | F12 : détail par PRM (segment C2/C3/C4), tarif souscrit, postes horosaisonniers, prestations |
| 20 | `Enedis.SGE.XSD.0127.F12_Donnees_Detail_Demat_1.20.1.xsd` | 1228 | F12 dématérialisé : réforme e-invoicing LDF24, vendeur/acheteur, codes TVA |
| 21 | `Enedis.SGE.XSD.0127.F12_Donnees_Recap_1.10.4.xsd` | 189 | F12 : récapitulatif par type tarifaire |
| 22 | `Enedis.SGE.XSD.0128.F12_Donnees_Taxes_1.10.4.xsd` | 180 | F12 : détail taxes (CSPE, CTA, etc.) |
| 23 | `ENEDIS.SGE.XSD.0130.C12_v1.12.1.xsd` | ~800 | C12 : données contractuelles/techniques |
| 24 | `ENEDIS.SGE.XSD.0132.R17_v1.9.1.xsd` | ~600 | R17 : CDC par PRM (XML) |
| 25 | `GRD.XSD.0299.Flux_F15_Donnees_Detail_v4.0.4.xsd` | ~600 | F15 : détail facturation réseau |
| 26 | `GRD.XSD.0301.Flux_C15_v5.2.0.xsd` | ~1000 | C15 : données contractuelles C5 |
| 27 | `GRD.XSD.0302.Flux_F15_Donnees_Generales_v4.0.4.xsd` | ~800 | F15 : en-tête + montants |

#### JSON -- Schémas R6X (10 fichiers, ~36 KB)

| # | Fichier | Sujet |
|---|---------|-------|
| 28 | `R6X-M023/Enedis.SGE.JSON.0510.Flux.R63_v1.2.0.json` | R63 : CDC time-series par PRM (M023) |
| 29 | `R6X-M023/Enedis.SGE.JSON.0511.Flux.R64_v1.2.1.json` | R64 : index relevés par PRM (M023) |
| 30 | `R6X-M023/Enedis.SGE.JSON.0512.Flux.R65_v1.2.0.json` | R65 : CDC par PRM (M023) |
| 31 | `R6X-M023/Enedis.SGE.JSON.0513.Flux.R66_v1.2.0.json` | R66 : CDC par PRM (M023) |
| 32 | `R6X-M023/Enedis.SGE.JSON.0515.Flux.R67_v1.3.0.json` | R67 : quantités par PRM (M023) |
| 33 | `R6X-REC/Enedis.SGE.JSON.0532.Flux.R63Xv1.1.0.json` | R63X : variante REC avec échéances |
| 34 | `R6X-REC/Enedis.SGE.JSON.0533.Flux.R64Xv1.1.0.json` | R64X : variante REC |
| 35 | `R6X-REC/Enedis.SGE.JSON.0534.Flux.R66Xv1.1.0.json` | R66X : variante REC |
| 36 | `Flux_C68_v1.2.0/...C68_v1.2.0.json` | C68 : données techniques/contractuelles complètes par PRM (1170 lignes) |

#### Données de test (4 fichiers Excel, ~49 KB)

| # | Fichier | Sujet |
|---|---------|-------|
| 37 | `JDD_C2C4_ENDESA_25042025.xlsx` | Jeu de données test C2/C4 |
| 38 | `JDD_C5_ENDESA_25042025.xlsx` | Jeu de données test C5 |
| 39 | `JDD_Endesa_C2C4.xlsx` | Jeu de données Endesa C2/C4 |
| 40 | `JDD_Endesa_C5.xlsx` | Jeu de données Endesa C5 |

#### Autre

| # | Fichier | Sujet |
|---|---------|-------|
| 41 | `2025-11-14_Présentation_Changement_API.pptx` | 1.7 MB -- Présentation migration API Enedis |
| 42 | `Enedis.SGE.GUI.0256.Detail des publications par tarif-compteur_v1.3.0.xls` | Détail publications par tarif/compteur |

---

## 2. Contenu détaillé par fichier clé

### SF1 -- Décryptage (`feature-enedis-sge-1-decrypt.md`)
- **Sujet** : Décryptage AES des fichiers flux SGE + classification par type
- **Données exploitables** :
  - Les fichiers `flux_enedis/` sont chiffrés AES (pas ZIP)
  - Discovery : AES-CBC (IV=16 premiers bytes), puis ECB, CBC IV-zero, CBC IV-from-key
  - Post-décryptage : résultat = XML direct OU ZIP contenant XML
  - Classification par pattern filename : `_R4H_CDC_`, `_R4M_CDC_`, `_R4Q_CDC_`, `_R171_`, `_R50_`, `_R151_`
  - Types ignorés : R172, X14, HDM
- **Env vars** : `ENEDIS_DECRYPT_KEY` (requis), `ENEDIS_ARCHIVE_DIR` (optionnel)
- **Module cible** : `backend/enedis/decrypt.py`, `backend/enedis/enums.py`
- **FluxType enum** : R4H, R4M, R4Q, R171, R50, R151, R172, X14, HDM, UNKNOWN

### SF2 -- Ingestion CDC (`feature-enedis-sge-2-ingestion-cdc.md`)
- **Sujet** : Parsing XML et stockage des Courbes De Charge
- **Données exploitables** :
  - R4H/R4M/R4Q = flux agrégés (pas de PRM individuel), R171 = per-PRM
  - 2 tables staging : `enedis_flux_file` (registre SHA256) + `enedis_flux_mesure` (mesures brutes)
  - R171 : unicité `(point_id, horodatage, flux_type)` ; R4 : sentinel `"AGGREGATE"` pour point_id
  - Parsers : `R4Parser`, `R171Parser` via `xml.etree.ElementTree`
  - Pipeline : classify → hash check → decrypt → validate XML → parse → batch insert
  - Double idempotence : hash fichier + contrainte unicité mesures

### SF3 -- Ingestion Index C5 (`feature-enedis-sge-3-ingestion-index.md`)
- **Sujet** : Parsing index R50/R151 pour segment résidentiel/petit tertiaire
- **Données exploitables** :
  - R50 = index mensuel par PRM, R151 = relevé trimestriel par PRM
  - Préfixe historique `ERDF_` dans les noms de fichiers
  - Option A (réutiliser `EnedisFluxMesure`) vs Option B (table dédiée `EnedisFluxIndex`)
  - Parsers : `R50Parser`, `R151Parser`
  - Fonction batch : `ingest_directory()`

### XSD F12 (Facturation réseau)
- **Valeur PROMEOS** : Schémas complets pour parser les factures Enedis acheminement
- Donnees_Generales : en-tête facture, montants HT/TTC/TVA, CSPE, données bancaires
- Donnees_Detail : par PRM (segment C2/C3/C4), tarifs souscrit (BTSUPLU, HTA5, BTINFCUST...), postes horosaisonniers (Pointe, HPH, HCH, HPE, HCE...)
- Donnees_Detail_Demat : réforme e-invoicing LDF24 (2023-2025), vendeur/acheteur SIRET
- Codes récapitulatifs : CGEST, CCOMP, CAC, CAS, CSF, CSV, CMDPS, CREAC, CSPE, PREST, FRAIS

### JSON R6X (Nouveau format CDC)
- **Valeur PROMEOS** : Schémas du futur format JSON remplaçant XML pour les flux R6X
- R63 : CDC time-series (v/d/p/n/tc/iv/ec par point)
- R64 : index relevés avec contexte (étapeMetier, typeReleve, motifReleve)
- R65/R66 : CDC simplifiées (v/d par point)
- R67 : quantités avec grille tarifaire (codeGrille, calendrier, classesTemporelles)
- Variantes REC : ajoutent bloc `echeances` (type, horodate, fréquence)

### JSON C68 (Données techniques PRM)
- **Valeur PROMEOS** : Schéma exhaustif des données techniques et contractuelles par PRM
- donneesGenerales : adresse, typage (bornePoste, sensible, hébergeur/décomptant)
- situationAlimentation : domaineTension, puissanceLimite, raccordement
- situationComptage : matricule, modèle, programmationHoraire (5 postes), déploiement Linky, TIC
- situationsContractuelles : client final (SIREN/SIRET/NAF), structureTarifaire, puissanceSouscrite
- installationsProduction : filière, technologie

---

## 3. Code source Enedis existant

### `backend/connectors/enedis_dataconnect.py` -- STUB
- **État** : Squelette vide
- **Ce qu'il fait** : Classe `EnedisDataConnectConnector` héritant de `Connector`. `test_connection()` vérifie la présence de `ENEDIS_CLIENT_ID`. `sync()` retourne `[]`.
- **Ce qu'il manque** : OAuth2 authorization code flow, token exchange/refresh, appels API DataConnect v5, parsing réponses, mapping vers `Compteur`/`Consommation`, gestion erreurs, pagination
- **Dépendances** : `os`, `connectors.base.Connector`

### `backend/connectors/enedis_opendata.py` -- STUB
- **État** : Squelette vide
- **Ce qu'il fait** : Classe `EnedisOpenDataConnector`. `test_connection()` retourne toujours "ok". `sync()` retourne `[]`.
- **Ce qu'il manque** : Appels HTTP vers `https://data.enedis.fr/`, requêtes datasets, parsing données
- **Dépendances** : `connectors.base.Connector` uniquement

### `backend/connectors/registry.py` -- FONCTIONNEL
- Les deux connecteurs Enedis sont importés et enregistrés dans le registre
- `list_connectors()`, `get_connector("enedis_dataconnect")`, `run_sync()` fonctionnent

### `backend/connectors/base.py` -- FONCTIONNEL
- ABC `Connector` avec `name`, `description`, `requires_auth`, `env_vars`, `test_connection()`, `sync()`

### `backend/routes/connectors_route.py` -- FONCTIONNEL
- Routes `/api/connectors/{name}/test` et `/sync` opérationnelles (tapent dans les stubs)

### `backend/models/compteur.py` -- FONCTIONNEL
- Modèle `Compteur` avec `meter_id` (PRM 14 chars), `energy_vector`, `delivery_point_id`, `data_source`
- Prêt à recevoir les données Enedis via le connecteur

### Pipeline SGE (SF1-SF3) -- NON IMPLÉMENTÉ
- **Aucun** des modules cible n'existe :
  - `backend/enedis/decrypt.py` -- à créer
  - `backend/enedis/models.py` -- à créer (`EnedisFluxFile`, `EnedisFluxMesure`)
  - `backend/enedis/parsers/r4.py` -- à créer
  - `backend/enedis/parsers/r171.py` -- à créer
  - `backend/enedis/parsers/r50.py` -- à créer
  - `backend/enedis/parsers/r151.py` -- à créer
  - `backend/enedis/pipeline.py` -- à créer (`ingest_file()`, `ingest_directory()`)

---

## 4. Couverture documentaire

| # | Sujet | Couvert ? | Fichier(s) source | Lacune identifiée |
|---|-------|-----------|--------------------|--------------------|
| 1 | DataConnect OAuth2 flow | ⚠️ | Stub connector, `.env.example` | Aucune doc OAuth détaillée dans le repo ; pas d'implémentation |
| 2 | Scopes & permissions DataConnect | ❌ | -- | Aucune documentation des scopes API |
| 3 | Format CDC 30min (C5) via DataConnect | ❌ | -- | Pas de spec DataConnect API response |
| 4 | Format CDC per-PRM (R171) via SGE | ✅ | `feature-enedis-sge-2-ingestion-cdc.md`, `Enedis-R17.pdf`, XSD R17 | Spec complète, pas encore implémenté |
| 5 | Format CDC agrégé (R4H/R4M/R4Q) via SGE | ✅ | `feature-enedis-sge-2-ingestion-cdc.md`, `Enedis-R4X.pdf` | Spec complète, pas encore implémenté |
| 6 | Format Index C5 (R50, R151) | ✅ | `feature-enedis-sge-3-ingestion-index.md` | Spec complète, pas encore implémenté |
| 7 | Décryptage AES fichiers SGE | ✅ | `feature-enedis-sge-1-decrypt.md` | Spec complète avec discovery modes AES |
| 8 | Consentement client (mandat) | ❌ | -- | Aucune doc sur le processus de mandat/consentement DataConnect |
| 9 | Gestion lifecycle consentement | ❌ | -- | Pas de workflow révocation/renouvellement |
| 10 | PDL/PRM mapping | ✅ | `compteur.py`, `DrawerAddCompteur.jsx`, specs CDC | Modèle existant, champ 14 chars |
| 11 | Profils tarifaires (HP/HC/Base/Tempo/EJP) | ✅ | XSD F12 (postes horosaisonniers), `tou_schedule.py`, `turpe_calendar.py` | Bien couvert via TURPE 7 |
| 12 | Puissance souscrite | ✅ | XSD F12 Detail, C68 JSON schema | Champs PS_Poste_Horosaisonnier dans F12, puissanceSouscrite dans C68 |
| 13 | Données techniques (FTA, segment C1-C5) | ✅ | C68 JSON schema (1170 lignes), XSD C12, C15 | Schéma exhaustif : compteur, disjoncteur, pertes, TIC, Linky |
| 14 | Facturation réseau (F12, F15) | ✅ | 5 XSD F12, 3 XSD/PDF F15 | Schémas complets facturation acheminement |
| 15 | Flux R6X (nouveau format JSON) | ✅ | 8 JSON schemas (M023 + REC) + PDF guide | R63-R67 + variantes REC |
| 16 | GRDF ADICT (gaz) | ❌ | -- | Aucune documentation gaz/GRDF |
| 17 | Erreurs API / codes retour | ❌ | -- | Pas de catalogue d'erreurs DataConnect/SGE |
| 18 | Rate limits / quotas | ❌ | -- | Aucune info sur les limites API |
| 19 | Sandbox / environnement test | ⚠️ | JDD Excel (4 fichiers) | Jeux de données test présents, mais pas de doc sandbox Enedis |
| 20 | Exemples de réponses JSON/XML | ⚠️ | XSD + JSON schemas | Schémas présents mais pas d'exemples concrets de réponses |
| 21 | Migration API (nouveau format) | ✅ | `2025-11-14_Présentation_Changement_API.pptx` | Présentation transition |
| 22 | Flux C68 (données techniques PRM) | ✅ | JSON schema C68 1170 lignes | Exhaustif |

---

## 5. Références croisées dans le code

| Fichier code | Référence Enedis | Contexte |
|-------------|------------------|----------|
| `.env.example` | `ENEDIS_CLIENT_ID`, `ENEDIS_CLIENT_SECRET` | Config OAuth DataConnect |
| `backend/connectors/enedis_dataconnect.py` | Classe connector stub | OAuth DataConnect |
| `backend/connectors/enedis_opendata.py` | Classe connector stub | Open Data publique |
| `backend/connectors/registry.py` | Import + register les 2 connecteurs | Registre auto-discovery |
| `backend/models/compteur.py` | `meter_id` (PRM 14 chars) | Modèle compteur |
| `backend/models/enums.py` | `TurpeSegment`, `HcReprogPhase/Status` | Nomenclature Enedis, TURPE 7 |
| `backend/models/patrimoine.py` | `hc_reprog_phase` sur DeliveryPoint | Chantier reprog HC Enedis |
| `backend/models/market_models.py` | `DataResolution.PT30M` commentaire Enedis C5 | Résolution données |
| `backend/models/tou_schedule.py` | `source="enedis_sge"` | Source horaires tarifaires |
| `backend/services/billing_engine/catalog.py` | Grilles TURPE 7 Enedis | Barèmes facturation |
| `backend/services/billing_engine/turpe_calendar.py` | Postes horosaisonniers Enedis | Calendrier HP/HC |
| `backend/services/import_mapping.py` | `delivery_code` = PRM/PDL/PCE | Import CSV/Excel |
| `backend/routes/compteurs.py` | Références PDL/PRM | Routes API compteurs |
| `frontend/src/pages/ConnectorsPage.jsx` | Labels "Enedis DataConnect", "Open Data Enedis" | UI connecteurs |
| `frontend/src/components/DrawerAddCompteur.jsx` | Champs PRM (élec) / PCE (gaz) | Formulaire ajout compteur |
| `frontend/src/components/SiteCreationWizard.jsx` | Champs PRM/PDL | Wizard création site |
| `frontend/src/ui/glossary.js` | Définitions Enedis/DataConnect/PRM/PDL | Glossaire UI |
| `frontend/src/ui/evidence.fixtures.js` | Données evidence Enedis | Fixtures démo |
| `backend/tests/test_connectors.py` | Assert `enedis_dataconnect` in registry | Test registre |
| `backend/tests/test_ems_timeseries.py` | `test_enedis_mixed_frequencies` | Test fréquences mixtes |

---

## 6. Synthèse & recommandations

### Forces

1. **Documentation SGE exhaustive** : 42 fichiers totalisant ~21 MB couvrant les flux R4X, R17, R6X, F12, F15, C12, C15, C68 avec XSD, JSON schemas et guides PDF officiels
2. **Spécifications fonctionnelles complètes** : 3 sous-features (SF1-SF3) entièrement spécifiées avec architecture, modèles de données, parsers, pipeline, et matrices de tests
3. **Infrastructure prête** : Framework connector fonctionnel (base, registry, routes), modèle `Compteur` avec champ PRM 14 chars, UI avec formulaires PRM/PCE, pages connecteurs
4. **Schémas R6X JSON** : Couverture du nouveau format post-migration API (R63-R67 en M023 et REC)
5. **Données de test** : 4 fichiers Excel JDD (C2/C4 et C5) pour validation

### Lacunes critiques

1. **DataConnect OAuth2** : Aucune documentation du flow OAuth dans le repo, aucune implémentation (stub vide), pas de gestion de tokens
2. **Consentement / Mandat** : Aucune documentation ni workflow pour le processus de consentement client (obligatoire pour DataConnect)
3. **GRDF / Gaz** : Zéro documentation ADICT/GRDF malgré les champs PCE dans l'UI
4. **Pipeline SGE non implémenté** : Les 3 sous-features sont spécifiées mais aucun module `backend/enedis/` n'existe
5. **Erreurs API et Rate limits** : Pas de catalogue d'erreurs ni de documentation quotas
6. **Pas de `.env` vars** : `ENEDIS_CLIENT_ID`/`SECRET` référencés dans le stub mais absents de `.env.example`

### Prochaines étapes

1. **Implémenter SF1 (Décryptage AES)** -- Fondation de tout le pipeline SGE ; spec prête, crypto lib disponible
2. **Implémenter SF2+SF3 (Ingestion CDC + Index)** -- Parsers XML, tables staging, pipeline `ingest_file()`/`ingest_directory()`
3. **Documenter et implémenter DataConnect OAuth2** -- Flow authorization code, token storage/refresh, appels API v5, mapping vers modèles existants
4. **Documenter le processus de consentement** -- Mandat client, lifecycle (création/révocation/renouvellement), conformité RGPD
5. **Ajouter les vars env** dans `.env.example` : `ENEDIS_CLIENT_ID`, `ENEDIS_CLIENT_SECRET`, `ENEDIS_DECRYPT_KEY`, `ENEDIS_ARCHIVE_DIR`
