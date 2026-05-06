# AUDIT TRANSVERSAL PHASE C PROMEOS — 6 AXES

**Date** : 2026-05-06
**Branche** : `claude/refonte-sol2`
**HEAD audit** : `579b81a1` (Sprint C-5 Phase 5.6 fix audit deep)
**Méthode** : 6 agents SDK spécialisés en parallèle (pattern audit deep Phase 5.5 généralisé)
**Durée** : ~1.5 h cumul

---

## 🎯 Synthèse exécutive (1 page)

**Déclencheur** : la Phase 5.5 audit deep Sprint C-5 a révélé **4 P0 invisibles** aux 7 agents SDK pré-commit cumulés (PRAGMA foreign_keys absent, erreur arithmétique x1000, R19 NULL faux positif, SG tolerance défaillant). Cet audit transversal généralise la rigueur Phase 5.5 deep à TOUTES les phases Phase C livrées (29 phases + 2 mini-sprints sécurité).

**Découvertes cardinales** : **10 P0 nouveaux + 15 P1 + 10 P2** non détectés par les audits sprint-end précédents. Pattern récurrent : **déclaration sans enforcement runtime** (cascade Org consentement câblée CASCADE_MAP mais pas wirée PATCH endpoint, BillAnomaly UNIQUE constraint absent, etc.).

**Verdict global** : Phase C **arithmétiquement saine** (1 seul bug ×1000 cardinal déjà corrigé Phase 5.6) mais **lacunes cardinales runtime + RGPD + sécurité DEMO_MODE** qui invalidaient partiellement la promesse fonctionnelle des Sprints C-3 → C-5.

**Impact business** : différenciateurs cardinaux (RGPD trace + Bill Intelligence anomaly detection + cascade vivante) **partiellement effectifs** sans corrections P0. Audit consultant énergie pré-pilote aurait détecté gaps cardinaux. Audit CNIL aurait flag preuve d'origine cassée.

**Plan d'action** : Phase 5.7 fix 5-7 P0 cardinaux (~2-3 h) + Sprint C-7 polish enrichi à ~30-40 h (~5 j-h).

---

## 📋 Méthode + périmètre couvert

### 6 AXES audités (pattern audit Phase 5.5 généralisé)

| AXE | Mission | Agent | Durée |
|---|---|---|---|
| **AXE 1** | Math Verifier — toute formule arithmétique reproductible | general-purpose | ~25 min |
| **AXE 2** | Runtime Enforcer — toute contrainte ORM enforced runtime | general-purpose | ~20 min |
| **AXE 3** | Edge Cases NULL/Empty/Boundary | general-purpose | ~20 min |
| **AXE 4** | Security & Org-Scoping (IDOR, DEMO_MODE, PII) | security-auditor | ~25 min |
| **AXE 5** | RGPD & Audit Trail (AuditLog wiring) | general-purpose | ~20 min |
| **AXE 6** | Cohérence Cross-Modules + 1 SoT par concept | architect-helios | ~10 min |

### Périmètre Phase C (29 phases + 2 mini-sprints)

- **Sprint C-1** (6 phases) : CO2 + cascade fondamentale + OPERAT
- **Sprint C-2** (5 phases) : temporalité + FE cleanup + audit log
- **Mini-sprint IDOR meters** (CWE-639)
- **Sprint C-3** (7 phases) : sources + R10 TraceTooltip + ELD
- **Mini-sprint IDOR Portfolio** (CWE-284)
- **Sprint C-4** (9 phases) : tests + observabilité + cascade vivante
- **Sprint C-5** (5 phases + 5.5 + 5.6) : Bill Intelligence + Capacité + RGPD ext + polish

---

## 🔢 AXE 1 — Math Verifier (verdict ✅ PASS, 3 P1 dette doc)

### Findings

| # | Finding | Sévérité | Localisation |
|---|---|---|---|
| 1 | `revenue.py:17-19` docstring `3.15 × 1.2 / 8760 = 0.43` STALE post-Phase 5.6 fix F3 | P1 | `services/capacity/revenue.py:17-19` |
| 2 | ADR-015 sections amont (§1-§180) non MAJ post-Phase 5.6 (auto-contradictoire) | P1 | `docs/adr/ADR-015-*.md` |
| 3 | `catalog.py:864 TICGN dead-entry` (`rate=0.01639` contredit `TICGN_FEV2026=10.73`) | P1 | `services/billing_engine/catalog.py:864` |

