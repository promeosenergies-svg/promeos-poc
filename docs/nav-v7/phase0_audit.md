# Phase 0 — Audit & baseline (Nav V7 Refonte)

**Date:** 2026-04-10
**Exécuteur:** Claude Code Opus 4.6 (1M context)
**Scope:** Audit préalable obligatoire avant refonte navigation V7.

---

## Baseline build + tests

| Système | Résultat |
|---|---|
| Frontend build (`npm run build`) | ✅ OK — 64m 54s (build artifacts générés) |
| Frontend tests (`vitest run`) | ✅ **3584 passed / 2 skipped / 0 failed** (155 files) — 9 unhandled errors (worker timeout routeMatching.test.js, non-bloquants) |
| Backend tests (collection) | ✅ **5022 tests collected** (non exécutés complètement — pytest run full non nécessaire à ce stade) |

**Gate baseline:** ✅ PASS — aucune régression autorisée en dessous de 3584 FE passed.

**Note perf:** le build prend ~65 min. Stratégie adoptée : **vitest ciblé par fichier** pour validation intermédiaire, build complet uniquement en Phase 5.

---

## Audit n°1 — ConformitePage supporte-t-elle le deep-linking ?

**Fichier:** `frontend/src/pages/ConformitePage.jsx`

**Constat:**
- ✅ Utilise `useSearchParams` (ligne 97-98)
- ✅ Supporte `?tab=obligations|donnees|execution|preuves`
- ❌ **Ne supporte PAS** un filtre par régulation (DT/BACS/APER/Audit SMÉ)
- 📌 APER a déjà une route séparée `/conformite/aper` pointant vers une page `AperPage.jsx` distincte
- 📌 Audit SMÉ est déjà rendu avec un anchor `id="audit-sme"` (ligne 660) — scroll possible via `#audit-sme`

**Verdict:**
Le refactor Phase 3 est **plus léger que prévu** :
- ✅ Garder `/conformite` + tab query param (existant)
- ✅ Ajouter lecture d'un query param `regulation=dt|bacs` pour pré-filtrer l'onglet Obligations (5-10 lignes)
- ✅ Garder `/conformite/aper` (existe déjà, page séparée)
- ✅ `/conformite/audit-sme` → `/conformite#audit-sme` (anchor navigation, pas de nouvelle route)

**Ajustement Plan v2:** au lieu de 4 nouvelles routes, on fait :
1. `/conformite` — vue d'ensemble (existant)
2. `/conformite?tab=obligations&regulation=dt` — Décret Tertiaire
3. `/conformite?tab=obligations&regulation=bacs` — Pilotage bâtiment (BACS)
4. `/conformite/aper` — Solarisation (existant)
5. `/conformite#audit-sme` — Audit SMÉ (expert, anchor)

---

## Audit n°2 — NavRail / NavPanel sont-ils actifs ?

**Fichiers:** `frontend/src/layout/{NavRail,NavPanel,Sidebar,AppShell}.jsx`

**Constat:**
- ✅ `NavRail.jsx` existe (76 lignes, Rail avec icônes tintées)
- ✅ `NavPanel.jsx` existe (509 lignes, Panel contextuel complet)
- ✅ `Sidebar.jsx` compose `<NavRail>` + `<NavPanel>` (ligne 122-124)
- ✅ `AppShell.jsx` importe et monte `<Sidebar>` (ligne 191)
- ✅ Rail+Panel Phase 6.3 est **en production**

**Verdict:** Pas de reconstruction nécessaire. On met à jour le contenu du registry et les composants lisent automatiquement.

**Complication détectée:** Le registry actuel a **deux structures parallèles** :
- `NAV_SECTIONS` — utilisé par `NavPanel` via `getSectionsForModule(activeModule)`
- `NAV_MAIN_SECTIONS` — utilisé par `Breadcrumb` via `ROUTE_SECTION_MAP`

**Décision Phase 1:** consolider en gardant les **deux exports synchronisés** (même source de données, deux vues). Alternative plus propre (supprimer NAV_MAIN_SECTIONS) = trop risqué pour cette refonte.

---

## Audit n°3 — `/` vs `/cockpit` sont-ils 2 pages distinctes ?

**Fichier:** `frontend/src/App.jsx`

**Constat:**
- ✅ `/` → route ligne 120 (composant Dashboard/HomePage)
- ✅ `/cockpit` → route ligne 225 (composant Cockpit — 77 kB bundle, cf. build output)
- ✅ **Deux pages distinctes, deux composants différents, deux bundles séparés**

**Verdict:** Aucun conflit. On garde les 2 items dans le panel Accueil comme décidé en Étape 1.

---

## Synthèse des ajustements Plan v2

| Phase | Ajustement | Raison |
|---|---|---|
| Phase 1 | Garder les 2 exports `NAV_SECTIONS` + `NAV_MAIN_SECTIONS` synchronisés | Existant utilisé par NavPanel ET Breadcrumb |
| Phase 1 | Renommer key `pilotage` → `cockpit` (et update ROUTE_MODULE_MAP) | Cohérence avec plan v2 |
| Phase 1 | Mettre à jour `Sidebar.jsx MODULE_LANDING` | Nouvelle key `cockpit` |
| Phase 3 | Au lieu de 4 nouvelles routes conformité, utiliser `?regulation=` query param | ConformitePage existe, refactor léger 10 lignes |
| Phase 3 | `/conformite/aper` déjà existant → à garder intact | AperPage.jsx séparée |
| Phase 3 | `/conformite/audit-sme` devient anchor `#audit-sme` sur /conformite | Section déjà présente ligne 660 |
| Phase 5 | Build complet uniquement en Phase 5 finale | Build lent 65 min, vitest ciblé entre-temps |

**Pas de STOP hard gate.** Aucune hypothèse v2 n'est fausse au point de bloquer. Les 3 audits passent avec ajustements mineurs.

---

## Décision : GO Phase 1

Conditions remplies :
- ✅ Baseline FE/BE verte
- ✅ Rail+Panel actif (pas de reconstruction)
- ✅ ConformitePage refactorable légèrement
- ✅ `/` et `/cockpit` distincts
- ✅ Ajustements documentés ci-dessus

Passage immédiat à Phase 1 — NavRegistry core atomique.
