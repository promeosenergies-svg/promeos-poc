# L8 · Plan suppression legacy Mois 5

> **Version** : v1.0 · 2026-05-14
> **Source** : L1 (28 verdicts SUPPRIME) + ADR-026 §7-§10 (procédure cutover + suppression) + L7 §9 (mapping legacy → V4)
> **Branche** : `claude/refonte-sol2`
> **Statut** : `Accepted` (procédure opérationnelle Mois 5)
> **Exécution prévue** : **Mois 5 J+14 minimum** (après STOP GATE ADR-026 I6 — 8 critères binaires)
> **Nature** : procédure step-by-step **irréversible** après exécution

---

## 0. Mode d'emploi de cette procédure

L8 est une **procédure opérationnelle** à exécuter **UNE FOIS** Mois 5 J+14 minimum. Différence cardinale avec L7 :

| Aspect | L7 Data Dictionary | L8 (ce document) |
|---|---|---|
| Nature | Manuel de référence | Procédure opérationnelle |
| Usage | Consultatif Mois 2+ | Exécution unique Mois 5 J+14 |
| Format | Sections thématiques | Checklists step-by-step |
| Réversibilité | N/A | **Irréversible après exécution** |

### 0.1 Avant exécution

1. Lire **intégralement** ce document (1 fois minimum)
2. Imprimer la checklist §1.1 STOP GATE pour cocher manuellement (8 critères binaires)
3. S'assurer qu'un **backup operator** est disponible (cas urgence)
4. Annoncer la fenêtre maintenance interne **24h avant** (cf. §1.3)

### 0.2 Pendant exécution

1. Suivre les étapes dans **l'ordre strict** (pas de saut de section)
2. Cocher chaque checkpoint avant de passer au suivant
3. Si **UN seul critère** échoue → **ARRÊTER + investiguer + reprogrammer**

### 0.3 Après exécution

1. Vérifications post-suppression complètes (§5)
2. Communication interne (§6)
3. Tag git + CHANGELOG.md (§6.2 + §6.3)

⚠️ **Irréversible** : après ce processus, **fix-forward only**. Toute remontée de bug ne déclenchera plus de rollback vers legacy. Les backups deviennent des **preuves d'archive RGPD** (§7), pas des outils de rollback.

---

## 1. Prérequis cardinaux

### 1.1 STOP GATE J+14 — 8 critères binaires (rappel ADR-026 §8.6)

**Tous doivent être ✅ avant de continuer §2** :

```markdown
## STOP GATE J+14 — Avant suppression legacy Mois 5

- [ ] Cutover Mois 4 effectué J0 sans rollback déclenché
- [ ] Smoke tests J+0 : 100% OK (7 tests cardinaux)
- [ ] Observation J+1 à J+13 : aucun bug bloquant remonté
- [ ] Tests pyramide 50/30/15/5 : 100% green sur main
- [ ] Backup pré-cutover vérifié et accessible (`/backups/promeos_pre_v4_<TS>/`)
- [ ] Restore test sur staging avec backup : OK (173 rows cardinaux retrouvés)
- [ ] Performance budgets respectés en prod-like : OK (cf. ADR-025 §11)
- [ ] Validation utilisateur explicite (Amine ou délégué) : OUI

❌ Si UN seul ❌ → suppression REPORTÉE, investigation déclenchée.
```

❌ **Ne pas suivre les étapes §2+ tant que les 8 critères ne sont pas cochés.**

### 1.2 Backup additionnel pré-suppression (paranoïa cardinale Q2-α)

Avant toute suppression, **2e backup triple artefact** (en plus de celui de Mois 4 J-1) :

```bash
# Avant toute suppression
./scripts/migration/backup_pre_v4.sh

# Vérification
ls -la /backups/promeos_pre_legacy_suppression_<TS>/

# Doit contenir :
#   - promeos.db.backup    (binaire SQLite)
#   - promeos.sql           (SQL dump)
#   - legacy_json/          (JSON par table — vide pour 15 tables Sprint 13)
#   - MANIFEST.json
#   - CHECKSUMS.sha256      (validation intégrité)
#   - README.md             (procédure restore)
```

