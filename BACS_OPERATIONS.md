# BACS Operations — UI + Remediation + Alertes

> Date : 2026-03-16
> Commit : `6a238b9`
> Statut : Implemente, teste, pushe

---

## Ce qui est livre

### BacsRegulatoryPanel.jsx
Composant UI sobre B2B affichant les 6 axes reglementaires :

```
┌──────────────────────────────────────────────────────┐
│ BACS REGLEMENTAIRE                  [Revue requise]  │
│                                                      │
│ ⚠ Aide a la conformite — PROMEOS ne certifie pas     │
│                                                      │
│ PERIMETRE                                            │
│ Assujetti : Oui                                      │
│ Seuil : TIER1_290                                    │
│ Putile : 300 kW                                      │
│ Echeance : 2025-01-01 (en retard!)                   │
│                                                      │
│ EXIGENCES R.175-3 (3/10)                             │
│ Suivi continu             ✓                          │
│ Pas horaire               ✓                          │
│ Zones fonctionnelles      ✕                          │
│ Retention 5 ans           ✕                          │
│ ...                                                  │
│                                                      │
│ EXPLOITATION / MAINTENANCE                           │
│ Consignes ecrites : ok                               │
│ Formation : Non                                      │
│ Points de controle : Non definis                     │
│                                                      │
│ INSPECTION                                           │
│ Derniere : 2024-06-01                                │
│ Prochaine : 2029-06-01                               │
│ Findings critiques : 0                               │
│                                                      │
│ PREUVES (2/4)                                        │
│ ✕ consignes                                          │
│ ✕ formation                                          │
│                                                      │
│ BLOCKERS                                             │
│ ⚠ 7 exigence(s) fonctionnelle(s) non demontree(s)   │
│ ⚠ Formation exploitant non demontree                │
│ ⚠ Preuves manquantes : consignes, formation         │
└──────────────────────────────────────────────────────┘
```

### Remediation
Pour chaque blocker, le moteur retourne :
- **cause** : explication du probleme
- **action** : correction attendue
- **proof** : preuve a fournir
- **priority** : critical / high / medium

7 types de remediation, ordonnes par priorite.

### Alertes
- Inspection en retard → blocker + review_required
- Formation absente → blocker
- Rapport non conforme → blocker
- Findings critiques → blocker + review_required

---

## Fichiers

| Fichier | Role |
|---------|------|
| `frontend/src/components/BacsRegulatoryPanel.jsx` | Composant UI 6 axes |
| `frontend/src/services/api.js` | +getBacsRegulatoryAssessment, +getBacsComplianceGate |
| `backend/services/bacs_regulatory_engine.py` | +remediation engine (7 types, ordonne) |
| `backend/tests/test_bacs_operations.py` | 8 tests (remediation 5, alertes 2, workflow 1) |

---

## Tests (8 passes)

| Test | Verifie |
|------|---------|
| remediation_missing_functional | Exigences manquantes |
| remediation_missing_consignes | Consignes absentes |
| remediation_no_inspection | Inspection absente |
| remediation_missing_proofs | Preuves manquantes |
| remediation_ordered | Priorite respectee |
| overdue_inspection_alert | Alerte retard |
| missing_training_alert | Alerte formation |
| critical_finding_workflow | Finding critique → review |

---

## Bilan conformite complet (OPERAT + BACS)

| Zone | Commits | Tests |
|------|---------|-------|
| OPERAT (8 commits) | securite → hardening | 96 |
| BACS gate | statuts prudents | 11 |
| BACS regulatory engine | moteur 6 axes | 15 |
| **BACS operations** | **UI + remediation + alertes** | **8** |
| **Total** | **12 commits** | **130 tests** |

---

## Limites restantes

| Limite | Impact |
|--------|--------|
| BacsRegulatoryPanel pas encore branche dans une page | A integrer dans ConformitePage ou Site360 |
| Remediation en lecture seule (pas de workflow d'action) | A connecter au systeme d'actions |
| Pas de notifications email echeances | A implementer |
| Preuve = reference (pas d'upload fichier) | A connecter au stockage |
