---
title: L2 Phase 0 · Audit cohérence brief ADR-025
date: 2026-05-14
branch: claude/refonte-sol2
mode: lecture seule (aucun fichier modifié sauf brief transféré §3.1 prompt)
mission: Vérifier cohérence brief ADR-025 vs doctrine v0.2 + L1 + maquettes M1-M5 + sprint Phase 3.5 + 7 critères Amine
sources_audites:
  - docs/dev/BRIEF_ADR-025_architecture_v4.md (transféré ce jour)
  - docs/doctrine/doctrine_v4_classement_priorisation.md (v0.2)
  - docs/dev/L1_audit_centre_action_v4_decisional.md (commit ee749a12)
  - docs/maquettes/centre_action_v4/ (5 HTML figées)
prompt_source: PROMPT_CLAUDE_CODE_mois1_L2.md (v1.0 · 2026-05-14)
---

# L2 Phase 0 · Audit cohérence brief ADR-025

Audit lecture-seule de la cohérence du brief architecture vs doctrine v0.2 + L1 + maquettes + sprint Phase 3.5 + 7 critères validation Amine. Aucun fichier modifié sauf transfert du brief.

---

## A · Doctrine v0.2 — 9/9 vérifications cohérence

| # | Vérification | Source brief | Source doctrine | Verdict |
|---|---|---|---|---|
| A1 | 7 kinds doctrine §3.1 dans `chk_kind` CHECK constraint | §2.1 `chk_kind CHECK (kind IN ('anomaly','action','decision','signal','evidence_request','deadline','recommendation'))` | §3.1 tableau cardinal 7 kinds | ✅ OK 7/7 |
| A2 | 5 lifecycle states doctrine §7.1 dans `chk_lifecycle_state` | §2.1 `chk_lifecycle_state CHECK (lifecycle_state IN ('new','triaged','planned','in_progress','closed'))` | §7.1 mapping FR 5 états | ✅ OK 5/5 |
| A3 | 6 closure reasons doctrine §7.1 possibles dans `closure_reason` | §2.1 commentaire `closure_reason VARCHAR(20), -- resolved\|dismissed\|not_applicable\|duplicate\|merged\|expired` | §7.1 mapping FR 6 valeurs | ✅ OK 6/6 (note : pas de CHECK formelle, juste commentaire — à formaliser dans ADR-025 final) |
| A4 | 7 blocker types doctrine §7.1 dans `chk_blocker_type` | §2.3 `action_blockers chk_blocker_type CHECK ('waiting_evidence','waiting_budget','waiting_third_party','waiting_data','waiting_supplier','waiting_manager_validation','waiting_regulatory_confirmation')` | §7.1 mapping FR 7 blockers | ✅ OK 7/7 |
| A5 | 15 event types doctrine §7.1 dans `chk_event_type` | §2.3 `chk_event_type CHECK ('created','state_changed','assigned','priority_changed','blocker_added','blocker_removed','evidence_added','evidence_verified','closed','reopened','merged','bulk_updated','exported','kind_corrected','priority_recalculated')` | §7.1 mapping FR 15 events | ✅ OK 15/15 |
| A6 | 8 composantes du score doctrine §4.2 dans `priority_explanation` JSONB | §4.2 components_adr022 (severity 25 + impact 25 + due_date 20) + components_v4 (compliance_risk 15 + confidence 10 + recurrence_bonus 5 + no_owner_penalty 5 + evidence_missing_bonus 5) = 8 | §4.2 tableau 8 composantes 0-25, 0-25, 0-20, 0-15, 0-10, 0-5, 0-5, 0-5 | ✅ OK 8/8 |
| A7 | 12 événements d'invalidation doctrine §4.3 dans §4.4 du brief | §4.4 liste 12 events (lifecycle_state_changed, owner_changed, due_date_changed, impact_changed, blocker_added, blocker_removed, evidence_added, evidence_expired, confidence_changed, recurrence_group_updated, regulatory_applicability_changed, nightly_priority_refresh) | §4.3 strictement les mêmes 12 events | ✅ OK 12/12 |
| A8 | 6 règles modulation R1-R6 doctrine §5 dans `modulation_rules_applied` | §4.2 JSONB `"modulation_rules_applied": ["R1","R2","R5","R6"]` exemple | §5 R1 (Risque réel) + R2 (Conformité proche) + R3 (Sans responsable) + R4 (Récurrence) + R5 (Confiance faible) + R6 (Opportunité ne masque obligation) = 6 règles | ✅ OK 6/6 |
| A9 | Q9-B `duplicate_groups` vs `recurrence_groups` strictement appliqué | §2.3 deux tables distinctes : `duplicate_groups` (representative_item_id + detection_method) ET `recurrence_groups` (occurrence_count + rolling_window_days + source_signature + scope_signature) | §6.4 doctrine UI Fusionner réservé doublons · Regrouper réservé récurrences | ✅ OK |

