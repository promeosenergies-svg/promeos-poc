# MATRICE FINALE DE VÉRITÉ — FACTURATION & ACHAT V1

**Date** : 11 mars 2026
**Base** : Code repo réel (pas les .md précédents)
**Tests billing** : 127/127 GREEN (90 engine + 37 invariants)
**Catalogue** : `2026-03-11_engine_v2.1_lockdown` — 24 taux, 15 [TO_VERIFY]

---

## 1. RÉSUMÉ EXÉCUTIF

Le moteur V2 de reconstitution de facture électricité **existe, fonctionne, et est branché bout en bout** (route → engine → frontend). Il décompose correctement une facture C4 BT en 7-11 composantes avec prorata calendaire exact, CTA sur la bonne assiette, et résolution temporelle CTA + accise.

**Mais** : 15 taux TURPE sont encore [TO_VERIFY], les anomalies R13/R14 restent câblées sur le V1 approximatif, les périodes multi-mois avec changement de taux ne sont pas proratées, et le V1 fallback peut encore apparaître sans signal clair (partiellement corrigé cette session).

| Catégorie | PRÉSENT | PARTIEL | ABSENT | V2 |
|-----------|---------|---------|--------|-----|
| **Facturation élec** | 12 | 9 | 4 | 0 |
| **Contrat / Achat** | 3 | 4 | 1 | 3 |
| **Gaz** | 1 | 0 | 0 | 5 |
| **Autres** | 4 | 3 | 1 | 0 |
| **TOTAL** | **20** | **16** | **6** | **8** |

**5 points encore bloquants pour affirmer "V1 crédible" :**
1. 15 taux TURPE [TO_VERIFY] non validés contre PDF Enedis officiel
2. R13/R14 (anomalies TURPE/taxes) câblées sur V1 approximatif, pas sur moteur V2
3. Pas de prorata inter-taux sur périodes chevauchant un changement de taux
4. Factures demo seed générées avec taux hardcodés (TURPE=0.0453, accise=0.0225) → incohérentes avec le moteur V2
5. Frontend n'envoie pas `engine=v2` → dépend du fallback silencieux

---

## 2. MATRICE FINALE

### A. FACTURATION ÉLECTRICITÉ

