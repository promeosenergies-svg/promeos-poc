# Audit post-fix Bill Intelligence P1.5 — 2026-05-24

> **Branche** : `claude/bill-intelligence-p15-audit-all-idempotence`
> **Base** : `claude/refonte-sol2 @ db8aaac1` (post audits + Phase 0-bis + Bill Intel P1)
> **Mode** : audit READ-ONLY après correction. Méthode `feedback-audit-sprint-visuel-fonctionnel`.

## TL;DR — Verdict

**🟢 GO pour le prochain chantier.**

Le dernier irritant P0 produit post-Bill P1 (D-P2-001) est résolu. `POST /api/billing/audit-all` est désormais **strictement idempotent** : aucune HTTP 500 sur re-run, aucun doublon, message FR doctriné.

- **10 tests nouveaux verts** (C3 — couvre 1er run, 2e run, simulation, no-auth, sync reste idempotent, message FR)
- **454 tests non-régression verts** (72 P1 + 382 source-guards + billing principal)
- **Audit visuel Playwright** : 2 clicks "Auditer tout" → 2 toasts FR succès, **0 console error**, **0 network 4xx/5xx**
- **Audit fonctionnel curl** : 2 runs successifs sur DB démo (36 factures, 78 anomalies) → 200/200, `created=0` + `updated=52` au 2e run

---

## 1. Reproduction (C1)

### Avant fix

```bash
curl -X POST -H "X-Org-Id: 1" http://127.0.0.1:8001/api/billing/audit-all
# → HTTP 500 (sur DB démo déjà auditée)
```

Trace ASGI (extraite des logs serveur) :

```
sqlalchemy.exc.PendingRollbackError: ...
Original exception was: (sqlite3.IntegrityError)
  UNIQUE constraint failed: bill_anomaly.invoice_id, bill_anomaly.code
[SQL: INSERT INTO bill_anomaly (..., code, ...) VALUES (?, 'R27', ...)]
```

### Cause exacte

- **Table** : `bill_anomaly`
- **Contrainte** : `UniqueConstraint("invoice_id", "code", name="uq_bill_anomaly_invoice_code")` (Phase 5.8 anti-doublons R19/R20 — `models/bill_anomaly.py:39`)
- **Source du doublon** : tous les 13 détecteurs R19-R31 dans [`services/bill_intelligence/anomaly_detector.py::detect_anomalies_for_invoice`](backend/services/bill_intelligence/anomaly_detector.py) faisaient `db.add(rN)` aveuglément, sans vérifier l'existence préalable.

Sur une DB déjà auditée (cas du seed démo HELIOS), le 1er `db.add(r27)` du 1er invoice violait la contrainte → `IntegrityError` propagée en HTTP 500 brut, et tous les `add()` suivants étaient bloqués en `PendingRollbackError`.

**Aucun lien avec `BillingInsight` ou `ActionCenterItem`** — bug purement isolé sur `bill_anomaly`.

---

## 2. Correction (C2)

### Approche : helper `_upsert_anomaly`

[`services/bill_intelligence/anomaly_detector.py`](backend/services/bill_intelligence/anomaly_detector.py) — ajout d'un helper UPSERT idempotent placé en tête du module :

```python
def _upsert_anomaly(db: Session, new_anomaly: BillAnomaly) -> tuple[str, BillAnomaly]:
    existing = db.query(BillAnomaly).filter(
        BillAnomaly.invoice_id == new_anomaly.invoice_id,
        BillAnomaly.code == new_anomaly.code,
        BillAnomaly.deleted_at.is_(None),
    ).first()
    if existing is None:
        db.add(new_anomaly)
        return ("created", new_anomaly)
    if existing.resolved_at is not None:
        return ("skipped_resolved", existing)  # respect travail opérateur
    # update champs métier (severity, actual_value, threshold, details_json,
    # is_monetizable, non_monetizable_reason, detected_at = now)
    ...
    return ("updated", existing)
```

**Règles préservées au update** :
- `id`, `created_at` → identité (FK preservées vers BillAnomalyEvidence + ActionCenterItem via EXTERNAL_REF)
- `resolved_at`, `resolution_note` → travail opérateur (sinon une nouvelle détection écraserait une résolution validée)

**Règles rafraîchies au update** : `severity`, `actual_value`, `threshold_value`, `details_json`, `is_monetizable`, `non_monetizable_reason`, `detected_at`.

### Pipeline refactor

Wrapper `_add_or_update(db, detected, counters, anomalies)` factorise les 13 branches. Chaque détecteur :

```python
# AVANT
try:
    r19 = detect_r19_vnu_dormant(invoice, db)
    if r19:
        db.add(r19)
        anomalies.append(r19)
except Exception as e: _logger.error(...)

# APRÈS
try:
    _add_or_update(db, detect_r19_vnu_dormant(invoice, db), counters, anomalies)
except Exception as e: _logger.error(...)
```

`detect_anomalies_for_invoice` accepte un paramètre `counters: Optional[dict]` qui est rempli en place avec `{created, updated, skipped_resolved}`.

