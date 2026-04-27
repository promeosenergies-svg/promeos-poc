# SF6 Action Plan — Enedis Raw Archive to Functional Promotion

> **Status**: working action plan for revising `feature-enedis-sge-6-data-staging.md`
> **Created**: 2026-04-27
> **Branch**: `feature/sf6-phase`
> **Purpose**: preserve the agreed SF6 reset decisions so future sessions can revise the spec step by step without treating previous overflow scaffolding as canonical.

---

## 1. Canonical Decisions

SF6 must define the correct raw-to-functional promotion architecture from the spec first. Existing `backend/data_staging/` code, promotion endpoints, bridge helpers, and service wiring are treated as previous agent overflow and are **not canonical**.

The implementation may later reuse, rewrite, or delete pieces of that scaffolding, but the PRD and implementation plan must not be constrained by it.

### Functional Boundary

SF6 builds the promoted real-data layer from the raw Enedis archive into product-side functional tables.

What this means for the user:
- Promeos gains a reliable promoted-data backbone for real Enedis measurements.
- Existing demo/seed behavior remains stable during SF6.
- Dashboards, calculations, services, and client-facing product surfaces are **not migrated** during SF6.

### Service Migration Boundary

Service migration is a later feature, not part of SF6.

Likely sequence:
1. SF6 promotes and validates real Enedis data into functional product tables.
2. Data is backfilled once at high volume.
3. The resulting dataset is stabilized and possibly used as seed/reference data.
4. Separate future feature waves migrate services and UI surfaces to those promoted tables.

### SF5 Dependency

SF5 is no longer a future prerequisite. SF5 R6X + C68 raw ingestion has been implemented and archived.

SF6 must therefore include the new SF5 raw archive tables as first-class upstream sources:
- `enedis_flux_mesure_r63`
- `enedis_flux_index_r64`
- `enedis_flux_itc_c68`

---

## 2. Current Spec Drift To Fix

The current SF6 PRD contains useful domain decisions, but it must be updated in several places.

### Drift 1 — Bridge Wording

Current wording says no bridge exists between raw archive data and functional data.

Revision direction:
- Reframe the problem as: no **canonical, validated promotion layer** exists.
- Explicitly ignore the current `data_staging.bridge` and related service wiring as non-canonical scaffolding.

### Drift 2 — Service Migration

Current roadmap mentions SF6 service migration, and current code has partial bridge behavior.

Revision direction:
- Remove service migration from SF6.
- Keep SF6 focused on promotion, audit, validation, backlog, and operational observability.
- Add a post-SF6 feature placeholder for service migration.

### Drift 3 — SF5 Status

Current spec treats SF5 as a future inserted prerequisite.

Revision direction:
- Mark SF5 as implemented/archived.
- Update dependency wording and source coverage accordingly.

### Drift 4 — API/CLI Scaffolding

Current code has endpoints and CLI behavior produced by previous overflow.

Revision direction:
- Define the preferred API, CLI, and operational architecture from scratch.
- Do not copy current endpoints unless they still match the desired contract.

### Drift 5 — Source Coverage

Current spec covers `R4x`, `R50`, `R171`, and `R151`, but not SF5 raw tables.

Revision direction:
- Add `R63`, `R64`, and `C68` to the source coverage matrix.
- Decide source-specific routing and promoted targets.

### Drift 6 — Rebuild Requirement

The existing implementation does not satisfy the intended spec and should be rebuilt according to the revised PRD.

Revision direction:
- The implementation plan must include cleanup or replacement of non-canonical scaffolding.
- Existing tests may be reused only if they match the revised contract.

---

## 3. Open Design Questions

These must be resolved while revising the spec.

### OQ1 — R63 Promotion Target

Likely direction:
- Promote `R63` load-curve points into `meter_load_curve`.

Questions:
- Which `R63` physical quantities map to active power, reactive power, and voltage?
- Which units are allowed?
- How should `pas` values map to `pas_minutes`?
- How should `nature_point`, `type_correction`, `indice_vraisemblance`, and `etat_complementaire` affect quality?

### OQ2 — R64 Promotion Target

Likely direction:
- Promote `R64` cumulative indexes into `meter_energy_index`.

Questions:
- How do `code_grille`, `id_calendrier`, `id_classe_temporelle`, and `code_cadran` map to canonical tariff identity?
- Does `R64` need a richer target model than `meter_energy_index`?
- How should source context fields such as `contexte_releve`, `type_releve`, and `motif_releve` be preserved?

