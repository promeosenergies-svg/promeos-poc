# ADR-019 — PATCH Endpoints Org/DP RGPD Complet

**Statut** : Accepté
**Date** : 2026-05-06
**Sprint** : C-7 Phase 0 (build Phase 7.3)
**Personnes impliquées** : Amine (founder), Claude regulatory-expert + architect-helios + security-auditor
**Tracking dette** : `D-Sprint-C7-PATCH-Consentement-Endpoint-001` (P0 RGPD CNIL)

---

## Contexte

L'audit transversal Phase C 6 AXES (Phase 5.7) AXE 5 RGPD a révélé que **aucun PATCH endpoint dédié consentement n'existe** sur Phase C, malgré ADR-007 (Sprint C-4) + ADR-007 ext (Sprint C-5 P5.3) ayant livré le modèle Org/DP consentement complet.

### Diagnostic Phase 0 Sprint C-7

**État pré-Phase 7.3** :

- `routes/patrimoine_crud.py:144` PATCH `/organisations/{org_id}` (générique CRUD) accepte `consentement_*` via `OrganisationUpdate.model_dump(exclude_unset=True)` + `setattr` brut
- Phase 5.8 G1 (commit `a1671aca`) a wiré `cascade_recompute_on_change` pour les champs `consentement_dataconnect_global` + `consentement_grdf_global` après commit
- **MANQUANT** :
  - Endpoint dédié `/organisations/{id}/consentement` avec sémantique RGPD claire
  - Endpoint pour DeliveryPoint local override `/delivery-points/{id}/consentement-local`
  - AuditLog wiring `RGPD_CONSENT_CHANGE` event (cf. ADR-018 wrapper similaire)
  - Validation pydantic stricte (cgu_version requis si `consentement_*=True`)
  - Schema `OrganisationConsentementUpdate` dédié (vs `OrganisationUpdate` générique)

