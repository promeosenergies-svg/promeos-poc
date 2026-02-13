Stockage & Autoconsommation Collective 

# 

# Dossier Complet : Stockage & Autoconsommation Collective (B2B, France/Europe) 

## Executive Summary 

10 idées clés : 
- Le stockage n’est JAMAIS obligatoire pour une ACC, mais il devient pertinent dès lors que les profils PV/conso sont désynchronisés (surplus midi, besoin soir/nuit) et que le coût d’investissement batterie peut être amorti sur 8-12 ans. 1 
- Trois scénarios justifient un stockage ACC : (i) désynchronisation production-consommation > 30%, (ii) contrainte injection réseau (limitation GRD), (iii) objectif de résilience/indépendance local (backupautonomy). 
- En France 2025 , le cadre réglementaire change radicalement : fin ARENH (décembre 2025), TURPE 7 (août 2026) avec tarifs injection-soutirage localisés, obligation mFRR > 10 MW (2026) — tous ces éléments modifient la rentabilité batterie. 2 3 
- Technologie cible : Batterie Li-ion (LFP 85%, NMC 15%) avec durée de stockage 2–4h pour ACC (coût 100–150 €/kWh CAPEX en 2025, décroissance -10%/an attendue). Alternatives (sodium-ion, flow) restent minoritaires et plus chères. 4 
- Dimensionnement cible : 10–30% de la puissance PV installée en kW batterie, 0.5–2 kWh par kWc PV selon profil conso. Typiquement, une ACC 100 kWc avec 40% de surplus midi → 20–30 kW / 10–20 kWh suffisent. 
- Deux modèles propriété dominants : (i) batterie propriété collective (investissement PMO ou financement tiers), (ii) batteries réparties chez certains participants (pooling/agrégation virtuelle). Battery-as-a-Service encore marginal en France. 
- Enjeux ACC avec stockage : comptage (impact clés de répartition si batterie = consommateur virtuel), règles de gouvernance (qui finance, qui récupère), conformité GRD/Enedis (raccordement, anti-îlotage, mesure). La complexité administrative peut annuler le gain technique. 
- Indépendance énergétique = mythe pour batterie courte durée . Une batterie 4–8 kWh peut couvrir 2–4 heures d’autonomie seulement (nuit = 8–10h). Besoin de saisonnalité exige 50–100× plus (hydrogène, STEP, oversizing). Batterie seule = autonomie locale, pas indépendance. 
- Business model ACC + stockage : revenus empilables = autoconsommation (ΔE × tarif local) + peak shaving (réduction TURPE) + RES potentiel (si > 100 kWh, participation mFRR). Rentabilité : seuil 30–40 k€/an en économies brutes pour justifier 100 k€ CAPEX batterie. 
- Risques réglementaires majeurs : (i) évolution tarifs grid (TURPE ajustement annuel), (ii) règles ACC (changement clé répartition par décret), (iii) batteries = ICPE si > puissance (exigences sécurité/assurance), (iv) cyber/données énergétiques (NIS2). 

→ GO/NO-GO décision : Stockage OK si (i) surplus PV > 25%, (ii) budget CAPEX ≥ 80 k€, (iii) gouvernance ACC clarifiée, (iv) objectif TAc/TAp/résilience défini. Sinon, NO-GO. 

## A. Contexte & Drivers du Stockage 

### A.1 Pourquoi le Stockage Devient Clé en 2025-2026 

La trajectoire française subit trois chocs simultanés : 

Fin ARENH (31/12/2025) : accès régulé au nucléaire disparaît → 100% prix de marché spot pour l’électricité en 2026. Volatilité prix attendue : -20 € à +150 €/MWh selon heures [Les Échos – Marché électricité 2025]. Corollaire : les heures bas prix (midi PV, nuit creux) intéressent fortement pour arbitrage ou recharge batterie. 

TURPE 7 août 2026 : CRE remplace les tarifs de soutirage/injection par un nouveau barème injection-withdrawal qui paie les batteries pour décharger en hiver (pics) ou charger en été (surplus PV). Incitation directe au stockage, surtout si localisé dans zone « injection » (souvent rurale/PV). 5 6 

Obligation mFRR > 10 MW (2026) : tous producteurs solaires/éoliens > 10 MW doivent participer au balancing national. Corollaire pour ACC : une batterie > 1 MW peut devenir actif de balancing et générer revenus flexibilité (~10–20 k€/an en France selon taille). 7 

Électrification usages : montée IRVE (bornes recharge, 100 000+ en 2025), PAC (chauffage), qui créent pics de puissance. Batterie + ACC = lissage local puissance souscrite → economies TURPE. 

### A.2 Clarifications Concepts : TAc, TAp, Autonomie, Indépendance 

Terminologie souvent confuse : Concept Définition Portée Batterie Taux d’Autoconsommation (TAc) kWh produits localement consommés sur site / kWh produits × 100 Batterie améliore TAc de 10–30% (ex : 50% → 70%), sauf si ACC sans batterie > 40% déjà Taux d’Autoproduction (TAp) kWh produits localement / kWh consommés × 100 TAp indépendant batterie (défini par PV puissance), mais batterie rend le TAp utilisable (décale production midi → conso soir) Autonomie de durée Temps couverture conso sans approvisionnement externe (heures) Batterie 4 kWh → 4h autonomie (cas typique ACC sur 1 kW conso). Suffit nuit locale (20h non-prod PV), pas assez saisonnalité Indépendance énergétique Couvrir 100% conso annuelle sans réseau Impossible batterie seule : exige oversize saisonnier (jours forts hiver) = 50–100× batterie court-terme. Hybridation hydrogène/STEP ou réseau incontournable 

Point critique : beaucoup de porteurs ACC confondent TAc/autonomie et imaginent que batterie 10 kWh offre 10 h autonomie. En réalité, si ACC 50 kW pics, 10 kWh = 12 min seulement ! Clarifier le besoin (pic vs décalage temporel) dès le départ. 

### A.3 Contexte Réglementaire France ACC 2025 

Cadre légal : Décret 2017-676 (ACC), décret 2023-256 (approche PMO), ordonnance 2023-1110 (Electricity Directive transposition). Règles clés : 
- Rayon 2 km maximal entre producteur/consommateur (en ligne électrique, pas vol d’oiseau) 
- Points de livraison multiples (> 1 production, > 1 conso) → repartition via clé (fixe ou dynamique mensuelle) 
- Personne Morale Organisatrice (PMO) responsable administratif/fisc 
- Mesure 15 min par point via Linky (quasi-temps réel Enedis API) 
- GRD Enedis approuve ACC, gère comptage/facturation par participant (en France UTE/distribution) 

Pas de stockage prévu nativement dans réglementACC : batterie = actif externe pilotable (EMS peut la charger/décharger) mais comptage reste au PDL (point de livraison). Schéma de raccordement = clé : batterie en arrière-compteur (derrière producteur) vs batterie sur réseau commun vs batterie chez consommateur. 

## B. Stockage : Technologies & Benchmark 

### B.1 Comparatif Technologique Multi-Critères Technologie CAPEX (€/kWh) Rendement (%) Durée idéale Cycles Cycle de Vie (ans) Avantages Limites Applicabilité ACC B2B Li-ion LFP 100–150 93–96 2–4 h 5000–8000 12–15 Densité, sûr, baisse prix rapide Coût initial, thermique ✅ RÉFÉRENCE 2025 Li-ion NMC 120–180 91–94 1–2 h 3000–5000 10–12 Ancien, connu, intégration Perte rapide, moins sûr, coûteux ⚠️ Transition LFP Sodium-ion 150–200 90–92 2–4 h 4000–6000 10–12 Abondant, recyclable, sûr Coût 30–40% + cher, moins dense ⛔ Niches industrielles Flow (Vanadium) 180–250 75–80 4–8 h+ 12000+ 20+ Long terme, décorrelé kWh, gestion chauffage Volumineux, coût initial, maintenance ⛔ Grands systèmes (MWh) Plomb (traditionnel) 60–80 85–90 0.5–2 h 800–1500 5–7 Pas cher, recyclable Lourd, toxique, obsolète ❌ À ÉVITER Supercapacitors 1000–5000 95 Secondes-minutes 1 000 000+ 10–20 Ultra-puissance, durée infinie Très cher €/kW, mini-capacité ⛔ Lissage pics nanosecondes Stockage thermique (ballons glace, TES) 20–50 80–95 Heures-jours ∞ 20+ Couplage CVC/génie climatique, bas coût Bâtiment-dépendant, peu flexible ⚠️ Niche tertiaire GTB Hydrogène vert 500–2000 25–40 Heures-jours 1000+ 15–20 Saisonnalité, industrie, multi-usages Perte énergétique, CAPEX très élevé, immaturité ⛔ Horizon 2030+ Batterie automobile V2G/V2B 100–150 (partagée) 92–96 1–4 h 5000+ (dégradation lente) 8–10 dans bâtiment Vecteur autre (mobilité), flexibilité, résilience Temps recharge limité, batterie vieillissante ⚠️ Cas IRVE + ACC 

Conclusion techno : LFP Li-ion = standard 2025 pour ACC B2B, coût juste en-dessous du seuil de rentabilité 1000 €/kWh systèmes, amélioration rapide (-10%/an LCOE). 

### B.2 Règles de Dimensionnement 

Inputs requis (obligatoires) : 
- Courbes PV 15 min sur 1–2 ans (Pmax kW, TAp cible %) 
- Profils conso 15 min par participant (Pmoyenne, pics) 
- Règles ACC (clé répartition fixe/dynamique ?) 
- Enedis info : limite injection réseau, tarifs TURPE 7 zone 
- Budget CAPEX disponible 
- Objectif : TAc (%), Wh décalé (kWh), pic puissance (kW), indépendance nuits (h) 

Méthode heuristique rapide (1 page) : 
- Calcul surplus PV mensuel : Pprod,mois – Cconso,mois = Esurplus,mois 
- Identification heures « gaspillées » : Esurplus qui n’a pas de conso (injection > 25% conso) 
- Batterie kWh min : 0.1–0.3 × Esurplus,mois (25–30% des surplus stockés, reste injections) 
- Batterie kW puissance : 20–30% × Pprod,max (charge/décharge rapide à midi/soir, pas undersized) 
- Scénario sensibilité : varié tarif batterie (100, 130, 170 €/kWh) → ROI 8, 10, 12 ans ? 
- Décision GO : Si TAc final > objectif + ROI < 10 ans → OK. Sinon → batterie surdimensionnée ou ACC déjà optimisé. 

