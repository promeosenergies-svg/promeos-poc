# FIX PROMEOS — Sprint Front XS — 24 mars 2026

## 1. Résumé exécutif

1 correction appliquée sur 2 prévues. La 2e (StickyFilterBar) est annulée car le fichier est dans le périmètre Yannick.

| # | Correction | Fichier | Résultat |
|---|---|---|---|
| 1 | KpiCard local UsagesDashboard → KpiCard partagé | `UsagesDashboardPage.jsx` | ✅ Appliqué |
| 2 | StickyFilterBar déplacement | `pages/consumption/StickyFilterBar.jsx` | ❌ Annulé (périmètre Yannick) |

**Note** : InsightsPanel.jsx (2e KpiCard local identifié dans l'audit) est aussi dans `pages/consumption/` = périmètre Yannick → non touché.

---

## 2. Modifications réalisées

### Fix 1 — KpiCard local UsagesDashboardPage supprimé

**Avant** : fonction locale `KpiCard({ label, value, unit, sub })` (20 lignes, inline styles CSS) définie dans le fichier, dupliquant le composant `ui/KpiCard`.

**Après** :
- Import ajouté : `import KpiCard from '../ui/KpiCard'`
- Définition locale supprimée (remplacée par commentaire de traçabilité)
- 6 appels `<KpiCard>` migrés :
  - `unit` concaténé dans `value` (le KpiCard standard ne supporte pas `unit` séparément)
  - Wrapper div migré de inline styles vers Tailwind grid (`grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3`)
- Rendu visuel : cartes plus cohérentes avec le design system (bordures, typographie, spacing)

### Fix 2 — StickyFilterBar (annulé)

`pages/consumption/StickyFilterBar.jsx` est dans le périmètre Yannick (`frontend/src/pages/consumption/`). Règle : on ne modifie pas, on ne déplace pas.

---

## 3. Fichiers touchés

| Fichier | Modification |
|---|---|
| `pages/UsagesDashboardPage.jsx` | Import KpiCard partagé, suppression local, migration 6 appels, Tailwind grid |

---

## 4. Tests

| Suite | Résultat |
|---|---|
| `step4_co2_guard.test.js` | 9/9 ✅ |

---

## 5. Risques de régression

| Risque | Probabilité | Mitigation |
|---|---|---|
| Apparence KpiCard légèrement différente (Card wrapper vs inline div) | Faible | Le design system KpiCard est plus propre que l'ancien inline |
| Concaténation value+unit change le rendu | Faible | Même texte affiché, juste concaténé |
| Grid Tailwind vs flex inline change le layout | Faible | Grid responsive, plus robuste que flex avec inline styles |

---

## 6. Points non traités

| Point | Raison |
|---|---|
| StickyFilterBar déplacement | Périmètre Yannick (`pages/consumption/`) |
| InsightsPanel KpiCard local | Périmètre Yannick (`pages/consumption/`) |
| MonitoringPage StatusKpiCard local | Périmètre Yannick |
| Hook usePageData | Effort S, hors sprint XS |
| Migration routes.js | Effort S, hors sprint XS |
| Décomposition pages > 1500L | Effort M, hors sprint XS |

---

## 7. Definition of Done

- [x] KpiCard local supprimé de UsagesDashboardPage
- [x] Import `ui/KpiCard` partagé utilisé
- [x] 6 appels migrés avec unit concaténé
- [x] Inline styles remplacés par Tailwind grid
- [x] 9 tests frontend passent
- [x] 0 fichier Yannick touché
- [x] StickyFilterBar non déplacé (périmètre Yannick confirmé)
