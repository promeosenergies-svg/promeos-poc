# Sprint WOW Phase 6.3 — Navigation OS Finalization

## Architecture: Rail + Panel

```
┌──────┬────────────────────┬──────────────────────────────┐
│ Rail │      Panel         │         Content              │
│ 64px │     208px          │         flex-1               │
│      │                    │                              │
│  [P] │  Module Header     │  header band (gradient)      │
│      │  icon + title      │  breadcrumb + scope          │
│ ┌──┐ │  + description     │                              │
│ │Co│ │                    │                              │
│ └──┘ │  Quick Actions     │                              │
│ ┌──┐ │  (module-scoped)   │         <Outlet />           │
│ │Op│ │                    │                              │
│ └──┘ │  Pins (starred)    │                              │
│ ┌──┐ │  Recents (3 max)   │                              │
│ │An│ │                    │                              │
│ └──┘ │  Section: Donnees  │                              │
│ ┌──┐ │    Patrimoine      │                              │
│ │Ma│ │    Imports          │                              │
│ └──┘ │    Connexions       │                              │
│ ┌──┐ │    ...              │                              │
│ │Ad│ │  Section: Admin     │                              │
│ └──┘ │    Utilisateurs     │                              │
│      │    Roles            │                              │
│ PRO  │    ...              │                              │
└──────┴────────────────────┴──────────────────────────────┘
```

## 5-Module Rule

| # | Module     | Key        | Tint    | Expert |
|---|-----------|------------|---------|--------|
| 1 | Cockpit   | cockpit    | blue    | no     |
| 2 | Operations| operations | emerald | no     |
| 3 | Analyse   | analyse    | indigo  | no     |
| 4 | Marche    | marche     | violet  | yes    |
| 5 | Admin     | admin      | slate   | yes    |

## Key IA Changes (vs Phase 6.2)

- **Module rename**: `donnees` → `admin`
- **Patrimoine moved**: Analyse → Admin (Donnees section, first item)
- **Section key rename**: `admin` → `iam` (IAM = Users/Roles/Assignments/Audit)
- **Module descriptions**: each module now has a `desc` field for panel header
- **Architecture**: back to Rail + Panel (from expandable sidebar)

## Component Files

| File | Role | Lines |
|------|------|-------|
| `NavRegistry.js` | Central data model (modules, sections, routes, tints) | ~190 |
| `NavRail.jsx` | 64px icon strip, tinted active states, tooltip | ~75 |
| `NavPanel.jsx` | Contextual panel with header, quick actions, recents, pins, sections | ~225 |
| `Sidebar.jsx` | Rail + Panel orchestrator, shared state management | ~105 |

## Color Life System

```
SIDEBAR_ITEM_TINTS = {
  blue:    { activeBg, activeText, activeBorder, dot }  // Cockpit
  emerald: { ... }                                       // Operations
  indigo:  { ... }                                       // Analyse
  violet:  { ... }                                       // Marche
  slate:   { ... }                                       // Admin
}
```

Rail active icon: tinted bg + ring-1 border + colored icon.
Panel active link: tinted bg + left border + bold text.

## localStorage Keys

| Key | Purpose |
|-----|---------|
| `promeos_sidebar_pins` | Favorite/pinned nav items (max 5) |
| `promeos.nav.recent` | Recent navigation paths (max 5) |
| `promeos_expert` | Expert mode toggle |

## Tests

- 44 NavRegistry tests covering: 5-module rule, Patrimoine in Admin, IA coherence, route mapping, section tints, expert filtering
- 10 navRecent utility tests
- Build: 0 errors
- Total: 235 vitest passing
