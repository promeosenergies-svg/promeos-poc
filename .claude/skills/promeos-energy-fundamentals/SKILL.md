---
name: promeos-energy-fundamentals
description: "Fondamentaux énergie B2B : unités (kWh/MWh/kW/kVA), DJU, facteurs CO₂, énergie primaire/finale, périodes tarifaires HP/HC/HPH/HCH/HPB/HCB/Pointe, puissance souscrite/atteinte, tan φ, réactif, courbes de charge, baseload, monotone, benchmarks OID/CEREN, signature énergétique, CUSUM, analyse de dérives. Utiliser ce skill pour unités, conversions, DJU, CO₂, énergie primaire vs finale, courbe de charge, optimisation puissance, KPIs (kWh/m², €/m², kgCO₂/m²), ou tout concept fondamental de gestion énergétique."
---

# Fondamentaux Énergie B2B

## Routing

| Contexte | Fichier |
|---|---|
| Signatures de charge par archétype, dérives, ICE | `references/archetypes-signatures.md` |
| 30 règles d'anomalie avec seuils | `references/anomaly-rules-30.md` |
| Tout le reste (unités, DJU, CO₂, KPIs) | Ce SKILL.md suffit |

## Proactive triggers

- Facteur CO₂ ≠ 0.052 pour l'électricité → "Le facteur CO₂ électricité France est 0.052 kgCO₂/kWh (ADEME V23.6). Valeur incorrecte."
- 0.0569 utilisé comme facteur CO₂ → "0.0569 est le tarif TURPE 7 HPH (€/kWh), PAS un facteur CO₂!"
- Coefficient EP ≠ 1.9 pour électricité → "Le coefficient EP électricité est 1.9 depuis janvier 2026 (ancien: 2.3)."
- Calcul KPI en frontend détecté → "Violation architecture: les KPIs doivent être calculés backend."
- kWh/m² > 500 pour un bureau → "Intensité anormalement élevée pour un bureau (benchmark OID: ~146 kWhEF/m²/an)."

## Unités et conversions

| Grandeur | Unité | Conversion |
|---|---|---|
| Énergie | kWh, MWh, GWh | 1 MWh = 1000 kWh, 1 GWh = 1000 MWh |
| Puissance active | kW, MW | Énergie utile |
| Puissance apparente | kVA, MVA | S = √(P² + Q²) |
| Puissance réactive | kVAR | Q = S × sin(φ) |
| Énergie finale (EF) | kWhEF | Ce que le compteur mesure |
| Énergie primaire (EP) | kWhEP | EP = EF × coefficient |
| Gaz : volume → énergie | m³ → kWh PCS | kWh = m³ × coeff_thermique (11.2-12.8) |

## Facteur de puissance et réactif

**cos φ** = P / S. Obligatoire ≥0.928 (tan φ ≤ 0.4) pour éviter pénalités TURPE.
Si tan φ > 0.4 : surcoût ~1.5 c€/kVARh excédentaire.
Solution : condensateurs (batterie de compensation), coût CAPEX ~10-30 €/kVAR.

## Facteurs CO₂ (ADEME Base Empreinte V23.6)

| Énergie | Facteur | Méthode |
|---|---|---|
| Électricité France | **0.052 kgCO₂/kWh** | Contenu moyen annuel (Base Carbone) |
| Électricité France (marginal) | ~0.060 kgCO₂/kWh | Contenu marginal (RTE) |
| Gaz naturel | **0.227 kgCO₂/kWh** PCI | Combustion + amont |
| Réseau de chaleur | Variable, ~0.100-0.200 | Dépend du mix local |
| Fioul domestique | 0.324 kgCO₂/kWh | |

⚠️ **0.0569 = tarif TURPE 7 HPH (€/kWh), JAMAIS un facteur CO₂**
Calcul CO₂ = toujours backend-only. Scope 1 (combustion directe) + Scope 2 (électricité achetée).
CSRD : Scope 2 location-based (facteur moyen) + market-based (avec GO/PPA).

## Coefficient énergie primaire

| Énergie | Coefficient EP | Date d'application |
|---|---|---|
| Électricité | **1.9** | Depuis 01/01/2026 (arrêté 10/12/2025) |
| Électricité (ancien) | 2.3 | Avant 01/01/2026 |
| Gaz | 1.0 | Stable |
| Bois | 0.6 | RE2020 |
| Réseau de chaleur | Variable (0.5-1.5) | Selon mix réseau |

⚠️ Le changement 2.3→1.9 impacte les calculs Décret Tertiaire : les bâtiments tout-électrique sont mécaniquement plus performants en EP.

## DJU (Degrés-Jours Unifiés)

### Formule

DJU_jour = max(0, 18 - T_moyenne_jour). Méthode COSTIC (référence OPERAT).
DJU_annuel = Σ DJU_jour sur l'année.

### Zones climatiques et DJU normales (30 ans)

| Ville | Zone | DJU annuel normal | Hiver (Nov-Mars) |
|---|---|---|---|
| Paris | H1a | ~2400 | ~1900 |
| Strasbourg | H1b | ~2800 | ~2200 |
| Lyon | H1b | ~2750 | ~2100 |
| Nantes | H2a | ~2100 | ~1600 |
| Bordeaux | H2b | ~1900 | ~1400 |
| Marseille | H2d | ~1500 | ~1100 |
| Nice | H3 | ~1200 | ~900 |

