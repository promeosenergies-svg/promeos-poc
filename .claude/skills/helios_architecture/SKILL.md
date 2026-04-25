---
name: helios_architecture
description: Architecture PROMEOS HELIOS — 6 pillars (EMS/RegOps/Bill/Achat/Flex/CX), 3-layers agents (ai_layer/ runtime + orchestration/ SDK + .claude/agents/ SDK-md), data model Org->EJ->Portefeuille->Site->Bat->Compteur.
triggers: [archi, architecture, HELIOS, pillar, SoT, source of truth, data model, ai_layer, orchestration, Org, Portefeuille, Site, DeliveryPoint, ADR]
source_of_truth: docs/architecture/ + backend/services/consumption_unified_service.py
last_verified: 2026-04-24
---

# Architecture HELIOS — Mapping canonique

## Quand charger cette skill

- ✅ Toute décision ADR ou design nouveau module
- ✅ Question "où dois-je mettre ce code ?" ou "quelle est la SoT pour X ?"
- ✅ Validation cohérence cross-pillar (EMS ↔ RegOps ↔ Bill ↔ Achat)
- ✅ Arbitrage entre couches 3-layers agents (ai_layer vs orchestration vs .claude/agents)
- ❌ Ne PAS charger pour : tarifs numériques → `tariff_constants` · deadlines → `regulatory_calendar`

## Hiérarchie data model

```
Organisation (org)
  ├─ EntiteJuridique (entreprise)
  │   └─ Portefeuille (regroupement commercial)
  │       └─ Site (localisation physique, NAF, archétype)
  │           └─ Bâtiment (usage, surface)
  │               └─ Compteur (PDL/PRM/PCE)
  │                   └─ DeliveryPoint (point livraison énergie)
```

**Règle d'or org-scoping** : chaque endpoint doit filtrer par `org_id` via `services/scope_utils.py:resolve_org_id()`. Multi-tenant strict (cross-org leak = P0 sécu).

## 6 Pillars HELIOS

| Pillar | Agent owner `.claude/agents/` | SoT backend | Usage |
|---|---|---|---|
| **EMS** (Energy Management) | `ems-expert` | `backend/services/consumption_unified_service.py` | Carpet plot, CUSUM, forecasting, DJU, flex |
| **RegOps** (Regulatory) | `regulatory-expert` | `backend/regops/` + `backend/config/tarifs_reglementaires.yaml` | DT, BACS, APER, Audit SMÉ, scoring |
| **Bill** (Billing) | `bill-intelligence` | `backend/bill/` + `backend/services/billing_engine/` | Shadow billing L0-L3, TURPE 7, accises |
| **Achat** (Procurement) | `bill-intelligence` (temp) | `backend/services/achat_*` | Post-ARENH, VNU, pricing simulator |
| **Flex** (Flexibility) | `ems-expert` | `backend/services/flex_*` | NEBCO, AOFD, EcoWatt, Tempo |
| **CX** (User Experience) | UI vs `prompt-architect` | `frontend/src/` | Color-Life 80/15/5, Rail+Panel, FindingCard |

## 3-layers agents

Doctrine stricte (memory `project_agent_sdk_migration_2026_04_15.md`) :

| Couche | Emplacement | Usage | Adapter |
|---|---|---|---|
| **Runtime production** | `backend/ai_layer/agents/` | API Anthropic directe, FastAPI-compatible, endpoint-driven | Anthropic SDK Python |
| **Orchestration dev/CI** | `backend/orchestration/agents/` (V120) | Scripts ponctuels, audits, CI | Claude Agent SDK → spawn CLI |
| **Délégation interactive** | `.claude/agents/*.md` | Sessions Claude Code, routing par Task tool | Claude Code SDK |

**Ne pas mélanger** : `ai_layer/` runtime ne doit jamais spawn CLI. `.claude/agents/` Markdown ne remplace pas les agents Python production.

## Sources of truth canoniques (ne pas dupliquer)

| Domaine | SoT | Ne pas ré-implémenter |
|---|---|---|
| Consommation unifiée | `backend/services/consumption_unified_service.py` | Calculs agrégés conso |
| CO₂ émissions | `backend/config/emission_factors.py` | Facteurs CO₂ |
| Tarifs réglementaires | `backend/config/tarifs_reglementaires.yaml` | TURPE, accises, CTA (via ParameterStore) |
| NAF résolution | `backend/utils/naf_resolver.py:resolve_naf_code()` | Classification sectorielle |
| Org scoping | `backend/services/scope_utils.py:resolve_org_id()` | Multi-tenant filter |
| Scoring conformité | `backend/regops/scoring.py` + `compliance_score_service.py` | DT/BACS/APER/AUDIT scoring |
| Seed démo | `backend/services/demo_seed/orchestrator.py` | HELIOS (5 sites) / MERIDIAN (3 sites), RNG=42 |

## Règle d'or : zero business logic in frontend

Le frontend est **affichage uniquement**. Tout calcul métier (CO₂, scoring, forecasting, anomaly detection) se fait **côté backend**, exposé via API REST, consommé en React via Context/hook.

**Pattern Option C** (appliqué V115/V120) :
1. Endpoint backend retourne valeur calculée
2. Context React (ex: `EmissionFactorsContext`) fetch + cache
3. Hook (ex: `useElecCo2Factor()`) expose au composant
4. Composant utilise directement (pas de `const X = 0.052`)

## Exemples d'usage dans les prompts agents

**`architect-helios`** : ADR sur nouveau module "NEBCO scoring" → pillar Flex, owner `ems-expert`, SoT `backend/services/flex_*`, délégation à `implementer` après accept.

**`implementer`** : endpoint `/api/sites/{id}/co2` → doit appeler `get_emission_factor("ELEC")` + `resolve_org_id()`, pas de hardcode.

**`code-reviewer`** : revue PR avec calcul CO₂ → flag si hardcode hors `emission_factors.py`.

## Anti-patterns (FAIL systématique)

- ❌ **Calcul CO₂ ou TURPE dans un `.jsx`** → violation zero business logic in frontend.
- ❌ **Duplication constante canonique** (0.052 ailleurs que `emission_factors.py`) → source-guard fail.
- ❌ **Endpoint sans `resolve_org_id`** → fuite cross-org P0 sécu.
- ❌ **Mélanger `ai_layer/` et `orchestration/`** → runtime FastAPI vs CI SDK = 2 usages distincts.
- ❌ **Créer nouveau service SoT** si SoT existe déjà (ex: re-écrire `naf_resolver` au lieu d'appeler) → DRY violation.
- ❌ **Bypass ParameterStore pour tarifs** → hardcode silencieux, pas de versionnement.

## Références

- Code SoT : [backend/services/consumption_unified_service.py](../../../backend/services/consumption_unified_service.py)
- Org scoping : [backend/services/scope_utils.py](../../../backend/services/scope_utils.py)
- ADR (si existent) : [docs/decisions/adr/](../../../docs/decisions/adr/)
- Memory data model : memory/docs_architecture_data_model.md
- Memory migration V120 : memory/project_agent_sdk_migration_2026_04_15.md
- Dernière vérification : 2026-04-24