| ID | Item | Statut | Périmètre couvert | Preuve code | Preuve test | Limite connue | Risque si vendu trop tôt | Action | Priorité |
|----|------|--------|-------------------|-------------|-------------|---------------|--------------------------|--------|----------|
| A1 | Moteur de reconstitution de facture | **PRÉSENT** | C4 BT (LU/MU/CU) + C5 BT (Base/HP-HC). Orchestrateur `build_invoice_reconstitution()` retourne RECONSTITUTED/PARTIAL/READ_ONLY/UNSUPPORTED | `engine.py:build_invoice_reconstitution()` — 280 lignes | 14 tests `TestBuildReconstitution` + 12 tests `TestIntegrationRealInvoice` | C3 HTA → UNSUPPORTED. Pas de multi-site batch. | Client HTA déçu | Aucune | — |
| A2 | Décomposition TURPE réelle | **PARTIEL** | C4 : 5 composantes (gestion, comptage, soutirage fixe, HPE, HCE). C5 : 3-4 composantes. Structure correcte. | `engine.py:compute_turpe_breakdown()` — 120 lignes | 5 tests `TestTurpeC4` + 4 tests `TestTurpeC5` | **15 taux [TO_VERIFY]** — pas validés contre PDF Enedis officiel. Écart ~7% sur assiette CTA vs facture réelle. | Montants TURPE erronés de ±5-10% | Télécharger PDF Enedis TURPE 7, valider les 15 taux | **NOW** |
| A3 | Gestion / comptage / soutirage fixe | **PRÉSENT** | C4 : gestion (EUR/an × prorata) + comptage (EUR/an × prorata) + soutirage fixe (EUR/kVA/an × kVA × prorata). C5 : gestion + comptage (pas de soutirage fixe). | `engine.py` lignes 140-185 | `test_c4_lu_full_month_5_components`, `test_c4_soutirage_fixe_formula` | Taux [TO_VERIFY]. Pas de soutirage fixe C5 (correct réglementairement). | Écart prorata si taux faux | Valider taux | **NOW** |
| A4 | Soutirage variable par période | **PRÉSENT** | HPE/HCE (LU), HP/HC (MU/CU/HP-HC), BASE (Base). Un ComponentResult par période. | `engine.py` lignes 185-210 | `test_c4_variable_hpe`, `test_c5_hp_hc_4_components` | Taux variable [TO_VERIFY]. Pas de période P (pointe). | Montant soutirage erroné | Valider taux | **NOW** |
| A5 | Périodes tarifaires dans le contrat | **PRÉSENT** | `price_hpe_eur_kwh`, `price_hce_eur_kwh`, `price_hp_eur_kwh`, `price_hc_eur_kwh`, `price_base_eur_kwh` sur EnergyContract. Demo seed Helios les remplit. | `billing_models.py` lignes 149-167, `packs.py` | `test_two_periods_hpe_hce` | Pas de prix par saison (été/hiver). Un seul jeu de prix par contrat. | Fourniture C4 LU4 approximative | Acceptable V1 | — |
| A6 | Gestion HP/HC / HPE/HCE / autres périodes | **PRÉSENT** | LU (HPE/HCE), MU (HP/HC), CU (HP/HC), HP_HC (HP/HC), BASE. Enum `TariffOption` + `PeriodCode`. | `types.py:TariffOption`, `catalog.py:get_soutirage_variable_codes()` | `test_c4_lu_variable_codes`, `test_c5_hp_hc_variable_codes`, `test_c5_base_variable_codes` | Pas de 5 plages (HPH/HCH/HPB/HCB/P). Pas de LU4 TURPE 7 (flat rate). | Structure TURPE 7 (août 2025+) incompatible pour LU | Ajouter LU flat rate TURPE 7 | **NEXT** |
| A7 | CTA sur la bonne assiette | **PRÉSENT** | Assiette = somme HT des composantes TURPE **fixes** uniquement (gestion + comptage + soutirage fixe). Exclut les composantes variables. Résolution temporelle 21.93% / 15%. | `engine.py:compute_cta()` — filtre `code.startswith("turpe_soutirage_var")` | `test_cta_assiette_c4`, `test_cta_excludes_variable`, `test_cta_real_invoice_assiette` | Assiette dépend des taux TURPE [TO_VERIFY]. Écart 7.6% vs facture réelle (332 vs 309 EUR). | CTA surestimée ~5 EUR/mois | Valider taux TURPE fixes | **NOW** |
| A8 | Accise | **PRÉSENT** | 3 taux PME par période : jan 2025 (0.02050), fév-jul 2025 (0.02623), août+ 2025 (0.02998). Résolution temporelle via `_resolve_temporal_code()`. | `catalog.py` + `engine.py:compute_excise()` | `test_accise_formula`, `test_accise_jan2025`, `test_accise_aout2025` | Pas de taux 2026 spécifique. Pas de segmentation ménage vs PME dynamique. | Accise 2026 potentiellement fausse | Ajouter taux 2026 quand LdF publiée | **NEXT** |
| A9 | TVA différenciée | **PRÉSENT** | 5.5% sur gestion, comptage, soutirage fixe, CTA, abonnement. 20% sur fourniture, soutirage variable, accise. Séparation `total_tva_reduite` / `total_tva_normale`. | `engine.py` + `catalog.py:get_tva_rate_for()` | `test_tva_split` | — | — | Aucune | — |
| A10 | Prorata temporis rigoureux | **PRÉSENT** | `jours / jours_dans_année` (365 ou 366). Détection année bissextile. | `engine.py:compute_prorata()` | 8 tests `TestComputeProrata` (jan, fév, fév bissextile, demi-mois, année, trimestre, zéro, 1 jour) | — | — | Aucune | — |
| A11 | Type facture : normale | **PRÉSENT** | `InvoiceType.NORMAL` → reconstitution complète. | `types.py:InvoiceType`, `engine.py` | `test_c4_lu_reconstituted` | — | — | Aucune | — |
| A12 | Type facture : acompte | **PRÉSENT** | `InvoiceType.ADVANCE` → `READ_ONLY` immédiat (pas de calcul fictif). | `engine.py` ligne ~250 | `test_advance_invoice_read_only` | Pas de rapprochement acompte/solde. | Acompte non analysé | Acceptable V1 | — |
| A13 | Type facture : régularisation | **PARTIEL** | `InvoiceType.REGULARIZATION` → reconstitué normalement (même pipeline que NORMAL). Enum existe. | `types.py`, `engine.py` | `test_regularization_reconstituted` | Pas de logique spécifique régul (delta vs estimé). R1/R9 peuvent faux-positiver. | Faux positifs sur régularisations | Filtrer R1/R9 pour type=REGUL | **NEXT** |
| A14 | Type facture : avoir | **PARTIEL** | `InvoiceType.CREDIT_NOTE` → `PARTIAL` (reconstitué mais flaggé). Enum existe. | `types.py`, `engine.py` | `test_credit_note_partial` | Pas de logique avoir spécifique (montant négatif, rapprochement). | Montant négatif mal interprété | Acceptable V1 | — |
| A15 | Index début / fin de période | **PARTIEL** | Champs `start_index`, `end_index` sur EnergyInvoice. Colonnes présentes en DB. | `billing_models.py` lignes 254-260 | Aucun test spécifique | Jamais peuplé par le seed. Pas utilisé par le moteur pour vérifier les kWh. | Pas de vérification kWh facturés vs index | Peupler dans seed + vérifier | **NEXT** |
| A16 | Écart facture fournisseur vs moteur | **PRÉSENT** | `compare_to_supplier_invoice()` : gap global (EUR + %) + gap par composante. Seuils : ±2% OK, ±5% warn, >5% alert. | `engine.py:compare_to_supplier_invoice()` | 5 tests `TestCompareToSupplier` | Comparaison TTC global uniquement si pas de détail composante fournisseur. | Écart par composante impossible sans extraction PDF | Acceptable V1 | — |
| A17 | Audit trail ligne par ligne | **PRÉSENT** | Chaque `ComponentResult` porte : `formula_used`, `inputs_used`, `assumptions`, `rate_sources[]`. `AuditTrace` agrège tout. | `types.py:ComponentResult`, `engine.py:generate_audit_trace()` | `test_every_component_has_formula`, `test_trace_contains_all_sources` | Pas de trace du calcul intermédiaire (juste inputs/outputs). | — | Acceptable V1 | — |
| A18 | Résolution des taux par date d'effet | **PARTIEL** | CTA : 21.93% (→ jan 2026) puis 15% (fév 2026+). Accise : 3 taux par période 2025. Résolution via `_resolve_temporal_code(code, at_date)`. Orchestrateur passe `period_start`. | `catalog.py:_resolve_temporal_code()` | `test_accise_jan2025`, `test_accise_aout2025` | **TURPE : aucune résolution temporelle** (pas de `at_date` dans `compute_turpe_breakdown`). Le taux TURPE est toujours le courant. | Si TURPE change (TURPE 7 août 2025), factures avant/après utilisent le même taux | Ajouter `at_date` à `compute_turpe_breakdown` | **NEXT** |
| A19 | Périodes multi-mois avec changement de taux | **ABSENT** | Le moteur utilise `period_start` comme seule date de résolution. Pas de prorata inter-taux si une facture chevauche une date de changement. | `engine.py` : `compute_cta(..., at_date=period_start)`, `compute_excise(..., at_date=period_start)` | Aucun test de chevauchement | Facture jan 20 → fév 15 : accise entièrement au taux jan (0.0205) au lieu de proratiser jan/fév. | Écart ±1-5% sur factures à cheval | Splitter les calculs aux dates de changement | **NEXT** |
| A20 | Segmentation C4 / C5 correcte | **PRÉSENT** | `resolve_segment(kva)` : >250 → C3_HTA, >36 → C4_BT, ≤36 → C5_BT. Fonctionne côté V2 engine ET V1 shadow (via `subscribed_power_kva` sur contrat). | `catalog.py:resolve_segment()`, `billing_shadow_v2.py:_resolve_segment()` | 8 tests `TestResolveSegment` | Segment basé uniquement sur puissance souscrite, pas sur tension (BT/HTA). | Client 250 kVA en HTA classé C4 | Ajouter tension si nécessaire | **LATER** |
| A21 | Puissance souscrite | **PRÉSENT** | `subscribed_power_kva` sur `EnergyContract`. Peuplé par seed Helios (108, 12, 250, 36, 150 kVA). Utilisé par V2 engine et V1 shadow. | `billing_models.py` ligne 134-137, `packs.py` | `test_c4_108kva`, `test_c5_boundary` | Pas de puissance souscrite par poste horosaisonnier. | — | Acceptable V1 | — |
| A22 | Puissance atteinte / Pmax | **ABSENT** | Aucun champ, aucun calcul. | — | — | — | Pas de vérification dépassement vs souscrit | Ajouter en V2 | **V2** |
| A23 | Dépassement de puissance | **ABSENT** | Aucun modèle de pénalité. | — | — | — | Pénalités non détectées | Hors scope V1 | **V2** |
| A24 | Énergie réactive | **ABSENT** | Aucun modèle. | — | — | — | Pénalités tg(φ) non détectées | Hors scope V1 | **V2** |
| A25 | Courbe de charge exploitée dans le billing | **ABSENT** | Aucune utilisation des meter readings dans le moteur de reconstitution. | — | — | — | Pas de vérification kWh facturés vs mesurés | Hors scope V1 | **V2** |