Exemple numérique : 
- ACC 80 kWc, 50 kWh/j conso moyenne → TAp = 60–70% 
- Surplus détecté : 30 kWh/j mid-day, 0 kWh night 
- Batterie recommandée : 10–15 kWh (33–50% surplus), 25 kW (puissance) 
- Coût : 15 kWh × 130 €/kWh + 25 kW × 400 €/kW (onduleur/install) = 1950 + 10k = ~12 k€ total (si integration, 10–15 k€) 
- ROI : si gain 2500 €/an (TAc amélioration 15%, TURPE baisse) → 4–5 ans payback ✅ 

### B.3 Schémas Raccordement : Où Placer la Batterie ? 

Trois architectures (impacts sur comptage/facturation) : 

Cas 1 : Batterie « côté producteur » (derrière onduleur) Panneaux PV → Onduleur → Batterie+Convertisseur → Compteur GRD (1 PDL)
 ↓
 Réseau interne ACC 

✅ Avantage : une batterie centralise, simple opération, optimisation claire (charge/décharge pilotable) 
❌ Inconvénient : si producteur = 1 entité, tout surplus dépend de sa batterie (mutuabilité réduite) 
→ Applicable : ACC petit (1 producteur majeur, 3–5 consommateurs) ou communautaire propriétaire batterie 

Cas 2 : Batterie « commune » sur site (en parallèle réseau ACC) Pandeaux → Onduleur → Compteur prod (PDL1)
 ↓
 Batterie + EMS
 ↓
Consommateurs (PDL2, PDL3...) ← Compteur conso
 ↓
 Réseau → Enedis 

✅ Avantage : batterie partagée, facile d’ajouter consommateurs ACC, EMS pilote carga optimisée 
❌ Inconvénient : comptage complexe (batterie ne doit pas rompre la clé de répartition), raccordement électrique lourd 
→ Applicable : ACC multi-sites (école + mairie + bâtiment tiers) avec batterie poolée 

Cas 3 : Batteries réparties (chez certains participants, agrégation virtuelle) Site A (PV + batterie 5 kWh) ← Virtuel VPP → Compte Agent
Site B (Conso) ← Virtuel VPP
Site C (PV + batterie 8 kWh) ← Virtuel VPP

EMS centralisé pilote toutes batteries en temps réel (MQTT/API) 

✅ Avantage : flexibilité, résilience site-by-site, facile scaling (ajouter batterie à un site = autonomie) 
❌ Inconvénient : synchronisation complexe, perte réseau (transmission données, algorithme), coût EMS élevé 
→ Applicable : ACC multi-sites large (10+), secteur industriel, PME dispersées 

Schéma recommandé B2B ACC : Cas 2 (batterie commune + EMS local), moins coûteux en data/cyber, plus transparent pour Enedis. 

## C. Où le Stockage Est Pertinent (10 Cas d’Usage Classés par Valeur) 

### C.1 Les 10 Cas Positifs (GO Stockage) 

Cas 1 : Désynchronisation PV↔︎Conso > 30%, pics puissance élevés 
- Symptômes : surplus midi > 50 kWh/jour, conso soir > conso jour, pics > 30 kW (IRVE, PAC) 
- Objectif : TAc +20%, réduction pics puissance (TURPE baisse) 
- Batterie recommandée : 20–30 kWh (couvrir 3–4 h conso soir), 30–40 kW (lissage pics) 
- Rentabilité : breakeven 7–9 ans (TAc + peak shaving + TURPE 7), seuil 40 k€/an gains 
- Exemple : Ombrière parking 60 kWc + terminal logistique (conso 50 kWh/j, pics midi 45 kW) → batterie 25 kWh / 40 kW GO . 

Cas 2 : Contrainte Injection Réseau (limitation GRD, saturation) 
- Symptômes : GRD plafonne injection à 20 kW (au-delà, coûts raccordement très élevés ou refus), PV 100 kWc → surplus 50 kW injecté 
- Objectif : consommer sur site max, réduire injection (éviter frais extension réseau) 
- Batterie recommandée : 15–20 kWh de « tampon » injection (réduire pics exports > seuil) 
- Rentabilité : très favorable si économie raccordement > 50 k€ (souvent le cas rural), payback 4–5 ans 
- Exemple : Ferme + CUMA 120 kWc en zone blanche, GRD limite injection 30 kW → batterie 18 kWh GO (avoid 100 k€ renforcement câble). 

Cas 3 : Opportunités Prix Dynamiques (arbitrage minute/heure) 
- Symptômes : prix spot < 0 €/MWh certaines heures (dumping PV), prix pic 20h > 200 €/MWh (contr…) 
- Objectif : charger heures négatives, décharger heures chères → arbitrage marginal 50–100 €/jour 
- Batterie recommandée : 8–12 kWh (arbitrage court-terme, cycles rapides) 
- Rentabilité : 5–8 k€/an revenu arbitrage (marginal, additionnel à TAc), payback 15–20 ans seul. Pertinent seulement si + TAc . 
- Exemple : ACC trader-friendly (participant ingénieur PV) qui optimise prix → Revenu arbitrage +5 k€/an MARGINAL , mais GO si déjà TAc. 

Cas 4 : Réduction Curtailment / Limitation PV (politique GRD) 
- Symptômes : RTE/Enedis impose limitation PV certaines heures (20:00–22:00 t par ex.), perte production > 10 MWh/an estimée 
- Objectif : stocker production « perdue » en période limitation, vendre/consommer après 
- Batterie recommandée : 12–18 kWh (couvrir 2–3h limitation), 20 kW 
- Rentabilité : revenu 3–8 k€/an selon règles limitation locale. GO si limitation > 5% annuel . 
- Exemple : Région Occitanie, zone saturée PV, ACC subit délestage 1–2 h/j été → batterie 15 kWh GO pour capturer perte. 

Cas 5 : Continuité d’Activité / Résilience (backup électricité) 
- Symptômes : site critique (données, santé, production temps-réel) qui ne tolère pas coupure > quelques secondes 
- Objectif : batterie = onduleur long-terme (4–8 h autonomie), secours en cas défaut réseau 
- Batterie recommandée : 20–40 kWh (couvrir nuit complète si nécessaire), puissance 5–10 kW (lisse transition) 
- Rentabilité : coût d’assurance/PRA dégression (batterie réduit exposition perte > 100 k€/h). ROI indirect via réduction sinistre. 
- Exemple : Cabinet médical, datacenter, usine production 24/7 → batterie 30 kWh GO priorité (résilience critère, pas prix). 

Cas 6 : Couplage IRVE (lissage + limitation puissance raccordement) 
- Symptômes : 20+ bornes recharge à site, pics simultanés 80–120 kW dépassent souscription (36 kW ex.), frais dépassement élevés 
- Objectif : batterie + EMS pilote bornes intelligemment, lisse pics, stocke PV midi → recharge nuit heures creuses/ACC 
- Batterie recommandée : 25–40 kWh (buffer charge progressive), 30–50 kW (pics borne) 
- Rentabilité : économie TURPE dépassement 20–40 k€/an , gain autoconso 10–15 k€/an → breakeven 4–6 ans 
- Exemple : Parking 30 places + bureaux 50 kWc PV → batterie 35 kWh/40 kW GO (couplage VE + solaire + ACC). 

Cas 7 : Couplage CVC / Stockage Thermique + Batterie (pilotage GTB flexible) 
- Symptômes : bâtiment tertiaire 3000 m², GTB déjà installée, PAC réversible (chaud/froid), ballons eau chaude 500 L inerte 
- Objectif : batterie électrique 5–10 kWh + 20–50 kWh thermique (glace, ballon) → cumul décale charges flexibles CVC 
- Batterie recommandée : 8 kWh Li-ion (gestion PAC), couples stockage thermique via EMS (charge ballon midi, décharge nuit) 
- Rentabilité : cumul ΔE + TURPE + confort thermique → ROI 6–8 ans. Excellente rentabilité si GTB déjà payée . 
- Exemple : Hôpital, campus université 100 kWc PV → batterie 8 kWh électrique + TES 30 kWh thermique GO (synergie). 

Cas 8 : Communauté Multi-Sites Avec Profils Complémentaires (lissage smart) 
- Symptômes : ACC 5 sites (école jour, hôtel nuit, PME jour/nuit, bâtiment adm jour, ferme sporadic), courbes inverses (école jour = hôtel nuit) 
- Objectif : batterie mini (5–10 kWh) suffit car complémentarité naturelle → lisse ACC à 70–80% auto-conso sans batterie, batterie finalise 15% gap 
- Batterie recommandée : 8–12 kWh seulement (effet pooling économies) 
- Rentabilité : très favorable, batterie petit CAPEX (10 k€) pour 20 k€/an gains → payback 5 ans ou moins . 
- Exemple : Bourg rural 5 entités, PV partagée 50 kWc, profils écart 12h → batterie 10 kWh GO (effet naturel mutualisation). 

Cas 9 : Optimisation Clé de Répartition (équité vs performance, dynamique) 
- Symptômes : ACC avec clé fixe statique (ex. 50/50 deux sites) mais production/conso dérives au fil mois → surplus surtaxé, déficit surpénalisé 
- Objectif : batterie + clé de répartition dynamique (algorithmique, optimisée IA chaque jour) → capture différences → finance batterie. 
- Batterie recommandée : 5–8 kWh (tampon algorithme, pas besoin grosse batterie) 
- Rentabilité : gain équité 10–20% vs clé fixe (moins conflits), batterie auto-finançable par écono redistribution . ROI variable mais possible. 
- Exemple : ACC collectivité complexe (école matin/soir, bâtiment admin 9–17h, PAB 24/7) → batterie 6 kWh + EMS clé smart GO (gouvernance améliorée). 

Cas 10 : Valorisation Flexibilité (participation mFRR, services réseau si > 1 MW batterie) 
- Symptômes : ACC grande (500+ kWc PV, multi-sites tertiaire/industrie) + batterie 100+ kWh → peut devenir actif services RTE, mFRR participation 
- Objectif : batterie offre services flexibilité (mFRR secondaire, capacité, freq response) → revenu 10–30 k€/an (certains cas) 
- Batterie recommandée : 50–150 kWh (agrégatrice) pour justifier overhead administratif mFRR 
- Rentabilité : revenu flexibilité additionnel 15–25 k€/an (si certifié VPP, BEEM agent), ROI 4–6 ans combiné TAc + services. 
- Exemple : Zone industrielle 300 kWc PV + 100 sites participants → batterie 80 kWh centralisée GO (revenu mFRR + TAc). 

