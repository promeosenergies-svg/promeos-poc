# OPERAT Audit-trail + Qualification source + UI trajectoire

> Date : 2026-03-16
> Commit : `ff9a7b4`
> Statut : Implemente, teste, pushe

---

## Fichiers crees

| Fichier | Role |
|---------|------|
| `backend/models/compliance_event_log.py` | Modele ComplianceEventLog (audit-trail immuable) |
| `backend/tests/test_compliance_evidence.py` | 14 tests (event log, source quality, fallback warnings) |

## Fichiers modifies

| Fichier | Modification |
|---------|-------------|
| `backend/models/tertiaire.py` | +reliability sur TertiaireEfaConsumption |
| `backend/models/__init__.py` | Export ComplianceEventLog |
| `backend/database/migrations.py` | Migration table event_log + colonne reliability |
| `backend/services/operat_trajectory.py` | Journalisation + qualification source + evidence_warnings |
| `backend/routes/tertiaire.py` | Endpoint GET /efa/{id}/proof-events |
| `frontend/src/services/api.js` | +validateEfaTrajectory, +getEfaProofEvents |
| `frontend/src/pages/tertiaire/TertiaireEfaDetailPage.jsx` | Bloc UI trajectoire OPERAT |

---

## Nouveau modele : ComplianceEventLog

```
id, entity_type, entity_id, action, before_json, after_json,
actor, source_context, created_at
INDEX(entity_type, entity_id)
```

Actions journalisees :
- `create` : creation consommation EFA
- `update` : mise a jour consommation
- `trajectory_compute` : recalcul trajectoire

---

## Qualification source

| Source | Fiabilite | Justification |
|--------|-----------|---------------|
| `import_invoice`, `api`, `factures` | **high** | Donnees tracees, verifiables |
| `declared_manual` | **medium** | Saisie utilisateur, non verifiee |
| `site_fallback`, `inferred`, `estimation`, `seed` | **low** | Fallback, non recevable comme preuve |
| `unknown`, `null` | **unverified** | Source inconnue |

**Regle critique : fallback JAMAIS classe "high" (test automatise).**

---

## Evidence warnings

Si baseline ou conso courante a une fiabilite `low` ou `unverified` :
- `evidence_warnings` dans la reponse validate
- Warning visible dans le bloc UI trajectoire
- Aucun statut interpretable comme "preuve forte"

---

## Bloc UI trajectoire

```
┌──────────────────────────────────────────────────────┐
│ TRAJECTOIRE OPERAT            [Trajectoire atteinte] │
│                                                      │
│ Reference              Observation 2026              │
│ 500 000 kWh (2019)     280 000 kWh                   │
│ [Fiable] factures      [Moyenne] declared_manual     │
│                                                      │
│ Objectif 2030 : 300 000 kWh         -20 000 kWh (-7%)│
│                                                      │
│ Donnees non normalisees climatiquement               │
└──────────────────────────────────────────────────────┘
```

Badges fiabilite : Fiable (vert), Moyenne (ambre), Faible (rouge), Non verifiee (gris)
Statut : Trajectoire atteinte (vert), Non atteinte (rouge), Non evaluable (gris)

---

## Endpoints ajoutes

| Methode | Path | Role |
|---------|------|------|
| GET | `/api/tertiaire/efa/{id}/proof-events` | Journal audit conformite (50 derniers events) |

Endpoint validate enrichi avec :
- `baseline.reliability`, `current.reliability`
- `evidence_warnings` (liste)

---

## Tests (14 passes)

| Test | Verifie |
|------|---------|
| create_generates_event | Event log sur creation conso |
| update_generates_event | Event log sur update conso |
| trajectory_compute_generates_event | Event log sur recalcul trajectoire |
| proof_events_returns_events | Endpoint proof-events |
| import_invoice_is_high | Qualification source |
| declared_manual_is_medium | Qualification source |
| site_fallback_is_low | Qualification source |
| none_is_unverified | Qualification source |
| unknown_string_is_unverified | Qualification source |
| fallback_never_high | **Garde-fou critique** |
| low_reliability_baseline_generates_warning | Warning evidence |
| high_reliability_no_evidence_warning | Pas de faux warning |
| validate_returns_reliability | Fiabilite dans reponse |

---

## Limites restantes

| Limite | Impact | Sprint suivant |
|--------|--------|---------------|
| Normalisation climatique | Comparaisons biaisees | Sprint conformite suivant |
| Manifest export (checksum/hash) | Export non certifie | Sprint conformite suivant |
| Actor toujours "system" | Pas de tracking utilisateur reel | Quand IAM branche |
| Journalisation export OPERAT | Pas encore trace dans event log | Sprint suivant |
| Pas de destruction/retention | Pas de politique archivage | Futur |
