# Audit Bill Intelligence — Résumé exécutif

**Date** : 2026-03-29 | **Score** : 78/100 | **P0** : 3 | **P1** : 6 | **P2** : 5

---

## État général

L'app Bill Intelligence est **fonctionnelle et visuellement solide**. Le drawer shadow billing 5 composantes avec formules et sources réglementaires est un point fort différenciant. La navigation cross-briques (Site360, Cockpit, Sidebar, deep-links) fonctionne. Les bloquants portent sur les **données démo incomplètes** et un endpoint manquant.

---

## Données

| Métrique | Valeur | Verdict |
|----------|--------|---------|
| Factures ELEC | 36 (5 sites, 7-8/site) | ✅ |
| Factures GAZ | **0** (4 contrats GAZ existent) | ❌ P0 |
| Contrats | 9 (5 elec + 4 gaz) | ✅ |
| Anomalies | 56 (41 high, 15 medium) | ✅ |
| Perte estimée | 51 791 € | ✅ |
| Couverture/site | ~58% (mois alternés) | ❌ P0 |
| Cohérence KPIs (summary/insights/scoped/per-site) | Parfaite | ✅ |
| Cockpit conso vs billing conso | Écart 16% | ⚠️ P1 |

---

## UX/UI — Page /bill-intel

| Critère | Verdict |
|---------|---------|
| 5 KPIs (factures, €, kWh, anomalies, pertes) | ✅ |
| Bannière contextuelle + anomalie prioritaire | ✅ |
| kpiMessaging intégré (simple + expert) | ✅ |
| Filtres status (Tous/Ouverts/Pris en charge/Résolus/Faux positifs) | ✅ |
| Sévérité + montant perte par insight | ✅ |
| Workflow (Résolu, Créer action, Comprendre l'écart, Dossier) | ✅ |
| Import CSV (50 Mo max) + PDF (20 Mo max) | ✅ |
| Loading / Empty / Error states | ✅ |
| Fournisseur visible par anomalie | ❌ P1 |
| Message "déjà importé" | ❌ P1 |

---

## UX/UI — Drawer "Comprendre l'écart"

| Critère | Verdict |
|---------|---------|
| Breakdown 5 composantes (fourniture, réseau, accise, TVA, abonnement) | ✅ |
| Formules transparentes (kWh × tarif) | ✅ |
| Sources réglementaires (CRE TURPE 7, Loi finances 2026) | ✅ |
| Badge confiance "Élevée" + reconstitution complète | ✅ |
| CEE informatif (card distincte) | ✅ |
| Boutons action (Créer action, Contester, Compléter) | ✅ |
| N° facture renseigné | ❌ P1 (seed) |

---

## UX/UI — Page /billing

| Critère | Verdict |
|---------|---------|
| CoverageBar (couverts/partiels/manquants) | ✅ |
| Chart comparaison YoY | ✅ |
| Deep-link ?site_id + ?month | ✅ |
| Onglets navigation ↔ /bill-intel | ✅ |
| Breadcrumb français | ❌ P2 ("Billing" au lieu de "Facturation") |

---

## Navigation cross-briques

| Lien | Verdict |
|------|---------|
| Site360 → SiteBillingMini → /bill-intel?site_id=X | ✅ |
| Cockpit → ImpactDecisionPanel → /bill-intel | ✅ |
| Sidebar Facturation + Ctrl+Shift+B | ✅ |
| AnomaliesPage → /bill-intel | ✅ |
| Aliases /factures, /facturation | ✅ |
| Actions billing (GET /api/actions) | ❌ P1 (405) |
| Dashboard widget billing | ❌ P2 (404) |

---

## Calculs & Règles

| Métrique | Valeur | Verdict |
|----------|--------|---------|
| Règles V1 (billing_service.py) | 14 | ✅ |
| Règles V2 (audit_rules_v0.py) | 20 (R01-R20) | ✅ |
| Total règles | 34 | ✅ |
| Shadow V2 : résolution tarifs | 4 niveaux (Contract → MktPrice → SiteTariff → Fallback) | ✅ |
| Engine bill_intelligence connecté | ✅ (main.py + PDF parser) | ✅ |
| Coexistence 2 pipelines | Overlap conceptuel, pas de doublon fonctionnel | ⚠️ P2 |

---

## Qualité code

| Fichier | LOC | Note |
|---------|-----|------|
| backend/routes/billing.py | 1 948 | ⚠️ Candidat split |
| backend/services/billing_service.py | 928 | OK |
| backend/services/billing_shadow_v2.py | 932 | OK |
| frontend/src/pages/BillIntelPage.jsx | 1 246 | ⚠️ Gros mais structuré |
| **Tests backend** | **545 fonctions** (16 fichiers) | ✅ |
| **Tests frontend** | 3 fichiers / 411 lignes | OK |

---

## Endpoints cassés

| Endpoint | Status | Priorité |
|----------|--------|----------|
| `/api/billing/coverage` | 404 | **P0** |
| `/api/actions?source_type=billing` | 405 | **P1** |
| `/api/dashboard` | 404 | P2 |

---

## Findings

### P0 — Bloquants

1. **0 factures GAZ** malgré 4 contrats GAZ → enrichir `demo_seed.py`
2. **`/api/billing/coverage` → 404** → implémenter (billing_coverage.py existe)
3. **Couverture ~58%/site** (mois alternés) → seed 12 mois complets

### P1 — Crédibilité

1. **GET `/api/actions?source_type=billing` → 405** → fix route actions
2. **Cockpit conso ≠ billing conso** (écart 16%) → aligner ou documenter
3. **56/56 insights "open"** → seed quelques resolved/ack
4. **N° facture "non renseigné"** → numéros réalistes dans le seed
5. **Fournisseur absent** de la liste anomalies → ajouter badge
6. **Pas de feedback "déjà importé"** → flag `already_exists` + toast

### P2 — Polish

1. Breadcrumb "Billing" → "Facturation"
2. `/api/dashboard` 404 → implémenter ou retirer
3. Overlap 2 pipelines → documenter ou migrer V2
4. `billing.py` 1 948 lignes → split par entité
5. Anomaly rate 86% → calibrer ~35% pour démo crédible

---

## Plan de correction

| # | Tâche | Effort | Cible |
|---|-------|--------|-------|
| 1 | Enrichir seed (GAZ + 12 mois + N° facture + statuts variés) | **M** | Avant démo |
| 2 | Implémenter `/api/billing/coverage` | **S** | Avant démo |
| 3 | Fix GET `/api/actions?source_type=billing` | **S** | Avant démo |
| 4 | Aligner conso cockpit vs billing | **M** | Avant démo |
| 5 | Ajouter fournisseur dans liste anomalies | **S** | Avant démo |
| 6 | Calibrer anomaly rate ~35% | **S** | Avant démo |
| 7 | Fix breadcrumb + feedback import | **XS** | Avant démo |
| 8 | Refactoring pipelines + routes | **L** | Post-démo |

**Effort total** : ~3-4 jours pour P0+P1, P2 post-démo.
