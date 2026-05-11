# ADR-021 — Hub Page Grammar L11 (Sprint Grammaire v1.2 / Phase 3.4)

**Statut** : Accepté
**Date** : 2026-05-10 (initial) · 2026-05-11 (validé Phase F clôturée)
**Sprint** : Grammaire v1.2 / Phase 3.4 + HARD STOP Phase F (V2 « juste milieu premium »)
**Personnes impliquées** : Amine (founder), Claude architect-helios + implementer
**Branche** : `claude/refonte-sol2`
**Doctrine** : `docs/vision/promeos_sol_doctrine.md` §12 (Loi L11) + addendum
`sol_v1_1_addendum_hub_page.md`
**Extraction trail Phase F** : commits `9c8851b3` (F.0 décision) → `68dd1547`
(F.1 HubKpiCard) → `29666297` (F.2 ChartFrame variants) → `c466ebbf` (F.3
HubSkeleton + HubError) → `ff2b3a4d` (F.4 backend is_demo) → `a4ad525d`
(F.5 AutoTerm) → `c7b51567` (F.6 typo + F.5.1 doublon BACS) → `81db5384`
(F.7 source-guards CI). Audit 7 angles validé 18.7/24 (78 %).

## Contexte

Le bilan Sprint Grammaire v1.1 (Phase 3.0 → 3.3.fix) a montré qu'au-delà des
primitifs locaux (`SolHeroCalm`, `SolBriefingHead`, `DecisionEvidenceCard`), les
6 hubs PROMEOS — **Briefing du jour, Énergie, Conformité, Factures, Achat,
Patrimoine** — partageaient une géométrie identique : hero signature B2B,
triptyque KPI, paire chart question/réponse, top priorités narrées, footer SCM.

L'addendum doctrinal **L11 Hub Page** (ingéré 09/05/2026 dans
`promeos_sol_doctrine.md` §12) formalise cette géométrie en 5 sous-lois
(L11.1 → L11.5) et impose leur application sur les 6 hubs. Sans wrapper
canonique + primitifs partagés, chaque hub réinventerait sa version, perdant
le bénéfice de la doctrine et multipliant la dette graphique.

Premier hub livré (CockpitJour, V2 maquette « juste milieu premium ») :
sert de référence et de premier consommateur des primitifs.

## Décision

### 1. Namespace `frontend/src/components/grammar/hub/`

