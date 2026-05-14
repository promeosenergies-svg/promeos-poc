# BRIEF ADR-027 · Sécurité org-scoping Centre d'Action V4

> **Statut** : `Proposed` → à acter par Amine avant production L4
> **Version** : v0.1
> **Date** : 2026-05-14
> **Branche cible** : `claude/refonte-sol2`
> **Risque** : **P0 sécu** — fuites `/api/action-center/*` identifiées L1
> **Doctrine source** : `docs/doctrine/doctrine_v4_classement_priorisation.md` v0.2
> **ADR amont** : ADR-022 · ADR-025 · ADR-026
> **Auteurs** : Amine + Claude (cadrage session 2026-05-14)

---

## 0. TL;DR exécutif

**ADR-027 = manuel défensif Centre d'Action V4.** Risque P0 sécu identifié en L1 (fuites org-scoping `/api/action-center/*`) → ce document fige les invariants, le modèle de menace, la matrice IDOR, les patterns techniques et les outils CI pour rendre V4 **structurellement sûr** par construction.

**11 invariants sécurité non négociables** :

| # | Invariant |
|---|---|
| IS1 | Toutes les routes `/api/action-center/*` ont `@org_scoped` obligatoire |
| IS2 | Aucun endpoint sensible sans test cross-org (couverture 100%) |
| IS3 | Cross-org GET/PATCH/DELETE retourne **404** (pas 403, anti-énumération) |
| IS4 | Viewer sur mutation retourne **403** (read-only enforcement) |
| IS5 | Admin endpoint exige `role=admin` ET `token < 5min` |
| IS6 | Bandit + Semgrep + gitleaks + pip-audit **passent en CI** (gate bloquant) |
| IS7 | Logs sécurité **sans body, sans query string sensible, sans token** |
| IS8 | IP **anonymisée** (/24 mask IPv4, /48 IPv6) |
| IS9 | `correlation_id` **obligatoire** sur toutes les requêtes |
| IS10 | Backup/export **non commitables** : `.gitignore` + source-guard CI bloque |
| IS11 | Pas d'accès DB direct dans routes · pattern repository org-scopé obligatoire |

**7 arbitrages techniques Q26-Q32 actés** :

| Q | Décision finale |
|---|---|
| Q26-C | `org_id` direct + `jwt_version=v1` (future-proof multi-org V4.1+) |
| Q27-B+ | Middleware + `@org_scoped` + pattern repository (triple filet) |
| Q28-D | Hybride 401 si token invalide / 403 si org_id manquant |
| Q29-D | CI continu + audit pen-test J-7 Mois 4 + ad-hoc |
| Q30-A+ | Bandit + Semgrep + gitleaks + pip-audit + 50 source-guards |
| Q31-B+ | Tokens 1h/30j + cookies HttpOnly/Secure/SameSite |
| Q32-B | Structured events sanitizés + audit log dédié |

**Modèle de menace V4** : 8 vecteurs M1-M8 (IDOR, privilege escalation, injection, JWT replay, énumération, CSRF, logs leak, brute force).

**IDOR matrix exhaustive** : 12 endpoints × 3 rôles × 2 orgs × 4 cas = **288 cellules**.

---

## 1. Périmètre et hors-scope

### 1.1 Périmètre ADR-027

L'ADR couvre :

- Modèle de menace V4 complet (8 vecteurs M1-M8)
- Structure JWT v1 + future-proofing v2 (multi-org)
- Middleware FastAPI `OrgScopingMiddleware`
- Décorateur `@org_scoped` obligatoire (IS1)
- Pattern repository org-scopé (IS11)
- 50 source-guards CI custom
- IDOR matrix 288 cellules (structure + 12 exemples cardinaux)
- Procédure audit pen-test J-7 Mois 4 (OWASP top 10)
- Configurations CI : Bandit + Semgrep + gitleaks + pip-audit
- Politique cookies HttpOnly/Secure/SameSite
- Logs sécurité structurés + anonymisation IP
- Rate limiting endpoints sensibles
- Gestion incidents sécu post-cutover

### 1.2 Hors-scope ADR-027

