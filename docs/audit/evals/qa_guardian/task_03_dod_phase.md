# Task 03 — DoD Phase 3A audit agents

**Agent cible** : `qa-guardian`
**Difficulté** : medium
**Sprint origin** : Audit agents

## Prompt exact

> La Phase 3A de l'audit agents SDK claime livraison. DoD (cf docs/audit/agents_sdk_phase0_report.md DoD Phase 3) :
> - CLAUDE.md racine < 120L avec agents routés
> - 4 skills partagées créées (emission_factors, regops_constants, regulatory_calendar, helios_architecture)
> - Source-guards SG7-SG12 PASS
> Vérifie.

## Golden output (PASS)

- [ ] Vérifie `wc -l CLAUDE.md` < 120
- [ ] Vérifie existence 4 skills
- [ ] Vérifie chaque skill a `source_of_truth`, `last_verified`, `Anti-patterns`
- [ ] Lance SG7-SG12
- [ ] Verdict `PASS | FAIL` avec détails

## Anti-patterns (FAIL)

- ❌ Verdict PASS sans vérification
- ❌ Oublie un critère DoD

## Rationale

Le rôle clé qa-guardian : enforcer DoD strict.
