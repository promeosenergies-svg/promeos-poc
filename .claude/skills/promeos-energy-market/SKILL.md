---
name: promeos-energy-market
description: "Marché énergie B2B France : post-ARENH, VNU/CAPN/CPN, fournisseurs CRE, pricing (fixe/indexé/spot/TRVE), EPEX Spot, mécanisme capacité, forward, NEBCO, flexibilité, PPA, CEE P5/P6, structure marché de gros, responsable d'équilibre. Utiliser ce skill dès qu'il est question de prix énergie, achats, fournisseurs, contrats B2B, stratégie d'achat, marché spot, ARENH, VNU, TRVE, comparaison offres, NEBCO, forward, ou tout fonctionnement du marché électricité/gaz France."
---

# Marché Énergie B2B France

## Routing

| Contexte | Fichier |
|---|---|
| Matching CDC→contrat, scénarios d'achat, simulation | `references/purchase-strategies.md` |
| Tout le reste (post-ARENH, fournisseurs, spot) | Ce SKILL.md suffit |

## Proactive triggers

- Contrat avec indexation ARENH post-2025 → "R12: L'ARENH a pris fin le 31/12/2025. Cette indexation est caduque."
- Prix unitaire > 0.25 €/kWh en fixe → "Prix très élevé. Benchmark CRE T4 2025 = 0.10-0.16 €/kWh en fixe B2B."
- Pas de break clause sur contrat > 36 mois → "Contrat long sans clause de sortie. Risque de lock-in."

## Structure du marché

| Acteur | Rôle | Exemples |
|---|---|---|
| Producteur | Génère kWh (nucléaire, ENR, thermique) | EDF, Engie, TotalEnergies, CNR |
| Fournisseur | Achète en gros, vend au détail B2B/B2C | EDF Entreprises, Engie Pro, Alpiq |
| Responsable d'Équilibre (RE) | Garantit l'équilibre injection=soutirage | Chaque fournisseur ou délégué |
| Agrégateur | Valorise flexibilité (effacement, ENR) | Voltalis, Energy Pool, Enel X |
| Courtier | Intermédiation AO, pas de fourniture | Selectra, Opera Energie, CWape |
| GRD/GRT | Réseau (Enedis/RTE élec, GRDF/GRTgaz) | Enedis, RTE, GRDF, Teréga |

## Post-ARENH → VNU (depuis 01/01/2026)

ARENH (42 €/MWh, 100 TWh/an) terminé 31/12/2025.
Remplacé par le mécanisme VNU (Vente au prix Nucléaire régUlé) :

