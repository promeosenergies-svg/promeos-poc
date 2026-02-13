# Ingestion Report: STOCKAGE_ACC

**Title:** Stockage et Autoconsommation Collective
**Content Hash:** 49c17273b9c4b4e5
**Ingested at:** 2026-02-11T19:36:21

## Pipeline Summary

| Step | Count |
|------|-------|
| Sections extracted | 44 |
| Chunks generated | 27 |
| YAML drafts created | 27 |

## Drafts by Type

- **checklist**: 1
- **knowledge**: 13
- **rule**: 13

## Drafts by Domain

- **acc**: 10
- **facturation**: 1
- **reglementaire**: 1
- **usages**: 15

## Sections

1. **Dossier Complet : Stockage & Autoconsommation Collective (B2B, France/Europe)** (level 1, 0 words)
2. **Executive Summary** (level 2, 386 words)
3. **A. Contexte & Drivers du Stockage** (level 2, 0 words)
4. **A.1 Pourquoi le Stockage Devient Clé en 2025-2026** (level 3, 180 words)
5. **A.2 Clarifications Concepts : TAc, TAp, Autonomie, Indépendance** (level 3, 172 words)
6. **A.3 Contexte Réglementaire France ACC 2025** (level 3, 126 words)
7. **B. Stockage : Technologies & Benchmark** (level 2, 0 words)
8. **B.1 Comparatif Technologique Multi-Critères Technologie CAPEX (€/kWh) Rendement (%) Durée idéale Cycles Cycle de Vie (ans) Avantages Limites Applicabilité ACC B2B Li-ion LFP 100–150 93–96 2–4 h 5000–8000 12–15 Densité, sûr, baisse prix rapide Coût initial, thermique ✅ RÉFÉRENCE 2025 Li-ion NMC 120–180 91–94 1–2 h 3000–5000 10–12 Ancien, connu, intégration Perte rapide, moins sûr, coûteux ⚠️ Transition LFP Sodium-ion 150–200 90–92 2–4 h 4000–6000 10–12 Abondant, recyclable, sûr Coût 30–40% + cher, moins dense ⛔ Niches industrielles Flow (Vanadium) 180–250 75–80 4–8 h+ 12000+ 20+ Long terme, décorrelé kWh, gestion chauffage Volumineux, coût initial, maintenance ⛔ Grands systèmes (MWh) Plomb (traditionnel) 60–80 85–90 0.5–2 h 800–1500 5–7 Pas cher, recyclable Lourd, toxique, obsolète ❌ À ÉVITER Supercapacitors 1000–5000 95 Secondes-minutes 1 000 000+ 10–20 Ultra-puissance, durée infinie Très cher €/kW, mini-capacité ⛔ Lissage pics nanosecondes Stockage thermique (ballons glace, TES) 20–50 80–95 Heures-jours ∞ 20+ Couplage CVC/génie climatique, bas coût Bâtiment-dépendant, peu flexible ⚠️ Niche tertiaire GTB Hydrogène vert 500–2000 25–40 Heures-jours 1000+ 15–20 Saisonnalité, industrie, multi-usages Perte énergétique, CAPEX très élevé, immaturité ⛔ Horizon 2030+ Batterie automobile V2G/V2B 100–150 (partagée) 92–96 1–4 h 5000+ (dégradation lente) 8–10 dans bâtiment Vecteur autre (mobilité), flexibilité, résilience Temps recharge limité, batterie vieillissante ⚠️ Cas IRVE + ACC** (level 3, 25 words)
9. **B.2 Règles de Dimensionnement** (level 3, 246 words)
10. **B.3 Schémas Raccordement : Où Placer la Batterie ?** (level 3, 259 words)
11. **C. Où le Stockage Est Pertinent (10 Cas d’Usage Classés par Valeur)** (level 2, 0 words)
12. **C.1 Les 10 Cas Positifs (GO Stockage)** (level 3, 1027 words)
13. **C.2 Les 6 Cas Négatifs (NO-GO Stockage)** (level 3, 511 words)
14. **D. Dimensionnement : Méthode Complète** (level 2, 0 words)
15. **D.1 Inputs Obligatoires (Checklist Data) Élément Source Format Utilité Courbes PV brutes Onduleurs, inverters CSV 15 min (puissance W) Calcul surplus, dimensionnement Courbes conso brutes Linky API Enedis ou compteurs CSV 15 min (kWh) par participant Alignement profil, clé répartition Année historique 12 mois min. Données représentatives Variance saisonnière Puissance souscrite site Contrat Enedis kW Dépassement coûts Tarifs Enedis (TURPE 7) CRE/Enedis tarif €/kWh soutirage, injection par zone ROI calc. Règles ACC (clé) Statuts PMO, décision admin % ou algorithme Comptabilité batterie Contrainte injection GRD Enedis lettres techniques kW limité Peak shaving necessity Localisation (adresses, lat/long) Google Maps Coordonnées Rayon 2 km validations Objectif client Réunion stakeholders TAc %, autonomie h, pics kW, budget Scope batterie** (level 3, 0 words)
16. **D.2 Processus de Dimensionnement (Étapes 1-6)** (level 3, 379 words)
17. **D.3 Tableau de Décision Simplifié (1 page) Profil ACC TAc sans batterie Surplus % conso Pics puissance Budget disponible Décision Batterie recommandée Petit tertiaire jour (20 kWc, 15 kWh/j conso) 55% 20% 8 kW 15 k€ ⚠️ MARGINAL 3–4 kWh si budget, sinon NON Multi-sites complémentaires (50 kWc, 5 entités, 40 kWh/j) 65% 25% 12 kW 30 k€ ✅ OUI 8–10 kWh / 12 kW Tertiaire désynchronisé (60 kWc, pic midi > pic soir) 40% 45% 30 kW 50 k€ ✅ OUI 15–20 kWh / 25 kW IRVE + ACC (100 kWc + 20 bornes) 50% 40% 70 kW pics 80 k€ ✅ OUI 30–40 kWh / 50 kW Industrie 24/7 résilience critique 35% 50% 150 kW 200 k€ ✅ OUI PRIORITAIRE 50–80 kWh / 80 kW + UPS Maison occupée soir mainly 75% 15% 3 kW 8 k€ ❌ NON Aucune (coût trop élevé) Ferme avec limitation GRD (120 kWc, plafond 30 kW) 20% 60% (injection bloquée) 80 kW 40 k€ ✅ OUI 20–25 kWh / 30 kW (limit) Collective complexe 10 entités (80 kWc) 50% 28% 15 kW 25 k€ ⚠️ DÉBAT GOUVERNANCE Si accord : 8–12 kWh, sinon NON** (level 3, 0 words)
18. **E. Business Models & Monétisation** (level 2, 0 words)
19. **E.1 Propriété Batterie : Trois Approches** (level 3, 233 words)
20. **E.2 Revenus Empilables (Stacking) & Modélisation Financière** (level 3, 412 words)
21. **E.3 Partage de Valeur dans ACC (Gouvernance + Transparence)** (level 3, 287 words)
22. **F. Architecture EMS/PMO & Mise en Conformité** (level 2, 0 words)
23. **F.1 Schéma Cible (Batteries + Comptage + Gouvernance) ┌─────────────────────────────────────────────────────────────┐** (level 3, 160 words)
24. **F.2 Fonctionnalités EMS Essentielles (MVP) Fonctionnalité Criticité Implémentation Collecte données 15-min Enedis 🔴 CRITIQUE API Data Connect OAuth2, chiffré, stockage cloud Prévision PV (météo + historiques) 🟡 HAUTE API meteo (Solcast, Clear Sky), ML local Calcul clé répartition (15 min) 🔴 CRITIQUE Moteur calcul SQL/Python, audit trail (journal changements) Optimisation batterie (dispatch) 🟡 HAUTE Heuristique simplifié (charge si surplus > seuil, décharge si deficit) ou MPC complet (AI) Facturation shadow billing 🔴 CRITIQUE Facture PDF/CSV par participant, export paiement SEPA, suivi impayés Dashboard cockpit PMO 🟡 HAUTE Vue temps-réel prod/conso/batterie, KPI TAc/TAp/cycles, historiques API REST données publiques 🟢 MOYENNE Endpoints GET site/ 😀 KPI, POST commandes (si autorisé) Alertes & notifications 🟢 MOYENNE Email, SMS, Slack webhook sur anomalies (dérive, batterie faible) Conformité règles ACC (rayon 2km) 🔴 CRITIQUE Géolocalisation PDL auto-check distance producteur-consommateur Audit / Traçabilité 🟡 HAUTE Log toutes décisions algo, facturation, changements clé (blockchain optionnel) Intégration GTB/IoT partenaire 🟢 MOYENNE MQTT/BACnet bridge, déploiement futur V2** (level 3, 0 words)
25. **F.3 Risques Conformité & Mitigation** (level 3, 368 words)
26. **G. Benchmark Europe & Monde : Tendances 2025-2026** (level 2, 0 words)
27. **G.1 Situation Réglementaire Comparée Pays Status Batterie BESS Incitation Prix Règles ACC/Communautés Barrier d’Entrée 🇫🇷 France Tari TURPE 7 injection-soutirage août 2026, favorab… ✅ Tarif local dynamique, mFRR obligation 2026 > 10 MW ✅ Décret 2017-676 ACC cadre clair, PMO simple ⚠️ Comptage complexe si batterie commune, réglementACC encore rigide 🇩🇪 Allemagne Exempt grid fees 2026–2029 (extension), privilège planning § 35 BauGB ✅ Marchés intraday volatiles, revenu arbitrage fort ✅ Genossenschaft (coop) + tiers-lieux, cadre très flexible ✅ Planification favorable (sauf distance 200m contrainte 2025) 🇵🇱 Pologne Peu réglementé, pricing incitatif début ⚠️ Électricité bon marché localement, arbitrage limite ❌ Communautés émergeantes, cadre incomplet ⚠️ Infrastructure DNO ancienne, grid faible stabilité 🇸🇪 Suède Batterie intégrée hydroélectricité (balancing clé) ✅ Revenu balancing très élevé (Nordic price) ⚠️ Micro-réseaux avancés, ACC peu pertinent ✅ Infrastructure VPP leader (Statkraft 10 GW) 🇮🇹 Italie Amélioration 2024–2025, tarifs légaux introduction ⚠️ Projet tarifario (en cours 2025), non encore appliqué ✅ Comunità energetiche décret stable (2017), retard implmentation ❌ Contexte politique instable, barrière légale RECs fournitures 🇳🇱 Pays-Bas Flexgrids 2025+, tarif dégressif injection ✅ Marché prix temps-réel maître, arbitrage optimisé ✅ Energiecoöperaties framework mature, 200+ opérationnels ✅ Leader Europe, modèles copiables (ZuidtrAnt, etc.) 🇬🇧 Royaume-Uni Post-Brexit, cadre réglementaire clarification 2025 ⚠️ Marché prix élevé, tarif batterie non harmonisé ❌ Community Energy peu soutenu après politique, modèles rares ⚠️ Coût batterie + électricité élevés (ROI difficile) 🇪🇸 Espagne Légalisation autoconsumo colectivo 2021–2023, in momentum ✅ Tarif autoconsommation compétitif, ajustement annuel ✅ Marcos normativos ACC claro desde 2021, maturité montante ✅ Boom PV + ACC simultané, modèles répliquent rapide 🇨🇭 Suisse Batteri peu incentivée (électricité bon marché historiquement) ⚠️ Tarif faible injection, arbitrage nul ✅ Micro-réseaux décentralisés normatif ✅ Léger, infrastructure stable, peu nécessité batterie 🇯🇵 Japon Très matur, batterie réseau grande capacité (GW) ✅ Régulation marché souple, service ancillaire fortement rémunérés ⚠️ Communautés énergie peu développées (focus centralisé EDF-type) ✅ Leader tech batterie (Sony, Panasonic), mais coûteux** (level 3, 31 words)
28. **G.2 Business Models Leaders Observés (Europe)** (level 3, 276 words)
29. **H. Recommandations Actionnables & Roadmap** (level 2, 0 words)
30. **H.1 Guide Décision (Arbre GO/NO-GO) START : "Faut-il une batterie pour notre ACC ?"** (level 3, 266 words)
31. **H.2 Playbooks Exécution (Par Scénario)** (level 3, 0 words)
32. **Playbook A : ACC Petit Tertiaire (1 producteur, 2–3 consommateurs, 20–40 kWc)** (level 3, 253 words)
33. **Playbook B : ACC Multi-Sites Tertiaire/Industrie (5–10 entités, 80–200 kWc, budget 50+ k€)** (level 3, 418 words)
34. **H.3 Architecture Cible EMS + Fonctionnalités Clés** (level 3, 180 words)
35. **I. Risques & Conformité Avancée** (level 2, 0 words)
36. **I.1 Matrix Risques Batterie ACC (Probabilité × Impact) Risque Prob Impact Mitigation Coût Mitigation Batterie défaut / courte durée (5 ans au lieu 12) Moyen (15%) 🔴 ÉLEVÉ (perte 50% ROI) Contrat garantie constructeur 10 ans, assurance BEEM 1–2 k€/an (assurance) Comptage Enedis réconciliation erreur (écart > 10%) Faible (5%) 🟠 MOYEN (conflit facturation, dispute 20 k€) Audit annuel comptage vs physique, fonds risque 3% énergie 1 k€/an audit Changement tarif TURPE 2027–2028 annule ROI Moyen (20%) 🟠 MOYEN (ROI 5 ans → 12 ans) Contrats indexation plafonnés (+2%/an max), clauses renégociation 2 k€ légal Batterie non conforme ICPE (classification tardive) Faible (8%) 🔴 ÉLEVÉ (arrêt, amende 10 k€, délai 6 mois) Pre-audit ICPE, dossier avant installation (< seuil = 0 impact) 3–5 k€ pré-audit Cyber-attaque EMS (vol clé répartition, sabotage) Très faible (2%) 🔴 ÉLEVÉ (perte confiance, litige 100 k€+) MFA 2FA, chiffrement TLS 1.3, pentest annuel, assurance cyber 5–10 k€/an Batterie surcharge/incendie (sécurité) Très faible (< 1%) 🔴 CRITIQUE (blessés, dégâts, responsabilité civile) BMS certifié, entretien régulier, assurance responsabilité (existe) 0 (inclus assurance bâtiment) Participants quittent ACC → perte de mutualité Moyen (15%) 🟠 MOYEN (batterie sous-utilisée, ROI dilué) Contrats pluriannuels (5 ans min.), pénalités sortie 5 k€ légal Délai implémentation > 12 mois (scope creep) Moyen (25%) 🟠 MOYEN (coûts +20%, batterie obsolète) Planning PERT ferme, jalons clairs, change management 0 (management) EMS non compatible future API Enedis 2027 Moyen (20%) 🟠 MOYEN (refonte logiciel 15 k€) Architecture modulaire EMS, liaison fabricant, contrat support 2027+ 0 (si build flexible) Batterie volée / acte de vandalisme Faible (5%) 🟠 MOYEN (remplacement 15 k€, coupure 2 mois) Clôture sécurité, vidéo surveillance, assurance vol 2–3 k€/an (surveillance)** (level 3, 0 words)
37. **I.2 Conformité Réglementaire (Checklist Pré-Installation)** (level 3, 169 words)
38. **I.3 Recommandations Avancées pour PROMEOS (Cockpit EMS Nouvelle Génération)** (level 3, 197 words)
39. **J. Conclusion & Recommandations Décision** (level 2, 0 words)
40. **Synthèse Exécutive :** (level 3, 275 words)
41. **Annexes** (level 2, 0 words)
42. **Glossaire** (level 3, 122 words)
43. **Checklists Implémentation (Téléchargeable)** (level 3, 27 words)
44. **Références & Sources (Liens + Dates)** (level 3, 650 words)

