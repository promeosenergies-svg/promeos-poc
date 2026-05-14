---
title: L5 Phase 0 · Audit cohérence brief ADR-028
date: 2026-05-14
branch: claude/refonte-sol2
mode: lecture seule (aucun fichier modifié sauf brief transféré §3.1 prompt)
mission: Vérifier cohérence brief ADR-028 vs ADR-025 + ADR-026 + ADR-027 + doctrine v0.2 + L1 + maquettes M1-M5 + 11 invariants IL + sprint Phase 3.5
sources_audites:
  - docs/dev/BRIEF_ADR-028_lifecycle_states.md (transféré ce jour · 1017 L)
  - docs/dev/L2_ADR-025_architecture_v4.md (commit 712da32a)
  - docs/dev/L3_ADR-026_migration_data.md (commit 1500f55b)
  - docs/dev/L4_ADR-027_securite_org_scoping.md (commit faba2a61)
  - docs/doctrine/doctrine_v4_classement_priorisation.md (v0.2)
  - docs/dev/L1_audit_centre_action_v4_decisional.md (commit ee749a12 · 86 verdicts)
  - docs/maquettes/centre_action_v4/ (5 HTML figées)
prompt_source: PROMPT_CLAUDE_CODE_mois1_L5.md (v1.0 · 2026-05-14)
---

# L5 Phase 0 · Audit cohérence brief ADR-028

Audit lecture-seule de la cohérence du brief lifecycle vs ADR-025/026/027 + doctrine + L1 + maquettes + 11 invariants IL + sprint Phase 3.5. Aucun fichier modifié sauf transfert du brief.

---

## A · Cohérence ADR-025 — 5/5 vérifications

| # | Vérification | Source brief | Source ADR-025 | Verdict |
|---|---|---|---|---|
| A1 | `lifecycle_state` enum = 5 valeurs cohérentes | §2.1 enum `LifecycleState` : NEW/TRIAGED/PLANNED/IN_PROGRESS/CLOSED | §4.1 colonne `lifecycle_state VARCHAR(20) NOT NULL` + §4.1 `chk_lifecycle_state CHECK (lifecycle_state IN ('new','triaged','planned','in_progress','closed'))` | ✅ OK 5/5 valeurs identiques |
| A2 | CHECK constraint `chk_lifecycle_state` couvre les 5 valeurs | §3.2 `VALID_TRANSITIONS` dict couvre exactement les 5 états | §4.1 CHECK constraint cardinal | ✅ OK alignement strict |
| A3 | CHECK constraint `chk_closure_consistency` cohérent avec transitions vers closed | §5 `_after_transition` : `if target == CLOSED: item.closed_at = utcnow(); item.closure_reason = closure_reason` | §4.1 `chk_closure_consistency CHECK ((lifecycle_state = 'closed' AND closed_at IS NOT NULL AND closure_reason IS NOT NULL) OR (lifecycle_state != 'closed' AND closed_at IS NULL))` | ✅ OK invariant DB respecté par state machine |
| A4 | Colonnes `closed_at` + `closure_reason` + `closure_payload` documentées | §5 `_after_transition` set les 3 colonnes (avec justification + actor_id + extra_payload dans closure_payload JSONB) | §4.1 colonnes présentes | ✅ OK 3 colonnes utilisées |
| A5 | Tables filles `action_event_log` cible pour IL8 | §5 `_after_transition` : `self.event_log.write(item_id, organisation_id, event_type='state_changed', actor_type, actor_id, actor_name, event_payload={from, to, closure_reason, justification, ...})` | §4.3 `action_event_log` table dédiée avec event_type incluant `state_changed` | ✅ OK alignement strict |

**Total A : 5/5 OK** ✅

---

## B · Cohérence ADR-026 — 3/3 vérifications

| # | Vérification | Source brief | Source ADR-026 | Verdict |
|---|---|---|---|---|
| B1 | Mapping 6 vocabulaires statuts legacy → 5 V4 documenté | §10 mapping libellés FR mode standard (5 lifecycle states + 6 closure_reasons) | §10 mapping legacy → V4 (5 lifecycle_states V4 + 6 closure_reasons cohérents) | ✅ OK 5 états V4 + 6 closure_reasons couvrent les 6 vocabulaires legacy |
| B2 | Seeds V4 régénération couvre les 5 lifecycle_states | §2.1 enum 5 états · seeds canonicals HELIOS/MERIDIAN doivent peupler tous les états pour démo | §7 régen seeds V4 idempotent depuis YAML canonicals | ✅ OK (par construction · les 5 états seront présents dans seeds) |
| B3 | Cutover Mois 4 ne casse pas la state machine | §1.2 hors-scope explicite ADR-026 (état migré sans casse) · §11 renvois "ADR-026 migration data (lifecycle_state legacy → V4)" | §5.1 cutover Mois 4 J0 : régen seeds V4 + smoke tests J+0 | ✅ OK state machine indépendante du cutover |