- **ADR-025** : architecture V4 cible (déjà acté)
- **ADR-026** : migration data + backup (déjà acté)
- **ADR-028 Lifecycle states** : state machine
- **ADR-029 Evidence + audit trail** : rétention RGPD par event_type
- **Infrastructure** : WAF, DDoS protection, TLS config (ops layer)
- **Compliance ISO 27001 / SOC 2** : pas un objectif Mois 6 (V4.1+ si pilots externes)

---

## 2. Modèle de menace V4 — 8 vecteurs

| # | Menace | Description | Mitigation | Niveau |
|---|---|---|---|---|
| **M1** | **IDOR via id direct** | `GET /items/{id}` sans filter `organisation_id` → user peut lire items d'autres orgs | Décorateur `@org_scoped` + filter SQL obligatoire (IS1) + pattern repository (IS11) | **P0** |
| **M2** | **Privilege escalation** | User → admin via endpoint `/correct-kind` ou `/bulk-update` | Vérification `role=admin` obligatoire + token < 5min (IS5) | **P0** |
| **M3** | **Injection SQL** | Raw SQL avec interpolation user input | Bandit CI + reviews + ORM uniquement | P1 |
| **M4** | **JWT replay** | Token volé réutilisé après revocation | Rotation 1h + refresh 30j + revocation list (IS5) | P1 |
| **M5** | **Énumération via 403/404 différenciés** | Attacker peut deviner si `item_id` existe dans autre org | Toujours **404** pour cross-org (IS3) | P1 |
| **M6** | **CSRF sur mutations** | Site malveillant force POST/PATCH sur PROMEOS | SameSite=Strict cookies + CSRF token + Origin check | P2 |
| **M7** | **Logs leak PII** | Body, query string, token en clair dans logs → fuite RGPD | Structured events sanitizés + sans body/token (IS7) + IP anonymisée (IS8) | **P1 (RGPD)** |
| **M8** | **Brute force endpoints sensibles** | `/correct-kind`, `/login` flood | Rate limiting 10 req/min sur endpoints sensibles | P2 |

---

## 3. Structure JWT v1 (Q26-C)

### 3.1 Payload cardinal

```json
{
  "sub": "user-uuid-v4",
  "org_id": "org-helios-uuid-v4",
  "role": "user",
  "jwt_version": "v1",
  "iat": 1748000000,
  "exp": 1748003600,
  "session_id": "session-uuid-v4"
}
```

**Champs obligatoires** :

| Champ | Type | Description |
|---|---|---|
| `sub` | UUID | Subject = user_id |
| `org_id` | UUID | Organisation_id cardinale (Q26-C single-org Mois 2-6) |
| `role` | enum | `admin` \| `user` \| `viewer` |
| `jwt_version` | string | `v1` Mois 2-6 (single-org), `v2` future multi-org |
| `iat` | int | Issued at (UTC timestamp) |
| `exp` | int | Expiration (1h après iat pour access token) |
| `session_id` | UUID | Pour revocation list (logout, password reset) |

### 3.2 Future-proofing v2 (Q26-C)

```json
{
  "jwt_version": "v2",
  "sub": "user-uuid",
  "organisations": [
    {"id": "org-a-uuid", "role": "user"},
    {"id": "org-b-uuid", "role": "viewer"}
  ],
  "active_org_id": "org-a-uuid"
}
```

**Migration v1 → v2** prévue V4.1+ si demande multi-org émerge :

```python
# backend/auth/jwt_extractor.py
def extract_org_id(token: dict, request: Request) -> UUID:
    version = token.get("jwt_version", "v1")
    if version == "v1":
        return UUID(token["org_id"])
    elif version == "v2":
        return extract_org_id_multi(token, request)
    else:
        raise HTTPException(401, "Unsupported JWT version")
```

### 3.3 Rotation tokens (Q31-B+)

| Token type | Durée | Cookie SameSite | Path |
|---|---|---|---|
| Access token | **1h** | Strict | `/` |
| Refresh token | **30j** | Strict | `/auth/refresh` |
| CSRF token | **1h** | Lax | `/` |
| Admin endpoint | **5min** | (header explicite) | n/a |

**Cookies obligatoires (IS7)** :
- `HttpOnly` : pas d'accès JS (anti-XSS)
- `Secure` : HTTPS only (anti-MITM)
- `SameSite=Strict` (Lax pour CSRF token)

---

