# Doctrine Courbes de Charge Enedis -- Directives Claude Code

Sources : `DOCTRINE_COURBES_CHARGE_ENEDIS_PROMEOS.md` + `Doctrine experte exploitation CDC` (Avril 2026)

## Directives pour Claude Code

### Regles imperatives

1. **Stockage UTC, affichage Europe/Paris** -- Toujours `datetime(timezone.utc)` en DB, conversion `Europe/Paris` uniquement a l'affichage
2. **Changements d'heure** -- 46 pas (ete) ou 50 pas (hiver) par jour de transition. Utiliser `pd.date_range(tz='Europe/Paris')` pour generer les pas. Ne JAMAIS hardcoder 48 pas/jour
3. **Unite** -- DataConnect renvoie W (puissance moyenne) ou Wh (energie) selon endpoint. Toujours verifier l'unite avant calcul. `E_30min(Wh) = P_moyenne(W) * 0.5`
4. **Courbes fictives** -- JAMAIS utiliser pour benchmark, diagnostic ou optimisation. Uniquement test/demo/seed
5. **Profils types** -- S'ecartent de 20-40% de la realite. Toujours afficher comme "estimation" avec disclaimer
6. **Consentement** -- Max 3 ans (P3Y). Prevoir renouvellement automatique avec notification a M-3
7. **Fenetre SGE** -- Max 7 jours consecutifs par requete CDC pour C2-C4. Pagination obligatoire
8. **Score qualite** -- `Q = 1 - (trous + aberrants + incoherents) / total_pas`. Seuils : >0.95 Excellent, 0.90-0.95 Bon, 0.80-0.90 Acceptable, <0.80 Insuffisant
9. **NILM** -- Ne PAS vendre comme fonctionnalite. Utiliser heuristiques metier (baseload nuit = veilles, correlation DJU = chauffage)
10. **Fallback obligatoire** -- PROMEOS doit produire de la valeur meme avec uniquement donnees publiques + factures. Jamais d'ecran vide

### Pas de temps par segment

| Segment | Compteur | Pas mesure | Pas publie | Canal |
|---|---|---|---|---|
| C1 | HTA (ICE, SAPHIR) | 10 min | 10 min | SGE SOAP |
| C2 | HTA (ICE, SAPHIR) | 10 min | 10 min | SGE SOAP |
| C3 | HTA (ICE, SAPHIR) | 10 min | 10 min | SGE SOAP |
| C4 | PME-PMI, BT >36 kVA | 10 min | 10 min | SGE SOAP |
| C5 Linky | Compteur communicant | variable | 30 min | DataConnect REST |
| C5 ancien | Electromecanique | pas de courbe | N/A | Index uniquement |

**Linky -- details critiques :**
- Enregistrement courbe de charge **inhibe par defaut**. Le client doit l'activer explicitement (espace client Enedis)
- Capacite : 3600 enregistrements max (= 75 jours a 30min, ou 25 jours a 10min)
- Taux activation actuel : ~30% (opt-in). CRE propose passage opt-out (cf. section evolution reglementaire)
- Linky communicant ~1 mois apres installation
- **Arrondi a l'entier kW** : perte precision 0.5 kWh/pas. Significatif pour petits consommateurs
- Pas configurable : 10, 15, 30, 60 min selon niveau de service active

### Cinq couches d'acces aux donnees

| Couche | Canal | Acces | Granularite | Priorite PROMEOS |
|---|---|---|---|---|
| Open Data public | data.enedis.fr | Libre | 15min a annuel | P1 (benchmark) |
| Profils reglementaires | opendata.enedis.fr | Libre | 30 min | P1 (shadow billing) |
| DataConnect REST | OAuth2 C5 Linky | Consentement | 30 min | P0 (petit tertiaire) |
| SGE SOAP/Portail | C1-C5, P1-P4 | Accord client + habilitation | 10 min | P0 (ETI/grand tertiaire) |
| Flux marche | R10, R50, R4X, IFJ | Fournisseur titulaire | 10-30 min | P2 (monitoring continu) |

### Sources Open Data exploitables (4 datasets cles)

