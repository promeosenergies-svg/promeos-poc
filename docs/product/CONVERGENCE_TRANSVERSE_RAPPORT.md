# Rapport de convergence transverse PROMEOS

**Date :** 2026-03-19
**Commit :** `3b67ed5`
**Tests front :** 31 | **Tests backend :** 141

---

## 1. Pages déjà convergées

| Page | RiskBadge | EmptyState | Deep-link | Timestamp | Labels OK |
|------|-----------|------------|-----------|-----------|-----------|
| **Cockpit** | ✅ (site + tableau) | — | ✅ → conformité | ✅ "Dernière analyse" | ✅ renommés |
| **Patrimoine** | ✅ (colonne tableau) | ✅ empty | ✅ → conformité par ligne | — | ✅ |
| **ConformitePage** | ✅ (impact EUR) | ✅ empty + partial | ✅ → preuves/actions | — | ✅ accents FR |
| **BillIntelPage** | — | ✅ unconfigured + empty | ✅ → achat énergie | — | ✅ breadcrumb |
| **Site360** | — | — | — | ✅ FreshnessIndicator | — |

## 2. Pages partiellement convergées

| Page | Ce qui manque |
|------|---------------|
| **PurchasePage** | RiskBadge absent, EmptyState absent |
| **ActionCenterPage** | RiskBadge sur impact_eur, EmptyState sur filtre vide |
| **MonitoringPage** | EmptyState variant, RiskBadge absent |
| **ComplianceSummaryBanner** | ✅ RiskBadge ajouté — OK |
| **DonneesTab** | ✅ variant="empty" ajouté — OK |

## 3. Pages encore hétérogènes

| Page | Composant KPI utilisé | Migration nécessaire |
|------|----------------------|---------------------|
| **Cockpit** | ExecutiveKpiRow (KpiTile) + EssentialsRow (MiniCard) | P2 — fonctionnel, migration risquée |
| **Patrimoine** | KpiCardCompact | P3 — acceptable |
| **CommandCenter** | KpiCard | P3 — acceptable |
| **Site360** | aucune variante KPI directe | — |

**Décision UnifiedKpiCard :** Les 6 variantes KPI existantes fonctionnent. Le composant UnifiedKpiCard est **disponible** pour les nouvelles intégrations mais la migration forcée des existantes est **trop risquée** (régression UI) pour un bénéfice marginal. Recommandation : adopter UnifiedKpiCard sur les prochaines features, déprécier progressivement les anciennes.

## 4. Fichiers à traiter ensuite

| Priorité | Fichier | Action |
|----------|---------|--------|
| P2 | PurchasePage.jsx | + RiskBadge sur scénarios + EmptyState |
| P2 | ActionCenterPage.jsx | + RiskBadge sur impact + EmptyState filtres vides |
| P3 | MonitoringPage.jsx | + EmptyState variant + RiskBadge si pertinent |
| P3 | Site360 TabResume | + RiskBadge sur risque site |
| P3 | Conformité tabs | + EmptyState variant sur tous les onglets vides |

## 5. Top 5 actions sprint suivant

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | RiskBadge + EmptyState sur PurchasePage | S | Cohérence achat |
| 2 | RiskBadge + EmptyState sur ActionCenterPage | S | Cohérence actions |
| 3 | Sidebar : ajouter séparateur visuel Admin | S | Lisibilité navigation |
| 4 | Tooltip "Comment c'est calculé" sur score conformité | S | Confiance |
| 5 | FreshnessIndicator sur ConformitePage | M | Fraîcheur données |

## 6. Risques de régression

| Risque | Probabilité | Impact |
|--------|------------|--------|
| Migration forcée KpiTile/MiniCard → UnifiedKpiCard | — | **Non recommandé** — trop risqué |
| RiskBadge avec valeur null/undefined | Faible | Géré par normalizeRisk → "inconnu" |
| EmptyState variant mal choisi | Faible | 4 variantes bien documentées |
| Deep-links vers routes inexistantes | Très faible | Routes déjà validées |

## 7. Recommandation release

**READY TO MERGE** — la convergence transverse est suffisante pour une release.

| Critère | Statut |
|---------|--------|
| RiskBadge sur 3+ pages cœur | ✅ (Cockpit, Patrimoine, Conformité) |
| EmptyState sur 3+ pages cœur | ✅ (Patrimoine, BillIntel, Conformité) |
| Deep-links inter-briques | ✅ (patrimoine→conformité, facture→achat, cockpit→conformité) |
| Timestamps/fraîcheur | ✅ (Cockpit, Site360) |
| Labels FR cohérents | ✅ (renommés, breadcrumb simplifié) |
| Tests convergence | ✅ (31 tests, 7 cross-pages) |
| 0 régression | ✅ (build + tests OK) |

---

## Bilan adoption composants partagés

```
                    Avant       Après
RiskBadge           0 pages  →  3 pages (Cockpit, Patrimoine, Conformité)
EmptyState enrichi  0 pages  →  3 pages (Patrimoine, BillIntel, Conformité)
getSiteRisk()       0 usages →  2 pages (Cockpit, Patrimoine)
Deep-links          2 liens  →  5 liens (patrimoine→conformité, facture→achat, cockpit→conformité, anomalies→conformité, conformité→OPERAT)
Timestamps          0 pages  →  2 pages (Cockpit, Site360)
Labels renommés     0        →  4 (Données exploitables, Couverture opérationnelle, Facturation breadcrumb, sidebar labels)
Tests front         0        →  31
```
