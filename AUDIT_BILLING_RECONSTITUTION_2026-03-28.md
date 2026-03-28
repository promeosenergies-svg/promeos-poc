# Audit Billing — Reconstitution Déterministe & Modale "Comprendre l'écart"

**Date** : 28 mars 2026
**Scope** : billing_shadow_v2, billing_engine V2, tax_catalog.json, InsightDrawer
**Trigger** : Anomalies visuelles sur la modale "Comprendre l'écart" (Facturation)

---

## Résumé des corrections

| # | Bug | Sévérité | Fichier | Statut |
|---|-----|----------|---------|--------|
| 1 | `delta_pct` du composant réseau écrase le `delta_pct` total TTC | **P0** | `billing_service.py` | Corrigé |
| 2 | Abonnement fournisseur : prorata annuel (jours/365) au lieu de mensuel (jours/30) | **P0** | `engine.py` | Corrigé |
| 3 | tax_catalog.json : entrées TURPE 7 C4_BT et C3_HTA manquantes | **P0** | `tax_catalog.json` | Corrigé |
| 4 | tax_catalog.json : ACCISE_ELEC manquante après juillet 2025 | **P0** | `tax_catalog.json` | Corrigé |
| 5 | tax_catalog.json : CTA_ELEC manquante après décembre 2025 | **P1** | `tax_catalog.json` | Corrigé |
| 6 | Précision `unit_rate` accise à 4 décimales (perte de précision) | **P2** | `billing_shadow_v2.py` | Corrigé |
| 7 | TURPE_GESTION_C4_BT catalog incohérent avec YAML/fallback (41.76 vs 30.60) | **P0** | `tax_catalog.json` | Corrigé |
| 8 | Tests `test_turpe_uses_yaml` et `test_taxes_accise_elec` : date pré-TURPE 7 | **P1** | `test_step28_shadow_breakdown.py` | Corrigé |

---

## Détail des corrections

### 1. `delta_pct` écrase le pourcentage total TTC (billing_service.py)

**Symptôme** : Sur la modale, la ligne Total TTC affiche "+55.6%" alors que l'écart réel est ~9.2%.

**Cause racine** : Dans `_rule_reseau_mismatch()` (L651), le dict metrics fait `**res` (qui contient `delta_pct` = % total TTC depuis shadow_billing_v2), puis écrase avec `"delta_pct": round(pct, 1)` où `pct` est le % du composant réseau uniquement.

**Vérification** : Le frontend (`InsightDrawer.jsx:382`) lit `m.delta_pct` pour la ligne Total TTC. Les autres usages frontend de `delta_pct` (ConsoKpiHeader, BenchmarkPanel, SiteCompliancePage) concernent d'autres objets data — aucun impact.

**Fix** : Renommé en `delta_reseau_pct` (R13) et `delta_taxes_pct` (R14). Le `delta_pct` de shadow_billing_v2 (% TTC) n'est plus écrasé.

### 2. Abonnement fournisseur : prorata incorrect (engine.py)

**Symptôme** : "180.00 EUR/mois × 0.0795 = 14.30 EUR HT" — devrait être ~174 EUR.

**Cause racine** : `fee_ht = fixed_fee_eur_month * prorata_factor` avec `prorata_factor = days/365` (prorata annuel). Correct pour les composantes en EUR/an (TURPE gestion, comptage, soutirage fixe), mais faux pour un abonnement mensuel.

**Source CRE** : Le prorata annuel `jours/365` est conforme à la brochure TURPE 7 pour les composantes tarifaires en EUR/an. Mais l'abonnement fournisseur est un tarif mensuel contractuel → prorata `jours/30`.

**Vérification croisée** : La reconstitution gaz (`_build_gas_reconstitution`) utilisait déjà `prorata_days / 30` correctement.

**Fix** : `monthly_prorata = prorata_days / 30.0` dédié pour l'abonnement fournisseur. Résultat : 180 × 29/30 = 174.00 EUR HT.

### 3. tax_catalog.json : TURPE 7 C4_BT et C3_HTA manquantes

**Symptôme** : Panel Expert affiche "TURPE_ENERGIE_C4_BT : 0.0313 EUR/kWh (TURPE 6, 2021)" pour une facture post-août 2025.

