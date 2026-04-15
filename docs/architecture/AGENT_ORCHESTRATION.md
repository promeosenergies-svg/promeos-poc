# Agent Orchestration — PROMEOS

> Migration progressive de Paperclip (`127.0.0.1:3100`) vers le **Claude Agent SDK** (Python).
> P0 livré : QA Guardian read-only.

## Distinction critique

| Couche | Module | Usage | Adapter |
|---|---|---|---|
| **Orchestration dev/CI** | `backend/orchestration/` (NOUVEAU) | QA, audits, sprints, CI/CD | Claude Agent SDK → spawn process CLI |
| **Agents production** | `backend/ai_layer/` (EXISTANT) | RegOps explainer, recommender, etc. | API Anthropic directe (light, FastAPI-compatible) |

⚠️ **Le SDK spawn un process Claude Code CLI par `query()`** (environ 1-3 s + le temps d'inférence).
Adapté aux scripts ponctuels et à la CI/CD, **pas au runtime serveur**. Pour les endpoints FastAPI, rester sur `ai_layer/`.

## Arborescence

```
backend/orchestration/                NOUVEAU (P0)
├── __init__.py
├── __main__.py                       # cd backend && python -m orchestration ...
├── config.py                         # Config centralisée (modèles, tools, chemins)
├── cli.py                            # Runner CLI (--list, --json, --dry-run)
├── agents/
│   ├── __init__.py
│   ├── qa_guardian.py                # ✅ P0 — Audit read-only
│   ├── regulatory.py                 # ⏳ P1 — DT/BACS/Billing/Achat
│   └── lead.py                       # ⏳ P1 — Orchestrateur principal
└── tools/
    └── (custom MCP tools à venir P2)

backend/ai_layer/                     EXISTANT (production)
├── agents/                           # 5 agents via API directe
├── client.py                         # AIClient (stub si pas d'API_KEY)
└── registry.py
```

## Usage

```bash
# Lister les agents
cd backend && python -m orchestration --list
cd backend && python -m orchestration --list --json

# Audit QA
cd backend && python -m orchestration qa full
cd backend && python -m orchestration qa tests
cd backend && python -m orchestration qa source-guards
cd backend && python -m orchestration qa constants
cd backend && python -m orchestration qa seed

# Sortie JSON (CI/CD)
cd backend && python -m orchestration qa full --json

# Dry run (affiche le prompt sans appeler l'API → pas besoin de clé)
cd backend && python -m orchestration qa source-guards --dry-run
```

## Sécurité — matrice par agent

| Agent | Read | Write | Bash | Network | Source-guard test |
|---|---|---|---|---|---|
| **QA Guardian** | ✅ | ❌ | ✅ (commandes lecture) | ❌ | `test_qa_guardian_is_readonly` |
| Regulatory (P1) | ✅ | ❌ | ❌ | ✅ (CRE, légifrance, bofip) | à créer |
| Lead Engineer (P1) | ✅ | ✅ (sous garde-fous) | ✅ | ❌ | à créer |

QA Guardian **n'a pas** `Write` / `Edit` / `MultiEdit` / `NotebookEdit` dans `allowed_tools`,
et les a explicitement dans `disallowed_tools`. Cette double protection est **testée** (test
`test_qa_guardian_is_readonly` qui passe en CI).

## Variables d'environnement

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | (requise pour live) | Clé API Anthropic — le SDK ne lit PAS `AI_API_KEY` |
| `AGENT_SDK_MODEL` | `sonnet` | Modèle principal (alias : `sonnet`, `opus`, `haiku`) |
| `AGENT_SDK_FALLBACK` | `haiku` | Modèle fallback |
| `AGENT_SDK_MAX_TURNS` | `15` | Limite de tours par exécution |

> **Note** : `AI_API_KEY` (utilisée par `ai_layer`) et `ANTHROPIC_API_KEY` (utilisée par le SDK)
> peuvent pointer vers la même clé Anthropic. Dupliquer la valeur dans `.env` si besoin.

## Constantes vérifiées (audit QA Guardian — scope `constants`)

| Constante | Valeur | Source | Fichier |
|---|---|---|---|
| Facteur CO₂ élec | **0.052 kgCO₂e/kWh** | ADEME Base Empreinte V23.6 | `backend/config/emission_factors.py` |
| Accise élec T1 | **30.85 €/MWh** (fév 2026+) | Loi de finances 2026 | `backend/config/tarifs_reglementaires.yaml` |
| Pénalité DT | **7 500 €** (NON-CONFORME) / **3 750 €** (À RISQUE) | Décret 2019-771 | `backend/regops/rules/tertiaire_operat.py` |
| Jalons DT | -25% (2030) / -40% (2040) / -50% (2050) | Décret 2019-771 | `backend/regops/rules/tertiaire_operat.py` |

⚠️ Piège connu : `0.0569` est un **tarif TURPE 7 HPH** en €/kWh, **PAS** un facteur CO₂.

## Roadmap migration

- [x] **P0** : QA Guardian (read-only audit) ← **livré**
- [ ] **P1** : Regulatory & Market Agent (4 rules engines en custom MCP tools) + Lead Engineer (orchestrateur)
- [ ] **P2** : Platform, Data Infra, Energy Analytics, UX/Demo
- [ ] **P3** : Retirer Paperclip du workflow
- [ ] **P4** : Évaluer Claude Managed Agents (cloud) pour les jobs CI/CD

## Liens utiles

- Smoke test SDK : `python -c "import claude_agent_sdk; print(claude_agent_sdk.__version__)"`
- Tests structurels (sans API key) : `python -m pytest backend/tests/test_orchestration_config.py -v`
- Config Paperclip pour rollback : voir `C:/Users/amine/.paperclip/instances/default/promeos_kb/`
