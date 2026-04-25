# Phase 6 — Plan de migration Paperclip → Claude Agent SDK

**Date** : 2026-04-24
**Branche** : `claude/agents-phase6`
**Scope** : Plan retrait progressif Paperclip + montée en charge agents SDK `.claude/agents/*.md`.
**Prérequis** : PR #260 (Phases 0-5) mergée OU appliquée sur la branche cible.

---

## 1. Contexte rappel

Paperclip (orchestrateur multi-agent Windows) cassé depuis 14/04/2026 (cf. `memory/feedback_paperclip_windows_broken.md`). Migration vers 3 couches :

| Couche | Emplacement | Usage | Statut |
|---|---|---|---|
| Runtime API production | `backend/ai_layer/agents/` (5 agents Python) | Endpoints FastAPI | ✅ Actif |
| Orchestration dev/CI | `backend/orchestration/agents/` (3 agents SDK V120) | Scripts CI | ⚠️ Stranded `claude/agents-kb-integration-s1` |
| Délégation interactive | `.claude/agents/*.md` (11 agents SDK) | Sessions Claude Code | ✅ Livré Phase 2 |

Paperclip KB préservée `~/.paperclip/instances/default/promeos_kb/` comme **référence uniquement**.

---

## 2. Ordre de migration — 5 vagues

| Vague | Agents | Rationale | Timing cible | Statut |
|---|---|---|---|---|
| **P0** | `qa-guardian`, `security-auditor` | Protection baseline tests + org-scoping P0 blocker | S+1 | ✅ Livré (Phase 2) — adoption user à confirmer |
| **P1** | `regulatory-expert`, `architect-helios` | Crédibilité business + décisions archi | S+2 | ✅ Livré (Phase 2) — agents V120 à fusionner |
| **P2** | `implementer`, `code-reviewer`, `test-engineer` | Core dev loop | S+3 | ✅ Livré (Phase 2) |
| **P3** | `bill-intelligence`, `ems-expert`, `data-connector` | Domain experts | S+4 | ✅ Livré (Phase 2) |
| **P4** | `prompt-architect`, retirement Paperclip | Méta + cleanup | S+5 | ✅ Livré `prompt-architect` / Paperclip retrait pending |

**Timing cible par rapport à merge PR #260** (J0 = merge).

---

## 3. Critères de retrait Paperclip

Conditions cumulatives pour archiver Paperclip définitivement :

- [ ] **100% agents SDK adoptés** : 11/11 `.claude/agents/` invoqués au moins 3 fois chacun en usage réel
- [ ] **14 jours consécutifs sans invocation Paperclip** : confirmation via `~/.paperclip/instances/default/telemetry/state.json`
- [ ] **Workflows critiques migrés** :
  - [ ] Audit baseline tests → `qa-guardian` (remplace QA Release Manager)
  - [ ] Audit réglementaire → `regulatory-expert` (remplace Regulatory Analyst)
  - [ ] Revue PR → `code-reviewer` (fonction absente Paperclip, nouveau)
  - [ ] Décisions archi → `architect-helios` (remplace CTO)
  - [ ] Exécution code → `implementer` (remplace Lead Engineer)
- [ ] **Premier run harness éval** (Phase 5) avec ≥ 80% PASS par agent
- [ ] **Merge V120 `orchestration/`** sur main (followup `v120_orchestration_merge.md`)

**Décision finale archive** : utilisateur après check cumulatif.

---

## 4. Plan de rollback

Si abandon progressif Paperclip révèle un gap non anticipé :

### Rollback soft — réactiver Paperclip

- Paperclip fonctionne sur WSL (Windows Subsystem Linux) — non testé mais plausible
- KB intacte `~/.paperclip/instances/default/promeos_kb/`
- Backup tar.gz existant : `C:/Users/amine/paperclip_backup_post_enrichment_20260415_103314.tar.gz`

### Rollback hard — retour à Claude Code sans agents

- `.claude/agents/*.md` peut être supprimé sans impact (les agents sont opt-in)
- `.claude/skills/emission_factors,regops_constants,regulatory_calendar,helios_architecture/` à conserver (bénéficient à toutes les sessions)
- `.claude/settings.json` hooks peuvent être désactivés via `"hooks": {}`

### Rollback critique

- Branche `claude/agents-sdk-catalogue` identifiable via tag à poser post-merge : `v-agents-phase0-5-foundation`
- Revert commit de merge = restauration main pré-foundation

---

## 5. Métriques de succès migration

À tracker semaine par semaine post-merge :

| Métrique | Cible S+1 | Cible S+5 | Source |
|---|---|---|---|
| Invocations agents SDK / semaine | ≥ 10 | ≥ 50 | transcript Claude Code |
| Ratio `qa-guardian` invoquée avant merge PR | 50% | 100% | manual review |
| Source-guards PASS en CI | 100% | 100% | GitHub Actions |
| Incidents production dus à violation règle d'or | 0 | 0 | GitHub issues |
| Commits format canonical `fix(module-pN)` | 70% | 100% | git log |
| Invocations Paperclip | → 0 | 0 | telemetry |

---

## 6. Risques résiduels identifiés

| # | Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Baseline TURPE/accises non consolidée (followup bloqué) | Haute | Moyen — skill `tariff_constants` Phase 3B reportée | Session parallèle TURPE déjà prompte (`docs/prompts/turpe_sot_consolidation.md`) |
| R2 | V120 `orchestration/` jamais merged → 3 agents SDK CI perdus | Moyenne | Moyen — CI jobs manuels | Followup `v120_orchestration_merge.md` avec tag snapshot pour récup |
| R3 | CO₂ frontend résiduel V120 Option C → régression visible | Basse | Faible — xfail tracé | Followup `co2_frontend_cleanup.md` owner à assigner |
| R4 | IDE auto-switch branche pendant sessions multi-worktree | Moyenne | Haut — deadlock réel incident | Documenté `local_main_hygiene.md` + règle CLAUDE.md rule 10 |
| R5 | Harness éval Phase 5 jamais exécuté → baseline qualité fictive | Haute | Haut — agents dérivent sans mesure | Décision user : exécuter 3 pilotes S+1 obligatoire |

---

## 7. DoD Phase 6

- [x] Plan migration 5 vagues validé (section 2)
- [x] Critères retrait Paperclip explicites (section 3)
- [x] Plan rollback documenté (section 4)
- [x] Métriques succès définies + source de tracking (section 5)
- [x] 5 risques résiduels identifiés avec mitigation (section 6)

---

## 8. Next actions (post Phase 6)

- **User** : exécute 3 pilotes harness éval (Phase 5) pour valider format
- **User** : merge PR #260 (Phases 0-5 foundation) quand prêt
- **User OR parallel session** : lance TURPE consolidation (`docs/prompts/turpe_sot_consolidation.md`)
- **Parallel session** : merge V120 `claude/agents-kb-integration-s1` (followup `v120_orchestration_merge.md`)
- **J+14** : revue cumul métriques section 5 + décision retrait Paperclip