**Cause racine** : `tax_catalog.json` avait les entrées TURPE 7 uniquement pour C5_BT. Pour C4_BT/C3_HTA, seules les entrées TURPE 6 (valid_to: 2025-07-31) existaient. Le `get_entry()` fait un fallback sur la première entrée quand aucune ne matche → retourne le taux TURPE 6 périmé.

**Impact chaîne** : `_safe_rate()` passe par `tax_catalog_service.get_rate()` (priorité 2) qui retourne le taux TURPE 6, court-circuitant le fallback hardcodé correct (priorité 3).

**Fix** : Ajouté 4 entrées TURPE 7 (valid_from 2025-08-01) :
- `TURPE_ENERGIE_C4_BT` : 0.0390 EUR/kWh
- `TURPE_GESTION_C4_BT` : 30.60 EUR/mois
- `TURPE_ENERGIE_C3_HTA` : 0.0260 EUR/kWh
- `TURPE_GESTION_C3_HTA` : 58.44 EUR/mois

### 4. tax_catalog.json : ACCISE_ELEC manquante post-juillet 2025

**Symptôme** : Panel Expert affiche "ACCISE_ELEC : 0.021 (2024)" pour une facture 2025-2026.

**Fix** : Ajouté 2 entrées :
- 2025-08-01 → 2026-01-31 : 0.02579 EUR/kWh (T2 PME, 25.79 EUR/MWh)
- 2026-02-01 → null : 0.02658 EUR/kWh (T2 PME, 26.58 EUR/MWh, LFI 2026)

### 5. tax_catalog.json : CTA_ELEC manquante post-2025

**Symptôme** : CTA affichée à 21.93% alors que le taux est 27.04% depuis le 1er janvier 2026.

**Fix** : Corrigé `valid_to` à 2025-12-31 et ajouté l'entrée CTA_ELEC 2026+ : 27.04% (aligné avec `catalog.py:CTA_ELEC_2026`).

### 6. Précision `unit_rate` accise (billing_shadow_v2.py)

**Cause** : `round(accise, 4)` → 0.02658 arrondi à 0.0266. Le test compare `kwh × unit_rate` vs `expected_taxes_ht` et trouve un écart.

**Fix** : `round(accise, 5)` pour les taux accise.

### 7. TURPE_GESTION_C4_BT incohérent entre catalog et YAML/fallback

**Constat** : Premier ajout mettait 41.76 EUR/mois (CG 217.80 + CC 283.27 = 501.07/12) mais le YAML et le fallback hardcodé utilisent 30.60 EUR/mois (gestion shadow simplifié, indexé TURPE 6 → 7).

**Vérification cross-source** : Script Python validant les 3 sources (YAML `tarif_loader`, `tax_catalog_service`, `_load_fallback`) → tous alignés sur 30.60.

**Fix** : Corrigé le taux à 30.60 EUR/mois dans `tax_catalog.json`.

### 8. Tests avec dates pré-TURPE 7 (test_step28_shadow_breakdown.py)

**Cause** : `FakeInvoice` utilise `period_start=2025-01-01` (TURPE 6 encore valide) mais les tests assertent des taux TURPE 7 (effectif août 2025).

**Fix** : Mis à jour les dates des tests à `2025-10-01` (post-TURPE 7) et ajusté les assertions accise (0.02579 au lieu de 0.02623).

---

## Cohérence vérifiée (cross-check 3 sources)

Validation par script des 3 sources de taux pour `date(2026, 3, 1)` :

| Code | YAML tarif_loader | tax_catalog.json | _FALLBACK hardcodé | Verdict |
|------|:-:|:-:|:-:|:-:|
| TURPE_ENERGIE_C5_BT | 0.0453 | 0.0453 | 0.0453 | OK |
| TURPE_ENERGIE_C4_BT | 0.0390 | 0.0390 | 0.0390 | OK |
| TURPE_ENERGIE_C3_HTA | 0.0260 | 0.0260 | 0.0260 | OK |
| TURPE_GESTION_C5_BT | 18.48 | 18.48 | 18.48 | OK |
| TURPE_GESTION_C4_BT | 30.60 | 30.60 | 30.60 | OK |
| TURPE_GESTION_C3_HTA | 58.44 | 58.44 | 58.44 | OK |
| ACCISE_ELEC | 0.02658 | 0.02658 | 0.02658 | OK |
| CTA_ELEC (2026) | — | 27.04 | — | OK |
| CTA_ELEC (2025) | — | 21.93 | — | OK |

---

## Éléments vérifiés (PAS de bug)