### C.2 Les 6 Cas Négatifs (NO-GO Stockage) 

Cas 1 : Profil Conso/PV Déjà Très Aligné (TAc naturel > 60% sans batterie) 
- Symptômes : ACC maison 9–17h tertiaire bureaux (pic conso = pic PV midi), TAc mesuré 65–75% déjà sans batterie 
- Problème : batterie apporte gain marginal < 10% TAc (60% → 68%), ROI > 15 ans → NO-GO 
- Décision : Invest plutôt énergie directe (baisse conso, PV supplémentaire) que stockage. 
- Exemple : Bâtiment admin+école (9–17h, midi conso/prod sync) → TAc déjà 70% → NO batterie . 

Cas 2 : CAPEX Batterie Trop Élevé vs Gain Marginal 
- Symptômes : ACC petit 20 kWc, surplus 5 kWh/j seulement → batterie minimale 4 kWh recommandée (500 € coût minimal), ROI > 20 ans 
- Problème : overhead CAPEX (onduleur, câblage, permit, commissionning) = 3–5 k€ minimum. Gain brut 2 k€/an → payback 2.5+ ans juste pour batterie → NO-GO économique . 
- Décision : Ignorer stockage, maximiser conso directe (gestion temps charge/décharge manuelle). 
- Exemple : Petit bâtiment tertiaire 20 kWc, conso 15 kWh/j (TAc déjà 50%) → NO batterie , gain marginal faible. 

Cas 3 : Besoin d’Autonomie Saisonnière (jours/semaines à couvrir) sans stockage long-terme 
- Symptômes : demande client “autonomie 10 jours hiver sans production PV” (jour décemb~ 8 h/jour, conso 200 kWh) 
- Problème : batterie 200 kWh = 26 k€ + onduleur 50 k€ = 76 k€+ , ROI 20+ ans impossible. Hydrogène/STEP/hybride seul viable. 
- Décision : NO batterie seule → Proposer hybride (batterie court 1–2 j + hydrogène saisonnier) ou accepter réseau. 
- Exemple : ACC rural demande 90% indépendance → NO Li-ion , faut STEP ou oversize x100 (économiquement fou). 

Cas 4 : Contraintes Espace/Sécurité/Assurance Trop Fortes 
- Symptômes : ACC en immeuble collectif urbain dense (pas place rez-de-chaussée < 50 m²), batterie classée ICPE si > 200 kW, assurance +30 k€/an 
- Problème : coût non-technique (place, permis ICPE, assurance) > bénéfice énergétique. 
- Décision : NO batterie → Mieux utiliser toiture pour PV supplémentaire. 
- Exemple : Immeuble Paris 75, ACC 5 appart, batterie inenvisageable → NO (espace + assurance prohibitif). 

Cas 5 : Complexité Gouvernance ACC > Bénéfice (conflits partage valeur) 
- Symptômes : ACC 10 participants hétérogènes (3 producteurs, 7 consommateurs) → débat “qui finance batterie? qui profite?” sans accord 
- Problème : transaction cost juridique, gouvernance 20+ réunions pour 5 k€/an gain → temps/argent gaspillé . 
- Décision : NO batterie → Rester ACC simple statique (clé proportionnelle annuelle), éviter complexité. 
- Exemple : ACC multi-propriétaires sans gestionnaire unique → NO batterie , trop d’enjeux équité. 

Cas 6 : Comptage/Contrats Rendant Montage Lourd Sans Bénéfice Immédiat 
- Symptômes : ACC comprend un pôle de recharge électrique (GRD impose compteur dédié non-mutualisable), batterie = “consommateur fantôme” complexe à facturer 
- Problème : coût rectification contrats Enedis, modification clé répartition, audit +5 k€ vs gain 2 k€/an → NO-GO admin . 
- Décision : NO batterie tout en attendant évolution réglementaire (Enedis API plus ouverte). 
- Exemple : ACC hétérogène (industrie + bornes recharge + tertiaire) → rectification contrats trop coûteuse → NO batterie (pour maintenant). 

## D. Dimensionnement : Méthode Complète 

### D.1 Inputs Obligatoires (Checklist Data) Élément Source Format Utilité Courbes PV brutes Onduleurs, inverters CSV 15 min (puissance W) Calcul surplus, dimensionnement Courbes conso brutes Linky API Enedis ou compteurs CSV 15 min (kWh) par participant Alignement profil, clé répartition Année historique 12 mois min. Données représentatives Variance saisonnière Puissance souscrite site Contrat Enedis kW Dépassement coûts Tarifs Enedis (TURPE 7) CRE/Enedis tarif €/kWh soutirage, injection par zone ROI calc. Règles ACC (clé) Statuts PMO, décision admin % ou algorithme Comptabilité batterie Contrainte injection GRD Enedis lettres techniques kW limité Peak shaving necessity Localisation (adresses, lat/long) Google Maps Coordonnées Rayon 2 km validations Objectif client Réunion stakeholders TAc %, autonomie h, pics kW, budget Scope batterie 

### D.2 Processus de Dimensionnement (Étapes 1-6) 

Étape 1 : Nettoyage Données & Calculs Basiques - Éliminer anomalies (0 W nuit erreur, pics outliers)
- Calculer PV moyen jour/mois, conso idem
- TAp = sum(PV) / sum(Conso) × 100
- TAc brut sans batterie = min(PV prod 15-min, Conso 15-min) / PV × 100
 (= part PV autoconsommée sur place, sans décalage) 

Étape 2 : Identification Besoins Stockage Surplus horaire = max(0, PV(t) - Conso(t))
Deficit horaire = max(0, Conso(t) - PV(t))

Surplus journalier = sum(Surplus horaire)
Deficit décalé soir/nuit = sum(Deficit 20:00-07:00)

Ratio = Surplus journalier / Conso journalière
Si Ratio > 30 % : stockage pertinent 

Étape 3 : Calcul Batterie kWh (Capacité) Batterie kWh min = 0.15 × Esurplus,mois,max
 (stock 15% des surplus pointe, reste injection)

Batterie kWh mid = 0.25 × Esurplus,mois,max
 (stock 25%, ~optimal)

Batterie kWh max = 0.40 × Esurplus,mois,max
 (stock 40%, oversized, ROI marginal)

Sélection : kWh mid, valider ROI après 

Étape 4 : Calcul Batterie kW (Puissance) Batterie kW min = 0.15 × PV_max
 (15% puissance crête, lissage léger)

Batterie kW mid = 0.25 × PV_max
 (25%, lissage significatif)

Batterie kW max = 0.35 × PV_max
 (35%, lissage agressif, cher)

Sélection : kW mid, vérifier pas undersized pour charge/décharge
rapide (ex. 4h cycle → kW ≥ kWh/4) 

Étape 5 : Calcul ROI / LCOE CAPEX batterie = kWh × 130 €/kWh + 25 k€ (onduleur install) + 5 k€ (EMS)
OPEX = 1.5 % CAPEX/an (maintenance, assurance)

Bénéfice annuel brut =
 + TAc amélioration (ΔkWh × tarif local 0.08–0.12 €/kWh)
 + TURPE baisse (réduction dépassement, injection smarte)
 + Services RES (mFRR si applicable, 10–20 k€/an)
 + Résilience (pondération interne)
 - OPEX

ROI payback = CAPEX / Bénéfice annuel net

Go si ROI < 10 ans, Prudence si 10–15 ans, NO-GO si > 15 ans 

Étape 6 : Sensibilités et Scénarios Variances clés :
- Coût batterie -10 % (120 €/kWh) → payback -1.5 ans
- Coût batterie +20 % (156 €/kWh) → payback +2 ans
- Tarif local électricité -5 % → payback +1.5 ans
- Tarif local +5 % → payback -1.5 ans
- Cycles batterie -20 % (charge moins souvent) → revenu décalé
- TURPE 7 impact +50 % (injection smarte récompensée) → payback -2 ans

Réaliser courbe sensibilité 2D (CAPEX × Tarif) pour clarté décision. 

### D.3 Tableau de Décision Simplifié (1 page) Profil ACC TAc sans batterie Surplus % conso Pics puissance Budget disponible Décision Batterie recommandée Petit tertiaire jour (20 kWc, 15 kWh/j conso) 55% 20% 8 kW 15 k€ ⚠️ MARGINAL 3–4 kWh si budget, sinon NON Multi-sites complémentaires (50 kWc, 5 entités, 40 kWh/j) 65% 25% 12 kW 30 k€ ✅ OUI 8–10 kWh / 12 kW Tertiaire désynchronisé (60 kWc, pic midi > pic soir) 40% 45% 30 kW 50 k€ ✅ OUI 15–20 kWh / 25 kW IRVE + ACC (100 kWc + 20 bornes) 50% 40% 70 kW pics 80 k€ ✅ OUI 30–40 kWh / 50 kW Industrie 24/7 résilience critique 35% 50% 150 kW 200 k€ ✅ OUI PRIORITAIRE 50–80 kWh / 80 kW + UPS Maison occupée soir mainly 75% 15% 3 kW 8 k€ ❌ NON Aucune (coût trop élevé) Ferme avec limitation GRD (120 kWc, plafond 30 kW) 20% 60% (injection bloquée) 80 kW 40 k€ ✅ OUI 20–25 kWh / 30 kW (limit) Collective complexe 10 entités (80 kWc) 50% 28% 15 kW 25 k€ ⚠️ DÉBAT GOUVERNANCE Si accord : 8–12 kWh, sinon NON 

## E. Business Models & Monétisation 

### E.1 Propriété Batterie : Trois Approches 

Modèle 1 : Batterie Propriété PMO/Collective PMO achète batterie 12 k€, amortit sur 10 ans → coût 1.2 k€/an (payroll)
Charge/décharge piloté par EMS commun
Fonds amortissement via cotisations ACC (quote-part par participant,
ou % économies réalisées)
Coût additionnel participant ~50–100 €/an 

✅ Transparence, mutualisation complète, gouvernance claire 
❌ Besoin budget initial collectif, risque défaut si PMO insolvable 
→ Recommandé : ACC publiques (collectivité, bailleur), mutuelles stables 

Modèle 2 : Batterie Tierce Détention (Battery-as-a-Service, BaaS) Prestataire finance batterie 12 k€, facture ACC 200–250 €/mois (15–20 ans)
BaaS opérateur offre garantie rendement, maintenance, remplacement
Revenus = loyer + partage gains flexibilité (if mFRR)
PMO reste gestionnaire ACC/clés, BaaS pilote batterie 

