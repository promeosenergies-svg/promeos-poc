# V66 — Billing Manual Test Checklist (QA 10 étapes)

> Date : 2026-02-23  |  Prérequis : backend + frontend lancés, org demo seedée

---

## Prérequis

1. `cd backend && uvicorn main:app --reload`
2. `cd frontend && npm run dev`
3. `POST /api/demo/seed-pack` → Groupe HELIOS (5 sites)
4. `POST /api/billing/seed-demo` → 2 contrats + 5 factures demo
5. Naviguer sur http://localhost:5173

---

## Étapes de test

### T1 — Org scoping de base
```bash
# Sans header → devrait retourner données de l'org demo
curl http://localhost:8000/api/billing/summary

# Avec org inexistant → 403 ou empty
curl -H "X-Org-Id: 9999" http://localhost:8000/api/billing/summary
```
**Attendu** : T1a = données HELIOS, T1b = `{"total_invoices":0,...}` ou 403

---

### T2 — Import CSV org-scopé
```bash
# Upload CSV avec site_id valide HELIOS
curl -X POST "http://localhost:8000/api/billing/import-csv?org_id=<ORG_ID>" \
  -F "file=@tests/fixtures/billing_sample.csv"
```
**Attendu** : `{"status":"ok", "imported": N, "skipped": 0}`

---

### T3 — Import PDF (V66 NEW)
1. Créer un PDF de test minimal avec le texte "EDF" et un numéro de facture
2. `curl -X POST "http://localhost:8000/api/billing/import-pdf?site_id=1" -F "file=@facture_test.pdf"`
**Attendu** : `{"status":"imported", "invoice_id":N, "confidence":0.X, ...}` (confiance ≥ 0.5)
**Cas erreur** : PDF vide → HTTP 422

---

### T4 — Règle R11 TTC Coherence
1. Créer une facture avec `total_eur=1000` mais lignes HT+TVA = 1030
2. `POST /api/billing/audit/{invoice_id}`
**Attendu** : anomalie `ttc_mismatch` avec severity=HIGH dans les insights

---

### T5 — Règle R12 Contract Expiry
1. Créer un contrat avec `end_date` = hier ou < aujourd'hui
2. Lier une facture à ce contrat
3. `POST /api/billing/audit/{invoice_id}`
**Attendu** : anomalie `contract_expired` severity=CRITICAL dans les insights

---

### T6 — Bridge ActionItem
1. Lancer `POST /api/billing/audit-all`
2. Vérifier que des ActionItem BILLING ont été créés : `GET /api/actions?source_type=billing`
3. Re-lancer `POST /api/billing/audit-all`
4. Vérifier pas de doublons (idempotency_key)
**Attendu** : T6a = N actions créées, T6b = même N (pas de doublon)

---

### T7 — BillIntelPage UI
1. Aller sur `/bill-intel`
2. Vérifier que le bouton PDF upload est visible
3. Vérifier que chaque ligne d'insight a un bouton "Créer action"
4. Cliquer "Créer action" → bouton doit changer d'état (créé)
**Attendu** : upload fonctionnel, CTA idempotent

---

### T8 — Site360 Factures tab
1. Aller sur `/patrimoine` → cliquer sur un site
2. Cliquer onglet "Factures"
**Attendu** : `SiteBillingMini` avec KPIs (nb factures, nb anomalies, dernière facture)
**Non attendu** : texte "à venir" ou stub

---

### T9 — AnomaliesPage billing
1. Aller sur `/anomalies`
2. Vérifier que les anomalies framework="FACTURATION" apparaissent
3. Cliquer "Ouvrir site" sur une anomalie billing → doit naviguer vers `/bill-intel`
**Attendu** : chip FACTURATION visible, navigation correcte

---

### T10 — Isolation multi-org
1. Créer deux orgs via seeder (A et B)
2. Importer factures dans org A
3. Requêter billing avec org_id de org B
**Attendu** : `{"invoices": [], "count": 0}` pour org B

---

## Checklist finale avant merge

- [ ] `grep "Organisation.first()" backend/routes/billing.py` → 0 résultats
- [ ] `grep "resolve_org_id" backend/routes/billing.py` → ≥ 13 occurrences
- [ ] `grep "response_model" backend/routes/billing.py` → ≥ 6 occurrences
- [ ] `grep "pdfplumber" backend/` → 0 résultats
- [ ] `pytest tests/test_billing_v66_scoping.py tests/test_billing_v66_pdf.py tests/test_billing_v66_checks.py -v` → all green
- [ ] `npx vitest run src/pages/__tests__/billingV66.page.test.js` → all green
- [ ] `pytest tests/ -x -q` → 0 régression
- [ ] `npx vitest run` → 0 régression