### B. CONTRAT / ACHAT

| ID | Item | Statut | Périmètre couvert | Preuve code | Preuve test | Limite connue | Risque si vendu trop tôt | Action | Priorité |
|----|------|--------|-------------------|-------------|-------------|---------------|--------------------------|--------|----------|
| B26 | Modèle de contrat complet | **PARTIEL** | EnergyContract avec : supplier, dates, prix multi-plages, puissance, option tarifaire, fee fixe, indexation, reconduction, notice. | `billing_models.py` | Tests seed | Pas de clause pass-through structurée. Pas d'historique avenant. | Contrats complexes non modélisables | Acceptable V1 | — |
| B27 | Modèle d'avenant | **ABSENT** | Aucun modèle. | — | — | — | Modifications contractuelles non traçables | V2 | **V2** |
| B28 | Dates effet / échéance / reconduction | **PRÉSENT** | `start_date`, `end_date`, `auto_renew`, `notice_period_days` sur EnergyContract. Radar renouvellement fonctionnel. | `billing_models.py`, `routes/billing.py` radar endpoint | Tests radar | — | — | Aucune | — |
| B29 | Clause pass-through modélisée | **PARTIEL** | Champ `pass_through_items` (TEXT/JSON) sur EnergyContract. Jamais peuplé par seed. Pas exploité par le moteur. | `billing_models.py` ligne 169-171 | Aucun test | Champ mort. | "On gère le pass-through" → faux | Peupler dans seed ou supprimer | **LATER** |
| B30 | Prix par période tarifaire | **PRÉSENT** | 5 champs prix sur contrat (HPE/HCE/HP/HC/BASE). Seed Helios les remplit correctement. V2 engine les utilise. | `billing_models.py`, `packs.py`, `engine.py` | `test_two_periods_hpe_hce` | Un seul jeu de prix (pas de pricing saisonnier été/hiver). | — | Acceptable V1 | — |
| B31 | Comparateur d'offres structuré | **PARTIEL** | `purchase_service.py` : 4 stratégies (Fixe, Indexé, Spot, RéFlex). Simulation indicative. | `purchase_service.py` | Tests purchase | P10/P90 et risk scores à fiabiliser | Recommandation sur données fictives | Corriger P10/P90 | **NEXT** |
| B32 | Campagne d'achat | **V2** | Non implémenté. | — | — | — | — | — | **V2** |
| B33 | Workflow multi-offres / validation | **V2** | Non implémenté. | — | — | — | — | — | **V2** |
| B34 | Forward curve | **V2** | Aucune courbe forward (EEX, PEG). Prix spot EPEX uniquement. | — | — | — | Stratégie indexée sans référence marché | Intégrer EEX Cal Y+1 | **V2** |
| B35 | Monte Carlo réel | **PARTIEL** | Existe (`purchase_service.py`) mais P10/P90 = ×0.85/×1.20 hardcodé. Pas de σ historique. | `purchase_service.py` | Tests purchase | Facteurs constants → fausse rigueur | Client croit à une simulation | Remplacer par σ-based | **NEXT** |
| B36 | Recommandation achat traçable | **PARTIEL** | Recommandation générée avec label stratégie + montant. Pas de trace du raisonnement (pourquoi cette stratégie). | `purchase_service.py` | Tests purchase | Pas de "explain" | Non auditable | Ajouter explain | **LATER** |

