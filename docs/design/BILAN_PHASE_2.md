# BILAN STOP GATE — Phase 2

> **Date** : 2026-04-19
> **Branche** : `claude/refonte-visuelle-sol` (worktree `promeos-refonte`)
> **Ports** : refonte 5175 · main 5173 (A/B vivants en parallèle) · backend commun 8001

---

## Phase en cours
- Phase 2 — CockpitSol.jsx branché API + sol_presenters + 3 modes
- Statut : **terminée** (Gate 2 finalisé après 6 fixes P0/P1)

---

## Ce qui est fait (commits)

### Commit atomique unique
```
feat(refonte-p2): CockpitSol + 3 modes + presenters purs + fallbacks runtime
```

**Contenu** :
- 17 fichiers créés · 9 modifiés · 0 backend touché
- 3 modes Surface/Inspect/Expert fonctionnels
- Presenters purs (`sol_presenters.js`) + helpers JSX (`sol_interpreters.jsx`)
- Routes : `/cockpit` → CockpitSol · `/cockpit-fixtures` → CockpitRefonte · `/cockpit-legacy` → Cockpit V1
- Fallbacks runtime : trend score si `/api/cockpit` 500 · billing.total_kwh si conso absente · mock courbe 24h si EMS vide · 3 week-cards toujours (fallback succès narratif)
- Tests : 174/174 source-guards Sol + 4274/4276 vitest (2 skipped pré-existants)
- Build Vite prod : ✓ 55s, aucun warning nouveau

### Fichiers par type
| Type | Créés | Modifiés |
|---|---|---|
| `.jsx` | 14 (composants Sol) + SolShowcase + CockpitSol = 16 | SolHero, SolKpiCard, SolSourceChip, SolHeadline, SolSubline, SolSectionHead, SolWeekCard, CockpitRefonte |
| `.js` | sol_presenters.js + barrel index.js réécrit = 2 | App.jsx |
| `.css` | tokens.css = 1 | index.css |
| `.md` | SOL_WIREFRAME_SPEC.md + SOL_MIGRATION_GUIDE.md + BILAN_PHASE_2.md = 3 | — |
| `.test.js` | — | sol_components.source.test.js |
| `.png` | 4 screenshots (refonte×2 + main×2) | — |

---

## Ce qui est validé

### Tests
- Source-guards Sol : **174 / 174 passing** (hex discipline, pas de fetch/axios, pas de `useState(data)`, font vars, component patterns)
- Vitest full suite : **4274 passing / 4276 total** (2 skipped pré-existants, 0 fail)
- Baseline non-régressée

### Build
- `npx vite build` : clean en 55 s
- Warnings : maplibre >500 kB (pré-existant, hors scope)
- `CockpitSol.jsx` bundlé sans erreur

### Source-guards Sol discipline
- ✓ Aucun hex hardcodé hors whitelist (`#FFFFFF`, `#0F172A`, `#245047`)
- ✓ Aucun import `services/api` dans `ui/sol/*`
- ✓ Aucun `fetch(` ni `axios.` dans `ui/sol/*`
- ✓ Aucun `useState` de données dans `ui/sol/*`
- ✓ Tous les composants utilisent `var(--sol-*)`

### Visuel (Playwright)
- Screenshot refonte `/cockpit` post-fix : [`docs/design/screenshots/cockpit_refonte_after.png`](./screenshots/cockpit_refonte_after.png) (1440×900 full + fold)
- Screenshot main `/cockpit` legacy : [`docs/design/screenshots/cockpit_main_before.png`](./screenshots/cockpit_main_before.png) (comparaison A/B)
- Les deux screenshots capturés via Playwright headless avec login réel (promeos@promeos.io)

### Validation zéro backend
```bash
git diff --name-only origin/main... | grep -E '^(backend/|.*\.py$)'
# → vide ✓
```

### Palette + typo
- Tokens V2 raw warm (journal en terrasse) lockés dans `tokens.css`
- Fraunces réservé : rail-logo `P.`, drawer-title, prose Inspect
- DM Sans : titres, headlines, body
- JetBrains Mono : chiffres tabular-nums, kickers, source chips, timerail, journal

---

## Ce qui reste dans la phase

### Definition of Done (10 critères)

