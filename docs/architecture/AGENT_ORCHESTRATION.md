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
backend/orchestration/                NOUVEAU (P0 + P1)
├── __init__.py
├── __main__.py                       # cd backend && python -m orchestration ...
├── config.py                         # Config centralisée (modèles, tools, chemins)
├── cli.py                            # Runner CLI (--list, --json, --dry-run, multi-agent)
├── agents/
│   ├── __init__.py
│   ├── qa_guardian.py                # ✅ P0 — Audit read-only (5 scopes)
│   ├── regulatory.py                 # ✅ P1 — Audit YAML tarifs + 3 MCP tools in-process
│   └── lead.py                       # ✅ P2 — Orchestrateur QA + Regulatory (full/quick/synthesis)
└── tools/
    └── (custom MCP tools globaux à venir)

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

# Regulatory Analyst (P1)
cd backend && python -m orchestration regulatory                    # défaut audit-coherence
cd backend && python -m orchestration regulatory audit-coherence
cd backend && python -m orchestration regulatory audit-cesures
cd backend && python -m orchestration regulatory audit-tariff
cd backend && python -m orchestration regulatory audit-cesures --dry-run

# Dry run (affiche le prompt sans appeler l'API → pas besoin de clé)
cd backend && python -m orchestration qa source-guards --dry-run
```

## Sécurité — matrice par agent

| Agent | Read | Write | Bash | Network | MCP custom | Source-guard test |
|---|---|---|---|---|---|---|
| **QA Guardian** (P0) | ✅ | ❌ | ✅ (commandes lecture) | ❌ | — | `test_qa_guardian_is_readonly` |
| **Regulatory Analyst** (P1) | ✅ | ❌ | ❌ | ❌ | 3 outils sur `tarifs_reglementaires.yaml` | `test_regulatory_module_imports` (Bash interdit, Write interdit) |
| Lead Engineer (P2) | ✅ | ✅ (sous garde-fous) | ✅ | ❌ | — | à créer |

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
- [x] **P1.1** : Regulatory Analyst + 3 custom MCP tools sur `tarifs_reglementaires.yaml` ← **livré**
- [x] **P1.2** : Lead Engineer (orchestrateur QA + Regulatory, scopes full/quick/synthesis) ← **livré**
- [ ] **P2** : Platform, Data Infra, Energy Analytics, UX/Demo
- [ ] **P3** : Retirer Paperclip du workflow
- [ ] **P4** : Évaluer Claude Managed Agents (cloud) pour les jobs CI/CD

## Custom MCP tools (Regulatory Analyst P1)

3 outils in-process déclarés via `@tool` du `claude-agent-sdk` et exposés à
l'agent via `create_sdk_mcp_server("promeos-tarifs", ...)`. Tous **read-only**.

| Tool | Input | Output | Usage |
|---|---|---|---|
| `list_sections` | — | Liste 27 sections du YAML avec `valid_from`/`valid_to`/source | Cartographie initiale, détection sources manquantes |
| `read_section` | `section_name: str` | Contenu YAML brut de la section | Lecture ciblée d'un mécanisme |
| `find_active_at_date` | `target_date: YYYY-MM-DD` | Liste des sections actives à cette date | Vérification césures (1/08/2025, 1/02/2026, 1/04/2026, etc.) |

Avantage vs `Read` brut : l'agent ne lit pas tout le YAML (473 lignes) à chaque appel,
il interroge un index sémantique. **Réduction tokens estimée : 60-80 %** pour un audit complet.

## Scopes Regulatory Analyst

| Scope | Action | Durée estimée | Coût estimé |
|---|---|---|---|
| `audit-coherence` | Audit structurel YAML (sources, dates, doublons, valeurs obsolètes) | 60-120 s | ~$0.05-0.10 |
| `audit-cesures` | Vérifie 5 césures temporelles critiques (TURPE 7, CTA 2026, ATRT 8…) | 30-60 s | ~$0.03-0.06 |
| `audit-tariff` | Audit profond d'un mécanisme spécifique | variable | variable |

## Liens utiles

- Smoke test SDK : `python -c "import claude_agent_sdk; print(claude_agent_sdk.__version__)"`
- Tests structurels (sans API key) : `python -m pytest backend/tests/test_orchestration_config.py -v`
- Config Paperclip pour rollback : voir `C:/Users/amine/.paperclip/instances/default/promeos_kb/`
