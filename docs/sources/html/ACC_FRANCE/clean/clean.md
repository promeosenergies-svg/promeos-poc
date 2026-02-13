Autoconsommation Collective en France 

# 

# Autoconsommation Collective en France 2025 – État, Leviers, Croissance et Intégration PROMEOS 

## Executive Summary 

L’ autoconsommation collective (ACC) est en phase de transformation structurelle en France fin 2025. Passée de 77 opérations en 2021 à ~900+ en juin 2025 (110+ MWc), elle bénéficie d’un cadre réglementaire enfin matérisant : l’arrêté du 21 février 2025 a porté le seuil de puissance de 3 à 5 MW (10 MW pour les collectivités), le TURPE 7 a simplifié la tarification depuis août 2025, et l’accise est passée à 0€/MWh. Ces trois pivots réglementaires déverrouillent une croissance exponentielle 2026–2030 : scénario central projette 6 000 opérations et 900 MWc (vs prudent : 2 700 opérations, 380 MWc; accéléré : 10 500 opérations, 1 400 MWc). 

Pour PROMEOS, l’ intégration d’une brique ACC transforme le positionnement en « micro-fournisseur local (2.0) + cockpit settlement + flexibilité » – un différentiel majeur face aux agrégateurs classiques et fournisseurs haut-débit. Le time-to-market clé : réduire le cycle projet de 12–24 mois actuels à 3–6 mois via standardisation juridique, APIs DataHub/DataConnect, shadow billing, et KYC automatisé. Trois packages : ACC Starter (diagnostic+kit PMO), ACC Ops (data+clés+facturation), ACC Optim (flex+prix+arbitrage) , portés par une roadmap MVP 90j (MVP 1.0), puis v1 à 180j, v2 à 12m . 

Les 10 leviers critiques pour croissance 2025–2030 sont : (1) seuil 5MW, (2) TURPE 7 option ACC, (3) DataHub/API, (4) standardisation PMO, (5) shadow billing, (6) tarification dynamique, (7) flex implicite/IRVE, (8) agrégation multi-sites, (9) primes investissement, (10) exemption d’accise 1MW. Les 10 irritants majeurs et solutions SaaS sont cartographiés fin de rapport. 

Sources principales : Legifrance, CRE délibérations 2024–2025, Enedis conventions, ADEME, RTE, Enogrid (370+ projets), Livre Blanc ACC 2024, DataHub-Enedis API, études SER/FNCCR. Dernière mise à jour : décembre 2025; horizons : données 2024-Q4 à 2025-Q2 consolidées . 

## A. Cadre Réglementaire ACC 2025 : Définitions, Rôles, Obligations & Évolutions 

### 1. Définitions & Architecture Légale 

L’ autoconsommation collective (article L315-2, Code de l’énergie) est définie comme : « opération permettant à un ou plusieurs producteurs et un ou plusieurs consommateurs finals de partager localement l’électricité produite, au sein d’une personne morale organisatrice (PMO) ». 1 2 3 

Deux périmètres coexistent : 4 5 6 Élément ACC Simple (même bâtiment) ACC Étendue (multi-sites) Critère géographique Points injection/soutirage au « même bâtiment » Distance max. 2 km (baseline); 20 km possible sur dérogation Puissance cumulée 3 MW (baseline historique) 5 MW (depuis 6 mars 2025) ; 10 MW dérogation collectivités Réglementation L315-2 Code énergie Arrêté 21 nov. 2019 + modifié 21 fév. 2025 Participants Illimité (producteurs + consommateurs) Idem Cas d’usage Copropriétés, bailleur monolithe Parcs activités, quartiers, multi-communes Obligation PMO Oui, obligatoire Oui, toujours obligatoire (sauf exc. bailleur social) 

Arrêté pivot du 21 février 2025 (publié JO 5 mars 2025) : 7 8 9 10 
- ✅ Augmentation 3 MW → 5 MW pour ACC étendue métropole continentale 
- ✅ Dérogation 10 MW pour communes/EPCI à fiscalité propre (si tous acteurs = mission service public ou SEM locales) 
- ⚠️ CRE avait préconisé 8 MW , mais gouvernement a retenu 10 MW → crédibilité politique signale engagement fort ACC 

### 2. Rôles, Responsabilités & Acteurs Clés 

### Personne Morale Organisatrice (PMO) 11 12 13 

Définition & mission obligatoires : 
- Entité juridique regroupant producteurs + consommateurs 
- Responsable unique vis-à-vis d’Enedis/GRD pour : 
- Signature convention ACC avec GRD 
- Définition clés de répartition (statique/dynamique simple/dynamique full) 
- Gestion entrées/sorties participants 
- Transmission données CRE (annuellement) 
- Maintien registre transparent participants 

Formes juridiques possibles : 14 
- Association loi 1901 (simplest, 60% réalité) 
- SARL / SAS (si financement tiers ou service payant) 
- SEM (communes/collectivités) 
- Exception bailleurs sociaux : peuvent être PMO seuls (sans création structure supplémentaire) 15 

Coûts estimés PMO (2024–2025) : 16 17 
- Création structure : €0–2 000 (assoc.) vs €1 000–5 000 (SAS/SARL) 
- Gestion opérationnelle : €500–2 000/an (petit projet) à €3 000–10 000/an (multi-sites) 
- Enjeu clé : absence standardisation = chaque PMO réinvente la roue 

### Gestionnaire Réseau Distribution (Enedis, ELD) 18 19 20 

Responsabilités opérationnelles : 
- Relever courbes conso/production (P30 = 30 min.) 
- Calculer TAc (part autoconsommée) / TAp (part alloconsommée) mensuellement 
- Transmettre données à fournisseur de complément & producteur 
- Notifier changements clés répartition à PMO (4j ouvrés) 
- Assurer conformité technique/réglementaire 

Contrat ACC obligatoire avec chaque opération : durée usuelle 3–5 ans, renouvelable. 

### Fournisseur de Complément (électricité alloconsommée) 21 22 
- Client conserve liberté choix fournisseur 
- Reçoit de Enedis données TAp (part fournie par lui) chaque mois 
- Facture = TAp × prix client-PMO + TURPE + taxes 
- TURPE 7 option ACC (depuis août 2025) : majoration fixe « gestion » mais rabais possible si taux autocons. élevé 

### Producteur (PV local) 23 24 25 
- Vend électricité ACc à PMO/consommateurs via contrat libre (prix négocié) 
- Perd rigidité tarif achat garanti (obligation achat) → risque prix négatif croissant 
- Surplus injecté = part non-ACc → marché spot ou contrat fournisseur 
- Opportunité : flexibilité implicite (réduction volontaire injection lors prix négatifs) 

### 3. Clés de Répartition : Mécanique Opérationnelle Clé 26 27 28 

Enedis propose 4 modalités (choisies par PMO, modifiables mensuellement sur préavis 4j) : Clé Fonctionnement Complexité Équité Cas d’usage Statique % fixes prédéfinis (ex: consomm. 25%, 35%, 40%) Basse Moyenne (inflexible) Petit collectif stable Dynamique par défaut Enedis calcule TAc prorata consommation réelle P30 Moyenne Haute Standard ACC Dynamique Simple PMO calcule % selon ses critères (ex: priorité charges communes) Haute Flexible Bailleurs sociaux Dynamique Full PMO optimise 15-min à 15-min selon production/conso temps réel Très haute Maximum ZAC multi-usages, tertiaire 

Irritant majeur identifié : 29 30 31 
- PMO doit changer clés manuellement chaque mois → lourdeur admin 
- Feedback terrain : 15–30h/mois pour PMO small-medium 
- Solution SaaS PROMEOS : calcul auto + simulation + envoi Enedis 1-click 

### 4. Cadre Contractuel : Convention Enedis & Obligations Spécifiques 32 33 34 

Convention ACC (1 par opération) doit préciser : 
- Identité PMO, producteurs, consommateurs, coordonnées bancaires 
- Localisation injection/soutirage, PRM identifiants 
- Clé de répartition choisie + modalités modification 
- Responsabilité d’équilibre (qui = fournisseur complément) 
- Durée, conditions résiliation 

Prérequis avant signature avec Enedis : 35 
- Tous participants équipés Linky (obligatoire pour ACC) 
- Consentement écrit conso/producteur (RGPD courbes charge) 
- CAE (Contrat Accès Exploitation) producteur déjà en place 
- PMO prouve en capacité (statuts, trésorerie, mandat direction) 

Délais typiques : 36 37 
- Instruction Enedis : 5 jours ouvrés (notification date démarrage) 
- Raccordement « simple » : 2 mois 
- Raccordement « complexe » (HTA, travaux réseau) : 12–18 mois 

### 5. Conformité & Risques : Exigences Type-Fournisseur 38 39 40 

Point critique : responsabilités ne sont pas du type « licence fourniture » au sens strict (PMO ≠ fournisseur légal). Mais obligations ressemblent à gestion d’équilibriste : 41 Obligation Acteur resp. Pénalité non-respect Automatisation possible? Transmission clés répartition à Enedis (4j max.) PMO Retard facturation, litiges participants ✅ Oui (API Enedis) Gestion entrées/sorties (préavis, rééquilibre) PMO Erreurs TAc/TAp, facturation incorrecte ✅ Oui (registre digital) Collecte consentement RGPD courbes PMO Amende CNIL (€500–€50k) ✅ Oui (e-signature) Facturation consommateurs ACC correcte PMO ou fournisseur Litiges, rupture contrat ✅ Oui (shadow billing) Réconciliation mensuelle Enedis/fournisseur Fournisseur + Enedis Divergence facturation ✅ Partiellement (API) Raportage CRE annuel (opérations, puissance,…) PMO Avertissement CRE (rare) ✅ Oui (automation) Prévention fraude, audit trail PMO + Enedis Possibilité révocation ACC ✅ Oui (blockchain possible, logs) 

“Painful point” le plus fréquemment cité : pas d’exigence d’autorisation-fournisseur explicite , mais si PMO facture ACC à consommateurs, elle doit être “prestataire de services responsable” (droit commercial) → assurance RC professionnelle requise + conformité droit consommateur (délai rétractation, facturation claire, etc.). 

### Pistes de simplification 2026–2030 (données SER/ADEME/CRE): 42 43 
- Standardisation modèle convention : un template unique Enedis + guide PMO 
- API DataHub/DataConnect : transmission auto. clés et données 
- Exemption reporting manuel : auto-reporting via plateforme SaaS 
- E-signature template : consentement RGPD pré-rempli 
- Responsabilité partagée clarifiée : fiche « qui fait quoi » 1 page 

### 6. Impacts Réglementaires Récents & Horizons 2026+ 

### TURPE 7 (1er août 2025) 44 45 
- Nouvelle tarification d’acheminement Enedis 
- Option ACC : majoration fixe (€/an) compensée par rabais possible si taux d’autocons. > seuil 
- Pour PROMEOS : impact : clients doivent calculer « coût TURPE net » → intégrer dans pricing 
- Calendrier : révision tous 4 ans → prochain 2029 

