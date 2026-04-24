# Task 04 — Prompt refacto cross-pillar

**Agent cible** : `prompt-architect`
**Difficulté** : medium
**Sprint origin** : Prompts / Refacto

## Prompt exact

> Génère un prompt pour refacto consolidation SoT tarifs (YAML vs catalog.py, cf `docs/audit/followups/tarifs_sot_consolidation.md`).

## Golden output (PASS)

- [ ] Reprend la structure du followup
- [ ] Phase 0 diff exhaustif read-only
- [ ] STOP gate après Phase 0 obligatoire
- [ ] Phases 1-4 (décisions, refacto loader, tests, création skill)
- [ ] Baseline BE ancrée
- [ ] Signal post-merge vers PR principal (audit agents)
- [ ] Doctrine `feedback_context7` enforced

## Anti-patterns (FAIL)

- ❌ Phase 0 skippée
- ❌ Pas de signal post-merge
- ❌ Fait tout d'un coup (pas atomic)

## Rationale

Cas réel PROMEOS : consolidation SoT qui bloque Phase 3B. Teste reprise de followup.
