# Sprint Refonte Cockpit Dual Sol2 — narratif

> Bilan honnête sans embellissement. Période 26→30 avril 2026 sur
> branche `claude/refonte-sol2`. 139 commits atomiques (492a0db2 →
> 0e346c4b).

## Durée réelle vs prévue

- **Prévu** : programme 12 semaines (26/04 → mi-juillet 2026), Sprint
  Cockpit dual = 1 vague de la Refonte Sol Doctrine v1.0.
- **Réel sur ce périmètre Cockpit dual** : **5 jours** (26→30/04/2026).
- **Phases qui ont débordé** : aucune au sens classique — le sprint a
  fonctionné par itérations courtes (Phase 0→24) avec audit après
  chaque livraison plutôt qu'en sprint planning rigide.

Le sprint Cockpit dual a déjà couvert la couche **doctrine exécutable**
+ **services backend Phase 1** + **routes Cockpit dual Phase 3** +
**polish itératif Phase 13→24**. La cible doctrine §11.3 est atteinte
en termes de **plateforme et flux**, mais pas validée par panel humain.

## Ce qui a fonctionné mieux que prévu

- **Doctrine v1.1 exécutable** : `backend/doctrine/` (constants 21 +
  KPIs 7 + error_codes 11) livré comme SoT canonique au lieu de
  documents éparpillés. Activable via skill `.claude/skills/promeos-
  doctrine/` et header agents Paperclip. PR #267 prête merge.
- **Refonte intégrale 10/10 pages** : couverture nav 100% en S1
  (Sprint 1.1 → 1.10bis). 14 agents en audit parallèle après chaque
  livraison ont permis d'attraper rapidement les régressions doctrine.
- **Source-guards baseline** : passage de 5 861 (pre-V120) à **6 183
  tests passing** (+322), zéro régression introduite par les phases
  20.bis → 24.3.
- **Phase 21.B** : SoT `regulatory_rates.js` (11 entrées + helpers
  format/tooltip) — désormais consommable par 19+ composants FE qui
  hardcodaient les chiffres inline.
- **Phase 22 consolidation 3 glossaires** : architecture finale via
  façades fallback vers `utils/acronyms.js` SoT canonique. Zero
  refactor des 19 consumers existants (Explain, SolAcronym, JargonText).

## Ce qui a buggé ou dérapé

- **Phase 16.F régression** "de la trajectoire de la trajectoire" :
  driftText backend contenait déjà "de la trajectoire" mais le JSX
  ajoutait " de la trajectoire 2030" → double phrase visible CFO.
  Fix Phase 16.bis.A : retrait côté backend.
- **Phase 20.bis P0 BLOQUANT Playwright** : 13/16 PNG identiques 7457
  bytes (page login) parce que `page.press('Enter')` ne déclenchait
  pas le submit React + `waitForURL` timeout silencieux. 3 agents
  audits convergents ont flagué cette régression meta-méthodologique.
  Fix Phase 23.A : `page.click('button[type="submit"]')` + `waitForURL`
  strict avec exit 1 sur fail.
- **Phase 23 anomalie arithmétique APER** : `count=4` (sites) ×
  `unit=20` (€/m²/an) = 80 € mais `value_eur=252 000` parce que le
  vrai multiplicateur était 12 600 m² (surface), pas 4. Audit Vérif
  #1 runtime API a détecté la divergence. Fix Phase 23.bis :
  `count=int(round(surface_m2))` + `unit_label="m²"` + tooltip FE qui
  détecte unit_label.
- **Phase 23.C OPERAT fallback** : code interprétait "sites sans
  statut DT" comme "OPERAT manquant", sur-estimant systématiquement
  l'exposition. Fix : ne compter que les sites avec
  `operat_declared=False` ou `statut_operat='non_declared'` explicite.
- **Phase 24.1 Playwright cumul** : même avec `page.goto` 25→40s +
  `commit` fallback 8s, **13/16 routes timeout** sur Vite dev (root
  cause : recompile lazy bundles per-route, IPC saturé). Le bump est
  défensif mais ne déverrouille pas les 13 routes — vrai fix futur =
  `vite build && vite preview` au lieu de `npm run dev`.

## Décisions prises seul faute d'instruction explicite

- **Architecture 3 glossaires** : choix Phase 22 de garder les 3
  systèmes (`Explain`+`ui/glossary.js`, `SolAcronym`+`domain/glossary.js`,
  `AcronymTooltip`+`utils/acronyms.js`) avec façades fallback, plutôt
  que refactorer les 19 consumers. Trade-off : maintenance dans 3
  endroits, mais zero risque de break runtime. Gain immédiat.