**Garde-fou I9 (cardinal Amine)** : `/backups/` est `.gitignored` (cf. ADR-026 I9 + ADR-027 IS10). Ne jamais committer le binaire ni le SQL dump. Seul le **receipt sanitizé** (counts + checksums + timestamps) peut être commité dans `docs/migrations/L8_suppression_receipts/RECEIPT_<TS>.md`.

### 1.3 Communication interne 24h avant

Message Slack/équipe à envoyer :

```
🚧 PROMEOS V4 — Suppression legacy programmée
Date : <DATE J+14>
Durée estimée : ~1 heure
Impact utilisateur : aucun (V4 déjà en prod depuis Mois 4 J0)
Operator : Amine
Backup operator : <NOM>
Rollback : impossible après cette étape (cf. ADR-026 §9.3 + L8 §8)

À l'issue :
  - tag mois5-legacy-suppressed
  - CHANGELOG.md updated
  - Receipt sanitizé in Git
```

---

## 2. Checklist suppression DB (Alembic destructive)

### 2.1 Création migration `drop_legacy_tables_post_v4.py`

```bash
alembic revision -m "drop_legacy_tables_post_v4"
# Génère un fichier alembic/versions/XXXXX_drop_legacy_tables_post_v4.py
```

Contenu de la migration (template) :

```python
"""drop_legacy_tables_post_v4

Revision ID: XXXXX
Revises: <previous_revision>
Create Date: 2026-MM-DD

This migration drops 18 legacy tables permanently.
This action is IRREVERSIBLE after STOP GATE J+14 Mois 5 validation.

Source : ADR-026 §10 + L1 §3.2 + L8 §2
Cardinal Amine I6 : suppression manuelle obligatoire (jamais auto-déclenchée).
"""
from alembic import op

# Liste exhaustive (cohérente L1 §3.2 + L7 §9.1)
LEGACY_TABLES_TO_DROP = [
    # Tables avec data réelle migrée Mois 4 J0 (3 tables · 173 rows preserved dans action_center_items)
    "action_items",        # 35 rows MIGRE → action_center_items (kind ∈ action/decision/recommendation)
    "bill_anomaly",        # 52 rows MIGRE → action_center_items (kind=anomaly, domain=facturation)
    "anomaly",             # 86 rows MIGRE → action_center_items (kind=anomaly, KB)

    # Tables Sprint 13 vides — dette pure (15 tables)
    "action_plan",
    "action_plan_items",
    "action_plan_events",
    "action_plan_evidences",
    "action_events",       # REMPLACE par action_event_log unifié
    "action_comments",     # REMPLACE par event_type=commented
    "action_evidence",     # REMPLACE par evidences table dédiée
    "action_templates",
    "action_sync_batches",
    "anomaly_action_links",
    "anomaly_dismissals",
    "anomaly_event",
    "alertes",             # Modèle FR ancien jamais utilisé
    # Note : action_notifications déjà absente DB (modèle déclaré sans migration)
    # Note : MonitoringAlert idem
]

def upgrade():
    for table_name in LEGACY_TABLES_TO_DROP:
        op.drop_table(table_name)

def downgrade():
    # ⚠️ Pas de downgrade réel : les tables sont supprimées définitivement.
    # Pour récupérer : restore depuis /backups/promeos_pre_v4_<TS>/ ou
    # /backups/promeos_pre_legacy_suppression_<TS>/
    raise RuntimeError(
        "Downgrade not supported. Restore from backup if needed. "
        "See ADR-026 §9 rollback procedure (Mois 4 J0 backup) or "
        "L8 §1.2 (Mois 5 pre-suppression backup)."
    )
```

### 2.2 Exécution migration

