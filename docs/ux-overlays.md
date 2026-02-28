# UX Overlays — Audit & Règles (V1)

> **But :** Référence pour tous les dropdowns, tooltips, popovers et modals du projet.
> Garantit qu'aucun overlay ne se retrouve clippé derrière un contenu voisin.

---

## 1. Inventaire des composants overlay

| Composant | Fichier | Portal | Z-index | Risque | Statut |
|-----------|---------|--------|---------|--------|--------|
| `UserMenu` dropdown | `layout/AppShell.jsx` | ✅ `document.body` | `z-[120]` | — | ✅ OK |
| `ScopeSwitcher` dropdown | `layout/ScopeSwitcher.jsx` | ✅ `document.body` | `z-[120]` | — | ✅ OK |
| `NavPanel` (sidebar) | `layout/NavPanel.jsx` | ❌ non-portal | `z-30` | Faible — toujours à gauche | ✅ OK |
| `CommandPalette` | `ui/CommandPalette.jsx` | ✅ (overlay plein écran) | `z-[200]` | — | ✅ OK |
| `Modal` | `ui/Modal.jsx` | ✅ `document.body` | `z-[200]` | — | ✅ OK |
| `Drawer` | `ui/Drawer.jsx` | ✅ `document.body` | `z-[200]` | — | ✅ OK |
| `TooltipPortal` | `ui/TooltipPortal.jsx` | ✅ `document.body` | `z-[9999]` | — | ✅ OK |
| `InfoTip` | `ui/InfoTip.jsx` | ✅ `document.body` | `z-[120]` | — | ✅ OK |
| `InfoTooltip` (consumption) | `pages/consumption/InfoTooltip.jsx` | ✅ `document.body` | `z-[120]` | Était `absolute` dans sticky+blur | ✅ **Fixed V1** |
| `SiteSearchDropdown` | `pages/consumption/StickyFilterBar.jsx` | ✅ `document.body` | `z-[120]` | Était `absolute z-40` dans sticky+blur | ✅ **Fixed V1** |
| Presets dropdown | `pages/consumption/StickyFilterBar.jsx` | ✅ `document.body` | `z-[120]` | Était `absolute z-30` dans sticky+blur | ✅ **Fixed V1** |
| `SitePicker` dropdown | `components/SitePicker.jsx` | ✅ `document.body` | `z-[120]` | Était `absolute z-50` | ✅ **Fixed V1** |
| `InsightBadge` detail | `pages/consumption/InsightsStrip.jsx` | ✅ `document.body` | `z-[120]` | Était `absolute z-30` | ✅ **Fixed V1** |

---

## 2. Carte des couches Z-index

```
z-[200]  Modals, Drawer, CommandPalette  (pleins écrans — portal body)
z-[120]  Dropdowns, tooltips, popovers  (portal body — tous overlays)
z-40     Header sticky                   (AppShell — backdrop-blur-md)
z-30     Sidebar aside                   (sticky left column)
z-20     StickyFilterBar                 (sticky top — backdrop-blur)
z-auto   Contenu de page normal
```

> **Règle absolue :** aucun overlay ne peut exister à moins de `z-[120]` rendu dans `document.body`.
> Un overlay dans un élément `z-20` sera toujours caché derrière un élément frère `z-21`.

---

## 3. Les 3 règles du développeur

### Règle 1 — Tout overlay = Portal + `position: fixed`

Un overlay (dropdown, tooltip, popover) **doit** être rendu dans `document.body` via `createPortal`.
Sa position est calculée depuis `element.getBoundingClientRect()` et appliquée en `style={{ top, left }}` avec `position: fixed`.

```jsx
// ✅ Correct
const [coords, setCoords] = useState(null);
const triggerRef = useRef(null);

const open = () => {
  const r = triggerRef.current.getBoundingClientRect();
  setCoords({ top: r.bottom + 4, left: r.left });
};

return (
  <>
    <button ref={triggerRef} onClick={open}>Ouvrir</button>
    {visible && coords && createPortal(
      <div className="fixed z-[120]" style={{ top: coords.top, left: coords.left }}>
        Contenu overlay
      </div>,
      document.body,
    )}
  </>
);

// ❌ Interdit — absolute piégé dans un stacking context ancêtre
<div className="relative">
  <button>Trigger</button>
  <div className="absolute top-full z-50">Overlay clippé !</div>
</div>
```

### Règle 2 — Outside-click doit vérifier les deux refs

Quand le dropdown est dans un portal, les clics sur le dropdown ne tombent **pas** dans le `triggerRef`. L'handler `mousedown` doit vérifier les deux :

```jsx
useEffect(() => {
  function handler(e) {
    if (
      triggerRef.current && !triggerRef.current.contains(e.target) &&
      dropRef.current   && !dropRef.current.contains(e.target)
    ) {
      setOpen(false);
    }
  }
  document.addEventListener('mousedown', handler);
  return () => document.removeEventListener('mousedown', handler);
}, []);
```

### Règle 3 — Contextes de stacking qui piègent les enfants

Ces propriétés CSS créent un nouveau stacking context — les `z-index` des enfants ne peuvent **pas** dépasser le z-index du conteneur :

| Propriété CSS | Crée un stacking context |
|--------------|--------------------------|
| `position: sticky/fixed/absolute/relative` + `z-index ≠ auto` | ✅ Oui |
| `backdrop-filter: blur(...)` | ✅ Oui (tous navigateurs modernes) |
| `opacity < 1` | ✅ Oui |
| `transform` | ✅ Oui |
| `filter` | ✅ Oui |
| `will-change: transform/opacity` | ✅ Oui |

**Corollaire :** Toute combinaison `sticky + z-XX + backdrop-blur` (comme `StickyFilterBar`) piège ses enfants absolus. La seule issue est le portal.

---

## 4. Diagnostic rapide

Si un overlay se retrouve derrière du contenu :

1. Inspecter l'ancêtre le plus proche avec `position: sticky/fixed` ou `backdrop-filter`
2. Vérifier si cet ancêtre a un `z-index` explicite → stacking context confirmé
3. Migrer l'overlay vers un portal (`createPortal` + `position: fixed`)
4. Assigner `z-[120]` au overlay (ou `z-[200]` pour les modals)

---

*Dernière mise à jour : V1 — audit complet overlays (Sprint WOW)*