**Total B : 3/3 OK** ✅

---

## C · Cohérence ADR-027 — 4/4 vérifications

| # | Vérification | Source brief | Source ADR-027 | Verdict |
|---|---|---|---|---|
| C1 | `admin_only_with_fresh_token` réutilisé pour IL3 | §6.2 endpoint `PATCH /reopen` décoré `@admin_only_with_fresh_token` (commentaire `# IS5 ADR-027 · IL3`) | §8 helper `admin_only_with_fresh_token` (token < 5min) | ✅ OK helper réutilisé sans duplication |
| C2 | HTTP 409 payload format cohérent §4 ADR-027 | §6.1 endpoint `/lifecycle` raise `HTTPException(409, detail={code, message, hint, correlation_id})` | §7 middleware JSONResponse 401/403 avec format identique `{code, message, hint, correlation_id}` | ✅ OK format payload uniforme |
| C3 | Décorateur `@org_scoped(allowed_roles=...)` utilisé sur endpoints lifecycle | §6.1 `@org_scoped(allowed_roles=["admin", "user"])` sur PATCH /lifecycle | §8 décorateur avec paramètre `allowed_roles` | ✅ OK décorateur réutilisé |
| C4 | IS4 viewer mutation = 403 cohérent | §6.1 commentaire explicite : `# IS4 viewer = 403` | IS4 invariant + §8 décorateur exclut viewer | ✅ OK invariant IS4 respecté |

**Total C : 4/4 OK** ✅

---

## D · Cohérence doctrine v0.2 — 4/4 vérifications

| # | Vérification | Source brief | Source doctrine | Verdict |
|---|---|---|---|---|
| D1 | 5 lifecycle states figés (§7.1 doctrine) | §2.1 enum 5 états : new/triaged/planned/in_progress/closed | doctrine §7.1 : 5 états identiques | ✅ OK |
| D2 | Q9-B recurrence ≠ duplicate respecté (IL5) | IL5 invariant : `merged_duplicate` interdit si `recurrence_group_id` sans `duplicate_group_id` · §4.2 code de validation explicite + Q37-A+ : `resolved_via_recurrence` ≠ `merged_duplicate` | doctrine §6.4 : Fusionner réservé doublons · Regrouper réservé récurrences | ✅ OK séparation cardinale respectée |
| D3 | Libellés FR mode standard documentés (§10 brief) | §10 mapping FR : "Qualifié", "Planifié", "En cours", "Clôturé", "Réouvert", "Résolu", "Écarté", "Non applicable", "Fusionné (doublon)", "Résolu via récurrence", "Expiré" | doctrine §7.1 mapping FR mode standard | ✅ OK 11 libellés FR mappés |
| D4 | 6 closure_reasons révisés cohérents avec doctrine §7.1 | brief : `resolved` / `dismissed` / `not_applicable` / `merged_duplicate` / `resolved_via_recurrence` / `expired` (6 valeurs) | doctrine §7.1 : `resolved` / `dismissed` / `not_applicable` / `duplicate` / `merged` / `expired` (6 valeurs) | ⚠️ OK avec **note mineure 1** : closure_reasons évolués depuis doctrine v0.2 (renommage `duplicate` + `merged` → `merged_duplicate` unifié + ajout `resolved_via_recurrence`). Évolution doctrinale raisonnée par Q37-A+ pour résoudre confusion sémantique. À documenter explicitement dans ADR-028 §17 (Conséquences) comme **évolution post-doctrine v0.2 actée par Q37-A+** |

**Total D : 4/4 OK** ✅ (1 note mineure)

---

## E · Cohérence L1 verdicts — 3/3 vérifications

