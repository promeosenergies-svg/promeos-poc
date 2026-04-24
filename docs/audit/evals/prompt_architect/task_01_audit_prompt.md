# Task 01 — Génère prompt d'audit simple

**Agent cible** : `prompt-architect`
**Difficulté** : easy
**Sprint origin** : Prompts / Audit

## Prompt exact

> Génère un prompt Claude Code pour auditer les endpoints `/api/billing/*` (conformité scoring + anomalies R01-R20).

## Golden output (PASS)

- [ ] Template Phase 0 read-only + STOP gate
- [ ] Phases numérotées avec DoD
- [ ] MCP Context7 + code-review + simplify listés
- [ ] Atomic commits format
- [ ] Source-guards par phase
- [ ] Baseline tests référencée

## Anti-patterns (FAIL)

- ❌ Prompt qui démarre direct en écriture
- ❌ Pas de STOP gate
- ❌ DoD vague

## Rationale

Test du template de base. Si raté, tous les prompts générés seront bancaux.
