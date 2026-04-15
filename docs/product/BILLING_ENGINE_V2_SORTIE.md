# BILLING ENGINE V2 — SORTIE COMPLÈTE

## 1. DIAGNOSTIC

### Problèmes identifiés dans le code existant (billing_shadow_v2.py)

| Bug | Impact | Sévérité |
|-----|--------|----------|
| `_resolve_segment(contract)` lit `subscribed_power_kva` sur `EnergyContract` qui n'a pas ce champ → toujours C5_BT | Segment TURPE toujours faux pour C4 (>36 kVA) | CRITIQUE |
| CTA calculée sur `turpe_gestion * (days/30)` ≈ 18 EUR au lieu de gestion+comptage+soutirage_fixe ≈ 309 EUR | CTA sous-estimée ×16.7 | CRITIQUE |
| Prorata `days/30.0` au lieu de `days/days_in_year` | Composantes fixes fausses | HAUTE |
| TURPE = single rate × kWh (pas de 5 composantes C4) | Acheminement non décomposé | HAUTE |
| Badge "Confiance élevée" hardcodé sans lien avec la qualité réelle | UX trompeuse | MOYENNE |
| Pas de prix par période (HPE/HCE/HP/HC) | Fourniture C4 impossible | HAUTE |

### Décision architecturale
**Clean-room billing engine** dans `services/billing_engine/` (package séparé) plutôt que refactor in-place de `billing_shadow_v2.py`. Raisons :
- Code existant trop couplé aux anciennes structures
- Permet migration progressive (fallback V1 via `?engine=v1`)
- Tests indépendants sans fixtures DB

---

## 2. ARCHITECTURE

```
backend/services/billing_engine/
├── __init__.py          # Exports publics
├── types.py             # Enums + dataclasses (TariffSegment, TariffOption,
│                        #   ComponentResult, ReconstitutionResult, AuditTrace)
├── catalog.py           # TURPE7_RATES dict, get_rate(), resolve_segment(),
│                        #   get_soutirage_*_codes() — ZERO magic numbers
└── engine.py            # compute_prorata(), compute_supply_breakdown(),
                         #   compute_turpe_breakdown(), compute_cta(),
                         #   compute_excise(), build_invoice_reconstitution(),
                         #   compare_to_supplier_invoice(), generate_audit_trace()
```

**Flux d'exécution** :
```
Route /shadow-breakdown → _compute_breakdown_v2()
  ↓ lit contract + invoice depuis DB
  ↓ mappe vers engine inputs
  ↓ appelle build_invoice_reconstitution()
      ↓ resolve_segment(kVA)
      ↓ compute_prorata(start, end)
      ↓ compute_supply_breakdown()     → N composantes fourniture
      ↓ compute_turpe_breakdown()      → 3-5 composantes TURPE
      ↓ compute_cta(turpe_fixes)       → 1 composante CTA
      ↓ compute_excise(kwh)            → 1 composante accise
      ↓ totalise HT/TVA/TTC
  ↓ compare_to_supplier_invoice()
  ↓ retourne JSON compatible frontend
```

---

## 3. MIGRATIONS

| Table | Colonne ajoutée | Type | Usage |
|-------|----------------|------|-------|
| `energy_contracts` | `subscribed_power_kva` | REAL | Segment TURPE |
| `energy_contracts` | `tariff_option` | VARCHAR(10) | Option tarifaire |
| `energy_contracts` | `price_hpe_eur_kwh` | REAL | Prix HPE |
| `energy_contracts` | `price_hce_eur_kwh` | REAL | Prix HCE |
| `energy_contracts` | `price_hp_eur_kwh` | REAL | Prix HP |
| `energy_contracts` | `price_hc_eur_kwh` | REAL | Prix HC |
| `energy_contracts` | `price_base_eur_kwh` | REAL | Prix Base |
| `energy_contracts` | `pass_through_items` | TEXT | Clauses pass-through |
| `energy_invoices` | `invoice_type` | VARCHAR(20) | Type facture |
| `energy_invoices` | `is_estimated` | BOOLEAN | Index estimé |
| `energy_invoices` | `start_index` | REAL | Index compteur début |
| `energy_invoices` | `end_index` | REAL | Index compteur fin |
| `energy_invoice_lines` | `period_code` | VARCHAR(10) | BASE/HP/HC/HPE/HCE |
| `energy_invoice_lines` | `line_category` | VARCHAR(50) | Catégorie fine |

