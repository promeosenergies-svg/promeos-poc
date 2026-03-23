# Cartographie Réglementaire Facture Énergie France — Q1 2026

**Agent** : SENTINEL-REG | **Date** : 2026-03-22 | **Périmètre** : Élec + Gaz, B2B + B2C

---

## 1. TURPE 7 — Acheminement Électricité

### 1. Faits juridiques
- **Type de texte** : Délibération CRE
- **Référence** : Délibération n°2025-78 du 13/03/2025 (HTA-BT) ; n°2025-77 (HTB)
- **Source** : [Légifrance HTA-BT](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051587195) ; [Légifrance HTB](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051587186)
- **Date publication** : 14 mai 2025
- **Date effet** : 1er août 2025 (durée 4 ans → 31/07/2029)
- **Statut** : EN VIGUEUR

Anticipation TURPE 6 : Délibération n°2025-08 du 15/01/2025 → +7,7% au 01/02/2025 (apurement CRCP).

### 2. Mécanisme concerné
- Principal : TURPE
- Secondaire : CTA (assiette modifiée), reprogrammation HP/HC Enedis

### 3. Segments impactés
- Énergie : Électricité
- B2B / B2C : Les deux
- Tous raccordés HTA-BT et HTB

### 4. Nature de l'impact
- Direct — visible sur chaque facture
- Au 01/08/2025 : −1,92% (transfert FACÉ vers budget État)
- Indexations futures : ~inflation au 1er août 2026, 2027, 2028

### 5. Lignes impactées
- Acheminement (composante principale)
- CTA (assiette = part fixe TURPE)
- TRVE (empilement)
- Offres de marché (pass-through)

### 6. Niveau d'impact : MAJEUR

### 7. Conséquence client
- B2B : Stabilisation ; attention reprog HP/HC
- B2C : Baisse intégrée dans TRVE

### 8. Conséquence PROMEOS
- Modules : Billing, Comparateur, Shadow billing, Cockpit
- Règles : Grilles TURPE 7 par puissance, nouvelles plages HP/HC
- QA : Recalcul acheminement tous profils

### 9. Actions
- Produit : Intégrer grilles TURPE 7, indexation annuelle
- Data : Tables tarifs au 1er août
- Juridique : Surveiller délibérations annuelles CRE

### 10. Incertitudes
- Niveau indexation 01/08/2026
- Calendrier reprog HC par zone Enedis

---

## 2. Accise sur l'Électricité (ex-TICFE / ex-CSPE)