## Generated Drafts

| ID | Type | Domain | Confidence | Status |
|----|------|--------|------------|--------|
| STOCKAGE_ACC_0 | rule | usages | low | draft |
| STOCKAGE_ACC_1 | rule | usages | low | draft |
| STOCKAGE_ACC_2 | knowledge | usages | low | draft |
| STOCKAGE_ACC_3 | rule | acc | low | draft |
| STOCKAGE_ACC_4 | rule | acc | low | draft |
| STOCKAGE_ACC_5 | knowledge | usages | low | draft |
| STOCKAGE_ACC_6 | knowledge | acc | low | draft |
| STOCKAGE_ACC_7 | rule | usages | low | draft |
| STOCKAGE_ACC_8 | knowledge | usages | low | draft |
| STOCKAGE_ACC_9 | knowledge | facturation | low | draft |
| STOCKAGE_ACC_10 | knowledge | usages | low | draft |
| STOCKAGE_ACC_11 | rule | usages | low | draft |
| STOCKAGE_ACC_12 | knowledge | usages | low | draft |
| STOCKAGE_ACC_13 | knowledge | acc | low | draft |
| STOCKAGE_ACC_14 | rule | acc | low | draft |
| STOCKAGE_ACC_15 | knowledge | reglementaire | low | draft |
| STOCKAGE_ACC_16 | knowledge | acc | low | draft |
| STOCKAGE_ACC_17 | knowledge | usages | low | draft |
| STOCKAGE_ACC_18 | rule | acc | low | draft |
| STOCKAGE_ACC_19 | rule | usages | low | draft |
| STOCKAGE_ACC_20 | knowledge | acc | low | draft |
| STOCKAGE_ACC_21 | checklist | usages | low | draft |
| STOCKAGE_ACC_22 | knowledge | usages | low | draft |
| STOCKAGE_ACC_23 | rule | usages | low | draft |
| STOCKAGE_ACC_24 | rule | usages | low | draft |
| STOCKAGE_ACC_25 | rule | acc | low | draft |
| STOCKAGE_ACC_26 | rule | acc | low | draft |

## Next Steps

1. Review drafts in `docs/kb/drafts/STOCKAGE_ACC/`
2. Upgrade confidence and refine tags/logic for each draft
3. Promote to validated: `python backend/scripts/kb_promote_item.py <file.yaml>`
4. Import to DB: `python backend/scripts/kb_seed_import.py --include-drafts`
5. Rebuild FTS index: `python backend/scripts/kb_build_index.py`
