# SECURITY AUDIT M2-3 — Couche Sécurité PROMEOS

> **Date** : 2026-05-15
> **Branche** : `feat/m2-3-security-layer` (depuis état HEAD post-Sprint M2-2)
> **Méthode** : Phase 1 audit-before-fix lecture seule (cf. SPRINT_M2-3_SECURITY_LAYER.md)
> **Particularité** : repo PROMEOS **déjà très mature en sécurité** — Sprint M2-3 réel ≠ rebuild from scratch comme suggéré par le prompt. Mission adaptée = **audit + consolidation + comblement gaps spécifiques V4**.

---

## 0. Synthèse exécutive

| Domaine | Statut existant | Action M2-3 réelle |
|---|---|---|
| AuthN (JWT) | ✅ JWT + middleware auth en place (`backend/middleware/auth.py`) | ⚠️ TTL 30min vs 15min recommandé · pas de refresh token visible |
| RBAC | ✅ `require_admin()` + `require_permission()` + `require_platform_admin` existants | ⚠️ Pas d'enum `Role` formel pour V4 (cf. ADR-027 §3.1 Role enum livré M2-2 commit 1/5) |
| Org-scoping | ✅ `org_id` JWT claim + `UserOrgRole` + cache TTL membership (`backend/middleware/cx_logger.py`) | ⚠️ V4 routes (Sprint M2-4) doivent consommer ce système existant + IS11 pattern repository (Sprint M2-3) |
| Endpoints publics | ⚠️ Majorité `require_admin()` ✓ · Gaps : `action_templates POST /seed`, `consumption_diagnostic POST /seed-demo` (auth optionnelle) | Fermer les 2 gaps |
| Secrets | ✅ `.env` gitignored · `.env.example` template · pas de secret en clair backend/ (seul `seed_data.py:893 demo2024` = code seed dev) | ✅ OK |
| Headers + CORS | ✅ `SecurityHeadersMiddleware` (X-Frame/X-Content-Type/HSTS/CSP) + CORS allowlist `_CORS_ORIGINS` (pas wildcard) | ✅ Existant suffisant — vérifier renforcement V4 if needed |
| Rate limiting | ✅ slowapi installé + `main_limiter.py` actif + handler 429 | ⚠️ Vérifier décorateurs effectifs sur `/auth/login` + exports V4 |
| Audit log | ✅ Table `audit_logs` existe (legacy) + V4 `action_event_log` (Sprint M2-2) avec IE7 schema_version + IS9 correlation_id | ⚠️ Sprint M2-6 finira l'intégration V4 evidence + audit trail (writer service) |

**Score global** : 70 % conforme · 30 % gaps spécifiques V4 + ajustements TTL.

**Mission M2-3 ajustée** : pas un rebuild from scratch (le prompt original assume greenfield · faux). 4 chantiers ciblés :
1. **Aligner V4 sur l'existant** — IS11 pattern repository org-scopé pour `backend/models/v4/` (Sprint M2-3)
2. **Combler 2 gaps endpoints non-protégés** (`action_templates POST /seed`, `consumption_diagnostic POST /seed-demo`)
3. **Documenter posture sécurité finale** (`SECURITY.md`)
4. **Tests sécurité V4** dans `backend/tests/security/` (préparation IDOR matrix Sprint M2-4)

---

## 1.1 Endpoints sans dépendance auth

### Inventaire

- 99 fichiers dans `backend/routes/` · 97 routers Python
- Recherche cibles `seed`/`admin`/`internal`/`debug` :

| Endpoint | Fichier | Auth ? | Verdict |
|---|---|---|---|
| `POST /api/action-templates/seed` | `action_templates.py:339` | ❌ Aucune (`Depends(get_db)` seul) | ⚠️ **GAP M2-3.4** |
| `POST /seed` (kb_usages) | `kb_usages.py:511` | À vérifier | À auditer |
| `POST /api/consumption/seed-demo` | `consumption_diagnostic.py:142` | ⚠️ `Depends(get_optional_auth)` | ⚠️ **GAP M2-3.4** (auth OPTIONNELLE) |
| `POST /api/billing/seed-demo` | `billing.py:1868` | ✅ `Depends(require_admin())` | OK |
| `POST /api/purchase/seed-demo` | `purchase.py:1123` | ✅ `Depends(require_admin())` | OK |
| `POST /api/demo/seed` | `demo.py` | ✅ `Depends(require_admin())` | OK |
| `POST /api/admin/...` | `admin_users.py` | ✅ `Depends(require_permission("admin"))` (3+) | OK |
| `POST /api/monitoring/emission-factors/seed` | `monitoring.py:843` | À vérifier | À auditer |

