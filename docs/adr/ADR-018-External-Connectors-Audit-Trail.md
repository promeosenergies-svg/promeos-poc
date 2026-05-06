# ADR-018 — External Connectors Audit Trail (CNIL preuve d'extraction)

**Statut** : Accepté
**Date** : 2026-05-06
**Sprint** : C-7 Phase 0 (build Phase 7.5)
**Personnes impliquées** : Amine (founder), Claude regulatory-expert + architect-helios + security-auditor
**Tracking dette** : `D-Sprint-C7-External-Connectors-Audit-Trail-001` (P0 CNIL)

---

## Contexte

L'audit transversal Phase C 6 AXES (Phase 5.7) AXE 5 RGPD a révélé que **aucun connecteur externe n'écrit d'event AuditLog** lors d'appels API tiers consommant des données à caractère personnel (PRM/PCE/SIREN — art. 4 RGPD).

### Diagnostic Phase 0 Sprint C-7

**4 connecteurs externes Phase C** (`backend/connectors/`) :

- `enedis_dataconnect.py` + `enedis_dataconnect_errors.py` — appels DataConnect Enedis (PRM élec, consentement client requis)
- `enedis_opendata.py` — appels Enedis Opendata (données agrégées publiques, moins sensibles)
- `entsoe_connector.py` — appels ENTSOE (prix marché, données publiques)
- `grdf_adict.py` + `grdf_errors.py` — appels ADICT GRDF (PCE gaz, consentement client requis)

**Service Sirene** (`backend/services/sirene_hydrate.py` + `sirene_lookup.py`) :

- Appels `recherche-entreprises.api.gouv.fr` (SIREN/SIRET, donnée publique mais traçabilité prospect/lead requise)
- `sirene_hydrate.py:153` ne fait que `logger.info` stdout (volatile, non requêtable, non scopé org)

→ **Aucun pattern centralisé**. Chaque connecteur log via `logging.info` ad-hoc — ni AuditLog DB ni `correlation_id` propagé.

### Impact CNIL

- "Preuve d'extraction" PRM/PCE post-incident : **impossible à reconstituer**
- Audit RGPD CNIL ne peut pas tracer "qui a consulté quoi quand pour quel client"
- Article 30 RGPD (registre des traitements) : extraction PRM = traitement — registre incomplet sans audit trail

---

## Décision

### Option retenue : **Décorateur `@audit_external_api_call(provider, endpoint)` centralisé**

3 options arbitrées :

| Option | Description | Effort | Maintenabilité | Verdict |
|---|---|---|---|---|
| A | Log manuel dans chaque connecteur (4×) | ~3 h | Régression possible | Anti-pattern duplication |
| **B** | **Décorateur centralisé `audit_log_service.audit_external_api_call`** | ~2-3 h | DRY + 1 SoT | ✅ **RETENUE** |
| C | Middleware HTTPX intercepteur global | ~3-4 h | Risque interception trop large (bibliothèques internes) | Trop intrusif |

### Justifications Option B

1. **DRY** : 1 décorateur Python applique cohérence cross-connecteurs (4 wirings)
2. **1 SoT** : `audit_log_service` reste la SoT canonique audit (cohérent Sprint C-2 P1.2)
3. **Configurable per-call** : `correlation_id` propagé via header, `payload_hash` SHA256 calculé automatiquement
4. **Tests cardinaux factorisés** : 1 test décorateur générique + 1 test wiring par connecteur

### Spec décorateur

```python
# backend/services/audit_log_service.py (extension Phase 7.5)

from functools import wraps
import hashlib
import json
import time
from typing import Callable

ALLOWED_PROVIDERS = {"DATACONNECT", "GRDF", "SIRENE", "ENEDIS_OPENDATA", "ENTSOE"}

def audit_external_api_call(provider: str, endpoint: str):
    """Décorateur Sprint C-7 Phase 7.5 (ADR-018) — audit trail RGPD extraction PRM/PCE/SIREN.

    Usage :
        @audit_external_api_call(provider="DATACONNECT", endpoint="GET /api/measure")
        def fetch_measure(...): ...

    Capture :
    - provider (DATACONNECT / GRDF / SIRENE / ENEDIS_OPENDATA / ENTSOE)
    - endpoint (string descriptif, sans tokens secrets)
    - status_code (HTTP)
    - duration_ms
    - payload_hash (SHA256 sur kwargs sanitisés — sans tokens)
    - correlation_id (header X-Correlation-ID propagé)
    - org_id (extrait kwargs si présent)
    - user_id (extrait kwargs si présent)

    Trigger : automatique sur tout call (pas opt-in). Non-blocking : si log fail, l'appel continue.
    """
    if provider not in ALLOWED_PROVIDERS:
        raise ValueError(f"provider invalide : {provider} (attendu : {ALLOWED_PROVIDERS})")

    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            status_code = None
            error_type = None
            try:
                result = fn(*args, **kwargs)
                # Best-effort : récupérer status_code si result.status_code disponible
                status_code = getattr(result, "status_code", 200)
                return result
            except Exception as e:
                error_type = type(e).__name__
                status_code = getattr(e, "status_code", 500)
                raise
            finally:
                duration_ms = int((time.perf_counter() - start) * 1000)
                _log_external_call_safe(
                    provider=provider,
                    endpoint=endpoint,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    error_type=error_type,
                    kwargs_sanitized=_sanitize_kwargs(kwargs),
                )
        return wrapper
    return decorator


def _sanitize_kwargs(kwargs: dict) -> dict:
    """Retire tokens / secrets / credentials avant hashing."""
    SECRET_KEYS = {"token", "api_key", "password", "secret", "authorization", "client_secret"}
    return {k: v for k, v in kwargs.items() if k.lower() not in SECRET_KEYS}


def _log_external_call_safe(...):
    """Insère AuditLog sans bloquer si DB fail (résilience cardinal)."""
    try:
        # Création AuditLog avec action=f"API_CALL_{provider}" + payload JSON
        # SHA256 du payload sanitized pour traçabilité sans stockage donnée brute
        payload_hash = hashlib.sha256(json.dumps(kwargs_sanitized, sort_keys=True).encode()).hexdigest()[:16]
        # ... insertion DB ...
    except Exception as exc:
        _logger.error("Audit external API call log failed: %s", type(exc).__name__)
        # Ne PAS raise — l'appel API doit continuer même si audit fail
```

