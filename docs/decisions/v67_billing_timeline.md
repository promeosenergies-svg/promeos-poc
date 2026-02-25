# V67 — Billing Timeline & Coverage

> Date : 2026-02-24 | Branche : feat/v67-billing-timeline | Basé sur V66 (commit d5504dc)

---

## FAITS

| Fait | Source |
|------|--------|
| `period_start`, `period_end`, `issue_date` : Date nullable sur EnergyInvoice | billing_models.py |
| Aucun index sur les champs date | billing_models.py — scan complet sur range queries |
| Tous les endpoints GET retournaient `.all()` sans limit/offset | routes/billing.py (V66) |
| N+1 dans `get_billing_anomalies_scoped` : 1 + N requêtes Site | routes/billing.py:849-881 |
| Règle R4 détecte déjà les factures sans dates | billing_service.py |
| Unique constraint sur `(site_id, invoice_number, period_start, period_end)` | billing_models.py |
| 17 endpoints billing existants, tous org-scopés (V66) | routes/billing.py |
| Pas de champ `is_credit` — avoirs détectés via `total_eur <= 0` | billing_models.py |

---

## HYPOTHÈSES

| ID | Hypothèse | Décision |
|----|-----------|----------|
| H1 | SoT période = `period_start`/`period_end`, fallback `issue_date` → mois entier | Acceptée |
| H2 | Seuil couverture = 80% des jours du mois (`COVERAGE_THRESHOLD = 0.80`) | Acceptée |
| H3 | Avoirs (`total_eur <= 0`) exclus du calcul couverture, inclus dans totaux | Acceptée |
| H4 | Range auto = min(period_start, issue_date) → max(period_end, issue_date) | Acceptée |
| H5 | Calcul à la volée sans nouvelle table (cache mémoire org-scoped si perf insuffisante) | Acceptée |
| H6 | Nouvelle page `/billing` distincte de `/bill-intel` | Acceptée |

---

## DÉCISIONS

| ID | Décision | Justification |
|----|----------|---------------|
| D1 | Route frontend `/billing` (alias `/facturation`) | URL bookmarkable + filtres via `?site_id=` |
| D2 | `GET /api/billing/periods` paginé (limit=24, offset=0) | 24 mois = 2 ans visibles, load more UX |
| D3 | `GET /api/billing/coverage-summary` pour les KPIs header | Payload léger, compute global |
| D4 | `GET /api/billing/missing-periods` format patrimoine-anomaly | Compatible AnomaliesPage si besoin |
| D5 | Index SQLAlchemy sur period_start, period_end, issue_date, (site_id, period_start) | Sans migration manuelle |
| D6 | Fix N+1 `anomalies-scoped` : dict lookup via `Site.id.in_()` | 1 requête au lieu de N |

---

## CONTRAT API

### GET /api/billing/periods

**Query params :** `site_id` (int), `month_from` (YYYY-MM), `month_to` (YYYY-MM), `limit` (int, défaut 24, max 120), `offset` (int, défaut 0), `org_id` (int override)

**Response 200 :**
```json
{
  "periods": [
    {
      "month_key": "2024-12",
      "month_start": "2024-12-01",
      "month_end": "2024-12-31",
      "coverage_status": "covered",
      "coverage_ratio": 1.0,
      "invoices_count": 2,
      "total_ttc": 1234.56,
      "missing_reason": null
    }
  ],
  "total": 18,
  "offset": 0,
  "limit": 24
}
```

**coverage_status values :** `"covered"` (≥80%), `"partial"` (1-79%), `"missing"` (0%)

---

### GET /api/billing/coverage-summary

**Query params :** `site_id` (int), `org_id` (int override)

**Response 200 :**
```json
{
  "range": { "min_month": "2023-01", "max_month": "2025-02" },
  "months_total": 26,
  "covered": 22,
  "partial": 1,
  "missing": 3,
  "missing_months": ["2025-02", "2024-09", "2023-11"],
  "top_sites_missing": [
    { "site_id": 5, "site_name": "Site Alpha", "missing_months_count": 3 }
  ]
}
```

**Response 200 (aucune facture) :**
```json
{
  "range": null,
  "months_total": 0,
  "covered": 0,
  "partial": 0,
  "missing": 0,
  "missing_months": [],
  "top_sites_missing": []
}
```

---

### GET /api/billing/missing-periods

**Query params :** `limit` (int, défaut 20, max 100), `offset` (int, défaut 0), `org_id` (int override)

**Response 200 :**
```json
{
  "items": [
    {
      "month_key": "2025-02",
      "site_id": 5,
      "site_name": "Site Alpha",
      "coverage_status": "missing",
      "coverage_ratio": 0.0,
      "missing_reason": "Aucune facture importée pour ce mois",
      "regulatory_impact": { "framework": "FACTURATION" },
      "cta_url": "/bill-intel?site_id=5&month=2025-02"
    }
  ],
  "total": 12,
  "offset": 0,
  "limit": 20
}
```

---

## RÈGLES DE COUVERTURE

```
COVERAGE_THRESHOLD = 0.80  # configurable

Pour chaque mois M dans [range_start, range_end] :
  1. Collecter toutes les factures dont la période intersecte M
  2. Exclure avoirs (total_eur <= 0) du calcul couverture
  3. Pour chaque facture non-avoir :
       covered_days |= {jour pour jour in [max(ps, M.start), min(pe, M.end)]}
  4. ratio = len(covered_days) / nb_jours_du_mois
  5. status = "covered" si ratio >= 0.80
              "partial"  si 0 < ratio < 0.80
              "missing"  si ratio == 0

SoT période facture :
  - Si period_start AND period_end: utiliser tels quels
  - Sinon si issue_date: ps=1er du mois, pe=dernier du mois
  - Sinon: facture ignorée pour la couverture (R4 l'a déjà signalée)
```

---

## FICHIERS MODIFIÉS / CRÉÉS (V67)

| Fichier | Action |
|---------|--------|
| `backend/models/billing_models.py` | +4 Index SQLAlchemy |
| `backend/services/billing_coverage.py` | NOUVEAU — moteur couverture |
| `backend/routes/billing.py` | +3 endpoints, fix N+1 anomalies-scoped |
| `backend/tests/test_billing_v67_coverage.py` | NOUVEAU — 12 tests |
| `frontend/src/services/api.js` | +3 wrappers |
| `frontend/src/pages/BillingPage.jsx` | NOUVEAU — page timeline |
| `frontend/src/components/BillingTimeline.jsx` | NOUVEAU — liste mensuelle |
| `frontend/src/components/CoverageBar.jsx` | NOUVEAU — barre visuelle |
| `frontend/src/pages/Site360.jsx` | +lien "Voir timeline" |
| `frontend/src/App.jsx` | +route /billing |
| `frontend/src/layout/NavRegistry.js` | +entrée /billing |
| `frontend/src/pages/__tests__/billingV67.page.test.js` | NOUVEAU — 25 tests |
| `docs/decisions/v67_billing_timeline.md` | NOUVEAU (ce fichier) |
| `docs/dev/v67_billing_manual_test.md` | NOUVEAU |
