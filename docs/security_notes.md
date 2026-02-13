# PROMEOS IAM — Security Notes (Sprint 12)

## Architecture

```
Client (React)
  │  Bearer token in Authorization header
  ▼
FastAPI Middleware (middleware/auth.py)
  │  decode_token() → payload {sub, org_id, role, exp}
  │  get_optional_auth() → AuthContext | None
  ▼
Route Handler
  │  check_site_access() / apply_scope_filter()   (services/iam_scope.py)
  ▼
SQLAlchemy Query (filtered by org_id + site_ids)
```

---

## DEMO_MODE Guard

| Variable d'environnement    | Default | Effet                                              |
|-----------------------------|---------|-----------------------------------------------------|
| `PROMEOS_DEMO_MODE`         | `true`  | Auth optionnelle — pas de token = acces complet      |
| `PROMEOS_JWT_SECRET`        | `"dev-secret-change-me"` | Secret HMAC pour signer les JWT |

### Comportement selon DEMO_MODE

| DEMO_MODE | Token present  | Resultat                                     |
|-----------|---------------|----------------------------------------------|
| true      | Non           | `get_optional_auth()` retourne `None` — acces total |
| true      | Oui (valide)  | Auth resolue — filtrage par scope            |
| true      | Oui (invalide)| `get_optional_auth()` retourne `None` (graceful) |
| false     | Non           | **401 Unauthorized**                         |
| false     | Oui (valide)  | Auth resolue — filtrage par scope            |
| false     | Oui (invalide)| **401 Invalid token**                        |

### Passage en production

```bash
export PROMEOS_DEMO_MODE=false
export PROMEOS_JWT_SECRET="votre-secret-256-bits-aleatoire"
```

---

## JWT (JSON Web Token)

### Payload

```json
{
  "sub": "42",
  "org_id": 1,
  "role": "energy_manager",
  "exp": 1700000000,
  "iat": 1699998200
}
```

### Parametres

| Parametre       | Valeur                          |
|----------------|---------------------------------|
| Algorithme     | HS256                           |
| Duree de vie   | 30 minutes                      |
| Secret         | `PROMEOS_JWT_SECRET` (env var)  |
| Librairie      | `python-jose[cryptography]`     |

### Refresh Token Policy

- `POST /api/auth/refresh` decode le token existant et emet un nouveau JWT
- Pas de refresh token separe — le JWT sert de refresh tant qu'il est valide
- Le frontend peut appeler `/refresh` avant expiration pour prolonger la session
- Token expire → redirection vers `/login` (intercepteur axios)

### Recommandations production

1. **Changer le secret** : ne jamais utiliser `"dev-secret-change-me"`
2. **Reduire la duree** : 15 minutes pour des environnements sensibles
3. **HTTPS obligatoire** : le JWT transite en clair dans le header Authorization
4. **Ajouter un refresh token** : token opaque avec rotation, stocke en BDD

---

## Scopes hierarchiques

### Modele de donnees

```
Organisation (ORG)
  └─ EntiteJuridique (ENTITE)
       └─ Portefeuille
            └─ Site (SITE)
```

### Resolution des scopes

| Scope defini   | Sites accessibles                   |
|---------------|-------------------------------------|
| `ORG:1`       | Tous les sites de l'organisation 1  |
| `ENTITE:3`    | Tous les sites de l'entite 3        |
| `SITE:42`     | Uniquement le site 42               |
| Aucun scope   | **Aucun acces** (deny-by-default)   |

### Deny-by-default

Si un `UserOrgRole` n'a aucun `UserScope` associe, l'utilisateur n'a acces a aucun site. Il faut explicitement assigner un scope via `/api/admin/users/{id}/scopes`.

### Expiration (prestataires)

`UserScope.expires_at` permet de definir un acces temporaire. Apres expiration, le scope est ignore par `get_scoped_site_ids()`.

---

## Filtrage server-side centralise

### Helper `services/iam_scope.py`

| Fonction                | Usage                                          |
|------------------------|-------------------------------------------------|
| `check_site_access()`  | Endpoints detail — raise 403 si site hors scope |
| `apply_scope_filter()` | Endpoints liste — filtre query par site_ids     |
| `apply_org_filter()`   | Endpoints liste — filtre query par org_id        |
| `get_effective_org_id()`| Resout org_id depuis auth ou parametre query    |

### Endpoints proteges (Sprint 12)