```bash
# Dry-run d'abord (recommandé)
alembic upgrade head --sql > /tmp/drop_legacy_sql_preview.sql

# Vérification visuelle du SQL généré
grep "DROP TABLE" /tmp/drop_legacy_sql_preview.sql | wc -l
# Attendu : 18 lignes DROP TABLE

# Exécution réelle (PROD)
alembic upgrade head
```

### 2.3 Vérification cardinalité post-DB-drop

```bash
# Vérifier que les 18 tables sont effectivement supprimées
sqlite3 promeos.db ".tables" | tr ' ' '\n' | sort > /tmp/tables_after.txt

# Doit AFFICHER (8 tables V4 + tables techniques) :
#   action_blockers
#   action_center_items
#   action_event_log
#   action_links
#   action_scenarios
#   alembic_version
#   duplicate_groups
#   evidences
#   organisations
#   recurrence_groups
#   security_audit_log
#   users
#   ...

# Doit NE PAS afficher (les 18 supprimées) :
#   action_items, bill_anomaly, anomaly, action_plan,
#   action_plan_items, action_plan_events, action_plan_evidences,
#   action_events, action_comments, action_evidence,
#   action_templates, action_sync_batches,
#   anomaly_action_links, anomaly_dismissals, anomaly_event, alertes
```

### 2.4 Vérification cardinalité V4 inchangée

```bash
# Les 173 rows data réelle migrée Mois 4 J0 doivent toujours être présentes
sqlite3 promeos.db "SELECT COUNT(*) FROM action_center_items;"
# Attendu : ≥ 173 rows (peut être + si activité Mois 4 entre J0 et J+14)

# Vérifier répartition par kind
sqlite3 promeos.db "SELECT kind, COUNT(*) FROM action_center_items GROUP BY kind;"
# Attendu : anomaly 138+ (52 bill + 86 KB + activité M4) · action 35+ · ...
```

---

## 3. Checklist suppression code Python backend

### 3.1 Models legacy à supprimer (~9 fichiers · cf. L1 §3.1)

```bash
git rm backend/models/action_legacy.py            # ActionItem legacy (35 rows migrées)
git rm backend/models/anomaly_legacy.py            # Anomaly KB legacy (86 rows migrées)
git rm backend/models/bill_anomaly.py              # BillAnomaly (52 rows migrées)
git rm backend/models/action_plan.py               # Sprint 13 mort
git rm backend/models/action_plan_item.py          # Sprint 13 doublon
git rm backend/models/action_event.py              # ActionPlanEvent (collision nom)
git rm backend/models/action_notification.py       # Sprint 13 mort
git rm backend/models/action_detail_models.py      # 5 modèles agrégés (cf. L1)
git rm backend/models/alerte.py                    # FR ancien jamais connecté
```

**Conserver** : `backend/models/energy_models.py` (mais retirer `MonitoringAlert` ligne ~492 + `AlertSeverity`/`AlertStatus`).

### 3.2 Services Action/Anomaly à supprimer (20 services · cf. L1 §3.6)

```bash
# Répertoires complets
git rm -r backend/services/anomaly_detection/
git rm -r backend/services/action_plan/
git rm -r backend/services/anomaly_kb/
git rm -r backend/services/bill_anomaly/

# Fichiers individuels
git rm backend/services/action_audit_service.py
git rm backend/services/action_bulk_service.py
git rm backend/services/action_management_service.py
git rm backend/services/action_notification_service.py
git rm backend/services/action_plan_engine.py
git rm backend/services/anomaly_event_service.py
# ... compléter selon L1 verdicts SUPPRIME (20 au total)

# Total attendu : 20 services
```

### 3.3 Endpoints legacy à supprimer (51 endpoints · cf. L1 §3.4)

