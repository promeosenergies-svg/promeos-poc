---
name: promeos-billing
description: "Expertise facture énergie France B2B : shadow billing, TURPE 6/7, accise, TICGN, CTA, TVA, CEE, VNU, capacité, structure facture EDF/Engie, audit anomalies, reclaim, prorata, régularisation, grilles chiffrées. Utiliser ce skill dès qu'il est question de factures d'énergie, shadow billing, vérification de facture, composantes tarifaires, TURPE, acheminement, taxes énergie, anomalies facture, recalcul facture, détection d'erreurs facture, prix énergie, ou toute ligne de facture électricité/gaz."
---

# PROMEOS Billing Intelligence

## Routing — Quand lire quel fichier

| Question / Contexte | Fichier reference à lire |
|---|---|
| Grilles tarifaires TURPE, valeurs €/kWh | `references/turpe7-grilles.md` |
| Vérification de facture, checklist, reclaim | `references/shadow-billing-checklist.md` |
| Benchmark marché, prix de gros, concurrence, ARENH, post-ARENH, CPPA | `references/benchmark-marche-2024.md` |
| Stockage batteries, flexibilité, autoconsommation, FCR, agrégation | `references/benchmark-stockage-2023.md` |
| Photovoltaïque, autoconsommation, PPA, soutien PV, agrivoltaïsme, panneaux | `references/benchmark-photovoltaique-2024.md` |
| Stratégie produit, positionnement, moats, pricing, GTM, concurrence | `docs/PROMEOS_STRATEGIE_FOURNISSEUR_4.0.md` |
| Tout le reste (pipeline, anomalies, cascade prix) | Ce SKILL.md suffit |

## Proactive triggers — Alerter sans qu'on demande

- Facture avec TURPE 6 après 01/08/2025 → "Cette facture utilise encore les tarifs TURPE 6. Vérifier si la transition TURPE 7 a été appliquée."
- Prix unitaire > 0.20 €/kWh sur contrat fixe → "Prix anormalement élevé pour un contrat fixe B2B. Benchmark CRE T4 2025 = 0.12-0.16 €/kWh."
- Accise ≠ taux en vigueur → "Vérifier le taux accise : T1=30.85 €/MWh (ménages), T2=26.58 €/MWh (PME/pro) depuis 01/02/2026. Ancien taux 25.79 €/MWh valable 01/08/2025-31/01/2026."
- Écart shadow billing > 5% → "Anomalie BILL_001 détectée. Écart significatif entre recalcul et facture."
- Doublon PRM + même période → "CRITICAL BILL_006 : doublon de facturation potentiel."

## Contexte marché 2024 — Vision Les Echos Études (déc 2024)

### Prix de référence fin 2024

