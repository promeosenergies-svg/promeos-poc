# Sprint M2-5 — Frontend Centre d'Action V4 (MV3)

**Date** : 2026-05-18
**Branche** : `feat/m2-5-frontend-v4` (forkée de `feat/m2-4-rollout` — M2-4.7 inclus)
**Base merge** : `claude/refonte-sol2` (PR future — `main` gelé jusqu'au GO)

> Document produit par le sprint **M2-5.0** — audit Phase 1 read-only + cadrage.
> Aucun code applicatif, aucun composant créé. Les décisions §2/§3/§6 marquées
> « ⏳ à confirmer » attendent le STOP gate Amine avant M2-5.1.

---

## 1. Cardinal

Backend V4 (14 endpoints `/api/v4/action-center/*`, doctrine v0.3, isolation IDOR,
rate limiting) opérationnel mais **invisible** : aucune UI ne le consomme. Pilote
externe dans ~2 mois → un backend sans interface = risque produit #1.

M2-5 livre un Frontend **MV3** : un Energy Manager doit pouvoir **ouvrir,
comprendre, agir, prouver, clôturer** un sujet dans l'UI, sur un parcours complet
(use case A — audit / facture / conformité OPERAT).

---

## 2. Stratégie de coexistence

Le legacy n'est **jamais** remplacé ni modifié. Coexistence stricte derrière flag.

| Surface legacy (audit Phase 1.3) | Route | Page | M2-5 |
|---|---|---|---|
| Plan d'actions | `/actions`, `/actions/new`, `/actions/:actionId` | `ActionsPage` | inchangé |
| Hub anomalies 4 piliers | `/anomalies` | `AnomaliesPage` | inchangé |
| Alias historique | `/action-center` → `Navigate /anomalies` | (redirect) | inchangé |

- **Route V4** : `/action-center-v4` — ⏳ à confirmer. Libre, aucune collision
  (`/action-center` est un simple redirect ≠ chemin distinct).
- **Feature flag** : `VITE_FEATURE_ACTION_CENTER_V4` — ⏳ à confirmer. Aucun
  système de flag n'existe (audit 1.5) → créé en M2-5.1.
- Flag **OFF** (défaut) : route `/action-center-v4` inaccessible (redirect home /
  404 propre), legacy 100 % intact.
- Flag **ON** : Centre d'Action V4 démontrable au pilote.

---

## 3. Sous-sprints (7 commits atomiques)

| # | Sprint | Effort | Livrable principal |
|---|--------|--------|--------------------|
| M2-5.0 | Audit + plan | 30-45 min | Ce document |
| M2-5.1 | Client API V4 + hooks + feature flag | 2-3h | `apiClientV4`, `useActionCenterV4Items`, flag |
| M2-5.2 | Page liste `/action-center-v4` | 3-4h | `ActionCenterV4ListPage`, FilterBar, Table |
| M2-5.3 | Drawer détail item (4 onglets read-only) | 4-5h | `ItemDetailDrawer` + Timeline/Evidences/Blockers/Links |
| M2-5.4 | Modal transition lifecycle | 2h | `LifecycleTransitionModal` (5 états + closure_reason) |
| M2-5.5 | Modals upload + verify evidence | 2-3h | `EvidenceUploadModal`, `EvidenceVerifyModal` |
| M2-5.6 | Modals blocker + display links | 2h | `BlockerAddModal`, `BlockerResolveModal`, `LinksDisplay` |
| M2-5.7 | Seed use case A + doc closure | 1-2h | Seed enrichi, screenshots démo |

**Total estimé** : ~17-22h sur 4-5 jours. Plan ⏳ à confirmer (fusion/split possibles).

---

## 4. Design system réutilisé (audit Phase 1.1 / 1.2)

`src/ui/` contient **38 composants** `.jsx` (les 22 attendus + 16 ajouts). Aucun
composant primitif nouveau ne sera créé. Réutilisation directe pour M2-5 :

- **Critiques** : `Drawer`, `Modal`, `Table`, `Pagination`, `FilterBar`, `Button`,
  `Badge`, `Skeleton`, `EmptyState`, `ErrorState`, `Tabs` — **tous présents**.
- **Probables** : `Card`, `Input`, `Select`, `Tooltip`, `Toggle`, `ToastProvider`,
  `PageShell` — **tous présents**.
- **Optionnels** : `Progress` (barre upload), `TrustBadge` (statut preuves) — présents.
- **Bonus pertinents** : `EvidenceDrawer`, `AsyncState` (wrapper loading/empty/error),
  `Combobox`, `FindingCard`, `ActiveFiltersBar`.

`src/components/` (~65 composants feature + 15 sous-dossiers). Patterns référence :
- `CreateActionModal.jsx` / `CreateActionDrawer.jsx` — modale d'action legacy
  (inspiration, pas réutilisation directe).
- `RequireAuth.jsx` — protection de route (à réutiliser pour `/action-center-v4`).
- `ErrorBoundary.jsx` — à englober la nouvelle route.

Composants feature V4 créés dans `src/pages/action-center-v4/` (dossier à créer M2-5.2).

---

## 5. Doctrine UI respectée

- Zéro anglais dans l'UI — copy FR avec accents.
- Zéro couleur hardcodée — `KPI_ACCENTS`, `SEVERITY_TINT`, `tint`, `ACCENT_BAR`
  depuis `src/ui/colorTokens.js` ; `src/ui/tokens.js` ; `src/ui/severity.js`.
- `focus-visible:ring-2 focus-visible:ring-blue-500` sur tout interactif.
- États gérés : loading skeleton, empty, error (avec retry), partial data —
  composant `AsyncState` disponible.
- React Router **v6**, lazy loading universel (`React.lazy`) — la route V4 suivra.
- Aucun composant legacy modifié.

---

## 6. Use case A (calibrage métier — finalisé M2-5.7) — ⏳ à confirmer

Energy Manager d'HELIOS reçoit une notification :

1. Voit la liste, repère « Vérifier consommation HP/HC Q3 — Site Paris Bureaux ».
2. Ouvre l'action en drawer.
3. Lit la timeline (créée par Copilot, état `new`, 0 evidence, 0 blocker).
4. Transitionne `new → triaged`, puis `triaged → planned`.
5. Manque la facture Engie Q3 : ajoute un blocker « Attente facture Q3 fournisseur ».
6. Reçoit la facture : upload (PDF, 2 MB), evidence créée en `pending`.
7. Résout le blocker.
8. Vérifie l'evidence (`verified_at` + `verified_by` + `expires_at` +90j).
9. Transitionne `planned → in_progress`, puis `in_progress → closed/resolved`.
10. **Conséquence conformité** : l'evidence vérifiée alimente le dossier OPERAT
    (lien obligation Décret Tertiaire — affichage statut mis à jour ; la vraie
    agrégation backend est différée M2-6).

---

## 7. Tests Vitest — ⚠️ surprise environnement (cf. §12)

**Baseline figée M2-5.0** : `npx vitest run` → **4751 tests passés / 2 skipped /
233 fichiers / 0 échec** (vitest 4, durée ~2,3 s).

Règle de non-régression M2-5 : **≥ 4751 passés, 0 nouvel échec** à chaque commit.

⚠️ La config (`vite.config.js`) est `environment: 'node'`, `include:
['src/**/__tests__/**/*.test.js']`. **Pas de jsdom, pas de `@testing-library/react`.**
La suite teste de la logique pure (transforms, source-guards, structure), pas du
rendu de composant. Conséquence sur le plan de test ci-dessous → **STOP gate §12.3**.

Couverture cible (~60 tests) :
- Transformations data API → UI (formatters dates/statuts/%) : ~10 — *node OK*
- Hooks data isolés (mock `apiClientV4`) : ~10 — *node OK*
- Validation client-side (matrice lifecycle, magic check PDF/JPG/PNG) : ~10 — *node OK*
- Tests d'erreur API (401/403/404/409/422/429 propagés) : ~10 — *node OK*
- Composants critiques (`LifecycleTransitionModal`, `EvidenceUploadModal`) : ~15 — *DOM requis*
- Parcours intégration mock use case A : ~5 — *DOM requis*

---

## 8. Garde-fous QA M2-5

- Feature flag OFF par défaut : legacy fonctionne à 100 %.
- Route `/action-center-v4` → 404 / redirect propre si flag OFF.
- Aucun import depuis le legacy Centre d'actions (isolation stricte).
- Client `apiClientV4` séparé de l'`apiClient` legacy — pas d'intercepteurs
  partagés susceptibles de corrompre le legacy.
- Aucun mock permanent dans le parcours pilote (seul le seed métier alimente).
- ESLint `--max-warnings=0` maintenu, `npm run build` clean.

---

## 9. Hors scope M2-5 (différés M2-6+)

- ActionLink polymorphique 6 modules (UI affiche `disabled` + message).
- Storage avancé (upload DOCX/XLSX — refusé client-side en M2-5.5).
- Scan antivirus, chiffrement at-rest.
- Dashboards conformité OPERAT temps réel (M2-5.7 affiche un statut, pas une agrégation).
- Tests E2E Playwright (Vitest suffit pour MV3).
- i18n complète (FR uniquement pour M2-5).

---

## 10. STOP gates entre sous-sprints

Comme M2-4 :
- Chaque sous-sprint commence par lecture du commit précédent.
- Audit Phase 1 court si découverte de l'existant requise.
- Bilan en chat avant le suivant.
- 0 régression vs baseline Vitest 4751.

---

## 11. Prérequis avant M2-5.1

- [x] Branche `feat/m2-5-frontend-v4` créée (depuis `feat/m2-4-rollout`).
- [x] Audit Phase 1 livré (ce document).
- [ ] M2-4.7 mergé sur `claude/refonte-sol2` (M2-5 est empilé sur M2-4 en attendant).
- [ ] Décisions §2/§3/§6 confirmées par Amine (route, flag, sous-sprints, use case A).
- [ ] Arbitrage environnement de test (§12.3).

---

## 12. Audit Phase 1 — inventaire détaillé & surprises

### 12.1 — Inventaire (faits)

| Domaine | Constat |
|---|---|
| UI `src/ui/` | 38 composants `.jsx` — tous les critiques/probables/optionnels présents |
| Feature `src/components/` | ~65 composants — `CreateActionModal`, `RequireAuth`, `ErrorBoundary` présents |
| Routing | React Router v6, lazy universel, legacy à 3 surfaces (§2) |
| Client API | **axios** — `src/services/api/core.js`, `baseURL = VITE_API_URL ‖ '/api'` |
| Auth | interceptor requête : JWT `localStorage['promeos_token']` → `Bearer` ; 401 → purge token |
| Scope | `setApiScope({orgId,siteId})` → headers `X-Org-Id` / `X-Site-Id` ; `cachedGet` TTL 60 s |
| Hooks | pattern `usePageData` → `{ data, loading, error, refetch }` (signature standard) |
| Feature flags | **aucun** — pas de `.env` ni `.env.example` ; `import.meta.env` : DEV/MODE/PROD/VITE_API_URL/VITE_SENTRY_DSN |
| Tests | vitest 4 — 4751 passés / 2 skipped / 233 fichiers, **`environment: 'node'`** |
| Tokens | `KPI_ACCENTS` / `SEVERITY_TINT` / `tint` dans `src/ui/colorTokens.js` |

### 12.2 — Surprises

1. **🔴 Cardinal — environnement de test `node`, pas de DOM.** La suite Vitest
   tourne en `environment: 'node'` sans `jsdom` ni `@testing-library/react`. Les
   tests de rendu de composant (≈20 du plan §7) ne peuvent pas tourner en l'état.
2. **Legacy à 3 surfaces** (`/actions`, `/anomalies`, `/action-center`→redirect)
   au lieu d'une seule route — `/action-center-v4` reste libre, nom à confirmer.
3. **Aucun fichier `.env`** — le système de feature flag et les fichiers
   `.env` / `.env.example` sont à créer ex nihilo en M2-5.1 (non bloquant).
4. **Baseline réelle 4751** ≠ CLAUDE.md règle #5 (« FE ≥ 3 783 ») — doc obsolète.
5. **Client API : pas de handling multipart explicite** (`Content-Type` JSON par
   défaut) — pour l'upload evidence (M2-5.5), `FormData` natif + override
   per-request. Géré nativement par axios, non bloquant.
6. **`EvidenceDrawer.jsx` existe déjà** dans `src/ui/` — base possible pour le
   drawer M2-5.3, à évaluer (composant primitif, adaptation probable).

### 12.3 — Arbitrage requis avant M2-5.1

L'environnement de test (surprise #1) impose un choix :

- **Option A** — ajouter `jsdom` + `@testing-library/react` + pragma
  `// @vitest-environment jsdom` par fichier de test composant. Permet le plan §7
  complet (~60 tests, dont ~20 de rendu). Coût : changement d'infra de test,
  3 deps ajoutées.
- **Option B** — respecter la doctrine node-env existante : tester uniquement
  logique / transforms / hooks / validation (~40 tests, pas de rendu). Plan §7
  amputé des ~20 tests de rendu.

Recommandation neutre : **Option A** si la qualité de rendu des modals critiques
doit être garantie avant pilote ; **Option B** si la cohérence avec la doctrine
de test du repo prime. Décision Amine.

> **Décision actée (M2-5.1)** : Option A. `jsdom` + `@testing-library/react` +
> `@testing-library/jest-dom` ajoutés ; pragma `// @vitest-environment jsdom`
> par fichier de test composant ; `include` Vitest élargi à `.test.{js,jsx}`.

---

## 13. Closure M2-5 — Récap final

**Date closure socle** : 2026-05-18 · **Hotfixes M2-5.7-bis → M2-5.9.bis** : 2026-05-19
**Hash final** : `d1596e05` (M2-5.9.bis — derniers blocants avant passage « ready »)
**Branche** : `feat/m2-5-frontend-v4` → PR #280 vers `claude/refonte-sol2` (**pas `main`**)

### 13.1 — Sous-sprints livrés

**Socle M2-5.0 → M2-5.7** (closure initiale 2026-05-18) :

| # | Sprint | Hash | Tests | Livrable |
|---|--------|------|-------|----------|
| M2-5.0 | Audit + plan | `22856e06` | 0 | Ce document (12 sections) |
| M2-5.1 | Infrastructure V4 | `eee85156` | 40 | `apiClientV4` + 14 hooks + feature flag |
| M2-5.2 | Page liste | `8ed5a3d5` | 23 | `/action-center-v4` + filtre lifecycle |
| M2-5.3.A | Drawer + Timeline | `3ca1a6d5` | 24 | `ItemDetailDrawer` + 4 onglets navigables |
| M2-5.3.B | 3 onglets read-only | `f5069023` | 43 | Preuves / Blocages / Liens + rectif `SECURITY.md` §2.4 |
| M2-5.4 | Write 1 — lifecycle | `3779fc6c` | 39 | Modal transition + pattern UI write figé |
| M2-5.5 | Writes 2+3 — evidence | `61d4735a` | 30 | Upload (multipart) + verify (confirm dialog) |
| M2-5.6 | Writes 4+5 — blocker | `c19ec87d` | 20 | Add (Select 7 types) + resolve (note optionnelle) |
| M2-5.7 | Closure + seed | `279430ec` | — | 6 actions HELIOS Use Case A + doc + backlog M3 |

**Hotfixes M2-5.7-bis → M2-5.9.bis** (audit pilot-readiness, 2026-05-19) :

| # | Sprint | Hash | Livrable |
|---|--------|------|----------|
| M2-5.7-bis | Fix seed | `65afe5fa` | Référence du décret BACS de l'action 6 corrigée |
| M2-5.8.A | Connexion démo | `b8272ea0` | `POST /api/auth/demo-login` + probe `GET /available` — débloque le P0-1 |
| M2-5.8.A.bis | Surface LoginPage | `ab19fd0d` | Bouton « Connexion démo HELIOS » (Option B — seule exception legacy, cf. §13.7) |
| M2-5.8.B | 3 P0 UX | `e3a09065` | Badge priorité + `KIND_LABELS` FR + a11y clavier |
| M2-5.8.C | Polish hotfix | `89e6c9f9` | Action vedette P0 + audit énergétique + label « Créé » |
| M2-5.9 | Durcissement sécu | `b74d79ea` | Purge timestamps des hints 409 + `verify_parent_item_access` verify/resolve |
| M2-5.9.bis | Blocants finaux | `d1596e05` | `kind`/`domain` FR drawer + rate-limit demo-login + probe jouabilité + writes masqués sur `closed` + reset pagination |

**Baseline FE** : **4751** (M2-5.0) → **5005** (M2-5.9.bis).

### 13.2 — Endpoints V4 consommés

| Hook | Endpoint | Consommé |
|------|----------|----------|
| `useActionCenterV4Items` | `GET /items` | ✅ M2-5.2 |
| `useActionCenterV4Item` | `GET /items/{id}` | ✅ M2-5.3.A |
| `useActionCenterV4Events` | `GET /items/{id}/events` | ✅ M2-5.3.A |
| `useActionCenterV4Evidences` | `GET /items/{id}/evidences` | ✅ M2-5.3.B |
| `useActionCenterV4Blockers` | `GET /items/{id}/blockers` | ✅ M2-5.3.B |
| `useActionCenterV4Links` | `GET /items/{id}/links` | ✅ M2-5.3.B |
| `useTransitionLifecycle` | `PATCH /items/{id}/lifecycle` | ✅ M2-5.4 |
| `useUploadEvidence` | `POST /items/{id}/evidences` | ✅ M2-5.5 |
| `useVerifyEvidence` | `PATCH /evidences/{id}/verify` | ✅ M2-5.5 |
| `useAddBlocker` | `POST /items/{id}/blockers` | ✅ M2-5.6 |
| `useResolveBlocker` | `PATCH /blockers/{id}/resolve` | ✅ M2-5.6 |
| **`useCreateItem`** | `POST /items` | ⏳ M3+ |
| **`useUpdateItem`** | `PATCH /items/{id}` | ⏳ M3+ |
| **`useCreateLink`** | `POST /items/{id}/links` | ⏳ M3+ |

**11/14 endpoints V4 consommés** (78 %). Les 3 restants (créer / éditer un item
depuis l'UI, créer un lien manuel) sont différés M3+ : non requis par le parcours
pilote Use Case A — les items naissent du seed (et, en prod, des détecteurs
backend), pas d'une saisie manuelle.

### 13.3 — Pattern UI write figé (M2-5.4 → répliqué 3×)

Établi M2-5.4 (lifecycle), répliqué M2-5.5 (upload + verify) et M2-5.6 (add +
resolve). Squelette :

1. Hook write (M2-5.1) `useXxx` → `{ execute, loading, error, data, reset }`.
2. Helper pur si validation (matrice lifecycle, validation MIME magic bytes…).
3. Modal montée conditionnellement (`{open && <Modal />}`) → zéro pollution des
   tests du composant parent.
4. `handleSubmit` try/catch → `classifyError` → erreur 422 corrigeable affichée
   inline / erreur infra (429, 5xx…) → toast + fermeture.
5. Au succès : `refetch` de la sous-ressource via son hook + remontée parent
   (`onSuccess` / bump de clé) ; refetch pessimiste, pas d'optimistic update.
6. Toast discret de succès.

**5 modals** respectent ce pattern. Aucune méta-programmation : le hook générique
`useV4Mutation` a été explicitement refusé (M2-5.1) — 14 hooks et 5 modals
explicites, duplication contrôlée assumée.

### 13.4 — Parcours Use Case A : codé bout en bout

**Activation démo** : la route `/action-center-v4` est protégée par
`RequireAuth`. L'accès pilote passe par le bouton « Connexion démo HELIOS » sur
`/login` (visible si `PROMEOS_DEMO_MODE=true` côté backend — surfacé par
M2-5.8.A.bis). Précondition : seed Use Case A exécuté
(`python -m seeds.use_case_a_seed`), compte `marie.dupont@helios.demo` seedé.

Le seed `backend/seeds/use_case_a_seed.py` crée **6 actions HELIOS** réalistes
pour l'organisation démo (org 1, Groupe HELIOS) :

| # | Action | État | Priorité | Mécaniques V4 |
|---|--------|------|----------|---------------|
| 1 | Vérifier consommation HP/HC Q3 — Paris Bureaux | `new` | P0 Critique | vedette démo vierge |
| 2 | Déclaration OPERAT 2025 — Échéance 30/09/2026 | `in_progress` | P1 | 8 events · 2 preuves (1 vérifiée + 1 en attente) · 1 blocage · 1 lien |
| 3 | Audit énergétique réglementaire — Nice Hôtel | `triaged` | P1 | 2 events |
| 4 | Renouvellement contrat fourniture électricité — 5 sites | `planned` | P2 | 3 events |
| 5 | Optimisation HP/HC — Marseille École | `closed` / `resolved` | P3 | 7 events · 1 preuve vérifiée · 1 lien |
| 6 | Vérification décret BACS — Lyon Bureaux | `closed` / `not_applicable` | P3 | 2 events |

Total seed : 6 actions · 23 events · 3 evidences · 1 blocker · 2 links.
Idempotent (PK UUID5 déterministes — un 2ᵉ run ignore les 6 actions).

Parcours codé :

1. `/login` → bouton « Connexion démo HELIOS » → session Marie Dupont.
2. Redirect `/action-center-v4` → AppShell + rail de nav + 9 items (6 du Use
   Case A, 3 du seed minimal M2-4.1.bis).
3. Clic sur une ligne → drawer détail, 4 onglets (Timeline / Preuves / Blocages /
   Liens).
4. Timeline : events FR + acteur (« Créé », « Transition d'état »…).
5. Preuves / Blocages : modals upload, verify, add, resolve (M2-5.5 / .6).
   Sur un item `closed` (actions 5 et 6), les boutons d'ajout sont masqués ;
   `verify` / `resolve` restent pilotés par l'état propre de chaque objet
   (M2-5.9.bis — pas de nouvelle preuve ni de nouveau blocage sur item clos).
6. Action vedette « Vérifier consommation HP/HC Q3 » (P0 Critique, état `new`),
   traitée **live** : `new → triaged → planned`, upload preuve, ajout puis
   résolution d'un blocage, vérification preuve, `planned → in_progress →
   closed/resolved`.

### 13.5 — Doctrines respectées tout M2-5

- Aucun composant legacy modifié (vérifié `git diff` à chaque sprint).
- Aucun import depuis `src/components/*` legacy dans le code V4.
- Aucune dépendance externe ajoutée hors les 3 deps test M2-5.1 (`jsdom` +
  `@testing-library/react` + `@testing-library/jest-dom`).
- Aucune méta-programmation : 14 hooks explicites, 5 modals explicites.
- Doctrine UI : 100 % FR, tokens partagés, composants `src/ui/` réutilisés tels quels.
- Duplication contrôlée préférée à la factorisation tardive (matrice lifecycle
  client = copie de `lifecycle_validator.py` — cf. dette M3-MATRIX-CONTRACT-TEST).
- `storage_uri` jamais référencé dans le code source V4 (5 sprints vérifiés ;
  garde-fou commentaires `feedback_source_guard_comment_regex_trap`).
- Feature flag `VITE_FEATURE_ACTION_CENTER_V4=false` par défaut → legacy 100 %
  intact si le flag est OFF.

### 13.6 — Sortie

PR `feat/m2-5-frontend-v4` → `claude/refonte-sol2` (**pas `main`** — `main` reste
gelé jusqu'au GO global). Ouverte en **draft** : self-review à froid 24 h avant
le passage en « ready » et le merge. Tag `m2-sprint-5-done` sur le commit de merge.

Dettes M2-5 reportées : 8 items dans `BACKLOG_M3.md` §5 (« issus du sprint M2-5 »).

### 13.7 — Exceptions à la doctrine « no legacy »

Sur l'ensemble des sous-sprints M2-5.0 → .8.C, **une seule exception** assumée à
la discipline « aucun composant legacy modifié » :

| Sprint | Fichier touché | Périmètre | Justification |
|--------|----------------|-----------|---------------|
| M2-5.8.A.bis | `frontend/src/pages/LoginPage.jsx` | state probe DEMO_MODE + bouton « Connexion démo HELIOS » + handler | Option B : seule voie d'accès pilote sans réplication de `LoginPage` ni refonte d'`AuthContext` — le walkthrough Phase 0 a prouvé que le prompt inline était inatteignable derrière `RequireAuth` |

Registre vivant : `BACKLOG_M3.md` → **M3-LEGACY-TOUCHES**.
