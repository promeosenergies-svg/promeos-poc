# Bilan — fix/billing-comprendre-ecart-drawer

**Date** : 2026-03-28
**Branche** : `fix/billing-comprendre-ecart-drawer`

---

## Résumé

Sprint correctif du drawer "Comprendre l'écart" dans Bill Intelligence.
**5 problèmes P0** (crédibilité tuée) et **8 problèmes P1** (compréhension dégradée) corrigés.

---

## Fichiers modifiés

### Backend (3 fichiers)

| Fichier | Changement |
|---------|-----------|
| `backend/services/billing_shadow_v2.py` | Enrichi `_build_breakdown_component()` (status, formula, source_ref, prorata_display). Ajouté `_extract_pdl_prm()`, `_compute_reconstitution_meta()`. Réécrit `compute_shadow_breakdown()` avec identification facture, reconstitution meta, CEE informational, expert section, hypothèses. |
| `backend/routes/billing.py` | Enrichi `_compute_breakdown_v2()` (identification, reconstitution meta, expert). Enrichi `get_insight_detail()` avec `invoice_identification`. |
| `backend/tests/test_step28_shadow_breakdown.py` | Corrigé 1 assertion (`"ok"` → `"missing_invoice_detail"` — comportement correct après fix). |

### Frontend (2 fichiers)

| Fichier | Changement |
|---------|-----------|
| `frontend/src/components/InsightDrawer.jsx` | V70 → V111. Ajouté : `InvoiceIdentCard` (P0.1), `ReconstitutionBanner` (P0.3/P0.4), CTAs actionnables (P1.8), section Debug technique collapsible (P1.7), TVA explicite (P1.1), note "— = non disponible" (P1.6), hypothèses breakdown. |
| `frontend/src/components/billing/ShadowBreakdownCard.jsx` | V2 → V111. Ajouté : statuts `missing_price`, `missing_invoice_detail`, `informational`. Formule + source_ref + prorata_display toujours visibles. CTA "Compléter les données" sur composantes manquantes. Badge reconstitution depuis API. Badge confiance avec tooltip rationale. |

### Tests ajoutés (2 fichiers)

| Fichier | Tests |
|---------|-------|
| `backend/tests/test_shadow_breakdown_enriched.py` | **17 tests** : identification PRM, attendu null/missing, reconstitution complete/partial/minimal, confiance élevée/très faible, prorata lisible, CEE informational, expert section, component status. |
| `frontend/src/__tests__/shadow_drawer_guards.test.js` | **17 tests** : source guards (zéro calcul front), P0.1 identification, P0.3 reconstitution, P0.4 confiance, P1.1 TVA, P1.4 CEE, P1.6 CTAs, P1.7 expert collapsible, prorata, formula, source_ref. |

---

## Corrections par priorité

### P0 — Crédibilité (5 fixes)

| # | Problème | Fix |
|---|----------|-----|
| P0.1 | Aucune identification facture | Encart : N° facture, période JJ/MM/AAAA (X jours), PRM, fournisseur, segment, puissance, kWh |
| P0.2 | Double "Attendu" contradictoire (17 640 vs 4 653) | `attendu_eur = null` si `status == "missing_price"`. Total attendu = somme des composantes reconstituables uniquement |
| P0.3 | Badge "Reconstitution complète" alors que 60% manquant | `reconstitution_status` calculé dynamiquement (`complete`/`partial`/`minimal`). Label depuis API, JAMAIS hardcodé |
| P0.4 | Pas de nuance confiance | Confiance 4 niveaux (`elevee`/`moyenne`/`faible`/`tres_faible`) basée sur % montant manquant. Rationale explicatif en tooltip |
| P0.5 | Accise : 2 valeurs (1 880 vs 1 842) | Chemin unique dans `compute_shadow_breakdown()`. Formula explicite `kwh × taux = montant` |

### P1 — Compréhension (8 fixes)

| # | Problème | Fix |
|---|----------|-----|
| P1.1 | TVA "— €" sans explication | Message explicite "TVA non détaillée sur cette facture" |
| P1.2 | Badge arrondi vs texte exact | `ecart_total_label` arrondi dans badge, `ecart_total_eur` exact dans texte |
| P1.3 | Prorata "× 0.0795" illisible | `prorata_display: "29/365 jours"`, `formula: "180 €/mois × 29/365 jours = 14,30 € HT"` |
| P1.4 | CEE "Attendu: 0,00 €" contradictoire | `status: "informational"`, `attendu: null`, message "Estimé à X € — inclus dans fourniture" |
| P1.5 | HPH/HCH = 0 sans explication | `status_message` explicatif quand kwh = 0 |
| P1.6 | "Non disponible" sans action | Chaque composante missing a un encart orange + CTA "Compléter les données du contrat" |
| P1.7 | Section Expert mélangée au contenu | `<details>` fermé par défaut, titre "Debug technique", séparé visuellement |
| P1.8 | Aucun CTA en bas du drawer | 3 boutons : "Créer une action", "Contester cette facture", "Compléter les données" |

---

## Résultats des tests

| Suite | Résultat |
|-------|----------|
| Backend — shadow breakdown enriched | **17/17 pass** |
| Backend — shadow breakdown existant | **26/26 pass** |
| Backend — suite complète | **741 pass, 1 skip, 1 fail pré-existant** (test_cee_v69 — bug `compliance_engine.py`, pas notre code) |
| Frontend — source guards drawer | **17/17 pass** |
| Frontend — suite complète | **3606 pass, 2 skip, 0 fail** |
| Frontend — build (vite) | **OK** (25s) |

**Zéro régression introduite.**

---

## Structure du payload enrichi (V1 fallback)

```
{
  // IDENTIFICATION FACTURE (P0.1)
  invoice_id, invoice_number, period_start, period_end, period_days,
  pdl_prm, supplier, segment, puissance_kva, kwh_total, energy_type,
  site_name, org_name,

  // RECONSTITUTION META (P0.3/P0.4)
  reconstitution_status,    // "complete" | "partial" | "minimal"
  reconstitution_label,     // texte FR
  missing_components,       // ["Fourniture d'énergie"]
  confidence,               // "elevee" | "moyenne" | "faible" | "tres_faible"
  confidence_label,         // "Élevée" | "Moyenne" | "Faible" | "Très faible"
  confidence_rationale,     // explication

  // TOTAUX
  total_expected_ht,        // somme reconstituable
  total_expected_ht_label,  // "3 986,68 € HT (partiel — hors fourniture)"
  total_gap_label,          // "Non calculable — reconstitution partielle"

  // COMPOSANTES (enrichies)
  components: [{
    name, label, expected_eur, invoice_eur, gap_eur, gap_pct,
    status,           // "ok" | "warn" | "alert" | "missing_price" | "missing_invoice_detail" | "informational"
    status_message,   // explication FR
    formula,          // "71 709 kWh × 0,02658 €/kWh = 1 906 € HT"
    source_ref,       // "CRE TURPE 7 C4_BT"
    prorata_display,  // "29/365 jours"
  }],

  // HYPOTHÈSES
  hypotheses,

  // EXPERT
  expert: { engine, catalog, segment, method, prix_ref_kwh, source_prix, tariff_source }
}
```

---

## Prochaines étapes potentielles

1. Implémenter les CTAs (navigation vers édition contrat, création action automatique)
2. Ajouter la ventilation horosaisonnière HPH/HCH/HPB/HCB dans le payload
3. Intégrer le billing engine V2 pour la décomposition fine par plage tarifaire
4. Ajouter un export PDF du drawer