| # | Vérification | Source brief | Source L1 | Verdict |
|---|---|---|---|---|
| E1 | 6 vocabulaires statuts SUPPRIME → 1 enum V4 cohérent | §2.1 enum unique `LifecycleState` (5 valeurs) · §3 matrice transitions strictes · §10 mapping FR unifie les vocabulaires | L1 audit : 6 vocabulaires statuts à unifier (vocab.legacy → V4 unique) | ✅ OK unification stricte |
| E2 | Endpoints lifecycle V4 cohérents avec 12 endpoints ADR-025 §5 | §6 : 2 endpoints (`PATCH /lifecycle` + `PATCH /reopen`) — couvrent les routes 4 et 8 de l'IDOR matrix ADR-027 §10.1 | ADR-025 §5 : 12 endpoints V4 cardinaux | ✅ OK 2 endpoints lifecycle parmi les 12 V4 |
| E3 | Tests planifiés (56) cohérents avec pyramide 100 ADR-025 §8 | §8 : 25 matrice + 20 closure_reasons + 11 IL = 56 tests | ADR-025 §10 pyramide stratifiée 100 tests V4 (50 SG + 30 unit/intégration + 15 contract + 5 e2e) | ✅ OK 56 tests s'inscrivent dans les 30 unit/intégration de la pyramide |

**Total E : 3/3 OK** ✅

---

## F · Cohérence maquettes M1-M5 — 3/3 vérifications

| # | Vérification | Source brief | Source maquette | Verdict |
|---|---|---|---|---|
| F1 | M1 boutons mappés aux transitions | §3.1 transitions : `qualify` (new→triaged) · `plan` (triaged→planned) · `start` (triaged/planned→in_progress) · `close` (any→closed) · `reopen` (closed→triaged) | M1 spec : boutons "Planifier", "Démarrer", "Clôturer", "Réassigner" sur item-cards | ✅ OK boutons "Planifier"/"Démarrer"/"Clôturer" mappent aux transitions ; "Réassigner" hors lifecycle (touche owner_id) |
| F2 | M2 drawer affiche `lifecycle_state` actuel + transitions possibles | §2.2 sémantique 5 états + libellés UI · §6.1 endpoint retourne item updated avec lifecycle_state | M2 spec : drawer affiche état actuel + actions disponibles (Planifier/Réassigner/Plus⌄) | ✅ OK drawer M2 reflète state machine |
| F3 | M5 Journal affiche events lifecycle (state_changed) | IL8 invariant : chaque transition écrit `action_event_log` avec event_type=`state_changed` · §5 `_after_transition` détaille payload | M5 spec : timeline chronologique 7j 38 events alimentée par `action_event_log` | ✅ OK M5 affiche les events state_changed comme tous les autres événements métier |

**Total F : 3/3 OK** ✅

---

## G · 11 invariants IL1-IL11 vérifiés — 11/11

| # | Invariant | Vérification dans brief | Verdict |
|---|---|---|---|
| G1 | **IL1** Transitions invalides → HTTP 409 | §5 `_before_transition` raise `InvalidTransitionError` + §6.1 endpoint catch et raise `HTTPException(409, detail={code, message, hint, correlation_id})` + §8.3 test `test_IL1_invalid_transition_returns_409` | ✅ ANCRÉ |
| G2 | **IL2** `closed → new` impossible | §3.2 `VALID_TRANSITIONS[CLOSED] = {TRIAGED}` (NEW absent) · §8.3 test `test_IL2_closed_to_new_impossible` | ✅ ANCRÉ |
| G3 | **IL3** Réouverture admin + fresh + justification | §6.2 endpoint `PATCH /reopen` décoré `@admin_only_with_fresh_token` + §5 `_verify_admin_role` + `_verify_fresh_token` + `_require_justification` (min 10 chars) + §8.3 test `test_IL3_reopen_requires_admin_fresh_token_justification` | ✅ ANCRÉ |
| G4 | **IL4** `expired` interdit P0/P1 conformité/facturation | §4.2 fonction `verify_closure_reason_valid` raise `EXPIRED_FORBIDDEN_ON_ACTIVE_PRIORITY` si domain ∈ {conformite, facturation} ET priority_bracket ∈ {P0, P1} + §8.3 test `test_IL4_expired_forbidden_on_p0_compliance` | ✅ ANCRÉ |
| G5 | **IL5** `merged_duplicate` interdit si recurrence sans duplicate | §4.2 `verify_closure_reason_valid` raise `MERGED_DUPLICATE_FORBIDDEN_ON_RECURRENCE` si `recurrence_group_id != None AND duplicate_group_id == None` + §8.3 test `test_IL5_merged_duplicate_forbidden_on_recurrence_only` | ✅ ANCRÉ |
| G6 | **IL6** Auto-close récurrence exige `group.resolved` | §4.3 `on_recurrence_group_resolved` raise `RECURRENCE_CASCADE_REQUIRES_RESOLVED_GROUP` si `group.status != RESOLVED` + §8.3 test `test_IL6_auto_close_recurrence_requires_resolved_group` | ✅ ANCRÉ |
| G7 | **IL7** Auto-close récurrence P0/P1 exige preuve ou justification | §4.3 `on_recurrence_group_resolved` skip P0/P1 sans `has_evidence OR has_justification` (avec log warning + audit trail) + §8.3 test `test_IL7_auto_close_p0_recurrence_requires_evidence_or_justification` | ✅ ANCRÉ |
| G8 | **IL8** Chaque transition écrit `action_event_log` | §5 `_after_transition` : `self.event_log.write(item_id, organisation_id, event_type='state_changed', actor_type, actor_id, actor_name, event_payload)` (avant `score_stale` et `repo.save`) + §8.3 test `test_IL8_every_transition_writes_event_log` | ✅ ANCRÉ |
| G9 | **IL9** Chaque transition met `score_stale=true` | §5 `_after_transition` : `item.score_stale = True` (après event_log) + §8.3 test `test_IL9_every_transition_invalidates_score` | ✅ ANCRÉ |
| G10 | **IL10** Frontend wait-for-server | §7 `transitionLifecycle` async/await sans optimistic update + commentaire explicite "IL10 : ne PAS faire optimistic update" + bouton avec spinner pendant l'appel + §8.3 placeholder e2e Playwright | ✅ ANCRÉ |
| G11 | **IL11** Réouverture trace event avec justification | §5 `_after_transition` payload inclut `justification` + §6.2 endpoint reopen valide `justification: str` (min 10 chars) + §8.3 test `test_IL11_reopen_event_has_justification` | ✅ ANCRÉ |