✅ Pas CAPEX pour ACC, risque financier transféré, performance garantie 
❌ Coût 200–250 €/mois x 180 mois = 36–45 k€ total >> achat direct (12 k€), marge BaaS ~200% 
→ Recommandé : ACC petit/PME, aversion risque, pas trésorerie 
→ Marché en croissance France 2025 (Effy, Engie Storage, agrégateurs) 

Modèle 3 : Batteries Distribuées (Propriété Participants Multiples) Site A propriétaire batterie 5 kWh (2 k€ budget), Site B batterie 8 kWh (3 k€)
EMS centralisé agrège/optimise (Agregio-type ou interne)
Chaque batterie reste propriété site (déductibilité fiscale indépendante)
Facturation ACC = % autoconsommation partagée + services flexibilité distribués 

✅ Décentralisation risque, résilience site-by-site, investissements modulables 
❌ Synchronisation complexe, perte réseau transmission (cyber), coût EMS élevé (5–10 k€) 
→ Recommandé : ACC grande, multi-sites tertiaire/industrie (10+), professionnels 

### E.2 Revenus Empilables (Stacking) & Modélisation Financière 

Pile de Revenus Typique (Hiérarchie Valeur) : 
- Autoconsommation directe (TAc amélioration) 
- Coût évité = (ΔkWh stocké/utilisé) × (tarif fournisseur local) 
- Exemple : +1000 kWh/an × 0.10 €/kWh = +100 €/an (marges) 
- Revenu par kWh de batterie ~ 5–10 €/(kWh batterie·an) 
- Valeur la plus stab 
- TURPE / Peak Shaving (réduction dépassement puissance) 
- Coût évité = réduction pics × tarif dépassement TURPE (0.50–1.50 €/kWh pic) 
- Exemple : 10 pic/an élevés × 10 kW × 50 €/kW = +5 k€/an 
- Revenu par kW ~ 500–1500 €/(kW batterie·an) si pics significatifs 
- Dépend fortement du site (industrie >> tertiaire) 
- Services Flexibilité / Balancing (mFRR, réserves) ← Nécessite > 1 MW batterie aggrégée 
- Revenu = participation marchés mFRR, capacité, frequency response 
- France 2026 : ~10–30 k€/an par 50 MW (petit), seuil entrée 1 MWh 
- Revenu moyen 20–100 €/(kWh batterie·an) si certifiée VPP 
- Volatilité élevée, dépend prix réseau 
- Arbitrage Prix (charge bas, décharge haut) ← Marginal pour ACC court-terme 
- Revenu = Δprix × kWh arbitré × efficacité batterie 
- Exemple : 100 cycles/an × 5 kWh × (prix max – prix min) × 90% = 1–3 k€/an max 
- Revenu moyen ~30–50 €/(kWh batterie·an), très volatile 
- Pertinent seulement si Enedis API temps-réel ouvert (2026+) 
- Réduction Injection / Curtailment (limitation GRD) 
- Revenu = économie coûts dépassement / limitation injection 
- Exemple : limite GRD 30 kW mais PV 60 kW → batterie absorbe 30 kW 2h/j = avoid coûts extension 
- Valeur ponctuelle 5–20 k€/an par site, diminue au fil du temps (une fois infrastructure stabilisée) 
- Résilience / Assurance (coût indirect : réduction sinistre, PRA) 
- Valeur non-marchande : impact coupure > 100 k€/h datacenters, hôpitaux 
- Valeur imputable 10–30% du CAPEX batterie sur durée (assurance réduite ~20%) 
- Pertinent pour usages critiques 

Modèle de Revenue Stacking (Cas Tertiaire Type 50 kWc + 15 kWh batterie) : Autoconsommation : 1200 kWh/an additionnel × 0.10 € = +120 €
TURPE peak shaving: 8 dépassement/an × 5 kW × 50 € = +2000 €
Arbitrage prix : 50 cycles × 8 kWh × 15 % gain × 90% = +540 €
Résilience (imputable) : 15 k€ CAPEX × 2 % valeur/an = +300 €
---
TOTAL / AN BRUT = +2960 €
OPEX (1.5 % CAPEX) = 15 k€ × 1.5 % = -225 €
NET ANNUEL = +2735 €
Payback = 15 k€ / 2.7 k€ = **5.5 ans OK** 

### E.3 Partage de Valeur dans ACC (Gouvernance + Transparence) 

Enjeu Principal : batterie commune create valeur (économies), faut règle claire « qui reçoit », sinon conflit. 

Trois Approches Partage : 

Approche 1 : Partage Proportionnel (Simple) Bénéfice global batterie = 2.7 k€/an (cf. exemple ci-dessus)
Clé répartition : 30 % Site A, 50 % Site B, 20 % Site C
→ Site A reçoit 810 €/an, B reçoit 1350 €/an, C reçoit 540 €/an
Avantage : transparent, prévisible
Inconvénient : ne récompense pas « utilisation réelle » batterie 

Approche 2 : Partage Performance (Complexe mais Juste) Bénéfice global = 2.7 k€/an, alloué par :
- (40 %) TAc amélioration → part proportionnelle consommation autoconsommée
- (40 %) TURPE reduction → part proportionnelle pic shaving contribution
- (20 %) Arbitrage/services → part proportionnelle cycles/utilisation

Nécessite mesure fine EMS (14 données 15-min par participant).
Avantage : incite optimisation, équité dynamique
Inconvénient : coût EMS +3–5 k€/an, audit annuel, risque dispute algorithme 

Approche 3 : Fonds Amortissement + Redistribution Surplus Bénéfice 2.7 k€/an
- Amortissement batterie : 1.5 k€/an (15 k€ / 10 ans) → fonds PMO
- Surplus revenu : 1.2 k€/an → redistribué participants pro-rata TAc
Site A reçoit dividende 1.2 k€ × 30 % = 360 €/an
Avantage : batterie « transparente » (propriété commune claire), surplus gain
Inconvénient : PMO doit gérer trésorerie, besoin comptabilité annuelle 

Recommandation : Approche 1 (Simple) si ACC petit < 5 entités, Approche 2 (Performance) si ACC professionnel avec EMS robuste, Approche 3 (Fonds) si ACC collectivité/bailleurs (gouvernance public). 

Cockpit Transparence (PROMEOS-type) : 
- Tableau de bord temps-réel : bénéfice accumulé, par site, par mois 
- Projection annuelle et prévision tarif batterie payback 
- Alertes si batterie underutilisée (ex. cycle < 1/j moyenne) 
- Votes participants annuels si modification clé 

## F. Architecture EMS/PMO & Mise en Conformité 

### F.1 Schéma Cible (Batteries + Comptage + Gouvernance) ┌─────────────────────────────────────────────────────────────┐
│ PMO / Cockpit (PROMEOS) │
├─────────────────────────────────────────────────────────────┤
│ • Données 15-min Enedis API (prod/conso participants) │
│ • Prévisions PV météo, prix spot 24h │
│ • Optimisation clé répartition (static/dynamic) │
│ • Pilotage batterie (charge/décharge setpoints) │
│ • Calcul facturation & shadow billing │
│ • KPI cockpit (TAc, TAp, surplus, cycles batterie) │
│ • Alertes non-conformité (dérive ACC, batterie) │
└─────────────────────────────────────────────────────────────┘
 ↕
 ┌─────────────────────┬─────────────────────┐
 ↓ ↓ ↓
 ┌─────────┐ ┌──────────────┐ ┌──────────────┐
 │EMS SITE │ │ BATTERIE │ │ EMS TERRAIN │
 │(optionl)│ │(Convertisseur) │(GTB si exist)│
 │GTB/CVC │ │ Onduleur │ │ (Pilot flex) │
 └─────────┘ └──────────────┘ └──────────────┘
 ↓ ↓ ↓
 ┌─────────────────────────┴─────────────────────┐
 │ Comptage GRD (Linky) │
 │ • Compteur production (PDL1) │
 │ • Compteur conso site A (PDL2) │
 │ • Compteur conso site B (PDL3) │
 │ • Index 15-min → Enedis serveur │
 └──────────────────────┬──────────────────────┘
 ↓
 ┌──────────────────────┐
 │ Enedis Infrastructure
 │ • Clé répartition validation
 │ • Fichier allocation mensuel
 │ • Reconciliation
 └──────────────────────┘ 

### F.2 Fonctionnalités EMS Essentielles (MVP) Fonctionnalité Criticité Implémentation Collecte données 15-min Enedis 🔴 CRITIQUE API Data Connect OAuth2, chiffré, stockage cloud Prévision PV (météo + historiques) 🟡 HAUTE API meteo (Solcast, Clear Sky), ML local Calcul clé répartition (15 min) 🔴 CRITIQUE Moteur calcul SQL/Python, audit trail (journal changements) Optimisation batterie (dispatch) 🟡 HAUTE Heuristique simplifié (charge si surplus > seuil, décharge si deficit) ou MPC complet (AI) Facturation shadow billing 🔴 CRITIQUE Facture PDF/CSV par participant, export paiement SEPA, suivi impayés Dashboard cockpit PMO 🟡 HAUTE Vue temps-réel prod/conso/batterie, KPI TAc/TAp/cycles, historiques API REST données publiques 🟢 MOYENNE Endpoints GET site/ 😀 KPI, POST commandes (si autorisé) Alertes & notifications 🟢 MOYENNE Email, SMS, Slack webhook sur anomalies (dérive, batterie faible) Conformité règles ACC (rayon 2km) 🔴 CRITIQUE Géolocalisation PDL auto-check distance producteur-consommateur Audit / Traçabilité 🟡 HAUTE Log toutes décisions algo, facturation, changements clé (blockchain optionnel) Intégration GTB/IoT partenaire 🟢 MOYENNE MQTT/BACnet bridge, déploiement futur V2 

### F.3 Risques Conformité & Mitigation 

Risque 1 : Comptage ≠ Réalité Physique (Perte Réseau, Erreur Mesure) 
- Symptôme : somme énergie distribuée ≠ somme production mesuré (écart > 5%) 
- Cause : pertes câble non mesurées, erreur onduleur, arrondis comptage Linky 
- Mitigation : (i) audit annuel comptage vs balances physiques, (ii) budget perte 3% intégré clé répartition 
- Coût : 1 k€ audit/an 

Risque 2 : Batterie Bloque/Défaut → Perte Produit Autoconso 
- Symptôme : batterie panne, ACC perte 10 kWh/j surplus stockable 
- Cause : défaut électronique, surcharge thermique, usure prématurée 
- Mitigation : (i) contrat maintenance (si BaaS) ou prestataire 500 €/an, (ii) redondance onduleur opt., (iii) assurance BEEM 
- Coût : 500 €/an maintenance + 2% CAPEX assurance 

