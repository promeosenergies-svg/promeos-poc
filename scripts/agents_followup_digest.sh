#!/usr/bin/env bash
# Agents SDK — Digest followup 30 secondes.
#
# Usage : ./scripts/agents_followup_digest.sh
# Output : docs/audit/followups/digest_$(date +%Y%m%d).md + stdout
#
# Exécution manuelle. Pas de cron. Zéro bruit, 100% contrôle user.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DATE=$(date +%Y-%m-%d)
OUT="docs/audit/followups/digest_${DATE}.md"
mkdir -p docs/audit/followups

SESSIONS_LOG="docs/audit/agent_sessions.jsonl"

{
    echo "# Agents SDK — Digest $DATE"
    echo ""
    echo "## Sessions totales"
    if [ -f "$SESSIONS_LOG" ]; then
        wc -l "$SESSIONS_LOG" | awk '{print $1, "sessions"}'
    else
        echo "0 sessions (file missing)"
    fi
    echo ""
    echo "## Top agents invoqués (analyse agent_sessions.jsonl)"
    if [ -f "$SESSIONS_LOG" ] && command -v jq >/dev/null 2>&1; then
        jq -r 'select(.agent) | .agent' "$SESSIONS_LOG" 2>/dev/null \
            | sort | uniq -c | sort -rn | head -12 \
            || echo "(no agent field in log — harness doesn't populate it yet)"
    else
        echo "(jq absent ou log vide — invocations non traçables automatiquement)"
    fi
    echo ""
    echo "## Agents silencieux (0 invocation)"
    echo "11 agents catalogue : architect-helios, implementer, code-reviewer,"
    echo "test-engineer, qa-guardian, regulatory-expert, bill-intelligence,"
    echo "ems-expert, data-connector, security-auditor, prompt-architect"
    echo "À comparer manuellement au top invoqués ci-dessus."
    echo ""
    echo "## Source-guards status"
    if [ -d backend/venv ]; then
        backend/venv/bin/python -m pytest tests/source_guards/ --tb=no -q 2>&1 | tail -3
    else
        echo "(venv absent, skip)"
    fi
    echo ""
    echo "## Baseline tests BE"
    if [ -d backend/venv ]; then
        backend/venv/bin/python -m pytest backend/ tests/ --collect-only 2>&1 \
            | grep -E "tests collected" | tail -1
    else
        echo "(venv absent, skip)"
    fi
    echo ""
    echo "## Open followups"
    n=$(ls docs/audit/followups/*.md 2>/dev/null | grep -v "digest_" | wc -l | tr -d ' ')
    echo "$n followup(s) actif(s) :"
    ls docs/audit/followups/*.md 2>/dev/null | grep -v "digest_" \
        | xargs -n1 basename | sed 's/^/  - /'
    echo ""
    echo "## TURPE SoT consolidation"
    if git ls-remote origin claude/tarifs-sot-consolidation 2>/dev/null | head -1 | grep -q refs; then
        echo "✅ branche créée sur origin"
    else
        echo "❌ branche claude/tarifs-sot-consolidation absente — prompt dispo : docs/prompts/turpe_sot_consolidation.md"
    fi
    echo ""
    echo "## CO₂ frontend cleanup (V120 Option C debt)"
    if [ -d backend/venv ]; then
        backend/venv/bin/python -m pytest tests/source_guards/test_frontend_co2_cleanup.py -v 2>&1 \
            | grep -E "XFAIL|XPASS|PASSED|FAILED" | head -1 || echo "(test not found)"
    else
        echo "(venv absent, skip)"
    fi
    echo ""
    echo "## Paperclip invocations (retirement check)"
    TELEMETRY="$HOME/.paperclip/instances/default/telemetry/state.json"
    if [ -f "$TELEMETRY" ]; then
        mod_days=$(( ($(date +%s) - $(stat -f %m "$TELEMETRY" 2>/dev/null || stat -c %Y "$TELEMETRY")) / 86400 ))
        echo "Telemetry file modifié il y a $mod_days jours"
        echo "Critère retirement : 14 jours d'inactivité"
    else
        echo "(Paperclip telemetry absent)"
    fi
    echo ""
    echo "---"
    echo "Généré par scripts/agents_followup_digest.sh — revoir checklist dans docs/audit/agents_sdk_followup_plan.md"
} | tee "$OUT"

echo ""
echo "Digest écrit : $OUT"