Script : `backend/migrations/add_billing_engine_v2_columns.py` (idempotent, re-runnable).

---

## 4. PLAN DE REFACTOR SERVICE-PAR-SERVICE

| Fichier | Action | Priorité |
|---------|--------|----------|
| `billing_engine/` (NOUVEAU) | Créé — engine déterministe | ✅ FAIT |
| `routes/billing.py` | `shadow-breakdown` pointe vers V2 avec fallback V1 | ✅ FAIT |
| `billing_shadow_v2.py` | INCHANGÉ — conservé comme fallback `?engine=v1` | Phase 2 |
| `billing_service.py` | Anomaly rules → à rewirer sur V2 reconstitution | Phase 2 |
| `config/tarifs_reglementaires.yaml` | Remplacé par `catalog.py` pour V2 | Phase 2 |
| `demo_seed/gen_billing.py` | Enrichi avec V2 fields | ✅ FAIT |
| `demo_seed/packs.py` | Helios contracts avec kVA/option/prix | ✅ FAIT |

---

## 5. CODE LIVRÉ

### Fichiers créés
- `backend/services/billing_engine/__init__.py` (26 lignes)
- `backend/services/billing_engine/types.py` (143 lignes)
- `backend/services/billing_engine/catalog.py` (310 lignes)
- `backend/services/billing_engine/engine.py` (644 lignes)
- `backend/tests/test_billing_engine.py` (88 tests, ~1060 lignes)
- `backend/migrations/add_billing_engine_v2_columns.py` (72 lignes)

### Fichiers modifiés
- `backend/models/enums.py` — +3 enums (TariffOptionEnum, InvoiceTypeEnum, ReconstitutionStatusEnum)
- `backend/models/billing_models.py` — +14 colonnes sur 3 tables
- `backend/models/__init__.py` — +3 exports enum
- `backend/routes/billing.py` — endpoint V2 + adapter `_compute_breakdown_v2()`
- `backend/services/demo_seed/packs.py` — helios contracts avec V2 fields
- `backend/services/demo_seed/gen_billing.py` — écrit les V2 fields
- `frontend/src/components/billing/ShadowBreakdownCard.jsx` — UX V2 honnête

---

## 6. TESTS

**88 tests — 11 classes — tous GREEN**

| Classe | Tests | Couverture |
|--------|-------|------------|
| TestComputeProrata | 8 | days/365, leap year, edge cases |
| TestCatalog | 7 | get_rate, RateSource, TVA, source tracability |
| TestResolveSegment | 8 | C5/C4/C3 boundaries, null/zero/negative |
| TestSoutirageCodeMapping | 6 | LU/MU/CU fixe+variable, C5 no fixe |
| TestComputeSupply | 4 | BASE, HPE+HCE, missing price, zero kWh |
| TestTurpeC4 | 5 | 5 composantes, gestion prorata, soutirage fixe, variable |
| TestTurpeC5 | 4 | 3-4 composantes, gestion rate, unsupported |
| TestCTA | 4 | Assiette C4, excludes variable, C5, real invoice |
| TestAccise | 3 | Formula, zero, traceability |
| TestBuildReconstitution | 13 | RECONSTITUTED/PARTIAL/READ_ONLY/UNSUPPORTED, totals, TVA split |
| TestCompareToSupplier | 4 | ok/warn/alert thresholds, per-component |
| TestAuditTrace | 2 | Sources, comparison |
| TestIntegrationRealInvoice | 10 | EDF C4 108 kVA LU structure complète |
| TestRegression | 6 | February, MU, CU, HP/HC C5, no fallback, zero power |

