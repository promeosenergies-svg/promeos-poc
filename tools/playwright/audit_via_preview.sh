#!/usr/bin/env bash
# Phase 25 — Audit Playwright via vite preview (mode prod) au lieu de vite dev.
#
# Pourquoi : `npm run dev` recompile les bundles lazy à chaque page.goto, ce qui
# sature l'IPC Playwright↔Chromium et fait timeout 13/16 routes (cf
# Phase 23.bis + Phase 24.1). En `vite build && vite preview`, les bundles
# sont déjà compilés → 16/16 routes hydratées sub-1s.
#
# Usage :
#   bash tools/playwright/audit_via_preview.sh                 # 16 routes + manifest
#   bash tools/playwright/audit_via_preview.sh --quick         # network count only (2 routes)
#
# Pré-requis :
#   - backend `:8001` UP (`cd backend && python main.py`)
#   - port 5176 libre (preview dédié, ne conflict pas avec dev sur 5175)
#
# Output :
#   - tools/playwright/captures/phase25_prod/<route>.png × 16
#   - tools/playwright/captures/phase25_prod/audit_manifest.json
#   - docs/sprints/SPRINT_RETRO_COCKPIT_DUAL_SOL2/outputs/network_count_*_prod.json

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PREVIEW_PORT=5176
PREVIEW_URL="http://127.0.0.1:${PREVIEW_PORT}"
QUICK_MODE=${1:-}

echo "──────────────────────────────────────────────────────────────"
echo "Phase 25 — Audit Playwright via vite preview (mode prod)"
echo "──────────────────────────────────────────────────────────────"

# 1. Build prod
echo "[1/4] vite build (frontend prod)…"
( cd frontend && npx vite build > /tmp/vite_build.log 2>&1 )
if [ $? -ne 0 ]; then
  echo "❌ vite build a échoué — voir /tmp/vite_build.log"
  exit 1
fi
echo "✓ build prod OK"

# 2. Cleanup éventuel preview précédent
echo "[2/4] cleanup preview existant sur :${PREVIEW_PORT}…"
PREVIEW_PID=$(lsof -ti:${PREVIEW_PORT} 2>/dev/null || true)
if [ -n "$PREVIEW_PID" ]; then
  kill -9 "$PREVIEW_PID" 2>/dev/null || true
  sleep 1
fi

# 3. Lancement preview en background
echo "[3/4] vite preview --port ${PREVIEW_PORT}…"
( cd frontend && nohup npx vite preview --port ${PREVIEW_PORT} --host 127.0.0.1 > /tmp/vite_preview.log 2>&1 & )
sleep 3

# Sanity check
HTTP=$(curl -sf -m 5 "${PREVIEW_URL}/" -o /dev/null -w "%{http_code}" || echo "000")
if [ "$HTTP" != "200" ]; then
  echo "❌ vite preview n'a pas démarré (HTTP $HTTP) — voir /tmp/vite_preview.log"
  exit 1
fi
echo "✓ preview UP sur ${PREVIEW_URL}"

# 4. Audit Playwright
echo "[4/4] Playwright audit 16 routes…"
if [ "$QUICK_MODE" == "--quick" ]; then
  # Mode rapide : juste les 2 routes Cockpit + network count
  node tools/playwright/count-network-requests.mjs \
    --url=${PREVIEW_URL}/cockpit/strategique \
    --output=docs/sprints/SPRINT_RETRO_COCKPIT_DUAL_SOL2/outputs/network_count_strategique_prod.json
  node tools/playwright/count-network-requests.mjs \
    --url=${PREVIEW_URL}/cockpit/jour \
    --output=docs/sprints/SPRINT_RETRO_COCKPIT_DUAL_SOL2/outputs/network_count_jour_prod.json
else
  FRONT_URL=${PREVIEW_URL} \
  OUT_DIR=tools/playwright/captures/phase25_prod \
  node tools/playwright/audit_phase17_all_routes.mjs
fi

# 5. Cleanup preview
PREVIEW_PID=$(lsof -ti:${PREVIEW_PORT} 2>/dev/null || true)
if [ -n "$PREVIEW_PID" ]; then
  kill -9 "$PREVIEW_PID" 2>/dev/null || true
fi

echo ""
echo "──────────────────────────────────────────────────────────────"
echo "✓ Phase 25 audit terminé"
echo "──────────────────────────────────────────────────────────────"
echo "  Captures : tools/playwright/captures/phase25_prod/"
echo "  Manifest : tools/playwright/captures/phase25_prod/audit_manifest.json"
if [ "$QUICK_MODE" == "--quick" ]; then
  echo "  Network  : docs/sprints/SPRINT_RETRO_COCKPIT_DUAL_SOL2/outputs/network_count_*_prod.json"
fi
