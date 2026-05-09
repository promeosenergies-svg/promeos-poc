# Visual Grammar — Regression Suite (Sprint Grammaire v1)

Spec Playwright qui détecte tout drift visuel sur les 7 vues cardinales PROMEOS post-Sprint Grammaire. Bloque PR Phase 2+ si drift > 0,5 %.

## Périmètre — 21 baselines (7 vues × 3 viewports)

| Slug | Route | Identité produit (vision Atlas/Briefing/Ledger) |
|---|---|---|
| `cockpit-jour` | `/cockpit/jour` | Cockpit Briefing — décision quotidienne |
| `cockpit-strategique` | `/cockpit/strategique` | Cockpit Note exécutive — situation → risque → décision → preuve |
| `centre-action` | `/?actionCenter=open&tab=actions` | Centre d'action peek — priorité → impact → action → suivi |
| `anomalies` | `/anomalies` | Ledger anomalies (4 piliers) |
| `site-paris-bureaux` | `/sites/1` | Atlas Site360 — patrimoine drill-down |
| `conformite` | `/conformite` | Conformité — trajectoire DT/BACS/APER |
| `factures` | `/bill-intel` | Ledger factures — shadow billing |

> `/onboarding` est exclu : Phase 0.1 redirige vers `/cockpit/jour` (cf. `App.jsx`). Phase 4 livrera un vrai wizard (test 2 doctrinal "dirigeant non-sachant").

Viewports : 1440×900 (desktop large), 1280×800 (desktop standard), 1024×1366 (iPad portrait).

## Activation Phase 3 du sprint

```bash
# une fois @playwright/test ajouté en devDependencies frontend ou racine
npm i -D @playwright/test
npx playwright test --config=frontend/tests/visual-grammar/playwright.config.ts
```

## Mise à jour des baselines (autorisée Phase 1/2 après validation Amine)

```bash
npx playwright test --config=frontend/tests/visual-grammar/playwright.config.ts --update-snapshots
```

⚠️ Les baselines sont **frozen** entre les phases du sprint : tout `--update-snapshots` doit être justifié dans le commit message et validé par revue.

## Pré-requis runtime

- Frontend : `http://localhost:5175` (port refonte-sol2) — `npm run dev` dans `frontend/`
- Backend : `http://localhost:8001` — `python main.py` dans `backend/`
- DEMO_MODE actif, seed `helios` chargé

## Capture initiale Phase 0 — `tools/playwright/grammar_audit_v1.mjs`

Les 21 baselines présentes dans `__snapshots__/` ont été produites par le script `.mjs` Phase 0 (qui utilise `playwright` natif sans `@playwright/test`). Phase 3 réutilise ces PNG comme référence — pas de re-capture nécessaire si `dev` du repo et seed n'ont pas bougé.

## Refs

- Sprint complet : `SPRINT_GRAMMAIRE_V1_1_CLAUDE_CODE.md`
- Audit factuel : `docs/audits/grammar_v1/SYNTHESE_AUDIT_PHASE_0.md`
- Doctrine : `docs/vision/promeos_sol_doctrine.md` v1.1 §5
- ADR enforcement : `docs/adr/ADR-016-*.md`