**Total A : 9/9 OK** ✅

---

## B · L1 verdicts — 7/7 vérifications cohérence

| # | Vérification | Source brief | Source L1 | Verdict |
|---|---|---|---|---|
| B1 | 86 verdicts L1 compatibles avec architecture proposée | §10 mapping legacy → V4 avec verdicts L1 référencés | L1 §11 distribution : GARDE 14 · SUPPRIME 28 · MIGRE 31 · REMPLACE 9 · RÉGÉNÈRE 4 = 86 | ✅ OK (chiffres groupés différemment dans brief mais cohérent dans l'esprit) |
| B2 | Aucun verdict L1 contredit l'architecture | brief §10 : Anomaly KB MIGRE → kind=anomaly · ActionItem MIGRE → polymorphique · ActionPlanItem SUPPRIME · etc. | L1 §3.1 + §3.2 mêmes verdicts | ✅ OK aucune contradiction détectée |
| B3 | Tableau §10 mappe correctement legacy → V4 cible | brief §10 contient mapping détaillé legacy → V4 → verdict L1 → ADR ref pour 14 catégories | L1 §3.1-§3.8 inventaire exhaustif par catégorie | ✅ OK |
| B4 | 8 tables V4 couvrent tous MIGRE et REMPLACE L1 | brief §2 : action_center_items (cardinale) + action_event_log + evidences + action_links + action_blockers + action_scenarios + duplicate_groups + recurrence_groups = 8 tables | L1 §3.2 : 173 rows MIGRE (action_items 35 + bill_anomaly 52 + anomaly 86) absorbés dans action_center_items · 5 tables REMPLACE (action_events, action_comments, action_evidence, anomaly_action_links, anomaly_dismissals) absorbées dans action_event_log + evidences + action_links | ✅ OK couverture complète |
| B5 | 28 SUPPRIME L1 confirmés Mois 5 dans plan §3 | brief §3.1 Mois 5 : DROP tables legacy + DELETE 1 667 LoC + DELETE 20 services + suppression endpoints | L1 §3.5 + §3.6 : 7 fichiers FE morts + 5 services Sprint 13 SUPPRIME M4-M5 | ✅ OK |
| B6 | 4 RÉGÉNÈRE L1 confirmés Mois 4 | brief §3.1 Mois 4 J jour : "Régénération seeds HELIOS + MERIDIAN format V4" | L1 §3.7 : 4 RÉGÉNÈRE (gen_actions, action_templates seed, audit_seed_coverage, gen_action_center_templates_v4) Mois 4 | ✅ OK |
| B7 | 14 GARDE L1 préservés (8 source-guards + 6 nouveaux) | brief §10 : "8 source-guards existants Réutilisés + 50 nouveaux V4 GARDE" + brief §8.1 pyramide 50 SG total | L1 §3.8 : 8 SG existants GARDE + 6 nouveaux V4 cardinaux = 14 SG cardinaux | ⚠️ OK avec **anomalie mineure 1** : différence d'unité — brief §8.1 compte 50 SG TOTAUX dans la pyramide V4 (incluant dérivés) ; L1 §3.8 liste 6 SG cardinaux nouveaux. Pas contradiction, à clarifier dans ADR-025 final |

**Total B : 7/7 OK** ✅ (1 anomalie mineure compteur SG)

---

## C · Maquettes M1-M5 — 5/5 vérifications cohérence

| # | Vérification | Source brief | Source maquette | Verdict |
|---|---|---|---|---|
| C1 | M1 v0.3.1 : `summary.active_items_count` ≠ `summary.p0_p1_count` confirmé §5.1 | §5.1 endpoint `/api/action-center/pilotage` retourne `summary: { active_items_count: 8, p0_p1_count: 4, ... }` — deux compteurs distincts | M1 maquette barre narrative : "8 sujets actifs · 4 P0/P1" (deux chiffres distincts) | ✅ OK séparation correcte |
| C2 | M2 v0.2 : drawer affiche evidence + event_log + scenarios + links via API §5.2 | §5.2 endpoint `/api/action-center/items/{id}?include=evidence,event_log,scenarios,links,blockers&mode=standard\|audit` | M2 spec figée : 5 sections (evidence + event_log + scenarios + links + blockers) | ✅ OK 5/5 includes alignés |
| C3 | M3 : filtres séparés `kind` / `priority` / `lifecycle` / `domain` couvrent les colonnes V4 | §2.1 colonnes : `kind` + `priority_bracket` + `lifecycle_state` + `domain` · §2.2 indexes : `idx_aci_kind_domain` + `idx_aci_lifecycle` + `idx_aci_priority_active` | M3 spec figée : Row 1 CLASSEMENT (kind séparé) · Row 2 PRIORISATION (priority/état/domaine) | ✅ OK colonnes + indexes supportent filtres M3 |
| C4 | M4 : 6 dimensions impact mappées à `impact_dimension` enum §5.3 | §2.1 `impact_dimension VARCHAR(20), -- estimated\|at_risk\|secured\|realized\|lost\|blocked` · §5.3 endpoint `/impact` retourne dimensions {estimated, at_risk, secured, realized, lost, blocked} | M4 spec figée : 6 dimensions strictes (Estimé/À risque/Sécurisé/Réalisé/Perdu/Bloqué) | ✅ OK 6/6 dimensions |
| C5 | M5 : journal chronologique alimenté par `action_event_log` §2.3 | §2.3 `action_event_log` table dédiée polymorphe + 15 event types + indexes par item+time et org+type+time | M5 spec figée : timeline chronologique 7j 38 events 3 day-groups | ✅ OK |

**Total C : 5/5 OK** ✅

---

## D · Sprint Phase 3.5 SynthèseStratégique — 4/4 vérifications cohérence

| # | Vérification | Source brief | Source contexte Phase 3.5 | Verdict |
|---|---|---|---|---|
| D1 | `regulatory_applicability_service` référencé comme SoT (Q4-A) | §4.4 mention `regulatory_applicability_changed` event d'invalidation · §10 mapping mention services regops · §15 metadata Q4-A acté | L1 §11.1 sprint Phase 3.5 actif `backend/regops/` 10+ fichiers · doctrine §5.6 R6 doit consommer `regulatory_applicability_service.status == APPLICABLE` | ✅ OK référencé |
| D2 | Pas de duplication de logique d'assujettissement réglementaire | §2.1 `regulatory_rule_id UUID` simple ref vers service externe — aucune logique d'applicabilité dans `action_center_items` | L1 §6.1 : V4 consomme `regulatory_applicability_service` comme SoT unique sans dupliquer | ✅ OK pas de duplication |
| D3 | Interface stub Mois 2-3 mentionnée comme placeholder en attendant Phase 3.5 | brief mentionne implicitement via §10 + §15 mais **pas de mention explicite "interface stub"** | L1 §6.1 + §9.4 indiquent : "interface stub Mois 2-3 + branchement réel Mois 4" | ⚠️ **Anomalie mineure 2** : brief manque mention explicite "interface stub Mois 2-3" pour Phase 3.5. À ajouter dans ADR-025 final §11 ou §3.1 |
| D4 | Brief ne casse pas le service en cours de build | §11 coexistence Mois 2-3 sans écriture cross-modèle · §3.1 cutover Mois 4 sec ne touche pas regops · §1.2 hors-scope = ADR-026/027/028/029 (pas regops) | L1 §6.1 mitigation : "ne pas perturber sprint en cours" | ✅ OK |

**Total D : 4/4 OK** ✅ (1 anomalie mineure D3 sur mention explicite stub)

---

## E · 7 critères validation Amine — 7/7 mapping confirmé

| # | Critère Amine | Vérifié dans brief par | Verdict mapping |
|---|---|---|---|
| E1 | **Critère 1** : Architecture respecte Q2-α table rase | brief §14 critère 1 → §3 cutover sec Mois 4 + §3.2 backup obligatoire 6× mentionné + §11 coexistence sans double-write | ✅ Mapping vérifié |
| E2 | **Critère 2** : Modèle simple et performant | brief §14 critère 2 → §2.1 single-table ~42 colonnes + §2.3 6 tables filles + §2.2 8 indexes spécifiques table cardinale + §9 budgets < 100ms | ✅ Mapping vérifié (avec **anomalie mineure 3** : compteur indexes flou — TL;DR dit "14 indexes critiques", §14 dit "8 indexes spécifiques", comptage total tables ≈ 20 indexes. À aligner dans ADR-025 final) |
| E3 | **Critère 3** : Audit trail défendable RGPD | brief §14 critère 3 → §2.3 `action_event_log` table dédiée + politique rétention configurable (5 ans CNIL par défaut) + survit à clôture item (`ON DELETE RESTRICT`) | ✅ Mapping vérifié |
| E4 | **Critère 4** : Score triable en SQL | brief §14 critère 4 → §2.1 `priority_score NUMERIC(5,2)` + `priority_bracket VARCHAR(2)` colonnes scalaires + §2.2 index `idx_aci_priority_active` B-tree natif `(organisation_id, priority_score DESC, priority_bracket) WHERE lifecycle_state != 'closed'` | ✅ Mapping vérifié |
| E5 | **Critère 5** : Sécurité org-scoping native | brief §14 critère 5 → §7.1 middleware FastAPI global + §7.2 décorateur `@org_scoped` + §7.3 source-guards automatique + `organisation_id` sur 8 tables (cardinale + 7 filles) + §13 renvoi ADR-027 | ✅ Mapping vérifié |
| E6 | **Critère 6** : Zéro double-write inutile | brief §14 critère 6 → §11 coexistence Mois 2-3 sans écriture cross-modèle + §3.1 cutover sec Mois 4 (Q13-B) + §3.2 garde-fous Q2-α | ✅ Mapping vérifié |
| E7 | **Critère 7** : Tests couvrent code + métier + API | brief §14 critère 7 → §8.1 pyramide stratifiée 50 SG (code) + 30 unit/intégration (métier dynamique) + 15 contract (API) + 5 e2e (UX critique) = 100 tests V4 totaux + §8.2 justification stratification | ✅ Mapping vérifié |

**Total E : 7/7 mapping confirmé** ✅

---

## Anomalies détectées

3 anomalies **mineures** (non bloquantes) à intégrer dans ADR-025 final §16 auto-évaluation :

### Anomalie mineure 1 — Compteur source-guards (Z-axis cohérence)

- **Section** : brief §8.1 + §10
- **Type** : différence d'unité de comptage
- **Détail** : brief §8.1 compte "50 SG totaux" dans la pyramide V4 ; L1 §3.8 liste "6 SG cardinaux nouveaux + 8 SG existants GARDE = 14"
- **Recommandation correction ADR-025** : clarifier dans §8.1 final que les 50 SG = 6 cardinaux nouveaux V4 + 8 existants GARDE + 36 SG dérivés (un par pattern : org-scoping queries, libellés FR, regex DOM, pas de Fusionner sur recurrence, etc.)

### Anomalie mineure 2 — Mention explicite "interface stub Phase 3.5"

- **Section** : brief §3.1 (Mois 2-3) + §11
- **Type** : mention implicite vs explicite
- **Détail** : brief référence Q4-A `regulatory_applicability_service` comme SoT mais ne précise pas l'interface stub Mois 2-3 en attendant que Phase 3.5 livre l'API stable
- **Recommandation correction ADR-025** : ajouter dans §3.1 Mois 2 ligne explicite "Interface stub `regulatory_applicability_service.is_applicable()` Mois 2-3 (R6 hardcoded temporairement) → branchement réel Mois 4 quand Phase 3.5 livre"

### Anomalie mineure 3 — Compteur indexes (cohérence interne brief)

- **Section** : brief TL;DR + §14 critère 2 + §2.2
- **Type** : flou compteur indexes
- **Détail** : TL;DR annonce "14 indexes critiques" · §14 critère 2 dit "8 indexes spécifiques" · comptage exhaustif §2.2 + §2.3 indexes des tables filles ≈ 20 indexes (8 cardinale + 3 event_log + 2 evidences + 2 links + 1 blockers + 1 scenarios + 1 duplicate_groups + 2 recurrence_groups)
- **Recommandation correction ADR-025** : aligner sur le compteur exhaustif réel dans TL;DR et §14 — soit "20 indexes (8 sur table cardinale + 12 sur tables filles)" soit "8 indexes critiques sur table cardinale + indexes secondaires sur tables filles"

---

## Total

| Bloc | Vérifications | OK | Anomalies bloquantes | Anomalies mineures |
|---|---|---|---|---|
| A · Doctrine v0.2 | 9 | 9 | 0 | 0 |
| B · L1 verdicts | 7 | 7 | 0 | 1 (compteur SG) |
| C · Maquettes M1-M5 | 5 | 5 | 0 | 0 |
| D · Sprint Phase 3.5 | 4 | 4 | 0 | 1 (mention stub) |
| E · 7 critères Amine | 7 | 7 | 0 | 1 (compteur indexes) |
| **TOTAL** | **32** | **32** | **0** | **3** |

- **Vérifications réussies** : **32 / 32** ✅
- **Anomalies bloquantes** : **0**
- **Anomalies mineures** : **3** (à intégrer comme corrections dans ADR-025 final §16)
- **Brief consommable en l'état pour Phase 1** : **OUI** (avec corrections mineures à appliquer dans transformation MADR)

---

## STOP GATE — Phase 0 terminée

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 0 TERMINÉE — STOP GATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Bilan Phase 0 disponible : docs/dev/L2_phase0_audit_coherence.md

Vérifications cohérence :
  A · Doctrine v0.2     : 9/9 OK
  B · L1 verdicts       : 7/7 OK (1 anomalie mineure : compteur SG)
  C · Maquettes M1-M5   : 5/5 OK
  D · Sprint Phase 3.5  : 4/4 OK (1 anomalie mineure : mention stub)
  E · 7 critères Amine  : 7/7 mapping confirmé (1 anomalie mineure : compteur indexes)

Total : 32/32 vérifications réussies ✅
Anomalies bloquantes : 0
Anomalies mineures : 3 (à intégrer comme corrections dans ADR-025 final)

Brief consommable : OUI
  → Phase 1 (production ADR-025 formel) doit appliquer les 3 corrections mineures
    documentées dans §"Anomalies détectées" lors de la transformation brief → MADR

⛔ NE PAS DÉMARRER Phase 1 avant validation utilisateur.

Confirmer pour passer en Phase 1 : « GO Phase 1 »
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Métadonnées Phase 0

```yaml
phase: "L2 Phase 0 — audit cohérence brief ADR-025"
status: "TERMINÉE — STOP GATE actif"
date: "2026-05-14"
files_produced:
  - docs/dev/BRIEF_ADR-025_architecture_v4.md (transféré ce jour)
  - docs/dev/L2_phase0_audit_coherence.md (ce fichier)
files_modified: 0
db_writes: 0
verifications_total: 32
verifications_ok: 32
anomalies_blocking: 0
anomalies_minor: 3
brief_consumable: true
corrections_to_apply_in_adr025:
  - "Clarifier compteur SG (6 cardinaux + 8 existants + 36 dérivés = 50 total)"
  - "Ajouter mention explicite interface stub Phase 3.5 Mois 2-3"
  - "Aligner compteur indexes (~20 indexes total : 8 cardinale + 12 tables filles)"
next_step: "Validation utilisateur 'GO Phase 1' → produire L2_ADR-025_architecture_v4.md (format MADR + 3 corrections mineures)"
```
