#!/usr/bin/env bash
# Harness éval 55 golden tasks (11 agents × 5 tasks).
#
# Usage :
#   ./scripts/run_agent_evals.sh                     # execute 55 tasks
#   ./scripts/run_agent_evals.sh --pilot             # execute 3 tasks pilotes
#   ./scripts/run_agent_evals.sh --agent regulatory_expert   # 1 agent (5 tasks)
#
# Output : docs/audit/evals/results/run_$(date +%Y-%m-%d).md
#
# Mode semi-manuel : le script génère les invocations à faire, l'exécution
# Claude Code reste manuelle pour ce sprint (automation Phase 7+).
# Il agrège les outputs JSON et check les golden_criteria.yaml.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVALS_DIR="$REPO_ROOT/docs/audit/evals"
RESULTS_DIR="$EVALS_DIR/results"
mkdir -p "$RESULTS_DIR"

DATE=$(date +%Y-%m-%d)
RESULT_FILE="$RESULTS_DIR/run_${DATE}.md"

PILOT_TASKS=(
    "regulatory_expert/task_01_operat_deadline.md"
    "bill_intelligence/task_03_anomaly_turpe7_hph.md"
    "architect_helios/task_05_db_migration_postgres.md"
)

list_tasks() {
    find "$EVALS_DIR" -name "task_*.md" -type f | sort
}

list_agent_tasks() {
    local agent=$1
    find "$EVALS_DIR/$agent" -name "task_*.md" -type f 2>/dev/null | sort
}

run_mode() {
    local mode=$1
    local agent=${2:-}
    case "$mode" in
        --pilot)
            echo "# Pilot run — 3 tasks représentatives"
            for t in "${PILOT_TASKS[@]}"; do echo "$EVALS_DIR/$t"; done
            ;;
        --agent)
            [ -z "$agent" ] && { echo "usage: --agent <name>" >&2; exit 2; }
            echo "# Agent run — $agent"
            list_agent_tasks "$agent"
            ;;
        *)
            echo "# Full run — 55 tasks"
            list_tasks
            ;;
    esac
}

count_tasks() {
    local n
    n=$(list_tasks | wc -l | tr -d ' ')
    echo "$n"
}

main() {
    local mode="${1:---full}"
    local agent="${2:-}"

    echo "# Eval run — $DATE"          >  "$RESULT_FILE"
    echo ""                             >> "$RESULT_FILE"
    echo "Tasks totales dans harness : $(count_tasks)" >> "$RESULT_FILE"
    echo ""                             >> "$RESULT_FILE"
    echo "## Tasks sélectionnées"      >> "$RESULT_FILE"
    echo ""                             >> "$RESULT_FILE"

    while IFS= read -r task_file; do
        [ -z "$task_file" ] && continue
        local rel="${task_file#$REPO_ROOT/}"
        echo "- [ ] \`$rel\`" >> "$RESULT_FILE"
    done < <(run_mode "$mode" "$agent" | grep -v '^#' || true)

    echo ""                             >> "$RESULT_FILE"
    echo "## Mode d'emploi"            >> "$RESULT_FILE"
    echo ""                             >> "$RESULT_FILE"
    echo "1. Pour chaque task, lire le prompt exact du .md"          >> "$RESULT_FILE"
    echo "2. L'envoyer à l'agent cible via Claude Code (Task tool)"  >> "$RESULT_FILE"
    echo "3. Comparer output au \`golden_criteria.yaml\` de l'agent" >> "$RESULT_FILE"
    echo "4. Cocher PASS / FAIL + loguer si FAIL dans"              >> "$RESULT_FILE"
    echo "   \`docs/audit/agent_failures/<agent>.md\`"              >> "$RESULT_FILE"

    echo "Result file : $RESULT_FILE"
}

main "$@"
