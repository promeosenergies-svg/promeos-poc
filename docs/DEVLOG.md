# DEVLOG PROMEOS

## Sprint V13 — Parity Lock + Classic UI (2026-02-17)

**Objectif** : Rendre le Consumption Explorer "best-in-class" tout en garantissant zéro régression sur les fonctionnalités historiques.

### Commits

#### V13-A — `useExplorerMode` + bouton de bascule UI
- Nouveau hook `useExplorerMode.js` : persiste le mode UI (`classic` | `expert`) dans le `localStorage`, **jamais** dans l'URL.
- Mode Classic = layout historique avec tous les contrôles visibles sans ouvrir de panneaux supplémentaires.
- Mode Expert = layout actuel Sprint V12 (couches, portfolio, contrôles avancés).
- Bouton de bascule ajouté en haut de `ConsumptionExplorerPage`.

#### V13-BC — `StickyFilterBar v5` (Classic 4 rangs) + `InfoTooltip` + bannière Portfolio
**StickyFilterBar v5 :**
- **Rangée 1** : Sites (chips sélectionnés + bouton +), Énergie, Période, Granularité, badge qualité.
- **Rangée 2** : Pills Mode (Agrège/Superpose/Empile/Sépare) + Pills Unité (kWh/kW/EUR). En Classic : **toujours visibles** (même en mono-site). En Expert : seulement en multi-site/portfolio (comportement V12 préservé).
- **Rangée 3** : Actions (Enregistrer / Effacer / Copier le lien / Presets).
- **Rangée 4** (Classic uniquement) : **Résumé contexte** — `{N}j • {Granularité} • {N} site(s) • {M} compteur(s) • Source: {X} • Qualité: {Q}%`. Placeholders "—" pendant le chargement.

**InfoTooltip :**
- Bulle "?" inline, en survol/focus, texte en français (10 caractères max par bulle).
- Ajoutée sur : Portfolio, Mode pills (4 modes), Unité pills (3 unités).

**Bannière Portfolio :**
- Bannière non-bloquante, dismissible (X), se réaffiche à chaque entrée en Portfolio.
- Message : « Mode Portfolio — vue agrégée multi-sites (mode Agrégé uniquement). »

**Chaîne de caractères harmonisée :**
- `Electricite` → `Électricité`, `Granularite` → `Granularité`, `releves` → `relevés`.

#### V13-D — Tests (UIModeParity.test.js)
- `useExplorerMode` : 8 tests (defaults, persistence, toggle, rejette les valeurs invalides).
- `ResumeContexte Row 4` : 13 tests (YTD, pluriel site/compteur, source, qualité, caps).
- URL state : 5 tests vérifiant que `uiMode` n'apparaît **jamais** dans les paramètres URL.
- Parity Classic/Expert : 8 tests (contrôles visibles, mode pills, résumé contexte).
- Portfolio banner : 2 tests (affichage, reset).

**Total : +36 tests → 593 tests, tous verts.**

### Checklist de parité (non-régressions)
- [x] Sélection de site : chips mono + multi (add/remove, max 5) + menu recherche
- [x] Bascule énergie : Électricité / Gaz
- [x] Pills période : 7j/30j/90j/12m/YTD + plage de dates personnalisée
- [x] Sélecteur de granularité (auto, read-only)
- [x] Modes : Agrège / Superpose / Empile / Sépare
- [x] Unités : kWh / kW / EUR (axe + calculs)
- [x] Couches : Tunnel, Objectifs, Talon, Météo, Signature
- [x] Brush / mini-timeline (> 20 points)
- [x] Presets save/load/delete + Effacer + Copier le lien
- [x] Sync URL (rechargement préserve l'état)
- [x] uiMode ne modifie pas l'URL
- [x] Zéro erreur console, build clean

---

## Sprint V12 — Portfolio + OverviewRow + Chart State Machine (2026-02-16)

- `StickyFilterBar v4` : chips uniquement des sites sélectionnés, `SiteSearchDropdown`, toggle Portfolio.
- `OverviewRow` : total_kwh, avg, pic, talon, hors-horaires, CO2e.
- `PortfolioPanel` : `AggregateChart` + 3 tables de classement (conso/dérive/hors-horaires) + MiniSparklines.
- Machine à états du graphique : loading / ready / empty / blocked.
- +25 tests → 527 tests.

## Sprint V11.1 — Parity Lock Consumption Explorer (2026-02-15)

- `StickyFilterBar v3` : pills période (7j/30j/90j/12m/YTD), plages de dates, Save/Reset/Copy.
- `ExplorerChart` : Recharts Brush, rangée résumé.
- `useExplorerPresets` : localStorage.
- Fix KB backend : POST /search + GET /stats.
- 492 → 527 tests.

## Fix Critique Demo Scope (2026-02-17)

- `ScopeContext` : `scopedSites` utilise les vraies API sites, non plus `mockSites`. Expose `orgSites` et `sitesCount`.
- `api.js` : `setApiScope()` + intercepteur axios inject `X-Org-Id` / `X-Site-Id`.
- `ScopeSwitcher` : sélecteur de site (Tous les sites / site individuel).
- Backend `cockpit.py` + `sites.py` : filtrage par `X-Org-Id` via join `Site→Portefeuille→EntiteJuridique→Organisation`.
- +30 tests → 557 tests.
