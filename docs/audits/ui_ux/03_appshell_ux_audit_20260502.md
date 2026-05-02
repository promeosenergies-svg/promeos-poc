---
audit: ui_ux_appshell
date: 2026-05-02
branch: claude/refonte-sol2
mode: read-only strict
component: frontend/src/layout/AppShell.jsx
scope: Header app + cloche action center + scope switcher + breadcrumb + mobile drawer
doctrine_ref: docs/vision/promeos_sol_doctrine.md (§5, §6.2)
guidelines: ui-ux-pro-max Quick Reference §1-§9
auteur: Claude Code (Opus 4.7)
---

# Audit UX/UI — AppShell (header + cloche + responsive)

> **Composant** : [frontend/src/layout/AppShell.jsx](../../../frontend/src/layout/AppShell.jsx) (~570 LOC)
>
> **Personas couverts** : tous (le header est partagé indépendamment du rôle).
>
> **Couche audit** : visuel + ergonomie + accessibilité — read-only strict.

---

## 1. Inventaire visuel

### 1.1 Container racine

| Aspect | Valeur | Source |
|---|---|---|
| Layout | `flex h-screen overflow-hidden` | [AppShell.jsx:251](../../../frontend/src/layout/AppShell.jsx#L251) |
| Background | `bg-gradient-to-b from-slate-50 via-white to-slate-50/80` | idem |

### 1.2 Skip link a11y

| Aspect | Valeur | Source |
|---|---|---|
| Visibilité | `sr-only focus:not-sr-only focus:absolute focus:z-[300]` | [AppShell.jsx:253-258](../../../frontend/src/layout/AppShell.jsx#L253-L258) |
| Style focus | `bg-blue-600 text-white rounded-lg text-sm font-medium px-4 py-2` | idem |
| Texte | "Aller au contenu" | idem |

### 1.3 Sidebar conditional render

| Mode | Rendu | Source |
|---|---|---|
| Desktop ≥768px | `<Sidebar />` persistent | [AppShell.jsx:262](../../../frontend/src/layout/AppShell.jsx#L262) |
| Mobile <768px | `<Drawer side="left" title="Navigation">` avec Sidebar dedans | [AppShell.jsx:264-272](../../../frontend/src/layout/AppShell.jsx#L264-L272) |

### 1.4 Header

| Aspect | Valeur | Source |
|---|---|---|
| Layout | `bg-white/80 backdrop-blur-md border-b border-slate-200/70 px-6 py-3 flex items-center justify-between sticky top-0 z-40` | [AppShell.jsx:277](../../../frontend/src/layout/AppShell.jsx#L277) |
| Hamburger mobile | `Menu size={20}` + `p-2 -ml-2 rounded-lg text-slate-500 hover:bg-slate-100` | [AppShell.jsx:281-287](../../../frontend/src/layout/AppShell.jsx#L281-L287) |
| Breadcrumb | composant import | [AppShell.jsx:289](../../../frontend/src/layout/AppShell.jsx#L289) |
| ScopeSwitcher | composant | [AppShell.jsx:291](../../../frontend/src/layout/AppShell.jsx#L291) |
| DataReadinessBadge | composant | [AppShell.jsx:293](../../../frontend/src/layout/AppShell.jsx#L293) |

### 1.5 Command Palette trigger

| Aspect | Valeur | Source |
|---|---|---|
| Layout | `flex items-center gap-2 px-3 py-2 bg-white/60 border border-slate-200/80 rounded-lg` | [AppShell.jsx:300-301](../../../frontend/src/layout/AppShell.jsx#L300-L301) |
| Texte | `text-sm text-slate-400 hover:text-slate-600` | idem |
| "Rechercher..." | `hidden sm:inline` (caché mobile) | [AppShell.jsx:304](../../../frontend/src/layout/AppShell.jsx#L304) |
| ⌘K kbd | `text-[10px] font-mono` | [AppShell.jsx:306](../../../frontend/src/layout/AppShell.jsx#L306) |
| ARIA | `aria-label="Ouvrir la recherche (Ctrl+K)"` | [AppShell.jsx:299](../../../frontend/src/layout/AppShell.jsx#L299) |

### 1.6 Cloche Action Center

| Aspect | Valeur | Source |
|---|---|---|
| Bouton | `relative p-2 bg-white/60 border rounded-lg text-slate-500 hover:text-slate-700` | [AppShell.jsx:318](../../../frontend/src/layout/AppShell.jsx#L318) |
| Icône | `<Bell size={16} />` | [AppShell.jsx:320](../../../frontend/src/layout/AppShell.jsx#L320) |
| Badge | `absolute -top-1 -right-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full min-w-[18px]` | [AppShell.jsx:322-323](../../../frontend/src/layout/AppShell.jsx#L322-L323) |
| Couleur badge | gray (count==null), red (count>=5), amber (1-4) — via `BADGE_COLOR_CLASS` + `useMemo` | [AppShell.jsx:188-200](../../../frontend/src/layout/AppShell.jsx#L188-L200) |
| ARIA | `aria-label="Centre d'actions"` + `title` redondant | [AppShell.jsx:316-317](../../../frontend/src/layout/AppShell.jsx#L316-L317) |

### 1.7 Toggle Expert + onboarding

| Aspect | Valeur | Source |
|---|---|---|
| Toggle | `<Toggle checked={isExpert} onChange={toggleExpert} label="Expert" size="sm" />` | [AppShell.jsx:332](../../../frontend/src/layout/AppShell.jsx#L332) |
| Onboarding tooltip | `absolute top-full right-0 mt-2 w-56 p-3 bg-indigo-600 text-white text-xs rounded-lg` | [AppShell.jsx:334](../../../frontend/src/layout/AppShell.jsx#L334) |
| Animation | `animate-[fadeIn_0.3s_ease-out]` (sans reduced-motion guard) | idem |

---

## 2. Forces ✅

1. **Skip link a11y** ([AppShell.jsx:253-258](../../../frontend/src/layout/AppShell.jsx#L253-L258)) — pattern WCAG SR/keyboard navigation. Visible uniquement au focus.
2. **Header sticky** + glass surface (backdrop-blur-md) — bonne hiérarchie visuelle, le header reste visible au scroll.
3. **Z-index défini** : header z-40, skip-link z-[300], onboarding tooltip z-50 — couches cohérentes (règle `z-index-management` §5).
4. **Mobile responsive** : `useMediaQuery('(min-width: 768px)')` + Drawer overlay + auto-close on route change ([AppShell.jsx:206-208](../../../frontend/src/layout/AppShell.jsx#L206-L208)).
5. **Cloche couleurs sémantiques** : gray (no count), amber (1-4), red (5+) — signal urgence visuel. Badge `min-w-[18px]` garantit une largeur minimum.
6. **ARIA labels** sur tous les boutons interactifs (hamburger, palette, cloche, expert toggle).
7. **Backward-compat** `?actionCenter=open&tab=actions` query-string pour deep-linking depuis les commandes shortcuts ([AppShell.jsx:202-215](../../../frontend/src/layout/AppShell.jsx#L202-L215)).
8. **Glass UI cohérent** : header + sidebar + panel partagent la même fondation glass (bg-white/80 + backdrop-blur).

---

## 3. Issues UX/UI/CS/ergonomie

### P0 — Critiques

#### P0.1 Hamburger mobile touch target sous-dimensionné

[AppShell.jsx:281-287](../../../frontend/src/layout/AppShell.jsx#L281-L287) — bouton `<Menu size={20} />` avec `p-2 -ml-2`.

Calcul touch target : icon 20px + padding 8px×2 = **36px effectif**. Le `-ml-2` est juste un offset margin (n'augmente pas la zone tactile).

- Apple HIG : minimum **44×44 pt** ❌
- Material Design : minimum **48×48 dp** ❌

→ **Sévérité P0** : critique sur mobile (le hamburger est la seule porte d'accès à la navigation).

**Règle violée** : `touch-target-size` (§2). Pattern standard mobile = `p-3` minimum (48px) ou `hitSlop` explicite.

#### P0.2 Cloche Action Center touch target sous-dimensionné

[AppShell.jsx:318](../../../frontend/src/layout/AppShell.jsx#L318) — `<Bell size={16} />` avec `p-2`.

Calcul : 16 + 8×2 = **32px effectif**. Encore plus sous-dimensionné que le hamburger.

→ **Sévérité P0** : aussi critique car action center = hub fonctionnel important.

#### P0.3 Pas de guard reduced-motion sur animations

[AppShell.jsx:334](../../../frontend/src/layout/AppShell.jsx#L334) `animate-[fadeIn_0.3s_ease-out]` sur tooltip onboarding — appliqué inconditionnellement.

**Règle violée** : `reduced-motion` (§1) — patrón répété dans tout le sprint nav.

→ **Sévérité P0** : a11y critique vestibulaire.

#### P0.4 Badge cloche état ambigu count==null vs count==0

[AppShell.jsx:321](../../../frontend/src/layout/AppShell.jsx#L321) — badge rendu si `actionCenterBadge.count !== null`.

- `count === null` → mode dégradé (Provider erreur 3× retry) → badge masqué
- `count === 0` → tout va bien → badge masqué (gray ne s'affiche jamais)
- `count >= 1` → badge visible

**Problème** : du point de vue user, "pas de badge" peut signifier soit "loading", soit "tout va bien", soit "endpoint cassé". 3 états différents → 1 même rendu.

**Règle violée** : `state-clarity` (§4) + `loading-states` (§7) — distinguer empty vs loading.

→ **Sévérité P0** : ambiguïté UX critique sur un signal action.

### P1 — Important

#### P1.1 Header padding fixe `px-6 py-3` non responsive

[AppShell.jsx:277](../../../frontend/src/layout/AppShell.jsx#L277) — `px-6 py-3` est appliqué identiquement desktop et mobile.

- Mobile <768px (avec hamburger) : 24px de padding horizontal réduit l'espace utile (~280px effectif sur viewport 320px)
- Recommandation : `px-4 sm:px-6` pour adapter

→ **Sévérité P1** : mobile UX étroite.

#### P1.2 Search button en mode mobile = icon-only sans label

[AppShell.jsx:304](../../../frontend/src/layout/AppShell.jsx#L304) — texte "Rechercher..." est `hidden sm:inline`. En mobile reste juste l'icône Search size=14.

- ARIA-label présent mais découvrabilité réduite
- Touch target : icon 14 + py-2 = ~30px → **sous-dimensionné** (P0 connecté)

→ **Sévérité P1** : combiné au touch target devient P0.

#### P1.3 Tooltip onboarding mobile overflow

[AppShell.jsx:334](../../../frontend/src/layout/AppShell.jsx#L334) — `w-56` (224px) `right-0`. Sur mobile <320px, le tooltip déborde côté droit.

→ **Sévérité P1** : mobile small.

#### P1.4 Toggle Expert hors contexte mobile

[AppShell.jsx:332](../../../frontend/src/layout/AppShell.jsx#L332) — toggle Expert visible header desktop ET mobile. Sur viewport étroit, la barre droite du header (palette + cloche + toggle) peut s'écraser ou wrapper.

→ **Sévérité P1** : à vérifier visuellement viewports 320-768px.

#### P1.5 Title attribute redondant avec aria-label

[AppShell.jsx:317](../../../frontend/src/layout/AppShell.jsx#L317) — `aria-label="Centre d'actions"` + `title="Centre d'actions"`.

- Pattern legacy : `title` était utilisé comme tooltip natif
- Avec `aria-label` présent, `title` est doublon ; certains screen readers les concatènent → "Centre d'actions Centre d'actions"

→ **Sévérité P1** : a11y bruit.

### P2 — Cosmétiques

#### P2.1 ⌘K vs Ctrl+K platform mismatch
Le bouton search affiche `<Command size={10} />K` toujours (Mac symbol ⌘) — sur Windows/Linux le user pense "Ctrl" mais voit "⌘". Petit signal de non-cross-platform.

#### P2.2 backdrop-blur-md sur header vs backdrop-blur-sm sur sidebar
Header `backdrop-blur-md` vs sidebar `backdrop-blur-sm` → légère incohérence visuelle. Peut être intentionnel (header plus opaque) mais non documenté.

#### P2.3 Onboarding tooltip auto-disappear ?
Le tooltip onboarding ne semble pas avoir de timer auto-dismiss (à vérifier dans `showOnboarding` state). Si trop persistant peut gêner.

#### P2.4 Toggle "Expert" label texte
Le toggle utilise `label="Expert"` — court et clair. Mais l'utilisateur non-tech peut ne pas savoir quel mode est "Expert" vs "Normal". Doctrine §12 (sachant vs non-sachant) — risque de friction.

---

## 4. Recommandations actionables

### Priorité immédiate (P0)

| # | Reco | Impact |
|---|---|---|
| R0.1 | Hamburger : `p-3` au lieu de `p-2` (48×48px effectif) ou ajouter explicit `hitSlop`. Test SG_NAV_FE_06 "no header button < 44pt mobile". | Mobile UX critique |
| R0.2 | Cloche : `p-2.5` ou augmenter Bell `size={18}` (icône 18 + padding 10×2 = 38px → toujours limite ; viser p-3 pour 42px+). | A11y mobile |
| R0.3 | Wrapper toutes animations app : `motion-reduce:animate-none`. | A11y critique |
| R0.4 | Distinguer 3 états badge cloche : `count === null && loading` → spinner gris (loading state), `count === null && error` → icône warning amber discrète, `count >= 1` → badge actuel. | UX clarté |

### Priorité prochaine (P1)

| # | Reco | Impact |
|---|---|---|
| R1.1 | Header padding : `px-4 sm:px-6 py-3` pour adapter mobile. | Mobile UX |
| R1.2 | Bouton search mobile : envisager afficher "Recherche" ou icône loupe + zone tactile élargie. | Discoverability |
| R1.3 | Tooltip onboarding : ajouter `max-w-[calc(100vw-2rem)]` pour clamp mobile. | Mobile |
| R1.4 | Vérifier overflow header droite mobile 320-414px : si overflow, masquer toggle expert avec dropdown menu (3-dots). | Robustesse |
| R1.5 | Retirer `title="Centre d'actions"` (gardons `aria-label`). | A11y propre |

### Priorité backlog (P2)

| # | Reco | Impact |
|---|---|---|
| R2.1 | Détection plateforme Mac/Windows pour kbd ⌘K vs Ctrl+K. Hook `useIsMac()`. | Polish |
| R2.2 | Documenter cohérence backdrop-blur-sm vs blur-md. | Doc |
| R2.3 | Auto-dismiss tooltip onboarding après 8s ou click dehors. | UX |
| R2.4 | Renommer "Expert" en "Mode pro" + tooltip explicatif détaillé. | Clarté |

---

## 5. Validation cross-référencée doctrine PROMEOS

| Doctrine | Conformité |
|---|---|
| §6.2 anti-pattern "menu surchargé" | ✅ — header concis (4 actions max : palette / cloche / expert / hamburger) |
| §11 le bon endroit | ✅ — actions transverses (search, notifications, mode) en header |

---

## 6. STOP audit livrable 3/3

Audit AppShell terminé read-only.

→ **4 P0 critiques** (hamburger touch + cloche touch + reduced-motion + badge ambigu) — tous mobile/a11y.
→ **5 P1 importantes** + **4 P2 cosmétiques** — backlog.

---

## 7. Synthèse cross-livrables (rail + panel + appshell)

### Patterns récurrents identifiés sur les 3 composants

| Pattern | NavRail | NavPanel | AppShell | Sévérité globale |
|---|---|---|---|---|
| **Touch target sous-dimensionné** | RailIcon w-12 h-14 (limite) | — | Hamburger 36px + Cloche 32px | **P0 systémique mobile** |
| **Pas de reduced-motion guard** | transition-all | animate-fadeIn | animate-fadeIn onboarding | **P0 systémique a11y** |
| **Texte sub-12px** | Label 10px, Badge 8px | Desc 11px, kbd 9px, labels 10px | kbd 10px, badge 10px | **P0 systémique lisibilité** |
| **Color life cohérent** | ✅ Tints | ✅ panelHeader gradient | ✅ MODULE_TINTS bandeau | ✅ Force |
| **A11y semantic** | ✅ aria-current | ✅ role="progressbar" | ✅ skip-link | ✅ Force |
| **Glass UI cohérent** | ✅ bg-slate-50/60 | ✅ bg-white/80 | ✅ bg-white/80 | ✅ Force |

### Recommandations sprint UX dédié (estimation)

| Priorité | Items | Estimé commits |
|---|---|---|
| **P0 systémique** | Touch targets (3 composants) + reduced-motion (3) + sub-12px audit (3) + badge cloche états (1) | ~3-4 commits |
| **P1** | Description module overflow + responsive padding + tooltip mobile + recents store unify | ~3-4 commits |
| **P2** | Color life polish + cross-platform kbd + UX cosmétiques | ~2-3 commits |

**Total sprint UX nav estimé** : ~8-11 commits atomiques.

### Action utilisateur 2026-05-02 (à exécuter immédiatement)

> "retire dans le menu la fonctionnalité 'récent'"

→ Réf : NavPanel section "RÉCENTS" ([NavPanel.jsx:163-179, 188-195](../../../frontend/src/layout/NavPanel.jsx) + rendu) + util orphelin [navRecent.js](../../../frontend/src/utils/navRecent.js).

Décision UX cohérente avec audit P0.2 (duplication store) + P2.2 (sub-utilité fonctionnelle). Suppression complète recommandée.

→ Suite : phase fix après livrable audit complet.
