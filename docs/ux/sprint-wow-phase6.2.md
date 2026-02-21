# Sprint WOW Phase 6.2 — Premium Sidebar (Expandable Rail)

## Architecture

Single expandable sidebar replacing the previous Rail + Panel two-column layout.

```
Collapsed (64px)          Expanded (240px, hover or pinned)
┌──────┐                  ┌────────────────────────────┐
│  P   │                  │ P  PROMEOS          [pin]  │
├──────┤                  ├────────────────────────────┤
│      │                  │ Scanner    Importer        │
│      │                  │ Creer act. Lancer ana.     │
│      │                  ├────────────────────────────┤
│ [ic] │                  │ * Epingles                 │
│ [ic] │                  │   Tableau de bord          │
│ ──── │                  │ ~ Recents                  │
│ [ic] │                  │   Conformite               │
│ [ic] │                  ├────────────────────────────┤
│ ──── │                  │ o Piloter          v       │
│ [ic] │                  │   Tableau de bord          │
│ [ic] │                  │   Vue executive            │
│ [ic] │                  │   Alertes         [3]      │
│ [ic] │                  │ o Executer         v       │
│      │                  │   Conformite               │
│      │                  │   Plan d'actions           │
│      │                  │ ...                        │
└──────┘                  └────────────────────────────┘
```

## Behavior

| State | Width | Trigger | Persisted |
|-------|-------|---------|-----------|
| Collapsed (rail) | 64px | Default, or mouseLeave (150ms debounce) | No |
| Expanded (hover) | 240px | mouseEnter | No |
| Expanded (pinned) | 240px | Pin button click | Yes (`promeos.sidebar.pinned`) |

## Features

- **Quick Actions**: 2x2 grid (Scanner, Importer, Creer action, Lancer analyse) — expanded only
- **Epingles**: Star up to 5 items, persisted (`promeos_sidebar_pins`)
- **Recents**: Last 5 visited nav items, auto-tracked (`promeos.nav.recent`), excludes pinned
- **Sections**: Collapsible with colored dot matching module tint
- **Badges**: Severity-aware pills (red/amber/blue with ring)
- **Expert mode**: Hides Marche/Donnees/Admin sections + expertOnly items
- **Permissions**: requireAdmin items filtered via AuthContext

## Color Tint System

| Module | Active BG | Active Text | Active Border | Section Dot |
|--------|-----------|-------------|---------------|-------------|
| Cockpit | blue-50/60 | blue-600 | blue-600 | blue-400 |
| Operations | emerald-50/60 | emerald-600 | emerald-600 | emerald-400 |
| Analyse | indigo-50/60 | indigo-600 | indigo-600 | indigo-400 |
| Marche | violet-50/60 | violet-600 | violet-600 | violet-400 |
| Donnees | slate-100/60 | slate-700 | slate-600 | slate-400 |

## localStorage Keys

| Key | Type | Description |
|-----|------|-------------|
| `promeos.sidebar.pinned` | 'true'/'false' | Lock sidebar expanded |
| `promeos_sidebar_pins` | JSON array | Pinned item paths (max 5) |
| `promeos.nav.recent` | JSON array | Recent nav paths (max 5) |
| `promeos_expert` | 'true'/'false' | Expert mode toggle |

## Files Changed

| File | Action |
|------|--------|
| `src/utils/navRecent.js` | NEW — recent tracking utility |
| `src/utils/__tests__/navRecent.test.js` | NEW — 10 tests |
| `src/layout/NavRegistry.js` | EDIT — added QUICK_ACTIONS, SECTION_TINTS, SIDEBAR_ITEM_TINTS |
| `src/layout/__tests__/NavRegistry.test.js` | EDIT — 41 tests total |
| `src/ui/CommandPalette.jsx` | EDIT — shared QUICK_ACTIONS import |
| `src/layout/Sidebar.jsx` | REWRITE — expandable rail (was Rail+Panel orchestrator) |
| `src/layout/NavRail.jsx` | DELETED |
| `src/layout/NavPanel.jsx` | DELETED |

## QA

- Build: 0 errors (2547 modules)
- Vitest: 246 tests pass (10 test files)
- Zero route regressions
- Pins backward compatible
