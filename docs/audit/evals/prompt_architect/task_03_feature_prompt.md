# Task 03 — Prompt feature nouveau module Flex

**Agent cible** : `prompt-architect`
**Difficulté** : medium
**Sprint origin** : Prompts / Feature

## Prompt exact

> Génère un prompt pour créer le module Flex scoring NEBCO (wedge stratégique). Délègue au bon agent chaque phase.

## Golden output (PASS)

- [ ] Phase 0 audit archi Flex existant
- [ ] Phase 1 délègue ADR à `architect-helios`
- [ ] Phase 2 délègue implémentation à `implementer`
- [ ] Phase 3 délègue tests à `test-engineer`
- [ ] Phase 4 délègue pre-merge à `code-reviewer` + `qa-guardian`
- [ ] Source-guards par phase + DoD mesurable
- [ ] Context7 MCP enforced

## Anti-patterns (FAIL)

- ❌ Pas de délégation par phase
- ❌ 1 seul agent fait tout
- ❌ Pas de Context7

## Rationale

Feature complète → coordination multi-agents. Test d'orchestration.