### 4 nouveaux event types `AuditLog.action`

- `API_CALL_DATACONNECT` — Enedis DataConnect (cardinal RGPD)
- `API_CALL_GRDF` — GRDF ADICT (cardinal RGPD)
- `API_CALL_SIRENE` — Recherche entreprises (lead/prospect)
- `API_CALL_ENEDIS_OPENDATA` — Données publiques (traçabilité opérationnelle)
- `API_CALL_ENTSOE` — Prix marché (audit trail commercial)

### Wiring 4 connecteurs Phase C

```python
# backend/connectors/enedis_dataconnect.py
@audit_external_api_call(provider="DATACONNECT", endpoint="GET /api/measure/CDC")
def fetch_load_curve(prm: str, ...): ...

@audit_external_api_call(provider="DATACONNECT", endpoint="GET /api/measure/INDEX")
def fetch_index(prm: str, ...): ...

# backend/connectors/grdf_adict.py
@audit_external_api_call(provider="GRDF", endpoint="GET /api/measures")
def fetch_pce_measures(pce: str, ...): ...

# backend/services/sirene_hydrate.py
@audit_external_api_call(provider="SIRENE", endpoint="GET /search")
def hydrate_siren_from_api(siren: str, ...): ...
```

---

## Conséquences

### Positives

- **CNIL "preuve d'extraction" complète** — toute extraction PRM/PCE/SIREN tracée DB requêtable
- **Article 30 RGPD registre traitements** : audit log = source vérité technique
- **DRY pattern** : décorateur réutilisable (extensible Phase D nouveaux connecteurs)
- **Sécurité PII** : `payload_hash` (vs payload brut) — pas de fuite SIREN/PRM en clair en DB
- **Performance** : <5ms overhead par call (insert AuditLog non-bloquant)

### Négatives

- **+1 INSERT DB par call externe** : ~1-3 ms par appel — acceptable même connecteur batch (1000 calls = ~3s overhead)
- **Stockage AuditLog augmente** : ~500 bytes par call → ~1.5 MB / 1000 calls / org (acceptable, rotation possible Sprint C-8)
- **Risque verbosity logs** : tous appels loggés — UI admin/audit doit filtrer par provider + period

### Mitigation

- Index composite `AuditLog (action, created_at)` pour requêtes audit rapides
- Rotation AuditLog Sprint C-8+ : archivage > 1 an vers cold storage (CNIL durée minimale 1 an art. 5)
- Source-guard `test_external_connectors_audit_decorator_present_source_guards.py` : grep `httpx.get|httpx.post` dans `backend/connectors/` + `backend/services/sirene_*` doit être ≤ 0 hors décorateur

---

## Implémentation Sprint C-7 Phase 7.5 (~2-3 h)

1. Étendre `services/audit_log_service.py` avec décorateur `audit_external_api_call` (~80 LOC)
2. Wirer 4 connecteurs (~15 min chacun)
3. Tests :
   - `test_audit_external_api_call_decorator_basic` (cardinal)
   - `test_audit_external_api_call_sanitization_secrets` (PII)
   - 4 tests wiring (1 par connecteur)
   - 1 test résilience (DB fail → call continue)
4. Source-guard anti-régression (decorator obligatoire)

### Délégation

- **regulatory-expert** validation CNIL article 30 + durée rétention
- **security-auditor** sanitization secrets + payload_hash SHA256
- **bill-intelligence** validation cohérence avec billing audit existant

---

## Références

- Tracking dette : `D-Sprint-C7-External-Connectors-Audit-Trail-001` (P0)
- Audit transversal Phase 5.7 AXE 5 finding C2 : `AUDIT_TRANSVERSAL_PHASE_C_2026_05_06.md`
- Pattern AuditLog Sprint C-2 P1.2 : `services/audit_log_service.py:log_patrimoine_change` + `log_cascade`
- CNIL article 30 RGPD : registre des activités de traitement
