# UX Overlays — Audit, Règles & Hook Premium (V2)

> **But :** Référence pour tous les dropdowns, tooltips, popovers et modals du projet.
> Garantit qu'aucun overlay n'est clippé derrière du contenu, ne dérive au scroll, ni ne sort du viewport.

---

## 1. Inventaire des composants overlay

| Composant | Fichier | Portal | Z-index | scroll/resize | Statut |
|-----------|---------|--------|---------|---------------|--------|
| `UserMenu` dropdown | `layout/AppShell.jsx` | ✅ body | `z-[120]` | — | ✅ OK |
| `ScopeSwitcher` dropdown | `layout/ScopeSwitcher.jsx` | ✅ body | `z-[120]` | ✅ hook | ✅ Premium V2 |
| `NavPanel` (sidebar) | `layout/NavPanel.jsx` | ❌ non-portal | `z-30` | — | ✅ OK (sidebar fixe) |
| `CommandPalette` | `ui/CommandPalette.jsx` | ✅ body | `z-[200]` | — | ✅ OK |
| `Modal` | `ui/Modal.jsx` | ✅ body | `z-[200]` | — | ✅ OK |
| `Drawer` | `ui/Drawer.jsx` | ✅ body | `z-[200]` | — | ✅ OK |
| `TooltipPortal` | `ui/TooltipPortal.jsx` | ✅ body | `z-[120]` ✅ | — | ✅ **z-[9999]→z-[120] V2** |
| `InfoTip` | `ui/InfoTip.jsx` | ✅ body | `z-[120]` | — | ✅ OK |
| `InfoTooltip` (consumption) | `pages/consumption/InfoTooltip.jsx` | ✅ body | `z-[120]` | — | ✅ Fixed V1 |
| `SiteSearchDropdown` | `pages/consumption/StickyFilterBar.jsx` | ✅ body | `z-[120]` | ✅ hook | ✅ Premium V2 |
| Presets dropdown | `pages/consumption/StickyFilterBar.jsx` | ✅ body | `z-[120]` | ✅ hook | ✅ Premium V2 |
| `SitePicker` dropdown | `components/SitePicker.jsx` | ✅ body | `z-[120]` | ✅ hook | ✅ Premium V2 |
| `InsightBadge` detail | `pages/consumption/InsightsStrip.jsx` | ✅ body | `z-[120]` | — | ✅ Fixed V1 |

---

## 2. Carte Z-index canonique

```
z-[200]  Modals, Drawer, CommandPalette   (plein écran — portal body)
z-[120]  Dropdowns, tooltips, popovers   (portal body — TOUS les overlays)
z-40     Header sticky                    (AppShell — backdrop-blur-md)
z-30     Sidebar aside                    (sticky left column)
z-20     StickyFilterBar                  (sticky top — backdrop-blur)
z-auto   Contenu de page normal
```

> **Règle absolue :** aucun overlay à moins de `z-[120]`, rendu dans `document.body`.
> Ne jamais utiliser de valeurs ad-hoc (z-50, z-[9999], z-9999) — elles cassent la cohérence.

---

## 3. Les 3 règles du développeur

### Règle 1 — Tout overlay = Portal + `position: fixed`

Un overlay **doit** être rendu dans `document.body` via `createPortal`.
Sa position est calculée en `position: fixed` — jamais en `position: absolute`.

```jsx
// ✅ CORRECT — portal + fixed + hook
import useFloatingPortalPosition from '@/hooks/useFloatingPortalPosition';

const triggerRef = useRef(null);
const dropRef    = useRef(null);
const { style } = useFloatingPortalPosition({ isOpen, triggerRef, portalRef: dropRef });

return (
  <>
    <button ref={triggerRef} onClick={() => setOpen(true)}>Ouvrir</button>
    {isOpen && createPortal(
      <div ref={dropRef} className="fixed z-[120] w-64 bg-white ..." style={style}>
        Contenu overlay
      </div>,
      document.body,
    )}
  </>
);

// ❌ INTERDIT — absolute piégé dans stacking context ancêtre
<div className="relative backdrop-blur-md sticky top-0 z-20">
  <div className="absolute top-full z-50">Overlay invisible !</div>
</div>
```

