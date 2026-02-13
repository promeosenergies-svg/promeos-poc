# PROMEOS IAM — Definition of Done Checklist

## Backend — Modeles & Enums
- [ ] 3 enums ajoutes: UserRole (11 values), ScopeLevel (3), PermissionAction (6)
- [ ] Modele User: email unique, hashed_password, actif, last_login, TimestampMixin
- [ ] Modele UserOrgRole: user_id + org_id unique, role enum
- [ ] Modele UserScope: scope_level + scope_id, expires_at nullable
- [ ] Modele AuditLog: user_id, action, resource_type, resource_id, detail_json
- [ ] Tous les modeles registered dans __init__.py

## Backend — Service IAM
- [ ] hash_password / verify_password (bcrypt via passlib)
- [ ] create_access_token / decode_token (JWT via python-jose)
- [ ] get_current_user dependency (FastAPI)
- [ ] get_current_user_role dependency
- [ ] get_scoped_site_ids: resolution hierarchique ORG→ENTITE→SITE
- [ ] check_permission: matrice role → modules
- [ ] require_permission: dependency factory
- [ ] create_user, assign_role, assign_scope, remove_role, soft_delete_user
- [ ] Protection last-owner (impossible supprimer dernier DG d'une org)

## Backend — Middleware
- [ ] OAuth2PasswordBearer scheme (auto_error=False)
- [ ] get_current_user_optional: retourne None si pas de token (mode demo)
- [ ] Env var PROMEOS_AUTH_ENABLED (default "false")

## Backend — Routes Auth (6 endpoints)
- [ ] POST /api/auth/login → JWT + user info + permissions
- [ ] POST /api/auth/refresh → nouveau token
- [ ] GET /api/auth/me → profil complet
- [ ] POST /api/auth/logout → ok (client-side)
- [ ] PUT /api/auth/password → change password
- [ ] POST /api/auth/switch-org → nouveau JWT pour autre org

## Backend — Routes Admin (8 endpoints)
- [ ] GET /api/admin/users → liste users de l'org
- [ ] POST /api/admin/users → creer user + role + scope
- [ ] GET /api/admin/users/{id} → detail
- [ ] PATCH /api/admin/users/{id} → modifier
- [ ] PUT /api/admin/users/{id}/role → changer role
- [ ] PUT /api/admin/users/{id}/scopes → definir scopes
- [ ] DELETE /api/admin/users/{id} → soft delete (last-owner protection)
- [ ] GET /api/admin/roles → matrice permissions

## Backend — Filtrage server-side
- [ ] dashboard_2min.py: filtre par org + site_ids du user
- [ ] actions.py: filtre par org + site_ids
- [ ] notifications.py: filtre par org
- [ ] compliance.py: filtre par site_ids
- [ ] billing.py: filtre par site_ids
- [ ] sites.py: filtre par scopes

## Backend — Seed demo
- [ ] Org "Groupe Atlas" creee
- [ ] 2 entites juridiques: Atlas IDF, Atlas Sud
- [ ] 3+ portefeuilles: IDF-Bureaux, IDF-Commerce, PACA, Occitanie(vide)
- [ ] 6 sites: Tour Atlas, Agence Republique, Data Center, Galerie, Campus, Entrepot
- [ ] 10 users crees avec passwords hashes
- [ ] Roles assignes (11 roles couverts)
- [ ] Scopes varies: ORG(tout), ENTITE(IDF), SITE(Tour Atlas), expire(prestataire)

## Backend — Tests
- [ ] ~32 tests IAM green (test_iam.py)
- [ ] 709+ tests existants toujours green (0 regression)
- [ ] Dependencies installees (jose, passlib, python-multipart)

## Frontend — Auth
- [ ] AuthContext: state user/org/role/token/permissions
- [ ] AuthContext: login(), logout(), switchOrg(), refreshToken()
- [ ] api.js: request interceptor (Bearer token)
- [ ] api.js: response interceptor (401 → /login)
- [ ] LoginPage: formulaire email + password + erreur
- [ ] RequireAuth: guard redirect /login si pas authentifie
- [ ] RequireAuth: 403 "Acces refuse" si pas la permission

## Frontend — Layout & Navigation
- [ ] App.jsx: AuthProvider wrapping, /login route publique
- [ ] AppShell: UserMenu (nom, role, org, switch org, logout)
- [ ] Sidebar: liens filtres par permissions du role
- [ ] ScopeContext: connecte a l'auth (API /me au lieu de mocks)
- [ ] AdminUsersPage: table users + CRUD role/scopes
- [ ] Breadcrumb: labels admin/login

## QA finale
- [ ] Frontend build OK (npx vite build)
- [ ] Login Sophie → voit tout (DG)
- [ ] Login Pierre → voit uniquement Tour Atlas (resp_site)
- [ ] Login Karim → prestataire lecture seule
- [ ] Login Emma → auditeur lecture seule, export OK
- [ ] Sans token → mode demo inchange (non-breaking)