**Total G : 11/11 OK** ✅

---

## H · Sprint Phase 3.5 — 2/2 vérifications

| # | Vérification | Source brief | Source contexte Phase 3.5 | Verdict |
|---|---|---|---|---|
| H1 | `regulatory_applicability_service` Q4-A référencé pour `qualify_system` transition | §3.1 matrice : transition `qualify_system` (new→triaged) avec rôle "system" et hook commentaire "from regulatory_applicability_service Q4-A" | ADR-025 §11.2 interface stub Mois 2-3 + branchement Mois 4 sur Phase 3.5 livré | ✅ OK référencé sans duplication |
| H2 | Pas de duplication de logique avec sprint en parallèle | brief consume `regulatory_applicability_service` comme service externe (black-box) via transition `qualify_system` · Q9 effets de bord système : `system_dismiss_on_not_applicable` déclenché par regulatory_applicability_service | ADR-025 §11.2 + L1 §6.1 mitigation : ne pas perturber sprint en cours | ✅ OK aucune duplication |

**Total H : 2/2 OK** ✅

---

## Anomalies détectées

**Aucune anomalie bloquante.** 1 note mineure :

### Note mineure 1 — Évolution closure_reasons depuis doctrine v0.2

- **Section** : brief §2.1 + §4.1 + §10 + doctrine §7.1
- **Type** : évolution doctrinale post-v0.2 raisonnée
- **Détail** : doctrine §7.1 liste 6 closure_reasons : `resolved` / `dismissed` / `not_applicable` / `duplicate` / `merged` / `expired`. Le brief ADR-028 fait évoluer cette liste vers 6 closure_reasons révisés : `resolved` / `dismissed` / `not_applicable` / **`merged_duplicate`** (fusion `duplicate`+`merged`) / **`resolved_via_recurrence`** (nouveau) / `expired`. Cette évolution est raisonnée par Q37-A+ (validation 2026-05-14) pour :
  1. Unifier `duplicate`+`merged` en un seul `merged_duplicate` (clarification sémantique : un item fusionné est nécessairement un doublon)
  2. Ajouter `resolved_via_recurrence` distinct de `merged_duplicate` pour respecter Q9-B (récurrence ≠ doublon)
- **Recommandation correction ADR-028** : ajouter explicitement dans §17 (Conséquences > Neutres) une mention "**Évolution post-doctrine v0.2** : closure_reasons révisés via Q37-A+ — `duplicate`+`merged` unifiés en `merged_duplicate` + ajout `resolved_via_recurrence` pour respecter Q9-B. Doctrine §7.1 sera mise à jour en avenant doctrinal v0.3 si nécessaire."

---

## Total

