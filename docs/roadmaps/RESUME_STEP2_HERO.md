# Rapport Step 2 — CockpitHero.jsx

**Branche** : `feat/cockpit-world-class`
**Commit** : `8b506a4` — `feat(step2): CockpitHero — gauge conformite + KPIs + risque decompose`
**Date** : 2026-03-23
**Statut** : DONE — 21/21 tests verts, 0 regression, build OK

---

## Ce qui a ete livre

### Composant `CockpitHero.jsx`
Hero block 3 colonnes pour le cockpit executif. Regle : **display-only, zero calcul metier**.

**Props :**
```
CockpitHero({ kpis, trajectoire, actions, billing, loading, error, orgNom, onEvidence })
```

### Colonne gauche — Gauge conformite
- Demi-cercle SVG (r=45, strokeWidth=10)
- Score depuis `kpis.conformiteScore` (0-100, RegAssessment)
- Couleur semantique : vert (>=80), amber (>=60), rouge (>=40), critique (<40)
- Label : Excellent / Satisfaisant / A risque / Critique
- Clic → `navigate('/conformite')`
- Bouton HelpCircle → `onEvidence('conformite')` (callback parent)
- Fraicheur : date + "Source : RegAssessment"

### Colonne centrale — 3 KPI cards
| KPI | Source | Statut |
|-----|--------|--------|
| Reduction DT cumulee | `trajectoire.reductionPctActuelle` | Actif |
| Intensite energetique | Non disponible dans hook | Placeholder '—' |
| CO2 evite (N vs N-1) | Non disponible dans hook | Placeholder '—' |

**Point important** : `reductionPctActuelle` est dans `trajectoire` (pas dans `kpis`). Le composant accepte `trajectoire` en prop.

### Colonne droite — Risque decompose
- Fond amber (KPI_ACCENTS.risque)
- Total : `fmtEur(kpis.risqueTotal)`
- 3 lignes breakdown : reglementaire / billing / contrat
- CTA "Voir le plan de rattrapage" → `navigate('/actions')`

### Etats
- Loading : Skeleton layout 3 colonnes
- Error : ErrorState "Donnees cockpit indisponibles"

### Pattern EvidenceDrawer
`onEvidence` est un callback — le composant ne gere pas son propre EvidenceDrawer. Le parent (`Cockpit.jsx`, step 6) le controle via son state `evidenceOpen` existant. Zero conflit d'etat.

---

## Fichiers crees

| Fichier | Type |
|---------|------|
| `frontend/src/pages/cockpit/CockpitHero.jsx` | **NOUVEAU** — Composant hero |
| `frontend/src/__tests__/CockpitHero.test.js` | **NOUVEAU** — 21 tests |

---

## Tests (21/21)

### Source Guards (5)
- Aucun `/ total * 100`, `1 - x/y * 100`, `* 0.0569`, `* 7500`, `* 3750`

### Design System (4)
- Import `fmtEur`, pas de formatage EUR manuel
- Import `KPI_ACCENTS` depuis colorTokens
- Import `Skeleton` et `ErrorState`

### Structure (9)
- 5 data-testid presents (gauge, 3 KPIs, risque)
- Navigate `/conformite` et `/actions`
- `onEvidence` callback (pas d'import EvidenceDrawer)
- Fraicheur `conformiteComputedAt`
- `trajectoire?.reductionPctActuelle`

### Accessibilite (2)
- `aria-label` sur boutons interactifs
- `focus-visible:ring` sur elements interactifs

---

## Definition of Done

- [x] `npx vitest run src/__tests__/CockpitHero.test.js` — 21/21 verts
- [x] `npm run build` — exit 0
- [x] Gauge SVG visible avec score depuis `kpis.conformiteScore`
- [x] Clic gauge → navigate('/conformite')
- [x] HelpCircle → `onEvidence('conformite')` callback
- [x] `conformiteComputedAt` affiche en sous-texte
- [x] Risque decompose visible avec `fmtEur` pour chaque ligne
- [x] Skeleton affiche si `loading=true`
- [x] ErrorState si `error` non null
- [x] Aucun calcul dans le fichier
- [x] Commit propre + push sur `feat/cockpit-world-class`

## Historique branche
```
feat/cockpit-world-class (pushed)
├── d40a4c8  fix(P0): cockpit credibility — unified compliance score + risk + trajectory
├── 0bcddd6  feat(step1): useCockpitData hook — parallel fetch, display-only
└── 8b506a4  feat(step2): CockpitHero — gauge conformite + KPIs + risque decompose
```
