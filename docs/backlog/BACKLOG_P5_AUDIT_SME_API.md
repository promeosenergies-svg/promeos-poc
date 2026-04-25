# Backlog Phase 5 Lot 6 — 3 demandes backend

> **Date de création** : 2026-04-19
> **Origine** : Lot 6 Phase 4 pré-flight 2 ([`docs/audit/api_regops_shape_phase4.md`](../audit/api_regops_shape_phase4.md))
> **Statut** : en attente d'arbitrage produit + PR backend Yannick ou équipe

Pendant la Phase 4 Conformité Tertiaire, l'audit API a révélé 3 absences d'endpoints qui forcent des compromis dans le hero Sol. Ce backlog consigne les 3 demandes produit à proposer à l'équipe backend pour un hero plus complet en Phase 5 (ou itération ultérieure).

## Demande 1 — Endpoint `GET /api/regops/portfolio-summary?org_id=X`

**Rationale** : l'API actuelle `/api/regops/site/{site_id}` est SITE-level. Pour un hero ORG-level (hub `/conformite/tertiaire`) avec des KPIs agrégés portefeuille (compliance_score moyen pondéré, frameworks applicables, pénalité cumulée), il faudrait un endpoint portefeuille.

**Shape souhaitée** :
```json
{
  "org_id": 1,
  "sites_count": 10,
  "compliance_score_avg": 68.3,
  "compliance_score_min": 42.0,
  "compliance_score_max": 89.5,
  "frameworks_applicable": {
    "TERTIAIRE_OPERAT": { "sites_count": 10, "weight_pct": 39 },
    "BACS": { "sites_count": 7, "weight_pct": 28 },
    "APER": { "sites_count": 4, "weight_pct": 17 },
    "AUDIT_SME": { "applicable_org": true, "weight_pct": 16 }
  },
  "weights_used": {
    "dt": 0.39, "bacs": 0.28, "aper": 0.17, "audit_sme": 0.16,
    "conditional_rules_version": "v3.1"
  },
  "penalty_risk_eur_total": 124500,
  "next_deadline_global": "2026-09-30",
  "deterministic_version": "894d84ef68af2444"
}
```

**Impact frontend** : le hero `ConformiteTertiaireSol.jsx` pourrait afficher les 4 KPIs du prompt original (compliance score composite, trajectoire 2030, frameworks badges avec poids, pénalité cumulée) au lieu des 3 compteurs simples de la Proposition A (EFA actives / Issues ouvertes / Issues critiques).

**Priorité** : P1 (hero pilote plus vendeur commercialement).

## Demande 2 — Endpoint `GET /api/audit-sme/status?org_id=X`

**Rationale** : Audit SMÉ est une règle au scope **organisation** (personne morale ≥ 250 salariés ou CA ≥ 50 M€, directive 2012/27/UE). Le backend a déjà le service `audit_sme_service.py` (fonctions `compute_score_audit_sme`, `get_audit_sme_assessment`, `compute_global_score_with_audit_sme`) mais aucun endpoint ne l'expose pour le frontend.

**Shape souhaitée** :
```json
{
  "org_id": 1,
  "applicable": true,
  "reason_applicable": "org.effectif_eti >= 250 · secteur tertiaire",
  "status": "pending|done|na|overdue",
  "deadline": "2026-10-11",
  "last_audit_date": "2022-10-11",
  "current_audit": {
    "id": 42,
    "prestataire": "Bureau Veritas",
    "statut": "draft",
    "progress_pct": 60
  },
  "score_audit_sme": 45.2,
  "source": "audit_sme_service"
}
```

**Impact frontend** : le hero afficherait un **4ᵉ KPI "Audit SMÉ"** avec countdown J-X vers deadline, déblocage des tooltips `audit_sme_org_scope` du glossaire. Gate règle protection `audit_sme_scope.test.js` conservée (scope ORG strict).

**Priorité** : P2 (règle spéciale Audit SMÉ est un différenciateur métier PROMEOS vs concurrents, mais absence actuelle non-bloquante en v2.4).

## Demande 3 — Enrichir `RegAssessment` avec `weights_used` + `penalty_risk_eur`

**Rationale** : l'endpoint SITE-level `/api/regops/site/{site_id}` expose `compliance_score` mais pas la ventilation. Les pondérations DT/BACS/APER/Audit SMÉ sont appliquées côté backend dans `compute_global_score_with_audit_sme` mais les poids effectifs ne remontent pas au frontend. Idem pour la pénalité monétaire par site.