Risque 3 : Évolution TURPE/Tarifs → Rentabilité Dégradée 
- Symptôme : TURPE 7 août 2026 initial, puis ajustement 2027 annule incitation injection-soutirage 
- Cause : politique énergétique gouvernementale, inflation 
- Mitigation : (i) contrats indexation tarifs batterie (ex. max +2% / an), (ii) clauses renégociation annuelle PMO 
- Coût : légal 2 k€ pour clauses robustes 

Risque 4 : Changement Réglementation ACC (Clé Fixe → Dynamique, Impact Batterie) 
- Symptôme : décret 2027 impose clé dynamique pour ACC, batterie doit s’adapter algorithme nouveau 
- Cause : UE directive harmonisation, politique français 
- Mitigation : (i) EMS architecture flexible (clé = paramètre, pas hard-coded), (ii) contrat PMO « adaptabilité », (iii) veille réglementaire 
- Coût : R&D EMS 5 k€ pour scalabilité 

Risque 5 : Cyber-Attaque / Données Énergétiques Sensibles (NIS2) 
- Symptôme : hacker accède API Enedis, modifie clé répartition en faveur un participant 
- Cause : token Vol, credential spear-phishing, bug API Enedis 
- Mitigation : (i) authentification multi-facteur (2FA), (ii) chiffrement TLS 1.3, (iii) audit sécu annuel (pentest), (iv) assurance cyber 
- Coût : 5–10 k€/an (souscription assurance + audit) 

Risque 6 : Batterie Classée ICPE (Si > Puissance Seuil) 
- Symptôme : batterie > 200 kW ou > 3 MWh → soumise réglementation ICPE (autorisation préfectorale, étude d’impact) 
- Cause : seuil automatique réglementation 
- Mitigation : (i) dimensionner batterie < seuil si possible, (ii) si dépassement, dossier ICPE 20 k€–50 k€, délai 6 mois 
- Coût : 0 si < seuil, 20–50 k€ + délai si dépassement 

## G. Benchmark Europe & Monde : Tendances 2025-2026 

### G.1 Situation Réglementaire Comparée Pays Status Batterie BESS Incitation Prix Règles ACC/Communautés Barrier d’Entrée 🇫🇷 France Tari TURPE 7 injection-soutirage août 2026, favorab… ✅ Tarif local dynamique, mFRR obligation 2026 > 10 MW ✅ Décret 2017-676 ACC cadre clair, PMO simple ⚠️ Comptage complexe si batterie commune, réglementACC encore rigide 🇩🇪 Allemagne Exempt grid fees 2026–2029 (extension), privilège planning § 35 BauGB ✅ Marchés intraday volatiles, revenu arbitrage fort ✅ Genossenschaft (coop) + tiers-lieux, cadre très flexible ✅ Planification favorable (sauf distance 200m contrainte 2025) 🇵🇱 Pologne Peu réglementé, pricing incitatif début ⚠️ Électricité bon marché localement, arbitrage limite ❌ Communautés émergeantes, cadre incomplet ⚠️ Infrastructure DNO ancienne, grid faible stabilité 🇸🇪 Suède Batterie intégrée hydroélectricité (balancing clé) ✅ Revenu balancing très élevé (Nordic price) ⚠️ Micro-réseaux avancés, ACC peu pertinent ✅ Infrastructure VPP leader (Statkraft 10 GW) 🇮🇹 Italie Amélioration 2024–2025, tarifs légaux introduction ⚠️ Projet tarifario (en cours 2025), non encore appliqué ✅ Comunità energetiche décret stable (2017), retard implmentation ❌ Contexte politique instable, barrière légale RECs fournitures 🇳🇱 Pays-Bas Flexgrids 2025+, tarif dégressif injection ✅ Marché prix temps-réel maître, arbitrage optimisé ✅ Energiecoöperaties framework mature, 200+ opérationnels ✅ Leader Europe, modèles copiables (ZuidtrAnt, etc.) 🇬🇧 Royaume-Uni Post-Brexit, cadre réglementaire clarification 2025 ⚠️ Marché prix élevé, tarif batterie non harmonisé ❌ Community Energy peu soutenu après politique, modèles rares ⚠️ Coût batterie + électricité élevés (ROI difficile) 🇪🇸 Espagne Légalisation autoconsumo colectivo 2021–2023, in momentum ✅ Tarif autoconsommation compétitif, ajustement annuel ✅ Marcos normativos ACC claro desde 2021, maturité montante ✅ Boom PV + ACC simultané, modèles répliquent rapide 🇨🇭 Suisse Batteri peu incentivée (électricité bon marché historiquement) ⚠️ Tarif faible injection, arbitrage nul ✅ Micro-réseaux décentralisés normatif ✅ Léger, infrastructure stable, peu nécessité batterie 🇯🇵 Japon Très matur, batterie réseau grande capacité (GW) ✅ Régulation marché souple, service ancillaire fortement rémunérés ⚠️ Communautés énergie peu développées (focus centralisé EDF-type) ✅ Leader tech batterie (Sony, Panasonic), mais coûteux 

Conclusion Benchmark : France 2026 se positionne bien (TURPE 7 attrayant), rattrape Allemagne/NL mais moins avancée politiquement. Modèle Allemagne (flexibilité planning) et Néerlandais (VPP mature) sont transférables si harmonisation UE continue. 

### G.2 Business Models Leaders Observés (Europe) 

Modèle 1 : « Battery + VPP Aggregator » (Allemagne, Statkraft 10 GW) Statkraft agrège 1000+ producteurs (solaire, éolien) + batteries décentralisées
Centralise dispatch via logiciel VPP propriétaire
Revenue stacking : marchés (spot+intraday+balancing) + services ancillaire
Scalabilité massive, CAPEX propriétaire élevé, donc VPP as a Service SaaS 

✅ Applicable France : Agregio (concurrent), ENRG (startup), Sunwatts (agrégateur) 

Modèle 2 : « Cooperative Energy Community + Batterie Commune » (Pays-Bas ZuidtrAnt) Coopérative locale 500 habitants finance batterie collective 50 kWh (20 k€)
Gère ACC, facturation, gouvernance démocratique (AGM annuelles)
Revenu = TAc amélioration + vente surplus grid (contrat PPA local)
Modèle quasi sans-profit (coop), réinvestis bénéfice achat PV supplémentaire 

✅ Applicable France : mutuelles, collectivités (Couzeix, St-Léger), bailleurs sociaux 

Modèle 3 : « Battery-as-a-Service SaaS + Dynamic Pricing » (Espagne, Ilek) Ilek = "fournisseur vert local" agit intermédiaire
Produit conso local = producteur PV + Ilek gère facturation
Batterie financer par Ilek, coûts variables repercutés consommateurs
Transparence prix 100 %, flexibilité participante (smart charging) 

✅ Applicable France : modèle Effy, Engie Solutions (BaaS commercial) 

Modèle 4 : « Microgrids Isolés + Batterie Autonomie » (Île Eigg Écosse, Tenerife) Microgrid 100 habitants, batterie 200 kWh autonomie, pas connexion réseau (îles)
Résilience/indépendance critère #1, rentabilité secondaire
Gestion algorithme temps-réel (écrêtage conso si batterie faible) 

⚠️ Marginal France (réseau ubiquitaire), sauf cas exceptionnel 

Modèle 5 : « Industrial Park IRECs + Flexibilité Partagée » (Allemagne Energize) 3–10 PME industrielle voisines mutualisent batterie grande (500 kWh)
+ pilotage flexible charges (compresseurs, refroidissement)
Revenue = TAc + peak shaving fort (industries pic puissance énorme)
Gouvernance : ESCo tiers gérant batterie + contrats individuels 

✅ Applicable France : ZAE (zones artisanales), clusters industriels 

## H. Recommandations Actionnables & Roadmap 

### H.1 Guide Décision (Arbre GO/NO-GO) START : "Faut-il une batterie pour notre ACC ?"
 │
 ├─ Q1 : TAc SANS batterie > 60 % ?
 │ ├─ OUI → "Surplus marginal, batterie gain < 10%"
 │ │ → ** STOP : NO-GO stockage **
 │ └─ NON → Q2
 │
 ├─ Q2 : Budget CAPEX disponible ≥ 30 k€ ?
 │ ├─ NON → "Coûts trop élevés vs gain"
 │ │ → ** STOP : NO-GO (sauf BaaS exploration) **
 │ └─ OUI → Q3
 │
 ├─ Q3 : Surplus journalier > 30 % consommation ?
 │ ├─ NON → "Surplus petit, batterie undersized marginale"
 │ │ → ** STOP : NO-GO (coûts fixes trop élevés) **
 │ └─ OUI → Q4
 │
 ├─ Q4 : Pics puissance > 20 kW OU contrainte GRD injection ?
 │ ├─ NON → "Lissage pics faible priorité"
 │ │ → ** PRUDENCE : batterie secondaire, 8–12 kWh min ** → Q5
 │ └─ OUI → "Peak shaving critique"
 │ → ** GO batterie priorité ** → Q5
 │
 ├─ Q5 : Gouvernance ACC clarifiée (propriété batterie, clé répartition définie) ?
 │ ├─ NON → "Risque conflit stakeholders > gains"
 │ │ → ** STOP : NO-GO sans accord préalable **
 │ │ (Recommandation : 1–2 réunions gouvernance avant)
 │ └─ OUI → Q6
 │
 ├─ Q6 : Objectif précis batterie (TAc %, autonomie h, résilience) défini ?
 │ ├─ NON → "Scope flou, risk overspend"
 │ │ → ** PRUDENCE : étude 5 k€ avant conception **
 │ └─ OUI → ** ✅ GO CONCEPTION BATTERIE **
 │
 └─ CONCLUSION : Dimensionnement détaillé, ROI/sensibilités, marché
 → Décision finale (approuve budget, timeline, modèle propriété) 

### H.2 Playbooks Exécution (Par Scénario) 

### Playbook A : ACC Petit Tertiaire (1 producteur, 2–3 consommateurs, 20–40 kWc) 

Phase 1 (Mois 0–1) : Diagnostic Rapide 
- Collect courbes 12 mois PV + conso (compteurs Enedis) 
- Calcul TAc/surplus simplifié (1 page Excel) 
- Budget CAPEX sketch (batterie 8 kWh ~10 k€) 
- Réunion gouvernance : accord propriété batterie, clé répartition 
- Livrables : 1 page décision GO/NO-GO, 1 ppt synthèse stakeholders 

