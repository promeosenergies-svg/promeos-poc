# ADR-005: API Contracts — Contrats implicites JSON entre frontend et backend

**Date**: 2026-02-11
**Statut**: Accepted
**Auteurs**: Equipe PROMEOS

---

## Contexte

PROMEOS expose 66+ endpoints REST via FastAPI, consommes par un client Axios unique (`services/api.js`). L'architecture est organisee en briques autonomes (RegOps, Bill Intelligence, Achat Energie, etc.) qui communiquent via des contrats JSON standardises (Finding, Action, Evidence). Le backend et le frontend sont developpes en parallele par la meme equipe.

---

## Probleme

Comment definir et maintenir les contrats API entre le frontend React et le backend FastAPI, sans sur-engineering (schemas formels, code generation) ni sous-engineering (pas de contrat du tout, regressions silencieuses)?

---

## Options envisagees

### Option A: OpenAPI spec-first + code generation

- (+) Contrats formels, types generes cote client
- (+) Documentation Swagger auto-generee
- (-) Lourd a maintenir: chaque changement necessite regeneration
- (-) Sur-engineering pour un POC avec 2 developpeurs
- (-) FastAPI genere deja `/docs` automatiquement

### Option B: GraphQL

- (+) Schema type, introspection
- (+) Client fetche exactement ce dont il a besoin
- (-) Complexite d'infrastructure (schema, resolvers, batching)
- (-) FastAPI + SQLAlchemy ne s'y pretent pas naturellement
- (-) Surdimensionne pour un POC

### Option C: Contrats implicites + tests de non-regression (retenu)

- (+) Zero overhead: pas de schema a maintenir separement
- (+) FastAPI auto-genere `/docs` (Swagger) a partir des type hints Python
- (+) Les tests Pytest verifient les contrats (status codes, champs attendus)
- (+) Le client `api.js` documente les contrats par l'usage
- (+) Le doc `BRICKS_INTERFACES.md` formalise les contrats cross-briques
- (-) Pas de validation statique cote frontend (pas de types TypeScript)
- (-) Les changements de schema peuvent casser le frontend silencieusement

---

## Decision

**Option C retenue.** Contrats maintenus par 4 mecanismes complementaires:

### 1. FastAPI type hints + Pydantic (backend)

Les endpoints utilisent des Pydantic models ou des type hints Python pour la validation:

```python
@router.get("/compliance/summary")
def get_summary(org_id: int = Query(None)):
    ...
    return {"total_sites": n, "compliant": c, "at_risk": r}
```

FastAPI genere automatiquement la doc OpenAPI sur `/docs`. Les reponses sont des `dict` JSON — pas de Pydantic response model systematique (choix de vitesse POC).

### 2. Client API centralise (frontend)

Un seul fichier `services/api.js` centralise tous les appels:

```javascript
export const getComplianceSummary = (params = {}) =>
  api.get('/compliance/summary', { params }).then(r => r.data);
```

Ce fichier sert de "contrat vivant": chaque fonction documente l'endpoint, les parametres et le format de retour attendu. Aucun composant n'appelle `axios` directement.

### 3. Headers implicites comme contrat de scope

Le scope est injecte via des headers HTTP, pas des query params:

| Header | Injecte par | Lu par |
|--------|------------|--------|
| `X-Org-Id` | Axios interceptor (ScopeContext) | `scope_utils.get_org_id(request)` |
| `X-Site-Id` | Axios interceptor (ScopeContext) | `scope_utils.get_site_id(request)` |
| `X-Request-Id` | Axios interceptor (tracing) | `RequestContextMiddleware` |
| `Authorization` | Axios interceptor (AuthContext) | `auth_router.get_current_user()` |

Convention: les endpoints `/demo/*` ne recoivent jamais de headers de scope (garde `isDemoPath()`).

### 4. BRICKS_INTERFACES.md (contrats cross-briques)

Le document `docs/architecture/BRICKS_INTERFACES.md` formalise les contrats entre briques:

- **Finding**: schema commun (regulation, rule_id, status, severity, confidence, evidence_required)
- **Action**: schema unifie (source_type, source_id, priority, status, roi_estimate)
- **Evidence**: schema (object_type, object_id, evidence_type, file_url)

Les briques communiquent via la base (FK polymorphiques `object_type + object_id`), jamais par import direct de code.

### 5. Tests comme filet de securite

Les 770+ tests backend verifient les contrats:

```python
def test_sites_returns_expected_fields():
    resp = client.get("/sites", headers={"X-Org-Id": "1"})
    assert resp.status_code == 200
    site = resp.json()[0]
    assert "id" in site
    assert "nom" in site
    assert "ville" in site
```

Les source guards frontend verifient que `api.js` importe les bons endpoints.

---

## Consequences

### Positives

- **Zero overhead**: pas de schema separe a maintenir, pas de code generation
- **Doc auto**: FastAPI `/docs` toujours a jour avec le code
- **Client centralise**: `api.js` est le contrat de reference cote frontend (813 lignes, 100+ exports)
- **Contrats cross-briques formalises**: `BRICKS_INTERFACES.md` documente Finding/Action/Evidence
- **Tests denses**: 770+ tests backend verifient les status codes et les champs

### Negatives

- Pas de validation statique cote frontend (JavaScript, pas TypeScript). Un champ renomme cote backend ne produit pas d'erreur de compilation cote frontend.
- Les reponses backend ne sont pas toutes wrappees dans des Pydantic response models: certaines retournent des `dict` ad-hoc.
- Le format d'erreur n'est pas 100% standardise (FastAPI `HTTPException` retourne `{"detail": "..."}`, mais certaines routes retournent des formats custom).

### Risques acceptes

- Si l'equipe grandit (3+ devs), la migration vers TypeScript cote frontend et des Pydantic response models systematiques cote backend sera necessaire. Le client centralise `api.js` facilite cette migration (un seul fichier a typer).
- Le format d'erreur sera standardise dans un sprint futur (envelope `{error, code, detail, request_id}`).