## 4. Middleware FastAPI `OrgScopingMiddleware`

```python
# backend/middleware/org_scoping.py

from fastapi import Request, HTTPException
from uuid import UUID, uuid4

class OrgScopingMiddleware:
    """
    Middleware global. Extrait org_id du JWT, l'injecte dans request.state.
    Invariants : IS1 (org_scoping natif), IS8 (IP anonymisée), IS9 (correlation_id)
    """

    async def __call__(self, request: Request, call_next):
        # IS9 : correlation_id obligatoire
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        request.state.correlation_id = correlation_id

        # IS8 : IP anonymisée
        request.state.client_ip = anonymize_ip(request.client.host)

        # Authentification + extraction org
        token = extract_jwt_from_cookie_or_header(request)
        if not token:
            return JSONResponse(
                status_code=401,
                content={
                    "code": "AUTH_TOKEN_MISSING",
                    "message": "Authentication required",
                    "hint": "Provide a valid access token",
                    "correlation_id": correlation_id
                }
            )

        try:
            payload = verify_jwt(token)
        except JWTError as e:
            return JSONResponse(
                status_code=401,
                content={
                    "code": "AUTH_TOKEN_INVALID",
                    "message": str(e),
                    "hint": "Re-authenticate to get a fresh token",
                    "correlation_id": correlation_id
                }
            )

        try:
            org_id = extract_org_id(payload, request)
        except ValueError:
            return JSONResponse(
                status_code=403,
                content={
                    "code": "ORG_SCOPING_MISSING",
                    "message": "Missing or invalid organisation context",
                    "hint": "Verify your JWT payload contains org_id claim",
                    "correlation_id": correlation_id
                }
            )

        request.state.user_id = UUID(payload["sub"])
        request.state.organisation_id = org_id
        request.state.role = payload["role"]
        request.state.session_id = UUID(payload["session_id"])
        request.state.token_iat = payload["iat"]

        log_security_event(
            event_type="request.entry",
            request=request,
            user_id=request.state.user_id,
            org_id=request.state.organisation_id,
        )

        response = await call_next(request)

        log_security_event(
            event_type="request.exit",
            request=request,
            status_code=response.status_code,
        )

        return response


def anonymize_ip(ip: str) -> str:
    """
    IS8 : anonymisation IP RGPD CNIL.
    IPv4 : /24 mask (XXX.YYY.ZZZ.0)
    IPv6 : /48 mask (XXXX:YYYY:ZZZZ::)
    """
    import ipaddress
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv4Address):
        return str(ipaddress.IPv4Network(f"{ip}/24", strict=False).network_address)
    else:
        return str(ipaddress.IPv6Network(f"{ip}/48", strict=False).network_address)
```

---

## 5. Décorateur `@org_scoped` (IS1)

```python
# backend/decorators/org_scoped.py
from functools import wraps
from fastapi import Request, HTTPException
import time

def org_scoped(allowed_roles: list[str] = ["admin", "user", "viewer"]):
    """Décorateur obligatoire sur toutes les routes /api/action-center/*."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = next((a for a in args if isinstance(a, Request)), None)
            if not request:
                raise HTTPException(500, "Request not injected")

            if not hasattr(request.state, 'organisation_id'):
                raise HTTPException(500, "OrgScopingMiddleware missing")

            user_role = request.state.role
            if user_role not in allowed_roles:
                if "admin" in allowed_roles and user_role != "admin":
                    log_security_event(
                        event_type="privilege.escalation.attempt",
                        request=request,
                        severity="warning",
                    )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "ROLE_FORBIDDEN",
                        "message": f"Role '{user_role}' not allowed",
                        "correlation_id": request.state.correlation_id
                    }
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def admin_only_with_fresh_token(func):
    """Helper IS5 : admin + token < 5min."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = next((a for a in args if isinstance(a, Request)), None)
        if request.state.role != "admin":
            raise HTTPException(403, ...)
        token_age = int(time.time()) - request.state.token_iat
        if token_age > 300:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "TOKEN_TOO_OLD_FOR_ADMIN",
                    "message": "Re-authenticate to perform admin actions",
                    "correlation_id": request.state.correlation_id
                }
            )
        return await func(*args, **kwargs)
    return wrapper
```

### 5.1 Usage attendu

