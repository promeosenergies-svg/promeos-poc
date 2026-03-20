# Sprint 3 — Contrats élargis, KPI exécutables, chaîne renforcée

**Date :** 2026-03-17
**Branche :** `ux/cockpit-v3`
**Commit :** `9488d80`

---

## 1. Résumé exécutif

| Chantier | Livré | Risque |
|----------|-------|--------|
| Schemas conformité + billing | 7 schemas stricts Pydantic | Faible |
| KPI catalogue canonique | 7 KPI machine-readable + endpoint | Nul |
| Invariants transverses | +5 tests (total 12) | Nul |
| CI smoke E2E | Pipeline ciblé smoke + chain | Nul |
| Désync patrimoine/conformité | `compliance_needs_review` exposé | Faible |

**Non traité** : connecteurs Enedis/Météo, refonte Cockpit.jsx, RGPD complet.

---

## 2. Fichiers modifiés

| Fichier | Rôle | Risque |
|---------|------|--------|
| `backend/schemas/conformite_schemas.py` | Schemas EFA, findings, recompute | Nul |
| `backend/schemas/billing_schemas.py` | Schemas invoices, reconciliation, payment | Nul |
| `backend/schemas/kpi_catalog.py` | 7 KpiDefinition + get_kpi/list_kpis | Nul |
| `backend/schemas/__init__.py` | Re-exports | Nul |
| `backend/routes/cockpit.py` | +endpoint GET /api/kpi-catalog | Faible |
| `backend/routes/patrimoine/_helpers.py` | +compliance_needs_review | Faible |
| `backend/tests/test_invariants.py` | +5 tests transverses | Nul |
| `.github/workflows/quality-gate.yml` | Smoke E2E ciblé + timeout | Nul |
| `frontend/src/pages/Patrimoine.jsx` | +needsReview compteur | Faible |

---

## 3. Détail

### A. Schemas Pydantic conformité + billing

| Schema | Champs validés |
|--------|---------------|
| `RecomputeRequest` | org_id > 0, site_ids optionnel |
| `ComplianceFindingPatch` | status enum, assigned_to max 255, notes max 2000 |
| `EfaCreateRequest` | nom min 1, site_id > 0, annee 2000-2050, surface bounds |
| `EfaUpdateRequest` | Champs optionnels avec mêmes bounds |
| `InvoiceAuditRequest` | invoice_id > 0, force bool |
| `BillingReconcileRequest` | org_id > 0, site_ids, dates |
| `PaymentRuleCreate` | site_id > 0, rule_type, amount bounds |

### B. KPI catalogue canonique

Endpoint : `GET /api/kpi-catalog`

```json
{
  "count": 7,
  "kpis": [
    {"kpi_id": "compliance_score_composite", "name": "Score de conformité composite", "unit": "score 0-100", "traceable": true},
    ...
  ]
}
```

### C. Invariants transverses

| Test | Vérifie |
|------|---------|
| site_identity_consistent_across_modules | Même site_id cohérent patrimoine ↔ complétude |
| contract_references_valid_site | Contrat avec site_id invalide rejeté |
| kpi_has_required_metadata | KPI cards ont source non vide |
| error_format_on_conformite_404 | Erreur 404 tertiaire = format standard |
| kpi_catalog_endpoint | /api/kpi-catalog retourne structure valide |

### D. CI smoke E2E

Pipeline ciblé sur `smoke.spec.js` + `e7-sprint1-chain.spec.js` avec timeout 5 min.

### E. Désync patrimoine/conformité

- Backend : `compliance_needs_review` ajouté dans `_serialize_site()` (true si DT ou BACS = A_RISQUE)
- Frontend : compteur `needsReview` disponible dans le registre Patrimoine

---

## 4. Tests exécutés

| Suite | Résultat |
|-------|----------|
| Backend (43 tests) | **43 passed** (14s) |
| Frontend build | **OK** (22s) |

---

## 5. TODO Sprint 4

| # | Action | Effort | Priorité |
|---|--------|--------|----------|
| 1 | Merge ux/cockpit-v3 → main | S | Haute |
| 2 | Connecteur Enedis (structure OAuth) | M | Haute |
| 3 | Connecteur Open-Meteo réel | S | Moyenne |
| 4 | Rate limiting global | S | Moyenne |
| 5 | RGPD : export/suppression données | M | Basse |
| 6 | Refactorer Cockpit.jsx | M | Basse |
| 7 | Schemas Pydantic routes restantes | M | Basse |
| 8 | Badge needsReview visible dans UI tableau | S | Basse |
