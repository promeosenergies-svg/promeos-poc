# Backlog Vague D Sprint 2 — Progress bars DT/BACS/APER SolPanel

> **Origine** : Sprint 1 Vague B phase B3 SKIP (23 avril 2026)
> **Vigilance V1 du prompt Vague B** : « Avant de coder, grep pour confirmer
> l'endpoint. Si endpoint absent ou shape insuffisante → SKIP B3, documenter
> pour Sprint 2 Vague D, ne pas créer un endpoint Vague B (scope creep). »

## Contexte

La refonte Sol a perdu les 3 progress bars DT/BACS/APER qui vivaient dans
`NavPanel.jsx` (main) section Conformité. L'audit fresh §3 les avait
identifiées comme feature à restaurer (Top 1 valeur métier DAF/RSE).

## État API backend (audit B3.1, 2026-04-23)

### ✅ Endpoint existant
`GET /api/compliance/portfolio/summary?org_id=X` — `backend/routes/compliance.py:506`

Délègue à `compute_portfolio_compliance_summary` dans
`backend/services/compliance_readiness_service.py:446`.

### ❌ Shape insuffisante
Le summary retourne :
- `kpis.data_blocked/warning/ready` (counts par gate status)
- `sites[*]` avec `score` composite + readiness + applicability
- `top_blockers`, `deadlines.d30/90/180/beyond`, `untrusted_sites`

**Mais PAS** d'agrégation `dt_score`, `bacs_score`, `aper_score` au
niveau portfolio. Les scores par framework existent au niveau SITE via
`compliance_score_service.ComplianceScoreResult.breakdown[*]`
(FrameworkScore avec framework / score / weight), mais **le service
portfolio ne les agrège pas**.

### Besoin pour B3 frontend
```json
{
  "org_id": 1,
  "total_sites": 12,
  ...existing...,
  "framework_scores": {
    "dt":   { "avg": 68, "sites_evaluated": 10, "weight": 0.45 },
    "bacs": { "avg": 72, "sites_evaluated":  7, "weight": 0.30 },
    "aper": { "avg": 55, "sites_evaluated":  4, "weight": 0.25 }
  }
}
```

## Travail Vague D proposé

### Backend (~1h)
1. Enrichir `compute_portfolio_compliance_summary` :
   - Itérer sur `sites` pour appeler `compute_compliance_score_with_breakdown`
   - Moyenner par framework parmi les sites où `FrameworkScore.available`
   - Ajouter `framework_scores` au dict retourné
2. Test backend : `backend/tests/test_compliance_portfolio_summary.py`
   - 3 sites avec RegAssessment DT=60,80,70 → `framework_scores.dt.avg=70`
   - Sites sans RegAssessment skip (weight adjusted)

### Frontend (~45 min)
1. Service `getPortfolioComplianceSummary` expose déjà les params.
   Hook `useCompliancePortfolioSummary({ enabled: currentModule === 'conformite' })`
2. Composant `ui/sol/SolProgressBars.jsx` (voir prompt B3.2 original) :
   - 3 barres horizontales compact (DT/BACS/APER) × 1.5 kW h tokens Sol
   - `role="progressbar"` + `aria-valuenow/min/max` + `aria-label`
   - `getComplianceScoreColor(value)` → vert/jaune/rouge selon seuils
3. Intégration SolPanel conditionnelle `currentModule === 'conformite'`
   entre section Pins/Recents et sections NAV.
4. Tests source-guards + wiring (~10 cas).

### Commits Vague D B3
- `feat(backend): add framework_scores aggregation to portfolio summary`
- `feat(sol-panel): add SolProgressBars component`
- `feat(sol-panel): integrate progress bars in conformite module`
- `test(sol-progress-bars): rendering + clamp + accessibility`

## Décision produit à arbitrer

- **Tiebreaker DT/BACS/APER** : si un site n'a PAS d'assessment pour un
  framework (ex. trop petit pour BACS), faut-il le compter avec score 0
  ou l'exclure de la moyenne ? → impact sur affichage portfolio
  (défavorise les DG avec petits sites non assujettis).
- Reco : exclure du dénominateur. Shape backend inclut
  `sites_evaluated` pour contextualiser.

## Lien avec autres backlogs

- [BACKLOG_P5_AUDIT_SME_API.md](./BACKLOG_P5_AUDIT_SME_API.md) : si
  Audit SMÉ devient aussi un 4ᵉ framework dans portfolio summary, ajuster
  le `ComplianceScoreResult.formula` simultanément.