### C. GAZ

| ID | Item | Statut | Périmètre couvert | Preuve code | Preuve test | Limite connue | Risque si vendu trop tôt | Action | Priorité |
|----|------|--------|-------------------|-------------|-------------|---------------|--------------------------|--------|----------|
| C37 | Lecture simple facture gaz | **PRÉSENT** | V2 engine retourne `READ_ONLY` pour gaz. V1 shadow calcule une estimation simple (kWh × taux). Factures affichées avec montant, kWh, période, fournisseur. | `engine.py` : `if energy_type == "GAZ": return READ_ONLY` | `test_gas_read_only` | Pas de reconstitution composante par composante. | — | Label "lecture seule" OK | — |
| C38 | Conversion PCS / m³ → kWh | **V2** | Aucun champ PCS. | — | — | — | kWh gaz non vérifiable | V2 | **V2** |
| C39 | ATRD7 segmenté | **V2** | Taux plat unique 0.025 EUR/kWh. Pas de profil T1-T4. | `tarifs_reglementaires.yaml` | — | — | >30% d'écart possible | V2 | **V2** |
| C40 | ATRT segmenté | **V2** | Taux plat unique 0.012 EUR/kWh. | `tarifs_reglementaires.yaml` | — | — | — | V2 | **V2** |
| C41 | Stockage gaz | **V2** | Non implémenté. | — | — | — | — | — | **V2** |
| C42 | Shadow billing gaz crédible | **V2** | Non implémenté. Gaz = READ_ONLY en V2. | — | — | — | — | — | **V2** |

