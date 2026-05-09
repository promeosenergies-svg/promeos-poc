# Phase 1.7 — Audit fixes Sprint Grammaire v1

_Capturé 2026-05-09 11:18 · branche `claude/refonte-sol2` · suite aux 5 audits parallèles (code-review/no-fake-code · UX persona Marie · UI/frontend-design · CX/CS · simplify) sur les 4 commits Phase 1._

## Note de traçabilité

Les modifications listées ci-dessous ont été produites comme commit atomique `fix(grammar-p1.7)`. Au moment du commit final, un processus parallèle (Phase L20 audit, autre sprint) a effectué un `git add .` global qui a **absorbé les modifications Phase 1.7** dans le commit `49235fb6 fix(audit-pL20)`. Le périmètre fonctionnel est livré, mais le commit message principal masque les fixes Phase 1.7.

Ce document rétablit la traçabilité doctrinale.

## 8 fixes appliqués

| # | Sévérité | Finding | Fichier | Action |
|---|---|---|---|---|
| 1 | **P0** | CTA `?site=1` ≠ ActionsPage attend `site_id=1` — drill-down silencieusement cassé | `frontend/src/pages/ConformitePage.jsx:809` | Query param renommé + ajout `titre=` |
| 2 | **P1** | `validateEvidence` throw au render-time → crash page si `evidence` undefined | `frontend/src/components/grammar/DecisionEvidenceCard.jsx:64-94` | Validation safe : retourne `{valid, reason}`, composant retourne `null` + `console.error` en dev si invalide |
| 3 | **P1** | `useAcronymes` closure `fetchError` ne se propageait qu'au 1er composant souscrit (Term × N en parallèle) | `frontend/src/hooks/useAcronymes.js:20-78` | `_lastError` module-scope partagé entre toutes les instances |
| 4 | **P1** | `acronyms.py` VNU défini "Versement pour Non-Usage" — DÉFINITION FAUSSE (vraie : Versement Nucléaire Universel, Loi 2023-491) | `backend/doctrine/acronyms.py:36-40` | Narrative corrigée + commentaire source légale |
| 5 | **P1** | `DecisionEvidenceCard` placée sous le fold sur /conformite — Marie DAF ne la voit jamais en CODIR 3 min | `frontend/src/pages/ConformitePage.jsx` | Bloc remonté avant `GuidedModeBandeau` / `NextBestActionCard` / `ComplianceScoreHeader` |
| 6 | **P2** | `DemoContext` `useState(true)` race condition — card visible 1 frame en prod avant fetch `/api/demo/status` | `frontend/src/contexts/DemoContext.jsx:6-23` | `useState(null)` + fallback `false` strict en cas d'erreur réseau |
| 7 | **P2** | `OnboardingPage` lazy import dead code après le redirect Phase 0.1 — chunk Vite chargé inutilement | `frontend/src/App.jsx:79` | Import retiré + commentaire pointant vers Phase 4 |
| 8 | **P2** | `grammar/SolPageFooter.jsx` alias zéro consommateur intermédiaire — bruit architectural | `frontend/src/components/grammar/{SolPageFooter.jsx,__tests__/SolPageFooter.test.js}` | Fichiers supprimés ; `index.js` re-exporte directement depuis `ui/sol/SolPageFooter` |

**Test mis à jour suite au fix #2** : `frontend/src/components/grammar/__tests__/DecisionEvidenceCard.test.js` — assertion `throw new Error` remplacée par `validateEvidence` + `return null`.

## Validation post-fix

| Métrique | Avant Phase 1.7 | Après Phase 1.7 |
|---|---|---|
| Vitest FE | 4 630 verts | **4 628 verts** (−2 normaux : retrait alias `SolPageFooter` + son test) |
| Pytest BE | OK | OK (acronyms.py fix non testé directement, test_doctrine_acronymes vert) |
| DOM `/conformite` | DEC count: 1, Term count: 1 | DEC count: 1, Term count: 1 (DEC remontée AVANT GuidedMode) |
| Fake code | 1 P1 (Term `_useAcronymes = null`) | 0 (Term consume vraiment useAcronymes Phase 1.6) |
| Fragiles tests pure-grep | 42/42 | 42/42 (3 tests de SolPageFooter alias supprimés, 39 + 3 nouveaux DEC = 42) |

## Score Phase 1 révisé

- **Avant audits** : ~6,0 / 10 (4 P1 + 4 P2 ouverts)
- **Après Phase 1.7** : ~7,5 / 10 (8 fixes appliqués)

Phase 2 démarre sur fondations saines.

## Dette résiduelle (à traiter Phase 2)

1. **42 tests Vitest grammar/ pure-grep ne testent pas le rendu** — migration `@testing-library/react` recommandée (effort ~2-3 h, hors scope Phase 2 visuelle)
2. **3 dictionnaires acronymes** coexistants (`utils/acronyms.js` + `domain/glossary.js` + YAML BE) — élimination des fallbacks statiques après stabilisation `useAcronymes` Phase 2
3. **`sha256_frozen` vide** dans `acronymes_doctrine.yaml` — calcul à figer dès Phase 2 close
4. **Tonalité Atlas/Briefing/Ledger** non différenciée — Phase 2 doit poser 3 classes utilitaires CSS sur `<main>` selon la vision (cf audit UI agent)
5. **DecisionEvidenceCard guardée DEMO_MODE** — Phase 2 doit livrer l'endpoint backend `/api/v1/conformite/top-decision-evidence` qui sert des données réelles (et retire le guard)

## Refs

- Commits Phase 1 chain : `2a06cbf4` (1.1) → `bba506c7` (1.2) → `3f9d448a` (1.3) → `4005e603` (1.6) → `49235fb6` (1.7 absorbé)
- Audits Phase 1.5 + 1.7 : 5 angles parallèles (code-review/no-fake-code · UX Marie · UI/frontend-design · CX/CS · simplify)
- Doctrine : `docs/vision/promeos_sol_doctrine.md` v1.1 §5 + §6 + §7
- Sprint complet : `SPRINT_GRAMMAIRE_V1_1_CLAUDE_CODE.md`