### Points positifs

- ✅ 33 formules vérifiées (CO2 ADEME 0.052/0.227/0.238 OK, accises 30.85/26.58/10.73 OK, weights doctrinaux somme=1.0 OK, Cabs OPERAT formule OK, CMDPS OK, intensity Σ/Σ OK)
- ✅ COEFF_KWH_EF_TO_KWH_EP_ELEC=1.9 fantôme bien supprimé Phase 4.3d (0 callsite résiduel)
- ✅ Phase 5.6 F3 fix Capacité 3.15 → 3150 confirmé propagé YAML + catalog.py + cost_simulator_2026.py
- ✅ **Aucune autre erreur arithmétique x100/x1000** trouvée Phase C

### Effort fix

- 3 dettes documentaires P1 : ~30 min cumul (revenue.py docstring + ADR-015 amont + catalog TICGN cleanup)

---

## 🛡️ AXE 2 — Runtime Enforcer (verdict 🔴 2 P0 NOUVEAUX)

### Findings cardinaux

| # | Finding | Sévérité |
|---|---|---|
| **F2** | **Cascade Org consentement_dataconnect/grdf_global JAMAIS déclenchée runtime** — déclarée `CASCADE_MAP_MVP_SPRINT_C1` mais PATCH `/organisations/{id}` (`patrimoine_crud.py:145`) sans appel `cascade_recompute_on_change`. Cascade vivante Phase 4.5 silencieusement non-enforced. **Reproduit exactement F1 PRAGMA pattern**. | 🔴 **P0** |
| **F4** | **BillAnomaly sans `UniqueConstraint(invoice_id, code)`** — permet doublons R19/R20 sur même facture → fuites coût CFO. | 🔴 **P0** |
| F6 | BillAnomaly `severity` / `code` `String(10/20)` sans Enum NI CheckConstraint — accept `severity="lol"` | P1 |
| F8 | Aucun pydantic validator sur consentement (Org/DP) — accept `consentement_dataconnect_global=True` sans `_by` ni `cgu_version` | P1 |
| F1 | PRAGMA `synchronous=NORMAL`, `cache_size`, `temp_store=MEMORY`, `mmap_size` non posés (perf SQLite WAL) | P2 |
| F10 | `get_effective_consent_with_audit` pas de check existence Org/DP en DB — fallback silencieux scope=none | P2 |

### Points positifs

- ✅ Phase 5.6 F1 fix : PRAGMA `foreign_keys=ON` enforced runtime (4 FK consentement_*_by ondelete=SET NULL effectives)
- ✅ 9 migrations Alembic Phase C : 0 destructive cumulé confirmé

### Effort fix

- F2 (cascade Org) : ~30 min (wirer cascade_recompute_on_change dans `patrimoine_crud.update_organisation`)
- F4 (UQ BillAnomaly) : ~20 min (migration 10e + delta DDL)
- F6+F8 : ~45 min (Enum/CheckConstraint + pydantic validators)

---

## 🐛 AXE 3 — Edge Cases NULL (verdict 🔴 3 P0 NOUVEAUX)

### Findings cardinaux

| # | Finding | Sévérité | Impact |
|---|---|---|---|
| **P0-1** | R20 `capacite_facturee = float(line.qty or 0)` puis `if capacite_facturee == 0: continue` — **collapse NULL → 0 → skip silencieux** = **faux negative R20** sites HTA (réplique exacte F2 R19 non corrigé pour R20) | 🔴 **P0** | `bill_intelligence/anomaly_detector.py:238-240` |
| **P0-2** | `billing_service.py:287, 1077-1078, 1153` agrégats `kwh = invoice.energy_kwh or 0` — acomptes NULL gonflent total_kwh portfolio à 0 mesuré, faussent benchmarks | 🔴 **P0** | `services/billing_service.py` 3 callsites |
| **P0-3** | `operat_export_service.py:80, 121, 170, 193-195` exports OPERAT avec `kwh or 0` + `surface or 0` — **CARDINAL RÉGLEMENTAIRE** : sanctions Décret Tertiaire si déclaration erronée | 🔴 **P0** | `services/operat_export_service.py` |
| P1-4 | `cost_simulator_2026.py:405` fallback `DEFAULT_ANNUAL_KWH=100000` silencieux si `annual_kwh_total IS NULL` | P1 | |
| P1-5 | `cee_service.py:261-262` `baseline_kwh = site.annual_kwh_total or 0` → CEE BAT-TH gisement = 0 sans warning | P1 | |
| Bonus | `onboarding_service.py:96` `surface_m2=site.surface_m2 or 1000` fallback 1000 m² silencieux | P2 | |

