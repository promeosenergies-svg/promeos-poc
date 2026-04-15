# Documentation Index

This repo keeps product/runtime code at the repo root and groups shared documentation under `docs/`.

## Canonical Homes

- `docs/specs/` — active feature specs and implementation plans
- `docs/decisions/` — decision records, with ADRs under `docs/decisions/adr/`
- `docs/reference/` — stable feature and system reference docs used for onboarding and production-grade follow-up
- `docs/audits/general/` — standalone audits, QA reports, deep dives, and verification notes
- `docs/audits/program/` — staged multi-step audit programs and their follow-ups
- `docs/audits/agent/` — archived tracked agent reports that were previously stored in `.agent/reports/`
- `docs/roadmaps/` — sprint plans, execution roadmaps, and milestone narratives
- `docs/product/` — product, strategy, domain, and operating-model synthesis
- `docs/demo/` — demo scripts and demo-specific walkthrough material
- `docs/dev/` — developer runbooks, setup notes, and workframe conventions
- `docs/evidence/curated/` — curated screenshots and visual evidence that should remain versioned
- `docs/archive/` — tracked legacy material that should not live at repo root anymore

## Related Conventions

- Repo-wide progress tracking stays in `ROADMAP.md` at the repo root.
- Generated screenshots, audit dumps, and similar raw outputs belong in `artifacts/`, not in `docs/`.
- Shared workframe read/write rules live in `docs/dev/workframe-contract.md`.
