# Phase 6.1 — Nav IA v4 + Color "Life" Balance

## Objectif
Corriger l'effet "tout blanc" sans saturation. Refondre l'IA du menu
pour un rendu world-class, oriente jobs-to-be-done. Zero regression.

## Architecture de l'Information (IA v4)

### Sections

| Section | ExpertOnly | Collapsible | Items (normal) | Items (expert) |
|---------|-----------|-------------|----------------|----------------|
| Cockpit | Non | Non | 2 | 2 |
| Operations | Non | Non | 3 | 3 |
| Analyse | Non | Oui (ouvert) | 2 | 3 (+Diagnostic) |
| Marche | Oui | Oui (ferme) | — | 3 |
| Donnees & Admin | Oui | Oui (ferme) | — | 9 (dont 4 admin) |

### Normal mode: ~7 items visibles
- Dashboard, Vue executive
- Plan d'actions, Alertes, Conformite
- Consommations, Performance

### Expert mode: +10 items
- + Diagnostic (dans Analyse)
- + Facturation, Strategie d'achat, Assistant Achat
- + Patrimoine, Imports, Connexions, Segmentation, Referentiels
- + Utilisateurs, Roles, Assignments, Audit Log (admin)

### Changements vs Phase 6
- "Pilotage" → "Cockpit" (plus clair)
- Alertes deplacees de Cockpit vers Operations (job-to-be-done: agir)
- Patrimoine deplace de Analyse vers Donnees & Admin (c'est de la config)
- "Reglages" → "Donnees & Admin" (plus explicite)
- "Achats energie" → "Strategie d'achat" (plus strategique)
- Analyse ouvert par defaut (pas collapsed) car c'est le coeur metier
- Veille (/watchers) retiree du nav (rarement utilisee)
- `order` metadata ajoutee pour tri explicite

## Sidebar v4

### Nouveautes
1. **Pins (favoris)**: bouton etoile sur hover, section "Epingles" en haut (max 5)
   - `localStorage.promeos_sidebar_pins` (JSON array de paths)
   - Etoile pleine amber si pinne, grise transparente sinon
   - Apparait uniquement au hover du lien (opacity-0 → opacity-100)
2. **Active styling**: `bg-blue-50/60 + border-l-2 border-blue-600 + icon text-blue-600`
3. **Hover**: `bg-slate-50` (plus doux que bg-gray-100)
4. **Section headers**: `text-[11px]` plus compact, spacing reduit
5. **Logo**: `text-lg` (plus compact que text-xl), padding py-4

### Conserve de v3.5
- Collapsible sections avec chevron rotatif
- Expert mode progressive disclosure
- Auto-open section par route active
- Persisted section state (localStorage)
- Tinted badges (bg-blue-100 text-blue-700)
- Expert chip indigo dans footer
- Aria labels FR
- Permission filter (requireAdmin, ROUTE_MODULE_MAP)
- Collapsed mode (w-16/w-60)

## AppShell

- Background: `bg-slate-50/60` (tres leger, relief cards vs fond)
- Header: `bg-white/95 backdrop-blur-sm border-gray-200/80` (glass effect subtil)
- **Header gradient band**: sur / et /cockpit uniquement
  - `h-24 bg-gradient-to-b from-blue-50/60 to-transparent -mb-24`
  - Effet "cockpit premium" sans aplat lourd, pointer-events-none

## Color Balance

| Element | Avant | Apres |
|---------|-------|-------|
| Page bg | bg-gray-50 | bg-slate-50/60 |
| Header | bg-white, border-gray-200 | bg-white/95 backdrop-blur, border-gray-200/80 |
| Sidebar border | border-gray-200 | border-gray-200/80 |
| Active link | bg-blue-50 text-blue-700 | + border-l-2 blue-600 + icon blue-600 |
| Hover link | bg-gray-100 | bg-slate-50 |
| Cockpit pages | flat bg | gradient band blue-50/60 |
| Badges | bg-red-500 (avant Phase 6) | bg-blue-100 text-blue-700 |

## QA

- `npm run build`: 0 errors
- `npx vitest run`: 181 passed (7 files)
- Pas de console.error
- Backward-compatible (collapsed, permissions, badges, CommandPalette)
- normalizeDashboardModel (Phase 6) previent incoherences KPI

## DoD

- [x] IA v4: 5 sections jobs-to-be-done (Cockpit/Operations/Analyse/Marche/Donnees)
- [x] Pins (favoris): etoile hover, max 5, localStorage
- [x] Active link: left-border 2px + icon accent blue
- [x] Hover: bg-slate-50
- [x] AppShell: bg-slate-50/60 + header glass + cockpit gradient band
- [x] Progressive disclosure: Normal ~7 items, Expert +10
- [x] CommandPalette existant (Ctrl+K) — pas de changement
- [x] normalizeDashboardModel (Phase 6) — pas de changement
- [x] Build + tests OK
- [x] Doc redigee
