# Phase 6.2 — Rail + Panel + Color Life

## Architecture

Replaces the flat sidebar with a **Rail + Panel** pattern inspired by Linear, Figma, and Notion.

### Components

| Component | File | Role |
|-----------|------|------|
| `NavRail` | `layout/NavRail.jsx` | 56px icon rail, always visible. 5 module icons with tinted active states. |
| `NavPanel` | `layout/NavPanel.jsx` | 208px contextual sub-nav. Sections, items, pins, badges, expert filtering. |
| `Sidebar` | `layout/Sidebar.jsx` | Composes Rail + Panel. Manages module/panel state, auto-select from route. |
| `NavRegistry` | `layout/NavRegistry.js` | Central data: modules, sections, routes, tints, helpers. |
| `AppShell` | `layout/AppShell.jsx` | Module-tinted header bands on all pages. |

### Data Model

```
NAV_MODULES (5)        NAV_SECTIONS (6)           Items
 cockpit    ──────────> Piloter                    Tableau de bord, Vue executive, Alertes
 operations ──────────> Executer                   Conformite, Plan d'actions
 analyse    ──────────> Analyser                   Consommations, Performance, Diagnostic*, Patrimoine
 marche     ──────────> Marche & Factures          Facturation, Achats energie, Assistant Achat
 donnees    ──────────> Donnees                    Imports, Connexions, KB, Segmentation, Veille
            └────────> Administration              Utilisateurs, Roles, Assignments, Audit Log
```

### Interaction Model

- **Click module icon**: Switch to that module's panel
- **Click active module icon**: Toggle panel open/close
- **Auto-select**: Route changes auto-switch the active module
- **State persistence**: Active module + panel open/close stored in localStorage

## Module Color System

Each module has a consistent color identity used across rail, panel, and header band:

| Module | Rail Active | Header Band |
|--------|------------|-------------|
| Cockpit | `bg-blue-50 text-blue-600` | `from-blue-50/60` |
| Operations | `bg-emerald-50 text-emerald-600` | `from-emerald-50/35` |
| Analyse | `bg-indigo-50 text-indigo-600` | `from-indigo-50/50` |
| Marche | `bg-violet-50 text-violet-600` | `from-violet-50/40` |
| Donnees | `bg-slate-100 text-slate-700` | `from-slate-100/50` |

## Features Preserved

- **Pins**: Star up to 5 items, shown above sections in panel
- **Severity badges**: Red (alerts), amber (monitoring), blue (default)
- **Expert mode**: Hides Marche/Donnees modules + expert-only sections/items
- **Permissions**: requireAdmin items filtered via AuthContext
- **Collapsible sections**: Chevron toggle, auto-open active section
- **A11y**: `role="tablist"/"tab"/"tabpanel"`, `aria-selected`, `aria-controls`, `focus-visible:ring-2`

## QA

- Build: 0 errors (2548 modules)
- Vitest: 229 tests pass (34 NavRegistry tests)
- Zero route/permission regressions