Phase 2 (Mois 1–2) : Conception Détaillée 
- Modelage 365 jours (kWh batterie, kW puissance, ROI 8–12 ans) 
- Sélection technologie : LFP 8 kWh 120–130 €/kWh supplier 
- Schema raccordement définitif (batterie derrière onduleur vs commun) 
- Pré-accord Enedis (email demande, délai 2–3 semaines) 
- Devis intégrateur (3 fournisseurs, négociation) 
- Livrables : schéma technique, devis détaillé, lettre Enedis OK 

Phase 3 (Mois 2–4) : Pilot & Déploiement 
- Commande batterie + onduleur + EMS (délai 4–8 semaines) 
- Travaux installation 2–5 jours (coupe brève) 
- Test mise en service + étalonnage onduleur 
- Formation PMO exploitation cockpit EMS 
- Livrables : batterie opérationnelle, rapport mise en service, manuel PMO 

Phase 4 (Mois 4–12) : Monitoring & Ajustement 
- Suivi mensuel KPI (TAc, cycles, revenue) 
- Réunion trimestrielle stakeholders (reporting gains) 
- Entretien annuel batterie (inspection, firmware) 
- Ajustement règles EMS si performance sous-objectif 
- Livrables : rapport 1 an, ROI confirmer vs. projection 

Budget Timing Typique : 
- Étude : 3 k€ 
- Batterie/onduleur/EMS : 12–15 k€ 
- Installation : 2–3 k€ 
- Pilot 3 mois : 0 (inclus) 
- Total : 17–21 k€ (pour 8 kWh LFP) 
- Timeline : 4 mois conception + installation + pilot 

### Playbook B : ACC Multi-Sites Tertiaire/Industrie (5–10 entités, 80–200 kWc, budget 50+ k€) 

Phase 0 (Mois -2 à 0) : Gouvernance Lourde 
- Réunion plénière : accord vision ACC (propriété, durée, objectif) 
- Constitution PMO officielle (ou mandater gestionnaire) 
- Rédaction statuts ACC, contrats inter-participants (légal 8 k€) 
- Signature conventions ACC (Enedis approval préalable) 
- Livrables : statuts signés, convention PMO, mandat gestionnaire 

Phase 1 (Mois 0–2) : Étude Technique Approfondie 
- Audit énergétique complet (72 k€ consultant si heavy) ou lite (8 k€) 
- Courbes 24 mois PV/conso, variabilité saisonnière 
- Profils de charge par participant, pics simultanéité 
- Constrainte GRD fine, limite injection par zone 
- Tarifs TURPE 7 zone exacte 
- Modelage multi-scénario batterie (10, 20, 30 kWh options, kW puissance) 
- Comparatif business models (propriété vs BaaS vs distribué) 
- Sélection modèle gouvernance valeur partage 
- Livrables : rapport audit 30 pages, 3 scénarios batterie, analyse comparative 

Phase 2 (Mois 2–4) : Conception & Approvals 
- Spécifications batterie/onduleur (RFQ tender 3 suppliers) 
- Schema raccordement, diagramme unifilaire 
- Pré-accord GRD/Enedis (dossier désa, délai 6–8 semaines) 
- Pré-accord assurance batterie (ICPE si dépassement) 
- Finalisation contrats BaaS (if applicable) vs achat outright 
- Négociation finale suppliers 
- Livrables : cahier charge technique, contrats signés suppliers, approbation GRD 

Phase 3 (Mois 4–8) : Mise en Oeuvre Infrastructure 
- Commande (lead time 8–12 semaines batterie) 
- Travaux génie civil (fondations batterie, câblage) 4–6 semaines parallèle 
- Installation système (batterie, onduleur, EMS) 2–4 semaines 
- Commissionning et tests 2 semaines 
- Formation PMO, participants (workshop 2 jours) 
- Livrables : batterie opérationnelle, formation vidéo, manuels 

Phase 4 (Mois 8–18) : Pilot Opérationnel (10 mois) 
- Fonctionnement nominal, monitoring KPI quotidien 
- Ajustement algorithme dispatch EMS (ex. seuil charge/décharge) 
- Feedback participants (forums, enquêtes) 
- Rapports mensuels PMO (transparence valeur créée) 
- Ajustement règles si dérives détectées 
- Livrables : dashboard KPI, rapports mensuels, retours utilisateurs 

Phase 5+ (Mois 18–36) : Optimisation & Scaling 
- Intégration services flexibilité (mFRR si > 1 MWh) 
- Ajustement tarif batterie si ROI dégradé (TURPE changes) 
- Plans évolution PV/batterie supplémentaire (extension) 
- Transition post-pilot à gestion de routine annuelle 
- Livrables : roadmap 3 ans, contrats renouvellement, stratégie flexibilité 

Budget Timing Typique : 
- Étude technique : 8–15 k€ 
- Batteries/onduleur (25 kWh LFP) : 25–30 k€ 
- EMS + architecture : 8–12 k€ 
- Installation/travaux : 8–12 k€ 
- Assurance/légal : 5–8 k€ 
- Pilot management : 0 (inclus opération) 
- Total : 54–77 k€ 
- Timeline : 6 mois étude + 6 mois implémentation + 10 mois pilot = 22 mois total 

### H.3 Architecture Cible EMS + Fonctionnalités Clés 

Composants Logiciels Minimum : 
- Connectivité Données (cloud AWS/Azure/OVH) 
- API Enedis Data Connect (OAuth2, refresh token) 
- Stockage time-series données 15-min (InfluxDB, TimescaleDB) 
- Webhook alertes (Slack, email) 
- Logique Métier 
- Calcul clé répartition (template Excel → moteur Python/SQL) 
- Optimisation batterie (heuristique ou MPC) 
- Facturation & settlement (PDF generation, SEPA) 
- Indicateurs KPI (TAc, TAp, cycles, LCOE) 
- Interface Utilisateur 
- Cockpit PMO (React/Vue dashboard temps-réel) 
- Portail participant (authenticated, vue personnelle) 
- Admin panel (gestion clé, alertes, users) 
- Infrastructure 
- Serveur VPS 4 vCPU, 16 GB RAM (100–200 €/mois) 
- Certificats SSL/TLS 
- Backup quotidien 

Coûts SaaS Estimation : Rubrique Startup Interne Service Tiers Développement initial 30–50 k€ (2–3 devs × 3 mois) 0 (outsource) Infrastructure cloud 200 €/mois × 12 = 2.4 k€/an Inclus SaaS Maintenance/update 5–8 k€/an (support) Inclus Support utilisateurs 3–5 k€/an Inclus Total année 1 ~40–60 k€ 150–300 €/mois (1.8–3.6 k€/an) Total années 2+ ~8–15 k€/an ~2–4 k€/an 

Recommandation : Pour ACC petit-moyen (< 30 kWh batterie), SaaS tiers (Enogrid, Communitiz, PROMEOS) préférable. Pour ACC grande/stratégique, build interne si ressources. 

## I. Risques & Conformité Avancée 

### I.1 Matrix Risques Batterie ACC (Probabilité × Impact) Risque Prob Impact Mitigation Coût Mitigation Batterie défaut / courte durée (5 ans au lieu 12) Moyen (15%) 🔴 ÉLEVÉ (perte 50% ROI) Contrat garantie constructeur 10 ans, assurance BEEM 1–2 k€/an (assurance) Comptage Enedis réconciliation erreur (écart > 10%) Faible (5%) 🟠 MOYEN (conflit facturation, dispute 20 k€) Audit annuel comptage vs physique, fonds risque 3% énergie 1 k€/an audit Changement tarif TURPE 2027–2028 annule ROI Moyen (20%) 🟠 MOYEN (ROI 5 ans → 12 ans) Contrats indexation plafonnés (+2%/an max), clauses renégociation 2 k€ légal Batterie non conforme ICPE (classification tardive) Faible (8%) 🔴 ÉLEVÉ (arrêt, amende 10 k€, délai 6 mois) Pre-audit ICPE, dossier avant installation (< seuil = 0 impact) 3–5 k€ pré-audit Cyber-attaque EMS (vol clé répartition, sabotage) Très faible (2%) 🔴 ÉLEVÉ (perte confiance, litige 100 k€+) MFA 2FA, chiffrement TLS 1.3, pentest annuel, assurance cyber 5–10 k€/an Batterie surcharge/incendie (sécurité) Très faible (< 1%) 🔴 CRITIQUE (blessés, dégâts, responsabilité civile) BMS certifié, entretien régulier, assurance responsabilité (existe) 0 (inclus assurance bâtiment) Participants quittent ACC → perte de mutualité Moyen (15%) 🟠 MOYEN (batterie sous-utilisée, ROI dilué) Contrats pluriannuels (5 ans min.), pénalités sortie 5 k€ légal Délai implémentation > 12 mois (scope creep) Moyen (25%) 🟠 MOYEN (coûts +20%, batterie obsolète) Planning PERT ferme, jalons clairs, change management 0 (management) EMS non compatible future API Enedis 2027 Moyen (20%) 🟠 MOYEN (refonte logiciel 15 k€) Architecture modulaire EMS, liaison fabricant, contrat support 2027+ 0 (si build flexible) Batterie volée / acte de vandalisme Faible (5%) 🟠 MOYEN (remplacement 15 k€, coupure 2 mois) Clôture sécurité, vidéo surveillance, assurance vol 2–3 k€/an (surveillance) 

### I.2 Conformité Réglementaire (Checklist Pré-Installation) 

Avant installation batterie, vérifier 100% coches : 
- Enedis accord : Dossier de demande d’adhésion ACC + schéma raccordement batterie signé Enedis (minimum 2 semaines) 
- ICPE classification : Batterie < 200 kW ET < 3 MWh → EXEMPT. Sinon, dossier Préfecture (délai 4–6 mois) 
- Normes sécurité : Batterie certifiée CE, onduleur CEI 62040-2, câblage aux normes NF C 15-100 
- Assurance : Responsabilité civile (batterie incluse), assurance BEEM si batterie > 200 kWh 
- Contrats juridiques : Statuts PMO, convention ACC signée, contrats participants, PV de gouvernance 
- Comptage : Linky pré-requis, Enedis vérifie accessibilité index (smart meter obligatoire) 
- Data protection : Conformité RGPD (données consommation sensibles), politique confidentialité PMO 
- Audit énergétique : Rapport initial (TAc, TAp, surplus) baseline pour après-batterie (obligatoire) 
- Plan de secours : Procédure si batterie en panne (comment consommer sans batterie ?) 
- Rayon 2 km : Géolocalisation PDL producteur/consommateur, distance en ligne confirmée < 2 km par Enedis 