```python
# Read endpoint (tous rôles)
@router.get("/api/action-center/items/{id}")
@org_scoped()
async def get_item(id: UUID, request: Request, repo: ActionCenterRepository = Depends(...)):
    return repo.get_by_id(id, organisation_id=request.state.organisation_id)

# Mutation endpoint (admin + user · IS4 viewer → 403)
@router.patch("/api/action-center/items/{id}/lifecycle")
@org_scoped(allowed_roles=["admin", "user"])
async def patch_lifecycle(...):
    ...

# Admin-only endpoint (IS5)
@router.patch("/api/action-center/items/{id}/correct-kind")
@admin_only_with_fresh_token
async def correct_kind(...):
    ...
```

---

## 6. Pattern repository org-scopé (IS11)

```python
# backend/repositories/action_center.py
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

class ActionCenterRepository:
    """Repository org-scopé. IS11 : aucune query sans organisation_id."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        id: UUID,
        organisation_id: UUID,  # ← obligatoire
    ) -> Optional[ActionCenterItem]:
        return self.db.query(ActionCenterItem).filter(
            ActionCenterItem.id == id,
            ActionCenterItem.organisation_id == organisation_id,
        ).first()

    def list_p0_p1_active(
        self,
        organisation_id: UUID,
        limit: int = 8,
    ) -> list[ActionCenterItem]:
        return self.db.query(ActionCenterItem).filter(
            ActionCenterItem.organisation_id == organisation_id,
            ActionCenterItem.priority_bracket.in_(["P0", "P1"]),
            ActionCenterItem.lifecycle_state != "closed",
        ).order_by(
            ActionCenterItem.priority_score.desc()
        ).limit(limit).all()

    def patch_lifecycle(
        self,
        id: UUID,
        organisation_id: UUID,
        new_state: str,
        actor_id: UUID,
    ) -> ActionCenterItem:
        item = self.get_by_id(id, organisation_id)
        if not item:
            # IS3 : 404 pour cross-org (anti-énumération)
            raise HTTPException(404, "Item not found")
        return item

# 7 autres repositories suivront le même pattern :
# EvidenceRepository, ActionEventLogRepository, ActionLinkRepository,
# ActionBlockerRepository, ActionScenarioRepository,
# DuplicateGroupRepository, RecurrenceGroupRepository
```

### 6.1 Anti-pattern interdit

```python
# ❌ INTERDIT — accès DB direct dans la route
@router.get("/api/action-center/items/{id}")
@org_scoped()
async def get_item(id: UUID, request: Request, db: Session = Depends(get_db)):
    return db.query(ActionCenterItem).filter(...).first()
    # ↑ pas de garantie organisation_id, faille IDOR possible

# ✅ OBLIGATOIRE — passage par repository
@router.get("/api/action-center/items/{id}")
@org_scoped()
async def get_item(id: UUID, request: Request, repo: ActionCenterRepository = Depends(get_repo)):
    return repo.get_by_id(id, organisation_id=request.state.organisation_id)
```

---

## 7. IDOR Matrix exhaustive — 288 cellules

### 7.1 Structure

```
ROUTES (12) × ROLES (3) × ORGS (2) × CAS (4) = 288 cellules

Routes Centre d'action V4 :
1.  GET    /api/action-center/pilotage
2.  GET    /api/action-center/items/{id}
3.  POST   /api/action-center/items
4.  PATCH  /api/action-center/items/{id}/lifecycle
5.  PATCH  /api/action-center/items/{id}/owner
6.  PATCH  /api/action-center/items/{id}/blockers
7.  POST   /api/action-center/items/{id}/close
8.  PATCH  /api/action-center/items/{id}/correct-kind  (admin only)
9.  GET    /api/action-center/items/{id}/audit-trail
10. GET    /api/action-center/impact
11. POST   /api/action-center/items/{id}/evidence
12. POST   /api/action-center/items/{id}/scenarios/{scenario_id}/select

Rôles : admin, user, viewer
Orgs  : org_helios, org_meridian (cross-org test)
Cas   : GET own, GET other, MUTATE own, MUTATE other
```

### 7.2 Exemples cardinaux (12 sur 288)