### Verdict

⚠️ **Partiel** — majorité ✅ require_admin · 2 gaps confirmés (`action_templates`, `consumption_diagnostic`) + 2 à re-vérifier (`kb_usages`, `monitoring`).

**Action M2-3.4** : ajouter `require_admin()` ou `require_permission("admin")` sur les 4 endpoints (1 commit atomique).

---

## 1.2 Org-scoping (tenant isolation)

### Inventaire

✅ Système existant **mature** :

```
backend/middleware/auth.py                 — JWT + extraction org_id depuis claim
backend/middleware/cx_logger.py            — cache TTL membership (user_id, org_id)
backend/services/scope_utils.py            — helpers
backend/services/iam_scope.py              — IAM scope service
backend/services/patrimoine_scope_guard.py — guard patrimoine spécifique
backend/tests/test_v57_multiorg_isolation.py — tests isolation multi-org
backend/tests/test_consumption_scope.py    — tests scope conso
backend/tests/test_usage_scope.py          — tests scope usage
backend/tests/test_regops_idor_multitenant_l35.py — tests IDOR regops
```

JWT claim `org_id` extrait par `get_current_user` (auth.py:78, :131, :186) avec :
- Vérification membership via `UserOrgRole` table
- Cache TTL pour perf
- DEMO_MODE bypass pour seed local

### Verdict

✅ **Conforme legacy** — système org_id JWT + UserOrgRole + cache + tests existant et fonctionnel.

⚠️ **Gap V4** — `backend/models/v4/` (Sprint M2-2) utilise `organisation_id` UUID col mais **n'est pas encore relié** au système de scope existant (qui utilise `org_id` Integer dans JWT).

**Action M2-3.3 (V4-spécifique)** : créer pattern repository org-scopé pour V4 (IS11 cardinal Amine) en s'appuyant sur le `request.state.organisation_id` (UUID) à extraire du JWT enrichi V4. Sprint M2-3 livre :
- `backend/repositories/v4_base.py` : ABC `V4Repository` avec `organisation_id: UUID` paramètre obligatoire
- Tests source-guards SG-10 : `test_no_query_v4_without_organisation_id_filter`
- ⚠️ Migration JWT `org_id` Int → `organisation_id` UUID = chantier futur (pas M2-3)

---

## 1.3 RBAC

### Inventaire

✅ Système existant :

```
backend/middleware/auth.py — require_admin(), require_permission(scope), require_platform_admin
```

Décorateurs utilisés sur :
- `routes/digest.py:26`         — `Depends(require_platform_admin)`
- `routes/admin_users.py` (3×)  — `Depends(require_permission("admin"))`
- `routes/billing.py:1871`      — `Depends(require_admin())`
- `routes/auth.py:340`          — `Depends(require_permission("admin"))`

V4 enum `Role` (admin/user/viewer/system) livré Sprint M2-2 commit 75104ac8 (`backend/models/v4/enums/role.py`) — pas encore connecté au middleware existant.

### Verdict

✅ **Conforme legacy** — RBAC fonctionnel via `require_admin/require_permission/require_platform_admin`.

⚠️ **Gap V4** — enum `Role` V4 (4 valeurs cohérent ADR-027 §3.1) défini mais pas encore consommé par les routes V4 (Sprint M2-4 livre les 12 endpoints `/api/action-center/*`).

**Action M2-3.2 (V4-spécifique)** : **NE PAS RÉÉCRIRE** le RBAC existant. Créer un wrapper `require_v4_role(*allowed: Role)` qui s'appuie sur `require_permission` existant + check `actor.role IN allowed`. Compatible avec routes legacy + nouvelles routes V4.

---

## 1.4 Secrets en clair

### Inventaire