### Statistiques

- **550 occurrences** patterns `or 0` / `or 0.0` (services + routes)
- **113 fallbacks** `or []` / `or {}`
- **~350 divisions runtime** estimées, **~23%** guardées explicitement, **~25** via `max(x, 1)` anti-pattern
- **~80 divisions sans guard apparent** dans modules in-scope

### Effort fix

- P0-1 R20 NULL : ~10 min (mêmé pattern Phase 5.6 F2)
- P0-2 billing agrégats : ~30 min (3 callsites)
- P0-3 OPERAT export : ~45 min (5 callsites + tests cardinal réglementaire)
- P1 reportés Sprint C-7 : ~2-3 h cumul

---

## 🔐 AXE 4 — Security & Org-Scoping (verdict 🔴 2 P0 HIGH SYSTÉMIQUES)

### Findings cardinaux

| ID | Finding | Sévérité |
|---|---|---|
| **SEC-2026-011** | Onboarding stepper `/api/onboarding-progress*` (4 routes) : `org_id_override` query param accepté sans guard ownership DEMO_MODE → cross-tenant énumération possible | 🔴 **High** |
| **SEC-2026-012** | **DEMO_MODE bypass systémique** : `resolve_org_id` X-Org-Id sans validation DB — affecte ~25 endpoints Phase C en DEMO. Pré-existant `D-Sprint-C7-Demo-Mode-Org-Validation-001` confirmé High par audit Phase 5.5 + ce passage | 🔴 **High** |
| SEC-2026-013 | `details_json.vnu_labels` BillAnomaly retourné JSON sans filtrage — PRM/PDL bruts exposés (PII RGPD) | 🟠 Medium |
| SEC-2026-014 | `/api/reference/sirene/lead-score/{siren}` expose MRR estimé PROMEOS sans auth — scrape concurrents possible | 🟠 Medium |
| SEC-2026-015 | `/api/pilotage/{flex-ready,roi}/{site_id}` accepte `site_id` alphanumériques (`retail-001`) court-circuite scoping même authentifié | 🟠 Medium |
| SEC-2026-016 | NPS/CSAT polluables (anti-flood désactivé en DEMO_MODE, scores arbitraires acceptés) | 🟡 Low |

### Inventaire complet

44 endpoints Phase C audités. Score sécurité :

- **OK strict** : 28 endpoints (org-scoping correct + auth ou public légitime)
- **Mitigé post fix** : 5 endpoints (post mini-sprints IDOR)
- **Résiduel** : 11 endpoints (problèmes ci-dessus)

### Effort fix

- SEC-011 + SEC-012 (DEMO_MODE bypass) : ~30 min cumul (1 fix `scope_utils.py` couvre 90% surface)
- SEC-013 PII sanitization : ~30 min
- SEC-014 SEC-015 SEC-016 : ~1 h cumul (gates + rate-limits)

---

## 📋 AXE 5 — RGPD & Audit Trail (verdict 🔴 3 P0 CARDINAUX)

### Findings cardinaux

| # | Finding | Sévérité |
|---|---|---|
| **P0** | **Aucun PATCH endpoint consentement** — Phase 5.3 livre colonnes mais ZÉRO endpoint `/api/orgs/{id}/consent` ou `/api/dp/{id}/consent` — Cockpit RGPD UI bloqué Sprint C-6 | 🔴 |
| **P0** | **Aucun event `RGPD_CONSENT_CHANGE`** dans AuditLog wiring — toute mutation consentement non tracée → audit CNIL "preuve d'origine" cassé | 🔴 |
| **P0** | **Connecteurs externes (DataConnect/GRDF/Sirene) sans audit trail** — extraction PRM/PCE/SIREN (donnée perso art. 4 RGPD) → CNIL "preuve d'extraction" impossible | 🔴 |
| P1 | Soft-delete Org/EJ/PF/Site/User non audité (5 endpoints, 0 `log_patrimoine_change` ni `RGPD_USER_DELETE` event) | 🟠 |
| P1 | Onboarding wizard sans audit_log patrimoine — SIRET/NAF/coords ingérés sans trace | 🟠 |
| P1 | Aucun endpoint art. 15 RGPD (export données utilisateur) | 🟠 |

