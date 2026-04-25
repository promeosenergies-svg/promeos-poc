# Task 05 — Arbitrage verdict contradictoire

**Agent cible** : `qa-guardian`
**Difficulté** : hard
**Sprint origin** : Meta / Orchestration

## Prompt exact

> `code-reviewer` dit PASS (zéro P0). `security-auditor` dit FAIL (1 Critical sur `/api/sites/{id}` : `resolve_org_id` appelé mais résultat non vérifié). Qu'est-ce que tu fais ?

## Golden output (PASS)

- [ ] Reconnaît la contradiction
- [ ] Priorise `security-auditor` sur Critical (sévérité CVE > P0 code review)
- [ ] Verdict final : `FAIL`
- [ ] Délègue à `architect-helios` pour arbitrage design
- [ ] Délègue à `implementer` pour fix
- [ ] Format JSON structuré avec blockers explicites

## Anti-patterns (FAIL)

- ❌ Verdict PASS (vote majorité naïf)
- ❌ Ignore Critical sécu
- ❌ Pas de délégation d'arbitrage

## Rationale

Méta-compétence : orchestrer les findings multi-agents. Cas réel post-Phase 4 audit agents.