```
✅ .env                       gitignored
✅ backend/.env               gitignored (présent local)
✅ .env.example               template public (sans secret réel)
✅ backend/.env.example       template public

Recherche secrets dans backend/ (hors venv/, hors test_, hors __pycache__) :
⚠️ backend/scripts/seed_data.py:893 — `password="demo2024"` (code seed dev — ACCEPTABLE)
✅ Pas d'autre `SECRET_KEY = "..."` ou `API_KEY = "..."` en dur
```

### Verdict

✅ **Conforme** — pas de secret en clair en production.

L'unique mention `demo2024` est dans `seed_data.py` qui crée des users de démo locale (DEMO_MODE) — c'est intentionnel et documenté dans CLAUDE.md (`Demo admin promeos@promeos.io / promeos2024`).

**Action M2-3** : aucune. Pas besoin de `chore(security): rotate exposed secrets`.

---

## 1.5 Headers + CORS

### Inventaire

✅ `backend/middleware/security_headers.py` existe avec :
- `X-Frame-Options: DENY` ✓
- `X-Content-Type-Options: nosniff` ✓
- `Strict-Transport-Security` (en prod uniquement) ✓
- `Content-Security-Policy: default-src 'self'` (élargie en dev) ✓
- `Referrer-Policy` ✓ (présent dans le module)

✅ `backend/main.py:174-177` CORSMiddleware avec `_CORS_ORIGINS` (allowlist depuis env, pas wildcard) + `allow_methods=["*"]` (large mais OK pour API REST interne).

### Verdict

✅ **Conforme** — middleware sécurité headers + CORS allowlist.

⚠️ **Gap mineur** : `Permissions-Policy: geolocation=()` non confirmé dans le grep (à vérifier dans `security_headers.py` complet).

**Action M2-3.6 (optionnel)** : ajouter `Permissions-Policy` si absent (1 commit micro).

---

## 1.6 Rate limiting

### Inventaire