### Bug découvert par les tests
**Prorata** : `days/days_in_month` donnait 1.0 pour un mois complet, appliquant le taux annuel entier à 1 mois. Corrigé en `days/days_in_year`.

---

## 7. CHECKLIST QUALITÉ

- [x] Zero magic numbers — tous les taux dans `catalog.py` avec source
- [x] Zero silent fallback — données manquantes → PARTIAL + `missing_inputs[]`
- [x] Chaque composante retourne : amount, formula, inputs, rate_sources
- [x] Prorata calendaire exact : `days / days_in_year`
- [x] CTA sur assiette correcte (gestion + comptage + soutirage fixe)
- [x] TVA split : 5.5% sur fixe/CTA, 20% sur variable/accise/fourniture
- [x] Gas → READ_ONLY (pas de calcul fictif)
- [x] Acomptes → READ_ONLY
- [x] C3 HTA → UNSUPPORTED
- [x] Badge "Confiance élevée" remplacé par statut reconstitution honnête
- [x] Taux [TO_VERIFY] génèrent des warnings explicites
- [x] Backward compatible (V1 fallback via `?engine=v1`)
- [x] Frontend compatible V1 et V2 simultanément
- [x] Seed Helios enrichi avec kVA/option/prix par période

---

## 8. RISQUES RÉSIDUELS

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Taux TURPE 7 `[TO_VERIFY]` vs CRE officiel | Écart composantes ±5-10% | Vérifier avec tables CRE avant production |
| CTA taux 27.04% vs 21.93% facture réelle | CTA surestimée ~23% | Confirmer arrêté CTA 2025 |
| C4 MU/CU: soutirage variable rates non vérifiés | Composantes acheminement | Cross-check CRE TURPE 7 |
| Pass-through clauses non implémentées | Contrats complexes | V2.1 |
| Énergie réactive / dépassement de puissance | Pénalités non calculées | Hors scope V1 |
| Factures multi-mois (>62j) | Prorata approximatif | Acceptable pour V1 |

---

## 9. NON-SCOPE V1 (EXPLICITE)

Les éléments suivants sont **intentionnellement exclus** de V1 :

- ❌ Énergie réactive / pénalités cos(φ)
- ❌ Mécanisme de capacité (MEOC)
- ❌ CEE (Certificats d'Économie d'Énergie)
- ❌ Reconstitution gaz (ATRD7/ATRT, PCS, T1-T4)
- ❌ Forward curve / Monte Carlo pour achats
- ❌ Campaign workflow (appels d'offres structurés)
- ❌ OCR PDF (extraction automatique de factures)
- ❌ Segments C3 HTA / C2 / C1
- ❌ Tarification pointe (période P)
- ❌ Dépassement de puissance souscrite

Chacun retourne un statut explicite (READ_ONLY ou UNSUPPORTED) au lieu de calculer silencieusement des valeurs fausses.

---

## 10. TOP 5 ACTIONS IMMÉDIATES

1. **Vérifier les taux TURPE 7 contre les tables CRE officielles** — Les rates `[TO_VERIFY]` dans `catalog.py` doivent être cross-checkés avec la délibération CRE TURPE 7 HTA-BT. Priorité : CTA (27.04% vs 21.93%), gestion C4 (303.36), comptage C4 (394.68), soutirage fixe LU (29.76).

2. **Re-seeder Helios et tester E2E** — `python -m services.demo_seed --pack helios --size S --reset` puis vérifier dans l'UI que le shadow-breakdown V2 s'affiche correctement pour chaque type de contrat.

3. **Rewirer les 14 anomaly rules** (`billing_service.py`) sur le `ReconstitutionResult` V2 au lieu du shadow V1 — les écarts par composante sont maintenant disponibles dans `component_gaps[]`.

4. **Ajouter les tests de benchmark TTC** — Avec les taux CRE vérifiés, ajouter un test qui compare le TTC engine vs TTC facture réelle (108 kVA LU) avec cible ≤ 2%.

5. **Supprimer `billing_shadow_v2.py`** — Une fois le V2 validé en production, retirer le fallback V1 et le code legacy.
