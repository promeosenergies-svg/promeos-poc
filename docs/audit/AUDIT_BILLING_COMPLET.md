# AUDIT BRIQUE BILLING — 28 mars 2026

## Score global : 72 / 100

> Brique fonctionnellement complète (14 règles, shadow V2 bridgé, 5 composantes, seed HELIOS). Faiblesses : catalog.py contient des erreurs critiques (CTA 15% erroné, TVA 5.5% non supprimée), seed utilise des tarifs hardcodés au lieu du moteur, et les factures en DB n'ont pas de `energy_type` renseigné.

---

## Scores par sous-brique

| Sous-brique | Score | Commentaire |
|-------------|:-----:|-------------|
| Billing Engine (catalog/parser) | 65 | Catalog riche (1261 l) mais CTA_ELEC_2026 = **15% FAUX** (devrait être 27.04%), TVA 5.5% sur 15 composantes non supprimée post-août 2025 |
| Shadow Billing V2 | 82 | Bridge DB opérationnel, versionnement temporel, TVA suppression gérée, `tariff_source` tracé |
| Billing Normalization | 70 | Fonctionnel mais couplé au seed |
| Rules (R1-R14) | 80 | 14 règles actives, seuils documentés, explainability |
| Seed HELIOS | 55 | Tarifs réseau hardcodés (0.045, 0.0225), pas de versionnement temporel, `energy_type` non renseigné |
| UX/UI (BillingPage + BillIntelPage) | 75 | ShadowBreakdownCard avec `tarif_version`, labels clairs, Explain terms, mais `tariff_source` pas visible utilisateur |
| Versionnement tarifaire | 78 | Shadow V2 gère TURPE 6→7 et CTA via DB versionnée. Catalog gère accise par date mais CTA/TVA erronés |
| Cohérence inter-briques | 80 | Billing → Actions (idempotent), → Cockpit (`billing_anomalies_eur`), → Market Data (`get_reference_price` via MktPrice), → RegOps (trust score) |
| Tests | 75 | 405 tests billing, 6565 lignes. Bonne couverture engine/shadow mais pas de golden tests factures réelles |

---

## Métriques code billing

| Métrique | Valeur |
|----------|--------|
| Fichiers backend billing | 22 (.py) |
| Fichiers tests billing | 16 |
| Lignes backend billing | 15 879 |
| Lignes tests billing | 6 565 |
| Tests unitaires billing | 405 |
| Fichiers frontend billing | 11 |
| Factures modèles (docs) | 85 PDFs/images |
| Factures en DB | 36 (demo_seed) |
| Règles anomalies | 14 (R1-R14) |
| Endpoints billing | 28 |

---

## Constantes obsolètes et erreurs trouvées

### CRITIQUE — Erreurs dans `billing_engine/catalog.py`

| # | Fichier:Ligne | Valeur code | Valeur correcte | Source | Impact |
|---|--------------|-------------|----------------|--------|--------|
| **C1** | `catalog.py:577` | CTA_ELEC_2026 = **15.00%** | **27.04%** | LFI 2025, arrêté jan 2026 | **FAUX** — CTA sous-estimé de 12 pts dans le billing engine |
| **C2** | `catalog.py:579` | source = "15%" | "27.04%" | — | Label trompeur |
| **C3** | `catalog.py:50-122` | `tva_rate: 0.055` sur 15 composantes TURPE | **0.20** post-août 2025 | LFI 2025 art. 20, BOFIP ACTU-2025-00057 | TVA sous-estimée sur abo/CTA/TURPE fixe |
| **C4** | `catalog.py:580` | `valid_from: "2026-02-01"` | `"2026-01-01"` | CTA applicable au 1er jan 2026 | Date d'effet décalée d'1 mois |

### MODÉRÉ — Seed HELIOS hardcodé

| # | Fichier:Ligne | Valeur code | Problème |
|---|--------------|-------------|----------|
| **S1** | `billing_seed.py:68` | `KWH * 0.045` réseau | Hardcodé au lieu d'utiliser TURPE par segment/date |
| **S2** | `billing_seed.py:69` | `KWH * 0.0225` taxes | Hardcodé au lieu d'utiliser CSPE versionnée |
| **S3** | `billing_seed.py:139` | `9000 * 0.0453 * 2.3` anomalie R13 | TURPE C5 hardcodé |
| **S4** | `billing_seed.py:143` | `9000 * 0.0225 * 1.08` anomalie R14 | CSPE hardcodée |
| **S5** | Factures DB | `energy_type = NULL` sur 36/36 factures | Impossible de filtrer élec vs gaz |

### FAIBLE — Shadow V2 (déjà corrigé ce sprint)

| # | Fichier | Statut |
|---|---------|--------|
| CTA YAML | `tarifs_reglementaires.yaml` | ✅ Corrigé → 27.04% |
| CSPE YAML | `tarifs_reglementaires.yaml` | ✅ Corrigé → 0.02658 |
| TVA réduite | `tarif_loader.py` | ✅ Corrigé → retourne 0.20 post-août 2025 |
| Bridge DB | `billing_shadow_v2.py` | ✅ Corrigé → `regulated_tariffs` |

