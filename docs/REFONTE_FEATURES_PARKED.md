# Refonte Sol — Registre des features parked

Ce registre liste les features temporairement retirées pendant la refonte
Sol V1 pour maintenir la vélocité Pattern C / Pattern A. Chaque entrée
a une **phase cible** de réintégration et une **priorité**.

L’objectif Phase 6 Lot 3 est de réduire cette liste à 0, ou de confirmer
explicitement les P2/P3 comme « différées à v2.3+ » selon signal
utilisateur pilote.

Chaque phase qui park une feature doit ajouter une ligne dans le tableau
ci-dessous. Les tests concernés sont marqués `describe.skip` ou `it.skip`
avec un commentaire `reporté Phase 6` pour traçabilité source.

## Conventions priorité

| Priorité | Signification |
| --- | --- |
| **P0** | Blocage démo pilote, à re-intégrer avant v2.2 |
| **P1** | Utile démo, à re-intégrer Phase 6 si signal utilisateur |
| **P2** | Fonction de confort, différable vers v2.3+ selon feedback |
| **P3** | Legacy non critique, à confirmer comme supprimé définitivement |

## Registre

| # | Feature | Page affectée | Fichier legacy | Test skip | Raison | Priorité | Phase cible |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Export pack Mémobox UI (exportResult state, badge Mémobox, bouton « Ouvrir dans la Mémobox », navigate `kb_open_url`) | EfaSol `/conformite/tertiaire/efa/:id` | `pages/tertiaire/TertiaireEfaDetailPage.jsx` (thin loader post-P4) | `pages/__tests__/exportMemoboxV40.test.js` → `describe.skip('GUARD TertiaireEfaDetailPage export → Mémobox (Lot 3 P4 : reporté Phase 6)')` + `it.skip('export pack button still present')` | Pattern C minimaliste Phase 4. Le backend `generate_operat_pack` (KB doc creation) reste intact — seul l’UI est retiré. | P1 | 6 |
| 2 | handlePrecheck + qualification status card (Complétude `completeness_pct` hero) | EfaSol `/conformite/tertiaire/efa/:id` | `pages/tertiaire/TertiaireEfaDetailPage.jsx` | `pages/__tests__/exportMemoboxV40.test.js` → `it.skip('handlePrecheck still works')` + `it.skip('qualification status card still present')` | Card redondante avec la status pill SolPageHeader + KPI Référence EfaSol. Endpoint backend `precheckTertiaireDeclaration` inchangé. | P2 | 6 ou différée |
| 3 | Précheck / Controls boutons secondaires (Contrôles `runTertiaireControls` + Pré-vérification inline sur la fiche) | EfaSol `/conformite/tertiaire/efa/:id` | `pages/tertiaire/TertiaireEfaDetailPage.jsx` | Aucun test dédié — legacy retirée silent (voir commit `b8d1017c` body pour trace) | Actions secondaires toujours accessibles depuis `/conformite/tertiaire` (liste parente). Endpoints backend inchangés. | P2 | 6 ou différée |

## Historique

- **Phase 4 (EfaSol)** — commit `b8d1017c` (2026-04-19) — 3 features ajoutées (#1, #2, #3).

## Notes

- Les entrées « P1 » sont candidates à l’arbitrage Phase 6 avant le tag
  `v2.2-lot3-fiches` : re-intégration en section optionnelle Pattern C
  vs confirmation différée.
- Les entrées « P2 » ne bloquent pas le pilote ; elles attendent un
  signal utilisateur (feedback démo) avant ré-intégration.
- Toute nouvelle feature parked doit ajouter une ligne au tableau + un
  commentaire `reporté Phase 6` ou `reporté v2.3+` dans le test skip
  correspondant. Ne pas parker une feature sans entrée ici.
