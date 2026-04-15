# BACS Regulatory Engine — Moteur reglementaire complet

> Date : 2026-03-16
> Commit : `7d94ed8`
> Statut : Implemente, teste, pushe

---

## Architecture 6 axes

```
evaluate_full_bacs(asset_id)
    │
    ├── 1. Eligibilite (tertiaire, putile, tier, renouvellement, ROI)
    ├── 2. Exigences fonctionnelles R.175-3 (10 criteres)
    ├── 3. Exploitation/maintenance R.175-4/5
    ├── 4. Inspection R.175-5-1
    ├── 5. Preuves documentaires
    └── 6. Statut final prudent
              │
              └── is_compliant_claim_allowed = False (TOUJOURS)
```

---

## Modeles crees

| Modele | Champs | Role |
|--------|--------|------|
| `BacsFunctionalRequirement` | 10 exigences R.175-3 (ok/partial/absent/not_demonstrated) | Exigences fonctionnelles |
| `BacsExploitationStatus` | consignes, formation, periodicite, controles | Exploitation/maintenance |
| `BacsProofDocument` | document_type, source, actor, file_ref, valid_until | Coffre preuves |

## Modeles enrichis

| Modele | Champs ajoutes |
|--------|---------------|
| `BacsInspection` | inspection_type, report_delivered_at, report_retention_until, settings_evaluated, functional_analysis_done, recommendations_json, report_compliant |

---

## Exigences fonctionnelles R.175-3

| Exigence | Champ | Statut possible |
|----------|-------|----------------|
| Suivi continu | continuous_monitoring | ok/partial/absent/not_demonstrated |
| Pas horaire | hourly_timestep | idem |
| Zones fonctionnelles | functional_zones | idem |
| Retention mensuelle 5 ans | monthly_retention_5y | idem |
| Valeurs de reference | reference_values | idem |
| Detection pertes efficacite | efficiency_loss_detection | idem |
| Interoperabilite | interoperability | idem |
| Arret manuel | manual_override | idem |
| Gestion autonome | autonomous_management | idem |
| Propriete donnees | data_ownership | idem |

Coverage = ok_count / 10 * 100%

---

## Exploitation/maintenance R.175-4/5

| Critere | Type | Impact si absent |
|---------|------|-----------------|
| Consignes ecrites | ok/partial/absent | Blocker |
| Formation exploitant | boolean + date | Blocker |
| Points de controle definis | boolean | Blocker |
| Processus reparation | boolean | Warning |

---

## Preuves attendues

| Type | Obligatoire |
|------|-------------|
| attestation_bacs | Oui |
| rapport_inspection | Oui |
| consignes | Oui |
| formation | Oui |
| derogation_tri | Si TRI > 10 ans |
| interop_certificat | Si applicable |

---

## Statut final

| Statut | Condition |
|--------|----------|
| not_applicable | Non tertiaire OU putile < 70 kW |
| potentially_in_scope | CVC non inventorie |
| review_required | Exigences non demontrees / inspection en retard / findings critiques / preuves manquantes |
| ready_for_internal_review | Tous les axes couverts, aucun blocker |

**JAMAIS de `is_compliant_claim_allowed = true`** — par design du moteur.

---

## API

```
GET /api/regops/bacs/site/{site_id}/regulatory-assessment
```

Retour complet : eligibilite + 10 exigences + exploitation + inspection + preuves + statut final.

---

## Tests (15 passes)

| Test | Verifie |
|------|---------|
| above_290_tier1 | Tier 1 correct |
| between_70_290_tier2 | Tier 2 correct |
| below_70_not_applicable | Hors perimetre |
| renewal_detected | Renouvellement |
| all_not_demonstrated | Exigences vides = 0% |
| missing_zones_blocks | Zone absente detectee |
| all_ok_passes | 100% couverture |
| absent_consignes_blocks | Consignes absentes |
| no_training_blocks | Formation absente |
| overdue_blocks | Inspection en retard |
| non_compliant_report | Rapport non conforme |
| missing_proofs | Preuves manquantes |
| never_compliant | JAMAIS compliant |
| ready_when_complete | Ready si tout OK |
| review_when_functional_missing | Review si exigences manquantes |

---

## Bilan conformite complet (OPERAT + BACS)

| Zone | Commits | Tests |
|------|---------|-------|
| OPERAT (8 commits) | securite → hardening | 96 |
| BACS gate (1 commit) | statuts prudents | 11 |
| **BACS regulatory engine (1 commit)** | **moteur complet** | **15** |
| **Total** | **10 commits** | **122 tests** |

---

## Limites restantes

| Limite | Impact |
|--------|--------|
| Pas d'UI BACS regulatory (API seule) | Frontend a enrichir |
| Exigences fonctionnelles saisies manuellement | Pas d'auto-detection |
| Pas de workflow d'approbation inspection | Approbation manuelle |
| Pas de lien automatique inspection → preuve | Lien via linked_entity |
| Pas d'alertes automatiques echeance | A implementer |
