---
name: energy-flexibility-dr
description: "Flexibilité et effacement énergie France : NEBCO, demand response, FCR/aFRR/mFRR, report de charge HP→HC, stockage batteries BESS, signaux RTE EcoWatt/Tempo, jours de pointe PP1/PP2, mécanisme de capacité, agrégateurs, AOFD, interruptibilité, Flex Score, flex locales Enedis. Utiliser ce skill pour flexibilité, effacement, pilotage de charge, stockage, optimisation HP/HC, signaux RTE, pointe électrique, NEBCO, réserves, agrégateurs."
---

# Flexibilité & Demand Response France

## Proactive triggers

- HP ratio > 75% et pas de recommandation report → "Potentiel d'optimisation HP→HC détecté. Simulation de décalage recommandée."
- Pmax > 90% puissance souscrite → "Risque de dépassement. Évaluer l'écrêtement ou le délestage."
- Site avec CVC > 100kW et pas de Flex Score → "Ce site a un potentiel de flexibilité. Calculer le Flex Score."

## Taxonomie des mécanismes

| Mécanisme | Activation | Rémunération | Seuil | Opérateur |
|---|---|---|---|---|
| FCR (Frequency Containment Reserve) | Auto, <30s | Capacité €/MW/h + énergie | 1 MW (pool possible) | RTE via enchères |
| aFRR (Automatic FRR) | Auto, <5min | Capacité + énergie | 1 MW | RTE (PICASSO) |
| mFRR (Manual FRR) | Manuel, <15min | Capacité + énergie | 1 MW | RTE (MARI) |
| NEBCO (ex-NEBEF) | Notification J-1 ou infrajournalier | Énergie €/MWh spot | **100kW** | RTE, via agrégateur |
| AOFD (Appel d'Offres Flex Décentralisée) | Contractuel | Capacité €/MW/an | Variable par lot | RTE |
| Interruptibilité | Signal RTE, <5s | Prime annuelle ~30-50 k€/MW | 50 MW | RTE, contrat direct |
| Capacité (certificats) | PP1/PP2 hiver | Certificats MW | Tout fournisseur | RTE enchères |
| Flex locale Enedis | Contractuel saisonnier | €/MW/an | 100 kW | Enedis |

## Réserves de fréquence — détail

**FCR** : Réglage primaire. Réponse proportionnelle ±200mHz en <30s. Enchères hebdo. Pool possible via agrégateur. Rémunération capacité ~10-20 €/MW/h. Idéal batteries.

**aFRR** : Réglage secondaire. Activation automatique plateforme PICASSO. Réponse <5min. Enchères quotidiennes. Rémunération capacité + énergie activée.

**mFRR** : Réglage tertiaire. Activation manuelle, offres sur MARI. Réponse <15min. Effacement industriel typique. ~200-500 €/MWh activé.

## NEBCO (ex-NEBEF)

Seuil abaissé à **100kW** depuis 01/09/2025 (RM-5-NEBCO-V01). Anciemment 1MW.
Mécanisme : valorisation de l'effacement comme de la production sur le marché spot.
Acteur : RE (Responsable d'Équilibre) d'effacement, souvent via agrégateur.
Rémunération : prix spot au moment de l'effacement + prime de capacité.
Module partenaire OE dans PROMEOS V1.
AOFD : 4 lots, 2900 MW appelables, enchères annuelles.

## Report HP→HC — analyse détaillée

Déclencheur PROMEOS : hp_pct >70% → recommandation optimisation.
Simulation décalage 1h : ~12% de la conso capturable vers HC.

| Usage | Potentiel décalage | Contrainte |
|---|---|---|
| CVC (ventilation, pompes) | 15-30% | Confort thermique, inertie bâtiment |
| ECS (eau chaude sanitaire) | 80-100% | Ballon tampon obligatoire |
| Recharge VE | 90-100% | Programmable, V2G possible |
| Process froid (entrepôt) | 40-60% | Inertie thermique enceinte |
| Éclairage | 0% | Non décalable |
| IT / serveurs | 0% | Non interruptible |
| Lavage industriel | 50-80% | Programmable si batch |

Économie estimée : 5-15% sur composante fourniture, jusqu'à 20% si TURPE 7 horosaisonnier.

## Stockage batteries (BESS)

| Application | Durée | Revenus typiques | Technologie |
|---|---|---|---|
| FCR | 30min-1h | 10-20 €/MW/h | Li-ion |
| Arbitrage spot | 2-4h | Spread peak/off-peak | Li-ion, flow |
| Peak shaving (CMDPS) | 15min-1h | Évite CMDPS 12.65×h | Li-ion |
| Secours (UPS+) | 15min | Pas de revenu direct | Li-ion |
| PV + stockage ACC | 2-4h | Autoconsommation +20-30% | Li-ion |

CAPEX batteries Li-ion 2025 : ~150-250 €/kWh, baisse 10-15%/an.
Marché France : 701 MW installés, objectif ×4 d'ici 2028 (PPE3).

## Mécanisme de capacité — détail

Obligation annuelle pour chaque fournisseur, proportionnelle à la pointe de ses clients.
Jours PP1 (10-15j/hiver) : pointe maximale, signal RTE J-1.
Jours PP2 (10-25j/hiver) : pointe secondaire.
Enchères RTE : 4 sessions/an. Prix 2025 : ~20-40 k€/MW.
Certificats achetables sur marché secondaire EPEX.

## Signaux RTE

**EcoWatt** : vert (normal) / orange (tendu) / rouge (coupures possibles). API publique. Notification J-1.
**Tempo** : 300j bleus (prix bas) + 43j blancs (moyen) + 22j rouges (très cher) × HP/HC = 6 prix. Signal J-1 à 17h. Uniquement résidentiel mais indicateur utile B2B.
**Vigilance coupure** : nouveau service 2025, J-3 à J-1.

## Flex Score PROMEOS

15 usages × 5 dimensions : volume (kW effaçable), durée (heures), réactivité (délai activation), récurrence (jours/an), contrainte (impact process). Score 0-100.
>70 : fortement flexible. 40-70 : modérément. <40 : peu flexible.

## Agrégateurs en France

Principaux : Voltalis (diffus), Energy Pool (industriel), Enel X (multi), Engie Flex Gen, EDF Store & Forecast, Total Flex, Compagnie Nationale du Rhône.
Modèle : partage revenus 70-80% client / 20-30% agrégateur (variable selon contrat).

## Optimisation puissance souscrite

CMDPS = 12.65 × h (€/kW dépassé par heure de dépassement). Calculé sur les 12 derniers mois glissants.
Méthode : analyser Pmax mensuelle sur 12 mois → si Pmax < Psouscrite×0.8 → réduction possible.
Économie : baisse de 1 kW souscrit ≈ économie sur composante fixe TURPE.
Risque : CMDPS coûteux si Pmax > Psouscrite après réduction → toujours garder marge 10%.
