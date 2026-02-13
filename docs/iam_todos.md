# PROMEOS IAM — TODO Priorise (Impact / Effort)

## Legende
- **Impact**: Prerequis, Critique, Haute, Moyenne
- **Effort**: XS (<30min), S (30min-1h), M (1-2h), L (2-4h)
- **Priorite**: P0 (bloquant), P1 (important), P2 (nice-to-have)

---

## P0 — Bloquant (must-have, ordre sequentiel)

| # | Tache | Impact | Effort | Dependances |
|---|-------|--------|--------|-------------|
| 1 | Enums IAM (UserRole, ScopeLevel, PermissionAction) | Prerequis | XS | — |
| 2 | Modeles IAM (User, UserOrgRole, UserScope, AuditLog) | Prerequis | S | #1 |
| 3 | Dependencies Python (jose, passlib, multipart) | Prerequis | XS | — |
| 4 | iam_service.py (hash, JWT, permissions, scopes) | Critique | M | #1, #2, #3 |
| 5 | Middleware auth (OAuth2 scheme, optional auth) | Critique | S | #4 |
| 6 | Routes /api/auth (login, me, refresh, logout, password, switch) | Critique | M | #4, #5 |
| 7 | Frontend AuthContext + API interceptors | Critique | S | #6 |
| 8 | LoginPage | Critique | S | #7 |
| 9 | RequireAuth + App.jsx integration | Critique | S | #7, #8 |
| 10 | QA regression (709 tests green + build OK) | Critique | S | all |

---

## P1 — Important (should-have, parallelisable apres P0)

| # | Tache | Impact | Effort | Dependances |
|---|-------|--------|--------|-------------|
| 11 | Routes /api/admin/users (8 endpoints CRUD) | Haute | M | #4, #5 |
| 12 | Filtrage server-side (6 routers critiques) | Haute | M | #4, #5 |
| 13 | AppShell UserMenu (nom, role, org, logout) | Haute | S | #7 |
| 14 | Sidebar permission filtering | Haute | S | #7 |
| 15 | ScopeContext connecte a l'auth (remplacer mocks) | Haute | M | #7 |
| 16 | Seed demo Groupe Atlas (10 personas, 6 sites) | Haute | M | #2, #4 |
| 17 | Tests IAM (~32 tests) | Haute | M | #4, #5, #6, #11 |

---

## P2 — Nice-to-have (can-wait)

| # | Tache | Impact | Effort | Dependances |
|---|-------|--------|--------|-------------|
| 18 | AdminUsersPage (frontend CRUD users/roles/scopes) | Moyenne | M | #11 |
| 19 | Breadcrumb labels (admin, login) | Basse | XS | #9 |
| 20 | Filtrage server-side (23 routers restants) | Moyenne | L | #12 |

---

## Ordre d'execution recommande

```
Phase 1 — Backend core (P0):
  #1 (enums) → #2 (models) → #3 (deps) → #4 (service)
  → #5 (middleware) → #6 (routes auth)

Phase 2 — Frontend core (P0):
  #7 (AuthContext) → #8 (LoginPage) → #9 (RequireAuth)

Phase 3 — Backend enrichissement (P1):
  #11 (admin routes) + #12 (scope filtering) + #16 (seed)
  → #17 (tests)

Phase 4 — Frontend enrichissement (P1):
  #13 (UserMenu) + #14 (Sidebar) + #15 (ScopeContext)

Phase 5 — Polish (P2):
  #18 (AdminUsersPage) + #19 (Breadcrumb) + #20 (autres routers)

Phase 6 — QA (#10):
  Tous les tests green + build OK
```

---

## Estimation totale

| Phase | Effort cumule |
|-------|--------------|
| Phase 1 (Backend P0) | ~XS+S+XS+M+S+M |
| Phase 2 (Frontend P0) | ~S+S+S |
| Phase 3 (Backend P1) | ~M+M+M+M |
| Phase 4 (Frontend P1) | ~S+S+M |
| Phase 5 (Polish P2) | ~M+XS+L |
| Phase 6 (QA) | ~S |