Délai total conformité : 8–12 semaines (dont 6 semaines attente Enedis). 

### I.3 Recommandations Avancées pour PROMEOS (Cockpit EMS Nouvelle Génération) 

Fonctionnalités Bonus Recommandées : 
- Prévision PV 48h Fine (météo + cloud detection) 
- Intégration Solcast API (acuracité 5%) 
- Prévisionalgo batterie (charge optimisée si prévision nuageux) 
- Coût ajout : 1 k€ intégration, 500 €/an Solcast API 
- Clé de Répartition Dynamique IA (optimisation équité + performance) 
- Algorithme jour-J qui ajuste clé selon profils réels (vs static mensuel) 
- Maximise TAc tout en maintenant équité (Gini index) 
- Coût : 10–20 k€ développement, 2 k€/an compute 
- Dash Participant Gamification 
- Ranking “contributes flexibility” (badges) 
- Competition intergroupes (quartier, entreprises) 
- Coût : 5 k€ UI/UX 
- API Publique (ouverture données anonymisées) 
- Permet agrégateurs/VPP externes à optimiser portfolio 
- Revenu potentiel (données licensed à Agregio, RTE, etc.) 
- Coût : 5 k€ architecture + security 
- Intégration GTB/IoT (couplage CVC + batterie) 
- API BACnet/MQTT pour lire temper, humidité, débit chauffage 
- EMS pilot CVC + batterie conjointement (ex. charge ballon nuit, décharge jour) 
- Coût : 10–15 k€ (intégration site-specific) 
- Blockchain Settlement (audit trail immuable) — optionnel, hype actuelle 
- Enregistrement immutable chaque transaction énergie 
- Utile pour litiges future (trace 100% fiable) 
- Coût : 5–10 k€ dev (smart contract Ethereum/Polygon) 

## J. Conclusion & Recommandations Décision 

### Synthèse Exécutive : 

Stockage batterie pour ACC pertinent SI ET SEULEMENT SI : 
- Surplus PV > 30% consommation (sinon TAc amélioration marginal < 10%) 
- Budget CAPEX ≥ 30 k€ (seuil minimum rentabilité) 
- Gouvernance ACC clarifiée (propriété batterie, clé répartition définie) 
- ROI projection < 10 ans (breakeven 4–8 ans typique si paramètres OK) 
- Objectif explicite (TAc/TAp%, autonomie h, résilience, indépendance) 

Sinon → NO-GO batterie (augmenter PV, optimiser conso, ACC simple sans stockage). 

Recommandation par Profil ACC : Profil Décision Batterie Recommandée Timeline Budget Total Petit tertiaire (20–40 kWc) ⚠️ MARGINAL (si surplus > 30%) 6–12 kWh, 12 kW 4 mois 15–20 k€ Multi-sites tertiaire (80–200 kWc) ✅ OUI (profile souvent désynchro) 20–40 kWh, 25–40 kW 6–8 mois 50–80 k€ IRVE + solaire ✅ OUI PRIORITAIRE (peak shaving crucial) 30–50 kWh, 40–60 kW 6 mois 70–120 k€ Industrie 24/7 (résilience) ✅ OUI PRIORITAIRE 50–100 kWh, 50–100 kW 8–12 mois 100–150 k€ Ferme/agriculture ⚠️ DÉBAT (si contrainte GRD forte, OUI) 15–25 kWh si limitation injection 4–6 mois 25–40 k€ Microgrid isolé ✅ OUI OBLIGATOIRE (autonomie) 100–500 kWh (saisonnier) 12–18 mois 150–500+ k€ 

Roadmap France 2025–2030 : 
- 2025 (Fin ARENH) : Volatilité prix accentuée → Window opportunity stockage (ROI attractive) 
- Août 2026 (TURPE 7) : Tarifs injection-soutirage localisés → incitation forte batteries injection smarte 
- 2026+ (mFRR obligation) : Génération > 10 MW doit balancer → VPP agrégation devient standard 
- 2027–2028 : Batterie cost curve -15–20% additional, > 80% LFP (sodium emergent) 
- 2030–2035 (Fit-for-55) : Batteries 1–5 MWh community-scale dominant business model 

Résilience vs Économie : Batterie → coûteux court-terme (CAPEX), mais sécurise prix électricité 8–12 ans (hedge inflation, TURPE evol., volatilité acheteur). 

## Annexes 

### Glossaire 
- ACC : Autoconsommation Collective (décret 2017-676) 
- TAc : Taux d’Autoconsommation = kWh produits consommés / kWh produits 
- TAp : Taux d’Autoproduction = kWh produits / kWh consommés 
- PMO : Personne Morale Organisatrice (gestionnaire ACC) 
- BESS : Battery Energy Storage System (système batterie électrique) 
- EMS : Energy Management System (logiciel pilotage) 
- GTB : Gestion Technique Bâtiment (automatisation/contrôle) 
- TURPE : Tarif d’Utilisation du Réseau Public d’Électricité (CRE) 
- mFRR : Manual Frequency Restoration Reserve (service balancing RTE) 
- VPP : Virtual Power Plant (agrégation smart centralisée) 
- LFP : Lithium Iron Phosphate (chimie batterie sûre) 
- LCOE : Levelized Cost of Energy (coût ramené €/kWh) 
- ICPE : Installation Classée pour la Protection Environnement (seuil réglementation) 

### Checklists Implémentation (Téléchargeable) 

Checklist Pré-Montage ACC (5 points critiques) 
Checklist Dimensionnement Batterie (8 étapes) 
Checklist Installation & Mise en Service (12 points qualité) 
Checklist Exploitation Année 1 (10 actions monitoring) 

### Références & Sources (Liens + Dates) 

Réglementations Officielles France : 
- Décret ACC 2017-676 (juin 2017) : https://www.legifrance.gouv.fr/dossierlegislatif/JORFDOLE000033836189/ 
- Décret BACS 2020-887 (juil. 2020) : https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000042167891 
- Loi APER 2023-175 (mars 2023) : https://www.legifrance.gouv.fr/dossierlegislatif/JORFDOLE000046848633/ 
- TURPE 7 CRE (nov. 2025) : https://www.cre.fr/documents/consultation-publique-turpe-7 

Analyses Industrie Clés : 
- IEA, “Global EV Outlook 2025” : batteries transport & stationary 
- SolarPower Europe, “European Solar Market Report 2025” : croissance ACC 
- Ember, “European Electricity Review 2025” : prix spot, volatilité 
- Agora Energiewende, “EV Battery Costs 2025” : CAPEX trajectoire LFP 
- REScoop/FEDARENE, “Renewable Energy Communities Facility” : business models EU 
- COME RES, “Advancing RECs Europe” : benchmarks 9 pays 

Études de Cas Référence : 
- ZuidtrAnt (Pays-Bas) : https://zuidtrant.nl/ (coopérative modèle 500 ha) 
- Couzeix (France) : commune 87, 5 école + ACC (collectivité pionnière) 
- Eeklo (Belgique) : 100% PV municipalité + ACC 
- Drumlin Wind Energy (Irlande) : coopérative vent 
- Grenzland-Pool (Allemagne) : cluster industriel border 

Plateformes SaaS Mentionnées : 
- PROMEOS : https://www.promeos.fr/ (MVP français ACC startup) 
- Enogrid EnoPower : https://enogrid.com/ (leader français 200+ opérations) 
- Communitiz EDF : https://www.edf.fr/…communitiz 
- Agregio Solutions : https://www.agregio-solutions.com/ (VPP agrégateur) 

Fin du dossier. Version : 2.0 | Date : Janvier 2026 | Cible : Décideurs B2B ACC France. 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 