| Élément | Verdict | Détail |
|---------|---------|--------|
| Ventilation HPB=0, HCB=0 | **OK** | Période 100% hiver → HPB/HCB correctement à zéro |
| Calendrier TURPE 7 (turpe_calendar.py) | **OK** | Postes horosaisonniers, jours fériés, HP/HC correct |
| Segment C4_BT pour 108 kVA | **OK** | 36 < 108 ≤ 250 → C4_BT (billing_shadow_v2:L494, catalog:L1117) |
| TVA 20% uniforme post août 2025 | **OK** | Suppression 5.5% correctement implémentée (engine + shadow) |
| Gestion TURPE prorata (EUR/an) | **OK** | 217.80 EUR/an × 29/365 = 17.30 EUR HT correct |
| Résolution temporelle CTA dans billing engine | **OK** | `_resolve_temporal_code` bascule sur 27.04% post 2026-01-01 |
| CEE shadow (coût implicite) | **OK** | Affiché à 0 EUR attendu, formule estimative à 317.18 EUR (design voulu) |
| Reconstitution gaz prorata abonnement | **OK** | Utilise déjà `prorata_days / 30` |
| Frontend InsightDrawer.jsx | **OK** | `m.delta_pct` lit le bon champ, pas de régression |
| Frontend autres pages (ConsoKpi, Benchmark) | **OK** | `delta_pct` sur d'autres objets, non impacté |
| Doublons tax_catalog.json | **OK** | Aucun doublon de période sur un même code |
| Continuité temporelle ACCISE_ELEC | **OK** | 2024-02→2025-01 / 2025-02→2025-07 / 2025-08→2026-01 / 2026-02→∞ |

---

## Tests — Bilan final

### Backend (billing)

```
pytest tests/ -k "billing or shadow or catalog or engine"
781 passed, 5 failed, 1 skipped
```

| Test | Fichier | Cause | Notre faute ? |
|------|---------|-------|:---:|
| `test_c4_cu_option` | `test_billing_engine.py` | Attend `turpe_soutirage_hp` mais engine retourne 4 plages HPH/HCH/HPB/HCB | Non |
| `test_invalid_status_rejected` | `test_billing_trust_gate.py` | Structure réponse API changée (`detail` manquant) | Non |
| `test_gas_ticgn_2023` | `test_shadow_billing_gas.py` | TICGN 2023 temporel non résolu (pas d'entrée bouclier) | Non |
| `test_gas_ticgn_2026` | `test_shadow_billing_gas.py` | TICGN 2026 temporel — même problème | Non |
| `test_compliance_engine_documented` | `test_sprint_p1.py` | Score compliance doc — test désynchronisé | Non |

### Frontend

```
vitest run → 3589 passed, 0 failed, 2 skipped
```

### Régression introduite par nos corrections : **0**

### Tests corrigés par nos soins : **+2** (`test_turpe_uses_yaml`, `test_taxes_accise_elec`)

---

## Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `backend/services/billing_service.py` | Renommé `delta_pct` → `delta_reseau_pct` (R13), `delta_taxes_pct` (R14) |
| `backend/services/billing_engine/engine.py` | Prorata abonnement fournisseur : `prorata_days/30` au lieu de `prorata_factor` (days/365) |
| `backend/services/billing_shadow_v2.py` | Précision accise `round(accise, 5)` au lieu de `round(accise, 4)` |
| `backend/app/referential/tax_catalog.json` | +8 entrées TURPE 7/ACCISE/CTA, correction gestion C4_BT, version `2026-03-28` |
| `backend/tests/test_step28_shadow_breakdown.py` | Dates post-TURPE 7 et assertion accise T2 corrigée |

---

## Definition of Done

- [x] Les 3 sources de taux (YAML, catalog JSON, fallback) sont alignées pour tous les segments
- [x] `delta_pct` sur la modale affiche le % TTC correct (pas le % composant)
- [x] Abonnement fournisseur prorata mensuel (jours/30), pas annuel (jours/365)
- [x] Panel Expert affiche les taux TURPE 7 pour les factures post-août 2025
- [x] Panel Expert affiche l'accise T2 2025-2026 correcte
- [x] CTA résout à 27.04% pour les factures 2026+
- [x] Frontend : 3589 tests passed, 0 failed
- [x] Backend billing : 781 passed, 5 failed (pré-existants non liés), 0 régression
- [x] Aucun doublon de code/période dans tax_catalog.json
