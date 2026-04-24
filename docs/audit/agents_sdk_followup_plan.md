# Agents SDK — Followup Plan (post-sprint audit)

**Cadence manuelle — pas de scheduler externe.**
**Triggers déterministes via CI + source-guards + log JSONL.**

## Review cadence

- **S+1 (2026-05-01)** : Quick pulse (10 min)
- **S+2 (2026-05-08)** : Full review (30 min)
- **M+1 (2026-05-24)** : Retrospective + décision retirement Paperclip (1 h)

## Triggers automatiques (pas de cron nécessaire)

- CI workflow `source_guards.yml` tourne à chaque PR → détecte drift structurel
- Stop hook `log_session.py` trace chaque session → `docs/audit/agent_sessions.jsonl` croît
- XFAIL strict CO₂ frontend → alerte XPASS si V120 Option C fixé silencieusement

## Checklist S+1 (10 min)

- [ ] `wc -l docs/audit/agent_sessions.jsonl` → combien de sessions via SDK agents ?
- [ ] Agents invoqués ≥ 3 fois : lesquels ? (`jq` sur JSONL)
- [ ] Agents invoqués 0 fois : lesquels ? → candidats archive ou repositionnement
- [ ] TURPE consolidation : branch créée ? (`git ls-remote origin claude/tarifs-sot-consolidation`)
- [ ] Run pilote #2 : 2 agents non couverts (proposition : `implementer` medium + `security-auditor` hard)
- [ ] Memory update ? (nouvelles constantes, patterns validés)

## Checklist S+2 (30 min)

- [ ] Cumul métriques : nb invocations / agent, taux succès estimé
- [ ] Cas d'échec remontés dans `docs/audit/agent_failures/<agent>.md` ?
- [ ] Golden task qui a FAIL en usage réel → lesquelles ajuster ?
- [ ] CLAUDE.md routing : des tâches ont-elles été mal routées ?
- [ ] Paperclip invocations résiduelles (si service tourne)

## Checklist M+1 (1 h)

- [ ] Décision retirement Paperclip : 14 jours sans invocation atteints ?
- [ ] Post-merge : CO₂ frontend cleanup peut-il être traité (followup `co2_frontend_cleanup.md`) ?
- [ ] Agent underperformer : modèle right-size (Haiku→Sonnet, ou Opus→Sonnet) ?
- [ ] Nouvelle skill nécessaire ? (pattern qui émerge dans 3+ agents)
- [ ] Prochain sprint agents (V121 ? extensions domain ?)

## Red flags (arrêt immédiat + diagnostic)

- ⚠️ Baseline tests < 6 027 BE → régression silencieuse
- ⚠️ Agent invoqué > 50 fois avec taux succès estimé < 60% → prompt cassé
- ⚠️ Source-guard FAIL en CI → hotfix P0
- ⚠️ `agent_sessions.jsonl` vide 7 jours → adoption nulle, diag CLAUDE.md routing

## Outil

`./scripts/agents_followup_digest.sh` → digest 3 min des métriques clés (lancement manuel).

## Références

- Catalogue : [agents_sdk_phase1_catalogue.md](agents_sdk_phase1_catalogue.md)
- Plan migration : [agents_sdk_phase6_migration.md](agents_sdk_phase6_migration.md)
- Retrospective : [agents_sdk_retrospective.md](agents_sdk_retrospective.md)
- Followups actifs : [followups/](followups/)
