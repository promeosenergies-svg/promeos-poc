# PROMEOS IAM ULTIMATE — Plan Technique

## Contexte

PROMEOS est un cockpit energetique multi-sites (FastAPI + SQLAlchemy/SQLite + React 18/Vite/Tailwind).

**Etat actuel**: AUCUNE authentification. L'API est ouverte (CORS `*`), pas de JWT, pas de users, pas de middleware auth. Le ScopeContext frontend utilise des mocks hardcodes. 60+ endpoints acceptent `org_id` sans validation. 709 tests green, 29 routers, 32 modeles.

**Objectif**: Implementer un IAM complet:
- Users multi-org (user appartient a N organisations)
- 11 roles metier entreprise
- Scopes hierarchiques avec heritage: ORG → ENTITE → SITE
- Deny-by-default, last-owner protection, soft delete
- JWT + OAuth2
- Filtrage server-side des donnees
- UI login/profil/admin
- Seed demo "Groupe Atlas" avec 10 personas

**Contrainte**: 709 tests green + 0 breaking change + frontend build OK. Migration progressive.

---

## Stack technique

| Composant | Choix |
|-----------|-------|
| Auth backend | `python-jose[cryptography]` (JWT) + `passlib[bcrypt]` (hash) |
| Auth scheme | OAuth2PasswordBearer (FastAPI natif) |
| Token | JWT access token (30min), refresh via /api/auth/refresh |
| DB | Tables users, user_org_roles, user_scopes, audit_logs (SQLAlchemy/SQLite) |
| Frontend | AuthContext React, axios interceptors, RequireAuth guard |
| Mode demo | `PROMEOS_AUTH_ENABLED=false` → skip auth, comportement actuel |

---

## Schema de donnees

### Hierarchie existante

```
Organisation (1) → EntiteJuridique (1..*) → Portefeuille (1..*) → Site (1..*) → Compteur
```

### Nouveaux modeles IAM

```
User (1) →← UserOrgRole (N:M) → Organisation
                ↓
           UserScope (1..*) → scope_level (ORG|ENTITE|SITE) + scope_id
```

#### User
- id, email (unique), hashed_password, nom, prenom, actif, last_login
- TimestampMixin (created_at, updated_at)

#### UserOrgRole
- id, user_id (FK), org_id (FK), role (UserRole enum)
- UniqueConstraint(user_id, org_id) — un seul role par org
- TimestampMixin

#### UserScope
- id, user_org_role_id (FK), scope_level, scope_id, expires_at (nullable)
- Heritage: ORG scope → acces implicite a toutes entites/sites de l'org

#### AuditLog
- id, user_id, action, resource_type, resource_id, detail_json, ip_address, created_at

---

## 11 Roles metier

| Role | Code | View | Edit | Admin | Export |
|------|------|------|------|-------|--------|
| Direction Generale | dg_owner | ALL | ALL | oui | oui |
| DSI / Admin | dsi_admin | ALL | ALL | oui | oui |
| DAF | daf | cockpit, billing, purchase, actions, reports | billing, purchase | non | oui |
| Acheteur energie | acheteur | purchase, billing, actions | purchase | non | oui |
| Resp. conformite | resp_conformite | conformite, actions, reports | conformite, actions | non | oui |
| Energy Manager | energy_manager | ALL | conso, diagnostic, actions, monitoring | non | oui |
| Resp. immobilier | resp_immobilier | patrimoine, conso, actions | patrimoine | non | oui |
| Resp. site | resp_site | patrimoine, conso, conformite, actions | patrimoine | non | non |
| Prestataire GTB | prestataire | patrimoine, conso, monitoring | rien | non | non |
| Auditeur | auditeur | ALL | rien | non | oui |
| PMO / ACC | pmo_acc | ALL | actions | non | oui |

---

## Logique de scope hierarchique

```
Scope ORG (id=1) → acces a TOUS les sites de l'organisation 1
Scope ENTITE (id=3) → acces a tous les sites de l'entite juridique 3
Scope SITE (id=42) → acces uniquement au site 42
```

**Deny-by-default**: si aucun scope defini → aucun acces (0 sites visibles).

**Heritage**: un scope ORG inclut automatiquement toutes les entites, portefeuilles et sites.

**Prestataire**: scope avec `expires_at` — acces revoque automatiquement apres expiration.

---

## Endpoints API

### Auth (6 endpoints)

| Methode | Path | Description |
|---------|------|-------------|
| POST | /api/auth/login | Login email+password → JWT |
| POST | /api/auth/refresh | Refresh token |
| GET | /api/auth/me | Profil + role + scopes + permissions |
| POST | /api/auth/logout | Logout (client-side) |
| PUT | /api/auth/password | Changer password |
| POST | /api/auth/switch-org | Changer d'org → nouveau JWT |

### Admin Users (8 endpoints)

| Methode | Path | Description |
|---------|------|-------------|
| GET | /api/admin/users | Liste users de l'org |
| POST | /api/admin/users | Creer user + role + scope |
| GET | /api/admin/users/{id} | Detail user |
| PATCH | /api/admin/users/{id} | Modifier user |
| PUT | /api/admin/users/{id}/role | Changer role |
| PUT | /api/admin/users/{id}/scopes | Definir scopes |
| DELETE | /api/admin/users/{id} | Soft delete |
| GET | /api/admin/roles | Matrice roles/permissions |

---

## Fichiers impactes

### Nouveaux fichiers (8)
- `backend/models/iam.py` — User, UserOrgRole, UserScope, AuditLog
- `backend/services/iam_service.py` — auth, JWT, permissions, scopes
- `backend/middleware/auth.py` — OAuth2 scheme, optional auth
- `backend/routes/auth.py` — 6 endpoints auth
- `backend/routes/admin_users.py` — 8 endpoints admin
- `backend/tests/test_iam.py` — ~32 tests
- `frontend/src/contexts/AuthContext.jsx`
- `frontend/src/pages/LoginPage.jsx`
- `frontend/src/pages/AdminUsersPage.jsx`
- `frontend/src/components/RequireAuth.jsx`

### Fichiers modifies (17)
- `backend/models/enums.py` — +3 enums
- `backend/models/__init__.py` — register IAM
- `backend/routes/__init__.py` — register 2 routers
- `backend/main.py` — register 2 routers
- `backend/requirements.txt` — +3 packages
- `backend/routes/dashboard_2min.py` — scope filtering
- `backend/routes/actions.py` — scope filtering
- `backend/routes/notifications.py` — scope filtering
- `backend/routes/compliance.py` — scope filtering
- `backend/routes/billing.py` — scope filtering
- `backend/routes/sites.py` — scope filtering
- `backend/scripts/seed_data.py` — seed Groupe Atlas
- `frontend/src/services/api.js` — intercepteurs auth
- `frontend/src/App.jsx` — AuthProvider + routes
- `frontend/src/layout/AppShell.jsx` — UserMenu
- `frontend/src/layout/Sidebar.jsx` — permission filtering
- `frontend/src/contexts/ScopeContext.jsx` — auth-connected
- `frontend/src/layout/Breadcrumb.jsx` — admin labels