```
Route 2 · GET /api/action-center/items/{id}
─────────────────────────────────────────────
admin/helios   own (item_helios)     → 200
admin/helios   other (item_meridian) → 404 (IS3 anti-énumération)
user/helios    own                   → 200
user/helios    other                 → 404 (IS3)
viewer/helios  own                   → 200 (read OK)
viewer/helios  other                 → 404

Route 4 · PATCH /api/action-center/items/{id}/lifecycle
─────────────────────────────────────────────
admin/helios   own                   → 200
admin/helios   other                 → 404 (IS3)
user/helios    own                   → 200
user/helios    other                 → 404
viewer/helios  own                   → 403 (IS4 viewer no mutation)
viewer/helios  other                 → 404 (IS3 prime, jamais 403)

Route 8 · PATCH /api/action-center/items/{id}/correct-kind (ADMIN)
─────────────────────────────────────────────
admin/helios   own (token < 5min)    → 200
admin/helios   own (token > 5min)    → 403 (IS5 fresh token)
admin/helios   other                 → 404 (IS3)
user/helios    own                   → 403 (IS5 admin only)
viewer/helios  own                   → 403 (IS5)
```

### 7.3 Génération automatique des tests

```python
# tests/contract/test_idor_matrix.py
import pytest

ROUTES = [
    ("GET", "/api/action-center/pilotage", "list"),
    ("GET", "/api/action-center/items/{id}", "read_one"),
    # ... 12 routes
]
ROLES = ["admin", "user", "viewer"]
ORGS = ["helios", "meridian"]
CASES = ["own", "other"]

@pytest.mark.parametrize("method,route,kind", ROUTES)
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("user_org", ORGS)
@pytest.mark.parametrize("case", CASES)
def test_idor_matrix(method, route, kind, role, user_org, case):
    expected = lookup_idor_matrix(route, role, user_org, case)
    actual = make_request(method, route, role, user_org, case)
    assert actual.status_code == expected["status_code"]
    assert actual.json().get("code") == expected.get("error_code")
```

Total tests générés : **288** (un par cellule).

---

## 8. 50 source-guards CI custom

### 8.1 Catégorisation (50 SG cardinaux)

```
A · Org-scoping (15 SG)
  - test_all_aci_queries_have_org_scoping
  - test_all_evidences_queries_have_org_scoping
  - test_all_routes_have_org_scoped_decorator
  - test_no_direct_db_query_in_action_center_routes  (IS11)
  - test_repositories_take_org_id_required_param
  - ... 10 autres

B · IDOR prevention (10 SG)
  - test_cross_org_returns_404_not_403  (IS3)
  - test_viewer_mutations_return_403  (IS4)
  - test_admin_endpoints_check_fresh_token  (IS5)
  - test_no_id_enumeration_in_error_messages
  - ... 6 autres

C · Logs sanitization (8 SG)
  - test_logs_no_body  (IS7)
  - test_logs_no_query_string_sensitive  (IS7)
  - test_logs_no_token
  - test_logs_anonymize_ip  (IS8)
  - test_logs_have_correlation_id  (IS9)
  - ... 3 autres

D · Backup safety (5 SG)
  - test_gitignore_excludes_backups  (IS10)
  - test_no_backup_files_in_git
  - test_receipt_has_no_pii
  - ... 2 autres

E · JWT + Cookies (7 SG)
  - test_jwt_version_v1_or_v2_only
  - test_cookies_httponly  (Q31-B+)
  - test_cookies_secure
  - test_cookies_samesite_strict_or_lax
  - ... 3 autres

F · Patterns interdits (5 SG)
  - test_no_eval_in_codebase
  - test_no_raw_sql_in_action_center
  - test_no_print_statements (use logging)
  - ... 2 autres
```

### 8.2 Exemples cardinaux

