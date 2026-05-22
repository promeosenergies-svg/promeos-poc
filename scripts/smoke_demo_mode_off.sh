#!/usr/bin/env bash
# scripts/smoke_demo_mode_off.sh
# M2-6.A.1 (PROMEOS-SEC-2026-001) — Smoke test pré-déploiement
#
# Vérifie que DEMO_MODE est désactivé sur l'env cible. Bloque le déploiement
# si available=true (l'endpoint POST /api/auth/demo-login exposerait alors
# un JWT HELIOS valide à tout attaquant non authentifié — CWE-307).
#
# Exit codes :
#   0 — DEMO_MODE off (sécu OK, deploy autorisé)
#   1 — DEMO_MODE on (STOP déploiement, alerte sécu)
#   2 — usage invalide (URL backend manquante)
#   3 — endpoint probe inaccessible (réseau / backend down)
#   4 — réponse inattendue (format JSON cassé)
#
# Voir : docs/deploy/RUNBOOK_DEPLOY.md Gate 1.

set -euo pipefail

TARGET_URL="${1:-}"
if [ -z "$TARGET_URL" ]; then
  echo "Usage: $0 <BACKEND_URL>"
  echo "Exemple: $0 https://staging-api.promeos.io"
  exit 2
fi

echo "🔍 Smoke test DEMO_MODE OFF sur $TARGET_URL"

PROBE_URL="${TARGET_URL}/api/auth/demo-login/available"
RESPONSE=$(curl -s -m 10 "$PROBE_URL" || true)

if [ -z "$RESPONSE" ]; then
  echo "❌ Probe endpoint inaccessible : $PROBE_URL"
  exit 3
fi

# Parse JSON via Python (toujours présent — backend Python). `True`/`False`
# Python normalisé en lowercase pour comparaison stable.
AVAILABLE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(str(json.load(sys.stdin).get('available', 'unknown')).lower())" 2>/dev/null || echo "parse_error")

case "$AVAILABLE" in
  false)
    echo "✅ DEMO_MODE désactivé (available=false)"
    exit 0
    ;;
  true)
    echo "❌ ALERTE SÉCU — DEMO_MODE est ACTIVÉ en $TARGET_URL"
    echo "   Référence : PROMEOS-SEC-2026-001"
    echo "   Action : forcer PROMEOS_DEMO_MODE=false dans le manifest"
    echo "   Runbook : docs/deploy/RUNBOOK_DEPLOY.md Gate 1"
    exit 1
    ;;
  *)
    echo "❌ Réponse inattendue : $RESPONSE"
    exit 4
    ;;
esac
