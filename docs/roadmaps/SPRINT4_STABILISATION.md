# Sprint 4 — Billing canonique, KPI runtime, review robuste

**Date :** 2026-03-17
**Branche :** `ux/cockpit-v3`
**Commit :** `a32ad06`

---

## 1. Résumé exécutif

| Chantier | Livré | Risque |
|----------|-------|--------|
| Billing canonique | Contrat Pydantic complet (invoice + line items + gap report) | Nul |
| KPI runtime traçables | `kpi_details[]` dans cockpit avec métadonnées | Faible |
| compliance_needs_review robuste | 4 critères + reason codes | Faible |
| CI smoke E2E visible | Step id + GITHUB_STEP_SUMMARY | Nul |
| UI badge needsReview | "N à revoir" dans sous-titre registre | Faible |

**Non traité** : connecteurs Enedis/Météo, refonte Cockpit.jsx, RGPD complet.

---

## 2. Fichiers modifiés

| Fichier | Rôle | Risque |
|---------|------|--------|
| `backend/schemas/billing_canonical.py` | Contrat invoice canonique | Nul |
| `backend/schemas/conformite_schemas.py` | Schemas EFA + findings | Nul |
| `backend/schemas/kpi_catalog.py` | +wrap_kpi_runtime() | Nul |
| `backend/schemas/__init__.py` | Re-exports | Nul |
| `backend/routes/cockpit.py` | +kpi_details[] dans réponse | Faible |
| `backend/routes/patrimoine/_helpers.py` | _compute_compliance_review_status() + reasons | Faible |
| `backend/tests/test_invariants.py` | +test needs_review has reasons | Nul |
| `.github/workflows/quality-gate.yml` | Step smoke id + summary | Nul |
| `frontend/src/pages/Patrimoine.jsx` | +needsReview dans stats + badge UI | Faible |

---

## 3. Détail des changements

### A. Billing canonique

```python
class BillingInvoiceCanonical(BaseModel):
    site_id: int          # > 0
    contract_id: int?     # > 0
    supplier_name: str    # 1-300 chars
    invoice_ref: str?     # max 100
    currency: str         # default "EUR"
    amount_ht: float      # 0 - 100M
    amount_ttc: float?    # 0 - 100M
    energy_unit: str      # default "kWh"
    energy_total: float?  # >= 0
    period_start: date
    period_end: date
    pricing_effective_date: date?
    line_items: List[BillingLineItem]
```

+ `BillingGapReport` pour documenter les champs présents/manquants/dérivables.

### B. KPI runtime traçables

Réponse `GET /api/cockpit` enrichie avec :
```json
{
  "kpi_details": [
    {
      "kpi_id": "compliance_score_composite",
      "value": 84.4,
      "unit": "score 0-100",
      "period": "instantané",
      "perimeter": "organisation",
      "source": "services/compliance_score_service.py:143-265",
      "traceable": true,
      "name": "Score de conformité composite"
    },
    ...
  ]
}
```

3 KPI wrappés : compliance_score, risque_financier, completeness.

### C. compliance_needs_review robuste

Avant : simple booléen `A_RISQUE in statut`.

Après : `_compute_compliance_review_status()` avec 4 critères :

| Critère | Code raison | Condition |
|---------|-------------|-----------|
| Non-conformité | `non_conforme` | DT ou BACS = NON_CONFORME |
| Risque réglementaire | `a_risque` | DT ou BACS = A_RISQUE |
| Patrimoine incomplet | `surface_manquante`, `siret_manquant` | surface ≤ 0, siret vide |
| Risque financier élevé | `risque_eleve` | risque > 10 000 € |
| Score critique | `score_critique` | compliance_score < 50 |

Sérialisation :
```json
{
  "compliance_needs_review": true,
  "compliance_review_reasons": ["a_risque", "surface_manquante"]
}
```

### D. CI smoke E2E visible

```yaml
- name: Smoke E2E (chain validation)
  id: smoke
  run: npx playwright test smoke.spec.js e7-sprint1-chain.spec.js --reporter=list
  timeout-minutes: 5

- name: Smoke E2E summary
  if: always()
  run: |
    echo "## Smoke E2E Results" >> $GITHUB_STEP_SUMMARY
    # ✅ ou ❌ selon outcome
```

### E. UI badge needsReview

- Compteur `needsReview` dans le memo stats
- Affiché dans le sous-titre registre : "N à revoir"
- Visible uniquement si > 0

---

## 4. Tests exécutés

| Suite | Résultat |
|-------|----------|
| Backend (44 tests) | **44 passed** (12.5s) |
| Frontend build | **OK** (21.5s) |
| Lint (ruff + ESLint) | **OK** |

---

## 5. Régressions potentielles

| Risque | Probabilité | Vérification |
|--------|------------|-------------|
| kpi_details casse un consommateur front | Très faible | Champ ajouté, pas modifié |
| needs_review trop large (faux positifs) | Faible | Critères documentés, ajustables |
| Badge "à revoir" non traduit | Nul | Texte FR natif |

---

## 6. Bilan global des 5 sprints

| Sprint | Focus | Tests | Commit |
|--------|-------|-------|--------|
| Sprint 0 | JWT + Alembic + api.js split | 31 | `56aa4d6` |
| Sprint 1 | patrimoine.py + ConformitePage + PII + E2E | 31 | `3b9d070` |
| Sprint 2 | APIError + schemas + KPI doc + invariants | 38 | `e7676d5` |
| Sprint 3 | Schemas élargi + KPI catalog + smoke CI + desync | 43 | `9488d80` |
| Sprint 4 | Billing canonical + KPI runtime + review robuste | 44 | `a32ad06` |

---

## 7. TODO Sprint 5

| # | Action | Effort | Priorité |
|---|--------|--------|----------|
| 1 | Merge ux/cockpit-v3 → main | S | Haute |
| 2 | Connecteur Enedis (structure OAuth) | M | Haute |
| 3 | Connecteur Open-Meteo réel | S | Moyenne |
| 4 | Rate limiting global | S | Moyenne |
| 5 | RGPD : export/suppression données | M | Basse |
| 6 | Refactorer Cockpit.jsx | M | Basse |
| 7 | Schemas Pydantic sur routes restantes | M | Basse |
| 8 | Billing canonical appliqué aux routes import | M | Basse |
