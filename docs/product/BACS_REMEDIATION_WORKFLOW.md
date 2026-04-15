# BACS Remediation Workflow — Boucle operationnelle fermee

> Date : 2026-03-16
> Commit : `4e0e980`
> Statut : Implemente, teste, pushe

---

## Boucle operationnelle

```
Detection (moteur reglementaire)
    │
    ▼
Blocker identifie
    │
    ▼
[Creer action corrective] ← CTA dans le panel
    │
    ▼
Action ouverte (status: open, proof: missing)
    │
    ▼
Preuve rattachee (status: ready_for_review, proof: uploaded)
    │
    ▼
Revue explicite
    ├── Acceptee → status: closed, proof: accepted
    └── Rejetee → status: open, proof: rejected
```

**Un blocker n'est JAMAIS leve automatiquement sans revue explicite.**

---

## Modele BacsRemediationAction

```
id, asset_id, blocker_code, blocker_cause, expected_action,
expected_proof_type, status (open/in_progress/ready_for_review/closed),
priority (critical/high/medium), owner, due_at,
proof_id, proof_review_status (missing/uploaded/accepted/rejected),
proof_reviewed_by, proof_reviewed_at,
resolution_notes, closed_at, closed_by
```

---

## Endpoints

| Methode | Path | Role |
|---------|------|------|
| POST | `/site/{id}/remediation` | Creer action depuis blocker |
| GET | `/site/{id}/remediation` | Lister actions |
| POST | `/remediation/{id}/attach-proof` | Rattacher preuve |
| POST | `/remediation/{id}/review-proof` | Valider/rejeter preuve |

---

## UI dans BacsRegulatoryPanel

Pour chaque remediation :
- Si action non creee : **bouton "Creer action corrective"**
- Si action creee : **badge statut** (Ouvert/En cours/A revoir/Clos) + **badge preuve** (Manquante/Fournie/Validee/Rejetee)

---

## Tests (7 passes)

| Test | Verifie |
|------|---------|
| create_from_blocker | Action creee avec statut open |
| action_prefilled | Cause + action + proof type corrects |
| attach_proof | Preuve rattachee + status ready_for_review |
| ready_for_review | Status change quand preuve presente |
| accepted_closes | Preuve acceptee → action fermee |
| rejected_reopens | Preuve rejetee → action rouverte |
| never_auto_lifted | Blocker JAMAIS leve automatiquement |

---

## Bilan conformite BACS complet

| Brique | Commit | Tests |
|--------|--------|-------|
| Compliance gate | `029b3ce` | 11 |
| Regulatory engine | `7d94ed8` | 15 |
| Operations (UI + remediation) | `6a238b9` | 8 |
| Productization (panel branche) | `1200a26` | 0 |
| **Remediation workflow** | **`4e0e980`** | **7** |
| **Total BACS** | **5 commits** | **41 tests** |

---

## Bilan conformite complet session (OPERAT + BACS)

| Zone | Commits | Tests |
|------|---------|-------|
| OPERAT | 8 | 96 |
| BACS | 5 | 41 |
| **Total** | **13** | **137** |