⁂ 
- https://www.e3s-conferences.org/articles/e3sconf/pdf/2023/51/e3sconf_supehr2023_03011.pdf ↩︎ 
- https://www.energy-storage.news/france-introduces-grid-tariff-reforms-for-energy-storage/ ↩︎ 
- https://opoura.com/news-and-insights/mfrr-requirement-in-france-from-2026/ ↩︎ 
- https://sacredsun.eu/tendances-2026-du-stockage-denergie-pour-les-entreprises-performance-modularite-et-intelligence-energetiquesacred-sun-europe-at-data-centre-world-paris-2025/ ↩︎ 
- https://www.pv-magazine.com/2025/10/10/france-revises-grid-tariffs-to-spur-smarter-battery-storage-use/ ↩︎ 
- https://www.energy-storage.news/france-introduces-grid-tariff-reforms-for-energy-storage/ ↩︎ 
- https://opoura.com/news-and-insights/mfrr-requirement-in-france-from-2026/ ↩︎ 
- TECSOL-Formation-PV-ACC-06-2025.pdf ↩︎ 
- https://www.emsys-renewables.com/products/virtual_power_plant/technology.php ↩︎ 
- https://energy-cities.eu/wp-content/uploads/2024/07/D-3.1-Report-on-selected-business-models-for-development-of-community-energy-projects.pdf ↩︎ 
- https://www.veolia.com/en/planet/renewable-energies-virtual-power-plants-smart-grids-blockchain-energy-transition ↩︎ 
- https://energy.ec.europa.eu/topics/markets-and-consumers/energy-consumers-and-prosumers/energy-communities_en ↩︎ 
- https://www.paulhastings.com/fr/publications/client-alerts/unlocking-energy-storage-in-the-eu-and-france-regulatory-and-contractual-pathways ↩︎ 
- https://www.energystream-wavestone.com/2025/09/virtual-power-plants-un-levier-essentiel-pour-la-flexibilite-energetique/ ↩︎ 
- https://becoop-kep.eu/wp-content/uploads/2022/02/Energy-Communities-business-models_paper.pdf ↩︎ 
- https://www.next-kraftwerke.com ↩︎ 
- https://fedarene.org/publication/business-models-for-industrial-energy-communities/ ↩︎ 
- https://www.sia-partners.com/fr/nos-expertises/les-virtual-power-plants-futur-paradigme-des-services-dagregation ↩︎ 
- Analyse-experte-Obligations-reglementaires-module-Data-Conformite-multi-energie-France-B2B.pdf ↩︎ 
- Plan-de-MVP-et-Offre-PROMEOS-Micro-fournisseur-local-augmente.pdf ↩︎ 
- Reglementations-energetiques-_-donnees-a-surveiller-et-formules-de-calcul.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1UJOz5hSHG5r50Rr-ct61Dg8G61b5miJL/66b57442-5ab5-46ba-9e32-fb56c7d97afb/Brique-1-Data-Conformite-_-Un-Systeme-Expert-Proactif-Pas-un-Cockpit-Passif.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1j_N_5fswFsyr83tshdBCH85xHdY68HGp/4276431a-acfd-4bdc-8015-f93377a7e353/Les-Echos-Stockage-delectricite.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1lBtWOWrphJWbg7S_YtjW94q35HXVfor6/cbc5a5fe-89e0-4089-98f3-eb3b0cc6e142/Plan-de-MVP-et-Offre-PROMEOS-Micro-fournisseur-local-augmente.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/14_hZ7KEgKXrb9EZvlEuCnWr1vMqP3m4s/5e0a1929-0cec-4cd7-95a6-261f3b12ab09/Les-Echos-Marche-de-lelectricite-la-bataille-est-relancee.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1Ht6JkKn-jF2zcrUZjjNl1tbBjARaZoKr/77b504f5-56db-4bac-8e92-53c0055d3c59/Les-Echos-Le-marche-des-data-centers.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1XCfazetekY-wv6g9o1ZOFNuZv7ny67Ed/f65e719d-c4d3-4af2-851d-d6afd6cf26d6/Les-Echos-Le-nouvel-age-dor-du-marche-du-photovoltaique.pdf ↩︎ 
- https://revue.cder.dz/index.php/rer/article/view/1422 ↩︎ 
- https://www.mdpi.com/1996-1073/13/10/2466 ↩︎ 
- https://iopscience.iop.org/article/10.1088/1742-6596/2600/8/082002 ↩︎ 
- http://ieeexplore.ieee.org/document/1364402/ ↩︎ 
- https://arxiv.org/pdf/2205.00074.pdf ↩︎ 
- https://www.mdpi.com/2071-1050/12/23/10144/pdf ↩︎ 
- https://www.mdpi.com/2313-0105/6/4/56/pdf ↩︎ 
- http://downloads.hindawi.com/journals/tswj/2014/906284.pdf ↩︎ 
- https://re.public.polimi.it/bitstream/11311/1031214/2/11311-1031214_Longo.pdf ↩︎ 
- https://www.mdpi.com/2673-9941/4/1/8/pdf?version=1710424494 ↩︎ 
- https://www.mdpi.com/2227-9717/8/3/367/pdf ↩︎ 
- https://www.mdpi.com/2076-3417/11/17/8231/pdf ↩︎ 
- https://tobias-massier.net/publications/download/Tjandra_OptimalSizingBattery_2022.pdf ↩︎ 
- https://www.flashbattery.tech/en/blog/eu-battery-regulation-obligations-updates/ ↩︎ 
- https://connected-energy.co.uk/industry-insights/revenue-generation-from-battery-energy-storage/ ↩︎ 
- https://go.ratedpower.com/hubfs/Ebook BESS.pdf ↩︎ 
- https://elektroonikaromu.ee/en/the-new-eu-battery-regulation/ ↩︎ 
- https://www.bclplaw.com/en-US/events-insights-news/battery-storage-revenues-and-routes-to-market.html ↩︎ 
- https://www.tum-create.edu.sg/sites/default/files/files/Tjandra_OptimalSizingBattery_2022.pdf ↩︎ 
- https://www.dnv.fr/services/battery-regulation—20231542/ ↩︎ 
- https://www.mckinsey.com/industries/electric-power-and-natural-gas/our-insights/evaluating-the-revenue-potential-of-energy-storage-technologies ↩︎ 
- https://hybridpowersystems.org/crete2019/wp-content/uploads/sites/13/2020/03/4B_6_HYB19_011_paper_Uhlemeyer_-Bj%C3%B6rn.pdf ↩︎ 
- https://www.vde.com/topics-en/energy/dienstleistungen ↩︎ 
- https://www.energydawnice.com/five-common-business-models-for-overseas-distributed-energy-storage/ ↩︎ 
- https://arxiv.org/html/2509.18082v1 ↩︎ 
- https://unece.org/sites/default/files/2024-10/4_EU_Rev.1.pdf ↩︎ 
- http://en.cnesa.org/latest-news/2025/12/18/major-report-released-research-on-business-models-for-the-development-of-distributed-energy-storage ↩︎ 
- https://www.sciencedirect.com/science/article/abs/pii/S2352152X22001220 ↩︎ 
- https://www.ecosistant.eu/en/eu-battery-regulation-2023-batt2-important-for-online-commerce/ ↩︎ 
- https://www.macquarie.com/hk/en/about/company/macquarie-asset-management/institutional/insights/battery-storage-strategies-for-revenue-stacking-and-investment-success.html ↩︎ 
- https://www.sciencedirect.com/science/article/abs/pii/S0378779624000038 ↩︎ 
- https://environment.ec.europa.eu/topics/waste-and-recycling/batteries_en ↩︎ 
- https://iopscience.iop.org/article/10.1149/MA2025-014514mtgabs ↩︎ 
- https://iopscience.iop.org/article/10.1149/MA2024-02111mtgabs ↩︎ 
- https://www.semanticscholar.org/paper/651418fb812e2986c4eefb63c273318b97c82e35 ↩︎ 
- https://www.semanticscholar.org/paper/ef12642d8e5f7af096130092a5ad48dcd33d51bf ↩︎ 
- https://www.semanticscholar.org/paper/3147bb5bbbd70e6c6d9006d83b42d21dc26e1221 ↩︎ 
- http://section.iaesonline.com/index.php/IJEEI/article/download/4417/823 ↩︎ 
- https://news.ycombinator.com/item?id=45441499 ↩︎ 
- https://www.nature.com/articles/s41598-025-93688-w ↩︎ 
- Les-Echos-Stockage-delectricite.pdf ↩︎ 
- https://www.ise.fraunhofer.de/content/dam/ise/en/documents/publications/studies/EN2024_ISE_Study_Levelized_Cost_of_Electricity_Renewable_Energy_Technologies.pdf ↩︎ 
- https://www.ecologie.gouv.fr/sites/default/files/publications/Thema - Growth in wind and solar energy.pdf ↩︎ 
- https://docs.nrel.gov/docs/fy25osti/92831.pdf ↩︎ 
- https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2025/Jul/IRENA_TEC_RPGC_in_2024_Summary_2025.pdf ↩︎ 
- https://www.pv-magazine.com/2024/06/13/french-startup-unveils-plug-and-play-pv/ ↩︎ 
- https://www.gridx.ai/knowledge/what-is-a-virtual-power-plant-vpp ↩︎ 
- https://www.lazard.com/media/xemfey0k/lazards-lcoeplus-june-2024-_vf.pdf ↩︎ 
- https://www.raylyst.eu/en/how-long-can-pv-batteries-provide-energy-self-sufficiency-for-your-home/ ↩︎ 
- https://www.sciencedirect.com/science/article/abs/pii/S0306261924023900 ↩︎ 
- https://www.sciencedirect.com/science/article/pii/S2211467X24002542 ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/19237389/a4758289-0869-4ef1-92d9-8de9db74b8e1/Les-Echos-Le-marche-des-data-centers.pdf ↩︎ 
- https://ratedpower.com/blog/france-land-challenges-solar-boom/ ↩︎ 
- https://papers.ssrn.com/sol3/Delivery.cfm/a7369b1d-b250-4c2f-b8cf-1a9ccae1f56f-MECA.pdf?abstractid=5236388&mirid=1 ↩︎ 
- https://www.nature.com/articles/s41597-025-05951-4 ↩︎ 
- https://www.sciencedirect.com/science/article/pii/S0960148125004756 ↩︎ 
- https://cordis.europa.eu/project/id/308755/reporting ↩︎ 
- https://www.ren21.net/gsr-2025/global_overview/ ↩︎ 
- https://modoenergy.com/research/france-battery-buildout-bess-construction-energy-storage-november-2025 ↩︎ 
- https://ietresearch.onlinelibrary.wiley.com/doi/abs/10.1049/gtd2.70063 ↩︎ 
- https://onlinelibrary.wiley.com/doi/10.1002/tee.70225 ↩︎ 
- https://ieeexplore.ieee.org/document/10958560/ ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/19237389/b9a96b87-8816-4f66-bc91-cd50c7515045/Les-Echos-Marche-de-lelectricite-la-bataille-est-relancee ↩︎ 
- https://africanscholarpub.com/ajsede/article/view/476 ↩︎ 
- https://www.scipedia.com/public/Balachandran_et_al_2025a ↩︎ 
- https://ieeexplore.ieee.org/document/10966880/ ↩︎ 
- https://rsisinternational.org/journals/ijriss/article.php?id=2770 ↩︎ 
- https://ieeexplore.ieee.org/document/9848542/ ↩︎ 
- https://ieeexplore.ieee.org/document/10759377/ ↩︎ 
- https://ieeexplore.ieee.org/document/10116942/ ↩︎ 
- https://ieeexplore.ieee.org/document/10082150/ ↩︎ 
- https://linkinghub.elsevier.com/retrieve/pii/S2405844024117410 ↩︎ 
- https://www.adb.org/sites/default/files/publication/479891/handbook-battery-energy-storage-system.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/19237389/cb22c1dc-985e-4cb5-b142-a22523e8c0ba/Les-Echos-Le-nouvel-age-dor-du-marche-du-photovoltaique.pdf ↩︎ 
- https://linkinghub.elsevier.com/retrieve/pii/S0306261921006140 ↩︎ 
- https://arxiv.org/pdf/2112.09816.pdf ↩︎ 
- https://arxiv.org/pdf/2310.05811.pdf ↩︎ 
- https://linkinghub.elsevier.com/retrieve/pii/S0142061524005106 ↩︎ 
- https://www.frontiersin.org/articles/10.3389/fenrg.2021.634912/pdf ↩︎ 
- https://www.taylorwessing.com/fr/insights-and-events/insights/2025/12/batteriespeicher-im-aussenbereich ↩︎ 
- https://www.statkraft.com/what-we-offer/energy-flexibility-management/virtual-power-plants/ ↩︎ 
- https://www.rescoop.eu/news-and-events/news/european-energy-communities-facility-a-project-to-support-energy-communities-in-developing-solid-business-plans ↩︎ 
- https://www.agregio-solutions.com/en/virtual-power-plant/ ↩︎ 
- https://come-res.eu/fileadmin/user_upload/Resources/Deliverables/D8.7_AdvancingRenewableEnergyCommunitiesEurope_EN_web.pdf ↩︎