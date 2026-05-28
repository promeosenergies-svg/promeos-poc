# Audit postfix — Usage Steering P2 Renderers & Cleanup (2026-05-27)

**Branche** : `claude/usage-steering-p2-renderers-cleanup`
**Base** : `claude/refonte-sol2` après merge PR #320 (squash `898a8723`)
**Verdict** : 🟢 **GO MERGE** — `/usages-horaires` fusionné dans `/usages` (redirect propre, lazy import retiré, HIDDEN_PAGES nettoyé). Renderer générique `UsageSignalCard` extrait depuis PilotageTab (réutilisable cross-composant). Source-guards G1-G7 verrouillent l'anti-régression de la boucle Pilotage → Action → retour source. Playwright HELIOS : 0 console error, 0 network 4xx/5xx, 0 navigation `/usage-steering`.

---

## 1 — Phase 0 audit (avant code)

| Vérif | État |
|---|---|
| `/usages-horaires` route + composant | `ConsumptionContextPage` (181 l), hidden depuis #313 |
| Composants Heatmap multiples | `HeatmapCard` (usages), `PatrimoineHeatmap`, `CarpetPlot`, `PortefeuilleScoringCard` (4 implémentations, contextes distincts) |
| Composants ProfileChart | **0** trouvé (nom inexistant dans le codebase) |
| Sites HELIOS noms uniques | **5 sites distincts** (« Siège HELIOS Paris », « Bureau Régional Lyon », « Entrepôt HELIOS Toulouse », « Hôtel HELIOS Nice », « École Jules Ferry Marseille ») — **0 doublon** au moment du sprint |
| Renderer générique pour PilotageCard | inexistant → **opportunité d'extraction** |

Phase 0 a permis de cadrer le scope : éviter le refactor invasif Heatmap7x24 (4 contextes différents) et se concentrer sur l'extraction utile (UsageSignalCard) + cleanup `/usages-horaires`.

---

## 2 — Livrables par chantier

### C1 — Fusion `/usages-horaires`

**Fichiers modifiés** :
- `frontend/src/App.jsx:82` — lazy import `ConsumptionContextPage` commenté (page reste sur disque jusqu'au cutover L8 mais n'est plus chargée par Vite).
- `frontend/src/App.jsx:520` — Route `/usages-horaires` remplacée par `<Navigate to="/usages" replace />` (preserve les deep-links bookmarks).
- `frontend/src/layout/NavRegistry.js:1147` — entrée `HIDDEN_PAGES` `/usages-horaires` retirée (devenue obsolète : la route redirige).
- `frontend/src/layout/NavRegistry.js:109` — mapping `ROUTE_MODULE_MAP` conservé (module=energie) pour fluidité breadcrumb pendant la transition redirect.

### C2 — Renderer partagé `UsageSignalCard.jsx`

**Fichier NEW** : `frontend/src/components/usages/UsageSignalCard.jsx` (146 lignes)

