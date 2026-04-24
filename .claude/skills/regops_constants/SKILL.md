---
name: regops_constants
description: Constantes RegOps PROMEOS — seuils BACS/APER/Audit SMÉ, jalons DT -40/-50/-60%, scoring DT/BACS/APER/AUDIT, sanctions. Wrapper des règles backend/regops/rules/.
triggers: [BACS, APER, DT, Décret Tertiaire, scoring, conformité, OPERAT, Audit SMÉ, ISO 50001, DPE, seuil regops, modulation, jalon, valeur absolue]
source_of_truth: backend/regops/rules/
last_verified: 2026-04-24
---

# RegOps Constants — Seuils, scoring, sanctions

## Quand charger cette skill

- ✅ Calcul scoring conformité DT/BACS/APER/AUDIT/DPE/CSRD
- ✅ Vérification applicabilité d'un site (surface, puissance, énergie consommée)
- ✅ Calcul sanction / pénalité réglementaire
- ✅ Comparaison jalons DT (objectif %, valeur absolue VA, modulation)
- ❌ Ne PAS charger pour : tarifs € → `tariff_constants` · calendrier pur deadlines → `regulatory_calendar`

## Seuils d'applicabilité (SoT = `backend/regops/rules/*.py`)

| Cadre | Seuil applicabilité | Unité | Source | Deadline entrée |
|---|---|---|---|---|
| **Décret Tertiaire** | ≥ 1 000 m² (usage tertiaire) | surface | Décret 2019-771, art. R174-22 | 01/10/2022 (OPERAT) |
| **BACS classe C (entrée)** | > 290 kW CVC | puissance nominale | Décret 2020-887 (modifié 2025-1343) | 01/01/2025 |
| **BACS classe C (extension)** | ≥ 70 kW CVC | puissance nominale | Décret 2025-1343 (27/12/2025) | **01/01/2030** |
| **APER parkings** | ≥ 500 m² (1500 m² si privé) | surface | Loi 2023-175, art. 40-44 | 01/07/2026 (1500m²) → 2028 |
| **APER toitures** | ≥ 500 m² surface bâtie neuve | surface | Loi 2023-175 | 01/07/2026 |
| **Audit SMÉ (audit énergétique)** | > 2,75 GWh final annuel | conso | Loi 2025-391 (APER adaptée) | **11/10/2026** |
| **ISO 50001 (SMÉ obligatoire)** | > 23,6 GWh final annuel | conso | Loi 2025-391 | **11/10/2027** |
| **DPE tertiaire** | bâtiments tertiaires | — | EPBD recast (transposition 2026-2027) | À préciser |
| **CSRD (volet énergie)** | > 250 salariés OU CA > 50 M€ | RH / CA | Directive 2022/2464 (post-Omnibus 2025) | 2025-2026 |

## Jalons Décret Tertiaire (objectifs)

**Méthodologie relative** (valeur historique de référence ≥ 2010) :

| Année cible | Réduction conso finale |
|---|---|
| 2030 | **-40%** vs référence |
| 2040 | **-50%** vs référence |
| 2050 | **-60%** vs référence |

**Méthodologie Valeur Absolue (VA)** : seuils en kWh/m²/an par activité (cf. arrêté Valeurs Absolues III du 13/04/2022). Calcul via `backend/regops/rules/tertiaire_operat.py`.

**Modulation** : ajustements possibles (climat, contraintes patrimoniales, disproportion économique). Dossier OPERAT à justifier.

## Scoring conformité (4 piliers)

| Pilier | Poids par défaut | Indicateur primaire |
|---|---|---|
| DT | 40% | % atteinte jalon 2030 (si applicable) |
| BACS | 20% | Classe B attestée OU classe C planifiée |
| APER | 20% | Surface PV installée / surface obligatoire |
| AUDIT (SMÉ/50001) | 20% | Audit à jour OU SMÉ ISO 50001 certifié |

Calcul : `backend/services/compliance_score_service.py` et `backend/regops/scoring.py`.

## Sanctions / pénalités

| Cadre | Sanction | Base de calcul | Texte |
|---|---|---|---|
| DT — publish & shame | Publication OPERAT non-conformité | — | Décret 2019-771 |
| DT — pénalité forfaitaire | **7 500 €** / bâtiment | amende administrative | Code construction L173-5 |
| DT — A_RISQUE | **3 750 €** | avertissement pré-amende | Même base |
| APER (parking) | **40 000 €/an** + **200 €/place** | surface non-équipée | Loi 2023-175 |
| Audit énergétique | **1 500 €/an** | non-réalisation | Loi 2025-391 |
| ISO 50001 | **3 000 €/an** | non-certification | Loi 2025-391 |
| BEGES (sous-info) | **50 000 €** (depuis oct 2023) | non-publication | Loi climat & résilience |

## Exemples d'usage dans les prompts agents

**`regulatory-expert`** : "Site 1 200 m² tertiaire, CVC 85 kW, conso 900 MWh/an"
→ DT applicable (>1 000 m²) · BACS applicable à partir de 2030 (>70 kW) · pas d'audit SMÉ (<2 750 MWh) · APER à vérifier surface parking.

**`architect-helios`** ADR sur scoring : appeler `backend/regops/scoring.py` — jamais hardcoder les poids ici.

## Anti-patterns (FAIL systématique)

- ❌ **Jalon DT 2026** → n'existe PAS. Seuls 2030/2040/2050 sont des jalons officiels.
- ❌ **BACS seuil 2027** → FAUX. Seuil 70 kW entre en vigueur **01/01/2030** (report décret 27/12/2025).
- ❌ **DT pénalité 10 k€** → obsolète (ancien barème). 7 500 € pénalité, 3 750 € A_RISQUE.
- ❌ **Confondre -40%** (jalon DT 2030) avec **-40% CEE** (obligation CEE P6) → cadres différents.
- ❌ **VA en kWh/m²/mois** → unités = kWh/m²/an (pas mois).
- ❌ **CSRD seuil 500 salariés** → c'est 250 salariés OU 50 M€ CA (post-Omnibus).

## Références

- Code SoT : [backend/regops/rules/](../../../backend/regops/rules/)
- Scoring : [backend/regops/scoring.py](../../../backend/regops/scoring.py)
- Compliance service : [backend/services/compliance_score_service.py](../../../backend/services/compliance_score_service.py)
- Décret Tertiaire : Légifrance n°2019-771
- Décret BACS : Légifrance n°2020-887 (modifié n°2025-1343)
- Loi APER : Légifrance n°2023-175
- Loi Audit/SMÉ : Légifrance n°2025-391
- Dernière vérification : 2026-04-24
