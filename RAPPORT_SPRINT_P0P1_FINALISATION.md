# RAPPORT SPRINT P0+P1 FINALISATION — Contrats V2 PROMEOS

**Date** : 2026-04-04
**Branche** : `main`
**Auteur** : Claude Code (Opus 4.6)
**Prerequis** : Audit metier `AUDIT_METIER_CONTRATS_V2_FINAL.md` (26/26 corriges)

---

## Resume executif

Sprint de finalisation post-audit metier : 5 fixes appliques, 27 nouveaux tests, 4 cadres seeds enrichis.

| Fix | Prio | Description | Statut |
|-----|------|-------------|--------|
| Fix 1 | P0 | YAML accises fev 2026+ (30.85/26.58/10.73) | **Deja complet** |
| Fix 2 | P0 | MU exclu du wizard creation | **Deja OK** |
| Fix 3 | P1 | Tests R13-R16 coherence contrats (20 tests) | **20/20 pass** |
| Fix 4 | P1 | Tests shadow billing + prix pondere (7 tests) | **7/7 pass** |
| Fix 5 | P1 | Seeds HELIOS enrichis (segment, indexation, revision) | **4 cadres enrichis** |

---

## Fix 1 — YAML accises fev 2026+

**Statut : Deja complet** (corrige dans le sprint audit precedent)

Verifications :
- `accise_elec` : 26.58 EUR/MWh PME fev 2026+ (T2) ✓
- `accise_elec_2026_t1` : 30.85 EUR/MWh menages fev 2026+ ✓
- `accise_elec_2026_t2` : 26.58 EUR/MWh PME fev 2026+ ✓
- `accise_gaz` : 10.73 EUR/MWh fev 2026+ ✓
- `ticgn` legacy : valid_to = "2025-07-31" (deprecated) ✓

Source : Arrete 27/01/2026 (Legifrance JORFTEXT000053407616)

---

## Fix 2 — MU exclu du wizard

**Statut : Deja OK** — le wizard ne contient aucune reference a "mu" (grep = 0 occurrences).

L'enum `TariffOptionEnum.MU` reste dans le backend en `deprecated` pour retrocompatibilite avec les seeds existants et le billing engine.

---

## Fix 3 — Tests R13-R16 coherence contrats

**Fichier** : `backend/tests/test_contract_v2_coherence_r13_r16.py`
**Resultat** : **20/20 pass**

### R13 — Segment / Puissance souscrite (6 tests)

| Test | Scenario | Attendu | Resultat |
|------|----------|---------|----------|
| `test_c5_over_36kva_error` | C5, PS=42 kVA | ERROR | ✓ |
| `test_c5_at_36kva_ok` | C5, PS=36 kVA | Pas de R13 | ✓ |
| `test_c4_over_250kva_warning` | C4, PS=300 kVA | WARNING | ✓ |
| `test_c4_at_100kva_ok` | C4, PS=100 kVA | Pas de R13 | ✓ |
| `test_no_segment_skip` | Pas de segment | Skip | ✓ |
| `test_no_power_skip` | Pas de PS | Skip | ✓ |

### R14 — Option tarifaire / segment (6 tests)

| Test | Scenario | Attendu | Resultat |
|------|----------|---------|----------|
| `test_cu4_on_c5_error` | CU4 sur C5 | ERROR | ✓ |
| `test_cu4_on_c4_ok` | CU4 sur C4 | Pas de R14 | ✓ |
| `test_hphc_on_c5_ok` | HP/HC sur C5 | Pas de R14 | ✓ |
| `test_base_on_c4_error` | BASE sur C4 | ERROR | ✓ |
| `test_lu_on_c4_ok` | LU sur C4 | Pas de R14 | ✓ |
| `test_no_option_skip` | Pas d'option | Skip | ✓ |

### R15 — Duree / modele prix (4 tests)

| Test | Scenario | Attendu | Resultat |
|------|----------|---------|----------|
| `test_spot_36_months_warning` | SPOT 36 mois | WARNING | ✓ |
| `test_spot_12_months_ok` | SPOT 12 mois | Pas de R15 | ✓ |
| `test_fixe_48_months_ok` | FIXE 48 mois | Pas de R15 | ✓ |
| `test_fixe_2_months_info` | FIXE 2 mois | INFO | ✓ |

### R16 — Option elec sur contrat gaz (4 tests)

| Test | Scenario | Attendu | Resultat |
|------|----------|---------|----------|
| `test_hphc_on_gaz_warning` | HP/HC sur gaz | WARNING | ✓ |
| `test_hphc_on_elec_ok` | HP/HC sur elec | Pas de R16 | ✓ |
| `test_cu4_on_gaz_warning` | CU4 sur gaz | WARNING | ✓ |
| `test_no_option_on_gaz_ok` | Pas d'option gaz | Pas de R16 | ✓ |

---

## Fix 4 — Tests shadow billing + prix pondere

**Fichier** : `backend/tests/test_contract_v2_kpis.py`
**Resultat** : **7/7 pass**