### OQ3 — C68 Promotion Target

Unresolved.

Possible directions:
- Defer C68 promotion and keep it raw-only for SF6.
- Promote selected C68 contractual/technical fields into a dedicated functional table.
- Use C68 only as PRM/meter enrichment evidence during SF6, without a promoted C68 table.

Decision needed before finalizing the data model.

### OQ4 — Functional Table Set

Current PRD defines three promoted tables:
- `meter_load_curve`
- `meter_energy_index`
- `meter_power_peak`

Questions:
- Are these still sufficient after adding `R63` and `R64`?
- Does `C68` require a fourth table?
- Should any target table include source-family-specific metadata columns, or should that remain only in audit lineage?

### OQ5 — Audit Granularity At High Volume

The PRD requires traceability for every promoted value, but full per-row event logging may become expensive at production scale.

Decision needed:
- Full event per promoted row for POC?
- Event only for updates/skips/flags, with source lineage encoded elsewhere?
- Partitioned or external audit table?

---

## 4. Revision Deep-Dive Order

Revise the SF6 spec in this order.

### Step 1 — Scope And Boundaries

Outcome:
- SF6 in/out is unambiguous.
- Service migration is out.
- Existing overflow scaffolding is explicitly non-canonical.
- SF5 is complete and included as upstream source coverage.

### Step 2 — Source Coverage Matrix

Outcome:
- One matrix lists every raw source table and supported flux family:
  - `R4H`, `R4M`, `R4Q`
  - `R50`
  - `R171`
  - `R151`
  - `R63`
  - `R64`
  - `C68`
- Each source has a preliminary status: promoted, partially promoted, or deferred.

### Step 3 — Functional Data Model

Outcome:
- Confirm target table set.
- Add any needed table for C68 or explicit deferral.
- Validate uniqueness, units, identity, and downstream semantics.

### Step 4 — Promotion Rules

Outcome:
- Define routing, value conversion, timestamp handling, quality scoring, skip/block behavior, and republication rules source by source.
- Include strict guardrails for unknown units, missing tariff identity, ambiguous PRM matching, and unparseable values.

### Step 5 — Audit, Replay, And Republication

Outcome:
- Define `PromotionRun`, `PromotionEvent`, source lineage, high-water marks, backlog replay, and replacement policy.
- Confirm what must be queryable immediately versus what can remain in raw/audit payloads.

### Step 6 — Operational Interface

Outcome:
- Define canonical CLI, API, metrics, health, and dry-run behavior.
- Ignore current overflow endpoints unless they match the desired design.

### Step 7 — Implementation Plan

Outcome:
- Produce a rebuild plan that can safely replace non-canonical scaffolding.
- Include cleanup, migrations, tests, validation on real raw data, and non-regression around the raw/product DB split.

---

## 5. Acceptance Criteria For The Revised Spec

The revised SF6 PRD is ready when:

- SF6 scope excludes service migration clearly.
- SF5 is documented as implemented and included in source coverage.
- `R63`, `R64`, and `C68` are either promoted with explicit rules or deliberately deferred with reasons.
- The target functional data model is final enough for implementation.
- PRM matching and backlog behavior are precise.
- Quality scoring and republication behavior are source-specific and mechanically implementable.
- Audit lineage is realistic for high-volume backfill.
- API/CLI/metrics are defined as preferred architecture, not inherited from overflow scaffolding.
- The implementation plan states how to rebuild or replace existing `backend/data_staging/` overflow code.
- Validation strategy includes focused unit tests, cross-DB tests, and real-data backfill checks.

---

## 6. Future Session Initialization Prompt

Use this prompt to restart work on SF6 without losing context:

```text
We are working in /Users/manocyprus/AI Projects/Promeos/promeos-poc on branch feature/sf6-phase.

Read docs/specs/action-plan-enedis-sge-6-data-staging.md first, then read docs/specs/feature-enedis-sge-6-data-staging.md.

Important context:
- Existing backend/data_staging scaffolding, promotion endpoints, bridge code, and service wiring are previous agent overflow and are not canonical.
- The revised SF6 spec must define the correct architecture from scratch.
- SF6 must not include service migration. Service migration is a later separate feature after high-volume backfill and validation.
- SF5 R6X + C68 raw ingestion is implemented and archived, so SF6 source coverage must include enedis_flux_mesure_r63, enedis_flux_index_r64, and enedis_flux_itc_c68.
- Do not edit files until we validate the section plan for the current deep dive.

Start by recapping the action plan, then propose the next section to revise.
```
