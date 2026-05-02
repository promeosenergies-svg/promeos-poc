---
audit: ui_ux_navrail
date: 2026-05-02
branch: claude/refonte-sol2
mode: read-only strict
component: frontend/src/layout/NavRail.jsx
scope: Rail icônes latéral 64px multi-persona (default / DG_OWNER / DAF)
doctrine_ref: docs/vision/promeos_sol_doctrine.md (§5, §6.2, §11)
guidelines: ui-ux-pro-max Quick Reference §1-§9
auteur: Claude Code (Opus 4.7)
---

# Audit UX/UI — NavRail (rail icônes latéral 64px)

> **Composant** : [frontend/src/layout/NavRail.jsx](../../../frontend/src/layout/NavRail.jsx) (110 LOC)
>
> **Personas couverts** : ENERGY_MANAGER (default Sol v1.1), DG_OWNER, DAF — différence d'ordre via `getOrderedModules(role, isExpert)`.
>
> **Couche audit** : visuel + ergonomie + accessibilité — read-only strict.

---

## 1. Inventaire visuel

### 1.1 Container

| Aspect | Valeur | Source |
|---|---|---|
| Largeur | `w-16` (64px) | [NavRail.jsx:65](../../../frontend/src/layout/NavRail.jsx#L65) |
| Hauteur | `h-screen` (100vh) | idem |
| Background | `bg-slate-50/60 backdrop-blur-sm` (glass) | idem |
| Bordure | `border-r border-slate-200/60` | idem |
| Padding | `py-3` + `gap-1` (rythme vertical) | idem |
| ARIA | `role="navigation"` + `aria-label="Modules"` | [NavRail.jsx:66-67](../../../frontend/src/layout/NavRail.jsx#L66-L67) |

### 1.2 Items rail (RailIcon)

| Aspect | Valeur | Source |
|---|---|---|
| Dimensions bouton | `w-12 h-14` (48 × 56 px) | [NavRail.jsx:33](../../../frontend/src/layout/NavRail.jsx#L33) |
| Forme | `rounded-xl` | idem |
| Transition | `transition-all duration-150` (pas de `motion-reduce` guard) | idem |
| Focus | `focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1` | [NavRail.jsx:34](../../../frontend/src/layout/NavRail.jsx#L34) |
| Active state | `${t.railActiveBg} ring-1 ${t.railActiveRing} ${t.railActiveText}` (tint dynamique) | [NavRail.jsx:36-37](../../../frontend/src/layout/NavRail.jsx#L36-L37) |
| Inactive state | `text-slate-400 hover:bg-slate-100 hover:text-slate-600` | [NavRail.jsx:38](../../../frontend/src/layout/NavRail.jsx#L38) |
| ARIA | `aria-label={tipText}` + `aria-current={isActive ? 'true' : undefined}` | [NavRail.jsx:40-41](../../../frontend/src/layout/NavRail.jsx#L40-L41) |
| Icône | `<Icon size={20} />` (lucide-react) | [NavRail.jsx:43](../../../frontend/src/layout/NavRail.jsx#L43) |
| Badge count | `w-4 h-4` (16 × 16 px), `text-[8px] font-bold bg-red-500 text-white rounded-full` | [NavRail.jsx:45](../../../frontend/src/layout/NavRail.jsx#L45) |
| Badge truncation | `> 9 ? '9+' : count` | [NavRail.jsx:46](../../../frontend/src/layout/NavRail.jsx#L46) |
| Label texte | `text-[10px] mt-0.5 leading-tight opacity-80` | [NavRail.jsx:49](../../../frontend/src/layout/NavRail.jsx#L49) |
| Tooltip | `<TooltipPortal text={tipText} position="right">` | [NavRail.jsx:30](../../../frontend/src/layout/NavRail.jsx#L30) |

### 1.3 Logo + séparateur + PRO badge

| Élément | Valeur | Source |
|---|---|---|
| Logo "P" | `w-10 h-10 mb-3 rounded-xl bg-white/80 shadow-sm ring-1`, `text-lg font-bold text-blue-600` | [NavRail.jsx:70-72](../../../frontend/src/layout/NavRail.jsx#L70-L72) |
| Séparateur Patrimoine | `w-8 h-[0.5px] my-2 bg-slate-300/60`, `role="separator" aria-orientation="vertical"` | [NavRail.jsx:82-89](../../../frontend/src/layout/NavRail.jsx#L82-L89) |
| PRO badge expert | `text-[9px] font-bold bg-indigo-50 text-indigo-600 ring-1` | [NavRail.jsx:101-106](../../../frontend/src/layout/NavRail.jsx#L101-L106) |

---

## 2. Forces ✅

1. **Tints color-life cohérents** ([TINT_PALETTE](../../../frontend/src/layout/NavRegistry.js#L259-L379)) — chaque module a sa couleur (blue/emerald/indigo/amber/violet/cyan/slate) appliquée à 12 propriétés Tailwind (railActiveBg, railActiveRing, railActiveText, etc.). Cohérence visuelle exemplaire.
2. **A11y semantic complète** : `role="navigation"`, `aria-label="Modules"`, `aria-label` par bouton, `aria-current` sur module actif, `role="separator"` + `aria-orientation` sur le boundary Patrimoine. Couverture WCAG/ARIA correcte sur la plupart des règles §1.
3. **Focus visible** : `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1` — ring 2px + offset 1px conforme à la règle `focus-states` (Apple HIG, MD).
4. **Tooltip on hover** (TooltipPortal position="right") — bonne pratique discoverability quand le label texte est petit. Compense la limite 10px du label.
5. **Truncation badge** `> 9 ? '9+' : count` — pattern standard évite l'overflow visuel.
6. **Layout flexbox vertical** propre : logo en haut → modules → flex-1 → expert badge en `mt-auto`. Hiérarchie spatiale claire.
7. **Séparateur graphique discret** (h-[0.5px]) avec ARIA correct — implémente doctrine §6.2 anti-pattern "pas de label Configuration" tout en signalisant la frontière config / lookup. Élégant.
8. **Role-based ordering** côté `getOrderedModules(role, isExpert)` — chaque persona a son ordre cohérent fréquence d'usage. Différenciant B2B fort.

---

## 3. Issues UX/UI/CS/ergonomie

### P0 — Critiques

#### P0.1 Touch target sous-dimensionné mobile

[NavRail.jsx:33](../../../frontend/src/layout/NavRail.jsx#L33) bouton `w-12 h-14` = **48 × 56 px**.

- Apple HIG : minimum **44 × 44 pt** ✅ OK
- Material Design : minimum **48 × 48 dp** ✅ OK *en théorie*
- **MAIS** le label texte 10px occupe ~10-12px en bas, donc la zone "icône + texte" effective est ~32-36px côté icône seul. L'utilisateur tape généralement sur l'icône (pas sur le label) → zone d'intention tactile sous-dimensionnée.

**Règle violée** : `touch-target-size` (Quick Reference §2) — extend hit area beyond visual bounds if needed.

→ **Sévérité P0** : impacte tous les mobiles + tablettes en mode portrait.

#### P0.2 Badge count text-[8px] sous-lisible

[NavRail.jsx:45](../../../frontend/src/layout/NavRail.jsx#L45) `text-[8px] font-bold bg-red-500 text-white`.

- `readable-font-size` (Quick Reference §5) : minimum 16px body, 12px minimum acceptable pour métadonnées
- 8px est en-dessous de tous les seuils de lisibilité, même pour un badge numérique
- Contraste `bg-red-500` vs `text-white` non vérifié (red-500 = #EF4444, white = #FFFFFF → ratio ~3.7:1 — **insuffisant** pour les 4.5:1 requis WCAG AA sur petit texte)

**Règles violées** : `readable-font-size` + `contrast-readability` + `color-accessible-pairs` (§6).

→ **Sévérité P0** : a11y + ergonomie sur tous viewports.

#### P0.3 Pas de support reduced-motion

[NavRail.jsx:33](../../../frontend/src/layout/NavRail.jsx#L33) `transition-all duration-150` — appliqué inconditionnellement.

**Règle violée** : `reduced-motion` (Quick Reference §1) — respect prefers-reduced-motion ; reduce/disable animations when requested.

→ **Sévérité P0** : a11y critique. Utilisateurs avec troubles vestibulaires ou sensibilité au mouvement n'ont pas d'opt-out.

### P1 — Important

#### P1.1 Logo "P" sans aria-label

[NavRail.jsx:70-72](../../../frontend/src/layout/NavRail.jsx#L70-L72) — wrapper `<div>` avec lettre "P" stylée. Pas de `aria-label="PROMEOS"` ni `role="img"`. Screen reader annoncera "P" — illisible.

**Règle violée** : `alt-text` + `aria-labels` (§1).

→ **Sévérité P1** : non-bloquant pour la navigation (logo n'est pas cliquable) mais communication brand absente pour SR.

#### P1.2 Label module 10px sub-lisibilité

[NavRail.jsx:49](../../../frontend/src/layout/NavRail.jsx#L49) `text-[10px]` — sous le seuil 12px de la règle `readable-font-size`. Tooltip mitige le problème mais le label permanent doit rester lisible (l'utilisateur ne hover pas systématiquement).

→ **Sévérité P1** : ergonomie longue durée + accessibility low-vision users.

#### P1.3 Séparateur h-[0.5px] anti-aliasing fragile

[NavRail.jsx:87](../../../frontend/src/layout/NavRail.jsx#L87) `h-[0.5px]`. Sur écrans non-Retina (ratio 1x), 0.5px est sous-pixel et peut disparaître selon le rendu navigateur. La sémantique a11y (`role="separator"`) reste mais le signal visuel est fragile.

→ **Sévérité P1** : invisibilité possible sur écrans standard.

#### P1.4 Badge count vs progress conformite incohérence

Le rail rend les badges via `MODULE_BADGE_KEY` ([NavRail.jsx:18-21](../../../frontend/src/layout/NavRail.jsx#L18-L21)) avec mapping `conformite: 'alerts'` et `energie: 'monitoring'`. Mais Phase 1.D a ajouté le module `facturation` avec badge `billing_anomalies` et P0.5 a ajouté progress conformité. La constante `MODULE_BADGE_KEY` n'a pas été étendue → **module `facturation` n'a pas de badge rendu sur le rail** alors que `billing_anomalies` est présent dans `NavBadgesResponse`.

→ **Sévérité P1** : inconsistance avec les capacités backend (le compteur existe mais n'est pas exposé).

### P2 — Cosmétiques

#### P2.1 Glass surface peu visible sur fond blanc
`bg-slate-50/60 backdrop-blur-sm` = quasi invisible sur le `bg-gradient-to-b from-slate-50 via-white` du AppShell. L'effet glass est subtil mais peu différencié.

#### P2.2 Pas de pressed/active state distinct
Hover existe (`hover:bg-slate-100`) mais pas de visual scale/opacity sur press. La règle `press-feedback` (§4) recommande un retour visuel ripple/highlight à l'appui.

#### P2.3 PRO badge ambigu
Apparence `bg-indigo-50 text-indigo-600 ring-1 ring-indigo-200/50` ressemble à un bouton (rounded, ring) mais est purement décoratif. Risque "looks-clickable, isn't" — anti-pattern §4.

---

## 4. Recommandations actionables

### Priorité immédiate (P0)

| # | Reco | Impact estimé |
|---|---|---|
| R0.1 | Étendre la zone tactile via `hitSlop` ou padding interne supplémentaire (minimum p-1.5 pour donner ~50px effectif). Ajouter test source-guard SG_NAV_FE_06 "no touch target < 44pt sur rail". | Mobile UX |
| R0.2 | Augmenter badge à `text-[10px]` minimum + utiliser `bg-red-600 text-white` (red-600 = #DC2626, contraste 4.5:1+ avec white). | A11y + lisibilité |
| R0.3 | Ajouter `motion-reduce:transition-none` sur `transition-all` — pattern Tailwind moderne. À répliquer sur tous les composants nav. | A11y critique |

### Priorité prochaine (P1)

| # | Reco | Impact |
|---|---|---|
| R1.1 | Wrapper logo : `<div role="img" aria-label="PROMEOS">P</div>` ou ajouter `<span className="sr-only">PROMEOS</span>`. | A11y SR |
| R1.2 | Label module : passer à `text-[11px]` ou `text-xs` (12px) + ajuster letter-spacing. Vérifier visuellement non-overflow. | Lisibilité |
| R1.3 | Séparateur : `h-px` (1px) au lieu de `h-[0.5px]`. Garde la discrétion + visibilité garantie. | Robustesse rendu |
| R1.4 | Étendre `MODULE_BADGE_KEY` avec `facturation: 'facturation'` + `achat: 'achat'` (utiliser les keys déjà exposées par `NavigationBadgesContext`). | Cohérence |

### Priorité backlog (P2)

| # | Reco | Impact |
|---|---|---|
| R2.1 | Renforcer glass surface : `bg-slate-100/70` au lieu de `bg-slate-50/60` pour différenciation visuelle. | Polish |
| R2.2 | Ajouter `active:scale-95` sur RailIcon button — micro-interaction press state. | Polish + feedback |
| R2.3 | PRO badge : ajouter `cursor-default` + envisager remplacer par icône `Zap` discrete pour éviter ambiguïté clickable. | Anti-confusion |

---

## 5. Validation cross-référencée doctrine PROMEOS

| Doctrine | Conformité |
|---|---|
| §6.2 anti-pattern "menu 4 niveaux" | ✅ — rail = 1 niveau (modules seuls), drill via panel |
| §6.2 anti-pattern "label Configuration" sur regroupement | ✅ — séparateur graphique sans label |
| §11 le bon endroit pour chaque brique | ✅ — 6 modules visibles couvrent les 6 piliers doctrine §4 (Cockpit, Conformité, Énergie, Patrimoine, Facturation Phase 1.D, Achat) |
| Multi-persona (§2 persona dominant Energy Manager) | ✅ — `default = energy_manager` (P0.5) |

---

## 6. STOP audit livrable 1/3

Audit NavRail terminé read-only. Aucune modification source.

→ **3 P0 actionables** (touch target, badge sub-lisible, reduced-motion) — fix recommandé en sprint UX dédié.
→ **4 P1 importantes** + **3 P2 cosmétiques** — backlog priorisé.

Suite : audit livrable 2/3 (NavPanel) → [02_navpanel_ux_audit_20260502.md](./02_navpanel_ux_audit_20260502.md).