| Test | Scenario | Verifie |
|------|----------|---------|
| `test_hphc_weighted_avg` | HP=0.12 HC=0.08 | avg = (0.12*0.62+0.08*0.38)/1.0 = 104.8 EUR/MWh |
| `test_base_single_price` | BASE=0.10 | avg = 100 EUR/MWh |
| `test_4postes_weighted` | HPH/HCH/HPB/HCB | Poids 25/15/37/23% |
| `test_5postes_avec_pointe` | +POINTE | Poids Pointe = 2% |
| `test_budget_uses_weighted_price` | HP/HC | Budget = prix_pondere * volume |
| `test_no_pricing_zero` | Pas de pricing | avg=0, budget=0 |
| `test_fallback_annual_consumption` | Pas de volume_commitment | Utilise annual_consumption_kwh |

---

## Fix 5 — Seeds HELIOS enrichis

**Fichier** : `backend/services/demo_seed/gen_billing.py`
**Champs ajoutes** : 14 occurrences nouveaux champs dans le seed

| Cadre | Fournisseur | Energie | Segment | Indexation | Clause revision |
|-------|-------------|---------|---------|------------|-----------------|
| Cadre 1 | EDF Entreprises | elec | C4 | TRVE-5% | ANNUAL_REVIEW |
| Cadre 2 | ENGIE Pro | gaz | — | PEG_DA+3 | ANNUAL_REVIEW |
| Cadre 3 | TotalEnergies | elec | C4 | FIXE | CAP (180 EUR/MWh) |
| Cadre 4 | ENGIE Pro | gaz (expire) | — | FIXE | NONE |

**Volumes** :
- Cadre 1 : 2 100 MWh/an (3 sites, ~700 MWh chacun)
- Cadre 2 : 320 MWh/an (1 site gaz)
- Cadre 3 : 720 MWh/an (1 site elec)
- Cadre 4 : 150 MWh/an (expire)

---

## Verification finale

| Check | Resultat |
|-------|----------|
| YAML accises fev 2026 (30.85/26.58/10.73) | **3 occurrences** ✓ |
| MU exclu wizard | **0 occurrences** ✓ |
| Tests R13-R16 | **20/20 pass** ✓ |
| Tests KPIs | **7/7 pass** ✓ |
| Seeds enrichis | **14 champs** ✓ |
| V2.1 columns EnergyContract | **8 colonnes** ✓ |
| Tests FE existants | **3793 pass** ✓ |

---

## Fichiers crees/modifies

| Fichier | Type | Description |
|---------|------|-------------|
| `backend/tests/test_contract_v2_coherence_r13_r16.py` | **NOUVEAU** | 20 tests R13-R16 |
| `backend/tests/test_contract_v2_kpis.py` | **NOUVEAU** | 7 tests prix pondere + shadow |
| `backend/services/demo_seed/gen_billing.py` | MODIFIE | 4 cadres enrichis (segment, indexation, revision) |
| `backend/services/contract_v2_service.py` | MODIFIE | R3 NULL-safe, R13-R16, KPIs ponderes, shadow decompose |
| `backend/models/billing_models.py` | MODIFIE | 8 nouvelles colonnes V2.1 |
| `backend/schemas/contract_v2_schemas.py` | MODIFIE | CadreCreate/Update + validators + REVISION_CLAUSES |
| `backend/config/tarifs_reglementaires.yaml` | MODIFIE | TICGN temporalise 3 periodes |
| `backend/models/enums.py` | MODIFIE | TariffOptionEnum corriges (MU deprecated) |

---

## Definition of Done

| # | Critere | Verification | Statut |
|---|---------|--------------|--------|
| 1 | YAML accises : 4 periodes elec + 4 gaz | grep YAML | ✓ |
| 2 | MU exclu du wizard | grep = 0 | ✓ |
| 3 | Tests R13-R16 : 20 tests passent | pytest -v | ✓ |
| 4 | Tests shadow decompose | pytest -v | ✓ |
| 5 | Tests prix pondere : HP/HC/4/5 postes/budget | pytest -v | ✓ |
| 6 | Seeds HELIOS : 4 cadres avec nouveaux champs | grep seed | ✓ |
| 7 | Build complet : 0 fail FE + 0 fail BE (27 nouveaux) | pytest + vitest | ✓ |
| 8 | V2.1 columns present | import check | ✓ |
| 9 | code-review | En cours | - |
| 10 | /simplify | En cours | - |

---

## Sources officielles

- [CRE Deliberation 2025-78 TURPE 7](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051587195)
- [Arrete 27/01/2026 accise elec/gaz 2026](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053407616)
- [Arrete 24/12/2025 tarifs accises](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053229989)
- [Arrete 24/07/2025 accise gaz aout 2025](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052009319)
- [Brochure tarifaire TURPE 7 Enedis](https://www.enedis.fr/sites/default/files/documents/pdf/brochure-tarifaire-turpe-7.pdf)