**Shape enrichie souhaitée** :
```json
{
  "site_id": 3,
  "compliance_score": 49.32,
  "compliance_score_breakdown": {
    "dt_score": 45.0,
    "bacs_score": 50.0,
    "aper_score": 30.0,
    "audit_sme_score": null
  },
  "weights_used": {
    "dt": 0.39, "bacs": 0.28, "aper": 0.17, "audit_sme": 0.16,
    "conditional_rules_version": "v3.1"
  },
  "penalty_risk_eur": 15000,
  "penalty_breakdown": {
    "operat_2026": 7500,
    "bacs_2030": 3750,
    "aper_2028": 3750
  },
  /* ... reste de la shape actuelle (findings, actions, etc.) ... */
}
```

**Impact frontend** :
- Le hero RegOpsSol Phase 3 Lot 3 `/regops/:id` pourrait afficher un KPI "Pénalité potentielle" réel (actuellement dérivé client via `sumPenalties(findings)` qui n'a pas de montants hardcoded, donc déjà honnête mais absence de source backend autoritaire).
- Le test guard `test_no_compliance_logic_in_frontend_conformite.py` pourrait être durci : interdire toute lecture directe de `finding.estimated_penalty_eur` sans passer par `regAssessment.penalty_risk_eur` (obligation source unique).

**Priorité** : P2 (amélioration traçabilité + consolidation source unique · impact UX faible en v2.4 car le workaround actuel fonctionne).

## Demande 4 — `GET /api/compliance/portfolio/summary?site_id=X` (scope site-level)

**Rationale** : l'endpoint actuel (`backend/routes/compliance.py:506-520`, `compute_portfolio_compliance_summary(db, org_id)`) accepte uniquement `org_id`. Le frontend `CompliancePipelinePage.jsx` récupère toujours la shape ORG-level, même quand l'utilisateur navigue via `useScope` vers un site spécifique. Résultat : le hero Sol Phase 5 (`CompliancePipelineSol.jsx`) affiche "5 sites / 5 prêts" même en scope=HELIOS Paris.

**Solution envisagée** : ajouter un filtre `site_id: Optional[int]` dans la route + le service, qui restreint :

- `total_sites` à 1 (ou 0 si hors scope)
- `kpis.data_{blocked,warning,ready}` au gate_status du site unique
- `deadlines.{d30,d90,d180,beyond}` aux échéances du site
- `untrusted_sites` au site (s'il est untrusted)
- `sites[]` à 1 entrée

**Alternative rejetée** (discipline Lot 6) : filtre client-side sur `summary.sites` qui recomputerait KPIs + buckets deadlines + liste untrusted côté front. Violerait les source-guards P5.0 (`gate_status_literal_assign`, `days_remaining_bucket`, `trust_score_threshold`) et introduirait une divergence silencieuse backend/front.

**Impact frontend** : cohérence §3 non-négo — scope switcher wiring vrai, KPIs passent à 1/1 quand user navigue vers 1 site. Jusqu'à livraison backend, hero `CompliancePipelineSol` reste ORG-level (comportement aligné legacy `CompliancePipelinePage.jsx` qui ignore déjà `selectedSiteId` côté fetch).

**Priorité** : **P1** (cohérence UX nav scope, différenciateur "vérité visible").

## Récapitulatif priorités

| # | Demande | Impact hero | Priorité |
|---|---|---|---|
| 1 | `/api/regops/portfolio-summary` | 4 KPIs ORG-level vendeurs (score composite + trajectoire + frameworks + pénalité) | **P1** |
| 4 | `/api/compliance/portfolio/summary?site_id=` | Scope switcher cohérent hero Phase 5 (1/1 site HELIOS Paris) | **P1** |
| 2 | `/api/audit-sme/status` | 4ᵉ KPI Audit SMÉ différenciateur | P2 |
| 3 | Enrichir RegAssessment (`weights_used` + `penalty_risk_eur`) | Traçabilité + source unique pénalité | P2 |

## Workaround Phase 4 en attendant (Proposition A validée user 2026-04-19)

Le hero `ConformiteTertiaireSol.jsx` Phase 4 lit `/api/tertiaire/dashboard` (endpoint existant, ORG-level, agrégats simples) et affiche 3 KPIs honnêtes :

- EFA actives (dashboard.active / dashboard.total_efa)
- Issues ouvertes (dashboard.open_issues)
- Issues critiques (dashboard.critical_issues)

Cette approche évite la fabrication de KPIs fantômes (discipline honnêteté Lot 6 = 7/7 remaps) et sera upgradable vers la spec originale dès livraison d'un des 3 endpoints ci-dessus.
