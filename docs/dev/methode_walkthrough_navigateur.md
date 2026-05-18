# Méthode — Walkthrough navigateur cardinal (routing / auth / pages)

> **Statut** : règle permanente. Établie sur deux paiements concrets en M2-5.8.
> Sibling de `docs/dev/conventions.md`. À appliquer dès M2-5.8.B.

## Origine — deux paiements en deux sprints

1. **M2-5.8.A — Phase 9 (smoke curl backend)** a attrapé un bug que les 219
   tests Vitest mockés ne pouvaient pas voir : `services/iam_service` exige
   `PROMEOS_JWT_SECRET` à l'import ; la CLI du seed cassait hors pytest (le
   fallback `test-only-secret` masquait le problème en test). Corrigé : seed
   découplé de `iam_service` (hash bcrypt direct).

2. **M2-5.8.B — Phase 0 (walkthrough navigateur)**, avant tout code, a révélé
   en 30 secondes que `/action-center-v4` redirigeait vers `/login` au lieu de
   monter `ActionCenterV4ListPage` → le `DemoLoginPrompt` inline livré en
   M2-5.8.A était **inatteignable**. Cause racine : `/action-center-v4` est
   enfant de `<RequireAuth>` dans `App.jsx` ; sans token → `<Navigate
   to="/login">`. Les tests jsdom rendaient le composant en isolation,
   court-circuitant Router + RequireAuth. Coût évité : un pilote ne voyant
   jamais le Centre d'Action V4.

Hashes : M2-5.8.A `b8272ea0` · M2-5.8.A.bis `ab19fd0d`.

## Pourquoi les tests mockés sont insuffisants ici

Les tests d'isolation composant ne valident **pas** :

- le contrat de **routing** — quel parent monte ce composant ?
- le contrat d'**authentification** — `RequireAuth`, middleware, redirections ;
- le contrat d'**environnement** — variables chargées à l'import, secrets requis ;
- les **interactions cumulées** Router + Context + Layout.

Ces quatre contrats ne se valident que par un parcours navigateur réel.

## Règle permanente

Tout sprint qui touche **l'un** de :

- le routing (`App.jsx`, `RequireAuth`, imbrication des `<Route>`) ;
- l'authentification (login, logout, token, `AuthContext`) ;
- un **nouveau composant de page** (monté par le Router) ;
- un middleware backend (auth, CORS, `populate_org_context`) ;
- un service importé avec dépendances d'environnement (secrets, config)

**DOIT inclure un walkthrough navigateur live, ≥ 4 étapes** :

1. **Sans auth** — comportement attendu (redirect / page publique).
2. **Login** — état post-auth attendu (page cible, state restauré).
3. **Action principale** — fonctionne en runtime (vrai appel API, pas de mock).
4. **Reload F5** — l'état persiste (token, session).

Walkthrough = Phase 0 (avant code) OU Phase 9 (avant commit), idéalement les deux.

## Anti-patterns

- ❌ « Les tests sont verts, on peut committer » — faux pour les sprints ci-dessus.
- ❌ « Le smoke curl backend a passé » — vérifie le backend, pas la chaîne UI.
- ❌ « C'est un petit changement, walkthrough overkill » — 30 s ne sont jamais overkill.
- ❌ « Les tests jsdom font un walkthrough équivalent » — ils court-circuitent
  Router / Layout / RequireAuth.

## Pattern correct

Backend démarré dans le mode cible (DEMO_MODE, prod-like…), frontend dev server,
fenêtre navigateur propre (`localStorage.clear()` avant). Au moins 4 étapes,
screenshot ou note par étape. Reporter dans le bilan : « Phase X walkthrough N/N OK ».

Outillage repo : scripts Playwright `tools/playwright/_*.mjs` (scratch, préfixe
`_`, non commités) — cf. `_m2_5_8b_phase0.mjs`, `_m2_5_8abis_phase5.mjs`.

## ROI mesuré

- **30 s** — durée du walkthrough Phase 0 M2-5.8.B.
- **~2 h** — coût du bug s'il est découvert chez le pilote.
- **~1,5 h** — sprint M2-5.8.A.bis qui aurait été évité si le walkthrough avait
  été fait dès M2-5.8.A.

Coût / bénéfice ≥ 1:200.

## Sprints concernés (prévision)

| Sprint | Walkthrough |
|--------|-------------|
| M2-5.8.B (3 P0 UX) | Phase 0 dispensée (continuité M2-5.8.A.bis 6/6) · Phase 9 post-impl recommandé |
| M2-5.9 (sécu multi-tenant) | cardinal si middleware auth touché |
| M2-5.10 (fidélité Sol) | Phase 9 obligatoire (sprint UX-heavy) |
| Phase D-3 (connecteurs live) | cardinal (chaîne API externe) |
| Phase D-4 (migration Postgres) | cardinal (chaîne DB) |
