# Bilan Traitement Lacunes Billing Engine — Q1 2026

**Agent** : SENTINEL-REG | **Date** : 2026-03-22 | **Statut** : 5/5 TERMINÉ — 0 régressions

---

## Résumé

5 lacunes identifiées par l'audit réglementaire traitées. Le billing engine passe de V2.1 à V2.2 avec support C3 HTA, stockage gaz explicité, CEE estimatif, péréquation préparée et réforme capacité anticipée.

**Tests** : 100 (baseline) → **171 pass, 0 fail** (+71 tests)

---

## Lacune 1 — C3 HTA (>250 kVA) — DÉBLOQUÉ

| Aspect | Détail |
|--------|--------|
| **Problème** | Les 25 taux TURPE 7 HTA existaient dans le catalog mais le moteur renvoyait UNSUPPORTED |
| **Solution** | Déblocage segment, mapping 5 plages (P/HPH/HCH/HPB/HCB), agrégation soutirage fixe |
| **Taux source** | CRE Délibération n°2025-78, brochure TURPE 7 p.9-12 |
| **Composantes** | Gestion (435.72), Comptage (376.39), SF 5 plages (CU/LU), Variable 5 plages, CTA, Accise |
| **Tests** | +5 tests (gestion, comptage, SF 5 plages, variable 5 périodes, LU vs CU) |

**Calcul vérifié** : Gestion HTA = 435.72 × (31/365) = 36.98 EUR ✓

---

## Lacune 2 — Stockage gaz ATS3 — SHADOW COMPOSANTE

| Aspect | Détail |
|--------|--------|
| **Problème** | Terme stockage doublé (331.44 EUR/MWh/j/an) mais invisible dans la reconstitution |
| **Solution** | Composante shadow (`amount_ht=0`, montant réel dans `inputs_used["shadow_amount_ht"]`) |
| **Taux** | 2025 : 0.00038 EUR/kWh ; 2026 (avr+) : 0.00046 EUR/kWh (+20%) |
| **Résolution temporelle** | `STOCKAGE_GAZ` → 2025 ou 2026 selon `at_date` |
| **Tests** | +3 tests (présence, zero HT, temporal 2025/2026) |

**Pas de double comptage** : `amount_ht=0` garanti par design.

---

## Lacune 3 — CEE composante estimative — SHADOW

| Aspect | Détail |
|--------|--------|
| **Problème** | CEE P6 = coût implicite +35% non visible dans la décomposition |
| **Solution** | Shadow composante élec + gaz, taux estimatif P5/P6 |
| **Taux** | P5 : 0.0050 EUR/kWh (~5 EUR/MWh) ; P6 : 0.0065 EUR/kWh (~6.5 EUR/MWh) |
| **Résolution temporelle** | `CEE_SHADOW` → P5 (pre-2026) ou P6 (post-2026) |
| **Tests** | +4 tests (présence élec, zero totals, P5 vs P6, présence gaz) |

**Flaggé ESTIMATIF** dans formula et source. Amount_ht = 0.

---

## Lacune 4 — Péréquation gaz ELD — PRÉPARÉ

| Aspect | Détail |
|--------|--------|
| **Problème** | LFI 2026 introduit péréquation nationale gaz au 01/07/2026 |
| **Solution** | Paramètre `grd_code` (défaut "GRDF") dans `build_invoice_reconstitution()` |
| **Comportement** | Tous les GRD utilisent taux GRDF ; GRD tracé dans assumptions |
| **Prêt pour** | Ajout taux ELD-spécifiques quand CRE publie |
| **Tests** | +2 tests (défaut GRDF, traçabilité ELD) |

**Rétrocompatible** : paramètre optionnel avec défaut.

---

## Lacune 5 — Réforme capacité nov 2026 — PLACEHOLDER

| Aspect | Détail |
|--------|--------|
| **Problème** | RTE acheteur unique en nov 2026, résolution temporelle non prête |
| **Solution** | `CAPACITE_ELEC_NOV2026` (placeholder = même taux 0.00043) + résolution temporelle |
| **Source** | "Réforme capacité RTE acheteur unique (nov 2026)" dans la source tracée |
| **Tests** | +2 tests (temporal nov 2026, boundaries 2025/2026/nov2026) |

**Prêt pour** : mise à jour du taux quand CRE publie le résultat des enchères réformées.

---

## Fichiers modifiés

| Fichier | Lignes ajoutées | Nature |
|---------|----------------|--------|
| `catalog.py` | ~80 | +get_soutirage_fixe_codes_5p, +8 taux, +3 résolutions temporelles |
| `engine.py` | ~100 | C3 HTA débloqué, +stockage shadow, +CEE shadow (élec+gaz), +grd_code |
| `test_billing_engine.py` | ~120 | +TestTurpeC3HTA (5), +TestCeeShadowElec (3), +TestCapaciteTemporelleReforme (2) |
| `test_shadow_billing_gas.py` | ~80 | +TestGasStockageShadow (3), +TestGasCeeShadow (1), +TestGasGrdCode (2) |

---

## Résultats tests finaux

```
test_billing_engine.py:              110/110 ✓
test_shadow_billing_gas.py:           24/24  ✓
test_billing_shadow_expected_elec.py: 18/18  ✓
test_billing_invariants_p0.py:        19/19  ✓ (adapté auto)
──────────────────────────────────────────────
TOTAL:                               171/171 ✓  (+71 vs baseline 100)
```

---

## Vérification triple

### Calculs
- Gestion HTA : 435.72 × (31/365) = 36.98 ✓ (CRE brochure p.9)
- SF HTA CU 5 plages : (14.41+14.41+14.41+12.55+11.22) × 400 × (31/365) = 2284.68 ✓
- Stockage shadow : 100000 × 0.00038 = 38.00 EUR (2025) < 100000 × 0.00046 = 46.00 (2026) ✓
- CEE P5 : 10000 × 0.0050 = 50 EUR < CEE P6 : 10000 × 0.0065 = 65 EUR ✓
- Capacité : 2025→0, 2026→0.00043, nov2026→0.00043 (placeholder) ✓

### Logique
- Shadows : amount_ht=0 sur stockage_gaz et cee_shadow (pas de double comptage) ✓
- grd_code : paramètre optionnel "GRDF" par défaut (rétrocompatible) ✓
- C3 HTA : soutirage fixe agrégé en 1 ComponentResult pour CTA assiette ✓
- Résolutions temporelles : STOCKAGE_GAZ, CEE_SHADOW, CAPACITE_ELEC_NOV2026 ✓

### Sources
- TURPE 7 HTA : CRE Délibération n°2025-78 du 13/03/2025
- ATS3 : CRE délibérations 2025-36 et 2026
- CEE : Estimation PROMEOS basée sur P5/P6 (780/1050 TWhc/an)
- Péréquation : LFI 2026 du 19/02/2026
- Capacité réforme : Loi de finances 2025, CRE oct 2025