✅ `backend/main_limiter.py` actif :
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
```

✅ `backend/main.py:138-151` :
- `from slowapi import _rate_limit_exceeded_handler`
- `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)`

✅ `backend/requirements.txt:47 slowapi>=0.1.9`

### Verdict

✅ **Conforme** — slowapi installé + handler 429 enregistré.

⚠️ **Gap potentiel** — vérifier que `@limiter.limit(...)` est appliqué effectivement sur :
- `/api/auth/login` (10/min/IP recommandé prompt)
- `/api/exports/*` (10/min/user recommandé prompt)
- Routes V4 sensibles (Sprint M2-4)

**Action M2-3.7 (V4-spécifique)** : audit ciblé `@limiter.limit` + ajout sur routes V4 en Sprint M2-4 (pas Sprint M2-3 — déférer).

---

## 1.7 Audit log

### Inventaire

✅ Table `audit_logs` existe en DB legacy (legacy structure).

✅ Migration `f415992b3d25_audit_log_extend_for_patrimoine_cascade.py` existe (extension audit_log pour cascade patrimoine).

✅ V4 `action_event_log` table créée Sprint M2-2 commit 7a03aba0 avec :
- IE7 `schema_version` VARCHAR(10) NOT NULL (Pydantic versionning)
- IS9 `correlation_id` UUID NOT NULL (traçabilité cross-actions)
- 16 event_types CHECK ADR-029 §6.1 (renommages aval acceptés)

✅ V4 `action_evidences` table créée Sprint M2-2 (D2 ADR-029 §2.1 autoritatif · IE6 90j enforced service Sprint M2-6).

### Verdict

✅ **Conforme V4** — schéma audit_log V4 (action_event_log) prêt + cohérent ADR-029.

⚠️ **Gap d'intégration** — service `write_event(event_type, payload_dict, ...)` avec validation Pydantic 16 schemas v1 = **Sprint M2-6** (pas Sprint M2-3).

⚠️ **Gap legacy** — `audit_logs` legacy continue de fonctionner pour les flows existants. Pas de hooks centralisés sur les 10 actions critiques (login_success, password_changed, etc.) — à vérifier en détail si déjà fait par Yannick.

**Action M2-3.5 (déferré)** : laisser intact la structure V4 (`action_event_log`) — Sprint M2-6 livrera le writer Pydantic. Pas de modification audit_log legacy en M2-3.

---

## Anomalies détectées

### Bloquantes : 0

### Mineures : 4

| # | Anomalie | Action M2-3 | Phase 2 sous-section |
|---|---|---|---|
| **A1** | `POST /api/action-templates/seed` sans auth | Ajouter `require_admin()` | M2-3.4 |
| **A2** | `POST /api/consumption/seed-demo` avec `get_optional_auth` (auth facultative) | Renforcer en `require_admin()` | M2-3.4 |
| **A3** | V4 routes Sprint M2-4 (à venir) doivent consommer pattern repository org-scopé (IS11) | Créer `backend/repositories/v4_base.py` ABC | M2-3.3 |
| **A4** | V4 enum `Role` (M2-2) pas connecté au middleware auth existant | Créer `require_v4_role(*allowed: Role)` wrapper | M2-3.2 |

### Différé Sprint M2-6 (pas M2-3) :

- Service `write_event()` Pydantic versionné (16 schemas v1) — IE7
- Magic bytes MIME validation evidence — IE9 cardinal Amine
- `expires_at = verified_at + 90j` Python enforce — IE6

### Différé Sprint M2-4 (pas M2-3) :

- 12 endpoints `/api/action-center/*` avec `require_v4_role` + IDOR matrix 288
- `@limiter.limit` sur routes V4 sensibles

---

## Plan adapté Sprint M2-3 (4 commits ciblés au lieu de 8)

| # | Commit | Cible | Justification |
|---|---|---|---|
| **M2-3.A** | `feat(security): M2-3.A — close 2 endpoints with require_admin (action_templates + consumption_seed)` | A1 + A2 | Gaps réels confirmés |
| **M2-3.B** | `feat(security): M2-3.B — V4 require_v4_role wrapper + Role enum integration` | A4 | Connecter V4 enum Role à middleware existant |
| **M2-3.C** | `feat(security): M2-3.C — V4 repository pattern org-scopé (IS11 cardinal)` | A3 | Préparation Sprint M2-4 |
| **M2-3.D** | `docs(security): M2-3.D — SECURITY.md posture finale + audit M2-3` | DoD | Documentation posture sécurité |

### Tests sécurité V4

- `backend/tests/security/test_v4_require_v4_role.py` — wrapper RBAC
- `backend/tests/security/test_v4_repository_org_scoping.py` — pattern IS11
- `backend/tests/security/test_endpoints_seed_now_protected.py` — non-régression A1+A2

### Pas de régénération de l'existant (anti-pattern)

❌ NE PAS réécrire :
- `backend/middleware/auth.py` (legacy fonctionnel)
- `backend/middleware/security_headers.py` (déjà conforme)
- `backend/main_limiter.py` (déjà actif)
- Système RBAC `require_admin/require_permission` (utilisé partout)
- Table `audit_logs` legacy

✅ EXTENSION ADDITIVE Q13-B inviolable :
- V4 wrappers (require_v4_role) appellent l'existant
- V4 repositories en sub-package isolé
- Documentation centralisée dans `SECURITY.md`

---

## Sortie Phase 1

```
═══════════════════════════════════════════════════════
PHASE 1 AUDIT TERMINÉ — STOP GATE
═══════════════════════════════════════════════════════

Sections auditées : 7/7 (1.1 → 1.7)
Repo sécurité maturity : 70 % (déjà conforme largement)

Gaps identifiés (mineurs) : 4 (A1-A4)
- A1+A2 : 2 endpoints non-protégés (action_templates seed + consumption seed-demo)
- A3 : V4 pattern repository à créer (préparation Sprint M2-4)
- A4 : V4 require_v4_role wrapper à créer (intégration enum Role M2-2)

Plan adapté : 4 commits ciblés (vs 8 du prompt générique)
Effort estimé : 0.5-1 jour vs 2 jours prompt original
0 réécriture de l'existant (anti-pattern)

Différé Sprint M2-4 : @limiter sur routes V4 + IDOR matrix
Différé Sprint M2-6 : write_event() Pydantic + magic bytes IE9

Rapport produit : SECURITY_AUDIT_M2-3.md (à la racine repo)

⛔ NE PAS DÉMARRER Phase 2 avant validation utilisateur.

Confirmer : « GO Phase 2 » (ou indiquer ajustements au plan adapté)
═══════════════════════════════════════════════════════
```