Cinq primitifs canoniques, **JSDoc documentés**, **aucune logique métier**
(règle d'or §8.1) :

| Primitif | Rôle (loi) | Validation DEV |
|---|---|---|
| `HubPage` | wrapper compound `max-w-[1180px]` + slots `KpiTriptych` / `ChartPair` / `Highlights` (L11.0) | `pillar` ∈ {briefing, energie, conformite, factures, achat, patrimoine}, slot cardinalités 3/2/3-5 |
| `SolHeroPremiumNight` | hero bleu nuit + illustration filaire SVG 8 buildings (L11.1) | aucune (display-only) |
| `ChartFrame` | wrapper question/réponse + chart slot + footer SCM (L11.4) | aucune (display-only) |
| `HubHighlight` | ligne action-card compacte rang/severity/invitation (L11.3) | `invitation.verb` ∈ liste blanche 12 verbes |
| `HubPageFooter` | alias `SolPageFooter` (L11.5) | aucune (re-export) |

Re-exports nommés depuis `components/grammar/index.js` (alias canoniques) →
les pages importent via `from 'components/grammar'` jamais via `grammar/hub/`
direct.

### 2. Endpoint backend canonique `GET /api/cockpit/jour`

Helper unique `_build_cockpit_jour_*` × 5 dans `backend/routes/cockpit.py`
(hero / kpis / charts / highlights / footer). Org-scoped strict via
`resolve_org_id`. Payload contractuel :

```json
{
  "hero":  { "eyebrow", "title", "sub", "meta": { "quality", "confidence", "period", "scope" }, "alerts": { "count", "criticalCount" } },
  "kpis":  [ { "id", "eyebrow", "label", "value", "unit", "delta": { "value", "unit", "direction", "label", "sentiment" }, "footScm" }, ... ×3 ],
  "charts":[ { "id", "question", "answer", "type", "series" | "subscribed_kw", "footScm" }, ×2 ],
  "highlights":[ { "id", "rang", "severity", "category", "scope", "title", "evidence", "impact": { "value", "label" }, "invitation": { "verb", "object", "href" } }, ×3-5 ],
  "footer": { "sources":[...], "confidence", "updatedAt", "methodologyHref" }
}
```

Validation runtime backend : `_COCKPIT_JOUR_ALLOWED_VERBS` frozenset (12
verbes L11.3) — toute valeur hors liste est neutralisée à `voir`.

### 3. `FilterContext` partagé multi-hub

Distinct de `ScopeContext` (org/portefeuille/site = HIÉRARCHIE patrimoine).
`FilterContext` couvre les **DIMENSIONS d'analyse temporelle** : `period`
(day/week/month/year/custom) + `view` (briefing/detail/historique) + `sort`.
Persisted localStorage `promeos_filters`. Tout hub L11 consomme `useFilter()`
et déclenche un re-fetch coordonné sur changement de period.

### 4. Tokens premium-night dédiés

8 tokens CSS dans `ui/sol/tokens.css` (`--sol-night-bg`, `--sol-night-bg-alt`,
`--sol-night-fg`, `--sol-night-line`, `--sol-night-dot`, `--sol-night-dot-hot`,
`--sol-night-fg-soft`, `--sol-night-fg-meta`). Ce sont les seuls tokens
autorisés pour le hero hub L11.1. Aucun hex inline.

### 5. Source guards CI

3 guards Vitest source-guards (pure-grep `readFileSync`) dans
`frontend/src/__tests__/source_guards/cockpit_jour_l11_fe_source_guards.test.js` :

- **SG_HUB_L11_01 hub-page-uses-canonical-grammar** — toute page hub L11
  importe les 5 primitifs depuis `components/grammar` + pose les marqueurs
  `data-page` + `data-doctrine="L11"` + utilise `useFilter()` + consomme
  `getCockpitJour` (ou équivalent).
- **SG_HUB_L11_02 promeos-marque-correcte** — la marque PROMEOS s'écrit
  toujours en majuscules sans accent dans tout libellé UI ou JSX rendu.
  Forme interdite : `Promeos`, `Proméos`, `promeos`, `proméos`. Toléré dans
  imports / chemins.
- **SG_HUB_L11_03 kpi-3-no-misleading-formulation** — pas de `100%`
  hardcodé, pas de `Total ARR` hors contexte, pas de `garantie` /
  `garanti` (engagement juridique non couvert).

## Conséquences

### Positives

- **Isomorphisme cross-hub** — les 5 hubs restants (énergie, conformité,
  factures, achat, patrimoine) appliquent la même géométrie sans réinvention.
  Phase 3.5+ devient un travail de composition pure.
- **Anti-régression doctrine** — le source-guard CI garantit que toute
  nouvelle page hub respecte L11. Pas de polish désordonné possible.
- **Backend single-source-of-truth** — tous les libellés narratifs (titre
  hero, question chart, evidence highlight) sont produits par le backend.
  Le frontend ne ré-écrit jamais une formulation business (règle d'or).
- **Filter UX cohérent** — un changement de période sur un hub peut
  propager via `FilterContext` vers les autres hubs (Phase 3.5+ wiring).

### Coûts

- **Couplage page ↔ payload backend** — la signature `getCockpitJour()`
  est figée. Toute évolution exige une migration coordonnée FE+BE.
- **5 nouveaux primitifs à maintenir** (~ 800 LOC + 36 tests). Compensé par
  élimination de 5× duplication future (énergie, conformité, factures, achat,
  patrimoine).
- **Décision deferral KpiTriptychCard** — la carte KPI premium reste inline
  dans `pages/CockpitJour.jsx` tant que le second hub L11 n'existe pas.
  Extraction prévue Phase 3.5 (HubKpiCard) une fois 2 consommateurs validés
  pour éviter la sur-abstraction prématurée.

## Alternatives considérées

1. **Réutiliser `SolBriefingHead` + `SolWeekCards` existants** — rejeté :
   la grammaire L11 introduit le hero bleu nuit signature B2B + le pattern
   ChartPair question/réponse (absent v1.1) + les highlights tri-cellule
   rang/scope/invitation (différent des week-cards). La rétrofitter aurait
   cassé les 8 pages refondues Sprint v1.1.

2. **Composer directement dans la page sans wrapper `HubPage`** — rejeté :
   sans validation DEV des cardinalités slot (3/2/3-5), la doctrine devient
   du texte mort. Le compound component force le respect.

3. **Une seule route `/hub/:pillar` paramétrée** — rejeté pour Phase 3.4 :
   chaque hub a son endpoint backend + son contexte métier. Un dispatcher
   générique sera réévalué Phase 3.6 quand 6/6 hubs seront livrés.

## Validation

- Backend : `backend/tests/test_cockpit_jour_endpoint.py` (23 tests) +
  endpoint org-scoped vérifié via `resolve_org_id`.
- Frontend : `frontend/src/__tests__/source_guards/cockpit_jour_l11_fe_source_guards.test.js`
  (11 tests) + 36 tests source-guards primitifs grammar/hub/.
- Baseline FE : 4 680 tests passants (vs 4 669 avant Step 6, +11). Zéro
  régression.
- Capture Playwright : prévue Step 7 — `tools/playwright/captures/sprint_grammaire_v12_phase34/`
  before/after `cockpit/jour`.

## Suite — Phase 3.5 (HARD STOP avant scaling 4 hubs restants)

Ne pas appliquer L11 sur énergie/conformité/factures/achat **avant** :

1. Capture before/after CockpitJour validée par user.
2. Audit UX/UI/CX/CS sur la page livrée (par les 4 personas).
3. Décision GO/NO-GO scaling — y compris extraction `HubKpiCard` si la
   carte inline pose problème.