| Dataset | URL path | Dimensions | Interet |
|---|---|---|---|
| Bilan electrique 15min | `bilan-electrique` | National, par segment C1-C5 | Contexte macro, benchmark portfolio |
| Agregats <=36 kVA | `conso-inf36` | profil x plage puissance | Benchmark C5, profils moyens |
| **Agregats >36 kVA** | `conso-sup36` | **profil x puissance x NAF** | **CRITIQUE** -- seule source publique benchmark sectoriel B2B |
| Coefficients profils | `coefficients-des-profils` | RES/PRO/ENT/PRD, statiques+dynamiques | Shadow billing, estimation pre-CDC |

### Pipeline de traitement CDC

```
COLLECTE -> VALIDATION -> NETTOYAGE -> NORMALISATION -> ANALYSE -> INTERPRETATION -> ACTION
```

**Controles qualite a l'ingestion :**
1. Completude : 48 pas (30min) ou 144 pas (10min) par jour, sauf changement heure
2. Trous : seuil critique >5% sur periode d'analyse
3. Doublons : meme horodatage, valeurs differentes (changements heure, reprises)
4. Ruptures : z-score entre pas consecutifs, detection changement compteur/puissance
5. Valeurs aberrantes : P < 0 (soutirage), P = 0 prolonge, P >> P_souscrite
6. Coherence : `|sum(CdC) - delta_Index| < 5%` sur meme periode
7. Changements granularite : resampling au pas le plus grossier pour comparaison

### Signatures typiques par batiment

| Type | Baseload relatif | Thermosensibilite | Horaires |
|---|---|---|---|
| Bureaux | 25-40% | Forte (chauffage+clim) | Tres marques LV 9h-18h |
| Commerce | 20-35% | Moyenne (clim ete) | Horaires ouverture |
| Hotellerie | 40-60% | Moyenne-forte | WE ~ semaine |
| Enseignement | 15-25% | Forte | Tres variables (vacances) |
| Sante (hopital) | 60-80% | Moyenne | Peu marques (24/7) |
| Data center | 85-95% | Faible | Quasi nuls |
| Entrepot logistique | 20-50% | Faible-moyenne | Marques semaine |
| Industrie process | 50-80% | Faible | Selon shifts |
| Eclairage public | 0% jour | Faible | Anti-solaire |

### Matrice droits d'acces

