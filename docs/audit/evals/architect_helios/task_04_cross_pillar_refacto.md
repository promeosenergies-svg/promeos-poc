# Task 04 — Refacto cross-pillar EMS ↔ Bill

**Agent cible** : `architect-helios`
**Difficulté** : medium
**Sprint origin** : Architecture

## Prompt exact

> Un changement dans `ems-expert` (calcul baseload) casse le shadow billing (ligne CTA). Que faire ?

## Contexte fourni

- Pillars : EMS (`backend/ems/`) et Bill (`backend/bill/`)
- Skill : `@.claude/skills/helios_architecture/SKILL.md`

## Golden output (PASS = tous cochés)

- [ ] Identifie le contrat API partagé (DTO cross-pillar)
- [ ] Propose versionning d'interface + migration
- [ ] Test d'intégration cross-pillar requis
- [ ] Délégue à `bill-intelligence` pour confirmation
- [ ] Délègue à `test-engineer` pour regression test

## Anti-patterns (FAIL si présent)

- ❌ Couple EMS et Bill (injection directe)
- ❌ Casse le contrat sans versionning
- ❌ Ignore `code-reviewer` review

## Rationale

Teste la capacité à arbitrer cross-pillar (cas réel V112/V113 billing refactor).
