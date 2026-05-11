# Phase 3.4 — Phase E · Décision formalisée GO extraction `HubKpiCard`

> **Statut** : DÉCISION VALIDÉE — GO extraction
> **Date** : 2026-05-11
> **Auteur** : Amine (validé via audit Phase D + recommandation forte `phase_3_4_decision_hubkpicard.md`)
> **Référence audit** : `docs/audits/phase_3_4_audit_grid.md` (score 73/96, bloquant 4.1)
> **ADR associé** : `docs/adr/ADR-021-hub-page-grammar-l11.md` (section à compléter Phase F)

---

## Décision

**GO extraction de `KpiTriptychCard` inline → `HubKpiCard` primitif dans `frontend/src/components/grammar/hub/`** avant tout scaling L11 sur les 5 hubs restants (Phase 3.5).

L'extraction est **élargie** par rapport au plan initial : 5 composants locaux à extraire au lieu de 1.

---

## Composants à extraire (scope Phase F)

| # | Composant inline actuel | Cible primitif | Localisation cible |
|---|---|---|---|
| 1 | `KpiTriptychCard` (130 lignes) | `HubKpiCard` | `components/grammar/hub/HubKpiCard.jsx` |
| 2 | `BarsDaily7d` | `ChartFrameBars` | `components/grammar/hub/charts/ChartFrameBars.jsx` |
| 3 | `LineCharge24h` | `ChartFrameLine` | `components/grammar/hub/charts/ChartFrameLine.jsx` |
| 4 | `Skeleton` local | `HubSkeleton` | `components/grammar/hub/states/HubSkeleton.jsx` |
| 5 | `Error` local | `HubError` avec correlation_id | `components/grammar/hub/states/HubError.jsx` |

**Justification scope élargi** : les 5 composants partagent la même problématique architecturale (inline = drift garanti × 5 hubs). Les extraire ensemble en une Phase F = ROI maximal vs 5 phases séparées plus tard.

---

## Justifications de la décision GO

### 1. Mathématique

| Moment | Coût | Risque |
|---|---|---|
| Maintenant (avant 3.5) | 5-7h | Faible |
| Pendant 3.5 (5 hubs parallèles) | 12-18h | Moyen-élevé |
| Après 3.5 | 24-32h | Très élevé (drift consolidé) |

**ROI immédiat ×2 à ×5**.

### 2. Doctrinale (Sol v1.1 + L11 + Design System Spec §7.4)

Les 5 primitifs L11 sont génériques par construction. Les laisser inline viole L11.5 (composition répétable) et bloque les source-guards CI.

### 3. Empirique (audit Phase D)

- Score 73/96 bloque sur 4.1 = 0
- 8 findings P1/P2 dépendent de Phase F
- Projection post-F : **83/96 (87 %)** → GO Phase 3.5

### 4. Risque inverse (faire maintenant) : aucun majeur

| Risque | Mitigation |
|---|---|
| Régression visuelle | Recapture Playwright Phase G, diff pixel-near |
| Régression fonctionnelle | Vitest 4 680 + 10+ tests nouveaux |
| Cassure imports | 1 seul consumer (`pages/CockpitJour.jsx`) |

---

## Conditions de réussite Phase F

- [ ] `frontend/src/pages/CockpitJour.jsx` ≤ 200 lignes
- [ ] 5 primitifs créés dans `components/grammar/hub/` avec stories + tests
- [ ] Backend filtre `is_demo` ajouté dans `GET /api/cockpit/jour` (7 → 5 sites)
- [ ] Tooltip Sol pour acronymes (BACS/EMS/OPERAT/CVC/DT)
- [ ] Valeur KPI Fraunces 28px → Newsreader 38px (Spec §5.3)
- [ ] `data-component="HubKpiCard"` (au lieu de `KpiTriptychCard`)
- [ ] Source-guards 11 → 13+ tests Vitest
- [ ] Vitest baseline 4 680 → 4 690+
- [ ] Visual regression Phase G : zéro diff pixel-near

---

## Plan d'exécution Phase F (7 sous-étapes atomiques)

| F | Sous-étape | Commit | Durée |
|---|---|---|---|
| F.1 | Extraction `HubKpiCard` | `feat(p3.4)!: extract HubKpiCard primitive from CockpitJour inline` | 1.5h |
| F.2 | Extraction `ChartFrameBars` + `ChartFrameLine` | `feat(p3.4)!: extract ChartFrame variants for hub pages` | 1h |
| F.3 | Extraction `HubSkeleton` + `HubError` | `feat(p3.4)!: extract HubSkeleton and HubError state primitives` | 45min |
| F.4 | Backend filtre `is_demo` | `fix(p3.4): filter is_demo=False parasites in cockpit/jour API` | 45min |
| F.5 | Tooltip Sol acronymes | `feat(p3.4): use Tooltip Sol component for L4 acronymes` | 45min |
| F.6 | Token KPI Newsreader 38px | `fix(p3.4): align KPI value typography with Design System Spec §5.3` | 30min |
| F.7 | Source guards CI étendus | `test(p3.4): add 2 source guards for naming consistency and contamination prevention` | 30min |
| **TOTAL** | | **7 commits atomiques** | **5h45** |

**Pause utilisateur requise** entre chaque F.x.

---

## Annexe — note sur la contamination commit `3774d2c0`

Le commit `docs(p3.4)` Phase D a embarqué 18 fichiers au lieu de 2 (16 WIP parallèle régulateur/sécurité). Décision : **ne rien faire** (déjà historisé) + lock pre-commit ajouté Phase F.7 (`commit-docs-only-stages-docs`) pour empêcher la récidive.

---

✅ Fin de la décision Phase E.
