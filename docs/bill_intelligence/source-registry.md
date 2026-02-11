# Source Registry — Bill Intelligence

Ce document reference les sources normatives utilisees par le moteur de calcul et d'audit.
Chaque entree pointe vers un `doc_id` dans la KB.

## Electricite — Tarifs reseau

| Source | Organisme | doc_id KB | Statut |
|--------|-----------|-----------|--------|
| TURPE 6 HTA-BT | CRE | `cre_turpe6_hta_bt_2025_02` | ACTIVE |
| TURPE 6 HTB | CRE | `cre_turpe6_htb_2025_02` | ACTIVE |
| TURPE 7 HTA-BT decision | CRE | `cre_turpe7_hta_bt_decision_2025` | ACTIVE |
| TURPE 7 HTB decision | CRE | `cre_turpe7_htb_decision_2025` | ACTIVE |

## Gaz — Tarifs reseau

| Source | Organisme | doc_id KB | Statut |
|--------|-----------|-----------|--------|
| ATRD7 GRDF | CRE | `cre_atrd7_grdf_news_2024` | ACTIVE |
| ATRT8 | CRE | `cre_atrt8_evolution_2026_04_decision` | ACTIVE |
| ATS3 | CRE | `cre_ats3_evolution_2026` | ACTIVE |

## Taxes

| Source | Organisme | doc_id KB | Statut |
|--------|-----------|-----------|--------|
| CTA | CRE | `cre_cta_project_2026` | ACTIVE |
| Accise electricite (TICFE/CIBS) | Legifrance | TODO | PARAM_MISSING |
| Accise gaz (TICGN/CIBS) | Legifrance | TODO | PARAM_MISSING |
| TVA energie | BOFiP | TODO | PARAM_MISSING |

## Structure facture

| Source | Organisme | doc_id KB | Statut |
|--------|-----------|-----------|--------|
| Modele facture EDF Pro | EDF | TODO | PARAM_MISSING |
| Modele facture Engie Pro | Engie | TODO | PARAM_MISSING |
| Modele facture TotalEnergies | TotalEnergies | TODO | PARAM_MISSING |

## Regles de facturation

| Source | Organisme | doc_id KB | Statut |
|--------|-----------|-----------|--------|
| Code de l'energie (prorata) | Legifrance | TODO | PARAM_MISSING |
| Conditions generales fournisseur | Fournisseur | TODO | PARAM_MISSING |

> **Note** : Les entrees `TODO / PARAM_MISSING` seront completees au fur et a mesure
> de l'ajout de documents dans la KB. Le moteur de calcul refuse de produire un
> resultat si une source requise est absente.
