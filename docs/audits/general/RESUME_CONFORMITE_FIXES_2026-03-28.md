# RÉSUMÉ — Corrections Conformité P0+P1 — 28 mars 2026

## Branche : `fix/conformite-audit-upgrade` (5 commits)

## Score audit : 78/100 → 90/100 (estimé après corrections)

---

## Commits

| # | SHA | Type | Description | Impact |
|---|-----|------|-------------|--------|
| 1 | `caf7999` | fix(conformite) | Poids scoring alignés DT=45% BACS=30% APER=25% | P0-2 résolu. DPE/CSRD supprimés de regs.yaml. Source unique. |
| 2 | `a9d6e84` | fix(tests) | 2 tests réparés (breakdown 3→5, format erreur actions) | P1-2 auto-résolu par commit 1. P1-3 adapté au nouveau format. |
| 3 | `4cad790` | fix(security) | Org-scoping sur 13 endpoints BACS site-based | P0-1 résolu. `_verify_site_access()` + `resolve_org_id()` + `get_optional_auth`. DEMO_MODE préservé. |
| 4 | `4d7730b` | fix(conformite) | APER détecté dans RegAssessment scoring | P1-1 + P1-6 résolus. `_detect_frameworks()` multi-framework. Score 90.4→84.0. Confidence low→high. |
| 5 | `5ef9655` | test(conformite) | 22 source guards (poids, seuils, pénalités) | Anti-régression sur les valeurs canoniques. |

---

## Résultats tests

| Suite | Avant | Après |
|-------|:-----:|:-----:|
| compliance_engine | 49/49 | 49/49 |
| compliance_v1 | 42/42 | 42/42 |
| compliance_score_service | 5/6 (**1 FAIL**) | 24/24 |
| regops_rules | 16/16 | 16/16 |
| regops_hardening | 30/30 | 30/30 |
| bacs_engine | 34/34 | 34/34 |
| bacs_v2_compliance | 11/11 | 11/11 |
| bacs_compliance_gate | 11/11 | 11/11 |
| bacs_exemption_workflow | 17/17 | 17/17 |
| bacs_regulatory_engine | 15/15 | 15/15 |
| bacs_api | 16/16 | 16/16 |
| step29_aper | 27/27 | 27/27 |
| action_close_rules | 18/19 (**1 FAIL**) | 19/19 |
| **conformite_source_guards** | — | **22/22** (nouveau) |
| **TOTAL** | **276 pass, 2 fail** | **333 pass, 0 fail** |

---

## Definition of Done

- [x] **Poids scoring** : DT=45, BACS=30, APER=25 dans regs.yaml (source unique)
- [x] **Poids cohérents** : code, YAML, docstring — une seule valeur
- [x] **2 tests réparés** : breakdown frameworks + action close format
- [x] **BACS org-scoping** : 13 endpoints site-based avec vérification site → org
- [x] **APER détecté** : `_detect_frameworks` reconnaît tous les frameworks par assessment
- [x] **Score réaliste** : site #1 passe de 90.4 à 84.0 (APER compté)
- [x] **High confidence** : site #1 HELIOS en high confidence (3/3 frameworks)
- [x] **Scoring contextuel** : chaque site a un profil d'applicabilité différent (vérifié)
- [x] **Source guards** : 22 tests sur poids 45/30/25, seuils 290/70, pénalité 7500
- [x] **0 régression** : 333/333 tests passent
- [x] **5 commits atomiques** (vs 7 prévus — certains P1 résolus en cascade)

---

## Items restants (non bloquants)

| # | Item | Priorité | Note |
|---|------|----------|------|
| P1-4 | BACS 70kW deadline 2030 vs 2027 | P1 | Décret n°2025-1343 cité — vérifier sur Légifrance |
| P1-5 | Trajectoire DT (-40/-50/-60%) absente du RegOps rule | P1 | Géré séparément par operat_trajectory.py — pas bloquant |
| P2-1 | regops.py org-scoping partiel | P2 | Moins critique que BACS (dashboard read-only) |
| P2-3 | datetime.utcnow() deprecated (32 warnings) | P2 | Python 3.14 warning, pas bloquant avant 3.15 |
| P2-4 | Pas d'endpoint RegOps tertiaire d'évaluation fresh | P2 | Fonctionnel via compliance/recompute-rules |
| P2-5 | BACS pénalité 7500€ non sourcée réglementairement | P2 | Estimation conservative |
| UI | ComplianceScoreHeader.jsx tooltip dit "45/30/25" | OK | Maintenant correct (regs.yaml aligné) |

---

## Fichiers modifiés

```
backend/regops/config/regs.yaml                    (+6, -6)   Poids scoring
backend/tests/test_action_close_rules_v49.py       (+3, -2)   Fix format erreur
backend/routes/bacs.py                              (+73, -19) Org-scoping
backend/services/compliance_score_service.py        (+32, -16) Multi-framework detection
backend/tests/test_conformite_source_guards.py      (+150)     Source guards (nouveau)
```

**Total : 264 lignes ajoutées, 43 supprimées.**

---

*Corrections réalisées le 28 mars 2026.*
*Branche : `fix/conformite-audit-upgrade` — prête pour merge dans main.*