**Cockpit RGPD UI bloqué Sprint C-6+** sans ces endpoints (cas d'usage : DAF coche/décoche consentement DataConnect/GRDF, voit immédiatement cascade impact, signe CGU version courante).

---

## Décision

### Option retenue : **Endpoints dédiés + RGPD_CONSENT_CHANGE wiring obligatoire**

3 options arbitrées :

| Option | Description | Effort | RGPD compliance | Verdict |
|---|---|---|---|---|
| A | Étendre `patrimoine_crud:update_organisation` (Phase 5.8 G1 partial) | ~30 min | Wiring AuditLog incomplet | Phase 5.8 G1 = MVP, pas final |
| **B** | **Endpoints dédiés `/organisations/{id}/consentement` + `/delivery-points/{id}/consentement-local`** | ~2-3 h | 100% RGPD + AuditLog + cascade + schemas | ✅ **RETENUE** |
| C | Endpoint unique `/consents` polymorphe (Org/DP) | ~3 h | Lisibilité moyenne (URL semantic) | Anti-pattern REST |

### Justifications Option B

1. **Sémantique URL claire** : `/organisations/{id}/consentement` = action RGPD dédiée (vs CRUD générique)
2. **Cockpit RGPD UI** : FE peut câbler boutons "Activer DataConnect" / "Activer GRDF" sur endpoint nominal
3. **AuditLog wiring** : 1 endpoint = 1 trigger `RGPD_CONSENT_CHANGE` (vs setattr brut indiscernable de side-effect)
4. **Schema validation pydantic** : `cgu_version` obligatoire si `consentement_*=True`, type Literal pour valeurs CGU connues
5. **Cohérence ADR-007 ext + ADR-018** : audit trail complet (wiring `RGPD_CONSENT_CHANGE` ↔ wrapper external connecteurs)

### Spec endpoints

#### `PATCH /api/organisations/{org_id}/consentement`

```python
# backend/routes/rgpd_consent.py (NOUVEAU)

class OrganisationConsentementUpdate(BaseModel):
    consentement_dataconnect_global: Optional[bool] = None
    consentement_grdf_global: Optional[bool] = None
    cgu_version: Optional[str] = Field(None, max_length=20, description="Version CGU acceptée — requise si consentement set")

    @model_validator(mode="after")
    def validate_cgu_required(self) -> "OrganisationConsentementUpdate":
        """ADR-019 : si consentement_*_global est set (True ou False explicite), cgu_version obligatoire."""
        consent_set = (self.consentement_dataconnect_global is not None) or (self.consentement_grdf_global is not None)
        if consent_set and not self.cgu_version:
            raise ValueError("cgu_version requis si consentement modifié (RGPD audit trail)")
        return self


@router.patch("/api/organisations/{org_id}/consentement", response_model=OrganisationConsentementResponse)
def patch_org_consentement(
    org_id: int,
    body: OrganisationConsentementUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth),  # auth STRICT (vs get_optional_auth) — RGPD requires user
):
    """Sprint C-7 Phase 7.3 (ADR-019) — PATCH consentement Org RGPD complet.

    Trigger automatique :
    - audit_log_service.log_consent_change(...) — event RGPD_CONSENT_CHANGE
    - cascade_recompute_on_change(...) — propagation Phase 4.5 (helper Phase 5.8 G1 préservé)
    """
    org_id_resolved = resolve_org_id(request, auth, db)
    if org_id_resolved != org_id:
        raise HTTPException(403, "Forbidden — org_id mismatch (cross-tenant blocked)")

    org = db.query(Organisation).filter(Organisation.id == org_id, not_deleted(Organisation)).first()
    if not org:
        raise HTTPException(404, "Organisation introuvable")

    # Capture old values
    old_values = {
        "consentement_dataconnect_global": org.consentement_dataconnect_global,
        "consentement_grdf_global": org.consentement_grdf_global,
        "consentement_dataconnect_cgu_version": org.consentement_dataconnect_cgu_version,
        "consentement_grdf_cgu_version": org.consentement_grdf_cgu_version,
    }

    # Mutation cardinale
    payload = body.model_dump(exclude_unset=True)
    for type_ in ("dataconnect", "grdf"):
        global_field = f"consentement_{type_}_global"
        if global_field in payload:
            setattr(org, global_field, payload[global_field])
            setattr(org, f"consentement_{type_}_at", datetime.now(timezone.utc))
            setattr(org, f"consentement_{type_}_by", auth.user_id)
            setattr(org, f"consentement_{type_}_cgu_version", payload.get("cgu_version"))

    db.commit()
    db.refresh(org)

    # AuditLog wiring (ADR-019 cardinal)
    audit_log_service.log_consent_change(
        db=db,
        user_id=auth.user_id,
        org_id=org_id,
        scope="global",
        type_=None,  # both types possibles, log structuré
        old_values=old_values,
        new_values=payload,
        cgu_version=payload.get("cgu_version"),
    )

    # Cascade wiring (Phase 5.8 G1 préservé)
    cascade_results = []
    for type_ in ("dataconnect", "grdf"):
        global_field = f"consentement_{type_}_global"
        if global_field in payload:
            try:
                result = cascade_recompute_on_change(
                    db=db, entity=org, field_modified=f"Organisation.{global_field}",
                    old_value=old_values[global_field], new_value=payload[global_field],
                    persist=True, user_id=auth.user_id, org_id=org_id,
                )
                cascade_results.append({"field": global_field, "actions": len(result.actions)})
            except Exception as exc:
                _logger.error("Cascade Org consent failed: %s", type(exc).__name__)

    return OrganisationConsentementResponse(
        org_id=org_id,
        consentement_dataconnect_global=org.consentement_dataconnect_global,
        consentement_grdf_global=org.consentement_grdf_global,
        cgu_version=payload.get("cgu_version"),
        cascade=cascade_results,
        rgpd_audit_logged=True,
    )
```

#### `PATCH /api/delivery-points/{dp_id}/consentement-local`

Pattern identique pour `DeliveryPoint.consentement_*_local` + override RGPD-protégé (cardinal Sprint C-4 P4.5 Option B archi-helios). Validation pydantic + AuditLog `scope="local"`.

### `audit_log_service.log_consent_change` helper (Sprint C-7 ext)

```python
# backend/services/audit_log_service.py (extension Phase 7.3 + 7.4)

def log_consent_change(
    db: Session,
    *,
    user_id: int,
    org_id: int,
    scope: Literal["global", "local"],
    type_: Optional[Literal["dataconnect", "grdf"]],
    old_values: dict,
    new_values: dict,
    cgu_version: Optional[str] = None,
    dp_id: Optional[int] = None,  # si scope=local
) -> AuditLog:
    """Sprint C-7 Phase 7.4 (ADR-019 + ticket D-Sprint-C7-AuditLog-Wiring-RGPD-Consent-Change-001).

    Event AuditLog action="RGPD_CONSENT_CHANGE" — preuve d'origine forte CNIL article 30.
    """
    return AuditLog(
        user_id=user_id,
        org_id=org_id,
        action="RGPD_CONSENT_CHANGE",
        entity_type="Organisation" if scope == "global" else "DeliveryPoint",
        entity_id=org_id if scope == "global" else dp_id,
        diff_json={
            "scope": scope,
            "type": type_,
            "cgu_version": cgu_version,
            "old": old_values,
            "new": new_values,
        },
        ...
    )
```

---

## Conséquences

### Positives

- **Cockpit RGPD UI débloqué** Sprint C-6+ : FE peut câbler endpoint nominal
- **CNIL "preuve d'origine forte" complète** : `RGPD_CONSENT_CHANGE` event + `cgu_version` + `user_id` capturés DB
- **Schema validation pydantic stricte** : `cgu_version` requis si consentement set (vs setattr brut Phase 5.8 G1)
- **Sémantique URL REST** : `/consentement` = action dédiée (vs CRUD générique `/{org_id}` PATCH)
- **Cascade wiring préservé** Phase 5.8 G1 + AuditLog ajouté
- **Auth strict** : `get_auth` (vs `get_optional_auth` patrimoine_crud) — RGPD requires user identifié

### Négatives

- **Endpoints supplémentaires** vs Phase 5.8 G1 minimal : ~150 LOC ajoutés
- **Backwards-compat** : `patrimoine_crud:update_organisation` PATCH continue à accepter `consentement_*` (legacy) — migration FE Sprint C-8 vers endpoint dédié
- **Migration tests existants** : tests Phase 5.8 G1 PATCH `/organisations/{id}` patrimoine_crud restent valides (legacy), nouveaux tests sur endpoint dédié

### Mitigation

- Documentation FE migration : `docs/dev/cockpit_rgpd_ui_migration_C8.md` (Sprint C-8 deprecation legacy)
- Source-guard : `test_patch_org_consentement_endpoint_audit_log_wired_source_guards.py` — vérifie `audit_log_service.log_consent_change` callsite présent dans route
- Tests cardinaux Phase 7.3 :
  - `test_patch_org_consentement_audit_log_event_created`
  - `test_patch_org_consentement_cgu_version_required_validation`
  - `test_patch_org_consentement_cascade_triggered`
  - `test_patch_org_consentement_cross_tenant_blocked` (sécurité)
  - `test_patch_dp_consentement_local_override_preserved`

---

## Implémentation Sprint C-7

**Phase 7.3 — PATCH endpoints Org/DP (~2-3 h)** :

1. Créer `backend/routes/rgpd_consent.py` (~150 LOC)
2. Créer `backend/schemas/rgpd_consent.py` (pydantic models : OrganisationConsentementUpdate, OrganisationConsentementResponse, DeliveryPointConsentementLocalUpdate)
3. Wiring `audit_log_service.log_consent_change` (Phase 7.4 prerequisite)
4. Tests intégration (5 cardinaux)
5. Source-guard anti-régression
6. Inscrire route dans `backend/main.py` + `backend/routes/__init__.py`

**Phase 7.4 — AuditLog `log_consent_change` (~1-2 h)** :

1. Étendre `services/audit_log_service.py` avec helper `log_consent_change`
2. Tests cardinaux helper (3 scenarios : global / local / change cgu_version sans bool)
3. Source-guard `test_audit_log_consent_change_helper_signature_stable_source_guards.py`

### Délégation

- **regulatory-expert** validation CNIL article 30 + cgu_version requirement
- **security-auditor** validation auth strict + cross-tenant blocked
- **architect-helios** cohérence ADR-007 ext + ADR-018 wrapper similaire

---

## Références

- Tracking dette : `D-Sprint-C7-PATCH-Consentement-Endpoint-001` + `D-Sprint-C7-AuditLog-Wiring-RGPD-Consent-Change-001`
- ADR amont : ADR-007 (RGPD modèle) + ADR-007 ext (Sprint C-5 P5.3) + ADR-018 (External Connectors audit)
- Phase 5.8 G1 wiring cascade existant : commit `a1671aca`
- Pattern AuditLog Sprint C-2 P1.2 : `services/audit_log_service.py`
