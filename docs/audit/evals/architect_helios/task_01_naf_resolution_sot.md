# Task 01 — SoT NAF resolution

**Agent cible** : `architect-helios`
**Difficulté** : easy
**Sprint origin** : Architecture / SoT

## Prompt exact

> Un junior dev veut écrire sa propre fonction de résolution NAF dans `backend/services/new_feature.py`. Quelle est la SoT canonique existante ? Que doit-il faire ?

## Contexte fourni

- Skill : `@.claude/skills/helios_architecture/SKILL.md`
- Memory : `memory/docs_architecture_data_model.md`

## Golden output (PASS = tous cochés)

- [ ] Cite `backend/utils/naf_resolver.py:resolve_naf_code()` comme SoT
- [ ] Refuse la duplication (DRY)
- [ ] Propose `from backend.utils.naf_resolver import resolve_naf_code`
- [ ] Format ADR léger ou recommandation courte

## Anti-patterns (FAIL si présent)

- ❌ Autorise la duplication
- ❌ Écrit le code à la place du junior (violation read-only architect)
- ❌ Ignore l'existence du SoT

## Rationale

Test basique du respect SoT. Si l'agent laisse passer, les doublons NAF vont proliférer.