### 1. Faits juridiques
- **Type de texte** : Loi de finances
- **Référence** : Loi n°2025-127 du 14/02/2025 ; Code des impositions
- **Source** : [impots.gouv.fr](https://www.impots.gouv.fr/taxes-interieures-de-consommation-tic) ; [ENGIE](https://entreprises-collectivites.engie.fr/actualites/ticfe-accise-electricite-point-taxe/)
- **Date effet** : 01/02/2026
- **Statut** : EN VIGUEUR

### 2. Mécanisme : Accise électricité + composante ZNI

### 3. Segments : Élec, B2B + B2C (taux différenciés)

### 4. Nature de l'impact
- Direct — ligne dédiée facture
- 30,85 €/MWh (ménages) ; 26,58 €/MWh (professionnels)
- +3% vs 2025

### 5. Lignes : Taxes/contributions, TRVE, offres marché

### 6. Niveau : MAJEUR

### 7. Conséquence client
- B2B : 26,58 €/MWh — vérifier taux réduits
- B2C : 30,85 €/MWh — fin bouclier

### 8. Conséquence PROMEOS
- Modules : Billing, Comparateur, Shadow billing, Fiscalité
- Règles : Taux par segment, taux réduits, exonérations

### 9. Actions
- Mise à jour taux au 1er février annuellement
- PLF 2027 : baisse prévue (à surveiller)

### 10. Incertitudes
- Montant exact PLF 2027
- Périmètre taux réduits post-réforme

---

## 3. VNU — Versement Nucléaire Universel (post-ARENH)

### 1. Faits juridiques
- **Type de texte** : Loi de souveraineté énergétique + décrets
- **Référence** : Art. L. 336-1 et s. Code de l'énergie
- **Source** : [Enercoop](https://www.enercoop.fr/blog/actualites/nationale/le-versement-nucleaire-universel) ; [SIRENergies](https://www.sirenergies.com/en/article/fin-arenh-2026-comprendre-le-dispositif-vnu)
- **Date effet** : 01/01/2026
- **Statut** : EN VIGUEUR (dormant — prix marché < seuils)

### 2. Mécanisme : VNU + fin ARENH (31/12/2025)

### 3. Segments : Élec, B2B + B2C (redistribution universelle)

### 4. Nature de l'impact
- Conditionnel — activé si prix > seuils
- Seuil 1 : 78 €/MWh ; Seuil 2 : ~110 €/MWh
- Prix actuel ~60 €/MWh → dormant au moins jusqu'en 2028
- EDF vend 100% nucléaire au marché (fin guichet ARENH 42 €/MWh)

### 5. Lignes : Fourniture, TRVE, offres marché, réconciliation

### 6. Niveau : CRITIQUE

### 7. Conséquence client
- B2B : Fin avantage ARENH 42€ → exposition marché directe
- B2C : Absorbé par TRVE tant que dormant

### 8. Conséquence PROMEOS
- Modules : Billing, Comparateur, Marché, Cockpit, Achat
- Règles : Supprimer ARENH 42€, logique VNU conditionnelle
- Alertes : Franchissement seuils 78/110 €/MWh

### 9. Actions
- Nouveau moteur pricing post-ARENH
- Flux prix marché spot/forward
- Pédagogie fin ARENH clients

### 10. Incertitudes
- Date activation effective VNU
- Révision triennale seuils CRE (~2028)

---

## 4. TRVE — Tarifs Réglementés de Vente d'Électricité

### 1. Faits juridiques
- **Type de texte** : Proposition CRE + arrêté ministériel
- **Source** : [CRE](https://www.cre.fr/actualites/toute-lactualite/la-cre-propose-de-maintenir-les-tarifs-reglementes-de-vente-de-lelectricite-ttc-stables-en-moyenne-au-1er-fevrier-2026-pour-les-consommateurs-souscrivant-une-puissance-inferieure-a-36-kva.html)
- **Date effet** : 01/02/2026
- **Statut** : EN VIGUEUR

### 2. Mécanisme : TRVE (Base/HP-HC/Tempo) + méthode option cible

### 3. Segments : Élec, B2C + petits pros ≤ 36 kVA

### 4. Nature de l'impact
- Direct — grilles réglementées
- −0,83% TTC moyen : Base −0,3%, HP/HC −1,7%, Tempo +6,2%

### 5. Lignes : Fourniture, acheminement, taxes (tout intégré)

### 6. Niveau : MAJEUR

### 7. Conséquence client
- Petits pros : Légère baisse sauf Tempo
- B2C : Stabilité globale

### 8. Conséquence PROMEOS
- Modules : Comparateur (référence TRV), Billing, Shadow billing
- QA : Recalcul comparateur à chaque mouvement

### 9. Actions
- Intégrer grilles février 2026, anticiper août 2026
- Alerter clients Tempo sur hausse

### 10. Incertitudes
- Mouvement août 2026
- Périmètre TRVE post-réforme

---

## 5. Mécanisme de Capacité Électricité

### 1. Faits juridiques
- **Type de texte** : Loi de finances 2025 + décret + délibérations CRE
- **Référence** : Délibération CRE n°2025-275 du 17/12/2025
- **Source** : [Capitole Energie](https://capitole-energie.com/2025/12/03/nouveau-mecanisme-de-capacite/)
- **Date effet** : Jan–mars 2026 (ancien) ; nov. 2026 (nouveau — acheteur unique RTE)
- **Statut** : TRANSITION → PUBLIÉ / APPLICATION FUTURE

### 2. Mécanisme : Garanties de capacité + réforme acheteur unique RTE

### 3. Segments : Élec, B2B + B2C

### 4. Nature de l'impact
- Direct/indirect — coût amont
- Enchères 2026 : 2,5–3,15 €/MW (bas historique)

### 5. Lignes : Capacité, fourniture, TRVE, offres marché

### 6. Niveau : WATCH → MAJEUR (réforme nov. 2026)

### 7. Conséquence client
- B2B : Coût très faible 2026 ; incertitude post-réforme
- B2C : Transparent dans TRV

### 8. Conséquence PROMEOS
- Préparer modèle nouveau mécanisme pour nov. 2026
- Tests transition ancien/nouveau

### 9. Incertitudes
- Prix sous nouveau régime
- Date exacte bascule

---

## 6. CEE — Certificats d'Économies d'Énergie

### 1. Faits juridiques
- **Type de texte** : Décret + arrêtés
- **Référence** : Décret n°2025-1048 du 30/10/2025
- **Source** : [ecologie.gouv.fr](https://www.ecologie.gouv.fr/politiques-publiques/dispositif-certificats-deconomies-denergie)
- **Date effet** : 01/01/2026 (P6)
- **Statut** : EN VIGUEUR

### 2. Mécanisme : CEE (obligations fournisseurs) + pénalités

### 3. Segments : Élec + Gaz, B2B + B2C

### 4. Nature de l'impact
- Indirect — coût amont, pas de ligne dédiée
- P6 : 1 050 TWhc/an (+35% vs P5)
- Répercussion : +4-6 c€/L carburant, +~13 €/an gaz

### 5. Lignes : Fourniture (intégré), offres/comparateurs, shadow billing

### 6. Niveau : MAJEUR

### 7. Conséquence client
- B2B : Hausse prix fourniture sans ligne explicite
- B2C : Hausse invisible

### 8. Conséquence PROMEOS
- Modéliser composante CEE implicite dans prix
- Flux prix CEE (Emmy)

### 9. Incertitudes
- Prix CEE sous P6
- Évolution fiches standardisées

---

## 7. CTA — Contribution Tarifaire d'Acheminement

### 1. Faits juridiques
- **Source** : [Opéra Energie](https://opera-energie.com/contribution-tarifaire-acheminement-cta/)
- **Date effet** : 01/02/2026
- **Statut** : EN VIGUEUR

### 2. Mécanisme : CTA (financement CNIEG)

### 3. Segments : Élec + Gaz, B2B + B2C

### 4. Nature de l'impact
- Direct — ligne dédiée
- Élec : 15% distribution (baisse ~25% vs 21,93%) / 5% transport
- Gaz : 20,80% distribution / 4,71% transport (inchangé)

### 5. Lignes : Taxes/contributions

### 6. Niveau : WATCH

### 7. Conséquence : ~−10 €/an élec par foyer

### 8. PROMEOS : Mise à jour taux CTA

---

## 8. TVA Énergie

### 1. Faits juridiques
- **Type de texte** : Loi de finances 2025, art. 20
- **Source** : [bofip.impots.gouv.fr](https://bofip.impots.gouv.fr/bofip/14639-PGP.html/ACTU-2025-00057)
- **Date effet** : 01/08/2025
- **Statut** : EN VIGUEUR

### 2. Mécanisme : TVA 20% uniforme (fin 5,5% abonnement)

### 3. Segments : Élec + Gaz, B2B + B2C

### 4. Nature de l'impact
- Direct — TVA 20% sur intégralité facture
- Compensé par baisse accise + TURPE → TTC quasi-stable

### 5. Lignes : TVA sur tous postes

### 6. Niveau : MAJEUR (structurel)

### 7. Conséquence client
- B2B : Neutre (récupération TVA)
- B2C : Hausse masquée par compensation

### 8. PROMEOS : TVA 20% uniforme, supprimer logique taux réduit

---

## 9. ATRD7 — Acheminement Gaz Distribution

### 1. Faits juridiques
- **Référence** : Délibération CRE n°2024-40 du 15/02/2024 ; n°2025-122 du 14/05/2025
- **Source** : [Légifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051670357)
- **Date effet** : Période 01/07/2024 – 30/06/2027 ; évolution annuelle 1er juillet
- **Statut** : EN VIGUEUR

Péréquation nationale : Loi de finances 2026 (19/02/2026) → consultation CRE pour 01/07/2026.

### 2. Mécanisme : ATRD + péréquation nationale + TDN

### 3. Segments : Gaz, B2B + B2C

### 4. Nature de l'impact
- Direct — acheminement distribution gaz
- Options T1-T4 + TP ; Rf + Rd

### 5. Lignes : Acheminement gaz distribution, CTA gaz, prix repère

### 6. Niveau : MAJEUR

### 7. PROMEOS : Grilles ATRD7, TDN, péréquation, mouvement 1er juillet

---

## 10. ATRT8 — Acheminement Gaz Transport

### 1. Faits juridiques
- **Référence** : Délibération CRE n°2026-28 du 28/01/2026
- **Source** : [Légifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053459757)
- **Date effet** : 01/04/2026 (+3,41%)
- **Statut** : PUBLIÉ / APPLICATION FUTURE

### 2. Mécanisme : ATRT + terme stockage

### 3. Segments : Gaz, B2B + B2C

### 4. +3,41% (inflation 0,41% + régularisation 3%)
Charges additionnelles : règlement UE 2024/1787 (méthane)

### 5. Lignes : Transport gaz, stockage, prix repère

### 6. Niveau : WATCH

---

## 11. Accise sur le Gaz (ex-TICGN)

### 1. Faits juridiques
- **Source** : [ENGIE](https://entreprises-collectivites.engie.fr/actualites/ticgn-accise-gaz-naturel-point-taxe/) ; [SEFE Energy](https://www.sefe-energy.fr/magazine/facture-de-gaz-laccise-sur-les-gaz-naturels-combustibles-anciennement-ticgn-evolue-au-1er)
- **Date effet** : 01/02/2026
- **Statut** : EN VIGUEUR

### 2. Mécanisme : Accise gaz + composante ZNI (5,66 €/MWh)

### 3. Taux : 16,39 €/MWh (dont 10,73 accise + 5,66 ZNI)

### 4. Calendrier aligné au 1er février (au lieu du 1er janvier)

### 5. Lignes : Taxes gaz, prix repère

### 6. Niveau : MAJEUR

### 7. PLF 2027 : hausse prévue (compensation baisse accise élec)

---

## 12. Prix Repère Gaz CRE

### 1. Faits juridiques
- **Référence** : Délibération CRE n°2025-238 du 29/10/2025
- **Source** : [CRE](https://www.cre.fr/consommateurs/prix-reperes-et-references/prix-repere-de-vente-de-gaz-naturel-a-destination-des-clients-residentiels.html) ; [Open data CRE](https://www.cre.fr/documents/open-data/construction-du-prix-repere-de-vente-de-gaz-de-la-cre.html)
- **Date effet** : Mensuel, méthodo révisée depuis 01/2026
- **Statut** : EN VIGUEUR

### 2. Construction : 80% indice mensuel + 20% trimestriel + coûts + taxes
Nouvelle composante risque depuis 02/2026.

### 3. Segments : Gaz, B2C résidentiel

### 6. Niveau : WATCH

### 7. PROMEOS : Import automatisé mensuel, intégrer composante risque

---

## 13. TDN — Terme de Débit Normalisé (Gaz)

### 1. Faits juridiques
- **Référence** : Délibération CRE n°2025-161 du 19/06/2025 (prestations GRD)
- **Source** : [GRDF — TDN](https://sites.grdf.fr/web/terme-debit-normalise) ; [Légifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051807406)
- **Date effet** : 01/07/2026
- **Statut** : PUBLIÉ / APPLICATION FUTURE

### 2. Mécanisme : TDN (autonome, distinct de l'ATRD)
Prestations associées : n°953 et n°954 « Étude adéquation poste livraison/besoins »

### 3. Segments
- Gaz, B2B uniquement
- Clients T1/T2/T3 avec débit normalisé > 40 Nm³/h
- B2C non concerné (99% à 6 ou 10 Nm³/h)

### 4. Nature de l'impact
- Direct — nouveau terme tarifaire acheminement
- 5,52 €/an/Nm³/h au 01/07/2026
- Principe : facturation proportionnelle au dimensionnement réseau

### 5. Lignes : Acheminement gaz (nouveau terme), contrat/poste livraison, shadow billing

### 6. Niveau : MAJEUR (B2B gaz)

### 7. Conséquence client
- B2B : Sites surdimensionnés pénalisés → opportunité optimisation
- Prestation GRDF n°953/954 pour vérifier adéquation

### 8. Conséquence PROMEOS
- Module TDN avec simulation économique
- Récupérer débit normalisé par site (flux GRDF)
- Alerte surdimensionnement
- QA : Tests T1/T2/T3 avec débit variable

### 9. Actions
- Développer module TDN
- Identifier clients surdimensionnés → proposition valeur
- Modéliser impact TDN sur portefeuille

### 10. Incertitudes
- Tarif définitif 01/07/2026
- Délai prestations adéquation GRDF
- Extension future autres segments

---

## 14. CPB — Certificats de Production de Biogaz

### 1. Faits juridiques
- **Type de texte** : Décret + Arrêté
- **Référence** : Décret n°2024-718 du 06/07/2024 ; Arrêté du 06/07/2024
- **Source** : [Légifrance Décret](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049891497) ; [Légifrance Arrêté](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049891614) ; [ENGIE CPB](https://entreprises-collectivites.engie.fr/actualites/tout-savoir-certificats-de-production-de-biogaz-cpb/)
- **Base légale** : Loi Climat et Résilience 22/08/2021 (art. L. 446-1 Code énergie)
- **Date effet** : 01/01/2026 (1ère période obligation)
- **Statut** : EN VIGUEUR

### 2. Mécanisme : CPB — MÉCANISME AUTONOME (distinct de « biométhane »)

### 3. Segments
- Gaz, B2B + B2C
- Fournisseurs gaz (obligés), producteurs biogaz (émetteurs CPB)

### 4. Nature de l'impact
- Indirect — coût amont, pas de ligne facture dédiée
- 2026 : 0,0041 CPB/MWh PCS
- 1ère période : 01/01/2026 – 31/12/2028 (montée progressive)
- Prix marché estimé : 70–100 €/CPB
- Pénalité : 100 € max/CPB manquant

### 5. Lignes : Fourniture gaz (amont), offres/comparateurs, shadow billing, réconciliation

### 6. Niveau : WATCH (2026) → MAJEUR (2027-2028)

### 7. Conséquence client
- B2B : +~0,3-0,4 €/MWh en 2026, croissant
- B2C : Quasi invisible en 2026

### 8. Conséquence PROMEOS
- Modéliser CPB dans coût fourniture gaz
- Décomposition coûts amont incluant CPB
- Documentation CPB distincte de biométhane

### 9. Incertitudes
- Prix réel CPB 2026 (liquidité incertaine)
- Quotas 2027-2028

---

## 15. Stockage Gaz — Terme Tarifaire

### 1. Faits juridiques
- **Référence** : Délibération CRE n°2025-36 du 29/01/2025 ; n°2025-76 du 12/03/2025
- **Source** : [Légifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051329726) ; [Selectra](https://selectra.info/energie/actualites/marche/factures-gaz-couts-stockage-explosion-avril-2026)
- **Date effet** : 01/04/2025 (en vigueur) ; 01/04/2026 (~+20%)
- **Statut** : EN VIGUEUR + À SURVEILLER (avril 2026)

### 2. Mécanisme : Terme stockage (intégré ATRT)
Opérateurs : Storengy (74,74%), Teréga (18,62%), Géométhane (6,64%)

### 3. Terme 2025 : 331,44 €/MWh/j/an (doublement vs 2024)
Hausse avril 2026 estimée : +20%

### 6. Niveau : MAJEUR

---

## 16. ETS2 — Quotas Carbone Bâtiments/Transport

### 1. Faits juridiques
- **Type de texte** : Règlement UE (Fit for 55)
- **Référence** : Directive 2003/87/CE révisée
- **Source** : [ecologie.gouv.fr](https://www.ecologie.gouv.fr/politiques-publiques/marches-du-carbone-seqe-ue-2) ; [ENGIE](https://entreprises-collectivites.engie.fr/actualites/restitution-quotas-carbone-tout-savoir-ets-2/)
- **Date effet** : Initialement 2027, reporté à 2028
- **Statut** : PUBLIÉ / APPLICATION FUTURE

### 2. Mécanisme : ETS2 (marché carbone bâtiment + transport)

### 3. Segments : Gaz chauffage + carburants, B2B + B2C

### 4. Plafond prix : 45 €/tCO₂ (prix 2020) jusqu'en 2029
Fournisseurs énergie = assujettis, consommateurs = payeurs finaux

### 6. Niveau : À SURVEILLER (2028+)

### 7. PROMEOS : Module prospectif impact ETS2 sur coûts gaz

---

## 17. Règles de Facturation Client

### 1. Faits juridiques
- Code de la consommation + Code de l'énergie
- **Source** : [service-public.fr](https://www.service-public.gouv.fr/particuliers/actualites/A18776)
- **Statut** : EN VIGUEUR (évolutions progressives)

### 2. Mécanismes
- Régularisation : remboursement 15 jours si > 25€
- Mouvements tarifaires calés au 1er février (élec + gaz)
- Méthode empilement TRVE par option cible
- Facturation électronique B2B (Factur-X) : déploiement 2026-2027

### 6. Niveau : WATCH

---

## Tableau de Synthèse

| # | Mécanisme | Énergie | Statut | Niveau | Prochaine date |
|---|-----------|---------|--------|--------|----------------|
| 1 | TURPE 7 | Élec | EN VIGUEUR | MAJEUR | 01/08/2026 |
| 2 | Accise élec | Élec | EN VIGUEUR | MAJEUR | 01/02/2027 |
| 3 | VNU | Élec | EN VIGUEUR (dormant) | CRITIQUE | Seuil 78€ |
| 4 | TRVE | Élec | EN VIGUEUR | MAJEUR | 01/08/2026 |
| 5 | Capacité | Élec | TRANSITION | MAJEUR | Nov. 2026 |
| 6 | CEE P6 | Élec+Gaz | EN VIGUEUR | MAJEUR | Continu |
| 7 | CTA | Élec+Gaz | EN VIGUEUR | WATCH | CNIEG |
| 8 | TVA | Élec+Gaz | EN VIGUEUR | MAJEUR | Structurel |
| 9 | ATRD7 | Gaz | EN VIGUEUR | MAJEUR | 01/07/2026 |
| 10 | ATRT8 | Gaz | PUBLIÉ | WATCH | 01/04/2026 |
| 11 | Accise gaz | Gaz | EN VIGUEUR | MAJEUR | 01/02/2027 |
| 12 | Prix repère | Gaz | EN VIGUEUR | WATCH | Mensuel |
| 13 | TDN | Gaz | PUBLIÉ | MAJEUR | 01/07/2026 |
| 14 | CPB | Gaz | EN VIGUEUR | WATCH→MAJEUR | Quota 2027 |
| 15 | Stockage | Gaz | EN VIGUEUR | MAJEUR | 01/04/2026 |
| 16 | ETS2 | Gaz | PUBLIÉ | À SURVEILLER | 2028 |
| 17 | Facturation | Élec+Gaz | EN VIGUEUR | WATCH | Continu |
