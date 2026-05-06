# ADR-D-01 — Dualité Compteur/Meter (Phase D-2 hotfix Tier 1 P0.3)

**Statut** : Accepté
**Date** : 2026-05-07
**Sprint** : Phase D-2 hotfix Tier 1
**Décideurs** : `architect-helios` agent SDK + audit deep multi-agents Phase D
**Révision** : 1.0

## Contexte

Phase D-0 hotfix (commit `55f8afa2`) a ajouté `Compteur.sub_meter_of_id` self-FK +
`Compteur.sub_meter_usage` String pour honorer la décision matrice v1 §3 D6 SousCompteur.

L'audit Phase D (commit `147d872b`) a révélé que :
- `Meter.parent_meter_id` (energy_models.py:107) a déjà self-FK + `sub_meters` relationship.
- 4 services exploitent **EXCLUSIVEMENT** `Meter.parent_meter_id` runtime :
  `consumption_unified_service`, `meter_unified_service`, `cost_by_period_service`,
  `cee_service`.
- `Compteur.sub_meter_of_id` Phase D-0 = **strictement orphelin runtime** (0 service consumer).
- FK Meter ↔ Compteur ABSENTE (pont implicite via `numero_serie` + `meter_id` PRM).

## Décision

**Option C retenue** : documenter dualité + bridge léger (~2-3h hotfix Tier 1).

3 options évaluées :
- **Option A — Rollback `Compteur.sub_meter_of_id`** : 2 j-h, perd l'optionalité onboarding wizard pré-readings.
- **Option B — Migration Meter → Compteur** : 5-10 j-h, hors scope hotfix (Meter porte 7 relationships critiques + tables enfants).
- **Option C — Documenter dualité + bridge** : 2-3 j-h, aligne Pilier 1 (SoT respecté) + Pilier 6 (anti-pattern documenté). ✅ **Retenue**.

## Rôles cardinaux

| Modèle | Rôle | Self-FK | Service exploitant |
| --- | --- | --- | --- |
| `Meter` | **SoT runtime** consommation/breakdown/cost | `parent_meter_id` | `consumption_unified_service` + `meter_unified_service` + `cost_by_period_service` + `cee_service` |
| `Compteur` | **SoT onboarding** wizard/CSV/manual/API import | `sub_meter_of_id` | `compteur_meter_bridge.ensure_meter_pair` (post-create) |

## Wiring cardinal

Tout wizard onboarding qui matérialise un `Compteur` avec `sub_meter_of_id` non NULL
**DOIT** appeler `services/compteur_meter_bridge.py:ensure_meter_pair(db, compteur)`
post-flush pour créer/mettre à jour le `Meter` sœur correspondant.

Le bridge propage automatiquement la hiérarchie `Compteur.sub_meter_of_id` →
`Meter.parent_meter_id` via match `numero_serie` (priorité 1) → `meter_id` PRM
(priorité 2) → `delivery_point_id` (priorité 3).

Source-guard test : `tests/source_guards/test_compteur_meter_bridge_source_guards.py`
détecte les fichiers qui écrivent `sub_meter_of_id` sans importer le bridge.

## Conséquences

### Positives

- Différenciateur Phase D-0 "pilotage CVC/IT/éclairage par sous-compteur" préservé via
  Meter (SoT runtime déjà branché).
- Onboarding wizard préservé sur Compteur (cycle de vie patrimonial avec
  TimestampMixin + SoftDeleteMixin + data_source/data_source_ref).
- Pas de breaking change DB (migration 13e Phase D-0 conservée).
- Pas de migration coûteuse Meter → Compteur (5-10 j-h économisés).

### Négatives

- Maintien d'une dualité (modèle plus complexe à comprendre pour newcomer).
- Bridge à appeler explicitement post-create (pas d'event ORM = anti-pattern Pilier 1).
- Source-guard à maintenir si nouveaux wizards ajoutés.

### Mitigations

- Docstrings amendés sur `Compteur.sub_meter_of_id` pour pointer vers `Meter.parent_meter_id`.
- Anti-pattern Pilier 8 candidat ADR-016 formalisé (`ADR-016-self-fk-runtime-wiring.md`).
- Source-guard automatisé empêche régression future.

## Anti-pattern Pilier 8 candidat ADR-016

> **"Self-FK orphelin sans wiring service runtime"**
>
> Toute self-FK ajoutée à un modèle SoT-onboarding doit (a) référencer un service
> runtime équivalent existant OU (b) déclarer un bridge explicite vers le SoT runtime.
> À défaut, la self-FK est rejetée en revue ADR.
>
> Détection automatisée : `grep -r "ForeignKey.*<self_table>" backend/models` ∩
> `grep -L "<column_name>" backend/services/*.py`.

## Liens

- Audit cardinal : [`docs/audits/AUDIT_D6_DUALITE_RUNTIME_2026_05_07.md`](../audits/AUDIT_D6_DUALITE_RUNTIME_2026_05_07.md)
- Bridge service : [`backend/services/compteur_meter_bridge.py`](../../backend/services/compteur_meter_bridge.py)
- Source-guard : [`backend/tests/source_guards/test_compteur_meter_bridge_source_guards.py`](../../backend/tests/source_guards/test_compteur_meter_bridge_source_guards.py)
- Phase D audit : [`docs/audits/AUDIT_PHASE_D_COMPLET_2026_05_07.md`](../audits/AUDIT_PHASE_D_COMPLET_2026_05_07.md)

**Confidence verdict global** : HIGH (88%) — risque résiduel = wizards futurs non
écrits qui ignoreraient le bridge (couvert par source-guard).