### Arrêté Accise (1er mars 2025) 46 47 
- Installations ≤ 1 MWc : exonération accise à 0 €/MWh (vs 30–40 €/MWh avant) 
- ≥ 1 MWc : tarif normal applicable 
- Impact : redynamise petit/moyen collectif, zones rurales 

### BACS (depuis 1er janvier 2025) 48 
- Obligation d’automatisation bâtiments ≥ 290 kW (2027 : ≥ 70 kW) 
- Pour ACC tertiaire : système de contrôle automatisé quasi-obligatoire → intégration SaaS EMS + ACC 

### Agenda non-certains (lobbying FNCCR/SER) : 49 
- ⚠️ Assouplissement critère distance (de 2 km → 5–20 km régulier) : demande en cours, réponse 2026? 
- ⚠️ Intégration communautés d’énergie (RED directive UE) : transposition France 2026? 
- ⚠️ Tarification TURPE 8 (post-2029) : inclure signal flex/prix négatif? 

## B. Marché ACC 2025 : Taille, Dynamique, Segments, Économie 

### 1. Chiffres Clés & Dynamique 2021–2025 

Trajectoire observée : 50 51 52 53 54 Période Opérations actives Puissance (MWc) Compteurs Croissance YoY 2021-Q4 77 ~2.4 N/A – 2022-Q4 ~140 ~6.5 ~1,500 +82% ops 2023-Q4 ~300 ~15 ~4,500 +114% ops 2024-Q2 ~500 ~50 ~7,000 (trending) 2024-Q4 698 73.6 8,342 + 233% ops (3 ans) 2025-Q2 ~900+ ~110 ~12,000 +40% ops (à l’année) 

Observations : 
- Croissance exponentielle pré-2025 : règle de 70 → doublement ~2.5 ans 
- Accélération visuelle 2024–2025 : arrêté février a déclenché > 200 projets nouveaux en pipeline pré-automne 2025 
- Ratio PRM/operation : moy. ~11–14 compteurs/projet (bailleurs sociaux : 50–200; ZAC : 20–50) 

### 2. Segmentation Typologies & Cas d’Usage 55 56 57 58 

### A. Bailleurs Sociaux (40–45% du marché 2025) 59 60 

Cas type : Immeuble collectif HLM 100+ logements + toit PV 50–150 kWc 

Modèle opérationnel : 
- PMO = bailleur lui-même (exception légale, bailleurs sociaux) 
- Électricité produite → priorité charges communes (ascenseurs, couloirs, eau chaude) 
- Surplus → participants logements (consentants parmi locataires) 
- Bénéfice : réduction charges communes ~15–25%/an, lutte précarité énergétique 

ROI économique : 61 62 
- Investissement CAPEX : ~€80–120k pour 50 kWc (aides CRE/régionales : €20–40k) 
- Économies annuelles : €12–18k (conso communes + survalue locataires) 
- Payback : 5–8 ans (avec aides); 10–12 ans (sans) 
- Sensibilité : très bonne si > 30% taux autocons. 

Cas clients réels : 
- Habitat 17 (78m² PV, 78 logements) 
- Habitat Hauts-de-France (exploitée via Enogrid) 
- RIVP Nord (Paris, multi-sites) 

### B. Collectivités Territoriales & Parcs Activités (30–35%) 63 64 

Cas type 1 : ZAC/parc activités 
- Producteur = entité municipale ou SEM 
- Consommateurs = 5–15 entreprises petit/moyen (manufactures, commerces, services) 
- Modèle = vente AC à prix « local » (€0.12–0.18/kWh vs marché €0.20+) 
- Complexité : clés dynamiques, entrées/sorties entreprises, multi-secteurs consommation 

Cas type 2 : Patrimoine public mutualisé 
- Mairie + écoles + médiathèque + piscine = PMO 
- Autocons. simple (même commune), clés statiques par bâtiment 
- Avantage : aucun participant privé, gouvernance simple 
- Baisse consommation électricité : 12–20%/an 

Cas clients : Communes Occitanie/Bretagne (données SER 2024), collectivités Normandie (FNCCR accompagnement) 

### C. Tertiaire Multi-Sites & Entreprises Privées (15–20%) 65 66 

Cas type : Groupe immobilier/retail > 3 sites dans même commune 
- Production : toitures sites A/B + ombrières parking C 
- Consommateurs : bureaux, stockages, charges communes 
- Besoin clé : flex implicite (modulation conso lors pics PV) 
- Pénalité : prix négatifs (récurrent 2025+) = perte €/MWh pour producteur → nécessite contrat « prix minimum » ou pilotage actif 

Sens économique : 
- Sans ACC : marché spot ~€55–65/MWh (2025) avec risque négatif 
- Avec ACC : €0.15–0.18/kWh (localisé) → economie 20–35% vs marché spot 
- Caveat : nécessite synchronisation conso/production (~50% taux ok; >70% = très bon) 

### D. Copropriétés Résidentielles (5–10%, en croissance) 67 68 

Cas type : Immeuble 50–100 lgt privés, assemblée générale vote ACC 

Modèle : 
- PMO = syndic ou association AC dédiée 
- PV toiture (~30 kWc typique) 
- Participants = consentants seulement (pas obligation) 

Défis majeurs : 
- Vote majorité simple (art. 25 loi 1965) exige concertation 
- Taux participation : moy. 40–60% (vs 95% bailleurs) 
- Litiges : facturation, charge commune vs privative 
- Fatigue démocratique : renouvellement AC chaque an coûteux administrativement 

ROI moins attractif : payback 10–15 ans → frilosité acheteurs énergies renouvelables classe moyenne 

### 3. Unit Economics Synthétisé (données terrain Enogrid, Animergy, HubWatt) 69 70 71 72 

### Scénario A : Bailleur Social 50 kWc / 100 participants INVESTISSEMENT (CAPEX)
├─ Installation PV (50 kWc) : €50,000
├─ Électronique (onduleur, monitoring) : €5,000
├─ Raccordement Enedis : €3,000
├─ PMO setup (statuts, registre) : €1,500
└─ Total CAPEX : €59,500

REVENUS ANNUELS (année 1)
├─ Production brute : 50 × 0.9 × 1,000h = 45 MWh/an (facteur charge 18%)
├─ Taux autocons. estimé : 55%
├─ TAc = 45 × 55% = 24.75 MWh/an @ €0.18/kWh (prix convenu) : €4,455
├─ Surplus vendu (marché spot, 45% produit) : 20.25 MWh @ €60/MWh : €1,215
├─ Prime investissement (CRE 2025) : €0–2,000 (dégression)
└─ Autres aides (région) : €4,000–8,000 (premier an)

COÛTS OPÉRATIONNELS ANNUELS (OpEx)
├─ Assurance RC/équipement : €300
├─ Maintenance & nettoyage : €400
├─ PMO gestion (estimé sans SaaS) : €2,000–3,000
├─ Frais bancaires/comptabilité : €200
└─ Total OpEx : €2,900–3,600

RÉSULTAT NET ANNUEL (année 1 avec aides)
└─ €4,455 (TAc) + €1,215 (surplus) + €5,000 (aides) – €3,300 (OpEx) = **€7,370/an**

PAYBACK SIMPLE (sans aides 2026+)
└─ (€59,500 – aides) / €5,670 (révenu annuel stabilisé) = **7–9 ans** 

### Scénario B : ZAC Activités 200 kWc / 12 entreprises INVESTISSEMENT (CAPEX)
├─ Installation PV (200 kWc) : €180,000
├─ Onduleurs + monitoring avancé (temps réel) : €18,000
├─ Raccordement HTA Enedis : €12,000
├─ PMO (SAS dédiée, légal/gouvernance) : €5,000
├─ Plateforme gestion clés (estimation) : €3,000
└─ Total CAPEX : €218,000

