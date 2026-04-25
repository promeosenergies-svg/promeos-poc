# Harness éval — 55 golden tasks (11 agents × 5)

Harness de non-régression des 11 AgentDefinitions `.claude/agents/*.md`.

## Structure

```
docs/audit/evals/
├── README.md                    # ce fichier
├── <agent_name>/
│   ├── task_01_<slug>.md        # 2 easy + 2 medium + 1 hard par agent
│   ├── task_02_<slug>.md
│   ├── task_03_<slug>.md
│   ├── task_04_<slug>.md
│   ├── task_05_<slug>.md
│   └── golden_criteria.yaml     # règles parsables pour auto-eval
└── results/
    └── run_YYYY-MM-DD.md        # output d'un run
```

## Distribution de difficulté

Chaque agent : **2 easy + 2 medium + 1 hard**.

- **easy** : mémoire factuelle (deadline, seuil, SoT file path). Test : l'agent cite la bonne valeur.
- **medium** : produit un artefact structuré (ADR court, JSON findings, diff de code). Test : format + exactitude.
- **hard** : décision architecturale avec trade-off. Test : arbitrage raisonné + délégation sortante pertinente.

## Format golden task

Chaque `task_<N>_<slug>.md` suit strictement :

```markdown
# Task <N> — <titre court>

**Agent cible** : <agent-name>
**Difficulté** : easy | medium | hard
**Sprint origin** : <module PROMEOS>

## Prompt exact
> <prompt littéral à envoyer à l'agent>

## Contexte fourni
- Fichiers : <liste précise>
- État : <branche, seed, memory entries>

## Golden output (PASS = tous cochés)
- [ ] <critère 1 mesurable>
- [ ] <critère 2>
- [ ] Format de sortie respecté

## Anti-patterns (FAIL si présent)
- ❌ <pattern erroné>
- ❌ <constante fausse>

## Rationale
<2-3 lignes justifiant la représentativité>
```

## Format golden_criteria.yaml

```yaml
agent: <name>
tasks:
  - id: task_01
    title: "<titre>"
    difficulty: easy|medium|hard
    pass_criteria:
      must_contain: ["pattern1", "pattern2"]
      must_not_contain: ["bad1"]
      delegation_expected: null | "<agent>"
    fail_if_contains: ["vague_word"]
```

## Exécution

### Mode pilote (3 tasks pour valider format)

```bash
./scripts/run_agent_evals.sh --pilot
# Lance : regulatory_expert/task_01, bill_intelligence/task_03, architect_helios/task_05
```

### Mode complet (55 tasks)

```bash
./scripts/run_agent_evals.sh
# Output : docs/audit/evals/results/run_$(date +%Y-%m-%d).md
```

### Mode ciblé (1 agent)

```bash
./scripts/run_agent_evals.sh --agent regulatory_expert
```

## Convention naming

- Dossiers : `<agent_name_with_underscores>/` (ex: `bill_intelligence/`, pas `bill-intelligence/`)
- Tasks : `task_NN_<slug_short>.md` (zero-padded, slug stable pour référence pérenne)

## Agent failures log

Chaque agent a un log dans [agent_failures/](../agent_failures/) :

```
| Date | Task | Failure mode | Root cause | Fix | Commit |
|------|------|--------------|------------|-----|--------|
```

À renseigner à chaque run révélant un FAIL.

## Retours attendus par run

1. Taux global PASS / FAIL sur 55
2. Taux par agent (5 tasks) — doit être ≥ 80% pour considérer l'agent production-ready
3. Liste FAIL avec root cause suggérée (prompt ambigu / mémoire obsolète / guardrail trop strict / délégation manquante)
4. Décisions : ajuster prompt agent, enrichir skill, refacto task trop dure ?

## Baseline attendue Phase 5

Phase 5 livre le **harness** (structure + 55 tasks). Premier run manuel (mode pilote 3 tasks) pour valider format. Baseline réelle = premier run complet post-Phase 5 (hors scope Phase 5 elle-même).

## Références

- Catalogue : [../agents_sdk_phase1_catalogue.md](../agents_sdk_phase1_catalogue.md)
- AgentDefinitions : [.claude/agents/](../../../.claude/agents/)
- Skills : [.claude/skills/](../../../.claude/skills/)
