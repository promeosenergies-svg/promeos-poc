# Audit docs Drive — extraction sans ACC pour PROMEOS

> **Mission** : lecture des 6 documents Drive prioritaires et extraction des éléments **compatibles avec PROMEOS sans ACC**.
> **Date** : 2026-05-23 · **Mode** : READ-ONLY (Drive uniquement, aucune modification de code).
> **Scope IN court terme** : Patrimoine · Conformité · Conso/Performance · Bill Intelligence · Achat · Centre d'Action · pilotage des usages **advisory**.
> **Scope OUT court terme** : ACC (Autoconsommation Collective), PMO, clé de répartition, participants ACC, settlement local, module ACC complet.
> **Filtre appliqué** : tout concept, KPI, endpoint ou idée touchant à l'ACC est marqué `EXCLURE ACC` et écarté.

## Sources lues

| # | Document | Drive ID | Taille | Statut |
|---|---|---|---|---|
| 1 | Brique 1 – Data & Conformité (Système expert proactif) | `1UJOz5hSHG5r50Rr-ct61Dg8G61b5miJL` | 38 KB | ✅ Lu intégral |
| 2 | Analyse experte – Obligations réglementaires & Data&Conformité multi-énergie | `1yZLK4vHKXnfggsBLFaALwIuE1h4hTgFS` | 205 KB | ✅ Lu intégral |
| 3 | brochure-tarifaire-turpe-7 (1) (CRE délibération 2025-78) | `1z9hLgaYVVDY64lDa3wCx2Yaya3XT-FG1` | 560 KB | ✅ Lu intégral |
| 4 | Air France – CMH – Diag BACS_v2 (Alter Watt 09/2025) | `1KkYbIWhqcYjK34bxwKkfANbHWTecLHYG` | 2,4 MB | ✅ Lu intégral (57 pages) |
| 5 | guide_bacs_janvier_2026 (v2 officiel) | `1KioIjrqZUXFV2e8kiTYFWIxAxqGMbTXD` | 330 KB | ✅ Lu intégral |
| 6 | 2026-04-16-barometre-flexibilite-consommation (RTE/CRE/CDC/ACE) | `1_faW7yut14Dkb80VEQiCd8c4jIVjN9Nr` | 18 MB | ✅ Lu (pas de troncature signalée) |

---

## 1. Règles réglementaires à intégrer

### 1.1 Décret Tertiaire (Éco Énergie Tertiaire)