Extrait depuis `PilotageTab.PilotageCard` (#318) :
- Export par défaut `<UsageSignalCard signal onCreateAction busyExternalRef lastResult />`.
- Named export `INSIGHT_LABEL_FR` (source unique de vérité partagée avec `PilotageSourceBackLink` drawer V4 #320).
- Stateless : busy/feedback state injectés par l'orchestrateur via props.
- Confidence badge centralisé (`Fiable` / `À confirmer` / `À fiabiliser`).
- Lecture pure des champs `signal.*` (doctrine §8.1, 0 calcul métier FE).
- testid `usage-signal-{external_ref}` + `usage-signal-cta-{external_ref}` + `usage-signal-confidence`.

**Fichier refactorisé** : `frontend/src/components/usages/PilotageTab.jsx`
- Import remplacé : `import UsageSignalCard from './UsageSignalCard'` (8 imports d'icônes + helper `fmt` + `INSIGHT_LABEL` + `CONFIDENCE_BADGE` + `ConfidenceBadge` + `PilotageCard` ⇒ tous supprimés, replaced par l'import unique).
- 95 lignes supprimées de PilotageTab, déplacées vers UsageSignalCard (zéro duplication).
- Usage : `<UsageSignalCard signal={action} onCreateAction={handleCreate} busyExternalRef={busyRef} lastResult={lastResult} />`.

**Décision Heatmap7x24 + ProfileChart** : extraction reportée en P3 (dette explicite §6). Les 4 implémentations Heatmap actuelles (HeatmapCard usages, PatrimoineHeatmap, CarpetPlot, PortefeuilleScoringCard) ont des data models distincts ; un renderer partagé exigerait un wrapper agnostic de schema qui ajouterait plus de complexité que de valeur en P2.

### C3 — Hygiene Recharts + dédup sites

**Vérification live** :
- Endpoint `/api/patrimoine/sites` HELIOS retourne 5 sites aux noms **uniques** (cf. Phase 0 audit). Pas de duplicate-key warning observé sur `/usages` Playwright.
- Les keys composites P0b (`head-${u}`, `ademe-${u}` dans `HeatmapCard`) + P1 (`s.id ?? \`strategy-${idx}-${name}\`` dans `CdcSimulationCard` + `entry.site_id ?? \`bubble-${idx}-${name}\`` dans `FlexBubbleChart`) restent en place.

**Verrou source-guard** : les G3 P1 (`test_g3_no_name_only_keys_in_usages_components`) restent verts. Anti-régression assurée par les sprints précédents.

### C4 — Non-régression Action Center

**Playwright HELIOS** :

```
1. /usages-horaires → redirect /usages : ✅ URL finale /usages
2. /usages?tab=pilotage : pilotage-tab visible + 3 cards usage-signal-*
3. /action-center-v4?domain=optimisation : 2 items pilotage + drawer
   → PilotageSourceBackLink visible
Console errors  : 0
Network 4xx/5xx : 0
Navigations /usage-steering : 0
```

Confirmation : la boucle Pilotage → Action → retour source reste fonctionnelle.

---

## 3 — Source-guards G1-G7 (9 tests)

Fichier : `backend/tests/source_guards/test_usage_steering_p2_cleanup_source_guards.py`

| ID | Vérification | Test |
|---|---|---|
| G1 | `/usages-horaires` redirige vers `/usages` (Navigate replace) | `test_g1_usages_horaires_route_is_redirect` |
| G2 | `ConsumptionContextPage` lazy import commenté (pas dans code actif) | `test_g2_consumption_context_page_not_imported_active` |
| G3 | `HIDDEN_PAGES` n'expose plus `/usages-horaires` | `test_g3_hidden_pages_no_longer_has_usages_horaires` |
| G4 | `UsageSignalCard.jsx` existe + exports défaut + `INSIGHT_LABEL_FR` | `test_g4_usage_signal_card_exists` |
| G5 | UsageSignalCard 0 calcul métier FE (`Math.round` sur surface/price/ademe interdits) | `test_g5_usage_signal_card_no_business_math` |
| G6 | PilotageTab importe + rend `<UsageSignalCard/>` + ancien `function PilotageCard` retiré | `test_g6_pilotage_tab_uses_usage_signal_card` |
| G7 | `/usages` canonique préservée + 0 `/usage-steering` + `PilotageSourceBackLink` dans drawer + `pilotage` dans ALL_TABS | 3 tests `test_g7_*` |

**Résultat** : **9/9 verts**.

---

## 4 — Tests anti-régression

| Suite | Résultat |
|---|---|
| BE `test_usage_steering_p2_cleanup_source_guards.py` (G1-G7) | **9/9 ✅** (nouveau) |
| BE source-guards cumul `-k "cockpit or billing or energie or usage_steering"` + endpoint + monitoring | **112+ verts ✅** |
| FE `pages/cockpit/__tests__/` + `pages/action-center-v4/components/drawer/__tests__/` + `__tests__/ux-hardening.test.js` | **74/74 ✅** |
| **Total cumul** | **112+ BE + 74 FE = 186+ tests verts** |

---

## 5 — Critères d'acceptation brief (7/7 ✅)

| # | Critère | État |
|---|---|---|
| 1 | `/usages` route canonique | ✅ G7 + Playwright |
| 2 | `/usages-horaires` fusionné ou redirigé proprement | ✅ Navigate replace → /usages (G1) |
| 3 | Aucun nouveau menu | ✅ G7 + HIDDEN_PAGES nettoyé |
| 4 | Aucun `/usage-steering` | ✅ G7 |
| 5 | 0 console error | ✅ Playwright HELIOS |
| 6 | 0 network 4xx/5xx golden path | ✅ Playwright |
| 7 | Pilotage → Action → Source non régressé | ✅ Playwright 3 étapes validées + G7 `PilotageSourceBackLink` préservé |

---

## 6 — Décisions clés

1. **`/usages-horaires` redirige (pas supprimé)** : preserve les bookmarks utilisateurs sans casser le routing. Page sur disque jusqu'au cutover formel L8 Mois 5 (cohérent avec pattern `CockpitPilotage` P0a #314).
2. **`UsageSignalCard` extrait, pas Heatmap7x24/ProfileChart** : extraction utile (PilotageCard 1 seul appelant initialement, mais design préparé pour futurs callers : drawer V4, drill-down site, etc.). Heatmap7x24/ProfileChart reportés P3 — 4 implémentations distinctes avec data models incompatibles, refactor invasif.
3. **`INSIGHT_LABEL_FR` exporté comme source unique de vérité** : aligné avec `PilotageSourceBackLink` (#320) qui mappe les mêmes 5 types. Évite la duplication de mapping FR cross-composant.
4. **`source_url` conditionnel** : UsageSignalCard rend le lien « Voir la source » seulement si `signal.source_url` présent (lecture pure, brief « pas de fallback silencieux »).
5. **Sites HELIOS noms uniques actuellement** : le warning « Site Test Phase 2 » P0 a probablement été observé sur un état seed précédent. La dédup BE de P1 (`_build_action_candidates`) + les keys composites P0b/P1 verrouillent l'anti-régression même si seed change.
6. **Pas de migration BE** : tous les changements P2 sont FE only (App.jsx + NavRegistry + UsageSignalCard NEW + PilotageTab refactor). Cohérent avec contrainte brief « cleanup sans casser ».

---

## 7 — Dette résiduelle

| # | Item | Origine | Statut |
|---|---|---|---|
| Heatmap7x24 partagé | 4 implémentations distinctes (HeatmapCard usages, PatrimoineHeatmap, CarpetPlot, PortefeuilleScoringCard) avec data models incompatibles | Audit Usage Steering #316 P2 | P3 — refactor invasif reporté |
| ProfileChart partagé | 0 composant nommé ProfileChart, plusieurs Recharts ad-hoc | Audit Usage Steering #316 P2 | P3 — nécessite design data model commun |
| `ConsumptionContextPage.jsx` orpheline sur disque | Fichier 181 l plus utilisé | P2 cleanup partiel | Cutover L8 Mois 5 (cohérent CockpitPilotage) |
| Audit menu Énergie #313 P1 | Renommer « Répartition par usage » → « Usages énergétiques » | hérité | P1 cosmétique |
| Audit menu Énergie #313 P1 | Audit IS11 `/api/energy/import/jobs` sans scope | hérité | P1 sécurité |

Aucune nouvelle dette créée.

---

## Verdict

🟢 **GO MERGE** — Cleanup P2 livré sans casser la boucle Pilotage → Action → Source :
- `/usages-horaires` fusionné dans `/usages` (redirect propre, bookmarks préservés)
- `UsageSignalCard` extrait comme renderer partagé (réutilisable cross-composant, lecture pure)
- 9 source-guards G1-G7 verrouillent les 7 axes anti-régression
- Playwright HELIOS valide les 3 étapes : redirect OK, tab pilotage OK, drawer back-link OK
- 0 console error, 0 network 4xx/5xx, 0 nouveau menu, 0 `/usage-steering`
- 186+ tests cumulés verts

Le sprint suivant (P3 — Heatmap7x24/ProfileChart si pertinent, cutover L8 legacy) peut démarrer.
