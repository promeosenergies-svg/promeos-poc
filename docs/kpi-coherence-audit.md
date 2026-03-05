# Audit Cohérence KPI — PROMEOS V117

> Généré le 2026-03-05 — Playbook Phase 0, Prompt 0.3

---

## 1. KPI "Consommation totale kWh"

| Module | Source | Fonction / Endpoint | Données |
| ------ | ------ | ------------------- | ------- |
| Cockpit | `cockpit.py` | GET `/api/cockpit` | Pas de conso directe — affiche `avancement_decret_pct` et `risque_financier_euro` |
| Conso Explorer | `consumption_context.py` | GET `/api/consumption/context` | `Timeseries` model — données compteur agrégées |
| Conso Diagnostic | `consumption_diagnostic.py` | GET `/api/consumption/diagnostic` | Service `consumption_diagnostic.py` — agrège par site/période |
| Monitoring | `monitoring.py` | GET `/api/monitoring` | `MonitoringEvent` + `Timeseries` — même source que conso |
| Billing | `billing.py` | GET `/api/billing/insights` | `BillingInvoice.montant_kwh` — données facture (pas compteur) |

### Verdict

**Cohérent** — La consommation kWh provient de 2 sources distinctes mais légitimes :
1. **Compteur** (`Timeseries`) : utilisé par Conso Explorer, Diagnostic, Monitoring
2. **Facture** (`BillingInvoice.montant_kwh`) : utilisé par Billing

Ce sont 2 métriques différentes (consommation mesurée vs consommation facturée). Pas d'incohérence.

---

## 2. KPI "Risque financier (EUR)"

| Module | Source | Fonction | Formule |
| ------ | ------ | -------- | ------- |
| Cockpit | `cockpit.py:88` | `func.sum(Site.risque_financier_euro)` | Somme directe du champ stocké sur Site |
| Patrimoine | `patrimoine.py:1180` | `func.coalesce(func.sum(Site.risque_financier_euro), 0)` | Même champ, même agrégation |
| Compliance | `compliance_rules.py:650` | `latest.compliance_score` + `risque_financier_euro` | Lu depuis `RegAssessment` |
| Actions | `action_plan_engine.py:168` | `readiness_score` (% sites conformes) | Métrique différente (readiness, pas risque) |

### Verdict

**Cohérent** — `risque_financier_euro` est un champ stocké sur le modèle `Site`, calculé par `compute_risque_financier()` dans `compliance_rules.py`. Cockpit et Patrimoine lisent le même champ avec la même agrégation `SUM()`.

Le moteur de compliance (`RegAssessment`) a son propre `compliance_score` (0-100) qui est une métrique différente — pas de confusion.

---

## 3. KPI "Score conformité"

| Module | Source | Calcul |
| ------ | ------ | ------ |
| RegOps | `regops/scoring.py:124` | `compute_compliance_score()` — dedup + clamp + profiling |
| BACS | `bacs_engine.py:551` | `_compute_compliance_score()` — 0-100, propre au BACS |
| Intake | `intake_engine.py:524` | % findings OK/OUT_OF_SCOPE |
| Cockpit | `cockpit.py:60-85` | Count `NON_CONFORME` + `A_RISQUE` sites (pas un score) |

### Verdict

**Cohérent mais à documenter** — Il y a 3 scores de conformité différents (RegOps, BACS, Intake), chacun pour un domaine réglementaire distinct. Le cockpit ne calcule pas de score global mais compte les sites non conformes. C'est correct mais pourrait bénéficier d'un score composite futur.

**Recommandation** : Créer un `compliance_composite_score` qui agrège RegOps + BACS + Tertiaire en un seul indicateur pour le cockpit.

---

## 4. Unités et formatage

### Formatter centralisé : `frontend/src/utils/format.js`

| Fonction | Conversion | Seuils |
| -------- | ---------- | ------ |
| `fmtEur(v)` | € → k€ → M€ | ≥1 000 → k€, ≥1 000 000 → M€ |
| `fmtEurFull(v)` | Toujours en € | Pas de conversion |
| `fmtKwh(v)` | kWh → k kWh → GWh | ≥1 000 → k kWh, ≥1 000 000 → GWh |
| `fmtArea(v)` | m² | Pas de conversion |
| `fmtAreaCompact(v)` | m² → k m² | ≥1 000 → k m² |
| `formatPercentFR(v)` | % (FR locale) | 0-100 → "24 %" |

### Utilisation

- **232 occurrences** de kWh/MWh/GWh dans le frontend (62 fichiers)
- `fmtKwh` utilisé dans : ConsumptionDiagPage, Patrimoine, ConsoKpiHeader, PortfolioPanel
- Certaines pages utilisent `fmtKwh` (centralisé), d'autres affichent directement "kWh" dans le JSX

### Incohérences trouvées

| Fichier | Ligne | Observation | Sévérité |
| ------- | ----- | ----------- | -------- |
| `ROISummaryBar.jsx` | 9 | `fmtEur` locale — utilise son propre formateur `Math.round(v).toLocaleString('fr-FR')` au lieu de `utils/format.fmtEur` | FAIBLE |
| `InsightDrawer.jsx` | divers | Mix de `fmtEur` importé et formatage inline | FAIBLE |
| `MonitoringPage.jsx` | divers | 17 occurrences kWh — la plupart inline, pas via `fmtKwh` | FAIBLE |
| `PurchaseAssistantPage.jsx` | divers | 12 occurrences kWh — formatage inline | FAIBLE |

### Verdict

**Globalement cohérent** — Le formatter centralisé existe et est bien conçu. Certaines pages anciennes utilisent encore du formatage inline, mais les valeurs et unités sont correctes. Pas de bug de conversion kWh↔MWh détecté.

**Recommandation** : Migrer progressivement les formatages inline vers `fmtKwh`/`fmtEur` pour uniformité.

---

## 5. Tableau récapitulatif

| KPI | Cohérent ? | Score | Recommandation |
| --- | ---------- | ----- | -------------- |
| Consommation kWh | OUI | 9/10 | Documenter la distinction compteur vs facture |
| Risque financier € | OUI | 10/10 | Même champ `Site.risque_financier_euro` partout |
| Score conformité | OUI (3 domaines) | 8/10 | Créer un score composite pour le cockpit |
| Unités & formatage | OUI | 8/10 | Migrer formatages inline vers `utils/format.js` |

### **Score cohérence KPI : 88/100**

---

## 6. Recommandations de refactoring

1. **Score composite conformité** : Agréger RegOps + BACS + Tertiaire en un indicateur cockpit unique
2. **Centraliser `fmtKwh`** : Remplacer les 17+ formatages inline kWh dans MonitoringPage par `fmtKwh`
3. **Unifier `fmtEur`** : ROISummaryBar devrait utiliser `utils/format.fmtEur` au lieu de son formateur local
4. **Documenter les sources** : Ajouter un commentaire dans cockpit.py expliquant que `risque_financier_euro` est calculé par le compliance engine

---

*Rapport généré par Playbook Phase 0.3 — Cohérence KPI cross-briques*
