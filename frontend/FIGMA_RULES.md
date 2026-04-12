# PROMEOS Figma Design System Rules

Règles d'intégration Figma → code pour le cockpit PROMEOS. Utilisé par Claude Code + Figma MCP pour générer du code conforme au design system existant.

## 1. Design tokens

### Emplacement
- **Couleurs/accents sémantiques** : `src/ui/colorTokens.js` (`KPI_ACCENTS`, `SEVERITY_TINT`, `HERO_ACCENTS`)
- **Spacing / grid** : `src/ui/conventions.js` (`LAYOUT`)
- **Typographie** : `src/ui/conventions.js` (`TYPO`)
- **Labels FR** : `src/ui/conventions.js` (`LABELS_FR`)
- **Glossaire métier** : `src/ui/glossary.js` (`GLOSSARY`)
- **Navigation / tints** : `src/layout/NavRegistry.js` (`NAV_MODULES`, `TINT_PALETTE`)

### Règle d'or : neutral-first + accents contrôlés
```
Pas de fond plein (bg-red-500). Toujours bg-{color}-50/60 + text-{color}-700 + border-{color}-200.
```

### Mapping sémantique Figma → code
| Figma (intent) | Token code | Exemple |
|----------------|------------|---------|
| Critique / alerte | `Badge status="crit"` | `bg-red-50 text-red-700 border-red-200` |
| Warning / à risque | `Badge status="warn"` | `bg-amber-50 text-amber-700 border-amber-200` |
| Succès / conforme | `Badge status="ok"` | `bg-green-50 text-green-700 border-green-200` |
| Info / neutre | `Badge status="info"` | `bg-blue-50 text-blue-700 border-blue-200` |

## 2. Bibliothèque de composants

### Emplacement unique : `src/ui/`
**Règle absolue** : avant de créer un nouveau composant UI, chercher dans `src/ui/` et `src/components/` s'il existe déjà.

### Composants disponibles (35+)
```
Button, Input, Select, Combobox, Badge, Toggle, Progress, Tooltip
Table, Card, KpiCard, MetricCard, PageShell
Drawer, Modal, Dialog
FilterBar, ActiveFiltersBar, Tabs
EvidenceDrawer, Explain, CommandPalette
Skeleton (SkeletonCard, SkeletonKpi, SkeletonTable)
EmptyState, ErrorState, AsyncState
Pagination, Sparkline, InfoTip
```

### Imports conventionnels
```jsx
// Toujours via le barrel export
import { Card, Button, Badge, PageShell } from '../ui';
// Pour Badge et composants courants, l'import nommé est OK :
import Badge from '../ui/Badge';
```

## 3. Stack technique

- **Framework** : React 18
- **Bundler** : Vite 5
- **Styling** : Tailwind CSS v4 (utility-first, aucun CSS-in-JS)
- **Icônes** : `lucide-react` EXCLUSIVEMENT
- **Routing** : React Router 6
- **State** : React Context + localStorage (pas de Redux/Zustand)
- **HTTP** : Axios (via `src/services/api/core.js`)
- **Tests** : Vitest (node env, structural guards)

## 4. Icônes

**Règle** : `lucide-react` uniquement. Jamais d'autres lib, jamais d'SVG inline.

```jsx
import { Search, Building2, CheckCircle2, AlertTriangle } from 'lucide-react';
<Search size={16} className="text-gray-400" />
```

**Taille standard** : `size={14}` inline, `size={16}` input, `size={20}` headers, `size={32}` hero.

## 5. Layout & responsivité

### Page template obligatoire
```jsx
import { PageShell } from '../ui';
export default function MyPage() {
  return (
    <PageShell>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Titre</h1>
        {/* ... */}
      </div>
    </PageShell>
  );
}
```

### Responsive
- **Mobile-first** : `md:`, `lg:` prefixes
- **Grilles standards** : `LAYOUT.cardGrid3` (1 col mobile → 3 col desktop) et `LAYOUT.cardGrid4`
- **Spacing page** : `LAYOUT.page` (px-6 py-6)
- **Spacing section** : `LAYOUT.sectionGap` (space-y-6)

