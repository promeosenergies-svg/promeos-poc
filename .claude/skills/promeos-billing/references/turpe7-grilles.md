# Grilles tarifaires TURPE 7 — Référence détaillée

Source: CRE délibérations n°2025-77 (transport HTB) et n°2025-78 (distribution HTA/BT), 13/03/2025.
Date d'effet: 01/08/2025 pour 4 ans.

## Composantes soutirage BT > 36 kVA

| Composante | HPH (€/kWh) | HCH (€/kWh) | HPB (€/kWh) | HCB (€/kWh) | Pointe (€/kWh) |
|---|---|---|---|---|---|
| Soutirage variable | 0.0569 | 0.0353 | 0.0444 | 0.0285 | 0.0740 |

## Composantes soutirage HTA

| Composante | HPH | HCH | HPB | HCB | Pointe |
|---|---|---|---|---|---|
| Soutirage variable | 0.0442 | 0.0286 | 0.0351 | 0.0228 | 0.0567 |

## Composante gestion

| Puissance souscrite | Annuel (€/an) |
|---|---|
| ≤ 36 kVA | ~15-25 €/an |
| > 36 kVA | ~40-80 €/an |
| HTA | ~150-400 €/an |

## Composante comptage

| Type compteur | Annuel (€/an) |
|---|---|
| Linky (C5) | ~20 €/an |
| C4 (BT > 36 kVA) | ~350 €/an |
| C3/C2 (HTA) | ~800-1500 €/an |

## Transition TURPE 6 → 7

- Ajustement CRCP +7.7% au 01/02/2025 (TURPE 6)
- TURPE 7 au 01/08/2025
- Flux F15 Enedis: relevé résiduel avec ASCS/ASCA spécifiques
- Si compteur Linky posé avant 01/08 → pas de facturation relevé résiduel
- Si compteur historique avec pose Linky après 01/08 → composantes socle et additionnelle neutralisées

## Versioning dans PROMEOS

Fichier: `backend/config/tarifs_reglementaires.yaml`
Chaque tarif a: `effective_from`, `effective_to`, `version` (TURPE_6 ou TURPE_7).
Le shadow billing sélectionne automatiquement la bonne grille selon la date de facture.