**Detail endpoints (check_site_access):**
- `GET /api/sites/{id}`, `GET /api/sites/{id}/stats`, `GET /api/sites/{id}/compliance`, `GET /api/sites/{id}/guardrails`
- `GET /api/alertes/{id}`
- `GET /api/purchase/estimate/{site_id}`, `GET /api/purchase/assumptions/{site_id}`, `PUT /api/purchase/assumptions/{site_id}`, `POST /api/purchase/compute/{site_id}`, `GET /api/purchase/results/{site_id}`, `GET /api/purchase/history/{site_id}`
- `GET /api/consumption-diagnostic/site/{site_id}`

**Liste endpoints (apply_scope_filter):**
- `GET /api/actions/list`, `GET /api/actions/summary`, `GET /api/actions/export.csv`
- `GET /api/notifications/list`

**Org-scoped endpoints (apply_org_filter / get_effective_org_id):**
- `GET /api/reports/audit.json`, `GET /api/reports/audit.pdf`
- `GET /api/dashboard/2min`

---

## Matrice des roles (11 roles)

| Role             | view                                    | edit                           | admin | export | sync  |
|------------------|-----------------------------------------|--------------------------------|-------|--------|-------|
| dg_owner         | ALL                                     | ALL                            | oui   | oui    | oui   |
| dsi_admin        | ALL                                     | ALL                            | oui   | oui    | oui   |
| daf              | cockpit, billing, purchase, actions, reports | billing, purchase           | non   | oui    | non   |
| acheteur         | purchase, billing, actions              | purchase                       | non   | oui    | non   |
| resp_conformite  | conformite, actions, reports            | conformite, actions            | non   | oui    | non   |
| energy_manager   | ALL                                     | conso, diag, actions, monitoring | non | oui    | oui   |
| resp_immobilier  | patrimoine, conso, actions              | patrimoine                     | non   | oui    | non   |
| resp_site        | patrimoine, conso, conformite, actions  | patrimoine                     | non   | non    | non   |
| prestataire      | patrimoine, conso, monitoring           | aucun                          | non   | non    | non   |
| auditeur         | ALL                                     | aucun                          | non   | oui    | non   |
| pmo_acc          | ALL                                     | actions                        | non   | oui    | non   |

---

## Audit Trail

Actions tracees dans `audit_logs` :

| Action           | Declencheur                   |
|------------------|-------------------------------|
| `login`          | Connexion reussie             |
| `logout`         | Deconnexion                   |
| `password_change`| Changement de mot de passe    |
| `switch_org`     | Changement d'organisation     |
| `impersonate`    | Impersonation (admin/demo)    |
| `create_user`    | Creation d'un utilisateur     |
| `update_user`    | Modification d'un utilisateur |
| `change_role`    | Changement de role            |
| `update_scopes`  | Modification des scopes       |
| `soft_delete`    | Desactivation d'un compte     |

### Consultation

- `GET /api/auth/audit` — Admin uniquement (require_permission("admin"))
- Filtrable par `action`, `user_id`, `resource_type`
- Detail JSON expandable dans l'UI admin (before/after)

---

## Tests de securite (61 tests)

| Classe de test         | Tests | Verifie                                |
|------------------------|-------|----------------------------------------|
| TestUserCRUD           | 3     | Creation, soft delete, email unique    |
| TestLogin              | 4     | Login OK, mauvais mdp, compte inactif  |
| TestJWT                | 3     | Token valide, expire, falsifie         |
| TestRolePermissions    | 4     | Permissions par role                   |
| TestScopeHierarchy     | 4     | Resolution ORG/ENTITE/SITE/vide        |
| TestScopeFiltering     | 3     | Dashboard, actions, sites filtres      |
| TestLastOwnerProtection| 2     | Protection dernier DG                  |
| TestPrestataire        | 2     | Acces avant/apres expiration           |
| TestSwitchOrg          | 2     | Switch org OK, switch non-autorise 403 |
| TestAdminEndpoints     | 5     | CRUD users admin                       |
| TestImpersonation      | 3     | Impersonation demo/admin/non-admin     |
| TestPasswordChange     | 3     | Changement mdp OK/mauvais/non-auth     |
| TestAuthMiddleware      | 5     | Middleware lenient/strict              |
| TestAntiLeak           | 7     | Zero fuite scope (403, export, audit)  |
| TestScopeHelperUnit    | 4     | check_site_access, apply_scope_filter  |
| TestAuditEvents        | 7     | Evenements audit                       |

**Total : 61 tests IAM + 709 baseline = 770 tests green**
