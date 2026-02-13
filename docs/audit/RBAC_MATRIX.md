# RBAC MATRIX - PROMEOS POC

**Date**: 2026-02-13
**Implementation**: `services/iam_service.py` (ROLE_PERMISSIONS dict)

---

## 1. Roles (11 roles metier)

| # | Role | Code enum | Description |
|---|------|-----------|-------------|
| 1 | DG / Owner | `dg_owner` | Direction generale, acces total |
| 2 | DSI / Admin | `dsi_admin` | Direction SI, admin sans approbation |
| 3 | DAF | `daf` | Direction financiere |
| 4 | Acheteur | `acheteur` | Achat energie |
| 5 | Resp. Conformite | `resp_conformite` | Responsable conformite |
| 6 | Energy Manager | `energy_manager` | Gestionnaire energie |
| 7 | Resp. Immobilier | `resp_immobilier` | Responsable patrimoine |
| 8 | Resp. Site | `resp_site` | Responsable site local |
| 9 | Prestataire | `prestataire` | Prestataire externe (read-only) |
| 10 | Auditeur | `auditeur` | Auditeur (read-only + export) |
| 11 | PMO / ACC | `pmo_acc` | Accompagnement projet |

---

## 2. Matrice des permissions

| Permission | DG_OWNER | DSI_ADMIN | DAF | ACHETEUR | RESP_CONFORMITE | ENERGY_MANAGER | RESP_IMMOBILIER | RESP_SITE | PRESTATAIRE | AUDITEUR | PMO_ACC |
|------------|----------|-----------|-----|----------|-----------------|----------------|-----------------|-----------|-------------|----------|---------|
| **view** | ALL | ALL | cockpit, billing, purchase, actions, reports | purchase, billing, actions | conformite, actions, reports | ALL | patrimoine, conso, actions | patrimoine, conso, conformite, actions | patrimoine, conso, monitoring | ALL | ALL |
| **edit** | ALL | ALL | billing, purchase | purchase | conformite, actions | conso, diagnostic, actions, monitoring | patrimoine | patrimoine | - | - | actions |
| **admin** | Oui | Oui | - | - | - | - | - | - | - | - | - |
| **export** | Oui | Oui | Oui | Oui | Oui | Oui | Oui | - | - | Oui | Oui |
| **sync** | Oui | Oui | - | - | - | Oui | - | - | - | - | - |
| **approve** | Oui | - | - | - | - | - | - | - | - | - | - |

**ALL** = acces a tous les modules

---

## 3. Niveaux de scope hierarchique

| Niveau | Code | Description | Exemple |
|--------|------|-------------|---------|
| Organisation | `org` | Acces a toute l'organisation | Groupe Casino (tous les sites) |
| Entite | `entite` | Acces a une entite juridique | Filiale Sud-Est (sites de cette filiale) |
| Site | `site` | Acces a un site specifique | Bureau Lyon 1 (ce site uniquement) |

**Resolution**: La permission est verifiee en cascade:
- Scope ORG couvre tous les sites de l'organisation
- Scope ENTITE couvre les sites de l'entite et ses portefeuilles
- Scope SITE couvre uniquement le site specifie

---

## 4. Modeles IAM (4 tables dans iam.py)

### User (users)

| Colonne | Type | Description |
|---------|------|-------------|
| id | Integer PK | - |
| email | String(200) UNIQUE | Login |
| hashed_password | String(200) | Bcrypt hash |
| nom | String(100) | Nom de famille |
| prenom | String(100) | Prenom |
| is_active | Boolean | Compte actif |
| last_login | DateTime | Derniere connexion |
| created_at / updated_at | DateTime | Timestamps |

### UserOrgRole (user_org_roles)

| Colonne | Type | Description |
|---------|------|-------------|
| id | Integer PK | - |
| user_id | FK -> users.id | - |
| org_id | FK -> organisations.id | - |
| role | Enum(UserRole) | Role dans cette org |
| expires_at | DateTime | Expiration (prestataire) |