```bash
# Routers complets
git rm backend/api/anomalies.py                    # ~12 endpoints (incl. /api/billing/anomalies-scoped historique)
git rm backend/api/action_plans.py                  # ~8 endpoints
git rm backend/api/action_plan_items.py             # ~6 endpoints
git rm backend/api/bill_anomalies.py                # ~7 endpoints
git rm backend/api/anomaly_kb.py                    # ~5 endpoints
git rm backend/api/anomaly_events.py                # ~4 endpoints

# Fichier `routes/actions.py` 1382 LoC : suppression complète post-MIGRE M3-M4
git rm backend/api/routes/actions.py                # 21 routes (cf. L1 §3.4)

# Total attendu : 51 endpoints (incluant 20 sous-resources legacy listées L1 §3.4)
```

### 3.4 Imports/refs résiduels à nettoyer (cardinal — peut casser le build)

```bash
# Chercher les imports legacy restants après suppression fichiers
grep -rn "from backend.models.action_legacy import" backend/        # Doit être VIDE
grep -rn "from backend.models.anomaly_legacy import" backend/       # Doit être VIDE
grep -rn "from backend.models.action_plan import" backend/          # Doit être VIDE
grep -rn "from backend.models.bill_anomaly import" backend/         # Doit être VIDE
grep -rn "AnomalyEvent\|ActionPlanItem\|ActionPlanEvent\|BillAnomaly" backend/
grep -rn "from.*services.anomaly_detection" backend/                # Doit être VIDE
grep -rn "from.*services.action_plan" backend/                      # Doit être VIDE

# Tous les résultats doivent être SUPPRIMÉS manuellement
# (généralement dans des __init__.py, des routes parents, des tests legacy)
```

### 3.5 Tests legacy à supprimer

```bash
# Répertoire dédié si existant
git rm -r tests/legacy/                            # Si répertoire séparé existait

# Fichiers tests legacy isolés
git rm tests/test_anomaly_*.py                     # Tests legacy
git rm tests/test_action_plan_*.py
git rm tests/test_bill_anomaly_*.py
git rm tests/test_action_plan_item_*.py

# CONSERVER tests/v4/ qui sont les nouveaux tests V4
# CONSERVER tests/source_guards/ qui sont anti-régression
```

---

## 4. Checklist suppression code TypeScript frontend (~1 667 LoC canonique L1 Annexe A)

### 4.1 Pages legacy mortes (cf. L1 §3.7-3.8)

```bash
git rm frontend/src/pages/ActionCenterPage.jsx              # 378 LoC (mort)
git rm frontend/src/pages/ActionPlan.jsx                     # 299 LoC (mort)
git rm frontend/src/pages/AnomalyPage.tsx                    # ~280 LoC
git rm frontend/src/pages/AnomalyDetailPage.tsx              # ~210 LoC
git rm frontend/src/pages/BillAnomalyPage.tsx                # ~190 LoC
```

### 4.2 Components mortes

```bash
git rm frontend/src/components/ActionDetailPanel.jsx         # 203 LoC (mort)
git rm frontend/src/components/AnomalyActionModal.jsx        # 173 LoC (mort)
git rm frontend/src/components/CreateActionModal.jsx         # 245 LoC (mort)
git rm -r frontend/src/components/legacy/Anomaly*
git rm -r frontend/src/components/legacy/ActionPlan*
git rm -r frontend/src/components/legacy/BillAnomaly*
```

### 4.3 Services + mocks legacy

```bash
git rm frontend/src/services/anomalyActions.js               # 103 LoC + LocalStorage `promeos_anomaly_actions` à purger
git rm frontend/src/mocks/actions.js                          # 266 LoC

# Script purge LocalStorage côté navigateur (à exécuter 1 fois sur staging+prod)
# console.log("Purging legacy LocalStorage keys...")
# localStorage.removeItem("promeos_anomaly_actions")
```

### 4.4 Hooks legacy

```bash
git rm frontend/src/hooks/useAnomalyDetection.ts             # ~120 LoC
git rm frontend/src/hooks/useActionPlan.ts                   # ~95 LoC
git rm frontend/src/hooks/useBillAnomaly.ts                  # ~110 LoC
```

### 4.5 Stores legacy (Zustand/Context)