- **Phase 23.bis count=surface_m2** : choix de remplacer la
  signification de `count` (sites → m²) plutôt que d'ajouter un nouveau
  champ `multiplier_value`. Plus simple côté FE (1 seul tooltip path)
  mais ambigu côté contrat API (count ne veut plus dire "nombre de
  sites" pour APER). Documenté inline + via `unit_label`.
- **Phase 24.3 price_assumption** : choix de propager le SoT prix
  energie via la dataclass de retour de `_estimate_capex_payback`
  plutôt que d'appeler le ParameterStore depuis le FE. Reste cohérent
  avec règle d'or "zero business logic frontend".

## Source-guards ajustés ou supprimés

- **`sourceGuards.test.js > glossary mentions taux 2026 (26.58)`**
  était rouge sur baseline (Phase 21.B.1 avait migré les chiffres de
  `ui/glossary.js` vers `domain/regulatory_rates.js`). Phase 24.3 a
  repointé le regex sur le nouveau SoT, sans modifier la sémantique
  du guard (toujours détecter "26.58 référencé quelque part en FE").

## Trade-offs intentionnels acceptés

- **Captures Playwright dégradées** : 3/16 routes hydratées (Cockpit
  Pilotage / Cockpit Stratégique / Conformité). Les 13 autres sont
  prises en mode dégradé (état partiel). Considéré acceptable pour
  audit FIN DE SPRINT, mais bloquant pour démo client réelle.
- **Backend cold-start dépendant** : le seed
  `python -m services.demo_seed --pack helios --size S` doit être
  réinitialisé avant chaque démo car la DB SQLite garde l'état entre
  runs. Pas de mécanisme idempotent end-to-end.
- **Tests pré-existants rouges** : `test_ai_client.py`,
  `test_ems_overlay.py`, `test_kb_telemetry.py` (93 fails + 14 errors
  total) **non corrigés** car hors scope Cockpit dual. Documentés
  comme dette baseline antérieure (incident V120 / sprint Agent SDK
  migration).
- **Surface batiments vs sites divergente** : `sum(batiments.surface_m2)
  = 35 000 m²` mais `sum(sites.surface_m2) = 17 500 m²`. Phase 1.E a
  corrigé `sites.surface_m2` à 17 500 (cible) mais les
  `batiments.surface_m2` individuels gardent les anciennes valeurs
  (sur-estimation × 2). Pas bloquant car le cockpit consomme sites
  via `cockpit_facts_service`.

## Dette technique créée

- **2 models JS résiduels** : `dashboardEssentials.js` (25 800 oct)
  et `dataActivationModel.js` (5 644 oct) restent dans
  `frontend/src/models/` alors que la spec attendait leur suppression
  Phase 1.4. Vérification consumers à mener avant suppression.
- **`priority_service.py` non matérialisé** : la "Phase 1 priorité"
  prévue comme service séparé est incorporée dans
  `cockpit_facts_service.py` (`get_top_priorities()`) — fonctionnel
  mais incohérent avec la spec.
- **22/32 sentinels source-guards** non créés avec le naming exact du
  prompt. Ils existent peut-être avec un naming différent (ex:
  `test_actions_decision_must_show_traced_eur` vs
  `test_actions_decision_show_mwh_or_traced_eur`) — pas vérifié
  exhaustivement par renaming heuristique.
- **Captures Playwright 13/16 timeout** : root cause infra Vite dev,
  pas de fix possible sans switch vers `vite build && vite preview`
  (chantier Phase 25).
- **CTA gaz transport coef** : non encore exposé dans
  `domain/regulatory_rates.js` (Phase 24.2 a corrigé distribution gaz
  + élec mais pas le coef transport gaz qui dépend de l'arrêté annuel).

## Prochaine priorité recommandée

Si je continuais sur cette branche, **dans cet ordre** :

1. **Phase 25 — Playwright build prod** : remplacer `npm run dev` par
   `vite build && vite preview` dans les scripts d'audit Playwright.
   Élimine la recompilation lazy per-route. Effort ~2-3h. Déverrouille
   13/16 routes pour audit fin de sprint réel.
2. **Phase 26 — Test utilisateur réel CFO/EM** : 4 sessions
   chronométrées sur le panel mobilisable (intra-PROMEOS team faute
   de panel client externe). Documente les verbatim et identifie les
   zones cognitives où la doctrine §11.3 ne tient pas en pratique.
3. **Phase 27 — Cleanup dette pré-existante** : `test_ai_client.py`
   (`_stub_response()` missing kb_context) + `test_ems_overlay.py`
   (org-scoping 403) + `test_kb_telemetry.py` (cascades hits sqlite).
   Effort ~4-6h. Permet de retomber sur baseline 100% verte.
4. **Phase 28 — Backend cold-start clean** : kill PID 56869
   (multiprocessing-fork) bloqué + idempotency `demo_seed`. Empêche
   les blocages de démo en production.
5. **Phase 29 — Démo intégrale juillet** : préparation panel investis-
   seur + Jean-Marc CFO + Marie DAF tertiaire conformément au
   programme `project_refonte_sol_doctrine_3mois.md`.

Stop suggéré : **avant Phase 25**, ne pas merger `claude/refonte-sol2`
sur `main` (le user a explicitement demandé un audit complet AVANT
remplacement de main par cette branche, cf memory `feedback_kb_naming
_convention.md` et discussion 26/04).
