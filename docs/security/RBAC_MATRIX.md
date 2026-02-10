# RBAC MATRIX - PROMEOS POC
**Date**: 2026-02-09
**Status**: 🔴 **NOT IMPLEMENTED** - Design ready, code missing

---

## OVERVIEW

PROMEOS POC currently has **NO authentication or authorization**. All 37 API endpoints are PUBLIC.

This document defines the **target RBAC (Role-Based Access Control) model** for production deployment across all 3 briques:
- **Brique 1**: RegOps (Deterministic compliance + AI agents)
- **Brique 2**: Bill Intelligence (planned)
- **Brique 3**: Scénarios achat post-ARENH (planned)

---

## ROLE HIERARCHY

```
SUPERADMIN (platform-wide)
  ↓ can impersonate
ADMIN (org-level)
  ↓ can manage
MANAGER (portfolio/site-level)
  ↓ can assign tasks
USER (read + limited actions)
  ↓ subset of
VIEWER (read-only)
  ↓
PUBLIC (anonymous, specific endpoints only)
```

---

## ROLE DEFINITIONS

### 1. PUBLIC (Anonymous)

**Scope**: No authentication required
**Use Cases**: Public dashboards, marketing pages, API health checks

**Allowed Actions**:
- View public statistics (aggregated, no PII)
- Health check endpoints

**Data Access**: None (aggregated data only)

---

### 2. VIEWER (Read-Only User)

**Scope**: Organisation-specific read-only
**Use Cases**: External auditors, consultants, read-only stakeholders

**Allowed Actions**:
- View sites, batiments, compteurs (own org only)
- View compliance status (own org only)
- View dashboards, KPIs, charts
- View regulatory news (RegSourceEvents)
- Export reports (PDF, Excel)

**Data Access**:
- Sites: WHERE org_id = user.org_id
- No sensitive data (no financial details, no contracts)

**Restrictions**:
- ❌ Cannot upload evidence
- ❌ Cannot acknowledge alerts
- ❌ Cannot trigger recomputes
- ❌ Cannot run connectors/watchers

---

### 3. USER (Standard User)

**Scope**: Organisation-specific read-write on specific objects
**Use Cases**: Site managers, energy managers, operational staff

**Allowed Actions** (inherits VIEWER +):
- Acknowledge alerts
- Add notes/comments to sites, obligations
- Mark guidance as dismissed
- Upload evidence (for assigned sites only)
- View AI insights
- Request AI explanations (rate-limited)

**Data Access**:
- Sites: WHERE org_id = user.org_id AND (assigned_site_ids OR role_scope='all')
- Can see financial data (bills, costs)

**Restrictions**:
- ❌ Cannot delete data
- ❌ Cannot trigger bulk operations
- ❌ Cannot manage users
- ❌ Cannot validate compliance manually (needs MANAGER)

---

### 4. MANAGER (Portfolio/Site Manager)

**Scope**: Portfolio or site-level authority
**Use Cases**: Regional managers, facility managers, portfolio leads

**Allowed Actions** (inherits USER +):
- Create/update/delete sites, batiments (own portfolio)
- Upload evidence (any type)
- Validate compliance status
- Assign tasks/obligations to users
- Complete actions
- Trigger site-level recomputes
- Run connectors for assigned sites
- Review and tag regulatory events
- Approve AI recommendations
- Configure site-level settings

**Data Access**:
- Sites: WHERE portfolio_id IN (assigned_portfolios)
- Full financial data
- Consumption history

**Restrictions**:
- ❌ Cannot delete organisations, entities, portfolios
- ❌ Cannot manage users outside own portfolio
- ❌ Cannot trigger org-wide operations

---

### 5. ADMIN (Organisation Administrator)

**Scope**: Full organisation authority
**Use Cases**: Organisation energy director, compliance officer, C-level

**Allowed Actions** (inherits MANAGER +):
- Create/update/delete organisations, entities, portfolios
- Manage users (create, assign roles, deactivate)
- Trigger org-wide recomputes
- Run all connectors/watchers
- Configure AI settings (model, budget, rate limits)
- Manage RBAC policies
- View audit logs
- Configure alerting rules
- Approve/reject evidence
- Override compliance status (with audit trail)
- Access Brique 2 (Bill Intelligence) admin features
- Access Brique 3 (Procurement) admin features

**Data Access**:
- All data: WHERE org_id = admin.org_id
- Financial data, contracts, PII