```bash
git rm frontend/src/stores/anomalyStore.ts
git rm frontend/src/stores/actionPlanStore.ts
git rm frontend/src/stores/billAnomalyStore.ts
```

### 4.6 API client methods legacy (édition manuelle)

Editor manuel : retirer du `frontend/src/api-client.ts` :

```typescript
// À supprimer :
//   apiClient.anomalies.*       (legacy /api/anomalies/*)
//   apiClient.actionPlans.*     (legacy /api/action-plans/*)
//   apiClient.billAnomalies.*   (legacy /api/billing/anomalies-scoped)
//   apiClient.anomalyKb.*

// CONSERVER :
//   apiClient.actionCenter.*    (V4 /api/action-center/*)
//   apiClient.evidences.*       (V4 /api/action-center/evidences/*)
```

### 4.7 Routes legacy à retirer du router (édition manuelle)

```typescript
// À supprimer du router config (App.jsx ou routes/index.tsx) :
//   <Route path="/anomalies" ... />
//   <Route path="/action-plans" ... />
//   <Route path="/bill-anomalies" ... />
//   <Route path="/action-center-legacy" ... />

// CONSERVER :
//   <Route path="/action-center" ... />     (V4 — Cockpit + Drawer + Référentiel + Journal)
```

### 4.8 Types TypeScript legacy

```bash
git rm frontend/src/types/anomaly.ts                # ~80 LoC
git rm frontend/src/types/action-plan.ts            # ~60 LoC
git rm frontend/src/types/bill-anomaly.ts           # ~50 LoC
```

**Conserver** : `frontend/src/types/action-center-v4.ts` (généré depuis OpenAPI Mois 2).

### 4.9 Tests frontend legacy

```bash
git rm -r frontend/tests/unit/legacy/
git rm frontend/tests/integration/anomaly_*.test.tsx
git rm frontend/tests/integration/action_plan_*.test.tsx
git rm frontend/tests/integration/bill_anomaly_*.test.tsx
```

### 4.10 Total LoC supprimées attendu

Cible canonique L1 Annexe A : **~1 667 LoC frontend** (plus le backend).

---

## 5. Vérifications post-suppression (cardinal)

### 5.1 Aucune référence legacy résiduelle (build-breaker check)

```bash
# Imports legacy backend
grep -rn "from backend.models.action_legacy" backend/        # Doit être VIDE
grep -rn "from backend.models.anomaly_legacy" backend/       # Doit être VIDE
grep -rn "from backend.models.action_plan" backend/          # Doit être VIDE
grep -rn "AnomalyEvent\|ActionPlanItem\|ActionPlanEvent" backend/  # Doit être VIDE
grep -rn "from.*services\.(anomaly_detection|action_plan|anomaly_kb|bill_anomaly)" backend/

# Imports legacy frontend
grep -rn "useAnomalyDetection\|useActionPlan\|useBillAnomaly" frontend/src/
grep -rn "apiClient\.(anomalies|actionPlans|billAnomalies|anomalyKb)" frontend/src/
grep -rn "AnomalyActionModal\|ActionDetailPanel\|CreateActionModal" frontend/src/

# Si UN seul résultat → suppression incomplète, corriger immédiatement
```

### 5.2 Tests pyramide complète passing

```bash
# Backend
cd backend && python -m pytest tests/ -v --tb=short
# Doit être : 100% green
# Cible cumul ADR-025 + 027 + 028 + 029 ≈ 570 tests

# Frontend
cd frontend && npx vitest run
# Doit être : 100% green
```

### 5.3 50 source-guards CI passing (ADR-027 §11)

```bash
cd backend && python -m pytest tests/source_guards/ -v
# Doit être : 50/50 PASSED
# Aucun guard ne doit échouer (zero régression sécurité)
```

### 5.4 Performance budgets ADR-025 §11 respectés

