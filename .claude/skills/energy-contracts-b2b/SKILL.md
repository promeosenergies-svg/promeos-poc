---
name: energy-contracts-b2b
description: "Contrats énergie B2B France : structure cadre/annexe, CGV, négociation prix, clauses critiques (break clause, take-or-pay, indexation), courtage, appel d'offres, gestion risque prix, hedging, forward, spread, benchmark offres, switching, bande tolérance, TCO. Utiliser ce skill pour contrats énergie, achat, négociation fournisseur, appel d'offres, comparaison offres, clauses contractuelles, risque prix, courtier, renouvellement contrat, switching."
---

# Contrats Énergie B2B France

## Proactive triggers

- Contrat expire dans < 180 jours → "J-180: Lancer l'appel d'offres pour le renouvellement."
- Contrat expire dans < 90 jours → "J-90: Négociation critique. Short-list fournisseurs à finaliser."
- Commission courtier non documentée → "Red flag: commission courtier non-disclosed. Exiger annexe écrite."
- Puissance contrat ≠ puissance Enedis → "Incohérence puissance. Forcer recalibration pour optimiser le TURPE."

## Architecture contrat PROMEOS

### Hiérarchie

```
ContratCadre (EntiteJuridique)
├── fournisseur, dates début/fin, pricing model
├── base_tariff_grid, CGV, clauses spéciales
└── AnnexeSite[] (par PRM/PCE)
    ├── puissance souscrite, option tarifaire
    ├── volume prévisionnel, bande tolérance
    └── price_overrides (si différent du cadre)
```

resolve_pricing(annexe) → {price, source:'cadre'|'override'|'spot'|'profile'|'fallback'}

### Types de contrat

| Type | Périmètre | Typique pour |
|---|---|---|
| Contrat unique | 1 site, 1 PRM | PME mono-site |
| Contrat cadre + annexes | Multi-sites, 1 entité juridique | ETI, grands comptes |
| Accord-cadre | Multi-entités, holding | Groupes, collectivités |
| Groupement d'achat | Multi-organisations | UGAP, coopératives |

## Composantes contractuelles clés

### Prix et indexation

| Composante | Description | Vérification PROMEOS |
|---|---|---|
| Prix fourniture | €/MWh par période tarifaire | resolve_pricing vs facture |
| Abonnement | €/mois ou €/an, fixe | Prorata si période partielle |
| TURPE | Pass-through (régulé CRE) | Vérifié vs grille en vigueur |
| Taxes | Pass-through (accise, CTA, TVA) | Taux vs date de consommation |
| Capacité | Pass-through ou forfaitisé | Cohérence vs obligation RE |
| CEE | Inclus ou pass-through | Variable, ~0.3-0.5 €/MWh |
| Commission courtier | Fixe ou €/MWh (souvent opaque) | Exiger transparence |

### Clauses critiques — checklist

| Clause | Importance | Vérification |
|---|---|---|
| **Durée** | Fondamentale | 1-3 ans standard, >3 ans = break clause obligatoire |
| **Break clause** | Critique | Résiliation sans pénalité à date anniversaire |
| **Reconduction tacite** | Attention | Préavis 1-3 mois, à surveiller (alerte J-180) |
| **Indexation** | Critique | Formule détaillée, index de référence (EPEX, EEX, TRVE) |
| **Bande tolérance** | Important | Volume ±X% sans pénalité (standard ±10-15%) |
| **Take-or-pay** | Risque | Volume minimum à payer même si non consommé |
| **Clause de révision** | Important | Conditions de renégociation en cours de contrat |
| **Conditions résiliation** | Critique | Motifs, préavis, pénalités, force majeure |
| **Garanties** | Important | Caution bancaire fournisseur (critère CRE) |

## CGV — points de vigilance

| Point | Risque | Action |
|---|---|---|
| Révision de prix unilatérale | Fournisseur augmente sans accord | Refuser ou plafonner |
| Pénalités dépassement volume | Facturation majorée hors bande | Négocier bande ±15% minimum |
| Préavis résiliation court | Client piégé dans reconduction tacite | Alerter à J-180, J-90 |
| Changement réglementaire pass-through | Toutes hausses taxes répercutées | Standard, vérifier le mécanisme |
| Facturation estimée | Fournisseur facture sur estimation | Exiger relevé réel si Linky |
| Cessation activité site | Pénalités si fermeture site | Clause de sortie anticipée |

## Appel d'offres (AO) — processus complet

### Timeline

| Étape | J- | Contenu |
|---|---|---|
| Cadrage | J-180 | Définition besoin, budget, critères, périmètre sites |
| Cahier des charges | J-150 | CDC technique : volumes, profils, exigences qualité |
| Envoi aux fournisseurs | J-120 | 5-8 fournisseurs minimum (panel diversifié) |
| Questions/réponses | J-110 | Clarifications anonymisées |
| Réception offres | J-90 | Deadline ferme, offres valides 30j |
| Analyse comparative | J-75 | Grille multi-critères (prix, services, solidité, RSE) |
| Short-list + négo | J-60 | 2-3 finalistes, négociation directe |
| Choix final | J-45 | Validation interne (DAF/DG) |
| Signature | J-30 | Contrat + annexes par site |
| Notification ancien | J-21 | Résiliation + switching Enedis |
| Bascule | J-0 | Changement effectif, pas d'interruption |