### Règle 2 — Utiliser `useFloatingPortalPosition` (scroll/resize/zoom)

Le hook `src/hooks/useFloatingPortalPosition.js` fournit :
- Position initiale calculée via `getBoundingClientRect()` **avant** le premier paint (no-flicker)
- Repositionnement automatique sur `scroll`, `resize`, `visualViewport` (pinch-zoom mobile)
- Throttling via `requestAnimationFrame` (max 60 fps)
- Cleanup automatique à la fermeture

```js
const { style, updatePosition } = useFloatingPortalPosition({
  isOpen,           // boolean — attache/détache les listeners
  triggerRef,       // ref vers le bouton déclencheur
  portalRef,        // ref vers le div portalisé
  placement,        // 'bottom-start' | 'bottom-end' | 'top-start'  (default: 'bottom-start')
  offset,           // gap px entre trigger et overlay               (default: 8)
  clampPadding,     // distance min aux bords du viewport            (default: 8)
});
// style = { top, left } — spread sur le div portalisé
// updatePosition() — forcer un recalcul immédiat (ex: contenu dynamique)
```

### Règle 3 — Outside-click doit vérifier les deux refs (cross-portal)

```jsx
useEffect(() => {
  if (!open) return;
  function handler(e) {
    if (triggerRef.current?.contains(e.target)) return;
    if (dropRef.current?.contains(e.target)) return;
    setOpen(false);
  }
  function onEsc(e) { if (e.key === 'Escape') setOpen(false); }
  document.addEventListener('mousedown', handler);
  document.addEventListener('keydown', onEsc);
  return () => {
    document.removeEventListener('mousedown', handler);
    document.removeEventListener('keydown', onEsc);
  };
}, [open]);
```

---

## 4. Pièges — Stacking contexts créés automatiquement

Ces propriétés CSS créent un nouveau stacking context — les `z-index` enfants ne peuvent **pas** dépasser le z-index du conteneur :

| Propriété CSS | Stacking context |
|--------------|-----------------|
| `position: sticky/fixed/relative/absolute` + `z-index ≠ auto` | ✅ Oui |
| `backdrop-filter: blur(...)` | ✅ Oui (tous navigateurs modernes) |
| `opacity < 1` | ✅ Oui |
| `transform: ...` | ✅ Oui |
| `filter: ...` | ✅ Oui |
| `will-change: transform/opacity` | ✅ Oui |
| `isolation: isolate` | ✅ Oui |

**Corollaire :** `StickyFilterBar` (`sticky + z-20 + backdrop-blur`) piège tout absolu enfant.
La seule issue : portal (`createPortal` + `position: fixed`).

---

## 5. Diagnostic rapide

Si un overlay se retrouve derrière du contenu :

1. Inspecter l'ancêtre avec `position: sticky/fixed` ou `backdrop-filter`
2. Vérifier si cet ancêtre a un `z-index` explicite → stacking context confirmé
3. Migrer l'overlay vers `createPortal` + `position: fixed`
4. Brancher `useFloatingPortalPosition` pour scroll/resize/zoom
5. Assigner `z-[120]` (overlay) ou `z-[200]` (modal)

---

## 6. data-testids stables (Playwright)

| Élément | `data-testid` |
|---------|--------------|
| ScopeSwitcher trigger | `scope-switcher-trigger` |
| ScopeSwitcher panel | `scope-switcher-panel` |
| StickyFilterBar + site trigger | `sticky-sitesearch-trigger` |
| StickyFilterBar + site panel | `sticky-sitesearch-panel` |
| StickyFilterBar presets trigger | `sticky-presets-trigger` |
| StickyFilterBar presets panel | `sticky-presets-panel` |
| InfoTip icon button | `infotip` |

---

*Dernière mise à jour : V2 — hook premium scroll/resize/zoom + data-testids (Sprint WOW)*