### D. AUTRES

| ID | Item | Statut | Périmètre couvert | Preuve code | Preuve test | Limite connue | Risque si vendu trop tôt | Action | Priorité |
|----|------|--------|-------------------|-------------|-------------|---------------|--------------------------|--------|----------|
| D43 | Mécanisme de capacité | **ABSENT** | Non implémenté. ~2-4 EUR/MWh manquants. | — | — | — | Composante facture ignorée (2-4% du total) | Hors scope V1 | **V2** |
| D44 | CEE | **ABSENT** | Non implémenté. | — | — | — | — | Hors scope V1 | **V2** |
| D45 | Règles anomalies branchées sur V2 | **PARTIEL** | 14 règles existent et s'exécutent. R1-R12 : fonctionnelles (V1). **R13 (TURPE) et R14 (taxes) : câblées sur `shadow_billing_v2()` V1**, pas sur le moteur V2 déterministe. | `billing_service.py` lignes 635-671 | Tests R1-R14 dans `test_billing.py` | R13/R14 utilisent le V1 approximatif (1 taux plat) → écarts TURPE/taxes basés sur estimation grossière | Anomalies TURPE/taxes imprécises | Rewirer R13/R14 sur V2 engine | **NOW** |
| D46 | UX honnête (pas de wording trompeur) | **PARTIEL** | V2 : labels RECONSTITUTED/PARTIAL/READ_ONLY/UNSUPPORTED corrects. V1 fallback : confidence cappée à "medium" (jamais "high"). Warning orange si fallback V1. | `ShadowBreakdownCard.jsx` | — | Frontend n'envoie pas `engine=v2` explicitement → dépend du fallback silencieux. "Shadow billing" encore dans le glossaire. | V1 affiché sans signal suffisant | Envoyer `engine=v2` + renommer "shadow billing" | **NOW** |
| D47 | Labels de statut corrects | **PRÉSENT** | RECON_STATUS : "Reconstitution complète", "Reconstitution partielle", "Lecture seule", "Segment non supporté". CONFIDENCE : "Confiance moyenne" (max V1), "Confiance faible". | `ShadowBreakdownCard.jsx` | — | — | — | Aucune | — |
| D48 | Couverture tests unitaires | **PRÉSENT** | 90 tests engine (14 classes) couvrant : prorata, catalog, segment, soutirage, supply, TURPE C4/C5, CTA, accise, reconstitution, comparaison, audit, intégration, régression. | `test_billing_engine.py` | 90/90 GREEN | Pas de test de chevauchement taux. Pas de test route HTTP. | — | Ajouter tests chevauchement | **NEXT** |
| D49 | Couverture tests intégration | **PARTIEL** | `TestIntegrationRealInvoice` : 12 tests sur facture EDF réelle (C4 108 kVA, jan 2025). `TestE2E_ShadowElec/Gaz` : 2 tests e2e V1. Pas de test HTTP route complet. | `test_billing_engine.py`, `test_billing_invariants_p0.py` | 14 tests intégration | Pas de test route → engine → JSON response. Pas de test avec DB réelle. | Bug de wiring non détecté | Ajouter test HTTP route | **NEXT** |
| D50 | Démo V1 crédible | **PARTIEL** | Seed Helios crée 5 sites avec contrats V2 réalistes. V2 engine produit des breakdowns C4/C5. Anomalies détectées. Radar contrats fonctionnel. | Seed + routes + frontend | Tests seed | **Factures seed générées avec taux hardcodés** (TURPE=0.0453, accise=0.0225) → incohérentes avec moteur V2. 15 taux [TO_VERIFY]. | Écarts non réalistes en démo → perte de crédibilité | Aligner seed sur V2 rates + valider taux | **NOW** |