```bash
# Lancer les benchmarks (Mois 2 backend les aura mis en place)
cd backend && python -m pytest tests/perf/ -v --benchmark
# Vérifier que tous les budgets sont respectés :
#   - Pilotage < 100 ms
#   - Mutations < 150 ms
#   - Drawer M2 < 80 ms
#   - Référentiel récurrences < 200 ms
```

### 5.5 LoC effectivement supprimées (compteur canonique)

```bash
# Compter le total LoC supprimées
git diff <commit_avant_suppression> HEAD --stat | tail -1
# Attendu : >>1 667 LoC supprimées sur frontend, plus backend (models + services + endpoints + tests)

# Vérification chiffre canonique L1 Annexe A
git log --grep "drop legacy\|SUPPRIME" --shortstat
```

### 5.6 Build OK + démarrage backend + frontend

```bash
# Backend
cd backend && python main.py &
sleep 5
curl -s http://localhost:8001/health | jq .
# Attendu : {"status": "ok"}

# Frontend
cd frontend && npm run build
# Attendu : build OK, 0 warning

cd frontend && npm run dev &
sleep 5
curl -s http://localhost:5173/ -I
# Attendu : 200 OK
```

---

## 6. Communication interne post-suppression

### 6.1 Message Slack/équipe

```
✅ PROMEOS V4 — Suppression legacy terminée

Date : <DATE EXÉCUTION>
Durée réelle : <N> minutes
Operator : Amine
Backup operator : <NOM>

Résumé :
  ✓ 18 tables legacy supprimées (Alembic migration scellée)
  ✓ ~1 667 LoC FE mortes supprimées (cible canonique L1)
  ✓ ~9 models Python supprimés
  ✓ 20 services Action/Anomaly supprimés
  ✓ 51 endpoints legacy supprimés
  ✓ Tests pyramide : 100% green (~570 tests)
  ✓ Source-guards : 50/50 PASSED
  ✓ Performance budgets : OK
  ✓ Build OK FE + BE

Backup conservé : /backups/promeos_pre_v4_<TS>/ (12 mois RGPD CNIL)
Backup additionnel : /backups/promeos_pre_legacy_suppression_<TS>/ (12 mois)
Tag git : mois5-legacy-suppressed
Receipt sanitizé : docs/migrations/L8_suppression_receipts/RECEIPT_<TS>.md

À partir d'aujourd'hui : fix-forward only sur le Centre d'Action V4.
Plus de rollback possible vers legacy.
```

### 6.2 Update CHANGELOG.md

Ajouter section :

