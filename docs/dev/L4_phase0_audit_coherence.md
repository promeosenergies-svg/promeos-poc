---
title: L4 Phase 0 · Audit cohérence brief ADR-027
date: 2026-05-14
branch: claude/refonte-sol2
mode: lecture seule (aucun fichier modifié sauf brief transféré §3.1 prompt)
mission: Vérifier cohérence brief ADR-027 vs ADR-025 + ADR-026 + doctrine v0.2 + L1 + maquettes M1-M5 + 11 invariants IS + 8 menaces M
sources_audites:
  - docs/dev/BRIEF_ADR-027_securite_org_scoping.md (transféré ce jour · 995 L)
  - docs/dev/L2_ADR-025_architecture_v4.md (commit 712da32a)
  - docs/dev/L3_ADR-026_migration_data.md (commit 1500f55b)
  - docs/doctrine/doctrine_v4_classement_priorisation.md (v0.2)
  - docs/dev/L1_audit_centre_action_v4_decisional.md (commit ee749a12 · 86 verdicts)
  - docs/maquettes/centre_action_v4/ (5 HTML figées)
prompt_source: PROMPT_CLAUDE_CODE_mois1_L4.md (v1.0 · 2026-05-14)
---

# L4 Phase 0 · Audit cohérence brief ADR-027

Audit lecture-seule de la cohérence du brief sécurité vs ADR-025 + ADR-026 + doctrine + L1 + maquettes + 11 invariants IS + 8 menaces M. Aucun fichier modifié sauf transfert du brief.

---

## A · Cohérence ADR-025 — 5/5 vérifications

| # | Vérification | Source brief ADR-027 | Source ADR-025 | Verdict |
|---|---|---|---|---|
| A1 | Schéma `action_center_items` colonne `organisation_id` indexée | §6 pattern repository force `organisation_id` filter sur toutes les méthodes | §4.1 : colonne `organisation_id UUID NOT NULL` + §4.2 : `idx_aci_priority_active(organisation_id, priority_score DESC, ...)` et 7 autres indexes avec org_id en 1ère colonne | ✅ OK alignement strict |
| A2 | Tables filles `evidences`, `action_event_log`, etc. ont toutes `organisation_id` | §6 mention 8 repositories tous org-scopés (ActionCenter + Evidence + ActionEventLog + ActionLink + ActionBlocker + ActionScenario + DuplicateGroup + RecurrenceGroup) | §4.3 : chaque table fille déclare `organisation_id UUID NOT NULL` | ✅ OK 7 tables filles + 1 cardinale = 8 tables couvertes |
| A3 | Middleware FastAPI cohérent avec §9 ADR-025 ("Sécurité org-scoping native") | §4 OrgScopingMiddleware avec extraction org_id, anonymisation IP, correlation_id, JSONResponse 401/403 sanitizé | §9.1 ADR-025 : OrgScopingMiddleware basique référencé | ✅ OK ADR-027 enrichit le squelette ADR-025 |
| A4 | Décorateur `@org_scoped` cohérent avec §9.2 ADR-025 | §5 décorateur étendu avec `allowed_roles` paramétrable + helper `admin_only_with_fresh_token` IS5 | §9.2 ADR-025 : décorateur basique référencé | ✅ OK ADR-027 enrichit avec roles + token freshness |
| A5 | 50 source-guards cohérent avec décomposition ADR-025 §10.2 | §8.1 50 SG en 6 catégories : Org-scoping (15) + IDOR prevention (10) + Logs sanitization (8) + Backup safety (5) + JWT+Cookies (7) + Patterns interdits (5) = 50 | §10.2 ADR-025 : "50 SG = 6 cardinaux nouveaux V4 + 8 existants GARDE + 36 dérivés" | ✅ OK 2 vues du même total 50 (par catégorie vs par origine) — pas contradiction |

**Total A : 5/5 OK** ✅

---

## B · Cohérence ADR-026 — 3/3 vérifications

