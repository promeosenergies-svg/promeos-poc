# Followup — Merge V120 orchestration/ sur main (P1)

**Origine** : Audit Agents SDK — Phase 0 (2026-04-24) faille #1
**Sévérité** : P1 — travail stranded
**Hors scope** : audit agents catalogue (branche séparée `claude/agents-kb-integration-s1`)

## Problème

11 commits locaux sur `claude/agents-kb-integration-s1` contiennent des artefacts critiques non accessibles depuis `main` :

- `backend/orchestration/` : module SDK complet (3 agents, 14 MCP tools, 729 L)
- `backend/routes/config_emission_factors.py` + `config_price_references.py` : endpoints Option C
- `frontend/src/contexts/EmissionFactorsContext.jsx` + `PriceReferenceContext.jsx`
- `.github/workflows/qa-orchestration.yml` : CI jobs
- ~50 tests backend + frontend (0 régression prouvée)
- 26 bugs réels découverts par les agents (cf. memory V120)

## État sécurisé (2026-04-24)

- ✅ Branche pushée : `origin/claude/agents-kb-integration-s1`
- ✅ Tag posé : `v120-snapshot-agents-kb` sur origin
- ✅ Stash patch sauvé : `/tmp/v120-stash-20260424.patch`
- ✅ 3 agents extraits : `/tmp/v120_{qa_guardian,regulatory,lead}.py`

## Audit agents SDK : utilisation prévue

**Ajustement 3 addendum** : extract system prompts (pas cherry-pick fichiers).

- `qa_guardian.py` V120 → base système prompt pour `.claude/agents/qa-guardian.md`
- `regulatory.py` V120 → base système prompt pour `.claude/agents/regulatory-expert.md`
- `lead.py` V120 → arbitrage architect-helios vs implementer (Phase 2, à documenter dans `docs/audit/agents_sdk_phase2_decisions.md`)

## Action proposée pour merge complet V120

### Option A — Merge via PR (recommandé)

1. Ouvrir PR `claude/agents-kb-integration-s1` → `main`
2. Review par utilisateur (beaucoup de conflits attendus : V115 Yannick déjà mergée ailleurs)
3. Resolve conflits + squash si nécessaire
4. Merge

### Option B — Cherry-pick sélectif

Si conflits trop lourds :
- Cherry-pick fichier par fichier (orchestration/, contexts Option C, tests)
- Demande discipline git carrée

### Prérequis

- Merge CX Sprint 3 + 4 de Yannick (V115 rebase) avant d'attaquer V120 pour minimiser conflits
- Vérifier que les 26 findings V120 ne sont pas déjà corrigés ailleurs

## Lien avec audit agents SDK

- **Bloque rien** dans l'audit Phase 1-6 (extract prompts suffit)
- **Débloquerait** : re-utilisation directe des 3 agents SDK (`backend/orchestration/`) au lieu de passer par `.claude/agents/*.md` uniquement
- Peut être traité en **parallèle** de l'audit

## Owner

À assigner. Estimation : ~1 journée (merge + resolve + tests).

## Références

- Branche : `claude/agents-kb-integration-s1` (origin)
- Tag snapshot : `v120-snapshot-agents-kb` (origin)
- Memory : `project_agent_sdk_migration_2026_04_15.md`
- 14 commits détaillés : `git log v120-snapshot-agents-kb --oneline -20`
