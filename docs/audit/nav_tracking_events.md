# Events tracker navigation — Sprint 1 Vague A phase A10

> **Date** : 2026-04-22 · **Scope** : instrumentation Vague 1 deep-links
> nav pour mesurer la fenêtre Test milieu Sprint 1 → 2.

## Inventaire events

| Event                              | Quand déclenché                                                           | Payload                                                |
|------------------------------------|---------------------------------------------------------------------------|--------------------------------------------------------|
| `nav_panel_opened`                 | Mount de `SolPanel` ou changement de module/route                         | `{ module, route, is_expert }`                         |
| `nav_deep_link_click`              | Click sur un item NAV_SECTIONS ou un deep-link `Raccourcis` dans SolPanel | `{ href, label, module, section_key, is_deep_link }`   |
| `anomaly_filter_applied`           | Filtre `fw` appliqué sur `/anomalies` (manuel ou deep-link)               | `{ framework, source: 'manual' \| 'deep_link' }`       |
| `aper_filter_applied`              | Filtre `filter` (parking/toiture) appliqué sur `/conformite/aper`         | `{ filter_type, source: 'deep_link' }` (V1 deep uniquement) |
| `renouvellements_horizon_selected` | Horizon 90/180/365 changé sur `/renouvellements` (manuel ou deep-link)    | `{ horizon, source: 'manual' \| 'deep_link' }`         |
| `route_change` *(existant)*        | Navigation pilotée par `trackRouteChange` dans SolAppShell                | `{ to: pathname }`                                     |

## Différenciation `source` : `deep_link` vs `manual`

- **`deep_link`** : l'URL arrive déjà avec le paramètre (ex.
  `/anomalies?fw=BACS` depuis un click panel). Détecté au **mount** via
  `useRef(false)` garde (fire-once).
- **`manual`** : l'utilisateur clique sur un select/bouton in-page.
  Wrappé autour de `setFilters`/`setHorizon`.

Cette distinction est **cruciale** pour le bilan Vague 1 → 2 : si les
clicks panel (`deep_link`) restent < 5 % vs clicks manuels, la valeur des
raccourcis est faible et la Vague 2 doit être re-calibrée.

## Snippet console pour lire les events en fin de fenêtre test

```javascript
const events = JSON.parse(localStorage.getItem('promeos_tracker') || '[]');

// Vues du panel
const opens = events.filter((e) => e.event === 'nav_panel_opened');

// Clicks sur un deep-link Raccourcis (is_deep_link: true)
const deepLinkClicks = events.filter(
  (e) => e.event === 'nav_deep_link_click' && e.is_deep_link
);

// Filters déclenchés — split par source
const manualFilters = events.filter(
  (e) => e.event.endsWith('_applied') && e.source === 'manual'
);
const deepLinkFilters = events.filter(
  (e) => e.event.endsWith('_applied') && e.source === 'deep_link'
);

const ratio = opens.length > 0
  ? ((deepLinkClicks.length / opens.length) * 100).toFixed(1)
  : 'n/a';

console.log(`Panels ouverts       : ${opens.length}`);
console.log(`Clicks deep-link     : ${deepLinkClicks.length}`);
console.log(`Ratio clicks/panels  : ${ratio}%`);
console.log(`Filters manuels      : ${manualFilters.length}`);
console.log(`Filters via deep-link: ${deepLinkFilters.length}`);
console.log(`Split deep/manual    : ${manualFilters.length} vs ${deepLinkFilters.length}`);
```

## Stockage

- LocalStorage ring buffer (200 events max, FIFO via
  `services/tracker.js`).
- Pas d'envoi réseau — POC-only. Pour un pilote réel, ajouter un
  flush périodique vers un backend analytics dédié.

## Ajouts post-Sprint 1 Vague A envisageables

- Tracker `nav_panel_collapsed` si on restaure une feature « réduire
  panel » (pas dans le scope Sprint 1).
- Tracker `aper_filter_applied` avec `source: 'manual'` quand une UX
  manuelle pour le filtre est ajoutée (V1 AperSol n'a pas de bouton
  filtre manuel — les week-cards drillent vers `/sites/:id`).
