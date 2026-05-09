# Phase 3.3.fix — Audit fixes Sprint Grammaire v1 (LEDGER bill-intel)

_Capturé 2026-05-09 16:13 · branche `claude/refonte-sol2` · suite à l'audit Phase 3.X tris (5 angles parallèles : code-review/no-fake-code · UX persona Marie · UI/frontend-design · CX/CS · simplify) sur le commit Phase 3.3 LEDGER reconstruction `b1b72d70`._

## Note de traçabilité

Les modifications listées ci-dessous ont été produites comme commit atomique `fix(grammar-p3.3.fix)`. Au moment du commit final, un processus parallèle (Phase L28 audit cross-pillar) a effectué un `git add .` global qui a **absorbé les modifications Phase 3.3.fix** dans le commit `02bd57b4 fix(audit-pL28)`. Le périmètre fonctionnel est livré, mais le commit message principal masque les fixes Phase 3.3.fix.

Ce document rétablit la traçabilité doctrinale.

## 5 fixes appliqués (~40 min)

| # | Sévérité | Finding | Fichier | Action |
|---|---|---|---|---|
| 1 | **P1** | Dead code : `topInsight useMemo` orphelin (commit P3.3 disait "65 LOC supprimées" mais le useMemo de calcul subsistait) | `frontend/src/pages/BillIntelPage.jsx` | useMemo retiré + commentaire Phase 3.3.fix P1 #1 explicatif |
| 2 | **P1** | `String(typeLabel).toUpperCase()` pouvait renvoyer `[object Object]` car `TYPE_LABELS[type]` contient des `<>` ReactNode JSX (shadow_gap, unit_price_high, etc.) | `frontend/src/pages/BillIntelPage.jsx:945+` | Résolution via `BILLING_INSIGHT_TYPE_LABELS[insight.type]` (registry plain string) au lieu de `TYPE_LABELS` (qui contient JSX) |
| 3 | **P1** | Drill-down cassé : `primaryCta.href="#insight-{id}"` (ancre statique sans DOM id correspondant) + double-action wrapper onClick parent + propagation `<a>` natif → click déclenchait navigation hash + drawer simultanément | `frontend/src/pages/BillIntelPage.jsx:945+` | `primaryCta` retiré du DEC bill-intel ; le wrapper `<div role="button">` capture seul le click pour ouvrir le drawer (cohérent UX, single-action) |
| 4 | **P2** | Mapping insight → DEC inliné (50+ LOC dans le JSX BillIntelPage) — 3e variante d'un mapping action/insight → DEC alors que `decisionAdapters.js` existe déjà comme SoT (CockpitPilotage + ActionCenterSlideOver) | `frontend/src/components/grammar/decisionAdapters.js` | Extraction `buildDecFromBillingInsight(insight, rang, categoryLabel, titreNode)` dans la SoT. Signature stricte (string-only pour `category`, ReactNode autorisé sur `titre`). Documentation contre-pattern ReactNode coercition |
| 5 | **P2** | Aucun test Vitest ne couvre les nouveaux primitifs Phase 3.3 (`top3Insights`, `bill-intel-top-decisions`) | `frontend/src/pages/__tests__/billIntelLedger.test.js` | Source-guard 9 tests pure-grep : Top 3 DEC structure + SoT mapping consommé + suppression dead code + ReactNode jamais coercé + pas de double-action drill-down |

## Validation post-fix

| Métrique | Avant Phase 3.3.fix | Après Phase 3.3.fix |
|---|---|---|
| Vitest FE | 4 608 verts | **4 617 verts** (+9 tests source-guards) |
| DOM `bill-intel-top-decisions` count | 1 | 1 (préservé) |
| DOM `top-anomaly-hero` (legacy) | 0 | 0 (régression guard) |
| `topInsight useMemo` orphelin | 1 (dead code) | **0** (supprimé) |
| Mapping inline LOC | ~50 LOC inline | ~5 LOC (3 résolveurs + 1 spread `{...decPayload}`) — SoT extraite |
| Drill-down DEC | href ancre + double-action | wrapper `<div role=button>` seul |

## Score Phase 3.3 révisé

- **Avant audit Phase 3.X tris** : 7,7/10 (3 P1 + 2 P2 ouverts)
- **Après Phase 3.3.fix** : ~8,5/10 (cible sprint atteinte)

## Cohérence cross-vues post Phase 3.3.fix

Les 3 vues cardinales Sprint Grammaire convergent maintenant sur **une SoT mapping decisionAdapters.js** :

- `aggregatePrioritiesForBriefing` (CockpitPilotage cockpit/jour) — agrégation anti-carbone-copy + DOMAIN_LABEL_FR + buildEvidenceFallback
- `buildDecisionFromAction` (ActionCenterSlideOver centre-action peek) — mapping action/issue → DEC LEDGER
- `buildDecFromBillingInsight` (BillIntelPage bill-intel — Phase 3.3.fix nouveau) — mapping insight billing → DEC LEDGER

Pattern commun : 4 cellules Loi L9, tonalité briefing calme via `toDecSeverityBriefing`, structure `{rang, category, scope, severity, titre, lead, evidence[4], methodologyRef}`.

## Refs

- Audit Phase 3.X tris : 5 agents convergents 3 P1 cardinaux + 2 P2 cleanup
- Sprint chain : `b1b72d70` (Phase 3.3 LEDGER) → `02bd57b4` (Phase 3.3.fix absorbé dans audit-pL28)
- Sprint complet : `2a06cbf4` → `bba506c7` → `3f9d448a` → `4005e603` → `8974c1e0` → `feb3aa04` → `fcce0607` → `798ee41d` → `010bfd83` → `60649e33` → `949b15a7` → `b1b72d70` → `02bd57b4` (3.3.fix absorbé) — **14 commits Sprint Grammaire**
- Doctrine : `docs/vision/promeos_sol_doctrine.md` v1.1 §5 + §5.6 + §6.4
- Memory : `feedback_lego_reconstruction_pages.md` (consigne Amine 09/05)
