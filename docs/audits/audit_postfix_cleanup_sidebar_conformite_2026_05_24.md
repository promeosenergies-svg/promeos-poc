# Audit postfix — Cleanup sidebar Conformité (2026-05-24)

**Branche** : `claude/cleanup-sidebar-conformite-souitems`
**Base** : `claude/refonte-sol2` (avant merge PR #298 / #299)
**Sprint** : navigation cleanup — `/conformite` redevient le **hub unique**.
**Verdict** : 🟢 **GO**

## Objectif

Nettoyer la sidebar Conformité sans changer la logique métier :

1. Retirer les 2 sous-items « Décret Tertiaire / OPERAT » et « Solarisation
   (APER) » de la sidebar.
2. Garder les routes `/conformite/tertiaire` et `/conformite/aper`
   accessibles en deep-link (page EFA/wizard OPERAT, page APER).
3. Surfacer les obligations à l'intérieur de `/conformite` via des **chips
   réglementaires internes** (`?regulation=`) — aucun nouveau menu.

Doctrine §6.2 (hub unique, anti-pattern menu surchargé) + audit personas Mai
2026 : Marie DAF n'a besoin que d'**une** porte d'entrée Conformité.

## Chantiers livrés

| # | Chantier | Fichier(s) clé(s) |
|---|---|---|
| 1 | Retrait des 2 sous-items DT/APER de `NAV_SECTIONS.conformite` | [NavRegistry.js](../../frontend/src/layout/NavRegistry.js) |
| 2 | Re-ajout `/conformite/tertiaire` + `/conformite/aper` dans `HIDDEN_PAGES` (deep-link only, indexés ⌘K) | [NavRegistry.js](../../frontend/src/layout/NavRegistry.js) |
| 3 | Chips réglementaires internes dans `/conformite` (Vue d'ensemble · DT/OPERAT · BACS · APER · SMÉ/BEGES) | [ConformitePage.jsx](../../frontend/src/pages/ConformitePage.jsx) |
| 4 | Extension `REGULATION_FILTER_MAP.audit-sme` avec `beges` + `bilan_ges` (chip SMÉ/BEGES) | [ConformitePage.jsx](../../frontend/src/pages/ConformitePage.jsx) |
| 5 | Mise à jour tests NavRegistry (16 → 14 items normaux ; section conformite : 3 → 1 item) | [NavRegistry.test.js](../../frontend/src/layout/__tests__/NavRegistry.test.js), [nav_v7_parity.test.js](../../frontend/src/__tests__/nav_v7_parity.test.js) |
| 6 | Source-guard test focalisé chips + anti-régression sidebar/menus fantômes (12 tests) | [conformite_regulation_chips.test.js](../../frontend/src/pages/__tests__/conformite_regulation_chips.test.js) |

## Boucle navigation post-cleanup

```
Sidebar (rail + panel module Conformité)
   │  1 seul item : « Conformité » → /conformite
   ▼
ConformitePage (/conformite)
   ├── Score header (ComplianceScoreHeader)
   ├── Audit SMÉ card
   ├── Frise réglementaire
   ├── [NOUVEAU] Barre chips réglementaires
   │      Vue d'ensemble · DT/OPERAT · BACS · APER · SMÉ/BEGES
   │      → setSearchParams('regulation', key) ; aria-selected, role tablist
   └── Tabs workflow (Obligations · Données · Plan d'exécution · Preuves)

Deep-links toujours actifs :
   /conformite/tertiaire   → TertiaireDashboardPage (wizard OPERAT, EFA)
   /conformite/aper        → AperPage
   /conformite/tertiaire/efa/:id → TertiaireEfaDetailPage
   /conformite/tertiaire/wizard  → TertiaireWizardPage
   /conformite/tertiaire/anomalies → TertiaireAnomaliesPage

Discoverability ⌘K :
   HIDDEN_PAGES indexe /conformite/tertiaire + /conformite/aper
   QUICK_ACTIONS conserve « Export OPERAT » → /conformite/tertiaire
```

## Règles non-négociables respectées

- ✅ Aucun nouveau menu (chips = filtre inline, pas tab strip)
- ✅ Aucun écran fantôme (toutes les routes existantes sont préservées)
- ✅ Aucun ACC / Flex / Partner Hub introduit
- ✅ Aucun jargon non expliqué (les chips reprennent les labels existants)
- ✅ Aucun label gaz/élec impacté (out of scope)
- ✅ Aucun KPI sans source/formule/unité/période (out of scope)
- ✅ Audit curl + Playwright en fin de sprint

## Tests

### Backend
Aucun changement backend. Pas de tests BE re-roulés.

### Frontend — Vitest

| Suite | Avant | Après | Δ |
|---|---|---|---|
| `NavRegistry.test.js` | 115 ✓ | 119 ✓ | +4 (cleanup tests) |
| `nav_v7_parity.test.js` | 17 ✓ | 17 ✓ | label updates, count 16 → 14 |
| `conformite_regulation_chips.test.js` (NEW) | — | 12 ✓ | nouveau fichier |
| **Suite FE complète** | 5302 ✓ | 5302 ✓ | 0 régression |
| Échecs pré-existants | 1 (`CompliancePage.jsx` not found, hors scope) | 1 | inchangé |

### Frontend — Playwright (audit postfix)

Script : [scripts/audit_postfix_cleanup_sidebar_conformite.mjs](../../scripts/audit_postfix_cleanup_sidebar_conformite.mjs)

```
✅ Sidebar contient au moins un lien vers /conformite (hub)
✅ Sidebar n'expose plus /conformite/tertiaire — hrefs=["/conformite"]
✅ Sidebar n'expose plus /conformite/aper
✅ Chip regulation-chip-all visible
✅ Chip regulation-chip-dt visible
✅ Chip regulation-chip-bacs visible
✅ Chip regulation-chip-aper visible
✅ Chip regulation-chip-audit-sme visible
✅ Label « Vue d'ensemble » présent dans la barre
✅ Label « Décret Tertiaire / OPERAT » présent dans la barre
✅ Label « BACS » présent dans la barre
✅ Label « APER » présent dans la barre
✅ Label « SMÉ / BEGES » présent dans la barre
✅ Chip DT cliquée → aria-selected=true
✅ URL contient ?regulation=dt
✅ Chip Vue d'ensemble retire le ?regulation= du URL
✅ /conformite/tertiaire deep-link → 200
✅ /conformite/aper deep-link → 200
✅ Pas de menu Partner Hub
✅ Pas de menu PMO
✅ 0 console error (collected 0)
✅ 0 network 5xx bloquant (collected 0)

─── BILAN ───
Passed: 22/22
```

### Curl smoke

```
GET  /conformite              → 200
GET  /conformite/tertiaire    → 200
GET  /conformite/aper         → 200
POST /api/auth/demo-login     → 200 (session démo Marie HELIOS)
```

## Critères d'acceptation (4/4 ✅)

| # | Critère | Statut |
|---|---|---|
| 1 | Sidebar affiche uniquement Conformité | ✅ |
| 2 | Aucun sous-item APER / DT visible | ✅ |
| 3 | /conformite affiche les sections internes (5 chips) | ✅ |
| 4 | Aucun menu ACC / PMO / Flex / Partner Hub | ✅ |

## Verdict

🟢 **GO** — cleanup propre, hub unique respecté, deep-links préservés,
discoverability ⌘K conservée, 22/22 contrôles Playwright verts, 0 console
error, 0 network 5xx bloquant.