**Restrictions**:
- ❌ Cannot access other organisations' data
- ❌ Cannot manage platform settings (SUPERADMIN only)

---

### 6. SUPERADMIN (Platform Administrator)

**Scope**: Cross-organisation platform authority
**Use Cases**: PROMEOS platform team, support engineers, SRE

**Allowed Actions** (inherits ADMIN +):
- Manage all organisations
- Impersonate any user (with audit trail)
- View system metrics, logs, traces
- Configure platform settings (CORS, rate limits, secrets)
- Manage connectors/watchers globally
- Toggle demo mode
- Run database migrations
- Access background job queue
- Purge stale data
- Manage feature flags

**Data Access**: ALL (cross-org)

**Audit Requirements**:
- All SUPERADMIN actions logged
- 2FA required
- Time-limited access tokens (max 8h)
- Impersonation requires justification + approval

---

## PERMISSION MATRIX - BRIQUE 1 (RegOps)

### API Routes

| Endpoint | PUBLIC | VIEWER | USER | MANAGER | ADMIN | SUPERADMIN |
|----------|--------|--------|------|---------|-------|------------|
| **COMPLIANCE (Legacy)** |
| GET /api/compliance/sites | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/compliance/site/{id}/assessment | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/compliance/site/{id}/validate | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/compliance/actions | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/compliance/actions/{id}/complete | ❌ | ❌ | ✅ Assigned | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/compliance/deadlines | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/compliance/gaps | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/compliance/evidence/upload | ❌ | ❌ | ✅ Assigned sites | ✅ Own portfolio | ✅ Own org | ✅ All |
| **SITES** |
| GET /api/sites | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/sites/{id} | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/sites | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| PUT /api/sites/{id} | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| DELETE /api/sites/{id} | ❌ | ❌ | ❌ | ❌ | ✅ Own org | ✅ All |
| GET /api/sites/{id}/stats | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| **REGOPS (NEW)** |
| GET /api/regops/site/{id} | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/regops/site/{id}/cached | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/regops/recompute (scope=site) | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/regops/recompute (scope=org) | ❌ | ❌ | ❌ | ❌ | ✅ Own org | ✅ All |
| GET /api/regops/dashboard | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| **CONNECTORS (NEW)** |
| GET /api/connectors/list | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /api/connectors/{name}/test | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/connectors/{name}/sync | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| **WATCHERS (NEW)** |
| GET /api/watchers/list | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /api/watchers/{name}/run | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| GET /api/watchers/events | ✅ (public feed) | ✅ | ✅ | ✅ | ✅ | ✅ |
| PATCH /api/watchers/events/{id}/review | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **AI AGENTS (NEW)** |
| GET /api/ai/site/{id}/explain | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/ai/site/{id}/recommend | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/ai/site/{id}/data-quality | ❌ | ❌ | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/ai/org/brief | ❌ | ❌ | ❌ | ❌ | ✅ Own org | ✅ All |
| GET /api/ai/insights | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| **COCKPIT** |
| GET /api/cockpit/overview | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/cockpit/alerts | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/cockpit/alerts/{id}/acknowledge | ❌ | ❌ | ✅ Assigned | ✅ Own portfolio | ✅ Own org | ✅ All |
| **DEMO MODE** |
| GET /api/demo/status | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /api/demo/toggle | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **GUIDANCE** |
| GET /api/guidance/next-steps | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/guidance/dismiss | ❌ | ❌ | ✅ Assigned | ✅ Own portfolio | ✅ Own org | ✅ All |

---

## PERMISSION MATRIX - BRIQUE 2 (Bill Intelligence - Planned)

| Endpoint | PUBLIC | VIEWER | USER | MANAGER | ADMIN | SUPERADMIN |
|----------|--------|--------|------|---------|-------|------------|
| POST /api/bills/upload | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/bills/site/{id} | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/bills/{id} | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/bills/{id}/anomalies | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/bills/{id}/validate | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/bills/analytics | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/bills/ocr | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/tariffs/reference | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Key Rules**:
- Bill upload = MANAGER+ (contains financial data)
- Anomaly detection visible to VIEWER+ (transparency)
- Validation requires MANAGER+ (financial approval)

---

## PERMISSION MATRIX - BRIQUE 3 (Scénarios Achat - Planned)

