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

## Personal Workspace (mandatory)

No personal material lives inside `promeos-poc/`. Ever. Every co-founder
has a dedicated out-of-repo workspace that git does not see:

```text
../workspace/personal/<person>/
  agents/       — personal Claude agents, custom prompts
  rules/        — personal coding rules, preferences
  prompts/      — scratch prompts, experiments
  config/       — machine-specific configs, tokens, keys
  experiments/  — one-shot scripts, throwaway branches
  data/         — personal data imports, regulatory dumps,
                  client exchanges in flight
  scripts/      — personal automation scripts
  notes/        — scratchpads, meeting notes, drafts
```

Rules:

- This workspace is created manually by each person, never tracked by git.
- Nothing here ever becomes a runtime dependency of the shared repo. If
  code in `backend/` or `frontend/` needs a file from here, that code must
  also work when the workspace is absent.
- When personal material matures into something shared, it gets explicitly
  promoted into the right zone inside `promeos-poc/` through a PR:
  `.claude/skills/` for reusable skills, `docs/` for documentation,
  `backend/` / `frontend/` for code, `tools/` for shared scripts.
- Promotion is a deliberate act, not an accident.

What belongs in the personal workspace instead of the repo:

- Raw imports from regulators (Enedis payloads, CRE bulletins, RTE feeds)
  before they are curated into `docs/` or `data/`
- Personal Claude Code agent definitions and prompts
- `.env.local`, local tokens, API keys
- Ad-hoc SQL scratch files, quick investigation notebooks
- Screenshots from exploratory sessions
- Draft plans and meeting notes before they become specs

## Sharing Informally with a Co-founder

When you want to share a note, draft, or question with the other co-founder
without going through a full spec PR, **use GitHub Draft PRs**, not an
in-repo drafts folder.

- Open the PR in **draft mode** with a clear title and short description.
- The other co-founder gets notified and can comment asynchronously.
- When the discussion is resolved, either merge the PR (if it became real
  content) or close it (if it was just a question).
- Nothing rots in the repo because closing a draft PR leaves zero trace
  on `main`.

Why not a `docs/drafts/` or `docs/notes/` folder: every team that creates
one turns it into a graveyard within three months. Draft PRs are
self-archiving, indexed, and already natively supported by GitHub.

For true async discussions that are not tied to a code change, use
GitHub Discussions on the repo (if enabled).

## Merge Process (autonomous)

`main` is protected. No direct push. Every change lands through a PR,
but each co-founder merges their own PRs autonomously — no cross-approval
required by default.

Required for every PR targeting `main`:

1. Branch named with a clear prefix: `feat/`, `fix/`, `chore/`, `docs/`,
   `refactor/`, `test/`, `wip/`.
2. PR description states intent in one line and lists the zones touched
   (`backend/`, `frontend/`, `docs/`, etc.).
3. CI green (backend pytest + frontend vitest).
4. Branch up to date with `main` at merge time — GitHub enforces this
   via the "require branches to be up to date before merging" setting.
   This is the single rule that would have caught the V119 rebase
   accident of `chore/repo-layout-workframe-cleanup`.
5. One intent per PR. No code change sneaks into a "chore" or "docs" PR.
6. Delete the branch after merge (or mark `wip/` branches explicitly).

### Commit message discipline

A commit message must honestly describe every zone the commit touches.

- `chore:` and `docs:` prefixes are reserved for commits that **only**
  touch their stated zone. A "chore: reorga" that silently modifies
  `backend/routes/*.py` is banned — the zone must appear in the message.
- Vague messages like `"Reorga"`, `"WIP"`, `"fix"` without a subject are
  banned on `main`. They make it impossible to review a rebase.
- If a commit touches `backend/`, `frontend/`, `.github/`, or `data/`,
  the message must explicitly mention it.

### Wait-for-eyes zones (voluntary review)

Autonomy does not mean recklessness. For the following five zones, the
author **voluntarily** requests a review from the other co-founder before
merge, even though the branch protection does not require it:

- `backend/services/billing/*` — shadow billing calculations, every line
  affects customer invoicing
- `backend/services/auth_*`, `backend/middleware/auth.py` — authentication
  and authorization
- `backend/models/*.py` touching migrations or column deletions
- `backend/services/compliance_*` — regulatory compliance with legal impact
- `.github/workflows/*` — CI/CD pipelines

For everything else (UX, nav, docs, reorgs, scripts, tests, frontend
components, new features not touching the five zones above), merge
autonomously without waiting.

## Pre-merge Checklist

Before marking a PR ready for merge (draft → ready, or direct merge for
autonomous PRs), the author runs the following self-check:

- [ ] Self-review of the full diff in GitHub, not just locally
- [ ] `git diff --name-only main..HEAD -- backend/ frontend/src/ .github/`
       returns empty if the PR is labelled `chore:` or `docs:`
- [ ] `/code-review` run on PRs touching code (bugs, security, regressions)
- [ ] `/simplify` run on PRs touching code (reuse, dead code, over-engineering)
- [ ] Tests pass locally: `cd backend && python -m pytest tests/ -q`
       and `cd frontend && npx vitest run`
- [ ] No file larger than 5 MB added to git
- [ ] No `.env`, `.env.local`, `*.bak`, `*.db`, or secret in the diff
- [ ] No machine-specific path (`C:\Users\...`, `/home/...`) in the diff
- [ ] Commit messages honestly list all zones touched
- [ ] Branch is up to date with `main` (rebase if GitHub complains)
- [ ] For wait-for-eyes zones, the other co-founder has been pinged

Reviewer checks (when a review happens):

- [ ] The diff matches the stated intent (scope discipline)
- [ ] No V-sprint feature silently reverted (rebase check on code files)
- [ ] Commit messages are honest about zones touched
- [ ] Merge strategy is clear (squash is the default)