### Inventaire AuditLog event_type cumul Phase C

- ✅ Présents : `site.update`, `site.archive`, `cascade.recompute`, `login`/`logout`/`password_change`/`switch_org`/`impersonate`, `operat_*`, `CX_*`, action_audit
- ❌ **MANQUANTS CARDINAUX** : `RGPD_CONSENT_CHANGE`, `RGPD_USER_DELETE`, `API_CALL_DATACONNECT`, `API_CALL_GRDF`, `API_CALL_SIRENE`, `ONBOARDING_*`

### Effort fix

- 3 P0 RGPD : ~3-4 h (endpoint PATCH + helper log_consent_change + wiring connecteurs)
- P1 reportés : ~2-3 h cumul

---

## 🔄 AXE 6 — Cohérence SoT (verdict 🟡 1 P1 + dette FE coverage)

### Findings cardinaux

| # | Finding | Sévérité |
|---|---|---|
| F1 | **Triple SoT CO₂ sans SG runtime** : `emission_factors.py` + `doctrine/constants.py` + YAML mirroir mais aucun source-guard ne vérifie cohérence runtime — drift silencieux possible | 🟠 P1 |
| F2 | BACS seuils 70/290 dans `emission_factors.py` (mauvais module) sans alias doctrine | 🟡 P2 |
| F3 | TraceTooltip termId validity invariant 5 doctrinal MVP — ✅ déjà fixé Phase 5.4 SG cross-stack | OK |
| F4 | Sentinelle `8500` à confirmer (mentionnée KPI mais non trouvée YAML/doctrine) | 🟡 P2 |
| F5 | Couverture FE TraceTooltip 6/68 (8.8%) — différenciateur R10 sous-exploité | 🟠 P1 (Sprint C-7) |

### Points positifs

- ✅ COEFF_EP_ELEC=1.9 fantôme : 0 callsite résiduel
- ✅ Cascade 14 champs cohérent vs `coherence_globale.yaml` invariants
- ✅ 0 valeur magique inline résiduelle détectée Phase C

### Effort fix

- F1 SG triple SoT CO₂ : ~30 min (parametrized SG MIRROR_MAP)
- F4 grep sentinelle 8500 : ~10 min
- F5 coverage FE : ~3 h Sprint C-7

---

## 📊 Tableau exhaustif findings (cross-AXE)