### Correction climatique

`conso_corrigée = conso_brute × (DJU_normale / DJU_réelle)`
Champ API : `is_normalized=True` quand correction appliquée.
Source : Open-Meteo (cache 30min, fallback station météo la plus proche).

### DJU froid (climatisation)

DJU_froid = max(0, T_moyenne_jour - 24). Pertinent pour hôtels, datacenters, commerce.
Nice : ~300, Marseille : ~250, Paris : ~100.

## Périodes tarifaires TURPE 7

### Saisons

- **Hiver** : Novembre à Mars (5 mois)
- **Été** : Avril à Octobre (7 mois)

### Plages horaires

| Période | Jours | Heures | Ratio prix |
|---|---|---|---|
| Pointe | PP1/PP2 (10-15j/hiver, RTE J-1) | Variables (7h-14h ou 18h-20h) | 1.30 |
| HPH | Lun-Sam hiver hors pointe | 7h-23h | 1.00 (réf) |
| HCH | Dim + fériés hiver + nuit | 23h-7h | 0.62 |
| HPB | Lun-Sam été | 7h-23h | 0.78 |
| HCB | Dim + fériés été + nuit | 23h-7h | 0.50 |

HC méridiennes 11h-14h pour nouveaux contrats (CRE 2026-33) : créneau supplémentaire lié au creux solaire.

## Courbes de charge — analyse

### Résolutions

| Source | Résolution | Segment | Volume/an |
|---|---|---|---|
| SGE télérelevé | 10min | C1-C4 | 52,560 points |
| DataConnect Linky | 30min | C5 | 17,520 points |
| Seed PROMEOS | Horaire | Démo | 8,760 points |
| Index compteur | Journalier | Tous | 365 points |

### Indicateurs clés d'une CDC

| Indicateur | Formule | Interprétation |
|---|---|---|
| Baseload | Min sur 30j (hors weekend) | Consommation plancher (IT, veille, éclairage sécu) |
| Facteur de charge | Énergie / (Pmax × heures) | FC>0.7=bon, FC<0.3=intermittent |
| Ratio weekend/semaine | Conso_WE / Conso_semaine | >0.5=potentiel d'économie weekend |
| Ratio nuit/jour | Conso_nuit / Conso_jour | >0.4=baseload élevé |
| Pointe vs baseload | Pmax / Pbaseload | >5=pic violent, optimiser |

### Monotone de puissance

Courbe des puissances triées par ordre décroissant (8760h/an).
Lecture : X% du temps, la puissance est ≤ Y kW.
Usage : dimensionnement puissance souscrite, batterie, effacement.
Si les 100 premières heures > 130% de la médiane → peak shaving rentable.

## Signature énergétique

E = a × DJU + b

- **a** = sensibilité thermique (kWh/DJU). a élevé → bâtiment thermiquement sensible → isolation prioritaire.
- **b** = baseload (kWh/jour hors chauffage). b élevé → usages non thermiques importants.
- R² : qualité de la corrélation. R²>0.85=bon modèle, R²<0.6=usages non thermiques dominants.

Période de calcul : hiver uniquement (Nov-Mars) pour éviter biais climatisation.

## CUSUM (Cumulative Sum)

Détection de dérives de consommation par rapport à un modèle de référence.

CUSUM_t = Σ(conso_réelle - conso_prédite) de t=1 à t=T

- CUSUM croissant → surconsommation systématique (dérive chauffage, fuite, équipement défaillant)
- CUSUM décroissant → sous-consommation (mesure d'économie effective, arrêt équipement)
- Seuil alerte : |CUSUM| > 5% × conso_annuelle_prédite

## KPIs PROMEOS

| KPI | Formule | Unité | Benchmark bureau OID |
|---|---|---|---|
| Intensité énergétique | conso_kWh / surface_m² | kWhEF/m²/an | ~146 |
| Intensité carbone | conso × facteur_CO₂ / surface | kgCO₂/m²/an | ~7.6 (élec seul) |
| Coût surfacique | coût_€ / surface | €HT/m²/an | ~18-25 |
| Ratio HP/HC | conso_HP / total × 100 | % | ~65-75 |
| Facteur de charge | Énergie / (Pmax × 8760) | sans unité | 0.3-0.5 |
| Baseload ratio | P_baseload / P_max | % | 20-35% |

### Benchmarks sectoriels (CEREN + OID + ADEME)

| Secteur | kWhEF/m²/an | kgCO₂/m²/an | €HT/m²/an |
|---|---|---|---|
| Bureau standard | 120-180 (OID: 146) | 6-10 | 15-25 |
| Enseignement | 80-130 | 4-7 | 8-15 |
| Hôtel / hébergement | 150-250 | 8-15 | 20-40 |
| Commerce alimentaire | 300-500 | 15-25 | 40-65 |
| Commerce non-alimentaire | 100-200 | 5-10 | 12-25 |
| Logistique (sec) | 30-70 | 2-4 | 3-8 |
| Logistique (froid) | 150-350 | 8-18 | 20-45 |
| Santé / hôpital | 200-350 | 10-20 | 25-45 |
| Industrie légère | 80-200 | 4-10 | 10-25 |

**Règle absolue** : Zéro business logic en frontend. Tous KPIs calculés backend.