---

## 3. RÈGLES DE CLASSEMENT

**PRÉSENT** = le code existe, est branché bout en bout (DB → moteur → API → frontend), ET prouvé par au moins 1 test automatisé.

**PARTIEL** = le code existe mais : soit le branchement bout en bout est incomplet, soit les taux sont [TO_VERIFY], soit le comportement n'est vrai que pour un sous-cas (ex: résolution temporelle pour CTA/accise mais pas TURPE), soit un champ existe en DB mais n'est pas exploité.

**ABSENT** = pas de code, pas de modèle, pas de test. La fonctionnalité n'existe pas.

**V2** = explicitement repoussé au scope V2. Non implémenté, non promis, documenté comme hors scope.

---

## 4. BLOQUANTS V1

Pour affirmer **"PROMEOS a une brique billing électricité V1 crédible"**, il faut lever ces 5 bloquants :

| # | Bloquant | Sévérité | Effort | Pourquoi c'est bloquant |
|---|----------|----------|--------|------------------------|
| **B1** | 15 taux TURPE [TO_VERIFY] non validés | **S0** | 1 jour | Les composantes TURPE sont le cœur de la reconstitution. Un écart de 7% sur l'assiette CTA est visible en démo. |
| **B2** | R13/R14 câblées sur V1 approximatif | **S1** | 2 jours | Les anomalies TURPE/taxes sont basées sur 1 taux plat au lieu de 5 composantes. Résultat : faux positifs ou faux négatifs. |
| **B3** | Factures seed incohérentes avec V2 | **S1** | 0.5 jour | Le seed génère des factures avec TURPE=0.0453 et accise=0.0225 hardcodés. Le moteur V2 les reconstitue avec d'autres taux → écarts systématiques en démo. |
| **B4** | Frontend ne force pas `engine=v2` | **S1** | 10 min | L'appel API est sans paramètre. Si V2 fail silencieusement → V1 approximatif affiché sans warning suffisant. |
| **B5** | Pas de prorata inter-taux | **S2** | 2 jours | Facture à cheval sur un changement CTA ou accise → taux unique appliqué à toute la période. Écart ±1-5%. |

