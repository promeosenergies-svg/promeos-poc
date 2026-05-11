# Phase 3.4 — Audit UX/UI/CX/CS · Cockpit Jour V2 (commit 0018f45e)

> **Cardinal** : à remplir **après** capture Playwright before/after.
> Audit en 4 dimensions, 32 critères, scoring 0-3 par critère, total /96.
> Seuil GO Phase 3.5 : **≥ 80/96** (83 %) + **0 critère bloquant à 0**.

---

## Méthode

Chaque critère reçoit une note :

- **0** = absent ou cassé (bloquant, doit être corrigé avant Phase 3.5)
- **1** = présent mais à améliorer
- **2** = correct, conforme à la spec
- **3** = excellent, exemplaire

Un critère bloquant à 0 entraîne **NO-GO Phase 3.5** quel que soit le total.

---

## Dimension 1 — UX (User Experience) · /24

### Compréhension immédiate

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 1.1 | **Test 5s** : un DG identifie les 3 décisions à arbitrer en 5 secondes | Faire tester par 3 personnes hors équipe | _ | |
| 1.2 | **Test 30s** : un DG explique l'état du parc HELIOS en 30 secondes | Idem | _ | |
| 1.3 | **Hierarchy** : le hero domine clairement la page | Inspection visuelle | _ | |
| 1.4 | **Vocabulaire** : aucun acronyme non expliqué (BACS, OPERAT, TURPE…) | Grep + survol tooltips | _ | |

### Parcours et navigation

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 1.5 | **Chaque highlight pousse vers une action concrète** | Cliquer les 3 CTA | _ | |
| 1.6 | **Pas de cul-de-sac** | Test navigation | _ | |
| 1.7 | **Retour** : depuis un sous-menu, retour cockpit jour fluide | Test navigation back | _ | |
| 1.8 | **Cross-référence** : valeurs cohérentes entre cockpit jour et autres vues | Vérifier KPIs matchent /energie | _ | |

**Sous-total UX : ___ / 24**

---

## Dimension 2 — UI (User Interface) · /24

### Fidélité à la maquette v2

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 2.1 | **Hero Premium-night** (#072A44 + illustration filaire) | Comparer hero-zoom.png | _ | |
| 2.2 | **3 KPI cards** avec icône, valeur Newsreader 38px, delta mono | Comparer kpi-1/2/3.png | _ | |
| 2.3 | **2 graphes** côte à côte avec question métier en titre | Comparer full-default.png | _ | |
| 2.4 | **3 highlights** différenciés avec border-left sévérité | Comparer highlight-1/2/3.png | _ | |

### Tokens et palette

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 2.5 | **Aucune couleur hardcodée** dans CockpitJour.jsx | grep hex literals | _ | |
| 2.6 | **Premium-night uniquement dans hero** | Inspection | _ | |
| 2.7 | **Triptyque typo** : Fraunces / DM Sans / JetBrains Mono | Inspection DevTools | _ | |
| 2.8 | **Hairlines fines** (0.5px ou 1px) | Inspection DevTools | _ | |

**Sous-total UI : ___ / 24**

---

## Dimension 3 — CX (Customer Experience) · /24

### Confiance et crédibilité

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 3.1 | **Footer SCM** présent (Source · Confiance · MAJ · Méthodologie) | Inspection | _ | |
| 3.2 | **Qualité ≠ Confiance** séparées dans meta hero | Inspection | _ | |
| 3.3 | **KPI 3** affiche "8 % de la souscrite utilisée" (non trompeur) | Source guard SG_HUB_L11_03 vert | _ | |
| 3.4 | **Marque PROMEOS** orthographe correcte partout | Source guard SG_HUB_L11_02 vert | _ | |

### Données et traçabilité

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 3.5 | **Chaque KPI** a unité, source, période, qualité, confiance | Inspection payload | _ | |
| 3.6 | **Highlights différenciés** (catégories distinctes) | Inspection liste | _ | |
| 3.7 | **Impacts différenciés** (pas 4× "3,8 k€") | Idem | _ | |
| 3.8 | **Tooltip aide** sur KPI 3 | Survol KPI 3 | _ | |

**Sous-total CX : ___ / 24**

---

## Dimension 4 — CS (Code & System) · /24

### Architecture composants

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 4.1 | **`<HubKpiCard>` extrait** dans grammar/hub/ | Vérifier import (PAS inline) | _ ← BLOQUANT | |
| 4.2 | **Page CockpitJour.jsx = composition pure** | Lecture (<200 lignes) | _ | |
| 4.3 | **5 primitifs L11** utilisés | Grep imports | _ | |
| 4.4 | **Aucun composant ad-hoc** | Source guards | _ | |

### Tests et CI

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 4.5 | **11 source-guards Vitest** verts | npm run test | _ | |
| 4.6 | **23 tests backend** verts | pytest | _ | |
| 4.7 | **Vitest baseline +11** (4 669 → 4 680) | npm run test:count | _ | |
| 4.8 | **Playwright snapshots** baseline OK | npx playwright test | _ | |

**Sous-total CS : ___ / 24**

---

## Total et décision

```text
UX  : ___ / 24
UI  : ___ / 24
CX  : ___ / 24
CS  : ___ / 24
─────────────────
TOTAL : ___ / 96
```

### Décision Phase 3.5

| Score | Décision |
|---|---|
| **≥ 80 / 96** ET aucun critère à 0 | ✅ **GO Phase 3.5** |
| 65-79 / 96 OU 1-2 critères à 1 | ⏸ **CORRECTION P1** avant Phase 3.5 |
| < 65 / 96 OU 1+ critère à 0 | ❌ **NO-GO** — refactor profond |

### Critères bloquants spécifiques (à 0 = NO-GO automatique)

- **4.1 `<HubKpiCard>` extrait** — si inline, scaling = duplication garantie
- **2.5 Aucune couleur hardcodée** — drift palette
- **3.4 Marque PROMEOS** — atteinte identité
- **4.4 Aucun composant ad-hoc** — drift architectural
