# Rapport Step 4 — ActionsImpact.jsx

**Branche** : `feat/cockpit-world-class`
**Commit** : `448a49b` — `feat(step4): ActionsImpact — actions P0/P1 + barres trajectoire`
**Date** : 2026-03-23
**Statut** : DONE — 16/16 tests verts, build OK

---

## Ce qui a ete livre

### Composant `ActionsImpact.jsx`
Liste actions prioritaires pour le cockpit executif. Regle : **display-only, zero calcul metier**.

**Props** : `ActionsImpact({ actions, loading })`

### Fetch interne
- `getActionsList({ status: 'open,in_progress', limit: 6 })` — deja dans `api/actions.js`
- Gestion loading/error/empty interne au composant

### Champs API reels utilises

| Champ API | Usage |
|-----------|-------|
| `title` | Titre affiche |
| `priority` (int 1-5) | PriorityBadge (1-2→P0, 3→P1, 4-5→P2) |
| `source_type` | SourceTag colore |
| `source_label` | Fallback FR |
| `estimated_gain_eur` | `fmtEur()` a droite |
| `due_date` | Echeance formatee FR |
| `source_deeplink` | Navigation au clic |

### Composants internes
- **PriorityBadge** : cercle colore P0/P1/P2 (rouge/amber/bleu)
- **SourceTag** : module d'origine (DT, Billing, Conso, Monitoring, Achat, Insight, Levier, Manuel)
- **ActionRow** : titre + tags + gain estime

### ImpactBar
Non affichee dans cette etape — les champs `impact_kwh_an` et `trajectoire_pts` sont absents du modele backend. Ils seront ajoutes dans un sprint ulterieur.

### Etats
- Loading : skeleton 4 lignes avec pulse
- Error : "Impossible de charger les actions"
- Empty : "Aucune action prioritaire en cours"
- Footer : potentiel total + CTA "Voir toutes les actions" → `/actions`

---

## Fichiers crees

| Fichier | Type |
|---------|------|
| `frontend/src/pages/cockpit/ActionsImpact.jsx` | **NOUVEAU** — Composant actions |
| `frontend/src/__tests__/ActionsImpact.test.js` | **NOUVEAU** — 16 tests |

---

## Tests (16/16)

### Source Guards (4)
- Aucun `* 0.0569`, `* 7500`, `* 3750`, `1 - x/y * 100`
- Pas de reassignment calcule sur savings/gain

### Design System (3)
- Import fmtEur, pas de formatage EUR manuel
- Navigate /actions

### Structure (9)
- data-testid actions-impact + action-row
- PriorityBadge + SourceTag
- Import getActionsList
- Champs API reels (title, priority, source_type, estimated_gain_eur)
- Skeleton + message empty
- focus-visible rings

---

## Historique branche

```
feat/cockpit-world-class (pushed)
├── d40a4c8  fix(P0): cockpit credibility — unified compliance score + risk + trajectory
├── 0bcddd6  feat(step1): useCockpitData hook — parallel fetch, display-only
├── 8b506a4  feat(step2): CockpitHero — gauge conformite + KPIs + risque decompose
├── 725dd29  feat(step3): TrajectorySection — courbe DT Recharts + barres sites kWh/m2
└── 448a49b  feat(step4): ActionsImpact — actions P0/P1 + barres trajectoire
```