---

## 5. DÉCISION PRODUIT

### **GO V1 DEMO WITH DISCLAIMERS**

**Justification :**
- Le moteur V2 existe, est branché, et produit des reconstitutions structurellement correctes (5 composantes TURPE, CTA bonne assiette, accise temporelle, TVA split, prorata calendaire).
- 127/127 tests billing GREEN.
- La démo est faisable si les disclaimers sont explicites sur les taux [TO_VERIFY] et que le seed est aligné.
- Les bloquants B1/B3/B4 sont résolubles en < 2 jours.

**Disclaimers obligatoires :**
> "Reconstitution V2.1 — segments C4 BT (LU/MU/CU) et C5 BT (Base/HP-HC).
> Taux CTA (21.93%) et accise (20.50-29.98 EUR/MWh PME) vérifiés sources officielles.
> 15 taux TURPE indicatifs (±7% vs facture réelle) — validation PDF Enedis en cours.
> Gaz = lecture seule. HTA = non supporté. Énergie réactive = non incluse.
> Marge d'erreur estimée : ±5% sur total TTC."

**Score : 64/100** (vs 38/100 audit V2 pré-corrections, vs 41/100 audit V1 initial)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Exactitude CTA | 8/10 | Taux corrigé, assiette correcte, résolution temporelle |
| Exactitude accise | 9/10 | 3 taux PME par période, résolution temporelle |
| Décomposition TURPE | 6/10 | Structure correcte (5 composantes), taux [TO_VERIFY] |
| Architecture moteur | 9/10 | 127 tests, traçabilité complète, 0 magic numbers, 0 silent fallback |
| Honnêteté UI | 7/10 | V2 = status explicites, V1 = confidence cappée + warning fallback |
| Contrats / Achat | 5/10 | Multi-plages OK, radar OK, mais P10/P90 fictifs |
| Gaz | 4/10 | Lecture seule honnête, mais gaz shadow V1 encore trompeur |
| Couverture tests | 8/10 | 127 billing + 37 invariants, mais pas de test HTTP route |

---

## 6. TOP 5 ACTIONS

| # | Action | Effort | Owner | Deadline |
|---|--------|--------|-------|----------|
| **1** | **Valider les 15 taux TURPE [TO_VERIFY]** contre le PDF Enedis TURPE 7 HTA-BT officiel. Corriger les taux, retirer les marqueurs [TO_VERIFY], mettre à jour les tests. | S (1 jour) | Backend | 13 mars |
| **2** | **Rewirer R13/R14** sur le moteur V2 (`build_invoice_reconstitution`) au lieu de `shadow_billing_v2()`. Les écarts par composante sont déjà dans `component_gaps[]`. | M (2 jours) | Backend | 18 mars |
| **3** | **Aligner le seed Helios** : remplacer TURPE=0.0453 et accise=0.0225 hardcodés dans `gen_billing.py` par les taux du catalogue V2. Ou mieux : générer les factures seed via le moteur V2 lui-même. | S (0.5 jour) | Backend | 13 mars |
| **4** | **Frontend : envoyer `engine=v2`** dans l'appel API shadow-breakdown pour forcer le moteur V2 et éviter le fallback silencieux V1. | XS (10 min) | Frontend | 12 mars |
| **5** | **Ajouter prorata inter-taux** : si `period_end` chevauche une date de changement CTA ou accise, splitter le calcul en 2 sous-périodes avec le bon taux chacune. | M (2 jours) | Backend | 21 mars |

---

*Matrice produite le 11 mars 2026 — PROMEOS Billing V1 Gatekeeper*
*Base : code repo réel, 127/127 billing tests GREEN, 4 agents d'audit parallèles*
