# ADR-D-05 — Accise CIBS Enum strict DP élec + gaz

**Statut** : ✅ ACCEPTED — implémenté Phase D-4 Tier 1 (commit `2268e90d`) + dedup Tier 4 (`6bbadcfb`)
**Date** : 2026-05-08
**Sprint** : Phase D-4 Tier 1 candidat
**Décideurs** : à figer post-revue (architect-helios + bill-intelligence + regulatory-expert)

## Contexte

Audit écarts matrice v1 (`AUDIT_ECARTS_MATRICE_V1_2026_05_07.md`) révèle 2 P0 cardinaux **billing** :

- P0-MATV1-002 : `DeliveryPoint.accise_categorie_gaz` Enum [NATUREL/GPL/GNL] — manquant
- P0-MATV1-003 : `DeliveryPoint.accise_categorie` (élec) Enum [MENAGES_ASSIMILES/PME/HAUTE_PUISSANCE] — manquant

Différentiel ~5-15% sur facture selon catégorie correctement déterminée.

## Sources réglementaires

- CIBS L.312-24 (gaz naturel/GPL/GNL)
- CIBS L.312-36/37 (électricité)
- CIBS L.312-48 (tarif réduit motifs — 7 motifs réglementaires)
- Arrêté 27/01/2026 JORFTEXT000053407616 (accises 2026)

## Constantes existantes (`backend/doctrine/constants.py`)

- ACCISE_ELEC_T1_EUR_PER_MWH = 30.85 (MENAGES_ASSIMILES)
- ACCISE_ELEC_T2_EUR_PER_MWH = 26.58 (PME)
- ACCISE_ELEC_HP (5.71 EUR/MWh dans YAML) — **HAUTE_PUISSANCE**
- ACCISE_GAS_EUR_PER_MWH = 10.73

## Options

### Option A — Enum strict aux DP (matérialisation)

- **Pour** : cohérent doctrine Pilier 1 (SoT runtime), pattern Pilier 9 (Enum strict canonique)
- **Contre** : migration colonne + saisie utilisateur ou inferred

### Option B — Fonction service `get_accise_categorie(dp)` runtime

- **Pour** : pas de migration
- **Contre** : déduction heuristique (Σ conso annuelle ?) — non déterministe sans saisie

### Option C — Enum + service inferred par défaut + override saisie

- **Pour** : meilleur des deux mondes (auto-détermination + override expert)
- **Contre** : complexité

## Décision (à figer Phase D-4 Tier 1)

**Recommandation cardinal** : Option C (Enum strict + inferred + override).

Justification :
1. Pilier 9 ADR-016 cardinal (Enum strict canonique post-audit officiel CIBS)
2. UX onboarding : auto-détermination via puissance_souscrite + atrd_option (gaz)
3. Override expert pour cas atypiques (multi-usages, exemptions L.312-48)

## Conséquences

- 2 nouveaux Enums `models/enums.py` :
  - `AcciseCategorieElec` (MENAGES_ASSIMILES/PME/HAUTE_PUISSANCE)
  - `AcciseCategorieGaz` (NATUREL/GPL/GNL)
- 2 nouvelles colonnes `DeliveryPoint.accise_categorie` (selon energy_type)
- Service `bill_intelligence/accise_categorizer.py` : auto-détermination
- Validators @validates strict (pattern Pilier 9 ADR-016)
- Migration Alembic 18e

## Impact billing

- Recalcul rétroactif factures 2026 si catégorie incorrecte (~5-15% différentiel)
- Anti-régression Bill Intelligence : R-Accise-Categorie tests cardinaux

## Effort estimé

**2h** : Enums + validators + migration + tests + cohérence cross-FK avec puissance_souscrite/atrd_option.

## Liens

- [`AUDIT_ECARTS_MATRICE_V1_2026_05_07.md`](../audits/AUDIT_ECARTS_MATRICE_V1_2026_05_07.md) §3 P0-MATV1-002 + P0-MATV1-003
- Matrice v1 : §4.6.B#16 + §4.6.C#18
- CIBS L.312 sources réglementaires