| Endpoint | PUBLIC | VIEWER | USER | MANAGER | ADMIN | SUPERADMIN |
|----------|--------|--------|------|---------|-------|------------|
| POST /api/procurement/scenarios | ❌ | ❌ | ❌ | ❌ | ✅ Own org | ✅ All |
| GET /api/procurement/scenarios | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/procurement/scenarios/{id}/options | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| GET /api/procurement/market-data | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /api/procurement/simulate | ❌ | ❌ | ❌ | ❌ | ✅ Own org | ✅ All |
| GET /api/procurement/analytics | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| POST /api/procurement/scenarios/{id}/execute | ❌ | ❌ | ❌ | ❌ | ✅ Own org | ✅ All |

**Key Rules**:
- Scenario creation = ADMIN only (strategic decision)
- Market data = PUBLIC (transparency, no PII)
- Simulation = ADMIN only (expensive compute)
- Execution = ADMIN only (triggers real procurement actions)

---

## UI PERMISSION MATRIX

### Frontend Pages

| Page | PUBLIC | VIEWER | USER | MANAGER | ADMIN | SUPERADMIN |
|------|--------|--------|------|---------|-------|------------|
| `/` (Home/Landing) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/dashboard` | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| `/cockpit` | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| `/sites` (list) | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| `/sites/:id` (detail) | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| `/sites/:id/edit` | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| `/sites/create` | ❌ | ❌ | ❌ | ✅ Own portfolio | ✅ Own org | ✅ All |
| `/regops/:id` | ❌ | ✅ Own org | ✅ Own org | ✅ Own portfolio | ✅ Own org | ✅ All |
| `/connectors` | ❌ | ✅ View only | ✅ View only | ✅ Test/Sync | ✅ Manage | ✅ Manage |
| `/watchers` | ❌ | ✅ View events | ✅ View events | ✅ Review | ✅ Run/Review | ✅ Manage |
| `/action-plan` | ❌ | ✅ View only | ✅ View only | ✅ Edit/Assign | ✅ Edit/Assign | ✅ All |
| `/bills` (Brique 2) | ❌ | ✅ View only | ✅ View only | ✅ Upload/Validate | ✅ Manage | ✅ All |
| `/procurement` (Brique 3) | ❌ | ❌ | ❌ | ✅ View scenarios | ✅ Create/Execute | ✅ All |
| `/admin/users` | ❌ | ❌ | ❌ | ❌ | ✅ Own org | ✅ All |
| `/admin/settings` | ❌ | ❌ | ❌ | ❌ | ✅ Own org | ✅ All |

### UI Components (Conditional Rendering)

| Component | Condition |
|-----------|-----------|
| "Upload Evidence" button | role >= USER AND (assigned_site OR role >= MANAGER) |
| "Validate Compliance" button | role >= MANAGER |
| "Delete Site" button | role >= ADMIN |
| "Run Connector" button | role >= MANAGER |
| "Trigger Recompute (org-wide)" button | role >= ADMIN |
| "Impersonate User" button | role == SUPERADMIN |
| AI "Request Explanation" button | role >= VIEWER (rate-limited per role) |
| "Execute Procurement Scenario" button | role >= ADMIN |

---

## DATA ISOLATION RULES

### Row-Level Security (Database)

**Principle**: Users can only access data within their organisation scope.

#### Organisation-Level Isolation (ADMIN role)

```sql
-- Sites accessible to ADMIN user
SELECT * FROM sites s
  JOIN portefeuilles p ON s.portefeuille_id = p.id
  JOIN entites_juridiques e ON p.entite_juridique_id = e.id
WHERE e.organisation_id = :user_org_id;
```

#### Portfolio-Level Isolation (MANAGER role)

```sql
-- Sites accessible to MANAGER user
SELECT * FROM sites s
WHERE s.portefeuille_id IN :user_assigned_portfolio_ids;
```

#### Site-Level Isolation (USER role)

```sql
-- Sites accessible to USER (if site-specific assignment)
SELECT * FROM sites s
WHERE s.id IN :user_assigned_site_ids
   OR s.portefeuille_id IN :user_assigned_portfolio_ids;