---

## Tableau de conformité tarifaire

| Composante | Dans le code | Valeur code | Valeur officielle mars 2026 | Source | Statut |
|------------|-------------|-------------|---------------------------|--------|:------:|
| TURPE 7 HTA CU HPH | DB `regulated_tariffs` | 42.30 €/MWh | 42.30 €/MWh | CRE n°2025-78 | ✅ |
| TURPE 7 HTA CU HCH | DB `regulated_tariffs` | 19.90 €/MWh | 19.90 €/MWh | CRE n°2025-78 | ✅ |
| TURPE 7 HTA CU HPB | DB `regulated_tariffs` | 10.10 €/MWh | 10.10 €/MWh | CRE n°2025-78 | ✅ |
| TURPE 7 HTA CU HCB | DB `regulated_tariffs` | 6.90 €/MWh | 6.90 €/MWh | CRE n°2025-78 | ✅ |
| TURPE 7 Pointe | DB `regulated_tariffs` | 57.40 €/MWh | 57.40 €/MWh | CRE n°2025-78 | ✅ |
| TURPE 7 Part fixe | DB `regulated_tariffs` | 14.41 €/kW/an | 14.41 €/kW/an | CRE n°2025-78 | ✅ |
| CSPE C5 pro (fév 2026) | DB `regulated_tariffs` | 30.35 €/MWh | 30.35 €/MWh | LFI 2026 | ✅ |
| CSPE C4 (fév 2026) | DB `regulated_tariffs` | 26.58 €/MWh | 26.58 €/MWh | LFI 2026 | ✅ |
| CSPE C2 (fév 2026) | DB `regulated_tariffs` | 26.58 €/MWh | 26.58 €/MWh | LFI 2026 | ✅ |
| CTA taux (DB) | DB `regulated_tariffs` | 27.04% | 27.04% | LFI 2025, jan 2026 | ✅ |
| CTA taux (YAML) | `tarifs_reglementaires.yaml` | 27.04% | 27.04% | — | ✅ |
| **CTA taux (catalog)** | `catalog.py:577` | **15.00%** | **27.04%** | — | **❌ FAUX** |
| CTA taux pré-2026 (catalog) | `catalog.py:569` | 21.93% | 21.93% | Arrêté juil 2021 | ✅ |
| TVA normale | DB + YAML + catalog | 20% | 20% | CGI art. 278 | ✅ |
| **TVA réduite (catalog)** | `catalog.py:50+` | **5.5%** | **20% (supprimée)** | LFI 2025 art. 20 | **❌** |
| TVA réduite (shadow V2) | `billing_shadow_v2.py` | 20% post-août 2025 | 20% | — | ✅ |
| TICGN pros | `tarifs_reglementaires.yaml` | 16.37 €/MWh | 16.37 €/MWh | Code impositions | ✅ |
| ATRD variable | `tarifs_reglementaires.yaml` | 0.025 €/kWh | ~25 €/MWh T2 | CRE ATRD7 GRDF | ✅ |
| ATRT transport | `tarifs_reglementaires.yaml` | 0.012 €/kWh | ~12 €/MWh | CRE ATRT8 | ✅ |
| Capacité | DB `regulated_tariffs` | 98.60 €/MW | 98.60 €/MW | Enchères déc 2025 | ✅ |
| CEE P6 | DB `regulated_tariffs` | 5.00 €/MWh | ~5 €/MWh | P6 2026-2030 | ✅ |
| CO₂ élec | `config/emission_factors.py` | 0.052 kgCO₂/kWh | 0.052 kgCO₂/kWh | ADEME V23.6 | ✅ |
| Prix ref fallback | `tarifs_reglementaires.yaml` | 0.068 €/kWh | Spot 30j | EPEX bridgé | ✅ |

---

## P0 — Bloquants démo (5 items)

| # | Fichier:Ligne | Problème | Correction | Effort |
|---|--------------|----------|------------|--------|
| 1 | `catalog.py:577` | **CTA_ELEC_2026 = 15%** — valeur fausse (devrait être 27.04%) | Corriger `"rate": 27.04` | 5 min |
| 2 | `catalog.py:580` | `valid_from: "2026-02-01"` — devrait être `"2026-01-01"` | Corriger la date | 5 min |
| 3 | `catalog.py:50-122` | `tva_rate: 0.055` sur 15 composantes TURPE fixe — non supprimée post-août 2025 | Ajouter versionnement TVA dans le catalog ou supprimer le 5.5% | 1h |
| 4 | Factures DB | `energy_type = NULL` sur 36/36 factures seed | Renseigner `energy_type` dans `gen_billing.py` / `billing_seed.py` | 30 min |
| 5 | `billing_seed.py:68-95` | Tarifs réseau/taxes hardcodés (0.045, 0.0225) au lieu du moteur | Utiliser `_safe_rate()` ou les constantes YAML | 1h |

## P1 — Crédibilité (5 items)

