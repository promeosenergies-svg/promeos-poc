# Audit — Extraction OPERAT Valeurs Absolues (CVCi/USEi)

**Date** : 2026-05-03
**Auteur** : Claude Code (regulatory-expert + extraction parent Drive ADEME/Cerema)
**Branche** : `claude/operat-va-extraction`
**Livrable** : `backend/config/operat_valeurs_absolues.yaml` (schéma v0.5)
**Statut** : PARTIAL — chronologie + méthodologie validées source primaire ; tables CVCi/USEi par zone × altitude restent à OCR

---

## 1. Mission initiale

Extraire les tables CVCi/USEi exhaustives par sous-catégorie OPERAT depuis les arrêtés "Valeurs Absolues" français pour enrichir la Section 5 OPERAT du document `docs/product/patrimoine_parametrage_requis_v1.md`.

Hypothèse initiale erronée : "VA I → VA VI, dernier arrêté = VA VI du 06/09/2025". Réalité confirmée par extraction primaire : il n'existe **pas de série VA I-VI consolidée**, mais une chaîne d'arrêtés modifiant l'arrêté méthode du 10/04/2020. Le "VA VI" supposé du 06/09/2025 est en réalité l'**arrêté du 1er août 2025 publié au JO du 6 septembre 2025** (NOR ATDL2430864A). Le user avait raison sur l'arrêté du 1er août 2025, ma KB locale confondait date de signature et date de publication JO.

## 2. Sources consultées

### 2.1 Tentatives de WebFetch direct (tous échec)

| Domaine | URL type | Résultat |
|---------|----------|----------|
| legifrance.gouv.fr | `/jorf/id/...`, `/loda/id/...` | 🔴 HTTP 403 anti-bot |
| ecologie.gouv.fr | `/decret-tertiaire`, `/politiques-publiques/...` | 🔴 HTTP 404 |
| bulletin-officiel.developpement-durable.gouv.fr | `/recherche?q=...` | 🟡 page rendue, recherche JS non exécutée |
| operat.ademe.fr | `/public/accueil`, `/public/faq` | 🟡 SPA Vue/Angular sans HTML statique |
| ademe.fr | `/expertises/batiment/...` | 🔴 HTTP 403 |
| web.archive.org | `/web/2025/...` | 🔴 bloqué allowlist Claude Code |

**Conclusion** : aucune extraction primaire possible via WebFetch sur sources institutionnelles ce 2026-05-03.

### 2.2 Sources extraites du Google Drive utilisateur (succès)

Dossier Drive consulté : `1Kqns6VQT3zRu8fjc8kj_JDoBuPQrQZrQ` (36 PDFs catalogués).

| Document | Drive ID | Taille | Statut extraction | Apport |
|----------|----------|--------|-------------------|--------|
| Cerema DEET ModeEmploi | `1mSGZlOfX5G9re3ANkzvqK8a5HSlNJhA2` | 21 MB | ✅ texte 170 KB | 19 valeurs Cabs cas pratiques + chronologie arrêtés |
| Arrêté 01/08/2025 (JO 06/09/2025) | `1yfUCVQe_8qdw2sAbR_qtF1P-774Bw0Os` | 146 KB | ✅ intégral | NOR ATDL2430864A confirmé + texte intégral hors annexes |
| Documentation ADEME 09/2025 (objectifs/attestations) | `1V3ROcNkcA9j4K3X48BXEWQ8BFehm2iqu` | 1 MB | ✅ intégral | Formules Cabs/Crelat/CVC/USE officielles ADEME |
| Décret cadre 2019-771 (JO 25/07/2019) | `1sIUaNq4j7Ef13FOoSr3jQk0l1c51jVHf` | 188 KB | ✅ intégral | Articles R.131-38 à R.131-44 + sanctions |
| Décret BACS modifié 2023-259 (JO 08/04/2023) | `1ArnqM1P9CoQIYXVnBpxXGdvLeikCOyh4` | 152 KB | ✅ intégral | Hors scope OPERAT (utile autre pillar) |
| Loi APER 2023-175 (JO 11/03/2023) | `1M86fl6G9YXQml7vY6Vr58ZJ34Vkekuy2` | 507 KB | ⚠️ texte 255 KB sauvé | Hors scope OPERAT (utile autre pillar) |
| Texte JO 18/12/2025 économie/énergie | `1uGoz3-OgJwm-qnEzbU1gsp4jViUlObZu` | 322 KB | ⚠️ texte 112 KB sauvé | Hors scope OPERAT (à reclasser) |

