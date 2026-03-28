# Rapport Step 3 — TrajectorySection.jsx

**Branche** : `feat/cockpit-world-class`
**Commit** : `725dd29` — `feat(step3): TrajectorySection — courbe DT Recharts + barres sites kWh/m2`
**Date** : 2026-03-23
**Statut** : DONE — 17/17 tests verts, build OK

---

## Ce qui a ete livre

### Composant `TrajectorySection.jsx`
Graphique trajectoire Decret Tertiaire avec Recharts. Regle : **zero calcul metier comme KPI**.

**Props :**
```
TrajectorySection({ trajectoire, loading, sites })
```

### Graphique Recharts (ComposedChart)
| Serie | Couleur | Style |
|-------|---------|-------|
| Reel | `#378ADD` bleu | Area pleine, dots |
| Objectif DT | `#E24B4A` rouge | Line pointillee |
| Projection + actions | `#1D9E75` vert | Area pointillee |

- `ResponsiveContainer` height 220
- `ReferenceLine` annee courante avec label "Aujourd'hui"
- Tooltip formate selon le mode (MWh ou %)

### Toggle kWh / % reduction
- 2 boutons pills (pas le Toggle switch)
- Mode `kwh` : axe Y en MWh
- Mode `pct` : axe Y en % reduction par rapport a l'annee de reference

**Exception documentee** : la conversion kWh→% est une transformation de presentation locale (changement d'echelle pour le graphique), pas un KPI metier affiche. Documente en commentaire dans le code.

### Legende + Jalons
- Legende custom HTML (Reel / Objectif DT / Projection + actions)
- Reference : annee + surface m2 du portefeuille
- Jalons DT depuis `trajectoire.jalons` (2026 -25%, 2030 -40%, etc.)

### SiteBar
- Barres horizontales kWh/m2 avec ligne objectif
- Coloration amber si depassement, bleu si conforme
- Affiche uniquement si prop `sites` fourni

### Etats
- Loading : Skeleton
- Empty : EmptyState "Trajectoire non disponible"

---

## Fichiers crees

| Fichier | Type |
|---------|------|
| `frontend/src/pages/cockpit/TrajectorySection.jsx` | **NOUVEAU** — Composant graphique |
| `frontend/src/__tests__/TrajectorySection.test.js` | **NOUVEAU** — 17 tests |

---

## Tests (17/17)

### Source Guards (5)
- Recharts only (pas Chart.js)
- Aucun `reductionPct = (1 - ...)` comme reassignment KPI
- Aucun `* 0.0569`, `* 7500`, `* 3750`
- Exception toggle documentee

### Structure (7)
- `data-testid="trajectory-section"`
- ComposedChart + ResponsiveContainer
- 3 series (reel, objectif, projection)
- ReferenceLine annee courante
- Jalons depuis trajectoire.jalons
- Toggle kWh/pct
- SiteBar, Skeleton, EmptyState

### Legende et contexte (2)
- Legende custom (Reel, Objectif DT, Projection)
- Reference annee + surface

### Fix applique
- `useMemo` deplace avant les early returns (react-hooks/rules-of-hooks)

---

## Historique branche

```
feat/cockpit-world-class (pushed)
├── d40a4c8  fix(P0): cockpit credibility — unified compliance score + risk + trajectory
├── 0bcddd6  feat(step1): useCockpitData hook — parallel fetch, display-only
├── 8b506a4  feat(step2): CockpitHero — gauge conformite + KPIs + risque decompose
└── 725dd29  feat(step3): TrajectorySection — courbe DT Recharts + barres sites kWh/m2
```