## 6. Organisation du code

```
src/
├── pages/              # 1 fichier = 1 route
├── components/         # Sous-organisé par domaine (patrimoine/, purchase/, ...)
├── ui/                 # Design system primitives
├── layout/             # AppShell, Sidebar, NavRegistry
├── contexts/           # React Context (Auth, Scope, Demo, ExpertMode)
├── hooks/              # Custom hooks
├── services/
│   ├── api/            # Clients API par domaine (patrimoine.js, billing.js, ...)
│   ├── logger.js
│   └── tracker.js
├── utils/              # format.js (fmtEur, fmtArea, fmtKwh, ...)
└── __tests__/          # Tests structurels
```

### Règle de nommage fichiers
- Pages : `PascalCase.jsx` (ex: `SireneOnboardingPage.jsx`)
- Composants : `PascalCase.jsx`
- Services : `camelCase.js`
- Tests : `*.test.js` (Vitest)

## 7. Patterns métier spécifiques PROMEOS

### Step indicator / Wizard
Quand Figma montre un flow multi-étapes, utiliser le pattern de `SireneOnboardingPage::StepIndicator`. Ne PAS créer un nouveau stepper.

### KPI Card
Utiliser `KpiCard` depuis `src/ui/KpiCard.jsx` avec le `kpiType` sémantique (`conformite`, `risque`, `alertes`, `actions`). Les couleurs sont auto-résolues via `KPI_ACCENTS`.

### Hub de CTA post-action
Pattern `NextStepsHub` (voir `SireneOnboardingPage`) : grille 2×2 de cards avec icône, impact badge, CTA. À réutiliser pour toute page "success" qui doit chaîner vers les étapes suivantes.

### Format helpers (obligatoires pour afficher des chiffres)
```jsx
import { fmtEur, fmtEurFull, fmtKwh, fmtKw, fmtArea, fmtPct, fmtDateFR } from '../utils/format';
fmtEur(23995)       // "24 k€"
fmtEurFull(23995)   // "23 995 €"
fmtKwh(125000)      // "125 MWh"
fmtArea(11600)      // "11,6k m²"
```

**Ne jamais hardcoder `€`, `kWh`, `m²` en JSX. Toujours passer par ces helpers.**

## 8. Règles d'intégration Figma MCP

Quand on importe un design Figma :

1. **Vérifier d'abord si un composant `src/ui/*` correspond** avant de copier la structure Figma.
2. **Mapper les couleurs Figma aux tokens PROMEOS** via `colorTokens.js` (pas de hex dur).
3. **Remplacer les icônes Figma par leur équivalent `lucide-react`**.
4. **Convertir les labels anglais Figma en français** via `LABELS_FR` ou glossaire.
5. **Appliquer `PageShell` comme wrapper** si c'est une page.
6. **Formats numériques** : passer par `utils/format.js`, jamais en dur.
7. **Animations** : utiliser les keyframes de `src/index.css` (`fadeIn`, `slideInUp`, `slideInRight`, `slideInLeft`).

## 9. Anti-patterns à refuser

- ❌ Créer un composant UI sans vérifier `src/ui/`
- ❌ Utiliser MUI, shadcn, Ant Design, Chakra (stack interdite)
- ❌ CSS-in-JS (styled-components, emotion)
- ❌ Hex colors hardcodés hors `colorTokens.js`
- ❌ Icônes hors `lucide-react`
- ❌ Labels en anglais (projet 100% FR)
- ❌ Emojis sauf si explicitement demandé
- ❌ `fontSize: 12px` → utiliser `text-xs`, `text-sm`, etc.
- ❌ `bg-red-500` → toujours `bg-red-50 text-red-700 border-red-200`

## 10. Tests de conformité design

Les tests `src/__tests__/*.test.js` vérifient :
- Présence des imports de tokens
- Pas de calculs hardcodés (source guards)
- Pas de valeurs CO2/kWh en dur
- Structure de navigation cohérente

**Tout nouveau composant Figma-importé doit passer** ces guards.