```

### ORM-Level Enforcement

**FastAPI Dependency**:
```python
def get_user_sites(db: Session, current_user: User) -> Query:
    """Return sites query scoped to user's permissions"""
    query = db.query(Site)

    if current_user.role == Role.SUPERADMIN:
        return query  # No filter - all sites

    if current_user.role == Role.ADMIN:
        # Org-level access
        return query.join(Portefeuille).join(EntiteJuridique).filter(
            EntiteJuridique.organisation_id == current_user.organisation_id
        )

    if current_user.role == Role.MANAGER:
        # Portfolio-level access
        return query.filter(
            Site.portefeuille_id.in_(current_user.assigned_portfolio_ids)
        )

    if current_user.role in [Role.USER, Role.VIEWER]:
        # Site-level or portfolio-level access
        return query.filter(
            or_(
                Site.id.in_(current_user.assigned_site_ids),
                Site.portefeuille_id.in_(current_user.assigned_portfolio_ids)
            )
        )

    # PUBLIC - no access
    return query.filter(False)
```

---

## RATE LIMITING BY ROLE

### AI Endpoints (Cost Control)

| Endpoint | VIEWER | USER | MANAGER | ADMIN | SUPERADMIN |
|----------|--------|------|---------|-------|------------|
| GET /api/ai/site/{id}/explain | 5/hour | 10/hour | 50/hour | 200/hour | Unlimited |
| GET /api/ai/site/{id}/recommend | 5/hour | 10/hour | 50/hour | 200/hour | Unlimited |
| GET /api/ai/org/brief | ❌ | ❌ | ❌ | 5/day | Unlimited |

### Write Endpoints (Abuse Prevention)

| Endpoint | USER | MANAGER | ADMIN | SUPERADMIN |
|----------|------|---------|-------|------------|
| POST /api/sites | ❌ | 10/hour | 50/hour | Unlimited |
| POST /api/compliance/evidence/upload | 20/hour | 100/hour | 500/hour | Unlimited |
| POST /api/regops/recompute | ❌ | 10/hour | 50/hour | Unlimited |
| POST /api/connectors/{name}/sync | ❌ | 5/hour | 20/hour | Unlimited |
| POST /api/watchers/{name}/run | ❌ | ❌ | 10/hour | Unlimited |

---

## AUDIT LOG REQUIREMENTS

### Logged Events

| Action | Severity | Retention | Alert |
|--------|----------|-----------|-------|
| Login (success/failure) | INFO | 1 year | 5 failures = alert |
| SUPERADMIN impersonation | CRITICAL | 5 years | Always alert |
| Site deletion | HIGH | 5 years | Always alert ADMIN |
| Compliance status override | HIGH | 5 years | Log + reason required |
| Evidence upload | MEDIUM | 2 years | - |
| Recompute (org-wide) | MEDIUM | 1 year | - |
| Connector sync | LOW | 90 days | - |
| AI query | LOW | 30 days | - |

### Audit Log Schema

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    impersonated_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)  # "site.delete", "regops.recompute"
    resource_type = Column(String(50), nullable=False)  # "site", "organisation"
    resource_id = Column(Integer, nullable=True)
    severity = Column(Enum(Severity), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String(500), nullable=True)
    request_payload = Column(Text, nullable=True)  # JSON
    response_status = Column(Integer, nullable=False)  # 200, 403, 500
    justification = Column(Text, nullable=True)  # Required for HIGH/CRITICAL actions
```

---

## AUTHENTICATION IMPLEMENTATION

### JWT-Based Auth

**Flow**:
1. User logs in → POST /api/auth/login (username, password)
2. Backend validates credentials
3. Backend returns JWT access token (15 min expiry) + refresh token (7 days)
4. Client stores tokens (httpOnly cookie or localStorage)
5. Client includes JWT in Authorization header: `Bearer <token>`
6. Backend validates JWT on each request

**JWT Payload**:
```json
{
  "sub": "user_id_123",
  "org_id": "org_456",
  "role": "MANAGER",
  "assigned_portfolio_ids": [1, 2, 3],
  "assigned_site_ids": [10, 20],
  "exp": 1738512000,
  "iat": 1738511100
}
```

**FastAPI Dependency**:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(min_role: Role):
    """Dependency factory for role-based access"""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role.value < min_role.value:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker
```

**Usage**:
```python
@router.post("/api/sites", dependencies=[Depends(require_role(Role.MANAGER))])
async def create_site(site: SiteCreate, current_user: User = Depends(get_current_user)):
    # current_user is guaranteed to be MANAGER or higher
    ...
```

---

## USER TABLE SCHEMA

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(Enum(Role), nullable=False, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    assigned_portfolio_ids = Column(JSON, nullable=True)  # [1, 2, 3] or NULL (all)
    assigned_site_ids = Column(JSON, nullable=True)  # [10, 20] or NULL
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
```

---

## IMPLEMENTATION ROADMAP