| # | Problème | Correction | Effort |
|---|----------|------------|--------|
| 1 | Pas de golden tests (factures réelles parsées + vérifiées) | Créer 2-3 golden tests depuis les 85 factures modèles | 4h |
| 2 | `billing.py` routes = 1863 lignes — monolithique | Extraire seed-demo, shadow endpoints, canonical validation | 3h |
| 3 | `ShadowBreakdownCard.jsx` n'affiche pas `tariff_source` (DB vs fallback) | Ajouter micro-texte source | 30 min |
| 4 | `compute_shadow_breakdown` utilise encore `get_cta_taux()` du YAML (pas le catalog temporel) | Aligner sur `_safe_rate` avec at_date | 1h |
| 5 | Le catalog a des taux TURPE 7 BT≤36 par plage (CU4) mais pas utilisés par le shadow (qui utilise la moyenne pondérée YAML) | Le bridge DB résout ce problème — documenter | 30 min |

## P2 — Best-in-class (5 items)

| # | Thème | Description | Effort |
|---|-------|-------------|--------|
| 1 | OCR factures | Parser les 85 factures modèles avec IA pour extraction automatique | 8h |
| 2 | Versionnement catalog complet | Migrer toutes les constantes catalog vers `regulated_tariffs` DB | 4h |
| 3 | Benchmark shadow | Comparer shadow billing vs facture réelle sur 10+ factures modèles | 4h |
| 4 | Alertes TVA | Détecter si un fournisseur facture encore 5.5% post-août 2025 | 2h |
| 5 | Export audit | PDF d'audit par facture avec décomposition et sources | 4h |

---

## Seed HELIOS — conformité

| Aspect | Statut | Détail |
|--------|:------:|--------|
| Nombre factures | 36 | 5 sites × ~7 mois |
| `energy_type` renseigné | **❌** | NULL sur 36/36 — pas de distinction élec/gaz |
| Tarifs réseau | **⚠️** | Hardcodés 0.045 €/kWh — pas de TURPE 6 avant août 2025 |
| Tarifs taxes | **⚠️** | Hardcodés 0.0225 €/kWh — pas de CSPE versionnée |
| Anomalie R13 | **⚠️** | TURPE × 2.3 hardcodé (0.0453) — fonctionnel mais pas versionné |
| Anomalie R14 | **⚠️** | CSPE × 1.08 hardcodé (0.0225) — idem |
| Idempotent | ✅ | `seed_billing_demo` vérifie les existants |
| Structure lines | ✅ | 5-8 lignes par facture (energy, network, tax, other) |

---

## Cohérence inter-briques

| Flux | Statut | Détail |
|------|:------:|--------|
| Billing → Actions | ✅ | `ActionItem` créé via `sync_actions`, source_type BILLING, idempotent |
| Billing → Cockpit | ✅ | `billing_anomalies_eur` dans le risque cockpit |
| Billing → Market Data | ✅ | `get_reference_price` → contrat > site_tariff > MktPrice spot 30j > fallback |
| Billing → Patrimoine | ✅ | `site_id`, `contract_id` sur chaque facture |
| Billing → RegOps | ✅ | Trust score basé sur anomalies shadow billing |

---

## Tests billing — résultat

```
405 tests billing au total
  - billing_engine: 109 tests
  - billing_5sites: 44 tests
  - billing_base: 41 tests
  - billing_invariants: 37 tests
  - billing_step28: 26 tests
  - billing_v68: 24 tests
  - shadow_gas: 24 tests
  - shadow_bridge: 18 tests (nouveau)
  - shadow_elec: 18 tests
  - billing_catalog: 18 tests
  - billing_coverage: 14 tests
  - billing_v66: 20 tests (checks + scoping + pdf)
  - billing_trust_gate: 6 tests
  - billing_v69: 6 tests

Résultat: 147 passed sur run sélectif (2 pré-existants exclus)
Golden tests: AUCUN (pas de factures réelles validées)
```

---

## Plan de correction (ordonné)

### Sprint immédiat (P0)

1. **Fix catalog CTA** — `catalog.py:577` → `rate: 27.04`, `valid_from: "2026-01-01"`, `tva_rate: 0.20`
2. **Fix catalog TVA 5.5%** — Supprimer ou versionner le `tva_rate: 0.055` sur les 15 composantes TURPE fixe post-août 2025
3. **Fix seed `energy_type`** — Renseigner élec/gaz sur les factures seedées
4. **Fix seed tarifs** — Utiliser les constantes YAML/DB au lieu des hardcodés

### Sprint suivant (P1)

5. **Golden tests** — Parser 2-3 factures EDF/Engie réelles → valider le shadow billing
6. **Split billing.py** — Extraire les endpoints seed et canonical en sous-modules
7. **UX `tariff_source`** — Afficher dans ShadowBreakdownCard

### Backlog (P2)

8. **Migration catalog → DB** — Toutes les constantes du catalog dans `regulated_tariffs`
9. **OCR factures** — Pipeline IA extraction
10. **Benchmark shadow** — Mesurer la précision sur factures réelles