| # | Vérification | Source brief ADR-027 | Source ADR-026 | Verdict |
|---|---|---|---|---|
| B1 | IS10 backup non commitables cohérent avec I9 ADR-026 | IS10 : "Backup/export non commitables : `.gitignore` + source-guard CI bloque" | I9 cardinal : "Backup hors Git · receipt sanitizé in Git" | ✅ OK IS10 = renforcement CI de I9 (source-guard automatise vérification) |
| B2 | Source-guard `.gitignore` aligné §6.1 ADR-026 | §8.2 `test_gitignore_blocks_backups` vérifie patterns `/backups/`, `*.backup`, `*.sql`, `**/legacy_json/` | §6.1 ADR-026 : `.gitignore` obligatoire avec exactement ces 4 patterns + autorisation `RECEIPT_*.md` | ✅ OK patterns identiques |
| B3 | Pas de PII dans `security_audit_log` (cohérent receipt sanitizé I9) | §10 `log_security_event` exclut explicitement body/token/query_string/cookies/authorization header · §10.1 table `security_audit_log` ne contient pas non plus payload sensible | §6.3 ADR-026 garde-fou anti-PII receipt + test source-guard `test_receipt_has_no_pii` | ✅ OK même politique anti-PII appliquée aux deux contextes (receipts et logs sécurité) |

**Total B : 3/3 OK** ✅

---

## C · Cohérence doctrine v0.2 — 4/4 vérifications

| # | Vérification | Source brief | Source doctrine | Verdict |
|---|---|---|---|---|
| C1 | Q4-A `regulatory_applicability_service` org-scopé natif | §6 pattern repository s'applique à tout service consommant la DB · `regulatory_applicability_service` étant un service externe consommé via repository, hérite de l'org-scoping | doctrine §5.6 R6 : Q4-A SoT consommé sans duplication | ✅ OK par nature (pattern repository couvre tous les accès DB) |
| C2 | Q6-A docs only respecté (aucun code modifié) | §1.2 hors-scope explicite : "Aucun code Python/TypeScript modifié" + §15.3 conformité Q6-A | doctrine arbitrage Q6-A | ✅ OK |
| C3 | Libellés FR dans codes d'erreur (mode standard vs audit) | §4 messages JSONResponse en anglais (`"message": "Authentication required"`) — convention API standard · le frontend doit traduire pour affichage utilisateur en mode standard FR | doctrine §7.1 mapping FR mode standard | ✅ OK avec note : codes/messages API en anglais (convention standard) · traduction FR au niveau frontend pour mode standard |
| C4 | Mode standard / audit cohérent avec logs sanitisation | §10 logs structurés sanitizés au niveau backend (sans body/token) · indépendant du mode UI | doctrine §7.2 mode standard / mode audit (toggle UI uniquement) | ✅ OK séparation claire : sanitisation backend (toujours) ≠ toggle UI mode standard/audit |

**Total C : 4/4 OK** ✅

---

## D · Cohérence L1 verdicts — 4/4 vérifications

| # | Vérification | Source brief | Source L1 | Verdict |
|---|---|---|---|---|
| D1 | Fuites `/api/action-center/*` P0 mitigées par IS1 + IS11 | TL;DR explicite "Risque P0 sécu identifié L1 → ce document fige les invariants" + IS1 + IS11 + IDOR matrix 288 | L1 audit §6 : fuite massive `/api/action-center/*` (sauf `/issues` et `/summary`) confirmée P0 sécu | ✅ OK risque P0 mitigé structurellement par construction V4 |
| D2 | 51 endpoints SUPPRIME couverts (legacy disparaît, V4 ré-implémente sécurisé) | §7.1 : 12 endpoints V4 listés (pilotage + items + 5 PATCH + close + correct-kind + audit-trail + impact + evidence + scenarios select) | L1 §3.4 distribution endpoints : 51 endpoints SUPPRIME (legacy `/api/anomalies/*`, `/api/action-plans/*`, etc.) | ✅ OK legacy disparaît · V4 ré-implémente avec org-scoping natif |
| D3 | 12 endpoints V4 référencés correctement (IDOR matrix routes) | §7.1 IDOR matrix : 12 routes V4 énumérées explicitement (4 GET + 5 PATCH + 3 POST) | L1 §3.6 (mapping legacy → V4) + ADR-025 §5 : ~12 endpoints V4 cardinaux | ✅ OK matrix exhaustive |
| D4 | 8 source-guards `GARDE` L1 réutilisés dans les 50 SG V4 | §8.1 50 SG en 6 catégories (somme exhaustive) | L1 §3.8 : 8 SG existants GARDE (test_bill_anomaly_yaml_runtime_consistency, test_navigation_badges, etc.) + 6 nouveaux V4 cardinaux | ✅ OK 8 existants comptés dans les 50 totaux (catégorie par origine vs catégorie par fonction) |

