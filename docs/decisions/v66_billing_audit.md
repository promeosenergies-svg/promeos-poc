# V66 — Billing Audit + Shadow-Billing V1 : Décisions

> Date : 2026-02-23  |  Sprint : V66  |  Auteur : PROMEOS team

---

## 1. FAITS — État de la brique Billing avant V66

| Composant | Fichier | État V65- |
|-----------|---------|-----------|
| Routing 15 endpoints | `backend/routes/billing.py` | ✓ Opérationnel — **0 org-scoping** |
| Shadow billing + R1-R10 | `backend/services/billing_service.py` | ✓ Complet — bridge ActionItem absent |
| PDF parser EDF/Engie | `backend/app/bill_intelligence/parsers/pdf_parser.py` | ✓ Templates OK — dépendance `pdfplumber` absente de requirements |
| BillIntelPage UI | `frontend/src/pages/BillIntelPage.jsx` | ✓ CSV + audit — pas de PDF upload ni CTA "Créer action" |
| 12 wrappers API | `frontend/src/services/api.js:583-604` | ✓ Complet |
| Site360 Factures tab | `frontend/src/pages/Site360.jsx` | ✗ Stub mort `<TabStub title="Factures">` |
| AnomaliesPage | `frontend/src/pages/AnomaliesPage.jsx` | ✓ Patrimoine — anomalies billing absentes |
| Action Center bridge | `backend/models/action_item.py` | ActionSourceType.BILLING présent — jamais instancié depuis billing |

---

## 2. ROOT CAUSES — 5 défauts critiques

### RC1 — Aucun org-scoping dans routes/billing.py
- **Impact** : Data leakage cross-org. Un tenant peut lire/créer des factures d'un autre tenant.
- **Cause** : `resolve_org_id()` présent dans `scope_utils.py` et utilisé par 12 autres routers — oublié lors du sprint billing initial.
- **Décision** : Appliquer `resolve_org_id()` + `_org_sites_query()` sur les 13 endpoints de données (hors `/rules` statique et `/seed-demo` admin).

### RC2 — Pas de response_model Pydantic
- **Impact** : Swagger inutilisable, validation outbound absente, risque de fuite de champs internes.
- **Décision** : Ajouter 4 schemas `ContractResponse`, `InvoiceResponse`, `BillingInsightResponse`, `BillingSummaryResponse` et les appliquer sur les 6 endpoints GET principaux.

### RC3 — pdf_parser.py utilise pdfplumber (absent de requirements.txt)
- **Impact** : `POST /billing/import-pdf` inexistant ; pdf_parser.py non appelable en production.
- **Cause** : Développé en local avec pdfplumber, pymupdf (fitz) était déjà dans requirements.
- **Décision** : Remplacer la fonction d'extraction par `extract_text_with_fitz(content: bytes)` utilisant `fitz` (pymupdf ≥ 1.24.0). Toute la logique template EDF/Engie reste intacte.

### RC4 — Pas de bridge billing → ActionItem
- **Impact** : Anomalies billing invisibles dans l'Action Center V65 (`/anomalies`).
- **Décision** : `persist_insights()` crée un `ActionItem` (BILLING, idempotent via `idempotency_key=billing:{invoice.id}:{anomaly_code}`). Route guard `/api/actions` interdit BILLING via API → création DB directe uniquement.

### RC5 — Site360 Factures tab = stub mort
- **Impact** : UX dégradée — onglet affiché mais inutilisable.
- **Décision** : Créer `SiteBillingMini.jsx` (KPIs + CTA) et remplacer le stub.

---

## 3. DÉCISIONS ARCHITECTURALES

### D1 — Pas de colonne org_id sur les modèles billing
Les modèles `EnergyContract`, `EnergyInvoice`, `BillingInsight` n'ont pas de `org_id` direct.
L'org est dérivée via la chaîne : `site → portefeuille → entite_juridique → organisation`.
**Raison** : éviter une migration DDL destructive. La chaîne join est déjà établie dans scope_utils.

### D2 — createActionFromBillingInsight utilise source_type='manual'
La route guard `POST /api/actions` (lignes 167-171) interdit `source_type=BILLING`.
Le CTA UI ("Créer action" depuis insight) utilise `source_type='manual'` + `idempotency_key=billing-insight:{id}`.
**Raison** : compatibilité route guard existante sans modification du guard.

### D3 — Anomalies billing dans AnomaliesPage via endpoint dédié
Un nouveau `GET /api/billing/anomalies-scoped` retourne les insights OPEN au format patrimoine-anomaly.
**Raison** : séparation claire ; AnomaliesPage agrège déjà les anomalies par `Promise.all`.

### D4 — Confiance PDF minimum 0.5 pour import
Si `confidence < 0.5` → HTTP 422. L'utilisateur doit corriger le PDF ou saisir manuellement.
**Raison** : éviter de polluer la DB avec des données mal parsées.

---

## 4. RÈGLES AJOUTÉES (R11 + R12)

| Règle | Code | Sévérité | Condition |
|-------|------|----------|-----------|
| R11 TTC Coherence | `ttc_mismatch` | HIGH | Δ(TTC facturé / HT+TVA recalculé) > 2% |
| R12 Contract Expiry | `contract_expired` | CRITICAL | Date fin contrat < aujourd'hui |
| R12 Contract Expiry Soon | `contract_expiry_soon` | HIGH | Date fin contrat dans ≤ 90 jours |

---

## 5. FICHIERS MODIFIÉS / CRÉÉS (V66)

| Fichier | Action |
|---------|--------|
| `backend/routes/billing.py` | Modifier — org scoping + response_model + import-pdf + anomalies-scoped |
| `backend/services/billing_service.py` | Modifier — R11 + R12 + ActionItem bridge |
| `backend/app/bill_intelligence/parsers/pdf_parser.py` | Modifier — fitz remplace pdfplumber |
| `backend/tests/test_billing_v66_scoping.py` | Créer |
| `backend/tests/test_billing_v66_pdf.py` | Créer |
| `backend/tests/test_billing_v66_checks.py` | Créer |
| `frontend/src/services/api.js` | Modifier — 3 nouveaux wrappers |
| `frontend/src/pages/BillIntelPage.jsx` | Modifier — PDF upload + "Créer action" |
| `frontend/src/components/SiteBillingMini.jsx` | Créer |
| `frontend/src/pages/Site360.jsx` | Modifier — remplacer TabStub Factures |
| `frontend/src/pages/AnomaliesPage.jsx` | Modifier — merge anomalies billing |
| `frontend/src/pages/__tests__/billingV66.page.test.js` | Créer |
