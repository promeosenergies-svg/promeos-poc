# Runbook déploiement PROMEOS — pilote externe HELIOS / MERIDIAN

> **Statut** : runbook sécurité pré-déploiement. Sibling de
> `docs/deployment.md` (qui couvre KB + AI items). Établi M2-6.A.1.
>
> **Cible** : staging + prod du pilote externe Q3 2026.

## Pré-deploy STOP gates sécu

Tout déploiement vers staging ou prod **DOIT** valider les 3 gates ci-dessous
avant d'être annoncé live. Échec d'un gate → STOP, fix, retry.

### Gate 1 — DEMO_MODE désactivé (PROMEOS-SEC-2026-001)

**Risque** : sans cette protection, l'endpoint `POST /api/auth/demo-login`
permet à un attaquant non authentifié d'obtenir un JWT HELIOS valide en 1 clic
(token harvesting CWE-307, **malgré** le rate-limit M2-5.9.bis qui ne protège
que contre le bruteforce répété).

**Vérification automatisée** :

```bash
./scripts/smoke_demo_mode_off.sh <BACKEND_URL>
```

Exit codes :

| Exit | Signification | Action |
|------|---------------|--------|
| `0`  | DEMO_MODE off — sécu OK | Continuer |
| `1`  | DEMO_MODE **on** — alerte sécu | **STOP**, fix manifest |
| `2`  | Usage invalide (URL manquante) | Corriger appel script |
| `3`  | Endpoint inaccessible | Vérifier backend + réseau |
| `4`  | Réponse inattendue | Investiguer (endpoint modifié ?) |

**En cas d'échec exit 1** :

1. Vérifier que `docker-compose.<env>.yml` contient `PROMEOS_DEMO_MODE: "false"`
   ET `DEMO_MODE: "false"` (les 2 — défense en profondeur).
2. Vérifier qu'aucun secret / env var de la plateforme deploy (k8s ConfigMap,
   Heroku config vars, etc.) ne force `PROMEOS_DEMO_MODE=true`.
3. Redémarrer le service backend après correction.
4. Re-lancer le smoke test → exit 0 attendu.

**Vérification CI** : workflow GitHub Actions
`.github/workflows/deploy-safety-gate.yml` (déclenché manuellement
`workflow_dispatch`) qui exécute manifest grep + live smoke.

### Gate 2 — Feature flag V4 activé

Pour que le pilote HELIOS/MERIDIAN voie le Centre d'Action V4 :

```bash
# Frontend env var au build time
VITE_FEATURE_ACTION_CENTER_V4=true
```

**Vérification** : ouvrir `/action-center-v4` après login démo → doit retourner
la table V4 (et non un 404). Si 404, vérifier `FEATURE_FLAG_V4_ENABLED` backend
ET le flag frontend (les deux doivent être à `true` simultanément).

### Gate 3 — Seed Use Case A présent

Pour la démo HELIOS, les 6 items Marie Dupont doivent être seedés :

```bash
python -m backend.seeds.use_case_a_seed
sqlite3 backend/data/promeos.db \
  "SELECT COUNT(*) FROM action_center_items WHERE organisation_id=1;"
# Attendu : ≥ 6
```

## Procédure deploy standard

> Adapter selon la plateforme cible réelle (à figer en M2-6.A.3 observabilité).

1. **Pull dernière version** `claude/refonte-sol2` (tag `m2-sprint-5-done` ou
   plus récent).
2. **Build frontend** : `cd frontend && npm run build`.
3. **Migrate DB** : `cd backend && alembic upgrade head` (vérifier 0 schéma drift).
4. **Restart backend** (docker-compose / k8s rollout / Heroku release).
5. **Valider les 3 gates ci-dessus** (≥ 1 échoue → STOP).
6. **Annoncer le déploiement réussi** (canal interne + notif pilote).

## Composition stack production cible

| Composant     | Stack    | Notes |
|---------------|----------|-------|
| Backend       | FastAPI + SQLAlchemy + SQLite (POC) → PostgreSQL (V4.1+) | Port 8001 |
| Frontend      | React 18 + Vite (build statique) | Servi via nginx |
| Reverse proxy | nginx / Traefik (TLS) | À figer M2-6.A.3 |
| Storage       | Filesystem (POC) → S3 (V4.1+) | `EVIDENCE_STORAGE_BACKEND` |
| Secrets       | `.env` + plateforme env vars | **JAMAIS** dans Git |

## En cas d'incident

> Section à enrichir en M2-6.A.3 (perf budgets + observabilité).

- **Rollback** : restaurer le tag git précédent + restart.
- **Logs** : structurés JSON (`LOG_FORMAT=json`), correlation_id propagé (IS9).
- **Sécu incident** : si Gate 1 a été contourné en prod, audit immédiat des
  `event_log` 7 derniers jours (table `event_logs`, type `demo_login_success`).
- **Contact escalation** : à figer (M2-6.A.3).

## Doctrine référencée

- [`docs/dev/methode_self_review_pr.md`](../dev/methode_self_review_pr.md) — cas trunk-based M2-6
  + pause 24 h entre sous-sprints.
- [`docs/dev/methode_walkthrough_navigateur.md`](../dev/methode_walkthrough_navigateur.md) —
  walkthrough post-deploy obligatoire avant annonce live.
- [`backend/.env.example`](../../backend/.env.example) — table comportement
  `PROMEOS_AUTH_ENABLED` × `PROMEOS_DEMO_MODE` (4 combinaisons + interdites).