**Total D : 4/4 OK** ✅

---

## E · Cohérence maquettes M1-M5 — 4/4 vérifications

| # | Vérification | Source brief ADR-027 | Source maquette | Verdict |
|---|---|---|---|---|
| E1 | Drawer M2 audit trail respecte logs sanitisation | §10 séparation explicite : `security_audit_log` (sécurité, sanitizé sans PII) vs `action_event_log` (métier, peut contenir données utilisateur intentionnellement) | M2 spec : drawer affiche `action_event_log` métier (5 derniers events) · pas `security_audit_log` | ✅ OK séparation claire entre audit trail métier et logs sécurité |
| E2 | Mode audit (toggle UI) ne révèle pas de tokens ni body | §10 sanitisation backend : tokens/body jamais loggés au niveau backend · le mode audit UI n'affiche que les codes techniques métier (lifecycle, IDs, etc.), pas les tokens | doctrine §7.2 mode audit UI affiche codes techniques métier · pas tokens/body | ✅ OK distinction claire mode audit UI (codes métier) vs logs backend (tokens jamais) |
| E3 | Filtres M3 Référentiel respectent org-scoping | §7.1 IDOR matrix inclut `GET /api/action-center/items` (route 2) consommée par M3 · IS1 force `@org_scoped` · IS3 force 404 cross-org | M3 spec : filtres kind/priority/lifecycle/domain consomment l'API items org-scopée | ✅ OK filtres FE alimentés par API org-scopée |
| E4 | M5 Journal chronologique alimenté par `action_event_log` (pas `security_audit_log`) | §10.1 `security_audit_log` table dédiée distincte de `action_event_log` (rétention 90j vs 5 ans) | M5 spec : timeline 7j 38 events alimentée par `action_event_log` métier | ✅ OK séparation propre (M5 ne consomme pas `security_audit_log` qui est admin-only) |

**Total E : 4/4 OK** ✅

---

## F · 11 invariants IS1-IS11 vérifiés — 11/11