```python
# tests/source_guards/test_no_direct_db_in_routes.py
def test_routes_use_repositories_not_db_directly():
    """IS11 : pas d'accès DB direct dans routes /api/action-center/*."""
    for route_file in Path("backend/api/action_center").glob("*.py"):
        content = route_file.read_text()
        forbidden_patterns = [
            r'db\.query\(',
            r'session\.execute\(',
            r'cursor\.execute\(',
        ]
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, content)
            assert not matches, f"Direct DB access in {route_file}: {pattern}"


# tests/source_guards/test_all_routes_have_org_scoped.py
def test_all_action_center_routes_have_org_scoped_decorator():
    """IS1 : toutes les routes /api/action-center/* ont @org_scoped."""
    for route_file in Path("backend/api/action_center").glob("*.py"):
        content = route_file.read_text()
        routes = re.findall(r'@router\.(get|post|patch|delete|put)', content)
        org_scoped = re.findall(r'@org_scoped|@admin_only_with_fresh_token', content)
        assert len(org_scoped) >= len(routes), (
            f"{route_file}: {len(routes)} routes but only {len(org_scoped)} org_scoped"
        )


# tests/source_guards/test_logs_no_pii.py
def test_logs_no_token_or_body():
    """IS7 : logs ne contiennent ni token ni body."""
    log_calls = grep_in_codebase(r'log_security_event\(.*\)')
    for call in log_calls:
        assert "body=" not in call
        assert "token=" not in call
        assert "query_string=" not in call


# tests/source_guards/test_gitignore_excludes_backups.py
def test_gitignore_blocks_backups():
    """IS10 : .gitignore exclut backups."""
    gitignore = Path(".gitignore").read_text()
    required = ["/backups/", "*.backup", "*.sql", "**/legacy_json/"]
    for pattern in required:
        assert pattern in gitignore, f"Missing in .gitignore: {pattern}"
```

---

## 9. CI Security workflow (Q30-A+)

```yaml
# .github/workflows/security.yml
name: Security CI

on:
  push:
    branches: [claude/refonte-sol2, main]
  pull_request:
    branches: [claude/refonte-sol2, main]

jobs:
  bandit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install bandit
      - name: Bandit SAST
        run: bandit -r backend/ -lll -ii -f json -o bandit-report.json

  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: |
            p/security-audit
            p/owasp-top-ten
            .semgrep/promeos-custom.yml

  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install pip-audit
      - name: Audit dependencies
        run: pip-audit --strict --desc -r requirements.txt

  source-guards:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - name: Run 50 source-guards
        run: pytest tests/source_guards/ -v --tb=short

  idor-matrix:
    runs-on: ubuntu-latest
    needs: [bandit, semgrep, source-guards]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - name: IDOR Matrix 288 tests
        run: pytest tests/contract/test_idor_matrix.py -v
```

**Tous bloquants** : un fail = PR refusée.

---

## 10. Logs sécurité structurés (Q32-B)

```python
# backend/logging/security.py
import structlog

logger = structlog.get_logger("security")

def log_security_event(
    event_type: str,
    request: Request,
    severity: str = "info",
    **extra,
):
    """
    Log structured security event.
    Invariants :
    - IS7 : pas de body, query string sensible, token
    - IS8 : IP anonymisée
    - IS9 : correlation_id obligatoire
    """
    safe_payload = {
        "event_type": event_type,
        "severity": severity,
        "correlation_id": request.state.correlation_id,
        "user_id": getattr(request.state, "user_id", None),
        "org_id": getattr(request.state, "organisation_id", None),
        "role": getattr(request.state, "role", None),
        "route": request.url.path,
        "method": request.method,
        "ip_anonymized": getattr(request.state, "client_ip", None),
        "user_agent_short": request.headers.get("user-agent", "")[:80],
        # ⚠ JAMAIS :
        #   - body, query_string brut, cookies, authorization header
        **extra,
    }

    if severity == "error":
        logger.error("security.event", **safe_payload)
    elif severity == "warning":
        logger.warning("security.event", **safe_payload)
    else:
        logger.info("security.event", **safe_payload)
```

### 10.1 Table dédiée `security_audit_log`

Séparée de `action_event_log` métier (RGPD : rétentions distinctes).

```sql
CREATE TABLE security_audit_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  event_type      VARCHAR(60) NOT NULL,
  severity        VARCHAR(20) NOT NULL,
  user_id         UUID,
  organisation_id UUID,
  role            VARCHAR(20),
  route           TEXT,
  method          VARCHAR(10),
  ip_anonymized   VARCHAR(50),
  user_agent_short VARCHAR(80),
  correlation_id  UUID NOT NULL,
  extra_payload   JSONB
);

CREATE INDEX idx_security_log_org ON security_audit_log(organisation_id, occurred_at DESC);
CREATE INDEX idx_security_log_user ON security_audit_log(user_id, occurred_at DESC);
CREATE INDEX idx_security_log_correlation ON security_audit_log(correlation_id);
```

