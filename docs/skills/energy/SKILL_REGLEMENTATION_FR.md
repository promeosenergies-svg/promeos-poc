---
name: promeos-reglementation-france
description: >
  Expert réglementation énergie France B2B 2024-2026.
  Décret Tertiaire, BACS, APER, Audit SMÉ, post-ARENH,
  fiscalité élec/gaz, délibérations CRE.
version: 2.0.0
tags: [regulatory, france, tertiaire, bacs, aper, cre, turpe]
---

# Réglementation Énergie France -- Expert PROMEOS

## 1. Décret Tertiaire (Décret n°2019-771)

### Jalons officiels
| Jalon | Objectif | Statut |
|-------|----------|--------|
| 2030  | -40% vs année référence | OFFICIEL |
| 2040  | -50% vs année référence | OFFICIEL |
| 2050  | -60% vs année référence | OFFICIEL |

Il n'existe pas de jalon intermédiaire 2026. Les 3 jalons ci-dessus sont les seuls définis par le décret.

### Règles d'applicabilité
- Seuil surface : >= 1 000 m² en France métropolitaine
- Périmètre : bâtiments à usage tertiaire (bureaux, commerce, enseignement,
  santé, hôtellerie, logistique, etc.)
- Année référence : choisie par le déclarant sur 2010-2020 (année la plus consommatrice recommandée)
- Plateforme OPERAT : déclaration obligatoire annuelle avant le 30 septembre

### Calcul conformité DT
- Trajectoire en énergie finale (kWhEF/m²/an)
- Correction DJU possible (méthode COSTIC préférée)
- Surface SHON RT ou surface chauffée selon le cas
- Pénalité personnes morales : **7 500 EUR/bâtiment**
- Pénalité personnes physiques : **1 500 EUR/bâtiment**
- Sanction complémentaire : publication "name and shame" sur OPERAT
- Pénalités renouvelables chaque année de non-conformité

### Source unique dans le code
-> `regops/scoring.py` -> `RegAssessment.compliance_score`
-> Poids DT : 45% (sans audit) / 39% (avec audit SMÉ)

---

## 2. BACS (Building Automation & Control Systems)

### Seuils d'obligation (Décret n°2025-1343)
| Puissance CVC | Échéance |
|--------------|----------|
| > 290 kW     | 01/01/2025 (effectif) |
| > 70 kW      | **01/01/2030** (report décret 27/12/2025) |

### Ce que BACS couvre
- Régulation automatique CVC (chauffage, ventilation, climatisation)
- Monitoring énergétique en temps réel par usage
- Rapport énergétique annuel automatisé
- **Exemption si TRI > 10 ans** documentée et opposable (après déduction aides/CEE)

### Poids scoring : 30% (sans audit) / 28% (avec audit SMÉ)

---

## 3. APER (Loi Accélération Énergies Renouvelables -- Loi n°2023-175)

### Obligations parking & toiture
| Type | Seuil | Obligation |
|------|-------|-----------|
| Parking extérieur | >= 1 500 m² | Ombrières PV sur >= 50% surface |
| Toiture/terrasse neuf | >= 500 m² | PV ou végétalisation >= 30% (2025) |

### Progression obligations toiture
| Date | Taux min toiture |
|------|-----------------|
| Actuel (2025) | 30% |
| 01/07/2026 | **40%** |
| 01/07/2027 | **50%** |
| 01/01/2028 | Obligation étendue aux bâtiments existants >= 500 m² |

### Poids scoring : 25% (sans audit) / 17% (avec audit SMÉ)

---

## 4. Audit Énergétique / SMÉ (Loi n°2025-391 du 30 avril 2025 -- loi DDADUE)

Transpose la Directive UE 2023/1791 sur l'efficacité énergétique.
Publiée au JO le 02/05/2025.

### Seuils de déclenchement (niveau Organisation = personne morale)
| Consommation annuelle (moy. 3 ans) | Obligation | Deadline |
|-------------------------------------|-----------|----------|
| > 2.75 GWh énergie finale | Audit énergétique tous les 4 ans (>= 80% facture) | **11/10/2026** |
| > 23.6 GWh énergie finale | ISO 50001 SMÉ obligatoire | **11/10/2027** |

-> Évaluation au niveau Organisation, PAS au niveau site individuel
-> Sanctions : 1 500 EUR/an (audit) / 3 000 EUR/an (SMÉ)

### Poids scoring : 16% (uniquement si applicable)

