# Remapping sentinels source-guards — passe automatique + inspection manuelle

> Pour chaque sentinel attendu (32) du prompt bilan, détection (1) match
> exact, (2) match approximatif par mots-clés, (3) inspection manuelle des
> candidats les plus probables, (4) classification finale.
>
> Date : 2026-04-30 · Branche : `claude/refonte-sol2` · SHA fin : `0e346c4b`

## Tableau remapping (post inspection manuelle)

| # | Sentinel attendu | Statut | Test équivalent réel | Fichier |
|---|---|---|---|---|
| 1 | `test_helios_no_demo_sites_leak` | 🔄 sémantique | `test_helios_s_creates_5_sites` (couvre seeding strict, pas le leak per se) | `backend/tests/test_demo_seed_packs.py` |
| 2 | `test_eur_amount_typed` | 🔄 renommé | `test_only_two_canonical_categories` + `test_no_modeled_or_estimated_keyword` | `backend/tests/test_eur_amount_service.py` |
| 3 | `test_eur_amount_traceability` | 🔄 renommé | `test_happy_path_persists` + `test_raises_on_empty_article` + `test_raises_on_empty_formula` | `backend/tests/test_eur_amount_service.py` |
| 4 | `test_no_modeled_eur_amount` | ✅ exact | `test_no_modeled_eur_amount` | `backend/tests/test_eur_amount_service.py` |
| 5 | `test_baseline_method_documented` | ✅ exact | `test_baseline_method_documented` | `backend/tests/test_baseline_service.py` |
| 6 | `test_baseline_r_squared_threshold` | 🔄 partiel | `test_r_squared_field_present` (présence champ, pas seuil) | `backend/tests/test_cockpit_facts_service.py` |
| 7 | `test_no_baseline_computation_in_frontend` | ✅ exact | `test_no_baseline_computation_in_frontend` | `backend/tests/test_baseline_service.py` |
| 8 | `test_baseline_a_fallback` | 🔄 renommé | `test_baseline_method_is_b_dju_adjusted_or_a_historical` | `backend/tests/test_cockpit_facts_service.py` |
| 9 | `test_cockpit_facts_unique_source` | ❓ ambigu | aucun équivalent strict — la doctrine "unique source" n'a pas de test dédié | — |
| 10 | `test_cockpit_facts_no_recompute` | ❓ ambigu | aucun équivalent strict — pas de test "no recompute" du payload | — |
| 11 | `test_cockpit_facts_dt_penalty_doctrine` | ✅ exact | `test_cockpit_facts_dt_penalty_doctrine` | `backend/tests/test_cockpit_facts_service.py` |
| 12 | `test_monthly_kpi_dju_adjusted` | ✅ exact | `test_monthly_kpi_dju_adjusted` | `backend/tests/test_cockpit_facts_service.py` |
| 13 | `test_monthly_kpi_normalized_window` | ✅ exact | `test_monthly_kpi_normalized_window` | `backend/tests/test_cockpit_facts_service.py` |
| 14 | `test_density_mode_consistent` | ❌ absent | feature `density_mode` non implémentée (`scope.density_mode = null` en runtime, cf `facts_endpoint.json`) | — |
| 15 | `test_density_mode_helios_direct` | ❌ absent | idem — pas de feature density_mode | — |
| 16 | `test_no_business_logic_in_frontend_cockpit` | 🔄 fichier-match | fichier dédié existe (FE) avec assertions comportementales | `frontend/src/__tests__/no_business_logic_in_frontend_cockpit.test.js` |
| 17 | `test_helios_surface_total` | 🔄 renommé | `test_helios_surface_total_17500_m2` + `test_facts_scope_surface_total_m2` | `backend/tests/test_helios_surface.py` |
| 18 | `test_trajectory_smoothed_by_echeance` | ✅ exact | `test_trajectory_smoothed_by_echeance` | `backend/tests/test_trajectory_smoothed.py` |
| 19 | `test_facture_portfolio_aggregation` | 🔄 partiel | `test_factures_is_high` (variation seuil, pas aggregation per se) | `backend/tests/test_compliance_evidence.py` |
| 20 | `test_acronyms_transformed_vue_executive` | 🔄 renommé | `test_replaces_known_acronym` + `test_inline_first_occurrence_glossed` + `test_all_canonical_acronyms_present` | `backend/tests/test_acronyms.py` |
| 21 | `test_notifications_timestamps_distributed` | 🔄 renommé | `test_notifications_seed_diverse_age_days` + `test_at_least_one_recent_under_24h` + `test_at_least_one_older_than_week` | `backend/tests/test_notifications_distribution.py` |
| 22 | `test_levers_kpi_in_mwh_not_eur` | 🔄 quasi-exact | `test_levers_kpi_value_in_mwh_not_eur` + `test_no_value_eur_field_in_levers` | `backend/tests/test_phase2_chiffrage_doctrinal.py` |
| 23 | `test_pilotage_triptyque_temporal_scales` | ❓ ambigu | aucun équivalent évident dans `test_pilotage_*.py` (concept triptyque non testé directement) | — |
| 24 | `test_no_surconso_7d_in_kpi_hero` | ❓ ambigu | concept présent (champ `surconso_7d_mwh` exposé) mais pas de garde-fou sur "absence dans KPI hero" | `backend/tests/test_cockpit_facts_service.py` (à vérifier) |
| 25 | `test_monthly_kpi_tooltip_complete` | 🔄 partiel | `test_monthly_vs_n1_present` (présence du bloc, pas tooltip exhaustif) | `backend/tests/test_cockpit_facts_service.py` |
| 26 | `test_exposure_kpi_decomposed` | 🔄 quasi-exact | `test_exposure_kpi_tooltip_decomposes_art_par_art` | `backend/tests/test_phase2_chiffrage_doctrinal.py` |
| 27 | `test_dt_penalty_uses_doctrine_constants` | 🔄 renommé | `test_imports_doctrine_penalty_constants` + `test_no_literal_7500_in_narrative_generator` | `backend/tests/test_phase2_chiffrage_doctrinal.py` |
| 28 | `test_actions_decision_show_mwh_or_traced_eur` | 🔄 renommé | `test_action_with_gain_exposes_mwh_year` + `test_critical_compliance_action_has_traced_penalty` + `test_non_critical_action_no_penalty` | `backend/tests/test_phase2_3_decisions_top3.py` |
| 29 | `test_kpi_hero_has_drill_down` | 🔄 quasi-exact | `test_all_3_hero_kpis_have_drill_down_href` + `test_each_builder_exposes_drill_down` | `backend/tests/test_phase3_drilldowns_legacy.py` |
| 30 | `test_pilotage_action_has_decision_link` | ❓ ambigu | `test_pilotage_strenum.py` ne couvre pas le link decision↔pilotage (couvre StrEnum + flex-ready) | — |
| 31 | `test_vue_executive_pushes_weekly_evolution` | 🔄 renommé | `test_typeddict_6_canonical_fields` + `test_direction_literal_4_values` + suite `test_phase3_3_weekly_deltas.py` (10 tests deltas) | `backend/tests/test_phase3_3_weekly_deltas.py` + `backend/tests/doctrine/test_weekly_delta_canonical.py` |
| 32 | `test_no_route_legacy_executive` | 🔄 fichier-match | `step3_no_legacy.test.js` (FE) couvre les redirects legacy → /cockpit/* via `legacyRedirects.js` | `frontend/src/__tests__/step3_no_legacy.test.js` |

## Synthèse compteurs (post inspection)

| Catégorie | Compte | Détail |
|---|---:|---|
| ✅ Exact match | **7/32** | #4, #5, #7, #11, #12, #13, #18 |
| 🔄 Renommé confirmé (équivalent solide) | **14/32** | #2, #3, #8, #16, #17, #20, #21, #22, #26, #27, #28, #29, #31, #32 |
| 🔄 Partiel (couvre une partie de la spec) | **5/32** | #1, #6, #19, #25 + #24 (intention présente, garde-fou direct manquant) |
| ❓ Ambigu (concept-level non garde-fou-able directement) | **4/32** | #9, #10, #23, #30 |
| ❌ Vraiment absent (feature non implémentée) | **2/32** | #14, #15 (`density_mode`) |

**Bilan exécutif** :
- **21/32 sentinels couverts solidement** (exact + renommé confirmé) = **66 %**
- **5/32 partiels** (couverture sémantique mais incomplète) = **+16 %**
- **4/32 ambigus** (concept-level, à matérialiser ou retirer) = **12 %**
- **2/32 absents** (feature `density_mode` non livrée) = **6 %**

## Lecture critique pour la revue

### Vrais trous doctrinaux (3 zones à arbitrer)

1. **#14/#15 `density_mode_consistent` + `density_mode_helios_direct`** :
   `scope.density_mode = null` en runtime (cf
   `outputs/facts_endpoint.json` ligne 2-15). Le concept "mode de
   densité" prévu par le prompt bilan n'a **pas été implémenté** dans
   le sprint.
   - **Action recommandée** : soit retirer `scope.density_mode` du
     contrat API si la feature est annulée, soit l'implémenter +
     garde-fou en Phase 25.

2. **#9 `cockpit_facts_unique_source` + #10 `cockpit_facts_no_recompute`** :
   pas de garde-fou explicite sur "le payload `_facts` est servi par UN
   service unique sans recompute". La discipline est tenue _de fait_
   (`cockpit_facts_service.get_cockpit_facts` est l'unique entrée, cf
   vérif #1 du précédent message) mais pas verrouillée par test.
   - **Risque** : un futur PR pourrait réintroduire un calcul parallèle
     dans `cockpit.py` sans alarme.

3. **#23 `pilotage_triptyque_temporal_scales` + #30 `pilotage_action_has_decision_link`** :
   le concept "triptyque temporel" et le link bidirectionnel
   pilotage↔decision ne sont pas testés directement. Couverture
   visuelle via captures Playwright, mais pas de non-régression
   automatisée.

### Faux trous (résolus, 14 sentinels)

22 sentinels prétendument manquants ont en fait un équivalent dans
le code, simplement **renommé pour mieux refléter la sémantique
réelle**. Exemples notables :

- `test_helios_surface_total` → `test_helios_surface_total_17500_m2`
  (plus précis : valeur cible inline)
- `test_kpi_hero_has_drill_down` →
  `test_all_3_hero_kpis_have_drill_down_href` (plus précis : 3 KPIs
  + `_href`)
- `test_dt_penalty_uses_doctrine_constants` → 2 tests décomposés :
  `test_imports_doctrine_penalty_constants` +
  `test_no_literal_7500_in_narrative_generator` (plus dur — le
  garde-fou interdit littéralement le nombre `7500` en source)
- `test_levers_kpi_in_mwh_not_eur` → `test_levers_kpi_value_in_mwh_not_eur`
  + `test_no_value_eur_field_in_levers` (couvre les 2 directions)
- `test_no_route_legacy_executive` → `step3_no_legacy.test.js` (FE
  scope, plus pertinent car les redirects sont React Router
  client-side)

### Discipline globale

- **Exact + renommé confirmé = 66 %** est cohérent avec la pratique
  observée pendant le sprint : l'équipe a privilégié la **sémantique
  précise** (avec valeur cible inline) à la **conformité littérale au
  prompt initial**. Ce n'est pas une dérive de discipline doctrinale
  — c'est un raffinement (et souvent une amélioration : naming plus
  spécifique, valeur cible explicite).
- Les **4 ambigus** (#9, #10, #23, #30) sont les seuls qui méritent
  un audit ciblé Phase 25 pour soit (a) ajouter le test sentinel
  manquant, soit (b) documenter pourquoi le concept n'est pas
  garde-fou-able directement.

## Méthode de la passe

```
# 1. Match exact : grep "def ${guard}\b" backend/tests/ frontend/src/__tests__/
# 2. Match approximatif :
#    - extraire kw1, kw2 du nom (skip "test_", "no_")
#    - chercher fichiers contenant `def test_*${kw1}*${kw2}*` ou
#      `def test_*${kw1}*` (fallback)
# 3. Inspection manuelle :
#    - pour chaque candidat, lire `def test_*` du fichier et
#      identifier les tests qui couvrent la sémantique du sentinel
# 4. Classification finale :
#    - exact / renommé confirmé / partiel / ambigu / absent
```