| # | Invariant | Vérification dans brief | Verdict |
|---|---|---|---|
| F1 | **IS1** Routes /api/action-center/* ont @org_scoped | §5 décorateur explicite avec usage attendu (`@org_scoped()` sur GET, `@org_scoped(allowed_roles=["admin","user"])` sur PATCH) + §8.1 source-guard `test_all_action_center_routes_have_org_scoped_decorator` | ✅ ANCRÉ |
| F2 | **IS2** Couverture cross-org 100% | §7 IDOR matrix 288 cellules = 100% des combinaisons routes × roles × orgs × cas + §7.3 génération automatique `@pytest.mark.parametrize` | ✅ ANCRÉ |
| F3 | **IS3** Cross-org → 404 anti-énumération | §7.2 exemples cardinaux montrent 404 pour cross-org (Route 2 line "admin/helios other → 404 IS3 anti-énumération") + §6 repository raise HTTPException(404) si cross-org | ✅ ANCRÉ |
| F4 | **IS4** Viewer mutation → 403 | §5 décorateur `@org_scoped(allowed_roles=["admin","user"])` exclut viewer + §7.2 Route 4 line "viewer/helios own → 403 IS4 viewer no mutation" | ✅ ANCRÉ |
| F5 | **IS5** Admin: role=admin + token <5min | §5 helper `admin_only_with_fresh_token` (token_age < 300s) + §7.2 Route 8 line "admin/helios own (token > 5min) → 403 IS5 fresh token" | ✅ ANCRÉ |
| F6 | **IS6** CI gate: Bandit + Semgrep + gitleaks + pip-audit | §9 workflow YAML complet `.github/workflows/security.yml` avec 4 jobs + 1 source-guards + 1 idor-matrix tous bloquants | ✅ ANCRÉ |
| F7 | **IS7** Logs sans body/query/token | §10 `log_security_event` exclut explicitement body/query_string/cookies/authorization header (commentaire `⚠ JAMAIS`) + §8.2 source-guard `test_logs_no_token_or_body` | ✅ ANCRÉ |
| F8 | **IS8** IP anonymisée /24 /48 | §4 fonction `anonymize_ip()` avec IPv4 /24 (`ipaddress.IPv4Network(f"{ip}/24")`) et IPv6 /48 + §10 `ip_anonymized` dans payload log | ✅ ANCRÉ |
| F9 | **IS9** correlation_id obligatoire | §4 middleware injecte `request.state.correlation_id = correlation_id` (depuis header X-Correlation-ID ou génère uuid4) + §10 `correlation_id` dans tous les logs + §8.1 SG `test_logs_have_correlation_id` | ✅ ANCRÉ |
| F10 | **IS10** Backup/export non commitables | §8.1 source-guard `test_gitignore_excludes_backups` + §8.2 exemple complet vérifie 4 patterns `.gitignore` + cohérent ADR-026 §6.1 I9 | ✅ ANCRÉ |
| F11 | **IS11** Pas d'accès DB direct, pattern repository | §6 pattern repository org-scopé documenté avec exemple complet `ActionCenterRepository` + §6.1 anti-pattern interdit explicitement (❌ `db.query()` direct dans route) + §8.1 SG `test_no_direct_db_query_in_action_center_routes` | ✅ ANCRÉ |

**Total F : 11/11 OK** ✅

---

## G · 8 menaces M1-M8 cohérentes — 8/8

| # | Menace | Mitigation référencée dans brief | Verdict |
|---|---|---|---|
| G1 | **M1** IDOR via id direct (P0) | IS1 (`@org_scoped`) + IS11 (pattern repository force `organisation_id` filter) + IDOR matrix 288 | ✅ MITIGATION RÉFÉRENCÉE |
| G2 | **M2** Privilege escalation (P0) | IS5 (`admin_only_with_fresh_token` : role=admin + token <5min) + §5 log `privilege.escalation.attempt` automatique | ✅ MITIGATION RÉFÉRENCÉE |
| G3 | **M3** Injection SQL (P1) | Bandit CI §9 + repository pattern §6 (ORM uniquement, pas de raw SQL) + §8.1 source-guard `test_no_raw_sql_in_action_center` | ✅ MITIGATION RÉFÉRENCÉE |
| G4 | **M4** JWT replay (P1) | §3.3 rotation tokens : access 1h + refresh 30j + revocation list (session_id) + IS5 admin token <5min | ✅ MITIGATION RÉFÉRENCÉE |
| G5 | **M5** Énumération 403/404 différenciés (P1) | IS3 invariant cardinal "Toujours 404 pour cross-org" + §7.2 IDOR matrix exemples montrent 404 systématique | ✅ MITIGATION RÉFÉRENCÉE |
| G6 | **M6** CSRF mutations (P2) | §3.3 cookies SameSite=Strict (Lax pour CSRF token) + §3.1 mention CSRF token séparé + Origin check implicite middleware | ✅ MITIGATION RÉFÉRENCÉE |
| G7 | **M7** Logs leak PII (P1 RGPD) | IS7 (sans body/query/token) + IS8 (IP anonymisée /24 /48) + §10 `log_security_event` exhaustif liste exclusions | ✅ MITIGATION RÉFÉRENCÉE |
| G8 | **M8** Brute force endpoints sensibles (P2) | §12 rate limiting `slowapi` : 10 req/min sur `/login`, 5 req/min sur `/correct-kind`, 30 req/min sur `/close` | ✅ MITIGATION RÉFÉRENCÉE |

**Total G : 8/8 OK** ✅

---

## Anomalies détectées

**Aucune anomalie bloquante. Aucune anomalie mineure significative.**

Notes informatives (non corrigeables ou par nature) :
- **C3 (informatif)** : messages d'erreur API (`message: "Authentication required"`) en anglais — convention API standard. Le frontend doit traduire pour mode standard FR (cf. doctrine §7.1). Pas un défaut de l'ADR mais un point d'attention pour le frontend.
- **A5 (informatif)** : décomposition 50 SG vue par catégorie fonctionnelle (ADR-027 §8.1) vs vue par origine (ADR-025 §10.2). Deux angles de vue cohérents du même total · pas une contradiction.

**Brief consommable en l'état pour Phase 1** sans correction préalable.

---

## Total

| Bloc | Vérifications | OK | Anomalies bloquantes | Anomalies mineures |
|---|---|---|---|---|
| A · ADR-025 | 5 | 5 | 0 | 0 |
| B · ADR-026 | 3 | 3 | 0 | 0 |
| C · Doctrine v0.2 | 4 | 4 | 0 | 0 (1 informative) |
| D · L1 verdicts | 4 | 4 | 0 | 0 |
| E · Maquettes M1-M5 | 4 | 4 | 0 | 0 |
| F · 11 invariants IS1-IS11 | 11 | 11 | 0 | 0 |
| G · 8 menaces M1-M8 | 8 | 8 | 0 | 0 |
| **TOTAL** | **39** | **39** | **0** | **0** |

- **Vérifications réussies** : **39 / 39** ✅
- **Anomalies bloquantes** : **0**
- **Anomalies mineures** : **0**
- **Brief consommable en l'état pour Phase 1** : **OUI** (sans correction préalable)

**Compteurs cardinaux** :
- 11 invariants IS1-IS11 : tous présents (1 mention bold chacun + références multiples)
- 8 menaces M1-M8 : toutes présentes
- IDOR : 16 mentions
- org_scop* : 27 mentions
- 50 source-guards : 6 catégories documentées
- 7 arbitrages Q26-Q32 : 2-9 mentions chacun

---

## STOP GATE — Phase 0 terminée

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 0 TERMINÉE — STOP GATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Bilan Phase 0 disponible : docs/dev/L4_phase0_audit_coherence.md

Vérifications cohérence :
  A · ADR-025          : 5/5 OK
  B · ADR-026          : 3/3 OK
  C · Doctrine v0.2    : 4/4 OK
  D · L1 verdicts      : 4/4 OK
  E · Maquettes M1-M5  : 4/4 OK
  F · 11 invariants    : 11/11 OK
  G · 8 menaces M1-M8  : 8/8 OK

Total : 39/39 vérifications réussies ✅
Anomalies bloquantes : 0
Anomalies mineures : 0

Compteur sécurité dans le brief :
  - org_scop* mentions : 27
  - IDOR mentions : 16
  - source-guards documentés : 50 (6 catégories)
  - 11 invariants IS1-IS11 : tous présents
  - 8 menaces M1-M8 : toutes mitigées
  - 7 arbitrages Q26-Q32 : tous documentés

Brief consommable : OUI (sans correction préalable)

⛔ NE PAS DÉMARRER Phase 1 avant validation utilisateur.

Confirmer pour passer en Phase 1 : « GO Phase 1 »
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Métadonnées Phase 0

```yaml
phase: "L4 Phase 0 — audit cohérence brief ADR-027"
status: "TERMINÉE — STOP GATE actif"
date: "2026-05-14"
files_produced:
  - docs/dev/BRIEF_ADR-027_securite_org_scoping.md (transféré ce jour, 995 L)
  - docs/dev/L4_phase0_audit_coherence.md (ce fichier)
files_modified: 0
db_writes: 0
verifications_total: 39
verifications_ok: 39
anomalies_blocking: 0
anomalies_minor: 0
brief_metrics:
  invariants_IS1_IS11: 11/11
  menaces_M1_M8: 8/8
  IDOR_mentions: 16
  org_scop_mentions: 27
  source_guards_documented: 50
  source_guards_categories: 6
  arbitrages_Q26_Q32: 7/7
  brief_lines: 995
brief_consumable: true
corrections_to_apply_in_adr027: []  # aucune correction requise
notes_informatives:
  - "C3: messages API en anglais (convention standard) · traduction FR au niveau frontend"
  - "A5: 50 SG vue par catégorie fonctionnelle (ADR-027) vs par origine (ADR-025) · pas contradiction"
next_step: "Validation utilisateur 'GO Phase 1' → produire L4_ADR-027_securite_org_scoping.md (format MADR · 50/50 auto-éval)"
```
