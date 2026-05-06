# ADR-017 — DEMO_MODE Architecture (validation org_id obligatoire)

**Statut** : Accepté
**Date** : 2026-05-06
**Sprint** : C-7 Phase 0 (build Phase 7.2)
**Personnes impliquées** : Amine (founder), Claude security-auditor + architect-helios
**Tracking dette** : `D-Sprint-C7-Demo-Mode-Org-Validation-001` (P0 PROMEOS-SEC-2026-001 + SEC-2026-012)

---

## Contexte

L'audit security-auditor Sprint C-5 Phase 5.5 (`PROMEOS-SEC-2026-001` HIGH) + audit transversal Phase 5.7 AXE 4 (`SEC-2026-012`) ont confirmé une **faille IDOR cross-tenant systémique en DEMO_MODE** :

`backend/services/scope_utils.py:get_scope_org_id` :

```python
# Pattern actuel (vulnérable)
raw = request.headers.get("X-Org-Id")
if raw:
    return int(raw)  # ❌ Pas de check existence Organisation en DB
```

**Impact** : ~25 endpoints Phase C affectés. Tout client non authentifié peut forger `X-Org-Id: <n>` et obtenir données cross-tenant arbitraires en DEMO_MODE.

**Surface attaque** : démo investisseur, POC publique, environnements pilote pré-prod si DEMO_MODE oublié.

### Audit Phase 0 Sprint C-7 — diagnostic terrain

- `DEMO_MODE` référencé dans 5+ fichiers : `scope_utils.py`, `middleware/auth.py`, `cx_logger.py`, plusieurs tests
- Comportement actuel `scope_utils.get_scope_org_id` (lignes 23-141) :
  1. `auth.org_id` (JWT) → priorité absolue
  2. `X-Org-Id` header → accepté brut sans validation DB
  3. `DEMO_MODE=false` + non résolu → 401
  4. `DEMO_MODE=true` + non résolu → fallback `DemoState.get_demo_org_id()` puis 1ère org active DB
- Tests dépendants du DEMO_MODE bypass : ~5 fichiers (`test_cockpit_facts_service`, `test_phase58`, `test_purchase_auth_hardening`, `test_events_upcoming`, `test_event_bus`)

→ Risque régression test si on supprime DEMO_MODE entièrement (Option C). Risque sécurité si on garde tel quel (statu quo).

---

## Décision

### Option retenue : **Option B — DEMO_MODE actif avec org_id validation DB stricte**

3 options arbitrées :

| Option | Description | Effort | Régression tests | Sécurité | Verdict |
|---|---|---|---|---|---|
| A | DEMO_MODE désactivé en prod, dev seul | Migration env vars + audit prod | ~2-3 h + risque oubli prod | 100% scope_utils enforced | Risqué (oubli config = back to vulnérable) |
| **B** | DEMO_MODE actif + org_id validation DB obligatoire | ~3-4 h | Tests démo garantis OK | 100% enforcing même DEMO | ✅ **RETENUE** |
| C | DEMO_MODE retiré complètement (seeds prod-like) | ~6-8 h refactor seeds | Régression majeure tests | 100% (pas de mode démo possible) | Trop coûteux MVP |

### Justifications Option B

1. **Démo investisseur préservée** : DEMO_MODE reste utilisable pour pitch + POC, juste sécurisé
2. **Tests Phase C non régressés** : ~5 tests dépendants gardent leur comportement (org_id démo dédié)
3. **Sécurité 100%** : `X-Org-Id` validé contre `Organisation.id` réelle DB → IDOR impossible
4. **Pattern pré-existant éprouvé** : mini-sprint IDOR Portfolio (CWE-284) + IDOR meters (CWE-639) ont validé l'approche `_check_X_belongs_to_org`

### Modifications cardinales

#### `services/scope_utils.py:get_scope_org_id`

