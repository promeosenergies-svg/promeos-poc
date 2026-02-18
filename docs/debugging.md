# PROMEOS — Guide de Debugging

## 1. Dev Panel

Ajouter `?debug` dans l'URL pour activer le DevPanel (bouton flottant en bas a droite).

**Onglets :**
- **Scope** : orgId, org.nom, sitesLoading, sitesCount, selectedSiteId, scopeLabel
- **API** : 20 derniers appels (url, method, status, duration ms, request_id)
- **Cache** : cles `promeos_*` dans localStorage avec taille
- **Env** : MODE, VITE_API_URL, VITE_SENTRY_DSN (masque)

## 2. Console structuree

Le logger frontend ecrit dans la console avec un format structure :

```
[Dashboard] Fetch alertes failed { status: 500 }
[ErrorBoundary] Something went wrong { stack: "...", componentStack: "..." }
[API] GET /sites failed { status: 500, requestId: "m1abc2def3" }
```

**Tags courants :** `Dashboard`, `API`, `ErrorBoundary`, `ScopeContext`

**Niveaux :** `debug`, `info`, `warn`, `error`

Usage dans le code :
```js
import { logger } from '../services/logger';
logger.error('MonComposant', 'Description du probleme', { extra: 'data' });
```

## 3. Request Tracing (X-Request-Id)

Chaque appel API genere un `X-Request-Id` unique (frontend) qui est propage au backend.

**Frontend → Backend :**
1. Intercepteur request Axios ajoute `X-Request-Id` header
2. Backend middleware lit ce header (ou en genere un si absent)
3. Le response contient `X-Request-Id` + `X-Response-Time`

**Pour correler front/back :**
1. Ouvrir DevPanel > onglet API
2. Noter le request_id de l'appel en erreur
3. Chercher ce request_id dans les logs backend

## 4. Backend JSON Logs

Tous les logs backend sont en JSON structure :

```json
{
  "ts": "2026-02-18T10:30:00.000000",
  "level": "info",
  "logger": "promeos.request",
  "message": "request",
  "request_id": "a1b2c3d4e5f6",
  "method": "GET",
  "path": "/api/sites",
  "status": 200,
  "duration_ms": 12.3
}
```

**Champs :**
- `ts` : timestamp ISO
- `level` : debug/info/warn/error
- `logger` : namespace (promeos.request, promeos.*, etc.)
- `request_id` : identifiant unique de la requete
- `method` : GET/POST/PATCH/DELETE
- `path` : chemin de l'endpoint
- `status` : code HTTP response
- `duration_ms` : temps de traitement en ms

## 5. Sentry (optionnel)

Pour activer Sentry :

1. Installer le package : `npm install @sentry/react`
2. Definir la variable d'environnement : `VITE_SENTRY_DSN=https://xxx@sentry.io/yyy`
3. Relancer le frontend

Le logger frontend envoie automatiquement les logs `error` et `warn` a Sentry.

**Sans `@sentry/react` installe ou sans `VITE_SENTRY_DSN` :** aucun impact, le bridge est silencieux.

## 6. Checklist "Avant de dire bug"

- [ ] Ouvrir DevPanel (`?debug`) — verifier orgId, sitesCount, sitesLoading
- [ ] Ouvrir Console navigateur — chercher `[tag]` errors
- [ ] Verifier onglet API du DevPanel — dernier fetch, status, duration
- [ ] Copier le request_id de l'appel en erreur
- [ ] Chercher ce request_id dans les logs backend (JSON)
- [ ] Verifier le scope : est-ce le bon orgId/siteId ?
- [ ] Verifier le token : est-il expire ? (401 dans le DevPanel)
- [ ] Tester avec un autre pack demo (DemoBanner > Changer de pack)
- [ ] Reproduire en mode Expert (toggle dans le header) pour voir les debug info
- [ ] Si ErrorState visible, noter le trace_id et le hint
