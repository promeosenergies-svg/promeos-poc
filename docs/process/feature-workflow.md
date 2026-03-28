# Feature Development Workflow

Framework for developing features from idea to merge. Each step has a clear deliverable and exit criteria.

---

## The 7 Steps

### 1. SPEC — Define functional requirements

Iterate on a spec/PRD file (`docs/specs/feature-{name}.md`) until the functional needs are precise and unambiguous.

**Deliverable:** Spec file with context, scope, requirements, schemas, edge cases, and out-of-scope section.

**Exit criteria:**
- Every requirement is testable (can write an acceptance check for it)
- Scope boundaries are explicit (what's in, what's out, what's deferred)
- Domain vocabulary is defined

**Typical iterations:** 2–5 rounds. The spec is never "v1 and done."

---

### 2. REVIEW — Challenge the spec

Structured review before any implementation planning. Goal: surface hidden assumptions, edge cases, and architecture decisions.

**Deliverable:** Decisions table appended to the spec (question / decision / justification).

**Format:** For each area of the spec, produce:
- **Confirmations** — "I understand X works like Y" (validates shared understanding)
- **Questions** — "What happens when Z?" (surfaces gaps)
- **Challenges** — "Have you considered alternative A instead of B?" (stress-tests choices)

**Exit criteria:**
- All open questions resolved with explicit decisions
- Edge cases identified and handled (or explicitly deferred)
- No "it depends" left — every ambiguity has a concrete answer

**Why this step matters:** In SF4, the review Q&A surfaced 15+ architecture decisions (error history strategy, retry semantics, concurrency model, dry-run behavior). Without it, the plan would have been built on assumptions that would have broken during implementation.

---

### 3. PLAN — Break into implementable phases

Create an implementation plan (`docs/specs/plan-{name}-implementation.md`) that decomposes the spec into ordered phases, each independently codeable and testable.

**Deliverable:** Plan file with phases, each containing:
- Files to create/modify
- Code snippets or pseudocode for key logic
- Test cases per phase
- Verification command to run after the phase

**Principles:**
- Each phase produces a working, testable increment (no "phase 3 depends on phase 5")
- Phase granularity = one focused commit (30min–2h of work)
- Tests are specified alongside code, not as an afterthought
- Reference files listed (existing patterns to follow in the codebase)

**Exit criteria:**
- Every spec requirement maps to at least one phase
- Each phase has explicit test cases
- Commit sequence is defined

---

### 4. BUILD — Code and test each phase

Implement phases sequentially. Each phase = code + tests + passing test suite.

**Per phase:**
1. Write the code
2. Write/update tests
3. Run phase-level tests: `pytest <module>/tests/ -x -v`
4. Commit with conventional commit message

**Rules:**
- Never skip tests for a phase ("I'll test it later" = tech debt)
- If a phase reveals a spec gap, update the spec and plan before continuing
- If tests fail, fix before moving to the next phase

---

### 5. VERIFY — Walk spec against implementation

After all phases are built, go back to the spec and verify every requirement point-by-point.

**Deliverable:** Checklist (can be informal) confirming each spec requirement is met.

**Process:**
- Read the spec top to bottom
- For each requirement, confirm: is it implemented? is it tested? does it match the spec exactly?
- Flag any deviations, missing pieces, or things that drifted during implementation

**Why this step matters:** Implementation drift is real. In SF4, the CLI report was missing the `permanently_failed` counter — a spec requirement that slipped through because we didn't do a systematic check. This step catches those gaps before they reach PR review.

---

### 6. VALIDATE — Real-world smoke test

Run the feature against real data or realistic conditions, not just test fixtures.

**Deliverable:** Evidence that the feature works end-to-end in a realistic scenario.

**Examples:**
- Ingestion pipeline: run against actual flux files, check DB state
- API endpoint: call from a REST client, verify response shape
- UI feature: manual walkthrough of the user flow
- Batch job: run with production-scale data subset

**Why this step matters:** Test fixtures are controlled. Real data has surprises (encoding issues, unexpected formats, edge cases in actual files). The SF2 real-file test (`ingest_real_db.py`) caught issues that synthetic fixtures didn't.

---

### 7. SHIP — PR, review, merge

Create the PR, get it reviewed, merge.

**Deliverable:** Merged PR on `main`.

**Process:**
- Create PR with summary, test plan, and any manual verification steps
- Run full test suite: backend + frontend
- User reviews and approves
- Merge (no auto-merge)

---

## Tracking Progress

Feature progress is tracked in `ROADMAP.md` at the repo root. Each feature shows its current step (1–7) and key references (spec, plan, PR).

## Adapting the Framework

Not every feature needs all 7 steps at full intensity:
- **Small fixes** (< 1 file, obvious change): steps 1–3 can be lightweight or mental-only
- **Large features** (multi-phase, new domain): all steps at full rigor
- **Refactors**: skip step 6 (validate) if covered by existing test suite

The key invariant: **never skip REVIEW (2) or VERIFY (5)** — those are where the most rework is prevented.