| Indicateur | Valeur | Tendance |
|---|---|---|
| Prix spot day-ahead (nov 2024) | 100 €/MWh | Élevé vs 2010-2020, mais 5x moins qu'août 2022 (492 €/MWh) |
| Calendaire Y+1 moy 2024 | 77 €/MWh | Baisse rapide depuis pic 365 €/MWh (2022) |
| Calendaire Y+2 moy 2024 | 67 €/MWh | Convergence vers ~70 €/MWh cible post-ARENH |
| TRVE résidentiel base | 251,6 €/MWh TTC | Baisse ~10% attendue fév 2025 |
| GO (garanties d'origine) | 0,45 €/MWh | Quasi-gratuit — offre verte = pas de surcoût |
| Garanties de capacité (9e enchère 2025) | 0 €/MW | Nucléaire rétabli, surcapacité |
| Prix B2B fin 2023 vs 2021 | +50% | Inertie contrats, normalisation en cours |
| ARENH (dernière année) | 42 €/MWh | Fin définitive 31/12/2025 |

### Décomposition facture résidentielle TRVE (CRE 2024)

| Composante | % facture TTC | Impact shadow billing |
|---|---|---|
| Fourniture | **54%** | Variable clé — prix spot ou fixe |
| TURPE | **22%** | Réglementé, stable intra-période |
| TVA | **15%** | Calculable (5.5% + 20%) |
| Accise | **7%** | Taux temporel critique |
| CTA | **2%** | % part fixe TURPE |

### Brique énergie dans le TRVE (CRE, €/MWh)

| Année | ARENH | Marché lissé | Complément écrêtement | Total énergie |
|---|---|---|---|---|
| 2019 | 21.4 | 17.6 | 10.0 | 49.0 |
| 2020 | 19.3 | 19.9 | 10.1 | 49.3 |
| 2021 | 19.5 | 18.9 | 10.3 | 48.7 |
| 2022 | 17.5 | 28.8 | 63.9 | 110.2 |
| 2023 | 18.9 | 124.2 | 89.8 | 232.9 |
| 2024 | 18.8 | 91.1 | 13.9 | 123.8 |

> Ces données calibrent le module de benchmark prix PROMEOS : un prix fourniture < 60 €/MWh est attractif post-ARENH, > 90 €/MWh signale un contrat à renégocier.

### Post-ARENH — Nouvelles règles d'approvisionnement (2026+)

| Mécanisme | Détail | Impact PROMEOS |
|---|---|---|
| CAPN (Contrats Allocation Production Nucléaire) | 10-15 ans, partage risque dispo nucléaire, cible électro-intensifs | Nouveau type contrat à modéliser |
| Contrats moyen terme EDF | 4-5 ans, ~60 €/MWh, B2B pro+collectivités | Benchmark pricing pour shadow billing |
| Enchères calendaires Y+4/Y+5 | Baseload, maturités longues, fournisseurs alternatifs | Référence approvisionnement alternatifs |
| Prélèvement État | 50% > 78 €/MWh, 90% > 110 €/MWh | Plafond prix de marché indirect |
| Prix cible | ~70 €₂₀₂₂/MWh en moyenne 15 ans | Ancrage shadow billing long terme |

### Concurrence et parts de marché 2024

| Segment | Historiques | Alternatifs | Observations |
|---|---|---|---|
| Grands sites non résidentiels | 48% | **52%** | Équilibre atteint |
| Sites moyens non résidentiels | 48% | **52%** | Idem |
| Petits sites non résidentiels | 57% (dont 29% TRVE) | **43%** | Marge progression alternatifs |
| Résidentiels | 72% (dont 62% TRVE) | **28%** | Fort potentiel |
| **Global volume** | **57%** | **43%** | Tendance → 50/50 en 2030 |

> 55 offres sur 67 moins chères que le TRVE (déc 2024). Discounts de -25% à -30%. Le TRVE sert de plafond de référence.

### CPPA — Tendance structurante

- 4,9 TWh cumulés depuis 2019, 26 CPPA signés jan-sept 2024
- 84% greenfield, prix attractifs (< marché spot)
- PROMEOS doit modéliser les CPPA dans la cascade de prix (entre contrat cadre et spot)

### CEE — Poids dans la facture

- Électricité = **27%** de l'obligation totale CEE (5e période)
- Coefficient : 0,478 kWh cumac/kWh vendu
- Poids dans tarif bleu : **2,9%**
- Pénalité max : 0,015 €/kWh cumac

### Consommation France — Trajectoire

- 2023 : **439 TWh** (point bas historique)
- 2024 estimé : ~445-450 TWh (léger rebond)
- 2030 cible : ~500 TWh
- 2035 cible RTE : **590-640 TWh** (scénario "fit for 55")
- Vecteurs : data centers, VE, industrie (H2 décarboné)
- 40M sites : 34,7M résidentiels, 4,8M petits pro, 447K moyens, 99K grands

## Architecture Shadow Billing

Pipeline: Données Enedis (CDC 30min/10min ou index) → Classification période tarifaire (HP/HC/HPH/HCH/HPB/HCB/Pointe) → Multiplication par prix contractuel (resolve_pricing(annexe)) → + Acheminement TURPE → + Taxes → = Facture recalculée → Δ vs facture réelle → Anomalies

## Composantes facture électricité B2B

| Composante | Calcul | Unité | Poids typique |
|---|---|---|---|
| Fourniture (énergie) | prix × volume par période tarifaire | €/MWh | ~35-45% |
| Abonnement fourniture | fixe mensuel | €/mois | ~2-5% |
| Acheminement (TURPE) | soutirage + gestion + comptage | €/kWh + €/kW/an | ~25-30% |
| Accise sur l'électricité | **T1=30.85 / T2=26.58 €/MWh** (depuis 01/02/2026) | €/MWh | ~10-12% |
| CTA | **15%** de la part fixe TURPE (depuis 01/02/2026) | € | ~2-3% |
| TVA | 5.5% sur abonnement+CTA, 20% sur conso+taxes | % | ~15-20% (TTC) |
| CEE | variable ~0.3-0.5 €/MWh | €/MWh | ~1-2% |
| Capacité | coût certificats × profil pointe | €/MWh | ~2-4% |

## Composantes facture gaz B2B

| Composante | Calcul | Unité | Poids typique |
|---|---|---|---|
| Fourniture (molécule) | prix × volume | €/MWh PCS | ~40-55% |
| Acheminement (ATRD+ATRT) | transport + distribution | €/MWh + €/an | ~20-25% |
| Accise gaz (ex-TICGN) | **16.39 €/MWh** (10.73 accise + 5.66 ZNI, depuis 01/02/2026) | €/MWh | ~8-12% |
| CTA gaz | % part fixe acheminement | € | ~2-3% |
| TVA | 5.5% abo+CTA, 20% conso+taxes | % | ~15-20% (TTC) |
| Stockage | contribution stockage souterrain | €/MWh | ~1-2% |

## Historique accise électricité

| Période | Taux | Contexte |
|---|---|---|
| Avant 2022 | 22.50 €/MWh | CSPE pré-bouclier |
| 01/02/2022 - 31/01/2024 | 1.00 €/MWh | Bouclier tarifaire |
| 01/02/2024 - 31/01/2025 | 21.00 €/MWh | Sortie progressive bouclier |
| 01/02/2025 - 31/07/2025 | 22.50 €/MWh | Retour pré-crise |
| 01/08/2025 - 31/01/2026 | 25.79 €/MWh | LFI 2025 + alignement TURPE 7 |
| **Depuis 01/02/2026** | **T1=30.85 / T2=26.58 €/MWh** | Taux par catégorie (ménages/PME) |

⚠️ Le versioning temporel est critique : appliquer le bon taux à la bonne période de consommation.

## TURPE 7 — Grille complète (depuis 01/08/2025, CRE n°2025-77/78)

### Composante soutirage (c€/kWh)

| Option | Pointe | HPH | HCH | HPB | HCB |
|---|---|---|---|---|---|
| BTINF ≤36kVA Base | — | 5.69 | 3.53 | 4.44 | 2.85 |
| BTINF HP/HC | — | 6.12 | 3.21 | 4.77 | 2.50 |
| BTSUP >36kVA | 7.40 | 5.69 | 3.53 | 4.44 | 2.85 |
| HTA courte | 5.51 | 4.24 | 2.63 | 3.31 | 2.12 |
| HTA longue | 4.03 | 3.10 | 1.92 | 2.42 | 1.55 |

### Composante gestion (€/an par point)

| Segment | Tarif |
|---|---|
| BTINF ≤36kVA | ~18-25 €/an |
| BTSUP >36kVA | ~150-300 €/an |
| HTA | ~500-1500 €/an |

### Composante comptage (€/an)

BTINF: inclus. BTSUP: ~200-600 €/an. HTA: ~800-2500 €/an (selon puissance).

### Dépassement puissance (CMDPS)

CMDPS = **12.65 × h** (€/kW dépassé × nombre d'heures de dépassement dans le mois).
Calculé sur chaque période de 10min (C1-C4) ou intégré mensuel (C5).

### Périodes tarifaires TURPE 7 (5 classes)

| Période | Ratio prix | Mois | Heures |
|---|---|---|---|
| Pointe | 1.30 | Nov-Mars | PP1/PP2 (10-15j mobiles RTE) |
| HPH | 1.00 (réf) | Nov-Mars | 7h-23h lun-sam hors pointe |
| HCH | 0.62 | Nov-Mars | 23h-7h + dim + jours fériés |
| HPB | 0.78 | Avr-Oct | 7h-23h lun-sam |
| HCB | 0.50 | Avr-Oct | 23h-7h + dim + jours fériés |

HC méridiennes 11h-14h pour nouveaux contrats (CRE 2026-33).

## Cascade de prix (resolve_pricing)

1. AnnexeSite.price_overrides → source: 'override'
2. ContratCadre.base_tariff_grid → source: 'cadre'
3. Spot 30 jours (si indexé) → source: 'spot'
4. SiteTariffProfile → source: 'profile'
5. Fallback: **0.068 €/kWh** (⚠️ PAS 0.18) → source: 'fallback'

## Prorata et régularisation

### Prorata temporel

Facture = volume_période × (nb_jours_facturés / nb_jours_période_standard).
Abonnement : prorata jour calendaire exact. Première/dernière facture toujours proratisées.

### Régularisation

- **Estimation → Réel** : quand relevé réel remplace estimation, facture de régul = (réel - estimé) × prix.
- **Changement tarif en cours de mois** : split au jour du changement, chaque portion au tarif applicable.
- **Régul annuelle TURPE** : ajustement composante puissance souscrite vs atteinte.
- Seuil d'alerte PROMEOS : régul > 50% du montant mensuel → investigation.

## Checklist Shadow Billing Mensuel

Phase 1 (M+7) — Structurel: PDL/PCE = registre? Puissance souscrite = Enedis? Option tarifaire (Base/HP-HC/BTINF/BTSUP/HTA) OK? Période 28-31j? Dates cohérentes?
Phase 2 (M+10) — Conso: Index fin - index début = conso? ±3% vs même mois N-1? Index estimé vs réel? Doublons période? Consommation négative?
Phase 3 (M+12) — Financier: Énergie = prix×volume par période? TURPE = grille en vigueur à la date? Accise = taux de la période (historique ci-dessus)? CEE? Capacité? CTA = **15%** × part fixe (depuis 02/2026)? TVA 5.5/20% correctement appliquée?
Phase 4 (M+14) — Alertes: Écart >2€/MWh → erreur probable. Conso >baseline+10% → investigation dérive. Régul >50% → vérification estimation. Montant TTC >N-1+15% → alerte budget.

## Anomalies types

| Code | Description | Sévérité | Seuil |
|---|---|---|---|
| BILL_001 | Écart fourniture vs shadow | HIGH | >5% |
| BILL_002 | Puissance facturée ≠ Enedis | HIGH | Tout écart |
| BILL_003 | Période tarifaire incorrecte | MEDIUM | Mauvaise classe HP/HC |
| BILL_004 | Accise ≠ taux en vigueur | HIGH | Tout écart |
| BILL_005 | Facturation sur estimé (relevé dispo) | LOW | Estimation alors que réel existe |
| BILL_006 | Doublon facturation (même période) | CRITICAL | Deux factures même PDL+période |
| BILL_007 | TVA taux incorrect | MEDIUM | ≠5.5% ou ≠20% selon ligne |
| BILL_008 | TURPE version obsolète | HIGH | Grille TURPE 6 après 01/08/2025 |
| BILL_009 | CTA calcul incorrect | MEDIUM | ≠15% × part fixe (depuis 02/2026) |
| BILL_010 | Régularisation anormale | MEDIUM | >50% du montant mensuel |
| BILL_011 | Capacité absente ou aberrante | MEDIUM | Manquante ou >5€/MWh |
| BILL_012 | Période facture chevauchante | HIGH | Overlap avec facture précédente |

## Structure type facture fournisseur (EDF/Engie)

```
FACTURE D'ÉLECTRICITÉ
├── En-tête: n° facture, PDL, dates, puissance souscrite
├── Fourniture
│   ├── Abonnement (fixe)
│   └── Consommation (par période: HPH, HCH, HPB, HCB, Pointe)
├── Acheminement (TURPE)
│   ├── Composante gestion
│   ├── Composante comptage
│   ├── Composante soutirage (par période)
│   └── Dépassement puissance (CMDPS si applicable)
├── Taxes et contributions
│   ├── Accise sur l'électricité (T1=30.85 / T2=26.58 €/MWh depuis 02/2026)
│   ├── CTA (15% × part fixe depuis 02/2026)
│   └── CEE (si visible)
├── Sous-total HT
├── TVA
│   ├── 5.5% sur (abonnement + CTA)
│   └── 20% sur (consommation + taxes)
└── Total TTC
```

## Reclaim (récupération trop-perçus)

Processus : détection anomalie → quantification écart → lettre de réclamation → négociation → avoir/remboursement.
Prescription : 14 mois (consommateur) / 5 ans (professionnel, Code civil).
Montants typiques B2B : 1-5% de la facture annuelle en erreurs récupérables.
Types fréquents : mauvaise puissance, TURPE obsolète, accise incorrecte, double facturation.

## Fichiers backend

- `backend/config/tarifs_reglementaires.yaml` — 300 lignes, tarifs versionnés (TURPE 6/7, accise, CTA)
- `backend/config/default_prices.py` — Fallback 0.068 €/kWh
- `backend/services/tariff_period_classifier.py` — 5 classes TURPE 7
- `backend/services/cost_by_period_service.py` — Ventilation kWh×€
- `backend/models/tou_schedule.py` — Fenêtres HP/HC
- `docs/bill_intelligence/` — Templates factures EDF/Engie

## Règles non-négociables

- Toujours HT dans les calculs, TTC uniquement en affichage final
- 0.068 €/kWh = fallback, jamais 0.18
- 0.0569 €/kWh = tarif TURPE 7 HPH, JAMAIS un facteur CO₂
- Accise = taux en vigueur à la date de consommation (pas de la facture)
- Accise gaz = 16.39 €/MWh total (10.73 accise + 5.66 ZNI) depuis 02/2026
- Versioning temporel : bon tarif à la bonne date
- Prorata au jour calendaire pour factures partielles
- CTA = **15%** de la part fixe TURPE depuis 02/2026 (ancien: 27.04% avant 08/2021, 21.93% avant 02/2026)

## Disclaimer

Les informations réglementaires de ce skill sont fournies à titre informatif et ne constituent pas un conseil juridique. Les valeurs tarifaires et seuils réglementaires sont basés sur les textes officiels en vigueur à la date de création du skill (avril 2026). Vérifier les sources officielles (CRE, Legifrance, ADEME/OPERAT) pour les valeurs à jour. PROMEOS n'est pas un cabinet de conseil réglementaire.
