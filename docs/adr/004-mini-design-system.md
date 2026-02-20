# ADR-004: Mini Design System — Composants UI maison sans bibliotheque externe

**Date**: 2026-02-11
**Statut**: Accepted
**Auteurs**: Equipe PROMEOS

---

## Contexte

PROMEOS est un cockpit B2B avec 30+ pages, des KPIs metier specifiques (conformite, risque, alertes), et un vocabulaire visuel propre (severite, modules, accents). Le frontend React 18 utilise Tailwind CSS pour le styling. Le produit est en phase POC/pilote avec un rythme de livraison eleve.

---

## Probleme

Comment garantir la coherence visuelle sur 30+ pages sans investir le temps d'integration d'une bibliotheque de composants generique (MUI, Chakra, Radix)?

---

## Options envisagees

### Option A: Material-UI / Ant Design

- (+) Composants riches, accessibilite native, theming
- (-) Bundle size (+100-200 KB gzipped)
- (-) Contraintes d'API: adapter le design PROMEOS aux patterns MUI
- (-) Surcharge CSS pour overrider le theme
- (-) Complexite de customisation des KpiCard, MetricCard, severity tokens

### Option B: Radix + shadcn/ui

- (+) Primitives headless, bonne accessibilite
- (+) Tailwind-native (shadcn)
- (-) Setup initial significatif (copy-paste components)
- (-) Les composants metier (KpiCard, MetricCard, ScopeSummary) n'existent pas
- (-) Dependance a un ecosysteme tiers pour un POC

### Option C: Mini design system maison (retenu)

- (+) 26 composants tailles sur mesure pour le domaine energie/conformite
- (+) Zero dependance supplementaire (Tailwind seul)
- (+) Bundle minimal: ~5 deps de production (react, axios, lucide, recharts, react-router)
- (+) Controle total sur l'API des composants
- (+) Tokens semantiques (KPI_ACCENTS, SEVERITY_TINT) alignes sur le vocabulaire metier
- (-) Accessibilite a gerer manuellement (focus rings, Tab traps, ARIA)
- (-) Pas de documentation Storybook (compense par conventions.js)

---

## Decision

**Option C retenue.** (Decision D4 du functional_spec.md)

### Architecture du design system

```
frontend/src/ui/
  ├── index.js              # Barrel export (source unique d'imports)
  ├── tokens.js             # Palette couleurs, spacing, radius
  ├── colorTokens.js        # Tokens semantiques: KPI_ACCENTS, SEVERITY_TINT, ACCENT_BAR, HERO_ACCENTS
  ├── conventions.js        # LAYOUT, TYPO, LABELS_FR
  ├── Button.jsx            # Variants: primary, secondary, ghost, danger
  ├── Card.jsx              # Card + CardHeader + CardBody
  ├── MetricCard.jsx        # KPI card avec accent bar, icon pill, trend
  ├── KpiCard.jsx           # KPI card v1 (compact)
  ├── Table.jsx             # Composable: Table, Thead, Tbody, Th, Tr, Td
  ├── Modal.jsx             # Focus trap, Escape, Tab cycling
  ├── PageShell.jsx         # Wrapper page standard (icon + title + actions)
  └── ... (26 composants total)
```

### Systeme de couleurs: regle 80/15/5

- **80% neutral**: surfaces grises (`bg-slate-50`, `bg-white`)
- **15% module tints**: identite de navigation (cockpit=blue, operations=emerald, analyse=indigo, marche=amber, admin=slate)
- **5% severity signals**: alertes/badges (`critical=red, high=orange, warn=amber, info=blue`)

API unifiee via l'objet `tint`:

```javascript
tint.module('cockpit').navActive()    // "bg-blue-50/60 text-blue-700 border-blue-500"
tint.severity('critical').badge()     // "bg-red-50 text-red-700 border border-red-200"
```

### Conventions partagees

```javascript
LAYOUT.page       = 'px-6 py-6'
LAYOUT.cardGrid3  = 'grid grid-cols-1 md:grid-cols-3 gap-6'
TYPO.pageTitle    = 'text-xl font-bold text-gray-900'
TYPO.kpiValue     = 'text-2xl font-bold text-gray-900'
LABELS_FR.loading = 'Chargement...'
```

### Evolution par versions

| Version | Sprint | Ajouts |
|---------|--------|--------|
| V1 | WOW DIAMANT | PageShell, KpiCard, FilterBar, Toast, Drawer |
| V2 | Top Pages WOW | MetricCard, StatusDot |
| V3 | Phase 6 | Tokens semantiques (KPI_ACCENTS, SEVERITY_TINT) |
| V4 | Scope coherence | ScopeSummary |
| V5 | UX standardisation | LAYOUT, TYPO, LABELS_FR |

---

## Consequences

### Positives

- **Bundle leger**: 5 deps de production, pas de CSS-in-JS runtime
- **Coherence**: barrel export + tokens + conventions = vocabulaire partage
- **Vitesse**: pas de boilerplate d'integration, composants crees en minutes
- **Domaine-specifique**: MetricCard avec severity, accent bar, trend — impossible avec un composant generique
- **25 tests** (colorTokens, KpiCard, DesignSystem source guards)

### Negatives

- L'accessibilite est geree au cas par cas (Modal: focus trap + Tab + Escape, Button: focus-visible ring). Pas de couverture automatique.
- Pas de documentation interactive (Storybook). Les conventions sont dans `conventions.js` et `colorTokens.js`.
- Chaque nouveau composant est cree from scratch (pas de primitives headless)

### Risques acceptes

- Si PROMEOS passe en production avec 50+ pages, une migration vers Radix primitives pourrait etre necessaire pour l'accessibilite. Le barrel export (`ui/index.js`) rend cette migration non-cassante: les imports ne changent pas.