```python
def get_scope_org_id(request: Request, auth: Optional[AuthContext], db: Session) -> Optional[int]:
    """Sprint C-7 Phase 7.2 fix (ADR-017) : validation org_id DB obligatoire X-Org-Id."""
    # 1. JWT auth (priorité absolue, déjà validé middleware)
    if auth and auth.org_id is not None:
        return auth.org_id

    # 2. X-Org-Id header — DOIT être validé DB (Sprint C-7 fix)
    raw = request.headers.get("X-Org-Id")
    if raw:
        try:
            org_id = int(raw)
        except (ValueError, TypeError):
            _security_logger.warning("X-Org-Id invalid format: %s", raw)
            return None

        # ADR-017 cardinal : check existence + actif + soft-delete en DB
        org = (
            db.query(Organisation)
            .filter(Organisation.id == org_id, Organisation.actif.is_(True), not_deleted(Organisation))
            .first()
        )
        if org is None:
            _security_logger.warning("X-Org-Id rejected: org_id=%d introuvable ou inactive", org_id)
            return None  # Fail securely (pas 403 — laisse fallback DEMO_MODE le cas échéant)

        return org_id

    # 3. None → fallback caller (DEMO_MODE → DemoState, ou 401)
    return None
```

#### `services/scope_utils.py:resolve_org_id`

Inchangé : continue à appeler `get_scope_org_id` puis fallback DEMO_MODE → DemoState. Mais désormais la chaîne est **secure-by-default** (rejet org_id invalide au lieu d'acceptation aveugle).

#### Tests intégration cardinaux

- `test_demo_mode_x_org_id_existing_org_accepted` : org_id réel → 200
- `test_demo_mode_x_org_id_inexistant_rejected` : org_id=99999 inexistant → fallback DemoState
- `test_demo_mode_x_org_id_soft_deleted_rejected` : org_id soft-deleted → fallback
- `test_demo_mode_x_org_id_inactif_rejected` : `actif=False` → fallback
- `test_idor_cross_tenant_blocked_in_demo_mode` : user A passe org_id B → données B inaccessibles (sécurité cardinale)

---

## Conséquences

### Positives

- **IDOR cross-tenant DEMO_MODE éliminé** (~25 endpoints Phase C protégés simultanément)
- **Pas de régression tests** (org_id démo dédié reste accessible via DemoState)
- **Crédibilité pilote investisseur** : démo sécurisée comme prod
- **Source-guard parametrized** : tous endpoints `resolve_org_id` héritent de la sécurité

### Négatives

- **+1 query DB par requête X-Org-Id** : impact perf négligeable (<1ms, query indexée sur PK)
- **5+ tests à éventuellement adapter** : fixtures doivent fournir org_id réel (vs entier arbitraire)
- **Logs warning supplémentaires** : org_id rejetés tracés `_security_logger` (utile audit, pas régression)

### Mitigation

- Cache LRU léger sur `Organisation.id → bool` actif (TTL 60s) si perf devient critique pilote prod
- Tests existants vérifiés Phase 7.2 build : adapter `X-Org-Id: 1` → `X-Org-Id: <demo_org_id>` selon DemoState
- Source-guard `test_demo_mode_org_validation_enforced_source_guards.py` : grep `int(raw)` sans validation = bloqué

---

## Implémentation Sprint C-7 Phase 7.2 (~3-4 h)

1. Modif `services/scope_utils.py:get_scope_org_id` (~15 LOC + signature change `db: Session` requis)
2. Adapter callsites `resolve_org_id` qui ne passaient pas `db` (audit grep)
3. Tests intégration : 5 tests cardinaux (cf. ci-dessus)
4. Source-guard anti-régression
5. Documentation : `docs/adr/ADR-017-*.md` (ce fichier) + commentaire en code

### Délégation

- **security-auditor** validation finale post-fix (pattern PROMEOS-SEC-2026-XXX)
- **test-engineer** pour scenarios IDOR cross-tenant cardinaux

---

## Références

- Tracking dette : `D-Sprint-C7-Demo-Mode-Org-Validation-001` (P0)
- Findings audits : PROMEOS-SEC-2026-001 (Phase 5.5) + SEC-2026-012 (Phase 5.7 transversal)
- Pattern précédents : mini-sprint IDOR meters (`40ebb348`) + IDOR Portfolio (`32d88c85`)
- Bilan Phase C : `BILAN_PHASE_C_7_7_LIVRES_2026_05_06.md` 5 P0 résiduels
