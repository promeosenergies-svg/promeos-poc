# Phase 6 — Navigation Redesign + Color Balance

## Objectif
Navigation world-class avec progressive disclosure via ExpertMode.
Normal: max ~7 items visibles (Pilotage + Execution + Analyse core).
Expert: + Diagnostic + Marche & factures + Reglages.

## Architecture de l'Information (IA)

### Sections

| Section | ExpertOnly | Collapsible | Items (normal) | Items (expert) |
|---------|-----------|-------------|----------------|----------------|
| Pilotage | Non | Non | 3 | 3 |
| Execution | Non | Non | 2 | 2 |
| Analyse | Non | Oui (ferme) | 3 | 4 (+Diagnostic) |
| Marche & factures | Oui | Oui (ferme) | — | 3 |
| Reglages | Oui | Oui (ferme) | — | 9 (dont 4 admin) |

### Normal mode: ~8 items visibles
- Tableau de bord, Vue executive, Alertes
- Conformite, Plan d'actions
- Patrimoine, Consommations, Performance

### Expert mode: +12 items
- + Diagnostic (dans Analyse)
- + Facturation, Achats energie, Assistant Achat
- + Imports, Connexions, Segmentation, Veille, Referentiels
- + Utilisateurs, Roles, Assignments, Audit Log (admin)

## NavRegistry.js

- `NAV_SECTIONS[]` avec flags `expertOnly`, `collapsible`, `defaultCollapsed`
- Item-level `expertOnly` (ex: Diagnostic dans Analyse)
- `ROUTE_MODULE_MAP` enrichi avec routes admin (/admin/roles, /assignments, /audit)
- `ALL_NAV_ITEMS` flat list pour CommandPalette

## Sidebar.jsx v3.5

### Nouveautes
1. **CollapsibleSection**: chevron rotatif + aria-expanded, toggle section
2. **Progressive disclosure**: `section.expertOnly && !isExpert` masque les sections
3. **Item-level filter**: `item.expertOnly && !isExpert` masque les items individuels
4. **Badges tinted**: `bg-blue-100 text-blue-700` (pas `bg-red-500 text-white`)
5. **Section state persisted**: `localStorage.promeos_sidebar_sections` (JSON)
6. **Auto-open**: si la route active est dans une section fermee, elle s'ouvre
7. **Expert indicator**: footer montre "Expert" chip quand mode actif
8. **Aria labels FR**: "Navigation principale", "Menu principal", "Deployer/Reduire"

### Backward-compatible
- Collapsed sidebar (w-16/w-60) inchange
- SidebarLink identique (active=bg-blue-50)
- Permission filter (requireAdmin, ROUTE_MODULE_MAP) inchange
- Badge fetch (notifications + monitoring) inchange

## AppShell.jsx

- Background raffine: `bg-slate-50/80` (plus chaud que `bg-gray-50`)
- Header, Expert toggle, UserMenu, CommandPalette inchanges

## Color Balance (coherent avec Phase 6 Dashboard)

- Badges: blue-100/blue-700 (tinted, pas agressif)
- Active link: bg-blue-50 text-blue-700
- Section labels: text-gray-400 uppercase, hover text-gray-600
- Chevron: text-gray-400, 150ms rotate transition
- Expert chip: bg-indigo-50 text-indigo-600

## QA

- `npm run build`: 0 errors
- `npx vitest run`: 181 passed (7 files)
- Pas de console.error
- Backward-compatible (collapsed sidebar, permissions, badges)
- Routes: tous les items NavRegistry ont des routes correspondantes dans App.jsx

## DoD

- [x] IA redesign: 5 sections jobs-to-be-done
- [x] Progressive disclosure: Normal ~8 items, Expert +12
- [x] Collapsible sections avec persistance
- [x] Badges tinted (pas agressifs)
- [x] Auto-open section si route active
- [x] Aria labels FR
- [x] Expert indicator dans footer
- [x] Routes admin completes dans ROUTE_MODULE_MAP
- [x] Build + tests OK
- [x] Doc redigee