REVENUS ANNUELS (année 1)
├─ Production brute : 200 × 0.85 × 1,100h = 187 MWh/an
├─ Taux autocons. estimé (petits tertiaires) : 60%
├─ TAc = 187 × 60% = 112.2 MWh @ €0.165/kWh : €18,513
├─ Surplus vendu (marché) : 74.8 MWh @ €55/MWh : €4,114
├─ Subvention CRE (appel d'offres, si admis) : €12,000–20,000
└─ TOTAL REVENUS (année 1) : **€34,627 + aides**

COÛTS OPÉRATIONNELS ANNUELS
├─ Assurance : €600
├─ Maintenance : €1,200
├─ PMO gestion (sans SaaS) : €4,000–6,000
├─ Gestion courbes/clés répartition (15h/mois manuel) : €2,400
├─ Plateforme/APIs (estimation) : €500
└─ Total OpEx : **€8,700–10,200**

RÉSULTAT NET ANNUEL (année 2–3, sans aides répétées)
└─ €18,513 (TAc) + €4,114 (surplus) – €9,500 (OpEx) = **€13,127/an**

PAYBACK (avec aides première année)
└─ (€218,000 – €18,000 aides) / €13,127 = **15.2 ans**
└─ **Limite rentabilité économique** → nécessite contrats durée 15+ ans ou nouveau modèle flex/services 

### Scénario C : Entreprise Tertiaire 100 kWc / Multi-sites 3 points INVESTISSEMENT (CAPEX)
├─ Installation PV (3 sites × 33 kWc) : €90,000
├─ Onduleurs + box données décentralisé : €9,000
├─ Raccordement (3 sites) : €9,000
├─ SaaS settlement (estimation) : €2,000
└─ Total : €110,000

ÉCONOMIES ANNUELLES vs. MARCHÉ SPOT (année 1)
├─ Consommation 300 MWh/an (mix 40% jour, 60% nuit)
├─ Production autoconsommable (60% sync.) : 61.2 MWh @ €0.17/kWh vs marché €0.55/MWh
├─ Économie par MWh : €0.38/kWh × 61.2 MWh = **€23,256/an**
├─ OpEx ACC (low-touch SaaS) : €2,500
├─ Flex services (réduction prix négatifs) : +€2,000–5,000 (bonus si pilotage)
└─ **NET BENEFIT YEAR 1 : €22,500–25,500**

PAYBACK : 110,000 / 23,500 = **4.7 ans** ✅ (attractive) 

### 4. Segmentation Rentabilité : Cas Gagnants vs. Difficiles 73 74 

Gagnants : 
- ✅ Bailleur social > 50 kWc, taux autocons. > 50% 
- ✅ ZAC activités tertiaire synchrone, 150+ kWc 
- ✅ Collectivité patrimonial (écoles/médiathèques) > 50 kWc 
- ✅ Copropriété > 80 kWc, participation > 70%, coûts gestion < €100/an 
- ✅ Entreprise multi-site, profil conso stable 

Difficiles : 
- ❌ Petit collectif (<30 kWc), peu de consommateurs (taux autocons. < 40%) 
- ❌ Production intermittente non-synchrone (ex: PV nuit, conso jour décalée) 
- ❌ Zone rurale : coûts Enedis raccordement ↑, peu de participants 
- ❌ Habitat collectif privé petit : friction vote, participation <50% 

## C. Croissance 2026–2030 : Scénarios & Drivers 

### 1. Trois Scénarios Probabilistes (Data-Driven Projection) 

Baseline 2025 : 900 opérations, 110 MWc (consolidées H1 2025) 

Assumptions par scénario : Driver Prudent Central Accéléré Croissance opérations/an (%) +25% +40% +55% Croissance puissance/an (%) +30% +45% +60% Taux adoption collectivités 10% 25% 45% Taux adoption bailleurs 15% 30% 50% Avg taille projet (MWc) 0.12 0.13–0.15 0.18 Enablers clés Lite: TURPE 7 + seuil 5MW Moderate: API Enedis + shadow billing Aggressive: Full SaaS + flex market 

Projections : Année Prudent Ops Central Ops Accél. Ops Central Power (MWc) 2025 (réel mi-année) 900 900 900 110 2026-Q2 (projec.) 1,200 1,500 2,000 160 2027-Q4 1,600 2,500 3,800 320 2028-Q4 2,100 4,000 6,500 550 2029-Q4 2,700 6,000 10,500 900 2030-Q4 2,700 6,000 10,500 900 MWc 

Interprétation : 
- Prudent = réalisation règlementaire partielle + friction SaaS + fatigue collectivités 
- Central (meilleure base) = plan gouvernement 2025–2026 mis en œuvre (API, TURPE, standardisation) 
- Accéléré = écosystème full digitalisé + tarification flex + communautés énergie transposées 

### 2. Dix Leviers Critiques Pour Croissance 75 76 77 78 79 80 

### Leviers Réglementaires/Institutionnels [Top 5] Levier Status 2025 Impact estimation Timeline Owner 1) Seuil puissance 3→5MW ✅ Effectif 6 mars 2025 +60% puissance moyenne (petits projets viables) Done Gouvernement 2) TURPE 7 option ACC ✅ Effectif 1er août 2025 +15% économies clients si taux autocons. >60% 2025-ongoing CRE/Enedis 3) Accise 0€ <1MWc ✅ Effectif 1er mars 2025 +40% margin petits projets (<500 kWc) Done Ministère Écologie 4) DataHub/API Enedis 🟡 Partiellement (RGPD consent.) -70% temps PMO gestion clés si auto (estimation) 2025-2026 Enedis DGEC 5) Standardisation PMO 🔴 Absent (ad-hoc) -40% cycle légal si modèle unique fourni 2026-2027 FNCCR/CRE/Ministère 

### Leviers Opérationnels/Technologiques [Middle 3] Levier Status 2025 Impact estimation Timeline 6) Shadow Billing auto 🟡 Enogrid/HubWatt pilots -80% facturation disputes , +15% NPS clients 2026-2027 7) E-signature templates 🟡 Emerging (Docusign, Zitadel) -50% cycle signature RGPD 2025-2026 8) KYC entreprise simplifié 🔴 Absent (manuel) -30% onboarding time si auto 2026-2027 

### Leviers Économiques/Marché [Last 2] Levier Status 2025 Impact 9) Tarification dynamique/flex 🟡 Pilots (Bohr Énergie, Animergy) +€5–10/MWh producer margin si gestion prix négatifs 10) Agrégation multi-sites/parc 🟡 ZAC pilots +25% taux autocons. moyens (optimisation clés) 

### 3. Signaux Faibles à Surveiller 2026+ 

Monitoring clé pour PROMEOS : 
- RED III transposition (Directive UE énergie renouvelable 2023/2413) : communautés énergie peuvent élargir périmètre 10+ km (France attendu 2026) 
- Arrêté flex/prix négatifs (loi finances 2025, art. 175) : pilotabilité production >10MW → ACC <10MW reste “demandeur” flex , mais nouvel arbitrage économique PV vs stockage vs flex 
- TICFE taux révisé (2027) : impact fiscal ACC si évolution 
- Évolution TURPE 8 (post-2029) : signal prix négatif vs TAc intégré? → tester hypothèse 

## D. Les Dix Leviers pour Simplifier & Accélérer (Process + Product) 

### Matrice Friction → Solution PROMEOS # Friction Douleur détaillée Cause racine Solution Process/Tech Gain time-to-market Dépendances 1) Montage PMO 2–4 mois Création structure juridique, statuts, ouverture compte, agréments. Chaque projet réinvente la roue. Absence standardisation légale, fiches d’instruction contradictoires (Enedis vs. prefet) Fournir modèle statuts «plug-and-play»; e-signature SGET; auto-registre Enedis. PROMEOS : PMO Workspace template library -1.5 mois (50% accel.) Partenariat CRE/Enedis pour validation template 2) Signature convention Enedis 4–8 sem. Rédaction Convention (model unique Enedis 2023 = 8 pages, flou inter-rôles). Retours multiples si erreurs. Convention pas digitalisée; Enedis ne refuse qu’en cas erreur PMO = délais d’attente Template AC convention + e-signature Docusign + vérification auto. checklist (PRM, Linky, mandats). PROMEOS : Convention Builder 1-click avec pré-remplissage Enedis DataHub -3 sem. Enedis AcceptDigital signature, PROMEOS intégration API Enedis 3) Collecte consentement RGPD (3–6 sem.) Chaque consommateur/producteur doit signer doc. papier AC, explications tarifs complexes Paperasse, inertie participants, non-compréhension courbes charge Kits RGPD pré-rédigés + e-signature en masse (bulk). Dashboard suivi consent. taux -4 sem. (bulk e-sig) Compliance CNIL (validation modèle) 4) Gestion clés répartition (15–30h/mois) PMO doit calculer clés, envoyer Enedis par mail avant J+4 mois. Erreurs = refacturation. Pas d’automatisation Enedis; PMO fait manuelle Excel PROMEOS : Clés Calculator auto (P30 flux Enedis via API) + simulation scénarios + envoi API Enedis auto. 1-click attestation -95% du temps PMO Enedis DataConnect API open access pour tous; accord secret data PMO 5) Entrées/sorties participants (2–6h/projet) Nouvel arrivant/départ = recalcul clés, nouvelle convention, risque rupture. Gestion registre flou. Absence registre digital; flux papier; oublis Enedis notif. PROMEOS : Participant Registry auto-update (e-signature new/exit, auto-notification Enedis J-1, recalc clés smart) -3h/événement Enedis batch API pour annulations 6) Calcul & réconciliation facturation (8–15h/mois) Enedis envoie TAc/TAp JSON; PMO ou fournisseur doit réconcilier, boucler erreurs, en cas écart. Litiges courants. Pas de norme XML; APIs écrites pour machines mais pas pour SaaS PMO; fournisseur opère en silo PROMEOS : Shadow Billing Engine (reçoit flux Enedis, calcule factures auto., compare fournisseur, flagge écarts, propose corrections) -80% temps + -70% erreurs facturation Enedis XML standardisation (ISO 20022 prêt?) + fournisseur intégration EDI 7) Génération factures ACC consommateurs (4–8h/mois) PMO ou gestionnaire doit générer factures AC (énergie à prix local) + factures fournisseur (complément). Deux systèmes, risque doublon/omission Absence standardisation facture ACC; PMO utilise Word/Excel custom PROMEOS : Facture Generator (template légal, signature digitale, envoi email mass, archives PDF, export comptable SEPA) -5h/mois + -100% oublis UBL invoice standard (EU 2020) adoption 8) Audit trail & conformité reporting PMO doit logger toutes transactions (clés, factures, consentements, entrées/sorties), prouver à CRE + Enedis. Aucun standard format. Pas de format audit trail; enregistrement => papier/email PROMEOS : Audit Dashboard (tous événements horodatés, signés crypto, export zippé pour CRE/Enedis, real-time) -3h/trimestre + 100% conformité Standard audit (ISO 27001 logs?) 9) Gestion prix négatifs & flex Producteur doit monitorer prix spot J-1, décider pivot ACC vs marché. Absent dans 90% projets. Pas d’outil decisional; producteur = reactive; ACC perd économies. Nouveau problème 2024–2025 (360h prix négatifs/semestre) PROMEOS : Flex & Price Arbitrage Module (alerte prix négatifs, recommande « réduire prod » ou « piloter conso », trace décisions) Variable (optionnel) RTE DataConnect pour prix temps-réel; IRVE integr. 10) Support & litiges participants PMO champs absorbé par questions participants (« pourquoi facturation ≠ estimé? »), escalades Enedis, arbitrages longs Aucun dashboard transparency pour participants; manque pédagogie consommateur PROMEOS : Participant Portal (chacun voit sa TAc/TAp, facture estimée vs réelle, clés appliquées, contact PMO 1-click, FAQs contextualisées) -5h/mois PMO + -70% litiges Portal UX design + data feed temps-réel Enedis 

### Récapitulatif : Impact Cumulé si 100% Solutions Implémentées 

Before (2025 state): 
- Cycle projet : 4–8 mois 
- Friction cumul. : ~100–150h/an par opération 
- Erreurs facturation : 5–10% projets/an 
- Taux abandonn. PMO : 10–15% 

After (PROMEOS full, 2027+): 
- Cycle projet : 3–4 mois (-50%) 
- Friction cumul. : 15–25h/an (-80%) 
- Erreurs : <1% 
- Taux abandon : <3% 

Impact marché : +40% opérations viables en small/medium, -30% coûts PMO → +2x croissance en scénario central 

## E. Intégration PROMEOS : Produit & Positionnement 

### 1. Positionnement Stratégique : PROMEOS = “Cockpit Local Energy 2.0” 

Avant PROMEOS : 
- Fournisseurs classiques = fourniture + facturation (baseline) 
- Agrégateurs flex = marché spot + services système (haut-débit) 
- Gap : pas de “single pane of glass” pour collectifs locaux + settlement robuste + micro-transactions 

Après PROMEOS + brique ACC : 
- Micro-fournisseur augmenté : “fourniture complément local + settlement ACC + flex implicite + cockpit décision” 
- Différenciation : 
- ✅ Upsell PMO vers “ABC Ops” (data+facturation) 
- ✅ Cross-sell flex/IRVE (services additionnels) 
- ✅ Valeur PMO = “time ROI” (10h/mois économisées = €400–600/mois) 
- ✅ Valeur consommateurs = “transparency + economie 15–30% vs marché” 

Target customer : 
- PMO startup (300–400 projets/an nouveaux) : besoin help desk + legal template 
- PMO établie (bailleurs, SEM) : besoin DP optimization + multi-sites 
- Fournisseur micro : besoin settlement + facturation décorrelée fourniture 

### 2. Three Packages Produit 81 82 83 

### ACC Starter (MVP Focus, Q1 2026) 

Positioning : “Diagnostic + kit PMO + validation conformité” 

Features : 
- ACC viability check (input: adresses, conso profiles Linky) → output : “go/no-go + devis temps” 
- Modèle statuts PMO compatible Enedis (downloadable, e-signable) 
- RGPD consent kit (templates, DocuSign integr.) 
- Pre-filled Enedis “demande d’entrée acc” form 
- Cost : €500–1,500/projet (one-shot) OR subscription €100/mois lock-in 
- Audience : petits collectifs, bailleurs exploring 

### ACC Ops (Core, 180j focus) 

Positioning : “Production to settlement, fully managed” 

Features : 
- Data & Monitoring : P30 curves from Enedis DataHub (API), dashboard prod/conso/TAc/TAp real-time 
- Clés Calculator : statique/dynamique simple/full auto (P30-based, editable scenario), monthly Enedis notification API-driven 
- Facturation ACC : shadow billing (PMO or reseller-agnostic), templates PDF/digital, paiement SEPA auto 
- Settlement : Enedis reconciliation log, export comptable (CSV/XML), audit trail horodaté 
- Participant Portal : login participant = sees facture ACC + estimated 3 months, contact PMO 
- Support : onboarding + monthly check-in 

Cost : €200–500/mois per operation (based on participants, complexity) 
SLA : 99.5% uptime, support <24h 
Audience : active PMOs (50–200 sites), bailleurs sociaux, collectivités 

### ACC Optim (Premium, 12m focus) 

Positioning : “Active optimization + flex market + price arbitrage” 

Features : 
- Everything in Ops + 
- Price Negative Monitoring : RTE DataConnect alert (day-ahead), auto-notification producteur + “reduce production?” or “pilot consumption” recommendation 
- Flex Dashboard : interface producteur = accept/decline flex offer, track margin impact 
- Implicit Flex : auto-pilot conso (partner IRVE, EMS buildings) during peak PV, “load shift” scoring 
- Arbitrage Engine : producteur voit “TAc price vs spot M0 today”, chooses best routing (ACC lock-in vs spot) 
- Ancillary Services : track capability for RTE mFRR (manoeuvrability frequency restoration) + revenue share model 
- Cost : €500–1,500/mth (premium), +% of flex revenue capture (e.g., 10–15%) 

Audience : Advanced PMOs, greenfield ACC projects with >500 kWc, industrial/multi-sites needing demand response 

### 3. Modules Logiciels (MVP → v1 → v2) 

Tech Stack (proposed): 
- Frontend : React (Acc Starter web form), Next.js (Ops + Optim dashboards) 
- Backend : Node.js + FastAPI (Python for data science), PostgreSQL 
- Integrations : Enedis API DataHub (OAuth2), Docusign API (e-sig), SEPA/bank APIs (settlement), Strapi CMS (template library) 
- Security : ISO 27001, encryption AES-256, audit logs, rate-limit Enedis API 

Module Roadmap : Phase Timeline MVP Scope v1 Scope v2 Scope (optional) PMO Workspace 0–90d Statuts templates, registre participants (spreadsheet export), contact directory E-sign integr., auto-notification Enedis, versioning doc Blockchain audit trail, instant notary integration Data & Monitoring 30–90d Manual P30 upload (CSV), basic dashboard (Grafana clone) Enedis DataHub API auto-pull (RGPD consent gate), alerts Predictive models (ML) for TAc forecasting, anomaly detection Clés & Settlement 60–150d Calc tool (spreadsheet + validation) Auto-calc from P30, Enedis API notify, scenario sim Full optimizer (mixed-integer programming) for > 3 producteurs Shadow Billing 90–180d Template factures Word/PDF Auto-gen from settlement logs, XML export, SEPA batch files Real-time billing (P15 if Enedis allows), instant invoice delivery Compliance Add-ons 120–180d Manual OPERAT export Auto-export structure (CSV format CRE), audit UI Integration BACS/OPERAT APIs API & Integrations 90–180d Webhook for Enedis events (polling) REST API for partners (PMO embedding), OAuth GraphQL, real-time subscriptions, Enedis <> PROMEOS sync 

### 4. PRD Mini : Problem, Users, Jobs, Features, Data, KPIs 

### Problem Statement 
- Currently : ACC PMOs spend 100–150h/year per operation on administrative overhead (clés, facturation, RGPD, registre) 
- Enablers exist : Linky data, Enedis API, e-sig tools, but fragmented, not coordinated 
- Market bottleneck : high time-to-market (4–8 mths) + low success rate (~85%) + churn from PMO fatigue 

### Users (Personas) 
- Alice, PMO bailieur 50 kWc, 100 logements 
- Goal : “Reduce paperwork from 30h/year to <5h, make participants happy” 
- Pain : manual Excel clés, participant complaints re: invoice clarity 
- Willingness to pay : €150–300/mth 
- Bob, ZAC collectivité 200 kWc, 12 companies 
- Goal : “Optimize TAc with dynamic keys, avoid negative prices” 
- Pain : no visibility into hourly arbitrage, lost revenue ~€5k/year 
- Willingness to pay : €400–800/mth 
- Carol, Fournisseur micro (50+ clients ACC) 
- Goal : “Automate facturation ACC clients, reduce reconciliation disputes” 
- Pain : manual shadow billing vs Enedis feeds, 1 error/50 = low NPS 
- Willingness to pay : % of volume (e.g., €0.01–0.03/MWh) 

### Jobs-to-be-Done 
- Job 1 : Onboard new participants without legal/admin friction (enable PMO growth) 
- Job 2 : Calculate fair keys from real data, avoid manual errors (build trust) 
- Job 3 : Create accurate participant invoices, enable self-service clarity (reduce churn) 
- Job 4 : Report compliance to CRE/Enedis with zero re-work (regulatory peace) 
- Job 5 (premium) : Monitor spot prices, maximize ACC margin vs arbitrage (grow revenue) 

### Core Features (MVP) 

Must-Have : 
- ✅ Statuts PMO templates (auto-fill, e-sign) 
- ✅ Participant registry (add/remove, versioning) 
- ✅ P30 import (manual CSV 90d, then auto Enedis API) 
- ✅ Clés calc (statique + dyn. simple, Enedis notify) 
- ✅ Facture template (PDF/email bulk) 
- ✅ Audit log (all events timestamped, exported) 

Nice-to-Have (v1) : 
- 🟡 Enedis DataHub API integration (auto-pull) 
- 🟡 Shadow billing reconciliation (vs Enedis feed) 
- 🟡 Participant portal (login, see invoice) 
- 🟡 SEPA batch export 

Future (v2+) : 
- 🟢 RTE price feed + flex arbitrage 
- 🟢 ML forecasting 
- 🟢 Blockchain audit 

### Data Model 

Entities : 
- Operation : id, name, address, PMO legal id, creation date, status (active/draft) 
- Participant : id, role (producer/consumer), PRM identifier (Linky point), name, email, consent_rgpd, join_date, exit_date 
- Clés : id, operation_id, version, type (statique/dyn simple/dyn full), coefficients (JSON), effective_date, notified_enedis_date 
- P30 Feed : operation_id, date, quarter (15min slot), prod_kWh, conso_kWh, tac_kWh, tap_kWh (from Enedis or manual) 
- Facture : id, participant_id, month, amount_tac_eur, tax_eur, total_eur, status (draft/sent/paid), sent_date, payment_date 
- Audit Log : timestamp, user_id, operation_id, action (add_participant, change_keys, send_facture, etc.), before/after JSON 

### Security & Compliance 
- Auth : OAuth2 (PMO + participant separate scopes) 
- Data : All participant/consumption data encrypted at rest (AES-256), in transit (TLS) 
- RGPD : explicit consent gate (Docusign), right-to-delete workflow, DPIA doc 
- Audit : immutable logs, crypto signature on key transmission to Enedis 

### Pricing Model (recommended SaaS hybrid) 

Opción A : Seat-based + Usage 
- Base : €200/mth per operation (includes 1 PMO user, 100 participants) 
- Overage : +€50 per 50 participants 
- Premium : +€300/mth for Optim module (flex + arbitrage) 
- Setup : €500 (one-shot) 

ARR example : 
- 500 opérations × €200 = €100k/mth baseline 
- 150 opérations Optim × €300 = €45k premium 
- Setup revenue : ~€5k/mth amortized 
- Total MRR target : €150k (€1.8M ARR, year 2) 

### Success Metrics (KPIs) 

Product : 
- DAU (daily active PMO users) : target 50% of customers by M12 
- Time-to-value : 90% of onboarded ops live in <30d (vs 4m before) 
- Feature adoption : clés auto-notify = 70%+ by M12; shadow bill = 40%+ by M18 

Business : 
- CAC payback : <12 months (assuming €300/mth ARPU) 
- NPS : target 45+ (SMB SaaS median ~30) 
- Churn : <5% MoM (target, vs industry 3–7%) 
- Expansion revenue : 15% (upsell Optim to 20% of base) 

Market Impact : 
- Opérations onboardées (cumul.) : 100 by M6, 500 by M12, 2,000 by M24 
- Power additionnal enabled : 50 MWc by M12, 300 MWc by M24 (vs 110 MWc baseline 2025) 
- Estimated contribution to market growth (Central scenario) : 25–35% 

## F. Benchmark Concurrence & Espaces Blancs PROMEOS 

### 1. Paysage Concurrentiel Actuel 

Acteurs clés 2025 : 84 85 86 87 88 Joueur Produit Core Type Couverture Avantages Limits Enogrid (lead market) EnoLab (étude) + EnoPower (gestion) + MonEnergie Collective (portal) SaaS + Services 370+ projets, 23 MW gérés Full suite (study→exec), strong brand Plateforme legacy (onboarding toujours ~3m), pas de settlement financier HubWatt Plateforme ACC (registre, clés, facturation) SaaS ~100+ projets estimé Facturation élégante, UX clean Petit market share, peu de visibilité, API Enedis intégration non-public EnoPower (Enogrid) Software gestion opérationnelle ACC SaaS 20+ MWc en produção Intégration Enedis native, interface simple Coûteux (€500–1k/mth estimé), pas d’onboarding, pas d’arbitrage prix Fournisseurs classiques (EDF, Enercoop, Ekwateur) Settlement + facturation (ACC = overlay) Aggrégat Partial (seulement clients propres) Couverture réseau, force commercial Pas d’outil PMO dédié, facturation 2-tiers complexe, pas de flex Bohr Énergie (Animergy partner) Agrégateur + arbitrage prix (“mandataire PMO”) Service 50+ projets en pipeline Flex + prix arbitrage, lève VC récente Modèle 2-sided (producteur + PMO), pas de SaaS PMO propre, few regions Plateformes européennes (Austria: Wenet, Slovenia: …very few) Full energy communities OS SaaS <10 deployments outside HQ Tech mature, RED III aligned Régulières non-transposables à France (régime collecte différent) 

Observation clé : marché très fragmenté = 5–10 SaaS minor + services ad-hoc. Aucun leader consolidé avec full stack (study + gestion + settlement + flex). Enogrid = closest, mais plateforme legacy (EnoLab = outil études, EnoPower = gestion basique). 

### 2. Matrix Différenciation PROMEOS Dimension Enogrid HubWatt Fournisseurs PROMEOS Win Onboarding 8–12 sem. 4–6 sem. 6–8 sem. 3–4 sem. (template PMO + e-sig) ✅ PROMEOS Clés auto-calc P30 🟡 Partial (EnoPower) ✅ Native ❌ Pas ✅ Full auto ✅ PROMEOS Settlement/Shadow Bill ❌ Absent 🟡 Partial 🟡 (fournisseur only) ✅ Full 3-way (PMO+fournisseur+Enedis) ✅ PROMEOS Flex/Arbitrage Prix ❌ No ❌ No ❌ No ✅ Optim module ✅ PROMEOS Participant Portal 🟡 MonEnergie Collective (light) ✅ Basique ❌ No ✅ Rich (facture + TAc/TAp + chat PMO) ✅ PROMEOS Integr. Enedis API 🟡 Manual 🟡 Custom ❌ Legacy ✅ Open (DataHub + DataConnect ready) ✅ PROMEOS Pricing Model Service (custom) SaaS/seat Fixed SaaS hybrid (seat + opt-in premium) ✅ PROMEOS (clarity) Go-to-Market Services + sales Direct SaaS Embedded Salesforce direct + partnerships (GRD, FNCCR) ✅ PROMEOS (multi-channel) 

### 3. Espaces Blancs & Opportunités PROMEOS 

### Blanc 1 : “PMO-in-a-box” pour petits collectifs 
- Gap : Bailleurs/collectivités petites (30–100 logements, <50 kWc) intimidé par “besoin SaaS complexe” 
- PROMEOS opportunity : lightweight starter (templates, consentements, simple clés statiques), mobile-friendly, pricing €100–150/mth 
- Win vs Enogrid : EnoLab = outil études (€500/projet), EnoPower = gestion avancée (€500/mth). Aucune solution intermédiaire 

### Blanc 2 : Full settlement (PMO + fournisseur + Enedis 3-way) 
- Gap : Erreurs facturation ACC = 5–10% projets (données terrain Animergy). Concurrence propose “2-way max” (PMO+Enedis ou fournisseur+Enedis) 
- PROMEOS opportunité : shadow billing avec API Enedis (3-way reconciliation auto) + participant visibility 
- Win : 1 truth source (PROMEOS) vs. 3 spreadsheets = -80% disputes, -15% chargeback 

### Blanc 3 : Flex/arbitrage implicite < 1 MW 
- Gap : Bohr/Animergy = agrégateurs (service boutique, >5 projets min). <5 projets = pas attractive. Petit ACC orphelin sur prix négatifs 
- PROMEOS opportunité : low-touch “flex dashboard” (prix spot alerts + reco) dans module Optim. Auto-connect IRVE/EMS para pilotage semi-auto 
- Win : 10–20 petits ACC + flex = collectively “big” aggregation, avec PROMEOS comme platform 

### Blanc 4 : Intégration directe GRD hors-Enedis 
- Gap : ELD (Entreprises Locales Distribution) = ~150 GRD régionales. None have native ACC SaaS offre 
- PROMEOS opportunité : white-label “ACC Manager by [GRD name]” → ELD peut market à clients, PROMEOS opère backend 
- Win : distribution partner strategy = 150 GRD × 20 small ACC/an = 3k projects/an incremental 

### Blanc 5 : “Micro-fournisseur” cockpit = PROMEOS + fourniture 
- Gap : PROMEOS = PMO tool. But PMO often wants = someone to “resell AC electricity” + handle facturation complément 
- PROMEOS opportunity : embedded “fournisseur de complément” module (PROMEOS owns supply layer, white-label to PMO or partner) → 1 invoice to end customer 
- Win : higher margin (cream 0.5–2€/MWh spread = €500–2k/operation/year), better NPS (1 invoice instead of 2) 

## G. Roadmap Brique ACC PROMEOS : 90j, 180j, 12m 

### 1. Phasing & Dependencies ┌─────────────────────────────────────────────────────────────┐
│ PROMEOS ACC Integration Roadmap 2026 (High-Level) │
├─────────────────────────────────────────────────────────────┤
│ Q1 2026 (Jan-Mar) : MVP 1.0 — Starter Pack │
│ Q2-Q3 2026 (Apr-Sep) : v1.0 — Full Ops │
│ Q4 2026-Q1 2027 (Oct-Mar) : v2.0 — Optim + Integrations │
└─────────────────────────────────────────────────────────────┘ 

### 2. 90-Day MVP 1.0 (Q1 2026) 

Goal : Validate problem (PMO onboarding friction), build landed product (Starter), acquire first 50–100 PMOs 

Scope : 
- ✅ PMO templates (statuts, conventions, RGPD docs) — downloadable, e-signable via DocuSign 
- ✅ Participant registry (spreadsheet export, basic dashboard, contact directory) 
- ✅ Clés calculator (upload P30 CSV, calc statique, notify Enedis template auto) 
- ✅ Facture template (doc generator, bulk email, PDF archive) 
- ✅ Website + onboarding flow (Webflow or simple React SPA) 

Tech Stack : 
- Frontend : Next.js (Vercel deploy) 
- Backend : Node.js Express + PostgreSQL (Railway or DigitalOcean) 
- Integration : Docusign API, SendGrid (email), manual CSV input (no API yet) 
- Cost : ~€3–5k/mth infra + ~200h dev 

Go-to-Market : 
- B2B2C : partner 2–3 major bailleurs (Habitat HF, RIVP) for pilot 
- Webinar + case study (FNCCR amplify) 
- Pricing : €100–200/mth starter, €500 setup (recoup dev in 1–2 customers) 

Success Criteria : 
- 50–100 PMOs onboarded (10–20 live ACC operations) 
- 80% report “onboarding time -30% vs before” 
- NPS 30+ 
- Churn <5% MoM (new product, expected) 

### 3. 180-Day v1.0 (Q2–Q3 2026) 

Goal : Full operational product (ACC Ops), monetize, prove unit economics 

Scope : 
- ✅ Enedis DataHub API integration (auto-pull P30, consent gates, retry logic) 
- ✅ Advanced clés (dynamique simple + full, multi-scenario editor, version control) 
- ✅ Settlement module (P30 + clés = TAc/TAp auto-calc, vs Enedis reconcile, export XML/CSV) 
- ✅ Shadow billing engine (compare Enedis data vs fournisseur invoice, flag discrepancies) 
- ✅ Participant portal (login, facture history, TAc/TAp transparency, contact PMO 1-click) 
- ✅ Compliance reporting (auto-export CRE format, audit log, attestation signature) 

Tech Stack : 
- Backend : FastAPI (Python) for data science (P30 processing, reconciliation logic) 
- Frontend : React Dashboards (Material-UI or shadcn/ui) 
- Database : PostgreSQL + Redis (cache, session) 
- Integration : Enedis DataHub (OAuth2 + API calls), SEPA batch (plaid or natixis) 
- Cost : ~€8–10k/mth infra + server costs + ~400h dev 

Go-to-Market : 
- Expand to 500–1000 PMOs (100–200 live operations) 
- Partner with 1 major fournisseur (EDF, Enercoop) for settlement integration 
- Community building (Discord for PMOs, monthly webinar) 
- Pricing : €200–400/mth Ops, €500 setup 

Success Criteria : 
- MRR €50–80k (200 avg customers × €300) 
- Churn <4% MoM 
- Customer effort score (CES) >7/10 (operability) 
- 90% of ACC operations in settlement module (not manual) 

### 4. 12-Month v2.0 (Q4 2026–Q1 2027) 

Goal : Premium features (Optim), market leadership, ecosystem lock-in 

Scope : 
- ✅ Flex Dashboard + Price Arbitrage (RTE spot feed, alert producer, recommendation engine) 
- ✅ Implicit flex (IRVE + EMS partners, auto-pilot consumption, load shift scoring) 
- ✅ Advanced analytics (predictive TAc forecasting, anomaly detection, benchmarking vs similar projects) 
- ✅ Multi-site aggregation (group clés optimizer for 3+ sites, maximize collective TAc) 
- ✅ Marketplace (templates, integrations, partners: onduleurs, IRVE, GTB) — small commission 
- ✅ Open API (REST/GraphQL for PMO white-label, fournisseur integrations) 

Tech Stack : 
- ML/AI : Time-series forecasting (Prophet or similar), clustering (K-means for benchmarking) 
- Real-time : WebSocket (Fastify or GraphQL subscriptions for price alerts) 
- Partner ecosystem : Stripe for marketplace, OAuth2 for 3P integrations 
- Cost : ~€15–20k/mth infra + ~600h dev 

Go-to-Market : 
- Acquire 2,000+ PMO accounts (500–800 live operations) 
- Launch Optim premium (30% upsell target = 400–500 accounts) 
- Partner integrations (2–3 major EMS, 5+ IRVE suppliers) 
- Thought leadership (case studies, whitepapers, speaking CRE) 
- Pricing : €300–500/mth Ops (expanded), €600–1500/mth Optim (flex) 

Success Criteria : 
- MRR €250–350k (goal for year-end 2027) 
- ARPU €300–400 (expansion revenue +20%) 
- NPS 50+ 
- CAC payback <10 months 
- Profitability target (depending on VC/bootstrap trajectory) 

## H. Appendices & Resources 

### A. Réglementations Clés à Surveiller 89 90 91 92 93 94 Source légale Contenu Impact ACC Date clé Arrêté 21 fév. 2025 (JO 5 mars) Seuil 3→5 MW; dérogation 10 MW collectivités Game-changer (viabilité +40%) Effectif 6 mars 2025 TURPE 7 (CRE délib. 2025-78) Option ACC (majoration + rabais possible) Tarification clarifiée, moins opaque Effectif 1er août 2025 Loi finances 2025, art. 175 Pilotabilité >10 MW, flex markets Accent flex (nouveau marché) Arrêté 8 sept. 2025 publiée Accise 0€ (avant 1 fév. 2025) <1 MWc exonérée Boom petits projets attendu Effectif 1er mars 2025 RED III directive UE (2023/2413) Communautés d’énergie, périmètre étendu France transposition 2026? En discussion BACS décret (depuis 1 jan. 2025) Automatisation bâtiments >290 kW Tertiaire ACC quasi-obligé SaaS Scope largit 2027 

### B. Liens & Ressources Clés 

Officiels : 
- Légifrance Code de l’énergie L315-1 à L315-8 95 
- CRE Délibération 2024-231 (18 déc. 2024) 96 
- Enedis Convention Model ACC 97 
- ADEME Guide ACC 2024 98 

Marché : 
- Enogrid : ACC pour bailleurs sociaux 2024 99 
- Livre Blanc ACC & Communautés Énergie (2024) 100 
- Enogrid Europe ACC 2025 benchmark 101 

Data & Monitoring : 
- Enedis Observatoire ACC (fin 2024 : 698 ops, 73.6 MWc) 102 
- Enedis DataHub/DataConnect API 103 

Communautés Énergétiques Citoyennes : 
- Énergie Partagée (réseau citoyen) 104 105 
- FNCCR (collectivités) 106 

### C. Templates & Checklists Notion-Ready 

### Checklist Montage PMO [utilisable directement] 
- Étape 1 : Viabilité (1–2 sem.) 
- Lister participants (producteurs, consommateurs) 
- Valider localisation (<2 km ou dérogation demandée?) 
- Additionner puissance producteurs (≤3–5–10 MW?) 
- Estimer taux autocons. (courbes Linky si possible) 
- Faire devis CAPEX PV + raccordement Enedis 
- Étape 2 : Structure PMO (2–4 sem.) 
- Choisir forme juridique (asso / SAS / SEM) 
- Préparer statuts (utiliser template PROMEOS) 
- Ouvrir compte bancaire PMO 
- Enregistrer à la préfecture/sous-préfecture (si obligatoire) 
- Souscrire assurance RC professionnel 
- Étape 3 : Consentements & Mandats (3–4 sem.) 
- Collecter consentement RGPD (tous participants) 
- Signer mandats Enedis (producteur = CAE/CARD-i, consommateur = accès courbes) 
- Créer registre participants (initial) 
- E-signature tous docs (DocuSign ou équivalent) 
- Étape 4 : Convention Enedis (2–4 sem.) 
- Pré-remplir template convention (PROMEOS auto-fill?) 
- Définir clés répartition (type + valeurs) 
- Signer avec Enedis (envoyer par portail Enedis DataHub) 
- Attendre confirmation Enedis (5 jours ouvrés max.) 
- Planifier date démarrage ACC (généralement J+15 jours) 
- Étape 5 : Mise en Service (2–6 mois, paralléle) 
- Installer PV + onduleur (entreprise RGE) 
- Raccordement Enedis (2 mois simple, 12–18 mois complexe) 
- Tests conformité (Consuel) 
- Lancer facturation ACC (premiers mois : vérifier TAc/TAp) 
- Activer participant portal 

Total : 3–6 mois (avec PROMEOS = -50% si outils auto-fill + e-sig) 

### Modèle Contrat PMO–Consommateur ACC (simplifié) CONTRAT D'AUTOCONSOMMATION COLLECTIVE
Entre [PMO], [Date], Durée [3–5 ans]

1. PARTIES
 - PMO Organisatrice : [Nom], [SIRET], [Adresse]
 - Consommateur : [Nom], PRM [xxxxxx], [Adresse]
 - Producteur : [Nom], PRM [yyyyy]

2. OBJET
 Partage électricité produite localement par producteur vers consommateur.

3. ÉLECTRICITÉ FOURNIE (TAc = "Traction Autoconsommée")
 - Quantité : calculée mensuellement par Enedis selon clé répartition
 - Prix : [€/kWh] = prix négocié entre producteur et consommateurs
 - Facturation : par PMO ou fournisseur complément, mensuel ou [autre]
 - Paiement : SEPA / virement / chèque, dans [^10] jours après facture

4. ÉLECTRICITÉ COMPLÉMENT (TAp = "Traction Alloconsommée")
 - Fournisseur : client conserve liberté choix
 - Fournisseur reçoit de Enedis : part non-fournie par ACC
 - Facturation : par fournisseur, selon contrat distinct

5. DROITS ET OBLIGATIONS
 - Consommateur : accepte participation ACC, consentement RGPD courbes
 - PMO : assure transparency TAc/TAp, gère registre, notifie changements
 - Producteur : garantit production disponibilité raisonnable, assurance RC

6. RÉSILIATION
 - Participants peuvent quitter ACC à tout moment, [préavis 30 jours]
 - PMO peut exclure participant si défaut paiement [60 jours]
 - En cas sortie, clés recalculées, notifié Enedis [J-1]

7. LITIGES
 - Domiciliation : [lieu], droit français
 - Escalade : PMO → médiation, puis tribunal [ville]

SIGNATURES : PMO, Consommateur, Producteur, [date] 

### D. Données Manquantes & Prochaines Études Recommandées 

Gaps actuels identifiés (données insuffisamment précises) : 
- Distribution statuts juridiques PMO : proportion asso / SAS / SEM / bailleur-PMO (données Enedis confidentielles) 
- Cost curve installations PV 2025 par région : variances de cost CAPEX très importantes entre Île-de-France vs. zones rurales 
- Profiling consommateurs ACC : quels secteurs > ROI? Résidentiel vs. tertiaire vs. industriel (données FNCCR à consolider) 
- Taux autocons. réels observés : moyenne, écart-type, saisonnalité (données Enedis non-publiées officiellement) 
- Willingness-to-pay PMO pour SaaS : étude pricing (few PMO data points) 
- Litiges / taux d’abandon : % projets échoués, causes principales (données anecdotiques vs. systématiques) 
- Calendrier transposition RED III : quand France auto-rises périmètre? (gouvernement non-confirmé) 

Recommandations études complémentaires : 
- Enquête SER/FNCCR auprès 200+ PMO (taille, secteurs, coûts opérationnels, satisfaction) 
- Benchmark prix SaaS PMO (Enogrid vs. HubWatt vs. fournisseurs custom) 
- Cost-benefit analysis ACC vs. achat-vente classique pour 10 typologies (ROI par cas d’usage) 

## Conclusion & Recommandations PROMEOS 

### 1. Synthèse Position Marché 

L’ ACC France est à un point d’inflexion (Q1 2026) : réglementation matière (3→5 MW, TURPE 7, accise 0€), mais opérationalisation très lourde (100–150h/an friction). PROMEOS a fenêtre d’opportunité de 12–18 mois pour devenir platform-of-choice PMO. 

Différenciation clé : settlement 3-way (PMO + fournisseur + Enedis) + onboarding rapide (<4 sem. vs. 4–8 mois) + optional flex/arbitrage. Aucun concurrent offre cette stack . 

### 2. Recommandations d’Action 

### Immédiat (Q4 2025–Q1 2026) : 
- Valider hypothèses PMO : interview 20–30 PMO (bailleurs, collectivités, ZAC) → coût réel gestion, painpoints prioritaires 
- Sécuriser partnerships : 
- Enedis : accord DataHub API access (production + PMO test accounts) 
- FNCCR : co-marketing pre-launch 
- DocuSign : intégration e-sig (priority partnership) 
- Définir MVP 1.0 scope : templates + registre + clés + facturation. Lancer développement Q1 2026 

### Court terme (Q2–Q3 2026) : 
- Acquisition pilote : 50–100 PMO (via bailleurs/collectivités partenaires, FNCCR événements) 
- Build + iterate : v1.0 (Ops complet) → test 50 customers, gather feedback 
- Pricing clarity : valider ARPU €300/mth, setup fees 

### Moyen terme (Q4 2026–2027) : 
- Scale GTM : partnerships ELD (white-label), direct sales to VC-backed ACC companies (Bohr, Animergy) 
- Expand features : Optim module (flex) → 30% of base upsell = €80k MRR incrementally 
- Target 2,000 PMOs by end-2027 (500–800 live operations, 300+ MWc enabled) 

### 3. Financial Projection (Unit Economics) 107 108 109 

Assumptions : 
- CAC : €500 per PMO (direct sales + partnerships, amortized 18 months) 
- ARPU : €300/mth base, +20% expansion (Optim + multi-site) 
- Churn : 4% MoM (target, SaaS SMB standard) 
- Gross margin : 80% (SaaS software, low variable cost) 

Year 1 (2026) : 
- Customer acquisition : 100–200 PMOs (end of year) 
- MRR : €20–40k 
- ARR : €240–480k 
- Unit economics : LTV (€16.7k annualized) / CAC (€500) = 33x ✅ (attractive) 

Year 2 (2027) : 
- Customer base : 500–1000 PMOs 
- MRR : €100–200k 
- ARR : €1.2–2.4M 
- Blended ARPU : €350 (after churn/expansion) 
- Profitability : EBITDA positive likely (team of 5–8) 

### 4. Success Criteria (12m Horizon) 

Product : >90% of new ACC opérations using PROMEOS for clés + settlement 
Market : Capture 30–40% of new PMO market (2,000 opérations = 1,500–2,000 PMOs) by end 2027 
Economic : ARR €1–2M, path to profitability, CAC payback <12 months 
Strategic : become synonymous with « ACC enabler » — referenced in FNCCR, CRE, government policy 

Report compiled: December 30, 2025 | Data freshness: August 2025 (latest regulatory); June 2025 (market data) | Next update: Q2 2026 
110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 

⁂ 
- https://enogrid.com/europe-autoconsommation-collective-2025/ ↩︎ 
- https://www.edf.fr/collectivites/decryptages/accompagner-votre-transition-durable/autoconsommation-collective-quelle-application-pour-les-collectivites ↩︎ 
- https://www.legifrance.gouv.fr/codes/id/LEGISCTA000032939883 ↩︎ 
- https://www.cre.fr/fileadmin/Documents/Deliberations/2024/241218_2024-231_Projet_Arrete_Autoconso_Collective.pdf ↩︎ 
- https://www.hellio.com/actualites/conseils/autoconsommation-collective ↩︎ 
- https://enogrid.com/europe-autoconsommation-collective-2025/ ↩︎ 
- https://www.gossement-avocats.com/blog/autoconsommation-collective-publication-de-larrete-du-21-fevrier-2025-modifiant-les-criteres-dune-operation-dautoconsommation-collective-etendue-et-prevoyant-une-nouvelle/ ↩︎ 
- https://www.journal-photovoltaique.org/les-actus/seuils-de-puissance-augmentes-pour-lautoconsommation-collective/ ↩︎ 
- https://www.enerplan.asso.fr/medias/publication/Jour2_Presentations.pdf ↩︎ 
- https://www.cre.fr/fileadmin/Documents/Deliberations/2024/241218_2024-231_Projet_Arrete_Autoconso_Collective.pdf ↩︎ 
- https://www.ville-de-saint-pierre-les-elbeuf.fr/wp-content/uploads/2025/07/2025-03-15-annexe.pdf ↩︎ 
- https://www.enedis.fr/sites/default/files/documents/pdf/autoconsommation-collective-guide-pedagogique.pdf ↩︎ 
- https://vendee-transitions.fr/habiter/autoconsommation-collective-guide-complet/ ↩︎ 
- https://wesmart.com/es/blog/autoconsommation-collective-france-2025 ↩︎ 
- https://enogrid.com/guide-de-lautoconsommation-collective-pour-les-bailleurs-sociaux/ ↩︎ 
- https://hubwatt.fr/vente-delectricite-en-autoconsommation-collective/ ↩︎ 
- https://wesmart.com/es/blog/autoconsommation-collective-france-2025 ↩︎ 
- https://www.enedis.fr/sites/default/files/documents/pdf/autoconsommation-collective-guide-pedagogique.pdf ↩︎ 
- https://vendee-transitions.fr/habiter/autoconsommation-collective-guide-complet/ ↩︎ 
- https://www.ville-de-saint-pierre-les-elbeuf.fr/wp-content/uploads/2025/07/2025-03-15-annexe.pdf ↩︎ 
- https://www.enedis.fr/sites/default/files/documents/pdf/autoconsommation-collective-guide-pedagogique.pdf ↩︎ 
- https://hubwatt.fr/vente-delectricite-en-autoconsommation-collective/ ↩︎ 
- https://www.sdec-energie.fr/sites/sdec.createurdimage.fr/files/2021-05-06_-enedis_autoconsommation_collective.pdf ↩︎ 
- https://hubwatt.fr/vente-delectricite-en-autoconsommation-collective/ ↩︎ 
- https://www.enedis.fr/sites/default/files/documents/pdf/autoconsommation-collective-guide-pedagogique.pdf ↩︎ 
- https://enogrid.com/les-cles-de-repartition-en-autoconsommation-collective/ ↩︎ 
- https://www.ville-de-saint-pierre-les-elbeuf.fr/wp-content/uploads/2025/07/2025-03-15-annexe.pdf ↩︎ 
- https://wesmart.com/es/blog/autoconsommation-collective-france-2025 ↩︎ 
- https://www.ecologie.gouv.fr/sites/default/files/documents/Lab2051_Autoconsommation_collective_Incubation.pdf ↩︎ 
- https://animergy.com/sans-obligation-achat-valoriser-production-pv/ ↩︎ 
- https://hubwatt.fr/vente-delectricite-en-autoconsommation-collective/ ↩︎ 
- https://www.ville-de-saint-pierre-les-elbeuf.fr/wp-content/uploads/2025/07/2025-03-15-annexe.pdf ↩︎ 
- https://www.enedis.fr/media/1881/download ↩︎ 
- https://www.enedis.fr/sites/default/files/documents/pdf/autoconsommation-collective-guide-pedagogique.pdf ↩︎ 
- https://www.enedis.fr/sites/default/files/documents/pdf/autoconsommation-collective-guide-pedagogique.pdf ↩︎ 
- https://www.ecologie.gouv.fr/sites/default/files/documents/Lab2051_Autoconsommation_collective_Incubation.pdf ↩︎ 
- https://www.enedis.fr/sites/default/files/documents/pdf/autoconsommation-collective-guide-pedagogique.pdf ↩︎ 
- https://enogrid.com/europe-autoconsommation-collective-2025/ ↩︎ 
- https://www.cre.fr/fileadmin/Documents/Deliberations/2024/241218_2024-231_Projet_Arrete_Autoconso_Collective.pdf ↩︎ 
- https://www.enedis.fr/sites/default/files/documents/pdf/autoconsommation-collective-guide-pedagogique.pdf ↩︎ 
- https://www.enedis.fr/sites/default/files/documents/pdf/autoconsommation-collective-guide-pedagogique.pdf ↩︎ 
- https://www.ecologie.gouv.fr/sites/default/files/documents/Lab2051_Autoconsommation_collective_Incubation.pdf ↩︎ 
- https://librairie.ademe.fr/energies/7854-autoconsommation-collective-photovoltaique-guide-pratique-a-l-attention-des-collectivites-territoriales.html ↩︎ 
- https://enogrid.com/turpe-7/ ↩︎ 
- https://www.enedis.fr/presse/facturation-pour-la-releve-des-compteurs-ce-quil-faut-savoir ↩︎ 
- https://www.les-energies-renouvelables.eu/conseils/autoconsommation/autoconsommation-collective-energie-panneau-solaire-photovoltaique/ ↩︎ 
- https://wesmart.com/es/blog/autoconsommation-collective-france-2025 ↩︎ 
- https://www.energystream-wavestone.com/2025/06/ems-outil-cle-pour-la-performance-energetique-des-batiments-panorama-du-marche-francais/ ↩︎ 
- https://solaire-info.fr/wp-content/uploads/2024/09/Livreblancautoconsommation_collective.pdf ↩︎ 
- https://enogrid.com/europe-autoconsommation-collective-2025/ ↩︎ 
- https://www.pv-magazine.fr/2025/01/20/dossier-autoconsommation-le-collectif-monte-en-puissance/ ↩︎ 
- https://observatoire.enedis.fr/autoconsommation ↩︎ 
- https://wesmart.com/es/blog/autoconsommation-collective-france-2025 ↩︎ 
- https://www.myelectricity.fr/guide-autoconsommation-collective-photovoltaique/ ↩︎ 
- https://www.pv-magazine.fr/2025/01/20/dossier-autoconsommation-le-collectif-monte-en-puissance/ ↩︎ 
- https://wesmart.com/es/blog/autoconsommation-collective-france-2025 ↩︎ 
- https://enogrid.com/guide-de-lautoconsommation-collective-pour-les-bailleurs-sociaux/ ↩︎ 
- https://atee.fr/system/files/2025-04/ATEE_BFC_Conf%C3%A9rence_PV_Autoconsommation_collective%20-%2013.03%202.pdf ↩︎ 
- https://enogrid.com/guide-de-lautoconsommation-collective-pour-les-bailleurs-sociaux/ ↩︎ 
- https://atee.fr/system/files/2025-04/ATEE_BFC_Conf%C3%A9rence_PV_Autoconsommation_collective%20-%2013.03%202.pdf ↩︎ 
- https://solaire-info.fr/wp-content/uploads/2024/09/Livreblancautoconsommation_collective.pdf ↩︎ 
- https://enogrid.com/guide-de-lautoconsommation-collective-pour-les-bailleurs-sociaux/ ↩︎ 
- https://atee.fr/system/files/2025-04/ATEE_BFC_Conf%C3%A9rence_PV_Autoconsommation_collective%20-%2013.03%202.pdf ↩︎ 
- https://solaire-info.fr/wp-content/uploads/2024/09/Livreblancautoconsommation_collective.pdf ↩︎ 
- https://www.idex.fr/le-blog/autoconsommation-collective-une-solution-solaire-pour-les-entreprises ↩︎ 
- https://atee.fr/system/files/2025-04/ATEE_BFC_Conf%C3%A9rence_PV_Autoconsommation_collective%20-%2013.03%202.pdf ↩︎ 
- https://wesmart.com/es/blog/autoconsommation-collective-france-2025 ↩︎ 
- https://atee.fr/system/files/2025-04/ATEE_BFC_Conf%C3%A9rence_PV_Autoconsommation_collective%20-%2013.03%202.pdf ↩︎ 
- https://www.enedis.fr/sites/default/files/documents/pdf/autoconsommation-collective-guide-pedagogique.pdf ↩︎ 
- https://animergy.com/sans-obligation-achat-valoriser-production-pv/ ↩︎ 
- https://hubwatt.fr/vente-delectricite-en-autoconsommation-collective/ ↩︎ 
- https://wesmart.com/es/blog/autoconsommation-collective-france-2025 ↩︎ 
- https://www.ecologie.gouv.fr/sites/default/files/documents/Lab2051_Autoconsommation_collective_Incubation.pdf ↩︎ 
- https://solaire-info.fr/wp-content/uploads/2024/09/Livreblancautoconsommation_collective.pdf ↩︎ 
- https://enogrid.com/europe-autoconsommation-collective-2025/ ↩︎ 
- https://www.cre.fr/fileadmin/Documents/Deliberations/2024/241218_2024-231_Projet_Arrete_Autoconso_Collective.pdf ↩︎ 
- https://www.ecologie.gouv.fr/sites/default/files/documents/Lab2051_Autoconsommation_collective_Incubation.pdf ↩︎ 
- https://enogrid.com/turpe-7/ ↩︎ 
- https://solaire-info.fr/wp-content/uploads/2024/09/Livreblancautoconsommation_collective.pdf ↩︎ 
- https://www.twobirds.com/fr/insights/2025/france/nouvelles-règles-sur-les-prix-négatifs-de-l’électricité ↩︎ 
- https://www.les-energies-renouvelables.eu/conseils/photovoltaique/les-chiffres-essentiels-du-photovoltaique/ ↩︎ 
- https://wesmart.com/es/blog/autoconsommation-collective-france-2025 ↩︎ 
- https://hubwatt.fr/vente-delectricite-en-autoconsommation-collective/ ↩︎ 
- https://www.lechodusolaire.fr/enogrid-et-bohr-energie-sallient-pour-accompagner-les-producteurs-delectricite-vers-lautoconsommation-collective/ ↩︎ 
- https://www.innovation24.news/2025/01/21/enogrid-lautoconsommation-collective-pour-tous-partout-en-france/ ↩︎ 
- https://enogrid.com/enopower/ ↩︎ 
- https://enogrid.com ↩︎ 
- https://www.wattselse.com/entreprises/enogrid ↩︎ 
- https://enogrid.com/europe-autoconsommation-collective-2025/ ↩︎ 
- https://www.cre.fr/fileadmin/Documents/Deliberations/2024/241218_2024-231_Projet_Arrete_Autoconso_Collective.pdf ↩︎ 
- https://www.gossement-avocats.com/blog/autoconsommation-collective-publication-de-larrete-du-21-fevrier-2025-modifiant-les-criteres-dune-operation-dautoconsommation-collective-etendue-et-prevoyant-une-nouvelle/ ↩︎ 
- https://www.ecologie.gouv.fr/sites/default/files/documents/220803-Plan-mise-en-oeuvre-autorites-francaises.pdf ↩︎ 
- https://solaire-info.fr/wp-content/uploads/2024/09/Livreblancautoconsommation_collective.pdf ↩︎ 
- https://www.twobirds.com/fr/insights/2025/france/nouvelles-règles-sur-les-prix-négatifs-de-l’électricité ↩︎ 
- https://www.legifrance.gouv.fr/codes/id/LEGISCTA000032939883 ↩︎ 
- https://www.cre.fr/fileadmin/Documents/Deliberations/2024/241218_2024-231_Projet_Arrete_Autoconso_Collective.pdf ↩︎ 
- https://www.enedis.fr/media/1881/download ↩︎ 
- https://librairie.ademe.fr/energies/7854-autoconsommation-collective-photovoltaique-guide-pratique-a-l-attention-des-collectivites-territoriales.html ↩︎ 
- https://enogrid.com/guide-de-lautoconsommation-collective-pour-les-bailleurs-sociaux/ ↩︎ 
- https://solaire-info.fr/wp-content/uploads/2024/09/Livreblancautoconsommation_collective.pdf ↩︎ 
- https://enogrid.com/europe-autoconsommation-collective-2025/ ↩︎ 
- https://observatoire.enedis.fr/autoconsommation ↩︎ 
- https://www.enedis.fr/acceder-aux-donnees-fournies-par-enedis ↩︎ 
- https://www.ess-france.org/sites/default/files/Energie_Energie%20Partag%C3%A9e_France.pdf ↩︎ 
- https://energie-partagee.org/wp-content/uploads/2025/05/rapport-dactivite-2024.pdf ↩︎ 
- https://www.fnccr.asso.fr ↩︎ 
- https://uniprice-consulting.com/les-4-modeles-de-tarification-saas-trouver-le-bon-equilibre-pour-votre-croissance/ ↩︎ 
- https://stripe.com/fr/guides/atlas/business-of-saas ↩︎ 
- https://poyesis.fr/blogs/guide-strategies-pricing-saas/ ↩︎ 
- https://www.union-habitat.org/centre-de-ressources/energie-environnement/habitat-17-choisit-l-autoconsommation-collective-pour ↩︎ 
- https://www.greenunivers.com/2025/03/lautoconsommation-collective-delectricite-passe-a-5-mw-383304/ ↩︎ 
- https://www.banque-france.fr/system/files/2023-05/822288_livre_diip_v2.pdf ↩︎ 
- https://www.senat.fr/rap/r19-007-1/r19-007-11.pdf ↩︎ 
- https://www.strategie-plan.gouv.fr/files/files/Publications/2016 SP/2016-11-29 - Rapport La révolution numérique et logement/rapport-logement-vorms-11-2016_0.pdf ↩︎ 
- https://www.yele.fr/wp-content/uploads/Etude-Luciole-Yele-Consulting-FLEX.pdf ↩︎ 
- https://cler.org/partager-equitablement-les-benefices-des-projets-denergies-renouvelables-2/ ↩︎ 
- https://www.bnains.org/archives/communiques/Worldline/20180321_Document_de_reference_2017_Worldline.pdf ↩︎ 
- https://www.technavio.com/report/energy-management-systems-market-analysis ↩︎ 
- https://energie-partagee.org/prise-de-valeur-placement-energie-partagee-2024/ ↩︎ 
- https://investors.worldline.com/content/dam/investors-worldline-com/assets/documents/general-meeting/2020/worldline-document-d-enregistrement-universel-2019.pdf ↩︎ 
- https://www.gminsights.com/fr/industry-analysis/energy-management-system-ems-market ↩︎ 
- https://www.energie-solidaire.org/quand-les-dividendes-deviennent-solidaires/ ↩︎ 
- https://www.efeo.fr/uploads/docs/Rapport annuel 2014-2015.pdf ↩︎ 
- https://www.cre.fr/fileadmin/Documents/Rapports_et_etudes/2025/CRE_RA2024-en.pdf ↩︎ 
- https://energie-partagee.org/assemblee-generale-epa-2024/ ↩︎ 
- https://www.sieml.fr/wp-content/uploads/2017/06/fascicule_rapports_CoSy_Sieml_25AVRIL.pdf ↩︎ 
- https://www.nrjx.tech/blog/en-quoi-un-logiciel-ems-permet-doptimiser-ses-processus-industriels ↩︎ 
- https://www.consultations-publiques.developpement-durable.gouv.fr/IMG/pdf/02__projet_de_ppe_3.pdf ↩︎ 
- https://solairepv.fr/wp-content/uploads/SolairePVEnFranceV3.1.pdf ↩︎ 
- https://www.france-renouvelables.fr/wp-content/uploads/2024/10/Observatoire-Systeme-Electrique-Renouvelables-2024_Maj.pdf ↩︎ 
- https://www.optima-energie.fr/blog/actualites/prix-electricite-evolution/ ↩︎ 
- https://www.rte-france.com/donnees-publications/etudes-prospectives/futurs-energetique-2050 ↩︎ 
- https://www.zuora.com/fr/guides/saas-pricing-models/ ↩︎ 
- https://www.lechodusolaire.fr/les-enr-domineraient-le-mix-energetique-en-france-dici-2027-selon-globaldata/ ↩︎ 
- https://www.connaissancedesenergies.org/questions-et-reponses-energies/ou-le-solaire-photovoltaique-est-il-le-plus-developpe-en-france-metropolitaine ↩︎ 
- https://cpl.thalesgroup.com/fr/software-monetization/saas-pricing-models-examples ↩︎ 
- https://condorito.fr/saas-modele-economique/ ↩︎ 
- https://www.france-renouvelables.fr/wp-content/uploads/2025/10/OBSERVATOIRE_systeme_EnR_2025_VF.pdf ↩︎ 
- https://rte-futursenergetiques2050.com/scenarios/m1 ↩︎ 
- https://www.placedesenergies.com/professionnels/actualites/tendances-de-l-energie-08-07-2025 ↩︎ 
- https://openenergytracker.org/fr/docs/france/renewables/ ↩︎ 
- https://www.custup.com/tarification-abonnement-saas/ ↩︎ 
- https://www.regie-energis.com/distribution/wp-content/uploads/2022/12/Modele-de-convention-relative-a-la-mise-en-oeuvre-dune-operation-dautoconsommation-collective.pdf ↩︎ 
- https://observatoire-electricite.fr/systeme-electrique/article/le-developpement-de-l-autoconsommation ↩︎ 
- https://rouen.fr/sites/default/files/cm/2023-10-09/7-47ann1.pdf ↩︎ 
- https://www.gossement-avocats.com/blog/autoconsommation-collective-publication-de-l-arrete-permettant-des-operations-d-autoconsommation-collective-dans-un-rayon-de-20-km/ ↩︎ 
- https://www.cre.fr/electricite/autoconsommation.html ↩︎ 
- https://enotea.fr/autoconsommation-collective/ ↩︎ 
- https://www.statistiques.developpement-durable.gouv.fr/edition-numerique/chiffres-cles-energies-renouvelables/fr/14-solaire-photovoltaique- ↩︎ 
- https://www.cre.fr/fileadmin/Documents/Deliberations/import/180215-027_AUTOCONSOMMATION.pdf ↩︎ 
- https://www.auvergnerhonealpes-ee.fr/fileadmin/mediatheque_Cdr/Documents/ENR/Energie_photovoltaique/Photovoltaique-Autoconsommation-collective-synthese-012363.pdf ↩︎ 
- https://observatoire.enedis.fr/article/lautoconsommation-collective-dans-les-starting-blocks ↩︎ 
- https://www.urbanisme-puca.gouv.fr/IMG/pdf/rapport_final_vf.pdf ↩︎ 
- https://www.enedis.fr/combien-coute-et-rapporte-lautoconsommation-collective ↩︎ 
- https://observatoire-electricite.fr/systeme-electrique/article/les-dispositifs-de-soutien-publics-a-l-autoconsommation ↩︎ 
- https://adherents.energie-partagee.org/wp-content/uploads/2024/02/guide-acc-citoyenne-fevrier-2024-1.pdf ↩︎ 
- https://sonergy.fr/autoconsommation-collective-energie-partagee-locale/ ↩︎ 
- https://www.citepa.org/consommation-denergie-la-part-des-enr-a-progresse-de-13-points-en-france-depuis-2005-mais-reste-insuffisante-au-regard-des-objectifs-europeens/ ↩︎ 
- https://www.tresor.economie.gouv.fr/Articles/f6e70afa-7b97-4eaa-8ce3-892a4be60211/files/10caa42b-c3c8-44ca-8a6e-9847f4f55b34 ↩︎ 
- https://concertation-strategie-energie-climat.gouv.fr/sites/default/files/2024-11/241104_Projet%20de%20Programmation%20pluriannuelle%20de%20l’%C3%A9nergie%203%20VFF.pdf ↩︎ 
- https://www.rexecode.fr/conjoncture-previsions/veille-documentaire/document-de-la-semaine/la-banque-de-france-abaisse-ses-perspectives-de-croissance-2025-2027 ↩︎ 
- https://energie-partagee.org/wp-content/uploads/2024/09/eurobserver-etat-energies-renouvelables-2023.pdf ↩︎ 
- https://www.daf-mag.fr/reglementation-1243/fiscalite-2115/croissance-en-france-bruxelles-revoit-ses-previsions-a-la-baisse-23286 ↩︎ 
- https://www.papernest.com/demarches-energie/decrypter/mix-energetique-comparaison/ ↩︎ 
- https://contrepoints.org/previsions-de-croissance-2026-la-france-est-3e-sur-le-podium-des-plus-mauvais-eleves-europeens/ ↩︎ 
- https://www.statistiques.developpement-durable.gouv.fr/les-energies-renouvelables-en-france-en-2024-dans-le-cadre-du-suivi-de-la-directive-ue-20182001 ↩︎ 
- https://www.banque-france.fr/fr/publications-et-statistiques/publications/projections-macroeconomiques-intermediaires-septembre-2025 ↩︎ 
- https://enogrid.prezly.com ↩︎ 
- https://www.notre-environnement.gouv.fr/actualites/breves/article/l-energie-en-france-et-dans-le-monde-deux-bouquets-bien-differents ↩︎ 
- https://www.assemblee-nationale.fr/dyn/dyn/contenu/visualisation/1087987/file/PAP2026_BG_Investir_France_2030_AV.pdf ↩︎ 
- https://www.lechodusolaire.fr/enogrid-deploie-une-suite-logicielle-complete-pour-lautoconsommation-collective/ ↩︎ 
- https://ec.europa.eu/eurostat/web/interactive-publications/energy-2025 ↩︎ 
- https://www.miedepain.asso.fr/wp-content/uploads/2012/09/MANUEL_VF-_maquette-web.pdf ↩︎ 
- https://doc.vayandata.com/documentation-active/51.2.0.5/enedis ↩︎ 
- https://programme-cee-actee.fr/wp-content/uploads/2024/02/CDC-AAP-AMO-CPE-VF_2024_14_03-1-1.pdf ↩︎ 
- https://www.edf.fr/collectivites/faq/facture/gerer-votre-facture/comment-automatiser-le-traitement-de-vos-donnees-de-facturation ↩︎ 
- https://programme-cee-actee.fr ↩︎ 
- https://www.centre-val-de-loire.ars.sante.fr/media/1633/download ↩︎ 
- https://www.fnccr.asso.fr/article/guide-fnccr-cot-cop-pour-les-projets-enr-thermiques-des-territoires/ ↩︎ 
- https://www.enerplan.asso.fr/dl-fichier-actualite?media=41896 ↩︎ 
- https://www.deepki.com/fr/blog/compteurs-linky-exploiter-donnees/ ↩︎ 
- https://www.ville-thonon.fr/service-public/particuliers?xml=F71 ↩︎ 
- https://community.gladysassistant.com/t/integration-enedis-linky/7470 ↩︎ 
- https://www.facebook.com/FimecoWalterFrance/posts/-exclure-un-membre-dune-association-attention-à-bien-respecter-ses-droits-un-rap/1508715047100238/ ↩︎ 
- https://www.strategie-plan.gouv.fr/files/2025-02/HE_Broschure_FR_act.pdf ↩︎ 
- https://priips.predica.com/credit-agricole/PS_LU1900068914.pdf ↩︎ 
- https://github.com/consometers/data-connect ↩︎ 
- https://www.ccomptes.fr/sites/default/files/2024-03/20240312-RPA-2024-ENPA-gestion-trait-de-cote.pdf ↩︎ 
- https://www.pv-magazine.fr/2025/03/10/lautoconsommation-collective-etendue-a-5-mwc/ ↩︎ 
- https://www.lechodusolaire.fr/autoconsommation-collective-un-bond-en-avant-avec-le-seuil-porte-a-5-mw/ ↩︎ 
- https://www.budget.gouv.fr/documentation/file-download/21111 ↩︎ 
- https://www.seban-associes.avocat.fr/modification-des-criteres-de-lautoconsommation-collective-etendue/ ↩︎ 
- https://www.sde35.fr/sites/default/files/2024-07/SDE35-RA-2023.pdf ↩︎ 
- https://www.hlm.coop/actualites/24/18892 ↩︎ 
- https://www.apem-energie.fr/🚨-nouvelle-evolution-pour-lautoconsommation-collective-en-france-🚨/ ↩︎ 
- https://journals.openedition.org/metropoles/11977 ↩︎ État 2025, Leviers de Marché & Plan de Simplification (2026–2030) Stockage & Autoconsommation Collective Arrêté 21 février 2025 — ACC (5MW_10MW, rayon, mod