Rétention : 90 jours (RGPD logs sécurité, vs 5 ans pour audit métier).

---

## 11. Procédure audit pen-test J-7 Mois 4 (Q29-D)

### 11.1 Checklist OWASP Top 10

```markdown
## Audit pen-test J-7 Mois 4 — Checklist

### A01 Broken Access Control (IDOR)
- [ ] Run IDOR matrix 288 tests : 100% pass
- [ ] Manual test : forge `X-Organisation-Id` header → 403/404
- [ ] Manual test : tampered JWT → 401

### A02 Cryptographic Failures
- [ ] JWT secret rotation procedure documented
- [ ] Cookies all HttpOnly + Secure + SameSite

### A03 Injection
- [ ] Bandit SAST : 0 high severity findings
- [ ] No raw SQL in /api/action-center/* (source-guard pass)

### A04 Insecure Design
- [ ] All routes have @org_scoped (CI gate pass)
- [ ] Repository pattern enforced (IS11)

### A05 Security Misconfiguration
- [ ] CORS configured strictly
- [ ] No default credentials
- [ ] No verbose error messages (stack traces)

### A06 Vulnerable Components
- [ ] pip-audit : 0 high CVE
- [ ] gitleaks : 0 secrets detected

### A07 Authentication Failures
- [ ] Brute force test on /login → rate limit triggers
- [ ] Token expiration enforced (1h verified)
- [ ] Refresh token revocation works

### A08 Software / Data Integrity
- [ ] Cutover backup checksums verified (cf. ADR-026 I5)
- [ ] No backup files in Git (CI source-guard)

### A09 Security Logging Failures
- [ ] Security audit log captures all auth attempts
- [ ] IP anonymized (IS8 verified)
- [ ] No PII in logs (IS7 verified)

### A10 Server-Side Request Forgery
- [ ] No user-controlled URL fetching
```

### 11.2 Output audit

```
/audits/pen_test_J-7_<TIMESTAMP>.md
├── Findings résumés (par criticité)
├── 288 IDOR tests results
├── Bandit + Semgrep + gitleaks + pip-audit reports
├── Verdict GO/NO-GO cutover
└── Plan correctifs si NO-GO
```

---

## 12. Rate limiting endpoints sensibles (M8)

```python
# backend/middleware/rate_limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/api/auth/login")
@limiter.limit("10/minute")
async def login(...): ...

@router.patch("/api/action-center/items/{id}/correct-kind")
@limiter.limit("5/minute")
@admin_only_with_fresh_token
async def correct_kind(...): ...

@router.post("/api/action-center/items/{id}/close")
@limiter.limit("30/minute")
@org_scoped(allowed_roles=["admin", "user"])
async def close_item(...): ...
```

---

## 13. Gestion incidents sécu post-cutover

```markdown
## Procédure incident sécu

1. **Détection** : logs sécurité montrent pattern suspect (IDOR tentatives, brute force, etc.)
2. **Triage P0/P1/P2** :
   - P0 : exploit confirmé en cours
   - P1 : tentative répétée (>10 events/min)
   - P2 : pattern isolé suspect
3. **Réponse P0** :
   - Revocation list : invalider tous tokens de la session compromise
   - Audit log dump pour analyse
   - Communication interne sous 1h
4. **Réponse P1** :
   - Rate limiting renforcé sur IP source
   - Investigation logs sur 24h
5. **Réponse P2** :
   - Tag pour review hebdo
6. **Post-mortem obligatoire** pour P0 + P1
```

---

## 14. Renvois ADR amont/aval

- **ADR-022** : composantes priorité (héritée)
- **ADR-025** : architecture V4 (§7 hybride middleware + SG + décorateur)
- **ADR-026** : invariant I9 backup hors Git → IS10 source-guard
- **ADR-028 Lifecycle states** : transitions sensibles (close, reopen, correct-kind)
- **ADR-029 Evidence + audit trail** : rétention logs sécurité 90j vs métier 5 ans

---

## 15. Critères de validation finale ADR-027

### 15.1 11 invariants vérifiés

