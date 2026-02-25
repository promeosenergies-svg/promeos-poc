# ADR V68 — Billing Unified (Shadow V2 + Deep-links + Seed 36 mois)

> V67 (Billing Timeline & Coverage) : **DONE** (commit 3cdd172). Ce doc couvre uniquement V68.
> Date : 2026-02-24

---

## Contexte

V67 a livré le moteur de couverture facturation (Timeline + CoverageBar). V66 avait livré Bill Intelligence (Shadow V1, R1-R12). V68 unifie les deux surfaces sur un contrat de données commun et enrichit l'analyse.

---

## Décisions

| ID | Décision | Choix retenu |
|----|----------|--------------|
| D1 | Fix Phase 0 | Optional chaining `summary?.range?.min_month` + `activeMonth` state |
| D2 | InvoiceNormalized | `billing_normalization.py` + `GET /billing/invoices/normalized` |
| D3 | Shadow V2 | `billing_shadow_v2.py` avec constantes TURPE/ATRD/ATRT/CSPE/TICGN |
| D4 | R13 + R14 | `_rule_reseau_mismatch` + `_rule_taxes_mismatch` dans BILLING_RULES (14 règles total) |
| D5 | BillIntelPage | `useSearchParams` → filtre site_id + month côté front |
| D6 | BillIntelPage CTA | Bouton "Voir timeline" → `/billing?site_id={X}` |
| D7 | BillingPage month | Lit `?month=YYYY-MM` → `activeMonth` → highlight BillingTimeline row |
| D8 | Seed 36 mois | Étend `billing_seed.py` → idempotent via source="seed_36m" |
| D9 | seed_data.py | Appelle `seed_billing_demo(db)` en fin de main() |

---

## Hypothèses

| ID | Hypothèse |
|----|-----------|
| H1 | `price_ref_eur_per_kwh` = prix all-in TTC/kWh dans ce modèle POC |
| H2 | TURPE simplifié C5 BT 2025 : 0.0453 EUR/kWh |
| H3 | R13 seuil : delta réseau > 10% (medium), > 20% (high) |
| H4 | R14 seuil : delta taxes > 5% (medium) |
| H5 | Seed 36 mois idempotent : check source="seed_36m" |

---

## Contrat API V68

### `GET /api/billing/invoices/normalized`

Query : `site_id?`, `month_key?` (YYYY-MM), `limit=50`, `offset=0`

```json
{
  "invoices": [{
    "id": 12, "org_id": 1, "site_id": 5,
    "fournisseur": "EDF ENR", "energie": "ELEC",
    "period_start": "2024-01-01", "period_end": "2024-01-31",
    "issue_date": "2024-02-05", "month_key": "2024-01",
    "ttc": 1620.0, "ht": 1420.0, "tva": 200.0,
    "ht_fourniture": 1020.0, "ht_reseau": 400.0,
    "kwh": 9000, "invoice_number": "EDF-2024-01",
    "status": "imported", "pdf_doc_id": null
  }],
  "total": 1, "offset": 0, "limit": 50
}
```

---

## Navigation bidirectionnelle

```
BillingTimeline  →  /bill-intel?site_id=X&month=YYYY-MM  →  BillIntelPage
BillIntelPage    →  /billing?site_id=X                   →  BillingPage (highlight mois)
Site360          →  /billing?site_id=X                   →  BillingPage
```

---

## Seed HELIOS 36 mois

| Dimension | Détail |
|-----------|--------|
| Période | Jan 2023 – Déc 2025 |
| Sites | site_a (ELEC 9000 kWh/mois), site_b (GAZ 6000 kWh/mois) |
| Trous | 2023-03, 2024-09 (site_a missing) ; 2025-02 (site_b missing) |
| Partiels | 2023-06 (15j), 2024-01 (20j/31) sur site_a |
| Anomalie R1 | 2024-07 : total_eur = shadow × 1.45 |
| Anomalie R13 | 2024-11 : NETWORK = TURPE × 2.3 |
| Anomalie R14 | 2025-01 : TAX = CSPE × 1.08 |
