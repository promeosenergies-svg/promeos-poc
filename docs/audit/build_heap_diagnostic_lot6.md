# Diagnostic dette heap 6 GB — Lot 6 Phase 4 pré-flight 1

> **Date** : 2026-04-19
> **Contexte** : depuis Phase 2 Lot 6 (KBExplorerSol, commit `5af025c7`), les builds `npx vite build` échouent avec `fatal error: out of memory` si le heap Node n'est pas bumped à ≥ 6 GB via `NODE_OPTIONS="--max-old-space-size=6144"`.

## Mesures

**Build avec heap 6 GB** :
```
time NODE_OPTIONS="--max-old-space-size=6144" npx vite build
→ ✓ built in 25.11s (second run) · 40-41s (premier run à froid)
```

**Top 10 chunks (post-build) :**

| Taille | Fichier |
|---|---|
| 1 023 222 B | `maplibre-BXynEkEX.js` |
| 429 529 B | `xlsx-D_0l8YDs.js` |
| 403 664 B | `index-CEREO_EJ.js` |
| 316 482 B | `CartesianChart-vq654mNp.js` |
| 179 220 B | `Site360-czwhADcS.js` |
| 167 440 B | `ConsumptionExplorerPage-C-DI9OMZ.js` |
| 152 434 B | `PurchasePage-0akW-AwU.js` |
| 140 699 B | `Patrimoine-mryulmjj.js` |
| 110 115 B | `Cockpit-DSHranNo.js` |
| 101 982 B | `ConformitePage-B92wZreS.js` |

## Hypothèse initiale (infirmée)

Hypothèse centrale du prompt Phase 4 pré-flight : **circular barrel export** via `sol/index.js` ou autres `index.js` de module.

**Test `grep -rn "^export \*" src/ui/sol/ src/pages/`** : **aucun résultat**. Zéro `export *` dans les barrels Sol + pages. Les index.js Sol utilisent des `export { default as Xxx } from './Xxx'` nommés, structure saine.

**Test `grep "from './index'"`** : aucun import circular détecté.

→ **Hypothèse circular barrel INFIRMÉE**.

## Cause probable réelle

Gros composants legacy non-refondus qui sont tous chargés par esbuild en mémoire simultanément pendant la passe production :

| LOC | Fichier |
|---|---|
| 3 134 | `pages/MonitoringPage.jsx` |
| 2 284 | `pages/Patrimoine.jsx` |
| 2 200 | `pages/Site360.jsx` |
| 2 148 | `pages/PurchasePage.jsx` |
| 1 823 | `pages/PurchaseAssistantPage.jsx` |
| 1 823 | `components/purchase/PurchaseAssistantWizard.jsx` |
| 1 579 | `pages/ActionsPage.jsx` |
| 1 327 | `components/ActionDetailDrawer.jsx` |

Somme = ~16 000 lignes de composants React lourds non encore passés par la refonte Sol. Combiné aux dépendances lourdes (recharts, maplibre-gl, xlsx, leaflet), le heap Node saute à > 4 GB pendant la passe de bundling + minification esbuild.

## Décision (règle 1 surveillance user · 2026-04-19)

> « Si le build heap révèle un barrel export circular (hypothèse centrale), documenter mais ne pas fixer pendant Phase 4 — risque de scope creep. »

L'hypothèse circular est infirmée. La cause réelle (gros composants legacy) **dépasse le scope Lot 6 Explorer/KB**.

**Décision** : NOTE le problème dans ce doc, skip fix Phase 4. Workaround opérationnel = `NODE_OPTIONS="--max-old-space-size=6144"` sur tous les build Lot 6+.

## Recommandation Phase 5 ou Lot 5 Admin

Les refontes futures à prioriser pour réduire le heap :

1. **Lot 5 Admin + MonitoringPage refonte** (3 134 LOC → thin loader + MonitoringSol déjà Lot 1 partiel) → gain estimé 2-3 MB d'AST
2. **Lot 7 Patrimoine/Site360 refactor** (2 284 + 2 200 = 4 484 LOC) → déjà partiellement refondu (Site360Sol Phase 2 Lot 3) mais le legacy Site360.jsx reste 2 200 LOC en dead code
3. **Purchase/Actions** : PurchasePage 2 148 + PurchaseAssistantWizard 1 823 + ActionsPage 1 579 = 5 550 LOC, hors roadmap Sol, à traiter séparément

**Action immédiate** : aucune.
**Action court terme** : ajouter `NODE_OPTIONS` au script `build` de `package.json` pour éviter recommencer à chaque clean install.