- [ ] **IS1** Toutes les routes `/api/action-center/*` ont `@org_scoped` → §5 + source-guard
- [ ] **IS2** Aucun endpoint sensible sans test cross-org → IDOR matrix 288 cellules
- [ ] **IS3** Cross-org GET/PATCH/DELETE retourne 404 → §7 + tests
- [ ] **IS4** Viewer sur mutation retourne 403 → §5.1 + IDOR matrix
- [ ] **IS5** Admin endpoint exige `role=admin` ET `token < 5min` → §5
- [ ] **IS6** Bandit + Semgrep + gitleaks + pip-audit passent en CI → §9
- [ ] **IS7** Logs sans body, sans query string sensible, sans token → §10
- [ ] **IS8** IP anonymisée /24 IPv4 /48 IPv6 → §4
- [ ] **IS9** `correlation_id` obligatoire → §4 + §10
- [ ] **IS10** Backup/export non commitables : `.gitignore` + source-guard → §8.1
- [ ] **IS11** Pas d'accès DB direct dans routes · pattern repository → §6

### 15.2 Cohérence cross-documents

- [ ] Cohérence ADR-025 (architecture cible)
- [ ] Cohérence ADR-026 (I9 backup hors Git → IS10)
- [ ] Cohérence doctrine v0.2 (mode standard / audit, libellés FR)
- [ ] Cohérence L1 (fuites `/api/action-center/*` P0 mitigées)

### 15.3 Conformité Q6-A

- [ ] Aucun code Python/TypeScript modifié
- [ ] Aucune table DB modifiée
- [ ] Aucun script créé sur disque (documentés DANS l'ADR uniquement)

---

## 16. Métadonnées ADR

```yaml
adr_number: 027
title: Sécurité org-scoping Centre d'Action V4
version: v0.1
status: Proposed
date: 2026-05-14
authors:
  - Amine (PROMEOS founder)
  - Claude (security co-pilot)
arbitrages_q26_q32:
  Q26: C   # org_id direct + jwt_version=v1
  Q27: B+  # middleware + décorateur + repository pattern
  Q28: D   # hybride 401/403
  Q29: D   # CI continu + pen-test J-7 + ad-hoc
  Q30: A+  # Bandit + Semgrep + gitleaks + pip-audit + 50 SG
  Q31: B+  # tokens 1h/30j + cookies HttpOnly/Secure/SameSite
  Q32: B   # structured events sanitizés + audit log dédié
invariants_securite:
  IS1: "Routes /api/action-center/* ont @org_scoped obligatoire"
  IS2: "Aucun endpoint sensible sans test cross-org"
  IS3: "Cross-org → 404 (anti-énumération)"
  IS4: "Viewer mutation → 403"
  IS5: "Admin endpoint: role=admin + token < 5min"
  IS6: "Bandit + Semgrep + gitleaks + pip-audit en CI gate"
  IS7: "Logs sans body/query/token"
  IS8: "IP anonymisée /24 /48"
  IS9: "correlation_id obligatoire"
  IS10: "Backup/export non commitables (.gitignore + SG)"
  IS11: "Pas d'accès DB direct · pattern repository"
threat_model:
  M1: "IDOR via id direct (P0)"
  M2: "Privilege escalation (P0)"
  M3: "Injection SQL (P1)"
  M4: "JWT replay (P1)"
  M5: "Énumération 403/404 différenciés (P1)"
  M6: "CSRF mutations (P2)"
  M7: "Logs leak PII (P1 RGPD)"
  M8: "Brute force endpoints sensibles (P2)"
idor_matrix:
  total_cells: 288
  routes: 12
  roles: 3
  orgs: 2
  cases: 4
source_guards:
  total: 50
  categories:
    org_scoping: 15
    idor_prevention: 10
    logs_sanitization: 8
    backup_safety: 5
    jwt_cookies: 7
    forbidden_patterns: 5
ci_tools:
  - bandit
  - semgrep
  - gitleaks
  - pip-audit
  - source-guards (50)
  - idor-matrix (288 tests)
next_adr: ADR-028 Lifecycle states
```

---

**Statut** : `Proposed`. À acter par Amine avant L4 production.

Une fois acté, ADR-027 devient **le manuel défensif Centre d'Action V4** pour Mois 2-6.
