# BACS Compliance Gate — Statuts prudents

> Date : 2026-03-16
> Commit : `029b3ce`
> Statut : Implemente, teste, pushe

---

## Principe

**JAMAIS de "BACS conforme" sans preuve.**

`is_compliant_claim_allowed = true` uniquement si :
- classe A ou B verifiee
- inspection completee sans findings critiques
- puissance >= seuil
- aucun blocker

---

## Statuts BACS

| Statut | Signification | Conditions |
|--------|--------------|-----------|
| `not_applicable` | Non concerne | Non tertiaire OU putile < 70 kW |
| `potentially_in_scope` | Potentiellement concerne | Tertiaire mais CVC non inventorie |
| `in_scope_incomplete` | Concerne, donnees insuffisantes | Inspection manquante |
| `review_required` | Revue requise | Classe inconnue / C-D / findings critiques |
| `ready_for_internal_review` | Pret pour revue interne | Tout OK (warnings mineurs acceptes) |

---

## Modeles enrichis

### BacsCvcSystem (+5 champs)
- `system_class` : A / B / C / D / null
- `system_class_source` : declaratif, inspection, import_doc, unknown
- `system_class_verified` : boolean
- `performance_baseline_kwh` : baseline pour detection perte efficacite
- `efficiency_loss_threshold_pct` : seuil (defaut 10%)

### BacsAsset (+2 champs)
- `bacs_scope_status` : statut perimetre
- `bacs_scope_reason` : explication textuelle

### BacsInspection (+6 champs)
- `inspector_name`, `inspector_qualification`
- `findings_json` : details [{code, severity, description}]
- `findings_count`, `critical_findings_count`
- `system_class_observed` : classe observee lors inspection

---

## Blockers (empechent ready_for_review)

| Blocker | Impact |
|---------|--------|
| Classe GTB inconnue | review_required + major warning |
| Classe C ou D | review_required + blocker |
| Aucune inspection completee | in_scope_incomplete |
| Findings critiques | review_required |

---

## Warnings (n'empechent pas ready_for_review)

| Warning | Note |
|---------|------|
| Classe declarative non verifiee | A verifier par inspection |
| Baseline performance absente | Perte efficacite non evaluable |
| Aucune evaluation BACS | Assessment absent |

---

## API

```
GET /api/regops/bacs/site/{site_id}/compliance-gate
```

Retour :
```json
{
  "bacs_status": "review_required",
  "reason": "Blocages : 1 systeme(s) sans classe GTB connue",
  "blockers": ["1 systeme(s) sans classe GTB connue"],
  "warnings": ["1 systeme(s) sans baseline performance"],
  "major_warnings": ["Classe GTB inconnue — conformite BACS non demontrable"],
  "details": {
    "putile_kw": 200,
    "systems_count": 1,
    "unknown_class_count": 1,
    "inspections_completed": 1
  },
  "is_compliant_claim_allowed": false
}
```

---

## Tests (11 passes)

| Test | Verifie |
|------|---------|
| unknown_class_never_compliant | Classe inconnue => jamais conforme |
| class_c_never_compliant | Classe C => bloquant |
| no_inspection_never_compliant | Inspection absente => pas de statut fort |
| critical_finding_blocks | Finding critique => review_required |
| non_tertiary_not_applicable | Non tertiaire => hors perimetre |
| below_threshold_not_applicable | Putile < 70 => hors perimetre |
| no_systems_potentially_in_scope | Pas de CVC => potentiellement concerne |
| all_conditions_met | Classe A verifiee + inspection => ready |
| class_b_also_ok | Classe B est conforme |
| unverified_class_generates_warning | Classe non verifiee => warning |
| no_baseline_warning | Baseline absente => warning efficacite |

---

## Bilan conformite complet (OPERAT + BACS)

| Brique | Commits | Tests |
|--------|---------|-------|
| OPERAT (securite → hardening) | 8 | 96 |
| **BACS compliance gate** | **1** | **11** |
| **Total** | **9** | **107** |