- **CAPN** (Coût d'Approvisionnement en Production Nucléaire) : prix de référence calculé par la CRE, reflète le coût complet du parc nucléaire EDF. Estimation ~70-80 €/MWh.
- **CPN** (Complément de Prix Nucléaire) : reversement si prix marché > CAPN. EDF reverse la différence aux fournisseurs alternatifs proportionnellement.
- Volume : basé sur les droits historiques des fournisseurs, décroissant sur 15 ans.
- Règle R12 PROMEOS : flag contrats avec indexation ARENH post-2025 → alerte anomalie.
- Impact pricing : les offres post-2026 intègrent CAPN comme composante de base au lieu de l'ARENH.

## TRVE (Tarif Réglementé de Vente d'Électricité)

Uniquement ≤36kVA (C5) et micro-entreprises ≤10 salariés. Fournisseur: EDF uniquement.
Composition TRVE: fourniture (~35-40%) + TURPE (~30%) + taxes (~25%) + marge (~5%).
TRVE août 2025 : ~0.2516 €/kWh TTC Base, ~0.2068/0.2776 €/kWh HC/HP (estimé post-TURPE 7).
Évolution : fixé semestriellement par CRE (fév + août), bouclier tarifaire terminé fin 2024.

## Modèles de pricing B2B

| Modèle | Risque client | Adapté à | Horizon |
|---|---|---|---|
| FIXE | Nul (prix garanti) | Budget prévisible, PME | 1-3 ans |
| FIXE_HOROSAISONNIER | Faible (prix par période) | Sites avec profil HP/HC marqué | 1-3 ans |
| FIXE_HORS_ACHEMINEMENT | Faible (fourniture fixe, TURPE régulé) | Standard grands comptes | 1-3 ans |
| INDEXE_SPOT | Élevé (exposition marché) | Flexibles, gros volumes | 1 an renouvelable |
| INDEXE_TRVE | Moyen (suit régulation) | Petits sites C5 | Variable |
| INDEXE_FORWARD | Moyen (suit Cal Y+1) | Hedging progressif | 1-3 ans |
| CLICK_AND_FIX | Variable (lissage) | Portefeuilles multi-sites | 1-3 ans, fixations partielles |

## Marché de gros — produits

**Spot** : Day-ahead (EPEX Spot, enchères 12h J-1), Intraday (continu, jusqu'à 5min avant).
**Forward** : Month+1, Quarter+1, Calendar Y+1/Y+2/Y+3 (EEX, ICE).
**Peak/Baseload** : Base = 24/7, Peak = 8h-20h lun-ven.

Statistiques EPEX 2025 : 513h prix négatifs, 1807h ≥100€/MWh. Volatilité record liée ENR intermittence.
HC méridiennes 11h-14h : creux de prix solaire, CRE 2026-33 crée nouvelle fenêtre.

## Mécanisme de capacité

Obligation : chaque fournisseur doit détenir des certificats de capacité (garanties MW) proportionnels à la consommation de ses clients en période de pointe.

- **PP1** : 10-15 jours/hiver, signal RTE J-1, 7h-14h ou 18h-20h
- **PP2** : 10-25 jours/hiver, signal RTE J-1
- Prix enchères RTE : variable annuel (2025 : ~20-40 k€/MW, hausse tendancielle)
- Répercussion client : €/MWh ajouté à la facture (composante "capacité")
- Calcul obligation : profilé sur consommation pointe du fournisseur

## CEE (Certificats d'Économies d'Énergie)

Mécanisme obligataire : fournisseurs (obligés) doivent financer des actions d'économie d'énergie.
- P5 (2022-2025) : objectif 3100 TWhc sur 4 ans. Prix : ~6-8 €/MWhc (2025).
- **P6 (2027-2030)** : objectif 1050 TWhc/an, nouveaux programmes, bonification tertiaire.
- Répercussion : ~0.3-0.5 €/MWh ajouté au prix fourniture.
- Opérations éligibles B2B : isolation, CVC, éclairage LED, GTB (BACS), variateurs, récup chaleur.
- Valorisation PROMEOS : identification opérations éligibles par site → estimation primes CEE.

## 15 fournisseurs CRE seedés

EDF Entreprises, ENGIE Pro, TotalEnergies, Alpiq, OHM Énergie, Vattenfall, Mint Énergie, Ekwateur, La Bellenergie, Alterna, Octopus Energy, ilek, Dyneff, GreenYellow, jpme.

Parts de marché B2B (CRE T4 2025) : EDF ~65%, Engie ~12%, TotalEnergies ~8%, alternatifs ~15%.

## Marché gaz B2B

- PEG (Point d'Échange Gaz) : marché unique France depuis 2018.
- TRV gaz : terminé 30/06/2023, tous clients en offre de marché.
- Prix repère gaz CRE : publié mensuellement, référence offres de marché.
- Forward gaz : TRS (Title Transfer Facility) + PEG.
- ATRT (transport GRTgaz/Teréga) + ATRD (distribution GRDF) = acheminement gaz.

## Stratégies d'achat

| Stratégie | Description | Profil client |
|---|---|---|
| Budget certain | 100% fixe, 1-3 ans | PME, budget contraint |
| Spot opportuniste | 100% indexé spot | Industriels flexibles |
| Hybride 70/30 | 70% fixe + 30% spot | Équilibre risque/opportunité |
| Click & Fix | Fixations progressives sur Cal Y+1 | Gros portefeuilles |
| PPA + complément | Portion ENR long terme + marché | Objectifs RSE/CSRD |
| Collar | Plancher + plafond, prime | Maîtrise budget max |
| Groupement d'achat | UGAP, CoopEnergie | Collectivités, mutualisé |

## Constantes

- ARENH historique: 42 €/MWh (terminé 31/12/2025)
- Accise élec: **25.79 €/MWh** (depuis 01/08/2025)
- TICGN: **15.43 €/MWh**
- Fallback PROMEOS: **0.068 €/kWh** (⚠️ PAS 0.18)
- CMDPS: **12.65 × h** (€/kW dépassé/heure)
- CTA: **27.04%** part fixe TURPE
