# Workframe Contract

Shared repo boundary and file-placement rules for humans and coding workframes.

## Shared Boundary

- The only shared git boundary is `promeos-poc/`.
- Do not treat the outer `/Promeos` folder as part of the repo contract.
- Runtime code stays in place: `backend/`, `frontend/`, `e2e/`, `data/`, `scripts/`, `tools/`.

## Shared Read Zones

- `README.md`, `ROADMAP.md`, `CHANGELOG.md`
- `docs/`
- `backend/`, `frontend/`, `e2e/`, `data/`, `scripts/`, `tools/`
- `.claude/skills/`, `CLAUDE.md`, `SKILL.md`
- `.paperclip/company.json`

## Shared Write Zones

- Specs, plans, audits, and product docs under `docs/`
- Manual Playwright helpers under `tools/playwright/`
- Curated versioned evidence under `docs/evidence/curated/`
- Generated or replayable outputs under `artifacts/`

## Local-Only / Ignore-First Zones

- `.agent/reports/` — generated agent output; do not rely on it as a shared tracked location
- `.paperclip/sessions/`, `.paperclip/state/`, `.paperclip/logs/`
- editor-local settings such as `.vscode/settings.local.json`
- ad hoc screenshots, exports, and capture dumps outside `artifacts/`

## Output Policy

- Raw screenshots, Playwright dumps, and manual audit captures go to:
  - `artifacts/playwright/`
  - `artifacts/audits/`
  - `artifacts/exports/`
- Only intentionally curated evidence should be moved from `artifacts/` into `docs/evidence/curated/`.

## Optional Outer Workspace Convention

For non-git material outside the repo, use a sibling workspace layout like:

```text
../workspace/
  imports/
  exports/
  archive/
  personal/<person>/
```

Examples:

- bulk imported Enedis payloads
- one-off regulatory source dumps
- personal prompts, scratchpads, and ad hoc experiments

This keeps the repo clean while still giving both co-founders and both workframes a predictable place for non-versioned material.