### Grille d'évaluation type

| Critère | Poids | Éléments |
|---|---|---|
| Prix (TCO) | 40-50% | €/MWh total par période, abo, services inclus |
| Services | 15-20% | Plateforme client, reporting, alertes, interlocuteur dédié |
| Solidité financière | 10-15% | Rating, caution, ancienneté |
| Flexibilité contrat | 10-15% | Break clause, bande tolérance, options |
| RSE / verdissement | 5-10% | GO incluses, PPA, label EKOénergie |
| Références | 5% | Clients B2B similaires |

## TCO (Total Cost of Ownership)

Le prix €/MWh seul ne suffit pas. TCO annuel par site :

```
TCO = (prix_fourniture × volume)
    + abonnement_fourniture
    + TURPE (régulé, identique tous fournisseurs)
    + accise + CTA + TVA
    + capacité (si pass-through)
    + CEE (si pass-through)
    + commission courtier (si applicable)
    + coûts de gestion (factures, support)
```

PROMEOS calcule le TCO par site et par portefeuille pour comparer les offres.

## Switching (changement de fournisseur)

| Étape | Délai | Acteur |
|---|---|---|
| Notification résiliation | J-21 minimum | Client ou nouveau fournisseur |
| Demande Enedis (MES/MCH) | J-21 | Nouveau fournisseur via GRD |
| Relevé index changement | J-0 | Enedis (ou estimé si pas Linky) |
| Bascule effective | J-0 | Automatique, pas d'interruption |
| Dernière facture ancien | J+30 | Ancien fournisseur |
| Première facture nouveau | J+30 | Nouveau fournisseur |

**Aucun frais de changement**, aucune interruption (garanti par code de l'énergie).
Vérifier : pas de pénalité contrat en cours (hors période de break clause).

## Bande de tolérance volume

Standard : ±10-15% du volume prévisionnel annuel.

| Situation | Conséquence typique |
|---|---|
| Conso dans la bande | Pas de pénalité |
| Conso < bande basse | Take-or-pay : paiement du volume minimum |
| Conso > bande haute | Facturation au prix spot (souvent plus cher) |

Négociation : ±20% pour les sites avec forte variabilité. ±5% pour les contrats très compétitifs.
PROMEOS : alerte trimestrielle si trajectoire volume hors bande (projection linéaire).

## Red flags contrat

### Critiques

- Pas de break clause >3 ans → client piégé
- Index ARENH post-2025 → R12 (ARENH n'existe plus)
- Commission courtier non-disclosed → conflit d'intérêts
- Fournisseur sans caution bancaire → risque défaillance
- Take-or-pay sans bande → volume 100% à payer
- Clause de révision unilatérale → prix modifiable sans accord

### Attention

- Scope service pauvre (pas de plateforme, pas de reporting)
- Puissance souscrite ≠ Enedis (écart > 10%)
- Volume prévisionnel sans bande tolérance documentée
- Reconduction tacite avec préavis court (<3 mois)
- Facturation estimée alors que Linky disponible
- Pas de clause de sortie anticipée par site

## Stratégies de couverture prix

| Stratégie | Description | Risque | Adapté à |
|---|---|---|---|
| 100% fixe | Prix garanti 1-3 ans | Nul | Budget certain, PME |
| 100% spot | Indexé EPEX DA/ID | Très élevé | Industriels flexibles |
| 70/30 | 70% fixe + 30% spot | Modéré | Équilibre standard |
| Click & Fix | Fixations progressives sur Cal Y+1 | Variable (lissage) | Gros portefeuilles |
| Collar | Plancher + plafond, prime | Limité | Maîtrise budget |
| PPA + complément | ENR long terme + marché | Moyen | Objectifs RSE/CSRD |

Forward : Spot J+1, Month+1, Quarter+1, Calendar Y+1/Y+2/Y+3 (EEX, ICE, EPEX).
Spread : Cal Y+2 - Cal Y+1 donne la prime de terme. Spread négatif → marché en contango.

## Contrôles PROMEOS automatisés

| Contrôle | Fréquence | Seuil alerte |
|---|---|---|
| Prix facturé vs contrat | Mensuel | Écart >2% |
| Puissance atteinte vs souscrite | Mensuel | Atteinte >80% souscrite |
| Volume réel vs engagement | Trimestriel | Hors bande tolérance |
| Expiration contrat | Continu | J-180 info, J-90 critique |
| Reconduction tacite | Continu | J-préavis alerte |
| Index ARENH post-2025 | À la signature | Flag R12 immédiat |
| Break clause date | Annuel | J-90 avant date break |
| Solidité fournisseur | Semestriel | Dégradation note |

## 15 fournisseurs CRE seedés

EDF Entreprises, ENGIE Pro, TotalEnergies, Alpiq, OHM Énergie, Vattenfall, Mint Énergie, Ekwateur, La Bellenergie, Alterna, Octopus Energy, ilek, Dyneff, GreenYellow, jpme.

Parts de marché B2B (CRE T4 2025) : EDF ~65%, Engie ~12%, TotalEnergies ~8%, alternatifs ~15%.
