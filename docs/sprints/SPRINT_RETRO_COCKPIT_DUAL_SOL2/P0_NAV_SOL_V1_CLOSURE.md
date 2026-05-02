---
sprint: cockpit_dual_sol2
phase: P0_NAV_CLOSURE
date: 2026-05-02
branch: claude/refonte-sol2
audit_ref: audit/navigation_audit_20260501.md
auteur: Claude Code (Opus 4.7)
status: closed
---

# P0 Navigation Sol v1.1 — Clôture 2026-05-02

5/5 trous P0 audit `navigation_audit_20260501.md` clos.
Cible doctrinale Sol v1.1 atteinte sur la branche `claude/refonte-sol2`.

## Table des 5 commits P0

| # | Trou P0 | Phase | Commit SHA | Description |
|---|---|---|---|---|
| **P0.4** | Badges conformité morts | Phase 1.B | [`eff5778d`](../../audits/navigation_audit_20260501.md) | Retrait dead-code progress badges DT/BACS/APER (recâblage P1.2) |
| **P0.2** | Rename canonical Cockpit labels | Phase 1.A | [`b14af2b6`](../../audits/navigation_audit_20260501.md) | "Vue exécutive" → "Synthèse stratégique" + "Tableau de bord" → "Briefing du jour" (Sol §11.3) |
| **P0.3** | Centre d'action en panel Accueil | Phase 1.C | [`86fdad8e`](../../audits/navigation_audit_20260501.md) | Item dédié `/action-center` dans section Accueil + ordre Briefing → Synthèse → Centre d'action |
| **P0.1** | Bill Intelligence module rail | Phase 1.D | [`ca2caf3a`](../../audits/navigation_audit_20260501.md) | Promotion Bill-Intel depuis item enfoui Patrimoine vers module rail dédié `facturation` (cyan, Receipt) |
| **P0.5** | Ordre rail final + séparateur Patrimoine | Phase 1.E | [`b7e25880`](../../audits/navigation_audit_20260501.md) | Cible Sol v1.1 : Accueil → Énergie → Conformité → Facturation → Achat → [sep] → Patrimoine + groupBoundary 'config' |

## Cible doctrinale atteinte

**Ordre rail final pour persona dominant Energy Manager (= default)** :

```
Accueil → Énergie → Conformité → Facturation → Achat → [séparateur] → Patrimoine
```

**Multi-persona conservé** (8 ROLE_MODULE_ORDER), Patrimoine systématiquement en dernière position visible peu importe le rôle (audit §5.3 usage one-shot setup).

## Preuve visuelle Playwright

Smoke spec : [`tools/playwright/nav_p0_smoke.spec.mjs`](../../../tools/playwright/nav_p0_smoke.spec.mjs)
Run : `node tools/playwright/nav_p0_smoke.spec.mjs` (depuis racine repo).

**11/11 assertions visuelles passent** — capture date 2026-05-02 :

| Capture | P0 vérifié | Constat |
|---|---|---|
| `rail_default.png` | P0.1 / P0.5 | 6 modules dans l'ordre cible Sol v1.1, séparateur fin visible avant Patrimoine |
| `rail_daf.png` | P0.5 | Facturation en position 2 (DAF hebdo §5.3), Patrimoine toujours en queue |
| `panel_cockpit.png` | P0.2 / P0.3 | 3 items canoniques : Briefing du jour + Synthèse stratégique + Centre d'action |
| `panel_facturation.png` | P0.1 | Section dédiée avec item "Vue d'ensemble" |
| `palette_centre.png` | P0.3 | ⌘K + "centre" → match Centre d'action via keywords |

Captures : [`tools/playwright/screenshots/nav_p0/`](../../../tools/playwright/screenshots/nav_p0/)
Report JSON : [`tools/playwright/screenshots/nav_p0/smoke_report.json`](../../../tools/playwright/screenshots/nav_p0/smoke_report.json)

## Anti-régression vérifiée

| Surface | État |
|---|---|
| Routes module-mapped accessibles | ✅ aucun 404 (ROUTE_MODULE_MAP étendu, pas modifié) |
| Pages Bill-Intel | ✅ `/bill-intel` ouvre `BillIntelPage` (App.jsx inchangé) |
| ⌘K palette | ✅ trouve les 6 modules + admin (keywords étendus rétro-compat) |
| Ctrl+Shift+C/F/B/L raccourcis | ✅ COMMAND_SHORTCUTS inchangé |
| Breadcrumb cohérent | ✅ `/bill-intel` → "Facturation > Vue d'ensemble" |
| AppShell cloche header + ActionCenterSlideOver | ✅ inchangée |
| A11y séparateur | ✅ `role="separator"` + `aria-orientation="vertical"` + non focusable |
| Mobile (panel collapse) | ✅ ordre respecté |

## Tests

| Domaine | Avant P0 | Après P0 | Delta |
|---|---|---|---|
| Vitest frontend | 4 317 | **4 364** | +47 net (incluant guards Phase 1.A → 1.E) |
| Source-guards Phase 1.A P0.2 | 0 | 7 | +7 |
| Source-guards Phase 1.C P0.3 | 0 | 4 | +4 |
| Source-guards Phase 1.D P0.1 | 0 | 6 | +6 |
| Source-guards Phase 1.E P0.5 | 0 | 26 | +26 |

Baseline FE désormais : **4 364 ✅ / 2 skipped** (≥ floor 3 783 CLAUDE.md).

## Audit livrable

L'audit Phase 0 read-only complet (614 lignes, 8 dimensions) est commité dans la même atomic Phase 1.F :
[`audit/navigation_audit_20260501.md`](../../audits/navigation_audit_20260501.md)

## Suite — Backlog P1

L'audit liste 4 axes P1 hygiène doctrinale :
- **P1.1** : `chore(nav-p1): document legacy redirects retirement plan` (legacyRedirects.js)
- **P1.2** : `feat(nav-p1): aggregate /api/v1/navigation/badges endpoint` (backend) — supprimer 2 calls Sidebar
- **P1.3** : `test(nav-p1): backend source-guard prevent legacy routes in NAV_MODULES`
- **P1.4** : `test(nav-p1): playwright e2e legacy redirects assertions`

Et 3 axes P2 polish :
- **P2.1** : sémantique badge alerts vs notifications
- **P2.2** : mobile bottom-nav 5 modules
- **P2.3** : cleanup `HIDDEN_PAGES` `/anomalies` doublon

STOP gate Phase 1.F respecté. P1.2 prochaine étape sur GO.
