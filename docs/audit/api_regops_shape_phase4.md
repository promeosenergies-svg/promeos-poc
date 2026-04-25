# Audit API RegAssessment + endpoints Conformité — Lot 6 Phase 4 pré-flight 2

> **Date** : 2026-04-19
> **Contexte** : le prompt Phase 4 Lot 6 spécifie 4 endpoints ORG-level (`/api/v1/regops/assessment?org_id=X`, `/operat-trajectory`, `/compliance-portfolio`, `/score-explain`) qui doivent alimenter le hero `/conformite/tertiaire`. Ce pré-flight vérifie la shape réelle.

## Résultat — MULTIPLES endpoints spec ABSENTS de l'API actuelle

| Endpoint spec | Statut réel |
|---|---|
| `/api/v1/regops/assessment?org_id=1` | ❌ HTTP 404 — prefix `v1` absent, route ORG-level inexistante |
| `/api/v1/regops/operat-trajectory?org_id=1` | ❌ inexistant |
| `/api/v1/regops/compliance-portfolio?org_id=1` | ❌ inexistant |
| `/api/v1/regops/score-explain?org_id=1` | ❌ inexistant |
| `/api/regops/site/{site_id}` | ✅ EXISTE (SITE-level seulement) |
| `/api/tertiaire/dashboard` | ✅ EXISTE — shape simple agrégats EFA |

## Shape `/api/regops/site/{site_id}` (SITE-level, pas ORG)

Réponse observée sur `/api/regops/site/3` (HELIOS pack) :

```json
{
  "site_id": 3,
  "global_status": "UNKNOWN",
  "compliance_score": 49.32,
  "next_deadline": "2026-09-30",
  "findings": [
    {
      "regulation": "TERTIAIRE_OPERAT",
      "rule_id": "OPERAT_NOT_STARTED",
      "status": "AT_RISK",
      "severity": "HIGH",
      "confidence": "HIGH",
      "legal_deadline": "2026-09-30",
      "explanation": "Declaration OPERAT non demarree. Echeance: 2026-09-30.",
      "missing_inputs": [],
      "category": "obligation"
    },
    /* autres findings TERTIAIRE_OPERAT / BACS / APER / CEE_P6 */
  ],
  "actions": [ /* action_code, label, priority_score, urgency_reason, owner_role, effort */ ],
  "missing_data": [],
  "deterministic_version": "894d84ef68af2444"
}
```

**Champs présents** :
- `compliance_score` (float 0-100) ✅
- `global_status` ✅ (enum `COMPLIANT | AT_RISK | NON_COMPLIANT | UNKNOWN | OUT_OF_SCOPE | EXEMPTION_POSSIBLE`)
- `next_deadline` ✅ (date ISO)
- `findings[]` avec `regulation`, `rule_id`, `status`, `severity`, `legal_deadline`, `category` ('obligation' | 'incentive')

**Champs spec mentionnés ABSENTS** :
- `weights_used` (pas de pondérations DT39/BACS28/APER17/AUDIT16 exposées)
- `frameworks_applicable` avec `weight_pct` par framework (dérivable côté client depuis `findings[].regulation` distinct mais pas de metadata weights)
- `penalty_risk_eur` agrégé (pas de montant pénalité exposé, seuls les `legal_deadline`)
- `operatTrajectory.gap_to_2030_pct` (trajectoire chiffrée inexistante, on a seulement le rule `TRAJECTORY_NOT_EVALUABLE` si data insuffisante)
- `audit_sme_status` (absent de cet endpoint — voir section dédiée ci-dessous)
- `score_explain` (aucun endpoint dédié)

## Shape `/api/tertiaire/dashboard` (ORG-level existant)

Réponse observée :

```json
{
  "total_efa": 10,
  "active": 9,
  "draft": 0,
  "closed": 1,
  "open_issues": 4,
  "critical_issues": 0
}
```

Compteurs simples agrégés au niveau organisation. **Zéro formule à calculer côté frontend** → aucun risque de violer la règle « zéro business logic en front ».

## Audit SMÉ — scope ORG confirmé mais endpoint manquant

**Fichier** : `backend/services/audit_sme_service.py`

Fonctions détectées :
- `compute_score_audit_sme(audit_record, obligation, statut) -> float` (ligne 170)
- `get_audit_sme_assessment(...)` (ligne 178)
- `compute_global_score_with_audit_sme(..., audit_sme_applicable: bool, ...)` (ligne 283-296)

