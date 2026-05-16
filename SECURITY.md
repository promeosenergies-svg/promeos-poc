# Security — PROMEOS

> Dernière mise à jour : Sprint M2-3 (4 commits, branche `feat/m2-3-security-layer`).
> Référence audit complet : [`SECURITY_AUDIT_M2-3.md`](SECURITY_AUDIT_M2-3.md).

---

## 1. Posture actuelle (TL;DR 3 personas)

Trois personas, trois questions :

- **Dev nouveau** — *"Comment ajouter un endpoint sensible ?"* → §3.
- **Auditeur pilote** — *"Quelles garanties d'isolation entre clients ?"* → §2 + §4.
- **Toi dans 3 mois** — *"Qu'est-ce qui reste à faire ?"* → §5.

**État M2-3** :

- ✅ JWT + auth middleware + 11 rôles legacy + scoping hiérarchique legacy (Sprint 11 IAM · `backend/middleware/auth.py` + `backend/services/iam_scope.py`)
- ✅ RBAC V4 par dessus — `require_v4_role` + mapping 11→4 rôles (M2-3.B)
- ✅ Repository pattern V4 fail-closed — `BaseRepositoryV4` (M2-3.C)
- ✅ 6 endpoints de seed fermés — admin + env guard (M2-3.A + M2-3.B)
- ✅ Headers sécurité, CORS allowlist, rate limiting slowapi, `audit_logs` (pré-existant)
- ⚠️ Dette JWT `org_id` int ↔ V4 `organisation_id` UUID — chantier M2-4 (§5.1)
- ⏳ IDOR matrix bout-en-bout + `@limiter` routes V4 — M2-4
- ⏳ Hierarchical scope V4 (ENTITÉ / PORTEFEUILLE / SITE) — M2-6+

---

## 2. Architecture de sécurité V4 (3 couches)

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

---

## 3. Pour le dev — Ajouter un endpoint sensible

**Checklist (5 items)** :

1. **Auth** : `Depends(require_v4_role(Role.ADMIN, Role.USER))` (rôles applicables).
2. **Org context** : `dependencies=[Depends(populate_org_context)]` sur la route.
3. **Repository** : utiliser un repo héritant de `BaseRepositoryV4` — ne **jamais** faire `db.query(Model).all()` direct sur un model V4.
4. **Env guard** (si endpoint admin/seed/debug) : `Depends(require_non_prod_env)`.
5. **Test** : au moins 1 cas `viewer → 403` + 1 cas `cross-org → 404`.

Exemple minimal :

```python
@router.get(
    "/api/v4/things/{thing_id}",
    dependencies=[Depends(populate_org_context)],
)
async def get_thing(
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
|---|---|---|
| JWT | Token signé HS256, claims `sub`/`org_id`/`role` | `get_jwt_payload`, `require_admin` |
| Rôle | RBAC V4 4 niveaux, fallback `viewer` least-privilege | `test_require_v4_role.py` (12 cas) |
| Org isolation | Repository fail-closed, force `organisation_id` au `create()` | `test_base_v4.py` (12 cas) |
| Cross-org read | `404` (pas `403` — pas de leak d'existence) | `test_base_v4.py::test_get_blocks_cross_org_access` |
| Cross-org write | `OrgScopeViolation` exception | `test_base_v4.py::test_update_blocks_cross_org_write` |
| Endpoint seed/admin | `require_admin` + `require_non_prod_env` (defense in depth) | `test_seed_endpoints_require_admin.py` (22 cas) |

**Limite connue (chantier M2-4)** : `populate_org_context` lit `org_id` du JWT au format `int` (legacy) mais les models V4 utilisent `organisation_id` UUID. En production routée, la chaîne JWT → repo V4 n'est pas bouclée — voir §5.1. Comportement actuel : *fail-visible* (queries vides ou `NoOrgContextError`), jamais *wrong data*.

---

## 5. Dettes connues et chantiers

> **§5 = source de vérité unique des différés.** Tous les autres docs y renvoient.

### 5.1 — Dette JWT int ↔ V4 UUID  🔴 P0 M2-4

- **Symptôme** : le JWT porte `org_id: int` (legacy — `Organisation.id` est un Integer PK). Les 8 models V4 (`backend/models/v4/`) utilisent `organisation_id: UUID`.
- **Impact** : la chaîne `JWT → populate_org_context → BaseRepositoryV4` ne match pas en type. Aucune route V4 réelle n'existe encore (les 12 endpoints `/api/action-center/*` = M2-4) — donc pas de bug en prod aujourd'hui, mais le câblage est bloqué.
- **Mitigation actuelle** : les tests M2-3.C bypassent en appelant `set_org_context(org_id_str)` directement. Le pattern est validé en isolation, pas la chaîne JWT réelle.
- **Résolution M2-4** : arbitrer en ADR entre (a) mapping `int → UUID` dans `populate_org_context`, (b) émettre des JWT avec `org_id: UUID`, (c) colonne `legacy_int_id` sur les V4 models.
- **Traçabilité (3/3)** : docstring `backend/middleware/org_context.py` · commit `13dad3ba` (M2-3.C) · ce paragraphe.

### 5.2 — Différés M2-4

- `@limiter` (rate limiting) sur les routes V4 (à créer en M2-4).
- IDOR matrix end-to-end : 12 endpoints × rôles × 2 orgs (cf. ADR-027 §10 — 288 cellules).
- Câblage `populate_org_context` réel → résolution dette §5.1.
- Tests d'intégration cross-org bout-en-bout (différés faute de routes V4 existantes).

### 5.3 — Différés M2-6

- Hierarchical scope V4 (ENTITÉ / PORTEFEUILLE / SITE) — extension par sous-classes de `BaseRepositoryV4`, hook `_apply_scope()` prêt.
- `write_event()` Pydantic strict (16 schemas v1) pour `action_event_log` — IE7.
- Magic bytes MIME validation upload evidence — IE9 cardinal Amine.
- Rétention 90j evidence enforce Python — IE6 (actuellement documenté, pas en CHECK SQL portable).
- Création rôle V4 `auditor` distinct (actuellement `auditeur` legacy → `viewer`).

### 5.4 — Hors scope Mois 2 (long terme)

- Refresh tokens + révocation.
- 2FA pour rôles admin.
- OAuth2 SSO (Google, Azure AD).
- Password rotation policy.

---

## 6. Référencement (pas de duplication)

- Matrice RBAC détaillée : [`docs/security/RBAC_MATRIX.md`](docs/security/RBAC_MATRIX.md)
- Plan IAM ultime (Sprint 11) : [`docs/iam_ultimate_plan.md`](docs/iam_ultimate_plan.md)
- Notes sécurité legacy : [`docs/security_notes.md`](docs/security_notes.md)
- Audit Sprint M2-3 (Phase 1 + état final) : [`SECURITY_AUDIT_M2-3.md`](SECURITY_AUDIT_M2-3.md)
- ADR-027 Sécurité org-scoping V4 : [`docs/dev/L4_ADR-027_securite_org_scoping.md`](docs/dev/L4_ADR-027_securite_org_scoping.md)

---

## 7. Reporting de vulnérabilités

Pour signaler une faille de sécurité : **<à compléter par Amine — email security@promeos.io ou canal dédié>**.

En attendant l'adresse officielle : ouvrir une issue GitHub **privée** (ne pas divulguer publiquement une faille non corrigée) ou contacter directement le mainteneur du repo.
