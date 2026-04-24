# Prompt Claude Code — Renforcement SDK agents V120 (Niveaux 1 + 2)

**Cible** : session Claude Code séparée post-merge V120.
**Branche** : `claude/sdk-agents-reinforcement` depuis `main` propre.
**Scope** : unifier SoT prompts + skills entre Subagents `.claude/agents/*.md` et SDK agents `backend/orchestration/agents/*.py`.
**MCP obligatoires** : Context7, code-review, simplify.
**Durée estimée** : 5h (N1 ~2h + N2 ~3h).

---

## Prérequis (bloquants)

- ✅ PR [#260](https://github.com/promeosenergies-svg/promeos-poc/pull/260) foundation mergée (11 Subagents + 4 skills + hooks + harness)
- ✅ V120 `claude/agents-kb-integration-s1` mergée sur `main` (followup `v120_orchestration_merge.md` CLOSED)
- Sans ces 2 merges → **STOP**, ce prompt est inexécutable.

---

## Contexte

Sprint audit agents SDK (2026-04-24) a livré **11 Subagents** `.claude/agents/*.md` raffinés par 3 rounds d'audit (vision/stratégie → véracité → memory/doctrine).

V120 avait livré **3 SDK agents Python** :
- `backend/orchestration/agents/qa_guardian.py` (`SYSTEM_PROMPT` hardcodé, 172L)
- `backend/orchestration/agents/regulatory.py` (`SYSTEM_PROMPT` + 3 MCP tools YAML, 395L)
- `backend/orchestration/agents/lead.py` (archivé par arbitrage user)

**Problème** : 2 sources de `SYSTEM_PROMPT` pour qa-guardian et regulatory (Subagent `.md` vs SDK `.py`). Risque divergence dans le temps + maintenance double.

**Cible** : Subagent `.md` = SoT unique → SDK `.py` = consumer qui charge le prompt au démarrage.

---

## Non-négociables

- Zero régression tests V120 (`backend/orchestration/tests/`)
- Zero régression baseline BE ≥ 6 027
- Atomic commits format `fix(orch-pN): Phase X — description`
- Branche `claude/sdk-agents-reinforcement` sortie de `main` propre
- Commit + push + draft PR immédiat (doctrine user)
- Pre-merge : `/code-review:code-review` + `/simplify`

---

## PHASE 0 — Audit read-only (STOP gate)

### 0.1 Vérifier prérequis merge

```bash
git checkout main && git pull --ff-only
test -d backend/orchestration/agents || { echo "V120 pas mergée"; exit 1; }
test -f .claude/agents/qa-guardian.md || { echo "PR #260 pas mergée"; exit 1; }
```

### 0.2 Extraire SYSTEM_PROMPTs actuels V120

```bash
python3 -c "
import ast, sys
for f in ['qa_guardian', 'regulatory']:
    tree = ast.parse(open(f'backend/orchestration/agents/{f}.py').read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and node.targets[0].id == 'SYSTEM_PROMPT':
            print(f'=== {f}.py ===')
            print(node.value.value[:500])
" > /tmp/v120_prompts_snapshot.txt
```

### 0.3 Diff Subagent .md vs V120 .py

Comparer pour identifier :
- Bonifications des 3 rounds d'audit présentes dans `.md` mais absentes du `.py`
- Contenu V120 à préserver (ex: bouts ops concrets `cd backend && python -m pytest...`)
- Convergences/divergences intentionnelles

Produire `docs/audit/followups/v120_vs_subagent_prompt_diff.md` (30-50L).

### ⛔ STOP GATE 0

Valider avec utilisateur :
1. Stratégie SoT : **Subagent .md = SoT unique** (default) OU fusion hybride si V120 a contenu ops non transférable dans `.md` ?
2. `lead.py` : reste archivé ou ré-activé en runner éval (Niveau 3) ?
3. Plan rollback : `v120-snapshot-agents-kb` tag de retour si régression.

---

## PHASE 1 — SoT unifiée prompts (~2h)

### 1.1 Créer `backend/orchestration/agents/_prompt_loader.py`

```python
"""Loader Subagent .md → SYSTEM_PROMPT SDK.

SoT unique: .claude/agents/<name>.md (corpus raffiné par 3 rounds d'audit).
Les SDK agents consomment le body markdown (hors frontmatter YAML).
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"


def load_system_prompt(agent_name: str) -> str:
    """Charge le body markdown de .claude/agents/<agent_name>.md (skip frontmatter)."""
    path = AGENTS_DIR / f"{agent_name}.md"
    if not path.exists():
        raise FileNotFoundError(
            f"Subagent definition missing: {path}. "
            f"Check PR #260 foundation is merged on main."
        )
    content = path.read_text(encoding="utf-8")
    parts = content.split("---\n", 2)
    if len(parts) == 3:
        return parts[2].strip()
    return content.strip()
```

### 1.2 Refacto `qa_guardian.py`

Remplacer le literal `SYSTEM_PROMPT = """..."""` par :
```python
from ._prompt_loader import load_system_prompt
SYSTEM_PROMPT = load_system_prompt("qa-guardian")
```

Préserver les `SCOPE_PROMPTS` dict (contenus ops spécifiques V120 toujours utiles).

### 1.3 Refacto `regulatory.py`

Idem avec `load_system_prompt("regulatory-expert")`.
Préserver les 3 MCP tools YAML (list_sections, read_section, find_active_at_date).

### 1.4 Tests

Créer `backend/orchestration/tests/test_prompt_loader.py` (3 tests < 40L total) :
- `load_system_prompt("qa-guardian")` retourne string non-vide sans `---`
- `load_system_prompt("inexistant")` raise `FileNotFoundError`
- Frontmatter YAML strippé (pas de `name:`, `model:` dans output)

Modifier `test_orchestration_qa.py` + `test_orchestration_regulatory.py` :
- Assertion existante "SYSTEM_PROMPT contient 'PROMEOS'" reste verte
- Ajouter assertion "SYSTEM_PROMPT contient 'SENTINEL-REG'" pour regulatory (bonif round 3)

### 1.5 Baseline

```bash
cd backend && ./venv/bin/python -m pytest orchestration/ -v
# Attendu : tous verts + 3 nouveaux tests
```

### 1.6 Atomic commit

`fix(orch-p1): Phase 1 — SoT unifiée prompts (Subagent .md → SDK consumer)`

---

## PHASE 2 — Skills canoniques en contexte SDK (~3h)

### 2.1 Enrichir `ClaudeAgentOptions`

Dans `qa_guardian.py`, `regulatory.py` :

```python
options = ClaudeAgentOptions(
    system_prompt=load_system_prompt("qa-guardian"),
    add_dirs=[str(REPO_ROOT / ".claude" / "skills")],  # 4 skills canoniques
    allowed_tools=QA_GUARDIAN_ALLOWED_TOOLS,
    disallowed_tools=QA_GUARDIAN_DISALLOWED_TOOLS,
    max_turns=AGENT_MAX_TURNS,
    cwd=str(REPO_ROOT),
    model=AGENT_MODEL,
)
```

### 2.2 Vérifier accès skills côté runtime

L'agent SDK peut maintenant `@.claude/skills/emission_factors/SKILL.md` comme un Subagent Claude Code interactif. Cohérence parfaite des constantes CO₂/TURPE/calendrier/archi.

### 2.3 Tests

`test_prompt_loader.py` ajout :
- Mock `ClaudeAgentOptions` : vérifier `add_dirs` contient chemin skills
- Si `ANTHROPIC_API_KEY` dispo : live test agent regulatory répond sur BACS 2030 en citant `@.claude/skills/regops_constants/SKILL.md`

### 2.4 Atomic commit

`fix(orch-p2): Phase 2 — skills canoniques via add_dirs dans SDK options`

---

## PHASE 3 — Source-guard unicité SoT (~1h)

### 3.1 Test `tests/source_guards/test_prompt_sot_unique.py`

```python
"""Source-guard : aucun SYSTEM_PROMPT literal dans backend/orchestration/agents/."""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ORCH_DIR = REPO_ROOT / "backend" / "orchestration" / "agents"
LITERAL_PATTERN = re.compile(r'^\s*SYSTEM_PROMPT\s*=\s*"""', re.M)


def test_no_hardcoded_system_prompt_in_orchestration():
    """SDK agents doivent charger via load_system_prompt(), pas literal."""
    if not ORCH_DIR.exists():
        return
    offenders: list[str] = []
    for py in ORCH_DIR.glob("*.py"):
        if py.name.startswith("_"):
            continue  # loader lui-même peut contenir le pattern en doc
        content = py.read_text(encoding="utf-8")
        if LITERAL_PATTERN.search(content):
            offenders.append(py.name)
    assert not offenders, (
        f"SDK agents avec SYSTEM_PROMPT literal : {offenders}. "
        f"Utiliser load_system_prompt('<agent-name>') pour SoT unique."
    )
```

### 3.2 Update doctrine

CLAUDE.md racine section "Agents Claude Code" : ajouter note :
> Les 3 SDK agents Python (`backend/orchestration/agents/`) consomment les Subagents `.claude/agents/*.md` comme SoT unique via `load_system_prompt()`. Fix prompt = un seul endroit à toucher.

### 3.3 Atomic commit

`fix(orch-p3): Phase 3 — source-guard SoT unique + doctrine CLAUDE.md`

---

## DoD globale

- [ ] V120 SDK agents chargent `.claude/agents/*.md` au démarrage via `load_system_prompt()`
- [ ] Skills `.claude/skills/` accessibles via `add_dirs` SDK
- [ ] Source-guard `test_prompt_sot_unique.py` PASS
- [ ] Baseline BE ≥ 6 027 non-régressée
- [ ] Tests V120 `backend/orchestration/tests/` 100% PASS
- [ ] 3 commits atomiques `fix(orch-pN)`
- [ ] PR draft ouverte, `/code-review` + `/simplify` exécutés
- [ ] Doctrine CLAUDE.md section agents mise à jour
- [ ] Diff produit Phase 0 committé dans followup `v120_vs_subagent_prompt_diff.md`

---

## Après merge N1+N2 — Niveau 3 optionnel (vague 2, sprint suivant)

Harness éval automatique CI :
- `lead.py` devient runner qui exécute les 55 golden tasks via SDK
- `.github/workflows/eval_weekly.yml` schedule cron hebdo (ou trigger manuel)
- Parse sortie agent vs `golden_criteria.yaml` (must_contain/must_not_contain)
- Alert si taux PASS < 80% par agent → regression détectée

Prompt Niveau 3 à produire post-feedback N1+N2 (quand premier run pilote manuel a calibré les seuils PASS réels).

---

## Signal post-merge

Une fois PR `claude/sdk-agents-reinforcement` mergée :
1. Update memory `project_agents_sdk_audit_2026_04_24.md` section Doctrine 3-layers : noter SoT unifiée Subagent → SDK
2. Update `docs/audit/agents_sdk_followup_plan.md` checklist M+1 : SDK agents utilisent skills ✓
3. Fermer followup `v120_orchestration_merge.md` si V120 intégrée
4. Evaluer si `lead.py` reste archivé ou ré-activé comme runner Niveau 3

---

**Début exécution** : Phase 0 read-only uniquement. STOP à la gate 0. Pas de code avant validation stratégie SoT.
