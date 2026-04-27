# Agents Paperclip — PROMEOS

Chaque agent doit inclure `_doctrine_header.md` en tête de son prompt système.

## Convention

```python
from pathlib import Path

DOCTRINE_HEADER = Path("agents/_doctrine_header.md").read_text(encoding="utf-8")
SYSTEM_PROMPT = DOCTRINE_HEADER + "\n\n" + agent_specific_prompt
```

## Pourquoi un dossier dédié

Les 11 AgentDefinitions Claude Code interactifs (`.claude/agents/*.md`) et les 5 agents
Python runtime (`backend/ai_layer/agents/`) couvrent les usages SDK natifs.

Ce dossier `agents/` est le point de bootstrap pour la couche Paperclip multi-agent
(architecture cible documentée dans `memory/reference_paperclip_*.md`). Il évite la
duplication du contrat doctrinal dans chaque agent.

## Test de conformité

`tests/doctrine/test_skill_and_agents_present.py::test_agents_doctrine_header_exists`
vérifie la présence du header. Toute couche d'agent ajoutée à PROMEOS Sol DOIT
ingérer `_doctrine_header.md` (équivalent à un linter doctrinal pour LLM).

## Drift detection

Le fichier `_doctrine_header.md` est la version condensée des 10 règles cardinales
de `CLAUDE.md` + `docs/doctrine/doctrine_promeos_sol_v1_1.md`. Toute évolution doctrine
v1.x DOIT répercuter dans ce header (sinon dérive entre agents et session Claude Code).