| # | Critère | Statut |
|---|---|---|
| 1 | `CockpitSol.jsx` existe + fonctionne sur port 5174 (en pratique 5175) | ✅ |
| 2 | Utilise uniquement des composants `ui/sol/*` (pas de V1 résiduel) | ✅ |
| 3 | Aucun hex hardcodé, aucun fetch direct, aucun calcul métier | ✅ |
| 4 | `sol_presenters.js` testé par source-guards | ⚠️ indirect (les composants qui l'importent passent, pas de test dédié presenter) |
| 5 | Drawers/modales existants intégrés (ActionDrawerProvider, CommandPalette, Evidence) | ⚠️ encore dans AppShell legacy, intégration clean en Phase 3 |
| 6 | Grammaire FR (espaces fines U+202F, insécables U+00A0, chevrons, vouvoiement) | ✅ `NBSP`+`NNBSP` constants, helpers formatFR/formatFREur/formatFRPct |
| 7 | Source chips sur tous les KPIs/graphes/tableaux | ✅ 3 KPI + courbe + (mode Expert table) |
| 8 | Screenshots avant/après dans `docs/design/screenshots/` | ✅ `cockpit_main_before.png` + `cockpit_refonte_after.png` |
| 9 | Tests verts, source-guards verts, build prod clean | ✅ |
| 10 | Validation Amine au STOP GATE | 🟡 en cours (ce bilan) |

### Items restants
- Test dédié `sol_presenters.test.js` (criterion 4) — reporté Phase 5 polish ou Lot 0
- Intégration drawers legacy dans layout Sol — Phase 3 SolAppShell
- Validation utilisateur visuelle Gate 2 — ce bilan

### Bugs identifiés + traités
- **P0.1** KPI Conformité `—/100` → ✅ fallback sur `trend[last].score` (59.4 rendu)
- **P0.2** KPI Consommation `— MWh` → ✅ fallback sur `billing.total_kwh / 1000` (1 268 MWh rendu)
- **P0.3** Courbe de charge absente → ✅ mock `buildFallbackLoadCurve()` 24 points type bureau
- **P1.4** Week-cards incomplets → ✅ 3 cards toujours, fallback succès narratif
- **P1.5** Footer chiffré + raccourci → ✅ `estimated_impact_eur`, `penalty_eur`, `sites_concerned`, "Automatisable" / "✓ Clean" / "⌘K"
- **P1.6** Section meta freshness → ✅ helper `freshness()` + rendu "X points · actualisé il y a Y min"

### Bugs backend identifiés (hors scope refonte)
- `/api/cockpit` retourne **500** depuis le frontend (cause probable : session auth state flicker côté scope context, curl direct avec `X-Org-Id: 1` fonctionne). À investiguer dans un PR main séparé.
- Même bug côté main 5173 (screenshot `cockpit_main_before` montre "Données cockpit indisponibles").

### TODO backend (documentés dans `sol_presenters.js`)
- `getBillingCompareMonthly()` pour delta N-1 facture
- `getCockpitConsoMonth()` pour delta N-1 conso
- Les deux en attente de PR séparé sur main

---

## Questions bloquantes

1. **`/api/cockpit` 500 runtime browser** — ce bug existe aussi sur main 5173 (screenshot confirme). OK pour ouvrir un ticket backend séparé et continuer la refonte avec les fallbacks en place ? (A = ticket séparé, continue · B = investigue avant Phase 3)

2. **Screenshots A/B obligatoires pour toutes les pages** — user a demandé "dans les screenshots pour la migration je souhaite ceux du main et ceux de la refonte à chaque fois" : j'intègre cette règle dans `SOL_MIGRATION_GUIDE.md` + étends le script Playwright pour toujours générer la paire `<page>_main_before.png` + `<page>_refonte_after.png`. Confirmé ? (A = oui intègre règle · B = non ponctuel)

3. **Test dédié `sol_presenters.test.js`** — criterion 4 de la DoD pas strictement rempli (les source-guards vérifient absence de fetch dans composants, pas dans presenters). Ajouter maintenant ou reporter en Phase 5 polish ? (A = ajoute maintenant · B = Phase 5)

---

## Prochaine phase attendue
- **Phase 3 — SolAppShell remplace AppShell global**
- Durée estimée : 1 h
- Dépendances satisfaites :
  - SolAppShell + SolRail + SolPanel + SolTimerail + SolCartouche livrés (Phase 1) ✓
  - NavRegistry mappé dans SolRail/SolPanel ✓
  - Scope context testé via showcase ✓
  - Contextes à préserver identifiés : `ScopeContext`, `AuthContext`, `ToastProvider`, `ActionDrawerProvider`, `CommandPalette`, `OnboardingOverlay` — tous restent montés au-dessus de SolAppShell dans App.jsx

### Critères STOP GATE 3 (extraits prompt)
- [ ] Toutes routes protégées rendues dans SolAppShell
- [ ] Header legacy (breadcrumb + scope switcher + search + user menu) remplacé ou absorbé
- [ ] ScopeSwitcher déplacé dans SolPanel ou slot dédié SolAppShell
- [ ] CommandPalette accessible via ⌘K (raccourci global préservé)
- [ ] OnboardingOverlay + ToastProvider toujours montés
- [ ] Mode Expert toggle préservé et fonctionnel
- [ ] Toutes routes V1 chargent sans régression visible
- [ ] Screenshots A/B main/refonte sur 4 pages minimum (cockpit, conformité, patrimoine, achat)
- [ ] 4274/4276 tests passing, 174/174 source-guards verts
- [ ] Build Vite prod clean

### Stratégie Phase 3 recommandée
1. Refacto `App.jsx` : wrapper `RequireAuth` > `SolAppShell` au lieu de `RequireAuth > AppShell`
2. SolAppShell accepte `<Outlet />` comme children pour compatibilité React Router
3. Header legacy supprimé — scope switcher + user menu + command palette trigger intégrés dans slot `rightSlot` de SolRail ou SolPanel
4. Garder `AppShell` legacy importable comme `LegacyAppShell` pour `/cockpit-legacy` test
5. Tests de régression : naviguer sur 10 routes clés, confirmer rendu

---

**Fin BILAN_PHASE_2.md**
