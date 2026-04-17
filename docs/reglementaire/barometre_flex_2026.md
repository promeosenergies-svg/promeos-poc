# Baromètre des flexibilités de consommation d'électricité — Édition 2026

**Source officielle** : RTE, Enedis, GIMELEC, Think Smartgrids, IGNES, ACTEE, IFPEB, SBA — Avril 2026
**Lien doctrine PROMEOS** : confirme doctrine Pilotage des usages (S1-S21), source primaire pour calibrer nos chiffres.

## Faits chiffrés 2025 (officiels)

### Marché & réseau
- **513h** de prix spot négatifs en 2025 (vs 352h en 2024, **+46%**)
- **3 TWh** d'EnR écrêtés en 2025 (vs 1.7 TWh 2024)
- **+5.9 GW** nouveau PV installé en 2025
- Prix pointe 18h-21h : **+111%** vs plage 10h-18h (vs +77% en 2024)
- Prix été plage méridienne 4× moins cher que pointe soir (-393%)
- Consommation corrigée stable ~**450 TWh/an** depuis 2023

### Flexibilité en pratique
- **708 000 sites** inscrits NEBCO fin 2025 (vs 340 000 fin 2024, **×2 en 1 an**)
- Nouveau mécanisme **NEBCO** (Notifications d'Échanges de Blocs de Consommation) actif depuis **1/09/2025**, remplace NEBEF
- Permet valorisation des **décalages** (pas seulement effacements)
- 1,2M clients résidentiels Tempo/type Tempo — baisse 30-40% jours rouges = **400 MW** hiver
- Agrégateurs agréés : 21 en 2025 dont 43% créés depuis 2023

### Tertiaire
- **32 000 BACS** installés fin 2025 (objectif 100 000 en 2030 non atteint, rythme actuel → 2040)
- 16% des bâtiments tertiaires équipés BACS (vs 15% en 2024)
- 45% des BACS installés ne sont pas exploités activement
- **Flex Ready®** : marque GIMELEC/Think Smartgrids créée en 2024, déployée en 2025

## Mécanisme NEBCO (1/09/2025+)

| Aspect | NEBEF (ancien) | NEBCO (nouveau) |
|---|---|---|
| Valorisation | Effacements uniquement | Décalages (baisse + hausse) |
| Opportunités | Rares (dépend barème fournisseur) | Quotidiennes (dépend spread prix) |
| Échéances | - | 7j pour sites >36 kVA, 2j pour ≤36 kVA |

**Formule de valorisation** :
```
Décalage = écart prix marché (spread) − solde compensation fournisseur
```

## Standard Flex Ready® (NF EN IEC 62746-4)

5 données échangées entre GTB et acteurs marché (fournisseurs, agrégateurs, GRD) :
1. **Horloge** (pas 15 min min, bidirectionnel)
2. **Puissance max instantanée** (kW)
3. **Prix** (€/kWh) — tarif fournisseur
4. **Puissance souscrite** (kVA)
5. **Empreinte carbone** (tCO₂e)

**Interopérabilité** :
- Amont : NF EN IEC 62746-4 (entre acteurs marché ↔ HEMS/GTB)
- Aval : Code of Conduct for Energy Smart Appliances (Commission UE) phase 2 — SAREF4ENER
- Norme EN 50631 (chauffage/ECS/ventilation), EN 50491-12-2 S2 (HEMS)

## Évolution Heures Creuses TURPE 7

### Calendrier déploiement (Enedis)
- **Phase 1** : nov 2025 → mai 2026 (5,2M clients résidentiels, HC identiques été/hiver)
- **Phase 2** : déc 2026 → nov 2027 (22,8M clients résidentiels+pro ≤36 kVA, HC saisonnalisées été/hiver)
- **Phase 3** : juin 2027 → août 2028 (550k clients Marché d'Affaires BT>36 + HTA)

### Créneaux par saison

**Saison basse (été, 1/04 → 31/10)** :
- À FAVORISER : 2h-6h + 11h-17h (heures solaires)
- À EXCLURE : 7h-11h + 18h-23h

**Saison haute (hiver, 1/11 → 31/03)** :
- À FAVORISER : 2h-6h + 21h-24h
- À EXCLURE : 7h-11h + 17h-21h

**Règles** :
- 8h HC/jour par client
- Si 2 plages : 1 diurne (8h-20h) + 1 nocturne (20h-8h)
- Plage nocturne min 5h (facilite recharge VE)
- Plage diurne min 2h

### Impact attendu
- **5 GW** de consommation déplacés vers 14h dès 2027 (ECS asservi + VE)
- ECS résidentiel aujourd'hui : pic nocturne 4h-8h (~7 GW) → demain split nuit/14h

## 3 types de flexibilités (doctrine officielle)

| Type | Horizon | Opportunité | Mécanisme |
|---|---|---|---|
| **1. Structurelle/régulière** | A-3 à J-7, fixe | HC, offres HP/HC/dynamiques | TRVe, contrats saisonnalisés |
| **2. Dynamique** | J-7 à H-1 | Marchés SPOT day-ahead + IDA | NEBCO, offres "bloc + SPOT" |
| **3. Équilibrage** | H-1 à temps réel | Mécanisme ajustement RTE | Services système (géré par RTE, hors flex quotidien) |

**Le module Pilotage PROMEOS cible les types 1 et 2.**

## Chiffres sectoriels (Enedis, 2024)

| Segment | Sites | Surface (millions m²) | BACS équipés | Conso TWh/an |
|---|---|---|---|---|
| Bureaux | 42 000 | 130 | 17% | - |
| Commerces | 60 000 | 150 | 17% | - |
| Enseignement | 37 000 | 166 | 13% (lycées 46%) | 4.5 |
| Santé | 3 000 | 30 | 40% | 7 |
| Hôtels/Restos | 12 000 | 25 | 11% | 5.7 |
| Sport/Culture | 21 000 | 42 | 11% | 8.3 |
| Transport | 3 500 | 30 | 27% | 3.8 |

**Total tertiaire** : 121 TWh/an, 70% de la consommation France avec résidentiel (139 TWh).

## Pic consommation journalier (2025 hiver ouvré)

- Tertiaire : pic matinal 7h-10h à 25 GW puis plateau
- Résidentiel : pic soir 19h à 36 GW (jour froid)
- Résidentiel été : pic tardif 22h, pic méridien émergent (climatisation)

**Plages à éviter pour le système** : 7h-10h + 17h-20h (ces 2 plages = 28% de la conso journalière tertiaire).

## Filière organisée

8 acteurs signataires du baromètre :
- RTE (gestionnaire transport)
- Enedis (GRD 95%)
- GIMELEC (équipementiers électriques, marque Flex Ready®)
- IGNES (équipementiers bâtiment)
- Think Smartgrids (filière smart grids, marque Flex Ready®)
- ACTEE/FNCCR (collectivités, programme CEE)
- IFPEB (performance bâtiment)
- SBA (Smart Buildings Alliance)
- AICN (Alliance Immobilière Convergence Numérique)

## Implications PROMEOS

### Alignements confirmés
- Module Pilotage B2B : sur la bonne trajectoire
- Wording "Pilotage des usages" : aligné avec la doctrine publique
- NEBCO à 100 kW : seuil interne correct
- Focus sur flex structurelle+dynamique (pas équilibrage RTE)

### Gaps à combler (voir DETTES.md)
1. **Créneaux TURPE 7 saisonnalisés** non intégrés dans classify_slots
2. **Flex Ready®** standard absent de notre API (5 données NF EN IEC 62746-4)
3. **Chiffres sectoriels** archétypes pas calibrés sur données Enedis 2024
4. **Connecteur EcoWatt®** non implémenté (utile pour flex dynamique hiver)

### Opportunités différenciantes (post S22)
- Score Flex Ready® par site (notre extension du standard)
- Prédiction prix négatifs (ML léger sur historique ENTSO-E)
- Intégration CO₂ réel via éco2mix (Option C V120)
- Audit flexibilité automatisé (alignement avec cahier SBA)