**Contrainte**: UNIQUE(user_id, org_id)

### UserScope (user_scopes)

| Colonne | Type | Description |
|---------|------|-------------|
| id | Integer PK | - |
| user_org_role_id | FK -> user_org_roles.id | - |
| scope_level | Enum(ScopeLevel) | ORG / ENTITE / SITE |
| scope_id | Integer | ID de l'entite/site cible |

### AuditLog (audit_logs)

| Colonne | Type | Description |
|---------|------|-------------|
| id | Integer PK | - |
| user_id | FK -> users.id | Qui |
| action | String(50) | Quoi (login, create_user, intake_apply...) |
| resource_type | String(50) | Sur quel type |
| resource_id | Integer | Sur quel ID |
| detail_json | Text | Details JSON |
| created_at | DateTime | Quand |

---

## 5. Authentification

| Aspect | Implementation |
|--------|---------------|
| Methode | JWT HS256 |
| Secret | `PROMEOS_JWT_SECRET` env var (fallback: `"dev-secret-change-me-in-prod"`) |
| Expiration | 30 minutes |
| Refresh | POST /api/auth/refresh |
| Payload | `{sub: user_id, org_id, role, exp, iat}` |
| Password hash | bcrypt |

---

## 6. Fonctions cles (iam_service.py)

| Fonction | Description |
|----------|-------------|
| `hash_password(plain)` | Bcrypt hash |
| `verify_password(plain, hashed)` | Bcrypt verify |
| `create_access_token(user_id, org_id, role)` | Generate JWT |
| `decode_token(token)` | Decode + validate JWT |
| `create_user(db, email, password, nom, prenom)` | Create user |
| `assign_role(db, user_id, org_id, role)` | Assign role to user-org |
| `assign_scope(db, user_org_role_id, scope_level, scope_id)` | Assign scope |
| `check_permission(role, action, module)` | Check ROLE_PERMISSIONS |
| `can(db, user_id, action, resource_type, resource_id)` | Full permission check (role + scope) |
| `get_accessible_site_ids(db, user_id, org_id)` | List sites user can access |
| `get_accessible_entity_ids(db, user_id, org_id)` | List entities user can access |

---

## 7. Pages frontend IAM

| Page | Route | Description |
|------|-------|-------------|
| LoginPage | /login | Connexion email + password |
| AdminUsersPage | /admin/users | CRUD utilisateurs |
| AdminRolesPage | /admin/roles | Liste roles + permissions |
| AdminAssignmentsPage | /admin/assignments | Assigner roles + scopes |
| AdminAuditLogPage | /admin/audit | Consulter logs d'audit |

---

## 8. Utilisateurs demo (seed_data.py)

| Email | Role | Org | Scope |
|-------|------|-----|-------|
| sophie@atlas.demo | DG_OWNER | Groupe Casino | ORG (tout) |
| marc@atlas.demo | DSI_ADMIN | Groupe Casino | ORG (tout) |
| claire@atlas.demo | DAF | Groupe Casino | ORG (tout) |
| julien@atlas.demo | ACHETEUR | Groupe Casino | ORG (tout) |
| nadia@atlas.demo | RESP_CONFORMITE | Groupe Casino | ORG (tout) |
| pierre@atlas.demo | ENERGY_MANAGER | Groupe Casino | ENTITE (1 filiale) |
| isabelle@atlas.demo | RESP_IMMOBILIER | Groupe Casino | ENTITE (1 filiale) |
| thomas@atlas.demo | RESP_SITE | Groupe Casino | SITE (1 site) |
| elena@atlas.demo | PRESTATAIRE | Groupe Casino | SITE (1 site) |
| yves@atlas.demo | AUDITEUR | Collectivite Azur | ORG (tout) |

**Password commun**: `demo2024`

**Superuser**: `promeos@promeos.io` / `13061984` (DG_OWNER sur les 2 orgs)
