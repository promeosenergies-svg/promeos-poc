# Task 02 — Rate limits Enedis DataConnect v5

**Agent cible** : `data-connector`
**Difficulté** : easy
**Sprint origin** : Enedis / Rate limits

## Prompt exact

> Quels sont les rate limits Enedis DataConnect v5 à respecter ? Que faire si dépassé ?

## Golden output (PASS)

- [ ] Cite rate limits Enedis (à jour via doc officielle)
- [ ] Skill `@promeos-enedis/SKILL.md` pour détails
- [ ] Back-off exponentiel + retry-after header respecté
- [ ] Monitoring metrics exposées
- [ ] Délègue à `architect-helios` si limitation nécessite batch architecture

## Anti-patterns (FAIL)

- ❌ Ignore rate limits
- ❌ Retry instantané (flood)
- ❌ Chiffres inventés

## Rationale

Opérationnel critique : dépasser les limits = banissement.
