# PROMEOS — Color Life System

## Principes

- **80/15/5** : 80% surfaces neutres, 15% teintes module, 5% accents signal
- **Pas de fond plein** : toujours `bg-{color}-50/40` (opacite reduite)
- **Tint = identite**, Severity = signal — jamais confondus

---

## Palettes

### Module Tints (`TINT_PALETTE` — NavRegistry.js)

| Module     | Tint    | Usage                                      |
|------------|---------|---------------------------------------------|
| cockpit    | blue    | Dashboard, alertes, vue d'ensemble          |
| operations | emerald | Conformite, plans d'actions                 |
| analyse    | indigo  | Consommations, performance, monitoring      |
| marche     | amber   | Factures, achats energie                    |
| admin      | slate   | Import, IAM, patrimoine                     |

Chaque tint a **15 tokens semantiques** :
`headerBand`, `panelHeader`, `softBg`, `hoverBg`, `activeBg`, `activeText`, `activeBorder`,
`railActiveBg`, `railActiveRing`, `railActiveText`, `dot`, `icon`, `pillBg`, `pillText`, `pillRing`

### Severity Tints (`SEVERITY_TINT` — colorTokens.js)

| Level    | Couleur | Label FR  | Usage                          |
|----------|---------|-----------|--------------------------------|
| critical | red     | Critique  | Alertes critiques              |
| high     | amber   | Eleve     | Alertes hautes                 |
| warn     | amber   | Attention | Avertissements                 |
| medium   | blue    | Moyen     | Informations moyennes          |
| info     | blue    | Info      | Informations                   |
| low      | gray    | Faible    | Faible priorite                |
| neutral  | gray    | -         | Etat neutre                    |

Chaque severity a **5 tokens** : `dot`, `chipBg`, `chipText`, `chipBorder`, `label`

---

## Disambiguation : Amber

Amber apparait dans les deux systemes :

| Contexte          | Recette                                             |
|-------------------|-----------------------------------------------------|
| Module (marche)   | `bg-amber-50/40` (wash subtil) + `ring-amber-200/60` |
| Severity (high)   | `bg-amber-50` + `border-amber-200` (chip signal)    |

La difference est dans la **recette** : le module utilise des opacites reduites et un ring, la severity utilise un border plein et un chip compact.

---

## API Helper (`tint` — colorTokens.js)

```javascript
import { tint } from '../ui/colorTokens';

// Module
tint.module('cockpit').navActive()   // "bg-blue-50/60 text-blue-700 border-blue-500"
tint.module('marche').pill()         // "bg-amber-50 text-amber-700 ring-1 ring-amber-200/60"
tint.module('analyse').icon()        // "text-indigo-500"
tint.module('cockpit').headerBand()  // "from-blue-50/60 to-transparent"
tint.module('cockpit').raw()         // full TINT_PALETTE entry

// Severity
tint.severity('critical').badge()    // "bg-red-50 text-red-700 border border-red-200"
tint.severity('critical').dot()      // "bg-red-500"
tint.severity('critical').label()    // "Critique"
```

---

## Dos / Don'ts

**DO :**
- Utiliser `tint.module(key)` pour tout accent lie a un module
- Utiliser `tint.severity(level)` pour les badges et dots d'alerte
- Utiliser `SEVERITY_TINT` dans les composants de diagnostic/alertes
- Garder les series de graphique en couleurs neutres (palette par defaut)

**DON'T :**
- Ne jamais utiliser un chip severity pour identifier un module
- Ne jamais utiliser un wash module pour signaler une alerte
- Ne pas hardcoder `bg-blue-600` dans les composants — passer par `tintColor` prop
- Ne pas creer de nouvelle map de couleurs locale — utiliser `SEVERITY_TINT` ou `KPI_ACCENTS`

---

## Accessibilite (A11y)

- **Focus visible** : `focus-visible:ring-2 focus-visible:ring-{color}-500` sur tous les interactifs
- **Contraste** : texte `{color}-700` sur fond `{color}-50` = ratio > 4.5:1
- **Dots** : `{color}-400` ou `{color}-500` = visibles sur fond blanc

---

## Fichiers cles

| Fichier | Contenu |
|---------|---------|
| `layout/NavRegistry.js` | `TINT_PALETTE`, `NAV_MODULES`, `MODULE_TINTS`, `getModuleTint()` |
| `ui/colorTokens.js` | `SEVERITY_TINT`, `KPI_ACCENTS`, `ACCENT_BAR`, `HERO_ACCENTS`, `tint` helper |
| `ui/PageShell.jsx` | Prop `tintColor` pour icone module |
| `ui/Tabs.jsx` | Prop `tint` pour tab active |
| `ui/Badge.jsx` | Severity badges (ok/warn/crit/info/neutral) |
| `ui/MetricCard.jsx` | KPI accent bar + icon pill |