### Phase 1: Foundation (2 hours)

1. Add User model (10 min)
2. Add JWT auth dependency (30 min)
3. Add /api/auth/login, /auth/refresh, /auth/logout endpoints (30 min)
4. Add password hashing (bcrypt) (15 min)
5. Protect 5 critical endpoints (DELETE, recompute, connectors, watchers) (30 min)
6. Test auth flow (15 min)

### Phase 2: RBAC Core (4 hours)

1. Add require_role() dependency (30 min)
2. Add get_user_sites() scoping (1 hour)
3. Protect all 37 endpoints with role checks (2 hours)
4. Add UI conditional rendering (30 min)
5. Test role enforcement (1 hour)

### Phase 3: Audit & Security (2 hours)

1. Add AuditLog model (15 min)
2. Add audit logging middleware (30 min)
3. Add rate limiting (slowapi) (30 min)
4. Add CORS whitelist (15 min)
5. Add security headers (helmet equivalent) (15 min)
6. Add 2FA for SUPERADMIN (15 min)

### Phase 4: Advanced (4 hours)

1. Add org-level settings (AI budget, rate limits) (1 hour)
2. Add impersonation feature (SUPERADMIN) (1 hour)
3. Add session management (revoke all sessions) (30 min)
4. Add password reset flow (email) (1 hour)
5. Add OAuth2 integration (Google, Azure AD) (30 min)

**Total Effort**: 12 hours

---

## TESTING STRATEGY

### Unit Tests

```python
def test_viewer_cannot_delete_site():
    viewer_user = create_user(role=Role.VIEWER)
    response = client.delete("/api/sites/1", headers=auth_header(viewer_user))
    assert response.status_code == 403

def test_manager_can_only_access_own_portfolio():
    manager = create_user(role=Role.MANAGER, assigned_portfolio_ids=[1])
    response = client.get("/api/sites/999", headers=auth_header(manager))  # Site in portfolio 2
    assert response.status_code == 404  # Hidden, not 403

def test_admin_can_access_all_org_sites():
    admin = create_user(role=Role.ADMIN, organisation_id=1)
    response = client.get("/api/sites", headers=auth_header(admin))
    sites = response.json()
    assert all(s["organisation_id"] == 1 for s in sites)
```

### Integration Tests

- Test full auth flow (login → API call → logout)
- Test token expiry + refresh
- Test rate limiting (429 Too Many Requests)
- Test audit log creation
- Test impersonation (SUPERADMIN → ADMIN)

---

## SECURITY BEST PRACTICES

### Implemented

- ❌ None (no auth yet)

### Required

1. **Password Policy**:
   - Min 12 characters
   - Require uppercase, lowercase, digit, special char
   - Bcrypt with cost factor 12

2. **Token Security**:
   - Access token: 15 min expiry
   - Refresh token: 7 days expiry, rotate on use
   - Store refresh token in httpOnly cookie (not localStorage)
   - CSRF protection for cookie-based auth

3. **Rate Limiting**:
   - Global: 100 req/min per IP
   - Per-endpoint: see tables above
   - Exponential backoff on failures

4. **Headers**:
   - X-Frame-Options: DENY
   - X-Content-Type-Options: nosniff
   - X-XSS-Protection: 1; mode=block
   - Strict-Transport-Security: max-age=31536000

5. **CORS**:
   - Whitelist origins (no wildcard)
   - Credentials: true only for trusted origins

6. **Secrets**:
   - JWT secret: 256-bit random (in .env, not in code)
   - Rotate secrets quarterly
   - Use AWS Secrets Manager / Vault in prod

7. **2FA**:
   - Required for ADMIN, SUPERADMIN
   - TOTP-based (Google Authenticator compatible)

---

## NEXT STEPS

1. **Immediate** (Tonight):
   - Create User model
   - Implement JWT auth
   - Protect 5 critical endpoints (DELETE, recompute, sync, run, toggle-demo)

2. **Short Term** (This Week):
   - Full RBAC implementation (37 endpoints)
   - Audit logging
   - Rate limiting
   - UI conditional rendering

3. **Medium Term** (Before Production):
   - 2FA for ADMIN+
   - OAuth2 integration
   - Password reset flow
   - Comprehensive RBAC tests (50+ test cases)

---

**Status**: 🔴 **CRITICAL** - No auth = production blocker
**Priority**: P0 - Implement Phase 1 before any deployment
**Reference**: See API_MAP.md for endpoint security requirements
