---
audit: ui_ux_navpanel
date: 2026-05-02
branch: claude/refonte-sol2
mode: read-only strict
component: frontend/src/layout/NavPanel.jsx
scope: Panel contextuel ~208px (header tinted + recents + items + progress + search)
doctrine_ref: docs/vision/promeos_sol_doctrine.md (§5, §6.2, §11)
guidelines: ui-ux-pro-max Quick Reference §1-§9
auteur: Claude Code (Opus 4.7)
---

# Audit UX/UI — NavPanel (panel contextuel ~208px)

> **Composant** : [frontend/src/layout/NavPanel.jsx](../../../frontend/src/layout/NavPanel.jsx) (~700 LOC)
>
> **Personas couverts** : ENERGY_MANAGER (default), DG_OWNER, DAF.
>
> **Couche audit** : visuel + ergonomie + accessibilité — read-only strict.

---

## 1. Inventaire visuel

### 1.1 Container

| Aspect | Valeur | Source |
|---|---|---|
| Dimensions | `flex flex-col h-screen`, width `clamp(190px, 14vw, 230px)` | [NavPanel.jsx:328-330](../../../frontend/src/layout/NavPanel.jsx#L328-L330) |
| Background | `bg-white/80 backdrop-blur-sm` (glass) | idem |
| Bordure | `border-r border-slate-200/60` | idem |
| ARIA | `role="navigation"` + `aria-label="Module ${mod.label}"` | [NavPanel.jsx:331-332](../../../frontend/src/layout/NavPanel.jsx#L331-L332) |

### 1.2 Header module (tinted)

| Élément | Valeur | Source |
|---|---|---|
| Padding | `px-3 pt-3 pb-2` | [NavPanel.jsx:337](../../../frontend/src/layout/NavPanel.jsx#L337) |
| Background | `bg-gradient-to-b ${t.panelHeader}` (tint dynamique du module) | idem |
| Animation | `animate-[fadeIn_0.2s_ease-out]` (sans guard reduced-motion) | idem |
| Icône module | `<mod.icon size={16} className={t.icon} />` | [NavPanel.jsx:340](../../../frontend/src/layout/NavPanel.jsx#L340) |
| Label module (h2) | `text-sm font-semibold text-slate-800` | [NavPanel.jsx:341](../../../frontend/src/layout/NavPanel.jsx#L341) |
| Description | `text-[11px] text-slate-400 mt-0.5 leading-snug` | [NavPanel.jsx:343](../../../frontend/src/layout/NavPanel.jsx#L343) |

### 1.3 Bouton "Demander à PROMEOS"

| Aspect | Valeur | Source |
|---|---|---|
| Trigger | déclenche `Ctrl+K` keydown synthétique | [NavPanel.jsx:351](../../../frontend/src/layout/NavPanel.jsx#L351) |
| Layout | `w-full flex items-center gap-2 px-2.5 py-1.5` | [NavPanel.jsx:354](../../../frontend/src/layout/NavPanel.jsx#L354) |
| Texte | `text-[11px] text-slate-400 hover:text-slate-700` | idem |
| Sparkle icon | violet-400 → violet-600 hover, 11px | [NavPanel.jsx:357](../../../frontend/src/layout/NavPanel.jsx#L357) |
| ⌘K kbd | `text-[9px] text-slate-400 bg-slate-100 rounded px-1 py-px font-mono` | [NavPanel.jsx:359-361](../../../frontend/src/layout/NavPanel.jsx#L359-L361) |
| ARIA | `aria-label="Demander à PROMEOS (Ctrl+K)"` | [NavPanel.jsx:355](../../../frontend/src/layout/NavPanel.jsx#L355) |

### 1.4 Section "RÉCENTS" (visible)

| Aspect | Valeur | Source |
|---|---|---|
| Stockage | `localStorage[RECENTS_KEY]` = string[] (clé `'promeos_nav_recents'`) | [NavPanel.jsx:164-179](../../../frontend/src/layout/NavPanel.jsx#L164-L179) |
| Capacity | `MAX_RECENTS = 5` | [NavPanel.jsx:165](../../../frontend/src/layout/NavPanel.jsx#L165) |
| Tracking | `useEffect` push sur changement de `_location.pathname` | [NavPanel.jsx:189-195](../../../frontend/src/layout/NavPanel.jsx#L189-L195) |
| ⚠️ duplication | `utils/navRecent.js` expose `getRecents/addRecent/clearRecents` (clé différente `'promeos.nav.recent'`) — Sidebar utilise cette dernière | [navRecent.js](../../../frontend/src/utils/navRecent.js) |

### 1.5 Section RÉCENTS rendu

[NavPanel.jsx:rendu] — header "RÉCENTS" en text-[10px] uppercase tracking-wider + horloge icône + items récents avec icône + label.

### 1.6 Progress conformité (Phase 2.B P1.2.bis)

| Aspect | Valeur | Source |
|---|---|---|
| Visibilité | `activeModule === 'conformite'` only | [NavPanel.jsx:372](../../../frontend/src/layout/NavPanel.jsx#L372) |
| Header | `text-[9px] font-semibold text-slate-400 uppercase tracking-wider` | [NavPanel.jsx:374](../../../frontend/src/layout/NavPanel.jsx#L374) |
| 3 frameworks | DT (emerald-500) / BACS (indigo-500) / APER (amber-500) | [NavPanel.jsx:378-380](../../../frontend/src/layout/NavPanel.jsx#L378-L380) |
| Hauteur barre | `h-1` (4px) sur fond `bg-slate-100 rounded-full overflow-hidden` | [NavPanel.jsx:394](../../../frontend/src/layout/NavPanel.jsx#L394) |
| Largeur fill | `style={{ width: `${pct}%` }}` + `transition-all duration-300` | [NavPanel.jsx:396-397](../../../frontend/src/layout/NavPanel.jsx#L396-L397) |
| Label framework | `text-[10px] font-medium text-slate-500 w-9` | [NavPanel.jsx:393](../../../frontend/src/layout/NavPanel.jsx#L393) |
| Label pct | `text-[10px] text-slate-400 w-7 text-right` | [NavPanel.jsx:399](../../../frontend/src/layout/NavPanel.jsx#L399) |
| ARIA | `role="group" aria-label="Progression obligations"` + `role="progressbar" aria-valuenow/min/max` | [NavPanel.jsx:373, 387-391](../../../frontend/src/layout/NavPanel.jsx#L373) |

### 1.7 Items panel (rendering)

Items Phase 2.B P1.2.bis recâblage progress + structure pinned/sections inchangée.

---

## 2. Forces ✅

1. **Width responsive** `clamp(190px, 14vw, 230px)` — pattern adaptive par viewport, évite les box trop larges sur 1366px et trop étroites sur tablettes.
2. **Header tinted gradient** par module (panelHeader from TINT_PALETTE) — cohérent avec NavRail, signale immédiatement le contexte d'usage.
3. **Animation fadeIn 200ms** sur changement de module — micro-interaction conforme (150-300ms range, règle `duration-timing` §7).
4. **Bouton "Demander à PROMEOS"** : pattern command-palette discoverability + ⌘K kbd visible — bonne pratique (DiscoverabilityFirst).
5. **Progress conformité a11y exemplaire** : `role="group"` + `aria-label` + 3× `role="progressbar"` avec `aria-valuenow/min/max`. Couverture WCAG complète (§1, §10).
6. **ARIA container** `aria-label="Module ${mod.label}"` — annonce dynamique au screen reader sur changement de module.
7. **Permission filter** sur les items via `hasPermission` — items invisibles si user n'a pas les droits. Sécurité UX cohérente.
8. **Site search inline** (module Patrimoine) avec raccourci `/` + Escape pour fermer — pattern terminal/vim-like utile pour power users.

---

## 3. Issues UX/UI/CS/ergonomie

### P0 — Critiques

#### P0.1 Description module 11px sub-lisibilité

[NavPanel.jsx:343](../../../frontend/src/layout/NavPanel.jsx#L343) `text-[11px] text-slate-400 mt-0.5 leading-snug`.

- 11px < 12px minimum recommandé `readable-font-size` (§6)
- `text-slate-400` (#94A3B8) sur le panelHeader gradient (gradient from-blue-50/40 etc.) → contraste **non garanti** WCAG AA 4.5:1.

**Règles violées** : `readable-font-size` + `contrast-readability` + `color-accessible-pairs`.

→ **Sévérité P0** : la description module est un secondary text régulièrement consulté par l'utilisateur — sub-lisible = friction permanente.

#### P0.2 Recents store dupliqué et déconnecté

[NavPanel.jsx:164-179](../../../frontend/src/layout/NavPanel.jsx#L164-L179) maintient son propre store `localStorage[promeos_nav_recents]` (string[]) tandis que [navRecent.js](../../../frontend/src/utils/navRecent.js) expose un autre store `localStorage[promeos.nav.recent]` (object[]) utilisé par Sidebar.

→ **Sévérité P0** : 2 sources de vérité incohérentes pour la même feature. Bug latent : si l'utilisateur navigue via Sidebar, la liste `RÉCENTS` du NavPanel n'est PAS mise à jour (clés différentes, formats différents).

**Note** : pré-existant au sprint nav (commit cd623b8f5 du 2026-04-12). Tracké en P2 dette mais réévalué P0 ici car visible utilisateur.

#### P0.3 Bouton "Demander à PROMEOS" ressemble à un input désactivé

[NavPanel.jsx:354](../../../frontend/src/layout/NavPanel.jsx#L354) — `bg-slate-50/70`, `text-slate-400`, `border-slate-200/60`.

- Apparence très "placeholder/disabled-like" (slate-400 sur bg-slate-50 = très peu de contraste)
- Le user peut penser que c'est une zone non-interactive ou un input grisé
- L'icône Sparkles violet est le seul signal d'interactivité

**Règles violées** : `state-clarity` (§4) — ne pas confondre avec disabled. `primary-action` (§4) — un appel-à-action doit être visible.

→ **Sévérité P0** : feature critique (entrée vers Command Palette) sous-utilisée pour cause de visibilité faible.

### P1 — Important

#### P1.1 Progress bar h-1 (4px) lisibilité limite

[NavPanel.jsx:394](../../../frontend/src/layout/NavPanel.jsx#L394) `h-1` = 4px de hauteur pour la barre.

- Sur écrans haute densité (Retina), 4px reste perceptible mais le `bg-slate-100` (fond non rempli) vs colored fill ne donne qu'~2-3 pixels effectifs colorés sur des progress 50-70%
- La règle `chart-readability` (§10) recommande au moins 6-8px pour progress bars compactes

→ **Sévérité P1** : data perception réduite, surtout pour utilisateurs low-vision.

#### P1.2 Label "DT/BACS/APER" 10px

[NavPanel.jsx:393](../../../frontend/src/layout/NavPanel.jsx#L393) `text-[10px] font-medium text-slate-500 w-9`.

- 10px < 12px minimum
- Acronymes (DT/BACS/APER) déjà denses cognitivement — taille petite ajoute friction

→ **Sévérité P1** : ergonomie longue durée.

#### P1.3 Animation fadeIn sans reduced-motion

[NavPanel.jsx:337](../../../frontend/src/layout/NavPanel.jsx#L337) `animate-[fadeIn_0.2s_ease-out]` — pas de guard `motion-reduce:animate-none`.

→ **Sévérité P1** : a11y, mais animation très courte (200ms) donc impact moindre que sur NavRail.

#### P1.4 Descriptions items module potentiellement trop longues

`mod.desc` ([NavRegistry.js NAV_MODULES](../../../frontend/src/layout/NavRegistry.js#L210)) ex : "Synthèse & décisions", "Sites, contrats & factures", "Échéances & arbitrage énergie". Avec `text-[11px] leading-snug` sur 200px width, certaines descriptions peuvent overflow ou wrapper sur 2 lignes — incohérent visuellement.

→ **Sévérité P1** : à vérifier avec les 7 modules.

### P2 — Cosmétiques

#### P2.1 ⌘K kbd 9px illisible
[NavPanel.jsx:359](../../../frontend/src/layout/NavPanel.jsx#L359) `text-[9px]` — purement décoratif à cette taille.

#### P2.2 Section RÉCENTS sub-utilité
La section RÉCENTS n'a pas de signal de valeur fort : elle duplique le pattern panel main items + l'historique navigateur. Et avec le bug duplication store P0.2, elle peut afficher des entrées obsolètes ou vides.

→ **Question UX** : RÉCENTS est-il vraiment utile vs un Command Palette ⌘K avec historique de recherche ?

#### P2.3 Site search "/" shortcut conflicting
[NavPanel.jsx:227](../../../frontend/src/layout/NavPanel.jsx#L227) — capture `/` keydown global. Conflits potentiels avec Vim users habitués au `/` pour search dans des inputs/codeblocs. Le guard `tagName === INPUT/TEXTAREA` couvre la plupart des cas mais pas les contenteditable customs.

---

## 4. Recommandations actionables

### Priorité immédiate (P0)

| # | Reco | Impact estimé |
|---|---|---|
| R0.1 | Description module : `text-xs` (12px) au lieu de `text-[11px]` + `text-slate-500` (au lieu de slate-400) pour atteindre 4.5:1 sur gradient. | Lisibilité |
| R0.2 | **Retirer la feature RÉCENTS** ou unifier sur `utils/navRecent.js`. Décision UX : la valeur ajoutée vs le coût de maintenance + bug duplication justifie la suppression (cf. message utilisateur 2026-05-02 : "retire la fonctionnalité Récents"). | Cohérence + simplification |
| R0.3 | Bouton "Demander à PROMEOS" : changer `text-slate-400` → `text-slate-600`, `bg-slate-50/70` → `bg-violet-50/40` (signal couleur Sparkles), border violet-200. Renforce le call-to-action. | Discoverability |

### Priorité prochaine (P1)

| # | Reco | Impact |
|---|---|---|
| R1.1 | Progress bar `h-1.5` (6px) au lieu de `h-1`. Garde la discrétion + lisibilité +50%. | Data perception |
| R1.2 | Labels DT/BACS/APER : passer à `text-xs` (12px) + ajuster `w-9` → `w-12` pour éviter truncation. | Lisibilité |
| R1.3 | Wrapper toutes animations panel par `motion-reduce:animate-none`. | A11y |
| R1.4 | Vérifier visuellement les 7 modules avec leur `desc` à 200px de width. Si certains overflow → tronquer ou raccourcir le `desc`. | Cohérence |

### Priorité backlog (P2)

| # | Reco | Impact |
|---|---|---|
| R2.1 | ⌘K kbd : passer à `text-[10px]` minimum. | Lisibilité |
| R2.2 | Réévaluer la section RÉCENTS dans son ensemble — supprimer ou refactor sur SoT. | Simplification (résolu via R0.2) |
| R2.3 | Documenter le shortcut `/` de site-search dans une légende d'aide ⌘K. | Discoverability |

---

## 5. Validation cross-référencée doctrine PROMEOS

| Doctrine | Conformité |
|---|---|
| §5 grammaire éditoriale (kicker + titre + narrative + KPIs) | ⚠️ — header module bien (kicker + titre + desc) mais panel n'est pas une page Sol — N/A |
| §6.2 anti-pattern "menu surchargé" | ⚠️ — sections multiples (header + ask + recents + progress + pinned + items + admin) cumulent vite. Densité élevée. |
| §11 le bon endroit | ✅ — items du module actif uniquement, séparation claire admin secondary |

---

## 6. STOP audit livrable 2/3

Audit NavPanel terminé read-only.

→ **3 P0** (description sub-lisible, recents duplication store, bouton Demander à PROMEOS faible visibility) — fix dont **R0.2 est demandé explicitement par l'utilisateur 2026-05-02 (retrait feature RÉCENTS)**.
→ **4 P1 importantes** + **3 P2 cosmétiques** — backlog.

Suite : audit livrable 3/3 (AppShell) → [03_appshell_ux_audit_20260502.md](./03_appshell_ux_audit_20260502.md).
