---
name: regulatory_calendar
description: Calendrier réglementaire énergie B2B France 2026-2050 — OPERAT, BACS 2030, Audit SMÉ, Capacité Nov 2026, CBAM, ETS2, CSRD, e-facture 2026. Deadlines canoniques.
triggers: [deadline, calendrier, échéance, OPERAT, BACS, Audit SMÉ, ISO 50001, CBAM, ETS2, CSRD, capacité, e-facture, 2026, 2030, 2040]
source_of_truth: backend/config/tarifs_reglementaires.yaml + memory/reference_regulatory_landscape_2026_2050.md
last_verified: 2026-04-24
---

# Calendrier réglementaire — Deadlines énergie B2B France

## Quand charger cette skill

- ✅ Planification conformité (quel site doit quoi pour quand ?)
- ✅ Compte à rebours réglementaire (ex: Capacité 1/11/2026 — combien de mois restants ?)
- ✅ Priorisation backlog sprint (deadline < 6 mois = P0)
- ✅ Génération alertes / notifications utilisateur
- ❌ Ne PAS charger pour : valeurs numériques tarifs → `tariff_constants` · facteurs CO₂ → `emission_factors`

## Deadlines 2026 (P1 imminentes)

| Date | Obligation | Cadre | Texte |
|---|---|---|---|
| **30/09/2026** | Dépôt données OPERAT N-1 | DT | Décret 2019-771 |
| **01/07/2026** | APER parkings 1500 m² (privés) / toitures 500 m² | APER | Loi 2023-175 |
| **01/09/2026** | E-facturation obligatoire (ETI + GE) | — | Ordonnance 2021-1190 |
| **11/10/2026** | **Audit énergétique** obligatoire (> 2,75 GWh) | Audit SMÉ | Loi 2025-391 |
| **01/11/2026** | **Mécanisme de capacité RTE** entrée en vigueur | Capacité | Délibération CRE |
| **01/01/2027** | BACS — phase transitoire (vérifier grandfathering sites existants) | BACS | Décret 2025-1343 |

## Deadlines 2027-2030

| Date | Obligation | Cadre |
|---|---|---|
| **11/10/2027** | SMÉ ISO 50001 certifié (> 23,6 GWh) | Audit SMÉ |
| **2027** | DPE tertiaire transposition EPBD recast | DPE |
| **2028** | ETS2 (carburants routiers + bâtiments) | ETS2 |
| **01/01/2028** | APER toitures progressif | APER |
| **01/01/2030** | **BACS seuil 70 kW** entrée en vigueur | BACS |
| **2030** | **Jalon DT -40%** vs référence | DT |
| **2030** | CEE P6 fin période + bilan | CEE |

## Deadlines 2030+ (stratégiques)

| Date | Obligation | Cadre |
|---|---|---|
| 2034 | CBAM importations — fin période transition, pleine effectivité | CBAM |
| 2040 | Jalon DT -50% vs référence | DT |
| 2050 | Jalon DT -60% vs référence + neutralité carbone France | DT |

## Priorités stratégiques Q2-Q3 2026 (memory `project_strategic_priorities_2026_avril.md`)

| Prio | Deadline | Initiative PROMEOS |
|---|---|---|
| **P1** | **01/11/2026** | Capacité Nov 2026 (fenêtre 6 mois — pass-through facture + coordination agents) |
| **P2** | Q2 2026 | Wedge Sirene (diagnostic freemium <3 min SIREN) |
| **P3** | Q3 2026 | CBAM (brique 6 scopes, first-mover B2B France) |
| **P4** | Q3-Q4 2026 | SENTINEL-REG (agent veille 17 mécanismes auto) |

## CSRD (post-Omnibus février 2025)

- **Seuil** : > 250 salariés OU CA > 50 M€ (au lieu des anciens 500/50).
- **Simplification Omnibus** : -80% scope data reporting, délais étendus pour certaines PME.
- **Première publication** : 2025 (GE) → 2026 (ETI) → vague 2027+ pour PME.
- **Volet énergie** : E1 (changement climatique), reporting scopes 1/2/3, cibles réduction GES.

## Exemples d'usage dans les prompts agents

**`regulatory-expert`** : "Audit conformité site X, quelles deadlines ?"
→ charge skill, retourne toutes les dates applicables filtrées par seuils site (surface, conso, puissance).

**`architect-helios`** : priorisation feature — ajouter Capacité Nov 2026 en P0 si fenêtre < 6 mois restants.

**`bill-intelligence`** : facture novembre 2026 doit inclure pass-through capacité.

## Anti-patterns (FAIL systématique)

- ❌ **"Jalon DT 2026"** → n'existe PAS. 1er jalon officiel = 2030.
- ❌ **"BACS 2027"** → FAUX. Seuil 70 kW = **01/01/2030** (report décret 27/12/2025).
- ❌ **"ETS2 2026"** → FAUX. Entrée en vigueur 2028.
- ❌ **"CSRD seuil 500 salariés"** → post-Omnibus c'est 250 salariés.
- ❌ **"E-facture 01/01/2026"** → reporté à **01/09/2026** (ETI/GE).
- ❌ Citer deadline sans source (Légifrance / CRE / ADEME / Journal Officiel) → viole doctrine zéro chiffre sans source.

## Références

- Tarifs YAML : [backend/config/tarifs_reglementaires.yaml](../../../backend/config/tarifs_reglementaires.yaml)
- Landscape 2026-2050 : memory/reference_regulatory_landscape_2026_2050.md
- Veille 2025-2026 : memory/reference_veille_reglementaire_2025_2026.md
- Priorités stratégiques : memory/project_strategic_priorities_2026_avril.md
- Dernière vérification : 2026-04-24