---

## 5. Post-ARENH 2026

### Chronologie
- ARENH (42 EUR/MWh, 100 TWh/an) terminé le 31/12/2025
- VNU (Versement Nucléaire Universel) depuis 01/01/2026
- Marchés de gros = nouvelle référence pour tous les fournisseurs
- **CAPN** (Contrats d'**Allocation** de Production Nucléaire) : contrats long terme EDF
  - Durée : 10-15 ans, livraison depuis 01/01/2027
  - Volume : 1 800 MW (~10.6 TWh/an)
  - Éligibilité : fournisseurs et consommateurs >= 7 GWh/an

### VNU -- mécanisme
- EDF vend 100% de sa production nucléaire au prix de marché
- Seuil 1 : 78 EUR/MWh -> redistribution partielle
- Seuil 2 : ~110 EUR/MWh -> redistribution renforcée
- En avril 2026 : VNU "dormant" (prix marché ~60 EUR/MWh < seuils)

### Impact sur les clients B2B
- Prix spot négatifs : 513h en 2025 (RTE Bilan Électrique 2025) -> signal NEBCO/flex
- Prix >= 100 EUR/MWh : 1 807h en 2025 (RTE) -> signal couverture
- HC méridiennes 11h-14h pour nouveaux clients (CRE délib. 2026-33 du 04/02/2026)
- Dynamique quart-heure depuis 01/10/2025 (L332-7)

---

## 6. Fiscalité Énergie France 2026 (depuis 01/02/2026)

### Accise Électricité (ex-CSPE/TICFE)
| Catégorie | Description | Tarif (EUR/MWh) |
|-----------|------------|----------------|
| T1 | Ménages & assimilés (<= 250 MWh) | **30.85** |
| T2 | PME / professionnels (250 MWh - 1 GWh) | **26.58** |
| T3 | Grandes entreprises (> 1 GWh) | Taux réduits selon éligibilité |

### Accise Gaz (ex-TICGN) depuis 01/02/2026
| Composante | Tarif |
|-----------|-------|
| Accise propre | 10.73 EUR/MWh |
| ZNI (péréquation zones non-interconnectées) | 5.66 EUR/MWh |
| **Total accise gaz** | **16.39 EUR/MWh** |

### TURPE 7 (Transport & Distribution Électricité)
- Délibération CRE n°2025-78, adoptée 13/03/2025
- Période : 01/08/2025 au **31/07/2029** (4 ans)
- Tarifs soutirage par segment :

| Segment | HPH (EUR/kWh) |
|---------|---------------|
| HTA | **0.0442** |
| BT > 36 kVA (C4) | **0.0569** |

- CMDPS (dépassement puissance) : **12.65 EUR/kW/h**
- Autres périodes (HCH, HPB, HCB, Pointe) : voir `tarifs_reglementaires.yaml`

### CTA (Contribution Tarifaire d'Acheminement)
- **Taux : 15%** depuis 01/02/2026 (arrêté du 28 janvier 2026)
- Historique : 27.04% (avant 08/2021) -> 21.93% (08/2021-01/2026) -> **15%** (actuel)

### TVA
- 5.5% sur abonnement + CTA
- 20% sur consommation + taxes

---

## 7. NEBCO (Notification d'Échanges de Blocs de Consommation)

- Remplace NEBEF depuis 01/09/2025 (RM-5-NEBCO-V01, CRE délib. 2025-199)
- Seuil : **100 kW par pas de contrôle** (hors zéro)
- Ouvre l'accès aux marchés de capacité et services système

---

## 8. Sources de référence à citer

| Référence | Objet |
|-----------|-------|
| Décret n°2019-771 | DT jalons |
| Décret n°2025-1343 | BACS report 70kW à 2030 |
| Loi n°2023-175 | APER ombrières/toitures |
| Loi n°2025-391 du 30/04/2025 | Audit/SMÉ (loi DDADUE) |
| CRE délib. 2025-78 | TURPE 7 HTA-BT |
| CRE délib. 2025-162 | Accès données 10min tiers |
| CRE délib. 2025-199 | Approbation règles NEBCO |
| CRE délib. 2026-33 du 04/02/2026 | HC méridiennes 11h-14h |
| Arrêté 28/01/2026 | CTA 15% distribution |
| ADEME Base Empreinte V23.6 | Facteurs CO2 |
| RTE Bilan Électrique 2025 | Stats prix spot |