Le paramètre `audit_sme_applicable: bool` confirme que **Audit SMÉ est une règle au scope organisation** (personne morale ≥ 250 salariés ou CA ≥ 50 M€, cf. directive 2012/27/UE). Le test guard Phase 4.0 `audit_sme_scope.test.js` qui interdit `site.audit_sme_*` tient.

**Cependant** : aucun endpoint API expose `audit_sme_status` pour consommation frontend. Le service backend l'utilise en interne pour composer le score global, mais il n'y a pas de `/api/audit-sme/status?org_id=X` accessible.

→ **Conséquence** : le 4ᵉ KPI optionnel "Audit SMÉ" du prompt Phase 4.3 est reporté en backlog Phase 5 (voir `docs/backlog/BACKLOG_P5_AUDIT_SME_API.md`).

## Mapping KPI hero Conformité Tertiaire ↔ champ backend

**Proposition A retenue** (site-level via scope switcher + ORG-level dashboard agrégats, combinaison honnête) :

Le hero `/conformite/tertiaire` consomme `/api/tertiaire/dashboard` (ORG-level, existant) pour ses 3 KPIs. Pas de `RegAssessment` dans ce hero car cet endpoint est SITE-level (pour `/regops/:id`, déjà refait Phase 3 Lot 3 RegOpsSol).

| KPI hero Phase 4 | Champ backend | Calcul |
|---|---|---|
| **KPI 1** EFA actives | `dashboard.active` + `dashboard.total_efa` | display "N actives / total" |
| **KPI 2** Issues ouvertes | `dashboard.open_issues` | display count + tone selon critical |
| **KPI 3** Issues critiques | `dashboard.critical_issues` | display count + priorité visuelle |

Optionnellement, narrative hero peut référencer `getTertiaireEfas()` pour lister top EFA à échéance proche (dérivé client : tri par `reporting_start` ou rapprochement avec EFA records).

**Pas de KPI Pénalité €** (absent API) — skip plutôt que N/A frustrant.
**Pas de badges weights** (absents API) — badges frameworks sans pourcentage si ventilation souhaitée.

## 7ᵉ remap assumé (discipline honnêteté Lot 6)

| Phase | Remap |
|---|---|
| P3 Contrats | weighted_price null vs 0 si 100% indexé |
| P4 Renouv | bestImpactCumulativeEur → readiness_score |
| P4 Renouv | totalScenariosCount → expiredCount |
| P5 Usages | efficiency_potential_mwh → readiness_score |
| P6 Horaires | hp_pct/hc_pct/shift_potential → behavior_score/offhours_pct/baseload_kw |
| P7 Watchers | active_count/coverage_pct → total_count/new_events_count |
| **P4 Lot 6** | **RegAssessment ORG + weights_used + penalty_risk_eur + operatTrajectory.gap → /tertiaire/dashboard agrégats (total_efa, active, open_issues, critical_issues)** |

## Assertion Audit SMÉ scope

```
ASSERT: Audit SMÉ EST évalué au niveau ORGANISATION (personne morale).
Source : backend/services/audit_sme_service.py:288 — fonction
compute_global_score_with_audit_sme prend audit_sme_applicable: bool
comme paramètre org-level, pas site-level.
Conséquence : tout composant frontend qui lirait `site.audit_sme_*`
est un bug architectural. Le test guard audit_sme_scope.test.js
(Phase 4.0) protège ce contrat.
```

## Décision règle 2 surveillance user (2026-04-19)

> « Si pré-flight 2 révèle un 7ᵉ remap, STOP et reviens me voir avant P4.1 pour adapter la spec. »

**STOP honoré**. User a validé **Proposition A** (adaptation honnête à la data réelle) après présentation du diagnostic, GO P4.0+ avec spec amendée :
- Hero lit `/api/tertiaire/dashboard` au lieu de RegAssessment ORG-level inexistant
- 3 KPIs (EFA actives / Issues ouvertes / Issues critiques) au lieu de 4 KPIs (compliance_score + trajectoire + frameworks + pénalité)
- Audit SMÉ reporté backlog P5 (endpoint à exposer)
- Test guards 4.0 amendés avec whitelist `findings.ops` (autoriser lecture enums `regulation/rule_id/status/severity` comme display pur)