| Demandeur | Donnees | Accord client | Canal |
|---|---|---|---|
| Client lui-meme | Toutes | Non | Espace Client web |
| Fournisseur titulaire | R10, R50, R4X (fil de l'eau) | Non requis | Flux automatiques |
| Fournisseur titulaire | Historique CDC + index | Oui (C5) | SGE M023/WS |
| Fournisseur non titulaire | Historique (acces restreint) | Oui | SGE |
| Tiers habilite (EMS) | CDC, index, contractuel | Oui | DataConnect (C5) / SGE (C2-C4) |
| Collectivite | Patrimoine public + agregats | Cadre legal CGCT | Portail collectivites |

### Roadmap d'exploitation industrielle

| Niveau | Donnees | Valeur | Horizon |
|---|---|---|---|
| 1 -- Benchmark public | Agregats + profils + ADEME/OPERAT | Intelligence sans donnee client | Mois 1-3 |
| 2 -- Simulation | Courbes fictives + profils types + factures | Produit demontrable, onboarding | Mois 2-4 |
| 3 -- Collecte reelle | DataConnect C5 + SGE C2-C4 | Pilotage reel (carpet, signature, gaspillage) | Mois 3-9 |
| 4 -- Multi-sites | Dizaines a centaines de sites | Portfolio scoring, priorisation | Mois 6-12 |
| 5 -- Analytics IA | Clustering, anomaly detection, forecasting | Intelligence augmentee | Mois 9-18 |
| 6 -- Activation business | IFJ temps reel + spot + flex | ROI monetaire direct | Mois 12-24 |

### Evolution reglementaire -- opt-out CRE (2026+)

La CRE propose de passer du modele actuel **opt-in** (30% activation courbes Linky) a un modele **opt-out** (activation par defaut, droit de retrait). Si adopte :
- Explosion volume donnees disponibles
- Opportunites massives EMS, flexibilite, IA predictive
- Modification Code consommation + avis CNIL requis
- Risque opposition associations consommateurs (vie privee : courbes 10min revelent habitudes)

**Impact PROMEOS** : surveiller cette evolution. Si opt-out adopte, l'onboarding DataConnect passe de "friction consentement" a "activation par defaut" -- game changer pour l'acquisition.

### ACC -- pas 15 minutes (depuis octobre 2024)

Depuis oct 2024, Enedis publie les courbes ACC au **pas 15 minutes** (avant : 30 min). Conformite article D315-1 Code energie. Impact sur :
- Repartition plus fine production/consommation participants
- Meilleur matching profils complementaires
- Outils tiers ACC (Coturnix, Enogrid, Sween) exploitent deja ce pas

### Secret statistique -- regles de publication

Les agregats Open Data ne sont publies que si :
- **Residentiel** : nombre sites >= 10
- **Professionnel** : nombre sites >= 10 OU consommation > 50 MWh

En dessous : valeur masquee (protection donnees personnelles). Attention aux trous dans les datasets a maille fine (IRIS, commune).

### Portail Collectivites Enedis

Source additionnelle pour segment collectivites :
- **Patrimoine propre** : acces direct courbes sites publics (ecoles, mairies, eclairage public) sans consentement (titulaire contrat)
- **Territoire** : agregats publics uniquement
- **Administres** : PAS d'acces sans consentement individuel (meme si collectivite AODE)
- **Fonctionnalites** : alertes depassement, cartographie capacite reseau raccordement EnR, bilan electrique territoire

### Architecture produit 4 phases (contrainte RGPD)

| Phase | Donnees | Friction | Valeur |
|---|---|---|---|
| 1 -- Acquisition | Courbes fictives NAF + agregats publics | Faible (pas de consentement) | Simulation, benchmark generique |
| 2 -- Onboarding | Consentement DataConnect OAuth2 | **Elevee** (taux conversion critique) | Acces donnees reelles |
| 3 -- Exploitation | CDC reelles 10-30min | Faible (automatique post-consent) | Pilotage, alertes, shadow billing |
| 4 -- Retention | Renouvellement consentement a M-33 | Moyenne (risque churn) | Continuite service |

**Impact economique** :
- LTV menacee si client revoque/ne renouvelle pas -> retour phase 1
- CAC augmente par friction consentement -> taux conversion plus faible
- Differenciation = prouver ROI consentement ("en acceptant, vous economisez X euros/an")

### Types de courbes -- precision technique

| Type | Description | Usage |
|---|---|---|
| **Brute** | Telereleve directe du compteur, sans traitement | Analyse comportementale (preferer si dispo) |
| **Corrigee** | Corrections aberrations, derives horloge, facteurs transformateurs | Facturation marche |
| **Completee** | Trous reconstitues par estimation (panne, coupure) | Exhaustivite facturation -- signaler en analyse |

**Regle Claude Code** : en analyse, toujours filtrer/ponderer selon qualite. Une courbe majoritairement completee (indice vraisemblance eleve) est moins fiable. Privilegier donnees brutes ou corrigees.

### Horodatage mensuels R6X (entreprises >36 kVA)

Les courbes mensuelles professionnels demarrent le **1er du mois a 2h00** et se terminent le **1er du mois suivant a 2h00**. Convention qui facilite gestion changements d'heure mais necessite **correction pour facturation en heures calendaires** (0h00 a 0h00).

### Differenciateurs concurrentiels

| Differenciateur | Moat |
|---|---|
| Maitrise DataConnect + SGE + GRDF | Complexite technique (SOAP+OAuth2+consentements) disqualifie 90% des concurrents |
| Carpet plot 24hx365j | Impact visuel immediat, diagnostic 5 secondes |
| Signature energetique E=axDJU+b | Standard ISO 50001 rarement automatise dans les EMS SaaS |
| Benchmark NAF croise Enedis | Agregats >36 kVA : source publique meconnue, rarement integree |
| Coherence cross-module | CDC -> trajectoire DT -> conformite -> facture -> achat -> action |
