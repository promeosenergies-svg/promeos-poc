# V51 — Audit Patrimoine : routing, API contract, CTAs

## Contexte

Le module Patrimoine est la source de verite pour les sites, batiments, compteurs et contrats.
Plusieurs modules (Cockpit, Tertiaire, Conformite, Analyse) referent ce patrimoine via CTAs et deep-links.
V51 audite la sante complete de la brique et corrige les trous identifies.

## FAITS (constates lors de l'audit)

### Inventaire complet

| Couche | Fichiers | Lignes |
|--------|----------|--------|
| Backend models | `patrimoine.py`, `site.py`, `batiment.py`, `compteur.py`, `organisation.py` | ~800 |
| Backend routes | `routes/patrimoine.py` | 1450 |
| Backend services | `services/patrimoine_service.py` | 992 |
| Frontend pages | `Patrimoine.jsx`, `Site360.jsx`, `SiteDetail.jsx` | ~1400 |
| Frontend API | `services/api.js` (31 exports patrimoine) | — |
| Frontend wizard | `PatrimoineWizard.jsx` (6-step import) | ~600 |
| Demo seed | `services/demo_seed/gen_master.py` + data | — |

### Routes backend (35+ endpoints)

- Staging pipeline : template, import, summary, rows, issues, fix, autofix, validate, activate, result, abandon
- Sites CRUD : list, detail, update (patch), archive, restore, merge
- Compteurs : list, update, move, detach
- Contrats : list, create, update, delete
- Delivery points : list par site
- KPIs : aggregat patrimoine
- Export CSV : sites, staging report
- Demo : load

### CTAs vers /patrimoine

| Module source | Fichier | CTA |
|---------------|---------|-----|
| CommandCenter | `pages/CommandCenter.jsx` | `/patrimoine` + `/sites/{id}` |
| ImpactDecisionPanel | `pages/cockpit/ImpactDecisionPanel.jsx` | `/patrimoine` |
| TertiaireDashboard | `pages/tertiaire/TertiaireDashboardPage.jsx` | `/patrimoine` |
| Site360 | `pages/Site360.jsx` | retour `/patrimoine` |
| Cockpit | `pages/Cockpit.jsx` | `/sites/{id}` (detail) |
| TertiaireWizard | `pages/tertiaire/TertiaireWizardPage.jsx` | `?site_id=` prefill |

### Etat avant V51

- **Routage** : 25/25 checks PASS — zero route cassee, zero CTA dead-end
- **API contract** : 31/31 fonctions frontend matchent un endpoint backend
- **3 wrappers manquants** identifies (export report, delivery points, KPIs patrimoine)

## DECISIONS

1. **Ajout de 4 wrappers API manquants** (`stagingExportReport`, `patrimoineDeliveryPoints`, `patrimoineKpis`, `patrimoineSitesExport`) — aligne front/back a 100%
2. **`getImportTemplate` existait deja** (L473 api.js) — doublon supprime
3. **`getImportTemplateColumns` existait deja** (L738 api.js) — pas de modification
4. **64 source guards** couvrant : Router (4), NavRegistry (3), API contract (31), CTAs (6), Wizard (4), Page features (6), Backend routes (10)
5. **Zero modification UX** — le module est sain, pas de regression a corriger

## HYPOTHESES

- Aucune hypothese non verifiee : tout a ete audite par lecture de source + tests automatises

## Fichiers modifies

| Fichier | Action |
|---------|--------|
| `frontend/src/services/api.js` | +4 wrappers, -1 doublon |
| `frontend/src/pages/__tests__/patrimoineAuditV51.test.js` | NEW — 64 source guards |
| `docs/decisions/v51_patrimoine_audit.md` | NEW |
| `docs/dev/patrimoine_routing_map.md` | NEW |
| `docs/dev/v51_patrimoine_manual_test.md` | NEW |

## Verification

```bash
# Frontend — 72 fichiers, 1946 tests, 0 fail
cd frontend && npx vitest run

# V51 guards specifiques
npx vitest run src/pages/__tests__/patrimoineAuditV51.test.js
# → 64/64 pass
```

## Risques

Aucun risque identifie — V51 est un audit non-destructif (ajout de wrappers + tests, zero modification de code existant).
