---
name: promeos-regulatory
description: "Réglementation énergie B2B France : Décret Tertiaire, OPERAT, BACS (GTB), APER, Audit Énergétique/SMÉ ISO 50001, DPE tertiaire, CSRD énergie, scoring conformité RegOps, sanctions, exclusions, modulation, Valeurs Absolues. Utiliser ce skill dès qu'il est question de conformité réglementaire énergie, décret tertiaire, objectifs -40%/-50%/-60%, OPERAT, BACS classe C, loi APER, audit énergétique, scoring conformité, DPE, CSRD, ou toute obligation énergie tertiaire."
---

# PROMEOS Regulatory — RegOps Engine

## Routing — Quand lire quel fichier

| Question / Contexte | Fichier reference à lire |
|---|---|
| Calcul DT, jalons, VA, modulation, sanctions | `references/decret-tertiaire-detail.md` |
| BACS seuils, classes, TRI, inspections | `references/bacs-detail.md` |
| Scoring, poids, applicabilité, APER, Audit | Ce SKILL.md suffit |

## Proactive triggers — Alerter sans qu'on demande

- Site > 1000m² sans scoring DT → "Ce site est assujetti au Décret Tertiaire (Décret n°2019-771, art. R174-22) mais n'a pas de scoring conformité."
- Deadline modulation < 6 mois (30/09/2026) → "Deadline modulation DT dans moins de 6 mois. Dossier OPERAT à préparer."
- Score conformité < 50% → "Score conformité critique. Actions correctives prioritaires nécessaires."
- BACS seuil 70kW applicable dès 01/01/2030 → "Le seuil BACS passe à 70kW au 01/01/2030 (report décret 27/12/2025). Vérifier les sites qui deviennent assujettis."
- CO₂ factor utilisé ≠ 0.052 → "Le facteur CO₂ électricité doit être 0.052 kgCO₂/kWh (ADEME V23.6). Valeur incorrecte détectée."

## Cadres réglementaires

| Cadre | Texte | Cible | Deadline | Sanctions |
|---|---|---|---|---|
| Décret Tertiaire | Décret n°2019-771 | Bâtiments ≥1,000m² | -40% 2030 / -50% 2040 / -60% 2050 | Publish & shame (OPERAT) + 7,500€/bâtiment |
| BACS | Décret n°2025-1343 | CVC > seuils kW | 01/01/2025 (290kW), **01/01/2030** (70kW, report déc. 2025) | Contrôle DREAL, amende administrative |
| APER | Loi n°2023-175 | Parkings ≥1,500m², toitures ≥500m² | Progressif 2025-2028 | 40,000€/an + 200€/place |
| Audit/SMÉ | Loi n°2025-391 | Orgs > 2.75 GWh | 11/10/2026 | 1,500€/an (audit), 3,000€/an (SMÉ) |
| DPE tertiaire | EPBD recast | Bâtiments tertiaires | 2026-2027 (transposition) | À définir |
| CSRD (volet énergie) | Directive 2022/2464 | Entreprises >250 sal ou CA>50M€ | 2025-2026 | Sanctions financières + audit |

## Décret Tertiaire — détail

### Jalons officiels (is_official:true)

- **2030** : -40% vs référence
- **2040** : -50% vs référence
- **2050** : -60% vs référence
- ⚠️ Pas de jalon 2026 (-25%) dans l'API PROMEOS.

### Année de référence

Par défaut: 2020. Choix possible parmi 2010-2020 (année la plus consommatrice recommandée).
Méthode: `conso_ref_corrigée = conso_ref_brute × (DJU_normale / DJU_année_ref)`
Objectif 2030: `objectif_2030 = conso_ref_corrigée × 0.60`

### Valeurs Absolues (VI)

Alternative à la méthode relative pour les bâtiments déjà performants.
Publiées par catégorie fonctionnelle (arrêté sept 2025) :

| Catégorie | VI 2030 (kWhEF/m²/an) | VI 2050 |
|---|---|---|
| Bureau standard | ~110 | ~70 |
| Enseignement | ~90 | ~55 |
| Hôtel | ~160 | ~100 |
| Commerce | ~130 | ~80 |
| Logistique (sec) | ~40 | ~25 |

Le site peut choisir la méthode la plus favorable (relative ou absolue).

### Périmètre et exclusions

**Inclus** : tous bâtiments tertiaires ≥1,000m², propriétaire OU locataire (bail tertiaire).
**Exclus** : constructions provisoires <2 ans, lieux de culte, bâtiments militaires, installations industrielles process (>80% process).
**Multi-occupants** : chaque occupant déclare sa partie, propriétaire déclare parties communes.
**Mixte** : si tertiaire >1,000m² même dans un bâtiment mixte → soumis.

### Modulation

Deadline demande : **30/09/2026** via OPERAT.
Motifs acceptés : contraintes techniques (patrimoine, architecture), coût disproportionné (>10% valeur vénale), changement activité.
Instruction par ADEME, réponse sous 6 mois.

### Plateforme OPERAT