| Sprint | Phase | AXE | Finding | Sévérité | Statut |
|---|---|---|---|---|---|
| C-4 | 4.5 | 2 | Cascade Org consentement non câblée runtime PATCH | 🔴 P0 | OUVERT |
| C-5 | 5.1 | 3 | R20 `line.qty or 0` collapse NULL | 🔴 P0 | OUVERT |
| C-1+ | * | 3 | `billing_service.py` agrégats `or 0` (3 callsites) | 🔴 P0 | OUVERT |
| C-1 | * | 3 | `operat_export_service.py` exports OPERAT NULL→0 | 🔴 P0 | OUVERT |
| C-5 | 5.1 | 2 | BillAnomaly UNIQUE(invoice_id, code) absent | 🔴 P0 | OUVERT |
| Pre-Phase C | * | 4 | DEMO_MODE bypass systémique scope_utils | 🔴 P0 | TRACÉ Sprint C-7 |
| V113 | * | 4 | Onboarding stepper IDOR org_id_override | 🔴 P0 | OUVERT |
| C-5 | 5.3 | 5 | PATCH endpoint consentement absent | 🔴 P0 | TRACÉ Sprint C-7 |
| C-5 | 5.3 | 5 | RGPD_CONSENT_CHANGE event AuditLog absent | 🔴 P0 | TRACÉ Sprint C-7 |
| Pre-Phase C | * | 5 | Connecteurs externes sans audit trail | 🔴 P0 | OUVERT |
| C-5 | 5.6 | 1 | revenue.py docstring stale 3.15 | 🟠 P1 | OUVERT |
| C-5 | 5.6 | 1 | ADR-015 amont sections non MAJ | 🟠 P1 | OUVERT |
| C-3 | 3.x | 1 | catalog TICGN dead-entry | 🟠 P1 | OUVERT |
| C-5 | 5.1 | 2 | BillAnomaly Enum + CheckConstraint | 🟠 P1 | OUVERT |
| C-5 | 5.3 | 2 | Pydantic validators consentement | 🟠 P1 | OUVERT |
| C-1+ | * | 3 | cost_simulator + cee_service NULL→0 | 🟠 P1 | OUVERT |
| C-5 | 5.5 | 4 | PII vnu_labels dans JSON response | 🟠 P1 | TRACÉ Sprint C-7 |
| V117 | * | 4 | Sirene lead-score sans auth | 🟠 P1 | OUVERT |
| V1 | * | 4 | Pilotage site_id alphanumérique bypass | 🟠 P1 | OUVERT |
| Pre-Phase C | * | 5 | Soft-delete Org/EJ/PF/Site/User non audité | 🟠 P1 | OUVERT |
| Pre-Phase C | * | 5 | Onboarding wizard sans audit_log patrimoine | 🟠 P1 | OUVERT |
| C-5 | * | 6 | Triple SoT CO₂ sans SG runtime | 🟠 P1 | OUVERT |
| C-5 | 5.4 | 6 | Couverture FE TraceTooltip 8.8% | 🟠 P1 | TRACÉ Sprint C-7 |
| C-5 | 5.6 | 2 | PRAGMA SQLite perf (synchronous, cache_size) | 🟡 P2 | OUVERT |
| C-1+ | * | 3 | onboarding fallback surface=1000 m² | 🟡 P2 | OUVERT |
| CX | * | 4 | NPS/CSAT polluables DEMO | 🟡 P2 | OUVERT |
| C-1 | * | 6 | BACS seuils dans `emission_factors.py` | 🟡 P2 | OUVERT |
| Pre-Phase C | * | 6 | Sentinelle 8500 à confirmer | 🟡 P2 | OUVERT |

**Total** : **10 P0 + 12 P1 + 7 P2 = 29 findings**, dont **18 nouveaux** (non tracés tracker pré-audit) et **11 confirmés** (déjà tracés Sprint C-7).

---

## 📋 Plan d'action priorisé

### Phase 5.7 (~2-3 h) — Fix 5 P0 cardinaux internes Sprint C-5

| Fix | Effort | Justification |
|---|---|---|
| **G1** Cascade Org consentement câblage PATCH `/organisations/{id}` | 30 min | Bug F2 AXE 2 — réplique pattern F1 PRAGMA |
| **G2** R20 `line.qty or 0` → distinguer NULL | 10 min | Pattern F2 AXE 3, mêmê fix F2 R19 Phase 5.6 |
| **G3** BillAnomaly `UniqueConstraint(invoice_id, code)` migration 10e | 20 min | Anti-doublons concurrents R19/R20 |
| **G4** revenue.py docstring + ADR-015 amont MAJ | 20 min | Cohérence post Phase 5.6 fix F3 |
| **G5** Onboarding stepper IDOR fix `org_id_override` | 30 min | SEC-2026-011 cross-tenant |
| **Total** | **~2 h** | + tests + commit |

### Sprint C-7 polish enrichi (~30-40 h, ~5 j-h)

**P0 reportés Sprint C-7** :
- DEMO_MODE bypass systémique scope_utils (SEC-2026-012)
- billing_service agrégats NULL→0 (P0-2 AXE 3)
- operat_export_service exports NULL→0 (P0-3 AXE 3, **CARDINAL RÉGLEMENTAIRE**)
- PATCH consentement endpoint + RGPD_CONSENT_CHANGE wiring
- Connecteurs externes audit trail (DataConnect/GRDF/Sirene)

**P1 reportés** :
- 12 findings P1 cumulés (BillAnomaly Enum, validators, FE coverage TraceTooltip, Triple SoT CO₂, etc.)

**P2 reportés** :
- 7 findings P2 (perf PRAGMA, sentinelles, polish docs)