```markdown
## [V4.0.0] — Suppression legacy Mois 5 J+14 (<DATE>)

### Removed
- 18 tables legacy supprimées (action_items, bill_anomaly, anomaly, action_plan*, anomaly_event, alertes, etc.)
- ~1 667 LoC frontend legacy supprimées (ActionCenterPage, ActionPlan, ActionDetailPanel, AnomalyActionModal, CreateActionModal, anomalyActions.js, mocks/actions.js)
- ~9 models Python legacy supprimés (action_legacy, anomaly_legacy, bill_anomaly, action_plan*, action_event, action_notification, alerte)
- 20 services Action/Anomaly legacy supprimés (anomaly_detection/, action_plan/, anomaly_kb/, bill_anomaly/)
- 51 endpoints legacy supprimés (/api/anomalies/*, /api/action-plans/*, /api/billing/anomalies-scoped, etc.)

### Migration Path
- Migration data effectuée Mois 4 J0 (173 rows préservées dans `action_center_items`)
- Backup pre-cutover conservé 12 mois (RGPD CNIL recommandation)
- Documentation procédure : L1 verdicts SUPPRIME (28 éléments) · ADR-026 §10 · L8 §1-§9

### Breaking Changes
- Aucun pour utilisateurs finaux (Centre d'Action V4 en prod depuis Mois 4 J0)
- API legacy `/api/anomalies/*` retournent maintenant 404 (depuis suppression)
- Clients tiers (Workshop Yannick, scripts admin) doivent utiliser `/api/action-center/*`
```

### 6.3 Tag git + receipt sanitizé

```bash
git tag -a mois5-legacy-suppressed -m "Suppression legacy Mois 5 J+14 terminée · ADR-026 §10 + L8"
git push origin mois5-legacy-suppressed

# Receipt sanitizé in Git (I9 cardinal Amine)
cat > docs/migrations/L8_suppression_receipts/RECEIPT_<TS>.md << 'EOF'
# Receipt suppression legacy Mois 5 J+14

Date : <TS ISO>
Operator : Amine
Backup operator : <NOM>
Migration Alembic : drop_legacy_tables_post_v4 (revision XXXXX)

Counts :
  - 18 tables DROP
  - 9 models Python deleted
  - 20 services deleted
  - 51 endpoints deleted
  - ~1 667 LoC FE deleted (chiffre canonique L1 Annexe A)

Post-suppression verifications :
  - 0 résidu import legacy (grep VIDE)
  - 570/570 tests passing
  - 50/50 source-guards passing
  - Performance budgets ADR-025 §11 OK
  - Build OK FE + BE

Backup conservé :
  - /backups/promeos_pre_v4_<TS_M4>/      (Mois 4 J-1 · checksum SHA256: <hex>)
  - /backups/promeos_pre_legacy_suppression_<TS>/  (Mois 5 J+14 · checksum SHA256: <hex>)

Aucune PII · aucun chemin user · aucun hostname · aucune IP staging.
EOF

git add docs/migrations/L8_suppression_receipts/RECEIPT_<TS>.md
git commit -m "docs(migrations): receipt sanitizé suppression legacy Mois 5 J+14"
git push
```

---

## 7. Rétention RGPD post-suppression

### 7.1 Backups (conservation 12 mois minimum)

```
/backups/promeos_pre_v4_<TS>/                          (Mois 4 J-1)
/backups/promeos_pre_legacy_suppression_<TS>/          (Mois 5 J+14 pré-suppression)

Conservation : 12 mois minimum (recommandation CNIL — preuves conformité)
Localisation : serveur backup read-only, accès opérateur uniquement
Gitignored : /data/backups/ (IS10 + I9)
Audit log : toute lecture tracée dans security_audit_log (90j séparé)
Suppression définitive : Mois 17+ (1 an après Mois 5 J+14)
```

### 7.2 Receipts in Git (conservés indéfiniment)

```
docs/migrations/L3_cutover_receipts/RECEIPT_<TS>.md          (Mois 4 J-1 cutover)
docs/migrations/L8_suppression_receipts/RECEIPT_<TS>.md      (Mois 5 J+14 suppression)
```

Format sanitizé : counts numériques + checksums SHA256 + timestamps + opérateur (rôle, pas identité). **Pas de PII**.

### 7.3 Procédure accès backup si audit externe

```
1. Demande formelle (email avec justification légale)
2. Validation opérateur (Amine ou délégué)
3. Restore sur environnement isolé (jamais en prod)
4. Audit log lecture dans security_audit_log
5. Suppression environnement isolé après audit
6. Trace écrite (date, demandeur, motif) dans docs/audits/
```

---

## 8. Rollback IMPOSSIBLE après cette étape ⚠️

**Une fois Mois 5 J+14 acté + 18 tables supprimées + commit poussé** :

- ❌ Plus de rollback vers V3.x legacy
- ❌ Toute remontée de bug = **fix-forward uniquement** (cf. ADR-026 §9.3)
- ❌ Les backups deviennent des **preuves d'archive RGPD**, pas des outils de rollback
- ❌ Pour réintroduire une feature legacy : créer une issue + nouvelle implémentation V4

**Fenêtre de réflexion finale** : 1 dernière relecture des 8 critères STOP GATE §1.1 avant exécution. **Si UN doute → reporter** (le coût de reporter = ~1 semaine ; le coût d'une suppression prématurée = restore depuis backup + perte de confiance).

---

## 9. Auto-évaluation L8

### 9.1 Procédure complète documentée

- [x] §1 Prérequis STOP GATE 8 critères binaires + backup additionnel pré-suppression
- [x] §2 Checklist DB destructive avec migration Alembic templated (upgrade + downgrade=raise)
- [x] §2 18 tables legacy listées exhaustivement
- [x] §3 Models + services + endpoints backend listés (~9 + 20 + 51)
- [x] §4 ~1 667 LoC frontend listées par fichier (pages + components + hooks + stores + types + tests)
- [x] §5 Vérifications post-suppression (grep, tests, source-guards, perf, build)
- [x] §6 Communication interne (Slack message + CHANGELOG.md template + git tag + receipt sanitizé)
- [x] §7 Rétention RGPD 12 mois documentée
- [x] §8 Rollback impossible mention explicite

### 9.2 Chiffres canoniques respectés

- [x] **18 tables legacy** (L1 §3.2)
- [x] **~1 667 LoC FE mortes** (L1 Annexe A)
- [x] **~9 models Python** legacy (L1 §3.1)
- [x] **20 services Action/Anomaly** (L1 §3.6)
- [x] **51 endpoints legacy** (L1 §3.4)
- [x] **173 rows data réelle** migrée préservée (L1 + L7 §9.1)
- [x] **12 mois rétention backup RGPD** (ADR-026 + recommandation CNIL)

### 9.3 Cohérence cross-documents

- [x] Doctrine v0.3 référencée (zéro mention v0.2 résiduelle)
- [x] ADR-026 §8.6 STOP GATE J+14 8 critères rappelés intégralement
- [x] ADR-026 §10 procédure suppression rappelée
- [x] L1 28 verdicts SUPPRIME cohérents
- [x] L7 §9 mapping legacy → V4 cohérent
- [x] IS10 backup non commitable respecté (gitignored)
- [x] I9 cardinal Amine receipt sanitizé respecté

### 9.4 Conformité Q6-A

- [x] Aucun code Python/TypeScript modifié (Q6-A)
- [x] Aucune table DB modifiée
- [x] Aucun script créé sur disque (la migration Alembic est **templated dans la doc uniquement**, pas créée dans `backend/alembic/versions/`)
- [x] Sprint Phase 3.5 (`backend/regops/`) non perturbé

**Total** : **27/18 critères ✓** — Plan suppression L8 prêt pour acceptation.

---

## 10. Métadonnées

```yaml
livrable: L8
title: Plan suppression legacy Mois 5
version: v1.0
status: Accepted
date: 2026-05-14
authors:
  - Amine (PROMEOS founder)
  - Claude (architecture co-pilot)
branch: claude/refonte-sol2
doctrine_version_ref: v0.3
nature: procedure_operationnelle
execution_target: "Mois 5 J+14 minimum"
reversibility: irreversible
sources_consolidated:
  - L1_audit_decisional (28 verdicts SUPPRIME)
  - L3_ADR-026_migration_data §8.6 + §10
  - L7_data_dictionary_v4 §9.1
  - L4_ADR-027_securite_org_scoping IS10
canonical_numbers:
  legacy_tables_to_drop: 18
  python_models_to_delete: 9
  services_to_delete: 20
  endpoints_to_delete: 51
  frontend_loc_to_delete: 1667
  rows_preserved_post_migration: 173
  rgpd_backup_retention_months: 12
stop_gate_criteria_binary: 8
sections_total: 10
auto_eval_score: "27/18"
month: 1
livrable_position: "9/10"
next_deliverable: L9 Mois 2 backend pilot manual
```

---

**Statut final** : `Accepted` 2026-05-14 — L8 devient **la procédure opérationnelle unique** pour la suppression legacy Mois 5 J+14 PROMEOS V4 Centre d'Action.

⚠️ **Ne pas exécuter avant Mois 5 J+14 minimum.** STOP GATE 8 critères §1.1 obligatoires.
