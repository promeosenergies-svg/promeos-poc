# PROMEOS — Audit Sévère V2 (hors ACC)
**Date** : 19 mars 2026 | **Périmètre** : Patrimoine → Conformité → Facturation → Achat → Actions

---

## Note globale

| | Note |
|-|------|
| **Actuelle (hors ACC)** | **6,0 / 10** |
| **Atteignable à 90 jours** | **8,5 / 10** |

---

## ACC — Hors scope POC (mais traces à neutraliser)

ACC/PMO/Settlement = **hors scope**. Non pénalisé.
Mais ces traces dans le code risquent de tromper un partenaire technique :

| Trace | Fichier |
|-------|---------|
| `PMO_ACC = "pmo_acc"` dans les enums | `backend/models/enums.py:437` |
| Rôle `PMO_ACC` assignable en admin | `backend/services/iam_service.py:108` |
| `PaymentRule` avec payeur / facturé | `backend/models/payment_rule.py` |
| Route `/portfolio-reconciliation` accessible | `frontend/src/App.jsx` |
| `acc` dans `RegulatoryOpportunity.opportunity_type` | `backend/models/flex_models.py:129` |

**Action** : Ajouter `# Réserve architecture future — non livré POC` sur chaque trace.

---

## Scores par axe

| Axe | Note |
|-----|------|
| Produit / Logique | 6/10 |
| UX / UI | 6,5/10 |
| Front | 6/10 |
| Back / API | 5,5/10 |
| Données / Modèle métier | 5,5/10 |
| Règles métier / Conformité | 5,5/10 |
| Facturation / Achat | 5/10 |
| Multi-sites / Navigation | 6/10 |
| Crédibilité marché | 5,5/10 |

---

## P0 — Bloquants (avant toute démo sérieuse)

### 1. Zéro auth stricte en production
285 endpoints utilisent `get_optional_auth`. Aucun n'utilise `get_current_user`.
`AUTH_ENABLED=false` par défaut. `DEMO_MODE=true` → CORS wildcard `"*"`.
Un attaquant sans token peut lire et écrire toutes les données.
- `backend/middleware/auth.py:25` → changer default à `"true"`
- `backend/main.py:94-97` → restreindre CORS hors DEMO_MODE
- Tous les routers POST/PATCH/DELETE → remplacer `get_optional_auth` → `get_current_user`

### 2. SECRET_KEY placeholder en .env
`SECRET_KEY=your-secret-key-change-in-production` → tous les JWT forgeable.
- `backend/.env` → valeur aléatoire 32 chars
- `backend/main.py` → bloquer démarrage si valeur placeholder

### 3. Calcul achat 100% en JavaScript, non auditable
`frontend/src/domain/purchase/scoring.js` + `engine.js` = toute la logique de scoring.
Le backend persiste les résultats mais ne les recalcule pas.
Décision d'achat = plusieurs M€ — non défendable contractuellement en JS.
- Migrer vers `backend/services/purchase_scoring_service.py`
- `scoring.js` et `engine.js` → mode display-only uniquement

---

## P1 — Crédibilité (avant premier pilote)

| # | Problème | Fichier | Correctif |
|---|----------|---------|-----------|
| P1.1 | `_detect_framework()` fragile → score conformité peut être faux silencieusement | `compliance_score_service.py:366` | Champ `framework` explicite sur `RegAssessment` |
| P1.2 | Shadow billing prorata 30j hardcodé → ±5-10% d'erreur systématique | `billing_shadow_v2.py` | `calendar.monthrange(y,m)[1]` |
| P1.3 | APER : éligibilité seule, sans productible PV ni ROI (= 25% du score de conformité) | `aper_service.py` | Intégrer `pvgis.py` (connecteur présent mais inactif) |
| P1.4 | Consommation réelle absente — confidence="none" sur 4/5 sites en démo | `consumption_unified_service.py` | Créer `demo_seed/gen_meter_readings.py` |
| P1.5 | 4 noms de champ différents pour le risque financier dans le front | `normalizeRisk.jsx` | 1 seul champ `risque_financier_eur` dans tous les endpoints |
| P1.6 | Achat gaz bloqué en dur — 60% des patrimoines mixtes non couverts | `purchase.py:48` | `ALLOWED_ENERGY_TYPES = {"elec", "gaz"}` |
| P1.7 | Aucune FK entre anomalie facture, action corrective et ROI mesuré | `action_item.py`, `billing_models.py` | Ajouter `source_billing_insight_id` sur `ActionItem` |
| P1.8 | Export OPERAT non validé — format ADEME/XSD non vérifié (TODO ouvert) | `operat.py`, `tertiaire_proof_catalog.py` | `operat_xsd_validator.py` avant téléchargement |
| P1.9 | N+1 queries sur compliance portfolio → timeout sur > 20 sites | `compliance_score_service.py:326` | Bulk-load RegAssessments, utiliser `compliance_score_composite` |

---

## P2 — Différenciation

| # | Problème | Fichier |
|---|----------|---------|
| P2.1 | 5 connecteurs présents (Enedis, MétéoFrance, PVGIS…) — aucun ne produit de données | `backend/connectors/` |
| P2.2 | KPI Catalog incomplet — formules manquantes pour "Couverture 74%", "Complétude 100%" | `schemas/kpi_catalog.py` |
| P2.3 | Flex (Sprint 21) non reliée aux scénarios achat ni au cockpit | `flex.py`, `purchase_service.py` |
| P2.4 | Cockpit sans tendance historique — `ComplianceScoreHistory` en DB, non exposé | `routes/cockpit.py` |
| P2.5 | CEE : 3 modèles en DB, zéro route, zéro page, zéro service actif | `backend/models/` |

---

## Chaîne logique — Écarts promesse vs réalité

```
Patrimoine        ✅  Livré correctement

Conformité        ⚠️  _detect_framework() fragile
                      APER sans productible PV
                      Export OPERAT non validé XSD
                      N+1 queries sur portfolio

Facturation       ⚠️  Prorata 30j hardcodé → fausses anomalies
                      Données réelles absentes en démo
                      Aucun lien FK vers ActionItem

Achat             ❌  Calcul 100% en JS — non auditable
                      Gaz absent (ALLOWED_ENERGY_TYPES={"elec"})
                      TariffWindow Flex non prise en compte

Actions           ⚠️  ROI non mesuré (lien facture → action manquant)
                      Tendances KPIs non exposées dans le cockpit
                      4 noms de champ différents pour le risque financier
```

---

## Top 7 actions — impact sur la note

| # | Action | Fichiers | Impact |
|---|--------|----------|--------|
| 1 | Auth stricte — `AUTH_ENABLED=true` + 285 endpoints protégés | `middleware/auth.py`, tous routers | **+0,8 pt** |
| 2 | Calcul purchase → serveur Python auditable | `purchase_scoring_service.py`, `scoring.js` | **+0,7 pt** |
| 3 | `_detect_framework()` → champ `framework` explicite | `compliance_score_service.py`, `compliance_models.py` | **+0,5 pt** |
| 4 | MeterReading réelles en seed (confidence "high" sur 3/5 sites) | `demo_seed/gen_meter_readings.py` | **+0,5 pt** |
| 5 | Prorata jours réels + FK anomalie → action | `billing_shadow_v2.py`, `action_item.py` | **+0,4 pt** |
| 6 | APER productible PVGIS + export OPERAT validé XSD | `aper_service.py`, `operat.py` | **+0,4 pt** |
| 7 | Tendances KPIs cockpit + 1 champ risque canonique | `cockpit.py`, `normalizeRisk.jsx` | **+0,3 pt** |