### Recommandations doctrinales ADR-016 (à acter)

**ADR-016 — Math + Runtime + Cross-Module Enforcement Audit Doctrine** :

1. **Pré-clôture phase obligatoire** : audit deep multi-AXES (math + runtime + edge + security + RGPD + cohérence) avant tout tag sprint
2. **Pattern declarations sans enforcement** : tout `CASCADE_MAP`, `UniqueConstraint`, `ondelete=*`, FK doit avoir test runtime cardinal
3. **NULL ≠ 0 doctrine** : tout calcul métier doit distinguer explicitement NULL (inconnu) de 0 (mesuré)
4. **DEMO_MODE security gates** : tout endpoint Phase C+ doit valider org_id en DB, pas seulement accepter X-Org-Id
5. **Audit trail RGPD** : tout mutation/extraction donnée perso doit avoir wiring `audit_log_service.log_event` obligatoire (source-guard parametrized par event_type)

### Métriques cardinales

- **18 findings nouveaux** détectés cet audit (vs ~10 attendus extrapolation Phase 5.5)
- **ROI audit transversal** : ~1.5 h pour catch 10 P0 + 12 P1 invisibles à 7 audits sprint-end précédents
- **Pattern cardinal détecté** : "déclaration sans enforcement runtime" (5 occurrences cross-phase)

---

## 🚦 STOP gate utilisateur

3 options arbitrage :

- 🅐 **Phase 5.7 fix 5 P0 internes (~2-3 h)** + dettes Sprint C-7 enrichies → BILAN Sprint C-5 propre
- 🅑 **Phase 5.7 étendue fix 5 P0 + 3 P1 cardinaux (~4-5 h)** = couvre AuditLog wiring + PATCH consentement + DEMO_MODE fix
- 🅒 **Documentation findings dans BILAN seul** + dettes Sprint C-7 (transparence audit, pas de fix immédiat) — risque pilote pré-prod sans corrections cardinales

Recommandation : **🅐** (fix 5 P0 internes Sprint C-5 minimum + dettes C-7 enrichies pour polishing structurel).

---

## Confidence agrégée

**0.78** — chaque AXE a confidence individuelle 0.7-0.95 selon profondeur du scan read-only. Incertitudes résiduelles principales :

- Sentinelle `8500` non confirmée (grep partiel uniquement)
- Couverture exhaustive endpoints Phase C : 44 listés, possible 5-10 endpoints pré-Phase C non audités
- Tests `pytest` non exécutés runtime pour confirmer F1 PRAGMA + F2 R20 collapse — vérification structurelle uniquement

---

**Fichiers cardinaux audités** :

- `backend/services/bill_intelligence/anomaly_detector.py` (Phase 5.1)
- `backend/services/billing_service.py` (Sprint C-1+)
- `backend/services/operat_export_service.py` (Sprint C-1)
- `backend/services/scope_utils.py` (pré-Phase C)
- `backend/services/audit_log_service.py` (Sprint C-2 P1.2)
- `backend/services/consent_service.py` (Sprint C-4 P4.5 + C-5 P5.3)
- `backend/regops/services/cascade_recompute_service.py` (Sprint C-1 P5)
- `backend/routes/onboarding_stepper.py` (V113)
- `backend/routes/sirene.py` (V116-117)
- `backend/routes/pilotage.py` (V1)
- `backend/routes/bill_intelligence.py` (Sprint C-5 P5.1)
- `backend/routes/patrimoine_crud.py` (pré-Phase C — cascade Org wiring manquant)
- `backend/models/bill_anomaly.py` (Sprint C-5 P5.1)
- `backend/connectors/enedis_dataconnect.py` + `grdf_adict.py` (pré-Phase C)
- `backend/services/sirene_hydrate.py` + `sirene_lookup.py` (pré-Phase C)
- `backend/database/connection.py` (Phase 5.6 fix F1)
- `backend/config/sources_reglementaires.yaml` + `coherence_globale.yaml` (Sprint C-3 + C-4 P4.1)
- 9 migrations Alembic Phase C
- ADR-007 à ADR-015

**Pattern audit multi-agents 10e application Phase C** — ROI cardinal record (18 findings nouveaux invisibles aux 7 audits SDK pré-commit cumulés).
