#!/usr/bin/env bash
# PROMEOS — Source guards CI : Design System & grammaire L11 (Sprint Grammaire v1.2).
#
# Exécuté par le hook pre-commit (.husky/pre-commit) et dans .github/workflows.
# Chaque guard scanne les fichiers pages/*.jsx pour détecter les anti-patterns
# architecturaux qui auraient échappé aux source-guards Vitest (lesquels ne
# couvrent que les fichiers explicitement listés).
#
# Convention exit code :
#   0 = tous les guards verts
#   1 = au moins un guard a détecté une violation (build doit échouer)
#
# Phase F.7 ajoute :
#   - Guard A : kpi-not-inline-in-hub-pages (anti-drift KPI inline)
#
# Usage local :
#   bash scripts/source_guards_design_system.sh
#
# Usage CI :
#   - run: bash scripts/source_guards_design_system.sh

set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"
cd "$REPO_ROOT"

EXIT_CODE=0

# ──────────────────────────────────────────────────────────────────────────
# Guard A — kpi-not-inline-in-hub-pages
# ──────────────────────────────────────────────────────────────────────────
#
# Cible : 7 pages-hub L11 (cockpit/jour livré + 5 hubs Phase 3.5 + cockpit
# stratégique). Empêche la récidive du bug architectural identifié en audit
# Phase D : KpiTriptychCard inline 130 lignes dans CockpitJour.jsx avant F.1.
#
# 2 patterns détectés :
#   1. className contenant `kpi-(card|icon|value|delta|eyebrow|label|foot|unit)`
#      = JSX KPI inline (au lieu d'utiliser <HubKpiCard />)
#   2. Définition locale `function KpiTriptychCard(` (ou variantes nommées
#      KpiCard / MetricCard / KpiBlock) = composant à extraire dans
#      components/grammar/hub/.
#
# Skip : si la page n'existe pas (Phase 3.5 pas encore livrée).
echo "→ Guard A : kpi-not-inline-in-hub-pages"

HUBS="CockpitJour Energie Conformite BillIntel BillIntelPage Achat AchatPage Patrimoine PatrimoinePage Cockpit CockpitStrategique CockpitDecision"
GUARD_A_VIOLATIONS=0

for page in $HUBS; do
  file="frontend/src/pages/${page}.jsx"
  [ ! -f "$file" ] && continue

  # Pattern 1 : className kpi-* inline
  if grep -qE 'className=["'"'"'][^"'"'"']*\bkpi-(card|icon|value|delta|eyebrow|label|foot|unit)\b' "$file"; then
    echo "❌ $file contient du JSX KPI inline (className kpi-*) — utiliser <HubKpiCard /> primitive"
    GUARD_A_VIOLATIONS=$((GUARD_A_VIOLATIONS + 1))
  fi

  # Pattern 2 : composant local KPI nommé
  if grep -qE 'function (KpiTriptychCard|KpiCard|MetricCard|KpiBlock)\s*\(' "$file"; then
    echo "❌ $file contient une définition locale de composant KPI — extraire vers components/grammar/hub/"
    GUARD_A_VIOLATIONS=$((GUARD_A_VIOLATIONS + 1))
  fi
done

if [ "$GUARD_A_VIOLATIONS" -eq 0 ]; then
  echo "  ✓ Guard A passé (0 violation sur $(echo "$HUBS" | wc -w | tr -d ' ') pages-hub scannées)"
else
  echo "  ✗ Guard A : $GUARD_A_VIOLATIONS violation(s) détectée(s)"
  EXIT_CODE=1
fi

# ──────────────────────────────────────────────────────────────────────────
# Sortie globale
# ──────────────────────────────────────────────────────────────────────────

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "✓ Tous les guards Design System sont verts"
fi

exit "$EXIT_CODE"
