# Sprint WOW Phase 6.3 — Premium Life (Depth + Color Life System)

## Color Life System — TINT_PALETTE

Centralized token map in `NavRegistry.js`. One entry per tint, 15 semantic keys each.

```
TINT_PALETTE = {
  blue:    { headerBand, panelHeader, softBg, hoverBg, activeBg, activeText, activeBorder, ... }
  emerald: { ... }
  indigo:  { ... }
  amber:   { ... }    ← marche (was violet)
  slate:   { ... }    ← admin
}
```

### Module → Tint Mapping

| Module     | Tint    | Primary use |
|-----------|---------|-------------|
| cockpit    | blue    | Dashboard, alerts |
| operations | emerald | Conformite, actions |
| analyse    | indigo  | Consommations, performance |
| marche     | amber   | Factures, achats |
| admin      | slate   | Donnees, IAM |

### Semantic Token Keys (per tint)

| Key | Purpose | Example (blue) |
|-----|---------|----------------|
| `headerBand` | AppShell header gradient | `from-blue-50/60 to-transparent` |
| `panelHeader` | Panel module header gradient | `from-blue-50/40 to-transparent` |
| `softBg` | Light background fill | `bg-blue-50/40` |
| `hoverBg` | Hover state | `bg-blue-50/30` |
| `activeBg` | Active item background | `bg-blue-50/60` |
| `activeText` | Active item text | `text-blue-700` |
| `activeBorder` | Active item border | `border-blue-500` |
| `railActiveBg` | Rail active icon bg | `bg-blue-50/70` |
| `railActiveRing` | Rail active ring | `ring-blue-300/50` |
| `railActiveText` | Rail active icon color | `text-blue-600` |
| `dot` | Section dot indicator | `bg-blue-400` |
| `icon` | Icon color | `text-blue-500` |
| `pillBg` | Pill/badge background | `bg-blue-50` |
| `pillText` | Pill/badge text | `text-blue-700` |
| `pillRing` | Pill/badge ring | `ring-blue-200/60` |

### Derived Maps (backward compat)

- `MODULE_TINTS[moduleKey]` → headerBand string (for AppShell)
- `SIDEBAR_ITEM_TINTS[tintName]` → { activeBg, activeText, activeBorder, dot }
- `SECTION_TINTS[sectionKey]` → tint name

### Helper

```js
getModuleTint('cockpit')       // → TINT_PALETTE.blue
getModuleTint('/conformite')   // → TINT_PALETTE.emerald (resolves route → module → tint)
```

## 80/15/5 Rule

- **80% neutral**: bg-white, bg-slate-50, text-slate-600/700/800
- **15% tint**: module-colored surfaces at low opacity (50/30, /40, /60)
- **5% accent**: active borders, icon colors, dots, badges

## Premium Canvas (AppShell)

- Page background: `bg-gradient-to-b from-slate-50 via-white to-slate-50/80`
- Header: `bg-white/80 backdrop-blur-md border-b border-slate-200/70`
- Header band: `h-24` with module tint gradient (was h-20)
- Search button: glass effect with `bg-white/60 shadow-sm`

## Sidebar Surfaces

- **NavRail**: `bg-slate-50/60 backdrop-blur-sm` + glass logo pill
- **NavPanel**: `bg-white/80 backdrop-blur-sm`
- **Separators**: `border-slate-200/40-60` (subtle, consistent)
- **Active**: tinted bg + border-l-2 + colored icon from TINT_PALETTE
- **Hover**: module-tinted hover (hoverBg) + text-slate-900
- **Section headers**: `text-[11px] tracking-wider uppercase text-slate-500` + colored dot

## Tests

- 52 NavRegistry tests (was 44)
- New: TINT_PALETTE (5 tests), getModuleTint (3 tests)
- Updated: amber replaces violet in tint coverage
- Build: 0 errors | 243 vitest passing
