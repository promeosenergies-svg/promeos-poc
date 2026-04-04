---
name: energy-france-veille
description: "Veille réglementaire énergie France 2025-2026 : TURPE 7, accise, VNU, HC méridiennes, NEBCO, BACS abaissement seuils, APER, audit énergétique, ETS2, CBAM, EED, CSRD, CEE P6, loi de finances 2026. Utiliser ce skill pour changements récents, veille marché, évolutions tarifaires, nouvelles obligations, calendrier réglementaire, directives européennes énergie."
---

# Veille Réglementaire Énergie France 2025-2026

## Proactive triggers

- Date > 01/07/2026 et prix dynamique transitoire → "Le régime transitoire des prix dynamiques a expiré. Vérifier le nouveau cadre CRE."
- Date > 01/01/2027 et BACS seuil encore à 290kW → "Le seuil BACS est passé à 70kW depuis le 01/01/2027. Mettre à jour le scoring."

## Entrées en vigueur récentes

| Date | Mesure | Référence | Impact PROMEOS |
|---|---|---|---|
| 01/01/2025 | BACS seuil 290kW CVC | Décret 2025-1343 | compliance_score: seuil BACS |
| 01/01/2026 | Fin ARENH → VNU (CAPN+CPN) | Loi 2023-175 art.L336-1 ss | flag R12 contrats indexés ARENH |
| 01/01/2026 | Coeff énergie primaire élec = 1.9 | Arrêté 10/12/2025 | DT trajectoire recalcul |
| 01/02/2025 | TURPE 6 révisé +7.7% | CRE 2025-012 | billing historique |
| 01/08/2025 | TURPE 7 (nouvelle grille) | CRE 2025-77/78 | billing+classifier |
| 01/08/2025 | Accise électricité = 25.79 €/MWh | LFI 2025 art.29 | constante billing |
| 01/09/2025 | NEBEF → NEBCO seuil 100kW | RM-5-NEBCO-V01 | nomenclature flex |
| 04/02/2026 | HC méridiennes 11h-14h (nouveaux contrats) | CRE 2026-33 | TOUSchedule, classifier |
| 01/01/2026 | Accise gaz (TICGN) = 15.43 €/MWh | LFI 2026 | constante billing gaz |

## Calendrier à venir

| Date | Mesure | Détail |
|---|---|---|
| 01/07/2026 | Fin régime transitoire offres dynamiques | Fournisseurs doivent proposer tarification dynamique (art.L332-7) |
| 30/09/2026 | Deadline modulation Décret Tertiaire | Demandes via OPERAT, instruction ADEME |
| 11/10/2026 | Deadline audit énergétique / SMÉ | Orgs >2.75 GWh (audit) ou >23.6 GWh (ISO 50001) |
| 01/01/2027 | BACS seuil abaissé 70kW CVC | Classe C minimum NF EN ISO 52120-1 |
| 01/01/2027 | CEE Période 6 (P6) | Objectif 1050 TWhc/an, nouveaux programmes |
| 2027-2028 | APER bâtiments existants | Ombrières parkings + toitures progressif |
| 01/01/2028 | ETS2 (bâtiments + transport) | Quotas CO₂, impact gaz bâtiments tertiaires |
| 2028 | CBAM phase définitive | Certificats CO₂ frontière, produits énergétiques |
| 2030 | Décret Tertiaire jalon -40% | Premier objectif contraignant |
| 2031 | Premier bilan DT ADEME | Publication rapport conformité national |

## Directives européennes impactantes

| Directive | Transposition | Impact B2B |
|---|---|---|
| EED recast (2023/1791) | En cours | Audits énergie renforcés, SMÉ obligatoire >10 TJ, plans réduction |
| EPBD recast (2024/1275) | 2026-2027 | DPE tertiaire obligatoire, ZEB 2030 (neuf), passeport rénovation |
| RED III (2023/2413) | 2025 | Objectif ENR 42.5% 2030, GO renforcées, PPA facilités |
| ETS2 | 2027-2028 | Quotas CO₂ bâtiments/transport, prix estimé 40-80 €/tCO₂ |
| CBAM (2023/956) | Phase transitoire | Reporting CO₂ importations, certificats à l'achat |
| CSRD (2022/2464) | 2025-2026 | Reporting durabilité (E1-E5), données énergie/CO₂ auditées |

## Loi de Finances 2026 — points énergie

- Accise électricité maintenue 25.79 €/MWh (pas de hausse prévue)
- TICGN maintenue 15.43 €/MWh
- CTA: taux inchangé 27.04%
- TVA énergie: pas de modification (5.5% abo, 20% conso)
- CEE: transition P5→P6 préparée, budget bonifié rénovation tertiaire

## PPE3 (2026-2035) — impacts clés

- Objectif conso finale 1243 TWh 2030
- Mix élec: 48 GW PV, 31 GW éolien terrestre, 15 GW offshore, 380 TWh nucléaire
- 6 EPR2 confirmés (Penly, Gravelines, Bugey, Tricastin)
- Flexibilités: 6.5 GW effacement/stockage
- Sortie fossiles tertiaire: 2040 gaz, fioul en priorité

## Sources à surveiller

| Source | URL/accès | Fréquence |
|---|---|---|
| CRE délibérations | cre.fr/consultations | Hebdo |
| DGEC/MTE arrêtés | legifrance.gouv.fr | Mensuel |
| RTE bilan prévisionnel | bilan-electrique.rte-france.com | Annuel |
| ADEME OPERAT | operat.ademe.fr | Continu |
| ATEE (CEE) | atee.fr/cee | Trimestriel |
| EPEX Spot prix | epexspot.com | Quotidien |
| EEX forward | eex.com/en/market-data | Quotidien |
| Enedis open data | data.enedis.fr | Mensuel |

## Impacts PROMEOS — matrice de priorité

**P0 (fait)**: TURPE 7 classifier, accise 25.79, NEBCO nomenclature, audit rule org-level.
**P1 (à faire)**: HC méridiennes TOUSchedule, VNU flag R12, BACS 70kW seuil paramétrable, données 10min connector.
**P2 (roadmap)**: ETS2 module CO₂ bâtiment, CSRD reporting énergie, EPBD DPE tertiaire, CEE P6 valorisation.