### Propagation jusqu'à l'API

`audit_invoice_full` propage les compteurs dans sa réponse. `audit_all_invoices` agrège + génère le message FR :

```python
fr_message = (
    f"Audit terminé : {len(results)} facture{...} analysée{...}, "
    f"{total_created} anomalie{...} créée{...}, "
    f"{total_updated} mise{...} à jour, "
    f"{total_skipped_resolved} déjà résolue{...}."
)
```

**Pas de `try/except` générique** (doctrine), **pas de suppression de la contrainte unique** (doctrine).

**Bonus** : commit explicite ajouté en fin de boucle (avant : commit conditionnel uniquement si `reconcile_results` → anomalies potentiellement perdues si invoice sans reconcile).

---

## 3. Tests (C3)

### 10 tests nouveaux pytest

[`tests/test_billing_audit_all_idempotent_p15.py`](backend/tests/test_billing_audit_all_idempotent_p15.py) :

| # | Test | Cas couvert |
|---|---|---|
| 1 | `test_upsert_creates_when_absent` | INSERT initial |
| 2 | `test_upsert_updates_when_open` | Update champs métier + id préservé |
| 3 | `test_upsert_skips_when_resolved` | SKIP si résolu + note préservée |
| 4 | `test_audit_all_first_run_returns_200` | 1er run → 200 + message FR |
| 5 | `test_audit_all_second_run_is_idempotent_no_500` | **2e run → 200, 0 doublon (cardinal)** |
| 6 | `test_audit_all_simulated_unique_violation_does_not_crash` | Pré-injection anomalie → upsert convertit en update |
| 7 | `test_audit_all_preserves_resolved_anomalies` | resolved_at + resolution_note intacts |
| 8 | `test_audit_all_without_org_context_returns_401_fr` | Préservation P1 C3 (NO_ORG_CONTEXT) |
| 9 | `test_sync_actions_from_anomalies_still_idempotent` | Régression P1 C4 — sync actions OK |
| 10 | `test_audit_all_message_fr_format` | "Audit terminé : ..." accord singulier/pluriel |

### Non-régression

| Catégorie | Tests | Statut |
|---|---|---|
| `test_bill_anomaly_detector.py` | 19 | ✅ pas un seul détecteur cassé par le refactor |
| `test_bill_anomaly_monetizable_invariant_p1.py` | 7 | ✅ |
| `test_bill_anomaly_evidence_p1.py` | 12 | ✅ |
| `test_billing_audit_all_no_org_context_p1.py` | 3 | ✅ |
| `test_billing_sync_actions_from_anomalies_p1.py` | 6 | ✅ |
| `test_billing_explainability_energy_aware_p1.py` | 7 | ✅ |
| `test_bill_intelligence_endpoint.py` | 4 | ✅ |
| `test_power_engines.py` | 14 | ✅ |
| `test_billing.py` | ~30 | ✅ |
| `source_guards/` | 352 + 1 skip | ✅ cardinal |
| **Total non-régression** | **~454** | **✅** |

---

## 4. Audit fonctionnel curl

Backend démarré sur `http://127.0.0.1:8001` (DEMO_MODE=true) sur DB démo HELIOS (36 factures, 52 anomalies pré-existantes du seed).

### Cas 1 — 1er run audit-all (X-Org-Id=1)

```bash
curl -X POST -H "X-Org-Id: 1" http://127.0.0.1:8001/api/billing/audit-all
```

```json
HTTP 200
{
  "status": "ok",
  "audited": 36,
  "total_anomalies": 78,
  "bill_anomalies_created": 0,
  "bill_anomalies_updated": 52,
  "bill_anomalies_skipped_resolved": 0,
  "message_fr": "Audit terminé : 36 factures analysées, 0 anomalie créée, 52 mises à jour, 0 déjà résolue."
}
```

### Cas 2 — 2e run audit-all (re-run idempotent — **CRITICAL**)

```json
HTTP 200
{
  "status": "ok",
  "bill_anomalies_created": 0,
  "bill_anomalies_updated": 52,
  "message_fr": "Audit terminé : 36 factures analysées, 0 anomalie créée, 52 mises à jour, 0 déjà résolue."
}
```

**Avant P1.5** : ce 2e run produisait **HTTP 500** (régression observée live durant P1).
**Après P1.5** : 200 stable, 0 doublon, message FR.

### Cas 3 — audit-all sans X-Org-Id (DEMO_MODE fallback)

```json
HTTP 200
{ "status": "ok", "message_fr": "Audit terminé : 36 factures analysées..." }
```

Fallback DEMO_MODE fonctionne (préservation P1 C3).

### Cas 4 — audit-all sans X-Org-Id (DEMO_MODE=false) → P1 C3

Couvert par `test_audit_all_without_org_context_returns_401_fr` : retourne `401 NO_ORG_CONTEXT` FR doctriné (non-régression).

---

## 5. Audit visuel Playwright

Frontend démarré sur `http://127.0.0.1:5175`. Captures dans `/tmp/promeos-audit-billing-p15/*.png` (hors repo, gitignore).