| Item | Valeur | Source |
|---|---|---|
| Texte | Décret **n°2019-771** du 23 juillet 2019 (art. 175 loi ELAN 2018) + arrêtés d'application | Doc 2 |
| Périmètre | Bâtiment tertiaire ≥ 1 000 m² surface de plancher tertiaire | Doc 2 |
| Cible 2030 | -40 % consommation finale **climat-corrigée** vs année référence 2010–2019 OU seuil absolu par arrêté | Doc 2, Doc 4 |
| Cible 2040 | -50 % | Doc 2 |
| Cible 2050 | -60 % | Doc 2 |
| Déclaration | Annuelle, plateforme OPERAT (ADEME), **avant 30 septembre** | Doc 2 |
| Historisation | 5 ans glissants minimum (justificatifs relevés, factures, rapports) | Doc 2 |
| Mutualisation | Compensation surperformances entre sites du **même EJ** (arrêté avril 2022) — **pas inter-EJ** | Doc 2 |
| Modulation | Dossier technique avant 30/09/2026 (monument classé, ROI disproportionné, changement d'activité) | Doc 2 |
| Climat correction | DJU publiés par administration (ADEME) — coefficients v2025+ | Doc 2 |
| Sanctions | Name & Shame + amende max **7 500 € (PM)** si objectif manqué sans plan justificatif | Doc 2 |
| Coefficients ADEME (CO₂) | 0,052 kgCO₂e/kWh élec · 0,227 kgCO₂e/kWh gaz (ADEME V23.6) | Doc 2 |

### 1.2 BACS (Building Automation & Control Systems)

| Item | Valeur | Source |
|---|---|---|
| Textes | Décret **n°2020-887** du 20/07/2020 + Décret **n°2023-259** + Arrêté **7/04/2023** | Doc 5 |
| Articles CCH | **R.175-1 à R.175-5-1** code de la construction et de l'habitation | Doc 5 |
| Seuil 2025 | Bâtiment existant CVC > **290 kW** : conformité avant 1er janvier 2025 | Docs 4, 5 |
| Seuil 2030 | Bâtiment existant CVC > **70 kW** : conformité avant 1er janvier 2030 | Doc 5 |
| Bâtiment neuf > 290 kW | Obligation dès **21 juillet 2021** | Doc 5 |
| Bâtiment neuf > 70 kW | Obligation dès **9 avril 2024** | Doc 5 |
| Renouvellement partiel/total | Délai **2 ans max** après renouvellement (si > 70 kW) | Doc 5 |
| Exemption TRI | **TRI > 10 ans** → exemption (étude documentée requise) | Docs 4, 5 |
| Formule TRI officielle | `TRI = S / (Σ Génergie × Cénergie)` avec `S = I − A` (investissement − aides) | Doc 5 |
| Calcul gain par défaut | `Génergie = G × (Σ Ci,j / 2)` avec `G = 15 %` défaut ou audit, Ci,j = conso 2 dernières années | Doc 5 |
| Exemption faible conso | Équipement < 5 % conso totale (éclairage seul, petits ballons ECS < 150 L, ventilation faible puissance) | Doc 4 |
| Norme classes | NF EN ISO 52120-1:2022 — classes **A / B / C / D** (C = conforme mini, A/B = bonus CEE 1,5–2×) | Docs 4, 5 |
| Inspection périodique | Tous les 5 ans (2 ans après install/renouvellement) ; rapport pro signé | Doc 5 |
| 4 fonctions minimales BACS | (i) mesure/enregistrement horaire par usage/zone (ii) pilotage temps réel (iii) détection dérives + alertes (iv) interopérabilité protocoles standards | Doc 2 |
| Points de mesure obligatoires | Température, éclairement, taux CO₂, détection présence, conso/prod horaire | Doc 5 |
| 7 lots ISO 52120-1 | Chauffage · Eau Chaude Sanitaire · Refroidissement · Ventilation+CVC · Éclairage · Stores · Gestion technique générale | Doc 4 |
| Sécurité légionelle ECS | T° production ≥ 60 °C · T° retour boucle ≥ 50 °C · T° usage ≥ 55 °C — interdit capteur T° direct dans circuit | Doc 4 |

### 1.3 APER (Loi sur l'Accélération de la Production d'EnR)

| Item | Valeur | Source |
|---|---|---|
| Texte | Loi **n°2023-175** du 10 mars 2023 + Décret **n°2024-1023** du 13/11/2024 | Doc 2 |
| Parking ≥ 10 000 m² non concédé | 50 % surface couverte ombrières PV avant **01/07/2026** — amende max **40 000 €/an** | Doc 2 |
| Parking 1 500–10 000 m² non concédé | 50 % surface couverte PV avant **01/07/2028** — amende max **20 000 €/an** | Doc 2 |
| Parking concédé/DSP | 50 % PV au renouvellement contrat ou date limite 2026–2028 | Doc 2 |
| Exemptions | Contrainte technique, patrimoniale, environnementale, économique disproportionnée, ombrage naturel ≥ 50 % arbres, démantèlement programmé — dossier justificatif | Doc 2 |
| Mutualisation | Parkings adjacents même propriétaire : ombrières peuvent couvrir obligation totale combinée | Doc 2 |

### 1.4 TURPE 7 (Tarif Utilisation Réseaux Publics Électricité)

| Item | Valeur | Source |
|---|---|---|
| Délibération CRE | **n° 2025-78** du 13 mars 2025 | Doc 3 |
| Publication JO | 14 mai 2025 | Doc 3 |
| Entrée en vigueur | **1er août 2025** (indexation −1,92 % vs TURPE 6, transfert Facé budget État) | Doc 3 |
| Durée validité | 4 ans moyenne, évolutions annuelles 1/8/2026, 2027, 2028 (≈ inflation) | Doc 3 |
| Apurement CRCP | Anticipé au 1/2/2025 (+7,7 % exceptionnel TURPE 6) pour lissage entrée TURPE 7 | Doc 3 |
| Domaines tension | HTA (1–50 kV) · BT > 36 kVA · BT ≤ 36 kVA | Doc 3 |
| Composantes | CG · CC · CS · CMDPS · CER · CACS · CR · CT · CI (= 0) · CACNC | Doc 3 |
| Plages temporelles HTA | 5 plages : Pointe / HPH / HCH / HPB / HCB | Doc 3 |
| Plages temporelles BT > 36 | 4 plages : HPH / HCH / HPB / HCB | Doc 3 |
| Pointe mobile | Signal **PP1 RTE** déterminé veille (10–15 j/an max) | Doc 3 |
| CER énergie réactive | **Supprimée en BT > 36 kVA** depuis 1/8/2025 — maintenue HTA (tg φ max 0,40 → 2,44 c€/kVAr·h) | Doc 3 |
| Heures creuses en journée | Décision CRE — déploiement **mi-2027 → mi-2028** — objectif déplacer ~5 GW conso vers après-midi d'ici 2030 | Doc 6 |
| Tarif Base | Suppression progressive : 18–36 kVA supprimé · 9–15 kVA extinction · 3–6 kVA expérimentation "pointe" | Doc 6 |

### 1.5 NEBCO + flexibilité (RTE/CRE)

| Item | Valeur | Source |
|---|---|---|
| NEBCO mise en service | **1er septembre 2025** (remplace NEBEF) | Doc 6 |
| Mécanisme | Décalages de consommation + effacements (paradigme shift NEBEF → décalages quotidiens) | Doc 6 |
| Agrément agrégateurs | **RTE** agrée, **CRE** vérifie — liste publique RTE Portail Services | Doc 6 |
| Rôle RTE | Mesure énergie modulée, rééquilibrage périmètres, facturation agrégateurs, versement aux fournisseurs | Doc 6 |
| Volumes sept→déc 2025 | +230 000 sites en 4 mois — total **708 000 sites tertiaires** + 600 000 résidentiels | Doc 6 |
| Clients HP/HC | ~14,5 M (2025) | Doc 6 |
| Clients TEMPO | ~1,2 M — capacité ~400 MW — réduction 30–40 % jours signalés | Doc 6 |
| Indice flexibilité conso | 4 % (2025) → cible **18 % en 2030** | Doc 6 |
| BACS Flex Ready® | 0 % aujourd'hui → cible > 50 % en 2030 (32 k BACS → 100 k cible 2030) | Doc 6 |
| Primo-agrégateur | Pas de statut régulé — intermédiaire, contractualisation obligatoire avec agrégateur RTE accrédité | Doc 6 |
| EPBD 2024 (UE) | Transposition France **mai 2026** — bâtiments neufs/rénovés "pilotables" (réaction signaux prix) | Doc 6 |
| Décret thermostat pièce par pièce | Obligation à partir de **2027** | Doc 6 |

### 1.6 Multi-énergie & liens entre obligations

- **Vecteurs prioritaires** : électricité (Enedis Data Connect), gaz (factures + GRDF), chaleur/froid réseau (factures fournisseur), vapeur — doc 2.
- **BACS = levier Décret Tertiaire** : conformité BACS facilite atteinte −40 % via régulation chauffage, ECS, ventilation, éclairage — docs 4, 5.
- **OPERAT = source de vérité officielle** pour Tertiaire — connecteur API prioritaire P0 — doc 2.

---

## 2. KPI / unités / formules utiles

### 2.1 KPI Décret Tertiaire

| KPI | Unité | Formule | Période | Source canonique |
|---|---|---|---|---|
| % Réduction conso finale | % | `(1 − ConsoCorrigéeAnnéeN / ConsoCorrigéeAnnéeRef) × 100` | annuelle glissante | OPERAT + factures corrigées DJU |
| Conso finale climat-corrigée | kWh/an | `ConsoMesurée × Coeff_DJU_Admin` | annuelle | Factures + coefficients ADEME v2025 |
| Conso spécifique | kWh/m²/an | `ConsoFinale / Surface_Tertiaire_m²` | annuelle | OPERAT calcul auto |
| Écart à objectif 2030 | points % | `40 − %Réduction_Actuelle` | au 31/12/2030 | OPERAT attestation |
| Trajectoire projection 2030 | % | projection linéaire/exponentielle conso fin 2029 vs cible | annuelle | calcul SaaS depuis conso historique |
| Score Éco Énergie Tertiaire | A/B/C ou 0–100 | A si ≥ −40 %, B si −20 à −40 %, C si < −20 % | annuelle | OPERAT + scoring PROMEOS |
| Sites conformes portfolio | entier / % | `Σ sites (Réd% ≥ Cible) / Σ sites × 100` | annuelle | agrégation OPERAT |

### 2.2 KPI BACS

| KPI | Unité | Formule / définition | Période | Source |
|---|---|---|---|---|
| Statut GTB | Conforme / Non conforme / Exempté | Classe ≥ C + inspection à jour OU TRI > 10 ans documenté | continu | attestation intégrateur + rapport inspection |
| Classe GTB | A / B / C / D | NF EN ISO 52120-1:2022 par lot | à déploiement | certificat mise en service |
| Score BACS | 0–100 ou A–E | A=100, B=75, partiel=50, absent=0 | continu | calcul SaaS (configurable) |
| Puissance CVC couverte | kW ou % | `Σ puissance CVC sous GTB / Σ puissance CVC site` | continu | audit GTB + specs équipements |
| Mois avant prochaine inspection | entier | depuis date dernière inspection | continu | calcul SaaS |
| Fonctionnalités implémentées | count / 4 | mesure horaire · pilotage auto · détection dérives+alertes · interopérabilité | continu | rapport inspection + test système |
| ROI exemption 10 ans | bool + € | étude coût invest vs économies sur 10 ans | avant deadline | rapport étude interne |
| Gain énergie par défaut | kWh/an | `Génergie = G × (Σ Ci,j / 2)` G = 15 % ou audit | annuel | doc 5 |
| TRI BACS officiel | années | `TRI = S / (Σ Génergie × Cénergie)` arrondi sup | installation | doc 5 |

### 2.3 KPI APER

| KPI | Unité | Formule | Source |
|---|---|---|---|
| Couverture PV parking | % | `(Surface_Ombrières_PV / Surface_Parking_Total) × 100` | plans site + CIRE PV |
| Solarization gap | m² | `50 % × Surface_Parking − Surface_Ombrières_Installées` | suivi déploiement |
| Statut conformité APER | Conforme / En cours / Non-conforme / Exempté | par site assujetti | registre installations + dossier |
| Puissance PV installée | kWc | Σ puissance crête panneaux | CIRE Enedis |
| Production PV annuelle estimée | MWh/an | `kWc × rendement (~0,8) × insolation site` | étude PV ou PVGIS |
| Délai avant échéance | mois | calcul auto vs 01/07/2026 ou 01/07/2028 | calendrier |

### 2.4 KPI TURPE 7 (extrait — voir doc 3 pour valeurs complètes)

| Composante | Unité | Formule appliquée par PDL | Périodicité |
|---|---|---|---|
| **CG** Gestion | €/an/PDL | terme fixe selon segment et canal (CARD vs Contrat Unique) | annuelle |
| **CC** Comptage | €/an/PDL | terme fixe selon segment | mensuelle/bimestrielle |
| **CS** Soutirage HTA | €/kW + c€/kWh | `CS = b₁×P₁ + Σ bᵢ(Pᵢ−Pᵢ₋₁) + Σ cᵢ×Eᵢ` (5 plages) | mensuelle |
| **CS** Soutirage BT>36 | €/kVA + c€/kWh | idem 4 plages | mensuelle |
| **CMDPS** Dépassements HTA | €/mois | `CMDPS = Σ 0,04 × bᵢ × √Σ(ΔP²)` mesure 10 min | mensuelle |
| **CMDPS** Dépassements BT>36 | €/mois | `CMDPS = 12,41 × h` (heures dépassement) — plafonné si > 30 % facture | mensuelle |
| **CER** Énergie réactive HTA | c€/kVAr·h | si Qréactive > 40 % Eactive en HPH+HCH saison haute → 2,44 c€/kVAr·h | mensuelle HTA |
| **CER** BT > 36 | — | **= 0** depuis 1/8/2025 (supprimée) | — |
| **CACNC** non-communicant | €/bimestre | socle 6,48 + majoration 4,14 si relève > 12 mois | bimestrielle |
| **CACS** Alim. complémentaire | €/an | 4 045,96 €/cellule + 1 103,68 €/km liaison aérienne | annuelle |
| **CR** Regroupement | €/an | `L × k × Ps` k(aérien)=0,63 k(souterrain)=0,92 €/kW/km | annuelle |
| **CT** Transfo BT→HTA | €/an | `10,54 × Psouscrite_regroupée` | annuelle |

> **Note ACC** : les coefficients CSᴬᶜᶜ (autoproduite vs alloproduite) **EXCLURE ACC**. PROMEOS sans ACC = appliquer la grille standard.

### 2.5 KPI pilotage usages (advisory)

| KPI | Unité | Formule / source | Période |
|---|---|---|---|
| Talon nocturne | kW ou kWh | min(P) ou Σ conso 22h–05h hors fériés | mensuelle / annuelle |
| Conso WE / jours fériés | % conso totale | `(ConsoWE + ConsoFériés) / ConsoTotale × 100` | annuelle |
| Pics puissance inexpliqués | kW ou nombre | max(P) par plage anormale, comptage occurrences | mensuelle |
| Incohérence météo-conso | indice corrélation | `r = Corrélation(DJU, ConsoChauffage)` — attendu > 0,85 | mensuelle/saisonnière |
| Dérive saisonnière | % | `(ConsoHiverN − ConsoHiverN-1) / ConsoHiverN-1` après correction DJU | annuelle |
| Signature énergétique site | régression | modèle ML conso = f(météo, occupation, production) | continu |
| Indice perf. énergétique (IPE) | kWh/m²/an | conso / surface — référence sectorielle | annuelle |
| Pmax_observée vs Psouscrite | ratio | si < 0,7 sur 6 mois → opportunité réduction Psous | mensuelle |
| Énergie réactive HTA | c€/kVAr·h | si tg φ > 0,40 en HPH+HCH → facturation CER | mensuelle |
| Gain NEBCO estimé | €/an | `Δ(prix_SPOT_max−min_jour) × puissance_décalée × jours_activés` | quotidienne / annuelle |

### 2.6 KPI baromètre flex 2026 (valeurs marché)

| Métrique | 2025 | Cible 2030 |
|---|---|---|
| NEBCO sites tertiaires | 708 000 | n/a |
| NEBCO résidentiel | 600 000 | n/a |
| Clients HP/HC | ~14,5 M | maintenu |
| BACS installés | 32 000 | 100 000 |
| % BACS Flex Ready® | 0 | > 50 |
| Indice flex conso | 4 % | 18 % |
| Capacité chauffage déplaçable | 2,5 GW (cible) | 2,5 GW |
| Capacité ECS déplaçable | 3,3 GW | stable, évité 19 h |
| Capacité après-midi flex | — | 4,3–5 GW |
| Amplitude résiduelle système | ~14 GW | ~16,5 GW |
| EnR écrêté | ~3 TWh | s/o |

---

## 3. Idées pour Bill Intelligence

### 3.1 Audit TURPE 7 par PDL (cœur Bill Intelligence)

1. **Recalcul mensuel CG** = PDL × tarif segment (HTA / BT>36 / BT≤36) vs facture. Surfacturation si écart > 5 %.
2. **Recalcul mensuel CC** = PDL × tarif. Anomalie si CC manquant alors qu'attendu.
3. **Recalcul CS** complet = `b₁×P₁ + Σ bᵢ(Pᵢ−Pᵢ₋₁) + Σ cᵢ×Eᵢ` par FTA (CU / MU / LU / CU4 / MU4 / MUDT) — comparaison vs facture → détection écart €.
4. **CMDPS abusif** : flagger si CMDPS > 30 % facture ET > 25× Psupplémentaire non souscrite → demande plafonnement légal.
5. **CER non facturé (HTA)** : si Qréactive > seuil ET facture CER = 0 → perte € côté client à recouvrer.
6. **CER facturé BT > 36** : ne doit plus apparaître depuis 1/8/2025 — toute facturation post-pivot = anomalie.
7. **CACNC persistant** : BT ≤ 36 sans Linky après 2026 → surcoût 51,84 €/an + majoration.
8. **Mauvais segment tarifaire** : si Psouscrite > 36 kVA en BT ≤ 36 → migration BT > 36 attendue.
9. **Surdimensionnement Psouscrite** : si Pmax_observée < 0,7 × Psouscrite stable 6 mois → recommandation réduction.

### 3.2 Migration TURPE 6 → TURPE 7

- Date pivot : **1er août 2025** (codée dans `tarifs_reglementaires.yaml`).
- Fenêtre 6 mois (jusqu'au 31/01/2026) : clients HTA/BT autorisés à 1 changement FTA sans pénalité délai 12 mois — **opportunité audit**.
- Simulation coût 12 mois historique avec grille v6 puis v7 → présentation client "coût TURPE 6 vs TURPE 7" — écart attendu ~−1,92 %.
- Apurement CRCP (+7,7 % anticipé au 1/2/2025) à intégrer.

### 3.3 Comparateur multi-FTA

- Importer Psouscrite + E par plage 12 mois historique.
- Calculer coût annuel CS pour chaque FTA disponible selon segment.
- Ranking : FTA optimal = coût min + marge sécurité 10 %.
- KPI : "Opportunité optimisation FTA = Coût_actuel − Coût_optimal".

### 3.4 Anomalies multi-énergie (gaz, chaleur, vapeur)

- Cohérence conso facture vs conso GTB théorique (factures gaz vs relevé compteur gaz).
- Détection oublis énergie (ex. gaz absent malgré chauffage déclaré).
- Historisation 5 ans (obligation Tertiaire) = base audit anomalies rétroactives.

### 3.5 Shadow billing NEBCO

- Ligne distincte de la facture standard : gains marginal `Δ(prix_SPOT_max−min) × puissance_décalée × jours_activés`.
- Cadre rémunération : avec fournisseur HP/HC classique vs offre **bloc+SPOT** (nouveau 2025) vs primo-agrégateur PROMEOS.
- Inputs : signaux prix SPOT EPEX (J-1, intraday), barème TEMPO, TURPE 7 post-2027 nouvelle plage afternoon.

### 3.6 Connecteurs P0 facturation

- **OPERAT** : import attestation + export pré-déclaration.
- **Enedis Data Connect** : P par 1/2 h, index, données canon shadow billing.
- **Factures fournisseur** : parser PDF + mapping ligne → composante TURPE 7.
- **Vault preuves** : archivage 5 ans (obligation légale Tertiaire) + audit readiness.

### 3.7 Capacité, CSPE, VNU, ARENH→VNU, CBAM

- Intégration **mécanisme capacité 2026-2027** (RTE) dans le shadow billing — non détaillé dans les docs lus, à enrichir.
- **ARENH → VNU** (post-1/1/2026) : changement de méthode valorisation — à coder dans `market_tariff_loader.py`.
- CSPE / accise / TVA : doc 1 et 2 mentionnent contrôles cohérence facture vs réglementaire, à raccrocher à `regulatory_sources_loader.py`.

---

## 4. Idées pour pilotage des usages (mode advisory)

### 4.1 Détecteurs de dérives (cœur advisory)

| Détecteur | Règle | Action advisory |
|---|---|---|
| **Talon nocturne** | Conso 22h–05h > 15 % conso totale | Recommander arrêt GTB chauffage/ECS, extinction éclairage. Comparable : 8 %. |
| **Dérive WE / jours fériés** | ConsoWE / ConsoJourOuvré > seuil typique (70 % vs 40 %) | GTB dysfonctionnelle, oubli coupure. Reco : paramétrage fermeture WE. |
| **Surventilation WE** | UTA en mode actif samedi/dimanche | Activer mode éco WE → −5 % élec. |
| **Surpuissance instantanée** | Pics P sans corrélation usage déclaré | Équipement défaillant (moteur, pompe). Reco : diagnostic. |
| **Drift saisonnier** | ConsoHiverN > ConsoHiverN-1 à DJU comparable | Régulation dérivée, isolation dégradée. Reco : audit thermique. |
| **Incohérence météo-chauffage** | r(DJU, ConsoChauffage) < 0,70 | Thermostat bloqué. Reco : ajustement −1 °C à +2 °C selon occupation. |
| **Perte d'efficacité équipement** | Écart conso vs baseline signature | Audit, révision/remplacement. |
| **Capteur GTB silencieux** | Flux IoT absent > 6 h | Maintenance critique (critère C1 BACS). |
| **Énergie réactive > tg φ 0,40 (HTA)** | Facturation CER non nulle | Installation condensateurs (ROI). |
| **Pmax_observée < 0,7 × Psouscrite** | Stable 6 mois | Réduction Psouscrite progressive. |
| **HP coûteuses** | Conso HPH/HCH disproportionnée vs HC | Décalage HP → HC. Économie ratio ~2×. |

### 4.2 Signature énergétique multi-paramètres

- Modèle conso = f(DJU, occupation, production, jour de la semaine, signal saisonnier).
- Régression linéaire ou ML léger ; r² publié dans `KpiTile` (Doctrine §8).
- Détection alerte si Δ(conso_observée − conso_modélisée) > seuil σ.

### 4.3 Carpet plot (heatmap 24 h × N jours)

- Composant `CarpetPlot.jsx` déjà présent côté FE (228 LoC, palette septile P10→P95).
- Vu comme **différenciant marché** (vs Deepki, Metron, Advizeo).
- À promouvoir dans `MonitoringPage.jsx` + `Site360.jsx` + export PDF CFO.

### 4.4 Sous-systèmes CVC monitorés (BACS-compatible)

| Sous-système | Points mesure | KPI |
|---|---|---|
| Chauffage | départ eau chaude, T° ambiance par zone | kWh/m², °C moyen intérieur, gain attendu **5–15 %** (régulation 19 °C max) |
| Refroidissement | départ eau froide, T° ambiance | kWh/m², heures > 26 °C, gain **5–15 %** (consigne 26 °C min) |
| Ventilation | débit air neuf, T° soufflage, % récupération | kWh/m², renouvellement air/h, gain **15–25 %** (variateur + détection absence) |
| ECS | T° production, débit, perte réseau | kWh ECS/m², T° perte, gain **3–8 %** (réduction débits) ; **alerte légionelle T° retour < 50 °C** |
| Éclairage | détecteur présence, niveau éclairement | gain **10–30 %** (commande + absence) |
| Auxiliaires | besoins réels mesurés | gain **10–25 %** (modulation pompes/ventilateurs) |

### 4.5 Tableau de bord PROMEOS Centre d'Action (advisory)

```
🔥 CHAUFFAGE   kWh/mois vs budget · T° moyenne vs consigne · loi d'eau écart · heures arrêt vs occupation
❄️ FROID       kWh/mois vs budget · heures freecooling · T° départ vs cible · anomalie PAC
💨 VENTILATION kWh/mois par CTA · débit/min vs réglementaire · récupération chaleur · ΔP filtre (alerte encrassement)
🚰 ECS         kWh/mois vs historique · T° production vs 60°C · perte réseau · alerte légionelle T° retour
📊 GLOBAL      IPE kWh/m²/mois · écart cible Tertiaire −40 % · dépense €/mois · score BACS conformité
```

### 4.6 Catalogue leviers flex par typologie (baromètre 2026)

| Usage | Type flex | Puissance min | Secteur |
|---|---|---|---|
| Chauffage / climatisation | décalage régulier (programmation) | 1–10 kW | tous |
| ECS ballon | décalage régulier | 0,5–2 kW | résidentiel + tertiaire petit |
| Recharge VE | décalage dynamique NEBCO-compatible | 3–11 kW | résidentiel / entreprise |
| Ventilation / clim process | modulation dynamique | variable | tertiaire moyen / industrie |
| Froid commercial | stockage thermique | 5–50 kW | retail / restauration |
| Chauffage piscines | décalage régulier | 10–100 kW | tertiaire équipements |
| IT / clim serveurs | modulation dynamique | 10+ kW | tertiaire / data centers |
| Process industriel | dispatchable load | > 100 kW | industrie |

### 4.7 Signaux temporels à intégrer

- **TEMPO** : jours rouges (baisse 30–40 % HC), forecast + historique 1,2 M clients.
- **NEBCO** : signal quotidien, conditionné écart SPOT — opportunités après-midi notamment.
- **EcoWatt RTE** : alertes système 3–4 niveaux (à brancher côté backend si pas fait).
- **TURPE 7 post-2027** : nouvelle fenêtre HC après-midi mi-2027 → mi-2028.

---

## 5. Idées pour Centre d'Action

### 5.1 Briques sources alimentant le Centre d'Action

Déjà câblées côté backend (`action_hub_service.py`) :
- **Compliance** → ComplianceFinding (DT, BACS, APER, OPERAT, audit SMÉ)
- **Consumption** → ConsumptionInsight (dérives, talon, drift)
- **Billing** → BillingInsight (anomalies TURPE / CTA / VNU / accise)
- **Purchase** → contrats expirants + signaux prix

À ajouter (cf. P2 audit Sol2) :
- **Flex / EMS** → opportunities NEBCO, BACS Flex Ready®, signaux EcoWatt
- **Patrimoine** → APER ombrières, surfaces à couvrir, gap solarization

### 5.2 Catalogue actions concrètes par déclencheur

#### Conformité (P0 / P1)

| Action | Déclencheur | Evidence | Priorité |
|---|---|---|---|
| Déclarer OPERAT | déclaration non faite au 30/09 | NOR Décret 2019-771, screenshot pré-déclaration / déclaration | P0 |
| Élaborer plan actions 2030 | projection conso fin 2029 < −40 % | calcul SaaS trajectoire + données historiques 5 ans | P1 |
| Audit GTB urgent | < 3 mois avant 1/1/2025 + site > 290 kW sans GTB | NOR Décret 2020-887, certificat équipement | P0 |
| Étude TRI BACS | bâtiment 70–290 kW avant deadline 2030 | NOR Décret 2023-259, formule `TRI = S/(ΣG×C)` | P1 |
| Lancer étude ombrières PV | parking ≥ 10 k m² à 18 mois avant 01/07/2026 + < 30 % couvert | NOR Loi APER 2023, plans site, deadline | P0/P1 |
| Inspection BACS périodique | tous les 5 ans (2 ans après install) | rapport pro signé | P1 |
| Modulation Tertiaire | site avec contrainte technique/patrimoniale/économique | dossier technique avant 30/09/2026 | P1 |

#### Conso / Pilotage (P1 / P2)

| Action | Déclencheur | Gain estimé | Priorité |
|---|---|---|---|
| Arrêt GTB chauffage nuit | talon > 15 % | ~15 % chauffage | P1 |
| Coupure chauffage jour férié | conso férié > 60 % conso jour normal | variable | P1 |
| Paramétrage mode éco WE | surventilation WE | −5 % élec | P2 |
| Reparamétrage GTB consigne T° | surchauffe vs comparables | −8 % par °C | P2 |
| Audit thermique enveloppe | glissement +12 % vs DT | −18 % | P3 |
| Isolement équipement défaillant | pics P sans usage | variable | P1 |
| Optimiser loi d'eau (chaud + froid) | écart consigne/optimum | 1–2 % | P1 |
| Sous-comptage électrique CTA/VC/PAC | absence comptage granulaire | meilleure traçabilité | P1 |
| Réduction Psouscrite | Pmax < 0,7 × Psous stable | économie CS = b₁ × ΔP €/an | P1 |
| Compensation cos φ (HTA) | CER facturé > 0 | économie CER post-condensateurs | P2 |

#### Bill Intelligence (P0 / P1)

| Action | Déclencheur | Priorité |
|---|---|---|
| Corriger mauvais segment tarifaire | Psous > 36 kVA en BT ≤ 36 | P0 |
| Réclamer CMDPS abusif | CMDPS > 30 % facture ET > 25× ΔP non souscrit | P1 |
| Récupérer CER non facturé HTA | Qréactive > seuil et CER = 0 | P2 |
| Retirer CACNC | Linky déployé BT ≤ 36 | P2 |
| Migrer version tarifaire | coût alternatif < 0,95 × coût observé + écart > 500 €/an | P1 |
| Auditer factures TURPE 7 (en continu) | post-1/8/2025 | P0 |

#### Achat / Flex (P1 / P2)

| Action | Déclencheur | Gain advisory | Priorité |
|---|---|---|---|
| Site éligible NEBCO | P > 9 kVA + agrégateur RTE-accrédité contractualisable | 300–800 €/an/MW décalé | P1 |
| BACS Flex Ready® upgrade | bâtiment tertiaire > 100 m² sans GTB flex | payback 3–5 ans | P2 |
| Optimiser facturation capacité (TURPE 7) | client 9–36 kVA en vue HC journée 2027 | restructuration HP/HC | P2 |
| VE charging piloté | résidentiel/site avec VE | recharge créneau super-creux | P2 |
| Activer signal TEMPO | client résidentiel/petit tertiaire | économie HC jours rouges | P1 |

### 5.3 Mécaniques cardinales

- **Mode advisory strict** : PROMEOS recommande, n'exécute pas (cohérent doctrine 2026-05-22). Aucun appel API dispatch agrégateur sans consentement signé.
- **Evidence obligatoire** : pour toute action issue compliance, joindre NOR + date + URL JORF. Pour BACS/APER : étude TRI ou diagnostic Alter Watt-like. Pour flex : contrat agrégateur RTE accrédité.
- **Lifecycle** : OPEN → IN_PROGRESS → ON_HOLD → DONE → CLOSED (5 états ADR-028) avec closure_reasons (6 valeurs). Trace auditable via `ActionEvent`.
- **Impact unifié** : `gain_kwh` + `gain_eur` + `co2_avoided_kg` calculés **backend** (`impact_decision_service.py`).

### 5.4 Priorités issues du diag Air France

Roadmap type pour un site de ce profil (15 354 m², 4,5 GWh/an, 30,6 % réduction cible 2030) :

| Phase | Délai | Actions | Budget | Gain |
|---|---|---|---|---|
| 1 | T0–T1 mois | finaliser raccordements GTB, centraliser compteurs existants, abonnement plateforme 5 ans | < 5–8 k€ | conformité C1 |
| 2 | T2–T6 mois | sous-compteurs CTA/VC/PAC, optimisation loi d'eau, formation SPIE Energy Management | ~16 k€ | 3,8 k€/an |
| 3 | T12+ | étudier horloge ECS (sous réserve risque sanitaire légionelle) | ~3 k€ | marginal |

Total : ~26 k€, ROI ~7 ans, < 10 ans → respect exemption BACS.

---

## 6. Éléments à EXCLURE car ACC

### 6.1 Concepts ACC à écarter explicitement

| Concept | Présent dans | Décision PROMEOS |
|---|---|---|
| **Autoconsommation Collective (ACC)** entité réglementaire | doc 2 (section extension future), doc 3 (CG/CS spécifiques) | **EXCLURE ACC** — module ACC absent court terme |
| **PMO** (Personne Morale Organisatrice) | doc 2 | **EXCLURE ACC** — rôle `UserRole.PMO_ACC` à parker derrière feature flag |
| **Clé de répartition** statique/dynamique/sur-mesure | doc 2 | **EXCLURE ACC** |
| **Settlement local** ACC | doc 2 | **EXCLURE ACC** |
| **Participants ACC** (producteur/consommateur) | doc 2 | **EXCLURE ACC** |
| **Contrat ACC multi-participants** | doc 2 | **EXCLURE ACC** |
| **Registre CRC Enedis** ACC | doc 2 | **EXCLURE ACC** |
| **Mutualisation clé répartition entre parkings ACC** | doc 2 | **EXCLURE ACC** (mutualisation Tertiaire intra-EJ ≠ ACC, à conserver) |
| **Flex score ACC** | doc 2 | **EXCLURE ACC** |
| **Communautés énergétiques locales** | doc 2 | **EXCLURE ACC** (perspective long terme post-2030) |
| **CG ACC collective HTA** (628,33 € CARD / 564,24 € CU) | doc 3 | **EXCLURE ACC** — ne pas auditer ce tarif |
| **CG ACC collective BT > 36** (314,17 / 282,12) | doc 3 | **EXCLURE ACC** |
| **CG ACC collective BT ≤ 36** (22,53 / 21,27) | doc 3 | **EXCLURE ACC** |
| **CS ACC part autoproduite / alloproduite BT > 36 (CU/LU)** | doc 3 | **EXCLURE ACC** |
| **CS ACC part autoproduite / alloproduite BT ≤ 36 (CU4/MU4)** | doc 3 | **EXCLURE ACC** |

### 6.2 Concepts proches à NE PAS confondre avec ACC

| Concept | Statut PROMEOS | Justification |
|---|---|---|
| **Autoconsommation INDIVIDUELLE** (panneaux PV consommés sur place sans partage) | ✅ IN scope — tarification standard, suivi taux d'autoconsommation site | Pas de répartition collective |
| **Mutualisation Décret Tertiaire** (compensation entre sites du même EJ) | ✅ IN scope — agrégation portefeuille OPERAT | Cadre intra-entité juridique, pas un partage d'énergie ACC |
| **Mutualisation APER parkings adjacents** (même propriétaire) | ✅ IN scope — accord propriétaire | Pas de partage entre participants ACC |
| **Réseau de chaleur urbain** (sous-station gestionnaire) | ✅ IN scope (multi-énergie) | Pas une opération ACC |
| **Production électricité site** (BACS R.175-3) | ✅ IN scope monitoring | Production locale individuelle, pas ACC |
| **NEBCO** (effacement / décalage) | ✅ IN scope advisory | Mécanisme RTE, indépendant ACC |
| **Capacité PV individuelle** | ✅ IN scope | Si pas de partage, pas ACC |
| **Flex Ready® BACS** | ✅ IN scope | Réactivité site individuel signaux marché |

### 6.3 Verdict transversal des 6 docs

| Doc | Présence ACC | Action |
|---|---|---|
| Doc 1 — Brique 1 | aucune mention explicite | rien à exclure |
| Doc 2 — Analyse experte | section "extension future ACC" (lignes 909–935) avec PMO, clé répartition | **EXCLURE** la section extension, garder le reste |
| Doc 3 — TURPE 7 | tarifs ACC collective explicites dans CG + CS | **EXCLURE** ces tarifs du pipeline shadow billing standard |
| Doc 4 — Air France BACS | aucune mention ACC | rien à exclure |
| Doc 5 — Guide BACS 2026 | absence ACC confirmée (BACS = bâtiment individuel) | rien à exclure |
| Doc 6 — Baromètre flex | aucune mention ACC (NEBCO/NEBEF pur) | rien à exclure |

**Conclusion** : seuls les docs 2 et 3 contiennent du contenu ACC à écarter. Dans tous les autres docs, l'ACC n'apparaît pas — extraction directe sans filtre additionnel nécessaire.

---

## 7. P0 / P1 / P2 de mise à jour produit-tech

### 7.1 P0 — Bloquant avant pilote payant

| # | Item | Cible technique | Source doc | Effort |
|---|---|---|---|---|
| P0-1 | **MAJ `config/tarifs_reglementaires.yaml` TURPE 7 complet** : 4 segments × 10 FTA × plages, dates 1/8/2025, apurement CRCP 1/2/2025 +7,7 %, CER BT > 36 = 0 | YAML + source-guard | doc 3 | 3–5 j-h |
| P0-2 | **MAJ shadow billing TURPE 7** : nouvelles formules CS (5 plages HTA, 4 plages BT), CMDPS (√Σ(ΔP²) HTA vs 12,41×h BT), CER conditionnel HTA, CACNC bimestriel BT ≤ 36 | `billing_canonical_service.py` + tests | doc 3 | 5–7 j-h |
| P0-3 | **Confirmer `bacs_regulatory_engine.py`** : seuils 290 kW (2025) et 70 kW (2030), dates 2020-887 + 2023-259, formule TRI officielle `S/(ΣG×C)`, exemption < 5 % conso, classes A/B/C/D ISO 52120-1, 7 lots | service + tests | docs 4, 5 | 3–4 j-h |
| P0-4 | **Connecteur OPERAT API** : import attestation + export pré-déclaration, calendrier 30/09, climat correction DJU ADEME v2025 | nouveau service `operat_connector.py` | doc 2 | 5–7 j-h |
| P0-5 | **Connecteur Enedis Data Connect** déjà partiel — confirmer P par 1/2 h granularité, index, ACL OAuth2 | `enedis_route.py` | doc 2 | 2–3 j-h (vérification) |
| P0-6 | **Confirmer mode ADVISORY ONLY pour Flex/NEBCO** : aucun appel dispatch agrégateur sans consentement client, log audit CRE/RTE prêt | `flex_nebco_service.py` + source-guard | doc 6 | 2–3 j-h |
| P0-7 | **Vault preuves NOR + date + URL** : intégration `Evidence` model (déjà ADR-029) avec MIME validation libmagic, rétention 5 ans Tertiaire | déjà en place — vérifier complétude | docs 2, 4 | 1–2 j-h |
| P0-8 | **Parking ACC** : feature flag `ENABLE_ACC_ROLE=false`, glossaire FE conditionné, KB `docs/kb/items/acc/` non exposée produit | flag + UI conditionnelle | docs 2, 3 | 2–3 j-h |
| P0-9 | **Migration TURPE 6 → 7 et fenêtre changement FTA** : audit jusqu'au 31/01/2026 sans pénalité 12 mois | `purchase_actions_engine.py` | doc 3 | 3–5 j-h |
| P0-10 | **Moteur détection dérives** : talon nocturne, dérive WE, surpuissance, incohérence météo-conso, drift saisonnier — exposés via `ConsumptionInsight` → action_hub | `consumption_diagnostic.py` + détecteurs | docs 1, 2 | 5–7 j-h |

**Total P0 estimé : ~31–46 j-h.**

### 7.2 P1 — Crédibilité avant scale-up

| # | Item | Cible | Source | Effort |
|---|---|---|---|---|
| P1-1 | Comparateur TURPE 6 vs 7 sur 12 mois historique + ranking FTA optimal | `purchase_strategy.py` + UI tab Achat | doc 3 | 5–7 j-h |
| P1-2 | Règles détection anomalies TURPE 7 : CMDPS abusif, CER non facturé HTA, segment incorrect, CACNC persistant, Psouscrite surdimensionnée | `bill_intelligence` règles R20+ | doc 3 | 5–7 j-h |
| P1-3 | Calcul trajectoire Décret Tertiaire (projection 2030, score A/B/C, gap to target) | `tertiaire_modulation_service.py` enrichi | docs 1, 2 | 3–5 j-h |
| P1-4 | Solarization gap APER : surface m² manquante, ROI ombrières, alerte délai amende 40 k€ / 20 k€ | `aper_service.py` + UI | doc 2 | 3–5 j-h |
| P1-5 | Checklist diagnostic BACS exposable (7 critères + 7 lots) inspiré méthodo Alter Watt | UI conformité + service | doc 4 | 3–5 j-h |
| P1-6 | Modèle calcul TRI BACS avec paramètres réels (I, A, G, C, S) + 2 devis import | `bacs_regulatory_engine.py` + UI | doc 5 | 3–5 j-h |
| P1-7 | Inspection BACS workflow : rappels 5 ans (2 ans après install), audit trail rapports pro | `bacs_alerts.py` | doc 5 | 2–3 j-h |
| P1-8 | Connecteur GTB générique (Niagara / BACnet / Modbus TCP / LonWorks via passerelle) | nouveau service `gtb_connector.py` | doc 4 | 8–12 j-h |
| P1-9 | Modèle shadow billing NEBCO distinct (ligne séparée) : Δ(prix SPOT) × P × jours | `billing_shadow_v2.py` extension | doc 6 | 3–5 j-h |
| P1-10 | Signaux EcoWatt RTE + TEMPO historique + forecast intégrés dans détecteurs flex | `flex_opportunity_detector.py` enrichi | doc 6 | 3–5 j-h |
| P1-11 | Traçabilité NEBCO/CRE/RTE par site : `agregateur_id`, `nb_activations_YTD`, `gains_YTD`, conformité TURPE 2027 | enrichir payload `/api/flex/*` | doc 6 | 2–3 j-h |
| P1-12 | KPI registry frontend (miroir `backend/doctrine/kpi_registry.py`) + source-guard FE | `frontend/src/doctrine/kpiRegistry.js` | doc 2 | 3–5 j-h |
| P1-13 | Moteur recommandations sobriété (playbooks) : chauffage 19 °C, ventilation WE, ECS, éclairage LED | `recommendation_engine.py` extension | docs 2, 4 | 5–7 j-h |
| P1-14 | Décret thermostat pièce par pièce (2027) — anticiper modèle données zone × consigne | modèle `Zone` + UI | doc 6 | 3–5 j-h |
| P1-15 | Multi-énergie (gaz, chaleur/froid réseau) : import factures + parsing, agrégation portefeuille | nouveau `gas_invoice_parser.py` + `heat_network_service.py` | docs 2, 4 | 8–12 j-h |

**Total P1 estimé : ~60–90 j-h.**

### 7.3 P2 — Différenciation world-class

| # | Item | Cible | Source | Effort |
|---|---|---|---|---|
| P2-1 | Promouvoir `CarpetPlot.jsx` (déjà 228 LoC) dans `MonitoringPage` + `Site360` + export PDF CFO | UI + service export | docs 1, 2 | 3–5 j-h |
| P2-2 | Moteur CUSUM (control chart cumulatif ISO 50001) | nouveau `cusum_service.py` | docs 1, 2 | 5–8 j-h |
| P2-3 | M&V IPMVP options B/C/D (Mesure & Vérification formelle) | enrichir `baseline_service.py` | doc 2 | 8–12 j-h |
| P2-4 | Forecasting probabiliste (Monte-Carlo volatilité SPOT 12–24 mois ahead) + valeur espérance gains NEBCO | nouveau `flex_forecast_service.py` | doc 6 | 8–12 j-h |
| P2-5 | TURPE 7 post-2027 simulateur tarifs (HC nuit + HC jour 2027–2028) | `purchase_strategy.py` extension | doc 6 | 5–8 j-h |
| P2-6 | Pilier Flex / EMS alimentation Centre d'Action (`build_actions_from_flex`) | `action_hub_service.py` + détecteur | doc 6 + audit Sol2 | 3–5 j-h |
| P2-7 | Module recommandation classe BACS cible (A/B vs C) selon typologie + ROI | `recommendation_engine.py` extension | doc 4 | 5–8 j-h |
| P2-8 | Veille réglementaire automatique (CRE / RTE / JORF) | nouveau `regulatory_watcher_service.py` | doc 2 | 8–12 j-h |
| P2-9 | Géo-cartographie potentiel PV (imagerie aérienne + cadastre) pour APER | nouveau service + intégration plans | doc 2 | 12–20 j-h |
| P2-10 | Forecasting saisonnier signature énergétique (méthodo Endesa Griffine 13 étapes) | `consumption_diagnostic.py` extension | docs 1, 2 + memory | 8–12 j-h |
| P2-11 | Intégration CSRD post-Omnibus / BEGES scope 1-2-3 | nouveau pilier reporting | doc 2 | 12–20 j-h |
| P2-12 | Primo-agrégateur — modèle commercial revenue-share % gains NEBCO | doctrine produit + ADR | doc 6 | 3–5 j-h (analyse) |
| P2-13 | ACC extension (clés répartition, PMO interface) — **uniquement si demande client explicite post-pilote** | nouveau pilier (Mois 6+) | docs 2, 3 | hors scope MVP |

**Total P2 estimé : ~80–130 j-h.**

### 7.4 Cumul effort

| Phase | Effort min | Effort max | Bloquant pilote ? |
|---|---|---|---|
| P0 | 31 j-h | 46 j-h | **Oui** |
| P1 | 60 j-h | 90 j-h | Non — crédibilité scale-up |
| P2 | 80 j-h | 130 j-h | Non — différenciation |
| **Total** | **171 j-h** | **266 j-h** | — |

À pondérer avec les 17–27 j-h du plan §13 de l'audit READ-ONLY `audit_readonly_promeos_scope_sans_acc_usage_steering.md` (recouvrement partiel sur P0-8 parking ACC).

---

## Synthèse cardinale

1. **Cadre réglementaire** : 5 textes-piliers — DT 2019-771, BACS 2020-887 + 2023-259, APER 2023-175, TURPE 7 délibération CRE 2025-78, NEBCO 1/9/2025 — tous traçables en NOR + date + URL JORF.
2. **TURPE 7 = chantier P0** : 4 segments × 10 FTA, plages HTA/BT, CER supprimée BT > 36, CACNC à retirer post-Linky, fenêtre changement FTA jusqu'au 31/01/2026.
3. **BACS = chantier P0** : seuils 290 → 70 kW, formule TRI officielle `S/(ΣG×C)`, classes A/B/C/D ISO 52120-1, 7 lots, exemption < 5 % conso, ECS souvent classe D (risque légionelle si forcer C).
4. **Pilotage advisory** : talon, dérive WE, surpuissance, drift saisonnier, signature, CUSUM (P2), carpet plot (P2 promotion). Mode advisory strict — PROMEOS conseille, n'exécute pas.
5. **Centre d'Action** : 4 briques opérationnelles (compliance / consumption / billing / purchase) + 2 à ajouter (flex P2, patrimoine APER P1). Evidence NOR + date + URL.
6. **ACC** : 0 module à coder. Seules les sections "extension future" du doc 2 et les CG/CS ACC du doc 3 sont à exclure. Tous les autres docs (BACS, baromètre flex) sont scope IN pur.
7. **Effort total P0 ≈ 31–46 j-h** pour passer la doctrine v1.3 à 100 % alignée sur les 6 docs Drive.

---

**Fin de l'audit** — sources Drive `1UJOz…`, `1yZLK…`, `1z9hL…`, `1KkYb…`, `1KioI…`, `1_faW…`.
Branche cible : `claude/refonte-sol2`.
Rapport prêt à être versionné dans `docs/audits/audit_docs_drive_promeos_sans_acc.md`.
