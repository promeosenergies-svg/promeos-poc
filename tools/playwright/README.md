# Playwright Helpers

Manual screenshot and audit helpers live here.

## Conventions

- Run these scripts from the repo root.
- Generated output goes to `artifacts/playwright/` or `artifacts/audits/`.
- Curated screenshots that should remain versioned belong in `docs/evidence/curated/`.

## Typical Usage

```bash
node tools/playwright/audit-agent.mjs --help
node tools/playwright/playwright-audit-p2.mjs
```

`audit-agent.mjs` also supports `PROMEOS_FRONTEND_URL` and `PROMEOS_BACKEND_URL` for local smoke runs when the default ports are unavailable.