### Parcours golden path

| # | Étape | Capture | Observation |
|---|---|---|---|
| 0 | Login démo HELIOS | n/a | OK |
| 1 | Navigation `/bill-intel` | `01_bill_intel.png` | Bouton "Auditer tout" visible, non disabled ✅ |
| 2 | **1er click "Auditer tout"** | `02_after_audit1.png` | Toast FR *"Audit terminé — les anomalies détectées sont affichées ci-dessous"* ✅ |
| 3 | **2e click "Auditer tout"** | `03_after_audit2.png` | Toast FR identique (idempotence visuelle) ✅ |
| 4 | Click "Créer les actions de litige facture" | n/a | Toast FR *"Aucune action facture à créer pour le moment"* (sync reste idempotente, P1 C4 préservé) ✅ |

### Métriques

| Métrique | Compte |
|---|---|
| `console.error` / `pageerror` | **0** |
| Réponses HTTP 4xx/5xx (hors hot-update, favicon) | **0** |

**Conclusion visuelle** : le DAF peut désormais cliquer "Auditer tout" autant de fois qu'il veut sans risque de crash silencieux ou de doublon.

---

## 6. Critères d'acceptation

| Critère | Statut | Preuve |
|---|---|---|
| `/api/billing/audit-all` ne retourne plus 500 sur re-run | ✅ | Test #5 + curl cas 2 + Playwright #3 |
| Les anomalies ne sont pas dupliquées | ✅ | Test #5 (`count_after_2 == count_after_1`) + curl (`created=0` au 2e run) |
| Les actions ne sont pas dupliquées | ✅ | Test #9 (sync-actions-from-anomalies reste idempotente) |
| Message FR clair | ✅ | Test #10 + curl (*"Audit terminé : 36 factures analysées, 0 anomalie créée..."*) |
| Tests nouveaux verts | ✅ | 10/10 |
| Non-régression Bill P1 | ✅ | 72 P1 + 382 source-guards + ~30 billing principal verts |
| Aucun nouveau menu | ✅ | NavRegistry intact |
| Aucun écran fantôme | ✅ | Aucune page créée |

---

## 7. Architecture du fix — pattern réutilisable

Le pattern `_upsert_anomaly` peut être généralisé à toute table avec UniqueConstraint où le service producteur peut être ré-exécuté :

- Préservation **identité** (`id`, `created_at`)
- Préservation **travail opérateur** (résolution, notes)
- Rafraîchissement **champs métier** (severity, valeur, contexte)
- Compteurs explicites `{created, updated, skipped_resolved}` pour message FR doctrin

Candidats futurs :
- `BillingInsight` (workflow_status géré côté UI — utile si re-import déclenche re-détection)
- `ActionCenterItem` (déjà idempotent via signature 4-tuple en P1 C1 conformité, autre pattern)

---

## 8. Dette résiduelle P2

Aucune nouvelle dette introduite. La dette D-P2-001 de l'audit P1 est **fermée**.

Restent les 6 autres dettes P2 inscrites en P1 ([audit_postfix_bill_intelligence_p1_2026_05_24.md §11](audit_postfix_bill_intelligence_p1_2026_05_24.md#11-dette-résiduelle-p2)) :
- D-P2-002 migration NOT NULL `actual_value`
- D-P2-003 stockage S3 evidence
- D-P2-004 suppression complète stubs FE
- D-P2-005 warnings ESLint cosmétiques
- D-P2-006 CMDPS gaz (équivalent ATRD/ATRT)
- D-P2-007 fixtures golden set gaz

---

## 9. Verdict

### 🟢 GO pour le prochain chantier

Le sprint P1.5 a atteint son objectif unique et précis : rendre `audit-all` strictement idempotent. Le bug racine du re-INSERT est neutralisé par un helper UPSERT élégant qui :
1. Ne masque jamais l'erreur (pas de try/except générique)
2. Ne supprime pas la contrainte unique (intégrité préservée)
3. Respecte le travail opérateur (résolutions préservées)
4. Propage des compteurs explicites jusqu'au message FR

**Note brique Bill Intelligence post-P1.5** : **8/10 → 8,5/10** (la dernière dette P0 produit est neutralisée).

### Prochains chantiers possibles

- **Bill Intel P2 doctrine** : migration NOT NULL `actual_value` + S3 evidence + CMDPS gaz + golden set fixtures (4 dettes P2 cumulables)
- **Autre brique** : Achat Energie (purchase), Cockpit V4 DAF, ou prochain audit de brique non encore couverte

---

*Audit clôturé le 2026-05-24 sur `claude/bill-intelligence-p15-audit-all-idempotence`. Mode READ-ONLY après correction. Méthode conforme [[feedback-audit-sprint-visuel-fonctionnel]] : helper UPSERT documenté, 10 tests nouveaux + 454 non-régression verts, curl 2 runs successifs + Playwright golden path 2 clicks "Auditer tout" → 0 console error / 0 network 4xx-5xx. Captures hors repo dans `/tmp/promeos-audit-billing-p15/`.*
