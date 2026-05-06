# Audit D6 Compteur vs Meter dualité runtime — Phase D-2 hotfix Tier 1 P0.3

**Date** : 2026-05-07
**Source** : `architect-helios` agent SDK (Pilier 6 ADR-016 audit deep)
**Périmètre** : décision architecturale ADR-D-01 sur dualité Compteur/Meter post Phase D-0

## Verdict cardinal

`Compteur.sub_meter_of_id` ajouté Phase D-0 (commit `55f8afa2`) est **strictement orphelin runtime**. Confidence : **HIGH (95%)**.

| Modèle | Rôle | Self-FK | Service exploitant | Statut |
| --- | --- | --- | --- | --- |
| `Meter` (energy_models.py:65) | **SoT runtime** consommation | `parent_meter_id` | `consumption_unified_service`, `meter_unified_service`, `cost_by_period_service`, `cee_service` | ✅ branché |
| `Compteur` (compteur.py:12) | **SoT onboarding** wizard/CSV | `sub_meter_of_id` (Phase D-0) | aucun runtime | ⚠️ orphelin |

**FK Meter ↔ Compteur** : ABSENTE (string match fragile via `numero_serie` dans `meter_unified_service:218-257`).

## Décision architecturale ADR-D-01

**Option C retenue** : documenter dualité + bridge léger (~2-3h hotfix Tier 1).

Justification cardinale :
- Option B (migration Meter → Compteur) : 5-10 j-h (Meter porte 7 relationships critiques + tables enfants), hors scope hotfix.
- Option A (rollback `Compteur.sub_meter_of_id`) : 2 j-h mais perd l'optionalité onboarding wizard pré-readings.
- **Option C** : 2-3 j-h, aligne Pilier 1 (SoT respecté) + Pilier 6 (anti-pattern documenté) + différenciateur Phase D-0 préservé via Meter.

La matrice v1 §3 D6 dit "self-FK sous-compteur", **pas** "via Compteur" — la combinaison Meter (runtime) + Compteur (onboarding) bridgés honore D6.

## Plan d'implémentation Phase D-2.3

### 1. Amender docstrings `models/compteur.py:40-55` (~10 min)

Clarifier rôle onboarding vs runtime, renvoyer vers `Meter.parent_meter_id`.

### 2. Créer `services/compteur_meter_bridge.py` (~30 min)

Fonction `ensure_meter_pair(db, compteur) -> Meter` :
- Match `numero_serie` (ou `meter_id` PRM) sur `Meter.meter_id`
- Crée Meter sœur si absente
- Propage hiérarchie `Compteur.sub_meter_of_id` → `Meter.parent_meter_id`
- Pas d'event ORM SQLAlchemy (anti-pattern Pilier 1).

### 3. Source-guard `tests/source_guards/test_compteur_meter_bridge.py` (~20 min)

Assert pour tout `Compteur.sub_meter_of_id IS NOT NULL` en DB → existence `Meter.parent_meter_id` correspondant.

### 4. ADR-D-01 + ADR-016 anti-pattern (~30 min)

`docs/adr/ADR-D-01-meter-compteur-duality.md` : décision dualité.
`docs/adr/ADR-016-self-fk-runtime-wiring.md` : anti-pattern Pilier 8 candidat "Self-FK orphelin sans wiring service runtime".

## Anti-pattern Pilier 8 candidat ADR-016

> **"Self-FK orphelin sans wiring service runtime"**
>
> Toute self-FK ajoutée à un modèle SoT-onboarding doit (a) référencer un service runtime équivalent existant OU (b) déclarer un bridge explicite vers le SoT runtime. À défaut, la self-FK est rejetée en revue ADR.
>
> Détection automatisée : `grep -r "ForeignKey.*<self_table>" backend/models` ∩ `grep -L "<column_name>" backend/services/*.py`.

## Risques mitigés

- **Drift wizard** : un wizard onboarding écrit `Compteur.sub_meter_of_id` sans Meter sœur → drill-down vide. **Mitigation** : `ensure_meter_pair()` appelé post-create wizard + source-guard test.
- **Documentation trompeuse** : docstrings actuels Compteur (compteur.py:42-43) annoncent "Différenciateur PROMEOS Mid-market premium pilotage CVC/IT" mais le pilotage runtime passe par Meter. **Mitigation** : amender docstring + renvoi croisé.
- **Cross-pillar EMS aveugle** : analytics carpet_plot/cusum/signature supposent sub-meters via Meter. **Mitigation** : bridge ensure_meter_pair pré-requis dur.

## Wizards onboarding actuels — audit cible

À grepper en complément Phase D-2.3 :
- `backend/services/demo_seed/`
- `backend/api/onboarding*.py`
- `backend/services/wizard*.py`

Probable que 0 wizard touche encore `Compteur.sub_meter_of_id` (Phase D-0 vient juste de l'ajouter) → étape réduite à protection source-guard.

**Confidence verdict global** : HIGH (88%) — risque résiduel = wizards futurs non écrits qui ignoreraient le bridge (couvert par source-guard).