Déclaration annuelle obligatoire (avant 30/09 de N+1).
Données : conso annuelle par énergie, surface, activité, année de référence.
Export PROMEOS → format OPERAT possible (CSV structuré).
Mapping NAF→OPERAT via `utils/naf_resolver.py` : 70.10Z→BUREAU_STANDARD, 85.31Z→ENSEIGNEMENT, 55.10Z→HOTEL_HEBERGEMENT, 52.10B→LOGISTIQUE_SEC.

## BACS — détail

### Obligation GTB

| Seuil CVC | Date | Classe min | Cible |
|---|---|---|---|
| >290 kW | 01/01/2025 | Classe C | Existants |
| >70 kW | **01/01/2030** (report décret 27/12/2025) | Classe C | Existants |
| Tout neuf | Immédiat | Classe B | Neuf RT2020/RE2020 |

### Classes NF EN ISO 52120-1:2022

| Classe | Niveau | Fonctionnalités |
|---|---|---|
| D | Non conforme | Pas de GTB ou GTB non fonctionnelle |
| C | Minimum réglementaire | Régulation horaire, programmation, comptage, alarmes |
| B | Avancé | Optimisation, historisation, détection anomalies |
| A | Haute performance | Gestion prédictive, interconnexion multi-systèmes |

### Exemption

TRI (temps de retour investissement) **>10 ans** → exemption documentée (après déduction aides/CEE).
Calcul TRI : CAPEX GTB / économies annuelles estimées (méthode ADEME).
Pas de plateforme centralisée (≠ OPERAT), contrôle par DREAL sur demande.

## APER — détail

### Parkings

| Surface | Obligation | Deadline |
|---|---|---|
| ≥10,000m² existant | 50% ombrières PV | 01/07/2026 |
| 1,500-10,000m² existant | 50% ombrières PV | 01/07/2028 |
| ≥1,500m² neuf | 50% ombrières PV | Immédiat |

Sanctions : 40,000€/an + 200€/place non couverte.
Exemption si contrainte technique documentée (patrimoine, ombrage, etc.).

### Toitures

Neuf et rénovations lourdes, surface ≥500m² : 50% végétalisée ou PV ou mixte.

## Audit Énergétique / SMÉ

| Critère | Obligation | Périodicité |
|---|---|---|
| Org > 2.75 GWh | Audit énergétique (NF EN 16247) | Tous les 4 ans |
| Org > 23.6 GWh | ISO 50001 (SMÉ certifié) | Continu + audit externe 3 ans |

Seule règle **org-level** (pas site-level). Deadlines : **11/10/2026** (audit >2.75 GWh) / **11/10/2027** (SMÉ >23.6 GWh).
Auditeurs qualifiés COFRAC ou équivalent.
Contenu audit : bilan énergétique, plan d'actions chiffré, ROI par action, priorisation.

## DPE tertiaire (EPBD recast)

Transposition 2026-2027. DPE obligatoire pour bâtiments tertiaires (vente + location + affichage).
Nouvelle échelle A-G harmonisée EU. ZEB (Zero Emission Building) obligatoire pour neuf à partir de 2030.
Passeport rénovation : feuille de route par bâtiment vers classe A/B.

## CSRD — volet énergie

Entreprises soumises (>250 salariés ou CA>50M€) doivent reporter ESRS E1 (Climat) :

- Consommation énergie totale (MWh) par source
- Part ENR (avec GO si market-based)
- Émissions GES scope 1+2+3
- Objectifs de réduction et trajectoire
- Données auditées par CAC

Impact PROMEOS : les données billing + consommation + CO₂ alimentent le reporting CSRD.

## Scoring conformité (source unique: compliance_score_service.py A.2)

### Pondérations

Standard: DT 45% / BACS 30% / APER 25% (CEE exclues du score).
Avec Audit: DT 39% / BACS 28% / APER 17% / Audit 16%.

### Applicabilité contextuelle

Chaque règle est applicable SI le site/org remplit les critères :
- DT si surface ≥1,000m²
- BACS si CVC >290kW (2025) ou >70kW (2030)
- APER si parking ≥1,500m² ou toiture ≥500m²
- Audit si org >2.75 GWh

Poids redistribués proportionnellement si une règle n'est pas applicable.

### Score par règle

| Score | Signification | Couleur |
|---|---|---|
| 90-100 | Conforme | Vert |
| 70-89 | En bonne voie | Vert clair |
| 50-69 | Attention requise | Orange |
| 30-49 | Non-conforme partiel | Rouge clair |
| 0-29 | Non-conforme critique | Rouge |

## Constantes

- CO₂ élec: **0.052 kgCO₂/kWh** (ADEME V23.6)
- CO₂ gaz: **0.227 kgCO₂/kWh**
- Coeff EP élec: **1.9** (jan 2026, ancien 2.3)
- OID bureau: ~146 kWhEF/m²/an (2022, 25,300 bâtiments)
- DJU: COSTIC, Open-Meteo (cache 30min), Paris ~2400, Lyon ~2750

## Disclaimer

Les informations réglementaires de ce skill sont fournies à titre informatif et ne constituent pas un conseil juridique. Les valeurs tarifaires et seuils réglementaires sont basés sur les textes officiels en vigueur à la date de création du skill (avril 2026). Vérifier les sources officielles (CRE, Legifrance, ADEME/OPERAT) pour les valeurs à jour. PROMEOS n'est pas un cabinet de conseil réglementaire.
