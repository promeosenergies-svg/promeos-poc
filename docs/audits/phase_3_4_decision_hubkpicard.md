# Phase 3.4 — Décision GO/NO-GO extraction `HubKpiCard`

> **À décider** : extraire `HubKpiCard` de `CockpitJour.jsx` (inline actuel) vers `frontend/src/components/grammar/hub/HubKpiCard.jsx` (primitif générique) **avant** Phase 3.5.

---

## Le problème exact

Actuellement, dans `CockpitJour.jsx` Phase 3.4, le composant qui rend chaque KPI card est **inline** dans le fichier de page (KpiTriptychCard local). Trois conséquences :

1. **Si on scale L11 sur 5 hubs sans extraction** : chaque page (`Energie.jsx`, `Conformite.jsx`, etc.) recopiera son propre `HubKpiCard` inline → **drift visuel garanti** dès le 2e hub.
2. **Source guards CI inutiles** : le guard `forbidden-components` ne peut pas bloquer un composant inline ; il ne détecte que les `<MyForbidden>` importés.
3. **Tests visual regression inefficaces** : si chaque hub a son rendu KPI, on doit maintenir 5 snapshots au lieu de 1.

---

## Les 3 questions GO/NO-GO

### Q1 — Le rendu actuel est-il déjà fidèle à la spec `<KPISol>` du Design System ?

Vérifier (sur `KpiTriptychCard` inline dans `CockpitJour.jsx`) :

- [ ] Icône circulaire 42px avec fond `--bullet-bg`
- [ ] Eyebrow mono 11px uppercase tracking-wider `--ink-tertiary`
- [ ] Label Inter 13.5px `--ink`
- [ ] Valeur Newsreader 38px tabular-nums `--ink` letter-spacing tighter
- [ ] Unité Inter 14px `--ink-tertiary`
- [ ] Delta mono 13.5px sentiment-aware (`--crit`, `--pos`, `--ink`)
- [ ] Tooltip aide (KPI 3 obligatoire)
- [ ] Foot SCM (Source · Confiance) mono 10px tracking-wide
- [ ] Padding 18-20px, border `--hairline` 1px, radius `--radius-xl` 12px
- [ ] Background `--surface` (blanc)
- [ ] States loading / empty / error / partial implémentés

### Q2 — Quels props sont génériques vs spécifiques à `/cockpit/jour` ?

Audit du JSX inline actuel :

| Prop | Générique L11 | Spécifique cockpit/jour | Décision |
|---|---|---|---|
| `id` | ✓ | | dans API |
| `icon` | ✓ | | dans API |
| `eyebrow` | ✓ | | dans API |
| `label` | ✓ | | dans API |
| `value` | ✓ | | dans API |
| `unit` | ✓ | | dans API |
| `delta` (value, direction, label, sentiment) | ✓ | | dans API |
| `helpTooltip` | ✓ | | dans API |
| `source`, `confidence` | ✓ | | dans API |
| `loading`, `partial`, `error` | ✓ | | runtime |

**Verdict attendu** : 100 % générique. Aucun prop spécifique cockpit/jour → l'extraction est légitime sans aucune perte.

### Q3 — Quel est le coût de l'extraction maintenant vs après Phase 3.5 ?

| Moment | Coût | Risque |
|---|---|---|
| **Maintenant** (avant Phase 3.5) | 1-3h | Faible — 1 seul consumer à updater |
| **Pendant Phase 3.5** | 4-6h | Moyen — risque régression sur hub livré |
| **Après Phase 3.5** | 8-12h | **Élevé** — drift visuel déjà installé |

**Verdict mathématique** : extraire maintenant est 3 à 12 fois moins cher qu'après.

---

## Plan d'extraction (si GO)

```text
P0 — Extraction mécanique (1h)
  1. Créer frontend/src/components/grammar/hub/HubKpiCard.jsx
     - Copier le JSX inline + déplacer les styles
     - Importer tokens depuis ui/sol/tokens.css (--sol-*)
     - Ajouter data-component="HubKpiCard"
  2. Remplacer dans CockpitJour.jsx : <HubKpiCard {...kpi} />
  3. Tests Vitest : import depuis nouveau chemin

P1 — Storybook (1-2h)  [SKIP si pas de Storybook dans le repo]
  4. Créer HubKpiCard.stories.jsx avec 8 stories

P2 — Tests dédiés (1h)
  5. HubKpiCard.test.jsx (Vitest)

P3 — Source guards (30min)
  6. Mettre à jour cockpit_jour_l11_fe_source_guards.test.js
```

**Total estimé** : 3-4h pour une extraction propre et testée.

---

## Critères de validation post-extraction

- [ ] `frontend/src/components/grammar/hub/HubKpiCard.jsx` existe
- [ ] `CockpitJour.jsx` n'a plus de JSX KPI inline
- [ ] CockpitJour.jsx perd ~80-120 lignes
- [ ] HubKpiCard.test.jsx couvre 6+ cas
- [ ] Vitest 4 680 → 4 686+ (au moins +6 tests dédiés)
- [ ] Aucune régression visuelle Playwright
- [ ] Source guard `kpi-card-not-inline` ajouté et vert
- [ ] ADR-021 mis à jour avec section "HubKpiCard extracted"

---

## Décision finale

**Recommandation forte : GO sur l'extraction avant Phase 3.5**

Raisons :

1. Coût 3-4h maintenant vs 8-12h après → **ROI immédiat ×3**
2. Risque architectural majeur si on skip : 5 hubs avec 5 implémentations divergentes
3. Phase 3.4 a déjà fait le travail conceptuel
4. Source guard CI peut bloquer toute future duplication