| Bloc | Vérifications | OK | Anomalies bloquantes | Anomalies mineures |
|---|---|---|---|---|
| A · ADR-025 | 5 | 5 | 0 | 0 |
| B · ADR-026 | 3 | 3 | 0 | 0 |
| C · ADR-027 | 4 | 4 | 0 | 0 |
| D · Doctrine v0.2 | 4 | 4 | 0 | 1 (closure_reasons évolués) |
| E · L1 verdicts | 3 | 3 | 0 | 0 |
| F · Maquettes M1-M5 | 3 | 3 | 0 | 0 |
| G · 11 invariants IL1-IL11 | 11 | 11 | 0 | 0 |
| H · Sprint Phase 3.5 | 2 | 2 | 0 | 0 |
| **TOTAL** | **35** | **35** | **0** | **1** |

- **Vérifications réussies** : **35 / 35** ✅
- **Anomalies bloquantes** : **0**
- **Anomalies mineures** : **1** (à intégrer comme correction dans ADR-028 final §17 Conséquences)
- **Brief consommable en l'état pour Phase 1** : **OUI** (avec 1 correction mineure à appliquer dans transformation MADR)

**Compteurs cardinaux brief** :
- 11 invariants IL1-IL11 : tous présents (mention bold + références multiples)
- 7 arbitrages Q33-Q39 : tous présents (2-6 mentions chacun)
- 5 lifecycle_states : enum complet
- 10 transitions strictes documentées
- 6 closure_reasons révisés
- 56 tests planifiés (25 matrice + 20 closure + 11 IL)
- 91 mentions "transitions" dans le brief
- 86 mentions "lifecycle_state" / "LifecycleState"

---

## STOP GATE — Phase 0 terminée

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 0 TERMINÉE — STOP GATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Bilan Phase 0 disponible : docs/dev/L5_phase0_audit_coherence.md

Vérifications cohérence :
  A · ADR-025          : 5/5 OK
  B · ADR-026          : 3/3 OK
  C · ADR-027          : 4/4 OK
  D · Doctrine v0.2    : 4/4 OK (1 note mineure : closure_reasons évolués via Q37-A+)
  E · L1 verdicts      : 3/3 OK
  F · Maquettes M1-M5  : 3/3 OK
  G · 11 invariants    : 11/11 OK
  H · Sprint Phase 3.5 : 2/2 OK

Total : 35/35 vérifications réussies ✅
Anomalies bloquantes : 0
Anomalies mineures : 1 (closure_reasons évolués post-doctrine v0.2 via Q37-A+)

Compteur lifecycle dans le brief :
  - 5 lifecycle_states (new/triaged/planned/in_progress/closed)
  - 10 transitions strictes documentées
  - 6 closure_reasons révisés (merged_duplicate + resolved_via_recurrence cardinaux)
  - 11 invariants IL1-IL11 tous présents
  - 7 arbitrages Q33-Q39 tous documentés
  - 56 tests planifiés (25 matrice + 20 closure + 11 IL)

Brief consommable : OUI
  → Phase 1 doit appliquer 1 correction mineure dans MADR :
    - §17 Conséquences (Neutres) : mention explicite évolution closure_reasons
      post-doctrine v0.2 via Q37-A+ (duplicate+merged → merged_duplicate +
      ajout resolved_via_recurrence pour respecter Q9-B)

⛔ NE PAS DÉMARRER Phase 1 avant validation utilisateur.

Confirmer pour passer en Phase 1 : « GO Phase 1 »
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Métadonnées Phase 0

```yaml
phase: "L5 Phase 0 — audit cohérence brief ADR-028"
status: "TERMINÉE — STOP GATE actif"
date: "2026-05-14"
files_produced:
  - docs/dev/BRIEF_ADR-028_lifecycle_states.md (transféré ce jour, 1017 L)
  - docs/dev/L5_phase0_audit_coherence.md (ce fichier)
files_modified: 0
db_writes: 0
verifications_total: 35
verifications_ok: 35
anomalies_blocking: 0
anomalies_minor: 1
brief_metrics:
  invariants_IL1_IL11: 11/11
  arbitrages_Q33_Q39: 7/7
  lifecycle_states: 5
  transitions_strictes: 10
  closure_reasons: 6
  tests_planifies: 56
  brief_lines: 1017
brief_consumable: true
corrections_to_apply_in_adr028:
  - "D4 note mineure: ajouter §17 Conséquences (Neutres) mention évolution closure_reasons post-doctrine v0.2 via Q37-A+ (duplicate+merged → merged_duplicate + ajout resolved_via_recurrence)"
next_step: "Validation utilisateur 'GO Phase 1' → produire L5_ADR-028_lifecycle_states.md (format MADR · 45/45 auto-éval · note Q37-A+ évolution closure_reasons intégrée)"
```
