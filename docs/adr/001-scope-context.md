# ADR-001: Scope Context — Gestion du perimetre Org/Site

**Date**: 2026-02-11
**Statut**: Accepted
**Auteurs**: Equipe PROMEOS

---

## Contexte

PROMEOS est un cockpit multi-tenant multi-sites (10-500 sites par organisation). Chaque page doit filtrer ses donnees selon l'organisation et optionnellement un site specifique. Le scope (orgId, portefeuilleId, siteId) doit etre:

- Persistant entre les sessions (retour apres fermeture navigateur)
- Injecte dans chaque appel API sans prop drilling
- Coherent entre toutes les pages et composants
- Compatible avec le mode demo (orgs dynamiques apres seed-pack)
- Compatible avec l'authentification IAM (org/scopes depuis le JWT)

---

## Probleme

Comment partager l'etat du perimetre (org/site) entre 30+ pages, l'injecter dans les headers HTTP de chaque appel API, et gerer la transition entre mode demo (mock) et mode authentifie (JWT) sans creer de couplage fort entre les composants?

---

## Options envisagees

### Option A: Redux / Zustand (state management global)

- (+) Etat global avec devtools
- (+) Middleware pour l'injection HTTP
- (-) Dependance supplementaire (~10-30 KB)
- (-) Boilerplate (actions, reducers, selectors)
- (-) Surdimensionne pour un seul "slice" d'etat

### Option B: URL query params (?orgId=3&siteId=12)

- (+) Shareable, bookmarkable
- (+) Pas besoin de localStorage
- (-) Pollue l'URL sur toutes les pages
- (-) Complexe a synchroniser avec le routeur
- (-) Fuite d'information dans les URLs partagees

### Option C: React Context + localStorage + module-level API scope (retenu)

- (+) Zero dependance supplementaire
- (+) Persistence native via localStorage
- (+) Injection API via `setApiScope()` au niveau module (pas de prop drilling)
- (+) Compatible demo (applyDemoScope) et auth (effectiveOrgId depuis AuthContext)
- (-) `_apiScope` est un etat module-level hors du cycle React
- (-) Pas de devtools dedie (compense par DevPanel)

---

## Decision

**Option C retenue.** Architecture en 3 couches:

1. **ScopeContext** (`contexts/ScopeContext.jsx`): React Context qui expose `useScope()` avec org, portefeuille, site, orgSites, sitesCount, scopeLabel. Persistance localStorage (`promeos_scope`). Fusion des sources: AuthContext (mode auth) ou MOCK_ORGS + demoOrgs (mode demo).

2. **setApiScope()** (`services/api.js`): Fonction module-level appelee par un `useEffect` dans ScopeContext a chaque changement de scope. Met a jour `_apiScope` utilise par l'intercepteur Axios pour injecter les headers `X-Org-Id` / `X-Site-Id`.

3. **Backend scope_utils** (`services/scope_utils.py`): Lit les headers `X-Org-Id` / `X-Site-Id` cote serveur et filtre les queries SQLAlchemy. Chaque route appelle `get_org_id(request)` et `apply_scope_filter(query, ...)`.

**Flux:**
```
ScopeContext (React) → setApiScope() (module) → Axios interceptor (header injection)
  → Backend middleware (X-Org-Id) → scope_utils (SQL filter)
```

---

## Consequences

### Positives

- **30+ pages** consomment `useScope()` sans prop drilling
- Le scope est persistant, coherent et injecte automatiquement
- Le DevPanel (`?debug`) affiche orgId, sitesCount, siteIds, scopeLabel en temps reel
- La transition demo → auth est transparente (effectiveOrgId)
- Les endpoints `/demo/*` sont exempts de scope injection (garde `isDemoPath()`)

### Negatives

- `_apiScope` est un etat module-level: invisible aux devtools React, risque de desynchronisation si `useEffect` rate un cycle
- Le requestId guard (`_fetchId.current`) dans ScopeContext est necessaire pour eviter les reponses stale lors de changements rapides d'org
- Les tests doivent mocker `localStorage` et `setApiScope` pour simuler le scope

### Risques acceptes

- Si un composant appelle l'API avant que le `useEffect` de ScopeContext ne s'execute, le header `X-Org-Id` peut etre absent ou stale. Mitigation: le backend genere un orgId par defaut si absent.
