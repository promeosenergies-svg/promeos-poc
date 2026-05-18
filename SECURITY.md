# Security — PROMEOS

> Dernière mise à jour : Sprint M2-4 — closure documentaire M2-4.7 (branche `feat/m2-4-rollout`, PR #279).
> Référence audit complet : [`SECURITY_AUDIT_M2-3.md`](SECURITY_AUDIT_M2-3.md).

---

## 1. Posture actuelle (TL;DR 3 personas)

Trois personas, trois questions :

- **Dev nouveau** — *"Comment ajouter un endpoint sensible ?"* → §3.
- **Auditeur pilote** — *"Quelles garanties d'isolation entre clients ?"* → §2 + §4.
- **Toi dans 3 mois** — *"Qu'est-ce qui reste à faire ?"* → §5.

**État M2-4** — Centre d'Action V4 routé (11 sous-sprints M2-4.0 → M2-4.7).

Socle M2-3 :

- ✅ JWT + auth middleware + 11 rôles legacy + scoping hiérarchique legacy (Sprint 11 IAM · `backend/middleware/auth.py` + `backend/services/iam_scope.py`)
- ✅ RBAC V4 — `require_v4_role` + mapping 11→4 rôles (M2-3.B)
- ✅ Repository pattern V4 fail-closed — `BaseRepositoryV4` (M2-3.C)
- ✅ 6 endpoints de seed fermés — admin + env guard (M2-3.A + M2-3.B)
- ✅ Headers sécurité, CORS allowlist, `audit_logs` (pré-existant)

Acquis M2-4 (Centre d'Action V4) :

- ✅ Dette JWT `org_id` résolue **à la racine** — `organisation_id` migré UUID → Integer FK (ADR-009 Option D · M2-4.1). Le JWT legacy câble le contexte V4 sans transformation.
- ✅ Seed V4 minimal idempotent — 2 orgs + items (`python -m seeds.v4_seed` · M2-4.1.bis).
- ✅ 14 endpoints V4 `/api/v4/action-center/*` — 3 templates + 4 read + 7 write (M2-4.2 → M2-4.4).
- ✅ Audit trail V4 — 5 `event_type` émis sur les écritures (`action_event_log` · M2-4.4) → §2.4.
- ✅ Validation upload evidence par magic bytes — anti-spoofing MIME (IE9 · M2-4.4).
- ✅ IDOR matrix systémique cross-org — 14 endpoints × rôles × 2 orgs, focus no-leak (M2-4.5).
- ✅ Rate limiting V4 — slowapi, 5 catégories de quotas, clé `user:<sub>` / fallback IP (M2-4.6) → §2.5.
- 🟡 Dette résiduelle JWT `user_id` int ↔ V4 `actor_id` UUID — P1 M3 (§5.1).
- ⏳ Scope hiérarchique V4 (ENTITÉ / PORTEFEUILLE / SITE) — M2-6+ (§5.3).

---

## 2. Architecture de sécurité V4

### 2.1 — Authentification (JWT)

- Stack : OAuth2 password flow, JWT HS256, claims `sub` + `org_id` + `role`.
- Code : `backend/middleware/auth.py` — `require_admin`, `require_permission`, `require_platform_admin`, `get_jwt_payload` (helper JWT-only M2-3.B).
- `decode_token` / `create_access_token` : `backend/services/iam_service.py`.
- DEMO_MODE (`PROMEOS_DEMO_MODE=true`) : token absent → payload `None` (bypass volontaire pour démo HELIOS). Un token *présent mais invalide* lève toujours 401, même en DEMO_MODE.

### 2.2 — Autorisation V4 (RBAC)

- Wrapper : `require_v4_role(*allowed_roles: Role)` — `backend/middleware/rbac.py`.
- Mapping legacy → V4 : `_LEGACY_TO_V4_ROLE` (11 rôles métier PROMEOS → 4 rôles V4 `admin`/`user`/`viewer`/`system`).
- Fallback : rôle legacy inconnu → `viewer` (least privilege) + warning log `rbac.unknown_legacy_role` (révèle les rôles oubliés sans casser l'app).
- Error codes : `ROLE_MISSING` / `ROLE_FORBIDDEN` (payload structuré).
- Référence détaillée : table `_LEGACY_TO_V4_ROLE` dans `backend/middleware/rbac.py`.

### 2.3 — Isolation org (repository V4)

- Pattern : `BaseRepositoryV4` — `backend/repositories/base_v4.py`.
- Mécanisme : `ContextVar` peuplé par la dependency `populate_org_context` (`backend/middleware/org_context.py`).
- **Fail-closed** : `current_org_id()` lève `NoOrgContextError` si le contexte n'est pas peuplé — impossible d'oublier le scoping (contraste avec les helpers legacy `iam_scope.py`, *oubliables*).
- `create()` force `organisation_id` depuis le contexte (override caller — defense in depth). `update`/`delete` lèvent `OrgScopeViolation` si cross-org. `get()` cross-org renvoie `None` (404 côté route — anti-énumération).
- Extension hiérarchique : hook `_apply_scope()` override-able + `_scope_column` class attr (cf. docstring `base_v4.py` — OCP, porte ouverte ENTITÉ/PORTEFEUILLE/SITE).
- Tests preuve : 12 tests `backend/tests/repositories/test_base_v4.py` (fail-closed + isolation A/B + OCP).

### 2.4 — Traçabilité (audit trail V4)

- Table : `action_event_log` — chaque écriture V4 émet un event horodaté **org-scopé**.
- 5 `event_type` émis par les endpoints write M2-4.4 : `item_created`, `lifecycle_changed`, `evidence_attached`, `evidence_verified`, `blocker_added` — tous dans la whitelist doctrine de 16 valeurs (SG-6 · ADR-029).
- Acteur : `actor_id` UUID dérivé **déterministe** (uuid5) du `user_id` JWT int ; le `user_id` int réel est tracé dans `event_payload.actor_user_id` (dette de typage résiduelle — §5.1, sans perte de traçabilité).
- Code : émission via `ActionEventLogRepository` dans `backend/routes/v4/action_center.py`.

### 2.5 — Rate limiting (V4)

- Stack : slowapi, storage in-memory (`backend/main_limiter.py`). Migration Redis multi-instance différée M3+.
- Clé de quota : `user:<sub>` si le JWT est décodable, sinon `ip:<adresse>` — fail-soft, le rate limiting ne casse jamais une requête (token absent/expiré/forgé → fallback IP silencieux).
- 5 catégories : READ 120/min · WRITE 60/min · UPLOAD 10/min · VERIFY 30/min · FALLBACK 100/min.
- Réponse 429 au format PROMEOS (`{code, message, hint, retry_after}`) + header `Retry-After`.
- Désactivé en environnement de test (`PROMEOS_RATE_LIMIT_ENABLED=false`, posé par `tests/conftest.py`) — sinon les suites V4 (mêmes user/IP, centaines d'appels rapides) déclencheraient des 429.
- ⚠️ Reverse proxy : pour un rate limit effectif derrière nginx / Cloudflare / ALB, uvicorn doit tourner `--proxy-headers --forwarded-allow-ips=<proxy>` **et** le proxy doit strip le `X-Forwarded-For` entrant (sinon un client spoofe son IP). Détail : docstring `main_limiter.py`.

---

## 3. Pour le dev — Ajouter un endpoint sensible

**Checklist (7 items)** :

1. **Auth** : `Depends(require_v4_role(Role.ADMIN, Role.USER))` (rôles applicables).
2. **Org context** : `dependencies=[Depends(populate_org_context)]` sur la route.
3. **Repository** : utiliser un repo héritant de `BaseRepositoryV4` — ne **jamais** faire `db.query(Model).all()` direct sur un model V4.
4. **Env guard** (si endpoint admin/seed/debug) : `Depends(require_non_prod_env)`.
5. **Test** : au moins 1 cas `viewer → 403` + 1 cas `cross-org → 404`.
6. **Audit** (si écriture) : émettre l'`event_type` V4 approprié (whitelist doctrine 16 valeurs — §2.4).
7. **Rate limit** : décorer la route `@limiter.limit(...)` avec la catégorie adaptée (READ/WRITE/UPLOAD/VERIFY — §2.5).

Exemple minimal :

```python
from main_limiter import limiter, QUOTA_READ_V4

@router.get(
    "/api/v4/action-center/things/{thing_id}",
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_READ_V4)
async def get_thing(
    request: Request,
    thing_id: str,
    db: Session = Depends(get_db),
    auth=Depends(require_v4_role(Role.VIEWER, Role.USER, Role.ADMIN)),
):
    thing = ThingV4Repository(db).get(thing_id)
    if thing is None:
        raise HTTPException(404, "Thing not found")
    return thing
```

---

## 4. Garanties d'isolation entre clients (pour pilote)

| Couche | Garantie | Preuve |
| --- | --- | --- |
| JWT | Token signé HS256, claims `sub`/`org_id`/`role` | `get_jwt_payload`, `require_admin` |
| Rôle | RBAC V4 4 niveaux, fallback `viewer` least-privilege | `test_require_v4_role.py` (12 cas) |
| Org isolation | Repository fail-closed, force `organisation_id` au `create()` | `test_base_v4.py` (12 cas) |
| Cross-org read | `404` (pas `403` — pas de leak d'existence) | `test_base_v4.py::test_get_blocks_cross_org_access` |
| Cross-org write | `OrgScopeViolation` exception | `test_base_v4.py::test_update_blocks_cross_org_write` |
| Endpoint seed/admin | `require_admin` + `require_non_prod_env` (defense in depth) | `test_seed_endpoints_require_admin.py` (22 cas) |
| IDOR end-to-end | 14 endpoints V4 × rôles × 2 orgs, cross-org → `404` no-leak | `test_v4_idor_matrix.py` (M2-4.5) |
| Audit trail | Chaque écriture V4 → event horodaté org-scopé | `action_event_log`, tests M2-4.4 |
| Anti-spoofing upload | MIME validé par magic bytes (pas par extension) | `file_validation.py` (IE9 · M2-4.4) |
| Rate limiting | 5 quotas par catégorie, clé `user:<sub>` / IP | `test_rate_limit.py` (M2-4.6) |

**Résolu (M2-4.1)** — la chaîne `JWT → populate_org_context → BaseRepositoryV4` est désormais bouclée : `organisation_id` est un Integer FK partagé legacy↔V4 (ADR-009 Option D), le contexte V4 est alimenté sans transformation de type. Dette résiduelle limitée à l'`actor_id` des audit events — typage seulement, traçabilité exacte (§5.1).

---

## 5. Dettes connues et chantiers

> **§5 = source de vérité unique des différés.** Tous les autres docs y renvoient.
> Backlog M3 détaillé (sprints + effort) : [`BACKLOG_M3.md`](BACKLOG_M3.md).

### 5.1 — Dette JWT `user_id` int ↔ V4 `actor_id` UUID  🟡 P1 M3

- **Symptôme** : le JWT porte `sub` / `user_id: int` (legacy). Les colonnes d'acteur des tables V4 — `action_event_log.actor_id`, `evidences.uploaded_by`, `action_blockers.added_by` — sont des `UUID`.
- **Impact** : *aucun bug en prod*. M2-4.4 dérive un `actor_id` UUID5 **déterministe** du `user_id` int et trace le `user_id` int réel dans `event_payload.actor_user_id`. La traçabilité est exacte ; seul le typage est hétérogène.
- **Pourquoi P1 et non P0** : la dette `org_id` (P0, résolue M2-4.1) bloquait le scoping — un défaut de sécurité. La dette `user_id` ne bloque rien : c'est une cohérence de schéma. Reclassée P1.
- **Résolution M3** (sprint `M3-JWT-USER-UUID`, cf. `BACKLOG_M3.md`) — 3 options parallèles à ADR-009 :
  - **A** — table de correspondance `users` int→UUID persistée (mapping auditable).
  - **B** — JWT émet `user_id: UUID` (impacte les consommateurs legacy — risque régression).
  - **D** — migrer `actor_id`/`uploaded_by`/`added_by` UUID→Integer FK `users.id` (parallèle exact de la résolution `org_id`). **Reco** : D, par symétrie avec ADR-009.
- **Traçabilité** : §2.4 · `backend/routes/v4/action_center.py` (dérivation uuid5) · ADR-009 (résolution sœur `org_id`).

### 5.2 — Différés M2-5

- **ActionLink — cibles polymorphes** : `site` / `building` / `meter` / `invoice` / `contract` (`regulatory_obligation` → M2-6). `link_target_validator.verify_link_target` lève `501 TARGET_MODULE_NOT_IMPLEMENTED` en attendant le repository V4 correspondant.
- **Evidence — formats** : DOCX / XLSX / ZIP / CSV (M2-4 = PDF / JPG / PNG seulement, validés par magic bytes).

### 5.3 — Différés M2-6

- Scope hiérarchique V4 (ENTITÉ / PORTEFEUILLE / SITE) — extension par sous-classes de `BaseRepositoryV4`, hook `_apply_scope()` prêt.
- `write_event()` Pydantic strict (16 schemas v1) pour `action_event_log` — IE7.
- Rétention 90j evidence enforce Python — IE6 (actuellement documenté, pas en CHECK SQL portable).
- Scan antivirus (ClamAV), chiffrement at-rest, backend S3 evidence. Stockage actuel = filesystem local par org (`PROMEOS_EVIDENCE_STORAGE_PATH`).
- Création rôle V4 `auditor` distinct (actuellement `auditeur` legacy → `viewer`).
- Endpoint admin `closed → reopened` (fresh token + justification, IL3) — si le besoin se confirme (`closed` est terminal aujourd'hui).
- `link_created` event_type — amendement ADR-029 à arbitrer (cf. `BACKLOG_M3.md` sprint `M3-LINK-EVENT-DOCTRINE`).

### 5.4 — Hors scope Mois 2 (long terme)

- Refresh tokens + révocation.
- 2FA pour rôles admin.
- OAuth2 SSO (Google, Azure AD).
- Password rotation policy.

### 5.5 — Dettes résolues — historique

| Dette | Résolue | Comment |
| --- | --- | --- |
| JWT `org_id` int ↔ V4 `organisation_id` UUID 🔴 P0 | M2-4.1 | ADR-009 Option D — `organisation_id` migré UUID→Integer FK (8 tables V4 vides → 0 backfill). JWT câblé sans transformation. |
| Câblage `populate_org_context` réel → `BaseRepositoryV4` | M2-4.1 | Type Integer cohérent de bout en bout (JWT → ContextVar → `_apply_scope`). |
| `@limiter` rate limiting sur routes V4 | M2-4.6 | slowapi, 5 catégories de quotas — cf. §2.5. |
| IDOR matrix end-to-end (14 endpoints × rôles × 2 orgs) | M2-4.5 | Focus no-leak : cross-org read → 404, jamais 403. |
| Magic bytes MIME validation upload evidence (IE9) | M2-4.4 | `file_validation.py` — anti-spoofing par signatures binaires. |
| Tests d'intégration cross-org bout-en-bout | M2-4.5 | Débloqués par l'existence des 14 routes V4 réelles. |

---

## 6. Référencement (pas de duplication)

- Matrice RBAC détaillée : [`docs/security/RBAC_MATRIX.md`](docs/security/RBAC_MATRIX.md)
- Plan IAM ultime (Sprint 11) : [`docs/iam_ultimate_plan.md`](docs/iam_ultimate_plan.md)
- Notes sécurité legacy : [`docs/security_notes.md`](docs/security_notes.md)
- Audit Sprint M2-3 (Phase 1 + état final) : [`SECURITY_AUDIT_M2-3.md`](SECURITY_AUDIT_M2-3.md)
- ADR-027 Sécurité org-scoping V4 : [`docs/dev/L4_ADR-027_securite_org_scoping.md`](docs/dev/L4_ADR-027_securite_org_scoping.md)
- ADR-009 Résolution dette JWT/UUID : [`docs/decisions/adr/009-jwt-uuid-resolution.md`](docs/decisions/adr/009-jwt-uuid-resolution.md)
- Backlog M3 (dettes ouvertes, sprints planifiés + effort) : [`BACKLOG_M3.md`](BACKLOG_M3.md)

---

## 7. Reporting de vulnérabilités

Pour signaler une faille de sécurité : **<à compléter par Amine — email security@promeos.io ou canal dédié>**.

En attendant l'adresse officielle : ouvrir une issue GitHub **privée** (ne pas divulguer publiquement une faille non corrigée) ou contacter directement le mainteneur du repo.