Sources brutes archivées dans `docs/sources/regulatory/operat/` :
- `cerema_deet_2025_raw.txt` (170 KB — base d'extraction principale)
- `joe_20251218_0296_0054.txt` (112 KB — à reclasser)
- `joe_20230311_0060_0001.txt` (255 KB — Loi APER, à déplacer vers `docs/sources/regulatory/aper/`)

## 3. Findings — chronologie réelle des arrêtés OPERAT

| Date signature | Référence | NOR | Apport principal | Confidence |
|----------------|-----------|-----|------------------|------------|
| 23/07/2019 | Décret n° 2019-771 | LOGL1909871D | Texte cadre articles R.131-38 à R.131-44 CCH | 🟢 source primaire |
| 10/04/2020 | Arrêté méthode | LOGL2007109A | Structure annexes I-VII, méthodes Cabs/Crelat | 🟢 cité par tous arrêtés modificatifs |
| 13/04/2022 | Arrêté sous-catégories | (NOR à confirmer) | Extension catégories tertiaires | 🟡 Cerema ligne 2743 |
| 28/11/2023 | Arrêté Cabs valeur défaut | (NOR à confirmer) | **Article 8-IV** : tables Cabs sous-cat "valeur par défaut" (ex enseignement primaire = 79 kWh/m²/an) | 🟡 Cerema ligne 1025 citation explicite |
| 20/02/2024 | Arrêté modificatif | (NOR à confirmer) | Surface piscine + délai déclaration Période 2010-2019 → 30/09/2027 | 🟡 Cerema lignes 715, 1565 |
| 05/07/2024 | Arrêté DJU | (NOR à confirmer) | Formules ajustement DJU intégrées plateforme OPERAT | 🟡 Cerema ligne 783 |
| **01/08/2025** | **Arrêté modificatif** | **ATDL2430864A** | **REMPLACE annexe II (Cabs/CVCi/USEi) + dernier tableau annexe III, ajoute GNL, supprime modèle attestation VII-1, transitoire jusqu'au 01/07/2026** | 🟢 source primaire JO |

Le YAML `backend/config/operat_valeurs_absolues.yaml` § `arretes_chronology` détaille chaque arrêté.

## 4. Findings — méthodologie ADEME confirmée 🟢

Source : Documentation OPERAT ADEME mise à jour Septembre 2025.

```
Cabs 2030 = CVC(n) + USE(n)
CVC(n) = Σ(CVCi × Si) / ΣSi
USE(n) = Σ(USEi × Si) / ΣSi
Si = Surface déclarée × (Nb jour n / Nb jour i)

Crelat 2030 (primo assujetti) = Cref × (Cabs2030(n) / Cabs2030(ref)) × (1 - 0.4)
Crelat 2030 (chgt occupant)   = Cref_liée × (Cabs2030(n) / Cabs2030_liée(ref)) × (1 - 0.4)
```

L'assujetti choisit la méthode la plus favorable (Cabs OU Crelat), par EFA. Suffit d'atteindre l'un des deux objectifs pour conformité.

## 5. Findings — 19 valeurs Cabs 2030 par sous-catégorie 🟡

Confidence 🟡 (cas pratiques pédagogiques officiels Cerema, pas reproduction de tables normatives).

| Code YAML | Cabs 2030 (kWh/m²/an) | Cerema |
|-----------|----------------------:|--------|
| `bureaux_standards_mairie_passoire` | 116 | L727 |
| `enseignement_primaire_valeur_defaut` ★ | **79** (art. 8-IV arrêté 28/11/2023) | L1025 |
| `enseignement_primaire_detaille_ecole` | 102 | L1163 |
| `periscolaire_mixte` | 111 | L1223 |
| `periscolaire_scenario_5h_jour` | 161 | L1267 |
| `periscolaire_scenario_4j_sem` | 142 | L1269 |
| `sports_valeur_defaut` ★ | **57** | L579+ |
| `sports_gymnase_detaille` | 68 | L1425 |
| `sports_centre_aquatique_detaille` | **423** | L1619 |
| `culture_mjc` | 92 | L1873 |
| `culture_salle_polyvalente` | 94 | L1873 |
| `atelier_technique_valeur_defaut` | 74 | L1805 |
| `atelier_technique_zone_atelier_modulee` | 56 | L2141 |
| `atelier_technique_magasin_stockage_modulee` | 29 | L2143 |
| `atelier_technique_bureau_modulee` | 74 | L2153 |
| `bureaux_multi_occupation_etalons` | 45 | L2073 |
| `bureaux_multi_occupation_modulee` | 39 (gain 15%) | L2181 |
| `administration_prefecture` | 120 | L2575 |
| `administration_conseil_departemental` | 123 | L2575 |

## 6. Gaps subsistants 🔴

### 6.1 Tables CVCi/USEi par sous-catégorie × zone climatique × altitude

**État** : 0% extrait. Les annexes officielles sont publiées sous deux formes complémentaires :
- **Tableau 3-1 du Cerema** (PDF p.77) : tables raster non extractibles via Drive natural-language. OCR PDF natif requis.
- **Annexes I et II de l'arrêté du 01/08/2025** : NON publiées dans le PDF JO. Article 6 renvoie explicitement à `bulletin-officiel.developpement-durable.gouv.fr/recherche` — bloqué WebFetch (SPA JS).

### 6.2 Mapping département des 8 zones climatiques OPERAT

**État** : descriptions textuelles dans le YAML (H1a "Nord et Est continental", etc.) mais listes de départements vides. À récupérer dans annexe arrêté méthode 10/04/2020.

### 6.3 NOR exacts de 4 arrêtés intermédiaires

VA II 13/04/2022, arrêté 28/11/2023, arrêté 20/02/2024, arrêté 05/07/2024 : NOR non extraits (Cerema ne les cite pas systématiquement, JO non encore récupérés).

### 6.4 FAQ OPERAT — question 5

URL `https://operat.ademe.fr/public/faq#question_5` non extractible via WebFetch (SPA). Cerema cite plusieurs questions FAQ (codes thématiques A1/A2/AN4/O4/E7/DC4/A11/A19/A20/A23 + IDs numériques 3, 13, 16, 21, 57, 65, 66, 91, 96, 121, 127, 169) mais **pas la question 5 spécifiquement**. Référencé en P1 follow-up.

## 7. Roadmap follow-up

| Priorité | Action | Effort estimé | Méthode recommandée |
|----------|--------|---------------|---------------------|
| **P0** | OCR Tableau 3-1 Cerema p.77 | 1-2h | Télécharger PDF Cerema 21 MB depuis Drive → `Read PDF natif pages=77-80` (préserve raster via OCR Claude multimodal) |
| **P0** | Récupérer annexes I+II arrêté 01/08/2025 | 1h | Manuel : naviguer bulletin-officiel.developpement-durable.gouv.fr et télécharger PDF annexes (NOR ATDL2430864A) |
| **P1** | Lecture Guide utilisateur OPERAT V1.1 (14 MB Drive) | 2h | Tenter MCP Drive read_file_content (risque explosion contexte) ou téléchargement local + Read PDF |
| **P1** | Mapping département zones climatiques | 30 min | Annexe arrêté 10/04/2020 (à OCR) |
| **P1** | Question 5 FAQ OPERAT | 5 min | User : paste manuel du contenu depuis navigateur |
| **P2** | NOR exacts 4 arrêtés intermédiaires | 1h | Recherche manuelle Légifrance avec dates exactes |
| **P2** | Wiring `tertiaire_operat.py` méthode Cabs | 4-6h | Sprint séparé — actuellement règles évaluent scope/échéances/trajectoire mais pas Cabs |

## 8. Évolution confidence avant/après

| Indicateur | Avant session 03/05 | Après session 03/05 |
|------------|---------------------|---------------------|
| Identification arrêté cible (NOR + date) | 🔴 hypothèse erronée "VA VI 06/09/2025" | 🟢 ATDL2430864A signé 01/08/2025 publié JO 06/09/2025 |
| Chronologie arrêtés OPERAT | 🔴 6 arrêtés VA hypothétiques sans NOR | 🟡 7 arrêtés réels identifiés (1 source primaire 🟢, 5 Cerema 🟡, 1 décret cadre 🟢) |
| Méthodologie ADEME (formules) | 🔴 hypothèses littérales | 🟢 source primaire ADEME 09/2025 |
| Sanctions | 🟡 valeur 7500€ sans source | 🟢 décret 2019-771 art. R.131-44 source primaire JO |
| Valeurs Cabs sous-catégories | 🔴 0 valeur | 🟡 19 valeurs cas pratiques Cerema |
| Tables CVCi/USEi par zone × altitude | 🔴 0% | 🔴 0% (gap principal subsistant) |
| Zones climatiques (descriptions) | 🔴 vide | 🟡 descriptions textuelles, départements vides |
| Échéances clés | 🟡 partiellement connues | 🟢 6 jalons confirmés source primaire |

## 9. Décisions à arbitrer (questions ouvertes pour Amine)

1. **Acceptation du YAML v0.5** dans `backend/config/operat_valeurs_absolues.yaml` malgré tables CVCi/USEi vides ? Le YAML est exploitable pour : référencer chronologie + méthodologie + 19 valeurs Cabs + sanctions + échéances. Les tables CVCi/USEi vides sont signalées par confidence 🔴 explicite.
2. **Wiring backend** : faut-il déjà brancher `tertiaire_operat.py` sur ce YAML pour la partie déjà chiffrée (échéances, sanctions, méthode Cabs simplifiée), ou attendre tables CVCi/USEi complètes ?
3. **Téléchargement local du PDF Cerema** (21 MB) dans `docs/sources/regulatory/operat/cerema_deet_2025.pdf` pour permettre OCR p.77 par Read PDF natif ?
4. **Reclasser** `joe_20230311_0060_0001.txt` (Loi APER) vers `docs/sources/regulatory/aper/` et `joe_20251218_0296_0054.txt` (texte économie 18/12/2025) après identification précise ?

## 10. Fichiers livrés ce sprint

| Fichier | Type | Description |
|---------|------|-------------|
| `backend/config/operat_valeurs_absolues.yaml` | nouveau | Schéma v0.5 — YAML structuré (chronologie + méthodo + 19 Cabs + sanctions + zones climatiques squelette) |
| `docs/audits/AUDIT_OPERAT_VA_EXTRACTION_2026_05_03.md` | nouveau | Le présent audit |
| `docs/sources/regulatory/operat/cerema_deet_2025_raw.txt` | nouveau | Extraction natural-language du Cerema (170 KB, source 80% des findings) |
| `docs/sources/regulatory/operat/joe_20251218_0296_0054.txt` | nouveau | Texte JO 18/12/2025 (à reclasser) |
| `docs/sources/regulatory/operat/joe_20230311_0060_0001.txt` | nouveau | Texte Loi APER (à déplacer vers `aper/` follow-up) |
| `backend/regops/config/legal_refs.py` | edit | +1 entrée pour arrêté 01/08/2025 NOR ATDL2430864A |

**Pas de modification de** `backend/regops/rules/tertiaire_operat.py` (règles métier inchangées — wiring séparé en follow-up P2).
